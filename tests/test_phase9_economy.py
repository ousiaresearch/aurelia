"""Phase 9 capital economy tests — value creation through productive activity."""
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


def make_world(tmp_path, world_id="solara"):
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
    db.commit()
    return db


def test_ensure_schema_creates_capital_pool():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    capital_economy.ensure_schema(db)
    row = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='capital_pool'").fetchone()
    assert row is not None
    cols = {r["name"] for r in db.execute("PRAGMA table_info(capital_pool)").fetchall()}
    assert {"world_id", "stock", "gdp_flow", "investment_rate", "tech_level", "innovation_stock"}.issubset(cols)


def test_gdp_flow_accumulates_from_productive_events(tmp_path):
    db = make_world(tmp_path, "solara")
    capital_economy.ensure_schema(db)
    # Inject productive event counts
    db.execute(
        """INSERT INTO capital_pool (world_id, stock, gdp_flow, investment_rate, tech_level, innovation_stock, updated_at)
           VALUES ('solara', 0.5, 0.0, 0.0, 0.1, 0.0, ?)""",
        (time.time(),),
    )
    events = {"work_success": 200, "small_trade": 100, "caregiving": 150, "productive_confidence": 50}
    for et, count in events.items():
        for _ in range(count):
            causal_ledger.emit_event(
                db, tick_number=1, world_id="solara", layer="micro",
                event_type=et, scope="household", magnitude=1.0,
            )
    capital_economy.apply_capital_flows(db, world_id="solara", tick_number=1)
    pool = capital_economy.get_pool(db, "solara")
    assert pool["gdp_flow"] > 0
    assert pool["stock"] >= 0.5  # at minimum unchanged


def test_capital_decays_under_war_pressure(tmp_path):
    db = make_world(tmp_path, "arkos")
    capital_economy.ensure_schema(db)
    db.execute(
        """INSERT INTO capital_pool (world_id, stock, gdp_flow, investment_rate, tech_level, innovation_stock, updated_at)
           VALUES ('arkos', 0.8, 0.0, 0.0, 0.1, 0.0, ?)""",
        (time.time(),),
    )
    # Force high war_pressure by writing macro_state
    import macro_dynamics
    macro_dynamics.ensure_schema(db)
    db.execute(
        "INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        ("arkos", 1, json.dumps({
            "gdp_proxy": 0.4, "legitimacy": 0.4, "repression": 0.6, "war_pressure": 0.95,
            "fiscal_capacity": 0.4, "public_health": 0.5, "food_security": 0.5,
            "border_openness": 0.5, "type_tension": 0.4, "inequality": 0.4,
        }), time.time()),
    )
    capital_economy.apply_capital_flows(db, world_id="arkos", tick_number=1)
    pool = capital_economy.get_pool(db, "arkos")
    assert pool["stock"] < 0.8  # decayed


def test_innovation_grows_from_rumor_velocity_and_tech(tmp_path):
    db = make_world(tmp_path, "mirithane")
    capital_economy.ensure_schema(db)
    db.execute(
        """INSERT INTO capital_pool (world_id, stock, gdp_flow, investment_rate, tech_level, innovation_stock, updated_at)
           VALUES ('mirithane', 0.5, 0.0, 0.0, 0.4, 0.1, ?)""",
        (time.time(),),
    )
    for _ in range(80):
        causal_ledger.emit_event(
            db, tick_number=1, world_id="mirithane", layer="micro",
            event_type="rumor_velocity", scope="network", magnitude=0.8,
        )
    capital_economy.apply_capital_flows(db, world_id="mirithane", tick_number=1)
    pool = capital_economy.get_pool(db, "mirithane")
    assert pool["innovation_stock"] > 0.1


def test_gdp_proxy_is_derived_from_capital(tmp_path):
    db = make_world(tmp_path, "verge")
    capital_economy.ensure_schema(db)
    capital_economy.seed_pool(db, "verge", stock=0.7, innovation=0.3, tech=0.4)
    gdp = capital_economy.gdp_proxy_for(db, "verge")
    # gdp = stock + innovation * tech = 0.7 + 0.3*0.4 = 0.82
    assert abs(gdp - 0.82) < 0.01


def test_investment_rate_driven_by_legitimacy_and_fiscal(tmp_path):
    db = make_world(tmp_path, "valdris")
    import macro_dynamics
    macro_dynamics.ensure_schema(db)
    capital_economy.ensure_schema(db)
    db.execute(
        "INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        ("valdris", 1, json.dumps({
            "gdp_proxy": 0.5, "legitimacy": 0.8, "fiscal_capacity": 0.6, "war_pressure": 0.1,
            "repression": 0.3, "public_health": 0.6, "food_security": 0.6,
            "border_openness": 0.5, "type_tension": 0.3, "inequality": 0.4,
        }), time.time()),
    )
    rate = capital_economy.compute_investment_rate(db, "valdris")
    # investment = 0.8 * 0.6 + 0.6 * 0.4 = 0.48 + 0.24 = 0.72
    assert abs(rate - 0.72) < 0.01


def test_two_worlds_diverge_in_capital_accumulation(tmp_path):
    """Worlds with different profiles accumulate capital at different rates."""
    db_high = make_world(tmp_path, "mirithane")
    db_low = make_world(tmp_path, "solara")
    capital_economy.ensure_schema(db_high)
    capital_economy.ensure_schema(db_low)
    # Inject same productive events into both
    for db in (db_high, db_low):
        db.execute(
            """INSERT INTO capital_pool (world_id, stock, gdp_flow, investment_rate, tech_level, innovation_stock, updated_at)
               VALUES (?, 0.3, 0.0, 0.0, 0.1, 0.0, ?)""",
            (db.execute("SELECT world_id FROM world_registry").fetchone()["world_id"], time.time()),
        )
        for _ in range(100):
            causal_ledger.emit_event(
                db, tick_number=1, world_id=db.execute("SELECT world_id FROM world_registry").fetchone()["world_id"],
                layer="micro", event_type="work_success", scope="household", magnitude=1.0,
            )
    import macro_dynamics
    macro_dynamics.ensure_schema(db_high)
    macro_dynamics.ensure_schema(db_low)
    # Mirithane: high legitimacy, low repression
    db_high.execute(
        "INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        ("mirithane", 1, json.dumps({
            "gdp_proxy": 0.5, "legitimacy": 0.85, "fiscal_capacity": 0.7, "war_pressure": 0.02,
            "repression": 0.2, "public_health": 0.78, "food_security": 0.68,
            "border_openness": 0.5, "type_tension": 0.3, "inequality": 0.4,
        }), time.time()),
    )
    # Solara: low legitimacy, high repression
    db_low.execute(
        "INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        ("solara", 1, json.dumps({
            "gdp_proxy": 0.4, "legitimacy": 0.20, "fiscal_capacity": 0.3, "war_pressure": 0.5,
            "repression": 0.8, "public_health": 0.5, "food_security": 0.4,
            "border_openness": 0.35, "type_tension": 0.5, "inequality": 0.5,
        }), time.time()),
    )
    capital_economy.apply_capital_flows(db_high, world_id="mirithane", tick_number=1)
    capital_economy.apply_capital_flows(db_low, world_id="solara", tick_number=1)
    p_high = capital_economy.get_pool(db_high, "mirithane")
    p_low = capital_economy.get_pool(db_low, "solara")
    assert p_high["stock"] > p_low["stock"]
