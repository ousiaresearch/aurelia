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


# ---------------------------------------------------------------------------
# D3 — divergence gates
# ---------------------------------------------------------------------------

def test_compare_runs_reports_divergence_score(tmp_path):
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
    assert "divergence_score" in comparison
    assert comparison["divergence_score"] > 0


def test_compare_runs_flags_zero_divergence_as_noop(tmp_path):
    """If branch is a byte-identical copy of baseline, divergence is zero and we warn."""
    import shutil
    baseline = tmp_path / "baseline"
    branch = tmp_path / "branch"
    make_counterfactual_run(baseline)
    shutil.copytree(baseline, branch)

    comparison = compare_runs(baseline, branch)
    assert comparison["divergence_score"] == 0
    assert any("no-op" in w.lower() or "divergence" in w.lower() or "identical" in w.lower() for w in comparison.get("warnings", []))


def test_compare_runs_reports_top_changed_event_types(tmp_path):
    """Branch with different event mix should expose the top deltas."""
    import shutil
    baseline = tmp_path / "baseline"
    branch = tmp_path / "branch"
    make_counterfactual_run(baseline)
    shutil.copytree(baseline, branch)
    # Add a batch of unique event types to the branch.
    db = sqlite3.connect(branch / "solara.db")
    for i in range(5):
        db.execute(
            "INSERT INTO causal_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"branch-{i}", 10 + i, "solara", "macro", "innovation_breakthrough", "[]", "[]", "world", 0.5, 0.4, 0.9, "{}", 0.0),
        )
    db.commit(); db.close()

    comparison = compare_runs(baseline, branch)
    assert "top_changed_event_types" in comparison
    types = comparison["top_changed_event_types"]
    assert any(t["event_type"] == "innovation_breakthrough" and t["delta"] == 5 for t in types)


def test_compare_runs_divergence_score_includes_metric_and_event_deltas(tmp_path):
    """Divergence score must combine event-count delta and metric deltas, not just one."""
    baseline = tmp_path / "baseline"
    branch = tmp_path / "branch"
    make_counterfactual_run(baseline)
    intervention = tmp_path / "aid.json"
    intervention.write_text(json.dumps({
        "branch_id": "solara-aid-test",
        "interventions": [
            {"tick": 2, "world_id": "solara", "type": "federation_aid", "payload": {"resource_stock": 0.20, "education_level": 0.10}}
        ]
    }))
    apply_intervention_file(baseline, branch, intervention)
    comparison = compare_runs(baseline, branch)
    # Score must exceed the largest single delta (otherwise it would be ignoring one axis).
    score = comparison["divergence_score"]
    biggest_world_delta = max(
        d["avg_resource_stock_delta"] + d["avg_education_level_delta"] + abs(d["causal_events_delta"])
        for d in comparison["worlds"].values()
    )
    assert score >= biggest_world_delta
