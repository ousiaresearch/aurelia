"""Normalized UI state contract for the PNW embodied world GUI."""

from __future__ import annotations

import json
import os
from typing import Any

from .world_state import (
    canonicalize_location_id,
    get_agents_in_location,
    get_exits_from,
    get_location,
)
from .text_engine import describe_location


def _safe(callable_, default):
    try:
        return callable_()
    except Exception:
        return default


def _player_location_id(agent) -> str:
    player_id = getattr(agent, "player_id", "owl")
    world = getattr(agent, "world", {}) or {}
    player = (world.get("agents") or {}).get(player_id, {})
    location_id = player.get("location_id", "cabin_bedroom")
    return canonicalize_location_id(agent.db, location_id) or "cabin_bedroom"


def _seasonal_tone(agent) -> str:
    def load():
        from .narrative_arcs import get_seasonal_narrative_tone

        season = (agent.world.get("time") or {}).get("season", "spring")
        active = agent.db.execute("SELECT COUNT(*) as c FROM story_arcs WHERE active = 1").fetchone()
        count = active["c"] if active else 0
        return get_seasonal_narrative_tone(season, count)

    return _safe(load, "")


def _ritual_status(agent) -> dict[str, Any]:
    def load():
        from .rituals import get_ritual_status

        return get_ritual_status(agent.db)

    return _safe(load, {"current": None, "upcoming": [], "recent": []})


def _daemon_narrative(limit: int = 30) -> list[dict[str, Any]]:
    log_path = os.path.join(os.path.dirname(__file__), "..", "world", "narrative_log.jsonl")
    entries: list[dict[str, Any]] = []
    if os.path.exists(log_path):
        with open(log_path, "r") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries[-limit:]


KEY_NPC_IDS = frozenset({"mira", "thomas", "sage", "wren"})


def _key_npcs(db) -> list:
    """Always-visible named NPCs, regardless of player location."""
    try:
        rows = db.execute(
            "SELECT * FROM agents WHERE type = 'npc' AND id IN (?, ?, ?, ?) ORDER BY name",
            tuple(KEY_NPC_IDS),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def build_ui_state(agent) -> dict[str, Any]:
    """Build a single normalized state payload for the GUI shell."""
    world = getattr(agent, "world", {}) or {}
    location_id = _player_location_id(agent)
    location = get_location(agent.db, location_id) or {"id": location_id, "name": location_id, "description": ""}

    inventory = _safe(lambda: __import__("src.economy", fromlist=["get_inventory"]).get_inventory(agent.db, getattr(agent, "player_id", "owl")), {})
    all_inventories = _safe(lambda: __import__("src.economy", fromlist=["get_all_inventories"]).get_all_inventories(agent.db), {})
    goals_active = _safe(lambda: __import__("src.goals", fromlist=["get_active_goals"]).get_active_goals(agent.db, getattr(agent, "player_id", "owl")), [])
    goals_all = _safe(lambda: __import__("src.goals", fromlist=["get_all_goals"]).get_all_goals(agent.db, getattr(agent, "player_id", "owl")), [])
    outputs = _safe(lambda: __import__("src.creative_output", fromlist=["get_recent_outputs"]).get_recent_outputs(agent.db, getattr(agent, "player_id", "owl"), limit=20), [])
    ecology = _safe(lambda: __import__("src.ecology", fromlist=["get_location_ecology"]).get_location_ecology(agent.db, location_id), {"plants": [], "animals": [], "fish": []})
    arcs = _safe(lambda: __import__("src.narrative_arcs", fromlist=["get_arc_status_summary"]).get_arc_status_summary(agent.db), [])
    events = _safe(lambda: [dict(row) for row in agent.db.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 50").fetchall()], [])

    return {
        "world": {
            "time": world.get("time", {}),
            "weather": world.get("weather", {}),
            "seasonal_tone": _seasonal_tone(agent),
        },
        "player": {
            "id": getattr(agent, "player_id", "owl"),
            "location_id": location_id,
            "location": location,
            "body": world.get("body", {}),
            "internal": world.get("internal", {}),
            "inventory": inventory,
        },
        "place": {
            "description": describe_location(agent.db, location_id, world),
            "exits": get_exits_from(agent.db, location_id),
            "npcs": [npc for npc in get_agents_in_location(agent.db, location_id) if npc.get("type") != "player"],
            "key_npcs": _key_npcs(agent.db),
            "ecology": ecology,
        },
        "stories": {
            "arcs": arcs,
            "daemon_narrative": _daemon_narrative(),
            "rituals": _ritual_status(agent),
        },
        "systems": {
            "goals": {"active": goals_active, "all": goals_all, "count": len(goals_active)},
            "creative_outputs": {"outputs": outputs, "count": len(outputs)},
            "economy": {"player_inventory": inventory, "all_inventories": all_inventories},
        },
        "events": events,
    }
