import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_coordinator_uses_loaded_module_directory_for_default_database(tmp_path):
    shutil.copy(ROOT / "aurelia_coordinator.py", tmp_path / "aurelia_coordinator.py")
    shutil.copy(ROOT / "aurelia_diplomacy.py", tmp_path / "aurelia_diplomacy.py")

    code = """
import json
from pathlib import Path
import aurelia_coordinator as coordinator
print(json.dumps({
    'root': str(coordinator.AURELIA_ROOT),
    'db_parent': str(coordinator.COORDINATOR_DB.parent),
    'expected': str(Path(coordinator.__file__).resolve().parent),
}))
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(proc.stdout)
    assert data["root"] == data["expected"]
    assert data["db_parent"] == data["expected"]


def test_coordinator_persists_and_deduplicates_federation_events(tmp_path):
    import aurelia_coordinator as coordinator

    db_path = tmp_path / "coordinator.db"
    with patch.object(coordinator, "COORDINATOR_DB", db_path):
        state = coordinator.CoordinatorState()
        events = [
            {
                "event_id": "solara:tick-7:npc-action-1",
                "world_id": "solara",
                "event_type": "npc_action",
                "category": "daily_life",
                "title": "Thren adjusts reef mirrors",
                "description": "Serein Petalgrave calibrates the reef laboratory mirrors.",
                "importance": 0.42,
                "actor_ids": ["npc_solara_0001"],
                "tags": ["thren", "schedule", "reef_labs"],
                "payload": {"npc_type": "thren", "activity": "working"},
                "world_time": {"year": 2026, "month": 6, "day": 1, "hour": 10},
                "created_at": 123.0,
            }
        ]

        assert state.record_federation_events("solara", events) == {"accepted": 1, "duplicates": 0}
        assert state.record_federation_events("solara", events) == {"accepted": 0, "duplicates": 1}

        stored = state.get_federation_events(limit=10)
        assert len(stored) == 1
        assert stored[0]["event_id"] == "solara:tick-7:npc-action-1"
        assert stored[0]["world_id"] == "solara"
        assert stored[0]["payload"]["npc_type"] == "thren"
        assert stored[0]["world_time"]["hour"] == 10


def test_federation_event_builder_promotes_meaningful_tick_outputs():
    from src_template.federation_events import build_federation_events

    tick_result = {
        "time": {"year": 2026, "month": 6, "day": 1, "hour": 10, "season": "summer"},
        "npc_ai_actions": [
            {
                "npc_id": "npc_arkos_0007",
                "npc_name": "Korr Vexis",
                "npc_type": "vorn",
                "activity": "working",
                "location_id": "autonomous_factory",
                "action": "Korr Vexis synchronizes factory arms with precise machine rhythm.",
                "occupation": "forge_coordinator",
            }
        ],
        "social_changes": [
            {
                "type": "new_alliance",
                "description": "Korr Vexis and GL-212 formed a protective alliance.",
                "npcs": ["npc_arkos_0007", "npc_arkos_0042"],
            }
        ],
        "economy": {"traded": [{"resource": "water", "amount": 12, "from": "arkos", "to": "solara"}]},
    }

    events = build_federation_events("arkos", tick_number=7, tick_result=tick_result, max_events=10)

    assert [event["event_type"] for event in events] == ["npc_action", "social_change", "trade_flow"]
    npc_event = events[0]
    assert npc_event["event_id"] == "arkos:tick-7:npc-action:npc_arkos_0007:0"
    assert npc_event["world_id"] == "arkos"
    assert npc_event["category"] == "daily_life"
    assert npc_event["actor_ids"] == ["npc_arkos_0007"]
    assert "vorn" in npc_event["tags"]
    assert npc_event["payload"]["location_id"] == "autonomous_factory"

    social_event = events[1]
    assert social_event["category"] == "social"
    assert social_event["actor_ids"] == ["npc_arkos_0007", "npc_arkos_0042"]
    assert social_event["world_time"]["hour"] == 10


def test_world_client_posts_federation_events_to_coordinator():
    from src_template.federation import publish_federation_events

    captured = {}

    class FakeResponse:
        def read(self):
            return json.dumps({"status": "ok", "accepted": 1, "duplicates": 0}).encode()

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(req.data.decode())
        return FakeResponse()

    event = {
        "event_id": "mirithane:tick-3:social:0",
        "world_id": "mirithane",
        "event_type": "social_change",
        "category": "social",
        "title": "Consensus circle expands",
        "description": "A Vorn newcomer is welcomed into the marsh circle.",
    }

    with patch("src_template.federation.urllib.request.urlopen", fake_urlopen):
        result = publish_federation_events("http://127.0.0.1:9001", "mirithane", [event], timeout=2.5)

    assert result == {"status": "ok", "accepted": 1, "duplicates": 0}
    assert captured["url"] == "http://127.0.0.1:9001/events"
    assert captured["timeout"] == 2.5
    assert captured["payload"] == {"world_id": "mirithane", "events": [event]}
