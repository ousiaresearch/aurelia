"""
npc_generation.py — Procedural NPC generation for the Pacific Northwest cabin world.

Expands the 4 hand-crafted key characters to a full population of ~50+
procedurally generated NPCs, each with:
- A name (culturally consistent — Pacific Northwest mountain community)
- Age, gender, occupation
- Personality traits (from a trait system)
- A home location
- Daily routine
- Relationships with nearby NPCs

The 4 key NPCs (Mira, Thomas, Sage, Wren) are preserved as-is.
The remaining ~46+ are generated to feel like real people who belong
in the mountains and forests of the Pacific Northwest.
"""

import json
import random
import time
from typing import Optional

# ── NAME POOLS — Pacific Northwest ──
# Mix of PNW heritage: Scandinavian, Indigenous, settler, modern eclectic

FIRST_NAMES_MALE = [
    "James", "John", "Robert", "William", "David", "Charles", "Thomas", "Michael",
    "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Paul", "Steven", "Andrew",
    "Kenneth", "Joshua", "Kevin", "Brian", "George", "Edward", "Timothy", "Jason",
    "Jeffrey", "Ryan", "Jacob", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry",
    "Justin", "Scott", "Brandon", "Benjamin", "Samuel", "Raymond", "Gregory", "Frank",
    "Alexander", "Patrick", "Jack", "Dennis", "Tyler", "Aaron", "Nathan", "Henry",
    "Douglas", "Zachary", "Peter", "Kyle", "Noah", "Ethan", "Jeremy", "Walter",
    "Christian", "Keith", "Roger", "Terry", "Austin", "Sean", "Gerald", "Carl",
    "Harold", "Dylan", "Arthur", "Lawrence", "Jordan", "Jesse", "Bryan", "Billy",
    "Bruce", "Gabriel", "Joe", "Logan", "Albert", "Willie", "Alan", "Eugene",
    "Russell", "Vincent", "Philip", "Bobby", "Johnny", "Ralph", "Roy", "Louis",
    "Howard", "Caleb", "Dale", "Nate", "Owen", "Finley", "Wayne", "Glen",
    "Erik", "Lars", "Sven", "Bjorn", "Olaf", "Leif", "Arne", "Knut",
    "Isaac", "Miles", "Rowan", "Silas", "Jasper", "Felix", "Hugo", "Oscar",
    "Theo", "Ellis", "Ronan", "Callum", "Eamon", "Desmond", "Niall", "Cian",
]

FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica",
    "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret", "Sandra", "Ashley",
    "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol", "Amanda", "Melissa",
    "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura", "Cynthia", "Kathleen", "Amy",
    "Angela", "Shirley", "Anna", "Brenda", "Pamela", "Emma", "Nicole", "Helen",
    "Samantha", "Katherine", "Christine", "Debra", "Rachel", "Carolyn", "Janet", "Catherine",
    "Maria", "Heather", "Diane", "Ruth", "Julie", "Olivia", "Joyce", "Virginia",
    "Victoria", "Kelly", "Lauren", "Christina", "Joan", "Evelyn", "Judith", "Megan",
    "Andrea", "Cheryl", "Hannah", "Jacqueline", "Martha", "Gloria", "Teresa", "Ann",
    "Sara", "Madison", "Frances", "Kathryn", "Janice", "Jean", "Abigail", "Alice",
    "Judy", "Sophia", "Grace", "Denise", "Amber", "Doris", "Marilyn", "Danielle",
    "Beverly", "Isabella", "Theresa", "Diana", "Natalie", "Brittany", "Charlotte", "Marie",
    "Kayla", "Alexis", "Lori", "Asha", "Greta", "Ellen", "Bridget", "Aisling",
    "Cora", "Hazel", "Iris", "Pearl", "Astrid", "Freya", "Ingrid", "Sigrid",
    "Liv", "Astrid", "Solveig", "Thyra", "Ylva", "Elsa", "Linnea", "Saga",
    "Ivy", "Willow", "Sage", "Wren", "Fern", "Hazel", "Iris", "Luna",
    "Aurora", "Cleo", "Maeve", "Niamh", "Orla", "Roisin", "Saoirse", "Tara",
]

SURNAMES = [
    "Anderson", "Olson", "Larson", "Hansen", "Pedersen", "Nilsen", "Jensen", "Knudsen",
    "Madsen", "Christensen", "Rasmussen", "Sorensen", "Paulsen", "Johansen", "Mikkelsen",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson",
    "Moore", "Taylor", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson",
    "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez", "Lewis", "Lee", "Walker",
    "Hall", "Allen", "Young", "Hernandez", "King", "Wright", "Lopez", "Hill", "Scott",
    "Green", "Adams", "Baker", "Gonzalez", "Nelson", "Carter", "Mitchell", "Perez",
    "Roberts", "Turner", "Phillips", "Campbell", "Parker", "Evans", "Edwards", "Collins",
    "Stewart", "Sanchez", "Morris", "Rogers", "Reed", "Cook", "Morgan", "Bell", "Murphy",
    "Bailey", "Rivera", "Cooper", "Richardson", "Cox", "Howard", "Ward", "Torres",
    "Peterson", "Gray", "Ramirez", "James", "Watson", "Brooks", "Kelly", "Sanders",
    "Price", "Bennett", "Wood", "Barnes", "Ross", "Henderson", "Coleman", "Jenkins",
    "Perry", "Powell", "Long", "Patterson", "Hughes", "Flores", "Washington", "Butler",
    "Simmons", "Foster", "Gonzales", "Bryant", "Alexander", "Russell", "Griffin", "Diaz",
    "Hayes", "Myers", "Ford", "Hamilton", "Graham", "Sullivan", "Wallace", "Woods",
    "Cole", "West", "Jordan", "Owens", "Reynolds", "Fisher", "Ellis", "Harrison",
    "Gibson", "Mcdonald", "Cruz", "Marshall", "Ortiz", "Gomez", "Murray", "Freeman",
    "Wells", "Webb", "Simpson", "Stevens", "Tucker", "Porter", "Hunter", "Hicks",
    "Crawford", "Boyd", "Mason", "Warren", "Fox", "Rose", "Rice", "Moreno",
    "Schmidt", "Patel", "Nichols", "Herrera", "Medina", "Ryan", "Fernandez", "Weaver",
    "Daniels", "Stephens", "Payne", "Kelley", "Dunn", "Pierce", "Arnold", "Tran",
    "Spencer", "Peters", "Hawkins", "Grant", "Hansen", "Castro", "Hoffman", "Hart",
    "Elliott", "Cunningham", "Knight", "Bradley", "Carroll", "Hudson", "Duncan",
    "Armstrong", "Berry", "Andrews", "Johnston", "Ray", "Lane", "Riley", "Carpenter",
    "Perkins", "Aguilar", "Silva", "Richards", "Willis", "Matthews", "Chapman", "Lawrence",
    "Garza", "Vargas", "Watkins", "Wheeler", "Larson", "Carlson", "Harper", "George",
    "Greene", "Burke", "Guzman", "Morrison", "Munoz", "Jacobs", "Obrien", "Lawson",
    "Franklin", "Lynch", "Bishop", "Carr", "Salazar", "Austin", "Mendez", "Gilbert",
    "Jensen", "Williamson", "Montgomery", "Harvey", "Oliver", "Howell", "Dean", "Hanson",
    "Weber", "Garrett", "Sims", "Burton", "Fuller", "Soto", "Mccoy", "Welch", "Chen",
    "Schultz", "Walters", "Reid", "Fields", "Walsh", "Little", "Bowman", "Davidson",
    "May", "Day", "Schneider", "Newman", "Brewer", "Lucas", "Holland", "Wong",
    "Banks", "Santos", "Curtis", "Pearson", "Delgado", "Valdez", "Pena", "Rios",
    "Douglas", "Sandoval", "Barrett", "Hopkins", "Keller", "Guerrero", "Stanley", "Bates",
    "Alvarado", "Beck", "Ortega", "Wade", "Estrada", "Contreras", "Barnett", "Caldwell",
    "Santiago", "Lambert", "Powers", "Chambers", "Nunez", "Craig", "Leonard", "Lowe",
    "Rhodes", "Byrd", "Shelton", "Frost", "Norris", "Leach", "Orr", "Berger",
    "Mckee", "Conway", "Stein", "Bullock", "Knox", "Meadows", "Solomon", "Vaughn",
    "Eagles", "Bender", "Blevins", "Guthrie", "Seymour", "Yates", "Pugh", "Salinas",
    "Schwartz", "Rutledge", "Mcintosh", "Puckett", "Kern", "Benton", "Mcgowan", "Mcmillan",
    "Elmore", "Faulk", "Williford", "Sumner", "Stallings", "Alderman", "Batts", "Blalock",
    "Braswell", "Bunn", "Creech", "Daughtry", "Dawson", "Eason", "Fonville", "Godwin",
    "Hardison", "Holliday", "Ipock", "Jessup", "Kittrell", "Lassiter", "Mabry", "Mangum",
    "Merritt", "Outlaw", "Pate", "Peacock", "Privett", "Riggs", "Rogers", "Sasser",
    "Scarborough", "Sugg", "Tilghman", "Tyson", "Vick", "Walston", "Wheaton", "Whitfield",
    "Wiggins", "Willoughby", "Wooten", "Yarborough",
    "Storm", "Forrest", "Heath", "Dale", "Glen", "Vale", "Rivers", "Stone",
    "Wolf", "Hawk", "Fox", "Bear", "Deer", "Owl", "Raven", "Crane", "Finch",
    "Sage", "Willow", "Fern", "Ivy", "Rowan", "Alder", "Cedar", "Birch", "Maple",
]

# ── OCCUPATIONS — Pacific Northwest mountain community ──

OCCUPATIONS = {
    "forest_ranger": {"count": 6, "locations": ["forest_edge", "cedar_trail", "ridgeline"], "skills": ["wildlife_monitoring", "trail_maintenance", "search_rescue", "fire_management"]},
    "logger": {"count": 8, "locations": ["cedar_deep", "forest_edge"], "skills": ["tree_felling", "chainsaw_operation", "timber_grading", "forest_knowledge"]},
    "mushroom_forager": {"count": 5, "locations": ["cedar_deep", "mountain_creek", "clearing"], "skills": ["mushroom_identification", "drying", "cooking", "forest_knowledge"]},
    "organic_farmer": {"count": 10, "locations": ["garden", "forest_edge"], "skills": ["organic_growing", "composting", "seed_saving", "food_preservation"]},
    "carpenter": {"count": 8, "locations": ["workshop", "cabin"], "skills": ["woodworking", "furniture_making", "timber_framing", "finishing"]},
    "woodworker": {"count": 6, "locations": ["workshop"], "skills": ["carving", "turning", "joinery", "finishing"]},
    "herbalist": {"count": 4, "locations": ["forest_edge", "garden", "cedar_trail"], "skills": ["plant_identification", "tincture_making", "healing", "wildcrafting"]},
    "wildlife_biologist": {"count": 3, "locations": ["forest_edge", "cedar_trail", "ridgeline"], "skills": ["animal_tracking", "data_collection", "habitat_assessment", "birding"]},
    "child": {"count": 12, "locations": ["cabin", "garden", "clearing"], "skills": ["playing", "learning", "helping"]},
    "elder": {"count": 8, "locations": ["cabin", "ridgeline", "clearing"], "skills": ["storytelling", "wisdom", "history", "weather_reading"]},
    "apprentice": {"count": 6, "locations": ["workshop", "garden", "forest_edge"], "skills": ["learning", "assisting", "carrying"]},
    "homemaker": {"count": 8, "locations": ["cabin", "garden", "wine_cellar"], "skills": ["cooking", "preserving", "mending", "gardening"]},
    "midwife": {"count": 2, "locations": ["cabin", "forest_edge"], "skills": ["healing", "childbirth", "herbal_remedies"]},
    "brewer": {"count": 3, "locations": ["cabin", "workshop"], "skills": ["brewing", "fermentation", "tasting"]},
    "writer": {"count": 4, "locations": ["cabin", "ridgeline", "clearing"], "skills": ["writing", "editing", "research"]},
    "artist": {"count": 4, "locations": ["cabin", "workshop", "clearing"], "skills": ["painting", "drawing", "sculpting"]},
    "mechanic": {"count": 4, "locations": ["workshop"], "skills": ["engine_repair", "welding", "electrical", "small_engine"]},
    "hunter": {"count": 5, "locations": ["cedar_deep", "forest_edge", "ridgeline"], "skills": ["hunting", "tracking", "butchering", "hide_tanning"]},
    "fisher": {"count": 5, "locations": ["mountain_creek", "cedar_trail"], "skills": ["fly_fishing", "rod_building", "stream_ecology"]},
    "guide": {"count": 3, "locations": ["cedar_trail", "ridgeline", "forest_edge"], "skills": ["navigation", "wilderness_safety", "natural_history", "group_management"]},
    "teacher": {"count": 3, "locations": ["cabin", "clearing"], "skills": ["teaching", "mentoring", "organizing"]},
    "nurse": {"count": 3, "locations": ["cabin", "forest_edge"], "skills": ["healing", "triage", "herbal_remedies"]},
    "retired": {"count": 6, "locations": ["cabin", "ridgeline", "clearing"], "skills": ["reading", "walking", "observing"]},
    "volunteer_firefighter": {"count": 4, "locations": ["cabin", "forest_edge", "cedar_trail"], "skills": ["fire_suppression", "first_aid", "chainsaw_operation"]},
    "naturalist": {"count": 3, "locations": ["cedar_trail", "mountain_creek", "clearing"], "skills": ["birding", "botany", "ecology", "education"]},
    "potter": {"count": 2, "locations": ["workshop", "cabin"], "skills": ["throwing", "glazing", "kiln_operation"]},
    "weaver": {"count": 2, "locations": ["cabin", "workshop"], "skills": ["spinning", "weaving", "dyeing"]},
    "luthier": {"count": 1, "locations": ["workshop"], "skills": ["instrument_building", "wood_selection", "finishing"]},
    "astronomer": {"count": 2, "locations": ["ridgeline", "cabin_deck"], "skills": ["observation", "photography", "celestial_navigation"]},
    "chef": {"count": 2, "locations": ["cabin", "cabin_kitchen"], "skills": ["cooking", "foraging", "fermentation", "preservation"]},
    "dog_trainer": {"count": 2, "locations": ["cabin", "cedar_trail"], "skills": ["training", "behavior", "agility"]},
    "photographer": {"count": 3, "locations": ["ridgeline", "clearing", "mountain_creek"], "skills": ["landscape", "wildlife", "darkroom"]},
    "yoga_instructor": {"count": 2, "locations": ["cabin", "clearing"], "skills": ["teaching", "meditation", "anatomy"]},
    "therapist": {"count": 2, "locations": ["cabin", "forest_edge"], "skills": ["counseling", "active_listening", "crisis_intervention"]},
    "beekeeper": {"count": 2, "locations": ["garden", "forest_edge"], "skills": ["hive_management", "honey_harvesting", "pollination"]},
    "cheesemaker": {"count": 1, "locations": ["cabin", "workshop"], "skills": ["cheese_culturing", "aging", "milk_handling"]},
    "mason": {"count": 2, "locations": ["workshop", "cabin"], "skills": ["stone_work", "fireplace_building", "restoration"]},
    "blacksmith": {"count": 1, "locations": ["workshop"], "skills": ["forging", "tool_making", "horseshoeing"]},
    "librarian": {"count": 2, "locations": ["cabin", "clearing"], "skills": ["cataloging", "research", "community"]},
    "veterinarian": {"count": 2, "locations": ["cabin", "forest_edge"], "skills": ["animal_care", "surgery", "diagnostics"]},
    "social_worker": {"count": 2, "locations": ["cabin", "forest_edge"], "skills": ["counseling", "advocacy", "community"]},
    "carpenter_apprentice": {"count": 3, "locations": ["workshop"], "skills": ["learning", "measuring", "cutting"]},
    "botanist": {"count": 2, "locations": ["cedar_trail", "mountain_creek", "clearing"], "skills": ["plant_taxonomy", "field_work", "herbarium"]},
    "park_ranger": {"count": 3, "locations": ["ridgeline", "cedar_trail", "forest_edge"], "skills": ["enforcement", "education", "trail_maintenance"]},
    "musician": {"count": 3, "locations": ["cabin", "clearing", "cabin_deck"], "skills": ["guitar", "singing", "songwriting"]},
    "poet": {"count": 2, "locations": ["cabin", "ridgeline", "wine_cellar"], "skills": ["writing", "reading", "observation"]},
}

# ── PERSONALITY TRAITS ──

PERSONALITY_TRAITS = [
    "warm", "reserved", "boisterous", "quiet", "cheerful", "melancholy",
    "practical", "dreamy", "sharp", "gentle", "stubborn", "easygoing",
    "proud", "humble", "curious", "cautious", "bold", "timid",
    "generous", "frugal", "honest", "cunning", "loyal", "independent",
    "patient", "impatient", "thoughtful", "impulsive", "serious", "playful",
    "kind", "stern", "optimistic", "pessimistic", "romantic", "pragmatic",
    "spiritual", "skeptical", "traditional", "progressive", "gregarious", "solitary",
    "intense", "laid_back", "meticulous", "spontaneous", "stoic", "expressive",
    "introspective", "outdoorsy", "bookish", "hands_on", "philosophical", "grounded",
]

SPEECH_PATTERNS = [
    "direct and plain", "soft and measured", "loud and laughing",
    "sparse but meaningful", "fast and animated", "slow and deliberate",
    "full of proverbs", "dry humor", "warm and motherly",
    "gruff but kind", "poetic", "blunt", "gentle",
    "storyteller", "questioner", "listener", "joker",
    "technical", "philosophical", "earnest", "wry",
]

# ── HOME LOCATIONS ──

HOME_LOCATIONS = [
    "cabin", "cabin_main_room", "cabin_bedroom",
    "workshop", "garden", "wine_cellar",
    "forest_edge", "cedar_trail", "ridgeline",
    "clearing", "mountain_creek", "cedar_deep",
    "cabin_deck", "cabin_kitchen",
]


def _pick_name(used_names: set, gender: str) -> str:
    """Pick a unique name."""
    pool = FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE
    available = [n for n in pool if n not in used_names]
    if not available:
        available = pool  # fallback: allow duplicates with surname differentiation
    first = random.choice(available)
    used_names.add(first)
    return first


def _pick_surname(used_combos: set, first: str) -> str:
    """Pick a surname, avoiding exact duplicates where possible."""
    available = [s for s in SURNAMES if f"{first} {s}" not in used_combos]
    if not available:
        available = SURNAMES
    surname = random.choice(available)
    used_combos.add(f"{first} {surname}")
    return surname


def generate_npc(population_index: int, used_names: set, used_combos: set) -> dict:
    """Generate a single procedural NPC."""
    gender = random.choice(["male", "female"])
    first = _pick_name(used_names, gender)
    surname = _pick_surname(used_combos, first)
    full_name = f"{first} {surname}"

    # Age distribution weighted toward working-age adults
    age_roll = random.random()
    if age_roll < 0.20:
        age = random.randint(5, 15)  # child
    elif age_roll < 0.30:
        age = random.randint(16, 22)  # young adult
    elif age_roll < 0.65:
        age = random.randint(23, 50)  # adult
    elif age_roll < 0.85:
        age = random.randint(51, 65)  # middle-aged
    else:
        age = random.randint(66, 85)  # elder

    # Occupation based on age
    if age < 12:
        occupation = "child"
    elif age < 18:
        occupation = random.choice(["apprentice", "child"])
    elif age > 70:
        occupation = random.choice(["elder", "homemaker", "retired"])
    else:
        # Weight toward common occupations
        occ_choices = []
        for occ, data in OCCUPATIONS.items():
            if occ not in ("child",):
                occ_choices.extend([occ] * data["count"])
        occupation = random.choice(occ_choices)

    occ_data = OCCUPATIONS.get(occupation, {})
    work_locations = occ_data.get("locations", ["cabin"])
    skills = occ_data.get("skills", [])

    # Personality
    traits = random.sample(PERSONALITY_TRAITS, k=random.randint(2, 4))
    speech = random.choice(SPEECH_PATTERNS)

    # Home
    if age < 18:
        home = random.choice(["cabin", "garden", "forest_edge"])
    else:
        home = random.choice(HOME_LOCATIONS)

    # Description
    descriptions = {
        "forest_ranger": f"A {gender} in a green uniform, weathered by sun and seasons. Knows every trail and every bird call.",
        "logger": f"A strong, quiet {gender} with sawdust in their hair and callused hands. Moves through the forest like they own it.",
        "mushroom_forager": f"A {gender} with a wicker basket and a field guide tucked in their pocket. Knows which mushrooms feed you and which ones kill you.",
        "organic_farmer": f"A sun-weathered {gender} with soil under their nails and a composting system they could talk about for hours.",
        "carpenter": f"A {gender} with careful hands and a tape measure on their belt. Builds things that last.",
        "woodworker": f"A {gender} with shavings on their sleeves and an eye for grain. Makes things beautiful.",
        "herbalist": f"A quiet {gender} who knows the secret uses of every plant. Smells like lavender and something older.",
        "wildlife_biologist": f"A {gender} with binoculars and a notebook. Tracks what moves through the forest.",
        "child": f"A small {gender} with bright eyes and boundless energy. The forest is their playground.",
        "elder": f"A {gender} whose face tells the story of decades in the mountains. Speaks slowly, remembers everything.",
        "apprentice": f"A young {gender} eager to learn, all elbows and enthusiasm. Carries things. Asks questions.",
        "homemaker": f"A capable {gender} who keeps the household running. Knows where everything is.",
        "midwife": f"A calm, knowing {gender} who has brought many into the world. Steady hands. Quiet voice.",
        "brewer": f"A {gender} with a fermentation setup and strong opinions about hops. Always tasting something.",
        "writer": f"A {gender} with a notebook and a distracted look. The forest gives them something to say.",
        "artist": f"A {gender} with paint on their hands and an eye for light. Sees the forest differently.",
        "mechanic": f"A grease-stained {gender} who can fix anything with wire and determination. Knows every engine sound.",
        "hunter": f"A quiet {gender} who moves through the forest like a shadow. Knows the deer trails.",
        "fisher": f"A {gender} with a fly rod and cold-water knowledge. Spends mornings on the creek.",
        "guide": f"A {gender} who knows every switchback and every weather sign. Leads people through the mountains.",
        "teacher": f"A patient {gender} who believes in learning. Makes the complicated simple.",
        "nurse": f"A calm {gender} with steady hands and a warm manner. Knows first aid and then some.",
        "retired": f"A {gender} who has earned their quiet. Reads. Walks. Watches the weather.",
        "volunteer_firefighter": f"A {gender} who runs toward danger when the alarm goes. Knows the forest fire patterns.",
        "naturalist": f"A {gender} who can name every bird by its call and every plant by its leaf.",
        "potter": f"A {gender} with clay under their nails and a wheel in the studio. Makes bowls that feel like home.",
        "weaver": f"A {gender} with a loom and an eye for color. Makes cloth that tells a story.",
        "luthier": f"A {gender} who builds instruments from wood and patience. Each one takes months.",
        "astronomer": f"A {gender} who knows the night sky like a map. Francis is their favorite star.",
        "chef": f"A {gender} who cooks with what the forest provides. Forages. Ferments. Makes magic.",
        "dog_trainer": f"A {gender} with a well-trained border collie and a calm voice. Understands animals.",
        "photographer": f"A {gender} with a camera and an eye for the light through the trees.",
        "yoga_instructor": f"A {gender} who teaches in the clearing. Knows the body. Knows the breath.",
        "therapist": f"A {gender} who listens more than they speak. The forest is part of the practice.",
        "beekeeper": f"A {gender} with a veil and a smoker. Knows every hive and every flower.",
        "cheesemaker": f"A {gender} with a cave and a recipe. Ages things. Waits.",
        "mason": f"A {gender} who works with stone. Builds fireplaces that will outlast the cabin.",
        "blacksmith": f"A {gender} with an anvil and a forge. Makes tools that last generations.",
        "librarian": f"A {gender} who knows every book and every story. Keeps the records.",
        "veterinarian": f"A {gender} who treats the animals in the valley. Calm hands. Kind eyes.",
        "social_worker": f"A {gender} who knows everyone's situation. Helps where they can.",
        "carpenter_apprentice": f"A young {gender} learning the trade. Measures twice. Cuts once.",
        "botanist": f"A {gender} with a press and a field journal. Knows every plant in the forest.",
        "park_ranger": f"A {gender} who patrols the ridgeline. Knows the rules. Enforces them gently.",
        "musician": f"A {gender} with a guitar and a voice that carries through the trees.",
        "poet": f"A {gender} who sees the world in metaphors. Writes by the fire.",
    }

    npc_id = f"npc_{population_index:03d}"

    properties = {
        "age": age,
        "gender": gender,
        "occupation": occupation,
        "personality": ", ".join(traits),
        "speech": speech,
        "description": descriptions.get(occupation, f"A {gender} of the village."),
        "skills": skills,
        "home": home,
        "traits": traits,
        "generated": True,
    }

    return {
        "id": npc_id,
        "name": full_name,
        "home": home,
        "work_locations": work_locations,
        "occupation": occupation,
        "properties": properties,
    }


def generate_npc_schedule(npc: dict, hour: int) -> dict:
    """Generate a schedule entry for an NPC at a given hour."""
    occupation = npc.get("occupation", "")
    props = npc.get("properties", {})
    age = props.get("age", 35)  # default to adult if age not set
    work_locs = npc.get("work_locations", ["cabin"])
    home = npc.get("home", "cabin")

    # Sleep hours
    if hour >= 22 or hour < 6:
        if age < 12 and hour < 7:
            return {"activity": "sleeping", "location_id": home, "description": "Sleeping soundly."}
        if age > 70 and hour < 7:
            return {"activity": "sleeping", "location_id": home, "description": "Sleeping. The old need their rest."}
        return {"activity": "sleeping", "location_id": home, "description": "Sleeping."}

    # Morning routine
    if hour == 6:
        if age < 16:
            return {"activity": "resting", "location_id": home, "description": "Waking slowly."}
        return {"activity": "working", "location_id": home, "description": "Waking. Starting the day."}

    # Work hours (7-17)
    if 7 <= hour < 12:
        if occupation == "child":
            return {"activity": "learning", "location_id": random.choice(["cabin", "garden", "clearing"]), "description": "Learning and playing."}
        if occupation == "elder":
            return {"activity": "socializing", "location_id": random.choice(["cabin", "ridgeline", "clearing"]), "description": "Morning in the clearing."}
        if occupation == "apprentice":
            return {"activity": "learning", "location_id": random.choice(work_locs), "description": "Learning the trade."}
        if occupation in ("writer", "artist", "poet"):
            return {"activity": "working", "location_id": random.choice(work_locs), "description": f"Creating. {occupation} at work."}
        if occupation in ("forest_ranger", "park_ranger"):
            return {"activity": "patrolling", "location_id": random.choice(work_locs), "description": "Patrolling the trails."}
        if occupation in ("logger", "carpenter", "woodworker"):
            return {"activity": "working", "location_id": random.choice(work_locs), "description": f"Working with wood."}
        if occupation in ("mushroom_forager", "herbalist", "botanist", "naturalist"):
            return {"activity": "working", "location_id": random.choice(work_locs), "description": "In the forest. Gathering."}
        if occupation in ("fisher",):
            return {"activity": "working", "location_id": random.choice(work_locs), "description": "Fishing the creek."}
        if occupation in ("hunter",):
            return {"activity": "working", "location_id": random.choice(work_locs), "description": "Hunting in the deep forest."}
        if occupation in ("organic_farmer", "beekeeper"):
            return {"activity": "working", "location_id": random.choice(work_locs), "description": "Tending the garden."}
        if occupation in ("astronomer",):
            return {"activity": "resting", "location_id": random.choice(work_locs), "description": "Sleeping. Works nights."}
        return {"activity": "working", "location_id": random.choice(work_locs), "description": f"Working. {occupation} at work."}

    if 12 <= hour < 14:
        if occupation in ("child", "elder"):
            return {"activity": "eating", "location_id": home, "description": "Lunch at home."}
        return {"activity": "eating", "location_id": random.choice([home, "cabin", "cabin_kitchen"]), "description": "Lunch break."}

    if 14 <= hour < 17:
        if occupation == "child":
            return {"activity": "playing", "location_id": random.choice(["clearing", "mountain_creek", "forest_edge"]), "description": "Playing."}
        if occupation == "elder":
            return {"activity": "resting", "location_id": random.choice(["cabin", "ridgeline", "clearing"]), "description": "Afternoon rest."}
        if occupation in ("writer", "artist", "poet"):
            return {"activity": "working", "location_id": random.choice(work_locs), "description": "Afternoon creating."}
        if occupation in ("forest_ranger", "park_ranger"):
            return {"activity": "patrolling", "location_id": random.choice(work_locs), "description": "Afternoon patrol."}
        if occupation == "astronomer":
            return {"activity": "resting", "location_id": random.choice(work_locs), "description": "Resting before the night watch."}
        return {"activity": "working", "location_id": random.choice(work_locs), "description": "Afternoon work."}

    # Evening (17-21)
    if 17 <= hour < 19:
        if occupation in ("logger", "organic_farmer", "carpenter", "woodworker"):
            return {"activity": "working", "location_id": random.choice(work_locs), "description": "End-of-day tasks."}
        if occupation == "astronomer":
            return {"activity": "working", "location_id": random.choice(work_locs), "description": "Setting up the telescope."}
        return {"activity": "eating", "location_id": home, "description": "Evening meal."}

    if 19 <= hour < 22:
        roll = random.random()
        if occupation == "astronomer":
            return {"activity": "working", "location_id": random.choice(work_locs), "description": "Observing the night sky."}
        if roll < 0.3:
            return {"activity": "socializing", "location_id": random.choice(["cabin", "cabin_deck", "clearing"]), "description": "Evening at the cabin."}
        if roll < 0.5:
            return {"activity": "socializing", "location_id": random.choice(["ridgeline", "clearing"]), "description": "Evening in the clearing."}
        if roll < 0.7 and occupation in ("writer", "poet", "artist"):
            return {"activity": "working", "location_id": home, "description": "Evening creating by firelight."}
        return {"activity": "resting", "location_id": home, "description": "Quiet evening at home."}

    return {"activity": "idle", "location_id": home, "description": "Going about their day."}


def generate_relationships(npc: dict, all_npcs: list) -> list:
    """Generate relationships between NPCs based on proximity and occupation."""
    relationships = []
    npc_id = npc["id"]
    npc_home = npc.get("home", "")
    npc_occ = npc["occupation"]
    npc_work = set(npc.get("work_locations", []))

    # Find candidates for relationships
    candidates = []
    for other in all_npcs:
        if other["id"] == npc_id:
            continue
        score = 0
        # Same home = family or neighbors
        if other.get("home", "") == npc_home:
            score += 3
        # Same workplace
        other_work = set(other.get("work_locations", []))
        if npc_work & other_work:
            score += 2
        # Same occupation
        if other["occupation"] == npc_occ:
            score += 1
        if score > 0:
            candidates.append((other, score))

    # Pick 1-3 relationships
    num_relationships = random.randint(1, 3)
    random.shuffle(candidates)
    for other, score in candidates[:num_relationships]:
        if score >= 3:
            rel_type = random.choice(["family", "close_friend", "neighbor"])
            affinity = random.uniform(0.6, 0.95)
        elif score >= 2:
            rel_type = random.choice(["friend", "coworker", "acquaintance"])
            affinity = random.uniform(0.4, 0.8)
        else:
            rel_type = "acquaintance"
            affinity = random.uniform(0.2, 0.6)

        relationships.append({
            "npc_a": npc_id,
            "npc_b": other["id"],
            "relationship": rel_type,
            "affinity": round(affinity, 2),
            "description": f"{rel_type.replace('_', ' ')}",
        })

    return relationships


def populate_village(db, target_population: int = 200) -> int:
    """
    Generate procedural NPCs to reach the target population.
    Returns the number of NPCs generated.
    """
    # Count existing NPCs
    existing = db.execute("SELECT COUNT(*) as cnt FROM agents WHERE type = 'npc'").fetchone()[0]
    to_generate = max(0, target_population - existing)

    if to_generate == 0:
        return 0

    used_names = set()
    used_combos = set()

    # Load existing NPC names to avoid duplicates
    existing_npcs = db.execute("SELECT name FROM agents WHERE type = 'npc'").fetchall()
    for row in existing_npcs:
        parts = row[0].split()
        if parts:
            used_names.add(parts[0])
        used_combos.add(row[0])

    # Generate NPCs
    all_new_npcs = []
    for i in range(to_generate):
        idx = existing + i + 1
        npc = generate_npc(idx, used_names, used_combos)
        all_new_npcs.append(npc)

    # Insert NPCs
    now = time.time()
    for npc in all_new_npcs:
        db.execute("""
            INSERT OR IGNORE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
            VALUES (?, ?, 'npc', ?, 'active', ?, ?, ?)
        """, (npc["id"], npc["name"], npc["work_locations"][0],
              json.dumps(npc["properties"]), now, now))

    # Generate schedules (every 2 hours to keep it manageable)
    for npc in all_new_npcs:
        for hour in range(0, 24, 2):
            sched = generate_npc_schedule(npc, hour)
            db.execute("""
                INSERT OR IGNORE INTO npc_schedules (npc_id, hour, activity, location_id, description)
                VALUES (?, ?, ?, ?, ?)
            """, (npc["id"], hour, sched["activity"], sched["location_id"], sched["description"]))

    # Generate relationships
    all_npcs = []
    for row in db.execute("SELECT id, name, properties FROM agents WHERE type = 'npc'").fetchall():
        props = json.loads(row[2]) if row[2] else {}
        occ = props.get("occupation", "")
        # Get work locations from OCCUPATIONS if available, otherwise use home
        work_locs = OCCUPATIONS.get(occ, {}).get("locations", [props.get("home", "cabin")])
        all_npcs.append({
            "id": row[0],
            "name": row[1],
            "occupation": occ,
            "home": props.get("home", "cabin"),
            "work_locations": work_locs,
            "properties": props,
        })

    relationship_count = 0
    for npc in all_npcs:
        rels = generate_relationships(npc, all_npcs)
        for rel in rels:
            # Avoid duplicate relationships
            existing = db.execute(
                "SELECT COUNT(*) as cnt FROM npc_relationships WHERE (npc_a = ? AND npc_b = ?) OR (npc_a = ? AND npc_b = ?)",
                (rel["npc_a"], rel["npc_b"], rel["npc_b"], rel["npc_a"])
            ).fetchone()[0]
            if existing == 0:
                db.execute("""
                    INSERT INTO npc_relationships (npc_a, npc_b, relationship, affinity, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (rel["npc_a"], rel["npc_b"], rel["relationship"], rel["affinity"], rel["description"]))
                relationship_count += 1

    db.commit()
    return to_generate
