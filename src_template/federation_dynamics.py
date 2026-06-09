"""federation_dynamics.py — Country collapse, unification, charter reform.

Phase 6.5 Module 3: For every secession, a collapse. For every fragmentation, a unification.
The map can shrink as well as grow. The Federation itself can change.
"""

import json
import time
import random
from typing import Optional, Dict, Any, List

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]
COUNTRY_NAMES = {
    "solara": "Solara", "valdris": "Valdris", "mirithane": "Mirithane",
    "arkos": "Arkos", "verge": "The Verge",
}


# ═══════════════════════════════════════════════════════════════════
# 1. COUNTRY COLLAPSE
# ═══════════════════════════════════════════════════════════════════

def check_country_collapse(
    db,
    world_id: str,
    tick_number: int,
    growth_snapshot: Optional[dict] = None,
    conflict_state: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Check if a country should collapse through one of 5 pathways."""

    # Pathway 1: Economic death spiral
    # trade_volume < 0.1 sustained, currency_stability < 0.3
    economic_collapse_risk = _check_economic_collapse(db, world_id, growth_snapshot)

    # Pathway 2: Successful revolution
    # War-level faction controls ≥60% territory for 20+ ticks
    revolution_risk = _check_revolution_collapse(db, world_id, tick_number)

    # Pathway 3: Demographic collapse
    # Population < 20% of starting level (12,000 → < 2,400)
    demographic_risk = _check_demographic_collapse(db, world_id)

    # Pathway 4: Ecological catastrophe
    # Requires disaster chain + resource depletion
    ecological_risk = _check_ecological_collapse(db, world_id)

    # Pathway 5: Federation expulsion
    # Diplomatic relations with all others < 0.1
    federation_risk = _check_federation_expulsion(world_id)

    # Calculate overall risk
    risks = {
        "economic": economic_collapse_risk,
        "revolution": revolution_risk,
        "demographic": demographic_risk,
        "ecological": ecological_risk,
        "federation": federation_risk,
    }

    max_risk = max(risks.values())
    if max_risk < 0.7:
        return None  # No pathway active enough

    # Identify which pathway triggered
    trigger = max(risks, key=risks.get)
    risk_level = risks[trigger]

    # Collapse probability increases with risk
    prob = 0.002 * risk_level * (1.0 + max_risk)
    if random.random() > prob:
        return None

    # COLLAPSE
    country_name = COUNTRY_NAMES.get(world_id, world_id)

    # Absorbing countries — neighbors divide the territory
    neighbors = [c for c in COUNTRIES if c != world_id]
    absorbing = random.sample(neighbors, min(2, len(neighbors)))

    # Log collapse
    db.execute("""
        INSERT INTO federation_events_log (event_type, world_id, description, tick_number, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, ("country_collapse", world_id,
          f"{country_name} has collapsed via {trigger}. Territory absorbed by {', '.join(a.title() for a in absorbing)}.",
          tick_number, time.time()))

    db.commit()

    return {
        "event_type": "country_collapse",
        "category": "sovereignty",
        "title": f"{country_name} collapses",
        "description": f"The country of {country_name} has collapsed through {trigger.replace('_', ' ')}. "
                       f"Its territory is being absorbed by {', '.join(a.title() for a in absorbing)}. "
                       f"The Federation now has {len(COUNTRIES)-1} members.",
        "importance": 1.0,
        "actor_ids": [],
        "tags": ["collapse", "sovereignty", world_id, trigger],
        "payload": {
            "trigger": trigger,
            "risk_levels": risks,
            "absorbing_countries": absorbing,
            "remaining_members": len(COUNTRIES) - 1,
        },
    }


def _check_economic_collapse(db, world_id: str, growth: Optional[dict]) -> float:
    """Return economic collapse risk 0.0-1.0."""
    # Simplified: check if trade routes are mentioned in events as collapsed
    disruption_events = db.execute(
        "SELECT COUNT(*) FROM events WHERE event_type = 'trade_route_collapse' AND "
        "description LIKE ?",
        (f"%{world_id}%",)
    ).fetchone()[0]
    if disruption_events >= 3:
        return 0.8
    if disruption_events >= 1:
        return 0.4
    return 0.0


def _check_revolution_collapse(db, world_id: str, tick_number: int) -> float:
    """Return revolution collapse risk 0.0-1.0."""
    war_factions = db.execute(
        "SELECT faction_id, member_count FROM factions WHERE world_id = ? AND status = 'war'",
        (world_id,)
    ).fetchall()
    if not war_factions:
        return 0.0

    total_pop = db.execute(
        "SELECT COUNT(*) FROM agents WHERE type = 'npc' AND state = 'active'"
    ).fetchone()[0] or 1

    for f in war_factions:
        territory_control = f["member_count"] / total_pop
        if territory_control >= 0.6:
            # Check duration
            war_ticks = db.execute(
                "SELECT COUNT(*) FROM sovereignty_events WHERE faction_id = ? AND event_type LIKE '%war%'",
                (f["faction_id"],)
            ).fetchone()[0]
            if war_ticks >= 20:
                return 0.9
            if war_ticks >= 10:
                return 0.6
    return 0.0


def _check_demographic_collapse(db, world_id: str) -> float:
    """Return demographic collapse risk 0.0-1.0."""
    total_pop = db.execute(
        "SELECT COUNT(*) FROM agents WHERE type = 'npc' AND state = 'active'"
    ).fetchone()[0] or 1
    ratio = total_pop / 12000  # Starting population
    if ratio < 0.1:
        return 0.95
    if ratio < 0.2:
        return 0.7
    if ratio < 0.3:
        return 0.3
    return 0.0


def _check_ecological_collapse(db, world_id: str) -> float:
    """Return ecological collapse risk 0.0-1.0."""
    disasters = db.execute(
        "SELECT COUNT(*) FROM events WHERE event_type = 'natural_disaster' AND description LIKE ?",
        (f"%{world_id}%",)
    ).fetchone()[0]
    if disasters >= 3:
        return 0.75
    if disasters >= 1:
        return 0.3
    return 0.0


def _check_federation_expulsion(world_id: str) -> float:
    """Return federation expulsion risk 0.0-1.0."""
    # Check diplomatic relations
    relations = _load_diplomatic_relations()
    low_relations = 0
    for other in COUNTRIES:
        if other == world_id:
            continue
        pair = sorted([world_id, other])
        pair_key = f"{pair[0]}|{pair[1]}"
        trust = relations.get(pair_key, {}).get("trust", 0.5)
        if trust < 0.1:
            low_relations += 1
    # All 4 others below 0.1
    if low_relations >= 4:
        return 0.85
    if low_relations >= 3:
        return 0.4
    return 0.0


# ═══════════════════════════════════════════════════════════════════
# 2. UNIFICATION
# ═══════════════════════════════════════════════════════════════════

def check_unification(
    db,
    world_id: str,
    tick_number: int,
    diplomatic_relations: Optional[Dict[str, Dict[str, float]]] = None,
) -> Optional[Dict[str, Any]]:
    """Two countries can merge through trust, survival, or absorption."""
    if diplomatic_relations is None:
        diplomatic_relations = _load_diplomatic_relations()

    for other in COUNTRIES:
        if other == world_id:
            continue

        pair = sorted([world_id, other])
        pair_key = f"{pair[0]}|{pair[1]}"
        rels = diplomatic_relations.get(pair_key, {})
        trust = rels.get("trust", 0.5)
        cooperation = rels.get("cooperation", 0.3)

        # Pathway 1: Voluntary union
        if trust > 0.8 and cooperation > 0.7:
            prob = 0.001 * trust * cooperation
            if random.random() < prob:
                return _create_unification_event(world_id, other, "voluntary", tick_number)

        # Pathway 2: Survival merger
        # Both at collapse risk
        collapse_a = _check_demographic_collapse(db, world_id)
        collapse_b = _check_demographic_collapse(
            db, other
        ) if _suppress_db else _check_demographic_collapse(db, other)
        # Simplified: only check the current world
        if collapse_a > 0.7:
            prob = 0.005 * trust * collapse_a
            if random.random() < prob:
                return _create_unification_event(world_id, other, "survival", tick_number)

        # Pathway 3: Diplomatic absorption
        if trust > 0.7 and collapse_a > 0.5:
            prob = 0.003 * trust * collapse_a
            if random.random() < prob:
                return _create_unification_event(world_id, other, "absorption", tick_number)

    return None


def _create_unification_event(
    world_a: str, world_b: str, pathway: str, tick_number: int
) -> Dict[str, Any]:
    """Create a unification event."""
    a_name = COUNTRY_NAMES.get(world_a, world_a)
    b_name = COUNTRY_NAMES.get(world_b, world_b)
    new_name = f"The {a_name}-{b_name} Union"

    pathway_desc = {
        "voluntary": "through mutual agreement and decades of cooperation",
        "survival": "to survive mounting pressures that neither could face alone",
        "absorption": f"as {b_name} agreed to join {a_name} to preserve its people and culture",
    }

    return {
        "event_type": "unification",
        "category": "sovereignty",
        "title": f"Unification: {a_name} and {b_name} merge",
        "description": f"The countries of {a_name} and {b_name} have unified "
                       f"{pathway_desc.get(pathway, pathway)}. "
                       f"The new entity is called '{new_name}'. "
                       f"Combined population, resources, and governance. "
                       f"The Federation now has {len(COUNTRIES)-1} members.",
        "importance": 1.0,
        "actor_ids": [],
        "tags": ["unification", "sovereignty", world_a, world_b, pathway],
        "payload": {
            "country_a": world_a,
            "country_b": world_b,
            "new_name": new_name,
            "pathway": pathway,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 3. FEDERATION REFORM
# ═══════════════════════════════════════════════════════════════════

_FEDERATION_REFORMS = [
    {
        "type": "charter_revision",
        "title": "Federation Charter Revised",
        "description": "After mounting pressure from multiple member states, the Federation "
                       "Charter has been amended. The revisions address long-standing grievances "
                       "about representation, resource distribution, and type recognition.",
    },
    {
        "type": "emergency_powers",
        "title": "Federation Grants Emergency Powers",
        "description": "In response to escalating crises, the Federation has granted emergency "
                       "coordination powers to one member state. Critics call it a power grab. "
                       "Supporters say it's the only way to prevent collapse.",
    },
    {
        "type": "expansion",
        "title": "Federation Expands Representation",
        "description": "The Federation Council has voted to create a new seat — for a type, "
                       "a region, or a faction that has earned recognition. The old order shifts.",
    },
    {
        "type": "dissolution",
        "title": "The Federation Dissolves",
        "description": "The Aurelian Federation — the governing framework binding five countries "
                       "since the Collapse — has been dissolved. Each country now stands alone. "
                       "Diplomatic relations, trade agreements, and mutual defense pacts are void. "
                       "A new era begins — or an old one ends.",
    },
]


def check_federation_reform(
    db, world_id: str, tick_number: int, growth_snapshot: Optional[dict] = None
) -> Optional[Dict[str, Any]]:
    """The Federation itself can change — charter, dissolution, expansion."""
    base_prob = 0.0001

    # Higher probability with diplomatic incidents
    incidents = growth_snapshot.get("diplomatic_incidents", 0) if growth_snapshot else 0
    if incidents > 10:
        base_prob *= 3.0
    elif incidents > 5:
        base_prob *= 1.5

    if random.random() > base_prob:
        return None

    reform = random.choice(_FEDERATION_REFORMS)

    return {
        "event_type": "federation_reform",
        "category": "sovereignty",
        "title": reform["title"],
        "description": reform["description"],
        "importance": 0.95,
        "actor_ids": [],
        "tags": ["federation", "reform", reform["type"], "crisis"],
        "payload": {
            "reform_type": reform["type"],
        },
    }


# ═══════════════════════════════════════════════════════════════════
# TICK INTEGRATION
# ═══════════════════════════════════════════════════════════════════

def check_all_federation_dynamics(
    db,
    world_id: str,
    tick_number: int,
    growth_snapshot: Optional[dict] = None,
    conflict_state: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Run all federation dynamics checks for a world."""
    events = []

    # Country collapse
    collapse = check_country_collapse(db, world_id, tick_number, growth_snapshot, conflict_state)
    if collapse:
        events.append(collapse)
        return events  # Collapse is world-changing — skip other checks this tick

    # Unification (only for some countries to avoid spam — random 20% of checks)
    if random.random() < 0.2:
        unification = check_unification(db, world_id, tick_number)
        if unification:
            events.append(unification)

    # Federation reform (only one country rolls per tick — the "host")
    if world_id == random.choice(COUNTRIES):
        reform = check_federation_reform(db, world_id, tick_number, growth_snapshot)
        if reform:
            events.append(reform)

    return events


def get_collapse_risk(db, world_id: str, growth_snapshot: Optional[dict] = None) -> Dict[str, Any]:
    """Return collapse risk assessment for dashboard."""
    risks = {
        "economic": round(_check_economic_collapse(db, world_id, growth_snapshot), 2),
        "revolution": round(_check_revolution_collapse(db, world_id, 0), 2),
        "demographic": round(_check_demographic_collapse(db, world_id), 2),
        "ecological": round(_check_ecological_collapse(db, world_id), 2),
        "federation": round(_check_federation_expulsion(world_id), 2),
    }
    max_risk = max(risks.values())
    if max_risk >= 0.8:
        overall = "critical"
    elif max_risk >= 0.5:
        overall = "elevated"
    elif max_risk >= 0.2:
        overall = "low"
    else:
        overall = "stable"

    risks["overall"] = overall
    return risks


# ── Internal helpers ──────────────────────────────────────────────

_suppress_db = False  # Flag for potential db-less checks

def _load_diplomatic_relations() -> Dict[str, Dict[str, float]]:
    try:
        import sqlite3 as _sql
        cdb = _sql.connect("/Users/johann/aurelia/coordinator.db", timeout=2)
        cdb.row_factory = _sql.Row
        rows = cdb.execute(
            "SELECT relation_key, trust, tension, cooperation, trade FROM diplomatic_relations"
        ).fetchall()
        cdb.close()
        return {r["relation_key"]: {
            "trust": r["trust"], "tension": r["tension"],
            "cooperation": r["cooperation"], "trade": r["trade"],
        } for r in rows}
    except Exception:
        return {}
