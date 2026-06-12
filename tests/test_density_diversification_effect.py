"""Regression tests for the density-diversification headline.

The public claim is not just that the knob exists; it must materially
collapse cross-world population variance. These tests keep that claim
anchored to executable migration behavior rather than report prose.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def _init_world(db_path: Path, world_id: str, pop: int) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE locations (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            created_at REAL
        );
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
    db.execute(
        "INSERT INTO locations VALUES ('town_square', 'Town Square', 'test fixture', ?)",
        (now,),
    )
    for i in range(pop):
        db.execute(
            "INSERT INTO agents VALUES (?, ?, 'npc', 'town_square', 'active', ?, ?, ?)",
            (f"{world_id}-npc-{i}", f"{world_id}-{i}", "{}", now, now),
        )
    db.commit()
    return db


def _world_counts(conns: dict[str, sqlite3.Connection]) -> dict[str, int]:
    return {
        world: int(db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0])
        for world, db in conns.items()
    }


def test_density_balancer_reduces_population_cv_by_at_least_90_percent_across_seeded_cases(tmp_path):
    from src_template import density_diversification_effect, phase10_dynamics

    seeded_cases = {
        2001: {"solara": 210, "arkos": 170, "mirithane": 70, "valdris": 35, "verge": 15},
        2002: {"solara": 12, "arkos": 45, "mirithane": 80, "valdris": 160, "verge": 203},
        2003: {"solara": 35, "arkos": 210, "mirithane": 20, "valdris": 185, "verge": 50},
    }

    reductions: list[float] = []
    for seed, populations in seeded_cases.items():
        case_dir = tmp_path / f"seed-{seed}"
        conns = {
            world: _init_world(case_dir / f"{world}.db", world, pop)
            for world, pop in populations.items()
        }
        fed = sqlite3.connect(case_dir / "federation.db")
        fed.row_factory = sqlite3.Row
        before = _world_counts(conns)

        for tick in range(1, 80):
            phase10_dynamics.process_migration_carriers(
                fed,
                conns,
                tick_number=tick,
                max_per_pair=10,
                density_diversification=1.0,
            )

        after = _world_counts(conns)
        reduction = density_diversification_effect.cv_reduction(before.values(), after.values())
        reductions.append(reduction)
        assert reduction >= 0.90, f"seed {seed} only reduced CV by {reduction:.1%}: {before} -> {after}"

    assert min(reductions) >= 0.90
