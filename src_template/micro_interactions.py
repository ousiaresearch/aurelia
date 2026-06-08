"""micro_interactions.py — mundane NPC interactions that feed causality.

The purpose is not prose. It converts small daily events into decision-state
changes and causal ledger rows, giving later meso/macro systems something real
to aggregate.
"""
from __future__ import annotations

import json
import random
import time
from typing import Any

try:  # package mode
    from . import causal_ledger
except Exception:  # flat/speed-run mode
    import causal_ledger

EVENTS = [
    ("work_success", 0.18, {"satisfaction": 0.010, "economic_stability": 0.006}, 0.15),
    ("work_failure", 0.13, {"satisfaction": -0.014, "economic_stability": -0.012}, -0.22),
    ("wage_dispute", 0.08, {"restlessness": 0.025, "economic_stability": -0.010}, -0.35),
    ("caregiving", 0.10, {"connectedness": 0.020, "satisfaction": 0.006}, 0.22),
    ("rumor_transmission", 0.13, {"restlessness": 0.012, "observed_injustice": 0.008}, -0.08),
    ("security_stop", 0.08, {"security": -0.025, "observed_injustice": 0.035}, -0.42),
    ("small_trade", 0.12, {"economic_stability": 0.012, "connectedness": 0.006}, 0.12),
    ("illness_seen", 0.06, {"security": -0.010, "satisfaction": -0.010}, -0.20),
    ("propaganda_exposure", 0.07, {"restlessness": -0.006, "ideological_alignment": 0.012}, 0.02),
    ("migration_plan", 0.05, {"restlessness": 0.020, "connectedness": -0.010}, -0.12),
]


def _loads(raw: Any) -> dict[str, float]:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except Exception:
        return {}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _choose(rng: random.Random) -> tuple[str, dict[str, float], float]:
    total = sum(w for _, w, _, _ in EVENTS)
    roll = rng.random() * total
    acc = 0.0
    for name, weight, deltas, valence in EVENTS:
        acc += weight
        if roll <= acc:
            return name, deltas, valence
    name, _, deltas, valence = EVENTS[-1]
    return name, deltas, valence


def run_micro_interactions(
    db,
    *,
    world_id: str,
    tick_number: int,
    max_interactions: int = 500,
    rng: random.Random | None = None,
) -> list[str]:
    """Run bounded mundane interactions and return emitted event IDs."""
    causal_ledger.ensure_schema(db)
    rng = rng or random.Random()
    rows = db.execute(
        """
        SELECT a.id, a.name, a.location_id, ds.variables
        FROM agents a
        JOIN npc_decision_state ds ON ds.npc_id = a.id
        WHERE a.type = 'npc' AND a.state = 'active'
        ORDER BY RANDOM()
        LIMIT ?
        """,
        (int(max_interactions),),
    ).fetchall()

    event_ids: list[str] = []
    now = time.time()
    for row in rows:
        event_type, deltas, valence = _choose(rng)
        variables = _loads(row["variables"])
        changed = {}
        for key, delta in deltas.items():
            before = float(variables.get(key, 0.5 if key != "restlessness" else 0.2))
            after = _clamp(before + delta + rng.uniform(-0.004, 0.004))
            variables[key] = after
            changed[key] = round(after - before, 4)

        db.execute(
            "UPDATE npc_decision_state SET variables=?, last_updated=? WHERE npc_id=?",
            (json.dumps(variables, sort_keys=True), now, row["id"]),
        )
        eid = causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="micro",
            event_type=event_type,
            scope="npc",
            actor_ids=[row["id"]],
            target_ids=[],
            magnitude=sum(abs(v) for v in changed.values()),
            valence=valence,
            payload={
                "npc_name": row["name"],
                "location_id": row["location_id"],
                "deltas": changed,
            },
        )
        event_ids.append(eid)

    return event_ids
