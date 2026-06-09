import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import federation_orchestrator


def _counts(summary):
    return {
        w: (d["population"], d["deceased"], d["factions"])
        for w, d in sorted(summary["worlds"].items())
    }


def test_barrier_runner_produces_causal_smoke(tmp_path):
    out = tmp_path / "run"
    summary = federation_orchestrator.run_causal_simulation(
        output_dir=out,
        worlds=["solara", "valdris", "arkos"],
        years=4,
        npc_count=300,
        ticks_per_year=6,
        seed=42,
        max_interactions=250,
        birth_scale=20.0,
        death_scale=8.0,
    )
    assert summary["ticks"] == 24
    assert summary["effects_scheduled"] > 0
    assert summary["effects_imported"] > 0
    assert summary["yearly_reports"]
    assert any(r["births"] + r["deaths"] > 0 for r in summary["yearly_reports"])
    assert any(sum(d.values()) > 0 for r in summary["yearly_reports"] for d in [r["factions"]])
    for world_id in ["solara", "valdris", "arkos"]:
        db = sqlite3.connect(out / f"{world_id}.db")
        row = db.execute("SELECT year, month FROM world_time WHERE id=1").fetchone()
        assert row is not None
        assert row[0] == 2029
        assert row[1] == 11
        db.close()
    assert (out / "causal_summary.json").exists()


def test_processing_order_does_not_change_world_counts_for_fixed_seed(tmp_path):
    kwargs = dict(
        years=1,
        npc_count=120,
        ticks_per_year=4,
        seed=99,
        max_interactions=60,
        birth_scale=20.0,
        death_scale=8.0,
    )
    a = federation_orchestrator.run_causal_simulation(
        output_dir=tmp_path / "a",
        worlds=["solara", "valdris", "arkos"],
        **kwargs,
    )
    b = federation_orchestrator.run_causal_simulation(
        output_dir=tmp_path / "b",
        worlds=["arkos", "valdris", "solara"],
        **kwargs,
    )
    assert _counts(a) == _counts(b)
