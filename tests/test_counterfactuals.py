import json
import sqlite3
from pathlib import Path

from src_template.counterfactuals import apply_intervention_file, compare_runs, render_comparison_report


def make_counterfactual_run(root: Path):
    root.mkdir(parents=True)
    db = sqlite3.connect(root / "solara.db")
    db.executescript(
        """
        CREATE TABLE causal_events (
            event_id TEXT PRIMARY KEY,
            tick_number INTEGER,
            world_id TEXT,
            layer TEXT,
            event_type TEXT,
            actor_ids TEXT,
            target_ids TEXT,
            scope TEXT,
            magnitude REAL,
            valence REAL,
            confidence REAL,
            payload TEXT,
            created_at REAL
        );
        CREATE TABLE causal_edges (parent_event_id TEXT, child_event_id TEXT, relation TEXT, weight REAL);
        CREATE TABLE civilization_metrics (
            world_id TEXT,
            tick_number INTEGER,
            education_level REAL,
            urbanization REAL,
            youth_bulge REAL,
            disease_pressure REAL,
            resource_stock REAL,
            property_rights REAL,
            state_capacity_type TEXT,
            repression_type TEXT,
            conflict_type TEXT,
            path_lock_in REAL,
            payload TEXT,
            created_at REAL
        );
        CREATE TABLE discoveries (discovery_id TEXT, world_id TEXT, tick_number INTEGER);
        CREATE TABLE great_persons (npc_id TEXT, world_id TEXT, tick_number INTEGER);
        """
    )
    for tick in range(1, 5):
        db.execute("INSERT INTO causal_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (f"base-{tick}", tick, "solara", "macro", "macro_state_update", "[]", "[]", "world", 0.2, 0.0, 0.9, "{}", float(tick)))
        db.execute("INSERT INTO civilization_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("solara", tick, 0.30, 0.20, 0.70, 0.40, 0.50, 0.45, "patrimonial", "legal", "latent", 0.10, "{}", float(tick)))
    db.commit(); db.close()
    (root / "causal_summary.json").write_text(json.dumps({
        "years": 1,
        "ticks": 4,
        "worlds": {"solara": {"population": 100, "deceased": 2, "factions": 1}},
        "yearly_reports": []
    }))


def test_apply_federation_aid_intervention_creates_branch_events_and_metric_delta(tmp_path):
    baseline = tmp_path / "baseline"
    branch = tmp_path / "branch"
    make_counterfactual_run(baseline)
    intervention = tmp_path / "aid.json"
    intervention.write_text(json.dumps({
        "branch_id": "solara-aid-test",
        "base_seed": 123,
        "interventions": [{
            "tick": 2,
            "world_id": "solara",
            "type": "federation_aid",
            "payload": {"resource_stock": 0.15, "education_level": 0.05, "duration_ticks": 2}
        }]
    }))

    result = apply_intervention_file(baseline, branch, intervention)

    assert result["branch_id"] == "solara-aid-test"
    assert result["interventions_applied"] == 1
    db = sqlite3.connect(branch / "solara.db")
    stock = db.execute("SELECT resource_stock FROM civilization_metrics WHERE tick_number = 2").fetchone()[0]
    event = db.execute("SELECT event_type FROM causal_events WHERE event_type = 'counterfactual_federation_aid'").fetchone()[0]
    db.close()
    assert stock == 0.65
    assert event == "counterfactual_federation_aid"


def test_compare_runs_reports_counterfactual_deltas(tmp_path):
    baseline = tmp_path / "baseline"
    branch = tmp_path / "branch"
    make_counterfactual_run(baseline)
    intervention = tmp_path / "aid.json"
    intervention.write_text(json.dumps({
        "branch_id": "solara-aid-test",
        "interventions": [{"tick": 2, "world_id": "solara", "type": "federation_aid", "payload": {"resource_stock": 0.10}}]
    }))
    apply_intervention_file(baseline, branch, intervention)

    comparison = compare_runs(baseline, branch)
    report = render_comparison_report(comparison)

    assert comparison["worlds"]["solara"]["causal_events_delta"] == 1
    assert comparison["worlds"]["solara"]["avg_resource_stock_delta"] > 0
    assert "# Aurelia Counterfactual Comparison" in report
    assert "solara" in report
