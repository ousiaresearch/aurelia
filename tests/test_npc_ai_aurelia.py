import json
import sqlite3
from unittest.mock import patch

import pytest


def make_db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(
        """
        CREATE TABLE locations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at REAL DEFAULT 0
        );
        CREATE TABLE agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'npc',
            location_id TEXT REFERENCES locations(id),
            state TEXT DEFAULT 'active',
            properties TEXT DEFAULT '{}',
            created_at REAL DEFAULT 0,
            updated_at REAL DEFAULT 0
        );
        CREATE TABLE npc_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id TEXT NOT NULL REFERENCES agents(id),
            hour INTEGER NOT NULL,
            activity TEXT NOT NULL DEFAULT 'idle',
            location_id TEXT REFERENCES locations(id),
            description TEXT DEFAULT ''
        );
        CREATE TABLE npc_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_a TEXT NOT NULL REFERENCES agents(id),
            npc_b TEXT NOT NULL REFERENCES agents(id),
            relationship_type TEXT DEFAULT 'acquaintance',
            affinity REAL DEFAULT 0.0,
            history TEXT DEFAULT '[]',
            updated_at REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE npc_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id TEXT NOT NULL REFERENCES agents(id),
            timestamp REAL NOT NULL,
            action_type TEXT NOT NULL,
            location_id TEXT REFERENCES locations(id),
            description TEXT DEFAULT '',
            properties TEXT DEFAULT '{}'
        );
        """
    )
    db.executemany(
        "INSERT INTO locations (id, name) VALUES (?, ?)",
        [("solar_farm_alpha", "Alpha Solar Farm"), ("reef_labs", "Reef Laboratories")],
    )
    props = {
        "npc_type": "thren",
        "occupation": "solar_engineer",
        "personality": "quiet builder",
        "psychological_profile": {
            "desires": ["to protect the ecology"],
            "fears": ["ecological collapse"],
        },
    }
    db.execute(
        "INSERT INTO agents (id, name, type, location_id, state, properties) VALUES (?, ?, 'npc', ?, 'active', ?)",
        ("npc_solara_0001", "Serein Petalgrave", "solar_farm_alpha", json.dumps(props)),
    )
    db.execute(
        """
        INSERT INTO npc_schedules (npc_id, hour, activity, location_id, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "npc_solara_0001",
            10,
            "working",
            "reef_labs",
            "Engaged in research and observation.",
        ),
    )
    db.commit()
    return db


def test_run_npc_ai_tick_uses_deep_seeded_schedule_not_old_template_locations():
    from src_template.npc_ai import run_npc_ai_tick

    db = make_db()
    with patch("src_template.npc_ai.random.random", return_value=0.0):
        actions = run_npc_ai_tick(db, 10)

    assert len(actions) == 1
    action = actions[0]
    assert action["npc_id"] == "npc_solara_0001"
    assert action["npc_type"] == "thren"
    assert action["activity"] == "working"
    assert action["location_id"] == "reef_labs"
    assert "Reef Laboratories" in action["action"] or "research" in action["action"]

    row = db.execute("SELECT location_id FROM agents WHERE id='npc_solara_0001'").fetchone()
    assert row["location_id"] == "reef_labs"

    logged = db.execute("SELECT action_type, location_id, properties FROM npc_actions").fetchone()
    assert logged["action_type"] == "working"
    assert logged["location_id"] == "reef_labs"
    assert json.loads(logged["properties"])["npc_type"] == "thren"


def test_glim_schedule_action_is_functional_not_inner_life_language():
    from src_template.npc_ai import run_npc_ai_tick

    db = make_db()
    glim_props = {"npc_type": "glim", "occupation": "drone_operator", "personality": "task-focused"}
    db.execute(
        "INSERT INTO agents (id, name, type, location_id, state, properties) VALUES (?, ?, 'npc', ?, 'active', ?)",
        ("npc_solara_0002", "GL-404", "solar_farm_alpha", json.dumps(glim_props)),
    )
    db.execute(
        """
        INSERT INTO npc_schedules (npc_id, hour, activity, location_id, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("npc_solara_0002", 10, "working", "reef_labs", "Running maintenance diagnostics."),
    )
    db.commit()

    with patch("src_template.npc_ai.random.random", return_value=0.0):
        actions = run_npc_ai_tick(db, 10)

    glim_action = [a for a in actions if a["npc_id"] == "npc_solara_0002"][0]
    assert glim_action["npc_type"] == "glim"
    assert "dream" not in glim_action["action"].lower()
    assert any(word in glim_action["action"].lower() for word in ["task", "diagnostic", "maintenance", "routine"])
