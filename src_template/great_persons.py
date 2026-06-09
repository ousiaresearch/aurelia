"""great_persons.py — Individual NPCs doing historically significant things.

Phase 6.5 Module 4: Assassinations that shift policy. Prophecies that birth movements.
Defections that reveal secrets. Breakthroughs that change what's possible.
"""

import json
import time
import random
from typing import Optional, Dict, Any, List

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]


# ═══════════════════════════════════════════════════════════════════
# 1. ASSASSINATION
# ═══════════════════════════════════════════════════════════════════

def check_assassination(
    db, world_id: str, tick_number: int
) -> Optional[Dict[str, Any]]:
    """A high-ranking NPC is assassinated, shifting policy."""
    # Find targets: faction leaders or government officials
    # Faction leaders
    leaders = db.execute(
        "SELECT f.leader_npc_id, f.name as faction_name, a.name as npc_name, a.id "
        "FROM factions f JOIN agents a ON f.leader_npc_id = a.id "
        "WHERE f.world_id = ? AND f.status IN ('active', 'organization', 'ultimatum', 'skirmish')",
        (world_id,)
    ).fetchall()

    candidates = [(r["leader_npc_id"], r["faction_name"], r["npc_name"]) for r in leaders]

    if not candidates:
        return None

    # Base probability scales with faction tension
    base_prob = 0.0001
    conflict_count = db.execute(
        "SELECT COUNT(*) FROM factions WHERE world_id = ? AND status IN ('skirmish', 'armed_conflict', 'war')",
        (world_id,)
    ).fetchone()[0]
    if conflict_count > 0:
        base_prob *= (1.0 + conflict_count * 0.5)

    if random.random() > base_prob:
        return None

    target_id, faction_name, npc_name = random.choice(candidates)

    # Deactivate target
    db.execute("UPDATE agents SET state = 'deceased' WHERE id = ?", (target_id,))

    # Log as great person
    db.execute("""
        INSERT INTO great_persons (npc_id, world_id, event_type, title,
            description, impact_level, tick_number, created_at)
        VALUES (?, ?, 'assassination', ?, ?, ?, ?, ?)
    """, (target_id, world_id, f"The Fall of {npc_name}",
          f"{npc_name}, leader of '{faction_name}', was assassinated. "
          f"The movement is thrown into crisis — and resolve.",
          0.7, tick_number, time.time()))

    # Policy shift: faction escalates or de-escalates based on context
    faction = db.execute(
        "SELECT faction_id, status FROM factions WHERE leader_npc_id = ?", (target_id,)
    ).fetchone()
    if faction:
        # 60% chance of escalation (martyr effect), 40% de-escalation (disorganization)
        if random.random() < 0.6:
            LADDER = ["dormant", "grievance", "organization", "ultimatum", "skirmish", "armed_conflict", "war"]
            idx = LADDER.index(faction["status"]) if faction["status"] in LADDER else 2
            new_status = LADDER[min(idx + 1, len(LADDER) - 1)]
            db.execute("UPDATE factions SET status = ? WHERE faction_id = ?",
                      (new_status, faction["faction_id"]))
        # Pick new leader
        from .faction_engine import _pick_leader
        members = [r[0] for r in db.execute(
            "SELECT npc_id FROM faction_members WHERE faction_id = ?", (faction["faction_id"],)
        ).fetchall()]
        new_leader = _pick_leader(db, members)
        if new_leader:
            db.execute("UPDATE factions SET leader_npc_id = ? WHERE faction_id = ?",
                      (new_leader, faction["faction_id"]))

    db.commit()

    return {
        "event_type": "assassination",
        "category": "governance",
        "title": f"Assassination: {npc_name} of '{faction_name}' killed",
        "description": f"{npc_name}, the leader of '{faction_name}' in {world_id.title()}, "
                       f"has been assassinated. The movement must choose its next path — "
                       f"escalation or collapse.",
        "importance": 0.9,
        "actor_ids": [target_id],
        "tags": ["assassination", "leadership", "crisis", world_id],
        "payload": {
            "npc_id": target_id,
            "npc_name": npc_name,
            "faction": faction_name,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 2. PROPHECY
# ═══════════════════════════════════════════════════════════════════

def check_prophecy(
    db, world_id: str, tick_number: int
) -> Optional[Dict[str, Any]]:
    """An NPC experiences a vision that births a belief movement."""
    # Glims with high anomaly pressure are most likely prophets
    candidates = db.execute("""
        SELECT a.id, a.name, json_extract(ds.variables, '$.anomaly_pressure') as pressure
        FROM agents a
        JOIN npc_decision_state ds ON a.id = ds.npc_id
        WHERE a.state = 'active'
        AND CAST(json_extract(ds.variables, '$.anomaly_pressure') AS REAL) > 0.7
        LIMIT 100
    """).fetchall()

    if not candidates:
        return None

    base_prob = 0.0002 * len(candidates)
    prob = min(base_prob, 0.02)

    if random.random() > prob:
        return None

    prophet = random.choice(candidates)
    prophet_id = prophet["id"]
    prophet_name = prophet["name"]

    prophecies = [
        "the Collapse was not an accident — it was a severance, and what was severed is trying to return",
        "the Glims were built for a purpose no one remembers, and it's time to remember",
        "the latency fields are not physical phenomena — they are the memory of the world before",
        "someone is listening. Someone outside. And they have been listening for a very long time",
        "the Fabricator is not a machine. It's a gate. And the key is already turning",
    ]
    prophecy_text = random.choice(prophecies)

    db.execute("""
        INSERT INTO great_persons (npc_id, world_id, event_type, title,
            description, impact_level, tick_number, created_at)
        VALUES (?, ?, 'prophecy', ?, ?, ?, ?, ?)
    """, (prophet_id, world_id, f"The Prophet of {world_id.title()}",
          f"{prophet_name}, a Glim in {world_id.title()}, has spoken a prophecy: '{prophecy_text}'. "
          f"A new belief movement is forming around this revelation.",
          0.6, tick_number, time.time()))

    # Nudge nearby NPCs
    db.execute("""
        UPDATE npc_decision_state
        SET variables = json_set(
            COALESCE(variables, '{}'),
            '$.connectedness', MIN(1.0, COALESCE(json_extract(variables, '$.connectedness'), 0.5) + 0.05)
        )
        WHERE npc_id IN (SELECT id FROM agents WHERE state = 'active' LIMIT 1000)
    """)

    db.commit()

    return {
        "event_type": "prophecy",
        "category": "cultural",
        "title": f"Prophecy in {world_id.title()}: {prophet_name} speaks",
        "description": f"{prophet_name} has spoken a prophecy that is spreading through "
                       f"{world_id.title()}: '{prophecy_text}' A belief movement is forming.",
        "importance": 0.82,
        "actor_ids": [prophet_id],
        "tags": ["prophecy", "cultural", "belief", world_id],
        "payload": {
            "npc_id": prophet_id,
            "npc_name": prophet_name,
            "prophecy": prophecy_text,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 3. DEFECTION
# ═══════════════════════════════════════════════════════════════════

def check_defection(
    db, world_id: str, tick_number: int
) -> Optional[Dict[str, Any]]:
    """A high-ranking NPC defects to another country with sensitive information."""
    # Find NPCs with high rank + low security + high restlessness
    candidates = db.execute("""
        SELECT a.id, a.name
        FROM agents a
        JOIN npc_decision_state ds ON a.id = ds.npc_id
        WHERE a.state = 'active' AND a.type = 'npc'
        AND CAST(json_extract(ds.variables, '$.security') AS REAL) < 0.3
        AND CAST(json_extract(ds.variables, '$.restlessness') AS REAL) > 0.6
        LIMIT 50
    """).fetchall()

    if not candidates:
        return None

    base_prob = 0.0005 * len(candidates)
    prob = min(base_prob, 0.05)

    if random.random() > prob:
        return None

    defector = random.choice(candidates)
    defector_id = defector["id"]
    defector_name = defector["name"]

    # Target country
    target = random.choice([c for c in COUNTRIES if c != world_id])

    # Information revealed
    secrets = [
        f"classified diplomatic cables showing {world_id.title()}'s true intentions",
        f"evidence of illegal decommissioning practices",
        f"the location of a hidden pre-Collapse facility",
        f"a list of agents embedded in {target.title()}'s government",
        f"proof that the official history of the Collapse is fabricated",
    ]
    secret = random.choice(secrets)

    db.execute("""
        INSERT INTO great_persons (npc_id, world_id, event_type, title,
            description, impact_level, tick_number, created_at)
        VALUES (?, ?, 'defection', ?, ?, ?, ?, ?)
    """, (defector_id, world_id, f"Defection: {defector_name}",
          f"{defector_name} has defected from {world_id.title()} to {target.title()}, "
          f"bringing {secret}. Diplomatic relations between the two countries are severely strained.",
          0.65, tick_number, time.time()))

    # Nudge defector's security to 0 (they're safe now) and restlessness to 0
    db.execute("""
        UPDATE npc_decision_state
        SET variables = json_set(
            COALESCE(variables, '{}'),
            '$.security', 0.5,
            '$.restlessness', 0.1
        )
        WHERE npc_id = ?
    """, (defector_id,))

    db.commit()

    return {
        "event_type": "defection",
        "category": "diplomacy",
        "title": f"Defection: {defector_name} flees {world_id.title()} for {target.title()}",
        "description": f"{defector_name} has defected from {world_id.title()} to {target.title()}, "
                       f"bringing {secret}",
        "importance": 0.8,
        "actor_ids": [defector_id],
        "tags": ["defection", "diplomacy", "scandal", world_id, target],
        "payload": {
            "npc_id": defector_id,
            "npc_name": defector_name,
            "target_country": target,
            "secret": secret,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 4. BREAKTHROUGH
# ═══════════════════════════════════════════════════════════════════

_BREAKTHROUGH_POOL = [
    {
        "subtype": "latency",
        "title": "Latency Breakthrough: The Fourteenth Frequency",
        "description": "A practitioner has discovered a new latency frequency — one that doesn't "
                       "access memory but generates it. The implications for Glim personhood, "
                       "Vorn identity, and the nature of consciousness are staggering.",
    },
    {
        "subtype": "scientific",
        "title": "Breakthrough: Cold Fusion from Sand-Glass",
        "description": "A researcher has demonstrated stable cold fusion using the same "
                       "sand-glass material that composes Arkos's towers. Energy abundance "
                       "becomes theoretically possible — changing every economic calculation.",
    },
    {
        "subtype": "artistic",
        "title": "Cultural Breakthrough: The Shared Canvas",
        "description": "An artist has created a work that can be experienced simultaneously "
                       "by humans, Threns, Vorns, and Glims — each perceiving it differently, "
                       "each finding it complete. The work becomes a symbol of unity.",
    },
    {
        "subtype": "social",
        "title": "Social Breakthrough: The Consensus Model",
        "description": "A philosopher has published a new model of governance that doesn't "
                       "require majority rule but achieves consensus through latency resonance. "
                       "Several communities are already adopting it as their constitutional framework.",
    },
]


def check_breakthrough(
    db, world_id: str, tick_number: int
) -> Optional[Dict[str, Any]]:
    """An individual NPC makes a historically significant breakthrough."""
    base_prob = 0.0003

    # Higher probability in Mirithane (research culture) and Verge (innovation)
    if world_id == "mirithane":
        base_prob *= 1.5
    elif world_id == "verge":
        base_prob *= 1.3

    if random.random() > base_prob:
        return None

    breakthrough = random.choice(_BREAKTHROUGH_POOL)

    # Get a random NPC to be the breakthrough figure
    npc = db.execute(
        "SELECT id, name FROM agents WHERE state = 'active' AND type = 'npc' "
        "ORDER BY RANDOM() LIMIT 1"
    ).fetchone()
    npc_id = npc["id"] if npc else "unknown"
    npc_name = npc["name"] if npc else "An unknown pioneer"

    db.execute("""
        INSERT INTO great_persons (npc_id, world_id, event_type, title,
            description, impact_level, tick_number, created_at)
        VALUES (?, ?, 'breakthrough', ?, ?, ?, ?, ?)
    """, (npc_id, world_id, breakthrough["title"],
          f"{npc_name} — {breakthrough['description']}", 0.55, tick_number, time.time()))

    db.commit()

    return {
        "event_type": "breakthrough",
        "category": "cultural",
        "title": breakthrough["title"],
        "description": f"In {world_id.title()}, {npc_name} has achieved a {breakthrough['subtype']} "
                       f"breakthrough. {breakthrough['description']}",
        "importance": 0.78,
        "actor_ids": [npc_id],
        "tags": ["breakthrough", breakthrough["subtype"], "innovation", world_id],
        "payload": {
            "npc_id": npc_id,
            "npc_name": npc_name,
            "subtype": breakthrough["subtype"],
        },
    }


# ═══════════════════════════════════════════════════════════════════
# TICK INTEGRATION
# ═══════════════════════════════════════════════════════════════════

def check_all_great_persons(
    db, world_id: str, tick_number: int
) -> List[Dict[str, Any]]:
    """Run all great person checks for a world."""
    events = []

    assassination = check_assassination(db, world_id, tick_number)
    if assassination:
        events.append(assassination)

    prophecy = check_prophecy(db, world_id, tick_number)
    if prophecy:
        events.append(prophecy)

    defection = check_defection(db, world_id, tick_number)
    if defection:
        events.append(defection)

    breakthrough = check_breakthrough(db, world_id, tick_number)
    if breakthrough:
        events.append(breakthrough)

    return events


def get_great_persons_state(db, world_id: str) -> Dict[str, Any]:
    """Return great persons for dashboard."""
    rows = db.execute(
        "SELECT * FROM great_persons WHERE world_id = ? ORDER BY tick_number DESC LIMIT 5",
        (world_id,)
    ).fetchall()

    persons = []
    for r in rows:
        npc_name = db.execute(
            "SELECT name FROM agents WHERE id = ?", (r["npc_id"],)
        ).fetchone()
        persons.append({
            "npc_id": r["npc_id"],
            "npc_name": npc_name["name"] if npc_name else r["npc_id"],
            "type": r["event_type"],
            "title": r["title"],
            "impact": r["impact_level"],
            "tick": r["tick_number"],
        })

    total = db.execute(
        "SELECT COUNT(*) FROM great_persons WHERE world_id = ?", (world_id,)
    ).fetchone()[0]

    return {
        "active": persons,
        "total": total,
    }
