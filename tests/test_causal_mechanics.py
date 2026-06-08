import json
import random
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import causal_ledger
import demography
import faction_lifecycle
import federation_effects
import macro_dynamics
import meso_aggregator
import micro_interactions
import world_state
import yearly_report


def make_world(tmp_path, world_id="solara", n=80):
    db = world_state.init_world(tmp_path / f"{world_id}.db")
    db.row_factory = sqlite3.Row
    now = time.time()
    db.execute(
        "INSERT OR IGNORE INTO locations (id, name, description, created_at) VALUES ('town_square', 'Town Square', 'test', ?)",
        (now,),
    )
    db.execute(
        """
        INSERT OR REPLACE INTO world_registry
            (id, world_id, name, region, timezone, hosted_agent_id, entry_location_id, api_port, created_at, updated_at)
        VALUES (1, ?, ?, 'test', 'UTC', 'palantir', 'town_square', 8765, ?, ?)
        """,
        (world_id, world_id.title(), now, now),
    )
    rows = []
    ds = []
    for i in range(n):
        npc_id = f"{world_id}:npc:{i}"
        typ = ["human", "thren", "vorn", "glim"][i % 4]
        rows.append((npc_id, f"NPC {i}", "npc", "town_square", "active", json.dumps({"npc_type": typ, "nationality": world_id}), now, now))
        ds.append((npc_id, json.dumps({
            "security": 0.55,
            "satisfaction": 0.55,
            "connectedness": 0.55,
            "restlessness": 0.25,
            "economic_stability": 0.55,
            "observed_injustice": 0.05,
        }), now, "[]"))
    db.executemany("INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.executemany("INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated, decision_log) VALUES (?, ?, ?, ?)", ds)
    db.commit()
    return db


def test_micro_meso_macro_pipeline_changes_state(tmp_path):
    db = make_world(tmp_path, n=60)
    before = db.execute("SELECT variables FROM npc_decision_state WHERE npc_id='solara:npc:0'").fetchone()[0]
    micro_ids = micro_interactions.run_micro_interactions(db, world_id="solara", tick_number=1, max_interactions=60, rng=random.Random(1))
    meso_ids = meso_aggregator.aggregate_meso_signals(db, world_id="solara", tick_number=1)
    macro_id = macro_dynamics.apply_macro_dynamics(db, world_id="solara", tick_number=1)
    db.commit()

    assert len(micro_ids) == 60
    assert len(meso_ids) > 0
    assert macro_id
    after = db.execute("SELECT variables FROM npc_decision_state WHERE npc_id='solara:npc:0'").fetchone()[0]
    assert before != after
    macro = macro_dynamics.latest_state(db, "solara")
    assert macro != macro_dynamics.DEFAULT_STATE


def test_demography_changes_population_and_records_events(tmp_path):
    db = make_world(tmp_path, n=200)
    before = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    counts = demography.run_demography(
        db,
        world_id="solara",
        tick_number=2,
        rng=random.Random(2),
        birth_scale=80.0,
        death_scale=40.0,
    )
    db.commit()
    after = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    assert counts["births"] + counts["deaths"] > 0
    assert after != before or counts["births"] != counts["deaths"]
    assert db.execute("SELECT COUNT(*) FROM demographic_events").fetchone()[0] == counts["births"] + counts["deaths"]


def test_faction_lifecycle_creates_or_changes_consequences(tmp_path):
    db = make_world(tmp_path, n=100)
    # Force pressure signals directly.
    meso_aggregator.ensure_schema(db)
    db.execute("""
        INSERT INTO meso_signals (signal_id, tick_number, world_id, location_id, signal_type, magnitude, source_event_count, payload, created_at)
        VALUES ('sig1', 3, 'solara', 'town_square', 'labor_unrest', 5.0, 80, '{}', ?)
    """, (time.time(),))
    counts = faction_lifecycle.run_faction_lifecycle(db, world_id="solara", tick_number=3, rng=random.Random(1))
    db.commit()
    assert counts["formed"] >= 1
    assert db.execute("SELECT COUNT(*) FROM factions WHERE world_id='solara'").fetchone()[0] >= 1
    assert db.execute("SELECT COUNT(*) FROM causal_events WHERE event_type='faction_formed'").fetchone()[0] >= 1


def test_federation_effects_schedule_next_tick_cross_world(tmp_path):
    fed = sqlite3.connect(tmp_path / "fed.db")
    fed.row_factory = sqlite3.Row
    causal_ledger.ensure_schema(fed)
    causal_ledger.emit_event(
        fed,
        tick_number=5,
        world_id="solara",
        layer="macro",
        event_type="faction_escalated",
        scope="faction",
        magnitude=0.8,
        valence=-0.7,
        payload={"faction_id": "f1"},
    )
    scheduled = federation_effects.resolve_outbound_effects(fed, tick_number=5, worlds=["solara", "valdris", "arkos"])
    fed.commit()
    assert scheduled >= 1
    assert causal_ledger.due_effects(fed, 5, "valdris") == []
    assert len(causal_ledger.due_effects(fed, 6, "valdris")) == 1


def test_yearly_report_includes_demography_and_causal_highlights(tmp_path):
    db = make_world(tmp_path, n=120)
    micro_interactions.run_micro_interactions(db, world_id="solara", tick_number=1, max_interactions=50, rng=random.Random(5))
    demography.run_demography(db, world_id="solara", tick_number=1, rng=random.Random(6), birth_scale=10.0, death_scale=1.0)
    report = yearly_report.build_yearly_report(db, world_id="solara", year_number=1, start_tick=1, end_tick=12)
    assert report["population"] > 0
    assert report["births"] + report["deaths"] > 0
    assert report["causal_highlights"]
    assert "causes=" in yearly_report.format_yearly_report(report)
