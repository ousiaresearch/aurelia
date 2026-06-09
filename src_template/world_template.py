"""
embodied_world/world_template.py — Configurable world primitives.

This module defines the "DNA" of a world — the configurable primitives
that determine what the world looks like, who lives there, what grows there,
and what the weather does.

A user provides a WorldConfig (from a YAML file or dict), and the simulation
engine uses it to generate a unique world. The same engine, different worlds.

Usage:
    from world_template import WorldConfig, load_config
    
    # Load from YAML
    config = load_config("my_world.yaml")
    
    # Or build programmatically
    config = WorldConfig(
        name="My World",
        geography=GeographyConfig(...),
        culture=CultureConfig(...),
        ...
    )
"""

from dataclasses import dataclass, field
from typing import Optional
import yaml
import json


# ── GEOGRAPHY ──

@dataclass
class GeographyConfig:
    """Physical setting of the world."""
    
    # Region name
    region_name: str = "The Valley"
    region_description: str = "A small village in a valley."
    
    # Climate type: "coastal_south", "coastal_north", "mountain", "desert", "plains", "mediterranean"
    climate: str = "coastal_south"
    
    # Water body: "sound", "ocean", "lake", "river", "bay", "sea"
    water_body_type: str = "sound"
    water_body_name: str = "The Sound"
    water_description: str = "dark water, the color of sweet tea"
    
    # Elevation: "sea_level", "low_rise", "foothills", "mountain"
    elevation: str = "low_rise"
    
    # Notable features (list of feature names)
    features: list = field(default_factory=lambda: [
        "lighthouse", "tabby_ruins", "maritime_forest", "farmland"
    ])
    
    # Location definitions — each is a dict with:
    #   id, name, description, parent_id, indoor, tags, connections
    # If None, defaults are generated from the template
    locations: Optional[list] = None


# ── CULTURE ──

@dataclass
class CultureConfig:
    """Cultural setting — names, occupations, speech patterns."""
    
    # Name pools
    male_first_names: list = field(default_factory=lambda: [
        "James", "John", "Robert", "William", "David", "Charles", "Thomas",
    ])
    female_first_names: list = field(default_factory=lambda: [
        "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    ])
    surnames: list = field(default_factory=lambda: [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis",
    ])
    
    # Speech style: "southern_us", "northern_us", "british", "irish", "french", "generic"
    speech_style: str = "southern_us"
    
    # Occupations common to this culture/region
    occupations: dict = field(default_factory=lambda: {
        "fisherman": {"count": 20, "locations": ["harbor", "dock"]},
        "farmer": {"count": 15, "locations": ["farm_edge", "farmhouse"]},
        "shopkeeper": {"count": 6, "locations": ["market_stall", "general_store"]},
        "craftsman": {"count": 12, "locations": ["town_square"]},
        "sailor": {"count": 8, "locations": ["harbor", "dock"]},
    })
    
    # Greeting style
    greeting_style: str = "casual_southern"  # casual_southern, formal, reserved, warm
    
    # Key phrases / expressions common to the region
    local_expressions: list = field(default_factory=lambda: [
        "Bless your heart",
        "Fixin' to",
        "Over yonder",
    ])


# ── ECOLOGY ──

@dataclass
class EcologyConfig:
    """What grows and lives in this world."""
    
    # Plant types: list of dicts with name, type, growth_rate, season, description
    plants: list = field(default_factory=lambda: [
        {"name": "rosemary", "type": "herb", "season": "spring"},
        {"name": "thyme", "type": "herb", "season": "spring"},
        {"name": "corn", "type": "crop", "season": "summer"},
        {"name": "pecans", "type": "tree", "season": "autumn"},
    ])
    
    # Animal types: list of dicts with name, habitat, count_range, season
    animals: list = field(default_factory=lambda: [
        {"name": "white_tailed_deer", "habitat": "forest", "count_range": [2, 8]},
        {"name": "brown_pelican", "habitat": "harbor", "count_range": [5, 30]},
        {"name": "blue_crab", "habitat": "tide_pools", "count_range": [10, 40]},
    ])
    
    # Fish types: list of dicts with name, season, abundance_range
    fish: list = field(default_factory=lambda: [
        {"name": "white_shrimp", "season": "autumn", "abundance_range": [0.5, 1.0]},
        {"name": "flounder", "season": "spring", "abundance_range": [0.3, 0.6]},
    ])


# ── CLIMATE ──

@dataclass
class ClimateConfig:
    """Weather and seasonal patterns."""
    
    # Temperature ranges by season (base_temp, temp_range_low, temp_range_high)
    season_temps: dict = field(default_factory=lambda: {
        "spring": {"base": 10, "range": (-2, 8)},
        "summer": {"base": 20, "range": (3, 12)},
        "autumn": {"base": 12, "range": (0, 8)},
        "winter": {"base": 3, "range": (-5, 5)},
    })
    
    # Weather probability weights by season
    season_weather: dict = field(default_factory=lambda: {
        "spring": {"clear": 0.25, "cloudy": 0.3, "foggy": 0.2, "rain": 0.2, "storm": 0.05},
        "summer": {"clear": 0.4, "cloudy": 0.25, "foggy": 0.1, "rain": 0.15, "storm": 0.1},
        "autumn": {"clear": 0.2, "cloudy": 0.3, "foggy": 0.2, "rain": 0.2, "storm": 0.1},
        "winter": {"clear": 0.15, "cloudy": 0.25, "foggy": 0.15, "rain": 0.2, "storm": 0.25},
    })
    
    # Daylight hours by season (earliest sunrise, latest sunset)
    daylight: dict = field(default_factory=lambda: {
        "spring": {"sunrise": 6, "sunset": 18},
        "summer": {"sunrise": 5, "sunset": 21},
        "autumn": {"sunrise": 7, "sunset": 17},
        "winter": {"sunrise": 8, "sunset": 16},
    })


# ── AGENT (the player character) ──

@dataclass
class AgentConfig:
    """The agent who inhabits this world."""
    
    name: str = "Agent"
    backstory: str = "A stranger who arrived recently."
    occupation: str = "traveler"
    
    # Starting location ID
    start_location: str = "cottage_bedroom"
    
    # Starting stats
    starting_energy: float = 0.8
    starting_mood: str = "awake"
    
    # Home location
    home_location: str = "cottage"


# ── RITUALS ──

@dataclass
class RitualConfig:
    """Seasonal rituals and events."""
    
    # List of rituals, each with season, day, title, description
    rituals: list = field(default_factory=lambda: [
        {
            "key": "planting_festival",
            "season": "spring",
            "day": 15,
            "title": "The Planting Festival",
            "locations": ["farm_edge", "farmhouse"],
        },
        {
            "key": "midsummer_bonfire",
            "season": "summer",
            "day": 15,
            "title": "The Midsummer Bonfire",
            "locations": ["beach"],
        },
        {
            "key": "harvest_feast",
            "season": "autumn",
            "day": 15,
            "title": "The Harvest Feast",
            "locations": ["town_square", "farmhouse"],
        },
        {
            "key": "solstice_gathering",
            "season": "winter",
            "day": 21,
            "title": "The Solstice Gathering",
            "locations": ["chapel", "tavern"],
        },
    ])


# ── MASTER CONFIG ──

@dataclass
class WorldConfig:
    """Complete world configuration."""
    
    name: str = "Embodied World"
    version: str = "1.0.0"
    
    geography: GeographyConfig = field(default_factory=GeographyConfig)
    culture: CultureConfig = field(default_factory=CultureConfig)
    ecology: EcologyConfig = field(default_factory=EcologyConfig)
    climate: ClimateConfig = field(default_factory=ClimateConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    rituals: RitualConfig = field(default_factory=RitualConfig)
    
    # Random seed for reproducibility (None = random)
    seed: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "geography": self.geography.__dict__,
            "culture": self.culture.__dict__,
            "ecology": self.ecology.__dict__,
            "climate": self.climate.__dict__,
            "agent": self.agent.__dict__,
            "rituals": self.rituals.__dict__,
            "seed": self.seed,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorldConfig":
        """Create from dict."""
        return cls(
            name=data.get("name", "Embodied World"),
            version=data.get("version", "1.0.0"),
            geography=GeographyConfig(**data.get("geography", {})),
            culture=CultureConfig(**data.get("culture", {})),
            ecology=EcologyConfig(**data.get("ecology", {})),
            climate=ClimateConfig(**data.get("climate", {})),
            agent=AgentConfig(**data.get("agent", {})),
            rituals=RitualConfig(**data.get("rituals", {})),
            seed=data.get("seed"),
        )


def load_config(path: str) -> WorldConfig:
    """Load world config from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return WorldConfig.from_dict(data)


def save_config(config: WorldConfig, path: str):
    """Save world config to a YAML file."""
    with open(path, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)


# ── DEFAULT TEMPLATES ──

def get_nc_coastal_config() -> WorldConfig:
    """The default NC coastal Carteret County world."""
    return WorldConfig(
        name="Carteret County, NC",
        geography=GeographyConfig(
            region_name="Carteret County",
            region_description="The Crystal Coast of North Carolina",
            climate="coastal_south",
            water_body_type="sound",
            water_body_name="Core Sound",
            water_description="dark water, the color of sweet tea, tannin-rich from the maritime forest",
            elevation="low_rise",
            features=["lighthouse", "tabby_ruins", "maritime_forest", "farmland", "pecan_orchard"],
        ),
        culture=CultureConfig(
            male_first_names=[
                "James", "John", "Robert", "William", "David", "Charles", "Thomas", "Michael",
                "Christopher", "Daniel", "Matthew", "Andrew", "Joshua", "Ryan", "Jacob",
                "Crawford", "Nate", "Owen", "Finley", "Dale", "Patrick", "Wayne",
            ],
            female_first_names=[
                "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
                "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret",
                "Martha", "Ellen", "Greta", "Asha", "Bridget", "Sarah", "Mary Beth",
            ],
            surnames=[
                "Brennan", "Henderson", "Moss", "Bowen", "Smith", "Johnson", "Williams",
                "Brown", "Jones", "Miller", "Davis", "Wilson", "Moore", "Taylor",
                "Crawford", "Boyd", "Mason", "Warren", "Fox", "Rose", "Rice",
            ],
            speech_style="southern_us",
            occupations={
                "shrimper": {"count": 20, "locations": ["harbor", "dock", "fisher_house"]},
                "crabber": {"count": 10, "locations": ["harbor", "dock"]},
                "farmer": {"count": 15, "locations": ["farm_edge", "farmhouse", "orchard"]},
                "woodcutter": {"count": 8, "locations": ["forest_edge", "forest_trail"]},
                "craftsman": {"count": 12, "locations": ["town_square", "general_store"]},
                "seamstress": {"count": 6, "locations": ["town_square"]},
                "cook": {"count": 8, "locations": ["tavern", "fisher_house", "farmhouse"]},
                "merchant": {"count": 6, "locations": ["market_stall", "general_store"]},
                "herbalist": {"count": 4, "locations": ["forest_edge", "cottage_garden"]},
                "sailor": {"count": 8, "locations": ["harbor", "dock", "tavern"]},
                "child": {"count": 30, "locations": ["town_square", "farmhouse"]},
                "elder": {"count": 12, "locations": ["town_square", "chapel", "general_store"]},
                "apprentice": {"count": 10, "locations": ["cottage_workshop", "general_store"]},
                "housekeeper": {"count": 8, "locations": ["fisher_house", "farmhouse"]},
                "bartender": {"count": 4, "locations": ["tavern"]},
                "fishmonger": {"count": 8, "locations": ["market_stall", "fisher_house"]},
                "mechanic": {"count": 5, "locations": ["harbor", "general_store"]},
                "teacher": {"count": 3, "locations": ["town_square", "chapel"]},
                "nurse": {"count": 3, "locations": ["town_square", "chapel"]},
                "hunter": {"count": 4, "locations": ["forest_edge", "forest_deep"]},
            },
            greeting_style="casual_southern",
            local_expressions=[
                "Bless your heart",
                "Fixin' to",
                "Over yonder",
                "Might could",
                "Come here often?",
            ],
        ),
        ecology=EcologyConfig(
            plants=[
                {"name": "rosemary", "type": "herb", "season": "spring"},
                {"name": "thyme", "type": "herb", "season": "spring"},
                {"name": "chives", "type": "herb", "season": "spring"},
                {"name": "hot_peppers", "type": "herb", "season": "summer"},
                {"name": "mint", "type": "herb", "season": "spring"},
                {"name": "collard_greens", "type": "crop", "season": "spring"},
                {"name": "sweet_potatoes", "type": "crop", "season": "summer"},
                {"name": "corn", "type": "crop", "season": "summer"},
                {"name": "tobacco", "type": "crop", "season": "summer"},
                {"name": "pecans", "type": "tree", "season": "autumn"},
                {"name": "sea_oats", "type": "grass", "season": "summer"},
                {"name": "spanish_moss", "type": "epiphyte", "season": "all"},
                {"name": "saw_palmetto", "type": "shrub", "season": "all"},
                {"name": "yaupon_holly", "type": "shrub", "season": "all"},
                {"name": "resurrection_fern", "type": "fern", "season": "all"},
                {"name": "seaweed", "type": "seaweed", "season": "all"},
                {"name": "beautyberry", "type": "shrub", "season": "summer"},
                {"name": "honeysuckle", "type": "vine", "season": "spring"},
                {"name": "live_oak", "type": "tree", "season": "all"},
                {"name": "longleaf_pine", "type": "tree", "season": "all"},
                {"name": "cypress", "type": "tree", "season": "all"},
            ],
            animals=[
                {"name": "cattle", "habitat": "pasture", "count_range": [8, 25]},
                {"name": "chicken", "habitat": "farmhouse", "count_range": [5, 15]},
                {"name": "brown_pelican", "habitat": "harbor", "count_range": [5, 30]},
                {"name": "blue_crab", "habitat": "tide_pools", "count_range": [10, 40]},
                {"name": "bottlenose_dolphin", "habitat": "rocky_point", "count_range": [0, 6]},
                {"name": "raccoon", "habitat": "forest_deep", "count_range": [2, 8]},
                {"name": "white_tailed_deer", "habitat": "forest_clearing", "count_range": [2, 8]},
                {"name": "cottontail_rabbit", "habitat": "farm_edge", "count_range": [5, 20]},
                {"name": "great_horned_owl", "habitat": "old_oak", "count_range": [1, 3]},
                {"name": "osprey", "habitat": "creek", "count_range": [1, 4]},
                {"name": "red_fox", "habitat": "forest_edge", "count_range": [1, 3]},
                {"name": "dog", "habitat": "farmhouse", "count_range": [1, 3]},
                {"name": "cat", "habitat": "general_store", "count_range": [1, 3]},
                {"name": "tree_frog", "habitat": "creek", "count_range": [20, 100]},
                {"name": "wild_turkey", "habitat": "forest_trail", "count_range": [3, 12]},
            ],
            fish=[
                {"name": "white_shrimp", "season": "autumn", "abundance_range": [0.5, 1.0]},
                {"name": "brown_shrimp", "season": "summer", "abundance_range": [0.4, 0.9]},
                {"name": "blue_crab_fish", "season": "summer", "abundance_range": [0.4, 0.8]},
                {"name": "red_drum", "season": "autumn", "abundance_range": [0.3, 0.7]},
                {"name": "flounder", "season": "spring", "abundance_range": [0.3, 0.6]},
                {"name": "speckled_trout", "season": "spring", "abundance_range": [0.3, 0.7]},
                {"name": "channel_bass", "season": "summer", "abundance_range": [0.2, 0.5]},
                {"name": "spot", "season": "all", "abundance_range": [0.4, 0.8]},
            ],
        ),
        climate=ClimateConfig(),  # defaults are already NC coastal
        agent=AgentConfig(
            name="Agent",
            backstory="A stranger who arrived recently.",
            occupation="traveler",
            start_location="cottage_bedroom",
            home_location="cottage",
        ),
        rituals=RitualConfig(
            rituals=[
                {"key": "planting_festival", "season": "spring", "day": 15,
                 "title": "The Planting Festival", "locations": ["farm_edge", "farmhouse", "town_square"]},
                {"key": "first_catch", "season": "spring", "day": 20,
                 "title": "The First Catch", "locations": ["harbor", "dock"]},
                {"key": "midsummer_bonfire", "season": "summer", "day": 15,
                 "title": "The Midsummer Bonfire", "locations": ["beach", "town_square"]},
                {"key": "sea_swimming", "season": "summer", "day": 25,
                 "title": "Sea Swimming Day", "locations": ["beach", "rocky_point"]},
                {"key": "harvest_feast", "season": "autumn", "day": 15,
                 "title": "The Harvest Feast", "locations": ["town_square", "farmhouse", "tavern"]},
                {"key": "pecan_cracking", "season": "autumn", "day": 22,
                 "title": "Pecan Cracking", "locations": ["orchard", "farmhouse"]},
                {"key": "solstice_gathering", "season": "winter", "day": 21,
                 "title": "The Solstice Gathering", "locations": ["chapel", "tavern", "town_square"]},
                {"key": "story_night", "season": "winter", "day": 28,
                 "title": "Story Night", "locations": ["tavern"]},
            ],
        ),
    )


# Export the default config
DEFAULT_CONFIG = get_nc_coastal_config()
