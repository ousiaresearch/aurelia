"""
narrative.py — Procedural narrative engine.

Weaves events, social dynamics, and world state into emergent stories.
Stories are not scripted — they arise from the interactions of systems.

The narrative engine:
1. Collects recent events and changes
2. Identifies patterns and connections
3. Weaves them into narrative arcs
4. Presents them as stories the player discovers

Story types:
- Personal dramas (NPC relationships, conflicts, joys)
- Community events (celebrations, crises, changes)
- Environmental stories (the village itself changing)
- Mysteries (things that need explaining)

Design principles:
- Stories emerge, they're not told
- The player discovers stories by being present
- Stories have beginnings, middles, and sometimes endings
- Multiple story threads run concurrently
- Stories affect the world and vice versa
"""

import json
import random
import time
from typing import Optional

from .world_state import get_db, log_event, DB_PATH


# ── NARRATIVE TEMPLATES ──

STORY_OPENERS = {
    "conflict": [
        "Tension has been building for days.",
        "It started small, as these things do.",
        "Nobody knows exactly how it began.",
        "The signs were there, if anyone had been watching.",
    ],
    "romance": [
        "Something has been growing between them.",
        "It began with a glance, then a conversation.",
        "The whole clearing has noticed, though they pretend not to.",
        "Love, as always, arrived unannounced.",
    ],
    "mystery": [
        "Something strange is happening in the clearing.",
        "People are talking in hushed voices.",
        "There are questions without answers.",
        "The forest holds its secrets close.",
    ],
    "change": [
        "Things are changing in the valley.",
        "The old ways are shifting.",
        "Something new is coming. Everyone can feel it.",
        "The clearing is not what it was.",
    ],
    "celebration": [
        "Joy, when it comes, comes all at once.",
        "The clearing deserves a celebration.",
        "After so much hardship, something good.",
        "The whole cabin seems to smile.",
    ],
    "hardship": [
        "These are hard times.",
        "The valley endures, as it always has.",
        "Some burdens are shared, some are carried alone.",
        "The forest gives, and the forest takes away.",
    ],
}

STORY_DEVELOPERS = {
    "conflict": [
        "The argument spilled into the street.",
        "Friends have been forced to choose sides.",
        "Words were spoken that cannot be unsaid.",
        "The tension is palpable. Everyone feels it.",
    ],
    "romance": [
        "They find excuses to be together.",
        "A gift was exchanged. Something meaningful.",
        "They walked the forest trail at sunset, hand in hand.",
        "The whole clearing smiles when they're together.",
    ],
    "mystery": [
        "Another clue, but it raises more questions.",
        "Someone saw something. Or did they?",
        "The old stories might hold an answer.",
        "Not everything has a rational explanation.",
    ],
    "change": [
        "The change is irreversible now.",
        "Some resist, some embrace it.",
        "The clearing adapts, as it always does.",
        "What was lost? What was gained?",
    ],
    "celebration": [
        "The cabin fills with laughter.",
        "Music and dancing late into the night.",
        "Even the weather seems to cooperate.",
        "For one night, all is well.",
    ],
    "hardship": [
        "The stores are running low.",
        "People help each other. That's what the clearing does.",
        "The forest has been unforgiving.",
        "But the community holds together.",
    ],
}

STORY_RESOLUTIONS = {
    "conflict": [
        "A quiet reconciliation. Not everything was forgiven, but the fighting stopped.",
        "Someone made the first gesture. The clearing breathed again.",
        "Time, as it does, began to heal the wound.",
        "The conflict resolved itself, as conflicts do — not with a bang, but with exhaustion.",
    ],
    "romance": [
        "A wedding, small and beautiful, in the cabin among the cedars.",
        "They moved in together. A new cabin, a new life.",
        "The clearing celebrates. Love won.",
        "Some stories don't end. They just continue.",
    ],
    "mystery": [
        "The mystery solved itself, as mysteries do — slowly, then all at once.",
        "Some mysteries remain. The forest is big enough for a few secrets.",
        "The answer was there all along, hidden in plain sight.",
        "Not every question needs an answer.",
    ],
    "change": [
        "The clearing has changed. Whether for better or worse, only time will tell.",
        "The change is complete. A new normal.",
        "Life goes on, as it always does.",
        "The valley remembers what was, and embraces what is.",
    ],
    "celebration": [
        "The celebration fades, as all celebrations do. But the memory remains.",
        "A good day. A necessary day.",
        "The clearing needed that. Everyone did.",
        "Joy, even briefly, leaves its mark.",
    ],
    "hardship": [
        "The hardship passes. It always does.",
        "The valley endures. It always has.",
        "Better days are coming. They always do.",
        "The community held. That's what matters.",
    ],
}


class StoryArc:
    """A narrative arc that develops over time."""

    def __init__(self, story_type: str, participants: list, trigger_event: str):
        self.story_type = story_type
        self.participants = participants
        self.trigger_event = trigger_event
        self.phase = "beginning"  # beginning, middle, end
        self.events = []
        self.created_at = time.time()
        self.last_update = time.time()

    def advance(self):
        """Move the story to the next phase."""
        if self.phase == "beginning":
            self.phase = "middle"
        elif self.phase == "middle":
            self.phase = "end"
        self.last_update = time.time()

    def is_complete(self) -> bool:
        return self.phase == "end" and (time.time() - self.last_update) > 86400  # 1 day

    def generate_narrative(self) -> str:
        """Generate a narrative description of the current story state."""
        participants_str = ", ".join(self.participants[:3]) if self.participants else "the village"
        if not participants_str:
            participants_str = "the village"

        if self.phase == "beginning":
            opener = random.choice(STORY_OPENERS.get(self.story_type, ["Something is happening."]))
            # Tailor opening to story type and participants
            if self.story_type == "conflict":
                return f"{opener}\n\nIt involves {participants_str}. {self._tailored_middle()} The story is just beginning."
            elif self.story_type == "romance":
                return f"{opener}\n\nBetween {participants_str}. {self._tailored_middle()} The story is just beginning."
            elif self.story_type == "celebration":
                return f"{opener}\n\n{participants_str} are at the center of it. The story is just beginning."
            elif self.story_type == "hardship":
                return f"{opener}\n\nIt touches {participants_str}. {self._tailored_middle()} The story is just beginning."
            else:
                return f"{opener}\n\nIt involves {participants_str}. The story is just beginning."

        elif self.phase == "middle":
            return f"{self._tailored_middle()}\n\n{participants_str}. The story deepens."

        else:  # end
            resolution = random.choice(STORY_RESOLUTIONS.get(self.story_type, ["The story concludes."]))
            return f"{resolution}"

    def _tailored_middle(self) -> str:
        """Generate a middle-phase description tailored to story type and participants."""
        devs = STORY_DEVELOPERS.get(self.story_type, ["The situation evolves."])
        dev = random.choice(devs)
        if not self.events:
            return dev
        # Use the last actual event to personalize
        last_event = self.events[-1] if self.events else ""
        # Extract a fragment from the event for authenticity
        if last_event and len(last_event) > 10:
            fragment = last_event[:80].strip()
            if not fragment.endswith(('.', '!', '?')):
                fragment = fragment.rsplit(' ', 1)[0] + '…'
            return f"{dev} Recent word has it: \"{fragment}\""
        return dev

    def to_dict(self) -> dict:
        return {
            "type": self.story_type,
            "participants": self.participants,
            "phase": self.phase,
            "events": self.events,
            "created_at": self.created_at,
        }


def init_narrative_tables(db):
    """Initialize narrative tables."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS story_arcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_type TEXT NOT NULL,
            participants TEXT DEFAULT '[]',
            phase TEXT DEFAULT 'beginning',
            trigger_event TEXT DEFAULT '',
            events TEXT DEFAULT '[]',
            active INTEGER DEFAULT 1,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS narrative_moments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            story_arc_id INTEGER REFERENCES story_arcs(id),
            content TEXT NOT NULL,
            location_id TEXT DEFAULT NULL,
            discovered INTEGER DEFAULT 0
        );
    """)
    db.commit()


def update_narratives(db) -> list:
    """
    Update active story arcs and potentially create new ones.
    Returns a list of narrative moments for the player to discover.
    """
    moments = []
    now = time.time()

    # Get active story arcs
    arcs = db.execute("SELECT * FROM story_arcs WHERE active = 1").fetchall()

    for arc_row in arcs:
        participants = json.loads(arc_row["participants"]) if arc_row["participants"] else []
        events = json.loads(arc_row["events"]) if arc_row["events"] else []
        story_type = arc_row["story_type"]
        phase = arc_row["phase"]
        arc_id = arc_row["id"]

        # Check for new events involving participants
        recent_events = db.execute("""
            SELECT * FROM events
            WHERE timestamp > ? AND agent_id = 'event'
            ORDER BY timestamp DESC LIMIT 20
        """, (arc_row["updated_at"],)).fetchall()

        new_events_found = False
        for event in recent_events:
            # Check if event is related to this story (participant name in description)
            desc = event["description"] or ""
            if any(p.lower() in desc.lower() for p in participants):
                events.append(event["description"])
                new_events_found = True

        if new_events_found:
            # Advance story phase based on accumulated events
            if len(events) >= 3 and phase == "beginning":
                phase = "middle"
                story = StoryArc(story_type, participants, arc_row["trigger_event"])
                story.phase = "middle"
                story.events = events
                narrative = story.generate_narrative()
                moments.append(narrative)

            elif len(events) >= 6 and phase == "middle":
                phase = "end"
                story = StoryArc(story_type, participants, arc_row["trigger_event"])
                story.phase = "end"
                story.events = events
                narrative = story.generate_narrative()
                moments.append(narrative)

            # Persist phase and event changes to DB
            db.execute("""
                UPDATE story_arcs
                SET phase = ?, events = ?, updated_at = ?
                WHERE id = ?
            """, (phase, json.dumps(events), now, arc_id))

        # Check if arc should be retired (ended with enough events)
        if phase == "end" and len(events) > 8:
            db.execute("UPDATE story_arcs SET active = 0 WHERE id = ?", (arc_id,))

    db.commit()
    return moments


def create_story_arc(db, story_type: str, participants: list, trigger_event: str) -> Optional[int]:
    """Create a new story arc."""
    # Check if a similar arc already exists
    existing = db.execute(
        "SELECT COUNT(*) as cnt FROM story_arcs WHERE story_type = ? AND active = 1",
        (story_type,)
    ).fetchone()

    if existing["cnt"] >= 3:
        return None  # Max 3 active arcs of same type

    now = time.time()
    db.execute("""
        INSERT INTO story_arcs (story_type, participants, trigger_event, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (story_type, json.dumps(participants), trigger_event, now, now))
    db.commit()

    return db.execute("SELECT last_insert_rowid() as id").fetchone()["id"]


def get_active_stories(db) -> list:
    """Get all active story arcs."""
    rows = db.execute("SELECT * FROM story_arcs WHERE active = 1 ORDER BY updated_at DESC").fetchall()
    stories = []
    for row in rows:
        story = StoryArc(
            row["story_type"],
            json.loads(row["participants"]) if row["participants"] else [],
            row["trigger_event"],
        )
        story.phase = row["phase"]
        story.events = json.loads(row["events"]) if row["events"] else []
        story.last_update = row["updated_at"]
        stories.append(story)
    return stories


def discover_narrative(db, location_id: str) -> list:
    """
    Check for undiscovered narrative moments at the current location.
    Returns narratives the player discovers by being present.
    """
    rows = db.execute("""
        SELECT * FROM narrative_moments
        WHERE location_id = ? AND discovered = 0
        ORDER BY timestamp DESC LIMIT 3
    """, (location_id,)).fetchall()

    moments = []
    for row in rows:
        moments.append(row["content"])
        db.execute("UPDATE narrative_moments SET discovered = 1 WHERE id = ?", (row["id"],))

    db.commit()
    return moments
