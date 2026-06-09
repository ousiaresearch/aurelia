"""
embodied_world/agent_api.py — Clean API for integrating with any agent harness.

This module provides a simple, self-contained interface for an agent to
inhabit the Embodied Creative World. It can be used standalone or wrapped
by any agent framework (Hermes, LangChain, CrewAI, custom, etc.).

Usage:
    from embodied_world.agent_api import EmbodiedAgent

    # Default world (NC coastal)
    agent = EmbodiedAgent()

    # Custom world from YAML
    agent = EmbodiedAgent(world_config="my_world.yaml")

    # Custom world from dict
    agent = EmbodiedAgent(world_config={"name": "My World", "geography": {...}})

    # Get a rich description of what the agent perceives
    world_text = agent.perceive()

    # Take an action
    result = agent.act("move", "east")
    result = agent.act("talk", "Marty")
    result = agent.act("create", "music sea shanty")

    # Get structured world state (for LLM context)
    state = agent.get_world_state()

    # Save
    agent.save()
"""

import json
import time
from pathlib import Path
from typing import Optional, Union

# Handle both installed package and standalone usage
try:
    from .world_state import get_db, init_world, seed_world, DB_PATH
    from .agent import Agent
    from .simulation import tick
    from .text_engine import describe_location
    from .psychology import describe_internal_state
    from .creative import get_active_projects, get_completed_projects, describe_project, PROJECT_TYPES
    from .npc_ai import get_npc_story
    from .npc_depth import OWLInteractionMemory, get_npc_depth_story, init_npc_depth
    from .narrative import get_active_stories
    from .events import get_recent_events
    from .rituals import get_upcoming_rituals
    from .persistence import save_snapshot, commit_snapshot
    from .world_template import WorldConfig, load_config, DEFAULT_CONFIG
except ImportError:
    from world_state import get_db, init_world, seed_world, DB_PATH
    from agent import Agent
    from simulation import tick
    from text_engine import describe_location
    from psychology import describe_internal_state
    from creative import get_active_projects, get_completed_projects, describe_project, PROJECT_TYPES
    from npc_ai import get_npc_story
    from npc_depth import OWLInteractionMemory, get_npc_depth_story, init_npc_depth
    from narrative import get_active_stories
    from events import get_recent_events
    from rituals import get_upcoming_rituals
    from persistence import save_snapshot, commit_snapshot
    from world_template import WorldConfig, load_config, DEFAULT_CONFIG


class EmbodiedAgent:
    """
    High-level interface for an agent to inhabit the world.
    
    Wraps the full simulation engine and provides clean methods
    for perception, action, and state inspection.
    """

    def __init__(self, db_path: Optional[Path] = None, world_config: Optional[Union[str, dict, WorldConfig]] = None):
        """
        Initialize or load the world.
        
        Args:
            db_path: Path to SQLite database. If None, uses default.
                     If the database doesn't exist, creates and seeds a new world.
            world_config: World configuration. Can be:
                         - None: use default NC coastal world
                         - str: path to a YAML config file
                         - dict: configuration dict
                         - WorldConfig: a WorldConfig object
        """
        # Resolve world config
        if world_config is None:
            self._config = DEFAULT_CONFIG
        elif isinstance(world_config, str):
            self._config = load_config(world_config)
        elif isinstance(world_config, dict):
            self._config = WorldConfig.from_dict(world_config)
        elif isinstance(world_config, WorldConfig):
            self._config = world_config
        else:
            raise ValueError(f"Invalid world_config type: {type(world_config)}")
        
        # Set seed if specified
        if self._config.seed is not None:
            import random
            random.seed(self._config.seed)
        
        if db_path:
            import os
            os.environ["EMBODIED_WORLD_DB"] = str(db_path)
        
        self._agent = Agent(db_path) if db_path else Agent()
        self._db = self._agent.db
        self._world = self._agent.world

    def _player_id(self) -> str:
        return getattr(self._agent, "player_id", "owl")

    def _player(self) -> dict:
        return self._world.get("agents", {}).get(self._player_id(), {})
    
    @property
    def config(self) -> WorldConfig:
        """Get the world configuration."""
        return self._config

    # ── PERCEPTION ──

    def perceive(self) -> str:
        """
        Get a rich, literary description of the current location.
        This is what the agent 'sees' — sensory, immersive prose.
        """
        return self._agent.perceive()

    def get_world_state(self) -> dict:
        """
        Get structured world state suitable for LLM context.
        Returns a dict with time, weather, body, internal state, location, NPCs.
        """
        player = self._player()
        location_id = player.get("location_id", "cabin_bedroom")
        
        # Get location info
        location = self._world.get("locations", {}).get(location_id, {})
        
        # Get NPCs at current location
        npcs_here = [
            a for a in self._world.get("agents", {}).values()
            if a.get("location_id") == location_id and a.get("type") != "player"
        ]
        
        # Get exits
        exits = self._world.get("exits", {}).get(location_id, [])
        
        return {
            "time": self._world.get("time", {}),
            "weather": self._world.get("weather", {}),
            "body": self._world.get("body", {}),
            "internal": self._world.get("internal", {}),
            "location": {
                "id": location_id,
                "name": location.get("name", "Unknown"),
                "description": location.get("description", ""),
            },
            "npcs_here": [
                {
                    "id": n["id"],
                    "name": n["name"],
                    "description": n.get("properties", {}).get("description", ""),
                }
                for n in npcs_here
            ],
            "exits": [
                {"direction": e["direction"], "to": e["to_location"], "description": e["description"]}
                for e in exits
            ],
        }

    def get_status(self) -> str:
        """Get a formatted status display."""
        return self._agent.act("status")

    def get_map(self) -> str:
        """Get current location map with exits and NPCs."""
        return self._agent.act("map")

    # ── ACTIONS ──

    def act(self, action: str, target: Optional[str] = None) -> str:
        """
        Perform an action in the world.
        
        Args:
            action: Command name (look, move, talk, ask, create, work, etc.)
            target: Optional target (direction, NPC name, item name, etc.)
        
        Returns:
            Rich text description of what happened.
        """
        self._last_result = self._agent.act(action, target)
        self._world = self._agent.world  # refresh world state
        return self._last_result

    def move(self, direction: str) -> str:
        """Move in a direction (north, south, east, west, uphill, downhill, in, out)."""
        return self.act("move", direction)

    def look(self) -> str:
        """Look around the current location."""
        return self.act("look")

    def examine(self, target: str) -> str:
        """Examine an object or NPC."""
        return self.act("examine", target)

    def talk(self, npc_name: str) -> str:
        """Talk to an NPC."""
        return self.act("talk", npc_name)

    def ask(self, npc_name: str, topic: str) -> str:
        """Ask an NPC about a specific topic."""
        return self.act("ask", f"{npc_name} {topic}")

    def advance(self, hours: float = 1.0) -> str:
        """Advance time by the given number of hours."""
        return self.act("advance", str(hours))

    def rest(self) -> str:
        """Rest for a moment."""
        return self.act("rest")

    def sleep(self) -> str:
        """Go to sleep."""
        return self.act("sleep")

    def wake(self) -> str:
        """Wake up."""
        return self.act("wake")

    # ── CREATIVE ──

    def create(self, project_type: str, item_name: str) -> str:
        """Start a creative project. Type: carpentry, writing, cooking, crafting, music, painting."""
        return self.act("create", f"{project_type} {item_name}")

    def work(self) -> str:
        """Work on the active creative project."""
        return self.act("work")

    def get_projects(self) -> dict:
        """Get active and completed projects."""
        return {
            "active": [describe_project(p) for p in get_active_projects(self._db)],
            "completed": [describe_project(p) for p in get_completed_projects(self._db)],
        }

    def get_creative_options(self) -> dict:
        """Get all available creative project types and items."""
        return {
            ptype: [item["name"] for item in pdata["items"]]
            for ptype, pdata in PROJECT_TYPES.items()
        }

    # ── INNER LIFE ──

    def think(self) -> str:
        """Check internal state — mood, interests, creative impulses."""
        return self._agent.act("think")

    def get_memories(self) -> dict:
        """Get recent and long-term memories."""
        internal = self._world.get("internal", {})
        return {
            "recent": json.loads(internal.get("recent_memories", "[]")),
            "long_term": json.loads(internal.get("long_term_memories", "[]")),
        }

    def get_impulse(self) -> str:
        """Get a creative impulse based on current interests."""
        return self._agent.act("impulse")

    # ── WORLD INFO ──

    def get_npc_info(self, npc_name: str) -> dict:
        """Get detailed info about an NPC."""
        npcs = self._db.execute("SELECT * FROM agents WHERE type = 'npc' AND name LIKE ?", (f"%{npc_name}%",)).fetchall()
        if not npcs:
            return {"error": f"No NPC named '{npc_name}' found."}
        npc = dict(npcs[0])
        story = get_npc_story(self._db, npc["id"])
        return story

    def get_stories(self) -> list:
        """Get active story arcs."""
        stories = get_active_stories(self._db)
        return [
            {"type": s.story_type, "participants": s.participants, "phase": s.phase, "narrative": s.generate_narrative()}
            for s in stories
        ]

    def get_events(self, limit: int = 10) -> list:
        """Get recent world events."""
        return get_recent_events(self._db, limit)

    def get_rituals(self) -> list:
        """Get upcoming seasonal rituals."""
        return get_upcoming_rituals(self._db)

    def get_social_web(self) -> str:
        """Get the social web at the current location."""
        return self._agent.act("social")

    def get_relationship(self, npc_name: str) -> dict:
        """Get the agent's relationship with an NPC."""
        npcs = self._db.execute("SELECT * FROM agents WHERE type = 'npc' AND name LIKE ?", (f"%{npc_name}%",)).fetchall()
        if not npcs:
            return {"error": f"No NPC named '{npc_name}' found."}
        npc = dict(npcs[0])
        depth = get_npc_depth_story(self._db, npc["id"])
        return {
            "name": depth["name"],
            "relationship": depth["relationship"],
            "trust": depth["trust"],
            "affection": depth["affection"],
            "respect": depth["respect"],
            "times_met": depth["times_met"],
            "profile": depth.get("profile", {}),
        }

    def observe(self) -> str:
        """Observe the natural world (ecology)."""
        return self._agent.act("observe")

    # ── PERSISTENCE ──

    def save(self, message: str = "") -> str:
        """Save the world state."""
        path, msg = self._agent.save(message)
        return str(path)

    # ── PROPERTIES ──

    @property
    def location(self) -> str:
        return self._player().get("location_id", "")

    @property
    def time(self) -> dict:
        return self._world.get("time", {})

    @property
    def weather(self) -> dict:
        return self._world.get("weather", {})

    @property
    def body(self) -> dict:
        return self._world.get("body", {})

    @property
    def internal(self) -> dict:
        return self._world.get("internal", {})

    @property
    def turn_count(self) -> int:
        return self._agent.turn_count
