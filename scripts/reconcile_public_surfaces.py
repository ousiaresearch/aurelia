#!/usr/bin/env python3
"""Reconcile local run artifacts, HF exports, and Cloudflare public surfaces.

This is an offline-friendly reconciler. All real network access lives
behind ``fetch_cloudflare_counts`` and is opt-in via the CLI. The core
counting and comparison logic works against local directories.

Output sections:

- Local artifacts
- HF exports
- Cloudflare public dashboard
- Count mismatches
- Known D1 cap limitation
- Recommended remediation
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

WORLDS = ("solara", "arkos", "mirithane", "valdris", "verge")

#: A dataset counts as "fully public" if its per-world parquet files are
#: present in the export root. Some worlds missing → "partial" (D1 cap
#: or partial ingestion). None → "missing".
D1_CAP_NOTE = (
    "D1 Free plan 500MB cap caused partial movement/diffusion ingestion for "
    "long runs; HF/local Parquet exports are the complete research archive for "
    "Phase 11 until D1 is upgraded or split."
)


# ---------------------------------------------------------------------------
# Local run counts
# ---------------------------------------------------------------------------

def _world_active_pop(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(str(db_path))
    try:
        try:
            return int(conn.execute(
                "SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'"
            ).fetchone()[0])
        except sqlite3.OperationalError:
            return 0
    finally:
        conn.close()


def load_local_counts(run_dirs: list[Path]) -> dict[str, Any]:
    """Return aggregate counts across the given run directories.

    Picks the most-recently-modified run as the canonical one for
    headline numbers but records every run for the per-run section.
    """
    runs = [Path(r) for r in run_dirs if Path(r).exists()]
    if not runs:
        return {"runs": [], "worlds": {}, "federation_causal_events": 0}

    per_run: list[dict[str, Any]] = []
    for run in runs:
        worlds = {w: _world_active_pop(run / f"{w}.db") for w in WORLDS}
        fed_db = run / "federation.db"
        fed_events = 0
        if fed_db.exists():
            try:
                conn = sqlite3.connect(str(fed_db))
                try:
                    row = conn.execute("SELECT COUNT(*) FROM causal_events").fetchone()
                    fed_events = int(row[0]) if row else 0
                except sqlite3.OperationalError:
                    fed_events = 0
                finally:
                    conn.close()
            except sqlite3.Error:
                fed_events = 0
        per_run.append({
            "dir": str(run),
            "label": run.name,
            "worlds": worlds,
            "federation_causal_events": fed_events,
        })

    # Headline numbers: most-recently-modified run.
    canonical = max(per_run, key=lambda r: r["label"])
    return {
        "runs": per_run,
        "worlds": canonical["worlds"],
        "federation_causal_events": canonical["federation_causal_events"],
        "canonical_run": canonical["label"],
    }


# ---------------------------------------------------------------------------
# HF export counts
# ---------------------------------------------------------------------------

def load_hf_export_counts(root: Path) -> dict[str, Any]:
    """Return per-dataset file counts and total NPC count where possible.

    The HF export shape differs by dataset (per-world for npc-population,
    flat for causal-events). Run/world are extracted from ``configs.json``
    so the report is shape-agnostic.
    """
    if not root.exists():
        return {}
    out: dict[str, Any] = {}
    for ds in ("aurelia-causal-events", "aurelia-federation-causal",
               "aurelia-civilization-metrics", "aurelia-npc-population"):
        ds_dir = root / ds
        configs_path = ds_dir / "configs.json"
        if not configs_path.exists():
            continue
        try:
            payload = json.loads(configs_path.read_text())
        except json.JSONDecodeError:
            continue
        data_section = payload.get("data", {}) or {}
        all_runs = sorted(data_section.keys())
        all_files: list[str] = []
        for run, run_files in data_section.items():
            all_files.extend(run_files)
        # Find the parent of <world>/<file> entries when nested; otherwise just the leaf.
        worlds_seen: set[str] = set()
        for rel in all_files:
            parts = Path(rel).parts
            # Convention: data/<run>/<world>/train.parquet → world is the 3rd segment.
            if len(parts) >= 3 and parts[-1] == "train.parquet":
                candidate = parts[-2]
                if candidate in WORLDS:
                    worlds_seen.add(candidate)
        out[ds] = {
            "files": len(all_files),
            "runs": all_runs,
            "worlds_present": sorted(worlds_seen),
            "expected_worlds": list(WORLDS),
            "missing_worlds": [w for w in WORLDS if w not in worlds_seen],
        }
    return out


# ---------------------------------------------------------------------------
# Cloudflare (network, only when the caller asks)
# ---------------------------------------------------------------------------

def fetch_cloudflare_counts(
    url: str,
    *,
    user_agent: str = "Aurelia-Reconciler/1.0",
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Fetch a public Cloudflare dashboard JSON. Network call.

    On HTTP error or network failure, returns a payload with
    ``reachable=False`` and the status code or error class — never raises.
    """
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return {"reachable": True, "status": 200, "raw": body[:512], "ok": False}
    except urllib.error.HTTPError as exc:
        return {"reachable": False, "status": exc.code, "error": exc.reason}
    except Exception as exc:
        return {"reachable": False, "status": None, "error": repr(exc)}

    runs = payload.get("runs") or []
    return {
        "reachable": True,
        "status": 200,
        "ok": bool(payload.get("ok", True)),
        "run_count": len(runs),
        "run_ids": [r.get("id") or r.get("run_id") for r in runs if r.get("id") or r.get("run_id")],
        "federation_causal_events": sum(int(r.get("federation_causal_events", 0) or 0) for r in runs),
    }


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare_counts(local: dict[str, Any], hf: dict[str, Any], cf: dict[str, Any]) -> dict[str, Any]:
    """Diff the three surfaces and produce a status per comparison row.

    Status values:
    - ``ok`` — surfaces agree (or one surface is N/A and the others match)
    - ``partial`` — D1 cap / partial ingestion: HF or CF has *some but not all* of the data
    - ``missing`` — surface expected to have data, has none
    - ``unreachable`` — surface could not be queried (Cloudflare only)
    """
    rows: list[dict[str, Any]] = []

    # NPC count by world. The HF export rows are not parsed here (cost);
    # we report local aggregate + HF file count for context.
    local_worlds = local.get("worlds", {}) or {}
    hf_npc = hf.get("aurelia-npc-population", {}) if hf else {}
    hf_files = int(hf_npc.get("files", 0)) if hf_npc else 0
    local_total_npc = sum(int(v or 0) for v in local_worlds.values())
    if local_total_npc and hf_files:
        npc_status = "ok"
        npc_note = f"local NPCs={local_total_npc}, HF npc files={hf_files} (rows not parsed)"
    elif local_total_npc and not hf_files:
        npc_status = "missing"
        npc_note = "local has NPCs but HF export has no npc-population files"
    elif not local_total_npc and hf_files:
        npc_status = "missing"
        npc_note = "HF has npc-population files but no local runs found"
    else:
        npc_status = "missing"
        npc_note = "no local NPCs and no HF files"
    rows.append({
        "name": "npc count (local vs hf)",
        "local": local_total_npc,
        "hf_files": hf_files if hf else "n/a",
        "cf": "n/a",
        "status": npc_status,
        "note": npc_note,
    })

    # Per-dataset HF coverage
    if hf:
        for ds in ("aurelia-causal-events", "aurelia-federation-causal",
                   "aurelia-civilization-metrics", "aurelia-npc-population"):
            info = hf.get(ds, {})
            files = info.get("files", 0)
            missing = info.get("missing_worlds", [])
            # The per-world check is only meaningful for the per-world-shaped
            # dataset (aurelia-npc-population). The other three are flat-per-run.
            if files == 0:
                status = "missing"
                note = "no parquet files"
                missing = []
            elif ds == "aurelia-npc-population" and missing:
                status = "partial"
                note = f"missing worlds: {', '.join(missing)} (likely D1 cap)"
            elif ds == "aurelia-npc-population":
                status = "ok"
                note = "all 5 worlds present across all runs"
            else:
                status = "ok" if files > 0 else "missing"
                note = "flat-per-run shape; per-world check not applicable"
            rows.append({
                "name": f"hf coverage: {ds}",
                "files": files,
                "missing_worlds": missing if ds == "aurelia-npc-population" else [],
                "status": status,
                "note": note,
            })

    # Federation causal events
    local_fed = int(local.get("federation_causal_events", 0) or 0)
    cf_fed = cf.get("federation_causal_events") if cf else None
    if cf.get("reachable") is False:
        rows.append({
            "name": "federation causal events (cf)",
            "local": local_fed,
            "cf": "unreachable",
            "status": "unreachable",
            "note": cf.get("error", "unknown"),
        })
    elif cf_fed is not None:
        status = _status_pair(local_fed, cf_fed)
        note = ""
        if local_fed > 0 and cf_fed < local_fed:
            status = "partial"
            note = f"local={local_fed}, cf={cf_fed} (D1 cap may be truncating)"
        rows.append({
            "name": "federation causal events (local vs cf)",
            "local": local_fed,
            "cf": cf_fed,
            "status": status,
            "note": note,
        })

    return {"comparisons": rows}


def _status_pair(a: int | None, b: int | None) -> str:
    if a is None and b is None:
        return "missing"
    if a is None or b is None:
        return "missing"
    if a == 0 and b == 0:
        return "missing"
    if a == b:
        return "ok"
    return "partial"


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def render_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Public Surface Reconciliation")
    lines.append("")
    lines.append(f"- generated_at: {result.get('generated_at', '?')}")
    lines.append(f"- canonical local run: `{result.get('local', {}).get('canonical_run', '?')}`")
    lines.append("")

    lines.append("## Local artifacts")
    local = result.get("local", {})
    if local.get("runs"):
        for run in local["runs"]:
            lines.append(f"### `{run['label']}`")
            lines.append(f"- federation causal events: {run['federation_causal_events']}")
            for w in WORLDS:
                lines.append(f"- {w}: {run['worlds'].get(w, 0)} active NPCs")
            lines.append("")
    else:
        lines.append("- (no local runs found)")
        lines.append("")

    lines.append("## HF exports")
    hf = result.get("hf_export", {})
    if not hf:
        lines.append("- (no HF export root found)")
    else:
        for ds, info in hf.items():
            lines.append(f"### {ds}")
            lines.append(f"- files: {info.get('files', 0)}")
            if info.get("runs"):
                lines.append(f"- runs: {', '.join(info['runs'])}")
            if info.get("missing_worlds"):
                lines.append(f"- missing worlds: {', '.join(info['missing_worlds'])} (D1 cap likely)")
            lines.append("")
    lines.append("")

    lines.append("## Cloudflare public dashboard")
    cf = result.get("cloudflare", {})
    if not cf:
        lines.append("- (no cloudflare payload provided)")
    elif cf.get("reachable") is False:
        lines.append(f"- reachable: false")
        lines.append(f"- status: {cf.get('status', '?')}")
        lines.append(f"- error: {cf.get('error', '?')}")
    else:
        lines.append(f"- reachable: true")
        lines.append(f"- run_count: {cf.get('run_count', 0)}")
        if cf.get("federation_causal_events") is not None:
            lines.append(f"- federation causal events: {cf['federation_causal_events']}")
    lines.append("")

    lines.append("## Count mismatches")
    comp = result.get("comparisons", [])
    if not comp:
        lines.append("- (no comparisons to report)")
    else:
        for row in comp:
            status = row.get("status", "?")
            note = row.get("note", "")
            details = " ".join(
                f"{k}={v}" for k, v in row.items() if k not in ("name", "status", "note")
            )
            lines.append(f"- [{status}] {row.get('name', '?')}: {details}{(' — ' + note) if note else ''}")
    lines.append("")

    lines.append("## Known D1 cap limitation")
    lines.append("")
    lines.append(D1_CAP_NOTE)
    lines.append("")

    lines.append("## Recommended remediation")
    for rec in result.get("recommendations", []):
        lines.append(f"- {rec}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def reconcile(
    run_dirs: list[Path],
    hf_root: Path,
    cloudflare_url: str | None = None,
    *,
    fetch_cf: bool = False,
    user_agent: str = "Aurelia-Reconciler/1.0",
) -> dict[str, Any]:
    local = load_local_counts(run_dirs)
    hf = load_hf_export_counts(hf_root) if hf_root else {}
    if fetch_cf and cloudflare_url:
        cf = fetch_cloudflare_counts(cloudflare_url, user_agent=user_agent)
    else:
        cf = {}
    comparison = compare_counts(local, hf, cf)
    recommendations = _recommend(local, hf, cf, comparison)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "local": local,
        "hf_export": hf,
        "cloudflare": cf,
        **comparison,
        "recommendations": recommendations,
    }


def _recommend(local, hf, cf, comparison) -> list[str]:
    recs: list[str] = []
    statuses = {r.get("status") for r in comparison.get("comparisons", [])}
    if "partial" in statuses:
        recs.append(
            "Re-run scripts/export_hf_dataset.py to regenerate missing Parquet files; "
            "treat the local Parquet export as the source of truth for long runs."
        )
    if "missing" in statuses:
        recs.append(
            "Some datasets have zero local coverage; run a Phase 11 export or smoke "
            "run to populate them."
        )
    if cf.get("reachable") is False:
        recs.append(
            f"Cloudflare dashboard unreachable (status={cf.get('status')}); "
            "verify the Worker URL and that your User-Agent is set."
        )
    if not local.get("runs"):
        recs.append(
            "No local run artifacts found; run `causal_run.py --clean` to produce a "
            "smoke run, then re-run the reconciler."
        )
    if not recs:
        recs.append("All three public surfaces are consistent.")
    return recs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", action="append", type=Path, default=[],
                        help="Local run dir (may be passed multiple times)")
    parser.add_argument("--hf-root", type=Path, default=Path("/tmp/hf-export"))
    parser.add_argument("--cloudflare-dashboard", type=Path, default=None,
                        help="Public dashboard URL (optional; only fetched with --fetch-cloudflare)")
    parser.add_argument("--fetch-cloudflare", action="store_true",
                        help="Actually hit the network for the Cloudflare dashboard")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    url = str(args.cloudflare_dashboard) if args.cloudflare_dashboard else None
    result = reconcile(
        args.run_dir,
        args.hf_root,
        cloudflare_url=url,
        fetch_cf=args.fetch_cloudflare,
    )
    md = render_markdown(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(md)
        print(f"wrote {args.output}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
