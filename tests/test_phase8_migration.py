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
import federation_effects
import federation_orchestrator
import migration_flows
import world_state


def make_world(tmp_path, world_id="solara", n=120):
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
        rows.append((npc_id, f"NPC {i}", "npc", "town_square", "active", json.dumps({"npc_type": "human", "nationality": world_id}), now, now))
        ds.append((npc_id, json.dumps({
            "security": 0.45,
            "satisfaction": 0.45,
            "connectedness": 0.55,
            "restlessness": 0.55,
            "economic_stability": 0.40,
            "observed_injustice": 0.15,
        }), now, "[]"))
    db.executemany("INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.executemany("INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated, decision_log) VALUES (?, ?, ?, ?)", ds)
    db.commit()
    return db


def test_migration_pressure_schedules_paired_outflow_and_inflow(tmp_path):
    fed = sqlite3.connect(tmp_path / "fed.db")
    fed.row_factory = sqlite3.Row
    causal_ledger.ensure_schema(fed)
    causal_ledger.emit_event(
        fed,
        tick_number=1,
        world_id="solara",
        layer="meso",
        event_type="migration_pressure",
        scope="country",
        magnitude=1.0,
        valence=-1.0,
    )
    federation_effects.resolve_outbound_effects(fed, tick_number=1, worlds=["solara", "valdris"])
    out = causal_ledger.due_effects(fed, 2, "solara")
    incoming = causal_ledger.due_effects(fed, 2, "valdris")
    assert any(e["effect_type"] == "refugee_outflow" for e in out)
    assert any(e["effect_type"] == "refugee_inflow" for e in incoming)
    source_payload = json.loads([e for e in out if e["effect_type"] == "refugee_outflow"][0]["payload"])
    target_payload = json.loads([e for e in incoming if e["effect_type"] == "refugee_inflow"][0]["payload"])
    assert source_payload["migration_group_id"] == target_payload["migration_group_id"]


def test_outflow_marks_emigrants_and_yearly_counts(tmp_path):
    db = make_world(tmp_path, "solara", n=200)
    before = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    causal_ledger.schedule_effect(
        db,
        source_event_id="source",
        apply_tick=5,
        target_world_id="solara",
        target_scope="country",
        effect_type="refugee_outflow",
        magnitude=2.0,
        payload={"migration_group_id": "mig1", "source_world": "solara", "target_world": "valdris", "migration_type": "refugee"},
    )
    counts = migration_flows.run_migration_flows(db, world_id="solara", tick_number=5, rng=random.Random(1))
    after = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    assert counts["emigration"] > 0
    assert after == before - counts["emigration"]
    yearly = demography.yearly_counts(db, "solara", 1, 12)
    assert yearly["emigration"] == counts["emigration"]
    assert db.execute("SELECT COUNT(*) FROM migration_cohorts WHERE direction='outflow'").fetchone()[0] == 1


def test_inflow_creates_immigrant_cohort_and_yearly_counts(tmp_path):
    db = make_world(tmp_path, "valdris", n=200)
    before = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    causal_ledger.schedule_effect(
        db,
        source_event_id="source",
        apply_tick=5,
        target_world_id="valdris",
        target_scope="country",
        effect_type="refugee_inflow",
        magnitude=2.0,
        payload={"migration_group_id": "mig1", "source_world": "solara", "target_world": "valdris", "migration_type": "refugee"},
    )
    counts = migration_flows.run_migration_flows(db, world_id="valdris", tick_number=5, rng=random.Random(2))
    after = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    assert counts["immigration"] > 0
    assert after == before + counts["immigration"]
    yearly = demography.yearly_counts(db, "valdris", 1, 12)
    assert yearly["immigration"] == counts["immigration"]
    row = db.execute("SELECT properties FROM agents WHERE id LIKE 'valdris:immigrant:%' LIMIT 1").fetchone()
    assert json.loads(row[0])["origin_world"] == "solara"


def test_barrier_runner_reports_nonzero_migration(tmp_path):
    out = tmp_path / "run"
    summary = federation_orchestrator.run_causal_simulation(
        output_dir=out,
        worlds=["solara", "valdris"],
        years=3,
        npc_count=180,
        ticks_per_year=6,
        seed=123,
        max_interactions=180,
        birth_scale=2.0,
        death_scale=2.0,
    )
    total_imm = sum(r["immigration"] for r in summary["yearly_reports"])
    total_em = sum(r["emigration"] for r in summary["yearly_reports"])
    assert total_imm > 0
    assert total_em > 0
