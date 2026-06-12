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


def make_verified_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    db = sqlite3.connect(run_dir / "solara.db")
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
        CREATE TABLE agents (id TEXT, type TEXT, state TEXT);
        """
    )
    db.executemany(
        "INSERT INTO causal_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("e1", 1, "solara", "micro", "drought_signal", "[]", "[]", "world", 0.4, -1, 0.9, "{}", 1.0),
            ("e2", 2, "solara", "macro", "food_security_decline", "[]", "[]", "world", 0.6, -1, 0.9, "{}", 2.0),
            ("e3", 3, "solara", "macro", "reconciliation_process", "[]", "[]", "world", 0.7, 1, 0.9, "{}", 3.0),
        ],
    )
    db.executemany("INSERT INTO causal_edges VALUES (?,?,?,?)", [("e1", "e2", "caused", 0.7), ("e2", "e3", "softened", 0.8)])
    db.execute("INSERT INTO civilization_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("solara", 3, 0.3, 0.25, 0.7, 0.4, 0.5, 0.45, "patrimonial", "legal", "latent", 0.1, "{}", 3.0))
    db.executemany("INSERT INTO agents VALUES (?,?,?)", [("a1", "npc", "active"), ("a2", "npc", "deceased")])
    db.commit()
    db.close()

    (run_dir / "causal_summary.json").write_text(json.dumps({
        "run_id": "phase13-fixture",
        "years": 1,
        "ticks": 3,
        "ticks_per_year": 3,
        "seed": 4242,
        "worlds": {"solara": {"population": 1, "deceased": 1, "factions": 0}},
        "yearly_reports": [
            {
                "world_id": "solara",
                "year": 1,
                "population": 1,
                "births": 0,
                "deaths": 1,
                "factions": {},
                "causal_highlights": [
                    {"event_type": "reconciliation_process", "count": 1},
                    {"event_type": "food_security_decline", "count": 1}
                ]
            }
        ]
    }))
    return run_dir


def test_render_verified_chronicle_card_contains_provenance(tmp_path):
    run_dir = make_verified_run(tmp_path)
    mod = load_script("render_verified_chronicles")

    cards = mod.build_verified_chronicle_cards(run_dir)

    assert len(cards) == 1
    card = cards[0]
    assert card["run_id"] == "phase13-fixture"
    assert card["world_id"] == "solara"
    assert card["year"] == 1
    assert card["source_paths"]["summary"].endswith("causal_summary.json")
    assert card["source_paths"]["world_db"].endswith("solara.db")
    assert card["metrics"]["population"] == 1
    assert "reconciliation_process" in card["evidence"]["top_event_types"]
    assert card["provenance_status"] == "verified"


def test_render_verified_chronicle_markdown_keeps_evidence_visible(tmp_path):
    run_dir = make_verified_run(tmp_path)
    mod = load_script("render_verified_chronicles")

    markdown = mod.render_verified_chronicles_markdown(run_dir)

    assert "# Aurelia Verified Chronicles" in markdown
    assert "## Year 1 — Solara" in markdown
    assert "Provenance: verified" in markdown
    assert "reconciliation_process" in markdown
    assert "Source summary:" in markdown
    assert "Source DB:" in markdown


def test_cli_writes_verified_chronicle_markdown(tmp_path):
    run_dir = make_verified_run(tmp_path)
    output = tmp_path / "chronicles.md"
    mod = load_script("render_verified_chronicles")

    mod.main(["--run-dir", str(run_dir), "--output", str(output)])

    text = output.read_text()
    assert "Aurelia Verified Chronicles" in text
    assert "Year 1 — Solara" in text
