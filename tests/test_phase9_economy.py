import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import capital_economy
import causal_ledger
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
    db.commit()
    return db


def test_capital_pool_schema(tmp_path):
    db = make_world(tmp_path, "solara")
    capital_economy.ensure_schema(db)
    row = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='capital_pool'").fetchone()
    assert row is not None


def test_capital_grows_from_productive_events(tmp_path):
    db = make_world(tmp_path, "mirithane")
    capital_economy.ensure_schema(db)
    causal_ledger.ensure_schema(db)

    # Simulate productive events
    for i in range(10):
        causal_ledger.emit_event(
            db, tick_number=1, world_id="mirithane", layer="micro",
            event_type="work_success", scope="individual", magnitude=0.5, valence=0.3,
        )
    for i in range(5):
        causal_ledger.emit_event(
            db, tick_number=1, world_id="mirithane", layer="micro",
            event_type="small_trade", scope="individual", magnitude=0.3, valence=0.2,
        )

    capital_economy.apply_capital_flows(db, world_id="mirithane", tick_number=1)
    state = capital_economy.latest_capital(db, "mirithane")
    assert state["stock"] > 0.5
    assert state["gdp_flow"] > 0.0
    assert state["investment_rate"] > 0.0


def test_capital_decays_under_high_war_pressure(tmp_path):
    db = make_world(tmp_path, "arkos")
    capital_economy.ensure_schema(db)
    causal_ledger.ensure_schema(db)

    # Seed capital
    db.execute(
        "INSERT OR REPLACE INTO capital_pool (world_id, stock, gdp_flow, investment_rate, tech_level, innovation_stock, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("arkos", 0.9, 0.05, 0.6, 0.1, 0.05, time.time()),
    )

    # Simulate war decay: no productive events, high war pressure macro state
    import macro_dynamics
    macro_dynamics.ensure_schema(db)
    db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (
        "arkos", 1, json.dumps({"war_pressure": 0.95, "legitimacy": 0.05, "fiscal_capacity": 0.10, "gdp_proxy": 0.5}), time.time()
    ))

    capital_economy.apply_capital_flows(db, world_id="arkos", tick_number=2)
    state = capital_economy.latest_capital(db, "arkos")
    assert state["stock"] < 0.9


def test_innovation_grows_from_rumor_velocity(tmp_path):
    db = make_world(tmp_path, "verge")
    capital_economy.ensure_schema(db)
    causal_ledger.ensure_schema(db)

    for i in range(15):
        causal_ledger.emit_event(
            db, tick_number=2, world_id="verge", layer="meso",
            event_type="rumor_velocity", scope="region", magnitude=0.4, valence=0.0,
        )

    capital_economy.apply_capital_flows(db, world_id="verge", tick_number=2)
    state = capital_economy.latest_capital(db, "verge")
    assert state["innovation_stock"] > 0.0


def test_gdp_derived_from_capital(tmp_path):
    db = make_world(tmp_path, "valdris")
    capital_economy.ensure_schema(db)

    # Set known capital state
    db.execute(
        "INSERT OR REPLACE INTO capital_pool (world_id, stock, gdp_flow, investment_rate, tech_level, innovation_stock, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("valdris", 0.7, 0.10, 0.65, 0.15, 0.08, time.time()),
    )

    gdp = capital_economy.compute_gdp_proxy(db, "valdris")
    # GDP should be a function of stock + innovation*tech
    assert gdp > 0.25
    assert gdp <= 1.0
    # stock alone is 0.7, innovation*tech is 0.08*0.15=0.012, so GDP should be roughly moderate
    assert 0.3 <= gdp <= 0.9
