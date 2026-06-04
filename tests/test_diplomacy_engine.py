import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_glim_sanctuary_event_creates_personhood_incident_and_relation_deltas(tmp_path):
    import aurelia_coordinator as coordinator

    db_path = tmp_path / "coordinator.db"
    with patch.object(coordinator, "COORDINATOR_DB", db_path):
        state = coordinator.CoordinatorState()
        state.record_federation_events(
            "arkos",
            [
                {
                    "event_id": "arkos:test:glim-sanctuary",
                    "world_id": "arkos",
                    "event_type": "npc_action",
                    "category": "daily_life",
                    "title": "Vorn shelter crew redirects a dreaming Glim",
                    "description": "A Vorn shelter crew protects an anomalous Glim fleeing Solara decommission review.",
                    "importance": 0.82,
                    "actor_ids": ["npc_arkos_vorn_1", "npc_arkos_glim_1"],
                    "tags": ["vorn", "glim", "shelter", "anomaly"],
                    "payload": {"npc_type": "glim", "activity": "shelter"},
                    "world_time": {"year": 2126, "month": 3, "day": 18, "hour": 12},
                    "created_at": 100.0,
                }
            ],
        )

        result = state.process_diplomacy_events(limit=20)

        assert result["incidents_created"] == 1
        incident = state.get_diplomatic_incidents(limit=5)[0]
        assert incident["source_event_id"] == "arkos:test:glim-sanctuary"
        assert incident["category"] == "glim_personhood"
        assert set(incident["affected_worlds"]) == {"arkos", "mirithane", "solara"}
        assert incident["severity"] > 0.7

        relations = state.get_diplomatic_relations()
        solara_arkos = relations["arkos|solara"]
        assert solara_arkos["tension"] > solara_arkos["baseline_tension"]
        assert solara_arkos["trust"] < solara_arkos["baseline_trust"]

        arkos_mirithane = relations["arkos|mirithane"]
        assert arkos_mirithane["trust"] > arkos_mirithane["baseline_trust"]
        assert arkos_mirithane["cooperation"] > arkos_mirithane["baseline_cooperation"]

        # Processing the same event again is idempotent.
        second = state.process_diplomacy_events(limit=20)
        assert second["incidents_created"] == 0


def test_trade_flow_event_updates_trade_relation_without_personhood_incident(tmp_path):
    import aurelia_coordinator as coordinator

    db_path = tmp_path / "coordinator.db"
    with patch.object(coordinator, "COORDINATOR_DB", db_path):
        state = coordinator.CoordinatorState()
        state.record_federation_events(
            "valdris",
            [
                {
                    "event_id": "valdris:test:ore-to-arkos",
                    "world_id": "valdris",
                    "event_type": "trade_flow",
                    "category": "economy",
                    "title": "Ore convoy bound for Arkos",
                    "description": "Valdris sends raw ore to Arkos factories for refinement.",
                    "importance": 0.5,
                    "tags": ["trade", "ore", "arkos"],
                    "payload": {"resource": "ore", "from": "valdris", "to": "arkos", "amount": 14},
                    "created_at": 200.0,
                }
            ],
        )

        result = state.process_diplomacy_events(limit=20)

        assert result["incidents_created"] == 1
        incident = state.get_diplomatic_incidents(limit=5)[0]
        assert incident["category"] == "trade"
        assert incident["affected_worlds"] == ["arkos", "valdris"]

        relations = state.get_diplomatic_relations()
        arkos_valdris = relations["arkos|valdris"]
        assert arkos_valdris["trade"] > arkos_valdris["baseline_trade"]
        assert arkos_valdris["cooperation"] > arkos_valdris["baseline_cooperation"]
        assert arkos_valdris["tension"] <= arkos_valdris["baseline_tension"]


def test_ingest_federation_events_records_and_processes_diplomacy_automatically(tmp_path):
    import aurelia_coordinator as coordinator

    db_path = tmp_path / "coordinator.db"
    with patch.object(coordinator, "COORDINATOR_DB", db_path):
        state = coordinator.CoordinatorState()
        result = state.ingest_federation_events(
            "mirithane",
            [
                {
                    "event_id": "mirithane:test:glim-marsh",
                    "world_id": "mirithane",
                    "event_type": "narrative_moment",
                    "category": "narrative",
                    "title": "The marsh glows around a Glim memory",
                    "description": "The memory marsh supports an anomalous Glim instead of treating it as broken.",
                    "importance": 0.8,
                    "tags": ["glim", "memory", "anomaly", "support"],
                    "payload": {},
                }
            ],
        )

        assert result["accepted"] == 1
        assert result["diplomacy"]["incidents_created"] == 1
        assert state.get_diplomatic_incidents(limit=1)[0]["category"] == "glim_personhood"


def test_diplomacy_module_classifies_verge_memory_trader_revelation():
    from aurelia_diplomacy import classify_diplomatic_event

    event = {
        "event_id": "verge:test:memory-leak",
        "world_id": "verge",
        "event_type": "narrative_moment",
        "category": "narrative",
        "title": "Memory trader releases a council memory",
        "description": "The Verge memory trader releases a memory implicating a Solara council member in Glim decommission orders.",
        "importance": 0.91,
        "tags": ["memory", "solara", "glim", "decommission"],
        "payload": {},
    }

    incident = classify_diplomatic_event(event)

    assert incident is not None
    assert incident["category"] == "memory_revelation"
    assert set(incident["affected_worlds"]) == {"verge", "solara", "mirithane", "arkos"}
    assert incident["relation_deltas"]["solara|verge"]["tension"] > 0
    assert incident["relation_deltas"]["arkos|mirithane"]["cooperation"] > 0
