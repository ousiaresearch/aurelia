"""regime_transitions.py — collapse recovery and regime change pathways."""
from __future__ import annotations

import json
import random
import time
import uuid

try:
    from . import causal_ledger, macro_dynamics, world_profiles
except Exception:
    import causal_ledger
    import macro_dynamics
    import world_profiles

RESOLUTION_PATHS = [
    "elite_defection",
    "popular_uprising",
    "external_intervention",
    "reform_from_within",
    "terminal_collapse",
]

CRISIS_TRIGGER_CONSECUTIVE_TICKS = 3
GDP_CRISIS_THRESHOLD = 0.05
LEGITIMACY_CRISIS_THRESHOLD = 0.10
POST_COLLAPSE_REVIVAL_CHANCE = 0.02  # per decade


def ensure_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS regime_events (
            event_id TEXT PRIMARY KEY,
            world_id TEXT NOT NULL,
            tick_number INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            from_regime TEXT,
            to_regime TEXT,
            resolution_path TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL
        );
    """)


def _in_crisis(state: dict) -> bool:
    return state.get("gdp_proxy", 0.5) < GDP_CRISIS_THRESHOLD and state.get("legitimacy", 0.5) < LEGITIMACY_CRISIS_THRESHOLD


def _consecutive_crisis_ticks(db, world_id: str, current_tick: int) -> int:
    """Count how many consecutive recent ticks have been in crisis."""
    rows = db.execute(
        "SELECT state FROM macro_state WHERE world_id=? AND tick_number <= ? ORDER BY tick_number DESC LIMIT ?",
        (world_id, current_tick, CRISIS_TRIGGER_CONSECUTIVE_TICKS),
    ).fetchall()
    count = 0
    for row in rows:
        try:
            state = json.loads(row["state"])
        except Exception:
            state = {}
        if _in_crisis(state):
            count += 1
        else:
            break
    return count


def _path_weights(db, state: dict, world_id: str) -> dict[str, float]:
    """Compute probability weights for resolution paths based on macro conditions."""
    w = {}
    w["elite_defection"] = (
        0.25
        + state.get("repression", 0.3) * 0.25
        + (1.0 - state.get("legitimacy", 0.5)) * 0.15
        + state.get("type_tension", 0.3) * 0.10
    )
    w["popular_uprising"] = (
        0.15
        + state.get("type_tension", 0.3) * 0.30
        + state.get("war_pressure", 0.0) * 0.20
        + state.get("repression", 0.3) * 0.10
    )
    w["external_intervention"] = (
        0.10
        + state.get("border_openness", 0.5) * 0.35
        + (1.0 - state.get("repression", 0.3)) * 0.10
    )
    w["reform_from_within"] = (
        0.20
        + (1.0 - state.get("repression", 0.3)) * 0.25
        + state.get("legitimacy", 0.3) * 0.10
        + state.get("fiscal_capacity", 0.3) * 0.10
    )
    w["terminal_collapse"] = 0.30

    # Boost reform if legalized factions exist
    try:
        has_legalized = db.execute(
            "SELECT COUNT(*) FROM factions WHERE world_id=? AND status='legalized'",
            (world_id,),
        ).fetchone()[0]
        if has_legalized > 0:
            w["reform_from_within"] += 0.20
            w["terminal_collapse"] -= 0.10
    except Exception:
        pass

    # Boost external intervention if border is open
    if state.get("border_openness", 0.5) > 0.5:
        w["external_intervention"] += 0.15

    return {k: max(0.01, v) for k, v in w.items()}


def _weighted_path(weights: dict, rng: random.Random) -> str:
    total = sum(weights.values())
    roll = rng.random() * total
    acc = 0.0
    for path, w in sorted(weights.items()):
        acc += w
        if roll <= acc:
            return path
    return "terminal_collapse"


def _resolve_elite_defection(db, *, world_id: str, tick_number: int, rng: random.Random) -> dict:
    """Regime falls, new leadership with reset legitimacy but low fiscal capacity."""
    new_legitimacy = 0.35 + rng.random() * 0.15  # 0.35–0.50
    new_gdp = 0.10 + rng.random() * 0.10  # 0.10–0.20
    state = _apply_reset(db, world_id, tick_number, {
        "legitimacy": new_legitimacy,
        "gdp_proxy": new_gdp,
        "repression": 0.25 + rng.random() * 0.15,
        "war_pressure": max(0.05, state_current(db, world_id).get("war_pressure", 0.9) * 0.3),
        "fiscal_capacity": 0.15,
    })
    causal_ledger.emit_event(db, tick_number=tick_number, world_id=world_id, layer="macro",
                             event_type="elite_defection", scope="country", magnitude=0.8, valence=0.1,
                             payload={"new_legitimacy": new_legitimacy, "new_gdp": new_gdp})
    return state


def _resolve_popular_uprising(db, *, world_id: str, tick_number: int, rng: random.Random) -> dict:
    new_legitimacy = 0.50 + rng.random() * 0.15  # 0.50–0.65
    new_gdp = 0.05 + rng.random() * 0.05  # 0.05–0.10 (economy wrecked)
    state = _apply_reset(db, world_id, tick_number, {
        "legitimacy": new_legitimacy,
        "gdp_proxy": new_gdp,
        "war_pressure": 0.90 + rng.random() * 0.10,
        "repression": 0.10,
    })
    causal_ledger.emit_event(db, tick_number=tick_number, world_id=world_id, layer="macro",
                             event_type="popular_uprising", scope="country", magnitude=1.0, valence=0.05,
                             payload={"new_legitimacy": new_legitimacy, "new_gdp": new_gdp})
    return state


def _resolve_external_intervention(db, *, world_id: str, tick_number: int, rng: random.Random) -> dict:
    new_legitimacy = 0.40 + rng.random() * 0.15  # 0.40–0.55
    new_gdp = 0.25 + rng.random() * 0.15  # 0.25–0.40
    state = _apply_reset(db, world_id, tick_number, {
        "legitimacy": new_legitimacy,
        "gdp_proxy": new_gdp,
        "repression": 0.20,
        "war_pressure": 0.10,
        "border_openness": 0.70,
        "type_tension": state_current(db, world_id).get("type_tension", 0.3) + 0.15,
    })
    causal_ledger.emit_event(db, tick_number=tick_number, world_id=world_id, layer="macro",
                             event_type="external_intervention", scope="country", magnitude=0.7, valence=0.3,
                             payload={"new_legitimacy": new_legitimacy, "new_gdp": new_gdp})
    return state


def _resolve_reform_from_within(db, *, world_id: str, tick_number: int, rng: random.Random) -> dict:
    current = state_current(db, world_id)
    new_legitimacy = current.get("legitimacy", 0.05) + 0.12
    new_gdp = current.get("gdp_proxy", 0.03) + 0.08
    state = _apply_reset(db, world_id, tick_number, {
        "legitimacy": min(1.0, new_legitimacy),
        "gdp_proxy": min(1.0, new_gdp),
        "repression": max(0.0, current.get("repression", 0.5) - 0.15),
        "war_pressure": max(0.0, current.get("war_pressure", 0.5) - 0.10),
    })
    causal_ledger.emit_event(db, tick_number=tick_number, world_id=world_id, layer="macro",
                             event_type="reform_from_within", scope="country", magnitude=0.5, valence=0.4,
                             payload={"new_legitimacy": new_legitimacy, "new_gdp": new_gdp})
    return state


def _resolve_terminal_collapse(db, *, world_id: str, tick_number: int, rng: random.Random) -> dict:
    state = _apply_reset(db, world_id, tick_number, {
        "legitimacy": 0.0,
        "gdp_proxy": 0.0,
        "repression": 0.99,
        "war_pressure": 0.99,
        "border_openness": 0.01,
        "fiscal_capacity": 0.0,
    })
    causal_ledger.emit_event(db, tick_number=tick_number, world_id=world_id, layer="macro",
                             event_type="terminal_collapse", scope="country", magnitude=1.0, valence=-0.8,
                             payload={"post_collapse": True})
    return state


def _check_post_collapse_revival(db, *, world_id: str, tick_number: int, rng: random.Random) -> bool:
    """Check for bottom-up reorganization after terminal collapse."""
    if rng.random() >= POST_COLLAPSE_REVIVAL_CHANCE:
        return False
    _apply_reset(db, world_id, tick_number, {
        "legitimacy": 0.20 + rng.random() * 0.10,
        "gdp_proxy": 0.10 + rng.random() * 0.10,
        "repression": 0.40,
        "war_pressure": 0.30,
        "fiscal_capacity": 0.10,
        "border_openness": 0.20,
    })
    causal_ledger.emit_event(db, tick_number=tick_number, world_id=world_id, layer="macro",
                             event_type="bottom_up_revival", scope="country", magnitude=0.6, valence=0.5,
                             payload={"from_post_collapse": True})
    return True


RESOLVERS = {
    "elite_defection": _resolve_elite_defection,
    "popular_uprising": _resolve_popular_uprising,
    "external_intervention": _resolve_external_intervention,
    "reform_from_within": _resolve_reform_from_within,
    "terminal_collapse": _resolve_terminal_collapse,
}


def state_current(db, world_id: str) -> dict[str, float]:
    return macro_dynamics.latest_state(db, world_id)


def _apply_reset(db, world_id: str, tick_number: int, overrides: dict) -> dict[str, float]:
    current = state_current(db, world_id)
    current.update(overrides)
    db.execute(
        "INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        (world_id, tick_number, json.dumps(current, sort_keys=True), time.time()),
    )
    return current


def check_and_resolve_crisis(db, *, world_id: str, tick_number: int, rng: random.Random) -> dict | None:
    ensure_schema(db)
    state = state_current(db, world_id)

    # Check if already in post-collapse
    post_collapse = db.execute(
        "SELECT COUNT(*) FROM regime_events WHERE world_id=? AND resolution_path='terminal_collapse'",
        (world_id,),
    ).fetchone()[0]
    if post_collapse > 0:
        # Check for revival chance (only check roughly every 10 ticks to simulate per-decade)
        last_revival = db.execute(
            "SELECT MAX(tick_number) FROM regime_events WHERE world_id=? AND event_type='bottom_up_revival'",
            (world_id,),
        ).fetchone()[0]
        if not last_revival or tick_number - last_revival >= 10:
            _check_post_collapse_revival(db, world_id=world_id, tick_number=tick_number, rng=rng)
        return None

    if not _in_crisis(state):
        return None

    consecutive = _consecutive_crisis_ticks(db, world_id, tick_number)
    if consecutive < CRISIS_TRIGGER_CONSECUTIVE_TICKS:
        return None

    # Trigger crisis
    weights = _path_weights(db, state, world_id)
    path = _weighted_path(weights, rng)

    # Record the trigger event
    event_id = f"regime:{world_id}:{tick_number}:{uuid.uuid4().hex[:6]}"
    db.execute(
        "INSERT INTO regime_events (event_id, world_id, tick_number, event_type, resolution_path, payload, created_at) VALUES (?, ?, ?, 'regime_crisis_triggered', ?, ?, ?)",
        (event_id, world_id, tick_number, path, json.dumps({"trigger_tick": tick_number}), time.time()),
    )

    causal_ledger.emit_event(db, tick_number=tick_number, world_id=world_id, layer="macro",
                             event_type="regime_crisis_triggered", scope="country", magnitude=1.0, valence=-0.5,
                             payload={"resolution_path": path, "weights": {k: round(v, 3) for k, v in weights.items()}})

    # Resolve
    resolver = RESOLVERS.get(path, _resolve_terminal_collapse)
    resolver(db, world_id=world_id, tick_number=tick_number, rng=rng)

    # Record resolution
    db.execute(
        "INSERT INTO regime_events (event_id, world_id, tick_number, event_type, resolution_path, payload, created_at) VALUES (?, ?, ?, 'regime_crisis_resolved', ?, ?, ?)",
        (f"{event_id}:res", world_id, tick_number, path, json.dumps({"resolution_path": path}), time.time()),
    )

    return {"triggered": True, "resolution": path}
