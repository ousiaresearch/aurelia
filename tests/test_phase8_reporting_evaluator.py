import importlib.util
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import causal_ledger
import demography
import macro_dynamics
import yearly_report
import world_state


def load_evaluator():
    path = ROOT / "scripts" / "evaluate_phase8_run.py"
    spec = importlib.util.spec_from_file_location("evaluate_phase8_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_world(tmp_path, world_id="solara", n=40):
    db = world_state.init_world(tmp_path / f"{world_id}.db")
    db.row_factory = sqlite3.Row
    now = time.time()
    db.execute("INSERT OR IGNORE INTO locations (id, name, description, created_at) VALUES ('town_square', 'Town Square', 'test', ?)", (now,))
    db.execute("""
        INSERT OR REPLACE INTO world_registry
            (id, world_id, name, region, timezone, hosted_agent_id, entry_location_id, api_port, created_at, updated_at)
        VALUES (1, ?, ?, 'test', 'UTC', 'palantir', 'town_square', 8765, ?, ?)
    """, (world_id, world_id.title(), now, now))
    rows = []
    ds = []
    for i in range(n):
        npc_id = f"{world_id}:npc:{i}"
        rows.append((npc_id, f"NPC {i}", "npc", "town_square", "active", json.dumps({"npc_type": "human", "nationality": world_id}), now, now))
        ds.append((npc_id, json.dumps({"security": 0.55, "satisfaction": 0.55, "connectedness": 0.55, "restlessness": 0.25, "economic_stability": 0.55}), now, "[]"))
    db.executemany("INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.executemany("INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated, decision_log) VALUES (?, ?, ?, ?)", ds)
    demography.ensure_schema(db)
    macro_dynamics.ensure_schema(db)
    return db


def test_macro_regime_classifier():
    assert yearly_report.classify_macro_regime({"war_pressure": 0.8, "legitimacy": 0.2, "repression": 0.4, "gdp_proxy": 0.4, "public_health": 0.5, "food_security": 0.6, "border_openness": 0.5, "type_tension": 0.5}) == "civil_conflict"
    assert yearly_report.classify_macro_regime({"war_pressure": 0.1, "legitimacy": 0.71, "repression": 0.1, "gdp_proxy": 0.7, "public_health": 0.8, "food_security": 0.7, "border_openness": 0.5, "type_tension": 0.2}) == "stable_growth"


def test_yearly_report_includes_phase8_fields(tmp_path):
    db = make_world(tmp_path, "solara")
    now = time.time()
    macro_dynamics.ensure_schema(db)
    db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (
        "solara", 12, json.dumps({"war_pressure": 0.85, "legitimacy": 0.20, "repression": 0.70, "gdp_proxy": 0.30, "public_health": 0.50, "food_security": 0.50, "border_openness": 0.30, "type_tension": 0.80}), now
    ))
    causal_ledger.emit_event(db, tick_number=4, world_id="solara", layer="macro", event_type="macro_resilience_recovery", scope="country", magnitude=0.01)
    causal_ledger.emit_event(db, tick_number=5, world_id="solara", layer="macro", event_type="faction_legalized", scope="faction", magnitude=0.5)
    db.execute("""
        INSERT INTO demographic_events (event_id, tick_number, world_id, event_type, npc_id, cause, payload, created_at)
        VALUES ('imm1', 6, 'solara', 'immigration', 'npcx', 'refugee', '{}', ?)
    """, (now,))
    db.execute("""
        INSERT INTO demographic_events (event_id, tick_number, world_id, event_type, npc_id, cause, payload, created_at)
        VALUES ('em1', 7, 'solara', 'emigration', 'npcy', 'refugee', '{}', ?)
    """, (now,))
    db.execute("""
        INSERT INTO factions (faction_id, name, world_id, region, status, primary_grievance, demand, member_count, influence, founded_tick, metadata, created_at)
        VALUES ('fac1', 'Legal Front', 'solara', 'capital', 'legalized', 'labor', 'rights', 20, 0.5, 1, '{}', ?)
    """, (now,))
    report = yearly_report.build_yearly_report(db, world_id="solara", year_number=1, start_tick=1, end_tick=12)
    assert report["macro_regime"] == "civil_conflict"
    assert report["migration_flows"] == {"immigration": 1, "emigration": 1, "net": 0}
    assert report["resilience_events"]["macro_resilience_recovery"] == 1
    assert report["faction_outcomes"]["faction_legalized"] == 1


def test_phase8_evaluator_passes_diverse_sample_and_writes_decades(tmp_path):
    evaluator = load_evaluator()
    worlds = ["solara", "valdris", "mirithane", "arkos", "verge"]
    reports = []
    for year in range(1, 51):
        for i, world in enumerate(worlds):
            reports.append({
                "world_id": world,
                "year": year,
                "population": 1000 - year * (i + 1),
                "births": 5,
                "deaths": 6,
                "immigration": 1 if i == 1 and year % 3 == 0 else 0,
                "emigration": 1 if i == 0 and year % 3 == 0 else 0,
                "macro_state": {
                    "gdp_proxy": 0.45 + i * 0.06,
                    "legitimacy": 0.35 + i * 0.07,
                    "repression": 0.20 + i * 0.05,
                    "public_health": 0.55 + i * 0.04,
                    "food_security": 0.50 + i * 0.03,
                    "war_pressure": 0.15 + i * 0.04,
                    "border_openness": 0.30 + i * 0.08,
                },
                "resilience_events": {"macro_resilience_recovery": 1 if year in {10, 20, 30} else 0},
                "factions": {"integrated": 2, "legalized": 1, "suppressed": 1, "radicalized": 1},
                "faction_outcomes": {"faction_integrated": 1, "faction_legalized": 1, "faction_suppressed": 1, "faction_radicalized": 1},
                "macro_regime": "transitional",
                "migration_flows": {"immigration": 1 if i == 1 and year % 3 == 0 else 0, "emigration": 1 if i == 0 and year % 3 == 0 else 0, "net": 0},
                "causal_highlights": [],
            })
    summary = {"years": 50, "ticks": 600, "effects_scheduled": 100, "effects_imported": 90, "worlds": {}, "yearly_reports": reports, "output_dir": str(tmp_path)}
    path = tmp_path / "causal_summary.json"
    path.write_text(json.dumps(summary))
    result = evaluator.evaluate_summary(summary)
    assert result["passed"] is True
    decade = evaluator.write_decade_summary(summary, tmp_path)
    assert (tmp_path / "decade_summary.json").exists()
    assert (tmp_path / "decade_summary.md").exists()
    assert decade["decades"][0]["decade"] == "1-10"
