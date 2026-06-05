"""decision_state.py — Mutable NPC decision variables that accumulate pressure."""
import json
import time
from typing import Dict, Any, Optional

# Variable names and their default values per type
BASE_STATE = {
    "security": 0.7,            # How safe the NPC feels
    "satisfaction": 0.6,        # Contentment with current life
    "connectedness": 0.5,       # Social bonds strength
    "restlessness": 0.2,        # Desire for change
    "ideological_alignment": 0.65,  # Agreement with country's governance
    "economic_stability": 0.55, # Resource security — set by economy wiring (Phase 6.6)
}

GLIM_BASE = {**BASE_STATE, "anomaly_pressure": 0.0, "observed_injustice": 0.0}


def init_decision_state(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS npc_decision_state (
            npc_id TEXT PRIMARY KEY,
            variables JSON NOT NULL DEFAULT '{}',
            last_updated REAL NOT NULL DEFAULT 0,
            decision_log JSON NOT NULL DEFAULT '[]'
        )
    """)
    db.commit()


def get_decision_state(db, npc_id: str) -> Dict[str, float]:
    row = db.execute(
        "SELECT variables FROM npc_decision_state WHERE npc_id = ?", (npc_id,)
    ).fetchone()
    if row:
        return json.loads(row[0])
    return {}


def ensure_decision_state(db, npc_id: str, npc_type: str = "human") -> Dict[str, float]:
    """Initialize decision state for an NPC if it doesn't exist."""
    state = get_decision_state(db, npc_id)
    if not state:
        base = GLIM_BASE if npc_type == "glim" else BASE_STATE
        db.execute(
            "INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated) VALUES (?, ?, ?)",
            (npc_id, json.dumps(base), time.time())
        )
        db.commit()
        return base.copy()
    return state


def nudge_variable(db, npc_id: str, variable: str, delta: float, clamp: bool = True):
    """Adjust a decision variable. Positive delta increases, negative decreases."""
    state = get_decision_state(db, npc_id)
    if not state:
        return
    current = state.get(variable, 0.5)
    new_val = current + delta
    if clamp:
        new_val = max(0.0, min(1.0, new_val))
    state[variable] = new_val
    db.execute(
        "UPDATE npc_decision_state SET variables = ?, last_updated = ? WHERE npc_id = ?",
        (json.dumps(state), time.time(), npc_id)
    )
    db.commit()
    return new_val


def check_threshold(state: Dict[str, float], variable: str, threshold: float, direction: str = "above") -> bool:
    """Return True if variable crosses threshold in specified direction."""
    val = state.get(variable, 0.0)
    if direction == "above":
        return val >= threshold
    return val <= threshold


def log_decision(db, npc_id: str, decision_type: str, details: Dict[str, Any]):
    """Record a decision that was triggered."""
    row = db.execute(
        "SELECT decision_log FROM npc_decision_state WHERE npc_id = ?", (npc_id,)
    ).fetchone()
    log = json.loads(row[0]) if row else []
    log.append({
        "type": decision_type,
        "ts": time.time(),
        "details": details,
    })
    # Keep last 20 decisions
    if len(log) > 20:
        log = log[-20:]
    db.execute(
        "UPDATE npc_decision_state SET decision_log = ? WHERE npc_id = ?",
        (json.dumps(log), npc_id)
    )
    db.commit()
