"""reconciliation.py — Peace, reform, and integration pathways.

Phase 6.5 Module 1: Every war pathway gets a peace pathway. Factions can achieve
demands, governments can reform, countries can mediate. The simulation can heal.
"""

import json
import time
import random
from typing import Optional, Dict, Any, List, Tuple

# ── Government profiles (shared with escalation_ladder) ──────────────

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

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]


# ═══════════════════════════════════════════════════════════════════
# 1. PEACE TREATIES
# ═══════════════════════════════════════════════════════════════════

def check_peace_treaty(
    db,
    faction_a: Dict[str, Any],
    faction_b: Optional[Dict[str, Any]],
    world_id: str,
    tick_number: int,
    diplomatic_relations: Optional[Dict[str, Dict[str, float]]] = None,
) -> Optional[Dict[str, Any]]:
    """Two factions in conflict can negotiate through a mediator.

    Returns a peace treaty event, or None.
    """
    # Check if either faction has a recent broken treaty (cooldown)
    fid_a = faction_a["faction_id"]
    fid_b = faction_b["faction_id"] if faction_b else None
    recent_break = db.execute(
        "SELECT MAX(tick_number) FROM peace_treaties WHERE (faction_a_id = ? OR faction_b_id = ?) AND broken = 1",
        (fid_a, fid_a)
    ).fetchone()
    if recent_break and recent_break[0] and (tick_number - recent_break[0]) < 20:
        return None

    # Mediator: random neutral country
    mediator = random.choice([c for c in COUNTRIES if c != world_id])

    # Base probability
    base_prob = 0.002

    # Faction influence difference — more balanced = more likely to negotiate
    inf_a = float(faction_a.get("influence", 0.3))
    inf_b = float(faction_b.get("influence", 0.3)) if faction_b else 0.5  # government = 0.5
    influence_diff = abs(inf_a - inf_b)
    if influence_diff < 0.2:
        base_prob *= 2.0

    # Mediator trust
    if diplomatic_relations is None:
        diplomatic_relations = _load_diplomatic_relations()
    pair = sorted([world_id, mediator])
    pair_key = f"{pair[0]}|{pair[1]}"
    mediator_trust = diplomatic_relations.get(pair_key, {}).get("trust", 0.5)
    base_prob *= (1.0 + mediator_trust)

    if random.random() > base_prob:
        return None

    # Create treaty
    treaty_id = f"peace:{fid_a}:{fid_b or 'govt'}:{tick_number}"
    now = time.time()

    # De-escalate both
    db.execute("UPDATE factions SET status = 'grievance' WHERE faction_id = ?", (fid_a,))
    if fid_b:
        db.execute("UPDATE factions SET status = 'grievance' WHERE faction_id = ?", (fid_b,))

    db.execute("""
        INSERT INTO peace_treaties (treaty_id, faction_a_id, faction_b_id, mediator_world,
            terms, signed_tick, durability, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 1.0, ?)
    """, (treaty_id, fid_a, fid_b, mediator, json.dumps({"mediated_by": mediator}), tick_number, now))
    db.commit()

    b_name = faction_b["name"] if faction_b else f"the government of {world_id}"
    return {
        "event_type": "peace_treaty",
        "category": "diplomacy",
        "title": f"Peace treaty: {faction_a['name']} — {b_name}",
        "description": f"A peace treaty has been signed between '{faction_a['name']}' and "
                       f"{b_name}, mediated by {mediator.title()}. "
                       f"Both sides de-escalate to grievance level.",
        "importance": 0.9,
        "actor_ids": [faction_a.get("leader_npc_id", "")],
        "tags": ["peace", "treaty", "diplomacy", world_id, mediator],
        "payload": {
            "treaty_id": treaty_id,
            "faction_a": faction_a["name"],
            "faction_b": b_name,
            "mediator": mediator,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 2. DEMAND SATISFACTION
# ═══════════════════════════════════════════════════════════════════

def check_demand_satisfaction(
    db,
    faction: Dict[str, Any],
    world_id: str,
    tick_number: int,
) -> Optional[Dict[str, Any]]:
    """Government meets faction demands → faction integrates into political system."""
    status = faction.get("status", "")
    if status not in ("organization", "ultimatum"):
        return None

    gov = GOVERNMENT_PROFILES.get(world_id, GOVERNMENT_PROFILES["solara"])
    concession = gov["concession_willingness"]
    repression = gov["repression_capacity"]

    # Only possible if government is willing enough
    if concession < 0.35:
        return None

    base_prob = 0.005 * concession * (1.0 - repression)
    influence = float(faction.get("influence", 0.3))
    base_prob *= (1.0 + influence)

    if random.random() > base_prob:
        return None

    # Integrate faction
    faction_id = faction["faction_id"]
    db.execute("UPDATE factions SET status = 'integrated' WHERE faction_id = ?", (faction_id,))

    # Members gain satisfaction and connectedness
    members = db.execute(
        "SELECT npc_id FROM faction_members WHERE faction_id = ?", (faction_id,)
    ).fetchall()
    for m in members:
        db.execute("""
            UPDATE npc_decision_state
            SET variables = json_set(
                COALESCE(variables, '{}'),
                '$.satisfaction', MIN(1.0, COALESCE(json_extract(variables, '$.satisfaction'), 0.5) + 0.2),
                '$.connectedness', MIN(1.0, COALESCE(json_extract(variables, '$.connectedness'), 0.5) + 0.1)
            )
            WHERE npc_id = ?
        """, (m["npc_id"],))

    # Government stability temporarily drops
    gov["stability"] = max(0.1, gov["stability"] - 0.05)
    _store_government_profile(world_id, gov)

    db.commit()

    return {
        "event_type": "demand_satisfied",
        "category": "governance",
        "title": f"Reform: {faction['name']}'s demands met",
        "description": f"The government of {world_id.title()} has met the demands of "
                       f"'{faction['name']}', integrating the faction into the political system. "
                       f"Members' satisfaction rises. Government stability temporarily dips.",
        "importance": 0.85,
        "actor_ids": [faction.get("leader_npc_id", "")],
        "tags": ["reform", "integration", "governance", world_id],
        "payload": {
            "faction_id": faction_id,
            "faction_name": faction["name"],
            "members_affected": len(members),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 3. FACTION MERGER
# ═══════════════════════════════════════════════════════════════════

def check_faction_merger(
    db,
    world_id: str,
    tick_number: int,
) -> List[Dict[str, Any]]:
    """Two factions with aligned grievances in same region can merge."""
    events = []
    active_factions = db.execute(
        "SELECT * FROM factions WHERE world_id = ? AND status NOT IN ('dissolved', 'sovereign', 'integrated')",
        (world_id,)
    ).fetchall()

    if len(active_factions) < 2:
        return events

    # Check all pairs
    for i in range(len(active_factions)):
        for j in range(i + 1, len(active_factions)):
            fa = dict(active_factions[i])
            fb = dict(active_factions[j])

            if fa.get("region") != fb.get("region"):
                continue
            if fa.get("primary_grievance") != fb.get("primary_grievance"):
                continue

            # Members overlap ratio
            members_a = set(r[0] for r in db.execute(
                "SELECT npc_id FROM faction_members WHERE faction_id = ?", (fa["faction_id"],)
            ).fetchall())
            members_b = set(r[0] for r in db.execute(
                "SELECT npc_id FROM faction_members WHERE faction_id = ?", (fb["faction_id"],)
            ).fetchall())
            overlap = len(members_a & members_b)
            overlap_ratio = overlap / max(len(members_a | members_b), 1)

            inf_similarity = 1.0 - abs(float(fa.get("influence", 0.3)) - float(fb.get("influence", 0.3)))

            base_prob = 0.003 * (0.3 + overlap_ratio) * (0.3 + inf_similarity)

            if random.random() > base_prob:
                continue

            # Merge: larger absorbs smaller
            if len(members_a) >= len(members_b):
                survivor, absorbed = fa, fb
            else:
                survivor, absorbed = fb, fa

            # Move all members of absorbed to survivor
            for nid in members_b:
                db.execute(
                    "INSERT OR REPLACE INTO faction_members (faction_id, npc_id, joined_tick, role) VALUES (?, ?, ?, 'member')",
                    (survivor["faction_id"], nid, tick_number)
                )

            # Dissolve absorbed
            db.execute(
                "UPDATE factions SET status = 'dissolved', dissolved_tick = ? WHERE faction_id = ?",
                (tick_number, absorbed["faction_id"])
            )
            db.execute("DELETE FROM faction_members WHERE faction_id = ?", (absorbed["faction_id"],))

            db.commit()

            events.append({
                "event_type": "faction_merged",
                "category": "governance",
                "title": f"Faction merger: {survivor['name']} absorbs {absorbed['name']}",
                "description": f"The factions '{survivor['name']}' and '{absorbed['name']}' "
                               f"in {world_id.title()} have merged, combining their movements. "
                               f"Combined membership: {len(members_a | members_b)}.",
                "importance": 0.7,
                "actor_ids": [survivor.get("leader_npc_id", "")],
                "tags": ["merger", "faction", world_id],
                "payload": {
                    "survivor": survivor["faction_id"],
                    "absorbed": absorbed["faction_id"],
                    "combined_members": len(members_a | members_b),
                },
            })

    return events


# ═══════════════════════════════════════════════════════════════════
# 4. PREVENTIVE REFORM
# ═══════════════════════════════════════════════════════════════════

def check_preventive_reform(
    db,
    world_id: str,
    tick_number: int,
) -> Optional[Dict[str, Any]]:
    """Government reforms before factions form — reducing future conflict risk."""
    gov = GOVERNMENT_PROFILES.get(world_id, GOVERNMENT_PROFILES["solara"])

    # Only possible if government has some willingness
    if gov["concession_willingness"] < 0.4:
        return None

    # Check grievance density
    grievance_density = _count_grievance_npcs(db)
    if grievance_density < 25:
        return None

    # Check no active factions already exist
    existing = db.execute(
        "SELECT COUNT(*) FROM factions WHERE world_id = ? AND status NOT IN ('dissolved', 'sovereign', 'integrated')",
        (world_id,)
    ).fetchone()[0]
    if existing > 0:
        return None  # Too late, factions already organized

    base_prob = 0.001 * gov["concession_willingness"] * (1.0 + grievance_density / 50)
    base_prob = min(base_prob, 0.05)

    if random.random() > base_prob:
        return None

    # Apply reform
    old_repression = gov["repression_capacity"]
    gov["repression_capacity"] = max(0.1, gov["repression_capacity"] - 0.1)
    gov["concession_willingness"] = min(0.9, gov["concession_willingness"] + 0.15)
    gov["stability"] = max(0.1, gov["stability"] - 0.03)
    _store_government_profile(world_id, gov)

    db.commit()

    return {
        "event_type": "preventive_reform",
        "category": "governance",
        "title": f"Reform in {world_id.title()}: government liberalizes",
        "description": f"The government of {world_id.title()} has enacted preventive reforms, "
                       f"reducing repression ({old_repression:.1f} → {gov['repression_capacity']:.1f}) "
                       f"and increasing concession willingness. Future faction formation 30% less likely. "
                       f"Stability dips slightly.",
        "importance": 0.75,
        "actor_ids": [],
        "tags": ["reform", "governance", world_id],
        "payload": {
            "old_repression": old_repression,
            "new_repression": gov["repression_capacity"],
            "grievance_density": grievance_density,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 5. THIRD-PARTY MEDIATION
# ═══════════════════════════════════════════════════════════════════

def check_mediation(
    db,
    faction: Dict[str, Any],
    world_id: str,
    tick_number: int,
    diplomatic_relations: Optional[Dict[str, Dict[str, float]]] = None,
) -> Optional[Dict[str, Any]]:
    """A neutral country brokers dialogue between a faction and its government."""
    status = faction.get("status", "")
    # Already handled by integrated/dissolved factions
    if status not in ("organization", "ultimatum", "skirmish"):
        return None

    if diplomatic_relations is None:
        diplomatic_relations = _load_diplomatic_relations()

    # Find a mediator
    candidates = []
    for other in COUNTRIES:
        if other == world_id:
            continue
        pair = sorted([world_id, other])
        pair_key = f"{pair[0]}|{pair[1]}"
        rels = diplomatic_relations.get(pair_key, {})
        if rels.get("trust", 0) >= 0.5 and rels.get("tension", 1) < 0.6:
            candidates.append(other)

    if not candidates:
        return None

    mediator = random.choice(candidates)
    pair = sorted([world_id, mediator])
    pair_key = f"{pair[0]}|{pair[1]}"
    mediator_trust = diplomatic_relations.get(pair_key, {}).get("trust", 0.5)

    base_prob = 0.004 * mediator_trust * (1.0 - float(faction.get("influence", 0.3)))

    if random.random() > base_prob:
        return None

    # De-escalate one rung
    LADDER = ["dormant", "grievance", "organization", "ultimatum", "skirmish", "armed_conflict", "war"]
    idx = LADDER.index(status) if status in LADDER else 3
    new_status = LADDER[max(0, idx - 1)]

    faction_id = faction["faction_id"]
    db.execute("UPDATE factions SET status = ? WHERE faction_id = ?", (new_status, faction_id))
    db.commit()

    return {
        "event_type": "mediation",
        "category": "diplomacy",
        "title": f"Mediation: {mediator.title()} brokers dialogue in {world_id.title()}",
        "description": f"{mediator.title()} has initiated mediation between "
                       f"'{faction['name']}' and the government of {world_id.title()}. "
                       f"The faction de-escalates from {status} to {new_status}.",
        "importance": 0.8,
        "actor_ids": [],
        "tags": ["mediation", "diplomacy", world_id, mediator],
        "payload": {
            "faction_id": faction_id,
            "mediator": mediator,
            "from_status": status,
            "to_status": new_status,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# TICK INTEGRATION
# ═══════════════════════════════════════════════════════════════════

def check_all_reconciliation(
    db,
    world_id: str,
    tick_number: int,
    growth_snapshot: Optional[dict] = None,
) -> List[Dict[str, Any]]:
    """Run all reconciliation checks for a world. Returns list of events."""
    events = []

    # 1. Preventive reform
    reform = check_preventive_reform(db, world_id, tick_number)
    if reform:
        events.append(reform)

    # 2. Faction-specific checks
    active_factions = db.execute(
        "SELECT * FROM factions WHERE world_id = ? AND status NOT IN ('dissolved', 'sovereign', 'integrated', 'dormant')",
        (world_id,)
    ).fetchall()

    for f in active_factions:
        faction_dict = dict(f)

        # Demand satisfaction
        demand_event = check_demand_satisfaction(db, faction_dict, world_id, tick_number)
        if demand_event:
            events.append(demand_event)
            continue  # Skip other checks for integrated factions

        # Mediation
        mediation_event = check_mediation(db, faction_dict, world_id, tick_number)
        if mediation_event:
            events.append(mediation_event)

    # 3. Faction mergers
    merger_events = check_faction_merger(db, world_id, tick_number)
    events.extend(merger_events)

    # 4. Peace treaties (between pairs of skirmish+ factions)
    skirmish_factions = [dict(f) for f in active_factions
                         if dict(f).get("status") in ("skirmish", "armed_conflict", "war")]
    if len(skirmish_factions) >= 2:
        for i in range(len(skirmish_factions)):
            for j in range(i + 1, len(skirmish_factions)):
                if random.random() < 0.3:  # 30% chance to check per pair per tick
                    treaty = check_peace_treaty(
                        db, skirmish_factions[i], skirmish_factions[j],
                        world_id, tick_number
                    )
                    if treaty:
                        events.append(treaty)

    # 5. Decay existing treaty durability
    db.execute("""
        UPDATE peace_treaties
        SET durability = MAX(0.0, durability - 0.001)
        WHERE durability > 0 AND broken = 0
    """)

    # Broken treaties
    fragile = db.execute(
        "SELECT * FROM peace_treaties WHERE durability < 0.3 AND broken = 0"
    ).fetchall()
    for pt in fragile:
        if random.random() < 0.01:
            db.execute(
                "UPDATE peace_treaties SET broken = 1 WHERE treaty_id = ?",
                (pt["treaty_id"],)
            )
            events.append({
                "event_type": "treaty_broken",
                "category": "diplomacy",
                "title": f"Peace treaty broken: {pt['treaty_id']}",
                "description": f"A peace treaty has collapsed. Hostilities may resume.",
                "importance": 0.8,
                "actor_ids": [],
                "tags": ["treaty_broken", world_id],
                "payload": {"treaty_id": pt["treaty_id"]},
            })

    db.commit()
    return events


def get_reconciliation_state(db, world_id: str) -> Dict[str, Any]:
    """Return reconciliation state for dashboard/API."""
    active_treaties = db.execute(
        "SELECT COUNT(*) FROM peace_treaties WHERE broken = 0 AND durability > 0.5"
    ).fetchone()[0]
    integrated = db.execute(
        "SELECT COUNT(*) FROM factions WHERE world_id = ? AND status = 'integrated'",
        (world_id,)
    ).fetchone()[0]

    return {
        "active_treaties": active_treaties,
        "integrated_factions": integrated,
    }


# ── Internal helpers ──────────────────────────────────────────────

def _count_grievance_npcs(db) -> int:
    """Count NPCs with significant grievance variables."""
    rows = db.execute(
        "SELECT variables FROM npc_decision_state"
    ).fetchall()
    count = 0
    for r in rows:
        try:
            ds = json.loads(r["variables"]) if isinstance(r["variables"], str) else r["variables"]
        except (json.JSONDecodeError, TypeError):
            continue
        # Count NPCs with at least one grievance condition
        if (ds.get("security", 0.5) < 0.3 or
            ds.get("satisfaction", 0.5) < 0.3 or
            ds.get("anomaly_pressure", 0) > 0.5 or
            ds.get("observed_injustice", 0) > 0.5):
            count += 1
    return count


def _load_diplomatic_relations() -> Dict[str, Dict[str, float]]:
    try:
        import sqlite3 as _sql
        cdb = _sql.connect("/Users/johann/aurelia/coordinator.db", timeout=2)
        cdb.row_factory = _sql.Row
        rows = cdb.execute(
            "SELECT relation_key, trust, tension FROM diplomatic_relations"
        ).fetchall()
        cdb.close()
        return {r["relation_key"]: {"trust": r["trust"], "tension": r["tension"]} for r in rows}
    except Exception:
        return {}


def _store_government_profile(world_id: str, profile: dict):
    """Store modified government profile. In-memory only — resets on daemon restart.
    This is intentional: profiles drift during a session, but baseline is lore."""
    GOVERNMENT_PROFILES[world_id] = profile
