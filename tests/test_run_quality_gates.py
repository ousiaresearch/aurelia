"""Quality gate tests for scripts/evaluate_run_quality.py.

These tests build small fake run directories and assert that the
evaluator surfaces real warnings and applies real score caps for
pathological run shapes — not just a perfect 1.0.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_world_db(path: Path, *, events: int = 0, factions: int = 0) -> None:
    """Create a per-world DB with a controllable event count and faction count."""
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE causal_events (
            event_id TEXT PRIMARY KEY,
            tick_number INTEGER, world_id TEXT, layer TEXT,
            event_type TEXT, actor_ids TEXT, target_ids TEXT,
            scope TEXT, magnitude REAL, valence REAL, confidence REAL,
            payload TEXT, created_at REAL
        );
        CREATE TABLE causal_edges (
            parent_event_id TEXT, child_event_id TEXT, relation TEXT, weight REAL
        );
        CREATE TABLE civilization_metrics (
            world_id TEXT, tick_number INTEGER,
            education_level REAL, urbanization REAL, youth_bulge REAL,
            disease_pressure REAL, resource_stock REAL, property_rights REAL,
            state_capacity_type TEXT, repression_type TEXT, conflict_type TEXT,
            path_lock_in REAL, payload TEXT, created_at REAL
        );
        CREATE TABLE discoveries (discovery_id TEXT, world_id TEXT, tick_number INTEGER);
        CREATE TABLE great_persons (npc_id TEXT, world_id TEXT, tick_number INTEGER);
        CREATE TABLE factions (faction_id TEXT, world_id TEXT, status TEXT);
        """
    )
    for i in range(events):
        db.execute(
            "INSERT INTO causal_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"e{i}", i, "solara", "micro", "work_success", "[]", "[]", "local", 0.5, 0.1, 1.0, "{}", 0.0),
        )
    for j in range(factions):
        db.execute(
            "INSERT INTO factions VALUES (?,?,?)",
            (f"f{j}", "solara", "active"),
        )
    db.commit()
    db.close()


def _make_summary(
    run_dir: Path,
    *,
    years: int,
    worlds: dict[str, dict],
    seed: int = 4242,
    ticks_per_year: int = 12,
) -> None:
    payload = {
        "years": years,
        "ticks": years * ticks_per_year,
        "seed": seed,
        "ticks_per_year": ticks_per_year,
        "worlds": worlds,
        "yearly_reports": [
            {"world_id": w, "year": y, "population": d.get("population", 0)}
            for w, d in worlds.items() for y in range(1, years + 1)
        ],
    }
    (run_dir / "causal_summary.json").write_text(json.dumps(payload))


def _make_federation(run_dir: Path) -> None:
    db = sqlite3.connect(run_dir / "federation.db")
    db.executescript(
        """
        CREATE TABLE causal_events (
            event_id TEXT PRIMARY KEY,
            tick_number INTEGER, world_id TEXT, layer TEXT,
            event_type TEXT, actor_ids TEXT, target_ids TEXT,
            scope TEXT, magnitude REAL, valence REAL, confidence REAL,
            payload TEXT, created_at REAL
        );
        CREATE TABLE causal_edges (parent_event_id TEXT, child_event_id TEXT, relation TEXT, weight REAL);
        CREATE TABLE cross_world_movements (npc_id TEXT, source_world TEXT, target_world TEXT, movement_type TEXT, tick_number INTEGER, created_at REAL);
        CREATE TABLE diffusion_events (event_id TEXT, tick_number INTEGER, source_world TEXT, target_world TEXT, trait TEXT, adoption_strength REAL, resisted INTEGER, created_at REAL);
        CREATE TABLE diplomatic_relations (relation_id TEXT, world_a TEXT, world_b TEXT, relation_type TEXT, strength REAL, established_tick INTEGER, dissolved_tick INTEGER, payload TEXT, created_at REAL);
        """
    )
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Pathological fixtures
# ---------------------------------------------------------------------------

def _build_factionless_run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    for w in ("solara", "arkos", "mirithane", "valdris", "verge"):
        _make_world_db(run / f"{w}.db", events=20, factions=0)
    _make_federation(run)
    _make_summary(
        run,
        years=20,
        worlds={
            w: {"population": 50, "deceased": 0, "factions": 0}
            for w in ("solara", "arkos", "mirithane", "valdris", "verge")
        },
    )
    return run


def _build_population_collapse_run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    for w in ("solara", "arkos", "mirithane", "valdris", "verge"):
        _make_world_db(run / f"{w}.db", events=200, factions=2)
    _make_federation(run)
    # valdris collapses to 1 NPC; one other world is fine.
    _make_summary(
        run,
        years=80,
        worlds={
            "solara": {"population": 80, "deceased": 5, "factions": 2},
            "arkos": {"population": 70, "deceased": 4, "factions": 2},
            "mirithane": {"population": 60, "deceased": 3, "factions": 2},
            "valdris": {"population": 1, "deceased": 50, "factions": 1},
            "verge": {"population": 55, "deceased": 2, "factions": 2},
        },
    )
    return run


def _build_metadata_missing_run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    for w in ("solara", "arkos", "mirithane", "valdris", "verge"):
        _make_world_db(run / f"{w}.db", events=10, factions=1)
    _make_federation(run)
    # No seed, no ticks_per_year, no causal_summary.json → all metadata missing.
    return run


def _build_pathological_but_event_heavy_run(tmp_path: Path) -> Path:
    """High event counts but pathological population/faction signals.

    Should not score 1.0.
    """
    run = tmp_path / "run"
    run.mkdir()
    for w in ("solara", "arkos", "mirithane", "valdris", "verge"):
        _make_world_db(run / f"{w}.db", events=2000, factions=0)
    _make_federation(run)
    _make_summary(
        run,
        years=100,
        worlds={
            "solara": {"population": 200, "deceased": 50, "factions": 0},
            "arkos": {"population": 30, "deceased": 80, "factions": 0},
            "mirithane": {"population": 25, "deceased": 90, "factions": 0},
            "valdris": {"population": 1, "deceased": 100, "factions": 0},
            "verge": {"population": 22, "deceased": 75, "factions": 0},
        },
    )
    return run


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_quality_warns_when_factions_never_form(tmp_path):
    run = _build_factionless_run(tmp_path)
    mod = load_script("evaluate_run_quality")
    result = mod.evaluate_run(run)
    warnings = " ".join(result.get("warnings", [])).lower()
    assert "faction" in warnings and ("absent" in warnings or "sparse" in warnings or "zero" in warnings)
    # Counts should expose worlds_with_factions=0
    counts = result.get("counts", {})
    assert counts.get("worlds_with_factions", 1) == 0
    # Hard cap applied
    assert result["overall_score"] <= 0.85


def test_quality_warns_on_population_collapse(tmp_path):
    run = _build_population_collapse_run(tmp_path)
    mod = load_script("evaluate_run_quality")
    result = mod.evaluate_run(run)
    warnings = " ".join(result.get("warnings", [])).lower()
    assert "population" in warnings and ("collapse" in warnings or "valdris" in warnings or "min" in warnings)
    # Counts should expose the min and CV
    counts = result.get("counts", {})
    assert counts.get("min_world_population", 999) <= 1
    # Hard cap applied
    assert result["overall_score"] <= 0.80


def test_quality_warns_on_missing_run_metadata(tmp_path):
    run = _build_metadata_missing_run(tmp_path)
    mod = load_script("evaluate_run_quality")
    result = mod.evaluate_run(run)
    warnings = " ".join(result.get("warnings", [])).lower()
    assert "metadata" in warnings or "seed" in warnings or "ticks_per_year" in warnings
    # Missing metadata should not be a hard cap by itself (other gates apply separately)


def test_quality_does_not_saturate_to_one_for_pathological_run(tmp_path):
    run = _build_pathological_but_event_heavy_run(tmp_path)
    mod = load_script("evaluate_run_quality")
    result = mod.evaluate_run(run)
    # High event volume must not mask the pathology.
    assert result["overall_score"] < 1.0
    # Should warn about at least one of: missing factions, depopulation, high CV.
    warnings = " ".join(result.get("warnings", [])).lower()
    assert any(needle in warnings for needle in ("faction", "population", "cv"))


def test_quality_counts_exposed_for_auditors(tmp_path):
    run = _build_population_collapse_run(tmp_path)
    mod = load_script("evaluate_run_quality")
    result = mod.evaluate_run(run)
    counts = result["counts"]
    for key in (
        "min_world_population",
        "max_world_population",
        "population_cv",
        "worlds_with_factions",
        "total_factions",
    ):
        assert key in counts, f"missing counts key: {key}"


def test_quality_thresholds_are_configurable_at_module_top():
    mod = load_script("evaluate_run_quality")
    # The module should expose the gate constants so an operator can tune them.
    expected = {
        "FRACTION_CRITICAL",
        "FRACTION_CRITICAL_CAP",
        "POP_COLLAPSE_CAP",
        "POP_CV_HIGH",
        "POP_CV_HIGH_CAP",
    }
    found = {name for name in expected if hasattr(mod, name)}
    assert found == expected, f"missing module-level threshold constants: {expected - found}"
