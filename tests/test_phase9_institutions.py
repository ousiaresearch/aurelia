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
import institutions
import macro_dynamics
import world_state


def make_world(tmp_path, world_id="solara", n=80):
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
        ds.append((npc_id, json.dumps({"security": 0.55, "satisfaction": 0.55, "connectedness": 0.55, "restlessness": 0.25, "economic_stability": 0.55}), now, "[]"))
    db.executemany("INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.executemany("INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated, decision_log) VALUES (?, ?, ?, ?)", ds)
    macro_dynamics.ensure_schema(db)
    return db


def insert_faction(db, world_id="solara", faction_id="fac1", status="active", grievance="labor_unrest", members=80):
    faction_lifecycle._ensure_extra_columns(db)
    now = time.time()
    db.execute(
        """
        INSERT INTO factions (faction_id, name, world_id, region, status, primary_grievance,
                              demand, member_count, influence, founded_tick, metadata, created_at,
                              lifecycle_stage, consequence_score, last_action_tick)
        VALUES (?, ?, ?, 'capital', ?, ?, 'concessions', ?, ?, 1, '{}', ?, 'organization', ?, 1)
        """,
        (faction_id, f"{grievance.replace('_',' ').title()} Front", world_id, status, grievance, members, 0.7, now, 0.5),
    )
    db.commit()


def test_institution_formed_from_legalized_faction(tmp_path):
    db = make_world(tmp_path, "mirithane")
    institutions.ensure_schema(db)
    insert_faction(db, "mirithane", "fac1", status="legalized", grievance="labor_unrest", members=50)
    causal_ledger.emit_event(
        db, tick_number=3, world_id="mirithane", layer="macro",
        event_type="faction_legalized", scope="faction", magnitude=0.5, valence=0.35,
        target_ids=["fac1"],
        payload={"faction_id": "fac1", "members": 50},
    )
    macro_dynamics.ensure_schema(db)
    db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (
        "mirithane", 3, json.dumps({"legitimacy": 0.70, "repression": 0.10, "war_pressure": 0.05, "fiscal_capacity": 0.60}), time.time()
    ))
    rng = random.Random(1)
    institutions.process_faction_outcome(db, world_id="mirithane", tick_number=3, faction_id="fac1",
                                          outcome="legalized", grievance="labor_unrest", rng=rng)
    inst = db.execute("SELECT * FROM institutions WHERE founding_faction_id='fac1'").fetchone()
    assert inst is not None
    assert inst["type"] == "labor_union"
    assert inst["durability"] > 0.3
    assert json.loads(inst["benefits"])["gdp_flow"] > 0


def test_institution_benefits_applied_to_macro(tmp_path):
    db = make_world(tmp_path, "solara")
    institutions.ensure_schema(db)
    macro_dynamics.ensure_schema(db)
    db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (
        "solara", 5, json.dumps({"legitimacy": 0.60, "repression": 0.25, "war_pressure": 0.10, "fiscal_capacity": 0.55,
                                  "gdp_proxy": 0.50, "public_health": 0.60, "border_openness": 0.45, "type_tension": 0.30,
                                  "food_security": 0.55, "water_security": 0.55, "infrastructure": 0.55, "inequality": 0.45}), time.time()
    ))
    institutions.create_institution(db, world_id="solara", tick_number=5, faction_id="fac1",
                                     inst_type="labor_union", name="United Workers")
    institutions.apply_institution_benefits(db, world_id="solara", tick_number=6)
    event = db.execute(
        "SELECT * FROM causal_events WHERE event_type='institution_benefit_applied' AND world_id='solara' LIMIT 1"
    ).fetchone()
    assert event is not None


def test_institution_decays_under_war_pressure(tmp_path):
    db = make_world(tmp_path, "arkos")
    institutions.ensure_schema(db)
    macro_dynamics.ensure_schema(db)
    db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (
        "arkos", 5, json.dumps({"legitimacy": 0.30, "repression": 0.40, "war_pressure": 0.85, "fiscal_capacity": 0.30,
                                  "gdp_proxy": 0.30, "public_health": 0.45, "border_openness": 0.30, "type_tension": 0.55,
                                  "food_security": 0.40, "water_security": 0.45, "infrastructure": 0.40, "inequality": 0.55}), time.time()
    ))
    institutions.create_institution(db, world_id="arkos", tick_number=5, faction_id="fac1",
                                     inst_type="political_party", name="Reform Party")
    inst_before = db.execute("SELECT durability FROM institutions WHERE world_id='arkos'").fetchone()
    institutions.apply_institution_benefits(db, world_id="arkos", tick_number=6)
    inst_after = db.execute("SELECT durability FROM institutions WHERE world_id='arkos'").fetchone()
    assert inst_after["durability"] < inst_before["durability"]


def test_second_faction_reinforces_institution(tmp_path):
    db = make_world(tmp_path, "valdris")
    institutions.ensure_schema(db)
    macro_dynamics.ensure_schema(db)
    db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (
        "valdris", 4, json.dumps({"legitimacy": 0.65, "repression": 0.15, "war_pressure": 0.05, "fiscal_capacity": 0.60,
                                  "gdp_proxy": 0.60, "public_health": 0.65, "border_openness": 0.50, "type_tension": 0.25,
                                  "food_security": 0.60, "water_security": 0.60, "infrastructure": 0.60, "inequality": 0.40}), time.time()
    ))
    institutions.create_institution(db, world_id="valdris", tick_number=4, faction_id="fac1",
                                     inst_type="labor_union", name="First Union")
    first_dur = db.execute("SELECT durability FROM institutions WHERE world_id='valdris'").fetchone()["durability"]
    rng = random.Random(7)  # first random ~0.32, well below form_prob
    institutions.process_faction_outcome(db, world_id="valdris", tick_number=5, faction_id="fac2",
                                          outcome="legalized", grievance="labor_unrest", rng=rng)
    second_dur = db.execute("SELECT durability FROM institutions WHERE world_id='valdris'").fetchone()["durability"]
    assert second_dur > first_dur
