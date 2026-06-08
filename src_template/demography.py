"""demography.py — real births, deaths, and migration counters."""
from __future__ import annotations

import json
import random
import time
import uuid

try:
    from . import causal_ledger, macro_dynamics
except Exception:
    import causal_ledger
    import macro_dynamics


def ensure_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS demographic_events (
            event_id TEXT PRIMARY KEY,
            tick_number INTEGER NOT NULL,
            world_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            npc_id TEXT,
            related_npc_id TEXT,
            cause TEXT DEFAULT '',
            payload TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_demographic_events_world_tick
            ON demographic_events(world_id, tick_number, event_type);
        CREATE TABLE IF NOT EXISTS migration_cohorts (
            cohort_id TEXT PRIMARY KEY,
            tick_number INTEGER NOT NULL,
            world_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            source_world TEXT NOT NULL,
            target_world TEXT NOT NULL,
            migration_type TEXT NOT NULL,
            cohort_size INTEGER NOT NULL,
            cause TEXT DEFAULT '',
            payload TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_migration_cohorts_world_tick
            ON migration_cohorts(world_id, tick_number, direction);
    """)


def _active_population(db) -> int:
    return db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]


def run_demography(
    db,
    *,
    world_id: str,
    tick_number: int,
    rng: random.Random | None = None,
    birth_scale: float = 1.0,
    death_scale: float = 1.0,
) -> dict[str, int]:
    """Apply birth/death events and return counts.

    Monthly speed-run calibration: probabilities are per tick. They are small but
    state-sensitive and produce non-static populations in smoke runs.
    """
    ensure_schema(db)
    rng = rng or random.Random()
    state = macro_dynamics.latest_state(db, world_id)
    pop = _active_population(db)
    if pop <= 0:
        return {"births": 0, "deaths": 0}

    birth_rate = 0.00045 * birth_scale
    birth_rate *= 0.60 + state["food_security"] * 0.45 + state["public_health"] * 0.35 + state["legitimacy"] * 0.20
    death_rate = 0.00038 * death_scale
    death_rate *= 0.75 + (1.0 - state["public_health"]) * 0.70 + state["war_pressure"] * 0.80 + (1.0 - state["food_security"]) * 0.50

    births = sum(1 for _ in range(pop) if rng.random() < birth_rate)
    deaths = sum(1 for _ in range(pop) if rng.random() < death_rate)
    births = min(births, max(25, pop // 40))
    deaths = min(deaths, max(25, pop // 40))

    event_counts = {"births": 0, "deaths": 0}
    now = time.time()
    candidates = db.execute(
        "SELECT id, location_id, properties FROM agents WHERE type='npc' AND state='active' ORDER BY id"
    ).fetchall()
    if not candidates:
        return event_counts
    sample_n = min(len(candidates), max(births, deaths, 1))
    active_rows = rng.sample(list(candidates), sample_n)

    for i in range(births):
        parent = active_rows[i % len(active_rows)]
        npc_id = f"{world_id}:child:{tick_number}:{uuid.uuid4().hex[:10]}"
        props = {"npc_type": "human", "born_tick": tick_number, "parent_id": parent["id"], "nationality": world_id}
        db.execute(
            """
            INSERT INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
            VALUES (?, ?, 'npc', ?, 'active', ?, ?, ?)
            """,
            (npc_id, f"Child_{tick_number}_{i}", parent["location_id"], json.dumps(props), now, now),
        )
        db.execute(
            "INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated, decision_log) VALUES (?, ?, ?, '[]')",
            (npc_id, json.dumps({"security": 0.6, "satisfaction": 0.6, "connectedness": 0.7, "restlessness": 0.1, "economic_stability": 0.55}), now),
        )
        ce = causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="micro",
            event_type="birth",
            scope="household",
            actor_ids=[parent["id"]],
            target_ids=[npc_id],
            magnitude=1.0,
            valence=0.55,
            payload={"parent_id": parent["id"], "child_id": npc_id},
        )
        db.execute(
            "INSERT INTO demographic_events (event_id, tick_number, world_id, event_type, npc_id, related_npc_id, cause, payload, created_at) VALUES (?, ?, ?, 'birth', ?, ?, 'household', ?, ?)",
            (ce, tick_number, world_id, npc_id, parent["id"], json.dumps({}), now),
        )
        event_counts["births"] += 1

    death_rows = active_rows[:deaths]
    for row in death_rows:
        if row["id"].startswith(f"{world_id}:child:{tick_number}"):
            continue
        cause = "illness" if state["public_health"] < 0.55 else "natural"
        db.execute("UPDATE agents SET state='deceased', updated_at=? WHERE id=?", (now, row["id"]))
        ce = causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="micro",
            event_type="death",
            scope="household",
            actor_ids=[row["id"]],
            magnitude=1.0,
            valence=-0.65,
            payload={"cause": cause},
        )
        db.execute(
            "INSERT INTO demographic_events (event_id, tick_number, world_id, event_type, npc_id, cause, payload, created_at) VALUES (?, ?, ?, 'death', ?, ?, ?, ?)",
            (ce, tick_number, world_id, row["id"], cause, json.dumps({}), now),
        )
        event_counts["deaths"] += 1

    return event_counts


def yearly_counts(db, world_id: str, start_tick: int, end_tick: int) -> dict[str, int]:
    ensure_schema(db)
    rows = db.execute(
        """
        SELECT event_type, COUNT(*) FROM demographic_events
        WHERE world_id=? AND tick_number BETWEEN ? AND ?
        GROUP BY event_type
        """,
        (world_id, start_tick, end_tick),
    ).fetchall()
    out = {"births": 0, "deaths": 0, "immigration": 0, "emigration": 0}
    for typ, count in rows:
        if typ == "birth":
            out["births"] = count
        elif typ == "death":
            out["deaths"] = count
        elif typ == "immigration":
            out["immigration"] = count
        elif typ == "emigration":
            out["emigration"] = count
    return out
