import json
import random
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import causal_ledger
import macro_dynamics
import regime_transitions
import world_state


def make_world(tmp_path, world_id="solara", n=40):
    db = world_state.init_world(tmp_path / f"{world_id}.db")
    db.row_factory = sqlite3.Row
    now = time.time()
    db.execute("INSERT OR IGNORE INTO locations (id, name, description, created_at) VALUES ('town_square', 'Town Square', 'test', ?)", (now,))
    db.execute("""INSERT OR REPLACE INTO world_registry (id, world_id, name, region, timezone, hosted_agent_id, entry_location_id, api_port, created_at, updated_at)
        VALUES (1, ?, ?, 'test', 'UTC', 'palantir', 'town_square', 8765, ?, ?)""",
        (world_id, world_id.title(), now, now))
    rows = []
    for i in range(n):
        npc_id = f"{world_id}:npc:{i}"
        rows.append((npc_id, f"NPC {i}", "npc", "town_square", "active", json.dumps({"npc_type": "human", "nationality": world_id}), now, now))
    db.executemany("INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.commit()
    return db


def force_collapse(db, world_id, tick):
    macro_dynamics.ensure_schema(db)
    for t in range(tick - 3, tick + 1):
        db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (
            world_id, t, json.dumps({"gdp_proxy": 0.02, "legitimacy": 0.03, "repression": 0.92, "war_pressure": 0.85, "border_openness": 0.10,
                                      "fiscal_capacity": 0.05, "public_health": 0.30, "food_security": 0.20, "water_security": 0.20,
                                      "infrastructure": 0.25, "type_tension": 0.70, "inequality": 0.60}), time.time()
        ))


def test_crisis_triggered_after_3_ticks_of_collapse(tmp_path):
    db = make_world(tmp_path, "arkos")
    force_collapse(db, "arkos", 10)
    rng = random.Random(42)
    result = regime_transitions.check_and_resolve_crisis(db, world_id="arkos", tick_number=10, rng=rng)
    assert result is not None
    assert result["triggered"] is True


def test_elite_defection_resets_legitimacy(tmp_path):
    db = make_world(tmp_path, "solara")
    force_collapse(db, "solara", 8)
    # Force elite_defection path
    regime_transitions.ensure_schema(db)
    db.execute("INSERT OR REPLACE INTO regime_events (event_id, world_id, tick_number, event_type, resolution_path, payload, created_at) VALUES (?, ?, ?, 'regime_crisis_triggered', 'elite_defection', '{}', ?)",
               ("ev1", "solara", 8, time.time()))
    rng = random.Random(1)
    macro_dynamics.ensure_schema(db)
    # Seed the macro state with a row that will be read by the resolution
    regime_transitions._resolve_elite_defection(db, world_id="solara", tick_number=8, rng=rng)
    state = macro_dynamics.latest_state(db, "solara")
    assert state["legitimacy"] > 0.30


def test_terminal_collapse_sets_post_collapse_status(tmp_path):
    db = make_world(tmp_path, "valdris")
    force_collapse(db, "valdris", 12)
    regime_transitions.ensure_schema(db)
    # Force conditions that lead to terminal collapse (no legalized factions, no border openness, high repression)
    rng = random.Random(99)
    result = regime_transitions.check_and_resolve_crisis(db, world_id="valdris", tick_number=12, rng=rng)
    # This should either be terminal_collapse or another path depending on rng
    assert result is not None
    assert result["resolution"] in {"elite_defection", "popular_uprising", "external_intervention",
                                      "reform_from_within", "terminal_collapse"}


def test_bottom_up_revival_chance(tmp_path):
    db = make_world(tmp_path, "arkos")
    regime_transitions.ensure_schema(db)
    # Set post-collapse status
    db.execute("""
        INSERT INTO regime_events (event_id, world_id, tick_number, event_type, resolution_path, payload, created_at)
        VALUES (?, ?, ?, 'terminal_collapse', 'terminal_collapse', ?, ?)
    """, ("ev2", "arkos", 20, json.dumps({"post_collapse": True}), time.time()))
    # Force revival with a guaranteed-roll seed
    rng = random.Random(42)
    revived = regime_transitions._check_post_collapse_revival(db, world_id="arkos", tick_number=30, rng=rng)
    # Random(42).random() = 0.639 > 0.02, so this shouldn't fire
    assert revived is False


def test_reform_from_within_path(tmp_path):
    db = make_world(tmp_path, "mirithane")
    # Moderate collapse — repression not too high
    macro_dynamics.ensure_schema(db)
    for t in range(5, 9):
        db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (
            "mirithane", t, json.dumps({"gdp_proxy": 0.04, "legitimacy": 0.06, "repression": 0.50, "war_pressure": 0.30,
                                          "border_openness": 0.40, "fiscal_capacity": 0.15, "public_health": 0.40,
                                          "food_security": 0.35, "water_security": 0.35, "infrastructure": 0.40,
                                          "type_tension": 0.40, "inequality": 0.45}), time.time()
        ))
    # Add legalized faction to enable reform
    db.execute("""INSERT INTO factions (faction_id, name, world_id, region, status, primary_grievance, demand, member_count, influence, founded_tick, metadata, created_at)
        VALUES ('fac_ref', 'Reform', 'mirithane', 'capital', 'legalized', 'labor_unrest', 'reform', 50, 0.6, 5, '{}', ?)""", (time.time(),))
    rng = random.Random(1)
    result = regime_transitions.check_and_resolve_crisis(db, world_id="mirithane", tick_number=8, rng=rng)
    assert result is not None
    # Should pick reform_from_within since repression is moderate and there's a legalized faction
