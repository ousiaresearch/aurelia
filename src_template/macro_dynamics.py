"""macro_dynamics.py — country-level state vector and feedback."""
from __future__ import annotations

import json
import time

try:
    from . import causal_ledger
except Exception:
    import causal_ledger

DEFAULT_STATE = {
    "gdp_proxy": 0.55,
    "inequality": 0.45,
    "food_security": 0.60,
    "water_security": 0.60,
    "public_health": 0.70,
    "legitimacy": 0.55,
    "repression": 0.30,
    "fiscal_capacity": 0.50,
    "infrastructure": 0.60,
    "border_openness": 0.50,
    "type_tension": 0.30,
    "war_pressure": 0.00,
}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def ensure_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS macro_state (
            world_id TEXT NOT NULL,
            tick_number INTEGER NOT NULL,
            state TEXT NOT NULL,
            created_at REAL NOT NULL,
            PRIMARY KEY(world_id, tick_number)
        );
    """)


def latest_state(db, world_id: str) -> dict[str, float]:
    ensure_schema(db)
    row = db.execute(
        "SELECT state FROM macro_state WHERE world_id=? ORDER BY tick_number DESC LIMIT 1",
        (world_id,),
    ).fetchone()
    if not row:
        return dict(DEFAULT_STATE)
    try:
        state = json.loads(row["state"])
    except Exception:
        state = {}
    out = dict(DEFAULT_STATE)
    out.update({k: float(v) for k, v in state.items() if isinstance(v, (int, float))})
    return out


def apply_macro_dynamics(db, *, world_id: str, tick_number: int) -> str:
    """Update macro state from meso signals and due effects; emit macro event."""
    ensure_schema(db)
    state = latest_state(db, world_id)
    rows = db.execute(
        "SELECT signal_type, SUM(magnitude) AS mag FROM meso_signals WHERE world_id=? AND tick_number=? GROUP BY signal_type",
        (world_id, int(tick_number)),
    ).fetchall()
    changes = {k: 0.0 for k in state}

    for row in rows:
        typ = row["signal_type"]
        mag = float(row["mag"] or 0.0)
        if typ == "economic_stress":
            changes["gdp_proxy"] -= mag * 0.05
            changes["legitimacy"] -= mag * 0.03
        elif typ == "labor_unrest":
            changes["legitimacy"] -= mag * 0.05
            changes["war_pressure"] += mag * 0.03
        elif typ == "repression_visibility":
            changes["repression"] += mag * 0.04
            changes["legitimacy"] -= mag * 0.04
            changes["type_tension"] += mag * 0.02
        elif typ == "public_health_risk":
            changes["public_health"] -= mag * 0.04
        elif typ == "migration_pressure":
            changes["border_openness"] -= mag * 0.01
            changes["legitimacy"] -= mag * 0.02
        elif typ == "social_solidarity":
            changes["legitimacy"] += mag * 0.02
            changes["public_health"] += mag * 0.01
        elif typ == "productive_confidence":
            changes["gdp_proxy"] += mag * 0.02
        elif typ == "market_activity":
            changes["gdp_proxy"] += mag * 0.015

    for effect in causal_ledger.due_effects(db, tick_number, world_id):
        et = effect["effect_type"]
        mag = float(effect["magnitude"] or 0.0)
        if et == "trade_shock":
            changes["gdp_proxy"] -= mag
            changes["food_security"] -= mag * 0.25
        elif et == "refugee_inflow":
            changes["border_openness"] -= mag * 0.2
            changes["fiscal_capacity"] -= mag * 0.1
        elif et == "ideology_diffusion":
            changes["war_pressure"] += mag * 0.1
            changes["legitimacy"] -= mag * 0.05
        elif et == "recognition_pressure":
            changes["legitimacy"] -= mag * 0.03
        causal_ledger.mark_effect_applied(db, effect["effect_id"])

    # gentle mean reversion so state does not saturate too quickly
    for key, baseline in DEFAULT_STATE.items():
        state[key] = _clamp(state[key] + changes[key] + (baseline - state[key]) * 0.002)

    db.execute(
        "INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        (world_id, int(tick_number), json.dumps(state, sort_keys=True), time.time()),
    )
    magnitude = sum(abs(v) for v in changes.values())
    return causal_ledger.emit_event(
        db,
        tick_number=tick_number,
        world_id=world_id,
        layer="macro",
        event_type="macro_state_update",
        scope="country",
        magnitude=magnitude,
        valence=(state["legitimacy"] + state["gdp_proxy"] + state["public_health"]) / 3.0 - 0.5,
        payload={"state": state, "changes": changes},
    )
