"""escalation_ladder.py — Faction conflict escalation state machine.

Phase 6 Module 2: Dormant → War state transitions driven by probability × influence × world state.
Each step is a decision point — nothing fires on a timer. Government response,
diplomatic intervention, and cross-world effects cascade from faction state changes.
"""

import json
import time
import random
from typing import Optional, Dict, Any, List, Tuple

# ── Ladder definition ─────────────────────────────────────────────

LADDER = ["dormant", "grievance", "organization", "ultimatum", "skirmish", "armed_conflict", "war"]

# Index-based progression: LADDER[i] → LADDER[i+1]
LADDER_INDEX = {state: i for i, state in enumerate(LADDER)}

# Base probability of escalation per tick when faction is at a given state
ESCALATION_BASE_PROB = {
    "grievance": 0.01,       # Grievance → Organization
    "organization": 0.005,   # Organization → Ultimatum
    "ultimatum": 0.003,      # Ultimatum → Skirmish
    "skirmish": 0.002,       # Skirmish → Armed Conflict
    "armed_conflict": 0.001, # Armed Conflict → War
}

# De-escalation chance when government makes concessions
DEESCALATION_BASE_PROB = {
    "organization": 0.03,
    "ultimatum": 0.02,
    "skirmish": 0.01,
    "armed_conflict": 0.005,
}

# Government profile per country — affects repression capacity and concession willingness
GOVERNMENT_PROFILES = {
    "solara": {
        "repression_capacity": 0.7,
        "concession_willingness": 0.3,
        "stability": 0.65,
        "label": "Solar Council autocracy",
    },
    "arkos": {
        "repression_capacity": 0.5,
        "concession_willingness": 0.6,
        "stability": 0.75,
        "label": "Arkos protective federation",
    },
    "mirithane": {
        "repression_capacity": 0.4,
        "concession_willingness": 0.55,
        "stability": 0.7,
        "label": "Mirithane research council",
    },
    "valdris": {
        "repression_capacity": 0.55,
        "concession_willingness": 0.45,
        "stability": 0.6,
        "label": "Valdris merchant consortium",
    },
    "verge": {
        "repression_capacity": 0.2,
        "concession_willingness": 0.7,
        "stability": 0.4,
        "label": "The Verge — decentralized",
    },
}


def _get_escalation_target(current_status: str) -> Optional[str]:
    """Get the next state in the ladder, or None if at war."""
    idx = LADDER_INDEX.get(current_status, -1)
    if idx < 0 or idx >= len(LADDER) - 1:
        return None
    return LADDER[idx + 1]


def _get_deescalation_target(current_status: str) -> Optional[str]:
    """Get the previous state in the ladder, or None if dormant."""
    idx = LADDER_INDEX.get(current_status, 0)
    if idx <= 1:  # Can't de-escalate below grievance
        return "dormant"
    return LADDER[idx - 1]


def check_escalation(
    db,
    faction: Dict[str, Any],
    world_id: str,
    growth_snapshot: Optional[dict] = None,
    diplomatic_tension: float = 0.3,
    tick_number: int = 0,
) -> Optional[Dict[str, Any]]:
    """Roll for faction escalation to the next rung of the conflict ladder.

    Returns an escalation event dict, or None.
    """
    current_status = faction.get("status", "grievance")
    target = _get_escalation_target(current_status)
    if not target:
        return None  # Already at war

    base_prob = ESCALATION_BASE_PROB.get(current_status, 0.001)

    # ── Modifiers ──────────────────────────────────────────────

    # 1. Faction influence — more members = more pressure
    influence = float(faction.get("influence", 0.1))
    prob = base_prob * (1.0 + influence)

    # 2. Government repression — less repression = easier escalation
    gov = GOVERNMENT_PROFILES.get(world_id, GOVERNMENT_PROFILES["solara"])
    repression = gov["repression_capacity"]
    prob *= (1.5 - repression)  # Range: 0.8 (Solara) to 1.3 (Verge)

    # 3. Diplomatic tension — higher tension destabilizes
    prob *= (1.0 + diplomatic_tension)  # Range: 1.0 to 2.0

    # 4. Government stability — lower stability encourages escalation
    stability = gov["stability"]
    prob *= (1.5 - stability)  # Range: 0.75 to 1.1

    # 5. Glim anomalies — chaos multiplier
    if growth_snapshot:
        anomalies = growth_snapshot.get("glim_anomaly_signals", 0)
        if anomalies > 0:
            prob *= (1.0 + min(anomalies / 100, 1.0))

    # 6. Economic instability from growth snapshot
    if growth_snapshot:
        instability = growth_snapshot.get("economic_instability", 0.0)
        prob *= (1.0 + instability)

    # 7. Member count momentum
    member_count = int(faction.get("member_count", 10))
    prob *= (1.0 + min(member_count / 100, 1.0))

    # Clamp probability — never exceed 50% per tick
    prob = min(prob, 0.5)

    if random.random() > prob:
        return None

    # Escalate
    faction_id = faction["faction_id"]
    db.execute(
        "UPDATE factions SET status = ?, metadata = json_set(COALESCE(metadata, '{}'), '$.escalated_at_tick', ?) WHERE faction_id = ?",
        (target, tick_number, faction_id)
    )

    # Log sovereignty event for tracking
    db.execute("""
        INSERT INTO sovereignty_events (faction_id, world_id, event_type, member_count, tick_number, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (faction_id, world_id, f"escalation:{target}", member_count, tick_number, time.time()))

    db.commit()

    event_type = f"escalation_{target.replace(' ', '_')}"
    return {
        "event_type": event_type,
        "category": "conflict",
        "title": f"Escalation: {faction['name']} reaches {target}",
        "description": f"The faction '{faction['name']}' in {world_id} has escalated from "
                       f"{current_status} to {target}. Influence: {influence:.2f}, "
                       f"members: {member_count}. Government repression: {repression:.1f}.",
        "importance": 0.85 + (LADDER_INDEX.get(target, 0) * 0.02),
        "actor_ids": [faction.get("leader_npc_id", "")],
        "tags": ["escalation", target, faction.get("primary_grievance", ""), world_id],
        "payload": {
            "faction_id": faction_id,
            "from_status": current_status,
            "to_status": target,
            "influence": influence,
            "member_count": member_count,
        },
    }


def check_deescalation(
    db,
    faction: Dict[str, Any],
    world_id: str,
    tick_number: int = 0,
) -> Optional[Dict[str, Any]]:
    """Government concessions or faction weakness may trigger de-escalation."""
    current_status = faction.get("status", "grievance")
    if current_status not in DEESCALATION_BASE_PROB:
        return None

    base_prob = DEESCALATION_BASE_PROB[current_status]

    # Government willingness to concede
    gov = GOVERNMENT_PROFILES.get(world_id, GOVERNMENT_PROFILES["solara"])
    concession = gov["concession_willingness"]
    prob = base_prob * (1.0 + concession)

    # Faction weakness reduces resistance to de-escalation
    member_count = int(faction.get("member_count", 10))
    if member_count < 20:
        prob *= 2.0
    if member_count < 10:
        prob *= 3.0

    prob = min(prob, 0.3)

    if random.random() > prob:
        return None

    target = _get_deescalation_target(current_status)
    faction_id = faction["faction_id"]

    db.execute(
        "UPDATE factions SET status = ? WHERE faction_id = ?",
        (target, faction_id)
    )
    db.execute("""
        INSERT INTO sovereignty_events (faction_id, world_id, event_type, member_count, tick_number, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (faction_id, world_id, f"deescalation:{target}", member_count, tick_number, time.time()))
    db.commit()

    return {
        "event_type": f"deescalation_{target}",
        "category": "conflict",
        "title": f"De-escalation: {faction['name']} drops to {target}",
        "description": f"The faction '{faction['name']}' in {world_id} has de-escalated to {target}. "
                       f"Members: {member_count}.",
        "importance": 0.5,
        "actor_ids": [],
        "tags": ["deescalation", target, world_id],
        "payload": {
            "faction_id": faction_id,
            "from_status": current_status,
            "to_status": target,
        },
    }


def apply_escalation_fallout(
    db,
    world_id: str,
    escalations: List[Dict[str, Any]],
    tick_number: int,
):
    """Apply population and diplomatic effects from escalation events.

    - Skirmish+: migration pressure on NPCs in faction region
    - Armed conflict+: mortality chance for faction members
    - War: severe mortality + mass migration
    """
    if not escalations:
        return

    # Identify the highest ladder state among active factions
    factions = db.execute(
        "SELECT * FROM factions WHERE world_id = ? AND status NOT IN ('dissolved', 'sovereign')",
        (world_id,)
    ).fetchall()

    max_state = "dormant"
    for f in factions:
        if LADDER_INDEX.get(f["status"], 0) > LADDER_INDEX.get(max_state, 0):
            max_state = f["status"]

    # ── Population effects ──────────────────────────────────────
    if LADDER_INDEX.get(max_state, 0) >= LADDER_INDEX.get("skirmish", 0):
        # Migration pressure: NPCs in the faction's region become restless
        for f in factions:
            if LADDER_INDEX.get(f["status"], 0) >= LADDER_INDEX.get("skirmish", 0):
                region = f["region"]
                members = db.execute(
                    "SELECT npc_id FROM faction_members WHERE faction_id = ?", (f["faction_id"],)
                ).fetchall()
                # Non-member NPCs in region get restlessness nudge
                db.execute("""
                    UPDATE npc_decision_state
                    SET variables = json_set(
                        COALESCE(variables, '{}'),
                        '$.restlessness',
                        MIN(1.0, COALESCE(json_extract(variables, '$.restlessness'), 0) + 0.02)
                    )
                    WHERE npc_id IN (
                        SELECT a.id FROM agents a
                        WHERE a.type = 'npc' AND a.state = 'active'
                        AND (a.location_id LIKE ? || '%' OR a.location_id LIKE ? || '%')
                    )
                """, (region, f"_{region}_"))
                # Faction members: security drops
                member_ids = [m["npc_id"] for m in members]
                if member_ids:
                    placeholders = ",".join("?" for _ in member_ids)
                    db.execute(f"""
                        UPDATE npc_decision_state
                        SET variables = json_set(
                            COALESCE(variables, '{{}}'),
                            '$.security',
                            MAX(0.0, COALESCE(json_extract(variables, '$.security'), 0.5) - 0.03)
                        )
                        WHERE npc_id IN ({placeholders})
                    """, member_ids)

    if LADDER_INDEX.get(max_state, 0) >= LADDER_INDEX.get("armed_conflict", 0):
        # Mortality: small chance per tick for faction members
        for f in factions:
            if LADDER_INDEX.get(f["status"], 0) >= LADDER_INDEX.get("armed_conflict", 0):
                members = db.execute(
                    "SELECT npc_id FROM faction_members WHERE faction_id = ?", (f["faction_id"],)
                ).fetchall()
                death_chance = 0.005  # 0.5% per tick at armed conflict
                if f["status"] == "war":
                    death_chance = 0.02  # 2% at war

                for m in members:
                    if random.random() < death_chance:
                        db.execute(
                            "UPDATE agents SET state = 'deceased' WHERE id = ?", (m["npc_id"],)
                        )

    if max_state == "war":
        # Mass migration — NPCs flee
        db.execute("""
            UPDATE npc_decision_state
            SET variables = json_set(
                COALESCE(variables, '{}'),
                '$.restlessness',
                MIN(1.0, COALESCE(json_extract(variables, '$.restlessness'), 0) + 0.05)
            )
            WHERE npc_id IN (
                SELECT id FROM agents WHERE type = 'npc' AND state = 'active'
            )
        """)

    db.commit()


def check_intervention(
    world_id: str,
    faction: Dict[str, Any],
    diplomatic_relations: Dict[str, Dict[str, float]],
    tick_number: int,
) -> List[Dict[str, Any]]:
    """Other countries may intervene when a faction reaches skirmish level or above.

    Returns list of intervention events.
    """
    status = faction.get("status", "")
    idx = LADDER_INDEX.get(status, 0)
    if idx < LADDER_INDEX.get("skirmish", 0):
        return []

    interventions = []
    COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]

    for other in COUNTRIES:
        if other == world_id:
            continue

        pair = sorted([world_id, other])
        pair_key = f"{pair[0]}|{pair[1]}"
        rels = diplomatic_relations.get(pair_key, {})
        trust = rels.get("trust", 0.5)
        tension = rels.get("tension", 0.3)

        # Intervention probability: higher if tension is high OR trust is very high (allies)
        base_prob = 0.01  # 1% base

        # High tension → intervene against the faction's country (support the rebels)
        if tension > 0.6:
            base_prob *= (tension * 2)

        # Low tension + high trust → intervene to stabilize (support the government)
        if tension < 0.3 and trust > 0.6:
            base_prob *= 0.5  # Reduce intervention — allies trust each other to handle it

        if random.random() < base_prob:
            intervention_type = "support_rebels" if tension > 0.5 else "diplomatic_pressure"
            interventions.append({
                "event_type": "intervention",
                "category": "diplomacy",
                "title": f"{other.title()} intervenes in {world_id}",
                "description": f"{other.title()} has initiated {intervention_type.replace('_', ' ')} "
                               f"in response to the {faction['name']} at {status} level.",
                "importance": 0.8,
                "actor_ids": [],
                "tags": ["intervention", intervention_type, other, world_id],
                "payload": {
                    "intervening_country": other,
                    "target_country": world_id,
                    "intervention_type": intervention_type,
                    "faction_id": faction["faction_id"],
                    "tick_number": tick_number,
                },
            })

    return interventions


def check_all_escalations(
    db,
    world_id: str,
    tick_number: int,
    growth_snapshot: Optional[dict] = None,
    diplomatic_relations: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[Dict[str, Any]]:
    """Check escalation/de-escalation for all active factions in a world.

    Returns list of events to add to the tick.
    """
    events = []

    # Need diplomatic tension — try to get it from coordinator
    if diplomatic_relations is None:
        diplomatic_relations = _load_diplomatic_relations()

    factions = db.execute(
        "SELECT * FROM factions WHERE world_id = ? AND status NOT IN ('dissolved', 'sovereign')",
        (world_id,)
    ).fetchall()

    for f in factions:
        faction_dict = dict(f)

        # Only check escalation if in an escalatable state
        status = faction_dict.get("status", "grievance")
        if status in ("dormant", "grievance", "organization", "ultimatum", "skirmish"):
            # Calculate diplomatic tension for this world's pairs
            avg_tension = _avg_diplomatic_tension(world_id, diplomatic_relations)
            esc_event = check_escalation(
                db, faction_dict, world_id, growth_snapshot, avg_tension, tick_number
            )
            if esc_event:
                events.append(esc_event)

                # Check for intervention
                interventions = check_intervention(
                    world_id, faction_dict, diplomatic_relations, tick_number
                )
                events.extend(interventions)

        if status in DEESCALATION_BASE_PROB:
            deesc_event = check_deescalation(db, faction_dict, world_id, tick_number)
            if deesc_event:
                events.append(deesc_event)

    # Apply fallout
    apply_escalation_fallout(db, world_id, events, tick_number)

    return events


def get_conflict_state(db, world_id: str) -> Dict[str, Any]:
    """Return a summary of conflict state for /api/growth."""
    factions = db.execute(
        "SELECT status, member_count, influence FROM factions WHERE world_id = ? AND status NOT IN ('dissolved', 'sovereign')",
        (world_id,)
    ).fetchall()

    active = 0
    max_intensity = 0.0
    at_war = 0
    total_members = 0

    for f in factions:
        active += 1
        total_members += f["member_count"]
        idx = LADDER_INDEX.get(f["status"], 0)
        intensity = idx / (len(LADDER) - 1)
        if intensity > max_intensity:
            max_intensity = intensity
        if f["status"] == "war":
            at_war += 1

    return {
        "active_conflicts": active,
        "conflict_intensity_max": round(max_intensity, 3),
        "factions_at_war": at_war,
        "total_faction_members": total_members,
    }


# ── Internal helpers ──────────────────────────────────────────────


def _load_diplomatic_relations() -> Dict[str, Dict[str, float]]:
    """Load diplomatic relations from coordinator DB."""
    try:
        import sqlite3
        cdb = sqlite3.connect("/Users/johann/aurelia/coordinator.db", timeout=2)
        cdb.row_factory = sqlite3.Row
        rows = cdb.execute(
            "SELECT relation_key, trust, tension, cooperation, trade FROM diplomatic_relations"
        ).fetchall()
        cdb.close()
        result = {}
        for r in rows:
            result[r["relation_key"]] = {
                "trust": r["trust"],
                "tension": r["tension"],
                "cooperation": r["cooperation"],
                "trade": r["trade"],
            }
        return result
    except Exception:
        return {}


def _avg_diplomatic_tension(
    world_id: str,
    relations: Dict[str, Dict[str, float]],
) -> float:
    """Calculate average diplomatic tension for this country across all pairs."""
    tensions = []
    for key, data in relations.items():
        if world_id in key:
            tensions.append(data.get("tension", 0.3))
    if not tensions:
        return 0.3
    return sum(tensions) / len(tensions)
