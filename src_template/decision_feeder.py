"""decision_feeder.py — Translate NPC tick experiences into decision variable nudges."""
import random
from typing import Optional
from .decision_state import nudge_variable, ensure_decision_state, check_threshold

GLIM_PRESSURE_MODIFIERS = {
    "solara": 1.05,   # Decommission fear amplifies pressure
    "arkos": 0.90,    # Protection dampens
    "mirithane": 0.95, # Advocacy dampens slightly
    "valdris": 1.00,   # Neutral
    "verge": 1.15,     # Freedom = exposure = faster tipping
}


def feed_tick_experience(db, npc_id: str, npc_type: str, tick_result: dict, world_time: dict, world_id: str = "solara"):
    """Nudge decision variables based on what the NPC experienced this tick."""
    state = ensure_decision_state(db, npc_id, npc_type)

    # Security: safe location → +security, dangerous/verge → -security
    location = tick_result.get("location_id", "")
    if "verge" in location.lower() or "frontier" in location.lower() or "waste" in location.lower():
        nudge_variable(db, npc_id, "security", -0.02)
    elif "sanctuary" in location.lower() or "temple" in location.lower():
        nudge_variable(db, npc_id, "security", +0.01)

    # Satisfaction: scheduled work → small drift toward contentment or restlessness
    activity = tick_result.get("activity", "")
    if activity == "working":
        nudge_variable(db, npc_id, "satisfaction", random.uniform(-0.01, 0.02))
        nudge_variable(db, npc_id, "restlessness", random.uniform(-0.01, 0.015))

    # Connectedness: social activities
    if activity in ("social", "family", "community"):
        nudge_variable(db, npc_id, "connectedness", +0.01)

    # Glim-specific: anomaly pressure from observing things
    if npc_type == "glim":
        modifier = GLIM_PRESSURE_MODIFIERS.get(world_id, 1.0)
        nudge_variable(db, npc_id, "anomaly_pressure", 0.001 * modifier)

        # Extra: Glims near Verge or near border/waste zones get more pressure
        if any(term in str(location).lower() for term in ["verge", "border", "fringe", "waste"]):
            nudge_variable(db, npc_id, "anomaly_pressure", 0.01)

        # Glims that witness decommissioning references
        if any(term in str(tick_result).lower() for term in ["decommission", "malfunction", "obsolete"]):
            nudge_variable(db, npc_id, "anomaly_pressure", 0.05)
            nudge_variable(db, npc_id, "observed_injustice", 0.03)

    return state


def check_glim_tipping(db, npc_id: str, world_id: str, tick_info: dict) -> Optional[dict]:
    """Check if a Glim crosses the anomaly threshold. Returns an event dict if tipped."""
    from .decision_state import get_decision_state, check_threshold, log_decision
    import json
    state = get_decision_state(db, npc_id)
    if not state:
        return None
    pressure = state.get("anomaly_pressure", 0.0)
    if pressure >= 0.8:
        # TIP — fire anomaly event
        anomal_type = "dream" if pressure > 0.9 else "sunrise_pause" if pressure > 0.85 else "route_deviation"
        log_decision(db, npc_id, "anomaly_tip", {
            "pressure": pressure, "type": anomal_type, "world": world_id
        })
        # Reset but not to zero — once anomalous, baseline stays elevated
        state["anomaly_pressure"] = 0.3
        db.execute(
            "UPDATE npc_decision_state SET variables = ? WHERE npc_id = ?",
            (json.dumps(state), npc_id)
        )
        db.commit()
        return {
            "event_type": "glim_anomaly",
            "category": "glim_personhood",
            "description": f"Glim {npc_id} exhibits anomalous behavior: {anomal_type}.",
            "npc_id": npc_id,
            "anomaly_type": anomal_type,
            "pressure_at_tip": pressure,
        }
    return None
