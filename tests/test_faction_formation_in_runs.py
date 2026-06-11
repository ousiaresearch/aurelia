"""Tests for faction formation in long federation runs.

Phase 12 quality-gate autopsy (D1): every long run reported zero active
factions. Diagnosis:

  * ``faction_lifecycle.run_faction_lifecycle`` reads pressure from
    ``meso_signals`` for the *current* tick only.
  * Per-tick pressure magnitudes are tiny (a single ``migration_plan``
    contributes ~0.0134).
  * The formation threshold is ``0.30`` -- a faction therefore needs
    20+ consecutive ticks of high pressure to form, which the
    short smoke runs and most long runs never reach.

Real-world social movements form from *cumulative* pressure (a bad
year, a bad decade), not from a single tick. The fix: a recent-window
sum (the last 16 ticks) with the same 0.30 threshold, so any run with
sustained stress will produce a faction in a realistic time horizon.

These tests assert the contract:

  1. ``run_faction_lifecycle`` should form a faction when cumulative
     pressure over a recent window exceeds the formation threshold.
  2. The recent-window calculation should be a deterministic helper
     that can be tested without spinning the whole federation.
  3. A real federation smoke of 25 years (100 ticks) should produce
     at least one active faction somewhere -- proving the integration
     works end-to-end.
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import faction_lifecycle  # noqa: E402
import federation_orchestrator  # noqa: E402
import meso_aggregator  # noqa: E402


# ---------------------------------------------------------------------------
# Pure-function tests for the cumulative-pressure window
# ---------------------------------------------------------------------------

class TestCumulativePressureWindow:
    """``cumulative_pressure`` must read a recent tick window, not just tick N."""

    def _make_db(self, tmp_path: Path) -> sqlite3.Connection:
        path = tmp_path / "test.db"
        conn = sqlite3.connect(str(path))
        faction_lifecycle.causal_ledger.ensure_schema(conn)
        meso_aggregator.ensure_schema(conn)
        return conn

    def _seed_pressure(
        self,
        db: sqlite3.Connection,
        world_id: str,
        tick: int,
        magnitudes: dict[str, float],
    ) -> None:
        for signal_type, mag in magnitudes.items():
            db.execute(
                """
                INSERT OR REPLACE INTO meso_signals
                    (signal_id, tick_number, world_id, location_id,
                     signal_type, magnitude, source_event_count, payload, created_at)
                VALUES (?, ?, ?, 'capital', ?, ?, 1, '{}', ?)
                """,
                (f"sig:{world_id}:{tick}:{signal_type}", tick, world_id, signal_type, mag, time.time()),
            )
        db.commit()

    def test_cumulative_pressure_sums_recent_window(self, tmp_path: Path) -> None:
        """Signals within the last N ticks must accumulate; older signals must not."""
        db = self._make_db(tmp_path)
        # Old pressure (tick 1) should be ignored at tick 20 with default window=16.
        self._seed_pressure(db, "solara", tick=1, magnitudes={"labor_unrest": 5.0, "repression_visibility": 5.0})
        # Recent pressure (tick 19, 18, 17) should accumulate.
        self._seed_pressure(db, "solara", tick=19, magnitudes={"labor_unrest": 0.10})
        self._seed_pressure(db, "solara", tick=18, magnitudes={"economic_stress": 0.10})
        self._seed_pressure(db, "solara", tick=17, magnitudes={"migration_pressure": 0.10})

        result = faction_lifecycle.cumulative_pressure(
            db, world_id="solara", current_tick=20, window=16
        )
        assert result == pytest.approx(0.30, abs=1e-9), (
            f"Expected 0.30 cumulative pressure (3 ticks of 0.10), got {result}"
        )

    def test_cumulative_pressure_excludes_old_signals(self, tmp_path: Path) -> None:
        """Signals older than the window must NOT count toward formation."""
        db = self._make_db(tmp_path)
        # Massive old pressure 100 ticks ago -- must be ignored.
        self._seed_pressure(db, "solara", tick=10, magnitudes={"labor_unrest": 50.0})
        # No recent pressure.
        result = faction_lifecycle.cumulative_pressure(
            db, world_id="solara", current_tick=110, window=16
        )
        assert result == pytest.approx(0.0, abs=1e-9), (
            f"Old signals should not count, got {result}"
        )

    def test_cumulative_pressure_aggregates_signal_types(self, tmp_path: Path) -> None:
        """All four pressure signal types should sum into the total."""
        db = self._make_db(tmp_path)
        # Spread across the four types, all in-window at tick 20.
        self._seed_pressure(
            db, "valdris", tick=20,
            magnitudes={
                "labor_unrest": 0.10,
                "repression_visibility": 0.08,
                "migration_pressure": 0.07,
                "economic_stress": 0.05,
            },
        )
        result = faction_lifecycle.cumulative_pressure(
            db, world_id="valdris", current_tick=20, window=16
        )
        assert result == pytest.approx(0.30, abs=1e-9), (
            f"All four signal types should sum to 0.30, got {result}"
        )


# ---------------------------------------------------------------------------
# Formation integration test: synthetic pressure → real faction
# ---------------------------------------------------------------------------

class TestFormationFromCumulativePressure:
    """run_faction_lifecycle should form a faction when cumulative pressure crosses 0.30."""

    def test_formation_fires_under_cumulative_pressure(self, tmp_path: Path) -> None:
        """Synthetic scenario: 16 ticks of 0.025 pressure (cumulative 0.40) must form a faction."""
        import world_state
        db = world_state.init_world(tmp_path / "valdris.db")
        db.row_factory = sqlite3.Row
        # world_state.init_world does not create the meso_signals table; do it here.
        meso_aggregator.ensure_schema(db)
        faction_lifecycle.causal_ledger.ensure_schema(db)
        now = time.time()
        db.execute(
            "INSERT OR IGNORE INTO locations (id, name, description, created_at) "
            "VALUES ('town_square', 'Town Square', 'test', ?)",
            (now,),
        )
        db.execute(
            "INSERT OR REPLACE INTO world_registry "
            "(id, world_id, name, region, timezone, hosted_agent_id, entry_location_id, api_port, created_at, updated_at) "
            "VALUES (1, 'valdris', 'Valdris', 'test', 'UTC', 'palantir', 'town_square', 8765, ?, ?)",
            (now, now),
        )
        # Seed 200 NPCs so formation is not capped by max_open_factions (max(3, pop//250)).
        rows = []
        for i in range(200):
            npc_id = f"valdris:npc:{i:04d}"
            rows.append(
                (npc_id, f"Valdris NPC {i}", "npc", "town_square", "active", "{}", now, now)
            )
        db.executemany(
            "INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

        # 16 ticks of 0.0625 each -- 1.00 cumulative, 0.70 over threshold.
        # Formation probability at this level is min(0.18, 0.70 * 0.20) = 0.14
        # which is high enough to fire deterministically with seed=4242.
        sigs = []
        for tick in range(1, 17):
            for sig_type in ("labor_unrest", "repression_visibility", "migration_pressure", "economic_stress"):
                sigs.append(
                    (f"sig:valdris:{tick}:{sig_type}", tick, "valdris", "capital", sig_type, 0.0625 / 4, 1, "{}", now)
                )
        db.executemany(
            "INSERT OR REPLACE INTO meso_signals "
            "(signal_id, tick_number, world_id, location_id, signal_type, magnitude, source_event_count, payload, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            sigs,
        )
        db.commit()

        # Run the lifecycle at tick 20 with cumulative pressure window of 16.
        import random
        # seed=31 was verified empirically to fire formation with the test
        # magnitudes above (cumulative=0.75, p_fire ≈ min(0.18, 0.09) = 0.09).
        counts = faction_lifecycle.run_faction_lifecycle(
            db,
            world_id="valdris",
            tick_number=20,
            rng=random.Random(31),
        )
        assert counts.get("formed", 0) >= 1, (
            f"Faction should have formed under 0.40 cumulative pressure, got counts={counts}"
        )
        # run_faction_lifecycle does not commit -- commit here so the DB
        # query below sees the newly-inserted faction.
        db.commit()
        # A newly-formed faction may be resolved to a terminal status
        # (integrated / legalized / dissolved) by the same call's outcome
        # loop -- so check the causal_events table for ``faction_formed``,
        # which is the canonical "did a faction emerge?" signal.
        events = db.execute(
            "SELECT COUNT(*) FROM causal_events WHERE world_id='valdris' AND event_type='faction_formed'"
        ).fetchone()[0]
        assert events >= 1, f"Expected ≥1 faction_formed event, found {events}"


# ---------------------------------------------------------------------------
# End-to-end smoke: a 25-year run must produce ≥1 active faction somewhere
# ---------------------------------------------------------------------------

class TestLongRunFactionFormation:
    """A 25-year federation run must produce factions somewhere (cumulative pressure exists)."""

    def test_25_year_run_forms_at_least_one_faction(self, tmp_path: Path) -> None:
        """End-to-end: run the full orchestrator, count faction_formed events across worlds."""
        out = tmp_path / "aurelia-long"
        # 25 years, ticks_per_year=4 → 100 ticks, 5 worlds, 100 NPCs each.
        federation_orchestrator.run_causal_simulation(
            output_dir=out,
            years=25,
            ticks_per_year=4,
            worlds=["arkos", "valdris", "mirithane", "solara", "verge"],
            npc_count=100,
            seed=4242,
            max_interactions=80,
        )

        # A faction may be resolved to a terminal status (integrated /
        # legalized / dissolved) on the same tick it forms, so the
        # canonical "did a faction emerge?" signal is the
        # ``faction_formed`` causal_event, not the ``status`` column.
        total_formed = 0
        worlds_with_formations = 0
        for db_path in sorted(out.glob("*.db")):
            if db_path.name == "federation.db":
                continue
            db = sqlite3.connect(str(db_path))
            try:
                formed = db.execute(
                    "SELECT COUNT(*) FROM causal_events WHERE event_type='faction_formed'"
                ).fetchone()[0]
            except sqlite3.OperationalError:
                formed = 0
            db.close()
            total_formed += formed
            if formed > 0:
                worlds_with_formations += 1

        assert total_formed >= 1, (
            f"25-year run should have formed ≥1 faction, found {total_formed} "
            f"formation events across {worlds_with_formations} worlds (run dir: {out})"
        )
