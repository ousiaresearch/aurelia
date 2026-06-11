"""migration_flows.py — cohort migration for Phase 8 causal federation.

Migration is represented as source/target cohort mutation rather than direct
cross-database row transfer. Source worlds mark active NPCs as emigrated; target
worlds create immigrant cohort NPCs. Both sides write demographic_events so
reports can show immigration/emigration.
"""
from __future__ import annotations

import json
import random
import time
import uuid

try:
    from . import causal_ledger, demography, macro_dynamics, world_profiles
except Exception:
    import causal_ledger
    import demography
    import macro_dynamics
    import world_profiles

MIGRATION_EFFECTS = {"refugee_outflow", "labor_outflow", "refugee_inflow", "labor_inflow"}

# Hard ceiling on per-tick migration effects. Without this, max_events was
# proportional to active population, which immigration itself inflates,
# producing an unbounded feedback loop (verge.db exploded to 600MB+ at
# tick 130+ in npc_count=100 seed=1001 runs). 8 is well above what any
# realistic mid-tick pressure surge can legitimately need.
MAX_MIGRATION_EVENTS_PER_TICK = 8

# Hard ceiling on the size of any single migration cohort. Without this,
# _cohort_size used max(25, pop // 40) for its upper bound, so the cohort
# itself scaled linearly with population. Combined with the effect cap
# above this still produced a runaway: 8 effects x 489 cohort at pop=19k
# = 3,900 immigrants per tick. A migration decision is a single act by
# a single actor; it should not get bigger as the world grows. 25 is the
# original floor before the pop-scaling term was added.
MAX_MIGRATION_COHORT_SIZE = 25


def _loads(raw) -> dict:
    try:
        return json.loads(raw or "{}")
    except Exception:
        return {}


def _active_population(db) -> int:
    return db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]


def _cohort_size(effect, state: dict, profile: dict, pop: int, *, direction: str) -> int:
    if pop <= 0:
        return 0
    mag = max(0.0, float(effect["magnitude"] or 0.0))
    mig = profile.get("migration", {})
    sensitivity = float(mig.get("push_sensitivity" if direction == "outflow" else "pull_attractiveness", 1.0))
    friction = float(mig.get("border_friction", 0.5))
    tolerance = float(mig.get("refugee_tolerance", 0.5))
    openness = state.get("border_openness", 0.5)
    pressure = mag * sensitivity
    if direction == "inflow":
        pressure *= max(0.25, (openness * 0.7 + tolerance * 0.5) - friction * 0.3)
    else:
        pressure *= max(0.25, 1.0 - openness * 0.2 + friction * 0.1)
    if pressure <= 0.005:
        return 0
    raw = int(pop * min(0.025, pressure * 0.025))
    return max(1, min(raw, MAX_MIGRATION_COHORT_SIZE))


def _insert_cohort(db, *, cohort_id: str, tick_number: int, world_id: str, direction: str,
                   source_world: str, target_world: str, migration_type: str, size: int,
                   cause: str, payload: dict, now: float) -> None:
    db.execute(
        """
        INSERT OR REPLACE INTO migration_cohorts
            (cohort_id, tick_number, world_id, direction, source_world, target_world,
             migration_type, cohort_size, cause, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cohort_id, tick_number, world_id, direction, source_world, target_world,
         migration_type, size, cause, json.dumps(payload, sort_keys=True), now),
    )


def _record_demo_event(db, *, tick_number: int, world_id: str, event_type: str, npc_id: str,
                       cause: str, payload: dict, now: float) -> str:
    ce = causal_ledger.emit_event(
        db,
        tick_number=tick_number,
        world_id=world_id,
        layer="micro",
        event_type=event_type,
        scope="migration",
        actor_ids=[npc_id] if npc_id else [],
        magnitude=1.0,
        valence=-0.20 if event_type == "emigration" else 0.10,
        payload=payload,
    )
    db.execute(
        """
        INSERT INTO demographic_events
            (event_id, tick_number, world_id, event_type, npc_id, cause, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ce, tick_number, world_id, event_type, npc_id, cause, json.dumps(payload, sort_keys=True), now),
    )
    return ce


def _apply_outflow(db, world_id: str, tick_number: int, effect, rng: random.Random) -> int:
    state = macro_dynamics.latest_state(db, world_id)
    profile = world_profiles.profile(world_id)
    pop = _active_population(db)
    size = _cohort_size(effect, state, profile, pop, direction="outflow")
    if size <= 0:
        return 0
    payload = _loads(effect["payload"])
    source_world = payload.get("source_world", world_id)
    target_world = payload.get("target_world", "unknown")
    migration_type = payload.get("migration_type") or ("refugee" if effect["effect_type"].startswith("refugee") else "labor")
    cohort_id = payload.get("migration_group_id") or f"mig:{world_id}:{tick_number}:{uuid.uuid4().hex[:8]}"
    now = time.time()
    rows = db.execute(
        "SELECT id, properties FROM agents WHERE type='npc' AND state='active' ORDER BY id"
    ).fetchall()
    if not rows:
        return 0
    selected = rng.sample(list(rows), min(size, len(rows)))
    moved = 0
    for row in selected:
        props = _loads(row["properties"])
        props.update({"emigrated_tick": tick_number, "emigration_target": target_world, "migration_group_id": cohort_id})
        db.execute("UPDATE agents SET state='emigrated', properties=?, updated_at=? WHERE id=?", (json.dumps(props, sort_keys=True), now, row["id"]))
        _record_demo_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            event_type="emigration",
            npc_id=row["id"],
            cause=migration_type,
            payload={"cohort_id": cohort_id, "source_world": source_world, "target_world": target_world, "migration_type": migration_type},
            now=now,
        )
        moved += 1
    _insert_cohort(
        db,
        cohort_id=cohort_id,
        tick_number=tick_number,
        world_id=world_id,
        direction="outflow",
        source_world=source_world,
        target_world=target_world,
        migration_type=migration_type,
        size=moved,
        cause=payload.get("source_event_type", effect["effect_type"]),
        payload=payload,
        now=now,
    )
    causal_ledger.emit_event(
        db,
        tick_number=tick_number,
        world_id=world_id,
        layer="meso",
        event_type="migration_outflow",
        scope="country",
        magnitude=moved / max(1, pop),
        valence=-0.35,
        payload={"cohort_id": cohort_id, "count": moved, "target_world": target_world, "migration_type": migration_type},
    )
    return moved


def _apply_inflow(db, world_id: str, tick_number: int, effect, rng: random.Random) -> int:
    state = macro_dynamics.latest_state(db, world_id)
    profile = world_profiles.profile(world_id)
    pop = _active_population(db)
    size = _cohort_size(effect, state, profile, max(pop, 50), direction="inflow")
    if size <= 0:
        return 0
    payload = _loads(effect["payload"])
    source_world = payload.get("source_world", "unknown")
    target_world = payload.get("target_world", world_id)
    migration_type = payload.get("migration_type") or ("refugee" if effect["effect_type"].startswith("refugee") else "labor")
    cohort_id = payload.get("migration_group_id") or f"mig:{source_world}:{world_id}:{tick_number}:{uuid.uuid4().hex[:8]}"
    now = time.time()
    created = 0
    for i in range(size):
        npc_id = f"{world_id}:immigrant:{tick_number}:{cohort_id.replace(':', '_')}:{i}:{uuid.uuid4().hex[:6]}"
        props = {
            "npc_type": "human",
            "nationality": world_id,
            "origin_world": source_world,
            "migration_group_id": cohort_id,
            "migration_type": migration_type,
            "arrived_tick": tick_number,
        }
        db.execute(
            """
            INSERT INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
            VALUES (?, ?, 'npc', 'town_square', 'active', ?, ?, ?)
            """,
            (npc_id, f"{source_world.title()} Migrant {tick_number}-{i}", json.dumps(props, sort_keys=True), now, now),
        )
        db.execute(
            "INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated, decision_log) VALUES (?, ?, ?, '[]')",
            (npc_id, json.dumps({"security": 0.42, "satisfaction": 0.40, "connectedness": 0.35, "restlessness": 0.58, "economic_stability": 0.38, "observed_injustice": 0.20}, sort_keys=True), now),
        )
        _record_demo_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            event_type="immigration",
            npc_id=npc_id,
            cause=migration_type,
            payload={"cohort_id": cohort_id, "source_world": source_world, "target_world": target_world, "migration_type": migration_type},
            now=now,
        )
        created += 1
    _insert_cohort(
        db,
        cohort_id=cohort_id,
        tick_number=tick_number,
        world_id=world_id,
        direction="inflow",
        source_world=source_world,
        target_world=target_world,
        migration_type=migration_type,
        size=created,
        cause=payload.get("source_event_type", effect["effect_type"]),
        payload=payload,
        now=now,
    )
    causal_ledger.emit_event(
        db,
        tick_number=tick_number,
        world_id=world_id,
        layer="meso",
        event_type="migration_inflow",
        scope="country",
        magnitude=created / max(1, pop),
        valence=-0.05,
        payload={"cohort_id": cohort_id, "count": created, "source_world": source_world, "migration_type": migration_type},
    )
    return created


def run_migration_flows(db, *, world_id: str, tick_number: int, rng: random.Random | None = None) -> dict[str, int]:
    demography.ensure_schema(db)
    causal_ledger.ensure_schema(db)
    rng = rng or random.Random()
    counts = {"immigration": 0, "emigration": 0}
    # Cap per-tick migration effects. The active-population-driven
    # formula is kept as a baseline (so small worlds still see at least
    # a few effects per tick), but MAX_MIGRATION_EVENTS_PER_TICK bounds
    # the ceiling so a population inflated by prior immigration cannot
    # raise the cap and create a runaway feedback loop.
    max_events = min(MAX_MIGRATION_EVENTS_PER_TICK, max(3, _active_population(db) // 30))
    processed = 0
    for effect in causal_ledger.due_effects(db, tick_number, world_id):
        et = effect["effect_type"]
        if et not in MIGRATION_EFFECTS:
            continue
        if processed >= max_events:
            causal_ledger.mark_effect_applied(db, effect["effect_id"])
            continue
        if et in {"refugee_outflow", "labor_outflow"}:
            moved = _apply_outflow(db, world_id, tick_number, effect, rng)
            counts["emigration"] += moved
            if moved > 0:
                processed += 1
        elif et in {"refugee_inflow", "labor_inflow"}:
            moved = _apply_inflow(db, world_id, tick_number, effect, rng)
            counts["immigration"] += moved
            if moved > 0:
                processed += 1
        causal_ledger.mark_effect_applied(db, effect["effect_id"])
    return counts
