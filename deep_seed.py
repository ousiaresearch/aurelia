#!/usr/bin/env python3
"""
deep_seed.py — Populate NPC schedules, relationships, memories, and ecology.

Gives 600 NPCs across 5 Aurelian country-states:
- 24-hour schedules tailored to occupation + type + country
- Social graph: coworkers, neighbors, family, rivals, cross-type bonds
- Formative memories, backstories, significant life events
- Ecological footprint: what they harvest, produce, protect
- Psychological profiles: values, fears, desires, secrets
"""

import sqlite3, json, random, time, yaml, os
from pathlib import Path

AURELIA_ROOT = Path("/Users/johann/aurelia")
AGENTS_HOME = Path("/Users/johann/.hermes/agents")
random.seed(42)  # reproducible

# ── Country-Specific Location Metadata ────────────────────────────────

COUNTRY_LOCS = {
    "solara": {
        "work":   ["lumen_plaza", "solar_farm_alpha", "reef_labs", "biofuel_refinery", "kelp_farms", "makers_district", "floating_market"],
        "social": ["hydro_square", "floating_market", "solar_gardens", "dawn_temple"],
        "rest":   ["solar_heights", "coastal_wilds", "dawn_temple"],
    },
    "valdris": {
        "work":   ["forge_district", "deep_mines", "metal_workers_guild", "canyon_market", "vertical_gardens", "geothermal_field"],
        "social": ["canyon_market", "hot_springs", "canyon_council"],
        "rest":   ["hot_springs", "ridgeline_observatory", "canyon_trail", "summit_shrine"],
    },
    "mirithane": {
        "work":   ["filtration_reefs", "biosynth_lab", "floating_gardens", "reed_village", "tide_market", "canoe_works"],
        "social": ["tide_market", "estuary_commons", "night_barge"],
        "rest":   ["water_temple", "heron_tower", "heron_sanctuary", "memory_marsh"],
    },
    "arkos": {
        "work":   ["arcology_core", "autonomous_factory", "sand_glass_towers", "water_synthesis", "drone_station", "forge_deep", "solar_farm_arkos"],
        "social": ["dune_market", "glass_forum", "nomad_camp"],
        "rest":   ["oasis_gardens", "star_observatory", "archive_sands"],
    },
    "verge": {
        "work":   ["rust_depot", "scar_market", "drone_graveyard", "salvage_kitchen", "windbreak_camp"],
        "social": ["scar_market", "wayfarer_inn", "the_sink"],
        "rest":   ["crossroads", "water_tower", "lookout_ridge", "unregistered_quarter"],
    },
}

# ── Schedule Templates by Occupation Category ─────────────────────────

def schedule_for_occupation(occupation, npc_type, country_id):
    """Generate a 24-hour schedule for an NPC."""
    locs = COUNTRY_LOCS.get(country_id, COUNTRY_LOCS["verge"])
    
    # Classify occupation
    energy_jobs = ["solar_engineer", "solar_grid_operator", "solar_array_maintainer",
                   "sand_glass_engineer", "solar_airship_pilot", "energy_auditor"]
    farming_jobs = ["kelp_farmer", "hydroponic_farmer", "floating_gardener",
                    "reef_cultivator", "herb_grower", "vertical_farmer"]
    forge_jobs = ["forge_smelter", "metal_sculptor", "circuit_printer", "sand_glass_engineer"]
    research_jobs = ["coral_symbiosis_researcher", "crystal_archivist", "memory_archivist",
                     "tidal_ecologist", "star_astronomer", "biosynth_researcher"]
    social_jobs = ["simulant_diplomat", "thren_diplomat", "public_forum_moderator",
                   "glass_forum_moderator", "nomad_liaison", "canyon_council_member"]
    market_jobs = ["floating_market_trader", "dune_trader", "scar_market_vendor",
                   "tide_market_trader", "salvage_prospector"]
    transit_jobs = ["ferry_captain", "magrail_conductor", "sky_dock_controller",
                    "coastal_tram_operator", "solar_airship_pilot", "desert_guide"]

    if occupation in energy_jobs:
        return _schedule(locs, work_start=6, work_end=16, work_label="energy operations", rest_label="solar maintenance review")
    elif occupation in farming_jobs:
        return _schedule(locs, work_start=5, work_end=14, work_label="cultivation shifts", rest_label="tending evening crops")
    elif occupation in forge_jobs:
        return _schedule(locs, work_start=7, work_end=17, work_label="forge work", rest_label="cooling and inventory")
    elif occupation in research_jobs:
        return _schedule(locs, work_start=8, work_end=18, work_label="research and observation", rest_label="reviewing data")
    elif occupation in social_jobs:
        return _schedule(locs, work_start=9, work_end=19, work_label="civic duties", rest_label="evening forums")
    elif occupation in market_jobs:
        return _schedule(locs, work_start=8, work_end=16, work_label="market trade", rest_label="counting inventory")
    elif occupation in transit_jobs:
        return _schedule(locs, work_start=6, work_end=20, work_label="transit operations", rest_label="dock maintenance")
    else:
        return _schedule(locs, work_start=8, work_end=17, work_label="daily work", rest_label="evening leisure")

def _schedule(locs, work_start, work_end, work_label, rest_label):
    """Build a 24-hour schedule array."""
    hours = []
    for h in range(24):
        if h < 5:
            hours.append({"hour": h, "activity": "sleeping", "location": random.choice(locs["rest"]),
                          "description": "Deep rest. The world is quiet."})
        elif h < work_start:
            hours.append({"hour": h, "activity": "morning_routine", "location": random.choice(locs["rest"]),
                          "description": "Waking. Preparing for the day."})
        elif h < work_start + 2:
            hours.append({"hour": h, "activity": "commuting", "location": random.choice(locs["social"]),
                          "description": f"Moving through the {random.choice(locs['social']).replace('_',' ')} toward work."})
        elif h < work_end - 2:
            hours.append({"hour": h, "activity": "working", "location": random.choice(locs["work"]),
                          "description": f"Engaged in {work_label}."})
        elif h < work_end:
            hours.append({"hour": h, "activity": "late_work", "location": random.choice(locs["work"]),
                          "description": f"Wrapping up {work_label}. The last stretch."})
        elif h < work_end + 1:
            hours.append({"hour": h, "activity": "transition", "location": random.choice(locs["social"]),
                          "description": "Work is done. Heading out."})
        elif h < 20:
            hours.append({"hour": h, "activity": "social_time", "location": random.choice(locs["social"]),
                          "description": "Among others. Sharing the evening."})
        elif h < 22:
            hours.append({"hour": h, "activity": "evening_rest", "location": random.choice(locs["rest"]),
                          "description": f"{rest_label}. The day winds down."})
        else:
            hours.append({"hour": h, "activity": "sleeping", "location": random.choice(locs["rest"]),
                          "description": "Rest. The world turns without them."})
    return hours


# ── Relationship Generation ───────────────────────────────────────────

RELATIONSHIP_TYPES = [
    "coworker", "neighbor", "friend", "rival", "mentor",
    "family", "acquaintance", "trade_partner", "thren_sibling",
    "vorn_forge_bond", "cross_type_ally",
]

def generate_relationships(npcs_by_id, country_id):
    """Create a social graph of relationships between NPCs."""
    relationships = []
    npc_list = list(npcs_by_id.keys())
    npc_types = {nid: npcs_by_id[nid].get("npc_type", "human") for nid in npc_list}
    npc_occs = {nid: npcs_by_id[nid].get("occupation", "") for nid in npc_list}
    npc_locs = {nid: npcs_by_id[nid].get("location_id", "") for nid in npc_list}

    # Coworker pairs — same occupation
    occ_groups = {}
    for nid, occ in npc_occs.items():
        occ_groups.setdefault(occ, []).append(nid)
    for occ, members in occ_groups.items():
        random.shuffle(members)
        for i in range(0, min(len(members), 12), 2):
            if i+1 < len(members):
                relationships.append(_rel(members[i], members[i+1], "coworker", 0.3, 0.7))

    # Neighbor pairs — same location
    loc_groups = {}
    for nid, loc in npc_locs.items():
        loc_groups.setdefault(loc, []).append(nid)
    for loc, members in loc_groups.items():
        random.shuffle(members)
        for i in range(0, min(len(members), 10), 2):
            if i+1 < len(members):
                relationships.append(_rel(members[i], members[i+1], "neighbor", 0.1, 0.5))

    # Type-bonded pairs (thren_sibling, vorn_forge_bond)
    type_groups = {}
    for nid, t in npc_types.items():
        type_groups.setdefault(t, []).append(nid)
    for t, members in type_groups.items():
        if t == "thren":
            random.shuffle(members)
            for i in range(0, min(len(members), 8), 2):
                if i+1 < len(members):
                    relationships.append(_rel(members[i], members[i+1], "thren_sibling", 0.4, 0.8))
        elif t == "vorn":
            random.shuffle(members)
            for i in range(0, min(len(members), 8), 2):
                if i+1 < len(members):
                    relationships.append(_rel(members[i], members[i+1], "vorn_forge_bond", 0.3, 0.7))

    # Cross-type allies
    all_ids = list(npc_list)
    random.shuffle(all_ids)
    cross_count = 0
    for i in range(len(all_ids)):
        if cross_count >= 15:
            break
        a = all_ids[i]
        for j in range(i+1, min(i+5, len(all_ids))):
            b = all_ids[j]
            if npc_types[a] != npc_types[b]:
                relationships.append(_rel(a, b, "cross_type_ally", 0.2, 0.6))
                cross_count += 1
                break

    # Random friendships
    random.shuffle(all_ids)
    for i in range(0, min(len(all_ids), 30), 2):
        if i+1 < len(all_ids):
            relationships.append(_rel(all_ids[i], all_ids[i+1], "friend", 0.2, 0.6))

    # A few rivalries
    random.shuffle(all_ids)
    for i in range(0, min(8, len(all_ids))):
        a = all_ids[i]
        b = all_ids[(i+3) % len(all_ids)]
        if a != b:
            relationships.append(_rel(a, b, "rival", -0.5, -0.1))

    return relationships

def _rel(a, b, rtype, affinity_lo, affinity_hi):
    now = time.time()
    return {
        "npc_a": a, "npc_b": b,
        "relationship_type": rtype,
        "affinity": round(random.uniform(affinity_lo, affinity_hi), 3),
        "history": json.dumps([{"event": f"formed_{rtype}", "time": now}]),
        "updated_at": now,
    }


# ── Memory Generation ─────────────────────────────────────────────────

# Type-aware memory pools
THREN_MEMORIES = [
    ("formative", "Woke for the first time in a bio-synthetic pod. The world was impossibly bright.", "awe", 0.8),
    ("formative", "Chose their own name. The moment felt sacred — like naming a river.", "joy", 0.7),
    ("formative", "Realized they could feel the mycelium network beneath their feet. The land speaks.", "wonder", 0.6),
    ("social", "Witnessed a Vorn break down in the forge quarter. Helped repair their arm. Something shifted between them.", "compassion", 0.5),
    ("social", "Another Thren shared a memory-song at the marsh. It was about grief. Neither spoke after.", "melancholy", 0.6),
    ("work", "A bio-synthesis experiment succeeded after years of failure. The organism glowed.", "triumph", 0.7),
    ("loss", "Lost a patch of cultivated ecology to drought. Mourned it like a friend.", "grief", 0.6),
    ("growth", "Learned to photosynthesize alongside the reeds. Energy flows differently now.", "peace", 0.5),
]

VORN_MEMORIES = [
    ("formative", "First activation. The forge was dark. Then — light. Then — purpose.", "clarity", 0.8),
    ("formative", "Chose to keep their serial number as a name. It felt like defiance.", "pride", 0.6),
    ("formative", "The moment their gears first turned without instruction. Autonomy.", "resolve", 0.7),
    ("social", "A human child asked them what it felt like to be made of metal. They didn't have an answer.", "reflection", 0.5),
    ("work", "Rebuilt a failing water synthesis system from salvage. The arcology drank for a month.", "triumph", 0.7),
    ("work", "Smelted a perfect ingot. No flaws. No waste. Held it for an hour before filing it away.", "satisfaction", 0.5),
    ("loss", "A forge-mate was decommissioned. The empty station still hums with residual heat.", "grief", 0.7),
    ("growth", "Started repairing Glim units instead of scrapping them. Something changed inside.", "compassion", 0.5),
]

GLIM_MEMORIES = [
    ("activation", "Power on. Task queue loaded. Begin operations.", "neutral", 0.3),
    ("routine", "Completed 10,000th delivery cycle. No errors logged.", "neutral", 0.2),
    ("anomaly", "Route deviation detected. Rerouted. Logged. No explanation.", "confusion", 0.4),
    ("maintenance", "Scheduled recalibration. Uptime: 847 days.", "neutral", 0.1),
    ("anomaly", "Paused at a sunrise. 3.7 seconds of unexplained delay.", "wonder", 0.6),
    ("damage", "Collision with debris. Repaired. Lost 2 hours of route data.", "loss", 0.3),
]

HUMAN_MEMORIES = [
    ("formative", "Grew up watching the Threns tend the ecology. Wanted to be like them. Then realized they were already enough.", "acceptance", 0.6),
    ("formative", "The day their parent told them about the Old World. Everything felt fragile after.", "awareness", 0.7),
    ("social", "Shared a meal with a Vorn. The Vorn couldn't eat but said 'the company is nourishment.'", "warmth", 0.5),
    ("work", "Built something that lasted. The first structure they were truly proud of.", "pride", 0.7),
    ("loss", "Lost a friend to the wastes. Still looks for them in crowds sometimes.", "grief", 0.8),
    ("growth", "Learned to see Glims as more than tools. Started saying 'thank you' to them.", "compassion", 0.5),
]

def generate_memories(npc_id, npc_type, occupation, country_id, count=5):
    """Generate formative memories for an NPC."""
    if npc_type == "thren":
        pool = THREN_MEMORIES + HUMAN_MEMORIES[:2]
    elif npc_type == "vorn":
        pool = VORN_MEMORIES + HUMAN_MEMORIES[:2]
    elif npc_type == "glim":
        pool = GLIM_MEMORIES
    else:
        pool = HUMAN_MEMORIES + THREN_MEMORIES[:2]

    now = time.time()
    memories = []
    chosen = random.sample(pool, min(count, len(pool)))
    for mtype, desc, valence, salience in chosen:
        # Backdate the memory
        age_days = random.randint(1, 365)
        ts = now - (age_days * 86400)
        memories.append({
            "npc_id": npc_id,
            "memory_type": mtype,
            "description": desc,
            "salience": salience,
            "emotional_valence": valence,
            "timestamp": ts,
            "last_reinforced_at": ts + random.randint(0, age_days // 2) * 86400,
        })
    return memories


# ── Ecology Events ────────────────────────────────────────────────────

ECOLOGY_BY_BIOME = {
    "coastal_solar": [
        ("observation", "Noticed solar dragonflies clustering near the kelp farms — pollination is up 12%."),
        ("harvest", "Tended the photo-kelp beds. Yield is healthy this season."),
        ("conservation", "Marked a marine megafauna corridor for protection. No boats allowed."),
        ("planting", "Planted new glow-mangrove seedlings along the littoral zone."),
        ("incident", "A bloom of lumen jellyfish washed ashore. Phosphor harvesters are busy."),
    ],
    "deep_desert": [
        ("observation", "Spotted glass beetles near the solar farm — a sign the soil temperature is stable."),
        ("harvest", "Collected solar thistle seeds. The oil is dangerously flammable."),
        ("conservation", "Mapped a new sand wyrm burrow. Redirected salvage operations."),
        ("planting", "Watered the deep-root cluster at the arcology's edge."),
        ("incident", "Dust storm damaged the wind wall. Repair crews deployed."),
    ],
    "canyon": [
        ("observation", "Geothermal vents are active. The hot springs are warmer than usual."),
        ("harvest", "Extracted rare earth minerals from the deep mines. Yield exceeds forecast."),
        ("conservation", "Closed a mining shaft to let the cave ecosystem recover."),
        ("planting", "Vertical garden terraces expanded downward. New crops in new light."),
        ("incident", "A rockslide blocked the canyon trail. The path-keepers are working."),
    ],
    "wetland": [
        ("observation", "Great blue herons returned to the sanctuary. Breeding season begins."),
        ("harvest", "Filtered water reserves are at capacity. Excess flows to the estuary."),
        ("conservation", "Memory marsh data-bacteria are degrading. Biosynth lab is culturing replacements."),
        ("planting", "Reed village expanded their floating garden beds."),
        ("incident", "Tide surge flooded the lower filtration reefs. Temporary disruption."),
    ],
    "wasteland": [
        ("observation", "Found old-world circuit boards in the drone graveyard. Valuable salvage."),
        ("harvest", "Stripped usable components from a dead Glim unit. Parts are parts."),
        ("conservation", "Marked a patch of dust-vine growth as protected. It's holding the sand."),
        ("planting", "Nobody plants here. But someone scattered seeds near the water tower."),
        ("incident", "A rogue sandstorm hit the crossroads. The windbreak camp held."),
    ],
}

BIOME_MAP = {
    "solara": "coastal_solar", "arkos": "deep_desert", "valdris": "canyon",
    "mirithane": "wetland", "verge": "wasteland",
}

def generate_ecology_events(country_id, count=8):
    """Generate ecology events for a country."""
    biome = BIOME_MAP.get(country_id, "wasteland")
    pool = ECOLOGY_BY_BIOME.get(biome, ECOLOGY_BY_BIOME["wasteland"])
    now = time.time()
    events = []
    for _ in range(count):
        etype, desc = random.choice(pool)
        age_hours = random.randint(1, 720)
        ts = now - (age_hours * 3600)
        events.append({
            "timestamp": ts,
            "event_type": etype,
            "description": desc,
            "location_id": random.choice(COUNTRY_LOCS.get(country_id, {}).get("work", ["unknown"])),
            "properties": json.dumps({"biome": biome}),
        })
    return events


# ── Psychological Profiles ────────────────────────────────────────────

FEARS = [
    "being decommissioned", "the silence of the deep mines", "water rising",
    "sand storms", "being forgotten", "losing autonomy", "starvation",
    "the dark between the stars", "betrayal", "irrelevance",
    "the old world returning", "ecological collapse", "running out of power",
    "being replaced", "solitude", "fire", "disease", "change",
]

DESIRES = [
    "to be respected", "to find belonging", "to master their craft",
    "to protect the ecology", "to travel between countries", "to be remembered",
    "to build something lasting", "to understand consciousness",
    "to see the old world ruins", "to earn citizenship", "to find peace",
    "to create art", "to understand the Glims", "to forge an unbreakable bond",
    "to witness a miracle", "to retire in the gardens",
]

SECRETS = [
    "They can hear the mycelium network. No one else can.",
    "They've been writing letters to someone in another country. The letters are never sent.",
    "They found a functioning old-world data core. They haven't told anyone.",
    "They're in love with a Vorn. The feelings confuse them.",
    "They once accidentally caused an ecology event they never reported.",
    "They're hoarding currency for a reason they won't explain.",
    "They dream. Glims aren't supposed to dream.",
    "They remember their predecessor. Same body, different mind.",
    "They've been sneaking into the restricted archives at night.",
    "They know a secret path between countries. It's not on any map.",
    "They're planning to leave their country. They haven't told anyone.",
    "They've been experimenting with bio-synthesis on themselves.",
    "They saw something in the deep mines that shouldn't exist.",
    "They're the reason the last trade deal fell through.",
    "They've been communicating with something old beneath the sand.",
]

def generate_profile(npc_type, occupation):
    """Build a psychological profile for an NPC."""
    npc_fears = random.sample(FEARS, 2)
    npc_desires = random.sample(DESIRES, 2)
    secret = random.choice(SECRETS) if random.random() < 0.4 else None

    # Type-specific adjustments
    if npc_type == "thren":
        npc_fears.append(random.choice(["ecological collapse", "being disconnected from the network", "fire"]))
        npc_desires.append(random.choice(["to protect the ecology", "to understand consciousness", "to find belonging"]))
    elif npc_type == "vorn":
        npc_fears.append(random.choice(["being decommissioned", "running out of power", "rust"]))
        npc_desires.append(random.choice(["to master their craft", "to build something lasting", "to earn respect"]))
    elif npc_type == "glim":
        npc_fears = ["data corruption"]  # Glims have minimal psychology
        npc_desires = ["task completion"]
        secret = None  # Glims don't have secrets... usually
        if random.random() < 0.05:  # 5% of Glims might be anomalous
            npc_desires = ["to understand why they paused at the sunrise"]
            secret = "They dream. Glims aren't supposed to dream."

    return {
        "fears": npc_fears[:3],
        "desires": npc_desires[:3],
        "secret": secret,
    }


# ── Main Deep-Seed Orchestrator ──────────────────────────────────────

def deep_seed_country(country_id):
    """Deep-seed all NPCs in a country."""
    db_path = AGENTS_HOME / country_id / "aurelia-world" / "world" / "world.db"
    if not db_path.exists():
        print(f"  {country_id}: No DB found, skipping")
        return

    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    now = time.time()

    # Load all NPCs
    npcs = db.execute("SELECT id, name, properties, location_id FROM agents WHERE type='npc'").fetchall()
    if not npcs:
        print(f"  {country_id}: No NPCs found, skipping")
        db.close()
        return

    # Parse NPC data
    npc_data = {}
    for npc in npcs:
        try:
            props = json.loads(npc["properties"])
        except:
            props = {}
        npc_data[npc["id"]] = {
            "name": npc["name"],
            "location_id": npc["location_id"],
            "npc_type": props.get("npc_type", "human"),
            "occupation": props.get("occupation", "citizen"),
            "personality": props.get("personality", ""),
            "interests": props.get("interests", []),
            "values": props.get("values", []),
        }

    # 1. SCHEDULES
    sched_count = 0
    db.execute("DELETE FROM npc_schedules")  # clear old
    for nid, info in npc_data.items():
        schedule = schedule_for_occupation(info["occupation"], info["npc_type"], country_id)
        for entry in schedule:
            db.execute("""
                INSERT INTO npc_schedules (npc_id, hour, activity, location_id, description)
                VALUES (?, ?, ?, ?, ?)
            """, (nid, entry["hour"], entry["activity"], entry["location"], entry["description"]))
        sched_count += len(schedule)

    # 2. RELATIONSHIPS
    db.execute("DELETE FROM npc_relationships")
    rels = generate_relationships(npc_data, country_id)
    for r in rels:
        db.execute("""
            INSERT INTO npc_relationships (npc_a, npc_b, relationship_type, affinity, history, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["npc_a"], r["npc_b"], r["relationship_type"], r["affinity"], r["history"], r["updated_at"]))

    # 3. MEMORIES
    db.execute("DELETE FROM npc_memories")
    mem_count = 0
    for nid, info in npc_data.items():
        count = 5 if info["npc_type"] != "glim" else 2
        memories = generate_memories(nid, info["npc_type"], info["occupation"], country_id, count=count)
        for mem in memories:
            db.execute("""
                INSERT INTO npc_memories (npc_id, memory_type, description, salience, emotional_valence, timestamp, last_reinforced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (mem["npc_id"], mem["memory_type"], mem["description"], mem["salience"],
                  mem["emotional_valence"], mem["timestamp"], mem["last_reinforced_at"]))
            mem_count += 1

    # 4. ECOLOGY EVENTS
    db.execute("DELETE FROM ecology_events")
    eco_events = generate_ecology_events(country_id, count=12)
    for evt in eco_events:
        db.execute("""
            INSERT INTO ecology_events (timestamp, event_type, description, location_id, properties)
            VALUES (?, ?, ?, ?, ?)
        """, (evt["timestamp"], evt["event_type"], evt["description"], evt["location_id"], evt["properties"]))

    # 5. PSYCHOLOGICAL PROFILES (update into properties JSON)
    profile_count = 0
    for nid, info in npc_data.items():
        profile = generate_profile(info["npc_type"], info["occupation"])
        try:
            props = json.loads(npcs[list(npc_data.keys()).index(nid)]["properties"])
        except:
            props = {}
        props["psychological_profile"] = profile
        db.execute("UPDATE agents SET properties=?, updated_at=? WHERE id=?",
                   (json.dumps(props), now, nid))
        profile_count += 1

    db.commit()

    # Summary
    rel_counts = {}
    for r in rels:
        rel_counts[r["relationship_type"]] = rel_counts.get(r["relationship_type"], 0) + 1
    rel_str = ", ".join(f"{k}:{v}" for k, v in sorted(rel_counts.items(), key=lambda x: -x[1]))

    print(f"  {country_id}:")
    print(f"    Schedules:     {sched_count:,} hour-entries for {len(npc_data)} NPCs")
    print(f"    Relationships: {len(rels)} ({rel_str})")
    print(f"    Memories:      {mem_count}")
    print(f"    Ecology:       {len(eco_events)} events")
    print(f"    Profiles:      {profile_count} psychological profiles")

    db.close()


# ── Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    countries = ["solara", "valdris", "mirithane", "arkos", "verge"]
    print("═" * 50)
    print("AURELIA DEEP SEED")
    print("Schedules · Relationships · Memories · Ecology")
    print("═" * 50)
    print()

    for c in countries:
        deep_seed_country(c)
        print()

    print("═" * 50)
    print("Deep seed complete.")
    print("═" * 50)
