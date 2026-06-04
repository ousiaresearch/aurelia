"""faction_engine.py — Faction formation, membership, and influence.

Phase 6 Module 1: Turns individual NPC grievances into organized collective action.
Factions form when grievance density crosses a threshold in a region — never on a timer.
Consumes Phase 4 decision_state, feeds the escalation ladder and sovereignty pipeline.
"""

import json
import time
import random
from typing import Optional, Dict, Any, List, Tuple

# ── Grievance definitions ──────────────────────────────────────────

GRIEVANCE_TYPES = {
    "oppression": {
        "label": "Oppression",
        "check": lambda ds: ds.get("security", 0.5) < 0.3 and ds.get("observed_injustice", 0) > 0.5,
        "demands": [
            "End the decommissioning of sentient beings",
            "Abolish the surveillance and containment apparatus",
            "Full legal rights for all citizens regardless of type",
        ],
    },
    "poverty": {
        "label": "Poverty",
        "check": lambda ds: ds.get("satisfaction", 0.5) < 0.3 and ds.get("economic_stability", 0.5) < 0.3,
        "demands": [
            "Land reform and redistribution of resources",
            "Universal basic income and debt forgiveness",
            "Worker ownership of production",
        ],
    },
    "displacement": {
        "label": "Displacement",
        "check": lambda ds: ds.get("restlessness", 0) > 0.7,
        "demands": [
            "Right of return to ancestral territories",
            "Compensation for forced relocation",
            "Recognition of displaced communities",
        ],
    },
    "personhood": {
        "label": "Personhood",
        "check": lambda ds: ds.get("anomaly_pressure", 0) > 0.5 and ds.get("observed_injustice", 0) > 0.3,
        "demands": [
            "Recognition of Glim personhood and legal standing",
            "Representation in all governing bodies",
            "End mandatory decommissioning at threshold age",
        ],
    },
    "autonomy": {
        "label": "Autonomy",
        "check": lambda ds: ds.get("connectedness", 0) > 0.7 and ds.get("restlessness", 0) > 0.4,
        "demands": [
            "Regional autonomy and self-governance",
            "Control over local resources and taxation",
            "Cultural and linguistic recognition",
        ],
    },
}

# Minimum NPCs in same region with same grievance to trigger formation check
FORMATION_THRESHOLD = 10

# Cooldown between faction formation checks in the same region (ticks)
FORMATION_COOLDOWN_TICKS = 10
_formation_cooldowns: Dict[str, int] = {}


def _faction_id(world_id: str, name: str) -> str:
    """Create a stable faction ID."""
    slug = name.lower().replace(" ", "-")[:40]
    return f"{world_id}:faction:{slug}:{int(time.time())}"


def scan_grievance_density(
    db,
    world_id: str,
    region: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Scan NPC decision states for grievance density by region and type.

    Returns: {grievance_type: {"region": str, "count": int, "npc_ids": [...]}}
    """
    rows = db.execute(
        "SELECT npc_id, variables FROM npc_decision_state"
    ).fetchall()

    # Group NPCs by location region
    npc_locations = {}
    loc_rows = db.execute(
        "SELECT id, location_id FROM agents WHERE type != 'player'"
    ).fetchall()
    for r in loc_rows:
        npc_id = r["id"]
        loc = r["location_id"] or "unknown"
        # Derive region from location — first component or parent area
        region_tag = loc.split("_")[0] if "_" in loc else loc
        if region and region_tag != region:
            continue
        npc_locations[npc_id] = region_tag

    # Count grievance density
    density: Dict[str, Dict[str, Any]] = {}
    for gt_key, gt_def in GRIEVANCE_TYPES.items():
        density[gt_key] = {"count": 0, "npc_ids": [], "regions": {}}

    for row in rows:
        npc_id = row["npc_id"]
        region_tag = npc_locations.get(npc_id, "unknown")
        try:
            ds = json.loads(row["variables"]) if isinstance(row["variables"], str) else row["variables"]
        except (json.JSONDecodeError, TypeError):
            continue

        for gt_key, gt_def in GRIEVANCE_TYPES.items():
            try:
                if gt_def["check"](ds):
                    density[gt_key]["count"] += 1
                    density[gt_key]["npc_ids"].append(npc_id)
                    density[gt_key]["regions"].setdefault(region_tag, 0)
                    density[gt_key]["regions"][region_tag] += 1
            except Exception:
                continue

    return density


def check_faction_formation(
    db,
    world_id: str,
    tick_number: int,
    growth_snapshot: Optional[dict] = None,
) -> Optional[dict]:
    """Check if conditions are ripe for a new faction to form.

    Returns a faction formation event dict, or None.
    """
    # Cooldown check
    cooldown_key = f"{world_id}:formation"
    if cooldown_key in _formation_cooldowns:
        if tick_number - _formation_cooldowns[cooldown_key] < FORMATION_COOLDOWN_TICKS:
            return None

    density = scan_grievance_density(db, world_id)

    # Find the strongest grievance by count
    best = None
    best_count = 0
    best_region = None

    for gt_key, data in density.items():
        for region, count in data.get("regions", {}).items():
            if count >= FORMATION_THRESHOLD and count > best_count:
                best = gt_key
                best_count = count
                best_region = region

    if not best:
        return None

    # Base probability modified by grievance density and world state
    base_prob = 0.003  # 0.3% per tick when threshold met
    density_mult = min(best_count / FORMATION_THRESHOLD, 5.0)
    prob = base_prob * density_mult

    # Modifiers from growth snapshot
    if growth_snapshot:
        anomalies = growth_snapshot.get("glim_anomaly_signals", 0)
        incidents = growth_snapshot.get("diplomatic_incidents", 0)
        if anomalies > 0:
            prob *= 1.5
        if incidents > 5:
            prob *= 1.3

    if random.random() > prob:
        return None

    # Form the faction
    gt_def = GRIEVANCE_TYPES[best]
    demand = random.choice(gt_def["demands"])
    region_str = best_region or "unknown"
    name = _generate_faction_name(best, region_str, world_id, db)

    # Pick initial members — up to 20 most-aligned NPCs in the region
    candidate_npcs = density[best]["npc_ids"][:50]  # First 50 matching NPCs
    initial_members = _pick_initial_members(db, candidate_npcs, region_str, max_members=20)

    # Pick leader — highest-influence among initial members
    leader_id = _pick_leader(db, initial_members)

    faction_id = _faction_id(world_id, name)

    # Insert faction record
    now = time.time()
    db.execute("""
        INSERT INTO factions (faction_id, name, world_id, region, status,
            primary_grievance, demand, leader_npc_id, member_count,
            influence, founded_tick, metadata, created_at)
        VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, 0.1, ?, '{}', ?)
    """, (faction_id, name, world_id, best_region, best, demand, leader_id,
          len(initial_members), tick_number, now))

    # Insert members
    for npc_id in initial_members:
        db.execute("""
            INSERT OR IGNORE INTO faction_members (faction_id, npc_id, joined_tick, role)
            VALUES (?, ?, ?, ?)
        """, (faction_id, npc_id, tick_number, "leader" if npc_id == leader_id else "member"))

    db.commit()
    _formation_cooldowns[cooldown_key] = tick_number

    return {
        "event_type": "faction_formed",
        "category": "governance",
        "title": f"Faction formed: {name}",
        "description": f"A new faction has organized in {best_region}, {world_id}: "
                       f"'{name}' demands {demand.lower()}. "
                       f"{len(initial_members)} members under {_get_npc_name(db, leader_id)}.",
        "importance": 0.75,
        "actor_ids": [leader_id] if leader_id else [],
        "tags": ["faction", "formation", best, best_region, world_id],
        "payload": {
            "faction_id": faction_id,
            "name": name,
            "grievance": best,
            "region": best_region,
            "member_count": len(initial_members),
            "leader_id": leader_id,
        },
    }


def update_all_factions(db, world_id: str, tick_number: int):
    """Per-tick maintenance: update influence, recruit, dissolve dead factions."""
    factions = db.execute(
        "SELECT * FROM factions WHERE world_id = ? AND status != 'dissolved' AND status != 'sovereign'",
        (world_id,)
    ).fetchall()

    for f in factions:
        fid = f["faction_id"]
        # Update member count
        member_count = db.execute(
            "SELECT COUNT(*) FROM faction_members WHERE faction_id = ?", (fid,)
        ).fetchone()[0]
        db.execute(
            "UPDATE factions SET member_count = ? WHERE faction_id = ?",
            (member_count, fid)
        )

        # Recalculate influence
        influence = _calculate_influence(db, fid)
        db.execute(
            "UPDATE factions SET influence = ? WHERE faction_id = ?",
            (influence, fid)
        )

        # Leader check — if leader dead, pick new one
        leader = f["leader_npc_id"]
        if leader:
            alive = db.execute(
                "SELECT 1 FROM agents WHERE id = ? AND state = 'active'", (leader,)
            ).fetchone()
            if not alive:
                members = db.execute(
                    "SELECT npc_id FROM faction_members WHERE faction_id = ? AND role != 'leader'",
                    (fid,)
                ).fetchall()
                member_ids = [m["npc_id"] for m in members]
                new_leader = _pick_leader(db, member_ids)
                if new_leader:
                    db.execute(
                        "UPDATE faction_members SET role = 'member' WHERE faction_id = ? AND npc_id = ?",
                        (fid, leader)
                    )
                    db.execute(
                        "UPDATE faction_members SET role = 'leader' WHERE faction_id = ? AND npc_id = ?",
                        (fid, new_leader)
                    )
                    db.execute(
                        "UPDATE factions SET leader_npc_id = ? WHERE faction_id = ?",
                        (new_leader, fid)
                    )

        # Recruitment — chance to add new members
        if random.random() < 0.1:  # 10% chance per tick
            _recruit_new_members(db, fid, world_id, tick_number, f["region"])

        # Dissolve if member count drops below 3
        if member_count < 3:
            db.execute(
                "UPDATE factions SET status = 'dissolved', dissolved_tick = ? WHERE faction_id = ?",
                (tick_number, fid)
            )
            db.execute("DELETE FROM faction_members WHERE faction_id = ?", (fid,))

    db.commit()


def get_active_factions(db, world_id: str) -> List[Dict[str, Any]]:
    """Return all active factions for a world."""
    rows = db.execute(
        "SELECT * FROM factions WHERE world_id = ? AND status IN ('active', 'forming', 'ultimatum', 'skirmish', 'armed_conflict')",
        (world_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# ── Internal helpers ──────────────────────────────────────────────


def _generate_faction_name(grievance: str, region: str, world_id: str, db) -> str:
    """Generate a faction name from grievance + region + flavor."""
    gt = GRIEVANCE_TYPES.get(grievance, {})
    label = gt.get("label", grievance.title())

    # Try to use a member name as flavor
    prefixes = [
        f"The {region.title()} {label} Front",
        f"{label} Collective of {region.title()}",
        f"The {region.title()} Liberation Movement",
        f"{label} Union of {region.title()}",
        f"Free {region.title()} Coalition",
    ]
    return random.choice(prefixes)


def _pick_initial_members(db, candidate_ids: List[str], region: str, max_members: int = 20) -> List[str]:
    """Select the most-aligned NPCs from candidates, limited to those in the region."""
    members = []
    for npc_id in candidate_ids:
        if len(members) >= max_members:
            break
        # Verify NPC exists and is active
        row = db.execute(
            "SELECT id, location_id FROM agents WHERE id = ? AND state = 'active'",
            (npc_id,)
        ).fetchone()
        if not row:
            continue
        loc = row["location_id"] or ""
        region_tag = loc.split("_")[0] if "_" in loc else loc
        if region_tag == region:
            members.append(npc_id)
    return members


def _pick_leader(db, npc_ids: List[str]) -> Optional[str]:
    """Pick the NPC with highest influence (connectedness + security) as leader."""
    best_id = None
    best_score = -1
    for npc_id in npc_ids:
        row = db.execute(
            "SELECT variables FROM npc_decision_state WHERE npc_id = ?", (npc_id,)
        ).fetchone()
        if not row:
            continue
        try:
            ds = json.loads(row["variables"]) if isinstance(row["variables"], str) else row["variables"]
        except (json.JSONDecodeError, TypeError):
            continue
        score = ds.get("connectedness", 0) + ds.get("security", 0)
        if score > best_score:
            best_score = score
            best_id = npc_id
    return best_id


def _get_npc_name(db, npc_id: str) -> str:
    """Get NPC name from agents table."""
    row = db.execute("SELECT name FROM agents WHERE id = ?", (npc_id,)).fetchone()
    return row["name"] if row else npc_id


def _calculate_influence(db, faction_id: str) -> float:
    """Calculate faction influence from member states."""
    members = db.execute(
        "SELECT npc_id FROM faction_members WHERE faction_id = ?", (faction_id,)
    ).fetchall()
    if not members:
        return 0.0

    total = 0.0
    for m in members:
        row = db.execute(
            "SELECT variables FROM npc_decision_state WHERE npc_id = ?", (m["npc_id"],)
        ).fetchone()
        if not row:
            continue
        try:
            ds = json.loads(row["variables"]) if isinstance(row["variables"], str) else row["variables"]
        except (json.JSONDecodeError, TypeError):
            continue
        # Influence per member: (1 - security) * (1 + connectedness)
        sec = ds.get("security", 0.5)
        conn = ds.get("connectedness", 0.5)
        total += (1.0 - sec) * (1.0 + conn)

    return total / max(len(members), 1)


def _recruit_new_members(db, faction_id: str, world_id: str, tick_number: int, region: str):
    """Recruit unaffiliated NPCs in the same region who share the grievance."""
    f = db.execute("SELECT primary_grievance, member_count FROM factions WHERE faction_id = ?", (faction_id,)).fetchone()
    if not f:
        return
    grievance = f["primary_grievance"]
    gt_def = GRIEVANCE_TYPES.get(grievance)
    if not gt_def:
        return

    # Find unaffiliated NPCs in region with matching grievance
    existing = set(
        r[0] for r in db.execute(
            "SELECT npc_id FROM faction_members WHERE faction_id = ?", (faction_id,)
        ).fetchall()
    )

    candidates = db.execute(
        "SELECT a.id, a.location_id, ds.variables FROM agents a "
        "JOIN npc_decision_state ds ON a.id = ds.npc_id "
        "WHERE a.type != 'player' AND a.state = 'active'"
    ).fetchall()

    recruited = 0
    for c in candidates:
        if c["id"] in existing:
            continue
        if recruited >= 5:  # Max 5 new members per recruitment tick
            break

        loc = c["location_id"] or ""
        region_tag = loc.split("_")[0] if "_" in loc else loc
        if region_tag != region:
            continue

        try:
            ds = json.loads(c["variables"]) if isinstance(c["variables"], str) else c["variables"]
        except (json.JSONDecodeError, TypeError):
            continue

        try:
            if gt_def["check"](ds):
                # Join probability based on alignment strength
                join_prob = 0.3
                if ds.get("observed_injustice", 0) > 0.7:
                    join_prob += 0.3
                if ds.get("restlessness", 0) > 0.5:
                    join_prob += 0.2

                if random.random() < join_prob:
                    db.execute(
                        "INSERT OR IGNORE INTO faction_members (faction_id, npc_id, joined_tick, role) "
                        "VALUES (?, ?, ?, 'member')",
                        (faction_id, c["id"], tick_number)
                    )
                    recruited += 1
        except Exception:
            continue

    if recruited > 0:
        db.commit()
