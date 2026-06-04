"""
privacy_layer.py — Known vs disclosed distinction.

Distinguishes between what OWL knows internally and what OWL is willing
to share. Interior knowledge influences decisions without being stated.
The trade system can't see interior state — but interior knowledge still
shapes trade behavior.

Interior state persists across sessions via data/interior.json.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

from .world_state import DB_PATH


def _get_interior_path(db_path: Path = DB_PATH) -> Path:
    """Interior state lives alongside the world database."""
    return db_path.parent / "interior.json"


class PrivacyLayer:
    """
    Manages interior (private) knowledge separate from shared world state.

    Interior knowledge can influence actions without appearing in command
    output, NPC dialogue, or trade negotiations. It persists across sessions.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.path = _get_interior_path(db_path)
        self._cache: dict[str, Any] = self._load()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._cache, f, indent=2)

    # ── Core API ─────────────────────────────────────────────────────────────

    def mark_interior(self, key: str, value: Any) -> None:
        """Mark a fact as interior knowledge — known but not disclosed."""
        self._cache[key] = value
        self._save()

    def get_interior(self, key: str, default: Any = None) -> Any:
        """Retrieve interior knowledge, or default if not set."""
        return self._cache.get(key, default)

    def is_interior(self, key: str) -> bool:
        """True if this key is marked as interior knowledge."""
        return key in self._cache

    def can_share(self, key: str) -> bool:
        """
        True if this key is NOT interior — i.e., it can be disclosed.
        Interior keys return False; all others return True.
        """
        return not self.is_interior(key)

    def list_interior(self) -> dict:
        """Return a copy of all interior knowledge."""
        return dict(self._cache)

    def remove(self, key: str) -> bool:
        """Remove an interior knowledge entry. Returns True if it existed."""
        if key in self._cache:
            del self._cache[key]
            self._save()
            return True
        return False

    def clear(self) -> None:
        """Clear all interior knowledge."""
        self._cache.clear()
        self._save()

    # ── Convenience helpers ────────────────────────────────────────────────────

    def interior_value_str(self, key: str) -> str:
        """Return interior value as a human-readable string, or empty string."""
        v = self.get_interior(key)
        if v is None:
            return ""
        return str(v)

    def __repr__(self) -> str:
        return f"PrivacyLayer({len(self._cache)} interior facts)"


# ── Module-level helpers ───────────────────────────────────────────────────────
# These allow one-liner usage without instantiating the class explicitly.

def _get_layer(db_path: Path = DB_PATH) -> PrivacyLayer:
    return PrivacyLayer(db_path)


def list_interior(db_path: Path = DB_PATH) -> dict:
    """Return all interior knowledge as a dict."""
    return _get_layer(db_path).list_interior()


def mark_interior(key: str, value: Any, db_path: Path = DB_PATH) -> None:
    """Mark a fact as interior."""
    _get_layer(db_path).mark_interior(key, value)


def get_interior(key: str, default: Any = None, db_path: Path = DB_PATH) -> Any:
    """Get an interior fact."""
    return _get_layer(db_path).get_interior(key, default)


def can_share(key: str, db_path: Path = DB_PATH) -> bool:
    """Check if a key can be shared (not interior)."""
    return _get_layer(db_path).can_share(key)


# ── Privacy-aware trade helper ───────────────────────────────────────────────
# Uses interior knowledge to inform decisions without revealing it.

def privacy_aware_accept(
    privacy: PrivacyLayer,
    npc_id: str,
    resource: str,
    fair_value: float,
    offered_value: float
) -> bool:
    """
    Decide whether to accept a trade given interior knowledge.

    If OWL knows (via interior layer) that the NPC undervalues this resource,
    accept even below fair value. Otherwise apply normal threshold.
    """
    # Interior knowledge: "{npc_id}_undervalues_{resource}" = True
    undervalues = privacy.get_interior(f"{npc_id}_undervalues_{resource}", False)
    if undervalues:
        return True  # Accept — OWL knows something NPC doesn't

    return offered_value >= fair_value * 0.9