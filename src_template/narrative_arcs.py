"""
narrative_arcs.py — Multi-interaction story arcs, NPC-initiated storytelling, and seasonal beats.

This module handles the higher-order narrative logic:

1. STORY ARC CREATION
   - Scans recent events for story-worthy patterns (conflicts, alliances, discoveries)
   - Creates story_arcs DB entries when a multi-interaction narrative begins
   - Triggers on NPC conversations, social dynamics, ritual completions, discoveries

2. NPC-INITIATED STORYTELLING
   - When an NPC has a story arc relevant to the player's location, they may mention it
   - NPC dialogue can reference ongoing stories (not just trigger them)
   - NPCs can "push" stories toward the player — hint at mysteries, invite participation

3. SEASONAL BEATS
   - Each season has narrative rhythms (repeating events, traditions, tensions)
   - Season transitions trigger significant narrative moments
   - Seasonal beats layer over active story arcs (a conflict becomes more tense in autumn)

4. STORY DISCOVERY (for the player)
   - Active stories are surfaced to the player through the /stories command
   - Player presence in locations where stories are unfolding accelerates arc progress
   - Stories can be "engaged" — the player's actions become part of the narrative

Design principles:
- Stories are discovered, not delivered
- NPC-initiated stories feel organic, not mechanical
- Seasonal beats give the world rhythm and anticipation
- Arc phase transitions feel like turning pages, not arbitrary thresholds
"""

import json
import random
import time
from typing import Optional

from .world_state import get_db, log_event, DB_PATH
from .narrative import init_narrative_tables, create_story_arc, StoryArc


# ── SEASONAL BEATS ────────────────────────────────────────────────────────────

SEASONAL_BEATS = {
    "spring": {
        "theme": "renewal and stirring",
        "beats": [
            {"name": "first_warm_day", "chance": 0.4, "weight": 0.8,
             "description": "The first warm day of the year. Everyone is outside."},
            {"name": "planting_community", "chance": 0.3, "weight": 0.9,
             "description": "The community gathers to plant. Old rivalries are set aside."},
            {"name": "late_frost", "chance": 0.15, "weight": 0.6,
             "description": "A late frost comes unexpectedly. Crops are threatened."},
            {"name": "traveler_arrives", "chance": 0.25, "weight": 0.5,
             "description": "A traveler arrives with news from beyond the valley."},
            {"name": "mushroom_bloom", "chance": 0.3, "weight": 0.4,
             "description": "The first mushroom bloom of the year draws foragers to the forest."},
        ],
        "story_prompts": ["new_beginnings", "old_wounds_healing", "arrivals_and_departures"],
    },
    "summer": {
        "theme": "expansion and abundance",
        "beats": [
            {"name": "long_day_gathering", "chance": 0.4, "weight": 0.9,
             "description": "The longest day is celebrated with fire and music until dawn."},
            {"name": "heat_wave", "chance": 0.2, "weight": 0.6,
             "description": "The heat presses down on the valley. People grow short-tempered."},
            {"name": "river_party", "chance": 0.35, "weight": 0.7,
             "description": "Someone organizes a river party. The whole community is invited."},
            {"name": "forest_fire_risk", "chance": 0.1, "weight": 0.5,
             "description": "The forest is dry. Everyone is careful with fire."},
            {"name": "festival_prep", "chance": 0.3, "weight": 0.8,
             "description": "Preparations for the midsummer festival fill the clearing with energy."},
        ],
        "story_prompts": ["community_joy", "summer_love", "hidden_tensions"],
    },
    "autumn": {
        "theme": "completion and reflection",
        "beats": [
            {"name": "harvest_community", "chance": 0.5, "weight": 1.0,
             "description": "The harvest brings the community together. Abundance is shared."},
            {"name": "preparation_urgency", "chance": 0.35, "weight": 0.8,
             "description": "Everyone feels the pressure to prepare before winter. Tempers shorten."},
            {"name": "mysterious_stranger", "chance": 0.2, "weight": 0.6,
             "description": "A stranger passes through, asking strange questions."},
            {"name": "first_frost", "chance": 0.3, "weight": 0.7,
             "description": "The first frost arrives. The forest begins to turn."},
            {"name": "animal_migration", "chance": 0.25, "weight": 0.4,
             "description": "The animals move through the valley in great numbers. Hunting is good."},
        ],
        "story_prompts": ["completion_and_loss", "preparing_for_darkness", "revealed_secrets"],
    },
    "winter": {
        "theme": "rest and interiority",
        "beats": [
            {"name": "first_snow", "chance": 0.4, "weight": 0.9,
             "description": "The first snow falls gently. The valley transforms."},
            {"name": "deep_freeze", "chance": 0.2, "weight": 0.6,
             "description": "A deep freeze settles over the valley. The creek runs solid."},
            {"name": "cabin_stories", "chance": 0.4, "weight": 0.8,
             "description": "Old stories are told by the fire. History comes alive."},
            {"name": "solstice_dark", "chance": 0.15, "weight": 0.7,
             "description": "The longest night. Some say strange things happen in the dark."},
            {"name": "blizzard", "chance": 0.1, "weight": 0.5,
             "description": "A blizzard isolates the valley. People turn inward."},
        ],
        "story_prompts": ["interior_conflicts", "old_secrets", "patience_and_endurance"],
    },
}

# Stories escalate in autumn/winter, resolve in spring/summer
SEASON_STORY_MODIFIER = {
    "spring": 1.0,
    "summer": 1.0,
    "autumn": 1.4,
    "winter": 1.2,
}


# ── STORY-WORTHY EVENT PATTERNS ──────────────────────────────────────────────

# Events that can trigger a story arc creation
STORY_TRIGGER_TYPES = {
    "npc_conflict", "social_argument", "rivalry", "betrayal",
    "new_alliance", "celebration", "farewell",
    "relationship_shift", "relationship_new",
    "discovery", "mystery_sign", "ritual_completed",
    "seasonal", "story_born",
}

STORY_TYPE_FROM_TRIGGER = {
    "npc_conflict": "conflict",
    "social_argument": "conflict",
    "rivalry": "conflict",
    "betrayal": "conflict",
    "new_alliance": "celebration",
    "celebration": "celebration",
    "farewell": "change",
    "relationship_shift": "romance",
    "relationship_new": "romance",
    "discovery": "mystery",
    "mystery_sign": "mystery",
    "ritual_completed": "change",
    "seasonal": "change",
    "story_born": "change",
}


# ── STORY CREATION FROM EVENTS ───────────────────────────────────────────────

def check_story_creation_from_events(db) -> Optional[str]:
    """
    Called every ~6 hours. Scans recent events for story-worthy patterns.
    Returns a description if a new story arc was created, else None.
    """
    init_narrative_tables(db)

    now = time.time()
    # Look at last 12 hours of events
    recent = now - (12 * 3600)

    events = db.execute("""
        SELECT * FROM events
        WHERE timestamp > ?
        ORDER BY timestamp DESC
        LIMIT 50
    """, (recent,)).fetchall()

    if len(events) < 2:
        return None

    # Find events that match story-worthy patterns
    story_candidates = []
    for event in events:
        event_type = event.get("event_type", "")
        desc = event.get("description", "") or ""
        location_id = event.get("location_id") or ""

        if event_type in STORY_TRIGGER_TYPES or any(k in event_type for k in STORY_TRIGGER_TYPES):
            story_candidates.append({
                "type": event_type,
                "description": desc,
                "location_id": location_id,
                "timestamp": event.get("timestamp", 0),
            })

    if not story_candidates:
        return None

    # Get the primary trigger
    primary = story_candidates[0]
    story_type = STORY_TYPE_FROM_TRIGGER.get(primary["type"], "change")

    # Find participants — extract NPC names from descriptions
    participants = _extract_npc_names(db, primary["description"])
    if len(participants) < 2:
        # Fall back to any NPCs mentioned across recent events
        participants = _extract_all_npc_mentions(db, events[:10])
    if len(participants) < 2:
        return None  # Need at least 2 participants for a story

    # Limit participants
    participants = list(participants)[:4]

    # Create the arc
    arc_id = create_story_arc(db, story_type, participants, primary["description"])
    if arc_id is None:
        return None  # Max arcs reached

    return f"A new {story_type} story unfolds involving {', '.join(participants)}"


def _extract_npc_names(db, description: str) -> set:
    """Extract NPC names mentioned in a description."""
    names = set()
    rows = db.execute("SELECT name FROM agents WHERE type = 'npc'").fetchall()
    for row in rows:
        name = row["name"]
        if name and name.lower() in description.lower():
            names.add(name)
    return names


def _extract_all_npc_mentions(db, events: list) -> set:
    """Extract all NPC names mentioned across a list of events."""
    names = set()
    rows = db.execute("SELECT name FROM agents WHERE type = 'npc'").fetchall()
    for row in rows:
        name = row["name"]
        if not name:
            continue
        for event in events:
            desc = (event.get("description") or "").lower()
            if name.lower() in desc:
                names.add(name)
                break
    return names


# ── NPC-INITIATED STORYTELLING ───────────────────────────────────────────────

def get_npc_story_prompts(db, npc_id: str, location_id: str, time_info: dict) -> list:
    """
    Returns story prompts the NPC might mention to the player.
    Called when NPC has relevant active stories and is in conversation range.
    """
    season = time_info.get("season", "spring")
    active_arcs = db.execute("""
        SELECT * FROM story_arcs
        WHERE active = 1
        ORDER BY updated_at DESC
        LIMIT 5
    """).fetchall()

    prompts = []
    for arc in active_arcs:
        participants = json.loads(arc["participants"]) if arc["participants"] else []
        phase = arc["phase"]
        story_type = arc["story_type"]

        # Check if NPC is a participant or if story is at this location
        if npc_id not in participants and arc.get("location_id") != location_id:
            # Story is elsewhere — NPC might reference it as news
            if random.random() < 0.3:  # 30% chance per arc
                prompts.append(_build_distant_story_prompt(arc, phase, story_type, season))
        else:
            # NPC is involved — they might push the story
            if random.random() < 0.5:  # 50% chance
                prompts.append(_build_involved_story_prompt(arc, phase, story_type, participants, npc_id))

    return prompts[:2]  # Max 2 story prompts per conversation turn


def _build_distant_story_prompt(arc: dict, phase: str, story_type: str, season: str) -> dict:
    """NPC references a story they heard about."""
    participants = arc.get("participants", "[]")
    if isinstance(participants, str):
        participants = json.loads(participants) if participants else []
    first_names = [p.split()[0] if ' ' in p else p for p in participants[:2]]
    people = " and ".join(first_names) if first_names else "someone"

    phase_texts = {
        "beginning": f"Have you heard? {people} — something's started between them.",
        "middle": f"Things between {people} have gotten complicated.",
        "end": f"The whole valley's talking about what happened between {people}.",
    }
    return {
        "type": "story_mention",
        "story_type": story_type,
        "text": phase_texts.get(phase, f"There's a story unfolding about {people}."),
    }


def _build_involved_story_prompt(arc: dict, phase: str, story_type: str, participants: list, npc_id: str) -> dict:
    """NPC directly involves the player in an ongoing story."""
    npc_name = next((p for p in participants if p != npc_id), participants[0] if participants else "someone")

    prompts_by_type = {
        "conflict": {
            "beginning": f"I've been worried about {npc_name}. Something's brewing.",
            "middle": f"You should talk to {npc_name}. Things aren't good between us.",
            "end": f"I don't know if {npc_name} will ever forgive what happened.",
        },
        "romance": {
            "beginning": f"I've noticed {npc_name} around more lately. Together.",
            "middle": f"They're not hiding it anymore. The whole clearing knows.",
            "end": f"Wedding plans? No, not yet. But it's coming.",
        },
        "mystery": {
            "beginning": f"Have you noticed anything strange around here?",
            "middle": f"I've been asking questions. Some answers, more questions.",
            "end": f"I think I know what happened. But should I tell anyone?",
        },
        "change": {
            "beginning": f"The valley is shifting. Can you feel it?",
            "middle": f"Things won't be the same after this. For any of us.",
            "end": f"It's done. What we built is finished. What's next?",
        },
    }

    texts = prompts_by_type.get(story_type, prompts_by_type["change"])
    return {
        "type": "story_involvement",
        "story_type": story_type,
        "text": texts.get(phase, "There's something I should tell you."),
    }


# ── SEASONAL BEAT PROCESSING ──────────────────────────────────────────────────

def process_seasonal_beat(db, season: str) -> Optional[dict]:
    """
    Called at season transition and periodically during a season.
    Rolls for a seasonal beat and returns it if triggered.
    """
    beat_data = SEASONAL_BEATS.get(season, SEASONAL_BEATS["spring"])
    beats = beat_data["beats"]

    for beat in beats:
        roll = random.random()
        if roll < beat["chance"]:
            # Beat triggered
            event = {
                "name": beat["name"],
                "description": beat["description"],
                "season": season,
                "theme": beat_data["theme"],
                "weight": beat["weight"],
            }
            # Log it
            log_event(db, "seasonal_beat", beat["description"], location_id="")
            return event

    return None


def get_seasonal_narrative_tone(season: str, active_arcs_count: int) -> str:
    """
    Returns the narrative tone overlay for the current season.
    Used to modulate NPC dialogue, event descriptions, and story pacing.
    """
    if active_arcs_count >= 3:
        tension = "The valley is thick with stories. Everyone feels it."
    elif active_arcs_count >= 1:
        tension = "Something is unfolding. The air feels expectant."
    else:
        tension = {
            "spring": "The valley stirs with new life. Possibility is in the air.",
            "summer": "Warm days and long light. The community feels whole.",
            "autumn": "The year is winding down. Reflections settle like fallen leaves.",
            "winter": "The valley is quiet. Stories breathe in the silence.",
        }.get(season, "The valley goes on.")

    return tension


# ── ARC ENGAGEMENT (player interacts with a story) ────────────────────────────

def engage_story(db, story_arc_id: int, player_action: str, player_location: str) -> Optional[dict]:
    """
    Called when the player does something that might engage an active story arc.
    Player presence accelerates arc progress; player actions become narrative material.
    """
    arc = db.execute("SELECT * FROM story_arcs WHERE id = ?", (story_arc_id,)).fetchone()
    if not arc or not arc["active"]:
        return None

    events = json.loads(arc["events"]) if arc["events"] else []
    participants = json.loads(arc["participants"]) if arc["participants"] else []
    phase = arc["phase"]

    # Add player action as an arc event
    player_tag = f"[{player_location}] "
    if player_action.startswith(player_tag):
        pass  # Already tagged
    else:
        player_action = player_tag + player_action

    events.append(player_action)

    # Update arc
    now = time.time()
    phase_changed = False
    new_phase = phase

    if len(events) >= 4 and phase == "beginning":
        new_phase = "middle"
        phase_changed = True
    elif len(events) >= 7 and phase == "middle":
        new_phase = "end"
        phase_changed = True

    db.execute("""
        UPDATE story_arcs
        SET events = ?, phase = ?, updated_at = ?
        WHERE id = ?
    """, (json.dumps(events), new_phase, now, story_arc_id))
    db.commit()

    if phase_changed:
        story = StoryArc(arc["story_type"], participants, arc["trigger_event"])
        story.phase = new_phase
        story.events = events
        narrative = story.generate_narrative()
        return {
            "phase_changed": True,
            "new_phase": new_phase,
            "narrative": narrative,
            "story_type": arc["story_type"],
        }

    return {
        "phase_changed": False,
        "events_count": len(events),
        "story_type": arc["story_type"],
    }


# ── ARC STATUS FOR UI ────────────────────────────────────────────────────────

def get_arc_status_summary(db) -> list:
    """Returns a compact status list of all active arcs for the dashboard."""
    arcs = db.execute("SELECT * FROM story_arcs WHERE active = 1 ORDER BY updated_at DESC").fetchall()

    summaries = []
    for arc in arcs:
        participants = json.loads(arc["participants"]) if arc["participants"] else []
        events = json.loads(arc["events"]) if arc["events"] else []
        story_type = arc["story_type"]
        phase = arc["phase"]

        # Progress bar
        if phase == "beginning":
            progress = min(len(events) / 3, 1.0)
        elif phase == "middle":
            progress = 0.5 + min((len(events) - 3) / 6, 0.5)
        else:
            progress = 1.0

        summaries.append({
            "id": arc["id"],
            "type": story_type,
            "phase": phase,
            "participants": participants,
            "events": len(events),
            "progress": round(progress * 100),
            "trigger": arc["trigger_event"][:60] + "..." if len(arc["trigger_event"] or "") > 60 else arc["trigger_event"] or "",
        })

    return summaries


# ── NARRATIVE MOMENT CREATION ────────────────────────────────────────────────

def create_narrative_moment(db, story_arc_id: int, content: str, location_id: str = None) -> int:
    """
    Create a discoverable narrative moment tied to a story arc.
    The player discovers these by being present in the right location at the right time.
    """
    now = time.time()
    row = db.execute("""
        INSERT INTO narrative_moments (timestamp, story_arc_id, content, location_id, discovered)
        VALUES (?, ?, ?, ?, 0)
    """, (now, story_arc_id, content, location_id))
    db.commit()
    return row.lastrowid


def advance_arcs_for_season(db, season: str) -> list:
    """
    Called at season transitions. Applies seasonal modifiers to active arcs.
    Autumn/winter: arcs escalate (conflict intensifies, mysteries deepen)
    Spring/summer: arcs tend toward resolution
    Returns narrative moments generated by the transition.
    """
    arcs = db.execute("SELECT * FROM story_arcs WHERE active = 1").fetchall()
    moments = []
    modifier = SEASON_STORY_MODIFIER.get(season, 1.0)

    if modifier <= 1.0:
        return moments  # No escalation in spring/summer

    for arc in arcs:
        events = json.loads(arc["events"]) if arc["events"] else []
        phase = arc["phase"]
        story_type = arc["story_type"]

        # Add an escalation event
        if phase == "beginning":
            escalation_texts = {
                "conflict": "The tension grows. Everyone has chosen sides.",
                "mystery": "The questions deepen. The answers feel further away.",
                "romance": "What began quietly has become undeniable.",
                "change": "The shift is irreversible now. The valley will not be the same.",
                "celebration": "The joy spreads. It seems to grow with each passing day.",
                "hardship": "The burden grows heavier. Some wonder if they can bear it.",
            }
            text = escalation_texts.get(story_type, "The story deepens.")
            events.append(f"[{season} escalation] {text}")

        elif phase == "middle":
            escalation_texts = {
                "conflict": "The breaking point approaches. It cannot be avoided.",
                "mystery": "Someone knows the truth. The question is whether they'll speak.",
                "romance": "They've stopped pretending. Everyone can see.",
                "change": "The old ways are crumbling. There's no going back now.",
            }
            text = escalation_texts.get(story_type, "The story cannot be stopped.")
            events.append(f"[{season} escalation] {text}")

        # Update arc
        now = time.time()
        db.execute("""
            UPDATE story_arcs
            SET events = ?, updated_at = ?
            WHERE id = ?
        """, (json.dumps(events), now, arc["id"]))

        # Create a discoverable moment
        story = StoryArc(arc["story_type"], json.loads(arc["participants"]) if arc["participants"] else [], arc["trigger_event"])
        story.phase = phase
        story.events = events
        moment_content = f"[{season.upper()}] {story.generate_narrative()}"
        create_narrative_moment(db, arc["id"], moment_content, arc.get("location_id"))

    db.commit()
    return moments