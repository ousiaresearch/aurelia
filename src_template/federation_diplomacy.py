"""federation_diplomacy.py — trade agreements, aid pacts, sanctions, mutual defense."""
from __future__ import annotations

import json
import time
import uuid

try:
    from . import causal_ledger, cultural_diffusion
except Exception:
    import causal_ledger
    import cultural_diffusion

RELATION_CONDITIONS = {
    "trade_agreement": {"gdp_proxy": 0.20, "border_openness": 0.30},
    "aid_pact": None,  # Special: one world in crisis
    "mutual_defense": {"war_pressure": 0.30},
    "research_cooperation": {"tech_level": 0.15},
    "open_borders": {"refugee_tolerance": 0.50},
    "sanctions": None,  # Special: one world high repression
}

RELATION_EFFECTS = {
    "trade_agreement": {"gdp_proxy": 0.005, "border_openness": 0.002},
    "aid_pact": {},  # Donor/recipient split handled in apply
    "mutual_defense": {"war_pressure": -0.003, "legitimacy": 0.002},
    "research_cooperation": {"innovation_stock": 0.004},
    "open_borders": {"border_openness": 0.003},
    "sanctions": {"gdp_proxy": -0.005},
}

BORDERS = {
    "solara": ["valdris", "arkos"],
    "valdris": ["solara", "mirithane", "verge"],
    "mirithane": ["valdris", "arkos"],
    "arkos": ["solara", "mirithane", "verge"],
    "verge": ["valdris", "arkos"],
}


def ensure_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS diplomatic_relations (
            relation_id TEXT PRIMARY KEY,
            world_a TEXT NOT NULL,
            world_b TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            strength REAL NOT NULL DEFAULT 0.5,
            established_tick INTEGER NOT NULL,
            dissolved_tick INTEGER,
            payload TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS world_macro_snapshot (
            world_id TEXT PRIMARY KEY,
            tick_number INTEGER NOT NULL,
            state TEXT NOT NULL,
            created_at REAL NOT NULL
        );
    """)


def ensure_borders(db, world_a, world_b):
    if world_a not in BORDERS:
        BORDERS[world_a] = []
    if world_b not in BORDERS[world_a]:
        BORDERS[world_a].append(world_b)
    if world_b not in BORDERS:
        BORDERS[world_b] = []
    if world_a not in BORDERS[world_b]:
        BORDERS[world_b].append(world_a)


def seed_world_diplo_state(db, world_id, state, tick_number: int = 0):
    """Store a current macro snapshot for diplomacy evaluation.

    Phase 9 accidentally wrote every snapshot with tick_number=0, which made
    diplomacy time-blind. Phase 10 keeps the live tick so relations can derive
    trust from duration and reports can reconstruct foreign-policy history.
    """
    ensure_schema(db)
    db.execute(
        "INSERT OR REPLACE INTO world_macro_snapshot (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        (world_id, int(tick_number), json.dumps(state, sort_keys=True), time.time()),
    )


def _macro_state(db, world_id):
    row = db.execute(
        "SELECT state FROM world_macro_snapshot WHERE world_id=? ORDER BY tick_number DESC LIMIT 1",
        (world_id,),
    ).fetchone()
    if not row:
        return {}
    try:
        return json.loads(row["state"])
    except Exception:
        return {}


def _in_crisis(state):
    return state.get("gdp_proxy", 0.5) < 0.10 and state.get("legitimacy", 0.5) < 0.15


def _can_form(relation_type, state_a, state_b, world_a, world_b):
    # Only block formation when both parties are failed states (truly no capacity)
    failed_a = state_a.get("gdp_proxy", 0.5) < 0.02 and state_a.get("legitimacy", 0.5) < 0.02
    failed_b = state_b.get("gdp_proxy", 0.5) < 0.02 and state_b.get("legitimacy", 0.5) < 0.02
    if failed_a or failed_b:
        return False, {}
    if relation_type == "aid_pact":
        crisis_a = _in_crisis(state_a)
        crisis_b = _in_crisis(state_b)
        if crisis_a and not crisis_b and state_b.get("gdp_proxy", 0.5) > 0.30:
            return True, {"donor": world_b, "recipient": world_a}
        if crisis_b and not crisis_a and state_a.get("gdp_proxy", 0.5) > 0.30:
            return True, {"donor": world_a, "recipient": world_b}
        return False, {}
    if relation_type == "sanctions":
        if state_a.get("repression", 0.3) > 0.70 and state_b.get("legitimacy", 0.5) > 0.45:
            return True, {"sender": world_b, "target": world_a}
        if state_b.get("repression", 0.3) > 0.70 and state_a.get("legitimacy", 0.5) > 0.45:
            return True, {"sender": world_a, "target": world_b}
        return False, {}
    conds = RELATION_CONDITIONS.get(relation_type, {})
    if not conds:
        return False, {}
    for key, threshold in conds.items():
        if state_a.get(key, 0) < threshold:
            return False, {}
        if state_b.get(key, 0) < threshold:
            return False, {}
    return True, {}


def _eval_pair(db, world_a, world_b, tick_number):
    state_a = _macro_state(db, world_a)
    state_b = _macro_state(db, world_b)
    if not state_a or not state_b:
        return 0

    # Check existing relations
    existing = db.execute(
        "SELECT relation_type FROM diplomatic_relations WHERE world_a=? AND world_b=? AND dissolved_tick IS NULL",
        (world_a, world_b),
    ).fetchone()
    if existing:
        return 0

    # Try to form relations in priority order
    priority = ["sanctions", "aid_pact", "trade_agreement", "mutual_defense", "research_cooperation"]
    for rel_type in priority:
        ok, meta = _can_form(rel_type, state_a, state_b, world_a, world_b)
        if not ok:
            continue
        rel_id = f"diplo:{world_a}:{world_b}:{rel_type}:{tick_number}:{uuid.uuid4().hex[:6]}"
        payload = dict(meta)
        now = time.time()
        db.execute(
            """
            INSERT INTO diplomatic_relations
                (relation_id, world_a, world_b, relation_type, strength, established_tick, payload, created_at)
            VALUES (?, ?, ?, ?, 0.5, ?, ?, ?)
            """,
            (rel_id, world_a, world_b, rel_type, tick_number, json.dumps(payload, sort_keys=True), now),
        )
        event_type = f"{rel_type}_{'signed' if rel_type != 'sanctions' else 'imposed'}"
        causal_ledger.emit_event(
            db, tick_number=tick_number, world_id="federation", layer="federation",
            event_type=event_type, scope="federation",
            actor_ids=[world_a, world_b], magnitude=0.5, valence=0.25,
            payload={"world_a": world_a, "world_b": world_b, "relation_type": rel_type, **payload},
        )
        return 1
    return 0


def _maintain_relations(db, tick_number):
    """Update diplomatic trust; dissolve only when capacity/conditions truly fail."""
    rows = db.execute(
        "SELECT * FROM diplomatic_relations WHERE dissolved_tick IS NULL"
    ).fetchall()
    for rel in rows:
        state_a = _macro_state(db, rel["world_a"])
        state_b = _macro_state(db, rel["world_b"])
        age_bonus = min(0.010, max(0, int(tick_number) - int(rel["established_tick"])) * 0.0004)
        peace_bonus = max(0.0, 0.35 - max(state_a.get("war_pressure", 0.0), state_b.get("war_pressure", 0.0))) * 0.010
        trade_bonus = min(state_a.get("gdp_proxy", 0.0), state_b.get("gdp_proxy", 0.0)) * 0.004
        repression_drag = max(state_a.get("repression", 0.0), state_b.get("repression", 0.0)) * 0.003
        crisis_drag = 0.010 if (state_a.get("gdp_proxy", 0.5) < 0.08 or state_b.get("gdp_proxy", 0.5) < 0.08) else 0.0
        new_strength = max(0.0, min(1.0, rel["strength"] + age_bonus + peace_bonus + trade_bonus - repression_drag - crisis_drag))
        should_dissolve = new_strength <= 0.03

        if rel["relation_type"] == "trade_agreement":
            # Truly failed states break trade immediately; strong accumulated
            # trade trust can survive only temporary downturns.
            failed = lambda s: s.get("gdp_proxy", 0.5) < 0.02 and s.get("legitimacy", 0.5) < 0.02
            if failed(state_a) or failed(state_b):
                should_dissolve = True
            elif new_strength < 0.35 and (state_a.get("gdp_proxy", 0.5) < 0.12 or state_b.get("gdp_proxy", 0.5) < 0.12):
                should_dissolve = True
        elif rel["relation_type"] == "aid_pact":
            failed = lambda s: s.get("gdp_proxy", 0.5) < 0.02 and s.get("legitimacy", 0.5) < 0.02
            if failed(state_a) or failed(state_b):
                should_dissolve = True
        elif rel["relation_type"] == "mutual_defense":
            if new_strength < 0.25 and state_a.get("war_pressure", 0.5) < 0.15 and state_b.get("war_pressure", 0.5) < 0.15:
                should_dissolve = True
        elif rel["relation_type"] == "research_cooperation":
            if state_a.get("tech_level", 0.1) < 0.05 or state_b.get("tech_level", 0.1) < 0.05:
                should_dissolve = True

        if should_dissolve:
            db.execute(
                "UPDATE diplomatic_relations SET dissolved_tick=?, strength=0.0 WHERE relation_id=?",
                (tick_number, rel["relation_id"]),
            )
            causal_ledger.emit_event(
                db, tick_number=tick_number, world_id="federation", layer="federation",
                event_type="diplomatic_relation_dissolved", scope="federation",
                actor_ids=[rel["world_a"], rel["world_b"]], magnitude=0.3, valence=-0.15,
                payload={"relation_type": rel["relation_type"], "world_a": rel["world_a"], "world_b": rel["world_b"], "strength": new_strength},
            )
        else:
            db.execute("UPDATE diplomatic_relations SET strength=? WHERE relation_id=?", (new_strength, rel["relation_id"]))
            causal_ledger.emit_event(
                db, tick_number=tick_number, world_id="federation", layer="federation",
                event_type="diplomatic_trust_accumulated", scope="federation",
                actor_ids=[rel["world_a"], rel["world_b"]], magnitude=new_strength, valence=0.15,
                payload={"relation_type": rel["relation_type"], "world_a": rel["world_a"], "world_b": rel["world_b"], "strength": new_strength},
            )


def evaluate_and_update_relations(db, *, worlds, tick_number):
    ensure_schema(db)
    _maintain_relations(db, tick_number)
    formed = 0
    for world_a in worlds:
        neighbors = BORDERS.get(world_a, [w for w in worlds if w != world_a])
        for world_b in neighbors:
            if world_b <= world_a:
                continue
            formed += _eval_pair(db, world_a, world_b, tick_number)
    return formed
