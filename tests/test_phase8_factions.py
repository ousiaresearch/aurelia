import json
import random
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import causal_ledger
import faction_lifecycle
import federation_effects
import macro_dynamics
import meso_aggregator
import world_state


def make_world(tmp_path, world_id="solara", n=160):
    db = world_state.init_world(tmp_path / f"{world_id}.db")
    db.row_factory = sqlite3.Row
    now = time.time()
    db.execute(
        "INSERT OR IGNORE INTO locations (id, name, description, created_at) VALUES ('town_square', 'Town Square', 'test', ?)",
        (now,),
    )
    db.execute(
        """
        INSERT OR REPLACE INTO world_registry
            (id, world_id, name, region, timezone, hosted_agent_id, entry_location_id, api_port, created_at, updated_at)
        VALUES (1, ?, ?, 'test', 'UTC', 'palantir', 'town_square', 8765, ?, ?)
        """,
        (world_id, world_id.title(), now, now),
    )
    rows = []
    ds = []
    for i in range(n):
        npc_id = f"{world_id}:npc:{i}"
        rows.append((npc_id, f"NPC {i}", "npc", "town_square", "active", json.dumps({"npc_type": "human", "nationality": world_id}), now, now))
        ds.append((npc_id, json.dumps({"security": 0.35, "satisfaction": 0.32, "connectedness": 0.55, "restlessness": 0.65, "economic_stability": 0.35, "observed_injustice": 0.55}), now, "[]"))
    db.executemany("INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.executemany("INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated, decision_log) VALUES (?, ?, ?, ?)", ds)
    db.commit()
    return db


def insert_faction(db, world_id="solara", faction_id="fac1", status="active", members=80, influence=0.8, score=0.9):
    faction_lifecycle._ensure_extra_columns(db)
    now = time.time()
    db.execute(
        """
        INSERT INTO factions (faction_id, name, world_id, region, status, primary_grievance,
                              demand, member_count, influence, founded_tick, metadata, created_at,
                              lifecycle_stage, consequence_score, last_action_tick)
        VALUES (?, 'Test Front', ?, 'capital', ?, 'labor_unrest', 'concessions', ?, ?, 1, '{}', ?, 'organization', ?, 1)
        """,
        (faction_id, world_id, status, members, influence, now, score),
    )
    db.commit()


def force_macro(db, world_id, tick, state):
    macro_dynamics.ensure_schema(db)
    db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (world_id, tick, json.dumps(state), time.time()))


def force_pressure(db, world_id, tick, mag=5.0):
    meso_aggregator.ensure_schema(db)
    db.execute("""
        INSERT OR REPLACE INTO meso_signals (signal_id, tick_number, world_id, location_id, signal_type, magnitude, source_event_count, payload, created_at)
        VALUES (?, ?, ?, 'town_square', 'labor_unrest', ?, 80, '{}', ?)
    """, (f"sig:{world_id}:{tick}", tick, world_id, mag, time.time()))


def test_low_legitimacy_high_repression_produces_non_integration_outcome(tmp_path):
    db = make_world(tmp_path, "solara")
    insert_faction(db, "solara", "fac1", members=100, influence=0.9, score=0.95)
    force_macro(db, "solara", 2, {"legitimacy": 0.10, "repression": 0.95, "war_pressure": 0.80, "gdp_proxy": 0.30, "public_health": 0.40})
    force_pressure(db, "solara", 3, mag=6.0)
    counts = faction_lifecycle.run_faction_lifecycle(db, world_id="solara", tick_number=3, rng=random.Random(4))
    assert counts["suppressed"] + counts["exiled"] + counts["radicalized"] + counts["splintered"] > 0
    assert db.execute("SELECT COUNT(*) FROM causal_events WHERE event_type IN ('faction_suppressed','faction_exiled','faction_radicalized','faction_splintered')").fetchone()[0] > 0


def test_splinter_outcome_creates_child_faction(tmp_path):
    db = make_world(tmp_path, "verge")
    insert_faction(db, "verge", "fac1", members=120, influence=0.95, score=1.2)
    force_macro(db, "verge", 2, {"legitimacy": 0.20, "repression": 0.20, "war_pressure": 0.95, "gdp_proxy": 0.30, "public_health": 0.40})
    force_pressure(db, "verge", 3, mag=8.0)
    counts = faction_lifecycle.run_faction_lifecycle(db, world_id="verge", tick_number=3, rng=random.Random(7), force_outcome="splintered")
    assert counts["splintered"] == 1
    assert db.execute("SELECT COUNT(*) FROM factions WHERE world_id='verge'").fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM causal_events WHERE event_type='faction_splintered'").fetchone()[0] == 1


def test_splintered_parent_is_marked_terminal(tmp_path):
    """A splintered parent must leave the open-factions set.

    Pre-fix: the parent stayed in the open set, got re-rolled every tick,
    could splinter again -- producing 2x open factions per tick.
    Post-fix: the parent is marked status='dissolved' with
    lifecycle_stage='splintered' for analytics. Only the child is open.
    """
    db = make_world(tmp_path, "verge")
    insert_faction(db, "verge", "fac1", members=120, influence=0.95, score=1.2)
    force_macro(db, "verge", 2, {"legitimacy": 0.20, "repression": 0.20, "war_pressure": 0.95, "gdp_proxy": 0.30, "public_health": 0.40})
    force_pressure(db, "verge", 3, mag=8.0)
    faction_lifecycle.run_faction_lifecycle(db, world_id="verge", tick_number=3, rng=random.Random(7), force_outcome="splintered")

    parent = db.execute("SELECT status, lifecycle_stage FROM factions WHERE faction_id='fac1'").fetchone()
    assert parent["status"] in faction_lifecycle.TERMINAL_STATUSES, (
        "Splintered parent still open: status=" + str(parent["status"]) +
        ". Open factions will double per tick."
    )
    assert parent["lifecycle_stage"] == "splintered", (
        "lifecycle_stage should be 'splintered' for analytics; got " + str(parent["lifecycle_stage"])
    )

    # And: the parent should NOT be counted as open in subsequent ticks.
    placeholders = ",".join("?" * len(faction_lifecycle.TERMINAL_STATUSES))
    open_count = db.execute(
        "SELECT COUNT(*) FROM factions WHERE world_id='verge' AND status NOT IN (" + placeholders + ")",
        list(faction_lifecycle.TERMINAL_STATUSES),
    ).fetchone()[0]
    assert open_count == 1, "Expected exactly 1 open faction (the child), got " + str(open_count)


def test_splintering_in_a_loop_does_not_explode_open_factions(tmp_path):
    """Forcing the splinter outcome over 20 ticks must keep the
    open-factions set bounded -- not let it double per tick.

    Pre-fix: with force_outcome='splintered', open_factions grows
    1, 2, 4, 8, 16, ... (uncapped for existing factions).
    Post-fix: each splinter dissolves the parent and creates 1 child,
    so the open set stays small. New formations can still add a few
    rows over 20 ticks (formation cap is max(3, pop//250)=3), but
    nothing exponential.
    """
    db = make_world(tmp_path, "verge", n=200)
    insert_faction(db, "verge", "fac1", members=100, influence=0.9, score=1.0)
    placeholders = ",".join("?" * len(faction_lifecycle.TERMINAL_STATUSES))
    open_counts = []
    # Hard cap on test runtime: if the bug returns and creates
    # exponential factions, bail out at first tick where open > 8
    # (which proves the bug is back without running for 20 ticks).
    for tick in range(1, 21):
        force_macro(db, "verge", tick, {"legitimacy": 0.20, "repression": 0.20, "war_pressure": 0.95, "gdp_proxy": 0.30, "public_health": 0.40})
        force_pressure(db, "verge", tick, mag=8.0)
        faction_lifecycle.run_faction_lifecycle(
            db, world_id="verge", tick_number=tick,
            rng=random.Random(7 + tick), force_outcome="splintered",
        )
        open_count = db.execute(
            "SELECT COUNT(*) FROM factions WHERE world_id='verge' AND status NOT IN (" + placeholders + ")",
            list(faction_lifecycle.TERMINAL_STATUSES),
        ).fetchone()[0]
        open_counts.append(open_count)
        if open_count > 8:
            # Bug returned -- fail fast with diagnostic data.
            assert False, (
                "Open factions exploded at tick " + str(tick) + ": " +
                str(open_count) + " open. Trajectory: " + str(open_counts)
            )

    # Bound: open_factions should stay small (formation cap = 3 for
    # n=200, plus one residual child from the last splinter). Pre-fix
    # this would be 16, 32, 64+ within a handful of ticks.
    assert max(open_counts) <= 4, (
        "Open factions grew too large under repeated splintering: max=" +
        str(max(open_counts)) + ". Trajectory: " + str(open_counts)
    )


def test_high_legitimacy_low_repression_produces_constructive_outcome(tmp_path):
    db = make_world(tmp_path, "mirithane")
    insert_faction(db, "mirithane", "fac1", members=80, influence=0.6, score=0.7)
    force_macro(db, "mirithane", 2, {"legitimacy": 0.85, "repression": 0.05, "war_pressure": 0.05, "gdp_proxy": 0.70, "public_health": 0.80})
    force_pressure(db, "mirithane", 3, mag=4.0)
    counts = faction_lifecycle.run_faction_lifecycle(db, world_id="mirithane", tick_number=3, rng=random.Random(1))
    assert counts["integrated"] + counts["legalized"] + counts["governing_coalition"] > 0


def test_faction_exiled_schedules_paired_migration_effects(tmp_path):
    fed = sqlite3.connect(tmp_path / "fed.db")
    fed.row_factory = sqlite3.Row
    causal_ledger.ensure_schema(fed)
    causal_ledger.emit_event(fed, tick_number=1, world_id="solara", layer="macro", event_type="faction_exiled", scope="faction", magnitude=1.0, valence=-0.6)
    federation_effects.resolve_outbound_effects(fed, tick_number=1, worlds=["solara", "valdris"])
    assert any(e["effect_type"] == "refugee_outflow" for e in causal_ledger.due_effects(fed, 2, "solara"))
    assert any(e["effect_type"] == "refugee_inflow" for e in causal_ledger.due_effects(fed, 2, "valdris"))
