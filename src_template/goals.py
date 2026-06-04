"""
Goals system - persistent goal tracking for OWL across sessions.
Goals decompose into steps, persist in the DB, and are checked by the simulation tick.
"""

import time
import uuid
from typing import Optional


# ── Schema ────────────────────────────────────────────────────────────────────

def init_goals(db) -> None:
    """Create goals and goal_steps tables if they don't exist."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            priority INTEGER DEFAULT 5,
            category TEXT DEFAULT 'general',
            context TEXT DEFAULT '',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            target_date REAL DEFAULT NULL,
            completed_at REAL DEFAULT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS goal_steps (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            sort_order INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            completed_at REAL DEFAULT NULL,
            FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
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


# ── Goal CRUD ─────────────────────────────────────────────────────────────────

def create_goal(
    db,
    agent_id: str,
    name: str,
    description: str = "",
    priority: int = 5,
    category: str = "general",
    context: str = "",
    target_date: Optional[float] = None,
) -> dict:
    """Create a new goal. Returns the goal dict."""
    now = time.time()
    gid = f"goal_{uuid.uuid4().hex[:8]}"
    db.execute("""
        INSERT INTO goals (id, agent_id, name, description, status, priority, category, context, created_at, updated_at, target_date)
        VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
    """, (gid, agent_id, name, description, priority, category, context, now, now, target_date))
    db.commit()
    return get_goal(db, gid)


def get_goal(db, goal_id: str) -> Optional[dict]:
    row = db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not row:
        return None
    g = dict(row)
    g["steps"] = get_goal_steps(db, goal_id)
    return g


def get_active_goals(db, agent_id: Optional[str] = None) -> list:
    """Return all active goals for an agent, ordered by priority then created_at."""
    agent_id = agent_id or _resolve_player_id(db)
    rows = db.execute("""
        SELECT * FROM goals
        WHERE agent_id = ? AND status = 'active'
        ORDER BY priority ASC, created_at ASC
    """, (agent_id,)).fetchall()
    goals = []
    for row in rows:
        g = dict(row)
        g["steps"] = get_goal_steps(db, g["id"])
        goals.append(g)
    return goals


def get_all_goals(db, agent_id: Optional[str] = None, status: Optional[str] = None) -> list:
    """Return all goals, optionally filtered by status."""
    agent_id = agent_id or _resolve_player_id(db)
    if status:
        rows = db.execute("""
            SELECT * FROM goals WHERE agent_id = ? AND status = ?
            ORDER BY priority ASC, created_at ASC
        """, (agent_id, status)).fetchall()
    else:
        rows = db.execute("""
            SELECT * FROM goals WHERE agent_id = ?
            ORDER BY priority ASC, created_at ASC
        """, (agent_id,)).fetchall()
    goals = []
    for row in rows:
        g = dict(row)
        g["steps"] = get_goal_steps(db, g["id"])
        goals.append(g)
    return goals


def update_goal_status(db, goal_id: str, status: str) -> None:
    now = time.time()
    completed_at = now if status in ("completed", "abandoned") else None
    db.execute("""
        UPDATE goals SET status = ?, updated_at = ?, completed_at = ?
        WHERE id = ?
    """, (status, now, completed_at, goal_id))
    db.commit()


def delete_goal(db, goal_id: str) -> None:
    db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    db.commit()


# ── Steps ─────────────────────────────────────────────────────────────────────

def get_goal_steps(db, goal_id: str) -> list:
    rows = db.execute("""
        SELECT * FROM goal_steps
        WHERE goal_id = ?
        ORDER BY sort_order ASC, created_at ASC
    """, (goal_id,)).fetchall()
    return [dict(row) for row in rows]


def add_step(db, goal_id: str, description: str, sort_order: int = 0) -> dict:
    now = time.time()
    sid = f"step_{uuid.uuid4().hex[:8]}"
    db.execute("""
        INSERT INTO goal_steps (id, goal_id, description, status, sort_order, created_at)
        VALUES (?, ?, ?, 'pending', ?, ?)
    """, (sid, goal_id, description, sort_order, now))
    db.commit()
    row = db.execute("SELECT * FROM goal_steps WHERE id = ?", (sid,)).fetchone()
    return dict(row)


def complete_step(db, step_id: str) -> None:
    now = time.time()
    db.execute("""
        UPDATE goal_steps SET status = 'completed', completed_at = ?
        WHERE id = ?
    """, (now, step_id))
    db.commit()
    step_row = db.execute("SELECT goal_id FROM goal_steps WHERE id = ?", (step_id,)).fetchone()
    if step_row:
        goal_id = step_row["goal_id"]
        pending = db.execute(
            "SELECT COUNT(*) FROM goal_steps WHERE goal_id = ? AND status = 'pending'",
            (goal_id,)
        ).fetchone()[0]
        if pending == 0:
            update_goal_status(db, goal_id, "completed")


def activate_step(db, step_id: str) -> None:
    db.execute("UPDATE goal_steps SET status = 'in_progress' WHERE id = ?", (step_id,))
    db.commit()


# ── Tick integration ───────────────────────────────────────────────────────────

def goals_tick(db, agent_id: Optional[str] = None) -> dict:
    """
    Called each simulation tick. Checks for:
    - Goals with all steps completed but still active -> auto-complete
    - Stale goals with no steps that have had no update in 14 days
    Returns summary dict with suggestions.
    """
    agent_id = agent_id or _resolve_player_id(db)
    summary = {"auto_completed": [], "stale": []}
    now = time.time()
    stale_threshold = 14 * 24 * 3600

    active = get_active_goals(db, agent_id)
    for goal in active:
        if goal["steps"] and all(s["status"] == "completed" for s in goal["steps"]):
            update_goal_status(db, goal["id"], "completed")
            summary["auto_completed"].append({"id": goal["id"], "name": goal["name"]})
        elif not goal["steps"] and (now - goal["updated_at"]) > stale_threshold:
            summary["stale"].append({"id": goal["id"], "name": goal["name"]})

    return summary


# ── Formatting helpers ─────────────────────────────────────────────────────────

def describe_goal(goal: dict) -> str:
    """One-line goal summary with progress."""
    total = len(goal.get("steps", []) or [])
    done = sum(1 for s in goal.get("steps", []) or [] if s["status"] == "completed")
    progress = f" [{done}/{total}]" if total > 0 else ""
    marker = "[!]" if goal["priority"] <= 2 else ("[~]" if goal["priority"] <= 5 else "[ ]")
    return f"{marker} {goal['name']}{progress} [{goal['status']}]"


def format_goal_list(goals: list) -> str:
    """Format a list of goals for display."""
    if not goals:
        return "No goals."
    lines = []
    for g in goals:
        lines.append(describe_goal(g))
        for step in g.get("steps", []) or []:
            done = "x" if step["status"] == "completed" else ("o" if step["status"] == "in_progress" else " ")
            lines.append(f"    [{done}] {step['description']}")
    return "\n".join(lines)


def format_tick_suggestions(summary: dict) -> str:
    """Format tick suggestions into narrative."""
    parts = []
    for kind, goals in summary.items():
        for g in goals:
            if kind == "auto_completed":
                parts.append(f"Goal complete: \"{g['name']}\"")
            elif kind == "stale":
                parts.append(f"Goal might be stale: \"{g['name']}\"")
    return " ".join(parts) if parts else ""