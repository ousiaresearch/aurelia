"""
npc_depth.py — Deep NPC personalities, context-sensitive dialogue, and OWL interaction memory.

NPCs are no longer trait-bags. They have:
- Full psychological profiles (values, fears, desires, secrets)
- Context-sensitive dialogue that responds to world state, relationships, and OWL's history
- Memory of every interaction with OWL — they remember kindness, slights, gifts, conversations
- Mood that shifts based on what's happening
- The ability to initiate conversations, ask for help, offer gifts, share secrets

Design principles:
- Every NPC should feel like a person you could know
- Dialogue should never repeat exactly
- NPCs remember and reference past interactions
- NPCs have inner lives that OWL can discover over time
- The more time you spend with an NPC, the deeper the relationship
"""

import json
import random
import time
from typing import Optional

from .world_state import get_db, log_event, DB_PATH
from .rituals import RITUALS


# ── PSYCHOLOGICAL PROFILES ──

VALUES = [
    "family", "honor", "knowledge", "wealth", "community", "independence",
    "tradition", "progress", "nature", "faith", "craft", "adventure",
    "peace", "justice", "beauty", "loyalty", "curiosity", "humility",
]

FEARS = [
    "the sea", "being alone", "poverty", "change", "death", "forgetting",
    "being forgotten", "the dark", "losing control", "betrayal", "failure",
    "the outside world", "aging", "irrelevance", "conflict", "loss",
]

DESIRES = [
    "to be respected", "to find love", "to learn something new", "to travel",
    "to master their craft", "to protect their family", "to be remembered",
    "to find peace", "to prove themselves", "to belong", "to create something lasting",
    "to understand the world", "to be free", "to make amends", "to heal old wounds",
]

SECRETS = [
    "They once left the village and regretted returning.",
    "They're in love with someone they can't have.",
    "They know something about the old tabby ruins that they've never told anyone.",
    "They're afraid they're not as good at their craft as people think.",
    "They once did something they're deeply ashamed of.",
    "They're saving money for a secret purpose.",
    "They can read — one of the few in the village who can.",
    "They had a child once, who died. No one talks about it.",
    "They're not from the village originally. They came here to hide.",
    "They've been writing a book about the village for years.",
    "They know the old stories — the real ones, not the sanitized versions.",
    "They're afraid of getting old.",
    "They once saw something in the forest they can't explain.",
    "They're more intelligent than they let on.",
    "They dream of leaving but never will.",
]


def generate_psychological_profile(properties: dict) -> dict:
    """Generate a deep psychological profile for an NPC."""
    occupation = properties.get("occupation", "")
    traits = properties.get("traits", [])
    age = properties.get("age", 30)

    # Select values based on personality traits
    npc_values = []
    if "kind" in traits or "warm" in traits:
        npc_values.append("community")
    if "curious" in traits or "thoughtful" in traits:
        npc_values.append("knowledge")
    if "proud" in traits or "traditional" in traits:
        npc_values.append("honor")
    if "frugal" in traits or "practical" in traits:
        npc_values.append("wealth")
    if "dreamy" in traits or "romantic" in traits:
        npc_values.append("beauty")
    if "bold" in traits or "independent" in traits:
        npc_values.append("adventure")
    if "gentle" in traits or "quiet" in traits:
        npc_values.append("peace")
    if "spiritual" in traits:
        npc_values.append("faith")

    # Fill remaining from general pool
    while len(npc_values) < 3:
        v = random.choice(VALUES)
        if v not in npc_values:
            npc_values.append(v)

    # Fears based on occupation and traits
    npc_fears = []
    if occupation in ("fisherman", "sailor"):
        npc_fears.append("the sea")
    if "solitary" in traits:
        npc_fears.append("being alone")
    if "traditional" in traits:
        npc_fears.append("change")
    if age > 60:
        npc_fears.append("being forgotten")
    # Add a random fear
    npc_fears.append(random.choice(FEARS))

    # Desires based on age and occupation
    npc_desires = []
    if age < 25:
        npc_desires.append(random.choice(["to prove themselves", "to find love", "to travel", "to be free"]))
    elif age < 50:
        npc_desires.append(random.choice(["to master their craft", "to protect their family", "to be respected"]))
    else:
        npc_desires.append(random.choice(["to be remembered", "to find peace", "to make amends"]))
    npc_desires.append(random.choice(DESIRES))

    # Secret (not all NPCs have one they'd share)
    secret = random.choice(SECRETS) if random.random() < 0.6 else None

    return {
        "values": npc_values[:4],
        "fears": list(set(npc_fears))[:3],
        "desires": list(set(npc_desires))[:3],
        "secret": secret,
    }


# ── OWL INTERACTION MEMORY ──

class OWLInteractionMemory:
    """Tracks the history of interactions between OWL and an NPC."""

    def __init__(self, npc_id: str, db):
        self.npc_id = npc_id
        self.db = db
        self.npc = db.execute("SELECT * FROM agents WHERE id = ?", (npc_id,)).fetchone()
        self.properties = {}
        if self.npc and self.npc[6]:
            try:
                self.properties = json.loads(self.npc[6])
            except (json.JSONDecodeError, TypeError):
                self.properties = {}

        self.interactions = self.properties.get("owl_interactions", [])
        self.relationship_level = self.properties.get("owl_relationship", "stranger")
        self.trust = self.properties.get("owl_trust", 0.5)
        self.affection = self.properties.get("owl_affection", 0.5)
        self.respect = self.properties.get("owl_respect", 0.5)
        self.times_met = self.properties.get("owl_times_met", 0)
        self.last_topic = self.properties.get("owl_last_topic", None)

    def record_interaction(self, interaction_type: str, topic: str = "", quality: float = 0.5):
        """Record an interaction with OWL."""
        interaction = {
            "type": interaction_type,
            "topic": topic,
            "quality": quality,
            "timestamp": time.time(),
        }
        self.interactions.insert(0, interaction)
        self.interactions = self.interactions[:50]  # Keep last 50
        self.times_met += 1
        self.last_topic = topic

        # Persist into the Gap 8 NPC memory table as well as legacy JSON props.
        self._store_salient_memory(interaction_type, topic, quality)

        # Update relationship metrics
        if interaction_type == "conversation":
            self.trust = min(1.0, self.trust + 0.02 * quality)
            self.affection = min(1.0, self.affection + 0.01 * quality)
        elif interaction_type == "gift":
            self.affection = min(1.0, self.affection + 0.1)
            self.trust = min(1.0, self.trust + 0.05)
        elif interaction_type == "help":
            self.trust = min(1.0, self.trust + 0.08)
            self.respect = min(1.0, self.respect + 0.05)
        elif interaction_type == "insult":
            self.affection = max(0.0, self.affection - 0.15)
            self.trust = max(0.0, self.trust - 0.1)
            self.respect = max(0.0, self.respect - 0.1)
        elif interaction_type == "shared_secret":
            self.trust = min(1.0, self.trust + 0.2)
            self.affection = min(1.0, self.affection + 0.1)

        # Update relationship level
        avg = (self.trust + self.affection + self.respect) / 3
        if avg > 0.8 and self.times_met > 10:
            self.relationship_level = "close_friend"
        elif avg > 0.6 and self.times_met > 5:
            self.relationship_level = "friend"
        elif avg > 0.4:
            self.relationship_level = "acquaintance"
        elif avg < 0.2:
            self.relationship_level = "estranged"
        else:
            self.relationship_level = "stranger"

    def _store_salient_memory(self, interaction_type: str, topic: str = "", quality: float = 0.5) -> None:
        """Write OWL interaction memory into npc_memories when that table exists."""
        if not self.npc:
            return
        try:
            from .npc_memory import store_memory
        except Exception:
            return

        # npc tuple: (id, name, type, location_id, state, properties, created_at, updated_at)
        npc_name = self.npc[1] if self.npc else self.npc_id
        location_id = self.npc[3] if self.npc else None
        topic_clean = topic or "ordinary things"

        if interaction_type == "gift":
            desc = f"Isildur gave {npc_name} {topic_clean}. The gift mattered enough to remember."
            valence = 0.7
            weight = max(0.65, quality)
        elif interaction_type == "insult":
            desc = f"Isildur spoke sharply to {npc_name} about {topic_clean}."
            valence = -0.7
            weight = max(0.65, quality)
        elif interaction_type == "help":
            desc = f"Isildur helped {npc_name} with {topic_clean}."
            valence = 0.6
            weight = max(0.6, quality)
        elif interaction_type == "shared_secret":
            desc = f"Isildur trusted {npc_name} with something private about {topic_clean}."
            valence = 0.8
            weight = 0.85
        else:
            desc = f"Talked with Isildur about {topic_clean}."
            valence = max(-1.0, min(1.0, (quality - 0.5) * 1.4))
            weight = max(0.35, min(0.75, quality))

        player = self.db.execute("SELECT id FROM agents WHERE type = 'player' ORDER BY id LIMIT 1").fetchone()
        player_id = player[0] if player else "owl"
        try:
            store_memory(
                self.db, self.npc_id, interaction_type, desc,
                emotional_valence=valence, weight=weight,
                related_npc_id=player_id, location_id=location_id,
            )
        except Exception:
            # Legacy JSON relationship memory should keep working even if the
            # optional memory table has not been initialized in an old database.
            return

    def get_greeting(self) -> str:
        """Generate a context-sensitive greeting."""
        name = self.npc["name"].split()[0] if self.npc else "friend"
        rel = self.relationship_level

        greetings = {
            "stranger": [
                f"'Oh. Hello.' {name} seems unsure who you are.",
                f"'Yes?' A cautious nod.",
                f"{name} looks up, guarded but polite.",
            ],
            "acquaintance": [
                f"'Hello again.' {name} offers a small smile.",
                f"'Back, are you?' {name} seems pleased enough.",
                f"'Good to see you.' A familiar face in the crowd.",
            ],
            "friend": [
                f"'There you are!' {name}'s face lights up.",
                f"'I was just thinking about you.' {name} grins.",
                f"'Come, sit. Tell me how you've been.' Warm, genuine.",
                f"{name} waves you over. 'I saved you some stew.'",
            ],
            "close_friend": [
                f"'My friend.' {name} embraces you like family. 'I have something to tell you.'",
                f"'You came.' {name}'s eyes are bright. 'I knew you would.'",
                f"'Sit. Stay.' {name} pulls up a chair. 'We have much to talk about.'",
                f"{name} looks at you with deep trust. 'I don't say this enough — I'm glad you're here.'",
            ],
            "estranged": [
                f"{name} looks away. The air between you is cold.",
                f"'What do you want?' {name}'s voice is flat.",
                f"{name} nods stiffly. The warmth is gone.",
            ],
        }

        options = greetings.get(rel, greetings["stranger"])
        return random.choice(options)

    def get_dialogue(self, topic: str, world_state: dict) -> str:
        """Generate context-sensitive dialogue on a topic."""
        profile = self.properties.get("psychological_profile", {})
        rel = self.relationship_level
        name = self.npc["name"].split()[0] if self.npc else "they"

        # Topic-sensitive responses
        topic_responses = {
            "village": self._dialogue_valley,
            "work": self._dialogue_work,
            "family": self._dialogue_family,
            "feelings": self._dialogue_feelings,
            "secret": self._dialogue_secret,
            "future": self._dialogue_future,
            "past": self._dialogue_past,
            "weather": self._dialogue_weather,
            "food": self._dialogue_food,
            "gossip": self._dialogue_gossip,
            "military": self._dialogue_military,
            "the_sea": self._dialogue_the_sea,
            "owl": self._dialogue_owl,
            "ritual": self._dialogue_ritual,
            "default": self._dialogue_default,
        }

        for key, method in topic_responses.items():
            if key in topic.lower():
                return method(profile, rel, world_state)

        return topic_responses["default"](profile, rel, world_state)

    def get_full_dialogue(self, topic: str, world_state: dict, location: str = "", time_of_day: str = "") -> str:
        """Combine greeting + topic response + a random observation about location/time."""
        greeting = self.get_greeting()
        topic_response = self.get_dialogue(topic, world_state)
        observation = self._get_location_time_observation(location, time_of_day, world_state)
        parts = [greeting, topic_response]
        if observation:
            parts.append(observation)
        return "\n\n".join(parts)

    def _get_location_time_observation(self, location: str, time_of_day: str, world_state: dict) -> str:
        """Generate a random observation about the current location or time of day."""
        name = self.npc["name"].split()[0] if self.npc else "They"
        rel = self.relationship_level

        observations = []

        # Time-of-day observations
        if time_of_day:
            time_obs = {
                "morning": [
                    f"'The morning light here is something special.' {name} gazes out.",
                    f"{name} stretches. 'Early hours. The village is just waking.'",
                    f"'There's a stillness in the morning I've never found anywhere else.'",
                ],
                "midday": [
                    f"The sun is high. {name} wipes their brow. 'Warm one today.'",
                    f"{name} glances at the sun. 'Good light for working. Can't waste it.'",
                    f"'Midday already? Time moves fast when you're busy.'",
                ],
                "afternoon": [
                    f"{name} leans back. 'The afternoon light makes everything golden.'",
                    f"'I love this time of day. The village feels... settled.'",
                    f"{name} watches the shadows lengthen. 'Evening's coming.'",
                ],
                "evening": [
                    f"The sky is turning orange. {name} watches quietly. 'Beautiful, isn't it?'",
                    f"{name} sighs contentedly. 'Evening. My favorite time. The day's work is done.'",
                    f"'There's something about evening light that makes me reflective.'",
                ],
                "night": [
                    f"{name} looks up at the stars. 'Clear night. You can see everything.'",
                    f"The village is quiet. {name} speaks softly. 'Night has its own kind of peace.'",
                    f"'I don't mind the dark. Never have. The stars are enough.'",
                ],
            }
            if time_of_day.lower() in time_obs:
                observations.extend(time_obs[time_of_day.lower()])

        # Location observations
        if location:
            loc_lower = location.lower()
            if "harbor" in loc_lower or "dock" in loc_lower or "port" in loc_lower:
                observations.extend([
                    f"{name} nods toward the water. 'The harbor's busy today. Good sign.'",
                    f"'Smell that salt air. Reminds me why I stay.'",
                    f"A ship creaks at the dock. {name} doesn't even look. 'Old sounds. Comforting.'",
                ])
            elif "market" in loc_lower or "square" in loc_lower:
                observations.extend([
                    f"The market bustles around you. {name} watches the crowd. 'Lots of faces today.'",
                    f"{name} picks up an apple from a nearby stall, sniffs it. 'Fresh. Good season for it.'",
                    f"'The market tells you everything about a village. Today it says: we're doing alright.'",
                ])
            elif "forest" in loc_lower or "wood" in loc_lower or "tree" in loc_lower:
                observations.extend([
                    f"{name} touches a tree trunk gently. 'These woods have been here longer than any of us.'",
                    f"A bird calls from somewhere deep. {name} smiles. 'Listen. The forest is talking.'",
                    f"'The trees remember things. If only they could speak.'",
                ])
            elif "tavern" in loc_lower or "inn" in loc_lower:
                observations.extend([
                    f"{name} settles onto a stool. 'This place has good bones. And good ale.'",
                    f"The fire crackles. {name} warms their hands. 'Nothing like a tavern fire.'",
                    f"'Every story in this village has been told at that bar. Every single one.'",
                ])
            elif "hill" in loc_lower or "mountain" in loc_lower or "cliff" in loc_lower:
                observations.extend([
                    f"{name} looks out from the height. 'You can see the whole valley from here.'",
                    f"The wind picks up. {name} doesn't flinch. 'I like the wind. It clears your head.'",
                    f"'Up here, the village looks small. But it's everything.'",
                ])
            else:
                observations.extend([
                    f"{name} looks around. '{location} — there's always something happening here.'",
                    f"'This place has its own rhythm. You just have to listen.'",
                    f"{name} takes in the surroundings. 'Familiar, but never quite the same twice.'",
                ])

        # Weather-based observations if no location/time obs
        if not observations:
            weather = world_state.get("weather", {})
            condition = weather.get("condition", "clear")
            season = world_state.get("season", "")
            if season:
                observations.append(f"'{season.capitalize()} suits this place.' {name} looks around contentedly.")
            else:
                observations.append(f"{name} takes a breath. 'Feels like a good day to be alive.'")

        return random.choice(observations) if observations else ""

    def _dialogue_valley(self, profile, rel, world_state=None):
        desires = profile.get("desires", [])
        values = profile.get("values", [])
        if "community" in values:
            return f"'This village... it's not perfect. But it's ours. We look out for each other. That matters.'"
        elif "adventure" in values:
            return f"'The village is beautiful. But sometimes I wonder what's beyond the horizon. Don't you?'"
        elif "to travel" in desires:
            return f"'I love this place. I do. But I dream of seeing the city. Just once. Is that wrong?'"
        else:
            return f"'Home. It's not the sea or the hills — it's the people. You know that.'"

    def _dialogue_work(self, profile, rel):
        occupation = self.properties.get("occupation", "worker")
        if rel in ("friend", "close_friend"):
            return f"'The {occupation} work is hard. But it's honest. And lately... I've been finding meaning in it I didn't expect.'"
        return f"'Work is work. It keeps the fire going and the table set. What else is there to say?'"

    def _dialogue_family(self, profile, rel):
        if rel == "close_friend":
            return f"'Family...' {self.npc['name'].split()[0]} pauses. 'They're everything. Even when they drive you mad. Especially then.'"
        elif rel == "friend":
            return f"'My family is my anchor. I don't know where I'd be without them.'"
        return f"'Family is... complicated. But they're mine.'"

    def _dialogue_feelings(self, profile, rel):
        fears = profile.get("fears", [])
        if rel in ("friend", "close_friend") and fears:
            fear = fears[0]
            return f"'I'll tell you something I don't say often. I'm afraid of {fear}. It keeps me up at night sometimes.'"
        elif rel == "close_friend":
            return f"'Lately I've been feeling... restless. Like something is changing. In me. In the village. I can't name it.'"
        return f"'Feelings. Hmm. I'm well enough. Thank you for asking.'"

    def _dialogue_secret(self, profile, rel):
        secret = profile.get("secret")
        if rel == "close_friend" and secret:
            return f"'You've been kind to me. I think... I think I can trust you.' {self.npc['name'].split()[0]} leans in. '{secret}'"
        elif rel == "friend":
            return f"'There are things I've never told anyone. Maybe someday. When the time is right.'"
        return f"'Everyone has their secrets. I'm no different.'"

    def _dialogue_future(self, profile, rel):
        desires = profile.get("desires", [])
        if desires:
            return f"'What do I want? {desires[0].capitalize()}. That's the dream, anyway. Whether it happens... we'll see.'"
        return f"'The future. I try not to think too far ahead. Today is enough.'"

    def _dialogue_past(self, profile, rel):
        if rel in ("friend", "close_friend"):
            return f"'The past... I've made mistakes. Things I wish I could undo. But they made me who I am. For better or worse.'"
        return f"'The past is the past. I try to look forward.'"

    def _dialogue_weather(self, world_state):
        weather = world_state.get("weather", {})
        condition = weather.get("condition", "clear")
        responses = {
            "clear": "'Beautiful day. Makes you glad to be alive.'",
            "cloudy": "'Overcast. Good weather for work — no distractions.'",
            "foggy": "'The fog is thick today. I can barely see the harbor. There's something peaceful about it, though.'",
            "rain": "'Rain. The village needs it. My bones don't appreciate it, but the village does.'",
            "storm": "'That storm is something else. I'm glad to be inside. The sea is angry today.'",
        }
        return responses.get(condition, "'Weather comes and goes. We endure.'")

    def _dialogue_ritual(self, profile, rel, world_state=None):
        """
        When the player is in the same location as an NPC during ritual
        preparation_days, surface that ritual as dialogue.

        The ritual definitions live in the Python RITUALS dict; the DB only
        tracks phase ('upcoming', 'preparing', 'completed').
        """
        if world_state is None:
            world_state = {}

        # Get the current preparing ritual from the DB state table
        try:
            row = self.db.execute("""
                SELECT ritual_key FROM ritual_state
                WHERE phase = 'preparing'
                LIMIT 1
            """).fetchone()
        except Exception:
            return None  # table missing or schema mismatch — skip silently

        if not row:
            return None

        ritual_key = row[0] if row else None
        ritual = RITUALS.get(ritual_key, {}) if ritual_key else {}
        if not ritual:
            return None

        prep_lines = ritual.get("preparation", [])
        title = ritual.get("title", "The ritual")
        name = self.npc[1].split()[0] if self.npc and self.npc[1] else "They"

        if not prep_lines:
            return None

        prep_line = random.choice(prep_lines) if isinstance(prep_lines, list) else str(prep_lines)

        # Relationship-scope the dialogue
        if rel in ("close_friend", "friend"):
            return f"'{title} — {prep_line} I'd like you there, if you want.'"
        elif rel == "acquaintance":
            return f"'{title} is coming. {prep_line}'"
        else:
            return f"'{title} soon. Just something we do here.'"

    def _dialogue_default(self, profile, rel):
        defaults = [
            f"'Hmm. That's something to think about.'",
            f"'I'm not sure what to say to that.'",
            f"'Interesting. Tell me more.'",
            f"'You have a way of seeing things differently.'",
        ]
        if rel == "close_friend":
            defaults.append("'You always know the right questions to ask.'")
        return random.choice(defaults)

    def save(self):
        """Save interaction memory back to NPC properties."""
        self.properties["owl_interactions"] = self.interactions
        self.properties["owl_relationship"] = self.relationship_level
        self.properties["owl_trust"] = round(self.trust, 3)
        self.properties["owl_affection"] = round(self.affection, 3)
        self.properties["owl_respect"] = round(self.respect, 3)
        self.properties["owl_times_met"] = self.times_met
        self.properties["owl_last_topic"] = self.last_topic

        self.db.execute(
            "UPDATE agents SET properties = ?, updated_at = ? WHERE id = ?",
            (json.dumps(self.properties), time.time(), self.npc_id)
        )
        self.db.commit()


def init_npc_depth(db):
    """Initialize deep profiles for all NPCs."""
    npcs = db.execute("SELECT * FROM agents WHERE type = 'npc'").fetchall()
    for npc in npcs:
        try:
            props = json.loads(npc["properties"]) if npc["properties"] else {}
        except (json.JSONDecodeError, TypeError):
            props = {}

        if "psychological_profile" not in props:
            props["psychological_profile"] = generate_psychological_profile(props)

        if "owl_interactions" not in props:
            props["owl_interactions"] = []
            props["owl_relationship"] = "stranger"
            props["owl_trust"] = 0.5
            props["owl_affection"] = 0.5
            props["owl_respect"] = 0.5
            props["owl_times_met"] = 0

        db.execute(
            "UPDATE agents SET properties = ? WHERE id = ?",
            (json.dumps(props), npc["id"])
        )
    db.commit()


def get_npc_depth_story(db, npc_id: str) -> dict:
    """Get the full depth story of an NPC."""
    npc = db.execute("SELECT * FROM agents WHERE id = ?", (npc_id,)).fetchone()
    if not npc:
        return {}

    try:
        props = json.loads(npc["properties"]) if npc["properties"] else {}
    except (json.JSONDecodeError, TypeError):
        props = {}

    profile = props.get("psychological_profile", {})
    memory = OWLInteractionMemory(npc_id, db)

    return {
        "name": npc["name"],
        "occupation": props.get("occupation", ""),
        "personality": props.get("personality", ""),
        "age": props.get("age", 0),
        "profile": profile,
        "relationship": memory.relationship_level,
        "trust": memory.trust,
        "affection": memory.affection,
        "respect": memory.respect,
        "times_met": memory.times_met,
        "recent_interactions": memory.interactions[:5],
    }
