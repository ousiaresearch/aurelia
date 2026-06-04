#!/usr/bin/env python3
"""
migrate_schema.py — Fix all schema mismatches between factory-created DBs
and the template source code.

Run once to bring all 5 Aurelian world DBs up to the full schema the code expects.
"""

import sqlite3
from pathlib import Path

AGENTS_HOME = Path("/Users/johann/.hermes/agents")

MIGRATIONS = [
    # creative_output table — missing reactions_count, discovered_by_owl
    ("creative_output", "reactions_count", "INTEGER DEFAULT 0"),
    ("creative_output", "discovered_by_owl", "INTEGER DEFAULT 0"),
    
    # goals — missing priority, category, deadline, reward
    ("goals", "priority", "INTEGER DEFAULT 5"),
    ("goals", "category", "TEXT DEFAULT 'general'"),
    ("goals", "deadline", "REAL DEFAULT NULL"),
    ("goals", "reward", "TEXT DEFAULT ''"),
    
    # story_arcs — missing active (different from status)
    ("story_arcs", "active", "INTEGER DEFAULT 1"),
    
    # narrative_moments — missing npc_id, mood
    ("narrative_moments", "npc_id", "TEXT DEFAULT NULL"),
    ("narrative_moments", "mood", "TEXT DEFAULT ''"),
    
    # npc_memories — missing related_npc_id, location_id, weight
    ("npc_memories", "related_npc_id", "TEXT DEFAULT NULL"),
    ("npc_memories", "location_id", "TEXT DEFAULT NULL"),
    ("npc_memories", "weight", "REAL DEFAULT 0.5"),
    
    # agent_inventory — might need location_id
    ("agent_inventory", "location_id", "TEXT DEFAULT ''"),
    
    # objects — missing state column
    ("objects", "state", "TEXT DEFAULT 'normal'"),
]

# Tables that need to exist but might be missing entirely
CREATE_TABLES = [
    """CREATE TABLE IF NOT EXISTS economy_production (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        npc_id TEXT,
        resource TEXT,
        amount REAL DEFAULT 0,
        location_id TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS economy_consumption (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        npc_id TEXT,
        resource TEXT,
        amount REAL DEFAULT 0,
        location_id TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS economy_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        from_npc TEXT,
        to_npc TEXT,
        resource TEXT,
        amount REAL DEFAULT 0,
        price REAL DEFAULT 0,
        location_id TEXT
    )""",
]

def migrate_world(country_id):
    db_path = AGENTS_HOME / country_id / "aurelia-world" / "world" / "world.db"
    if not db_path.exists():
        print(f"  {country_id}: NO DB")
        return
    
    db = sqlite3.connect(str(db_path))
    changes = 0
    
    # Create missing tables
    for sql in CREATE_TABLES:
        try:
            db.execute(sql)
            changes += 1
        except Exception:
            pass
    
    # Get existing tables and columns
    tables = {}
    for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        tname = row[0]
        try:
            cols = set(r[1] for r in db.execute(f"PRAGMA table_info({tname})"))
            tables[tname] = cols
        except:
            pass
    
    # Add missing columns
    for table, column, col_type in MIGRATIONS:
        if table in tables and column not in tables[table]:
            try:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                changes += 1
            except Exception as e:
                print(f"    WARN: {table}.{column}: {e}")
    
    # Update story_arcs.active from status
    try:
        db.execute("UPDATE story_arcs SET active = 1 WHERE status = 'active'")
        db.execute("UPDATE story_arcs SET active = 0 WHERE status != 'active'")
    except:
        pass
    
    db.commit()
    db.close()
    print(f"  {country_id}: {changes} migrations applied")


if __name__ == "__main__":
    print("═" * 50)
    print("AURELIA SCHEMA MIGRATION")
    print("═" * 50)
    for c in ["solara", "valdris", "mirithane", "arkos", "verge"]:
        migrate_world(c)
    print("═" * 50)
    print("Migration complete.")
