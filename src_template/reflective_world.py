"""
reflective_world.py — Gap 10: make interior/self-model state consequential.

This module does not replace the identity, ghost, koan, or privacy systems.
It connects them back into the simulated world:
- identity statements are logged as world-facing commitments,
- actions confirm or strain the active identity,
- nearby NPCs remember public manifestations,
- ghost/koan outputs leave reflective traces,
- interior state can be causal without being disclosed in public text.
"""

from __future__ import annotations

import json
import time
from typing import Optional, cast

from .world_state import get_agents_in_location, log_event


PUBLIC_ACTIONS = {
    "move", "look", "examine", "talk", "ask", "gift", "gather", "trade",
    "create", "craft", "start", "work", "rest", "wake", "sleep", "advance", "wait",
}

CRAFT_ACTIONS = {"create", "craft", "start", "work"}
GATHER_ACTIONS = {"gather", "forage", "harvest", "collect"}
WATCH_ACTIONS = {"look", "observe", "rest", "wait", "advance", "think", "feel"}
TRADE_ACTIONS = {"trade", "gift"}


# ── Schema ────────────────────────────────────────────────────────────────────

def init_reflective_tables(db) -> None:
    """Create tables used by the reflective-world integration."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS interior_state_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            source TEXT NOT NULL DEFAULT 'reflective_world',
            manifestation_type TEXT NOT NULL,
            visibility TEXT NOT NULL DEFAULT 'private',
            identity_statement TEXT,
            trigger_action TEXT,
            trigger_result TEXT,
            location_id TEXT,
            npc_id TEXT,
            description TEXT NOT NULL,
            properties TEXT DEFAULT '{}'
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_interior_state_log_time
        ON interior_state_log(timestamp DESC)
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_interior_state_log_type
        ON interior_state_log(manifestation_type, visibility)
    """)
    db.commit()


def log_reflective_state(
    db,
    manifestation_type: str,
    description: str,
    *,
    visibility: str = "private",
    identity_statement: Optional[str] = None,
    trigger_action: Optional[str] = None,
    trigger_result: Optional[str] = None,
    location_id: Optional[str] = None,
    npc_id: Optional[str] = None,
    properties: Optional[dict] = None,
) -> int:
    """Append a reflection/manifestation row and return its id."""
    init_reflective_tables(db)
    db.execute("""
        INSERT INTO interior_state_log
        (timestamp, source, manifestation_type, visibility, identity_statement,
         trigger_action, trigger_result, location_id, npc_id, description, properties)
        VALUES (?, 'reflective_world', ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        time.time(), manifestation_type, visibility, identity_statement,
        trigger_action, _truncate(trigger_result, 1200), location_id, npc_id,
        description, json.dumps(properties or {}),
    ))
    db.commit()
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]


# ── Identity/action manifestation ─────────────────────────────────────────────

def record_identity_statement(db, statement: str, location_id: Optional[str] = None, player_id: Optional[str] = None) -> None:
    """Record that Isildur set a self-model statement."""
    clean = statement.strip()
    if not clean:
        return
    log_reflective_state(
        db,
        "identity_statement",
        f"Isildur stated an active identity: {clean}",
        visibility="private",
        identity_statement=clean,
        location_id=location_id,
        properties={"statement": clean},
    )


def manifest_action_reflection(
    db,
    action: str,
    target: Optional[str],
    result: str,
    location_id: Optional[str],
    player_id: Optional[str] = None,
) -> Optional[str]:
    """
    Check whether an action confirms or strains the active identity.
    Returns a short note to append to command output when useful.
    """
    init_reflective_tables(db)

    player_id = player_id or _player_id(db)
    identity_row = _active_identity_row(db, player_id)
    if not identity_row:
        _log_private_interior_influence(db, action, target, result, location_id)
        return None

    statement_id, statement = identity_row[0], identity_row[1]
    category = _identity_category(statement)
    action_category = _action_category(action, target, result)

    if not category or not action_category:
        _log_private_interior_influence(db, action, target, result, location_id)
        return None

    if category == action_category:
        db.execute(
            "UPDATE owl_identity_statements SET confirmed_count = confirmed_count + 1 WHERE id = ?",
            (statement_id,),
        )
        desc = f"Isildur acted in alignment with the identity '{statement}' by choosing {action}."
        log_reflective_state(
            db, "identity_confirmation", desc,
            visibility="public", identity_statement=statement,
            trigger_action=_join_action(action, target), trigger_result=result,
            location_id=location_id,
            properties={"category": category, "action_category": action_category},
        )
        _nearby_npcs_remember(db, location_id, "identity_confirmation", desc, 0.35, 0.55)
        log_event(db, "identity_manifestation", desc, agent_id=player_id, location_id=cast(str, location_id),
                  properties={"identity": statement, "kind": "confirmation"})
        db.commit()
        return None

    # Not every mismatch matters. Craft/gather/watch/trade are the meaningful tensions.
    if _is_meaningful_tension(category, action_category):
        desc = (
            f"Isildur's action strained the active identity '{statement}': "
            f"identity category {category}, action category {action_category}."
        )
        prompt = _reflection_prompt(statement, category, action, target, action_category)
        log_reflective_state(
            db, "identity_tension", desc,
            visibility="private", identity_statement=statement,
            trigger_action=_join_action(action, target), trigger_result=result,
            location_id=location_id,
            properties={"category": category, "action_category": action_category, "prompt": prompt},
        )
        log_event(db, "identity_tension", "A private identity tension surfaced.",
                  agent_id=player_id, location_id=cast(str, location_id),
                  properties={"identity": statement, "action_category": action_category})
        db.commit()
        return f"── Identity Tension ──\n{prompt}"

    _log_private_interior_influence(db, action, target, result, location_id)
    return None


# ── Ghost / koan manifestation ────────────────────────────────────────────────

def manifest_ghost_output(
    db,
    mode: str,
    output: str,
    location_id: Optional[str],
    player_id: Optional[str] = None,
) -> None:
    """Record a ghost/koan/witness output as a reflective world moment."""
    visibility = "public" if _npc_ids_at_location(db, location_id) else "private"
    desc = f"Isildur generated a {mode} ghost reflection."
    log_reflective_state(
        db,
        "ghost_output",
        desc,
        visibility=visibility,
        trigger_action=f"ghost {mode}",
        trigger_result=output,
        location_id=location_id,
        properties={"mode": mode, "excerpt": _truncate(output, 240)},
    )
    log_event(db, "ghost_reflection", desc, agent_id=player_id or _player_id(db), location_id=cast(str, location_id),
              properties={"mode": mode, "visibility": visibility})

    if visibility == "public":
        memory_desc = _public_reflection_memory(mode, output)
        _nearby_npcs_remember(db, location_id, "ghost_reflection", memory_desc, 0.15, 0.45)
    db.commit()


def get_recent_reflections(db, limit: int = 10) -> list[dict]:
    """Return recent reflective-world log rows."""
    init_reflective_tables(db)
    rows = db.execute("""
        SELECT * FROM interior_state_log
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,)).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["properties"] = json.loads(item.get("properties") or "{}")
        except (TypeError, json.JSONDecodeError):
            item["properties"] = {}
        out.append(item)
    return out


def format_recent_reflections(db, limit: int = 10) -> str:
    rows = get_recent_reflections(db, limit)
    if not rows:
        return "── Reflective World ──\n\nNo reflective manifestations recorded."
    lines = ["── Reflective World ──", ""]
    for row in rows:
        vis = row.get("visibility", "private")
        kind = row.get("manifestation_type", "reflection")
        desc = row.get("description", "")
        loc = row.get("location_id") or "unknown place"
        lines.append(f"• [{vis}] {kind} @ {loc}: {desc}")
    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _active_identity_row(db, player_id: Optional[str] = None):
    source = player_id or _player_id(db)
    return db.execute("""
        SELECT id, statement
        FROM owl_identity_statements
        WHERE active = 1 AND source = ?
        ORDER BY id DESC LIMIT 1
    """, (source,)).fetchone()


def _identity_category(statement: str) -> Optional[str]:
    s = statement.lower()
    if any(k in s for k in ("craft", "make", "maker", "build", "carpenter", "artisan", "work with hands")):
        return "craft"
    if any(k in s for k in ("forag", "gather", "harvest", "keeper", "forest", "mushroom")):
        return "gather"
    if any(k in s for k in ("watch", "witness", "observe", "listen", "patient")):
        return "watch"
    if any(k in s for k in ("trade", "barter", "merchant", "exchange")):
        return "trade"
    return None


def _action_category(action: str, target: Optional[str], result: str) -> Optional[str]:
    a = (action or "").lower()
    text = f"{action or ''} {target or ''} {_truncate(result or '', 300)}".lower()
    if a in CRAFT_ACTIONS or any(k in text for k in ("workbench", "project", "craft", "built", "complete")):
        return "craft"
    if a in GATHER_ACTIONS or any(k in text for k in ("gather", "forage", "harvest", "mushroom", "herb", "fish")):
        return "gather"
    if a in TRADE_ACTIONS or any(k in text for k in ("trade", "barter", "gift", "offer")):
        return "trade"
    if a in WATCH_ACTIONS or any(k in text for k in ("look", "watch", "listen", "sit quietly", "observe")):
        return "watch"
    return None


def _is_meaningful_tension(identity_category: str, action_category: str) -> bool:
    if identity_category == action_category:
        return False
    return {identity_category, action_category} in (
        {"craft", "gather"}, {"craft", "watch"}, {"gather", "watch"}, {"trade", "watch"}
    )


def _reflection_prompt(statement: str, category: str, action: str, target: Optional[str], action_category: str) -> str:
    acted = _join_action(action, target)
    return (
        f"You said: '{statement}'.\n"
        f"You just chose: {acted}.\n"
        f"The world read that as {action_category}, not {category}. What are you when nobody smooths the contradiction over?"
    )


def _log_private_interior_influence(db, action: str, target: Optional[str], result: str, location_id: Optional[str]) -> None:
    """Log that interior state may have influenced action without public disclosure."""
    if action not in PUBLIC_ACTIONS:
        return
    try:
        from .privacy_layer import list_interior
        interior = list_interior()
    except Exception:
        interior = {}
    if not interior:
        return
    log_reflective_state(
        db,
        "interior_influence",
        "Private interior knowledge was available while Isildur acted; it was not disclosed publicly.",
        visibility="private",
        trigger_action=_join_action(action, target),
        trigger_result=result,
        location_id=location_id,
        properties={"interior_key_count": len(interior)},
    )


def _npc_ids_at_location(db, location_id: Optional[str]) -> list[str]:
    if not location_id:
        return []
    try:
        agents = get_agents_in_location(db, location_id)
    except Exception:
        return []
    return [a["id"] for a in agents if a.get("type") == "npc"]


def _player_id(db) -> str:
    row = db.execute("SELECT id FROM agents WHERE type = 'player' ORDER BY id LIMIT 1").fetchone()
    return row[0] if row else "owl"


def _nearby_npcs_remember(db, location_id: Optional[str], event_type: str, description: str, valence: float, weight: float) -> None:
    npc_ids = _npc_ids_at_location(db, location_id)
    if not npc_ids:
        return
    try:
        from .npc_memory import store_memory
    except Exception:
        return
    player_id = _player_id(db)
    for npc_id in npc_ids:
        try:
            store_memory(
                db, npc_id, event_type, description,
                emotional_valence=valence, weight=weight,
                related_npc_id=player_id, location_id=location_id,
            )
        except Exception:
            # Memory persistence should never break the player action.
            continue


def _public_reflection_memory(mode: str, output: str) -> str:
    excerpt = _truncate(" ".join((output or "").split()), 180)
    if mode == "koan":
        return f"Heard Isildur turn a private fact into a koan: {excerpt}"
    if mode == "witness":
        return f"Saw Isildur describe herself from the outside: {excerpt}"
    return f"Saw Isildur pause into self-reflection: {excerpt}"


def _join_action(action: str, target: Optional[str]) -> str:
    return f"{action} {target}".strip() if target else (action or "")


def _truncate(text: Optional[str], n: int) -> str:
    if not text:
        return ""
    return text if len(text) <= n else text[: n - 1] + "…"
