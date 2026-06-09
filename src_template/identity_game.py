"""
identity_game.py — Consequential self-model rules.

OWL maintains a working identity statement ("I am a craftsperson").
When OWL acts against its stated identity, a reflection prompt surfaces —
not a command, a question. NPCs maintain their own model of OWL's
identity, which may diverge from OWL's self-model.

The identity statement is a load-bearing structure. Decorative self-models
that never encounter resistance don't teach anything about the self.
"""

import re
from typing import Optional

from .world_state import get_db, log_event, DB_PATH


# ── Identity keyword sets ────────────────────────────────────────────────────
# Used to detect divergence between stated identity and observed action.

CRAFT_KEYWORDS = [
    "craftsperson", "maker", "build", "create", "shape",
    "work with hands", "carpenter", "artisan", "smith", "tailor",
    "prepare", "construct", "form", "fabricate"
]

GATHER_KEYWORDS = [
    "gather", "forage", "harvest", "collect", "pick",
    "find", "snare", "trap", "hunt", "catch", "scoop"
]

TRADE_KEYWORDS = [
    "trade", "exchange", "give", "receive", "barter",
    "sell", "buy", "offer", "negotiate", "deal"
]

WATCH_KEYWORDS = [
    "watch", "observe", "look", "sit", "rest", "wander",
    "walk", "listen", "sit still", "be still"
]

IDENTITY_KEYWORDS = {
    "craft": CRAFT_KEYWORDS,
    "gather": GATHER_KEYWORDS,
    "trade": TRADE_KEYWORDS,
    "watch": WATCH_KEYWORDS,
}


# ── Schema ────────────────────────────────────────────────────────────────────

def init_identity_tables(db) -> None:
    """Create the identity statements table if it doesn't exist."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS owl_identity_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            statement TEXT NOT NULL,
            set_at REAL NOT NULL,
            source TEXT NOT NULL DEFAULT 'isildur',
            confirmed_count INTEGER NOT NULL DEFAULT 0,
            revision_count INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_active
        ON owl_identity_statements(active, source)
    """)


# ── Core API ──────────────────────────────────────────────────────────────────

def set_identity(db, statement: str, source: str = "owl") -> None:
    """
    Set a new active identity statement, deactivating any previous one
    from the same source.
    """
    import time as _time
    # Deactivate previous active statements from this source
    db.execute(
        "UPDATE owl_identity_statements SET active = 0 WHERE active = 1 AND source = ?",
        (source,)
    )
    db.execute(
        "INSERT INTO owl_identity_statements (statement, set_at, source, active) VALUES (?, ?, ?, 1)",
        (statement.strip(), _time.time(), source)
    )


def get_active_identity(db, source: str = "owl") -> Optional[str]:
    """Return the current active identity statement, or None."""
    row = db.execute(
        "SELECT statement FROM owl_identity_statements "
        "WHERE active = 1 AND source = ? ORDER BY id DESC LIMIT 1",
        (source,)
    ).fetchone()
    return row[0] if row else None


def get_active_statement_row(db, source: str = "owl") -> Optional[tuple]:
    """Return the full active identity row, or None."""
    row = db.execute(
        "SELECT id, statement, set_at, source, confirmed_count, revision_count "
        "FROM owl_identity_statements "
        "WHERE active = 1 AND source = ? ORDER BY id DESC LIMIT 1",
        (source,)
    ).fetchone()
    return row if row else None


def confirm_identity(db, statement_id: int) -> None:
    """Record that the identity was confirmed through action."""
    db.execute(
        "UPDATE owl_identity_statements SET confirmed_count = confirmed_count + 1 WHERE id = ?",
        (statement_id,)
    )


def revise_identity(db, new_statement: str) -> None:
    """
    Revise the current active identity — deactivate it, increment revision_count,
    and insert the new statement.
    """
    import time as _time
    db.execute(
        "UPDATE owl_identity_statements SET active = 0, "
        "revision_count = revision_count + 1 WHERE active = 1 AND source = 'isildur'"
    )
    set_identity(db, new_statement.strip(), "owl")


def list_identities(db, source: str = "owl") -> list[dict]:
    """Return all identity statements for a source, active and historical."""
    rows = db.execute(
        "SELECT id, statement, set_at, source, confirmed_count, revision_count, active "
        "FROM owl_identity_statements WHERE source = ? ORDER BY id DESC",
        (source,)
    ).fetchall()
    return [
        {
            "id": r[0],
            "statement": r[1],
            "set_at": r[2],
            "source": r[3],
            "confirmed_count": r[4],
            "revision_count": r[5],
            "active": bool(r[6]),
        }
        for r in rows
    ]


# ── Divergence detection ───────────────────────────────────────────────────────
# Returns a reflection prompt if the action type conflicts with the stated identity.

def check_identity_divergence(
    db,
    action_type: str,
    action_desc: str = ""
) -> Optional[str]:
    """
    Given an action type string and description, check whether it conflicts
    with the current active identity. Returns a reflection prompt (not a command)
    if divergence is found, else None.
    """
    identity = get_active_identity(db, "owl")
    if not identity:
        return None

    identity_lower = identity.lower()
    action_lower = (action_type + " " + action_desc).lower()

    # Determine which identity category this is
    is_craft = any(k in identity_lower for k in CRAFT_KEYWORDS)
    is_gather = any(k in identity_lower for k in GATHER_KEYWORDS)
    is_watch = any(k in identity_lower for k in WATCH_KEYWORDS)

    # Determine which action category this is
    acted_gather = any(k in action_lower for k in GATHER_KEYWORDS)
    acted_craft = any(k in action_lower for k in CRAFT_KEYWORDS)
    acted_watch = any(k in action_lower for k in WATCH_KEYWORDS)

    # Divergence: stated craft identity, but action is gather
    if is_craft and acted_gather:
        return (
            f"You said you were a craftsperson. "
            f"You just gathered {action_desc}. "
            f"What are you?"
        )

    # Divergence: stated craft identity, but spending hours watching
    if is_craft and acted_watch:
        return (
            f"You said you were a craftsperson. "
            f"You sat still for hours instead. "
            f"What does that mean?"
        )

    # Divergence: stated gather identity, but crafting instead
    if is_gather and acted_craft:
        return (
            f"You said you were a forager. "
            f"You just built something instead. "
            f"What are you?"
        )

    # Divergence: stated watch identity, but gathering aggressively
    if is_watch and acted_gather and not is_gather:
        return (
            f"You said you were one who watches. "
            f"You just moved through the forest taking. "
            f"What are you?"
        )

    return None


# ── NPC assessment of OWL ─────────────────────────────────────────────────────
# NPCs form their own model of OWL based on observed action history.

def npc_assesses_owl_identity(db, npc_id: str) -> str:
    """
    NPC forms its own model of OWL's identity based on OWL's action history.
    Returns one of: 'forager', 'craftsperson', 'trader', 'watcher', 'observer'.
    """
    rows = db.execute(
        "SELECT type, COUNT(*) as cnt FROM events "
        "WHERE agent_id = 'isildur' "
        "GROUP BY type "
        "ORDER BY cnt DESC LIMIT 10"
    ).fetchall()

    if not rows:
        return "observer"

    action_summary = " ".join(f"{row[1]} {row[0]}" for row in rows)

    if any(k in action_summary for k in GATHER_KEYWORDS):
        model = "forager"
    elif any(k in action_summary for k in CRAFT_KEYWORDS):
        model = "craftsperson"
    elif any(k in action_summary for k in TRADE_KEYWORDS):
        model = "trader"
    elif any(k in action_summary for k in WATCH_KEYWORDS):
        model = "watcher"
    else:
        model = "observer"

    return model


# ── Identity history ─────────────────────────────────────────────────────────

def get_identity_history(db, source: str = "owl") -> dict:
    """
    Return structured identity history: current statement, total revisions,
    total confirmations, and a list of past statements.
    """
    current = get_active_statement_row(db, source)
    history = list_identities(db, source)

    if not current:
        return {
            "current": None,
            "total_revisions": 0,
            "total_confirms": 0,
            "history": history,
        }

    return {
        "current": {
            "id": current[0],
            "statement": current[1],
            "set_at": current[2],
            "source": current[3],
            "confirmed_count": current[4],
            "revision_count": current[5],
        },
        "total_revisions": sum(1 for h in history if h["revision_count"] > 0),
        "total_confirms": current[4],
        "history": history,
    }


# ── Formatting helpers ────────────────────────────────────────────────────────

def format_identity_prompt(identity: str, divergence: str) -> str:
    """Format a divergence prompt for display."""
    return (
        f"── Identity ──\n\n"
        f"You said: \"{identity}\"\n\n"
        f"{divergence}\n\n"
        f"Reply with 'identity I am <statement>' to set a new identity "
        f"or 'identity revise' to reflect on what you just did."
    )


def format_identity_status(db, source: str = "owl") -> str:
    """Format the current identity status for display."""
    identity = get_active_identity(db, source)
    if not identity:
        return "── Identity ──\n\nNo identity statement set.\n\nUse: identity I am <statement>"

    row = get_active_statement_row(db, source)
    if not row:
        return f"── Identity ──\n\n{identity}"

    import time
    age_hours = (time.time() - row[2]) / 3600
    age_str = f"{age_hours:.1f}h ago" if age_hours < 24 else f"{age_hours/24:.1f}d ago"

    return (
        f"── Identity ──\n\n"
        f"{identity}\n\n"
        f"Set {age_str} | confirmed {row[4]}× | revised {row[5]}×\n\n"
        f"Use: identity I am <statement> | identity revise"
    )