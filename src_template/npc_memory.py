"""
npc_memory.py — NPC memory system with emotional salience.

NPCs don't just remember events — they remember them with feeling.
A kindness from a friend lingers. A betrayal cuts deep and fades slowly.
A conversation about the weather evaporates by afternoon.

Each memory has:
- Emotional valence: how positive or negative it felt (-1.0 to 1.0)
- Weight: how important it is right now (0.0 to 1.0)
- Decay rate: how fast it fades (slower for intense emotions)
- Reinforcement: related events strengthen the memory

The system provides:
- Store new memories with emotional context
- Retrieve salient memories (highest current weight)
- Decay all memories over time
- Reinforce related memories when similar events happen
- Emotional summary: what an NPC "feels" about another NPC
"""

import json
import math
import random
import time
from typing import Optional

from .world_state import get_db, log_event, DB_PATH


# ── CONSTANTS ──

# Decay rates per emotion category (per game-day)
DECAY_RATES = {
    "neutral": 0.15,    # Weather talk, mundane observations — fade fast
    "mild": 0.08,       # Pleasant/unpleasant but not intense
    "strong": 0.04,     # Significant emotional events — linger
    "trauma": 0.02,     # Betrayal, loss — very slow decay
}

# Valence thresholds
VALENCE_MILD = 0.3
VALENCE_STRONG = 0.6

# Maximum memories per NPC (to prevent unbounded growth)
MAX_MEMORIES_PER_NPC = 50


# ── INIT ──

def init_memory_tables(db):
    """Initialize the NPC memory tables."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS npc_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT NOT NULL,
            emotional_valence REAL DEFAULT 0.0,
            weight REAL DEFAULT 0.5,
            decay_rate REAL DEFAULT 0.1,
            related_npc_id TEXT DEFAULT NULL,
            location_id TEXT DEFAULT NULL,
            created_at REAL NOT NULL,
            last_reinforced_at REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_memories_npc ON npc_memories(npc_id);
        CREATE INDEX IF NOT EXISTS idx_memories_related ON npc_memories(related_npc_id);
        CREATE INDEX IF NOT EXISTS idx_memories_weight ON npc_memories(weight);
    """)
    db.commit()


# ── MEMORY CREATION ──

def _classify_intensity(valence: float) -> str:
    """Classify emotional intensity based on absolute valence."""
    abs_val = abs(valence)
    if abs_val >= 0.8:
        return "trauma"
    elif abs_val >= VALENCE_STRONG:
        return "strong"
    elif abs_val >= VALENCE_MILD:
        return "mild"
    else:
        return "neutral"


def _get_decay_rate(valence: float) -> float:
    """Get decay rate based on emotional intensity."""
    intensity = _classify_intensity(valence)
    return DECAY_RATES[intensity]


def store_memory(
    db,
    npc_id: str,
    event_type: str,
    description: str,
    emotional_valence: float = 0.0,
    weight: float = 0.5,
    related_npc_id: Optional[str] = None,
    location_id: Optional[str] = None,
) -> int:
    """
    Store a new memory for an NPC.

    Args:
        db: Database connection
        npc_id: The NPC who remembers
        event_type: Category — conversation, conflict, gift, observation, etc.
        description: Human-readable memory text
        emotional_valence: -1.0 (very negative) to 1.0 (very positive)
        weight: Initial importance (0.0 to 1.0)
        related_npc_id: Optional — the other NPC involved
        location_id: Optional — where it happened

    Returns:
        The memory ID
    """
    now = time.time()
    decay_rate = _get_decay_rate(emotional_valence)

    # Clamp values
    emotional_valence = max(-1.0, min(1.0, emotional_valence))
    weight = max(0.0, min(1.0, weight))

    db.execute("""
        INSERT INTO npc_memories
        (npc_id, event_type, description, emotional_valence, weight, decay_rate,
         related_npc_id, location_id, created_at, last_reinforced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (npc_id, event_type, description, emotional_valence, weight, decay_rate,
          related_npc_id, location_id, now, now))

    db.commit()

    # Prune old memories if over limit
    _prune_memories(db, npc_id)

    return db.execute("SELECT last_insert_rowid() as id").fetchone()[0]


# ── MEMORY RETRIEVAL ──

def get_salient_memories(db, npc_id: str, limit: int = 5, related_npc_id: Optional[str] = None) -> list:
    """
    Get the most salient (highest current weight) memories for an NPC.

    Current weight is computed as:
        current_weight = weight * exp(-decay_rate * days_since_reinforcement)

    This means:
    - Recent, emotionally intense memories are most salient
    - Old, neutral memories fade to near-zero
    - Reinforced memories get a fresh decay timer

    Args:
        db: Database connection
        npc_id: The NPC whose memories to retrieve
        limit: Maximum number of memories to return
        related_npc_id: Optional — filter to memories about a specific NPC

    Returns:
        List of memory dicts, sorted by current salience (highest first)
    """
    now = time.time()

    if related_npc_id:
        rows = db.execute("""
            SELECT * FROM npc_memories
            WHERE npc_id = ? AND related_npc_id = ?
            ORDER BY weight DESC
        """, (npc_id, related_npc_id)).fetchall()
    else:
        rows = db.execute("""
            SELECT * FROM npc_memories
            WHERE npc_id = ?
            ORDER BY weight DESC
        """, (npc_id,)).fetchall()

    memories = []
    for row in rows:
        # Compute current salience with decay
        days_since_reinforcement = (now - row["last_reinforced_at"]) / 86400.0
        current_weight = row["weight"] * math.exp(-row["decay_rate"] * days_since_reinforcement)

        memory = {
            "id": row["id"],
            "npc_id": row["npc_id"],
            "event_type": row["event_type"],
            "description": row["description"],
            "emotional_valence": row["emotional_valence"],
            "weight": row["weight"],
            "current_salience": current_weight,
            "decay_rate": row["decay_rate"],
            "related_npc_id": row["related_npc_id"],
            "location_id": row["location_id"],
            "created_at": row["created_at"],
            "last_reinforced_at": row["last_reinforced_at"],
        }
        memories.append(memory)

    # Sort by current salience
    memories.sort(key=lambda m: m["current_salience"], reverse=True)

    return memories[:limit]


def get_emotional_summary(db, npc_id: str, related_npc_id: str) -> dict:
    """
    Get a summary of how an NPC feels about another NPC.

    Returns:
        dict with:
        - overall_valence: weighted average of memory valences (-1 to 1)
        - dominant_emotion: the strongest emotional category
        - memory_count: total memories about this NPC
        - most_salient: the single most salient memory
        - trend: "warming", "cooling", or "stable" based on recent vs older memories
    """
    memories = get_salient_memories(db, npc_id, limit=20, related_npc_id=related_npc_id)

    if not memories:
        return {
            "overall_valence": 0.0,
            "dominant_emotion": "neutral",
            "memory_count": 0,
            "most_salient": None,
            "trend": "neutral",
        }

    # Weighted average valence (by current salience)
    total_salience = sum(m["current_salience"] for m in memories)
    if total_salience == 0:
        overall_valence = 0.0
    else:
        overall_valence = sum(m["emotional_valence"] * m["current_salience"] for m in memories) / total_salience

    # Dominant emotion from the most salient memory
    most_salient = memories[0]
    dominant_emotion = _classify_intensity(most_salient["emotional_valence"])

    # Trend: compare recent memories (last 3 days) to older ones
    now = time.time()
    recent = [m for m in memories if (now - m["created_at"]) < 259200]  # 3 days
    older = [m for m in memories if (now - m["created_at"]) >= 259200]

    if recent and older:
        recent_valence = sum(m["emotional_valence"] for m in recent) / len(recent)
        older_valence = sum(m["emotional_valence"] for m in older) / len(older)
        diff = recent_valence - older_valence
        if diff > 0.1:
            trend = "warming"
        elif diff < -0.1:
            trend = "cooling"
        else:
            trend = "stable"
    elif recent:
        trend = "warming" if overall_valence > 0 else "cooling" if overall_valence < 0 else "stable"
    else:
        trend = "stable"

    return {
        "overall_valence": round(overall_valence, 3),
        "dominant_emotion": dominant_emotion,
        "memory_count": len(memories),
        "most_salient": most_salient,
        "trend": trend,
    }


# ── MEMORY REINFORCEMENT ──

def reinforce_memories(db, npc_id: str, event_type: str, related_npc_id: Optional[str] = None,
                       location_id: Optional[str] = None, boost: float = 0.15) -> int:
    """
    Reinforce existing memories that match the given context.

    When an NPC experiences something similar to a past memory,
    that memory becomes stronger and its decay timer resets.

    Args:
        db: Database connection
        npc_id: The NPC whose memories to reinforce
        event_type: Match memories of this type
        related_npc_id: Optional — match memories about this NPC
        location_id: Optional — match memories from this location
        boost: How much to increase weight by

    Returns:
        Number of memories reinforced
    """
    now = time.time()
    reinforced = 0

    # Build query dynamically
    query = "SELECT * FROM npc_memories WHERE npc_id = ? AND event_type = ?"
    params = [npc_id, event_type]

    if related_npc_id:
        query += " AND related_npc_id = ?"
        params.append(related_npc_id)

    if location_id:
        query += " AND location_id = ?"
        params.append(location_id)

    rows = db.execute(query, params).fetchall()

    for row in rows:
        new_weight = min(1.0, row["weight"] + boost)
        db.execute("""
            UPDATE npc_memories
            SET weight = ?, last_reinforced_at = ?
            WHERE id = ?
        """, (new_weight, now, row["id"]))
        reinforced += 1

    # Also reinforce memories about the same NPC even if event type differs
    if related_npc_id:
        rows2 = db.execute("""
            SELECT * FROM npc_memories
            WHERE npc_id = ? AND related_npc_id = ? AND event_type != ?
        """, (npc_id, related_npc_id, event_type)).fetchall()

        for row in rows2:
            new_weight = min(1.0, row["weight"] + boost * 0.5)  # Half boost for tangential
            db.execute("""
                UPDATE npc_memories
                SET weight = ?, last_reinforced_at = ?
                WHERE id = ?
            """, (new_weight, now, row["id"]))
            reinforced += 1

    db.commit()
    return reinforced


# ── MEMORY DECAY ──

def decay_all_memories(db, hours_passed: float = 1.0) -> int:
    """
    Apply time-based decay to all memories.

    This should be called periodically (e.g., every simulation tick).
    Uses exponential decay: weight *= exp(-decay_rate * days)

    Args:
        db: Database connection
        hours_passed: How many game-hours have passed

    Returns:
        Number of memories that were decayed
    """
    # Convert hours to days for decay calculation
    days = hours_passed / 24.0

    rows = db.execute("SELECT * FROM npc_memories WHERE weight > 0.01").fetchall()
    decayed = 0

    for row in rows:
        # Exponential decay based on this memory's decay rate
        new_weight = row["weight"] * math.exp(-row["decay_rate"] * days)
        if new_weight < 0.01:
            new_weight = 0.01  # Floor — memories never fully disappear

        if new_weight != row["weight"]:
            db.execute("UPDATE npc_memories SET weight = ? WHERE id = ?",
                       (round(new_weight, 4), row["id"]))
            decayed += 1

    db.commit()
    return decayed


# ── MEMORY PRUNING ──

def _prune_memories(db, npc_id: str):
    """Remove lowest-weight memories if NPC has too many."""
    count = db.execute(
        "SELECT COUNT(*) as cnt FROM npc_memories WHERE npc_id = ?", (npc_id,)
    ).fetchone()[0]

    if count <= MAX_MEMORIES_PER_NPC:
        return

    # Remove the lowest-weight memories
    excess = count - MAX_MEMORIES_PER_NPC
    db.execute("""
        DELETE FROM npc_memories
        WHERE id IN (
            SELECT id FROM npc_memories
            WHERE npc_id = ?
            ORDER BY weight ASC
            LIMIT ?
        )
    """, (npc_id, excess))
    db.commit()


# ── CONVENIENCE: MEMORY FROM CONVERSATION ──

def remember_conversation(db, npc_a_id: str, npc_b_id: str, location_id: str,
                         topic: str, affinity: float, was_positive: bool) -> tuple:
    """
    Create memories for both NPCs after a conversation.

    The memory's emotional valence is derived from:
    - The affinity between the NPCs
    - Whether the conversation was positive
    - The topic (some topics are more memorable)

    Returns:
        (memory_a_id, memory_b_id)
    """
    now = time.time()

    # Determine valence
    base_valence = (affinity - 0.5) * 2.0  # Map 0-1 to -1 to 1
    if was_positive:
        valence = min(1.0, base_valence + 0.2)
    else:
        valence = max(-1.0, base_valence - 0.2)

    # Weight based on topic significance
    significant_topics = {"conflict", "betrayal", "gift", "confession", "secret", "help"}
    if topic in significant_topics:
        weight = 0.7
    elif affinity > 0.7 or affinity < 0.3:
        weight = 0.6  # Extreme affinities are more memorable
    else:
        weight = 0.4

    # Create memory descriptions
    npc_a_name = db.execute("SELECT name FROM agents WHERE id = ?", (npc_a_id,)).fetchone()
    npc_b_name = db.execute("SELECT name FROM agents WHERE id = ?", (npc_b_id,)).fetchone()
    a_name = npc_a_name["name"] if npc_a_name else "Someone"
    b_name = npc_b_name["name"] if npc_b_name else "Someone"

    loc_clean = location_id.replace("_", " ") if location_id else "the valley"

    if was_positive:
        desc_a = f"Talked with {b_name} at {loc_clean} about {topic}. It was good."
        desc_b = f"Talked with {a_name} at {loc_clean} about {topic}. It was good."
    else:
        desc_a = f"Talked with {b_name} at {loc_clean} about {topic}. It was tense."
        desc_b = f"Talked with {a_name} at {loc_clean} about {topic}. It was tense."

    mem_a = store_memory(db, npc_a_id, "conversation", desc_a,
                         emotional_valence=valence, weight=weight,
                         related_npc_id=npc_b_id, location_id=location_id)
    mem_b = store_memory(db, npc_b_id, "conversation", desc_b,
                         emotional_valence=valence, weight=weight,
                         related_npc_id=npc_a_id, location_id=location_id)

    return mem_a, mem_b


# ── CONVENIENCE: MEMORY FROM EVENT ──

def remember_event(db, npc_id: str, event: dict, was_affected: bool = True) -> Optional[int]:
    """
    Create a memory from a world event.

    Args:
        db: Database connection
        npc_id: The NPC who experienced the event
        event: The event dict (from events.py)
        was_affected: Whether this NPC was directly affected

    Returns:
        Memory ID, or None if the event isn't memorable
    """
    event_type = event.get("type", "unknown")
    title = event.get("title", "")
    desc = event.get("description", "")
    location_id = event.get("location_id", "")

    # Determine if this event is memorable
    memorable_types = {
        "social_argument", "new_conflict", "breakup", "new_alliance",
        "celebration", "traveling_trader", "bear_sighting", "storm_damage",
        "mushroom_bloom", "wedding", "funeral", "birth",
    }

    if event_type not in memorable_types and not was_affected:
        return None

    # Determine emotional valence from event type
    positive_types = {"celebration", "new_alliance", "wedding", "birth", "mushroom_bloom", "traveling_trader"}
    negative_types = {"social_argument", "new_conflict", "breakup", "storm_damage", "funeral"}

    if event_type in positive_types:
        valence = random.uniform(0.3, 0.8)
        weight = 0.6
    elif event_type in negative_types:
        valence = random.uniform(-0.8, -0.3)
        weight = 0.7
    else:
        valence = random.uniform(-0.2, 0.2)
        weight = 0.4

    memory_desc = f"{title}. {desc}" if title else desc

    return store_memory(db, npc_id, event_type, memory_desc,
                        emotional_valence=valence, weight=weight,
                        location_id=location_id)


# ── FORMATTING FOR NARRATIVE ──

def format_memory_for_dialogue(memory: dict, npc_name: str, other_name: str) -> Optional[str]:
    """
    Format a memory as dialogue text that an NPC might reference.

    Returns a prose string like:
        "Mira remembers when Thomas helped her clear the trail. She brings it up."
    """
    if not memory:
        return None

    desc = memory.get("description", "")
    valence = memory.get("emotional_valence", 0.0)
    event_type = memory.get("event_type", "")

    if event_type == "conversation":
        if valence > 0.3:
            templates = [
                f"{npc_name} remembers the conversation with {other_name}. It was good.",
                f"A thought crosses {npc_name}'s mind — {other_name}, and what they said.",
                f"{npc_name} smiles, remembering {other_name}.",
            ]
        elif valence < -0.3:
            templates = [
                f"{npc_name} thinks of {other_name}. The memory is not warm.",
                f"Something {other_name} said still sits with {npc_name}.",
                f"{npc_name}'s expression shifts, just slightly, at the thought of {other_name}.",
            ]
        else:
            return None  # Neutral memories don't surface in dialogue

        return random.choice(templates)

    elif event_type in ("conflict", "social_argument", "new_conflict"):
        return f"{npc_name} hasn't forgotten what happened with {other_name}."

    elif event_type in ("gift", "help"):
        return f"{npc_name} remembers {other_name}'s kindness."

    elif event_type == "betrayal":
        return f"The wound {other_name} left is still there."

    return None
