"""capital_economy.py — Phase 9 value creation through productive activity.

Capital economy converts micro-level productive events (work success, trade,
caregiving, productive confidence) into persistent capital stock. This breaks
the Phase 8 single-attractor collapse by giving the system a way to *create*
value, not just shuffle or destroy it.

Capital stock accumulates from GDP flow, modulated by investment rate. It
decays under war pressure and repression. Innovation stock grows from
rumor velocity and tech level. GDP proxy becomes a derived quantity from
capital + innovation rather than an independent variable.
"""
from __future__ import annotations

import json
import time

try:
    from . import causal_ledger, macro_dynamics
except Exception:
    import causal_ledger
    import macro_dynamics

# Micro events that contribute to GDP flow, with per-event yield
PRODUCTIVE_EVENTS = {
    "work_success": 0.002,
    "small_trade": 0.003,
    "caregiving": 0.001,
    "productive_confidence": 0.0015,
    "work_failure": -0.0008,  # small drag, not a full loss
}

INNOVATION_EVENTS = {
    "rumor_velocity": 0.0008,
    "rumor_transmission": 0.0002,
    "productive_confidence": 0.0005,
}

# Macro conditions that drain capital
DECAY_PER_TICK = {
    "war_pressure": 0.030,
    "repression": 0.015,
    "type_tension": 0.010,
}


def ensure_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS capital_pool (
            world_id TEXT PRIMARY KEY,
            stock REAL NOT NULL DEFAULT 0.5,
            gdp_flow REAL NOT NULL DEFAULT 0.0,
            investment_rate REAL NOT NULL DEFAULT 0.0,
            tech_level REAL NOT NULL DEFAULT 0.1,
            innovation_stock REAL NOT NULL DEFAULT 0.0,
            updated_at REAL NOT NULL
        );
    """)


def seed_pool(db, world_id: str, *, stock: float = 0.5, innovation: float = 0.0, tech: float = 0.1) -> None:
    ensure_schema(db)
    db.execute(
        """INSERT OR IGNORE INTO capital_pool
            (world_id, stock, gdp_flow, investment_rate, tech_level, innovation_stock, updated_at)
            VALUES (?, ?, 0.0, 0.0, ?, ?, ?)""",
        (world_id, stock, tech, innovation, time.time()),
    )
    db.commit()


def get_pool(db, world_id: str) -> dict:
    ensure_schema(db)
    row = db.execute(
        "SELECT * FROM capital_pool WHERE world_id=?", (world_id,)
    ).fetchone()
    if row is None:
        # Initialize with defaults
        seed_pool(db, world_id)
        row = db.execute(
            "SELECT * FROM capital_pool WHERE world_id=?", (world_id,)
        ).fetchone()
    return {
        "world_id": row["world_id"],
        "stock": float(row["stock"]),
        "gdp_flow": float(row["gdp_flow"]),
        "investment_rate": float(row["investment_rate"]),
        "tech_level": float(row["tech_level"]),
        "innovation_stock": float(row["innovation_stock"]),
    }


def compute_investment_rate(db, world_id: str) -> float:
    """Investment rate driven by legitimacy and fiscal capacity."""
    try:
        state = macro_dynamics.latest_state(db, world_id)
    except Exception:
        return 0.0
    legitimacy = state.get("legitimacy", 0.5)
    fiscal = state.get("fiscal_capacity", 0.5)
    return legitimacy * 0.6 + fiscal * 0.4


def _event_counts(db, world_id: str, tick_number: int) -> dict[str, int]:
    """Count micro events for a world at a tick."""
    try:
        rows = db.execute(
            """SELECT event_type, COUNT(*) AS c FROM causal_events
               WHERE world_id=? AND tick_number=? AND event_type IN (
                   'work_success','small_trade','caregiving','productive_confidence',
                   'work_failure','rumor_velocity','rumor_transmission'
               )
               GROUP BY event_type""",
            (world_id, int(tick_number)),
        ).fetchall()
        return {r["event_type"]: int(r["c"]) for r in rows}
    except Exception:
        return {}


def _macro_state(db, world_id: str) -> dict:
    try:
        return macro_dynamics.latest_state(db, world_id)
    except Exception:
        return {}


def gdp_proxy_for(db, world_id: str) -> float:
    """GDP proxy derived from capital stock + innovation * tech."""
    pool = get_pool(db, world_id)
    return min(1.0, max(0.0, pool["stock"] + pool["innovation_stock"] * pool["tech_level"]))


def apply_capital_flows(db, *, world_id: str, tick_number: int) -> str | None:
    """Apply one tick of capital economy dynamics. Emit causal events."""
    ensure_schema(db)
    pool = get_pool(db, world_id)
    state = _macro_state(db, world_id)

    # 1. Count productive events and compute GDP flow
    counts = _event_counts(db, world_id, tick_number)
    gdp_flow = 0.0
    for et, yield_ in PRODUCTIVE_EVENTS.items():
        gdp_flow += counts.get(et, 0) * yield_

    # 2. Innovation accumulates from rumour velocity and tech
    innovation_gain = 0.0
    for et, yield_ in INNOVATION_EVENTS.items():
        innovation_gain += counts.get(et, 0) * yield_
    innovation_gain *= (1.0 + pool["tech_level"])

    # 3. Investment rate from macro
    investment_rate = compute_investment_rate(db, world_id)

    # 4. Capital formation: flow * (1 - war_dampening) * investment_rate
    war_pressure = state.get("war_pressure", 0.0)
    repression = state.get("repression", 0.3)
    formation_factor = max(0.0, 1.0 - war_pressure * 0.7 - repression * 0.15)
    capital_formation = gdp_flow * formation_factor * max(investment_rate, 0.10)

    # 5. Capital decay from war, repression, type tension
    decay = pool["stock"] * (
        war_pressure * DECAY_PER_TICK["war_pressure"]
        + repression * DECAY_PER_TICK["repression"]
        + state.get("type_tension", 0.3) * DECAY_PER_TICK["type_tension"]
    )

    new_stock = max(0.0, min(1.0, pool["stock"] + capital_formation - decay))
    new_innovation = max(0.0, min(1.0, pool["innovation_stock"] + innovation_gain))

    # 6. Tech level slowly rises with innovation stock
    new_tech = min(1.0, pool["tech_level"] + new_innovation * 0.002)

    db.execute(
        """UPDATE capital_pool SET
            stock=?, gdp_flow=?, investment_rate=?, tech_level=?, innovation_stock=?, updated_at=?
           WHERE world_id=?""",
        (new_stock, gdp_flow, investment_rate, new_tech, new_innovation, time.time(), world_id),
    )
    db.commit()

    # 7. Emit causal events for significant changes
    event_id = None
    if abs(capital_formation) > 0.001:
        event_type = "capital_formation" if capital_formation > 0 else "capital_decay"
        event_id = causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="meso",
            event_type=event_type,
            scope="country",
            magnitude=abs(capital_formation),
            valence=capital_formation,
            payload={"stock": new_stock, "gdp_flow": gdp_flow, "investment_rate": investment_rate},
        )
    if innovation_gain > 0.002:
        causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="meso",
            event_type="innovation_gain",
            scope="country",
            magnitude=innovation_gain,
            valence=innovation_gain,
            payload={"innovation_stock": new_innovation, "tech_level": new_tech},
        )
    # GDP trend event for long-term tracking
    if new_stock > pool["stock"] * 1.10:
        causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="meso",
            event_type="gdp_growth",
            scope="country",
            magnitude=new_stock - pool["stock"],
            valence=0.4,
            payload={"delta": new_stock - pool["stock"]},
        )
    elif new_stock < pool["stock"] * 0.90 and new_stock < 0.20:
        causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="meso",
            event_type="gdp_contraction",
            scope="country",
            magnitude=pool["stock"] - new_stock,
            valence=-0.5,
            payload={"delta": new_stock - pool["stock"]},
        )
    return event_id
