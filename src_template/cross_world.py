"""cross_world.py — NPC border crossings, migration, and asylum.

Phase 6.6 Module 4: NPCs can cross between countries. The 5 sealed containers
become a single world with permeable borders. Every border crossing is a decision,
not a timer — fueled by push factors from decision state and pull factors from
target country conditions.
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

# Border adjacency — which countries share borders
BORDERS = {
    "solara": ["valdris", "mirithane", "verge"],
    "valdris": ["solara", "arkos", "mirithane"],
    "mirithane": ["solara", "valdris", "arkos", "verge"],
    "arkos": ["valdris", "mirithane"],
    "verge": ["solara", "mirithane"],
}

# Pull factors per country
PULL_FACTORS = {
    "solara": {"economic": 0.6, "security": 0.5, "freedom": 0.2, "type_acceptance": {"human": 0.8, "thren": 0.2, "vorn": 0.4, "glim": 0.1}},
    "valdris": {"economic": 0.7, "security": 0.4, "freedom": 0.5, "type_acceptance": {"human": 0.7, "thren": 0.5, "vorn": 0.4, "glim": 0.2}},
    "mirithane": {"economic": 0.5, "security": 0.6, "freedom": 0.6, "type_acceptance": {"human": 0.8, "thren": 0.7, "vorn": 0.6, "glim": 0.3}},
    "arkos": {"economic": 0.6, "security": 0.5, "freedom": 0.4, "type_acceptance": {"human": 0.7, "thren": 0.6, "vorn": 0.9, "glim": 0.7}},
    "verge": {"economic": 0.2, "security": 0.2, "freedom": 0.9, "type_acceptance": {"human": 0.8, "thren": 0.8, "vorn": 0.8, "glim": 0.9}},
}


def check_cross_world_movement(
    db,
    world_id: str,
    tick_number: int,
    diplomatic_relations: Optional[Dict[str, Dict[str, float]]] = None,
    max_migrants: int = 10,
) -> List[Dict[str, Any]]:
    """Check for NPCs wanting to cross borders this tick.

    Returns list of cross-world event dicts.
    """
    events = []

    if diplomatic_relations is None:
        diplomatic_relations = _load_diplomatic_relations()

    # Find NPCs with push factors strong enough to consider leaving
    push_candidates = db.execute("""
        SELECT a.id, a.name, a.type, a.location_id,
               ds.variables
        FROM agents a
        JOIN npc_decision_state ds ON a.id = ds.npc_id
        WHERE a.state = 'active' AND a.type = 'npc'
        AND (
            CAST(json_extract(ds.variables, '$.security') AS REAL) < 0.3
            OR CAST(json_extract(ds.variables, '$.restlessness') AS REAL) > 0.7
            OR CAST(json_extract(ds.variables, '$.satisfaction') AS REAL) < 0.25
            OR CAST(json_extract(ds.variables, '$.economic_stability') AS REAL) < 0.3
        )
        ORDER BY RANDOM() LIMIT 50
    """).fetchall()

    migrated = 0
    for npc in push_candidates:
        if migrated >= max_migrants:
            break

        npc_id = npc["id"]
        npc_type = (npc["type"] or "human").lower()
        try:
            ds = json.loads(npc["variables"]) if isinstance(npc["variables"], str) else npc["variables"]
        except (json.JSONDecodeError, TypeError):
            ds = {}

        # Choose target from border-adjacent countries
        neighbors = BORDERS.get(world_id, [])
        if not neighbors:
            continue

        # Score each neighbor
        scores = []
        for target in neighbors:
            score = _score_destination(target, npc_type, ds, diplomatic_relations, world_id)
            scores.append((target, score))

        if not scores:
            continue

        best_target, best_score = max(scores, key=lambda x: x[1])
        if best_score < 0.3:  # Not compelling enough
            continue

        # Migration probability
        base_prob = 0.02  # 2% per qualifying NPC per tick
        push_mult = (1.0 - ds.get("security", 0.5)) + ds.get("restlessness", 0.3)
        prob = base_prob * push_mult * (1.0 + best_score)

        if random.random() > prob:
            continue

        # Migrate
        _migrate_npc(db, npc_id, world_id, best_target, tick_number)
        migrated += 1

        # Determine migration type
        ds_security = ds.get("security", 0.5)
        if ds_security < 0.2 and npc_type == "glim":
            migration_type = "asylum"
            description = f"Glim {npc['name']} flees {world_id.title()} for sanctuary in {COUNTRY_NAMES.get(best_target, best_target)}."
        elif ds_security < 0.3:
            migration_type = "refugee"
            description = f"{npc['name']} seeks refuge in {COUNTRY_NAMES.get(best_target, best_target)}."
        else:
            migration_type = "migration"
            description = f"{npc['name']} migrates from {world_id.title()} to {COUNTRY_NAMES.get(best_target, best_target)}."

        events.append({
            "event_type": "cross_world_migration",
            "category": "population",
            "title": f"{migration_type.title()}: {npc['name']} → {COUNTRY_NAMES.get(best_target, best_target)}",
            "description": description,
            "importance": 0.4 if migration_type == "migration" else 0.65,
            "actor_ids": [npc_id],
            "tags": ["migration", migration_type, world_id, best_target],
            "payload": {
                "npc_id": npc_id,
                "npc_name": npc["name"],
                "npc_type": npc_type,
                "source": world_id,
                "target": best_target,
                "type": migration_type,
            },
        })

        # If asylum seeker, generate diplomatic incident
        if migration_type == "asylum":
            events.append({
                "event_type": "asylum_claim",
                "category": "diplomacy",
                "title": f"Asylum tension: {world_id.title()} — {COUNTRY_NAMES.get(best_target, best_target)}",
                "description": f"{world_id.title()} demands the return of {npc['name']}, "
                               f"a Glim who fled to {COUNTRY_NAMES.get(best_target, best_target)}. "
                               f"The asylum claim strains diplomatic relations.",
                "importance": 0.75,
                "actor_ids": [npc_id],
                "tags": ["asylum", "diplomacy", "tension", world_id, best_target],
                "payload": {"source": world_id, "target": best_target, "npc_id": npc_id},
            })

    if migrated > 0:
        db.commit()

    return events


def _score_destination(
    target: str,
    npc_type: str,
    push_state: Dict[str, float],
    diplomatic_relations: Dict[str, Dict[str, float]],
    source: str,
) -> float:
    """Score how attractive a destination is for this NPC."""
    pull = PULL_FACTORS.get(target, PULL_FACTORS["verge"])

    # Type acceptance — how welcome would this type be?
    type_acceptance = pull.get("type_acceptance", {}).get(npc_type, 0.5)

    # Economic pull — weighted by NPC's economic_stability need
    economic_need = 1.0 - push_state.get("economic_stability", 0.55)
    economic_score = pull.get("economic", 0.5) * economic_need

    # Freedom pull — weighted by NPC's restlessness
    freedom_need = push_state.get("restlessness", 0.2)
    freedom_score = pull.get("freedom", 0.5) * freedom_need

    # Security pull — weighted by NPC's security deficit
    security_need = 1.0 - push_state.get("security", 0.7)
    security_score = pull.get("security", 0.5) * security_need

    # Diplomatic relations modifier — easier to go to friendly countries
    pair = sorted([source, target])
    pair_key = f"{pair[0]}|{pair[1]}"
    trust = diplomatic_relations.get(pair_key, {}).get("trust", 0.5)
    diplomatic_score = trust * 0.5

    # Glim-specific: Verge has highest Glim acceptance
    if npc_type == "glim":
        if target == "verge":
            type_acceptance += 0.3
        elif target == "arkos":
            type_acceptance += 0.15

    return (type_acceptance * 0.3 + economic_score * 0.2 + freedom_score * 0.2 +
            security_score * 0.2 + diplomatic_score * 0.1)


def _migrate_npc(db, npc_id: str, source: str, target: str, tick_number: int):
    """Execute an NPC migration between worlds."""
    # Update NPC nationality
    db.execute("""
        UPDATE agents
        SET properties = json_set(
            COALESCE(properties, '{}'),
            '$.nationality', ?,
            '$.previous_nationality', json_extract(COALESCE(properties, '{}'), '$.nationality')
        )
        WHERE id = ?
    """, (target, npc_id))

    # Log the migration
    db.execute("""
        INSERT OR IGNORE INTO cross_world_movements (npc_id, source_world, target_world, movement_type, tick_number, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (npc_id, source, target, "migration", tick_number, time.time()))


def get_migration_state(db, world_id: str) -> Dict[str, Any]:
    """Return migration statistics for dashboard."""
    emigrants = db.execute(
        "SELECT COUNT(*) FROM cross_world_movements WHERE source_world = ?", (world_id,)
    ).fetchone()[0]
    immigrants = db.execute(
        "SELECT COUNT(*) FROM cross_world_movements WHERE target_world = ?", (world_id,)
    ).fetchone()[0]

    return {
        "emigrants": emigrants,
        "immigrants": immigrants,
        "net": immigrants - emigrants,
    }


# ── Helpers ────────────────────────────────────────────────────────

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
