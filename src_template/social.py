"""
social.py — NPC social dynamics: relationships evolve, conflicts arise, alliances form.

This system runs on simulation ticks and updates NPC relationships based on:
- Shared experiences (working together, being in the same place)
- Personality compatibility
- Events that affect multiple NPCs
- Time (relationships naturally drift)
- OWL's actions (mediating, taking sides, etc.)

Design principles:
- Relationships are fluid, not static
- Conflicts emerge from incompatibility, not scripts
- Alliances form around shared interests
- NPCs remember how OWL treats them
- Social change is gradual but meaningful
"""

import json
import random
import time
from typing import Optional

from .world_state import get_db, log_event, DB_PATH


def evolve_relationships(db, hours_passed: float = 1.0) -> list:
    """
    Evolve NPC relationships based on current world state.
    Returns a list of notable changes.
    """
    changes = []
    now = time.time()

    # Get all NPC relationships
    relationships = db.execute("""
        SELECT r.*, a1.name as name_a, a1.properties as props_a,
               a2.name as name_b, a2.properties as props_b,
               a1.location_id as loc_a, a2.location_id as loc_b
        FROM npc_relationships r
        JOIN agents a1 ON r.npc_a = a1.id
        JOIN agents a2 ON r.npc_b = a2.id
    """).fetchall()

    for rel in relationships:
        affinity = rel["affinity"]
        rel_type = rel["relationship"]
        old_affinity = affinity

        # ── PROXIMITY EFFECT ──
        # NPCs in the same location get closer
        if rel["loc_a"] == rel["loc_b"]:
            affinity += 0.002 * hours_passed

        # ── PERSONALITY COMPATIBILITY ──
        try:
            props_a = json.loads(rel["props_a"]) if rel["props_a"] else {}
            props_b = json.loads(rel["props_b"]) if rel["props_b"] else {}
            traits_a = props_a.get("traits", [])
            traits_b = props_b.get("traits", [])

            # Shared traits increase affinity
            shared_traits = set(traits_a) & set(traits_b)
            if shared_traits:
                affinity += 0.001 * len(shared_traits) * hours_passed

            # Opposing traits decrease affinity
            opposites = [
                ("warm", "reserved"), ("boisterous", "quiet"), ("optimistic", "pessimistic"),
                ("gregarious", "solitary"), ("bold", "timid"), ("serious", "playful"),
                ("traditional", "progressive"), ("spiritual", "skeptical"),
            ]
            for t1, t2 in opposites:
                if (t1 in traits_a and t2 in traits_b) or (t2 in traits_a and t1 in traits_b):
                    affinity -= 0.001 * hours_passed
        except (json.JSONDecodeError, TypeError):
            pass

        # ── RELATIONSHIP TYPE DRIFT ──
        # Relationships naturally evolve over time
        if rel_type == "acquaintance":
            if affinity > 0.6:
                rel_type = "friend"
            elif affinity < 0.2:
                rel_type = "rival"
        elif rel_type == "friend":
            if affinity > 0.8:
                rel_type = "close_friend"
            elif affinity < 0.3:
                rel_type = "acquaintance"
        elif rel_type == "close_friend":
            if affinity > 0.9:
                rel_type = "family"  # As close as family
            elif affinity < 0.5:
                rel_type = "friend"
        elif rel_type == "rival":
            if affinity < 0.1:
                rel_type = "enemy"
            elif affinity > 0.4:
                rel_type = "acquaintance"
        elif rel_type == "potential_romance":
            if affinity > 0.7:
                rel_type = "romance"
            elif affinity < 0.3:
                rel_type = "acquaintance"
        elif rel_type == "romance":
            if affinity > 0.85:
                rel_type = "married"
            elif affinity < 0.4:
                rel_type = "acquaintance"
                changes.append({
                    "type": "breakup",
                    "description": f"{rel['name_a']} and {rel['name_b']} have parted ways. It's sad to see.",
                })

        # ── RANDOM EVENTS ──
        # Small random drift
        affinity += random.uniform(-0.005, 0.005) * hours_passed

        # Clamp
        affinity = max(0.0, min(1.0, affinity))

        # Save if changed
        if abs(affinity - old_affinity) > 0.001 or rel_type != rel["relationship"]:
            db.execute("""
                UPDATE npc_relationships SET affinity = ?, relationship = ?, description = ?
                WHERE id = ?
            """, (round(affinity, 3), rel_type, rel_type.replace("_", " "), rel["id"]))

        # Notable changes
        if abs(affinity - old_affinity) > 0.05:
            direction = "closer" if affinity > old_affinity else "more distant"
            changes.append({
                "type": "relationship_shift",
                "description": f"{rel['name_a']} and {rel['name_b']} have grown {direction}.",
                "npc_a": rel["name_a"],
                "npc_b": rel["name_b"],
                "old_affinity": round(old_affinity, 2),
                "new_affinity": round(affinity, 2),
            })

    db.commit()
    return changes


def generate_alliances(db) -> list:
    """
    Detect and form alliances between NPCs with shared interests.
    Returns a list of new alliances.
    """
    alliances = []

    # Find NPCs in the same location with high affinity but no formal relationship
    rows = db.execute("""
        SELECT a1.id as id_a, a1.name as name_a, a1.properties as props_a,
               a2.id as id_b, a2.name as name_b, a2.properties as props_b,
               a1.location_id
        FROM agents a1
        JOIN agents a2 ON a1.location_id = a2.location_id AND a1.id < a2.id
        WHERE a1.type = 'npc' AND a2.type = 'npc'
    """).fetchall()

    for row in rows:
        # Check if they already have a relationship
        existing = db.execute("""
            SELECT COUNT(*) as cnt FROM npc_relationships
            WHERE (npc_a = ? AND npc_b = ?) OR (npc_a = ? AND npc_b = ?)
        """, (row["id_a"], row["id_b"], row["id_b"], row["id_a"])).fetchone()

        if existing[0] == 0:
            # Check for shared occupation or interests
            try:
                props_a = json.loads(row["props_a"]) if row["props_a"] else {}
                props_b = json.loads(row["props_b"]) if row["props_b"] else {}
                occ_a = props_a.get("occupation", "")
                occ_b = props_b.get("occupation", "")

                if occ_a == occ_b:
                    # Same occupation — natural alliance
                    affinity = random.uniform(0.3, 0.6)
                    db.execute("""
                        INSERT INTO npc_relationships (npc_a, npc_b, relationship, affinity, description)
                        VALUES (?, ?, 'coworker', ?, ?)
                    """, (row["id_a"], row["id_b"], affinity, f"coworkers"))

                    alliances.append({
                        "type": "new_alliance",
                        "description": f"{row['name_a']} and {row['name_b']} have formed a bond as fellow {occ_a}s.",
                    })
            except (json.JSONDecodeError, TypeError):
                pass

    db.commit()
    return alliances


def detect_conflicts(db) -> list:
    """
    Detect emerging conflicts between NPCs.
    Returns a list of new conflicts.
    """
    conflicts = []

    # Find NPCs with low affinity who are forced to interact
    rows = db.execute("""
        SELECT r.id, r.npc_a, r.npc_b, r.affinity, r.relationship,
               a1.name as name_a, a2.name as name_b,
               a1.location_id as loc_a, a2.location_id as loc_b
        FROM npc_relationships r
        JOIN agents a1 ON r.npc_a = a1.id
        JOIN agents a2 ON r.npc_b = a2.id
        WHERE r.affinity < 0.3 AND r.relationship NOT IN ('rival', 'enemy')
    """).fetchall()

    for row in rows:
        # If they're in the same location, conflict is more likely
        if row["loc_a"] == row["loc_b"] and random.random() < 0.1:
            db.execute("""
                UPDATE npc_relationships SET relationship = 'rival', description = 'rival'
                WHERE id = ?
            """, (row["id"],))

            conflicts.append({
                "type": "new_conflict",
                "description": f"Tension between {row['name_a']} and {row['name_b']} has boiled over into open rivalry.",
            })

    db.commit()
    return conflicts


def get_relationship_web(db, npc_id: str) -> dict:
    """Get the full relationship web for an NPC."""
    relationships = db.execute("""
        SELECT r.*,
               CASE WHEN r.npc_a = ? THEN a2.name ELSE a1.name as other_name,
               CASE WHEN r.npc_a = ? THEN a2.id ELSE a1.id as other_id
        FROM npc_relationships r
        JOIN agents a1 ON r.npc_a = a1.id
        JOIN agents a2 ON r.npc_b = a2.id
        WHERE r.npc_a = ? OR r.npc_b = ?
        ORDER BY r.affinity DESC
    """, (npc_id, npc_id, npc_id, npc_id)).fetchall()

    return {
        "allies": [dict(r) for r in relationships if r["affinity"] > 0.6],
        "friends": [dict(r) for r in relationships if 0.4 < r["affinity"] <= 0.6],
        "neutral": [dict(r) for r in relationships if 0.2 <= r["affinity"] <= 0.4],
        "rivals": [dict(r) for r in relationships if r["affinity"] < 0.2],
    }
