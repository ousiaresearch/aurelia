"""
seasons.py — Full year cycle with seasonal effects on everything.

The village lives through spring, summer, autumn, and winter. Each season
brings changes to weather, ecology, NPC behavior, and the feel of the world.

Design principles:
- Seasons are ~90 days each (30 days/month × 3 months)
- Weather patterns shift with seasons
- NPCs change routines seasonally
- The world looks and feels different
- Seasonal events mark the year
"""

import json
import random
import time
from typing import Optional

from .world_state import get_db, log_event, DB_PATH


# ── SEASON DATA ──

SEASON_DATA = {
    "spring": {
        "months": [3, 4, 5],
        "base_temp": 9,
        "temp_range": (-1, 7),
        "weather_weights": {"clear": 0.18, "cloudy": 0.32, "foggy": 0.22, "rain": 0.24, "storm": 0.04},
        "daylight_hours": (6, 19),
        "description": "Spring comes wet and green. Sword ferns lift out of the duff, the creek runs cold, and fog holds low between the cedars.",
        "mood": "hopeful",
        "activities": ["planting", "walking", "gardening", "repairing", "mushroom_hunting"],
        "events": [
            "The first trilliums appear beside the cedar trail.",
            "The creek runs high with snowmelt and rain.",
            "Steller's jays argue from the deck rail.",
            "New fern fronds uncurl in the understory.",
            "Fog fills the valley before burning off near noon.",
        ],
    },
    "summer": {
        "months": [6, 7, 8],
        "base_temp": 19,
        "temp_range": (3, 11),
        "weather_weights": {"clear": 0.42, "cloudy": 0.24, "foggy": 0.12, "rain": 0.16, "storm": 0.06},
        "daylight_hours": (5, 21),
        "description": "Summer opens the deck and warms the ridge. The cedars hold shade; the garden drinks deeply when rain comes.",
        "mood": "alive",
        "activities": ["gardening", "painting", "sitting_outside", "stargazing", "walking"],
        "events": [
            "The longest day. Light stays in the treetops late.",
            "Blueberries ripen in the garden.",
            "Dust rises from Highway 58 on the dry afternoons.",
            "A raven works the thermals above the ridge.",
            "Night insects start up after the heat leaves the deck boards.",
        ],
    },
    "autumn": {
        "months": [9, 10, 11],
        "base_temp": 11,
        "temp_range": (0, 8),
        "weather_weights": {"clear": 0.18, "cloudy": 0.28, "foggy": 0.22, "rain": 0.24, "storm": 0.08},
        "daylight_hours": (7, 17),
        "description": "Autumn settles in rain and gold. Chanterelles come up under the cedars, vine maples redden, and woodsmoke starts to matter.",
        "mood": "reflective",
        "activities": ["harvesting", "preserving", "woodcutting", "mending", "gathering"],
        "events": [
            "Chanterelles appear in the damp cedar duff.",
            "Vine maples turn red along the clearing.",
            "The first hard rain drums on the cabin roof all night.",
            "Firewood gets stacked under cover.",
            "The creek darkens and quickens with the season.",
        ],
    },
    "winter": {
        "months": [12, 1, 2],
        "base_temp": 4,
        "temp_range": (-4, 5),
        "weather_weights": {"clear": 0.12, "cloudy": 0.28, "foggy": 0.18, "rain": 0.28, "storm": 0.14},
        "daylight_hours": (8, 16),
        "description": "Winter is low cloud, cold rain, and early dark. The cabin contracts around the stove; the cedars stand black and wet outside.",
        "mood": "quiet",
        "activities": ["mending", "storytelling", "indoor_work", "visiting", "resting"],
        "events": [
            "The shortest day. Darkness comes early under the trees.",
            "A windstorm drops cedar limbs across the trail.",
            "Ice rims the shallow parts of the creek before sunrise.",
            "The stove becomes the center of the room.",
            "Francis is clear from the deck on the cold nights.",
        ],
    },
}


def get_season_data(season: str) -> dict:
    """Get the data for a season."""
    return SEASON_DATA.get(season, SEASON_DATA["spring"])


def get_season_weather(season: str) -> str:
    """Get a weighted random weather condition for the season."""
    data = get_season_data(season)
    weights = data["weather_weights"]
    roll = random.random()
    cumulative = 0
    for weather, weight in weights.items():
        cumulative += weight
        if roll <= cumulative:
            return weather
    return "cloudy"


def get_season_temperature(season: str, hour: int) -> float:
    """Get a temperature for the season and time of day."""
    data = get_season_data(season)
    base = data["base_temp"]
    temp_mod = {
        0: -5, 1: -5, 2: -6, 3: -6, 4: -5, 5: -4, 6: -3, 7: -2,
        8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 4, 14: 3, 15: 2,
        16: 1, 17: 0, 18: -1, 19: -2, 20: -3, 21: -3, 22: -4, 23: -4,
    }.get(hour, 0)
    return base + temp_mod + random.uniform(-1.5, 1.5)


def describe_season_change(old_season: str, new_season: str) -> str:
    """Generate a description of the season changing."""
    if old_season == new_season:
        return ""

    transitions = {
        ("winter", "spring"): "The first thaw. Ice melts. The creek runs fast. Somewhere, a bird sings that hasn't sung in months.",
        ("spring", "summer"): "The days grow long. The warmth deepens. The village is green and gold and alive.",
        ("summer", "autumn"): "The light changes. Golden, then amber. The first leaves fall. The air has a bite.",
        ("autumn", "winter"): "The first frost. The garden dies back. The sea turns dark. The fires burn longer.",
    }

    return transitions.get((old_season, new_season), f"The season turns to {new_season}.")


def get_seasonal_npc_activity(npc_occupation: str, season: str) -> str:
    """Get a seasonal activity description for an NPC based on their occupation."""
    activities = {
        "fisherman": {
            "spring": "Preparing the boats and nets for the season ahead.",
            "summer": "Long days on the water. The fishing is good.",
            "autumn": "The herring run. The busiest time.",
            "winter": "Mending nets. Repairing boats. Waiting for spring.",
        },
        "farmer": {
            "spring": "Planting. The fields are turned and sown.",
            "summer": "Tending. Watering. Watching the crops grow.",
            "autumn": "Harvest. The busiest, most important time.",
            "winter": "Planning. Repairing tools. Resting the land.",
        },
        "shepherd": {
            "spring": "Lambing season. Long nights watching the flock.",
            "summer": "Moving the sheep to the upper pasture.",
            "autumn": "Bringing the flock down. Shearing the last of the season's fleece.",
            "winter": "Feeding hay. Keeping the sheep warm.",
        },
        "woodcutter": {
            "spring": "The forest is wet. Splitting last year's wood.",
            "summer": "Cutting and stacking. The wood needs to dry.",
            "autumn": "The main cutting season. Winter is coming.",
            "winter": "Delivering firewood. Every chimney in the village needs feeding.",
        },
        "default": {
            "spring": "Spring brings new energy.",
            "summer": "The warm days are a gift.",
            "autumn": "Time to prepare for the cold.",
            "winter": "Winter is for rest and reflection.",
        },
    }

    occ_activities = activities.get(npc_occupation, activities["default"])
    return occ_activities.get(season, "Going about their work.")


def generate_seasonal_event(db, season: str) -> Optional[str]:
    """Generate a seasonal event. Returns description or None."""
    data = get_season_data(season)
    events = data.get("events", [])

    if events and random.random() < 0.1:  # 10% chance per check
        event = random.choice(events)
        now = time.time()
        db.execute("""
            INSERT INTO events (timestamp, agent_id, event_type, description, location_id, properties)
            VALUES (?, NULL, 'seasonal', ?, NULL, ?)
        """, (now, event, json.dumps({"season": season})))
        db.commit()
        return event

    return None
