"""
persistence.py — Snapshots, git versioning, and crash recovery.

The world state is sacred. This module ensures it's never lost:
- Hourly JSON snapshots (human-readable, diffable)
- Git versioning (full history, rollback capability)
- Daily compressed backups
- Graceful recovery from any failure
"""

import json
import time
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from .world_state import to_json, DB_PATH

SNAPSHOTS_DIR = Path(__file__).parent.parent / "world" / "snapshots"
BACKUPS_DIR = Path(__file__).parent.parent / "world" / "backups"
WORLD_DIR = Path(__file__).parent.parent / "world"


def _ensure_dirs():
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def _git_repo_initialized() -> bool:
    """Check if the world directory is a git repo."""
    git_dir = WORLD_DIR / ".git"
    return git_dir.exists()


def init_git():
    """Initialize git repo in the world directory."""
    if _git_repo_initialized():
        return
    subprocess.run(
        ["git", "init"],
        cwd=str(WORLD_DIR),
        capture_output=True,
        text=True
    )
    # Create .gitignore
    gitignore = WORLD_DIR / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("backups/\n*.db-wal\n*.db-shm\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(WORLD_DIR), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init: world repository"], cwd=str(WORLD_DIR), capture_output=True)


def save_snapshot(db, label: str = "") -> Path:
    """Save a JSON snapshot of the world state."""
    _ensure_dirs()

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    label_part = f"_{label}" if label else ""
    filename = f"world_{timestamp}{label_part}.json"
    filepath = SNAPSHOTS_DIR / filename

    world_json = to_json(db)
    filepath.write_text(world_json)

    # Also save as latest.json for easy access
    latest = SNAPSHOTS_DIR / "latest.json"
    latest.write_text(world_json)

    return filepath


def commit_snapshot(db, message: str = "") -> Optional[str]:
    """Save a snapshot and commit it to git."""
    _ensure_dirs()

    if not _git_repo_initialized():
        init_git()

    filepath = save_snapshot(db)

    try:
        # Copy db to world dir for versioning
        db_backup = WORLD_DIR / "world.db"
        if DB_PATH.exists():
            shutil.copy2(str(DB_PATH), str(db_backup))

        # Git add and commit
        subprocess.run(["git", "add", "-A"], cwd=str(WORLD_DIR), capture_output=True)
        commit_msg = message or f"world snapshot: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(WORLD_DIR),
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return commit_msg
    except Exception as e:
        pass

    return None


def create_backup() -> Optional[Path]:
    """Create a daily compressed backup of the world."""
    _ensure_dirs()

    timestamp = time.strftime("%Y-%m-%d")
    backup_name = f"world_backup_{timestamp}.tar.gz"
    backup_path = BACKUPS_DIR / backup_name

    try:
        subprocess.run(
            ["tar", "-czf", str(backup_path), "-C", str(WORLD_DIR.parent), "world"],
            capture_output=True,
            text=True
        )
        return backup_path
    except Exception:
        return None


def get_latest_snapshot() -> Optional[dict]:
    """Load the latest snapshot."""
    latest = SNAPSHOTS_DIR / "latest.json"
    if latest.exists():
        return json.loads(latest.read_text())
    return None


def list_snapshots() -> list:
    """List all available snapshots."""
    if not SNAPSHOTS_DIR.exists():
        return []
    return sorted(
        [f.name for f in SNAPSHOTS_DIR.glob("world_*.json") if f.name != "latest.json"],
        reverse=True
    )


# ── WORLD ARTIFACTS ──────────────────────────────────────────────────────────
"""
World artifacts: persistent physical changes made by the player or NPCs.
The world remembers what you've built, placed, grown, or changed.
Not creative_output (which is content) — these are physical world state.
"""

import uuid


def place_artifact(
    db,
    name: str,
    description: str,
    location_id: str,
    artifact_type: str = "placed",
    created_by: str | None = None,
    properties: dict = None
) -> str:
    """
    Record a physical artifact in the world.
    Returns the artifact id.
    """
    if created_by is None:
        try:
            row = db.execute("SELECT id FROM agents WHERE type = 'player' ORDER BY created_at ASC LIMIT 1").fetchone()
            created_by = row["id"] if row else "owl"
        except Exception:
            created_by = "owl"

    artifact_id = f"artifact_{uuid.uuid4().hex[:12]}"
    props = json.dumps(properties or {})
    now = time.time()

    db.execute("""
        INSERT INTO world_artifacts
        (id, name, description, location_id, artifact_type, created_by, created_at, properties)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (artifact_id, name, description, location_id, artifact_type, created_by, now, props))
    db.commit()
    return artifact_id


def get_artifacts_at_location(db, location_id: str, include_hidden: bool = False) -> list:
    """Get all artifacts at a location."""
    query = "SELECT * FROM world_artifacts WHERE location_id = ?"
    if not include_hidden:
        query += " AND visible = 1"
    query += " ORDER BY created_at ASC"
    rows = db.execute(query, (location_id,)).fetchall()
    return [_row_to_artifact(r) for r in rows]


def get_all_artifacts(db) -> list:
    """Get all artifacts in the world."""
    rows = db.execute("SELECT * FROM world_artifacts WHERE visible = 1 ORDER BY created_at ASC").fetchall()
    return [_row_to_artifact(r) for r in rows]


def remove_artifact(db, artifact_id: str) -> bool:
    """Remove an artifact (soft-delete — mark invisible)."""
    cur = db.execute("UPDATE world_artifacts SET visible = 0 WHERE id = ?", (artifact_id,))
    db.commit()
    return cur.rowcount > 0


def artifact_exists_at_location(db, location_id: str, name: str) -> bool:
    """Check if a named artifact already exists at a location."""
    row = db.execute(
        "SELECT id FROM world_artifacts WHERE location_id = ? AND name = ? AND visible = 1",
        (location_id, name)
    ).fetchone()
    return row is not None


def _row_to_artifact(row) -> dict:
    """Convert a world_artifacts row dict."""
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "location_id": row["location_id"],
        "artifact_type": row["artifact_type"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "properties": json.loads(row["properties"]) if row["properties"] else {},
        "visible": bool(row["visible"]),
    }


def log_artifact_event(db, artifact_id: str, event_type: str, description: str):
    """Log an event related to an artifact (discovery, decay, etc.)."""
    now = time.time()
    db.execute("""
        INSERT INTO events (timestamp, agent_id, event_type, description, properties)
        VALUES (?, NULL, ?, ?, ?)
    """, (now, f"artifact_{event_type}", description, json.dumps({"artifact_id": artifact_id})))
    db.commit()
