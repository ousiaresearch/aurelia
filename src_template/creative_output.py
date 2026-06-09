"""
Creative output pipeline — completed projects become world artifacts,
visible to NPCs, and trigger reactions and events.
"""

import time
import uuid
import random
from typing import Optional


# ── Schema ────────────────────────────────────────────────────────────────────

def init_creative_output(db) -> None:
    """Ensure creative_output table exists (it should from world_state init)."""
    # Table is created in world_state; this just ensures it exists
    db.execute("""
        CREATE TABLE IF NOT EXISTS creative_output (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL DEFAULT 'isildur',
            type TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'Untitled',
            content TEXT NOT NULL DEFAULT '',
            location_id TEXT DEFAULT NULL,
            state TEXT DEFAULT 'completed',
            properties TEXT DEFAULT '{}',
            reactions_count INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS creative_reactions (
            id TEXT PRIMARY KEY,
            output_id TEXT NOT NULL,
            npc_id TEXT NOT NULL,
            reaction_type TEXT NOT NULL,
            comment TEXT DEFAULT '',
            created_at REAL NOT NULL,
            FOREIGN KEY (output_id) REFERENCES creative_output(id) ON DELETE CASCADE
        )
    """)
    db.commit()


def _resolve_player_id(db, fallback: str = "owl") -> str:
    """Return the active player id for legacy-safe helper defaults."""
    try:
        row = db.execute("SELECT id FROM agents WHERE type = 'player' ORDER BY created_at ASC LIMIT 1").fetchone()
        if row:
            return row["id"]
    except Exception:
        pass
    return fallback


# ── Record output ─────────────────────────────────────────────────────────────

def record_completed_project(db, project: dict) -> dict:
    """
    When a project completes, record it as a creative output in the world.
    This makes it visible to NPCs and queryable by the simulation.
    Returns the created output record.
    """
    now = time.time()
    oid = f"cout_{uuid.uuid4().hex[:8]}"

    props = {}
    try:
        import json
        pprops = project.get("properties", "{}")
        if isinstance(pprops, str):
            props = json.loads(pprops)
        elif isinstance(pprops, dict):
            props = pprops
    except Exception:
        props = {"original_project": project.get("id", "")}

    creator_id = project.get("creator_id") or _resolve_player_id(db)

    db.execute("""
        INSERT INTO creative_output (id, creator_id, type, title, content, location_id, state, properties, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?)
    """, (
        oid,
        creator_id,
        project.get("type", "craft"),
        project.get("item_name", project.get("title", "Untitled")),
        project.get("completion_description", project.get("content", "")),
        project.get("location_id"),
        json.dumps(props),
        now,
        now,
    ))
    db.commit()

    # Log it as an event
    from src.world_state import log_event
    log_event(
        db, "creative_complete",
        f"Created: {project.get('item_name', 'Untitled')}",
        agent_id=creator_id,
        location_id=project.get("location_id"),
        properties={"output_id": oid, "type": project.get("type"), "quality": props.get("quality", 0)}
    )

    return get_creative_output(db, oid)


def get_creative_output(db, output_id: str) -> Optional[dict]:
    row = db.execute("SELECT * FROM creative_output WHERE id = ?", (output_id,)).fetchone()
    if not row:
        return None
    out = dict(row)
    try:
        import json
        out["properties"] = json.loads(out.get("properties", "{}"))
    except Exception:
        out["properties"] = {}
    out["reactions"] = get_reactions(db, output_id)
    return out


def get_recent_outputs(db, creator_id: Optional[str] = None, limit: int = 20) -> list:
    """Get recent creative outputs, optionally filtered by creator. Defaults to active player."""
    if creator_id is None:
        creator_id = _resolve_player_id(db)
    if creator_id:
        rows = db.execute("""
            SELECT * FROM creative_output
            WHERE creator_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (creator_id, limit)).fetchall()
    else:
        rows = db.execute("""
            SELECT * FROM creative_output
            ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
    outputs = []
    for row in rows:
        out = dict(row)
        try:
            import json
            out["properties"] = json.loads(out.get("properties", "{}"))
        except Exception:
            out["properties"] = {}
        outputs.append(out)
    return outputs


def get_outputs_by_type(db, output_type: str, limit: int = 20) -> list:
    rows = db.execute("""
        SELECT * FROM creative_output
        WHERE type = ?
        ORDER BY created_at DESC LIMIT ?
    """, (output_type, limit)).fetchall()
    outputs = []
    for row in rows:
        out = dict(row)
        try:
            import json
            out["properties"] = json.loads(out.get("properties", "{}"))
        except Exception:
            out["properties"] = {}
        outputs.append(out)
    return outputs


# ── NPC Reactions ──────────────────────────────────────────────────────────────

REACTION_TYPES = [
    "admires", "asks_about", "requests", "comments_on",
    "wants_to_trade", "mentions_to_others", "inspired_by"
]

REACTION_COMMENTS = {
    "admires": [
        "That's remarkable work.",
        "I've never seen the like.",
        "Beautiful craftsmanship.",
    ],
    "asks_about": [
        "How long did that take you?",
        "Where did you learn that?",
        "What wood is that?",
    ],
    "requests": [
        "Would you make me one someday?",
        "I could trade you for something like that.",
        "That's the kind of thing I'd like to own.",
    ],
    "comments_on": [
        "Interesting choice of material.",
        "The proportions are just right.",
        "You can feel the care in it.",
    ],
    "wants_to_trade": [
        "I have mushrooms that might interest you.",
        "I could offer you some herbs for that.",
        "What would you take for it?",
    ],
    "mentions_to_others": [
        "You should see what they made at the cabin.",
        "I told Thomas about this.",
        "Mira asked about your work.",
    ],
    "inspired_by": [
        "It makes me want to try something.",
        "That gives me an idea.",
        "I hadn't thought of using it that way.",
    ],
}


def npc_reacts_to_output(db, npc_id: str, output: dict) -> Optional[dict]:
    """
    An NPC reacts to a creative output. Called when NPC is at the same
    location as the output or when OWL shows it to them.
    Returns the reaction dict or None.
    """
    now = time.time()
    rid = f"creact_{uuid.uuid4().hex[:8]}"

    # Weight reaction types based on NPC personality and output type
    reaction_type = random.choice(REACTION_TYPES)
    comment = random.choice(REACTION_COMMENTS.get(reaction_type, ["That's interesting."]))

    db.execute("""
        INSERT INTO creative_reactions (id, output_id, npc_id, reaction_type, comment, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (rid, output["id"], npc_id, reaction_type, comment, now))
    db.execute("UPDATE creative_output SET reactions_count = reactions_count + 1 WHERE id = ?", (output["id"],))
    db.commit()

    # Log as event
    from src.world_state import log_event
    npc_row = db.execute("SELECT name FROM agents WHERE id = ?", (npc_id,)).fetchone()
    npc_name = npc_row["name"] if npc_row else npc_id
    log_event(
        db, "creative_reaction",
        f"{npc_name} reacts to '{output['title']}': {comment}",
        agent_id=npc_id,
        location_id=output["location_id"] if output["location_id"] else None,
        properties={"output_id": output["id"], "reaction_type": reaction_type}
    )

    return {
        "id": rid,
        "output_id": output["id"],
        "npc_id": npc_id,
        "npc_name": npc_name,
        "reaction_type": reaction_type,
        "comment": comment,
    }


def get_reactions(db, output_id: str) -> list:
    rows = db.execute("""
        SELECT cr.*, a.name as npc_name
        FROM creative_reactions cr
        JOIN agents a ON a.id = cr.npc_id
        WHERE cr.output_id = ?
        ORDER BY cr.created_at DESC
    """, (output_id,)).fetchall()
    return [dict(row) for row in rows]


# ── Tick integration ───────────────────────────────────────────────────────────

def creative_output_tick(db, owl_location: str = None) -> dict:
    """
    Each tick, check if any NPCs are near recent outputs and might react.
    Returns summary of reactions that occurred.
    """
    summary = {"reactions": []}
    now = time.time()

    # Get outputs from the last 72 hours (3 ticks worth) that have no reactions
    recent_cutoff = now - (72 * 3600)
    outputs = db.execute("""
        SELECT * FROM creative_output
        WHERE created_at > ? AND reactions_count = 0
        ORDER BY created_at DESC
    """, (recent_cutoff,)).fetchall()

    for output in outputs:
        # Get NPCs at the output's location
        loc = output["location_id"] if output["location_id"] else (owl_location if owl_location else "cabin")
        nearby_npcs = db.execute("""
            SELECT id FROM agents
            WHERE id != 'isildur' AND location_id = ? AND state = 'active'
        """, (loc,)).fetchall()

        for npc_row in nearby_npcs:
            # 30% chance per NPC per tick to react to a reaction-worthy output
            if output["type"] in ("carpentry", "writing", "drawing", "music") and random.random() < 0.3:
                reaction = npc_reacts_to_output(db, npc_row["id"], dict(output))
                if reaction:
                    summary["reactions"].append(reaction)

    return summary


# ── Formatting helpers ─────────────────────────────────────────────────────────

def describe_output(output: dict) -> str:
    """One-line summary of a creative output."""
    title = output.get("title", "Untitled")
    output_type = output.get("type", "craft")
    reactions = output.get("reactions_count", 0)
    reaction_note = f" ({reactions} reaction{'s' if reactions != 1 else ''})" if reactions > 0 else ""
    return f"[{output_type}] {title}{reaction_note}"


def format_output_list(outputs: list, limit: int = 20) -> str:
    """Format a list of outputs for display."""
    if not outputs:
        return "No creative outputs yet."
    lines = []
    for out in outputs[:limit]:
        lines.append(describe_output(out))
    return "\n".join(lines)


def format_reaction(reaction: dict) -> str:
    """Format an NPC's reaction for narrative delivery."""
    return f"{reaction['npc_name']} {reaction['reaction_type']}: \"{reaction['comment']}\""