"""macro_dynamics.py — country-level state vector and feedback."""
from __future__ import annotations

import json
import time

try:
    from . import causal_ledger, world_profiles
except Exception:
    import causal_ledger
    import world_profiles

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

SHOCK_CAPS = {
    "gdp_proxy": 0.020,
    "food_security": 0.018,
    "water_security": 0.012,
    "public_health": 0.018,
    "legitimacy": 0.020,
    "repression": 0.018,
    "fiscal_capacity": 0.015,
    "infrastructure": 0.010,
    "border_openness": 0.018,
    "type_tension": 0.018,
    "war_pressure": 0.020,
    "inequality": 0.010,
}

RECOVERABLE_KEYS = {"gdp_proxy", "food_security", "water_security", "public_health", "legitimacy", "fiscal_capacity", "infrastructure", "border_openness"}
TENSION_KEYS = {"repression", "type_tension", "war_pressure", "inequality"}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _cap_delta(key: str, delta: float) -> float:
    cap = SHOCK_CAPS.get(key, 0.015)
    return max(-cap, min(cap, float(delta)))


def baseline_state(world_id: str) -> dict[str, float]:
    out = dict(DEFAULT_STATE)
    try:
        out.update(world_profiles.macro_baseline(world_id))
    except Exception:
        pass
    return out


def _recovery_delta(key: str, state: dict[str, float], baseline: dict[str, float], resilience: dict) -> float:
    rate = float(resilience.get("recovery_rate", 0.010))
    if key == "public_health":
        rate += float(resilience.get("health_resilience", 0.0))
    elif key == "food_security":
        rate += float(resilience.get("food_resilience", 0.0))
    elif key == "fiscal_capacity":
        rate += float(resilience.get("fiscal_resilience", 0.0))

    if key in RECOVERABLE_KEYS:
        if state.get(key, 0.0) >= baseline.get(key, 0.0):
            return 0.0
        governance = max(
            0.0,
            state.get("fiscal_capacity", 0.5) * 0.45
            + state.get("legitimacy", 0.5) * 0.35
            + (1.0 - state.get("repression", 0.3)) * 0.20
            - state.get("war_pressure", 0.0) * 0.25,
        )
        return (baseline[key] - state[key]) * rate * governance

    if key in TENSION_KEYS:
        if state.get(key, 0.0) <= baseline.get(key, 0.0):
            return 0.0
        civic = max(
            0.0,
            state.get("legitimacy", 0.5) * 0.40
            + state.get("public_health", 0.6) * 0.20
            + state.get("gdp_proxy", 0.5) * 0.20
            + (1.0 - state.get("repression", 0.3)) * 0.20,
        )
        return -(state[key] - baseline[key]) * rate * civic
    return 0.0


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
    baseline = baseline_state(world_id)
    row = db.execute(
        "SELECT state FROM macro_state WHERE world_id=? ORDER BY tick_number DESC LIMIT 1",
        (world_id,),
    ).fetchone()
    if not row:
        return baseline
    try:
        state = json.loads(row["state"])
    except Exception:
        state = {}
    out = dict(baseline)
    out.update({k: float(v) for k, v in state.items() if isinstance(v, (int, float))})
    return out


def _emit_recovery_events(db, *, world_id: str, tick_number: int, recovery: dict[str, float]) -> None:
    for key, delta in recovery.items():
        if abs(delta) < 0.002:
            continue
        event_type = "macro_tension_decay" if delta < 0 and key in TENSION_KEYS else "macro_resilience_recovery"
        causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="macro",
            event_type=event_type,
            scope="country",
            magnitude=abs(delta),
            valence=abs(delta),
            payload={"key": key, "delta": round(delta, 6)},
        )


def apply_macro_dynamics(db, *, world_id: str, tick_number: int) -> str:
    """Update macro state from meso signals and due effects; emit macro event."""
    ensure_schema(db)
    state = latest_state(db, world_id)
    baseline = baseline_state(world_id)
    profile = world_profiles.profile(world_id)
    resilience = profile.get("resilience", {})
    shock_absorption = max(0.0, min(0.95, float(resilience.get("shock_absorption", 0.5))))

    try:
        rows = db.execute(
            "SELECT signal_type, SUM(magnitude) AS mag FROM meso_signals WHERE world_id=? AND tick_number=? GROUP BY signal_type",
            (world_id, int(tick_number)),
        ).fetchall()
    except Exception:
        rows = []
    raw_changes = {k: 0.0 for k in state}

    for row in rows:
        typ = row["signal_type"]
        mag = float(row["mag"] or 0.0)
        if typ == "economic_stress":
            raw_changes["gdp_proxy"] -= mag * 0.05
            raw_changes["legitimacy"] -= mag * 0.03
        elif typ == "labor_unrest":
            raw_changes["legitimacy"] -= mag * 0.05
            raw_changes["war_pressure"] += mag * 0.03
        elif typ == "repression_visibility":
            raw_changes["repression"] += mag * 0.04
            raw_changes["legitimacy"] -= mag * 0.04
            raw_changes["type_tension"] += mag * 0.02
        elif typ == "public_health_risk":
            raw_changes["public_health"] -= mag * 0.04
        elif typ == "migration_pressure":
            raw_changes["border_openness"] -= mag * 0.01
            raw_changes["legitimacy"] -= mag * 0.02
        elif typ == "social_solidarity":
            raw_changes["legitimacy"] += mag * 0.02
            raw_changes["public_health"] += mag * 0.01
        elif typ == "productive_confidence":
            raw_changes["gdp_proxy"] += mag * 0.02
        elif typ == "market_activity":
            raw_changes["gdp_proxy"] += mag * 0.015
        elif typ.startswith("faction_outcome:"):
            outcome = typ.split(":", 1)[1]
            if outcome in {"integrated", "legalized", "governing_coalition", "victorious"}:
                raw_changes["legitimacy"] += mag * 0.018
                raw_changes["repression"] -= mag * 0.010
                raw_changes["war_pressure"] -= mag * 0.010
            elif outcome in {"suppressed", "radicalized", "splintered", "exiled"}:
                raw_changes["war_pressure"] += mag * 0.018
                raw_changes["legitimacy"] -= mag * 0.010
                raw_changes["repression"] += mag * 0.008

    for effect in causal_ledger.due_effects(db, tick_number, world_id):
        et = effect["effect_type"]
        mag = float(effect["magnitude"] or 0.0)
        if et in {"refugee_inflow", "labor_inflow", "refugee_outflow", "labor_outflow"}:
            # Migration flow module consumes these; keep macro from marking them here.
            continue
        if et == "trade_shock":
            raw_changes["gdp_proxy"] -= mag
            raw_changes["food_security"] -= mag * 0.25
        elif et == "ideology_diffusion":
            raw_changes["war_pressure"] += mag * 0.1
            raw_changes["legitimacy"] -= mag * 0.05
        elif et == "recognition_pressure":
            raw_changes["legitimacy"] -= mag * 0.03
        elif et == "disease_alert":
            raw_changes["public_health"] -= mag * 0.06
        elif et in {"refugee_outflow", "labor_outflow", "labor_inflow"}:
            # Migration flow module consumes these; keep macro from marking them here.
            continue
        causal_ledger.mark_effect_applied(db, effect["effect_id"])

    capped_changes = {}
    recovery = {}
    for key in baseline:
        absorbed = raw_changes.get(key, 0.0) * (1.0 - shock_absorption)
        capped = _cap_delta(key, absorbed)
        capped_changes[key] = capped
        intermediate = _clamp(state.get(key, baseline[key]) + capped)
        tmp_state = dict(state)
        tmp_state[key] = intermediate
        rec = _recovery_delta(key, tmp_state, baseline, resilience)
        recovery[key] = rec
        state[key] = _clamp(intermediate + rec)

    _emit_recovery_events(db, world_id=world_id, tick_number=tick_number, recovery=recovery)

    db.execute(
        "INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        (world_id, int(tick_number), json.dumps(state, sort_keys=True), time.time()),
    )
    magnitude = sum(abs(v) for v in capped_changes.values()) + sum(abs(v) for v in recovery.values())
    return causal_ledger.emit_event(
        db,
        tick_number=tick_number,
        world_id=world_id,
        layer="macro",
        event_type="macro_state_update",
        scope="country",
        magnitude=magnitude,
        valence=(state["legitimacy"] + state["gdp_proxy"] + state["public_health"]) / 3.0 - 0.5,
        payload={"state": state, "changes": capped_changes, "raw_changes": raw_changes, "recovery": recovery},
    )
