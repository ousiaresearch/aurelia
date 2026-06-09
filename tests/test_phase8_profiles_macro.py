import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import macro_dynamics
import meso_aggregator
import world_profiles
import world_state


def make_world(tmp_path, world_id="solara", n=40):
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
        ds.append((npc_id, json.dumps({
            "security": 0.55,
            "satisfaction": 0.55,
            "connectedness": 0.55,
            "restlessness": 0.25,
            "economic_stability": 0.55,
            "observed_injustice": 0.05,
        }), now, "[]"))
    db.executemany("INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.executemany("INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated, decision_log) VALUES (?, ?, ?, ?)", ds)
    db.commit()
    return db


def test_profiles_are_distinct_and_merged():
    solara = world_profiles.profile("solara")
    verge = world_profiles.profile("verge")
    assert solara["macro_baseline"]["repression"] > verge["macro_baseline"]["repression"]
    assert verge["migration"]["refugee_tolerance"] > solara["migration"]["refugee_tolerance"]
    assert "gdp_proxy" in solara["macro_baseline"]
    assert "shock_absorption" in verge["resilience"]


def test_macro_state_uses_world_specific_baselines(tmp_path):
    solara = make_world(tmp_path, "solara", n=20)
    verge = make_world(tmp_path, "verge", n=20)
    s = macro_dynamics.latest_state(solara, "solara")
    v = macro_dynamics.latest_state(verge, "verge")
    assert s["repression"] > v["repression"]
    assert v["border_openness"] > s["border_openness"]


def test_macro_shocks_are_capped(tmp_path):
    db = make_world(tmp_path, "solara", n=100)
    meso_aggregator.ensure_schema(db)
    db.execute("""
        INSERT INTO meso_signals (signal_id, tick_number, world_id, location_id, signal_type, magnitude, source_event_count, payload, created_at)
        VALUES ('shock', 1, 'solara', 'town_square', 'economic_stress', 100.0, 100, '{}', ?)
    """, (time.time(),))
    before = macro_dynamics.latest_state(db, "solara")
    macro_dynamics.apply_macro_dynamics(db, world_id="solara", tick_number=1)
    after = macro_dynamics.latest_state(db, "solara")
    assert before["gdp_proxy"] - after["gdp_proxy"] <= 0.025
    assert before["legitimacy"] - after["legitimacy"] <= 0.025


def test_macro_state_can_recover_from_sub_baseline(tmp_path):
    db = make_world(tmp_path, "mirithane", n=100)
    macro_dynamics.ensure_schema(db)
    db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (
        "mirithane", 0, json.dumps({
            "public_health": 0.30,
            "fiscal_capacity": 0.70,
            "legitimacy": 0.70,
            "repression": 0.10,
            "war_pressure": 0.0,
        }), time.time()
    ))
    before = macro_dynamics.latest_state(db, "mirithane")["public_health"]
    macro_dynamics.apply_macro_dynamics(db, world_id="mirithane", tick_number=1)
    after = macro_dynamics.latest_state(db, "mirithane")["public_health"]
    assert after > before
    assert db.execute("SELECT COUNT(*) FROM causal_events WHERE event_type='macro_resilience_recovery'").fetchone()[0] >= 1
