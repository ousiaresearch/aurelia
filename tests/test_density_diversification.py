"""Test for the density_diversification knob on the federation orchestrator.

These tests are pure orchestration: no real run, just enough state to
exercise the migration balancing logic.
"""
import sqlite3
from pathlib import Path

import pytest


def _init_world(db_path: Path, world_id: str, pop: int) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.executescript(
        """
        CREATE TABLE agents (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            location_id TEXT,
            state TEXT,
            properties TEXT,
            created_at REAL,
            updated_at REAL
        );
        """
    )
    now = 0.0
    for i in range(pop):
        db.execute(
            "INSERT INTO agents VALUES (?, ?, 'npc', 'town_square', 'active', ?, ?, ?)",
            (f"{world_id}-npc-{i}", f"{world_id}-{i}", "{}", now, now),
        )
    db.commit(); db.close()


def test_balance_migration_pair_picks_over_to_under(tmp_path):
    from src_template import phase10_dynamics
    conns = {}
    pops = {"solara": 200, "valdris": 180, "mirithane": 60, "arkos": 50, "verge": 10}
    for w, p in pops.items():
        _init_world(tmp_path / f"{w}.db", w, p)
        conns[w] = sqlite3.connect(tmp_path / f"{w}.db")
    pair = phase10_dynamics._balance_migration_pair(conns)
    assert pair is not None
    src, tgt = pair
    assert pops[src] == 200
    assert pops[tgt] == 10


def test_balance_migration_pair_returns_none_when_balanced(tmp_path):
    from src_template import phase10_dynamics
    conns = {}
    for w, p in {"solara": 100, "valdris": 100, "mirithane": 100}.items():
        _init_world(tmp_path / f"{w}.db", w, p)
        conns[w] = sqlite3.connect(tmp_path / f"{w}.db")
    assert phase10_dynamics._balance_migration_pair(conns) is None


def test_density_diversification_param_is_accepted(tmp_path):
    """Orchestrator API must accept and validate the new parameter."""
    from src_template import federation_orchestrator
    import inspect
    sig = inspect.signature(federation_orchestrator.run_causal_simulation)
    assert "density_diversification" in sig.parameters
    assert sig.parameters["density_diversification"].default == 0.0

    with pytest.raises(ValueError):
        federation_orchestrator.run_causal_simulation(
            output_dir=tmp_path, years=1, npc_count=5, ticks_per_year=1,
            density_diversification=1.5,
        )
    with pytest.raises(ValueError):
        federation_orchestrator.run_causal_simulation(
            output_dir=tmp_path, years=1, npc_count=5, ticks_per_year=1,
            density_diversification=-0.1,
        )
