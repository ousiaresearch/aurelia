#!/usr/bin/env python3
"""
aurelia_factory.py — Create Aurelian country-state worlds from YAML configs.

Usage:
    python3 aurelia_factory.py configs/solara.yaml
    python3 aurelia_factory.py --all

Each run creates/updates a world database with locations, ecology, currency tables,
and the agent entry for the target country.
"""

import sys, os, json, time, sqlite3, yaml, random
from pathlib import Path

AURELIA_ROOT = Path("/Users/johann/aurelia")
AGENTS_HOME = Path("/Users/johann/.hermes/agents")
SRC_TEMPLATE = AURELIA_ROOT / "src_template"

# ── Currency-to-symbol mapping ───────────────────────────────────────

CURRENCY_SYMBOLS = {"Lumen": "☀", "Kael": "♦", "Miri": "≈", "Ark": "▲"}
CURRENCY_BACKING = {
    "Lumen": "Solar energy credits + biofuel yield",
    "Kael": "Rare earth minerals + refined metals",
    "Miri": "Purified water reserves + filtration capacity",
    "Ark": "Stored solar energy + manufactured output",
}

# ── World Schema ─────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS world_time (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    year INTEGER NOT NULL DEFAULT 2126,
    month INTEGER NOT NULL DEFAULT 3,
    day INTEGER NOT NULL DEFAULT 17,
    hour INTEGER NOT NULL DEFAULT 6,
    minute INTEGER NOT NULL DEFAULT 0,
    season TEXT NOT NULL DEFAULT 'spring',
    time_of_day TEXT NOT NULL DEFAULT 'dawn',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS tick_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick_number INTEGER NOT NULL,
    real_timestamp REAL NOT NULL,
    world_year INTEGER NOT NULL,
    world_month INTEGER NOT NULL,
    world_day INTEGER NOT NULL,
    world_hour INTEGER NOT NULL,
    world_minute INTEGER NOT NULL,
    season TEXT NOT NULL,
    time_of_day TEXT NOT NULL,
    npc_moves INTEGER DEFAULT 0,
    npc_ai_actions INTEGER DEFAULT 0,
    npc_conversations INTEGER DEFAULT 0,
    social_changes INTEGER DEFAULT 0,
    emergent_events INTEGER DEFAULT 0,
    ecology_events INTEGER DEFAULT 0,
    narrative_moments INTEGER DEFAULT 0,
    ritual_events INTEGER DEFAULT 0,
    economy_produced INTEGER DEFAULT 0,
    economy_consumed INTEGER DEFAULT 0,
    economy_traded INTEGER DEFAULT 0,
    creative_outputs INTEGER DEFAULT 0,
    error TEXT DEFAULT NULL,
    duration_ms INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS weather (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    condition TEXT NOT NULL DEFAULT 'clear',
    temperature REAL NOT NULL DEFAULT 18.0,
    wind_speed REAL NOT NULL DEFAULT 3.0,
    wind_direction TEXT DEFAULT 'SE',
    humidity REAL NOT NULL DEFAULT 0.7,
    visibility TEXT NOT NULL DEFAULT 'clear',
    description TEXT DEFAULT 'A clear sky.',
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    parent_id TEXT REFERENCES locations(id),
    x INTEGER DEFAULT 0,
    y INTEGER DEFAULT 0,
    elevation REAL DEFAULT 0.0,
    indoor INTEGER DEFAULT 0,
    tags TEXT DEFAULT '[]',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS exits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_location TEXT NOT NULL REFERENCES locations(id),
    to_location TEXT NOT NULL REFERENCES locations(id),
    description TEXT DEFAULT '',
    travel_time_hours REAL DEFAULT 0.25,
    mode TEXT DEFAULT 'walk',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'npc',
    location_id TEXT REFERENCES locations(id),
    state TEXT DEFAULT 'active',
    properties TEXT DEFAULT '{}',
    travel_state TEXT DEFAULT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS objects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    location_id TEXT REFERENCES locations(id),
    properties TEXT DEFAULT '{}',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS npc_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id TEXT NOT NULL REFERENCES agents(id),
    hour INTEGER NOT NULL,
    activity TEXT NOT NULL DEFAULT 'idle',
    location_id TEXT REFERENCES locations(id),
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS npc_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_a TEXT NOT NULL REFERENCES agents(id),
    npc_b TEXT NOT NULL REFERENCES agents(id),
    relationship_type TEXT DEFAULT 'acquaintance',
    affinity REAL DEFAULT 0.0,
    history TEXT DEFAULT '[]',
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS npc_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id TEXT NOT NULL REFERENCES agents(id),
    memory_type TEXT NOT NULL,
    description TEXT NOT NULL,
    salience REAL DEFAULT 0.5,
    emotional_valence TEXT DEFAULT 'neutral',
    timestamp REAL NOT NULL,
    last_reinforced_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS npc_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id TEXT NOT NULL REFERENCES agents(id),
    timestamp REAL NOT NULL,
    action_type TEXT NOT NULL,
    location_id TEXT REFERENCES locations(id),
    description TEXT DEFAULT '',
    properties TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    location_id TEXT,
    agent_id TEXT,
    properties TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS narrative_moments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    story_arc_id INTEGER,
    content TEXT DEFAULT '',
    location_id TEXT,
    discovered INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS story_arcs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    title TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    characters TEXT DEFAULT '[]',
    description TEXT DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS ecology_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    location_id TEXT,
    properties TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS animals (
    id TEXT PRIMARY KEY,
    species TEXT NOT NULL,
    population INTEGER DEFAULT 10,
    location_id TEXT REFERENCES locations(id),
    health REAL DEFAULT 0.8,
    properties TEXT DEFAULT '{}',
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS plants (
    id TEXT PRIMARY KEY,
    species TEXT NOT NULL,
    abundance REAL DEFAULT 0.5,
    location_id TEXT REFERENCES locations(id),
    health REAL DEFAULT 0.8,
    properties TEXT DEFAULT '{}',
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    unit TEXT DEFAULT 'unit',
    category TEXT DEFAULT 'material',
    perishable INTEGER DEFAULT 0,
    decay_rate REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS resource_nodes (
    id TEXT PRIMARY KEY,
    location_id TEXT NOT NULL REFERENCES locations(id),
    resource_id TEXT NOT NULL REFERENCES resources(id),
    yield_per_harvest REAL DEFAULT 1.0,
    season TEXT DEFAULT 'any',
    cooldown_hours REAL DEFAULT 24.0,
    last_harvested REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS agent_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL REFERENCES agents(id),
    resource_id TEXT NOT NULL REFERENCES resources(id),
    quantity REAL NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL,
    UNIQUE(agent_id, resource_id)
);

CREATE TABLE IF NOT EXISTS trade_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id TEXT REFERENCES agents(id),
    seller_id TEXT REFERENCES agents(id),
    resource_id TEXT REFERENCES resources(id),
    quantity REAL NOT NULL,
    notes TEXT DEFAULT '',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS world_exploration (
    agent_id TEXT NOT NULL,
    location_id TEXT NOT NULL REFERENCES locations(id),
    visit_count INTEGER DEFAULT 0,
    first_visit REAL,
    last_visit REAL,
    PRIMARY KEY (agent_id, location_id)
);

CREATE TABLE IF NOT EXISTS world_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id TEXT NOT NULL UNIQUE,
    data TEXT DEFAULT '{}',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS world_artifacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    location_id TEXT REFERENCES locations(id),
    created_by TEXT,
    artifact_type TEXT DEFAULT 'misc',
    properties TEXT DEFAULT '{}',
    created_at REAL NOT NULL
);

-- Currency system tables
CREATE TABLE IF NOT EXISTS currency_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL REFERENCES agents(id),
    currency TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL,
    UNIQUE(agent_id, currency)
);

CREATE TABLE IF NOT EXISTS exchange_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_currency TEXT NOT NULL,
    to_currency TEXT NOT NULL,
    rate REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(from_currency, to_currency)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount REAL NOT NULL,
    exchange_rate REAL DEFAULT 1.0,
    note TEXT DEFAULT '',
    location_id TEXT DEFAULT ''
);

-- NPC departure/travel tracking
CREATE TABLE IF NOT EXISTS npc_departures (
    npc_id TEXT NOT NULL,
    departed_at REAL NOT NULL,
    from_location TEXT NOT NULL,
    to_location TEXT NOT NULL,
    route TEXT DEFAULT '',
    travel_cost_hours REAL DEFAULT 0.25,
    UNIQUE(npc_id)
);

-- Goals
CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    progress REAL DEFAULT 0.0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS goal_steps (
    id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    sort_order INTEGER DEFAULT 0
);

-- Rituals
CREATE TABLE IF NOT EXISTS ritual_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ritual_type TEXT NOT NULL,
    last_occurred REAL,
    next_occurrence REAL,
    location_id TEXT,
    properties TEXT DEFAULT '{}'
);

-- Creative output
CREATE TABLE IF NOT EXISTS creative_output (
    id TEXT PRIMARY KEY,
    creator_id TEXT NOT NULL,
    output_type TEXT NOT NULL,
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'completed',
    location_id TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS creative_reactions (
    id TEXT PRIMARY KEY,
    output_id TEXT NOT NULL,
    npc_id TEXT NOT NULL,
    reaction_type TEXT NOT NULL,
    comment TEXT DEFAULT '',
    created_at REAL NOT NULL
);

-- Internal state for agents
CREATE TABLE IF NOT EXISTS body_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    energy REAL DEFAULT 1.0,
    comfort REAL DEFAULT 0.8,
    hunger REAL DEFAULT 0.0,
    thirst REAL DEFAULT 0.0,
    warmth REAL DEFAULT 0.7,
    mood TEXT DEFAULT 'content',
    current_action TEXT DEFAULT 'idle',
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS internal_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    creative_urge REAL DEFAULT 0.5,
    dominant_interest TEXT DEFAULT 'observation',
    social_need REAL DEFAULT 0.3,
    restlessness REAL DEFAULT 0.2,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS interior_state_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    source TEXT NOT NULL,
    manifestation_type TEXT NOT NULL,
    visibility TEXT DEFAULT 'private',
    identity_statement TEXT DEFAULT '',
    trigger_action TEXT,
    trigger_result TEXT DEFAULT '',
    location_id TEXT DEFAULT '',
    description TEXT DEFAULT '',
    properties TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS owl_identity_statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    statement TEXT NOT NULL,
    category TEXT DEFAULT 'identity',
    confidence REAL DEFAULT 0.5,
    confirmed_count INTEGER DEFAULT 1,
    revision_count INTEGER DEFAULT 0,
    total_confirms INTEGER DEFAULT 0,
    total_revisions INTEGER DEFAULT 0,
    set_at REAL DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS fish_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    species TEXT NOT NULL,
    location_id TEXT NOT NULL,
    population INTEGER DEFAULT 50,
    health REAL DEFAULT 0.8,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS smoke (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    content TEXT NOT NULL,
    source TEXT DEFAULT 'world',
    tags TEXT DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_npc_schedules_npc ON npc_schedules(npc_id);
CREATE INDEX IF NOT EXISTS idx_npc_schedules_hour ON npc_schedules(hour);
CREATE INDEX IF NOT EXISTS idx_npc_relationships_a ON npc_relationships(npc_a);
CREATE INDEX IF NOT EXISTS idx_npc_relationships_b ON npc_relationships(npc_b);
CREATE INDEX IF NOT EXISTS idx_npc_memories_npc ON npc_memories(npc_id);
CREATE INDEX IF NOT EXISTS idx_exits_from ON exits(from_location);
CREATE INDEX IF NOT EXISTS idx_agent_inventory_agent ON agent_inventory(agent_id);
"""


def create_world_from_config(config_path: str):
    """Create a world database from a YAML config file."""
    config_path = Path(config_path)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return False

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    world_id = cfg["world_id"]
    world_name = cfg["name"]
    currency_name = cfg.get("currency")

    # Agent directory
    agent_dir = AGENTS_HOME / world_id / "aurelia-world"
    agent_dir.mkdir(parents=True, exist_ok=True)
    db_path = agent_dir / "world" / "world.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Also create scripts and src dirs
    (agent_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (agent_dir / "src").mkdir(parents=True, exist_ok=True)

    print(f"Building {world_name} ({world_id}) → {db_path}")
    print(f"  Currency: {currency_name} {CURRENCY_SYMBOLS.get(currency_name, '?')}")

    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    now = time.time()

    # ── 1. World time ──────────────────────────────────────────────
    db.execute("""
        INSERT INTO world_time (id, year, month, day, hour, minute, season, time_of_day, created_at, updated_at)
        VALUES (1, 2126, 3, 17, 6, 0, 'spring', 'dawn', ?, ?)
    """, (now, now))

    # ── 2. Weather ─────────────────────────────────────────────────
    wx = cfg.get("weather_profile", {})
    base_temp = wx.get("base_temp", 20)
    db.execute("""
        INSERT INTO weather (id, condition, temperature, wind_speed, wind_direction, humidity, visibility, description, updated_at)
        VALUES (1, 'clear', ?, 3.0, 'SE', 0.6, 'clear', 'A clear sky over Aurelia.', ?)
    """, (base_temp, now))

    # ── 3. Body + Internal state ───────────────────────────────────
    db.execute("INSERT INTO body_state (id, updated_at) VALUES (1, ?)", (now,))
    db.execute("INSERT INTO internal_state (id, created_at, updated_at) VALUES (1, ?, ?)", (now, now))

    # ── 4. Locations ───────────────────────────────────────────────
    locations = cfg.get("locations", [])
    for i, loc in enumerate(locations):
        loc_id = loc["id"]
        # Place on a rough map grid
        x = (i % 4) * 40 + 20
        y = (i // 4) * 30 + 20
        elevation = loc.get("elevation", 0)
        indoor = 1 if loc.get("indoor", False) else 0
        tags = json.dumps(loc.get("tags", []))

        db.execute("""
            INSERT INTO locations (id, name, description, x, y, elevation, indoor, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (loc_id, loc["name"], loc["description"], x, y, elevation, indoor, tags, now))

    print(f"  Locations: {len(locations)}")

    # ── 5. Exits — connect locations that share tags ────────────────
    exit_count = 0
    transit_ids = [l["id"] for l in locations if "transit" in l.get("tags", [])]
    all_ids = [l["id"] for l in locations]

    # Connect transit hubs to all other locations
    for transit_id in transit_ids:
        for other_id in all_ids:
            if other_id != transit_id:
                db.execute("""
                    INSERT INTO exits (from_location, to_location, description, travel_time_hours, mode, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (transit_id, other_id, f"From transit hub to {other_id}", 0.5, "walk", now))
                exit_count += 1

    # Connect adjacent locations in sequence
    for i in range(len(all_ids) - 1):
        db.execute("""
            INSERT INTO exits (from_location, to_location, description, travel_time_hours, mode, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (all_ids[i], all_ids[i+1], f"From {all_ids[i]} to {all_ids[i+1]}", 0.15, "walk", now))
        exit_count += 1
        # Add reverse
        db.execute("""
            INSERT INTO exits (from_location, to_location, description, travel_time_hours, mode, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (all_ids[i+1], all_ids[i], f"From {all_ids[i+1]} to {all_ids[i]}", 0.15, "walk", now))
        exit_count += 1

    print(f"  Exits: {exit_count}")

    # ── 6. Resources — Aurelian-specific resources ──────────────────
    resources = [
        ("solar_cell", "Solar Cell", "unit", "energy", 0, 0.0),
        ("biogel", "Biogel", "liter", "fuel", 0, 0.0),
        ("synth_fiber", "Synth-Fiber", "meter", "material", 1, 0.02),
        ("printed_circuit", "Printed Circuit", "unit", "electronics", 0, 0.0),
        ("purified_water", "Purified Water", "liter", "essential", 0, 0.0),
        ("rare_earth", "Rare Earth Mineral", "gram", "mineral", 0, 0.0),
        ("lumen_crystal", "Lumen Crystal", "crystal", "energy", 0, 0.0),
        ("kelp_fuel", "Kelp Biofuel", "liter", "fuel", 1, 0.01),
        ("salvage_component", "Salvage Component", "unit", "salvage", 0, 0.0),
        ("reed_fiber", "Reed Fiber", "bundle", "material", 1, 0.03),
    ]
    for res_id, name, unit, cat, perishable, decay in resources:
        db.execute("""
            INSERT OR IGNORE INTO resources (id, name, unit, category, perishable, decay_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (res_id, name, unit, cat, perishable, decay))

    print(f"  Resources: {len(resources)}")

    # ── 7. Ecology — animals and plants ─────────────────────────────
    ecology = cfg.get("ecology", {})
    
    animal_count = 0
    for species in ecology.get("animals", []):
        loc = random.choice(all_ids) if all_ids else "unknown"
        animal_id = f"{world_id}_{species}"
        pop = random.randint(8, 30)
        db.execute("""
            INSERT INTO animals (id, species, population, location_id, health, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (animal_id, species, pop, loc, 0.8, now))
        animal_count += 1

    plant_count = 0
    for species in ecology.get("plants", []):
        loc = random.choice(all_ids) if all_ids else "unknown"
        plant_id = f"{world_id}_{species}"
        abundance = random.uniform(0.3, 0.9)
        db.execute("""
            INSERT INTO plants (id, species, abundance, location_id, health, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (plant_id, species, abundance, loc, 0.8, now))
        plant_count += 1

    print(f"  Ecology: {animal_count} animals, {plant_count} plants")

    # ── 8. Agent entry ──────────────────────────────────────────────
    agent_info = cfg.get("agent", {})
    agent_id = agent_info.get("agent_id", world_id)
    entry_loc = agent_info.get("entry_location", all_ids[0]) if all_ids else "unknown"
    name = agent_info.get("name", world_name.capitalize())

    db.execute("""
        INSERT INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
        VALUES (?, ?, 'player', ?, 'active', '{}', ?, ?)
    """, (agent_id, name, entry_loc, now, now))

    # ── 9. World registry ───────────────────────────────────────────
    registry_data = json.dumps({
        "world_id": world_id,
        "name": world_name,
        "full_name": cfg.get("full_name", world_name),
        "region": cfg.get("region", "Aurelia"),
        "currency": currency_name,
        "currency_symbol": CURRENCY_SYMBOLS.get(currency_name, ""),
        "currency_backing": CURRENCY_BACKING.get(currency_name, ""),
        "location_count": len(locations),
        "biome": cfg.get("geography", {}).get("biome", "unknown"),
    })
    db.execute("""
        INSERT INTO world_registry (world_id, data, created_at)
        VALUES (?, ?, ?)
    """, (world_id, registry_data, now))

    db.commit()
    db.close()

    # ── 10. Save config to agent dir ────────────────────────────────
    config_dest = agent_dir / "world_config.yaml"
    with open(config_dest, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

    # ── 11. Copy src template ───────────────────────────────────────
    import shutil
    src_dest = agent_dir / "src"
    for src_file in SRC_TEMPLATE.iterdir():
        if src_file.is_file() and src_file.suffix == '.py':
            shutil.copy2(src_file, src_dest / src_file.name)

    # ── 12. Create world_daemon.py from template ─────────────────────
    daemon_template = AURELIA_ROOT / "world_daemon_template.py"
    if daemon_template.exists():
        daemon_content = daemon_template.read_text()
        # Customize for this world
        daemon_content = daemon_content.replace("WORLD_ID_PLACEHOLDER", world_id)
        daemon_content = daemon_content.replace("AGENT_ID_PLACEHOLDER", agent_id)
        daemon_content = daemon_content.replace("API_PORT_PLACEHOLDER", str(8765 + list(["solara","valdris","mirithane","arkos","verge"]).index(world_id)))
        script_dest = agent_dir / "scripts" / "world_daemon.py"
        script_dest.write_text(daemon_content)

    print(f"  Agent: {agent_id} @ {entry_loc}")
    print(f"  ✓ {world_name} created successfully\n")
    return True


def main():
    if "--all" in sys.argv:
        configs = sorted((AURELIA_ROOT / "configs").glob("*.yaml"))
        if not configs:
            print("No configs found in configs/")
            sys.exit(1)
        
        for cfg_path in configs:
            if not create_world_from_config(str(cfg_path)):
                print(f"Failed: {cfg_path}")
    elif len(sys.argv) > 1:
        create_world_from_config(sys.argv[1])
    else:
        print("Usage: python3 aurelia_factory.py <config.yaml> | --all")
        sys.exit(1)


if __name__ == "__main__":
    main()
