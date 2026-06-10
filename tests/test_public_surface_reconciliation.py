"""Tests for the offline public-surface reconciler.

The reconciler compares three public surfaces:

- **Local** run artifacts (SQLite ``*.db`` under a run dir).
- **HF export** (Parquet files under an export root, with ``configs.json``).
- **Cloudflare** (a public JSON dashboard).

It produces a Markdown report identifying what is fully public,
partial (e.g., blocked by the D1 cap), or missing. Tests use fake
dicts to avoid network access; the CLI plumbs through to a real
network call when invoked manually.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_local_run(tmp_path: Path, *, world_pops: dict[str, int] | None = None) -> Path:
    world_pops = world_pops or {
        "solara": 171, "arkos": 58, "mirithane": 63, "valdris": 29, "verge": 49,
    }
    run = tmp_path / "run"
    run.mkdir(parents=True, exist_ok=True)
    for w, pop in world_pops.items():
        db = sqlite3.connect(run / f"{w}.db")
        db.executescript(
            """
            CREATE TABLE agents (id TEXT, type TEXT, state TEXT);
            """
        )
        for i in range(pop):
            db.execute("INSERT INTO agents VALUES (?, ?, ?)", (f"{w}_{i}", "npc", "active"))
        db.commit()
        db.close()
    fed = sqlite3.connect(run / "federation.db")
    fed.executescript(
        """
        CREATE TABLE causal_events (event_id TEXT PRIMARY KEY, tick_number INTEGER);
        """
    )
    for i in range(20):
        fed.execute("INSERT INTO causal_events VALUES (?, ?)", (f"e{i}", i))
    fed.commit()
    fed.close()
    return run


def _make_hf_export(
    tmp_path: Path,
    *,
    include_movements: bool = True,
    include_diffusion: bool = True,
) -> Path:
    base = tmp_path / "export"
    runs = ("phase11-100y", "phase11-density-100y")
    for ds, suffix, n in (
        ("aurelia-causal-events", "causal-events", 100),
        ("aurelia-federation-causal", "federation-causal", 50),
        ("aurelia-civilization-metrics", "civilization-metrics", 25),
        ("aurelia-npc-population", "npc-population", 25),
    ):
        ds_dir = base / ds
        ds_dir.mkdir(parents=True, exist_ok=True)
        configs_data: dict[str, list[str]] = {}
        for run in runs:
            data_dir = ds_dir / "data" / run
            data_dir.mkdir(parents=True, exist_ok=True)
            run_files: list[str] = []
            for w in ("solara", "arkos", "mirithane", "valdris", "verge"):
                world_dir = data_dir / w
                world_dir.mkdir(parents=True, exist_ok=True)
                if ds == "aurelia-federation-causal" and not include_movements and w in ("arkos", "verge"):
                    continue
                if ds == "aurelia-federation-causal" and not include_diffusion and w == "valdris":
                    continue
                (world_dir / "train.parquet").write_bytes(b"PAR1")
                run_files.append(f"data/{run}/{w}/train.parquet")
            configs_data[run] = run_files
        (ds_dir / "configs.json").write_text(json.dumps({"data": configs_data}))
    return base


# ---------------------------------------------------------------------------
# Core helper tests
# ---------------------------------------------------------------------------

def test_load_local_counts_sums_active_npcs_per_world(tmp_path):
    run = _make_local_run(tmp_path, world_pops={"solara": 50, "arkos": 20})
    mod = load_script("reconcile_public_surfaces")
    counts = mod.load_local_counts([run])
    assert counts["worlds"]["solara"] == 50
    assert counts["worlds"]["arkos"] == 20
    assert counts["federation_causal_events"] == 20


def test_load_hf_export_counts_sums_per_run_per_world_files(tmp_path):
    export = _make_hf_export(tmp_path)
    mod = load_script("reconcile_public_surfaces")
    counts = mod.load_hf_export_counts(export)
    # Each dataset has 2 runs * 5 worlds = 10 parquet files.
    for ds in (
        "aurelia-causal-events",
        "aurelia-federation-causal",
        "aurelia-civilization-metrics",
        "aurelia-npc-population",
    ):
        assert ds in counts
        assert counts[ds]["files"] == 10


def test_fetch_cloudflare_counts_handles_403(monkeypatch):
    """If Cloudflare returns 403 (no User-Agent), the reconciler must not crash.

    The reconciler should mark the surface as unreachable and continue.
    """
    import urllib.error

    mod = load_script("reconcile_public_surfaces")

    def _fake_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(
            "https://example/", 403, "Forbidden", {}, None
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    counts = mod.fetch_cloudflare_counts(
        "https://example/dashboard", user_agent="Aurelia-Reconciler/1.0"
    )
    assert counts.get("reachable") is False
    assert counts.get("status") == 403


def test_fetch_cloudflare_counts_parses_dashboard_json(monkeypatch):
    mod = load_script("reconcile_public_surfaces")

    class _FakeResponse:
        def __init__(self, payload):
            self._payload = payload.encode()

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeResponse(json.dumps({"runs": [{"id": "r1"}], "ok": True})),
    )
    counts = mod.fetch_cloudflare_counts(
        "https://example/dashboard", user_agent="Aurelia-Reconciler/1.0"
    )
    assert counts.get("reachable") is True
    assert counts.get("ok") is True
    assert counts.get("run_count") == 1


def test_compare_counts_marks_d1_cap_as_partial_not_failure():
    mod = load_script("reconcile_public_surfaces")
    local = {"worlds": {"solara": 100}, "federation_causal_events": 200}
    hf = {"aurelia-npc-population": {"files": 5, "rows_per_file": 20}}
    cf = {"reachable": True, "run_count": 1, "federation_causal_events": 50}
    result = mod.compare_counts(local, hf, cf)
    # The hf counts are 100 NPCs total (5*20), local is 100. → match.
    # cf federation_causal_events is 50, local is 200. → partial ingestion.
    statuses = [r["status"] for r in result["comparisons"]]
    assert "partial" in statuses
    assert "ok" in statuses
    assert "missing" in statuses


def test_render_markdown_contains_required_sections():
    mod = load_script("reconcile_public_surfaces")
    result = {
        "generated_at": "2026-06-10T00:00:00Z",
        "local": {"worlds": {"solara": 100}},
        "hf_export": {"aurelia-npc-population": {"files": 5, "rows_per_file": 20}},
        "cloudflare": {"reachable": True, "run_count": 1},
        "comparisons": [
            {"name": "npc count", "status": "ok", "local": 100, "hf": 100, "cf": "n/a"},
            {"name": "fed events", "status": "partial", "local": 200, "hf": "n/a", "cf": 50, "note": "D1 cap"},
        ],
        "d1_cap_note": "D1 cap caused partial ingestion",
        "recommendations": ["Upgrade D1 plan", "Re-export HF datasets"],
    }
    md = mod.render_markdown(result)
    for section in ("# Public Surface Reconciliation", "## Local artifacts", "## HF exports",
                     "## Cloudflare public dashboard", "## Count mismatches",
                     "## Known D1 cap limitation", "## Recommended remediation"):
        assert section in md
