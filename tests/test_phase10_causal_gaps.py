"""Phase 10 tests — close causal gaps from the 2026-06-08 deep dive."""
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import capital_economy
import causal_ledger
import federation_diplomacy
import federation_orchestrator
import macro_dynamics
import phase10_dynamics
import world_state
import yearly_report


def make_world(tmp_path, world_id="mirithane", npc_count=80):
    db = world_state.init_world(tmp_path / f"{world_id}.db")
    db.row_factory = sqlite3.Row
    now = time.time()
    db.execute(
        "INSERT OR IGNORE INTO locations (id, name, description, created_at) VALUES ('loc_0', 'Test Settlement', 'test', ?)",
        (now,),
    )
    db.execute(
        """
        INSERT OR REPLACE INTO world_registry
            (id, world_id, name, region, timezone, hosted_agent_id, entry_location_id, api_port, created_at, updated_at)
        VALUES (1, ?, ?, 'test', 'UTC', 'palantir', 'loc_0', 8765, ?, ?)
        """,
        (world_id, world_id.title(), now, now),
    )
    for i in range(npc_count):
        props = {
            "age": 16 + (i % 55),
            "sex": "male" if i % 2 == 0 else "female",
            "education": 0.18 + (i % 7) * 0.04,
            "urban": i % 3 == 0,
            "skill": "artisan" if i % 5 == 0 else "laborer",
        }
        db.execute(
            """INSERT OR IGNORE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
               VALUES (?, ?, 'npc', 'loc_0', 'active', ?, ?, ?)""",
            (f"npc_{i}", f"NPC {i}", json.dumps(props), now, now),
        )
    db.commit()
    return db


def seed_macro(db, world_id, tick, **overrides):
    macro_dynamics.ensure_schema(db)
    state = macro_dynamics.baseline_state(world_id)
    state.update(overrides)
    db.execute(
        "INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        (world_id, tick, json.dumps(state, sort_keys=True), time.time()),
    )
    db.commit()
    return state


def test_civilization_tick_changes_formerly_constant_macro_dimensions(tmp_path):
    db = make_world(tmp_path, "mirithane")
    capital_economy.ensure_schema(db)
    capital_economy.seed_pool(db, "mirithane", stock=0.72, innovation=0.65, tech=0.38)
    seed_macro(
        db,
        "mirithane",
        1,
        infrastructure=0.60,
        water_security=0.60,
        inequality=0.45,
        public_health=0.70,
        fiscal_capacity=0.60,
        repression=0.25,
        war_pressure=0.10,
        legitimacy=0.68,
    )
    before = macro_dynamics.latest_state(db, "mirithane")
    phase10_dynamics.apply_civilization_tick(db, world_id="mirithane", tick_number=2, rng_seed=123)
    after = macro_dynamics.latest_state(db, "mirithane")
    assert after["infrastructure"] != before["infrastructure"]
    assert after["water_security"] != before["water_security"]
    assert after["inequality"] != before["inequality"]
    metrics = phase10_dynamics.latest_metrics(db, "mirithane")
    assert 0 <= metrics["education_level"] <= 1
    assert 0 <= metrics["urbanization"] <= 1
    assert metrics["repression_type"] in {"surveillance", "legal", "violent", "propaganda", "none"}
    assert metrics["state_capacity_type"] in {"patrimonial", "bureaucratic", "prebendal", "developmental"}
    assert metrics["conflict_type"] in {"latent", "civil_war", "insurgency", "terrorism", "interstate_war"}


def test_innovation_pathway_creates_discovery_and_great_person_when_thresholds_cross(tmp_path):
    db = make_world(tmp_path, "verge", npc_count=120)
    capital_economy.ensure_schema(db)
    capital_economy.seed_pool(db, "verge", stock=0.82, innovation=0.88, tech=0.42)
    seed_macro(db, "verge", 10, legitimacy=0.62, fiscal_capacity=0.55, war_pressure=0.05, gdp_proxy=0.75)
    phase10_dynamics.apply_civilization_tick(db, world_id="verge", tick_number=11, rng_seed=7)
    discoveries = db.execute("SELECT COUNT(*) FROM discoveries WHERE world_id='verge'").fetchone()[0]
    great = db.execute("SELECT COUNT(*) FROM great_persons WHERE world_id='verge'").fetchone()[0]
    pool = capital_economy.get_pool(db, "verge")
    assert discoveries >= 1
    assert great >= 1
    assert pool["tech_level"] > 0.42
    assert db.execute("SELECT COUNT(*) FROM causal_events WHERE event_type IN ('technological_discovery','great_person_emergence')").fetchone()[0] >= 2


def test_diplomacy_snapshot_uses_tick_and_strength_accumulates(tmp_path):
    fed = sqlite3.connect(tmp_path / "fed.db")
    fed.row_factory = sqlite3.Row
    federation_diplomacy.ensure_schema(fed)
    federation_diplomacy.seed_world_diplo_state(fed, "solara", {"gdp_proxy": 0.7, "border_openness": 0.7, "legitimacy": 0.7, "repression": 0.1, "war_pressure": 0.05, "tech_level": 0.4}, tick_number=12)
    federation_diplomacy.seed_world_diplo_state(fed, "valdris", {"gdp_proxy": 0.6, "border_openness": 0.65, "legitimacy": 0.65, "repression": 0.15, "war_pressure": 0.08, "tech_level": 0.35}, tick_number=12)
    federation_diplomacy.ensure_borders(fed, "solara", "valdris")
    federation_diplomacy.evaluate_and_update_relations(fed, worlds=["solara", "valdris"], tick_number=12)
    rel = fed.execute("SELECT * FROM diplomatic_relations WHERE dissolved_tick IS NULL").fetchone()
    assert rel is not None
    start_strength = rel["strength"]
    # Peaceful continuity should strengthen, not decay to zero.
    for tick in range(13, 18):
        federation_diplomacy.evaluate_and_update_relations(fed, worlds=["solara", "valdris"], tick_number=tick)
    rel2 = fed.execute("SELECT * FROM diplomatic_relations WHERE relation_id=?", (rel["relation_id"],)).fetchone()
    assert rel2["strength"] > start_strength
    assert fed.execute("SELECT tick_number FROM world_macro_snapshot WHERE world_id='solara'").fetchone()[0] == 12


def test_cross_world_movement_transfers_npcs_and_logs_carriers(tmp_path):
    src = make_world(tmp_path, "arkos", npc_count=20)
    dst = make_world(tmp_path, "mirithane", npc_count=5)
    fed = sqlite3.connect(tmp_path / "fed.db")
    fed.row_factory = sqlite3.Row
    causal_ledger.ensure_schema(fed)
    before_src = src.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    before_dst = dst.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    moved = phase10_dynamics.transfer_migration_cohort(
        fed,
        src,
        dst,
        source_world="arkos",
        target_world="mirithane",
        tick_number=5,
        cohort_size=4,
        movement_type="refugee",
    )
    assert moved == 4
    assert src.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0] == before_src - 4
    assert dst.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0] == before_dst + 4
    assert fed.execute("SELECT COUNT(*) FROM cross_world_movements").fetchone()[0] == 4
    assert fed.execute("SELECT COUNT(*) FROM causal_events WHERE event_type='cross_world_movement'").fetchone()[0] == 4


def test_causal_edges_link_same_tick_drivers_and_effects(tmp_path):
    db = make_world(tmp_path, "solara")
    e1 = causal_ledger.emit_event(db, tick_number=3, world_id="solara", layer="micro", event_type="work_success", scope="household", magnitude=0.5)
    e2 = causal_ledger.emit_event(db, tick_number=3, world_id="solara", layer="macro", event_type="capital_formation", scope="country", magnitude=0.4)
    e3 = causal_ledger.emit_event(db, tick_number=3, world_id="solara", layer="macro", event_type="macro_state_update", scope="country", magnitude=0.2)
    linked = phase10_dynamics.link_tick_causality(db, world_id="solara", tick_number=3)
    assert linked >= 2
    edges = db.execute("SELECT parent_event_id, child_event_id, relation FROM causal_edges").fetchall()
    assert {tuple(r) for r in edges} >= {
        (e1, e2, "productive_activity_to_capital"),
        (e2, e3, "macro_feedback"),
    }


def test_counterfactual_branch_runs_independent_scenario(tmp_path):
    source = make_world(tmp_path, "valdris", npc_count=40)
    capital_economy.seed_pool(source, "valdris", stock=0.45, innovation=0.35, tech=0.25)
    seed_macro(source, "valdris", 1, gdp_proxy=0.45, legitimacy=0.25, repression=0.55, war_pressure=0.45)
    result = phase10_dynamics.run_counterfactual_branch(
        source,
        output_path=tmp_path / "counterfactual.db",
        world_id="valdris",
        start_tick=2,
        ticks=5,
        intervention={"legitimacy": 0.25, "repression": -0.20, "foreign_aid": 0.15},
        rng_seed=77,
    )
    assert result["ticks"] == 5
    assert result["branch_id"].startswith("cf:valdris:")
    assert Path(result["db_path"]).exists()
    db = sqlite3.connect(result["db_path"])
    db.row_factory = sqlite3.Row
    assert db.execute("SELECT COUNT(*) FROM counterfactual_events").fetchone()[0] >= 1


def test_civic_processes_create_goals_rituals_reconciliation_peace_and_sovereignty(tmp_path):
    db = make_world(tmp_path, "mirithane", npc_count=90)
    capital_economy.seed_pool(db, "mirithane", stock=0.65, innovation=0.55, tech=0.35)
    seed_macro(db, "mirithane", 4, legitimacy=0.72, repression=0.12, war_pressure=0.18, type_tension=0.42, fiscal_capacity=0.62)
    phase10_dynamics.apply_civilization_tick(db, world_id="mirithane", tick_number=5, rng_seed=55)
    assert db.execute("SELECT COUNT(*) FROM goals WHERE category IN ('education','public_health','infrastructure','reconciliation')").fetchone()[0] >= 1
    event_types = {r[0] for r in db.execute("SELECT DISTINCT event_type FROM causal_events WHERE tick_number=5").fetchall()}
    assert {"civic_ritual_observed", "reconciliation_process", "npc_dialogue_exchange", "goal_progress"}.issubset(event_types)
    assert db.execute("SELECT COUNT(*) FROM peace_treaties").fetchone()[0] >= 1
    assert db.execute("SELECT COUNT(*) FROM sovereignty_events").fetchone()[0] >= 1


def test_yearly_report_includes_phase10_metrics(tmp_path):
    db = make_world(tmp_path, "solara", npc_count=80)
    capital_economy.seed_pool(db, "solara", stock=0.55, innovation=0.35, tech=0.28)
    seed_macro(db, "solara", 1, legitimacy=0.58, repression=0.24, war_pressure=0.22, fiscal_capacity=0.52)
    phase10_dynamics.apply_civilization_tick(db, world_id="solara", tick_number=2, rng_seed=20)
    report = yearly_report.build_yearly_report(db, world_id="solara", year_number=1, start_tick=1, end_tick=4)
    assert "phase10" in report
    assert report["phase10"]["education_level"] >= 0
    assert report["phase10"]["state_capacity_type"] in {"patrimonial", "bureaucratic", "prebendal", "developmental"}
    assert report["phase10"]["causal_edges"] >= 1


def test_foreign_strategy_intervenes_in_environmental_crisis(tmp_path):
    fed = sqlite3.connect(tmp_path / "fed_strategy.db")
    fed.row_factory = sqlite3.Row
    federation_diplomacy.ensure_schema(fed)
    phase10_dynamics.ensure_federation_schema(fed)
    federation_diplomacy.seed_world_diplo_state(
        fed,
        "arkos",
        {"gdp_proxy": 0.22, "legitimacy": 0.20, "repression": 0.55, "war_pressure": 0.30, "water_security": 0.10, "public_health": 0.28},
        tick_number=14,
    )
    federation_diplomacy.seed_world_diplo_state(
        fed,
        "mirithane",
        {"gdp_proxy": 0.70, "legitimacy": 0.65, "repression": 0.12, "war_pressure": 0.05, "water_security": 0.62, "public_health": 0.72},
        tick_number=14,
    )
    acted = phase10_dynamics.apply_foreign_strategy(fed, worlds=["arkos", "mirithane"], tick_number=14)
    assert acted >= 1
    assert fed.execute("SELECT COUNT(*) FROM federation_strategy_events WHERE strategy_type='stabilization_aid'").fetchone()[0] >= 1
    assert fed.execute("SELECT COUNT(*) FROM causal_events WHERE event_type='foreign_strategy_intervention'").fetchone()[0] >= 1


def test_phase10_integrated_smoke_produces_nonzero_causal_gap_signals(tmp_path):
    out = tmp_path / "run"
    summary = federation_orchestrator.run_causal_simulation(
        output_dir=out,
        worlds=["solara", "valdris", "verge"],
        years=3,
        npc_count=120,
        ticks_per_year=4,
        seed=2026,
        max_interactions=120,
        birth_scale=12.0,
        death_scale=4.0,
    )
    assert summary["ticks"] == 12
    fed = sqlite3.connect(out / "federation.db")
    fed.row_factory = sqlite3.Row
    assert fed.execute("SELECT COUNT(*) FROM causal_edges").fetchone()[0] > 0
    assert fed.execute("SELECT COUNT(*) FROM cross_world_movements").fetchone()[0] > 0
    assert fed.execute("SELECT COUNT(*) FROM diffusion_events").fetchone()[0] > 0
    assert fed.execute("SELECT COUNT(*) FROM diplomatic_relations WHERE strength > 0.5").fetchone()[0] > 0
    for world_id in ["solara", "valdris", "verge"]:
        db = sqlite3.connect(out / f"{world_id}.db")
        db.row_factory = sqlite3.Row
        assert db.execute("SELECT COUNT(*) FROM civilization_metrics").fetchone()[0] > 0
        state = json.loads(db.execute("SELECT state FROM macro_state ORDER BY tick_number DESC LIMIT 1").fetchone()[0])
        assert state["infrastructure"] != 0.6
        assert state["water_security"] != 0.6
        assert state["inequality"] != 0.45
        assert db.execute("SELECT COUNT(*) FROM discoveries").fetchone()[0] > 0
        assert db.execute("SELECT COUNT(*) FROM causal_edges").fetchone()[0] > 0
        db.close()
