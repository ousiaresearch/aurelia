"""
npc_ai.py — Advanced NPC AI: long-term goals, memory, adaptation.

NPCs are no longer just schedule-following agents. They have:
- Long-term goals they pursue across multiple sessions
- Memory of interactions with OWL and other NPCs
- Adaptation to changing world conditions
- Personality-driven decision making
- The ability to initiate actions, not just react

Design principles:
- NPCs pursue goals that make sense for their personality
- Memory shapes future behavior
- NPCs adapt to world changes (weather, economy, relationships)
- NPC actions create emergent stories
- NPCs can surprise the player
"""

import json
import random
import time
from typing import Optional

from .world_state import get_db, log_event, get_npc_schedule, get_npc_relationships, move_agent as ws_move_agent, DB_PATH


# ── NPC GOAL TYPES — what NPCs want ──

GOAL_TYPES = {
    "career": {
        "description": "Advance in their trade",
        "actions": ["practice_skill", "seek_apprentice", "take_risk", "save_money"],
        "occupations": ["logger", "carpenter", "woodworker", "organic_farmer", "fisher", "guide", "brewer", "chef", "mechanic", "mason", "blacksmith", "potter", "weaver", "luthier", "cheesemaker", "beekeeper"],
    },
    "family": {
        "description": "Start or grow a family",
        "actions": ["courting", "marry", "have_child", "care_for_elder"],
        "occupations": ["all"],
    },
    "wealth": {
        "description": "Accumulate wealth",
        "actions": ["trade", "invest", "save", "seek_opportunity"],
        "occupations": ["logger", "hunter", "fisher", "organic_farmer", "brewer", "cheesemaker", "beekeeper", "dog_trainer", "photographer", "yoga_instructor", "therapist", "veterinarian"],
    },
    "reputation": {
        "description": "Be respected in the community",
        "actions": ["help_neighbor", "donate", "organize_event", "mentor"],
        "occupations": ["all"],
    },
    "knowledge": {
        "description": "Learn and understand",
        "actions": ["study", "travel", "experiment", "teach"],
        "occupations": ["naturalist", "wildlife_biologist", "botanist", "astronomer", "writer", "poet", "librarian", "teacher", "herbalist", "mushroom_forager"],
    },
    "peace": {
        "description": "Live a quiet, peaceful life",
        "actions": ["garden", "walk", "read", "rest"],
        "occupations": ["all"],
    },
    "adventure": {
        "description": "See the world beyond the mountains",
        "actions": ["plan_departure", "explore", "save_for_journey", "talk_to_travelers"],
        "occupations": ["guide", "fisher", "hunter", "apprentice", "dog_trainer", "photographer"],
    },
    "craft_mastery": {
        "description": "Master their craft",
        "actions": ["practice", "create_masterpiece", "teach_apprentice", "innovate"],
        "occupations": ["carpenter", "woodworker", "potter", "weaver", "luthier", "blacksmith", "mason", "cheesemaker", "artist", "musician", "writer", "poet"],
    },
}


class NPCMind:
    """Represents an NPC's inner life: goals, memories, personality."""

    def __init__(self, npc_id: str, db):
        self.npc_id = npc_id
        self.db = db
        self.npc = db.execute("SELECT * FROM agents WHERE id = ?", (npc_id,)).fetchone()
        self.properties = {}
        if self.npc and self.npc["properties"]:
            try:
                self.properties = json.loads(self.npc["properties"])
            except (json.JSONDecodeError, TypeError):
                self.properties = {}

        # Load or initialize memory
        self.memories = self.properties.get("memories", [])
        self.goals = self.properties.get("goals", [])
        self.current_mood = self.properties.get("mood", "content")

    def generate_goals(self):
        """Generate goals based on personality and occupation."""
        occupation = self.properties.get("occupation", "")
        traits = self.properties.get("traits", [])
        age = self.properties.get("age", 30)

        goals = []

        # Age-based goals
        if age < 25:
            goals.append(random.choice([GOAL_TYPES["adventure"], GOAL_TYPES["career"], GOAL_TYPES["family"]]))
        elif age < 50:
            goals.append(random.choice([GOAL_TYPES["career"], GOAL_TYPES["family"], GOAL_TYPES["wealth"]]))
        else:
            goals.append(random.choice([GOAL_TYPES["reputation"], GOAL_TYPES["peace"], GOAL_TYPES["knowledge"]]))

        # Personality-based goals
        if "ambitious" in traits or "proud" in traits:
            goals.append(GOAL_TYPES["reputation"])
        if "curious" in traits or "dreamy" in traits:
            goals.append(GOAL_TYPES["knowledge"])
        if "generous" in traits or "kind" in traits:
            goals.append(GOAL_TYPES["peace"])
        if "bold" in traits:
            goals.append(GOAL_TYPES["adventure"])

        # Occupation-based goals
        if occupation in ["carpenter", "woodworker", "potter", "weaver", "luthier", "blacksmith", "mason", "cheesemaker"]:
            goals.append(GOAL_TYPES["craft_mastery"])
        if occupation in ["organic_farmer", "logger", "fisher", "hunter", "beekeeper"]:
            goals.append(GOAL_TYPES["wealth"])
        if occupation in ["forest_ranger", "park_ranger", "naturalist", "wildlife_biologist", "botanist"]:
            goals.append(GOAL_TYPES["knowledge"])
        if occupation in ["guide", "astronomer", "writer", "artist", "poet", "musician"]:
            goals.append(random.choice([GOAL_TYPES["knowledge"], GOAL_TYPES["reputation"]]))
        if occupation in ["mushroom_forager", "herbalist", "forager"]:
            goals.append(random.choice([GOAL_TYPES["knowledge"], GOAL_TYPES["craft_mastery"]]))
        if occupation in ["therapist", "nurse", "midwife", "social_worker", "teacher"]:
            goals.append(GOAL_TYPES["peace"])
        if occupation in ["retired", "elder"]:
            goals.append(random.choice([GOAL_TYPES["peace"], GOAL_TYPES["reputation"]]))

        self.goals = list(set(g["description"] for g in goals))[:3]  # Max 3 goals
        return self.goals

    def add_memory(self, content: str, importance: float = 0.5):
        """Add a memory."""
        memory = {
            "content": content,
            "importance": importance,
            "timestamp": time.time(),
        }
        self.memories.insert(0, memory)
        # Keep last 20 memories
        self.memories = self.memories[:20]

    def think(self) -> Optional[str]:
        """
        NPC thinks about what to do next.
        Returns an action dict with description and optional world-side effects,
        or None if the NPC chooses to rest this tick.
        """
        if not self.goals:
            self.generate_goals()

        # Check relationships
        relationships = get_npc_relationships(self.db, self.npc_id)
        close_friends = [r for r in relationships if r["affinity"] > 0.6]
        rivals = [r for r in relationships if r["affinity"] < 0.3]

        # Collect possible world-side effects for this tick
        world_effect = None

        # Goal-driven behavior with real world consequences
        if self.goals:
            current_goal = random.choice(self.goals)

            if "family" in current_goal and close_friends:
                friend = random.choice(close_friends)
                other_id = friend["npc_b"] if friend["npc_a"] == self.npc_id else friend["npc_a"]
                other = self.db.execute("SELECT name FROM agents WHERE id = ?", (other_id,)).fetchone()
                if other:
                    # Move to wherever the friend is, if not already there
                    friend_loc = self.db.execute(
                        "SELECT location_id FROM agents WHERE id = ?", (other_id,)
                    ).fetchone()
                    if friend_loc and friend_loc["location_id"] != self.npc["location_id"]:
                        ws_move_agent(self.db, self.npc_id, friend_loc["location_id"])
                        self.npc["location_id"] = friend_loc["location_id"]
                        world_effect = f"{self.npc['name']} walked over to join {other['name']}."
                    else:
                        world_effect = f"{self.npc['name']} spends time with {other['name']}, deepening their bond."
                    self.add_memory(f"Spent time with {other['name']}")

            elif "wealth" in current_goal:
                # Move toward the market or town if not already there
                if self.npc["location_id"] not in ("town_hwy58", "marketplace", "trading_post"):
                    ws_move_agent(self.db, self.npc_id, "marketplace")
                    self.npc["location_id"] = "marketplace"
                    world_effect = f"{self.npc['name']} headed to the marketplace for extra work."
                else:
                    world_effect = f"{self.npc['name']} works extra hours at the marketplace."

            elif "reputation" in current_goal:
                # Help a neighbor — pick a random NPC and move to them
                eligible = self.db.execute(
                    "SELECT id, location_id FROM agents WHERE type='npc' AND id != ? ORDER BY RANDOM() LIMIT 1",
                    (self.npc_id,)
                ).fetchone()
                if eligible and eligible["location_id"] != self.npc["location_id"]:
                    ws_move_agent(self.db, self.npc_id, eligible["location_id"])
                    self.npc["location_id"] = eligible["location_id"]
                    other_name = self.db.execute("SELECT name FROM agents WHERE id = ?",
                                                 (eligible["id"],)).fetchone()
                    name = other_name["name"] if other_name else "a neighbor"
                    world_effect = f"{self.npc['name']} walked over to help a neighbor."
                else:
                    world_effect = f"{self.npc['name']} helps a neighbor with a difficult task."

            elif "knowledge" in current_goal:
                # Move to a knowledge-rich location
                if self.npc["location_id"] not in ("library", "naturalist_cabin", "workshop"):
                    ws_move_agent(self.db, self.npc_id, "workshop")
                    self.npc["location_id"] = "workshop"
                    world_effect = f"{self.npc['name']} headed to the workshop to study."
                else:
                    world_effect = f"{self.npc['name']} studies quietly, lost in thought."

            elif "adventure" in current_goal:
                if self.npc["location_id"] not in ("ridgeline", "forest_edge", "clearing"):
                    ws_move_agent(self.db, self.npc_id, "ridgeline")
                    self.npc["location_id"] = "ridgeline"
                    world_effect = f"{self.npc['name']} hiked to the ridgeline, gazing at distant peaks."
                else:
                    world_effect = f"{self.npc['name']} stares at the ridgeline, dreaming of distant mountains."

            elif "craft_mastery" in current_goal:
                if self.npc["location_id"] not in ("workshop", "cabin_main_room"):
                    ws_move_agent(self.db, self.npc_id, "workshop")
                    self.npc["location_id"] = "workshop"
                    world_effect = f"{self.npc['name']} retreated to the workshop to create."
                else:
                    world_effect = f"{self.npc['name']} works on a new creation, pushing the boundaries of their craft."

            elif rivals:
                # Avoid a rival — move away from them
                rival = random.choice(rivals)
                rival_id = rival["npc_b"] if rival["npc_a"] == self.npc_id else rival["npc_a"]
                rival_loc = self.db.execute(
                    "SELECT location_id FROM agents WHERE id = ?", (rival_id,)
                ).fetchone()
                if rival_loc:
                    # Find a location that isn't where the rival is
                    all_locs = ["cabin_main_room", "workshop", "garden", "cedar_trail",
                                "mountain_creek", "clearing", "forest_edge"]
                    safe_locs = [l for l in all_locs if l != rival_loc["location_id"]]
                    new_loc = random.choice(safe_locs) if safe_locs else self.npc["location_id"]
                    if new_loc != self.npc["location_id"]:
                        ws_move_agent(self.db, self.npc_id, new_loc)
                        self.npc["location_id"] = new_loc
                        other = self.db.execute("SELECT name FROM agents WHERE id = ?",
                                               (rival_id,)).fetchone()
                        other_name = other["name"] if other else "a former friend"
                        world_effect = f"{self.npc['name']} avoided {other_name}, keeping distance."

        if world_effect:
            return world_effect
        return None

    def save(self):
        """Save the NPC's mental state back to the database."""
        self.properties["memories"] = self.memories
        self.properties["goals"] = self.goals
        self.properties["mood"] = self.current_mood

        self.db.execute(
            "UPDATE agents SET properties = ?, updated_at = ? WHERE id = ?",
            (json.dumps(self.properties), time.time(), self.npc_id)
        )
        self.db.commit()


def init_npc_ai(db):
    """Initialize NPC AI tables and generate initial goals for all NPCs."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS npc_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id TEXT NOT NULL REFERENCES agents(id),
            timestamp REAL NOT NULL,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            location_id TEXT DEFAULT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_npc_actions_npc ON npc_actions(npc_id);
        CREATE INDEX IF NOT EXISTS idx_npc_actions_time ON npc_actions(timestamp);
    """)
    db.commit()

    # Generate goals for all NPCs that don't have them
    npcs = db.execute("SELECT * FROM agents WHERE type = 'npc'").fetchall()
    for npc in npcs:
        try:
            props = json.loads(npc["properties"]) if npc["properties"] else {}
        except (json.JSONDecodeError, TypeError):
            props = {}

        if not props.get("goals"):
            mind = NPCMind(npc["id"], db)
            mind.generate_goals()
            mind.save()


def _load_props(row) -> dict:
    """Parse an agent properties JSON blob safely."""
    try:
        return json.loads(row["properties"]) if row["properties"] else {}
    except (json.JSONDecodeError, TypeError, KeyError, IndexError):
        return {}


def _location_name(db, location_id: str) -> str:
    if not location_id:
        return "an unknown place"
    row = db.execute("SELECT name FROM locations WHERE id = ?", (location_id,)).fetchone()
    return row["name"] if row else location_id.replace("_", " ").title()


def _schedule_action_text(npc, props: dict, schedule: dict, location_name: str) -> str:
    """Create a type-aware action description from the deep-seeded schedule."""
    npc_type = props.get("npc_type", "human")
    occupation = props.get("occupation", "citizen").replace("_", " ")
    activity = schedule.get("activity", "acting").replace("_", " ")
    detail = schedule.get("description", "")

    if npc_type == "glim":
        base = f"{npc['name']} executes {activity} tasking at {location_name}"
        if detail:
            base += f": {detail}"
        return base
    if npc_type == "vorn":
        base = f"{npc['name']}, a Vorn {occupation}, carries out {activity} at {location_name}"
        if detail:
            base += f": {detail}"
        return base
    if npc_type == "thren":
        base = f"{npc['name']}, a Thren {occupation}, follows their {activity} rhythm at {location_name}"
        if detail:
            base += f": {detail}"
        return base
    base = f"{npc['name']}, a human {occupation}, begins {activity} at {location_name}"
    if detail:
        base += f": {detail}"
    return base


def _insert_npc_action(db, npc_id: str, action_type: str, description: str,
                       location_id: str, properties: dict) -> None:
    """Insert an NPC action, tolerating older schemas without properties."""
    try:
        db.execute("""
            INSERT INTO npc_actions (npc_id, timestamp, action_type, description, location_id, properties)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (npc_id, time.time(), action_type, description, location_id, json.dumps(properties)))
    except Exception:
        db.execute("""
            INSERT INTO npc_actions (npc_id, timestamp, action_type, description, location_id)
            VALUES (?, ?, ?, ?, ?)
        """, (npc_id, time.time(), action_type, description, location_id))


def _scheduled_npc_action(db, npc, hour: int) -> Optional[dict]:
    """Return a meaningful schedule-driven action for one NPC, moving them if needed."""
    schedule = get_npc_schedule(db, npc["id"], hour)
    if not schedule:
        return None

    target_location = schedule.get("location_id")
    if target_location:
        exists = db.execute("SELECT 1 FROM locations WHERE id = ?", (target_location,)).fetchone()
        if not exists:
            return None
        if target_location != npc["location_id"]:
            ws_move_agent(db, npc["id"], target_location)

    props = _load_props(npc)
    npc_type = props.get("npc_type", "human")
    location_id = target_location or npc["location_id"]
    location_name = _location_name(db, location_id)
    action_type = schedule.get("activity", "scheduled_action")
    description = _schedule_action_text(npc, props, schedule, location_name)
    action_props = {
        "npc_type": npc_type,
        "occupation": props.get("occupation", "citizen"),
        "activity": action_type,
        "schedule_id": schedule.get("id"),
        "source": "deep_seed_schedule",
    }
    _insert_npc_action(db, npc["id"], action_type, description, location_id, action_props)

    return {
        "npc_id": npc["id"],
        "npc_name": npc["name"],
        "npc_type": npc_type,
        "occupation": props.get("occupation", "citizen"),
        "activity": action_type,
        "action": description,
        "location_id": location_id,
        "source": "deep_seed_schedule",
    }


def _feed_npc_experience(db, npc_id: str, action: dict, world_id: str = "solara"):
    """Feed decision state from a single NPC's tick experience."""
    try:
        from .decision_feeder import feed_tick_experience
        props = {}
        row = db.execute("SELECT properties FROM agents WHERE id = ?", (npc_id,)).fetchone()
        if row:
            try:
                props = json.loads(row[0]) if row[0] else {}
            except (json.JSONDecodeError, TypeError):
                props = {}
        npc_type = action.get("npc_type", props.get("npc_type", "human"))
        feed_tick_experience(db, npc_id, npc_type, action, {}, world_id)
    except Exception:
        pass  # Don't let decision feeding break the tick


def run_npc_ai_tick(db, hour: int, world_id: str = "solara") -> list:
    """
    Run AI for active NPCs.

    Aurelia NPCs are deep-seeded with schedules, type identity, relationships,
    and memories. The schedule is the primary action driver because it anchors
    actions in real country locations instead of obsolete template locations.
    """
    actions = []

    # Only run AI during waking hours (6-22)
    if hour < 6 or hour > 22:
        return actions

    npcs = db.execute("SELECT * FROM agents WHERE type = 'npc' AND state = 'active'").fetchall()

    # Not every NPC acts every tick — stochastic
    for npc in npcs:
        if random.random() > 0.15:  # 15% chance per NPC per tick
            continue

        scheduled = _scheduled_npc_action(db, npc, hour)
        if scheduled:
            actions.append(scheduled)
            # Feed decision state from this tick's experience
            _feed_npc_experience(db, npc["id"], scheduled, world_id)
            continue

        # Fallback for older worlds without deep-seeded schedules. Avoid letting
        # obsolete location names break the whole tick; if the legacy mind fails,
        # record a local reflective action instead of silently swallowing it.
        try:
            mind = NPCMind(npc["id"], db)
            action = mind.think()
            if action:
                props = _load_props(npc)
                payload = {
                    "npc_id": npc["id"],
                    "npc_name": npc["name"],
                    "npc_type": props.get("npc_type", "human"),
                    "occupation": props.get("occupation", "citizen"),
                    "activity": "ai_action",
                    "action": action,
                    "location_id": npc["location_id"],
                    "source": "legacy_goal_ai",
                }
                actions.append(payload)
                _insert_npc_action(db, npc["id"], "ai_action", action, npc["location_id"], payload)
                mind.save()
                _feed_npc_experience(db, npc["id"], payload, world_id)
        except Exception as exc:
            props = _load_props(npc)
            description = f"{npc['name']} keeps to their current rhythm; legacy goal AI could not resolve this tick."
            payload = {
                "npc_id": npc["id"],
                "npc_name": npc["name"],
                "npc_type": props.get("npc_type", "human"),
                "occupation": props.get("occupation", "citizen"),
                "activity": "local_rhythm",
                "action": description,
                "location_id": npc["location_id"],
                "source": "fallback_local_rhythm",
                "error": str(exc),
            }
            actions.append(payload)
            _insert_npc_action(db, npc["id"], "local_rhythm", description, npc["location_id"], payload)

    db.commit()
    return actions


def get_npc_story(db, npc_id: str) -> dict:
    """Get the story of an NPC: their goals, memories, and recent actions."""
    npc = db.execute("SELECT * FROM agents WHERE id = ?", (npc_id,)).fetchone()
    if not npc:
        return {}

    try:
        props = json.loads(npc["properties"]) if npc["properties"] else {}
    except (json.JSONDecodeError, TypeError):
        props = {}

    recent_actions = db.execute("""
        SELECT * FROM npc_actions WHERE npc_id = ?
        ORDER BY timestamp DESC LIMIT 10
    """, (npc_id,)).fetchall()

    relationships = get_npc_relationships(db, npc_id)

    return {
        "name": npc["name"],
        "occupation": props.get("occupation", ""),
        "personality": props.get("personality", ""),
        "goals": props.get("goals", []),
        "memories": props.get("memories", [])[:5],
        "recent_actions": [dict(a) for a in recent_actions],
        "relationships": [
            {
                "other": r["npc_b"] if r["npc_a"] == npc_id else r["npc_a"],
                "type": r["relationship"],
                "affinity": r["affinity"],
            }
            for r in relationships[:10]
        ],
    }
