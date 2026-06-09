"""
embodied_world/setup_wizard.py — Interactive world setup.

Walks the user through creating a WorldConfig step by step.
Can be run standalone or called from an agent harness.

Usage:
    python -m src.setup_wizard
    python -m src.setup_wizard --output my_world.yaml
    python -m src.setup_wizard --preset nc_coastal
"""

import sys
import os
from pathlib import Path
from typing import Optional

try:
    from .world_template import (
        WorldConfig, GeographyConfig, CultureConfig, EcologyConfig,
        ClimateConfig, AgentConfig, RitualConfig,
        get_nc_coastal_config, load_config, save_config, DEFAULT_CONFIG,
    )
except ImportError:
    from world_template import (
        WorldConfig, GeographyConfig, CultureConfig, EcologyConfig,
        ClimateConfig, AgentConfig, RitualConfig,
        get_nc_coastal_config, load_config, save_config, DEFAULT_CONFIG,
    )


# ── PRESETS ──

PRESETS = {
    "nc_coastal": {
        "description": "Carteret County, NC — Crystal Coast fishing village",
        "factory": get_nc_coastal_config,
    },
    "pacific_northwest": {
        "description": "Pacific Northwest — mountain valley with old-growth forest",
        "factory": lambda: WorldConfig(
            name="Pacific Northwest Valley",
            geography=GeographyConfig(
                region_name="The Valley",
                region_description="A mountain valley in the Pacific Northwest, wrapped in old-growth forest.",
                climate="coastal_north",
                water_body_type="river",
                water_body_name="The River",
                water_description="cold, clear water running fast over smooth stones",
                elevation="foothills",
                features=["old_growth_forest", "hot_springs", "terraced_farms"],
            ),
            culture=CultureConfig(
                speech_style="northern_us",
                greeting_style="casual",
                occupations={
                    "fisherman": {"count": 10, "locations": ["harbor", "dock"]},
                    "farmer": {"count": 12, "locations": ["farm_edge", "farmhouse"]},
                    "lumberjack": {"count": 15, "locations": ["forest_edge", "forest_deep"]},
                    "craftsman": {"count": 8, "locations": ["town_square"]},
                    "shopkeeper": {"count": 6, "locations": ["market_stall", "general_store"]},
                    "sailor": {"count": 5, "locations": ["harbor", "dock"]},
                    "child": {"count": 25, "locations": ["town_square", "farmhouse"]},
                    "elder": {"count": 10, "locations": ["town_square", "chapel"]},
                },
            ),
            ecology=EcologyConfig(
                plants=[
                    {"name": "douglas_fir", "type": "tree", "season": "all"},
                    {"name": "western_red_cedar", "type": "tree", "season": "all"},
                    {"name": "salmonberry", "type": "shrub", "season": "spring"},
                    {"name": "huckleberry", "type": "shrub", "season": "summer"},
                    {"name": "sword_fern", "type": "fern", "season": "all"},
                    {"name": "oregano", "type": "herb", "season": "spring"},
                    {"name": "potatoes", "type": "crop", "season": "summer"},
                    {"name": "wheat", "type": "crop", "season": "summer"},
                ],
                animals=[
                    {"name": "black_bear", "habitat": "forest_deep", "count_range": [1, 4]},
                    {"name": "salmon", "habitat": "creek", "count_range": [50, 200]},
                    {"name": "bald_eagle", "habitat": "forest_edge", "count_range": [1, 3]},
                    {"name": "elk", "habitat": "forest_clearing", "count_range": [3, 12]},
                    {"name": "raccoon", "habitat": "forest_deep", "count_range": [2, 8]},
                    {"name": "deer", "habitat": "forest_clearing", "count_range": [2, 8]},
                ],
                fish=[
                    {"name": "chinook_salmon", "season": "autumn", "abundance_range": [0.4, 0.9]},
                    {"name": "steelhead", "season": "spring", "abundance_range": [0.3, 0.7]},
                    {"name": "cutthroat_trout", "season": "summer", "abundance_range": [0.2, 0.5]},
                ],
            ),
            climate=ClimateConfig(
                season_temps={
                    "spring": {"base": 8, "range": (-5, 10)},
                    "summer": {"base": 18, "range": (5, 15)},
                    "autumn": {"base": 10, "range": (-3, 8)},
                    "winter": {"base": -2, "range": (-15, 5)},
                },
                season_weather={
                    "spring": {"clear": 0.2, "cloudy": 0.3, "foggy": 0.15, "rain": 0.3, "storm": 0.05},
                    "summer": {"clear": 0.5, "cloudy": 0.2, "foggy": 0.05, "rain": 0.15, "storm": 0.1},
                    "autumn": {"clear": 0.15, "cloudy": 0.25, "foggy": 0.15, "rain": 0.35, "storm": 0.1},
                    "winter": {"clear": 0.1, "cloudy": 0.2, "foggy": 0.1, "rain": 0.15, "storm": 0.45},
                },
            ),
        ),
    },
    "mediterranean": {
        "description": "Mediterranean coast — olive groves, warm seas, ancient ruins",
        "factory": lambda: WorldConfig(
            name="Mediterranean Coast",
            geography=GeographyConfig(
                region_name="The Coast",
                region_description="A sun-drenched Mediterranean coastline with olive groves and ancient ruins.",
                climate="mediterranean",
                water_body_type="sea",
                water_body_name="The Sea",
                water_description="deep blue water, warm and clear, smelling of salt and wild herbs",
                elevation="low_rise",
                features=["olive_groves", "vineyards", "ancient_ruins", "fishing_harbor"],
            ),
            culture=CultureConfig(
                speech_style="french",
                greeting_style="warm",
                male_first_names=[
                    "Jean", "Pierre", "Louis", "Antoine", "Henri", "François", "Michel",
                    "André", "Philippe", "René", "Marcel", "Paul",
                ],
                female_first_names=[
                    "Marie", "Jeanne", "Françoise", "Monique", "Catherine", "Nathalie",
                    "Isabelle", "Sylvie", "Anne", "Claire", "Sophie",
                ],
                surnames=[
                    "Dupont", "Martin", "Bernard", "Dubois", "Moreau", "Laurent",
                    "Simon", "Michel", "Lefebvre", "Leroy", "Roux", "David",
                ],
                occupations={
                    "fisherman": {"count": 15, "locations": ["harbor", "dock"]},
                    "farmer": {"count": 20, "locations": ["farm_edge", "farmhouse", "orchard"]},
                    "winemaker": {"count": 10, "locations": ["orchard", "farmhouse"]},
                    "craftsman": {"count": 8, "locations": ["town_square"]},
                    "merchant": {"count": 8, "locations": ["market_stall", "general_store"]},
                    "sailor": {"count": 6, "locations": ["harbor", "dock"]},
                    "child": {"count": 25, "locations": ["town_square", "farmhouse"]},
                    "elder": {"count": 10, "locations": ["town_square", "chapel"]},
                },
                local_expressions=[
                    "Bonjour",
                    "C'est la vie",
                    "À bientôt",
                    "Santé",
                ],
            ),
            ecology=EcologyConfig(
                plants=[
                    {"name": "olive_tree", "type": "tree", "season": "all"},
                    {"name": "grape_vine", "type": "vine", "season": "summer"},
                    {"name": "lavender", "type": "herb", "season": "summer"},
                    {"name": "rosemary", "type": "herb", "season": "all"},
                    {"name": "thyme", "type": "herb", "season": "spring"},
                    {"name": "wheat", "type": "crop", "season": "summer"},
                    {"name": "tomatoes", "type": "crop", "season": "summer"},
                    {"name": "figs", "type": "tree", "season": "autumn"},
                    {"name": "citrus", "type": "tree", "season": "winter"},
                ],
                animals=[
                    {"name": "wild_boar", "habitat": "forest", "count_range": [2, 8]},
                    {"name": "rabbit", "habitat": "farm_edge", "count_range": [5, 20]},
                    {"name": "seagull", "habitat": "harbor", "count_range": [10, 40]},
                    {"name": "dolphin", "habitat": "rocky_point", "count_range": [0, 6]},
                    {"name": "goat", "habitat": "pasture", "count_range": [5, 15]},
                    {"name": "donkey", "habitat": "farmhouse", "count_range": [1, 4]},
                ],
                fish=[
                    {"name": "sea_bass", "season": "summer", "abundance_range": [0.4, 0.8]},
                    {"name": "sardine", "season": "spring", "abundance_range": [0.5, 1.0]},
                    {"name": "red_mullet", "season": "autumn", "abundance_range": [0.3, 0.6]},
                    {"name": "octopus", "season": "winter", "abundance_range": [0.2, 0.5]},
                ],
            ),
            climate=ClimateConfig(
                season_temps={
                    "spring": {"base": 15, "range": (5, 12)},
                    "summer": {"base": 25, "range": (8, 15)},
                    "autumn": {"base": 18, "range": (5, 10)},
                    "winter": {"base": 8, "range": (0, 8)},
                },
                season_weather={
                    "spring": {"clear": 0.4, "cloudy": 0.25, "foggy": 0.1, "rain": 0.2, "storm": 0.05},
                    "summer": {"clear": 0.7, "cloudy": 0.15, "foggy": 0.05, "rain": 0.05, "storm": 0.05},
                    "autumn": {"clear": 0.35, "cloudy": 0.25, "foggy": 0.1, "rain": 0.25, "storm": 0.05},
                    "winter": {"clear": 0.25, "cloudy": 0.25, "foggy": 0.1, "rain": 0.3, "storm": 0.1},
                },
            ),
        ),
    },
    "desert": {
        "description": "Desert oasis — sand, heat, and a hidden spring",
        "factory": lambda: WorldConfig(
            name="Desert Oasis",
            geography=GeographyConfig(
                region_name="The Oasis",
                region_description="A hidden oasis in a vast desert, where water seeps up from ancient aquifers.",
                climate="desert",
                water_body_type="lake",
                water_body_name="The Spring",
                water_description="clear, cool water bubbling up from deep underground, surrounded by reeds",
                elevation="sea_level",
                features=["sand_dunes", "oasis_palms", "ancient_well", "trading_post"],
            ),
            culture=CultureConfig(
                speech_style="generic",
                greeting_style="formal",
                male_first_names=[
                    "Ahmed", "Omar", "Khalid", "Yusuf", "Ibrahim", "Ali", "Hassan",
                    "Tariq", "Rashid", "Samir", "Nadir", "Jamal",
                ],
                female_first_names=[
                    "Fatima", "Aisha", "Layla", "Zahra", "Maryam", "Khadija", "Safia",
                    "Nadia", "Hana", "Rana", "Dina", "Salma",
                ],
                surnames=[
                    "Al-Rashid", "Ibn-Khalid", "Al-Farsi", "Hassan", "Al-Mansour",
                    "Rashid", "Al-Said", "Khan", "Malik", "Suleiman",
                ],
                occupations={
                    "merchant": {"count": 15, "locations": ["market_stall", "town_square"]},
                    "farmer": {"count": 8, "locations": ["farm_edge", "farmhouse"]},
                    "craftsman": {"count": 10, "locations": ["town_square"]},
                    "herbalist": {"count": 5, "locations": ["forest_edge", "cottage_garden"]},
                    "child": {"count": 20, "locations": ["town_square", "farmhouse"]},
                    "elder": {"count": 8, "locations": ["town_square", "chapel"]},
                },
                local_expressions=[
                    "Peace be upon you",
                    "God willing",
                    "Inshallah",
                    "Welcome, traveler",
                ],
            ),
            ecology=EcologyConfig(
                plants=[
                    {"name": "date_palm", "type": "tree", "season": "all"},
                    {"name": "desert_rose", "type": "shrub", "season": "spring"},
                    {"name": "aloe", "type": "succulent", "season": "all"},
                    {"name": "wheat", "type": "crop", "season": "winter"},
                    {"name": "barley", "type": "crop", "season": "winter"},
                    {"name": "pomegranate", "type": "tree", "season": "autumn"},
                    {"name": "henna", "type": "shrub", "season": "summer"},
                ],
                animals=[
                    {"name": "camel", "habitat": "pasture", "count_range": [3, 10]},
                    {"name": "desert_fox", "habitat": "forest_edge", "count_range": [1, 4]},
                    {"name": "hawk", "habitat": "old_oak", "count_range": [1, 3]},
                    {"name": "goat", "habitat": "pasture", "count_range": [5, 15]},
                    {"name": "chicken", "habitat": "farmhouse", "count_range": [5, 12]},
                ],
                fish=[
                    {"name": "tilapia", "season": "all", "abundance_range": [0.3, 0.7]},
                    {"name": "catfish", "season": "summer", "abundance_range": [0.2, 0.5]},
                ],
            ),
            climate=ClimateConfig(
                season_temps={
                    "spring": {"base": 25, "range": (10, 15)},
                    "summer": {"base": 38, "range": (10, 18)},
                    "autumn": {"base": 28, "range": (8, 12)},
                    "winter": {"base": 15, "range": (0, 10)},
                },
                season_weather={
                    "spring": {"clear": 0.6, "cloudy": 0.15, "foggy": 0.05, "rain": 0.1, "storm": 0.1},
                    "summer": {"clear": 0.8, "cloudy": 0.1, "foggy": 0.0, "rain": 0.02, "storm": 0.08},
                    "autumn": {"clear": 0.5, "cloudy": 0.2, "foggy": 0.05, "rain": 0.15, "storm": 0.1},
                    "winter": {"clear": 0.4, "cloudy": 0.2, "foggy": 0.1, "rain": 0.2, "storm": 0.1},
                },
            ),
        ),
    },
}


# ── WIZARD ──

def ask(prompt: str, default: str = "", choices: Optional[list] = None) -> str:
    """Ask the user a question with an optional default."""
    if choices:
        choices_str = " / ".join(choices)
        full_prompt = f"\n{prompt}\n  [{choices_str}]"
        if default:
            full_prompt += f" (default: {default})"
        full_prompt += "\n> "
    else:
        full_prompt = f"\n{prompt}"
        if default:
            full_prompt += f" (default: {default})"
        full_prompt += "\n> "
    
    answer = input(full_prompt).strip()
    if not answer and default:
        return default
    if choices and answer and answer.lower() not in [c.lower() for c in choices]:
        print(f"  Please choose from: {', '.join(choices)}")
        return ask(prompt, default, choices)
    return answer


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    default_str = "Y/n" if default else "y/N"
    answer = ask(f"{prompt} [{default_str}]", "y" if default else "n")
    return answer.lower() in ("y", "yes", "true", "1")


def ask_list(prompt: str, min_items: int = 1) -> list:
    """Ask for a comma-separated list."""
    answer = ask(prompt)
    items = [i.strip() for i in answer.split(",") if i.strip()]
    if len(items) < min_items:
        print(f"  Please provide at least {min_items} item(s).")
        return ask_list(prompt, min_items)
    return items


def run_wizard(output_path: Optional[str] = None) -> WorldConfig:
    """Run the interactive setup wizard."""
    
    print("=" * 60)
    print("  EMBODIED CREATIVE WORLD — Setup Wizard")
    print("=" * 60)
    print()
    print("This wizard will help you create your world.")
    print("You can choose a preset or build from scratch.")
    print()
    
    # ── PRESET OR CUSTOM ──
    print("Available presets:")
    for key, preset in PRESETS.items():
        print(f"  {key}: {preset['description']}")
    print("  custom: Build your own world from scratch")
    print()
    
    choice = ask("Choose a preset or 'custom'", "nc_coastal",
                 list(PRESETS.keys()) + ["custom"])
    
    if choice in PRESETS:
        config = PRESETS[choice]["factory"]()
        print(f"\n✓ Loaded preset: {config.name}")
        
        if ask_yes_no("Would you like to customize this preset?", False):
            config = customize_config(config)
    else:
        config = build_from_scratch()
    
    # ── SAVE ──
    print()
    print("=" * 60)
    print(f"  World: {config.name}")
    print(f"  Region: {config.geography.region_name}")
    print(f"  Climate: {config.geography.climate}")
    print(f"  Agent: {config.agent.name} ({config.agent.occupation})")
    print("=" * 60)
    
    if output_path is None:
        output_path = ask("Save config to file", "world_config.yaml")
    
    save_config(config, output_path)
    print(f"\n✓ World config saved to: {output_path}")
    print()
    print("To use this world:")
    print(f'  agent = EmbodiedAgent(world_config="{output_path}")')
    print()
    
    return config


def customize_config(config: WorldConfig) -> WorldConfig:
    """Customize an existing config."""
    
    print("\n── Customization ──")
    print("Press Enter to keep the current value.\n")
    
    # Name
    config.name = ask("World name", config.name)
    
    # Geography
    if ask_yes_no("Customize geography?", False):
        config.geography.region_name = ask("Region name", config.geography.region_name)
        config.geography.climate = ask(
            "Climate type", config.geography.climate,
            ["coastal_south", "coastal_north", "mountain", "desert", "plains", "mediterranean"]
        )
        config.geography.water_body_type = ask(
            "Water body type", config.geography.water_body_type,
            ["sound", "ocean", "lake", "river", "bay", "sea"]
        )
        config.geography.water_body_name = ask("Water body name", config.geography.water_body_name)
        config.geography.elevation = ask(
            "Elevation", config.geography.elevation,
            ["sea_level", "low_rise", "foothills", "mountain"]
        )
    
    # Culture
    if ask_yes_no("Customize culture?", False):
        config.culture.speech_style = ask(
            "Speech style", config.culture.speech_style,
            ["southern_us", "northern_us", "british", "irish", "french", "generic"]
        )
        config.culture.greeting_style = ask(
            "Greeting style", config.culture.greeting_style,
            ["casual_southern", "formal", "reserved", "warm", "casual"]
        )
        if ask_yes_no("Customize name pools?", False):
            config.culture.male_first_names = ask_list("Male first names (comma-separated)")
            config.culture.female_first_names = ask_list("Female first names (comma-separated)")
            config.culture.surnames = ask_list("Surnames (comma-separated)")
    
    # Agent
    if ask_yes_no("Customize your character?", False):
        config.agent.name = ask("Your name", config.agent.name)
        config.agent.backstory = ask("Your backstory", config.agent.backstory)
        config.agent.occupation = ask("Your occupation", config.agent.occupation)
    
    # Seed
    if ask_yes_no("Set a random seed for reproducibility?", False):
        seed_str = ask("Seed (integer)", "")
        if seed_str.isdigit():
            config.seed = int(seed_str)
    
    return config


def build_from_scratch() -> WorldConfig:
    """Build a world config from scratch through interactive prompts."""
    
    print("\n── Building Your World From Scratch ---\n")
    
    # ── WORLD NAME ──
    name = ask("World name", "My World")
    
    # ── GEOGRAPHY ──
    print("\n── Geography ──")
    region_name = ask("Region name", "The Valley")
    region_description = ask("Region description", "A small village in a valley.")
    
    climate = ask(
        "Climate type", "coastal_south",
        ["coastal_south", "coastal_north", "mountain", "desert", "plains", "mediterranean"]
    )
    
    water_body_type = ask(
        "Water body type", "sound",
        ["sound", "ocean", "lake", "river", "bay", "sea"]
    )
    water_body_name = ask("Water body name", "The Sound")
    water_description = ask("Water description", "dark, calm water")
    
    elevation = ask(
        "Elevation", "low_rise",
        ["sea_level", "low_rise", "foothills", "mountain"]
    )
    
    features = ask_list("Notable features (comma-separated, e.g. lighthouse,ruins,forest)")
    
    geography = GeographyConfig(
        region_name=region_name,
        region_description=region_description,
        climate=climate,
        water_body_type=water_body_type,
        water_body_name=water_body_name,
        water_description=water_description,
        elevation=elevation,
        features=features,
    )
    
    # ── CULTURE ──
    print("\n── Culture ──")
    speech_style = ask(
        "Speech style", "southern_us",
        ["southern_us", "northern_us", "british", "irish", "french", "generic"]
    )
    greeting_style = ask(
        "Greeting style", "casual_southern",
        ["casual_southern", "formal", "reserved", "warm", "casual"]
    )
    
    male_names = ask_list("Male first names (comma-separated)", 3)
    female_names = ask_list("Female first names (comma-separated)", 3)
    surnames = ask_list("Surnames (comma-separated)", 3)
    
    culture = CultureConfig(
        male_first_names=male_names,
        female_first_names=female_names,
        surnames=surnames,
        speech_style=speech_style,
        greeting_style=greeting_style,
    )
    
    # ── ECOLOGY ──
    print("\n── Ecology ──")
    print("Define what grows and lives in your world.")
    
    plants = []
    if ask_yes_no("Add plants?", True):
        while True:
            plant_name = ask("Plant name (or 'done')", "done")
            if plant_name.lower() == "done":
                break
            plant_type = ask("  Type", "herb", ["herb", "crop", "tree", "shrub", "grass", "vine", "fern", "seaweed", "succulent"])
            plant_season = ask("  Season", "spring", ["spring", "summer", "autumn", "winter", "all"])
            plants.append({"name": plant_name, "type": plant_type, "season": plant_season})
    
    animals = []
    if ask_yes_no("Add animals?", True):
        while True:
            animal_name = ask("Animal name (or 'done')", "done")
            if animal_name.lower() == "done":
                break
            habitat = ask("  Habitat", "forest")
            count_min = int(ask("  Min count", "1"))
            count_max = int(ask("  Max count", "10"))
            animals.append({"name": animal_name, "habitat": habitat, "count_range": [count_min, count_max]})
    
    fish = []
    if ask_yes_no("Add fish/seafood?", True):
        while True:
            fish_name = ask("Fish name (or 'done')", "done")
            if fish_name.lower() == "done":
                break
            fish_season = ask("  Season", "summer", ["spring", "summer", "autumn", "winter", "all"])
            fish.append({"name": fish_name, "season": fish_season, "abundance_range": [0.3, 0.8]})
    
    ecology = EcologyConfig(plants=plants, animals=animals, fish=fish)
    
    # ── CLIMATE ──
    print("\n── Climate ──")
    use_default_climate = ask_yes_no("Use default temperature/weather for this climate type?", True)
    
    if use_default_climate:
        climate = ClimateConfig()  # defaults work for coastal_south
        # Adjust roughly for other climates
        if climate == "mountain":
            climate.season_temps = {
                "spring": {"base": 5, "range": (-10, 10)},
                "summer": {"base": 15, "range": (0, 12)},
                "autumn": {"base": 5, "range": (-8, 8)},
                "winter": {"base": -5, "range": (-20, 3)},
            }
        elif climate == "desert":
            climate.season_temps = {
                "spring": {"base": 25, "range": (10, 15)},
                "summer": {"base": 38, "range": (10, 18)},
                "autumn": {"base": 28, "range": (8, 12)},
                "winter": {"base": 15, "range": (0, 10)},
            }
        elif climate == "mediterranean":
            climate.season_temps = {
                "spring": {"base": 15, "range": (5, 12)},
                "summer": {"base": 25, "range": (8, 15)},
                "autumn": {"base": 18, "range": (5, 10)},
                "winter": {"base": 8, "range": (0, 8)},
            }
    else:
        print("Enter temperature ranges for each season (base, low, high):")
        temps = {}
        for season in ["spring", "summer", "autumn", "winter"]:
            base = int(input(f"  {season} base temp (default 10): ") or "10")
            low = int(input(f"  {season} low (default -5): ") or "-5")
            high = int(input(f"  {season} high (default 10): ") or "10")
            temps[season] = {"base": base, "range": (low, high)}
        climate = ClimateConfig(season_temps=temps)
    
    # ── AGENT ──
    print("\n── Your Character ──")
    agent_name = ask("Your name", "Wanderer")
    agent_backstory = ask("Your backstory", "A stranger who arrived seeking a new life.")
    agent_occupation = ask("Your occupation", "traveler")
    
    agent = AgentConfig(
        name=agent_name,
        backstory=agent_backstory,
        occupation=agent_occupation,
    )
    
    # ── RITUALS ──
    print("\n── Seasonal Rituals ──")
    rituals = []
    if ask_yes_no("Add seasonal rituals?", True):
        for season in ["spring", "summer", "autumn", "winter"]:
            if ask_yes_no(f"  Add a {season} ritual?", True):
                title = ask(f"    {season} ritual title", f"The {season.title()} Festival")
                day = int(ask(f"    Day of season (1-90)", "15"))
                rituals.append({
                    "key": f"{season}_festival",
                    "season": season,
                    "day": day,
                    "title": title,
                    "locations": ["town_square"],
                })
    
    ritual_config = RitualConfig(rituals=rituals)
    
    # ── SEED ──
    seed = None
    if ask_yes_no("Set a random seed for reproducibility?", False):
        seed = int(ask("Seed", "42"))
    
    # ── BUILD ──
    config = WorldConfig(
        name=name,
        geography=geography,
        culture=culture,
        ecology=ecology,
        climate=climate,
        agent=agent,
        rituals=ritual_config,
        seed=seed,
    )
    
    return config


# ── ENTRY POINT ──

def main():
    """Run the setup wizard from the command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Embodied Creative World — Setup Wizard")
    parser.add_argument("--output", "-o", help="Output YAML file path", default=None)
    parser.add_argument("--preset", "-p", help="Start with a preset", choices=list(PRESETS.keys()), default=None)
    args = parser.parse_args()
    
    if args.preset:
        config = PRESETS[args.preset]["factory"]()
        print(f"Loaded preset: {config.name}")
        if ask_yes_no("Customize this preset?", True):
            config = customize_config(config)
        output = args.output or "world_config.yaml"
        save_config(config, output)
        print(f"\n✓ Saved to: {output}")
    else:
        run_wizard(args.output)


if __name__ == "__main__":
    main()
