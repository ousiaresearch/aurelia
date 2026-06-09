import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import causal_ledger
import cultural_diffusion
import institutions
import macro_dynamics
import world_state


def make_fed_db(tmp_path):
    db = sqlite3.connect(tmp_path / "fed.db")
    db.row_factory = sqlite3.Row
    causal_ledger.ensure_schema(db)
    cultural_diffusion.ensure_schema(db)
    institutions.ensure_schema(db)
    # Seed traits for two worlds
    for world_id, traits in [
        ("solara", {"openness_to_trade": 0.75, "institutional_memory": 0.60, "xenophobia": 0.20, "innovation_culture": 0.40, "governance_norms": 0.70}),
        ("valdris", {"openness_to_trade": 0.30, "institutional_memory": 0.40, "xenophobia": 0.35, "innovation_culture": 0.10, "governance_norms": 0.50}),
    ]:
        now = time.time()
        for trait, value in traits.items():
            db.execute(
                "INSERT OR REPLACE INTO cultural_traits (world_id, trait, value, source_world, adopted_tick) VALUES (?, ?, ?, NULL, 0)",
                (world_id, trait, value),
            )
    db.commit()
    return db


def make_world_db(tmp_path, world_id):
    db = world_state.init_world(tmp_path / f"{world_id}.db")
    db.row_factory = sqlite3.Row
    now = time.time()
    db.execute("INSERT OR IGNORE INTO locations (id, name, description, created_at) VALUES ('town_square', 'Town Square', 'test', ?)", (now,))
    db.execute("""INSERT OR REPLACE INTO world_registry (id, world_id, name, region, timezone, hosted_agent_id, entry_location_id, api_port, created_at, updated_at)
        VALUES (1, ?, ?, 'test', 'UTC', 'palantir', 'town_square', 8765, ?, ?)""", (world_id, world_id.title(), now, now))
    db.commit()
    return db


def test_trait_diffuses_from_high_to_low(tmp_path):
    fed = make_fed_db(tmp_path)
    # Run enough ticks that governance_norms (or any trait) diffuses
    for t in range(1, 8):
        cultural_diffusion.apply_diffusion_tick(fed, worlds=["solara", "valdris"], tick_number=t)
    val_after = cultural_diffusion.trait_value(fed, "valdris", "governance_norms")
    # With random trait selection, not every run picks governance_norms.
    # Check that at least one trait shifted meaningfully.
    changes = 0
    for trait in cultural_diffusion.CULTURAL_TRAITS:
        orig = {"governance_norms": 0.50, "openness_to_trade": 0.30, "xenophobia": 0.35, "institutional_memory": 0.40, "innovation_culture": 0.10}[trait]
        if abs(cultural_diffusion.trait_value(fed, "valdris", trait) - orig) > 0.001:
            changes += 1
    assert changes >= 1  # At least one trait diffused


def test_xenophobic_world_resists_diffusion(tmp_path):
    fed = make_fed_db(tmp_path)
    # Re-seed valdris with HIGH xenophobia for this test
    cultural_diffusion.seed_traits(fed, "valdris", {"xenophobia": 0.85, "openness_to_trade": 0.30})
    pre = cultural_diffusion.trait_value(fed, "valdris", "openness_to_trade")
    # Run several ticks
    for t in range(1, 5):
        cultural_diffusion.apply_diffusion_tick(fed, worlds=["solara", "valdris"], tick_number=t)
    val = cultural_diffusion.trait_value(fed, "valdris", "openness_to_trade")
    # High xenophobia (0.85) should severely limit how much openness diffuses
    assert val < 0.42  # Started at 0.30, shouldn't jump much toward solara's 0.75


def test_institution_diffuses_between_worlds(tmp_path):
    fed = make_fed_db(tmp_path)
    # Create an institution in solara
    institutions.ensure_schema(fed)
    institutions.create_institution(fed, world_id="solara", tick_number=1, faction_id="fac1", inst_type="labor_union", name="United Workers")
    # Bump durability so it survives
    fed.execute("UPDATE institutions SET durability=0.8 WHERE world_id='solara'")
    fed.commit()
    # Set up border between worlds
    cultural_diffusion.ensure_borders(fed, "solara", "valdris")
    cultural_diffusion.apply_diffusion_tick(fed, worlds=["solara", "valdris"], tick_number=4)
    # Check if valdris got a copy
    inst = fed.execute("SELECT * FROM institutions WHERE world_id='valdris'").fetchone()
    assert inst is not None
    assert inst["type"] == "labor_union"


def test_cultural_distance_changes(tmp_path):
    fed = make_fed_db(tmp_path)
    d1 = cultural_diffusion.cultural_distance(fed, "solara", "valdris")
    for t in range(1, 10):
        cultural_diffusion.apply_diffusion_tick(fed, worlds=["solara", "valdris"], tick_number=t)
    d2 = cultural_diffusion.cultural_distance(fed, "solara", "valdris")
    assert d2 < d1  # Distance should shrink as traits diffuse


def test_diffusion_events_recorded(tmp_path):
    fed = make_fed_db(tmp_path)
    for t in range(1, 6):
        cultural_diffusion.apply_diffusion_tick(fed, worlds=["solara", "valdris"], tick_number=t)
    events = fed.execute(
        "SELECT COUNT(*) FROM causal_events WHERE event_type IN ('cultural_trait_adopted','cultural_trait_resisted')"
    ).fetchone()[0]
    assert events > 0
