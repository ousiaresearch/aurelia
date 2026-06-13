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
    assert "Factions: 0" in markdown
    assert "reconciliation_process" in markdown
    assert "Source summary:" in markdown
    assert "Source DB:" in markdown


def test_missing_world_db_marks_card_partial_but_keeps_summary_evidence(tmp_path):
    run_dir = make_verified_run(tmp_path)
    (run_dir / "solara.db").unlink()
    mod = load_script("render_verified_chronicles")

    cards = mod.build_verified_chronicle_cards(run_dir)

    assert cards[0]["provenance_status"] == "partial"
    assert "reconciliation_process" in cards[0]["evidence"]["top_event_types"]


def test_build_provenance_manifest_embeds_auditable_evidence_without_tmp_paths(tmp_path):
    run_dir = make_verified_run(tmp_path)
    mod = load_script("render_verified_chronicles")

    manifest = mod.build_provenance_manifest(run_dir)
    raw = json.dumps(manifest)

    assert manifest["schema"] == "aurelia.phase13.provenance.v1"
    assert manifest["source_run"]["run_id"] == "phase13-fixture"
    assert manifest["source_run"]["seed"] == 4242
    assert manifest["source_run"]["ticks_per_year"] == 3
    assert manifest["source_run"]["source_files"]["summary"] == "causal_summary.json"
    assert manifest["cards"][0]["source_files"]["world_db"] == "solara.db"
    assert manifest["cards"][0]["metrics"]["population"] == 1
    assert "reconciliation_process" in manifest["cards"][0]["evidence"]["top_event_types"]
    assert str(tmp_path) not in raw


def test_cli_writes_verified_chronicle_markdown_and_manifest(tmp_path):
    run_dir = make_verified_run(tmp_path)
    output = tmp_path / "chronicles.md"
    manifest_output = tmp_path / "chronicles.provenance.json"
    mod = load_script("render_verified_chronicles")

    mod.main([
        "--run-dir", str(run_dir),
        "--output", str(output),
        "--manifest-output", str(manifest_output),
    ])

    text = output.read_text()
    manifest = json.loads(manifest_output.read_text())
    assert "Aurelia Verified Chronicles" in text
    assert "Year 1 — Solara" in text
    assert "Committed provenance manifest: [chronicles.provenance.json](chronicles.provenance.json)" in text
    assert str(manifest_output) not in text
    assert str(run_dir) not in text
    assert "Source summary: `causal_summary.json`" in text
    assert "Source DB: `solara.db`" in text
    assert manifest["source_run"]["run_id"] == "phase13-fixture"


def test_llm_prompt_packet_carries_evidence_lock_without_invention(tmp_path):
    run_dir = make_verified_run(tmp_path)
    mod = load_script("render_verified_chronicles")
    card = mod.build_verified_chronicle_cards(run_dir)[0]

    packet = mod.build_llm_chronicle_prompt_packet(card)
    serialized = json.dumps(packet)

    assert packet["schema"] == "aurelia.phase13.llm_prompt.v1"
    assert packet["card_ref"] == {"run_id": "phase13-fixture", "world_id": "solara", "year": 1}
    assert "Do not invent" in packet["messages"][0]["content"]
    assert "reconciliation_process" in serialized
    assert "food_security_decline" in serialized
    assert "population" in serialized
    assert "solara.db" in serialized
    assert str(tmp_path) not in serialized


def test_llm_chronicle_draft_preserves_required_evidence(tmp_path):
    run_dir = make_verified_run(tmp_path)
    mod = load_script("render_verified_chronicles")
    card = mod.build_verified_chronicle_cards(run_dir)[0]

    draft = mod.render_grounded_llm_chronicle_draft(card)

    assert "## Year 1 — Solara" in draft
    assert "Run: `phase13-fixture`" in draft
    assert "Provenance: verified" in draft
    assert "reconciliation_process" in draft
    assert "food_security_decline" in draft
    assert "Population: 1" in draft
    assert mod.validate_llm_chronicle_draft(draft, card)["valid"] is True


def test_invalid_llm_chronicle_draft_reports_missing_evidence(tmp_path):
    run_dir = make_verified_run(tmp_path)
    mod = load_script("render_verified_chronicles")
    card = mod.build_verified_chronicle_cards(run_dir)[0]

    validation = mod.validate_llm_chronicle_draft("Year 1 was dramatic but unsourced.", card)

    assert validation["valid"] is False
    assert "reconciliation_process" in validation["missing_evidence"]


def test_cli_writes_llm_chronicles_and_prompt_packets(tmp_path):
    run_dir = make_verified_run(tmp_path)
    output = tmp_path / "verified.md"
    llm_output = tmp_path / "llm.md"
    prompt_output = tmp_path / "prompts.jsonl"
    mod = load_script("render_verified_chronicles")

    mod.main([
        "--run-dir", str(run_dir),
        "--output", str(output),
        "--llm-output", str(llm_output),
        "--prompt-output", str(prompt_output),
    ])

    llm_text = llm_output.read_text()
    prompt_lines = prompt_output.read_text().splitlines()
    assert "# Aurelia LLM Chronicle Drafts" in llm_text
    assert "Evidence lock: passed" in llm_text
    assert "reconciliation_process" in llm_text
    assert len(prompt_lines) == 1
    assert json.loads(prompt_lines[0])["card_ref"]["world_id"] == "solara"
    assert str(run_dir) not in llm_text
