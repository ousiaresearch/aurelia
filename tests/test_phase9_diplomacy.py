import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import causal_ledger
import federation_diplomacy
import institutions


def make_fed_db(tmp_path, worlds=None):
    db = sqlite3.connect(tmp_path / "fed.db")
    db.row_factory = sqlite3.Row
    causal_ledger.ensure_schema(db)
    federation_diplomacy.ensure_schema(db)
    if worlds:
        for w in worlds:
            federation_diplomacy.seed_world_diplo_state(db, w, {"gdp_proxy": 0.5, "legitimacy": 0.5, "repression": 0.2,
                                                                "border_openness": 0.5, "war_pressure": 0.1, "tech_level": 0.1})
    db.commit()
    return db


def seed_macro(fed, world_id, state):
    now = time.time()
    fed.execute(
        "INSERT OR REPLACE INTO world_macro_snapshot (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        (world_id, 0, json.dumps(state), now),
    )
    fed.commit()


def test_trade_agreement_signed_between_stable_worlds(tmp_path):
    fed = make_fed_db(tmp_path, ["solara", "valdris"])
    seed_macro(fed, "solara", {"gdp_proxy": 0.55, "border_openness": 0.60, "legitimacy": 0.60, "repression": 0.15, "war_pressure": 0.05})
    seed_macro(fed, "valdris", {"gdp_proxy": 0.45, "border_openness": 0.55, "legitimacy": 0.55, "repression": 0.20, "war_pressure": 0.10})
    federation_diplomacy.ensure_borders(fed, "solara", "valdris")
    federation_diplomacy.evaluate_and_update_relations(fed, worlds=["solara", "valdris"], tick_number=4)
    rel = fed.execute("SELECT * FROM diplomatic_relations WHERE world_a='solara' AND world_b='valdris'").fetchone()
    assert rel is not None
    assert rel["relation_type"] == "trade_agreement"


def test_aid_pact_established_when_one_world_in_crisis(tmp_path):
    fed = make_fed_db(tmp_path, ["mirithane", "verge"])
    seed_macro(fed, "mirithane", {"gdp_proxy": 0.08, "border_openness": 0.40, "legitimacy": 0.12, "repression": 0.60, "war_pressure": 0.50})
    seed_macro(fed, "verge", {"gdp_proxy": 0.70, "border_openness": 0.65, "legitimacy": 0.75, "repression": 0.10, "war_pressure": 0.05})
    federation_diplomacy.ensure_borders(fed, "mirithane", "verge")
    federation_diplomacy.evaluate_and_update_relations(fed, worlds=["mirithane", "verge"], tick_number=5)
    rel = fed.execute("SELECT * FROM diplomatic_relations WHERE relation_type='aid_pact'").fetchone()
    assert rel is not None
    donor = json.loads(rel["payload"]).get("donor")
    recipient = json.loads(rel["payload"]).get("recipient")
    assert donor == "verge"
    assert recipient == "mirithane"


def test_sanctions_imposed_on_high_repression_world(tmp_path):
    fed = make_fed_db(tmp_path, ["arkos", "mirithane"])
    seed_macro(fed, "arkos", {"gdp_proxy": 0.40, "border_openness": 0.30, "legitimacy": 0.15, "repression": 0.85, "war_pressure": 0.60})
    seed_macro(fed, "mirithane", {"gdp_proxy": 0.65, "border_openness": 0.50, "legitimacy": 0.70, "repression": 0.10, "war_pressure": 0.05})
    federation_diplomacy.ensure_borders(fed, "arkos", "mirithane")
    federation_diplomacy.evaluate_and_update_relations(fed, worlds=["arkos", "mirithane"], tick_number=6)
    rel = fed.execute("SELECT * FROM diplomatic_relations WHERE relation_type='sanctions'").fetchone()
    assert rel is not None


def test_diplomacy_events_in_ledger(tmp_path):
    fed = make_fed_db(tmp_path, ["solara", "valdris"])
    seed_macro(fed, "solara", {"gdp_proxy": 0.55, "border_openness": 0.60, "legitimacy": 0.60, "repression": 0.15, "war_pressure": 0.05})
    seed_macro(fed, "valdris", {"gdp_proxy": 0.45, "border_openness": 0.55, "legitimacy": 0.55, "repression": 0.20, "war_pressure": 0.10})
    federation_diplomacy.ensure_borders(fed, "solara", "valdris")
    federation_diplomacy.evaluate_and_update_relations(fed, worlds=["solara", "valdris"], tick_number=4)
    events = fed.execute(
        "SELECT COUNT(*) FROM causal_events WHERE event_type IN ('trade_agreement_signed','aid_pact_established','sanctions_imposed')"
    ).fetchone()[0]
    assert events > 0


def test_relation_dissolves_when_conditions_fail(tmp_path):
    fed = make_fed_db(tmp_path, ["solara", "valdris"])
    seed_macro(fed, "solara", {"gdp_proxy": 0.55, "border_openness": 0.60, "legitimacy": 0.60, "repression": 0.15, "war_pressure": 0.05})
    seed_macro(fed, "valdris", {"gdp_proxy": 0.45, "border_openness": 0.55, "legitimacy": 0.55, "repression": 0.20, "war_pressure": 0.10})
    federation_diplomacy.ensure_borders(fed, "solara", "valdris")
    federation_diplomacy.evaluate_and_update_relations(fed, worlds=["solara", "valdris"], tick_number=4)
    rel = fed.execute("SELECT * FROM diplomatic_relations WHERE world_a='solara' AND world_b='valdris' AND dissolved_tick IS NULL").fetchone()
    assert rel is not None
    # Now collapse valdris GDP to a truly failed state
    seed_macro(fed, "valdris", {"gdp_proxy": 0.01, "border_openness": 0.10, "legitimacy": 0.01, "repression": 0.60, "war_pressure": 0.60})
    federation_diplomacy.evaluate_and_update_relations(fed, worlds=["solara", "valdris"], tick_number=8)
    rel2 = fed.execute("SELECT * FROM diplomatic_relations WHERE world_a='solara' AND world_b='valdris' AND dissolved_tick IS NULL").fetchone()
    assert rel2 is None
