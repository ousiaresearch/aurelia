"""Tests for Phase 13 batch chronicle generation.

Phase H/13 should be usable without a GPU during CI: prompt rendering,
chronicle file generation, and GPU worker planning are pure/testable. The
actual llama.cpp model load stays behind an adapter and is only exercised
manually.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_batch_chronicles():
    path = ROOT / "src_template" / "batch_chronicles.py"
    spec = importlib.util.spec_from_file_location("batch_chronicles", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeChronicleClient:
    def __init__(self):
        self.calls: list[dict] = []

    def chat(self, messages, *, temperature=0.7, max_tokens=800):
        self.calls.append({"messages": messages, "temperature": temperature, "max_tokens": max_tokens})
        user = messages[-1]["content"]
        assert "Year 7" in user
        assert "Current state:" in user
        return "Year 7 — Solara\n\nThe river ran low, and the granaries learned patience."


def make_world_db(path: Path) -> Path:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE agents (id TEXT, name TEXT, type TEXT, location_id TEXT, state TEXT, properties TEXT, created_at REAL, updated_at REAL);
        CREATE TABLE world_time (id INTEGER PRIMARY KEY, year INTEGER, month INTEGER, day INTEGER, season TEXT);
        CREATE TABLE factions (name TEXT, status TEXT, grievance_type TEXT, member_count INTEGER);
        CREATE TABLE npc_decision_state (npc_id TEXT, variables TEXT, last_updated REAL, decision_log TEXT);
        CREATE TABLE discoveries (discovery_id TEXT, discovery_type TEXT, title TEXT, description TEXT, tick_number INTEGER, created_at REAL);
        CREATE TABLE great_persons (npc_id TEXT, event_type TEXT, title TEXT, description TEXT, tick_number INTEGER, created_at REAL);
        """
    )
    db.execute("INSERT INTO world_time VALUES (1, 2033, 7, 15, 'summer')")
    for i, species in enumerate(["human", "thren", "vorn", "glim"]):
        db.execute(
            "INSERT INTO agents VALUES (?, ?, 'npc', 'town_square', 'active', ?, 0, 0)",
            (f"npc-{i}", f"NPC {i}", json.dumps({"npc_type": species})),
        )
        db.execute(
            "INSERT INTO npc_decision_state VALUES (?, ?, 0, '[]')",
            (f"npc-{i}", json.dumps({"economic_stability": 0.52, "satisfaction": 0.61})),
        )
    db.execute("INSERT INTO factions VALUES ('River Compact', 'active', 'scarcity', 4)")
    db.execute("INSERT INTO discoveries VALUES ('d1', 'agriculture', 'Dry Canal Method', 'A low-water irrigation discipline.', 42, 0)")
    db.commit()
    db.close()
    return path


def test_prompt_template_is_externalized_and_rendered():
    mod = load_batch_chronicles()
    template = mod.load_chronicle_prompt_template()
    assert "{world_profile}" in template
    assert "{year_summary}" in template
    assert "{world_context}" in template

    messages = mod.build_chronicle_messages(
        "solara",
        "Population: 4 active.",
        "[discovery] Dry Canal Method: A low-water irrigation discipline.",
        7,
    )
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Solara, the agricultural heartland" in messages[0]["content"]
    assert "Year 7" in messages[1]["content"]
    assert "Dry Canal Method" in messages[1]["content"]


def test_batch_generate_writes_chronicle_with_fake_client(tmp_path):
    mod = load_batch_chronicles()
    world_db = make_world_db(tmp_path / "solara.db")
    client = FakeChronicleClient()
    events_data = {
        "7": {
            "solara": [
                {
                    "category": "discovery",
                    "title": "Dry Canal Method",
                    "description": "A low-water irrigation discipline spreads along the Luthien.",
                }
            ]
        }
    }

    result = mod.batch_generate(
        ["solara"],
        range(7, 8),
        events_data,
        {"solara": str(world_db)},
        client,
        tmp_path,
        max_tokens=300,
    )

    chronicle = tmp_path / "chronicles" / "solara_Y0007.txt"
    assert chronicle.exists()
    text = chronicle.read_text()
    assert "Year 7 — Solara" in text
    assert client.calls and client.calls[0]["max_tokens"] == 300
    assert result["written"] == 1
    assert result["fallbacks"] == 0


def test_gpu_worker_plan_caps_by_worlds_and_vram():
    mod = load_batch_chronicles()
    plan = mod.plan_gpu_workers(vram_gb=96, model_vram_gb=17, worlds=["solara", "valdris", "mirithane", "arkos", "verge"], reserve_gb=8)
    assert plan["workers"] == 5
    assert plan["estimated_vram_gb"] == 85

    small = mod.plan_gpu_workers(vram_gb=26, model_vram_gb=17, worlds=["solara", "valdris"], reserve_gb=8)
    assert small["workers"] == 1


def test_cli_dry_run_prints_gpu_plan_without_model(tmp_path, capsys):
    mod = load_batch_chronicles()
    rc = mod.main([
        "--output", str(tmp_path),
        "--dry-run",
        "--vram-gb", "96",
        "--model-vram-gb", "17",
        "--years", "2",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY RUN" in out
    assert "chronicles: 10" in out
    assert "workers: 5" in out
