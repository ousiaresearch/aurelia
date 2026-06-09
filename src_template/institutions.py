"""institutions.py — durable institutions from constructive faction outcomes."""
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

INSTITUTION_TYPES = {
    "labor_unrest": "labor_union",
    "economic_stress": "trade_guild",
    "repression_visibility": "civil_rights_body",
    "migration_pressure": "refugee_council",
}

INSTITUTION_BENEFITS = {
    "labor_union": {"gdp_flow": 0.003, "repression": -0.002, "legitimacy": 0.001},
    "trade_guild": {"gdp_flow": 0.004, "border_openness": 0.002, "fiscal_capacity": 0.001},
    "civil_rights_body": {"repression": -0.005, "public_health": 0.003, "legitimacy": 0.002},
    "refugee_council": {"refugee_tolerance": 0.003, "type_tension": -0.002, "border_openness": 0.001},
    "political_party": {"legitimacy": 0.004, "fiscal_capacity": 0.002, "repression": -0.001},
    "constitutional_court": {"legitimacy": 0.005, "repression": -0.003, "war_pressure": -0.002},
}

CONSTRUCTIVE_OUTCOMES = {"legalized", "governing_coalition", "integrated", "victorious"}


def ensure_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS institutions (
            institution_id TEXT PRIMARY KEY,
            world_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            founded_tick INTEGER NOT NULL,
            founding_faction_id TEXT,
            influence REAL NOT NULL DEFAULT 0.1,
            durability REAL NOT NULL DEFAULT 0.5,
            benefits TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_at REAL NOT NULL
        );
    """)


def _inst_type_for(grievance: str, outcome: str) -> str | None:
    base = INSTITUTION_TYPES.get(grievance)
    if outcome == "governing_coalition":
        return "political_party"
    if outcome == "victorious":
        return "constitutional_court"
    if outcome == "legalized" and base:
        return base
    if outcome == "integrated" and base:
        return base
    return None


def create_institution(db, *, world_id: str, tick_number: int, faction_id: str,
                       inst_type: str, name: str, influence: float = 0.2) -> str:
    ensure_schema(db)
    now = time.time()
    inst_id = f"{world_id}:institution:{inst_type}:{tick_number}:{uuid.uuid4().hex[:8]}"
    benefits = INSTITUTION_BENEFITS.get(inst_type, {})
    db.execute(
        """
        INSERT OR REPLACE INTO institutions
            (institution_id, world_id, name, type, founded_tick, founding_faction_id,
             influence, durability, benefits, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
        """,
        (inst_id, world_id, name, inst_type, tick_number, faction_id,
         influence, 0.5, json.dumps(benefits, sort_keys=True), now),
    )
    causal_ledger.emit_event(
        db,
        tick_number=tick_number,
        world_id=world_id,
        layer="macro",
        event_type="institution_founded",
        scope="institution",
        target_ids=[inst_id],
        magnitude=0.5,
        valence=0.4,
        payload={
            "institution_id": inst_id,
            "type": inst_type,
            "faction_id": faction_id,
        },
    )
    return inst_id


def process_faction_outcome(db, *, world_id: str, tick_number: int, faction_id: str,
                            outcome: str, grievance: str, rng: random.Random) -> str | None:
    ensure_schema(db)
    state = macro_dynamics.latest_state(db, world_id)
    inst_type = _inst_type_for(grievance, outcome)
    if not inst_type:
        return None

    # Formation probability: higher with legitimacy and lower repression
    form_prob = state.get("legitimacy", 0.5) * 0.35 + (1.0 - state.get("repression", 0.3)) * 0.25
    if outcome == "victorious":
        form_prob = 0.70
    elif outcome == "governing_coalition":
        form_prob += 0.15
    elif outcome == "legalized":
        form_prob += 0.20  # Legalized factions have a path to institutionalize

    if rng.random() > form_prob:
        return None

    # Check for existing institution of same type to reinforce
    existing = db.execute(
        "SELECT institution_id, durability FROM institutions WHERE world_id=? AND type=? AND status='active'",
        (world_id, inst_type),
    ).fetchone()

    if existing:
        # Reinforce
        new_durability = min(1.0, existing["durability"] + 0.15)
        db.execute("UPDATE institutions SET durability=? WHERE institution_id=?", (new_durability, existing["institution_id"]))
        causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="macro",
            event_type="institution_reinforced",
            scope="institution",
            target_ids=[existing["institution_id"]],
            magnitude=0.3,
            valence=0.3,
            payload={"institution_id": existing["institution_id"], "faction_id": faction_id},
        )
        return existing["institution_id"]

    name = f"{grievance.replace('_', ' ').title()} Institution"
    if inst_type == "political_party":
        name = f"People's Party"
    elif inst_type == "constitutional_court":
        name = "Constitutional Court"
    return create_institution(db, world_id=world_id, tick_number=tick_number,
                              faction_id=faction_id, inst_type=inst_type, name=name)


def apply_institution_benefits(db, *, world_id: str, tick_number: int) -> dict[str, float]:
    ensure_schema(db)
    state = macro_dynamics.latest_state(db, world_id)
    institutions_rows = db.execute(
        "SELECT * FROM institutions WHERE world_id=? AND status='active'",
        (world_id,),
    ).fetchall()

    deltas = {}
    war = state.get("war_pressure", 0.0)
    repression = state.get("repression", 0.0)
    legitimacy = state.get("legitimacy", 0.5)

    for inst in institutions_rows:
        benefits = json.loads(inst["benefits"] or "{}")
        for key, delta in benefits.items():
            deltas[key] = deltas.get(key, 0.0) + float(delta)

        # Durability: low base decay, scaled by war/repression; passive gain when stable
        decay = 0.001 + war * 0.006 + repression * 0.003
        gain = max(0.0, (legitimacy - 0.30)) * 0.004
        new_durability = max(0.0, min(1.0, inst["durability"] + gain - decay))
        if new_durability <= 0.02:
            db.execute("UPDATE institutions SET status='dissolved', durability=0.0 WHERE institution_id=?",
                       (inst["institution_id"],))
            causal_ledger.emit_event(
                db, tick_number=tick_number, world_id=world_id, layer="macro",
                event_type="institution_dissolved", scope="institution",
                target_ids=[inst["institution_id"]], magnitude=0.3, valence=-0.3,
                payload={"institution_id": inst["institution_id"], "type": inst["type"]},
            )
        else:
            db.execute("UPDATE institutions SET durability=? WHERE institution_id=?",
                       (new_durability, inst["institution_id"]))

    if deltas:
        causal_ledger.emit_event(
            db, tick_number=tick_number, world_id=world_id, layer="macro",
            event_type="institution_benefit_applied", scope="country",
            magnitude=sum(abs(v) for v in deltas.values()),
            valence=0.25,
            payload={"deltas": deltas, "active_institutions": len(institutions_rows)},
        )

    return deltas
