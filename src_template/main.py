"""
main.py — Entry point for the Embodied Creative World.

Usage:
    python -m src.main              # Interactive session
    python -m src.main --init       # Initialize/reset world
    python -m src.main --status     # Show world status
    python -m src.main --snapshot   # Save a snapshot
    python -m src.main --populate   # Generate procedural NPCs
"""

import sys
import argparse

from .world_state import init_world, get_world, get_db, DB_PATH
from .agent import run_interactive, Agent
from .persistence import save_snapshot, commit_snapshot, list_snapshots
from .ecology import init_ecology
from .npc_generation import populate_village


def init_pnw_runtime_world(db_path=None):
    """Initialize the canonical PNW Isildur world, including runtime extension tables."""
    import time
    from pnw_init import (
        _seed_locations_pnw, _seed_exits_pnw, _seed_objects_pnw,
        _seed_npcs_pnw, _seed_owl_pnw, _seed_schedules_pnw, _seed_relationships_pnw,
    )

    db = init_world(db_path or DB_PATH)
    now = time.time()

    db.execute("""
        INSERT OR REPLACE INTO world_time (id, year, month, day, hour, minute, season, time_of_day, created_at, updated_at)
        VALUES (1, 2026, 3, 17, 6, 0, 'spring', 'dawn', ?, ?)
    """, (now, now))

    weather_desc = (
        "The fog sits heavy in the valley this morning, threading between the old-growth cedars "
        "like breath. The air smells of damp bark and cold water. Everything is quiet except the creek."
    )
    db.execute("""
        INSERT OR REPLACE INTO weather (id, condition, temperature, wind_speed, wind_direction, humidity, visibility, description, updated_at)
        VALUES (1, 'foggy', 8.0, 2.0, 'NE', 0.92, 'low', ?, ?)
    """, (weather_desc, now))

    _seed_locations_pnw(db, now)
    _seed_exits_pnw(db)
    _seed_objects_pnw(db, now)
    _seed_npcs_pnw(db, now)
    _seed_owl_pnw(db, now)
    _seed_schedules_pnw(db)
    _seed_relationships_pnw(db)

    from .narrative import init_narrative_tables
    from .npc_ai import init_npc_ai
    from .rituals import init_ritual_tables
    from .npc_depth import init_npc_depth
    from .npc_memory import init_memory_tables
    from .identity_game import init_identity_tables
    from .reflective_world import init_reflective_tables
    from .goals import init_goals
    from .creative_output import init_creative_output
    from .ecology import init_ecology
    from .economy import seed_resources, seed_resource_nodes, seed_initial_inventory

    init_narrative_tables(db)
    init_npc_ai(db)
    init_ritual_tables(db)
    init_npc_depth(db)
    init_memory_tables(db)
    init_identity_tables(db)
    init_reflective_tables(db)
    init_goals(db)
    init_creative_output(db)
    init_ecology(db)
    seed_resources(db)
    seed_resource_nodes(db)
    seed_initial_inventory(db)

    db.commit()
    return db


def main():
    parser = argparse.ArgumentParser(description="Embodied Creative World")
    parser.add_argument("--init", action="store_true", help="Initialize/reset the world")
    parser.add_argument("--status", action="store_true", help="Show world status")
    parser.add_argument("--snapshot", action="store_true", help="Save a snapshot")
    parser.add_argument("--snapshots", action="store_true", help="List snapshots")
    parser.add_argument("--web", action="store_true", help="Start web visual interface")
    parser.add_argument("--host", default="127.0.0.1", help="Web server host")
    parser.add_argument("--port", type=int, default=8765, help="Web server port")
    parser.add_argument("--population", type=int, default=None, help="Target population (default: 200)")
    parser.add_argument("--world", "-w", default=None, help="World config YAML file path")
    args = parser.parse_args()

    if args.init:
        print("Initializing PNW Isildur world...")
        init_pnw_runtime_world()
        print("Run without --init to start the session.")
        return

    if args.status:
        if not DB_PATH.exists():
            print("No world found. Run with --init first.")
            return
        db = get_db()
        world = get_world(db)
        t = world.get("time", {})
        w = world.get("weather", {})
        b = world.get("body", {})
        i = world.get("internal", {})
        npc_count = sum(1 for a in world.get("agents", {}).values() if a.get("type") == "npc")
        print(f"Time: {t.get('hour', 0):02d}:{t.get('minute', 0):02d} — {t.get('season', '?')}, {t.get('time_of_day', '?')}")
        print(f"Weather: {w.get('condition', '?')}, {w.get('temperature', '?')}°C")
        print(f"Body: mood={b.get('mood', '?')}, energy={b.get('energy', 0):.0%}, hunger={b.get('hunger', 0):.0%}")
        print(f"Internal: mood={i.get('mood', '?')}, interest={i.get('dominant_interest', '?')}, creative_urge={i.get('creative_urge', 0):.0%}")
        print(f"NPCs: {npc_count}")
        return

    if args.snapshot:
        if not DB_PATH.exists():
            print("No world found. Run with --init first.")
            return
        db = get_db()
        path = save_snapshot(db)
        commit_snapshot(db)
        print(f"Snapshot saved: {path.name}")
        return

    if args.snapshots:
        snaps = list_snapshots()
        if snaps:
            for s in snaps[:10]:
                print(f"  {s}")
        else:
            print("No snapshots found.")
        return

    if args.web:
        from .web_server import run_web_mode
        run_web_mode(args.host, args.port)
        return

    if args.population:
        if not DB_PATH.exists():
            print("No world found. Run with --init first.")
            return
        db = get_db()
        generated = populate_village(db, args.population)
        print(f"Generated {generated} NPCs. Target population: {args.population}")
        return

    # Default: interactive session
    if not DB_PATH.exists():
        print("No world found. Initializing PNW Isildur world...")
        init_pnw_runtime_world()
        print(f"World created at {DB_PATH}")
        print()

    run_interactive()


if __name__ == "__main__":
    main()
