#!/usr/bin/env python3
"""
populate_npcs.py — Create 120 NPCs per Aurelian country-state.
Each NPC is typed as Thren, Vorn, Glim, or human.
Distribution reflects each country's character.
"""

import sqlite3, json, random, time, yaml, os
from pathlib import Path

AURELIA_ROOT = Path("/Users/johann/aurelia")
AGENTS_HOME = Path("/Users/johann/.hermes/agents")
NPC_COUNT = 120

# ── NPC Type Taxonomy (Scheme C — original coinages) ──────────────────
# Thren: bio-synthetic sentients. Organic, breathing, belonging in ecology.
# Vorn:  mechanical sentients. Gears, forges, hard consonants.
# Glim:  non-sentient drones. Quick, mindless, ambient workers.
# human: regular humans.

NPC_TYPES = ["thren", "vorn", "glim", "human"]

# Type distribution weights per country (thren, vorn, glim, human)
TYPE_WEIGHTS = {
    "solara":   [0.35, 0.10, 0.15, 0.40],  # Thren research capital — bio-heavy
    "arkos":    [0.10, 0.35, 0.20, 0.35],  # Desert arcology — Vorn industry
    "valdris":  [0.10, 0.30, 0.15, 0.45],  # Canyon mines — Vorn + humans
    "mirithane":[0.35, 0.10, 0.10, 0.45],  # Wetlands — Thren ecology
    "verge":    [0.20, 0.20, 0.20, 0.40],  # Melting pot — even mix
}

# ── Name pools ────────────────────────────────────────────────────────

# Human names — warm, Aurelian feel
HUMAN_GIVEN = [
    "Aria", "Kai", "Nova", "Zephyr", "Lyra", "Orion", "Vega", "Rune",
    "Talis", "Soren", "Ember", "Ash", "Terra", "Sol", "Lumen", "Vael", "Nyx",
    "Orin", "Seren", "Mira", "Thane", "Jora", "Kest", "Pax", "Ren", "Silas",
    "Zara", "Ivo", "Eko", "Zin", "Fane", "Quill", "Reva", "Gale", "Haze",
    "Tess", "Dex", "Neri", "Fenn", "Orla", "Bram", "Sage", "Venn", "Rook",
    "Cleo", "Flint", "Indra", "Jun", "Kael", "Lior", "Merit", "Nadia",
    "Oren", "Petra", "Rei", "Sula", "Teo", "Umi", "Voss", "Wynn", "Xen",
]
HUMAN_SURNAMES = [
    "Solaris", "Ventris", "Aurelian", "Terraforge", "Glassweaver", "Redshore",
    "Skyborn", "Ashvalley", "Suntear", "Stormveil", "Ironbend", "Nightwhisper",
    "Flintedge", "Brooksong", "Reedwalker", "Cloudrest", "Saltvein", "Dunefall",
    "Brightwater", "Frostmere", "Thornwood", "Misthollow", "Starcradle",
    "Ridgecrest", "Deepwell", "Embercoast", "Mossgrave", "Tidepool",
    "Windhaven", "Glassmere", "Sandspine", "Cragfern", "Sunshadow",
]

# Thren names — soft, breathy, organic
THREN_GIVEN = [
    "Breva", "Aelis", "Thessaly", "Mirael", "Liora", "Yves", "Sael",
    "Orith", "Navine", "Caelum", "Sorrel", "Eirian", "Luthien", "Vaela",
    "Anara", "Ithil", "Selune", "Faye", "Reverie", "Thessia", "Verdis",
    "Isolde", "Brielle", "Aurene", "Sylva", "Dahlia", "Lumine", "Ariael",
    "Cerule", "Vesper", "Solenne", "Elowen", "Miravel", "Aether", "Serein",
]
THREN_SURNAMES = [
    "Bloomweave", "Dewfall", "Reedheart", "Tideborn", "Greenhollow",
    "Mosswind", "Petalgrave", "Starbloom", "Rainveil", "Fernhallow",
    "Willowmere", "Softroot", "Silkstream", "Dawnrift", "Leafwhisper",
    "Thornberry", "Sagewater", "Vinecrest", "Pearldrop", "Mistgarden",
]

# Vorn names — hard consonants, mechanical resonance
VORN_GIVEN = [
    "Kragg", "Torq", "Vexis", "Draven", "Ironn", "Kolt", "Graith",
    "Bolvar", "Rivet", "Stern", "Korvax", "Grindel", "Piston", "Tungsten",
    "Axel", "Forge", "Temper", "Ratchet", "Clank", "Rust", "Burnish",
    "Diezel", "Grommet", "Harrow", "Junker", "Kovak", "Luxite", "Mallek",
    "Nicket", "Oxide", "Platin", "Quartz", "Rivvik", "Solder", "Trunion",
]
VORN_SURNAMES = [
    "Ironvale", "Steelcrest", "Anvilborn", "Gearwright", "Hammerfall",
    "Voltstream", "Burnside", "Castforge", "Deepvein", "Foundry",
    "Grindstone", "Hotplate", "Jackshaft", "Killswitch", "Linkchain",
    "Mountbolt", "Nickelback", "Overpress", "Pulverise", "Quenchwell",
    "Rivetsong", "Slagheap", "Torchborn", "Underplate", "Vicegrip",
    "Weldmark", "Crosspeen", "Yieldpoint", "Zincfall", "Crucible",
]

# Glim names — designation-style, short, quick
GLIM_PREFIXES = ["GL", "GM", "GW", "DR", "SV", "DL", "MN", "RP", "TK", "BR"]
GLIM_DESIGNATIONS = [
    f"{random.choice(GLIM_PREFIXES)}-{random.randint(100,999)}"
    for _ in range(120)
]  # Generate a pool; we'll pick from it

def glim_name():
    """Glim names are functional designations."""
    prefix = random.choice(GLIM_PREFIXES)
    num = random.randint(10, 999)
    suffix = random.choice(["", "", "", "-A", "-B", "-R", "-X"])
    return f"{prefix}-{num}{suffix}"

# ── Personality & trait pools ─────────────────────────────────────────

PERSONALITIES = [
    "cautious observer", "relentless optimist", "quiet builder", "fierce negotiator",
    "gentle teacher", "wary veteran", "brilliant eccentric", "patient mediator",
    "restless explorer", "devoted caretaker", "sharp pragmatist", "dreamy idealist",
    "stoic worker", "passionate artist", "calculating strategist", "warm connector",
]
INTERESTS = [
    "solar engineering", "botany", "currency theory", "thren rights",
    "old-world history", "crystal carving", "trade negotiation", "bio-synthesis",
    "desert navigation", "weaving", "circuit design", "water purification",
    "mountain geology", "bird migration", "salvage archaeology", "storytelling",
    "airship mechanics", "geothermal mapping", "herb cultivation", "metal sculpture",
    "data archiving", "musical performance", "kelp farming", "drone piloting",
    "vorn collective bargaining", "glim fleet optimization", "cross-type diplomacy",
]
VALUES = [
    "autonomy above all", "community first", "knowledge is currency",
    "the land remembers", "precision in all things", "kindness costs nothing",
    "prove yourself daily", "beauty sustains", "trust is earned",
    "water is sacred", "energy never lies", "leave no trace",
    "repair not replace", "silence is wisdom", "action over words",
]
MOODS = ["content", "restless", "focused", "wary", "hopeful", "melancholic", "determined", "curious"]

# ── Bio templates by type ─────────────────────────────────────────────
def make_bio(npc_type, occupation, country_name):
    occ = occupation.replace("_", " ")
    if npc_type == "thren":
        return random.choice([
            f"A {occ} in {country_name}. Thren — bio-synthetic, woven into the ecology of the land.",
            f"Thren {occ}. Chose the organic path. Belongs to {country_name} the way roots belong to soil.",
            f"Bio-synthetic {occ} in {country_name}. Thren through and through — breathing, growing, belonging.",
        ])
    elif npc_type == "vorn":
        return random.choice([
            f"A {occ} in {country_name}. Vorn — mechanical sentience, forged with intent.",
            f"Vorn {occ}. Metal and purpose. The hum of gears is their heartbeat in {country_name}.",
            f"Mechanical sentient working as {occ} in {country_name}. Vorn — built to last, built to serve themselves.",
        ])
    elif npc_type == "glim":
        return random.choice([
            f"Glim unit assigned to {occ} duty in {country_name}. Non-sentient. Efficient.",
            f"Autonomous drone — {occ} operations. Glim designation. No inner life, just function.",
            f"Glim fleet unit. {occ} tasking. Runs on schedule. Does not dream.",
        ])
    else:
        return random.choice([
            f"A human {occ} living in {country_name}.",
            f"Citizen of {country_name}. Works as {occ}. Human — organic, mortal, stubborn.",
            f"Human {occ}. Born in {country_name}, plans to stay.",
        ])

def load_config(country_id):
    path = AURELIA_ROOT / "configs" / f"{country_id}.yaml"
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f)
    return None

def pick_name(npc_type):
    """Generate a name appropriate to the NPC type."""
    if npc_type == "thren":
        return f"{random.choice(THREN_GIVEN)} {random.choice(THREN_SURNAMES)}"
    elif npc_type == "vorn":
        return f"{random.choice(VORN_GIVEN)} {random.choice(VORN_SURNAMES)}"
    elif npc_type == "glim":
        return glim_name()
    else:
        return f"{random.choice(HUMAN_GIVEN)} {random.choice(HUMAN_SURNAMES)}"

def populate_country(country_id):
    cfg = load_config(country_id)
    if not cfg:
        print(f"  No config for {country_id}")
        return 0

    db_path = AGENTS_HOME / country_id / "aurelia-world" / "world" / "world.db"
    if not db_path.exists():
        print(f"  No database for {country_id}")
        return 0

    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    now = time.time()

    # Check existing NPC count
    existing = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc'").fetchone()[0]
    needed = NPC_COUNT - existing
    if needed <= 0:
        print(f"  {country_id}: Already has {existing} NPCs, skipping")
        db.close()
        return 0

    # Get locations and occupations
    locations = [r["id"] for r in db.execute("SELECT id FROM locations").fetchall()]
    occupations = cfg.get("npc_occupations", ["citizen"])
    country_name = cfg.get("name", "Aurelia")
    weights = TYPE_WEIGHTS.get(country_id, [0.25, 0.25, 0.25, 0.25])

    type_counts = {"thren": 0, "vorn": 0, "glim": 0, "human": 0}
    created = 0
    for i in range(needed):
        npc_id = f"npc_{country_id}_{created:04d}"
        npc_type = random.choices(NPC_TYPES, weights=weights, k=1)[0]
        name = pick_name(npc_type)
        occupation = random.choice(occupations)
        loc = random.choice(locations) if locations else "unknown"

        # Glims have simpler personality profiles
        if npc_type == "glim":
            properties = json.dumps({
                "npc_type": npc_type,
                "occupation": occupation,
                "personality": "task-focused",
                "interests": [random.choice(["maintenance", "logistics", "assembly", "survey"])],
                "values": ["efficiency"],
                "mood": "neutral",
                "bio": make_bio(npc_type, occupation, country_name),
                "traits": {
                    "talkativeness": round(random.uniform(0.0, 0.2), 2),
                    "curiosity": 0.0,
                    "industriousness": round(random.uniform(0.8, 1.0), 2),
                    "sociability": 0.0,
                    "stubbornness": 0.0,
                }
            })
        else:
            properties = json.dumps({
                "npc_type": npc_type,
                "occupation": occupation,
                "personality": random.choice(PERSONALITIES),
                "interests": random.sample(INTERESTS, min(3, len(INTERESTS))),
                "values": random.sample(VALUES, min(2, len(VALUES))),
                "mood": random.choice(MOODS),
                "bio": make_bio(npc_type, occupation, country_name),
                "traits": {
                    "talkativeness": round(random.uniform(0.2, 0.9), 2),
                    "curiosity": round(random.uniform(0.2, 0.9), 2),
                    "industriousness": round(random.uniform(0.3, 0.9), 2),
                    "sociability": round(random.uniform(0.2, 0.9), 2),
                    "stubbornness": round(random.uniform(0.1, 0.8), 2),
                }
            })

        db.execute("""
            INSERT INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
            VALUES (?, ?, 'npc', ?, 'active', ?, ?, ?)
        """, (npc_id, name, loc, properties, now, now))

        type_counts[npc_type] += 1
        created += 1

    db.commit()

    # Verify
    total = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc'").fetchone()[0]
    tc = " / ".join(f"{t}:{c}" for t, c in type_counts.items() if c > 0)
    print(f"  {country_id}: Created {created} NPCs → total {total} [{tc}]")

    db.close()
    return created

# ── Main ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    countries = ["solara", "valdris", "mirithane", "arkos", "verge"]
    total = 0
    print("Populating Aurelian country-states (Thren / Vorn / Glim / Human)...")
    print()
    for c in countries:
        n = populate_country(c)
        total += n
    print(f"\nTotal NPCs created: {total}")
