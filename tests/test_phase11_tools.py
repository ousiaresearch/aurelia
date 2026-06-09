import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_world_db(path: Path):
    db = sqlite3.connect(path)
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
        CREATE TABLE causal_edges (
            parent_event_id TEXT,
            child_event_id TEXT,
            relation TEXT,
            weight REAL
        );
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
        CREATE TABLE agents (id TEXT, type TEXT, state TEXT);
        """
    )
    events = [
        ("e1", 1, "solara", "micro", "drought_signal", "[]", "[]", "world", 0.4, -1, 0.9, "{}", 1.0),
        ("e2", 2, "solara", "macro", "food_security_decline", "[]", "[]", "world", 0.6, -1, 0.9, "{}", 2.0),
        ("e3", 3, "solara", "macro", "faction_pressure", "[]", "[]", "world", 0.8, -1, 0.9, "{}", 3.0),
    ]
    db.executemany("INSERT INTO causal_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", events)
    db.executemany("INSERT INTO causal_edges VALUES (?,?,?,?)", [("e1", "e2", "caused", 0.7), ("e2", "e3", "amplified", 0.8)])
    db.execute("INSERT INTO civilization_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("solara", 3, 0.3, 0.25, 0.7, 0.4, 0.5, 0.45, "patrimonial", "legal", "latent", 0.1, "{}", 3.0))
    db.execute("INSERT INTO discoveries VALUES ('d1','solara',2)")
    db.execute("INSERT INTO great_persons VALUES ('p1','solara',3)")
    db.executemany("INSERT INTO agents VALUES (?,?,?)", [("a1", "npc", "active"), ("a2", "npc", "deceased")])
    db.commit()
    db.close()


def make_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    make_world_db(run_dir / "solara.db")
    fed = sqlite3.connect(run_dir / "federation.db")
    fed.executescript(
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
        CREATE TABLE cross_world_movements (npc_id TEXT, source_world TEXT, target_world TEXT, movement_type TEXT, tick_number INTEGER, created_at REAL);
        CREATE TABLE diffusion_events (event_id TEXT, tick_number INTEGER, source_world TEXT, target_world TEXT, trait TEXT, adoption_strength REAL, resisted INTEGER, created_at REAL);
        CREATE TABLE diplomatic_relations (relation_id TEXT, world_a TEXT, world_b TEXT, relation_type TEXT, strength REAL, established_tick INTEGER, dissolved_tick INTEGER, payload TEXT, created_at REAL);
        """
    )
    fed.execute("INSERT INTO cross_world_movements VALUES ('npc1','solara','arkos','refugee',2,2.0)")
    fed.execute("INSERT INTO diffusion_events VALUES ('diff1',2,'solara','arkos','governance_norms',0.5,0,2.0)")
    fed.execute("INSERT INTO diplomatic_relations VALUES ('rel1','solara','arkos','trade_agreement',0.7,1,NULL,'{}',1.0)")
    fed.commit(); fed.close()
    (run_dir / "causal_summary.json").write_text(json.dumps({
        "years": 1,
        "ticks": 3,
        "worlds": {"solara": {"population": 1, "deceased": 1, "factions": 0}},
        "yearly_reports": [{"world_id": "solara", "year": 1, "population": 1, "births": 0, "deaths": 1, "factions": {}, "causal_highlights": [{"event_type": "faction_pressure", "count": 1}]}]
    }))
    return run_dir


def test_export_causal_graph_contains_valid_nodes_and_edges(tmp_path):
    db_path = tmp_path / "solara.db"
    make_world_db(db_path)
    mod = load_script("export_causal_graph")

    graph = mod.export_graph(db_path, run_id="test-run", world_id="solara", start_tick=1, end_tick=3)

    assert graph["stats"]["nodes"] == 3
    assert graph["stats"]["edges"] == 2
    node_ids = {n["id"] for n in graph["nodes"]}
    assert all(e["source"] in node_ids and e["target"] in node_ids for e in graph["edges"])
    assert graph["stats"]["layers"]["macro"] == 2


def test_explain_event_returns_upstream_chain(tmp_path):
    db_path = tmp_path / "solara.db"
    make_world_db(db_path)
    mod = load_script("explain_event")

    explanation = mod.explain_event(db_path, "e3", depth=3)

    assert explanation["target"]["event_id"] == "e3"
    assert explanation["upstream"][0]["event"]["event_id"] == "e2"
    assert explanation["upstream"][0]["upstream"][0]["event"]["event_id"] == "e1"


def test_render_run_report_summarizes_world_and_federation(tmp_path):
    run_dir = make_run_dir(tmp_path)
    mod = load_script("render_run_report")

    report = mod.render_report(run_dir)

    assert "# Aurelia Run Report" in report
    assert "solara" in report
    assert "causal events: 3" in report
    assert "cross-world movements: 1" in report
    assert "faction_pressure" in report


def test_evaluate_run_quality_scores_observable_run(tmp_path):
    run_dir = make_run_dir(tmp_path)
    mod = load_script("evaluate_run_quality")

    result = mod.evaluate_run(run_dir)

    assert result["engine_health"] > 0
    assert result["causal_richness"] > 0
    assert result["federation_richness"] > 0
    assert "warnings" in result
