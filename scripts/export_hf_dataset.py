#!/usr/bin/env python3
"""
export_hf_dataset.py — Export Aurelia SQLite simulation data into HuggingFace-
ready dataset directories.

A dataset directory written by this script is consumable directly via:

    from datasets import load_dataset
    ds = load_dataset("json", data_files="aurelia-causal-events/data/phase11-100y/train.jsonl")

The output layout is:

    <dataset-name>/
        README.md                 (HF card, generated from --readme-template)
        data/
            <run_id>/
                train.jsonl       (default) or train.parquet
        configs.json               (optional; lists run_id -> file mapping)

Each invocation exports ONE dataset (one of: causal_events, civilization_metrics,
federation_causal, npc_population) across ONE OR MORE runs. Use --runs with a
comma-separated list of run dirs, or --auto to discover all standard run
directories under /tmp.

By default the writer emits Parquet (smaller, faster to load, recommended for HF).
Use --format jsonl for a human-streamable format. Parquet is written via pyarrow
when available, otherwise falls back to a JSONL file with .parquet extension
(will be corrected at upload time).

Examples:

    PYTHONPATH=. python3 scripts/export_hf_dataset.py \\
        --dataset causal_events \\
        --runs /tmp/aurelia-run-100y,/tmp/aurelia-run-200y \\
        --out /tmp/hf-export/aurelia-causal-events \\
        --run-ids phase11-100y,phase11-200y

    PYTHONPATH=. python3 scripts/export_hf_dataset.py \\
        --dataset civilization_metrics \\
        --auto \\
        --out /tmp/hf-export/aurelia-civilization-metrics

The script is intentionally side-effect-free: it never reads HF_TOKEN and never
contacts the Hub. Uploading is a separate step (see docs/HUGGINGFACE_PUBLISH.md).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Iterable

# Make src_template importable when run as `python3 scripts/export_hf_dataset.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import pyarrow as pa  # type: ignore
    import pyarrow.parquet as pq  # type: ignore

    HAS_PYARROW = True
except Exception:  # pragma: no cover
    pa = None  # type: ignore
    pq = None  # type: ignore
    HAS_PYARROW = False

WORLDS = ["arkos", "mirithane", "solara", "valdris", "verge"]

# Where to auto-discover runs from
AUTO_RUN_PATHS = [
    Path("/tmp/aurelia-bolster-scan"),
    Path("/tmp/aurelia-run-100y"),
    Path("/tmp/aurelia-run-200y"),
    Path("/tmp/aurelia-run-density"),
    Path("/tmp/aurelia-cf-solara-aid"),
]

AUTO_RUN_LABELS = {
    "/tmp/aurelia-bolster-scan": "phase11-bolster-scan-y5",
    "/tmp/aurelia-run-100y": "phase11-100y",
    "/tmp/aurelia-run-200y": "phase11-200y",
    "/tmp/aurelia-run-density": "phase11-density-100y",
    "/tmp/aurelia-cf-solara-aid": "phase11-cf-solara-aid",
}


# ─── Row transforms per dataset ────────────────────────────────────────────────


def _to_jsonable(v: Any) -> Any:
    """Coerce a SQLite cell value to a JSON-safe scalar."""
    if v is None or isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


def export_causal_events(db_paths: list[Path], run_label: str) -> list[dict]:
    """One row per (run, tick, world, event_id). Joins per-world dbs only —
    federation causal events live in federation.db and are surfaced separately
    via export_federation_causal."""
    rows: list[dict] = []
    for db_path in db_paths:
        world_id = db_path.stem
        if world_id not in WORLDS:
            continue
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.execute(
                """
                SELECT event_id, tick_number, world_id, layer, event_type,
                       actor_ids, target_ids, scope, magnitude, valence,
                       confidence, payload, created_at
                FROM causal_events
                ORDER BY tick_number
                """
            )
            for r in cur:
                rows.append(
                    {
                        "run_id": run_label,
                        "event_id": r[0],
                        "tick_number": r[1],
                        "world_id": r[2],
                        "layer": r[3],
                        "event_type": r[4],
                        "actor_ids": json.loads(r[5]) if r[5] else [],
                        "target_ids": json.loads(r[6]) if r[6] else [],
                        "scope": r[7],
                        "magnitude": r[8],
                        "valence": r[9],
                        "confidence": r[10],
                        "payload": json.loads(r[11]) if r[11] else {},
                        "created_at": r[12],
                    }
                )
    return rows


def export_civilization_metrics(db_paths: list[Path], run_label: str) -> list[dict]:
    rows: list[dict] = []
    for db_path in db_paths:
        world_id = db_path.stem
        if world_id not in WORLDS:
            continue
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.execute(
                """
                SELECT world_id, tick_number, education_level, urbanization,
                       youth_bulge, disease_pressure, resource_stock,
                       property_rights, state_capacity_type, repression_type,
                       conflict_type, path_lock_in, payload, created_at
                FROM civilization_metrics
                ORDER BY tick_number
                """
            )
            for r in cur:
                rows.append(
                    {
                        "run_id": run_label,
                        "world_id": r[0],
                        "tick_number": r[1],
                        "education_level": r[2],
                        "urbanization": r[3],
                        "youth_bulge": r[4],
                        "disease_pressure": r[5],
                        "resource_stock": r[6],
                        "property_rights": r[7],
                        "state_capacity_type": r[8],
                        "repression_type": r[9],
                        "conflict_type": r[10],
                        "path_lock_in": r[11],
                        "payload": json.loads(r[12]) if r[12] else {},
                        "created_at": r[13],
                    }
                )
    return rows


def export_federation_causal(db_path: Path, run_label: str) -> dict[str, list[dict]]:
    """Returns two lists: events (causal_events where layer='federation') and
    edges (causal_edges where both endpoints are federation events in this run).
    """
    events: list[dict] = []
    edges: list[dict] = []
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.execute(
            """
            SELECT event_id, tick_number, world_id, layer, event_type,
                   actor_ids, target_ids, scope, magnitude, valence,
                   confidence, payload, created_at
            FROM causal_events
            WHERE layer = 'federation'
            ORDER BY tick_number
            """
        )
        event_ids: set[str] = set()
        for r in cur:
            events.append(
                {
                    "run_id": run_label,
                    "event_id": r[0],
                    "tick_number": r[1],
                    "world_id": r[2],
                    "layer": r[3],
                    "event_type": r[4],
                    "actor_ids": json.loads(r[5]) if r[5] else [],
                    "target_ids": json.loads(r[6]) if r[6] else [],
                    "scope": r[7],
                    "magnitude": r[8],
                    "valence": r[9],
                    "confidence": r[10],
                    "payload": json.loads(r[11]) if r[11] else {},
                    "created_at": r[12],
                }
            )
            event_ids.add(r[0])
        cur = conn.execute(
            "SELECT parent_event_id, child_event_id, relation, weight FROM causal_edges"
        )
        for r in cur:
            if r[0] in event_ids and r[1] in event_ids:
                edges.append(
                    {
                        "run_id": run_label,
                        "parent_event_id": r[0],
                        "child_event_id": r[1],
                        "relation": r[2],
                        "weight": r[3],
                    }
                )
    return {"events": events, "edges": edges}


def export_npc_population(db_path: Path, run_label: str) -> list[dict]:
    """One row per (npc, run). Joins `agents` with end-of-run state and counts
    of the npc's own `events` log entries. Heavy selectors (memories, etc.) are
    intentionally not flattened to keep rows small."""
    rows: list[dict] = []
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.execute(
            """
            SELECT a.id, a.name, a.type, a.location_id, a.state,
                   a.properties, a.travel_state, a.created_at, a.updated_at,
                   (SELECT count(*) FROM events e WHERE e.agent_id = a.id) AS event_count
            FROM agents a
            WHERE a.type = 'npc'
            ORDER BY a.id
            """
        )
        for r in cur:
            rows.append(
                {
                    "run_id": run_label,
                    "npc_id": r[0],
                    "name": r[1],
                    "npc_type": r[2],
                    "location_id": r[3],
                    "final_state": r[4],
                    "properties": json.loads(r[5]) if r[5] else {},
                    "travel_state": r[6],
                    "created_at": r[7],
                    "updated_at": r[8],
                    "event_count": r[9],
                }
            )
    return rows


# ─── Writers ─────────────────────────────────────────────────────────────────


def _write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    n = 0
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
            n += 1
    return n


def _write_parquet(path: Path, rows: list[dict]) -> int:
    if not HAS_PYARROW or pa is None or pq is None:
        raise RuntimeError("pyarrow not installed; use --format jsonl")
    # Parquet cannot write an empty struct {} as a field type. Replace empty
    # dicts with a sentinel key so pyarrow infers a valid schema.
    rows = [
        {
            k: ({"_empty": True} if v == {} else v)
            for k, v in r.items()
        }
        for r in rows
    ]
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, str(path))
    return table.num_rows


# ─── Orchestration ────────────────────────────────────────────────────────────


def discover_runs(auto_paths: list[Path]) -> list[tuple[Path, str]]:
    out = []
    for p in auto_paths:
        if p.exists() and (p / "federation.db").exists():
            out.append((p, AUTO_RUN_LABELS.get(str(p), p.name)))
    return out


def write_dataset_rows(
    dataset: str, run_dir: Path, run_label: str, fmt: str, out_root: Path
) -> dict[str, int]:
    counts: dict[str, int] = {}
    if dataset == "causal_events":
        dbs = [run_dir / f"{w}.db" for w in WORLDS]
        rows = export_causal_events(dbs, run_label)
        target = out_root / "data" / run_label
        target.mkdir(parents=True, exist_ok=True)
        fname = "train.jsonl" if fmt == "jsonl" else "train.parquet"
        if fmt == "parquet":
            counts["causal_events"] = _write_parquet(target / fname, rows)
        else:
            counts["causal_events"] = _write_jsonl(target / fname, rows)
    elif dataset == "civilization_metrics":
        dbs = [run_dir / f"{w}.db" for w in WORLDS]
        rows = export_civilization_metrics(dbs, run_label)
        target = out_root / "data" / run_label
        target.mkdir(parents=True, exist_ok=True)
        fname = "train.jsonl" if fmt == "jsonl" else "train.parquet"
        if fmt == "parquet":
            counts["civilization_metrics"] = _write_parquet(target / fname, rows)
        else:
            counts["civilization_metrics"] = _write_jsonl(target / fname, rows)
    elif dataset == "federation_causal":
        db = run_dir / "federation.db"
        if not db.exists():
            return counts
        out = export_federation_causal(db, run_label)
        target = out_root / "data" / run_label
        target.mkdir(parents=True, exist_ok=True)
        for kind, rows in out.items():
            fname = f"{kind}.jsonl" if fmt == "jsonl" else f"{kind}.parquet"
            if fmt == "parquet":
                counts[kind] = _write_parquet(target / fname, rows)
            else:
                counts[kind] = _write_jsonl(target / fname, rows)
    elif dataset == "npc_population":
        # one file per world
        for world in WORLDS:
            db = run_dir / f"{world}.db"
            if not db.exists():
                continue
            rows = export_npc_population(db, run_label)
            target = out_root / "data" / run_label / world
            target.mkdir(parents=True, exist_ok=True)
            fname = "train.jsonl" if fmt == "jsonl" else "train.parquet"
            if fmt == "parquet":
                counts[f"npcs_{world}"] = _write_parquet(target / fname, rows)
            else:
                counts[f"npcs_{world}"] = _write_jsonl(target / fname, rows)
    else:
        raise ValueError(f"unknown dataset: {dataset}")
    return counts


def write_manifest(out_root: Path) -> None:
    """Write a `configs.json` summarising the file layout for HF."""
    config_path = out_root / "configs.json"
    manifest: dict[str, Any] = {"data": {}}
    data_dir = out_root / "data"
    if data_dir.exists():
        for run_dir in sorted(data_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            files = sorted(
                str(f.relative_to(out_root)) for f in run_dir.rglob("*") if f.is_file()
            )
            manifest["data"][run_dir.name] = files
    config_path.write_text(json.dumps(manifest, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True, choices=[
        "causal_events", "civilization_metrics", "federation_causal", "npc_population",
    ])
    ap.add_argument(
        "--runs",
        help="comma-separated list of run directories (e.g. /tmp/aurelia-run-100y,/tmp/aurelia-run-200y)",
    )
    ap.add_argument("--auto", action="store_true", help="discover all standard run dirs under /tmp")
    ap.add_argument(
        "--run-ids",
        help="comma-separated run labels (must match --runs order); defaults to basename",
    )
    ap.add_argument("--out", required=True, help="output dataset root directory")
    ap.add_argument("--format", choices=["parquet", "jsonl"], default="parquet")
    ap.add_argument("--manifest", action="store_true", help="write configs.json summary")
    args = ap.parse_args()

    if not args.runs and not args.auto:
        ap.error("provide either --runs or --auto")

    runs: list[tuple[Path, str]] = []
    if args.auto:
        runs.extend(discover_runs(AUTO_RUN_PATHS))
    if args.runs:
        explicit = [Path(p.strip()) for p in args.runs.split(",") if p.strip()]
        if args.run_ids:
            labels = [s.strip() for s in args.run_ids.split(",") if s.strip()]
            if len(labels) != len(explicit):
                ap.error("--runs and --run-ids must have the same length")
            runs.extend(zip(explicit, labels))
        else:
            runs.extend((p, p.name) for p in explicit)

    if not runs:
        print("no runs found", file=sys.stderr)
        return 1

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    grand_total = 0
    started = time.time()
    for run_dir, run_label in runs:
        if not run_dir.exists():
            print(f"[skip] {run_dir} does not exist", file=sys.stderr)
            continue
        counts = write_dataset_rows(args.dataset, run_dir, run_label, args.format, out_root)
        n = sum(counts.values())
        grand_total += n
        breakdown = ", ".join(f"{k}={v}" for k, v in counts.items()) or "(empty)"
        print(f"[ok]   {run_label:40s} {n:>9,} rows   {breakdown}")

    if args.manifest:
        write_manifest(out_root)

    elapsed = time.time() - started
    print(f"\nDone. {grand_total:,} rows in {elapsed:.1f}s -> {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
