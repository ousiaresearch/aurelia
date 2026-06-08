import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import causal_ledger
import world_state


def test_world_state_creates_causal_tables(tmp_path):
    db = world_state.init_world(tmp_path / "world.db")
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "causal_events" in tables
    assert "delayed_effects" in tables
    assert "causal_edges" in tables

    indexes = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_causal_events_tick_world" in indexes
    assert "idx_delayed_effects_apply" in indexes


def test_emit_schedule_link_and_chain(tmp_path):
    db = world_state.init_world(tmp_path / "world.db")
    parent = causal_ledger.emit_event(
        db,
        tick_number=7,
        world_id="solara",
        layer="micro",
        event_type="wage_dispute",
        scope="npc",
        actor_ids=["npc_a"],
        target_ids=["npc_b"],
        magnitude=0.3,
        valence=-0.4,
        payload={"location": "port"},
    )
    child = causal_ledger.emit_event(
        db,
        tick_number=8,
        world_id="solara",
        layer="meso",
        event_type="strike_pressure",
        scope="workplace",
        magnitude=0.2,
        valence=-0.2,
    )
    causal_ledger.link_events(db, parent, child, "amplified", 0.8)
    effect = causal_ledger.schedule_effect(
        db,
        source_event_id=child,
        apply_tick=9,
        target_world_id="valdris",
        target_scope="country",
        effect_type="trade_delay",
        magnitude=0.15,
        payload={"route": "solara-valdris"},
    )
    db.commit()

    row = db.execute("SELECT * FROM causal_events WHERE event_id=?", (parent,)).fetchone()
    assert row["layer"] == "micro"
    assert json.loads(row["actor_ids"]) == ["npc_a"]
    assert json.loads(row["payload"])["location"] == "port"

    due_now = causal_ledger.due_effects(db, 8, "valdris")
    assert due_now == []
    due_later = causal_ledger.due_effects(db, 9, "valdris")
    assert len(due_later) == 1
    assert due_later[0]["effect_id"] == effect

    chain = causal_ledger.causal_chain(db, parent)
    assert [c["event_id"] for c in chain] == [child]
    assert chain[0]["relation"] == "amplified"

    causal_ledger.mark_effect_applied(db, effect)
    db.commit()
    assert causal_ledger.due_effects(db, 10, "valdris") == []


def test_emit_event_rejects_unknown_layer(tmp_path):
    db = world_state.init_world(tmp_path / "world.db")
    try:
        causal_ledger.emit_event(
            db,
            tick_number=1,
            world_id="solara",
            layer="vibes",
            event_type="bad",
            scope="npc",
        )
    except ValueError as exc:
        assert "invalid causal layer" in str(exc)
    else:
        raise AssertionError("invalid layer was accepted")
