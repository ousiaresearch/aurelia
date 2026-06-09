"""
ecology.py — Living ecology system for the village.

Plants grow, animals move, fish run in seasons, things decay and grow.
The ecology runs on simulation ticks and creates emergent environmental
storytelling: a garden gone to seed, a new bird's nest, a dead tree
falling across a trail.

Design principles:
- Everything has a lifecycle: seed → growth → maturity → decay → death
- Seasons drive the ecology
- Player actions affect the ecology (tending gardens, cutting trees)
- Environmental clues tell stories without words
"""

import json
import random
import time
from typing import Optional

from .world_state import get_db, log_event, DB_PATH


# ── PLANT TYPES ──

PLANT_TYPES = {
    # Cabin garden herbs and food plants
    "rosemary": {"type": "herb", "growth_rate": 0.02, "max_age": 365, "season": "spring", "harvestable": True, "smell": "resinous, warm"},
    "thyme": {"type": "herb", "growth_rate": 0.025, "max_age": 300, "season": "spring", "harvestable": True, "smell": "earthy, sharp"},
    "lavender": {"type": "herb", "growth_rate": 0.018, "max_age": 500, "season": "summer", "harvestable": True, "smell": "dry purple sweetness"},
    "chard": {"type": "crop", "growth_rate": 0.03, "max_age": 120, "season": "spring", "harvestable": True},
    "kale": {"type": "crop", "growth_rate": 0.025, "max_age": 150, "season": "autumn", "harvestable": True},
    "snap_peas": {"type": "crop", "growth_rate": 0.035, "max_age": 100, "season": "spring", "harvestable": True},
    "blueberries": {"type": "shrub", "growth_rate": 0.008, "max_age": 1500, "season": "summer", "harvestable": True},

    # PNW forest plants
    "sword_fern": {"type": "fern", "growth_rate": 0.012, "max_age": 900, "season": "all", "harvestable": False},
    "deer_fern": {"type": "fern", "growth_rate": 0.011, "max_age": 800, "season": "all", "harvestable": False},
    "douglas_iris": {"type": "flower", "growth_rate": 0.018, "max_age": 400, "season": "spring", "harvestable": False, "color": "violet"},
    "horsetail": {"type": "reed", "growth_rate": 0.022, "max_age": 500, "season": "spring", "harvestable": False},
    "salal": {"type": "shrub", "growth_rate": 0.01, "max_age": 1200, "season": "all", "harvestable": True},
    "oregon_grape": {"type": "shrub", "growth_rate": 0.01, "max_age": 900, "season": "spring", "harvestable": True},
    "red_huckleberry": {"type": "shrub", "growth_rate": 0.009, "max_age": 1200, "season": "summer", "harvestable": True},
    "chanterelles": {"type": "fungus", "growth_rate": 0.02, "max_age": 90, "season": "autumn", "harvestable": True, "smell": "apricot and wet duff"},
    "western_redcedar": {"type": "tree", "growth_rate": 0.002, "max_age": 5000, "season": "all", "harvestable": False},
    "douglas_fir": {"type": "tree", "growth_rate": 0.003, "max_age": 4000, "season": "all", "harvestable": False},
    "vine_maple": {"type": "tree", "growth_rate": 0.004, "max_age": 1200, "season": "autumn", "harvestable": False},
    "bigleaf_maple": {"type": "tree", "growth_rate": 0.004, "max_age": 1800, "season": "all", "harvestable": False},
}

# ── ANIMAL TYPES ──

ANIMAL_TYPES = {
    "black_tailed_deer": {"habitat": "forest_edge", "count": (1, 6), "season": "all", "sound": "silence", "behavior": "browsing"},
    "roosevelt_elk": {"habitat": "clearing", "count": (0, 8), "season": "all", "sound": "low calls", "behavior": "grazing"},
    "black_bear": {"habitat": "cedar_deep", "count": (0, 2), "season": "spring", "sound": "brush breaking", "behavior": "foraging"},
    "coyote": {"habitat": "ridgeline", "count": (1, 4), "season": "all", "sound": "yipping", "behavior": "moving along the edge"},
    "raccoon": {"habitat": "mountain_creek", "count": (1, 5), "season": "all", "sound": "chittering", "behavior": "washing its paws"},
    "river_otter": {"habitat": "mountain_creek", "count": (0, 3), "season": "all", "sound": "chirping", "behavior": "slipping through water"},
    "steller_jay": {"habitat": "cabin_deck", "count": (2, 8), "season": "all", "sound": "scolding", "behavior": "arguing in the cedars"},
    "raven": {"habitat": "ridgeline", "count": (1, 5), "season": "all", "sound": "croaking", "behavior": "riding the wind"},
    "varied_thrush": {"habitat": "cedar_deep", "count": (1, 6), "season": "spring", "sound": "fluted song", "behavior": "singing from shadow"},
    "barred_owl": {"habitat": "cedar_deep", "count": (1, 2), "season": "all", "sound": "low calling", "behavior": "watching"},
    "tree_frog": {"habitat": "mountain_creek", "count": (20, 100), "season": "spring", "sound": "peeping", "behavior": "singing after rain"},
    "snowshoe_hare": {"habitat": "forest_edge", "count": (2, 10), "season": "winter", "sound": "silence", "behavior": "freezing under salal"},
}

# ── FISH TYPES ──

FISH_TYPES = {
    "cutthroat_trout": {"season": "spring", "abundance": (0.3, 0.7), "location": "mountain_creek", "value": "medium"},
    "rainbow_trout": {"season": "summer", "abundance": (0.25, 0.65), "location": "mountain_creek", "value": "medium"},
    "coho_salmon": {"season": "autumn", "abundance": (0.1, 0.5), "location": "river_bridge", "value": "high"},
    "steelhead": {"season": "winter", "abundance": (0.1, 0.4), "location": "river_bridge", "value": "high"},
}

def init_ecology(db) -> None:
    """Initialize the ecology tables and seed initial state."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_type TEXT NOT NULL,
            location_id TEXT NOT NULL,
            age_days REAL DEFAULT 0,
            health REAL DEFAULT 1.0,
            stage TEXT DEFAULT 'seedling',
            tended INTEGER DEFAULT 0,
            properties TEXT DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_type TEXT NOT NULL,
            location_id TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            health REAL DEFAULT 1.0,
            properties TEXT DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fish_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fish_type TEXT NOT NULL,
            location_id TEXT NOT NULL,
            abundance REAL DEFAULT 0.5,
            properties TEXT DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ecology_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT NOT NULL,
            location_id TEXT DEFAULT NULL,
            properties TEXT DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_plants_location ON plants(location_id);
        CREATE INDEX IF NOT EXISTS idx_animals_location ON animals(location_id);
        CREATE INDEX IF NOT EXISTS idx_fish_location ON fish_stock(location_id);
    """)

    now = time.time()

    # Seed plants in appropriate PNW locations
    plant_seeds = [
        # Cabin garden
        ("rosemary", "garden"), ("thyme", "garden"), ("lavender", "garden"),
        ("chard", "garden"), ("kale", "garden"), ("snap_peas", "garden"),
        ("blueberries", "garden"),
        # Forest and creek system
        ("sword_fern", "cedar_trail"), ("sword_fern", "cedar_deep"),
        ("deer_fern", "mountain_creek"), ("douglas_iris", "forest_edge"),
        ("horsetail", "mountain_creek"), ("salal", "cedar_deep"),
        ("oregon_grape", "forest_edge"), ("red_huckleberry", "clearing"),
        ("chanterelles", "cedar_deep"), ("chanterelles", "cedar_trail"),
        ("western_redcedar", "cedar_deep"), ("western_redcedar", "cedar_trail"),
        ("douglas_fir", "forest_edge"), ("vine_maple", "clearing"),
        ("bigleaf_maple", "mountain_creek"),
    ]

    for plant_type, location in plant_seeds:
        db.execute("""
            INSERT OR IGNORE INTO plants (plant_type, location_id, age_days, health, stage, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (plant_type, location, random.randint(10, 60), random.uniform(0.6, 1.0),
              random.choice(["growing", "mature"]), now, now))

    # Seed animals
    animal_seeds = [
        ("black_tailed_deer", "forest_edge", random.randint(1, 4)),
        ("roosevelt_elk", "clearing", random.randint(0, 5)),
        ("black_bear", "cedar_deep", random.randint(0, 1)),
        ("coyote", "ridgeline", random.randint(1, 3)),
        ("raccoon", "mountain_creek", random.randint(1, 4)),
        ("river_otter", "mountain_creek", random.randint(0, 2)),
        ("steller_jay", "cabin_deck", random.randint(2, 6)),
        ("raven", "ridgeline", random.randint(1, 4)),
        ("varied_thrush", "cedar_deep", random.randint(1, 4)),
        ("barred_owl", "cedar_deep", random.randint(1, 2)),
        ("tree_frog", "mountain_creek", random.randint(30, 80)),
        ("snowshoe_hare", "forest_edge", random.randint(2, 7)),
    ]

    for animal_type, location, count in animal_seeds:
        db.execute("""
            INSERT OR IGNORE INTO animals (animal_type, location_id, count, health, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (animal_type, location, count, random.uniform(0.7, 1.0), now, now))

    # Seed fish stocks
    for fish_type, data in FISH_TYPES.items():
        db.execute("""
            INSERT OR IGNORE INTO fish_stock (fish_type, location_id, abundance, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (fish_type, data["location"], random.uniform(*data["abundance"]), now, now))

    db.commit()


def get_plant_stage(age_days: float, growth_rate: float, max_age: float) -> str:
    """Determine plant stage based on age and growth."""
    progress = age_days / max_age
    if progress < 0.1:
        return "seedling"
    elif progress < 0.3:
        return "growing"
    elif progress < 0.7:
        return "mature"
    elif progress < 0.9:
        return "flowering"
    elif progress < 1.0:
        return "fruiting"
    else:
        return "dying"


def describe_plant(plant: dict) -> str:
    """Generate a literary description of a PNW plant."""
    ptype = plant["plant_type"]
    stage = plant["stage"]
    health = plant["health"]
    tended = plant.get("tended", 0)

    descriptions = {
        "seedling": {
            "rosemary": "A tiny rosemary seedling, just a few leaves above the soil.",
            "thyme": "A small thyme plant, barely established.",
            "lavender": "A small lavender start, silver-green and stubborn.",
            "chard": "Bright chard seedlings hold their color against the dark soil.",
            "snap_peas": "Pea shoots curl toward the trellis with small green intent.",
            "default": "A small seedling, just beginning.",
        },
        "growing": {
            "rosemary": "Rosemary growing well, its woody stems thickening.",
            "thyme": "Thyme spreading across the bed, healthy and strong.",
            "lavender": "Lavender grows in a soft gray clump, waiting for heat.",
            "chard": "Chard leaves are broad and glossy from the rain.",
            "kale": "Kale stands dark and sturdy in the damp air.",
            "sword_fern": "Sword ferns lift green ribs out of the duff.",
            "chanterelles": "Chanterelles press gold through the cedar duff.",
            "default": "Growing steadily, healthy and green.",
        },
        "mature": {
            "rosemary": "A mature rosemary bush, fragrant and full.",
            "thyme": "Thyme in full spread, a carpet of tiny leaves.",
            "lavender": "Lavender in full bloom, a haze of purple and scent.",
            "blueberries": "Blueberry canes hold small dusty fruit under wet leaves.",
            "sword_fern": "Sword ferns crowd the trail edge in glossy green fans.",
            "western_redcedar": "The cedar rises with wet bark and patient shadow.",
            "douglas_fir": "A Douglas fir stands above the understory, dark-needled and still.",
            "vine_maple": "Vine maple leans through the clearing in a crooked red-green lattice.",
            "default": "Fully grown and healthy.",
        },
        "flowering": {
            "rosemary": "Rosemary blooms with tiny blue flowers visited by bees.",
            "lavender": "Lavender flowers, and the air holds its dry purple sweetness.",
            "douglas_iris": "Douglas iris blooms violet at the forest edge.",
            "oregon_grape": "Oregon grape shows yellow flowers under glossy leaves.",
            "default": "In full flower, beautiful.",
        },
        "fruiting": {
            "blueberries": "Blueberries hang in small blue clusters, rain-dulled and ready.",
            "red_huckleberry": "Red huckleberries shine like beads in the understory.",
            "salal": "Salal berries darken beneath thick green leaves.",
            "chanterelles": "Chanterelles flare gold from the damp duff.",
            "default": "Bearing fruit.",
        },
        "dying": {
            "default": "Past its prime, beginning to brown and wither.",
        },
    }

    stage_descs = descriptions.get(stage, {})
    desc = stage_descs.get(ptype, stage_descs.get("default", f"A {ptype.replace('_', ' ')} in {stage} stage."))

    if health < 0.4:
        desc += " It looks unhealthy — perhaps it needs attention."
    elif tended:
        desc += " It's been well tended."

    return desc


def update_ecology(db, season: str, days_passed: float = 1.0) -> list:
    """
    Update the ecology for a simulation tick.
    Returns a list of notable events.
    """
    events = []
    now = time.time()

    # ── UPDATE PLANTS ──
    plants = db.execute("SELECT * FROM plants").fetchall()
    for plant in plants:
        ptype = plant["plant_type"]
        plant_info = PLANT_TYPES.get(ptype, {})
        growth_rate = plant_info.get("growth_rate", 0.01)
        max_age = plant_info.get("max_age", 365)

        # Season modifier
        season_mod = 1.0
        plant_season = plant_info.get("season", "spring")
        if season == plant_season:
            season_mod = 1.5
        elif season == "winter":
            season_mod = 0.2

        # Growth
        new_age = plant["age_days"] + days_passed * season_mod
        new_stage = get_plant_stage(new_age, growth_rate, max_age)

        # Health decay/growth
        health = plant["health"]
        if plant["tended"] > 0:
            health = min(1.0, health + 0.01 * days_passed)
        else:
            health = max(0.0, health - 0.002 * days_passed)

        # Water needs (simplified)
        if season == "summer":
            health = max(0.0, health - 0.005 * days_passed)

        db.execute("""
            UPDATE plants SET age_days = ?, stage = ?, health = ?, updated_at = ?
            WHERE id = ?
        """, (new_age, new_stage, round(health, 2), now, plant["id"]))

        # Check for notable changes
        if new_stage != plant["stage"]:
            if new_stage == "flowering":
                events.append({
                    "type": "plant_flowering",
                    "description": f"The {ptype} in {plant['location_id']} is flowering.",
                    "location_id": plant["location_id"],
                })
            elif new_stage == "dying":
                events.append({
                    "type": "plant_dying",
                    "description": f"The {ptype} in {plant['location_id']} is dying.",
                    "location_id": plant["location_id"],
                })

    # ── UPDATE ANIMALS ──
    animals = db.execute("SELECT * FROM animals").fetchall()
    for animal in animals:
        atype = animal["animal_type"]
        animal_info = ANIMAL_TYPES.get(atype, {})

        # Seasonal changes
        animal_season = animal_info.get("season", "all")
        count = animal["count"]

        if season == "spring" and animal_season in ("all", "spring"):
            # Breeding season
            count = int(count * random.uniform(1.0, 1.15))
        elif season == "winter":
            # Some animals leave or die
            if animal_season != "all":
                count = int(count * random.uniform(0.7, 0.95))

        # Random fluctuation
        count = max(0, count + random.randint(-1, 1))

        # Health
        health = animal["health"]
        if season == "winter":
            health = max(0.3, health - 0.01)
        else:
            health = min(1.0, health + 0.005)

        db.execute("""
            UPDATE animals SET count = ?, health = ?, updated_at = ?
            WHERE id = ?
        """, (count, round(health, 2), now, animal["id"]))

    # ── UPDATE FISH ──
    fish_stocks = db.execute("SELECT * FROM fish_stock").fetchall()
    for fish in fish_stocks:
        ftype = fish["fish_type"]
        fish_info = FISH_TYPES.get(ftype, {})

        abundance = fish["abundance"]
        fish_season = fish_info.get("season", "all")

        if season == fish_season:
            abundance = min(1.0, abundance + random.uniform(0.01, 0.05))
        else:
            abundance = max(0.05, abundance - random.uniform(0.01, 0.03))

        # Random fluctuation
        abundance = max(0.05, min(1.0, abundance + random.uniform(-0.02, 0.02)))

        db.execute("""
            UPDATE fish_stock SET abundance = ?, updated_at = ?
            WHERE id = ?
        """, (round(abundance, 2), now, fish["id"]))

        # Notable fish runs
        if abundance > 0.8 and fish["abundance"] <= 0.8:
            events.append({
                "type": "fish_run",
                "description": f"The {ftype} are running! Good fishing.",
                "location_id": fish["location_id"],
            })

    # Log events
    for event in events:
        db.execute("""
            INSERT INTO ecology_events (timestamp, event_type, description, location_id, properties)
            VALUES (?, ?, ?, ?, ?)
        """, (now, event["type"], event["description"], event["location_id"], "{}"))

    db.commit()
    return events


def get_location_ecology(db, location_id: str) -> dict:
    """Get the ecology state for a location."""
    plants = db.execute("SELECT * FROM plants WHERE location_id = ?", (location_id,)).fetchall()
    animals = db.execute("SELECT * FROM animals WHERE location_id = ?", (location_id,)).fetchall()
    fish = db.execute("SELECT * FROM fish_stock WHERE location_id = ?", (location_id,)).fetchall()

    return {
        "plants": [dict(p) for p in plants],
        "animals": [dict(a) for a in animals],
        "fish": [dict(f) for f in fish],
    }


def describe_location_ecology(db, location_id: str) -> list:
    """Generate literary descriptions of ecology in a location.
    Returns a list of description strings."""
    eco = get_location_ecology(db, location_id)
    parts = []

    # Plants
    for plant in eco["plants"]:
        if plant["stage"] in ("flowering", "fruiting", "mature"):
            parts.append(describe_plant(plant))

    # Animals
    for animal in eco["animals"]:
        count = animal["count"]
        atype = animal["animal_type"]
        if count > 0:
            if atype == "black_tailed_deer":
                parts.append("A black-tailed deer watches from the tree line, ears twitching.")
            elif atype == "roosevelt_elk":
                parts.append(f"{count} elk graze at the clearing's edge, large and quiet.")
            elif atype == "black_bear":
                parts.append("A black bear has worked through here recently; the salal is bent and torn.")
            elif atype == "coyote":
                parts.append("A coyote moves along the ridge, there and gone before the eye settles.")
            elif atype == "raccoon":
                parts.append("A raccoon works the creek stones with clever paws.")
            elif atype == "river_otter":
                parts.append("River otters slip through the cold water like thrown shadows.")
            elif atype == "steller_jay":
                parts.append("Steller's jays argue in the cedars, blue-black and indignant.")
            elif atype == "raven":
                parts.append("A raven rides the ridge wind and says one hard word to the trees.")
            elif atype == "varied_thrush":
                parts.append("A varied thrush sings from somewhere deep in the green shadow.")
            elif atype == "barred_owl":
                parts.append("A barred owl watches from the cedar dark, patient and nearly invisible.")
            elif atype == "tree_frog":
                parts.append("Tree frogs sing their peeping chorus after the rain.")
            elif atype == "snowshoe_hare":
                parts.append("A snowshoe hare freezes under the salal, then vanishes into it.")

    # Fish
    for fish in eco["fish"]:
        if fish["abundance"] > 0.6:
            parts.append(f"The water is alive with {fish['fish_type']}.")

    return parts
