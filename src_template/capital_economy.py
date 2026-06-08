"""capital_economy.py — persistent capital pool, GDP flow, and innovation."""
from __future__ import annotations

import json
import time

try:
    from . import causal_ledger, macro_dynamics
except Exception:
    import causal_ledger
    import macro_dynamics

PRODUCTIVE_EVENTS = {
    "work_success": 0.002,
    "small_trade": 0.003,
    "caregiving": 0.001,
    "productive_confidence": 0.004,
    "market_activity": 0.003,
}

INNOVATION_EVENTS = {
    "rumor_velocity": 0.003,
    "productive_confidence": 0.005,
    "small_trade": 0.001,
}


def ensure_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS capital_pool (
            world_id TEXT PRIMARY KEY,
            stock REAL NOT NULL DEFAULT 0.5,
            gdp_flow REAL NOT NULL DEFAULT 0.0,
            investment_rate REAL NOT NULL DEFAULT 0.3,
            tech_level REAL NOT NULL DEFAULT 0.1,
            innovation_stock REAL NOT NULL DEFAULT 0.0,
            updated_at REAL NOT NULL
        );
    """)


def _ensure_row(db, world_id: str) -> None:
    now = time.time()
    db.execute(
        "INSERT OR IGNORE INTO capital_pool (world_id, stock, gdp_flow, investment_rate, tech_level, innovation_stock, updated_at) VALUES (?, 0.5, 0.0, 0.3, 0.1, 0.0, ?)",
        (world_id, now),
    )


def latest_capital(db, world_id: str) -> dict:
    ensure_schema(db)
    _ensure_row(db, world_id)
    row = db.execute(
        "SELECT stock, gdp_flow, investment_rate, tech_level, innovation_stock FROM capital_pool WHERE world_id=?",
        (world_id,),
    ).fetchone()
    return {
        "stock": float(row["stock"]),
        "gdp_flow": float(row["gdp_flow"]),
        "investment_rate": float(row["investment_rate"]),
        "tech_level": float(row["tech_level"]),
        "innovation_stock": float(row["innovation_stock"]),
    }


def compute_gdp_proxy(db, world_id: str) -> float:
    cap = latest_capital(db, world_id)
    raw = cap["stock"] * 0.75 + cap["innovation_stock"] * cap["tech_level"] * 0.50
    # Clamp but allow values to escape basin floor
    return max(0.0, min(1.0, raw))


def apply_capital_flows(db, *, world_id: str, tick_number: int) -> str:
    ensure_schema(db)
    _ensure_row(db, world_id)
    cap = latest_capital(db, world_id)
    state = macro_dynamics.latest_state(db, world_id)
    now = time.time()

    # Count productive events this tick
    placeholders = ",".join("?" * len(PRODUCTIVE_EVENTS))
    event_types = tuple(PRODUCTIVE_EVENTS.keys())
    rows = db.execute(
        f"SELECT event_type, COUNT(*) AS cnt FROM causal_events WHERE world_id=? AND tick_number=? AND event_type IN ({placeholders}) GROUP BY event_type",
        (world_id, tick_number, *event_types),
    ).fetchall()

    gdp_flow = 0.0
    for row in rows:
        multiplier = PRODUCTIVE_EVENTS.get(row["event_type"], 0.0)
        gdp_flow += int(row["cnt"]) * multiplier

    # Innovation from innovation-causing events
    innov_placeholders = ",".join("?" * len(INNOVATION_EVENTS))
    innov_types = tuple(INNOVATION_EVENTS.keys())
    innov_rows = db.execute(
        f"SELECT event_type, COUNT(*) AS cnt FROM causal_events WHERE world_id=? AND tick_number=? AND event_type IN ({innov_placeholders}) GROUP BY event_type",
        (world_id, tick_number, *innov_types),
    ).fetchall()

    innovation_gain = 0.0
    for row in innov_rows:
        multiplier = INNOVATION_EVENTS.get(row["event_type"], 0.0)
        innovation_gain += int(row["cnt"]) * multiplier

    # Investment rate from macro conditions
    investment_rate = (
        state.get("legitimacy", 0.5) * 0.45
        + state.get("fiscal_capacity", 0.5) * 0.35
        + (1.0 - state.get("war_pressure", 0.0)) * 0.20
    )
    investment_rate = max(0.05, min(0.95, investment_rate))

    # Capital accumulation with war decay
    war_pressure = state.get("war_pressure", 0.0)
    repression = state.get("repression", 0.3)
    decay = cap["stock"] * max(0.0, war_pressure * 0.025 + repression * 0.005)

    new_stock = cap["stock"] + gdp_flow * investment_rate - decay
    new_stock = max(0.0, new_stock)

    # Tech progress: very slow but persistent
    tech_growth = innovation_gain * 0.02 if innovation_gain > 0 else 0.0
    new_tech = max(0.05, min(0.50, cap["tech_level"] + tech_growth))

    # Innovation stock accumulation
    new_innovation = max(0.0, cap["innovation_stock"] + innovation_gain - cap["innovation_stock"] * 0.002)

    db.execute(
        """
        INSERT OR REPLACE INTO capital_pool
            (world_id, stock, gdp_flow, investment_rate, tech_level, innovation_stock, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (world_id, new_stock, gdp_flow, investment_rate, new_tech, new_innovation, now),
    )

    magnitude = abs(new_stock - cap["stock"]) + innovation_gain
    event_type = "gdp_growth" if new_stock > cap["stock"] else "gdp_contraction"

    ce = causal_ledger.emit_event(
        db,
        tick_number=tick_number,
        world_id=world_id,
        layer="macro",
        event_type=event_type,
        scope="country",
        magnitude=magnitude,
        valence=0.1 if new_stock > cap["stock"] else -0.1,
        payload={
            "stock": new_stock,
            "gdp_flow": gdp_flow,
            "investment_rate": investment_rate,
            "decay": decay,
            "innovation_gain": innovation_gain,
            "delta": new_stock - cap["stock"],
        },
    )
    return ce
