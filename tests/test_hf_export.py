"""Tests for the HuggingFace dataset exporter and README renderer.

These tests are RED-GREEN: they run against the live local data in /tmp (if
present) and fall back to synthesizing a small SQLite fixture when it isn't.
CI always uses the fixture path (no external state dependency); manual
verification against the real exports happens in `make test-hf-local` (not yet
in the Makefile — see README).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

# Make scripts importable when run as `python3 tests/test_hf_export.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# Skip pyarrow import errors here; tests do not require pyarrow
try:
    import pyarrow.parquet as pq  # noqa: F401
    HAS_PYARROW = True
except Exception:
    HAS_PYARROW = False

import export_hf_dataset as exporter  # noqa: E402
import render_hf_readme as renderer  # noqa: E402


WORLDS = exporter.WORLDS


def _build_fixture(tmp: Path) -> Path:
    """Build a tiny Aurelia-like SQLite fixture in tmp/fixture/{world}.db and
    tmp/fixture/federation.db. Returns the fixture root dir."""
    root = tmp / "fixture"
    root.mkdir(parents=True, exist_ok=True)

    # One minimal causal_events row per world
    for world in WORLDS:
        db = root / f"{world}.db"
        with sqlite3.connect(str(db)) as conn:
            conn.executescript(
                """
                CREATE TABLE causal_events (
                    event_id TEXT PRIMARY KEY,
                    tick_number INTEGER NOT NULL,
                    world_id TEXT NOT NULL,
                    layer TEXT NOT NULL CHECK(layer IN ('micro','meso','macro','federation')),
                    event_type TEXT NOT NULL,
                    actor_ids TEXT NOT NULL DEFAULT '[]',
                    target_ids TEXT NOT NULL DEFAULT '[]',
                    scope TEXT NOT NULL,
                    magnitude REAL NOT NULL DEFAULT 0.0,
                    valence REAL NOT NULL DEFAULT 0.0,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    payload TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL
                );
                CREATE TABLE civilization_metrics (
                    world_id TEXT NOT NULL,
                    tick_number INTEGER NOT NULL,
                    education_level REAL NOT NULL,
                    urbanization REAL NOT NULL,
                    youth_bulge REAL NOT NULL,
                    disease_pressure REAL NOT NULL,
                    resource_stock REAL NOT NULL,
                    property_rights REAL NOT NULL,
                    state_capacity_type TEXT NOT NULL,
                    repression_type TEXT NOT NULL,
                    conflict_type TEXT NOT NULL,
                    path_lock_in REAL NOT NULL,
                    payload TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    PRIMARY KEY(world_id, tick_number)
                );
                CREATE TABLE agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'npc',
                    location_id TEXT,
                    state TEXT DEFAULT 'active',
                    properties TEXT DEFAULT '{}',
                    travel_state TEXT DEFAULT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    agent_id TEXT DEFAULT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    location_id TEXT DEFAULT NULL,
                    properties TEXT DEFAULT '{}'
                );
                """
            )
            conn.execute(
                """
                INSERT INTO causal_events VALUES (
                    'evt:test:1:wage_dispute:abc', 1, ?, 'micro', 'wage_dispute',
                    '[\"x:npc:1\"]', '[]', 'npc', 0.1, -0.2, 1.0, '{}', 1.0
                )
                """,
                (world,),
            )
            conn.execute(
                """
                INSERT INTO civilization_metrics VALUES (
                    ?, 1, 0.5, 0.4, 0.7, 0.3, 0.6, 0.5,
                    'bureaucratic', 'legal', 'latent', 0.0, '{}', 1.0
                )
                """,
                (world,),
            )
            conn.execute(
                """
                INSERT INTO agents VALUES (
                    ?, 'NPC', 'npc', 'town', 'active', '{}', NULL, 1.0, 1.0
                )
                """,
                (f"{world}:npc:0001",),
            )
            conn.execute(
                "INSERT INTO events(timestamp, agent_id, event_type) VALUES (1.0, ?, 'work_success')",
                (f"{world}:npc:0001",),
            )

    # Federation db
    fed = root / "federation.db"
    with sqlite3.connect(str(fed)) as conn:
        conn.executescript(
            """
            CREATE TABLE causal_events (
                event_id TEXT PRIMARY KEY,
                tick_number INTEGER NOT NULL,
                world_id TEXT NOT NULL,
                layer TEXT NOT NULL CHECK(layer IN ('micro','meso','macro','federation')),
                event_type TEXT NOT NULL,
                actor_ids TEXT NOT NULL DEFAULT '[]',
                target_ids TEXT NOT NULL DEFAULT '[]',
                scope TEXT NOT NULL,
                magnitude REAL NOT NULL DEFAULT 0.0,
                valence REAL NOT NULL DEFAULT 0.0,
                confidence REAL NOT NULL DEFAULT 1.0,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL
            );
            CREATE TABLE causal_edges (
                parent_event_id TEXT NOT NULL,
                child_event_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 1.0,
                PRIMARY KEY(parent_event_id, child_event_id)
            );
            """
        )
        conn.execute(
            """
            INSERT INTO causal_events VALUES (
                'evt:federation:1:cross_world_movement:def', 1, 'federation',
                'federation', 'cross_world_movement',
                '[\"arkos\"]', '[\"solara\"]', 'federation', 0.5, 0.0, 1.0,
                '{\"source_world\":\"arkos\",\"target_world\":\"solara\"}', 1.0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO causal_events VALUES (
                'evt:federation:1:cultural_diffusion:ghi', 1, 'federation',
                'federation', 'cultural_diffusion',
                '[\"arkos\"]', '[\"solara\"]', 'federation', 0.3, 0.0, 1.0,
                '{\"source_world\":\"arkos\",\"target_world\":\"solara\"}', 1.0
            )
            """
        )
        conn.execute(
            "INSERT INTO causal_edges VALUES ('evt:federation:1:cross_world_movement:def', 'evt:federation:1:cultural_diffusion:ghi', 'migration_to_cultural_change', 0.5)"
        )
    return root


# ── causal_events ────────────────────────────────────────────────────────────


def test_export_causal_events_row_count(tmp_path: Path):
    fix = _build_fixture(tmp_path)
    rows = exporter.export_causal_events([fix / f"{w}.db" for w in WORLDS], "test_run")
    assert len(rows) == len(WORLDS), f"expected {len(WORLDS)} events, got {len(rows)}"
    r = rows[0]
    assert r["run_id"] == "test_run"
    assert r["event_id"] == "evt:test:1:wage_dispute:abc"
    assert r["layer"] == "micro"
    assert r["actor_ids"] == ["x:npc:1"]
    assert isinstance(r["payload"], dict)


def test_export_causal_events_jsonl_round_trip(tmp_path: Path):
    fix = _build_fixture(tmp_path)
    out = tmp_path / "out"
    counts = exporter.write_dataset_rows(
        "causal_events", fix, "test_run", "jsonl", out
    )
    assert counts["causal_events"] == len(WORLDS)
    f = out / "data" / "test_run" / "train.jsonl"
    assert f.exists()
    lines = f.read_text().strip().split("\n")
    assert len(lines) == len(WORLDS)
    for line in lines:
        obj = json.loads(line)
        assert "event_id" in obj
        assert "layer" in obj


# ── civilization_metrics ─────────────────────────────────────────────────────


def test_export_civilization_metrics(tmp_path: Path):
    fix = _build_fixture(tmp_path)
    rows = exporter.export_civilization_metrics(
        [fix / f"{w}.db" for w in WORLDS], "test_run"
    )
    assert len(rows) == len(WORLDS)
    r = rows[0]
    assert r["state_capacity_type"] == "bureaucratic"
    assert r["world_id"] in WORLDS


# ── federation_causal ───────────────────────────────────────────────────────


def test_export_federation_causal(tmp_path: Path):
    fix = _build_fixture(tmp_path)
    out = exporter.export_federation_causal(fix / "federation.db", "test_run")
    assert len(out["events"]) == 2
    assert len(out["edges"]) == 1
    e = out["events"][0]
    assert e["layer"] == "federation"
    assert e["world_id"] == "federation"
    edge = out["edges"][0]
    assert edge["relation"] == "migration_to_cultural_change"
    assert edge["weight"] == 0.5


# ── npc_population ───────────────────────────────────────────────────────────


def test_export_npc_population(tmp_path: Path):
    fix = _build_fixture(tmp_path)
    rows = exporter.export_npc_population(fix / "solara.db", "test_run")
    assert len(rows) == 1
    assert rows[0]["npc_id"] == "solara:npc:0001"
    assert rows[0]["event_count"] == 1
    assert rows[0]["final_state"] == "active"


# ── discover_runs ────────────────────────────────────────────────────────────


def test_discover_runs_filters_missing(tmp_path: Path):
    # Build a real-looking fixture
    fix = _build_fixture(tmp_path)
    # discover_runs uses hardcoded AUTO_RUN_PATHS — we test with a manually
    # constructed list instead.
    runs = exporter.discover_runs([fix, tmp_path / "nonexistent"])
    assert len(runs) == 1
    assert runs[0][0] == fix


# ── README renderer ──────────────────────────────────────────────────────────


def test_render_hf_readme_contains_frontmatter_and_schema(tmp_path: Path):
    fix = _build_fixture(tmp_path)
    export_root = tmp_path / "export"
    # Exporter writes to <export_root>/<dataset_slug>/data/<run_id>; renderer
    # expects the same layout, so build the dataset subdir explicitly.
    ds_root = export_root / "aurelia-causal-events"
    exporter.write_dataset_rows("causal_events", fix, "test_run", "jsonl", ds_root)

    text = renderer.render("causal_events", export_root)
    assert text.startswith("---"), "must begin with YAML frontmatter"
    assert "license: cc-by-4.0" in text
    assert "task_categories:" in text
    assert "size_categories:" in text
    assert "Schema" in text
    assert "Loading" in text
    assert "test_run" in text
    # The renderer's per-run row table emits the run id; confirm it picked
    # up test_run and didn't fall back to the real run ids.
    assert "| `test_run` |" in text


def test_size_category_bucket():
    assert renderer.size_category(100) == "n<1K"
    assert renderer.size_category(2_000) == "1K<n<5K"
    assert renderer.size_category(50_000) == "10K<n<100K"
    assert renderer.size_category(500_000) == "100K<n<1M"


# ── schema completeness ──────────────────────────────────────────────────────


def test_all_four_datasets_have_schema():
    for ds in ("causal_events", "civilization_metrics", "federation_causal", "npc_population"):
        assert ds in renderer.SCHEMAS
        info = renderer.SCHEMAS[ds]
        assert "primary_file" in info
        assert "schema" in info
        assert len(info["schema"]) >= 5
        for col, typ, desc in info["schema"]:
            assert col
            assert typ
            assert desc


# ── F1 — README links to research guide and examples ──────────────────────


def test_render_hf_readme_links_to_research_start_here(tmp_path):
    fix = _build_fixture(tmp_path)
    export_root = tmp_path / "export"
    ds_root = export_root / "aurelia-causal-events"
    exporter.write_dataset_rows("causal_events", fix, "test_run", "jsonl", ds_root)
    text = renderer.render("causal_events", export_root)
    assert "AURELIA_RESEARCH_START_HERE" in text
    assert "github.com/ousiaresearch/aurelia" in text


def test_render_hf_readme_links_to_density_example_for_npc_population(tmp_path):
    fix = _build_fixture(tmp_path)
    export_root = tmp_path / "export"
    ds_root = export_root / "aurelia-npc-population"
    exporter.write_dataset_rows("npc_population", fix, "test_run", "jsonl", ds_root)
    text = renderer.render("npc_population", export_root)
    assert "02_reproduce_density_diversification" in text


def test_render_hf_readme_links_to_density_example_for_civilization_metrics(tmp_path):
    fix = _build_fixture(tmp_path)
    export_root = tmp_path / "export"
    ds_root = export_root / "aurelia-civilization-metrics"
    exporter.write_dataset_rows("civilization_metrics", fix, "test_run", "jsonl", ds_root)
    text = renderer.render("civilization_metrics", export_root)
    assert "02_reproduce_density_diversification" in text


def test_render_hf_readme_links_to_canon_guide(tmp_path):
    fix = _build_fixture(tmp_path)
    export_root = tmp_path / "export"
    ds_root = export_root / "aurelia-federation-causal"
    exporter.write_dataset_rows("federation_causal", fix, "test_run", "jsonl", ds_root)
    text = renderer.render("federation_causal", export_root)
    assert "AURELIA_CANON_AND_DATA_GUIDE" in text


def test_render_hf_readme_links_to_causal_chain_example_for_federation(tmp_path):
    fix = _build_fixture(tmp_path)
    export_root = tmp_path / "export"
    ds_root = export_root / "aurelia-federation-causal"
    exporter.write_dataset_rows("federation_causal", fix, "test_run", "jsonl", ds_root)
    text = renderer.render("federation_causal", export_root)
    assert "03_trace_causal_chain" in text


def test_parquet_round_trip_when_pyarrow_available(tmp_path: Path):
    if not HAS_PYARROW:
        pytest.skip("pyarrow not installed in this env")
    fix = _build_fixture(tmp_path)
    out = tmp_path / "out"
    exporter.write_dataset_rows("causal_events", fix, "test_run", "parquet", out)
    f = out / "data" / "test_run" / "train.parquet"
    assert f.exists()
    import pyarrow.parquet as pq
    t = pq.read_table(str(f))
    assert t.num_rows == len(WORLDS)
    assert "event_id" in t.column_names
    assert "layer" in t.column_names
