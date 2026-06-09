"""
events.py — Emergent event generator.

Events arise from the interactions of systems, not from scripts.
The event generator reads the current world state and asks:
- What's unusual right now?
- What systems are interacting in interesting ways?
- What would a person in this world notice?

Event types:
- Weather events (storms, fog, cold snaps, clear spells)
- Social events (arguments, celebrations, arrivals, departures, romance, rivalry)
- Ecological events (mushroom blooms, harvests, animal sightings, disease)
- Economic events (traveling traders, shortages, windfalls)
- Personal events (NPC milestones, OWL discoveries)

Design principles:
- Events are generated from system state, not random
- Events cascade — one event can trigger others
- Events have consequences that persist
- Events are narrated, not just logged
"""

import json
import random
import time
from typing import Optional

from .world_state import get_db, log_event, DB_PATH


# ── EVENT TEMPLATES ──

WEATHER_EVENTS = {
    "storm_approaching": {
        "condition": lambda w: w.get("wind_speed", 0) > 10 and w.get("humidity", 0) > 0.7,
        "probability": 0.3,
        "title": "Storm Approaching",
        "description": "The wind picks up. Dark clouds gather over the ridgeline. A storm is coming.",
        "consequences": {"creek_flood": 0.3, "travel_halted": True},
    },
    "heavy_fog": {
        "condition": lambda w: w.get("condition") == "foggy" and w.get("humidity", 0) > 0.9,
        "probability": 0.2,
        "title": "Heavy Fog",
        "description": "The fog is so thick you can barely see the cedars past the deck. The world has shrunk to arm's reach.",
        "consequences": {"travel_slow": True, "mood_effect": "melancholy"},
    },
    "clear_spell": {
        "condition": lambda w: w.get("condition") == "clear" and w.get("temperature", 10) > 15,
        "probability": 0.15,
        "title": "Clear Spell",
        "description": "The sky is clear and the air is warm. A rare perfect day in the mountains. The ridgeline is sharp against the blue.",
        "consequences": {"mood_effect": "content", "foraging_bonus": 0.2},
    },
    "cold_snap": {
        "condition": lambda w: w.get("temperature", 10) < 0,
        "probability": 0.4,
        "title": "Cold Snap",
        "description": "The cold bites. The creek has frozen at the edges. Breath hangs in the air.",
        "consequences": {"crop_damage": 0.2, "mood_effect": "cold"},
    },
}

SOCIAL_EVENTS = {
    "argument": {
        "condition": lambda db: _check_tension(db),
        "probability": 0.15,
        "title": "Argument in the Clearing",
        "description_fn": lambda db: _generate_argument(db),
        "consequences": {"relationship_change": -0.1},
    },
    "celebration": {
        "condition": lambda db: _check_celebration(db),
        "probability": 0.1,
        "title": "Celebration",
        "description_fn": lambda db: _generate_celebration(db),
        "consequences": {"mood_effect": "content", "social_need": -0.2},
    },
    "newcomer": {
        "condition": lambda db: _check_newcomer(db),
        "probability": 0.05,
        "title": "Newcomer Arrives",
        "description": "A stranger arrives on the mountain road. They're looking for work, or perhaps just a quiet place.",
        "consequences": {"new_npc": True},
    },
    "departure": {
        "condition": lambda db: _check_departure(db),
        "probability": 0.05,
        "title": "Someone Leaves",
        "description_fn": lambda db: _generate_departure(db),
        "consequences": {"npc_leaves": True, "mood_effect": "melancholy"},
    },
    "romance": {
        "condition": lambda db: _check_romance(db),
        "probability": 0.08,
        "title": "Romance Blossoms",
        "description_fn": lambda db: _generate_romance(db),
        "consequences": {"relationship_change": 0.2, "mood_effect": "content"},
    },
    "rivalry": {
        "condition": lambda db: _check_rivalry(db),
        "probability": 0.1,
        "title": "Rivalry Intensifies",
        "description_fn": lambda db: _generate_rivalry(db),
        "consequences": {"relationship_change": -0.15},
    },
}

ECOLOGY_EVENTS = {
    "mushroom_bloom": {
        "condition": lambda db: _check_mushroom_bloom(db),
        "probability": 0.3,
        "title": "Mushroom Bloom",
        "description": "The chanterelles are up. The forest floor is gold. Wren will be out there for days.",
        "consequences": {"foraging_bonus": 0.5, "market_mushrooms": True},
    },
    "poor_harvest": {
        "condition": lambda db: _check_poor_harvest(db),
        "probability": 0.15,
        "title": "Poor Harvest",
        "description": "The garden beds are thin this year. The greenhouse took a frost. People worry.",
        "consequences": {"food_shortage": True, "mood_effect": "worried"},
    },
    "bountiful_harvest": {
        "condition": lambda db: _check_bountiful_harvest(db),
        "probability": 0.15,
        "title": "Bountiful Harvest",
        "description": "The garden is overflowing. Tomatoes, chard, lavender, herbs. There will be plenty.",
        "consequences": {"food_surplus": True, "mood_effect": "grateful"},
    },
    "animal_sighting": {
        "condition": lambda db: _check_animal_sighting(db),
        "probability": 0.1,
        "title": "Rare Animal Sighting",
        "description_fn": lambda db: _generate_animal_sighting(db),
        "consequences": {"mood_effect": "excited"},
    },
    "disease": {
        "condition": lambda db: _check_disease(db),
        "probability": 0.05,
        "title": "Sickness in the Valley",
        "description": "A sickness is going around. Several people are ill. The nurse is busy.",
        "consequences": {"npc_sick": True, "mood_effect": "worried"},
    },
}

ECONOMIC_EVENTS = {
    "traveling_trader": {
        "condition": lambda db: random.random() < 0.02,
        "probability": 0.5,
        "title": "Traveling Trader",
        "description": "A traveling trader arrives on the mountain road with goods from town. News from the valley.",
        "consequences": {"new_goods": True, "mood_effect": "excited"},
    },
    "shortage": {
        "condition": lambda db: _check_shortage(db),
        "probability": 0.2,
        "title": "Shortage",
        "description_fn": lambda db: _generate_shortage(db),
        "consequences": {"prices_up": True, "mood_effect": "worried"},
    },
    "windfall": {
        "condition": lambda db: _check_windfall(db),
        "probability": 0.1,
        "title": "Windfall",
        "description_fn": lambda db: _generate_windfall(db),
        "consequences": {"prices_down": True, "mood_effect": "content"},
    },
}


# ── CONDITION CHECKERS ──

def _check_tension(db):
    """Check if any NPC relationships are strained."""
    rows = db.execute(
        "SELECT COUNT(*) as cnt FROM npc_relationships WHERE affinity < 0.3 AND relationship NOT IN ('rival', 'enemy')"
    ).fetchone()
    return rows[0] > 0 if rows else False

def _check_celebration(db):
    """Check if conditions are right for a celebration."""
    time_row = db.execute("SELECT * FROM weather WHERE id = 1").fetchone()
    if time_row and time_row[1] == "clear" and time_row[2] > 12:
        world_time = db.execute("SELECT * FROM world_time WHERE id = 1").fetchone()
        if world_time and world_time[7] in ("summer", "autumn"):
            return True
    return False

def _check_newcomer(db):
    """Check if a newcomer should arrive."""
    npc_count = db.execute("SELECT COUNT(*) as cnt FROM agents WHERE type = 'npc'").fetchone()[0]
    return npc_count < 250 and random.random() < 0.3

def _check_departure(db):
    """Check if someone should leave."""
    npc_count = db.execute("SELECT COUNT(*) as cnt FROM agents WHERE type = 'npc'").fetchone()[0]
    return npc_count > 50 and random.random() < 0.2

def _check_romance(db):
    """Check if any NPCs should fall for each other."""
    rows = db.execute(
        "SELECT COUNT(*) as cnt FROM npc_relationships WHERE affinity > 0.6 AND relationship = 'acquaintance'"
    ).fetchone()
    return rows[0] > 0 if rows else False

def _check_rivalry(db):
    """Check if any rivalries should intensify."""
    rows = db.execute(
        "SELECT COUNT(*) as cnt FROM npc_relationships WHERE relationship = 'rival' AND affinity < 0.4"
    ).fetchone()
    return rows[0] > 0 if rows else False

def _check_mushroom_bloom(db):
    """Check if mushrooms are blooming."""
    plants = db.execute("SELECT * FROM plants WHERE plant_type IN ('chanterelle','morel','bolete') AND health > 0.6").fetchall()
    return len(plants) > 0

def _check_poor_harvest(db):
    """Check if crops are failing."""
    plants = db.execute("SELECT * FROM plants WHERE plant_type IN ('tomato','chard','herb','root_vegetable') AND health < 0.4").fetchall()
    return len(plants) > 2

def _check_bountiful_harvest(db):
    """Check if crops are thriving."""
    plants = db.execute("SELECT * FROM plants WHERE plant_type IN ('tomato','chard','herb','root_vegetable') AND health > 0.8 AND stage = 'mature'").fetchall()
    return len(plants) > 2

def _check_animal_sighting(db):
    """Check for rare animal sightings."""
    animals = db.execute("SELECT * FROM animals WHERE animal_type IN ('black_bear','elk','red_fox','osprey','mountain_goat') AND count > 0").fetchall()
    return len(animals) > 0 and random.random() < 0.3

def _check_disease(db):
    """Check if disease should spread."""
    animals = db.execute("SELECT * FROM animals WHERE health < 0.5 AND count > 5").fetchall()
    return len(animals) > 0

def _check_shortage(db):
    """Check if there's a food shortage."""
    fish = db.execute("SELECT AVG(abundance) as avg FROM fish_stock").fetchone()
    return fish and fish[0] < 0.3 if fish else False

def _check_windfall(db):
    """Check for economic windfall."""
    fish = db.execute("SELECT AVG(abundance) as avg FROM fish_stock").fetchone()
    return fish and fish[0] > 0.7 if fish else False


# ── EVENT GENERATORS ──

def _generate_argument(db):
    """Generate an argument between NPCs."""
    row = db.execute("""
        SELECT r.npc_a, r.npc_b, a1.name as name_a, a2.name as name_b
        FROM npc_relationships r
        JOIN agents a1 ON r.npc_a = a1.id
        JOIN agents a2 ON r.npc_b = a2.id
        WHERE r.affinity < 0.4
        ORDER BY r.affinity ASC
        LIMIT 1
    """).fetchone()
    if row:
        topics = ["money", "a boundary dispute", "a misunderstanding", "old gossip", "a broken promise", "trail access", "noise"]
        topic = random.choice(topics)
        return f"{row[2]} and {row[3]} had a heated argument about {topic}. Everyone in the clearing heard it."
    return "Tensions flare in the clearing. Voices raised, then silence."

def _generate_celebration(db):
    """Generate a celebration event."""
    celebrations = [
        "The whole community gathers in the clearing for a spontaneous celebration. Someone brought out a guitar.",
        "A wedding! The cabin is full of people. The whole valley celebrates.",
        "The harvest feast. Long tables in the clearing, food and drink for everyone.",
        "A birthday. The cabin is full of laughter and song.",
        "The fishermen return with an extraordinary catch from the creek. Everyone celebrates.",
        "A clear night on the ridgeline. Someone brought a telescope. The stars are extraordinary.",
    ]
    return random.choice(celebrations)

def _generate_departure(db):
    """Generate a departure event."""
    row = db.execute("""
        SELECT a.name, a.properties FROM agents a
        WHERE a.type = 'npc' AND a.state = 'active'
        ORDER BY RANDOM() LIMIT 1
    """).fetchone()
    if row:
        reasons = ["to seek work in the city", "to join family elsewhere", "for reasons unknown", "after a disagreement", "to start a new life", "to attend a training"]
        reason = random.choice(reasons)
        return f"{row[0]} has left the valley, {reason}. Their absence is felt."
    return "Someone has left the valley. Their cabin stands empty."

def _generate_romance(db):
    """Generate a romance event."""
    row = db.execute("""
        SELECT r.npc_a, r.npc_b, a1.name as name_a, a2.name as name_b
        FROM npc_relationships r
        JOIN agents a1 ON r.npc_a = a1.id
        JOIN agents a2 ON r.npc_b = a2.id
        WHERE r.affinity > 0.6 AND r.relationship = 'acquaintance'
        ORDER BY r.affinity DESC
        LIMIT 1
    """).fetchone()
    if row:
        signs = ["They were seen walking the cedar trail together.", "They can't stop talking to each other in the clearing.", "Someone saw them exchanging glances across the garden.", "They find excuses to be in the same place.", "They were spotted sharing a bottle of wine on the deck at dusk."]
        return f"Something is growing between {row[2]} and {row[3]}. {random.choice(signs)}"
    return "A new romance is whispered about in the valley."

def _generate_rivalry(db):
    """Generate a rivalry event."""
    row = db.execute("""
        SELECT r.npc_a, r.npc_b, a1.name as name_a, a2.name as name_b
        FROM npc_relationships r
        JOIN agents a1 ON r.npc_a = a1.id
        JOIN agents a2 ON r.npc_b = a2.id
        WHERE r.relationship = 'rival'
        ORDER BY r.affinity ASC
        LIMIT 1
    """).fetchone()
    if row:
        escalations = ["The rivalry has turned bitter. Insults were exchanged.", "Their competition is affecting the whole community.", "It's gotten personal now. Friends are being forced to choose sides.", "A public confrontation in the clearing. It was ugly."]
        return f"The rivalry between {row[2]} and {row[3]} intensifies. {random.choice(escalations)}"
    return "Old rivalries resurface. The valley feels tense."

def _generate_animal_sighting(db):
    """Generate an animal sighting."""
    row = db.execute("SELECT * FROM animals WHERE animal_type IN ('black_bear','elk','red_fox','osprey','mountain_goat') AND count > 0 ORDER BY RANDOM() LIMIT 1").fetchone()
    if row:
        sightings = {
            "black_bear": "A black bear has been spotted near the garden. Bold as brass, checking the compost.",
            "elk": "A herd of elk is moving through the valley. Thirty, maybe more. Magnificent.",
            "red_fox": "A red fox has been seen near the cabin again. Bold as brass.",
            "osprey": "An osprey circles overhead, hunting the creek. Its cry is sharp and wild.",
            "mountain_goat": "Mountain goats on the ridgeline. White against the rock, impossibly sure-footed.",
        }
        return sightings.get(row[1], f"A {row[1]} has been spotted.")
    return "An unusual animal has been seen in the valley."

def _generate_shortage(db):
    """Generate a shortage event."""
    shortages = [
        "Fish are scarce. The creek is running low. The fishermen worry.",
        "The store shelves are thin. Supplies from town haven't arrived.",
        "Firewood is running low. The woodcutters work double time to keep up.",
        "The well is lower than usual. Water must be rationed.",
        "The mushroom season was poor this season. Everyone feels it.",
    ]
    return random.choice(shortages)

def _generate_windfall(db):
    """Generate a windfall event."""
    windfalls = [
        "An extraordinary catch! The creek is full of trout. Fish for everyone.",
        "A trader paid handsomely for the valley's honey and herbs. Money flows.",
        "The garden harvest is the best in years. Preserves for everyone.",
        "A traveler left a generous donation at the cabin. The community prospers.",
        "The chanterelle bloom came early and strong. The whole valley celebrates.",
    ]
    return random.choice(windfalls)


# ── MAIN EVENT GENERATION ──

def generate_events(db) -> list:
    """
    Generate emergent events based on current world state.
    Returns a list of generated events.
    """
    events = []
    now = time.time()

    weather = db.execute("SELECT * FROM weather WHERE id = 1").fetchone()
    world_time = db.execute("SELECT * FROM world_time WHERE id = 1").fetchone()

    # Check all event categories
    all_event_categories = [
        ("weather", WEATHER_EVENTS),
        ("social", SOCIAL_EVENTS),
        ("ecology", ECOLOGY_EVENTS),
        ("economic", ECONOMIC_EVENTS),
    ]

    for category, event_dict in all_event_categories:
        for event_key, event_template in event_dict.items():
            try:
                condition = event_template["condition"]
                is_pure_chance = (event_key == "traveling_trader")
                if is_pure_chance:
                    should_trigger = True
                elif category == "weather":
                    should_trigger = condition(weather) if weather else False
                else:
                    should_trigger = condition(db)

                if should_trigger:
                    prob = event_template.get("probability", 0.1)
                    if random.random() < prob:
                        desc_fn = event_template.get("description_fn")
                        if desc_fn:
                            description = desc_fn(db)
                        else:
                            description = event_template["description"]

                        event = {
                            "type": f"{category}_{event_key}",
                            "title": event_template["title"],
                            "description": description,
                            "consequences": event_template.get("consequences", {}),
                            "category": category,
                        }
                        events.append(event)

                        db.execute("""
                            INSERT INTO events (timestamp, agent_id, event_type, description, location_id, properties)
                            VALUES (NULL, 'event', ?, ?, NULL, ?)
                        """, (event["type"], description, json.dumps(event["consequences"])))

                        _apply_consequences(db, event["consequences"])

            except Exception:
                continue

    db.commit()
    return events


def _apply_consequences(db, consequences: dict):
    """Apply event consequences to the world state."""
    if not consequences:
        return

    if consequences.get("creek_flood"):
        creek_objs = db.execute("SELECT * FROM objects WHERE location_id = 'mountain_creek'").fetchall()
        for obj in creek_objs:
            db.execute("UPDATE objects SET state = 'flooded' WHERE id = ?", (obj[0],))

    if consequences.get("crop_damage"):
        db.execute("UPDATE plants SET health = MAX(0.1, health - 0.2) WHERE plant_type IN ('tomato','chard','herb','root_vegetable')")

    if consequences.get("foraging_bonus"):
        db.execute("UPDATE fish_stock SET abundance = LEAST(1.0, abundance + 0.1)")

    if consequences.get("relationship_change"):
        change = consequences["relationship_change"]
        db.execute("UPDATE npc_relationships SET affinity = MAX(0.0, MIN(1.0, affinity + ?))", (change,))

    if consequences.get("mood_effect"):
        pass  # Handled by psychology system

    if consequences.get("new_npc"):
        from .npc_generation import generate_npc
        used_names = set(r[0].split()[0] for r in db.execute("SELECT name FROM agents WHERE type = 'npc'").fetchall())
        used_combos = set(r[0] for r in db.execute("SELECT name FROM agents WHERE type = 'npc'").fetchall())
        npc_count = db.execute("SELECT COUNT(*) as cnt FROM agents WHERE type = 'npc'").fetchone()[0]
        new_npc = generate_npc(npc_count + 1, used_names, used_combos)
        db.execute("""
            INSERT OR IGNORE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
            VALUES (?, ?, 'npc', ?, 'active', ?, ?, ?)
        """, (new_npc["id"], new_npc["name"], new_npc["work_locations"][0],
              json.dumps(new_npc["properties"]), time.time(), time.time()))

    db.commit()


def get_recent_events(db, limit: int = 10) -> list:
    """Get recent events."""
    rows = db.execute(
        "SELECT * FROM events WHERE agent_id = 'event' ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    ).fetchall()
    return [dict(r) for r in rows]