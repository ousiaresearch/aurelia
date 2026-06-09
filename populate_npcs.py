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
NPC_COUNT = 12000  # was 120 — Phase 5 scaling

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

# ── Combinatorial Name Generation ─────────────────────────────────────
# Syllable pools × type-appropriate pairing = ~100K+ unique names per type

_HUMAN_SYL = [
    "Ar", "Ka", "No", "Ze", "Ly", "Or", "Ve", "Ru", "Ta", "So",
    "Em", "Ash", "Ter", "Lu", "Vae", "Ny", "Se", "Mi", "Tha", "Jo",
    "Kes", "Pax", "Si", "Za", "Iv", "Ek", "Zin", "Fa", "Qui", "Re",
    "Ga", "Ha", "Tes", "Dex", "Ne", "Fen", "Orl", "Br", "Sa", "Ven",
    "Ro", "Cle", "Fli", "In", "Jun", "Lio", "Me", "Na", "Ore", "Pet",
    "Rai", "Su", "Teo", "Um", "Vos", "Wy", "Xe", "Cy", "Zel", "Tor",
    "Val", "Mar", "Del", "Fae",
]
_HUMAN_SURFIX = [
    "crest", "vale", "mere", "fall", "shire", "haven", "gard", "well",
    "wood", "forge", "mark", "watch", "holm", "rest", "reach", "hold",
    "spire", "brook", "field", "stone", "moor", "grave", "coast", "pool",
    "gate", "march", "glen", "crag", "dell", "keep",
]

_THREN_SYL = [
    "Brev", "Ael", "Thes", "Mir", "Lior", "Yves", "Sael", "Orith",
    "Nav", "Cael", "Sor", "Eir", "Luth", "Vael", "Anar", "Ithil",
    "Sel", "Faye", "Rev", "Ver", "Isol", "Briel", "Aur", "Sylv",
    "Dahl", "Lum", "Cer", "Vesp", "Sol", "Elow", "Aeth", "Ser",
    "Thal", "Maev", "Oria", "Nys", "Wren", "Mel", "Cal", "Fior",
]
_THREN_SURFIX = [
    "bloom", "weave", "dew", "heart", "tide", "hollow", "wind",
    "petal", "star", "rain", "fern", "willow", "root", "silk",
    "dawn", "leaf", "thorn", "sage", "vine", "mist", "pearl",
    "nacre", "grove", "shade", "briar", "brook", "glade", "whisper",
]

_VORN_SYL = [
    "Krag", "Torq", "Vex", "Drav", "Irn", "Kolt", "Graith",
    "Bol", "Riv", "Stern", "Korv", "Grind", "Pist", "Tungs",
    "Ax", "Forg", "Temp", "Ratch", "Clank", "Rust", "Burn",
    "Diez", "Grom", "Harr", "Junk", "Kov", "Lux", "Mal",
    "Nick", "Ox", "Plat", "Quar", "Rivv", "Sold", "Trun",
    "Cruc", "Weld", "Slag", "Vice", "Zinc", "Cop", "Braz",
]
_VORN_SURFIX = [
    "vale", "crest", "born", "wright", "fall", "stream", "side",
    "forge", "vein", "stone", "plate", "shaft", "switch", "chain",
    "bolt", "press", "well", "song", "heap", "mark", "grip",
    "peen", "point", "fall", "bed", "cast", "torch", "drift",
]

GLIM_PREFIXES = ["GL", "GM", "GW", "DR", "SV", "DL", "MN", "RP", "TK",
                 "BR", "CX", "FQ", "HN", "JS", "KV", "LM", "NP", "QR", "ST"]


def _combo_name(syl_pool, surfix_pool, max_syls=2):
    """Generate a unique name by combining syllables + surfix."""
    count = random.randint(1, max_syls)
    chosen = [random.choice(syl_pool) for _ in range(count)]
    base = "".join(chosen).capitalize()
    suffix = random.choice(surfix_pool)
    return f"{base} {suffix.capitalize()}"


# Track generated names to avoid collisions at scale
_used_names: set = set()


def pick_name(npc_type):
    """Generate a unique name appropriate to the NPC type."""
    for _ in range(100):  # retry loop for uniqueness
        if npc_type == "thren":
            name = _combo_name(_THREN_SYL, _THREN_SURFIX)
        elif npc_type == "vorn":
            name = _combo_name(_VORN_SYL, _VORN_SURFIX)
        elif npc_type == "glim":
            prefix = random.choice(GLIM_PREFIXES)
            num = random.randint(10, 9999)
            suffix = random.choice(["", "", "", "-A", "-B", "-R", "-X", "-K"])
            name = f"{prefix}-{num}{suffix}"
        else:
            name = _combo_name(_HUMAN_SYL, _HUMAN_SURFIX)
        if name not in _used_names:
            _used_names.add(name)
            return name
    # Fallback: force unique with counter
    base = f"{npc_type}-{len(_used_names)}"
    _used_names.add(base)
    return base


# ── Type-aware occupation matrix ──────────────────────────────────────
TYPE_OCCUPATIONS = {
    "thren": [
        "biofuel_chemist", "reef_cultivator", "filtration_tech", "biosynth_researcher",
        "herbalist", "solar_botanist", "water_ecologist", "genetic_weaver",
        "marsh_archivist", "kelp_farmer", "algae_engineer", "floating_gardener",
        "microbiome_analyst", "pollinator_keeper", "wetland_cartographer",
    ],
    "vorn": [
        "forge_operator", "metal_smith", "sand_glass_engineer", "drone_station_op",
        "geothermal_tech", "deep_miner", "autonomous_factory_supervisor", "circuit_weaver",
        "turbine_mechanic", "structural_welder", "alloy_chemist", "crane_controller",
        "pipeline_inspector", "heavy_hauler", "subterranean_surveyor",
    ],
    "glim": [
        "solar_panel_cleaner", "kelp_harvester", "salvage_sort", "warehouse_loader",
        "drone_courier", "street_sweeper", "assembly_line_worker", "cargo_scanner",
        "maintenance_runner", "delivery_unit", "survey_drone", "rubble_clearer",
    ],
    "human": [
        "bureaucrat", "merchant", "teacher", "medic", "guide", "trader",
        "council_clerk", "dock_worker", "market_vendor", "innkeeper",
        "courier", "guard", "architect", "diplomat", "artist",
        "cook", "fisher", "weaver", "scribe", "carpenter",
    ],
}

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
    # Use type-aware occupations when available, fall back to config list
    fallback_occs = cfg.get("npc_occupations", ["citizen"])
    country_name = cfg.get("name", "Aurelia")
    weights = TYPE_WEIGHTS.get(country_id, [0.25, 0.25, 0.25, 0.25])

    type_counts = {"thren": 0, "vorn": 0, "glim": 0, "human": 0}
    created = 0
    for i in range(needed):
        npc_id = f"npc_{country_id}_{created:05d}"  # 5-digit padding for 12k
        npc_type = random.choices(NPC_TYPES, weights=weights, k=1)[0]
        name = pick_name(npc_type)
        occ_pool = TYPE_OCCUPATIONS.get(npc_type, fallback_occs)
        occupation = random.choice(occ_pool)
        loc = random.choice(locations) if locations else "unknown"

        if i > 0 and i % 2000 == 0:
            print(f"  ... {i}/{needed} NPCs created")
            db.commit()  # commit every 2k to keep memory low

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
