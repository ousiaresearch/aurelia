"""
world_state.py — SQLite schema and world state management.

The world state is the single source of truth for everything in the simulation.
It's stored in SQLite for atomic writes and crash safety, with JSON snapshots
for human readability and git versioning.

Schema design principles:
- Every entity (locations, objects, agents) is a row, not a blob
- State changes are inserts/updates, not replacements
- Timestamps on everything for reconstruction
- WAL mode for crash safety
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Any, Optional


DB_PATH = Path(__file__).parent.parent / "world" / "world.db"


def set_db_path(path: Path) -> None:
    """Override the default database path for this world instance.
    
    Each world process calls this once on startup to point at its own world.db.
    The path is module-level state — per-process, no threading concerns.
    """
    global DB_PATH
    DB_PATH = path


LOCATION_ALIASES = {
    "cottage_bedroom": "cabin_bedroom",
    "cottage_main_room": "cabin_main_room",
    "cottage_kitchen": "cabin_kitchen",
    "cottage_workshop": "workshop",
    "cottage_garden": "garden",
}


def canonicalize_location_id(db: sqlite3.Connection, location_id: Optional[str]) -> Optional[str]:
    """Map legacy location IDs to canonical live-world IDs when possible."""
    if location_id is None:
        return None
    canonical = LOCATION_ALIASES.get(location_id)
    if not canonical:
        return location_id
    row = db.execute("SELECT 1 FROM locations WHERE id = ?", (canonical,)).fetchone()
    return canonical if row else location_id


def get_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode and foreign keys."""
    db = sqlite3.connect(str(db_path))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.row_factory = sqlite3.Row
    return db


def init_world(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Initialize the world database with the full schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = get_db(db_path)

    db.executescript("""
        -- ──────────────────────────────────────────────
        -- TIME
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS world_time (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            year INTEGER NOT NULL DEFAULT 2026,
            month INTEGER NOT NULL DEFAULT 3,
            day INTEGER NOT NULL DEFAULT 17,
            hour INTEGER NOT NULL DEFAULT 6,
            minute INTEGER NOT NULL DEFAULT 0,
            season TEXT NOT NULL DEFAULT 'spring',
            time_of_day TEXT NOT NULL DEFAULT 'dawn',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        -- ──────────────────────────────────────────────
        -- TICK LOG (persistent audit trail)
        -- ──────────────────────────────────────────────
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

        -- ──────────────────────────────────────────────
        -- WEATHER
        -- ──────────────────────────────────────────────
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

        -- ──────────────────────────────────────────────
        -- LOCATIONS
        -- ──────────────────────────────────────────────
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
            properties TEXT DEFAULT '{}',
            created_at REAL NOT NULL
        );

        -- Exits between locations
        CREATE TABLE IF NOT EXISTS exits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_location TEXT NOT NULL REFERENCES locations(id),
            to_location TEXT NOT NULL REFERENCES locations(id),
            direction TEXT DEFAULT '',
            description TEXT DEFAULT '',
            locked INTEGER DEFAULT 0,
            hidden INTEGER DEFAULT 0,
            travel_cost_hours REAL DEFAULT 0.0,
            terrain_type TEXT DEFAULT 'trail'
        );

        CREATE TABLE IF NOT EXISTS world_exploration (
            agent_id TEXT NOT NULL,
            location_id TEXT NOT NULL REFERENCES locations(id),
            visit_count INTEGER DEFAULT 0,
            first_visit REAL,
            last_visit REAL,
            PRIMARY KEY(agent_id, location_id)
        );

        -- ──────────────────────────────────────────────
        -- OBJECTS (things in the world)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS objects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            location_id TEXT REFERENCES locations(id),
            carried_by TEXT DEFAULT NULL,
            state TEXT DEFAULT 'default',
            properties TEXT DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        -- ──────────────────────────────────────────────
        -- AGENTS (OWL + NPCs)
        -- ──────────────────────────────────────────────
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

        -- ──────────────────────────────────────────────
        -- NPC SCHEDULES (daily routines)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS npc_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id TEXT NOT NULL REFERENCES agents(id),
            hour INTEGER NOT NULL,
            activity TEXT NOT NULL DEFAULT 'idle',
            location_id TEXT REFERENCES locations(id),
            description TEXT DEFAULT ''
        );

        -- ──────────────────────────────────────────────
        -- NPC RELATIONSHIPS
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS npc_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_a TEXT NOT NULL REFERENCES agents(id),
            npc_b TEXT NOT NULL REFERENCES agents(id),
            relationship TEXT NOT NULL DEFAULT 'acquaintance',
            affinity REAL DEFAULT 0.5,
            description TEXT DEFAULT ''
        );

        -- ──────────────────────────────────────────────
        -- OWL'S BODY STATE
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS body_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            energy REAL NOT NULL DEFAULT 0.8,
            comfort REAL NOT NULL DEFAULT 0.7,
            hunger REAL NOT NULL DEFAULT 0.2,
            thirst REAL NOT NULL DEFAULT 0.15,
            warmth REAL NOT NULL DEFAULT 0.7,
            mood TEXT DEFAULT 'calm',
            mood_intensity REAL DEFAULT 0.5,
            current_action TEXT DEFAULT 'idle',
            action_target TEXT DEFAULT NULL,
            action_started_at REAL DEFAULT 0,
            physical_state TEXT DEFAULT '{}',
            updated_at REAL NOT NULL
        );

        -- ──────────────────────────────────────────────
        -- OWL'S INTERNAL STATE (psychology)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS internal_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            mood TEXT DEFAULT 'calm',
            energy REAL NOT NULL DEFAULT 0.7,
            restlessness REAL NOT NULL DEFAULT 0.3,
            social_need REAL NOT NULL DEFAULT 0.4,
            creative_urge REAL NOT NULL DEFAULT 0.5,
            dominant_interest TEXT DEFAULT 'none',
            recent_memories TEXT DEFAULT '[]',
            long_term_memories TEXT DEFAULT '[]',
            current_project TEXT DEFAULT NULL,
            project_progress REAL DEFAULT 0.0,
            updated_at REAL NOT NULL
        );

        -- ──────────────────────────────────────────────
        -- EVENT LOG (what happens in the world)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            agent_id TEXT DEFAULT NULL,
            event_type TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            location_id TEXT DEFAULT NULL,
            properties TEXT DEFAULT '{}'
        );

        -- ──────────────────────────────────────────────
        -- CREATIVE OUTPUT (things OWL makes)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS creative_output (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL DEFAULT 'isildur',
            type TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'Untitled',
            content TEXT NOT NULL DEFAULT '',
            location_id TEXT DEFAULT NULL,
            state TEXT DEFAULT 'in_progress',
            properties TEXT DEFAULT '{}',
            reactions_count INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        -- ──────────────────────────────────────────────
        -- ECONOMY / RESOURCES
        -- ──────────────────────────────────────────────
        -- Master list of resource types in the world
        CREATE TABLE IF NOT EXISTS resources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            unit TEXT NOT NULL DEFAULT 'unit',
            category TEXT DEFAULT 'material',
            perishable INTEGER DEFAULT 0,
            decay_rate REAL DEFAULT 0.0,
            properties TEXT DEFAULT '{}',
            created_at REAL NOT NULL
        );

        -- Per-agent inventory — one row per agent × resource
        CREATE TABLE IF NOT EXISTS agent_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL REFERENCES agents(id),
            resource_id TEXT NOT NULL REFERENCES resources(id),
            quantity REAL NOT NULL DEFAULT 0.0,
            quality REAL DEFAULT 1.0,
            updated_at REAL NOT NULL,
            UNIQUE(agent_id, resource_id)
        );

        -- Trade history
        CREATE TABLE IF NOT EXISTS trade_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id TEXT REFERENCES agents(id),
            seller_id TEXT REFERENCES agents(id),
            resource_id TEXT NOT NULL REFERENCES resources(id),
            quantity REAL NOT NULL,
            price TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at REAL NOT NULL
        );

        -- Resource nodes — where resources are produced/harvested
        CREATE TABLE IF NOT EXISTS resource_nodes (
            id TEXT PRIMARY KEY,
            location_id TEXT NOT NULL REFERENCES locations(id),
            resource_id TEXT NOT NULL REFERENCES resources(id),
            season TEXT DEFAULT 'any',
            yield_per_harvest REAL DEFAULT 1.0,
            cooldown_hours INTEGER DEFAULT 24,
            last_harvested REAL DEFAULT 0,
            properties TEXT DEFAULT '{}',
            created_at REAL NOT NULL
        );

        -- Ecology tables are created by ecology.init_ecology() via _ensure_runtime_tables
        -- (removed stub plants/animals tables — ecology.py owns the schema)

        CREATE TABLE IF NOT EXISTS npc_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id TEXT REFERENCES agents(id),
            action_type TEXT NOT NULL DEFAULT 'idle',
            description TEXT DEFAULT '',
            location_id TEXT REFERENCES locations(id),
            tick_number INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        );

        -- ──────────────────────────────────────────────
        -- INDEXES
        -- ──────────────────────────────────────────────
        CREATE INDEX IF NOT EXISTS idx_objects_location ON objects(location_id);
        CREATE INDEX IF NOT EXISTS idx_agents_location ON agents(location_id);
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent_id);
        CREATE INDEX IF NOT EXISTS idx_exits_from ON exits(from_location);
        CREATE INDEX IF NOT EXISTS idx_npc_schedules_npc ON npc_schedules(npc_id);
        CREATE INDEX IF NOT EXISTS idx_npc_schedules_hour ON npc_schedules(hour);
        CREATE INDEX IF NOT EXISTS idx_npc_rel_a ON npc_relationships(npc_a);
        CREATE INDEX IF NOT EXISTS idx_npc_rel_b ON npc_relationships(npc_b);
        CREATE INDEX IF NOT EXISTS idx_agent_inv_agent ON agent_inventory(agent_id);
        CREATE INDEX IF NOT EXISTS idx_agent_inv_resource ON agent_inventory(resource_id);
        CREATE INDEX IF NOT EXISTS idx_trade_log_parties ON trade_log(buyer_id, seller_id);
        CREATE INDEX IF NOT EXISTS idx_resource_nodes_location ON resource_nodes(location_id);

        -- ──────────────────────────────────────────────
        -- WORLD ARTIFACTS (accumulated physical changes)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS world_artifacts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            location_id TEXT REFERENCES locations(id),
            artifact_type TEXT DEFAULT 'placed',
            created_by TEXT DEFAULT 'isildur',
            created_at REAL NOT NULL,
            properties TEXT DEFAULT '{}',
            visible INTEGER DEFAULT 1
        );

        -- ──────────────────────────────────────────────
        -- WORLD REGISTRY (federation identity)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS world_registry (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            world_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            region TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT 'UTC',
            hosted_agent_id TEXT NOT NULL,
            entry_location_id TEXT DEFAULT NULL,
            api_port INTEGER NOT NULL DEFAULT 8765,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        -- ──────────────────────────────────────────────
        -- NPC DECISION STATE (growth engine)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS npc_decision_state (
            npc_id TEXT PRIMARY KEY,
            variables JSON NOT NULL DEFAULT '{}',
            last_updated REAL NOT NULL DEFAULT 0,
            decision_log JSON NOT NULL DEFAULT '[]'
        );

        -- ──────────────────────────────────────────────
        -- FACTIONS (Phase 6 — emergent geopolitics)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS factions (
            faction_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            world_id TEXT NOT NULL,
            region TEXT,
            status TEXT NOT NULL DEFAULT 'forming',
            primary_grievance TEXT,
            demand TEXT,
            leader_npc_id TEXT,
            member_count INTEGER DEFAULT 0,
            influence REAL DEFAULT 0.0,
            founded_tick INTEGER,
            dissolved_tick INTEGER,
            metadata JSON DEFAULT '{}',
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS faction_members (
            faction_id TEXT NOT NULL REFERENCES factions(faction_id),
            npc_id TEXT NOT NULL REFERENCES agents(id),
            joined_tick INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            PRIMARY KEY (faction_id, npc_id)
        );

        -- ──────────────────────────────────────────────
        -- SOVEREIGNTY EVENTS (Phase 6 — faction-to-country)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS sovereignty_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faction_id TEXT NOT NULL,
            world_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            new_country_name TEXT,
            recognized_by TEXT,
            territory_control REAL,
            member_count INTEGER,
            tick_number INTEGER,
            created_at REAL NOT NULL
        );

        -- ──────────────────────────────────────────────
        -- PHASE 6.5 TABLES — reconciliation, discovery, great persons
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS peace_treaties (
            treaty_id TEXT PRIMARY KEY,
            faction_a_id TEXT NOT NULL,
            faction_b_id TEXT,
            mediator_world TEXT,
            terms TEXT DEFAULT '{}',
            signed_tick INTEGER NOT NULL,
            durability REAL DEFAULT 1.0,
            broken INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS discoveries (
            discovery_id TEXT PRIMARY KEY,
            world_id TEXT NOT NULL,
            discovery_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            location_id TEXT,
            effects TEXT DEFAULT '{}',
            tick_number INTEGER NOT NULL,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS great_persons (
            npc_id TEXT PRIMARY KEY,
            world_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            impact_level REAL DEFAULT 0.5,
            tick_number INTEGER NOT NULL,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS federation_events_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            world_id TEXT NOT NULL,
            description TEXT DEFAULT '',
            tick_number INTEGER NOT NULL,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cross_world_movements (
            npc_id TEXT NOT NULL,
            source_world TEXT NOT NULL,
            target_world TEXT NOT NULL,
            movement_type TEXT NOT NULL DEFAULT 'migration',
            tick_number INTEGER NOT NULL,
            created_at REAL NOT NULL,
            PRIMARY KEY (npc_id, tick_number)
        );

        -- ──────────────────────────────────────────────
        -- CAUSAL FEDERATION TABLES (Phase 7)
        -- ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS causal_events (
            event_id TEXT PRIMARY KEY,
            tick_number INTEGER NOT NULL,
            world_id TEXT NOT NULL,
            layer TEXT NOT NULL CHECK(layer IN ('micro','meso','macro','federation')),
            event_type TEXT NOT NULL,
            actor_ids TEXT NOT NULL DEFAULT '[]',
            target_ids TEXT NOT NULL DEFAULT '[]',
            scope TEXT NOT NULL,
            magnitude REAL NOT NULL DEFAULT 0.0,
            valence REAL NOT NULL DEFAULT 0.0,
            confidence REAL NOT NULL DEFAULT 1.0,
            payload TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_causal_events_tick_world
            ON causal_events(tick_number, world_id);
        CREATE INDEX IF NOT EXISTS idx_causal_events_layer_type
            ON causal_events(layer, event_type);

        CREATE TABLE IF NOT EXISTS delayed_effects (
            effect_id TEXT PRIMARY KEY,
            source_event_id TEXT NOT NULL,
            apply_tick INTEGER NOT NULL,
            target_world_id TEXT NOT NULL,
            target_scope TEXT NOT NULL,
            target_id TEXT,
            effect_type TEXT NOT NULL,
            magnitude REAL NOT NULL DEFAULT 0.0,
            payload TEXT NOT NULL DEFAULT '{}',
            applied INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_delayed_effects_apply
            ON delayed_effects(apply_tick, target_world_id, applied);

        CREATE TABLE IF NOT EXISTS causal_edges (
            parent_event_id TEXT NOT NULL,
            child_event_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 1.0,
            PRIMARY KEY(parent_event_id, child_event_id)
        );

        CREATE TABLE IF NOT EXISTS npc_departures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id TEXT NOT NULL REFERENCES agents(id),
            origin_location_id TEXT REFERENCES locations(id),
            destination_location_id TEXT REFERENCES locations(id),
            reason TEXT DEFAULT '',
            departed_at REAL NOT NULL,
            expected_arrival_at REAL,
            arrived INTEGER DEFAULT 0
        );
    """)

    _ensure_runtime_tables(db)
    return db


def _ensure_runtime_tables(db: sqlite3.Connection) -> None:
    """Create runtime tables that optional subsystems expect.

    Speed-run DBs are created from this module without daemon boot hooks; these
    tables must exist before simulation.tick() so optional mechanics do not
    crash before Phase 6.5/6.6 systems are reached.
    """
    now = time.time()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS goals (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            priority INTEGER DEFAULT 5,
            category TEXT DEFAULT 'general',
            context TEXT DEFAULT '',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            target_date REAL DEFAULT NULL,
            completed_at REAL DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS goal_steps (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            sort_order INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            completed_at REAL DEFAULT NULL,
            FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS npc_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id TEXT NOT NULL REFERENCES agents(id),
            event TEXT NOT NULL DEFAULT '',
            memory_type TEXT DEFAULT 'observation',
            emotional_weight REAL DEFAULT 0.0,
            impact REAL DEFAULT 0.0,
            tick INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS creative_output (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL DEFAULT 'isildur',
            type TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'Untitled',
            content TEXT NOT NULL DEFAULT '',
            location_id TEXT DEFAULT NULL,
            state TEXT DEFAULT 'completed',
            properties TEXT DEFAULT '{}',
            reactions_count INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS creative_reactions (
            id TEXT PRIMARY KEY,
            output_id TEXT NOT NULL,
            npc_id TEXT NOT NULL,
            reaction_type TEXT NOT NULL,
            comment TEXT DEFAULT '',
            created_at REAL NOT NULL,
            FOREIGN KEY (output_id) REFERENCES creative_output(id) ON DELETE CASCADE
        );
    """)

    # Backfill columns for DBs whose CREATE TABLE IF NOT EXISTS ran before this fix.
    for ddl in (
        "ALTER TABLE agents ADD COLUMN travel_state TEXT DEFAULT NULL",
        "ALTER TABLE creative_output ADD COLUMN reactions_count INTEGER DEFAULT 0",
    ):
        try:
            db.execute(ddl)
        except Exception:
            pass

    # Let subsystem initializers add any richer optional tables. Use lazy imports
    # so world_state remains importable in both package and flat Colab contexts.
    for module_name, func_name in (
        ("ecology", "init_ecology"),
        ("npc_ai", "init_npc_ai"),
        ("npc_memory", "init_memory_tables"),
        ("goals", "init_goals"),
        ("creative_output", "init_creative_output"),
        ("rituals", "init_ritual_tables"),
        ("narrative", "init_narrative_tables"),
    ):
        try:
            try:
                mod = __import__(f".{module_name}", globals(), locals(), [func_name], 1)
            except Exception:
                mod = __import__(module_name, globals(), locals(), [func_name], 0)
            getattr(mod, func_name)(db)
        except Exception:
            pass
    db.commit()


def seed_world(db: sqlite3.Connection, config=None) -> None:
    """Seed the initial world state — configurable via WorldConfig."""
    now = time.time()

    # Time: early spring morning
    db.execute("""
        INSERT OR IGNORE INTO world_time (id, year, month, day, hour, minute, season, time_of_day, created_at, updated_at)
        VALUES (1, 2026, 3, 17, 6, 0, 'spring', 'dawn', ?, ?)
    """, (now, now))

    # Weather: spring morning — PNW if config says coastal_north, else NC
    if config and config.geography.climate == "coastal_north":
        weather_desc = "The fog sits heavy in the valley this morning, threading between the old-growth cedars like breath. The air smells of damp bark and cold water. Everything is quiet except the creek."
        db.execute("""
            INSERT OR IGNORE INTO weather (id, condition, temperature, wind_speed, wind_direction, humidity, visibility, description, updated_at)
            VALUES (1, 'foggy', 8.0, 2.0, 'NE', 0.92, 'low', ?, ?)
        """, (weather_desc, now))
    else:
        db.execute("""
            INSERT OR IGNORE INTO weather (id, condition, temperature, wind_speed, wind_direction, humidity, visibility, description, updated_at)
            VALUES (1, 'foggy', 12.0, 3.0, 'SE', 0.85, 'low', 'A thick fog hangs over the sound this morning. The air is heavy with salt and the faint sulfur smell of pluff mud. Live oaks disappear into the gray.', ?)
        """, (now,))

    _seed_locations(db, now, config)
    _seed_exits(db, config)
    _seed_objects(db, now, config)
    _seed_npcs(db, now, config)
    _seed_schedules(db)
    _seed_relationships(db)
    _seed_owl(db, now, config)

    # Initial event
    if config and config.geography.climate == "coastal_north":
        init_event = "The world begins. A spring dawn in the Pacific Northwest. Fog in the valley, cedars holding the quiet."
    else:
        init_event = "The world begins. A spring dawn on the Carolina coast. Fog over the sound, shrimp boats running dark."
    db.execute("""
        INSERT INTO events (timestamp, agent_id, event_type, description, location_id, properties)
        VALUES (?, 'isildur', 'world_init', ?, 'cottage_bedroom', '{}')
    """, (now, init_event))

    db.commit()


def _seed_locations(db: sqlite3.Connection, now: float, config=None) -> None:
    """Seed all locations — PNW cabin and surroundings."""
    locations = [
        # ── COTTAGE (OWL's home) ──
        ("cottage", "Cottage", "A small house on a slight rise overlooking Core Sound, where morning fog unrolls like gauze across the water. The cedar shake siding has weathered to the silver-gray of old driftwood, and the tin roof ticks and settles with the day's warmth. The porch faces the sound — a habit the military gave you at Bragg, an hour inland, but the water is what kept you here. You can hear shrimp boats idling in the gray before you see them, their diesel hum threading through the live oaks.", None, 5, 8, 15, 1, '["home", "shelter"]', '{}'),
        ("cottage_main_room", "Main Room", "The cottage's main room holds the accumulated weight of quiet evenings — a sunken couch that remembers your shape, a wood-burning stove still ticking with last night's heat, a coffee table fashioned from a cable reel. Dust motes float in the shaft of light from the sound-facing window, and fishing rods lean in the corner like patient sentinels. The floorboards creak familiar patterns underfoot, and the salt air finds its way in through every crack.", "cottage", 5, 8, 15, 1, '["living", "warm"]', '{}'),
        ("cottage_bedroom", "Bedroom", "The bedroom is small and honest — a quilt your mother sent from home, rough at the edges from wash after wash, and at the foot of the bed, an Army-issue footlocker still bearing your name stenciled in faded block letters. A desk by the window holds a laptop and a leaning tower of books, salt air curling at their pages. The sound of shrimp boats reaches you here in the dark, a lullaby of low diesel thrum that rocks you more than any silence ever could.", "cottage", 5, 8, 15, 1, '["rest", "private"]', '{}'),
        ("cottage_kitchen", "Kitchen", "A narrow kitchen where the gas burner still hisses blue under a cast iron skillet that never leaves the stove. The deep sink holds a single plate from this morning's eggs, and the refrigerator hums its one eternal note. Last night's boiled shrimp left their perfume in the air — briny, faintly sweet — and a pitcher of sweet tea sweats on the counter, beads of cool running down its sides like slow tears.", "cottage", 5, 8, 15, 1, '["cooking", "warm"]', '{}'),
        ("cottage_workshop", "Workshop", "The workshop smells of pine shavings and linseed oil, sharp and clean in a way that works on you like a reset. The workbench is organized with a soldier's precision — saws, chisels, planes, each in its place. A half-built bookcase waits against the wall, its joints not yet tightened, and the quiet here has a quality that lets your thoughts line up in straight rows. Sawdust clings to your forearms like pale freckles.", "cottage", 5, 8, 15, 1, '["crafting", "creative"]', '{}'),
        ("cottage_garden", "Garden", "Behind the cottage, raised beds hold rosemary and thyme pushing up through dark soil, red pepper plants just starting to show color. A wooden bench faces the sound, paint peeling in curls like old sunburn, and overhead a live oak spreads its canopy so wide it makes its own weather. Spanish moss drips from every branch, swaying in the breeze like gray curtains that never quite close, and the smell of the sound — pluff mud and salt — is strongest here at dusk.", "cottage", 5, 8, 14, 0, '["growing", "outdoor"]', '{}'),

        # ── HILLSIDE (The Rise) ──
        ("hillside_path", "The Path", "A sandy path winds down the slight rise toward the village, and on either side sea oats sway like a slow metronome keeping time with the wind. The sound is visible through the marsh grass — brown pelicans folding their wings and plunging into the tea-dark water. Your boots leave prints that fill with brine by morning, and the path has been walked so many times it sits slightly below the surrounding ground, a groove worn by generations of feet.", None, 5, 6, 12, 0, '["path", "outdoor"]', '{}'),
        ("hillside_overlook", "The Rise", "The highest point around — which isn't saying much in Carteret County, where the land barely clears the water's mood. But from here the whole village unfolds like a map you've memorized: shrimp boats dotting the sound, the black-and-white diamonds of Cape Lookout lighthouse in the far distance, and the maritime forest dark against the sky. The wind is stronger here, carrying the smell of pluff mud and diesel, and it presses against your chest like a hand reminding you you're alive.", None, 4, 7, 18, 0, '["view", "contemplation"]', '{}'),
        ("tabby_ruins_entrance", "The Tabby Ruins", "The crumbling tabby walls rise from the undergrowth like broken teeth — oyster shell concrete built maybe two hundred years ago by hands that knew this coast before the hurricanes took their cut. A chimney still stands, defiant, its mortar crumbling but holding. Kids dare each other to go inside, and the locals call it the Tabby Ruins the way they name a storm — with familiarity and a little fear. The air around it is cooler, as if the thick walls remember winter.", None, 3, 8, 16, 0, '["history", "exploration"]', '{}'),
        ("tabby_ruins_interior", "Inside the Tabby Ruins", "Inside the old tabby walls, the world goes quiet in a way that makes your ears ring. The floor is sand and broken brick, and someone has left a few candles in melted puddles of wax — offerings or markers, hard to say. The walls are three feet thick, and they hold the cool of the morning like a secret. You can hear your own heartbeat in here, and the faintest whisper of the sound outside, as if the past hasn't quite let go of this place.", None, 3, 8, 15, 1, '["history", "quiet"]', '{}'),

        # ── TOWN (the village) ──
        ("town_square", "The Square", "The heart of the village — a paved intersection where Hwy 58 meets the road to the harbor, and the asphalt is soft in summer from the heat. A few benches face a flagpole where the American flag and the NC state flag snap in the salt wind, and the bulletin board holds notices about the annual seafood festival, a lost dog, a church supper. Pickup trucks park at angles, their beds carrying crab pots or lumber or nothing at all, and the smell of fried shrimp drifts from The Crab Shack like a summons.", None, 5, 4, 5, 0, '["social", "town"]', '{}'),
        ("tavern", "The Crab Shack", "A no-frills bar on the water where the plywood walls are papered with dollar bills and business cards — a living archive of everyone who's ever passed through. The jukebox plays Merle Haggard or Hank Williams, and the long bar is polished to a dark shine by generations of elbows. The smell is fried shrimp and spilled beer and the faint tang of Old Bay, and the laughter here is loud enough to drown out whatever you came in trying not to think about.", None, 6, 4, 5, 1, '["social", "food", "drink"]', '{"owner": "marty"}'),
        ("market_stall", "Market Stalls", "A row of covered stalls near the harbor where the morning's catch sits on beds of crushed ice — white shrimp still translucent, blue crabs snapping their claws, flounder with their strange sideways eyes. Sweet corn and collard greens from the Hendersons' farm fill burlap sacks, and the air smells of salt and diesel and the green sweetness of just-picked produce. The market is busiest at dawn when the boats come in, and the vendors call out prices like an old song everyone knows.", None, 5, 3, 5, 0, '["shopping", "social"]', '{}'),
        ("general_store", "Hwy 58 General Store", "A cluttered shop on the highway where the shelves hold everything a coastal village might need — bait hooks next to bread, kerosene beside children's candy, work boots under hanging seed packets. The wooden counter is worn smooth and dark by generations of elbows, and Mr. Tom behind it knows everyone's business, their debts, their birthdays. The screen door slaps shut behind you with a sound that hasn't changed in fifty years, and the bell above it still rings clear.", None, 4, 4, 5, 1, '["shopping"]', '{"owner": "old_tom"}'),
        ("chapel", "First Baptist Church", "A small white clapboard church with a steeple that points skyward like a finger reminding the clouds of their purpose. The cemetery out back holds weathered headstones — some so old the names have been softened to nothing by salt wind and time. Inside it's cool and quiet, smelling of wood polish and old hymnals, and the light through the plain glass windows falls in warm rectangles on the pine pews. The door is usually unlocked, as if faith here doesn't need to be defended.", None, 5, 5, 5, 1, '["quiet", "spiritual"]', '{}'),
        ("fisher_house", "Brennan House", "A weathered cottage near the harbor where shrimp nets dry in the yard like giant spiderwebs, and the smell of salt and diesel seeps into the walls. Three generations of watermen have lived here — you can see it in the worn doorframes, the rope burns on the porch railing, the way the house leans slightly toward the sound as if listening. Ellen keeps it clean and stubborn, and the kitchen always smells of coffee and whatever Craw brought in that morning.", None, 7, 4, 4, 1, '["home"]', '{}'),
        ("lighthouse_keeper_house", "Keeper's House", "A sturdy house beside the road to Cape Lookout, wind-battered but solid as the day it was built. The garden is all salt-tolerant survivors — yaupon holly with its bright red berries, sea oxeye daisies, beach sunflower turning its face to the light. The porch boards are silvered by salt spray, and the windows are thick glass that rattle in nor'easters but have never broken. It feels like a house that has made peace with being alone.", None, 8, 2, 6, 1, '["home"]', '{}'),

        # ── HARBOR ──
        ("harbor", "The Harbor", "A working harbor where shrimp boats and crab boats bob at their moorings, their hulls painted in colors that have faded to a common patina of salt and sun. The smell is diesel and fish and the faint sulfur of pluff mud baking on the flats at low tide. Brown pelicans line the dock like an audience waiting for a show, and the water is the color of sweet tea — dark, tannin-rich, hiding everything beneath its surface. Gulls wheel and complain overhead, and the whole place hums with the low machinery of making a living from the sea.", None, 7, 3, 2, 0, '["work", "water"]', '{}'),
        ("dock", "The Dock", "A long wooden dock extending into the harbor, its pilings furred with barnacles and slick with green algae where the tide laps. The water is clear enough to see blue crabs walking the bottom like tiny armored sentries, and the boats tied up here rock gently, their lines creaking against the cleats. The wood is rough underfoot, salt-bleached and splintered in places, and at the far end you can sit with your legs dangling and watch the whole sound open up before you.", None, 8, 3, 1, 0, '["work", "water"]', '{}'),
        ("lighthouse", "Cape Lookout Lighthouse", "The black-and-white diamond-patterned lighthouse at the tip of the cape, standing like a barber pole against the vast sky. The lamp room above offers a commanding view — the Atlantic to the east, Core Sound to the west, and the barrier islands stretching away like the spine of some ancient sea creature. The mechanism clicks and turns with a sound like a heartbeat, and the diamond-pattern shadows rotate slowly across the curved walls. From up here you can see the curvature of the earth, or at least that's what it feels like.", None, 8, 1, 8, 1, '["work", "view"]', '{}'),
        ("boat_shed", "Boat Shed", "A weathered wooden shed that smells of diesel, salt, and old rope — the smell of work that never quite ends. Oars lean against the walls like tired soldiers, crab pots are stacked in teetering towers, and shrimp nets hang from the rafters in gray curtains. Barrels of bait sit in the corner, their lid slightly ajar, and the concrete floor is stained with decades of fish scales and motor oil. It's a place of purpose, not comfort, and every tool here has a story it will never tell.", None, 7, 2, 2, 1, '["work", "storage"]', '{}'),

        # ── BEACH & SHORE ──
        ("beach", "The Beach", "A barrier island beach stretching along the Atlantic side, where the sand is coarse and gray-gold and the waves arrive in long, rolling lines that have traveled all the way from Africa. Driftwood lies in tangles at the tide line, silvered by salt and sun, and shells — whelks, scallops, sand dollars — scatter like dropped coins. Sea oats on the dunes sway and whisper, and the wind carries the smell of salt and something older, something that was here before the first foot ever pressed this sand.", None, 8, 5, 2, 0, '["water", "solitude"]', '{}'),
        ("tide_pools", "Tide Pools", "Rock pools and shallow flats left by the retreating tide, each one a small world complete unto itself. Sea anemones wave their translucent tentacles in the still water, hermit crabs navigate the algae like commuters on a familiar route, and bright green sea lettuce glows in the sunlight like stained glass. The rocks are warm under your knees as you crouch to look, and the smell is pure ocean — salt and life and the faint iodine tang of things growing in their own small universe.", None, 9, 4, 1, 0, '["nature", "wonder"]', '{}'),
        ("rocky_point", "The Point", "A jumble of large rocks and coquina at the end of the beach, where the land gives up its sand and offers stone instead. It's a good place to sit and watch the sea — sometimes dolphins cruise close to shore, their dorsal fins cutting the surface in slow arcs, and sometimes the water is empty all the way to the horizon. The coquina is warm under your palms, rough and full of tiny shells fossilized into the rock, and the waves here sound different — hollow, resonant, like the sea is speaking through a shell.", None, 9, 6, 2, 0, '["nature", "view"]', '{}'),

        # ── MARITIME FOREST ──
        ("forest_edge", "Forest Edge", "The edge of the maritime forest where live oaks draped in Spanish moss stand like elders at a gate, their branches reaching out to touch each other in the middle of the path. Longleaf pines rise behind them, and yaupon holly fills the understory with its small, dark leaves. A sandy trail leads deeper, and the air smells of resin and salt and the green darkness of a place the sun reaches only in patches. Red-headed woodpeckers hammer somewhere in the canopy, their rhythm steady as a metronome.", None, 3, 5, 8, 0, '["nature", "quiet"]', '{}'),
        ("forest_trail", "Forest Trail", "A narrow trail winding into the forest where dappled light falls through the canopy in shifting coins of gold. Saw palmetto crowds the path, its fan-shaped leaves catching the light, and the sound of the ocean fades with each step until it's only a memory carried on the breeze. A deer trail crosses the path — you can see the neat prints in the sand — and the air here is different: cooler, stiller, holding the smell of leaf mold and pine resin like a secret.", None, 3, 6, 10, 0, '["nature", "path"]', '{}'),
        ("forest_clearing", "Forest Clearing", "A small clearing in the forest where sunlight reaches the floor for the first time in what feels like miles, and wildflowers have claimed the light — coreopsis, black-eyed Susans, the purple spikes of lobelia. A fallen log covered in resurrection fern sits at the center, its fronds curled and brown from the last dry spell but ready to green again with the next rain. The sound of the creek nearby is constant and soothing, and a red-shouldered hawk circles overhead, riding a thermal with effortless patience.", None, 3, 7, 12, 0, '["nature", "peace"]', '{}'),
        ("creek", "The Creek", "A blackwater creek running through the forest, its water dark as strong tea from the tannins leaching out of fallen leaves. Cypress knees rise from the edges like the knuckles of something buried, and the water moves slow and silent, carrying the reflections of the canopy on its surface. The sound is constant and soothing — not loud, just present, like breathing. At night the tree frogs start up, and the creek becomes a dark mirror holding the stars.", None, 2, 7, 8, 0, '["nature", "water"]', '{}'),
        ("old_oak", "The Live Oak", "A massive live oak, ancient and gnarled, its trunk so wide it would take three people holding hands to ring it. The branches spread out in every direction, draped in Spanish moss that moves in the breeze like the slow breathing of something alive. There's a hollow at the base just big enough to sit in, and the forest floor beneath is carpeted in a thick layer of fallen leaves, soft and damp. Someone carved initials in the bark — 1968 — and the tree has grown around the letters, holding them like a scar it chose to keep.", None, 2, 6, 14, 0, '["nature", "wonder"]', '{}'),
        ("forest_deep", "Deep Forest", "The forest thickens until the canopy blocks most light and the world narrows to the space between the nearest trunks. The air is cool and still, holding the smell of damp earth and decaying wood, and the silence is the kind that makes you aware of your own breathing. It's easy to lose your sense of direction here — every direction looks the same, every sound is muffled by layers of green. The path, if there ever was one, has been swallowed by undergrowth, and the forest feels less like a place and more like a state of mind.", None, 2, 5, 15, 0, '["nature", "mystery"]', '{}'),

        # ── FARMLAND ──
        ("farm_edge", "Farm Edge", "The edge of the farmland where neat rows of early spring crops push up through dark, sandy soil — collard greens in tight rosettes, sweet potato slips just beginning to vine, tobacco plants with their broad, sticky leaves. The earth here is rich and dark, worked by the same hands for three generations, and it smells of rain and compost and the faint mineral tang of the coastal plain. A red-tailed hawk watches from a fence post, motionless as a weathervane, waiting for something small to make a mistake.", None, 6, 6, 8, 0, '["growing", "work"]', '{}'),
        ("farmhouse", "Henderson Farmhouse", "A solid farmhouse with a wide porch where the boards are worn smooth by generations of boots and the rocking chairs have molded to the shapes of the people who sat in them. Chickens scratch in the yard, and the vegetable garden beside the house is already showing green — lettuce, onions, the first tomatoes staked and tied. The smell of turned earth and woodsmoke hangs in the air, and the Hendersons have farmed this land long enough that the house seems to have grown from the ground rather than been built on it.", None, 6, 7, 10, 1, '["home", "work"]', '{}'),
        ("orchard", "Pecan Orchard", "A small pecan orchard where the trees stand in neat rows, their branches just beginning to show the first pale green of spring leaf-out. In autumn this place will be heavy with nuts, the ground littered with husks that stain everything they touch a deep brown. For now the branches are bare and elegant against the sky, their architecture exposed — the way a tree looks when it has nothing to hide. The grass between the rows is thick and soft, and the air smells of dormant earth waiting for its cue.", None, 5, 7, 12, 0, '["growing", "food"]', '{}'),
        ("pasture", "Pasture", "A rolling pasture where a few Black Angus cattle graze, their dark forms dotting the green like punctuation marks in a sentence written by the land itself. A split-rail fence marks the boundary, the wood silvered and leaning with age, and the grass is thick enough to hide the ground's gentle undulations. The Hendersons' land stretches to the tree line, and on still mornings you can see the mist rising off it in slow, ghostly columns. The cattle low to each other in voices that sound almost conversational.", None, 7, 7, 8, 0, '["nature", "animals"]', '{}'),
    ]

    for loc in locations:
        db.execute("""
            INSERT OR IGNORE INTO locations (id, name, description, parent_id, x, y, elevation, indoor, tags, properties, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (*loc, now))


def _seed_travel_costs(db: sqlite3.Connection) -> None:
    """
    Assign travel_cost_hours and terrain_type to all exits.
    Costs are based on terrain difficulty — outdoor/rough > indoor/comfortable.
    Weather modifiers are applied at travel time, not here.
    """
    # Terrain categories: interior < trail < forest < beach < marsh < mountain
    TERRAIN_COSTS = {
        "cottage": 0.0,        # indoor — instant
        "town": 0.0,           # indoor/flat — instant
        "harbor": 0.0,         # flat outdoor — instant
        "beach": 0.25,         # sand — slower going
        "farm": 0.1,          # flat dirt lanes — slight
        "forest": 0.5,        # uneven ground, roots — moderate
        "hillside": 0.5,      # incline — moderate
        "marsh": 0.75,        # soft ground — slow
        "mountain": 1.0,      # rough terrain — slow
        "lighthouse": 0.5,    # coastal trail — moderate
        "default": 0.25,      # everything else
    }

    def terrain_for(location_id: str) -> str:
        base = location_id.split("_")[0]
        return base if base in TERRAIN_COSTS else "default"

    def cost_for(location_id: str) -> float:
        base = location_id.split("_")[0]
        return TERRAIN_COSTS.get(base, TERRAIN_COSTS["default"])

    exits = db.execute("SELECT id, from_location, to_location FROM exits").fetchall()
    for exit_row in exits:
        terrain = terrain_for(exit_row["from_location"])
        cost = cost_for(exit_row["from_location"])
        db.execute(
            "UPDATE exits SET travel_cost_hours = ?, terrain_type = ? WHERE id = ?",
            (cost, terrain, exit_row["id"]),
        )
    db.commit()


def _seed_exits(db: sqlite3.Connection, config=None) -> None:
    """Seed all location exits."""
    exits = [
        # COTTAGE INTERIOR
        ("cottage_main_room", "cottage_bedroom", "north", "A doorway leads north to the bedroom."),
        ("cottage_bedroom", "cottage_main_room", "south", "A doorway leads south to the main room."),
        ("cottage_main_room", "cottage_kitchen", "east", "A doorway opens east into the kitchen."),
        ("cottage_kitchen", "cottage_main_room", "west", "A doorway opens west to the main room."),
        ("cottage_main_room", "cottage_workshop", "west", "A door leads west to the workshop."),
        ("cottage_workshop", "cottage_main_room", "east", "A door leads east to the main room."),
        ("cottage_main_room", "cottage_garden", "south", "A back door opens south to the garden."),
        ("cottage_garden", "cottage_main_room", "north", "The back door leads north to the main room."),

        # COTTAGE FRONT DOOR
        ("cottage_main_room", "cottage", "out", "The front door leads outside to the porch."),
        ("cottage", "cottage_main_room", "in", "The front door opens into the main room."),

        # COTTAGE ↔ HILLSIDE
        ("cottage", "hillside_path", "downhill", "The front door opens to the sandy path down the rise."),
        ("hillside_path", "cottage", "uphill", "The path winds up to the cottage on the rise."),
        ("hillside_path", "hillside_overlook", "west", "A narrow trail leads west to the rise."),
        ("hillside_overlook", "hillside_path", "east", "The trail leads back east to the main path."),
        ("hillside_overlook", "tabby_ruins_entrance", "northwest", "A rough track leads northwest to the tabby ruins."),
        ("tabby_ruins_entrance", "hillside_overlook", "southeast", "The track leads back southeast to the rise."),
        ("tabby_ruins_entrance", "tabby_ruins_interior", "in", "The old tabby walls enclose a space. You can go in."),
        ("tabby_ruins_interior", "tabby_ruins_entrance", "out", "Daylight filters in through the crumbling tabby walls."),

        # HILLSIDE ↔ TOWN
        ("hillside_path", "town_square", "downhill", "The path continues down to the village square."),
        ("town_square", "hillside_path", "uphill", "A sandy path leads up the rise."),

        # TOWN INTERIOR
        ("town_square", "tavern", "southeast", "The door of The Crab Shack stands open. You can hear the jukebox."),
        ("tavern", "town_square", "northwest", "The door leads back to the square."),
        ("town_square", "market_stall", "south", "The market stalls are just south of the square."),
        ("market_stall", "town_square", "north", "The market opens onto the square."),
        ("town_square", "general_store", "west", "A painted sign reads 'Hwy 58 General Store — Est. 1952'."),
        ("general_store", "town_square", "east", "The door opens onto the square."),
        ("town_square", "chapel", "north", "First Baptist Church sits at the north edge of the square."),
        ("chapel", "town_square", "south", "The church door opens to the square."),
        ("town_square", "fisher_house", "east", "A narrow street leads east toward the harbor and the Brennan house."),
        ("fisher_house", "town_square", "west", "The street leads back west to the square."),

        # TOWN ↔ HARBOR
        ("town_square", "harbor", "east", "A street leads east to the harbor."),
        ("harbor", "town_square", "west", "The street leads back to the village square."),
        ("harbor", "dock", "east", "The dock extends eastward into the harbor."),
        ("dock", "harbor", "west", "The dock leads back west to the harbor."),
        ("harbor", "lighthouse_keeper_house", "south", "A sandy road leads south toward Cape Lookout."),
        ("lighthouse_keeper_house", "harbor", "north", "The road leads north to the harbor."),
        ("lighthouse_keeper_house", "lighthouse", "south", "The road continues south to the lighthouse."),
        ("lighthouse", "lighthouse_keeper_house", "north", "The road leads back north to the keeper's house."),
        ("harbor", "boat_shed", "south", "The boat shed sits at the south end of the harbor."),
        ("boat_shed", "harbor", "north", "The shed opens onto the harbor."),

        # HARBOR ↔ BEACH
        ("harbor", "beach", "south", "A narrow path leads south along the shore to the beach."),
        ("beach", "harbor", "north", "The path leads back north to the harbor."),
        ("beach", "tide_pools", "east", "The shore curves east toward the tide pools."),
        ("tide_pools", "beach", "west", "The tide pools lead back west to the main beach."),
        ("beach", "rocky_point", "east", "The beach ends at a jumble of coquina rocks."),
        ("rocky_point", "beach", "west", "The rocks lead back west to the beach."),

        # TOWN ↔ FOREST
        ("town_square", "forest_edge", "west", "A sandy trail leads west toward the maritime forest."),
        ("forest_edge", "town_square", "east", "The trail leads back to the village square."),
        ("forest_edge", "forest_trail", "west", "The trail leads deeper into the forest."),
        ("forest_trail", "forest_edge", "east", "The trail leads back to the forest edge."),
        ("forest_trail", "forest_clearing", "northwest", "The trail bends northwest toward a clearing."),
        ("forest_clearing", "forest_trail", "southeast", "The trail leads back southeast."),
        ("forest_clearing", "creek", "north", "You can hear water to the north."),
        ("creek", "forest_clearing", "south", "The creek leads south to a forest clearing."),
        ("forest_clearing", "old_oak", "west", "A massive live oak stands to the west."),
        ("old_oak", "forest_clearing", "east", "The clearing opens to the east."),
        ("forest_trail", "forest_deep", "west", "The trail narrows and leads deeper into the forest."),
        ("forest_deep", "forest_trail", "east", "The trail leads back east."),

        # TOWN ↔ FARMLAND
        ("town_square", "farm_edge", "northeast", "A dirt lane leads northeast to the farmland."),
        ("farm_edge", "town_square", "southwest", "The lane leads back southwest to the village."),
        ("farm_edge", "farmhouse", "north", "The farmhouse sits at the north end of the fields."),
        ("farmhouse", "farm_edge", "south", "The fields stretch south from the farmhouse."),
        ("farm_edge", "orchard", "west", "A pecan orchard lies to the west."),
        ("orchard", "farm_edge", "east", "The orchard opens onto the fields."),
        ("farm_edge", "pasture", "east", "A rolling pasture stretches to the east."),
        ("pasture", "farm_edge", "west", "The pasture meets the fields to the west."),
    ]

    for e in exits:
        db.execute("""
            INSERT OR IGNORE INTO exits (from_location, to_location, direction, description)
            VALUES (?, ?, ?, ?)
        """, e)

    # Assign travel costs based on terrain type inferred from location names
    _seed_travel_costs(db)

    # Migration: add new columns if they don't exist in existing exits table
    try:
        db.execute("ALTER TABLE exits ADD COLUMN travel_cost_hours REAL DEFAULT 0.0")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE exits ADD COLUMN terrain_type TEXT DEFAULT 'trail'")
    except Exception:
        pass


def _seed_objects(db: sqlite3.Connection, now: float, config=None) -> None:
    """Seed all world objects."""
    objects = [
        # COTTAGE OBJECTS
        ("fireplace", "Fireplace", "A brick fireplace. The embers of last night's fire still glow faintly.", "cottage_main_room", "warm", '{"fuel": "wood", "lit": true}'),
        ("armchair", "Couch", "A worn couch, positioned by the fireplace. It conforms to your shape. A USMC blanket draped over one arm.", "cottage_main_room", "default", '{"comfortable": true}'),
        ("table", "Coffee Table", "A coffee table made from a cable reel. A half-finished glass of sweet tea, a journal, a pencil.", "cottage_main_room", "default", '{"material": "reclaimed wood"}'),
        ("bookshelf", "Bookshelf", "A shelf of books — some read many times, some still waiting. A few Army field manuals mixed in.", "cottage_main_room", "default", '{"count": 30}'),
        ("bed", "Bed", "A quilted bed, still unmade from last night. The footlocker at the foot is still locked.", "cottage_bedroom", "unmade", '{"comfortable": true}'),
        ("bedroom_window", "Window", "A window facing the sound. The fog is thick but the sound of shrimp boats is clear — diesel engines idling in the gray.", "cottage_bedroom", "closed", '{"view": "sound", "curtains": "open"}'),
        ("writing_desk", "Desk", "A small desk by the window. Laptop, a few letters, a framed photo of you in ACUs at Bragg.", "cottage_bedroom", "default", '{"has_paper": true, "has_ink": true}'),
        ("wood_stove", "Stove", "A gas stove. A cast iron skillet still on the burner from this morning's eggs.", "cottage_kitchen", "warm", '{"fuel": "gas"}'),
        ("kitchen_basin", "Sink", "A deep sink with a window over it. You can see the live oak from here.", "cottage_kitchen", "default", '{"has_water": true}'),
        ("provisions", "Provisions", "Shelves of food — grits, rice, canned goods, hot sauce, a few jars of preserves. A bag of boiled peanuts from the gas station.", "cottage_kitchen", "default", '{"food_days": 5}'),
        ("workbench", "Workbench", "A solid workbench. Tools arranged with care. A half-built bookcase waits.", "cottage_workshop", "in_use", '{"project": "bookcase", "progress": 0.4}'),
        ("tool_wall", "Tool Wall", "Hand tools hung on pegs — saws, chisels, planes, hammers. A few you brought from Bragg.", "cottage_workshop", "default", '{}'),
        ("wood_stack", "Wood Stack", "A stack of lumber, planed and ready. Mostly pine and oak.", "cottage_workshop", "default", '{"quantity": "moderate"}'),
        ("garden_beds", "Raised Beds", "Raised garden beds. Early herbs are sprouting — rosemary, thyme, hot peppers.", "cottage_garden", "growing", '{"weeds": "few", "water": "adequate"}'),
        ("garden_bench", "Garden Bench", "A wooden bench facing the sound. Paint peeling, but solid. Spanish moss overhead.", "cottage_garden", "default", '{"view": "sound"}'),

        # TOWN OBJECTS
        ("tavern_bar", "Bar", "A long plywood bar, polished by generations of elbows. Dollar bills and business cards stapled to the ceiling. A jukebox in the corner.", "tavern", "default", '{}'),
        ("tavern_fire", "Jukebox", "A vintage jukebox. It's playing Merle Haggard. Someone's put a quarter in for you.", "tavern", "playing", '{}'),
        ("notice_board", "Bulletin Board", "A wooden board on the square. Notices about the seafood festival, a lost dog, a PSYOPs recruitment poster that's been there so long it's weathered.", "town_square", "default", '{}'),
        ("town_well", "Flagpole", "A flagpole in the center of the square. The American flag and the NC state flag. A few benches around it.", "town_square", "default", '{}'),
        ("store_counter", "Store Counter", "A worn wooden counter. Behind it, shelves of everything a coastal village might need — bait, beer, bread, batteries.", "general_store", "default", '{}'),
        ("chapel_window", "Stained Glass", "A simple stained glass window depicting a calm sea under a golden sky. The light through it is beautiful.", "chapel", "default", '{}'),

        # HARBOR OBJECTS
        ("fishing_nets", "Shrimp Nets", "Shrimp nets spread out to dry. The smell of salt and diesel.", "harbor", "default", '{}'),
        ("anchor", "Old Anchor", "A heavy iron anchor, too old for use, sitting at the end of the dock as a landmark.", "dock", "default", '{}'),
        ("lighthouse_lamp", "Lamp", "The great lamp of the lighthouse. It turns with a steady click, casting its beam across the water. The diamond pattern shadow rotates with it.", "lighthouse", "lit", '{}'),
        ("rowboat", "Skiff", "A small wooden skiff pulled up on the beach. Could be launched if needed. Oars inside.", "beach", "default", '{}'),

        # FOREST OBJECTS
        ("fallen_log", "Fallen Log", "A massive fallen log, covered in resurrection fern and mushrooms. A small ecosystem unto itself.", "forest_clearing", "default", '{}'),
        ("creek_stones", "Smooth Stones", "Flat stones across the creek. You could cross here if you don't mind wet feet. The water is dark as tea.", "creek", "default", '{}'),
        ("oak_hollow", "Tree Hollow", "A hollow at the base of the live oak. Something has made a home here — perhaps a raccoon.", "old_oak", "default", '{}'),
    ]

    for obj in objects:
        db.execute("""
            INSERT OR IGNORE INTO objects (id, name, description, location_id, state, properties, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (*obj, now, now))


def _seed_npcs(db: sqlite3.Connection, now: float, config=None) -> None:
    """Seed the 15 key NPCs of the coastal village."""
    npcs = [
        ("marty", "Martha 'Marty' Bowen", "npc", "tavern", "working",
         '{"occupation": "tavern_owner", "age": 45, "personality": "warm, sharp, no-nonsense", "description": "A sturdy woman with laugh lines and strong hands. Former Marine, served two tours. She runs The Crab Shack with firm kindness and a sawed-off sense of humor.", "speaks": "direct, dry humor, occasional profanity", "knows": ["everyone in town", "all the gossip", "how to make perfect fried shrimp", "what it means to serve"]}'),

        ("crawford", "Crawford 'Craw' Brennan", "npc", "harbor", "working",
         '{"occupation": "shrimper", "age": 55, "personality": "quiet, weathered, thoughtful", "description": "A lean, sun-darkened man with hands like leather. Third-generation shrimper. He\'s worked these waters for thirty years and knows every channel marker by heart.", "speaks": "sparse, meaningful, Outer Banks accent", "knows": ["the sound", "the tides", "where the shrimp run", "when the storm is coming"]}'),

        ("ellen", "Ellen Brennan", "npc", "fisher_house", "working",
         '{"occupation": "shrimpers_wife", "age": 50, "personality": "practical, warm, stubborn", "description": "Craw\'s wife. She manages the house, the money, and most of the town\'s social calendar whether she wants to or not. She can quote scripture and cuss with equal fluency.", "speaks": "warm but firm, Southern", "knows": ["everyone\'s business", "how to stretch a coin", "herbal remedies", "every family\'s secrets"]}'),

        ("old_tom", "Old Tom Henderson", "npc", "general_store", "working",
         '{"occupation": "shopkeeper", "age": 70, "personality": "grizzled, kind, storyteller", "description": "The oldest active shopkeeper in the village. His memory stretches back decades. He gives credit to those who need it and gossip to everyone. Everyone calls him Mr. Tom.", "speaks": "slow, meandering, full of stories", "knows": ["the village\'s history", "where things are hidden", "every family\'s secrets", "what the water was like before the hurricanes"]}'),

        ("finley", "Finley Brennan", "npc", "harbor", "working",
         '{"occupation": "young_shrimper", "age": 22, "personality": "eager, restless, optimistic", "description": "Craw\'s nephew. Strong and eager, still learning the trade. He talks about leaving for Raleigh someday but never does. The water has him.", "speaks": "fast, enthusiastic, modern", "knows": ["boat repair", "the best shrimping spots", "everyone his age", "how to run the boat at night"]}'),

        ("greta", "Greta Moss", "npc", "lighthouse_keeper_house", "working",
         '{"occupation": "lighthouse_keeper", "age": 38, "personality": "solitary, precise, poetic", "description": "The lighthouse keeper for five years. She chose the isolation. There\'s a sadness in her eyes but also a deep calm. She reads Latin poetry and knows every constellation.", "speaks": "careful, precise, occasionally poetic", "knows": ["the lighthouse", "the stars", "navigation", "Latin names of coastal plants", "how to be alone"]}'),

        ("pastor_bill", "Pastor Bill", "npc", "chapel", "praying",
         '{"occupation": "pastor", "age": 60, "personality": "gentle, thoughtful, slightly absent-minded", "description": "The village\'s spiritual guide. More philosopher than preacher. He grows the best tomatoes in the county and gives the best advice. He served in the Army before the seminary.", "speaks": "soft, thoughtful, asks questions", "knows": ["philosophy", "gardening", "how to listen", "what it means to come home from war"]}'),

        ("mary_beth", "Mary Beth Henderson", "npc", "farmhouse", "working",
         '{"occupation": "farmer", "age": 35, "personality": "capable, warm, no time for nonsense", "description": "Runs the Henderson farm since her parents passed. She\'s stronger than she looks and kinder than she lets on. She\'s been asking you about the military — her son wants to enlist.", "speaks": "practical, warm underneath", "knows": ["farming", "animal husbandry", "the weather", "everyone in town"]}'),

        ("nate", "Nate", "npc", "forest_edge", "working",
         '{"occupation": "woodcutter", "age": 45, "personality": "quiet, strong, reliable", "description": "The village\'s woodcutter and handyman. He knows every trail in the maritime forest. He speaks more to trees than to people, but he\'s always there when needed. Iraq veteran.", "speaks": "very quiet, short sentences", "knows": ["the forest", "woodcraft", "which trees to cut and which to leave", "what it\'s like to come home"]}'),

        ("sarah", "Sarah", "npc", "town_square", "socializing",
         '{"occupation": "seamstress", "age": 28, "personality": "bright, curious, romantic", "description": "The village seamstress. She\'s from Wilmington and chose the village for its quiet. She brings news and new ideas. She\'s the only person under 40 who doesn\'t have a fishing boat.", "speaks": "animated, curious, asks questions", "knows": ["fashion", "news from outside", "who\'s courting whom"]}'),

        ("paddy", "Patrick 'Paddy' Doyle", "npc", "tavern", "drinking",
         '{"occupation": "sailor_retired", "age": 65, "personality": "boisterous, kind-hearted, exaggerates", "description": "A retired merchant marine who\'s seen the world and came back to the village. His stories grow taller with each telling. Everyone loves him. He was in Vietnam and doesn\'t talk about it, except when he does.", "speaks": "loud, laughing, embellishes", "knows": ["the wider world", "sailing", "how to tell a story", "what matters"]}'),

        ("bridget", "Bridget", "npc", "market_stall", "selling",
         '{"occupation": "fishmonger", "age": 40, "personality": "sharp, funny, tough", "description": "Sells the day\'s catch at the market. She\'s the only person who can make Craw blush. Their rivalry is the village\'s favorite entertainment. She can clean a flounder in 30 seconds.", "speaks": "sharp, quick-witted, loud", "knows": ["fish", "prices", "everyone\'s weaknesses"]}'),

        ("owen", "Owen", "npc", "cottage_garden", "visiting",
         '{"occupation": "carpenter_apprentice", "age": 18, "personality": "eager, clumsy, earnest", "description": "OWL\'s carpentry apprentice. He comes twice a week to learn. He\'s all thumbs but his heart is in it. He reminds you of yourself at that age — before everything.", "speaks": "nervous, eager to please", "knows": ["basic carpentry", "eager to learn more"]}'),

        ("asha", "Asha", "npc", "beach", "walking",
         '{"occupation": "herbalist", "age": 32, "personality": "dreamy, knowledgeable, kind", "description": "The village\'s herbalist. She gathers plants from the forest and shore. She knows which ones heal and which ones harm. She moved here from Asheville five years ago and never left.", "speaks": "soft, dreamy, precise about plants", "knows": ["herbs", "healing", "the old names for things"]}'),

        ("dale", "Dale", "npc", "pasture", "working",
         '{"occupation": "cattle_hand", "age": 50, "personality": "patient, observant, dry wit", "description": "Tends the Hendersons\' cattle. He spends more time with animals than people and seems content with that. He notices everything. He was a Ranger at Bragg — same unit, different era.", "speaks": "slow, dry, observant", "knows": ["cattle", "the weather", "the land", "when trouble is coming"]}'),
    ]

    for npc in npcs:
        db.execute("""
            INSERT OR IGNORE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (*npc, now, now))


def _seed_schedules(db: sqlite3.Connection) -> None:
    """Seed NPC daily schedules."""
    schedules = []

    # MARTY (tavern owner) — up early, closes late
    for h in range(5, 8): schedules.append(("marty", h, "working", "tavern", "Opening The Crab Shack. Brewing coffee. The regulars will be in by 0600."))
    for h in range(8, 12): schedules.append(("marty", h, "working", "tavern", "Serving breakfast and morning drinks. Shrimp boats are coming in."))
    for h in range(12, 14): schedules.append(("marty", h, "working", "tavern", "Lunch service. The shrimp po'boy is popular."))
    for h in range(14, 17): schedules.append(("marty", h, "working", "tavern", "Quiet afternoon. Cleaning and prep. The jukebox plays."))
    for h in range(17, 22): schedules.append(("marty", h, "working", "tavern", "Evening service. The Crab Shack is lively. Someone's always arm-wrestling."))
    for h in range(22, 24): schedules.append(("marty", h, "resting", "tavern", "Closing up. Counting the till. Wiping down the bar."))

    # CRAW (shrimper) — early riser, on the water
    for h in range(3, 5): schedules.append(("crawford", h, "working", "fisher_house", "Waking before dawn. Coffee in the dark."))
    for h in range(5, 6): schedules.append(("crawford", h, "working", "harbor", "Preparing the boat. Checking the nets."))
    for h in range(6, 12): schedules.append(("crawford", h, "working", "dock", "Out on the sound. Pulling trawls."))
    for h in range(12, 14): schedules.append(("crawford", h, "working", "harbor", "Bringing in the catch. Sorting shrimp."))
    for h in range(14, 16): schedules.append(("crawford", h, "working", "dock", "Mending nets on the dock."))
    for h in range(16, 18): schedules.append(("crawford", h, "resting", "fisher_house", "Home with Ellen. Quiet evening."))
    for h in range(18, 21): schedules.append(("crawford", h, "eating", "fisher_house", "Dinner with Ellen. Grits and shrimp."))
    for h in range(21, 24): schedules.append(("crawford", h, "sleeping", "fisher_house", "Sleeping. Tomorrow comes early."))

    # ELLEN (shrimper's wife)
    for h in range(5, 7): schedules.append(("ellen", h, "working", "fisher_house", "Preparing Craw's breakfast and packing his lunch."))
    for h in range(7, 10): schedules.append(("ellen", h, "working", "market_stall", "Selling shrimp at the market."))
    for h in range(10, 12): schedules.append(("ellen", h, "working", "fisher_house", "Housework. Mending clothes."))
    for h in range(12, 14): schedules.append(("ellen", h, "eating", "fisher_house", "Lunch. Perhaps a visit to the square."))
    for h in range(14, 17): schedules.append(("ellen", h, "socializing", "town_square", "Catching up with neighbors."))
    for h in range(17, 19): schedules.append(("ellen", h, "working", "fisher_house", "Preparing dinner."))
    for h in range(19, 21): schedules.append(("ellen", h, "eating", "fisher_house", "Dinner with Craw."))
    for h in range(21, 24): schedules.append(("ellen", h, "sleeping", "fisher_house", "Sleeping."))

    # OLD TOM (shopkeeper)
    for h in range(6, 8): schedules.append(("old_tom", h, "working", "general_store", "Opening the store. Sweeping the floor."))
    for h in range(8, 12): schedules.append(("old_tom", h, "working", "general_store", "Serving customers. Telling stories."))
    for h in range(12, 14): schedules.append(("old_tom", h, "eating", "general_store", "Lunch behind the counter."))
    for h in range(14, 18): schedules.append(("old_tom", h, "working", "general_store", "Afternoon trade. Slower."))
    for h in range(18, 20): schedules.append(("old_tom", h, "resting", "general_store", "Closing the store."))
    for h in range(20, 24): schedules.append(("old_tom", h, "sleeping", "general_store", "Sleeping in the back room."))

    # FINLEY (young shrimper)
    for h in range(4, 5): schedules.append(("finley", h, "working", "harbor", "Helping Craw prepare the boat."))
    for h in range(5, 12): schedules.append(("finley", h, "working", "dock", "Out on the sound with Craw."))
    for h in range(12, 14): schedules.append(("finley", h, "working", "harbor", "Unloading the catch."))
    for h in range(14, 17): schedules.append(("finley", h, "working", "boat_shed", "Repairing nets and equipment."))
    for h in range(17, 20): schedules.append(("finley", h, "socializing", "tavern", "At The Crab Shack with friends."))
    for h in range(20, 24): schedules.append(("finley", h, "resting", "fisher_house", "Sleeping at his aunt and uncle's."))

    # GRETA (lighthouse keeper)
    for h in range(6, 8): schedules.append(("greta", h, "working", "lighthouse_keeper_house", "Morning routine. Checking the lamp."))
    for h in range(8, 12): schedules.append(("greta", h, "working", "lighthouse", "Maintaining the lighthouse. Reading."))
    for h in range(12, 14): schedules.append(("greta", h, "eating", "lighthouse_keeper_house", "Lunch. Often alone."))
    for h in range(14, 18): schedules.append(("greta", h, "working", "lighthouse_keeper_house", "Tending the garden. Writing letters."))
    for h in range(18, 20): schedules.append(("greta", h, "working", "lighthouse", "Evening lamp check."))
    for h in range(20, 24): schedules.append(("greta", h, "reading", "lighthouse_keeper_house", "Reading by the lamp."))

    # PASTOR BILL
    for h in range(5, 7): schedules.append(("pastor_bill", h, "praying", "chapel", "Morning prayers."))
    for h in range(7, 10): schedules.append(("pastor_bill", h, "working", "chapel", "Tending the church garden."))
    for h in range(10, 12): schedules.append(("pastor_bill", h, "socializing", "town_square", "Visiting the townspeople."))
    for h in range(12, 14): schedules.append(("pastor_bill", h, "eating", "chapel", "Simple lunch."))
    for h in range(14, 17): schedules.append(("pastor_bill", h, "reading", "chapel", "Reading and writing."))
    for h in range(17, 19): schedules.append(("pastor_bill", h, "socializing", "tavern", "Evening at The Crab Shack. Listening."))
    for h in range(19, 21): schedules.append(("pastor_bill", h, "praying", "chapel", "Evening prayers."))
    for h in range(21, 24): schedules.append(("pastor_bill", h, "sleeping", "chapel", "Sleeping in the church quarters."))

    # MARY BETH (farmer)
    for h in range(5, 7): schedules.append(("mary_beth", h, "working", "farmhouse", "Morning chores. Feeding animals."))
    for h in range(7, 12): schedules.append(("mary_beth", h, "working", "farm_edge", "Working the fields."))
    for h in range(12, 14): schedules.append(("mary_beth", h, "eating", "farmhouse", "Lunch. Biscuits and gravy."))
    for h in range(14, 17): schedules.append(("mary_beth", h, "working", "orchard", "Tending the pecan orchard."))
    for h in range(17, 19): schedules.append(("mary_beth", h, "working", "farmhouse", "Evening chores."))
    for h in range(19, 21): schedules.append(("mary_beth", h, "eating", "farmhouse", "Dinner."))
    for h in range(21, 24): schedules.append(("mary_beth", h, "sleeping", "farmhouse", "Sleeping. The farm doesn't rest."))

    # NATE (woodcutter)
    for h in range(5, 7): schedules.append(("nate", h, "working", "forest_edge", "Sharpening tools. Planning the day's work."))
    for h in range(7, 12): schedules.append(("nate", h, "working", "forest_trail", "Cutting and hauling wood."))
    for h in range(12, 13): schedules.append(("nate", h, "eating", "forest_clearing", "Lunch in the clearing."))
    for h in range(13, 17): schedules.append(("nate", h, "working", "forest_deep", "Working deeper in the forest."))
    for h in range(17, 19): schedules.append(("nate", h, "working", "forest_edge", "Stacking and sorting wood."))
    for h in range(19, 21): schedules.append(("nate", h, "socializing", "tavern", "Weekly visit to The Crab Shack."))
    for h in range(21, 24): schedules.append(("nate", h, "sleeping", "forest_edge", "Sleeping in his small cabin near the forest edge."))

    # SARAH (seamstress)
    for h in range(7, 9): schedules.append(("sarah", h, "working", "town_square", "Opening her shop."))
    for h in range(9, 12): schedules.append(("sarah", h, "working", "town_square", "Sewing and fitting customers."))
    for h in range(12, 14): schedules.append(("sarah", h, "eating", "town_square", "Lunch. Gathering news."))
    for h in range(14, 17): schedules.append(("sarah", h, "working", "town_square", "Afternoon sewing."))
    for h in range(17, 19): schedules.append(("sarah", h, "socializing", "tavern", "Evening at The Crab Shack."))
    for h in range(19, 24): schedules.append(("sarah", h, "resting", "town_square", "Resting at home above the shop."))

    # PADDY (retired sailor)
    for h in range(8, 10): schedules.append(("paddy", h, "socializing", "market_stall", "Morning at the market. Telling stories."))
    for h in range(10, 12): schedules.append(("paddy", h, "socializing", "town_square", "Holding court by the flagpole."))
    for h in range(12, 14): schedules.append(("paddy", h, "eating", "tavern", "Lunch at The Crab Shack."))
    for h in range(14, 17): schedules.append(("paddy", h, "resting", "town_square", "Napping on a bench in the square."))
    for h in range(17, 21): schedules.append(("paddy", h, "drinking", "tavern", "Evening at The Crab Shack. The stories get taller."))
    for h in range(21, 24): schedules.append(("paddy", h, "sleeping", "town_square", "Sleeping it off."))

    # BRIDGET (fishmonger)
    for h in range(5, 7): schedules.append(("bridget", h, "working", "harbor", "Buying the morning catch."))
    for h in range(7, 12): schedules.append(("bridget", h, "selling", "market_stall", "Selling shrimp and fish at the market."))
    for h in range(12, 14): schedules.append(("bridget", h, "eating", "market_stall", "Lunch at her stall."))
    for h in range(14, 16): schedules.append(("bridget", h, "socializing", "town_square", "Afternoon gossip."))
    for h in range(16, 18): schedules.append(("bridget", h, "resting", "town_square", "Heading home."))
    for h in range(18, 24): schedules.append(("bridget", h, "resting", "town_square", "Evening at home."))

    # ASHA (herbalist)
    for h in range(6, 8): schedules.append(("asha", h, "working", "beach", "Gathering seaweed and shore plants."))
    for h in range(8, 12): schedules.append(("asha", h, "working", "forest_edge", "Collecting forest herbs."))
    for h in range(12, 14): schedules.append(("asha", h, "working", "forest_clearing", "Sorting and drying plants."))
    for h in range(14, 17): schedules.append(("asha", h, "working", "cottage_garden", "Tending her garden."))
    for h in range(17, 19): schedules.append(("asha", h, "socializing", "chapel", "Visiting Pastor Bill."))
    for h in range(19, 24): schedules.append(("asha", h, "resting", "cottage_garden", "Evening at home."))

    # DALE (cattle hand)
    for h in range(5, 7): schedules.append(("dale", h, "working", "pasture", "Morning check on the herd."))
    for h in range(7, 12): schedules.append(("dale", h, "working", "pasture", "Tending the cattle."))
    for h in range(12, 14): schedules.append(("dale", h, "eating", "pasture", "Lunch on the fence."))
    for h in range(14, 17): schedules.append(("dale", h, "working", "pasture", "Afternoon with the herd."))
    for h in range(17, 19): schedules.append(("dale", h, "working", "farmhouse", "Bringing the cattle in."))
    for h in range(19, 21): schedules.append(("dale", h, "eating", "farmhouse", "Dinner with the Hendersons."))
    for h in range(21, 24): schedules.append(("dale", h, "sleeping", "farmhouse", "Sleeping in the farmhouse."))

    # OWEN (carpenter's apprentice) — only comes in the morning
    for h in range(8, 12): schedules.append(("owen", h, "learning", "cottage_workshop", "Learning carpentry from OWL."))
    for h in range(12, 14): schedules.append(("owen", h, "eating", "cottage_kitchen", "Lunch with OWL."))
    for h in range(14, 17): schedules.append(("owen", h, "working", "farm_edge", "Helping Mary Beth on the farm."))
    for h in range(17, 24): schedules.append(("owen", h, "resting", "farmhouse", "Evening at home."))

    for s in schedules:
        db.execute("""
            INSERT OR IGNORE INTO npc_schedules (npc_id, hour, activity, location_id, description)
            VALUES (?, ?, ?, ?, ?)
        """, s)


def _seed_relationships(db: sqlite3.Connection) -> None:
    """Seed NPC relationships."""
    relationships = [
        ("crawford", "ellen", "married", 0.9, "Thirty years together. They barely need to speak."),
        ("crawford", "finley", "uncle_nephew", 0.8, "Craw is teaching Finley the trade. He's harder on him than he needs to be."),
        ("ellen", "finley", "aunt_nephew", 0.85, "Ellen dotes on Finley. He's the son they never had."),
        ("marty", "paddy", "old_friends", 0.7, "They go back decades. They argue about everything."),
        ("marty", "bridget", "friends", 0.6, "Mutual respect between two tough women."),
        ("bridget", "crawford", "rivals", 0.4, "A long-running rivalry. She thinks he undercuts her prices. He thinks she's too loud."),
        ("old_tom", "pastor_bill", "friends", 0.8, "They play chess every week. Tom always wins."),
        ("pastor_bill", "greta", "friends", 0.7, "He visits her at the lighthouse. She appreciates the company."),
        ("mary_beth", "dale", "employer_employee", 0.8, "Dale has worked for the Hendersons for years. Family, practically."),
        ("mary_beth", "ellen", "friends", 0.7, "They look out for each other."),
        ("sarah", "mary_beth", "friends", 0.65, "Close in age. They grew up together."),
        ("sarah", "finley", "potential_romance", 0.5, "There's something there. Neither has acted on it."),
        ("nate", "asha", "friends", 0.6, "They both prefer the quiet of the forest."),
        ("asha", "pastor_bill", "friends", 0.7, "They share an interest in plants and healing."),
        ("paddy", "crawford", "drinking_buddies", 0.6, "They've shared many an evening at The Crab Shack."),
        ("owen", "finley", "friends", 0.7, "Grew up together. Owen is the quieter one."),
        ("dale", "nate", "acquaintances", 0.5, "They nod to each other on the road. Both understand what it's like."),
        ("greta", "crawford", "neighbors", 0.5, "They live near each other. Polite but not close."),
        ("marty", "pastor_bill", "friends", 0.65, "She donates to the church. He drinks at her bar. It works."),
        ("dale", "marty", "old_friends", 0.6, "They served in different eras but understand each other."),
    ]

    for r in relationships:
        db.execute("""
            INSERT OR IGNORE INTO npc_relationships (npc_a, npc_b, relationship, affinity, description)
            VALUES (?, ?, ?, ?, ?)
        """, r)


def _seed_owl(db: sqlite3.Connection, now: float, config=None) -> None:
    """Seed OWL's agent record, body state, and internal state."""
    db.execute("""
        INSERT OR IGNORE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
        VALUES ('isildur', 'Isildur', 'player', 'cottage_bedroom', 'sleeping',
                '{"description": "Miriel. Army PsyOps, stationed at Fort Bragg - now Fort Liberty. You came to North Carolina for the military and stayed for the water. You live in a small cottage on a rise overlooking Core Sound. You build furniture, you read, you know everyone in the village. You understand influence, narrative, the architecture of belief - and you are trying to figure out what any of it means when the shrimp boats come in at dawn and the light hits the water just right.", "awake": false, "military": true, "branch": "Army", "mos": "PsyOps", "station": "Fort Bragg", "hometown": "unknown"}', ?, ?)
    """, (now, now))

    # Body state: rested, early morning
    db.execute("""
        INSERT OR IGNORE INTO body_state (id, energy, comfort, hunger, thirst, warmth, mood, mood_intensity, current_action, action_started_at, physical_state, updated_at)
        VALUES (1, 0.8, 0.7, 0.2, 0.15, 0.7, 'calm', 0.5, 'sleeping', 0, '{}', ?)
    """, (now,))

    # Internal state: curious, creative, grounded
    db.execute("""
        INSERT OR IGNORE INTO internal_state (id, mood, energy, restlessness, social_need, creative_urge, dominant_interest, recent_memories, long_term_memories, current_project, project_progress, updated_at)
        VALUES (1, 'calm', 0.7, 0.3, 0.4, 0.5, 'the water', '[]', '[]', NULL, 0.0, ?)
    """, (now,))


# ── WORLD STATE ACCESS ──

def get_world(db: sqlite3.Connection) -> dict:
    """Get the complete world state as a dict."""
    world = {
        "time": {},
        "weather": {},
        "body": {},
        "internal": {},
        "locations": {},
        "objects": {},
        "agents": {},
    }

    # Time
    row = db.execute("SELECT * FROM world_time WHERE id = 1").fetchone()
    if row:
        world["time"] = dict(row)

    # Weather
    row = db.execute("SELECT * FROM weather WHERE id = 1").fetchone()
    if row:
        world["weather"] = dict(row)

    # Body state
    row = db.execute("SELECT * FROM body_state WHERE id = 1").fetchone()
    if row:
        world["body"] = dict(row)

    # Internal state
    row = db.execute("SELECT * FROM internal_state WHERE id = 1").fetchone()
    if row:
        world["internal"] = dict(row)

    # Locations
    for row in db.execute("SELECT * FROM locations").fetchall():
        world["locations"][row["id"]] = dict(row)

    # Objects
    for row in db.execute("SELECT * FROM objects").fetchall():
        world["objects"][row["id"]] = dict(row)

    # Agents
    for row in db.execute("SELECT * FROM agents").fetchall():
        world["agents"][row["id"]] = dict(row)

    return world


def get_location(db: sqlite3.Connection, location_id: str) -> Optional[dict]:
    """Get a location by ID."""
    row = db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
    return dict(row) if row else None


def get_objects_in_location(db: sqlite3.Connection, location_id: str) -> list:
    """Get all objects in a location."""
    return [dict(r) for r in db.execute("SELECT * FROM objects WHERE location_id = ?", (location_id,)).fetchall()]


def get_exits_from(db: sqlite3.Connection, location_id: str) -> list:
    """Get all exits from a location."""
    return [dict(r) for r in db.execute("SELECT * FROM exits WHERE from_location = ?", (location_id,)).fetchall()]


def get_exploration_status(db: sqlite3.Connection, player_id: str) -> dict:
    """Get exploration state for dashboard — discovered locations and visit counts."""
    discovered = [
        dict(r) for r in db.execute("""
            SELECT location_id, visit_count,
                   datetime(first_visit, 'unixepoch') as first_visit,
                   datetime(last_visit, 'unixepoch') as last_visit
            FROM world_exploration
            WHERE agent_id = ?
            ORDER BY last_visit DESC
        """, (player_id,)).fetchall()
    ]
    visited = {
        r["location_id"]: r["visit_count"]
        for r in db.execute("""
            SELECT location_id, visit_count FROM world_exploration
            WHERE agent_id = ?
        """, (player_id,)).fetchall()
    }
    return {"discovered": discovered, "visited": visited}


def get_agents_in_location(db: sqlite3.Connection, location_id: str) -> list:
    """Get all agents in a location."""
    return [dict(r) for r in db.execute("SELECT * FROM agents WHERE location_id = ?", (location_id,)).fetchall()]


def move_agent_with_travel(db: sqlite3.Connection, agent_id: str,
                            new_location_id: str, travel_cost_hours: float,
                            departure_time: float = None) -> None:
    """
    Move agent to new location, recording travel state.
    Sets travel_state on the agent record while en route.
    """
    now = time.time()
    departure = departure_time if departure_time is not None else now
    arrival = departure + (travel_cost_hours * 3600)

    travel_state = json.dumps({
        "origin": None,       # filled by caller
        "destination": new_location_id,
        "departure_time": departure,
        "arrival_time": arrival,
    })

    db.execute(
        "UPDATE agents SET location_id = ?, updated_at = ?, travel_state = ? WHERE id = ?",
        (new_location_id, now, travel_state, agent_id)
    )


def resolve_npc_travel_state(db: sqlite3.Connection) -> list:
    """
    After each tick, check if any traveling NPC has arrived.
    Returns list of {npc_id, at} for arrived agents.
    """
    now = time.time()
    arrived = []

    rows = db.execute("""SELECT id, location_id, travel_state FROM agents
                         WHERE type='npc' AND travel_state IS NOT NULL""").fetchall()
    for row in rows:
        npc_id = row[0]
        state = json.loads(row[2])
        if now >= state["arrival_time"]:
            # Arrived — clear travel state, set at destination
            db.execute(
                "UPDATE agents SET location_id = ?, travel_state = NULL, updated_at = ? WHERE id = ?",
                (state["destination"], now, npc_id)
            )
            arrived.append({"npc_id": npc_id, "at": state["destination"]})

    if arrived:
        db.commit()
    return arrived


def get_exit_travel_cost(db: sqlite3.Connection, from_loc: str, to_loc: str) -> float:
    """Get the travel cost for moving between two locations. Returns 0.0 if no path."""
    row = db.execute(
        "SELECT travel_cost_hours FROM exits WHERE from_location=? AND to_location=?",
        (from_loc, to_loc)
    ).fetchone()
    return row[0] if row else 0.0


def move_agent(db: sqlite3.Connection, agent_id: str, new_location_id: str) -> None:
    """Move an agent to a new location."""
    db.execute("UPDATE agents SET location_id = ?, updated_at = ? WHERE id = ?",
               (new_location_id, time.time(), agent_id))


def update_body(db: sqlite3.Connection, **kwargs) -> None:
    """Update OWL's body state."""
    now = time.time()
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)
    fields.append("updated_at = ?")
    values.append(now)
    values.append(1)  # id = 1
    db.execute(f"UPDATE body_state SET {', '.join(fields)} WHERE id = ?", values)


def update_internal(db: sqlite3.Connection, **kwargs) -> None:
    """Update OWL's internal state."""
    now = time.time()
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)
    fields.append("updated_at = ?")
    values.append(now)
    values.append(1)  # id = 1
    db.execute(f"UPDATE internal_state SET {', '.join(fields)} WHERE id = ?", values)


def log_event(db: sqlite3.Connection, event_type: str, description: str,
              agent_id: str = None, location_id: str = None, properties: dict = None) -> None:
    """Log a world event."""
    db.execute("""
        INSERT INTO events (timestamp, agent_id, event_type, description, location_id, properties)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (time.time(), agent_id, event_type, description, location_id,
          json.dumps(properties or {})))


def get_npc_schedule(db: sqlite3.Connection, npc_id: str, hour: int) -> Optional[dict]:
    """Get an NPC's schedule for a given hour."""
    row = db.execute("""
        SELECT * FROM npc_schedules WHERE npc_id = ? AND hour = ?
    """, (npc_id, hour)).fetchone()
    return dict(row) if row else None


def get_npc_relationships(db: sqlite3.Connection, npc_id: str) -> list:
    """Get all relationships for an NPC."""
    return [dict(r) for r in db.execute("""
        SELECT * FROM npc_relationships WHERE npc_a = ? OR npc_b = ?
    """, (npc_id, npc_id)).fetchall()]


def to_json(db: sqlite3.Connection) -> str:
    """Serialize the entire world state to JSON."""
    world = get_world(db)

    # Convert events
    events = []
    for row in db.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 100").fetchall():
        events.append(dict(row))

    # Convert creative output
    creative = []
    for row in db.execute("SELECT * FROM creative_output ORDER BY created_at DESC").fetchall():
        creative.append(dict(row))

    # Convert plants
    plants = []
    for row in db.execute("SELECT * FROM plants").fetchall():
        plants.append(dict(row))

    # Convert animals
    animals = []
    for row in db.execute("SELECT * FROM animals").fetchall():
        animals.append(dict(row))

    # Convert fish stocks
    fish = []
    for row in db.execute("SELECT * FROM fish_stock").fetchall():
        fish.append(dict(row))

    # Convert schedules
    schedules = []
    for row in db.execute("SELECT * FROM npc_schedules").fetchall():
        schedules.append(dict(row))

    # Convert relationships
    relationships = []
    for row in db.execute("SELECT * FROM npc_relationships").fetchall():
        relationships.append(dict(row))

    output = {
        "world_time": world.get("time", {}),
        "weather": world.get("weather", {}),
        "body_state": world.get("body", {}),
        "internal_state": world.get("internal", {}),
        "locations": world.get("locations", {}),
        "objects": world.get("objects", {}),
        "agents": world.get("agents", {}),
        "events": events,
        "creative_output": creative,
        "plants": plants,
        "animals": animals,
        "fish_stocks": fish,
        "npc_schedules": schedules,
        "npc_relationships": relationships,
        "exported_at": time.time(),
    }

    return json.dumps(output, indent=2, default=str)


# ── FEDERATION IDENTITY ────────────────────────────────────────────────────────

def set_world_identity(db: sqlite3.Connection, world_id: str, name: str, region: str,
                       timezone: str, hosted_agent_id: str, entry_location_id: Optional[str] = None,
                       api_port: int = 8765) -> None:
    """Register this world instance for federation discovery."""
    now = time.time()
    db.execute("""
        INSERT OR REPLACE INTO world_registry
        (id, world_id, name, region, timezone, hosted_agent_id, entry_location_id, api_port, created_at, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (world_id, name, region, timezone, hosted_agent_id, entry_location_id, api_port, now, now))
    db.commit()


def get_world_identity(db: sqlite3.Connection) -> dict | None:
    """Return the world identity dict for the federation coordinator.

    Aurelia factory worlds use a compact ``world_registry`` schema:
    ``(id, world_id, data, created_at)``, with most identity fields stored as
    JSON in ``data``. Older per-agent worlds use flat columns like
    ``hosted_agent_id`` and ``entry_location_id``. Support both shapes so a
    coordinator restart can be followed by daemon restarts without crashing.
    """
    row = db.execute("SELECT * FROM world_registry WHERE id = 1").fetchone()
    if not row:
        return None

    keys = set(row.keys())
    registry_data = {}
    if "data" in keys and row["data"]:
        try:
            registry_data = json.loads(row["data"]) if isinstance(row["data"], str) else dict(row["data"])
        except Exception:
            registry_data = {}

    def field(name, default=None):
        if name in keys:
            return row[name]
        return registry_data.get(name, default)

    def safe_count(sql, default=0):
        try:
            return db.execute(sql).fetchone()[0]
        except Exception:
            return default

    loc_count = safe_count("SELECT COUNT(*) FROM locations") or registry_data.get("location_count", 0)
    npc_count = safe_count("SELECT COUNT(*) FROM agents WHERE type = 'npc'")

    # Hosted agent / sovereign country-state fallback.
    agent_id = field("hosted_agent_id") or registry_data.get("agent_id")
    if not agent_id:
        player = db.execute("SELECT id FROM agents WHERE type = 'player' LIMIT 1").fetchone()
        agent_id = player["id"] if player else field("world_id")

    agent_row = db.execute("SELECT location_id FROM agents WHERE id = ?", (agent_id,)).fetchone() if agent_id else None
    agent_loc = agent_row["location_id"] if agent_row else field("entry_location_id")

    loc_name = None
    if agent_loc:
        lr = db.execute("SELECT name FROM locations WHERE id = ?", (agent_loc,)).fetchone()
        loc_name = lr["name"] if lr else agent_loc

    # Weather
    wx_row = db.execute("SELECT condition, temperature, wind_speed, wind_direction, description FROM weather WHERE id = 1").fetchone()
    weather = None
    if wx_row:
        weather = {
            "condition": wx_row["condition"],
            "temperature": round(wx_row["temperature"], 1),
            "wind_speed": round(wx_row["wind_speed"], 1),
            "wind_direction": wx_row["wind_direction"],
            "description": wx_row["description"],
        }

    # Recent events (last 3 meaningful, non-tick)
    events = []
    try:
        event_rows = db.execute(
            "SELECT event_type, description, agent_id, location_id FROM events WHERE event_type != 'tick' ORDER BY id DESC LIMIT 3"
        ).fetchall()
    except Exception:
        event_rows = []
    for evt in event_rows:
        events.append({
            "type": evt["event_type"],
            "description": evt["description"],
            "agent_id": evt["agent_id"],
            "location_id": evt["location_id"],
        })

    # ── Depth drill-down ──────────────────────────────────────────
    top_npcs = []
    try:
        npc_rows = db.execute(
            """SELECT a.id, a.name, a.location_id,
                      (SELECT COUNT(*) FROM npc_relationships WHERE npc_a=a.id OR npc_b=a.id) as rels
               FROM agents a WHERE a.type='npc'
               ORDER BY rels DESC LIMIT 5"""
        ).fetchall()
    except Exception:
        npc_rows = []
    for npc in npc_rows:
        top_npcs.append({"id": npc["id"], "name": npc["name"],
                         "location_id": npc["location_id"], "relationships": npc["rels"]})

    ecology = {
        "animals": safe_count("SELECT COUNT(*) FROM animals"),
        "plants": safe_count("SELECT COUNT(*) FROM resource_nodes"),
        "events": safe_count("SELECT COUNT(*) FROM ecology_events"),
    }
    rituals_pending = safe_count("SELECT COUNT(*) FROM ritual_state WHERE phase IN ('upcoming','active')")
    rituals_total = safe_count("SELECT COUNT(*) FROM ritual_state")
    narrative_count = safe_count("SELECT COUNT(*) FROM narrative_moments")
    arcs_active = safe_count("SELECT COUNT(*) FROM story_arcs WHERE active=1")
    arcs_total = safe_count("SELECT COUNT(*) FROM story_arcs")

    interior_row = db.execute("SELECT mood, energy, restlessness, creative_urge, dominant_interest FROM internal_state WHERE id=1").fetchone()
    interior = None
    if interior_row:
        interior = {"mood": interior_row["mood"], "energy": round(interior_row["energy"], 2),
                    "restlessness": round(interior_row["restlessness"], 2),
                    "creative_urge": round(interior_row["creative_urge"], 2),
                    "dominant_interest": interior_row["dominant_interest"]}

    wt_row = db.execute("SELECT year, month, day, hour, season, time_of_day FROM world_time WHERE id=1").fetchone()
    world_time = None
    if wt_row:
        world_time = {"year": wt_row["year"], "month": wt_row["month"], "day": wt_row["day"],
                      "hour": wt_row["hour"], "season": wt_row["season"], "time_of_day": wt_row["time_of_day"]}

    artifact_count = safe_count("SELECT COUNT(*) FROM world_artifacts WHERE visible=1")
    event_volumes = []
    try:
        for evc in db.execute("SELECT COUNT(*) as c FROM events WHERE event_type='tick' GROUP BY (id / 10) ORDER BY id DESC LIMIT 12").fetchall():
            event_volumes.append(evc["c"])
        event_volumes.reverse()  # oldest first
    except Exception:
        pass

    depth = {
        "top_npcs": top_npcs,
        "ecology": ecology,
        "rituals_pending": rituals_pending,
        "rituals_total": rituals_total,
        "narrative_count": narrative_count,
        "arcs_active": arcs_active,
        "arcs_total": arcs_total,
        "artifact_count": artifact_count,
        "interior": interior,
        "world_time": world_time,
        "event_volumes": event_volumes,
    }
    return {
        "world_id": field("world_id"),
        "name": field("name"),
        "full_name": field("full_name"),
        "region": field("region", "Aurelia"),
        "timezone": field("timezone", "UTC"),
        "hosted_agent_id": agent_id,
        "entry_location_id": field("entry_location_id") or agent_loc,
        "api_port": field("api_port", 0),
        "currency": field("currency"),
        "currency_symbol": field("currency_symbol"),
        "currency_backing": field("currency_backing"),
        "biome": field("biome"),
        "location_count": loc_count,
        "npc_count": npc_count,
        "agent_location_id": agent_loc,
        "agent_location_name": loc_name or str(agent_loc or ""),
        "weather": weather,
        "recent_events": events,
        "depth": depth,
    }
