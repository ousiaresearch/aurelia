"""Tests for the migration feedback loop cap.

The cap on per-tick migration effects in run_migration_flows is bounded
by max_events = max(3, _active_population(db) // 30). Active population
grows as immigration flows in, so the cap itself grows without bound and
the system runs away. The fix introduces an absolute ceiling so that no
matter how large the population becomes, the per-tick cap is bounded.
"""
from __future__ import annotations

import json
import random
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_template"))

import causal_ledger
import migration_flows
import world_state


def _make_world(tmp_path, *, world_id: str, n: int):
    db = world_state.init_world(tmp_path / (world_id + ".db"))
    db.row_factory = sqlite3.Row
    now = time.time()
    db.execute(
        "INSERT OR IGNORE INTO locations (id, name, description, created_at) VALUES ('town_square', 'Town Square', 'test', ?)",
        (now,),
    )
    rows, ds = [], []
    for i in range(n):
        npc_id = world_id + ":npc:" + str(i)
        rows.append((npc_id, "NPC " + str(i), "npc", "town_square", "active",
                     json.dumps({"npc_type": "human", "nationality": world_id}), now, now))
        ds.append((npc_id, json.dumps({
            "security": 0.45, "satisfaction": 0.45, "connectedness": 0.55,
            "restlessness": 0.55, "economic_stability": 0.40, "observed_injustice": 0.15,
        }), now, "[]"))
    db.executemany("INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.executemany("INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated, decision_log) VALUES (?, ?, ?, ?)", ds)
    db.commit()
    return db


def _schedule_inflow(db, *, world_id: str, apply_tick: int, group_id: str, magnitude: float = 2.0):
    causal_ledger.schedule_effect(
        db, source_event_id="seed-" + group_id, apply_tick=apply_tick,
        target_world_id=world_id, target_scope="country",
        effect_type="refugee_inflow", magnitude=magnitude,
        payload={"migration_group_id": group_id, "source_world": "solara", "target_world": world_id, "migration_type": "refugee"},
    )


def test_per_tick_cap_is_bounded_absolute_constant():
    """The per-tick cap should be a module-level constant bounded by an absolute ceiling.

    This protects against the feedback loop where active population grows
    due to immigration, which raises the per-tick cap, which allows more
    immigration, ad infinitum.
    """
    assert hasattr(migration_flows, "MAX_MIGRATION_EVENTS_PER_TICK"), (
        "migration_flows must expose MAX_MIGRATION_EVENTS_PER_TICK as a hard ceiling"
    )
    cap = migration_flows.MAX_MIGRATION_EVENTS_PER_TICK
    assert isinstance(cap, int) and 1 <= cap <= 32, (
        "Cap must be a small positive integer; got " + repr(cap)
    )


def test_per_cohort_size_is_bounded_absolute_constant():
    """The cohort size cap should also be a module-level constant.

    _cohort_size previously used max(25, pop // 40) as its ceiling,
    which scaled linearly with population. Combined with the effect cap
    this still ran away (8 effects x 489 cohort at pop=19k = 3,900/tick).
    """
    assert hasattr(migration_flows, "MAX_MIGRATION_COHORT_SIZE"), (
        "migration_flows must expose MAX_MIGRATION_COHORT_SIZE as a hard ceiling"
    )
    cap = migration_flows.MAX_MIGRATION_COHORT_SIZE
    assert isinstance(cap, int) and 1 <= cap <= 100, (
        "Cohort cap must be a small positive integer; got " + repr(cap)
    )


def test_cohort_size_does_not_grow_with_population():
    """The cohort size returned by _cohort_size must NOT scale with population.

    A migration decision is a single act by a single actor; it should
    not get bigger as the world grows. Two worlds of different sizes
    with identical state, profile, and effect must produce the same
    cohort size.
    """
    effect = {"magnitude": 2.0, "effect_type": "refugee_inflow", "payload": "{}"}
    state = {"border_openness": 0.5}
    profile = {"migration": {"pull_attractiveness": 1.0, "border_friction": 0.5, "refugee_tolerance": 0.5}}

    # Use populations large enough that raw cohort would exceed the cap,
    # so the cap is the binding constraint on all three. This proves
    # the cohort is capped, not that raw just happens to be small at
    # small populations.
    small = migration_flows._cohort_size(effect, state, profile, pop=2_000, direction="inflow")
    large = migration_flows._cohort_size(effect, state, profile, pop=20_000, direction="inflow")
    huge = migration_flows._cohort_size(effect, state, profile, pop=200_000, direction="inflow")

    assert small == large == huge, (
        "Cohort size grew with population: small=" + str(small) +
        " large=" + str(large) + " huge=" + str(huge) + ". Feedback loop is back."
    )
    # And the cohort must be bounded by the cap.
    assert small <= migration_flows.MAX_MIGRATION_COHORT_SIZE


def test_runaway_immigration_is_bounded_over_long_run(tmp_path):
    """With repeated refugee_inflow effects over 60 ticks, per-tick
    immigration must never exceed the bounded ceiling (cap effects x
    max cohort size), no matter how large the population grows.

    The original bug had max_events = _active_population // 30, so the
    cap grew with the very population that immigration inflates. With
    the absolute cap, the per-tick ceiling is fixed at
    MAX_MIGRATION_EVENTS_PER_TICK effects and never grows.
    """
    db = _make_world(tmp_path, world_id="verge", n=100)
    rng_seed = 1001
    cap = migration_flows.MAX_MIGRATION_EVENTS_PER_TICK

    # Schedule a refugee_inflow effect every tick
    for t in range(1, 61):
        _schedule_inflow(db, world_id="verge", apply_tick=t, group_id="mig-" + str(t))

    imm_per_tick = []
    for tick in range(1, 61):
        counts = migration_flows.run_migration_flows(db, world_id="verge", tick_number=tick, rng=random.Random(rng_seed + tick))
        imm_per_tick.append(counts["immigration"])

    # The hard ceiling: no single tick can ever admit more immigrants
    # than cap * max_cohort_size. This is the actual invariant the
    # feedback loop violated.
    max_imm = max(imm_per_tick)
    assert max_imm <= cap * 25, (
        "Per-tick immigration " + str(max_imm) + " exceeds the bounded cap ("
        + str(cap) + " effects x 25 max cohort = " + str(cap * 25) + "). Feedback loop is back."
    )


def test_cap_holds_even_when_due_effects_explode(tmp_path):
    """When many inflow effects are simultaneously due, the cap must still hold.

    Schedule 50 effects at tick 5, run migration once, expect at most
    MAX_MIGRATION_EVENTS_PER_TICK effects to be processed and total
    immigrants to stay bounded.
    """
    db = _make_world(tmp_path, world_id="verge", n=100)
    cap = migration_flows.MAX_MIGRATION_EVENTS_PER_TICK

    for i in range(50):
        _schedule_inflow(db, world_id="verge", apply_tick=5, group_id="burst-" + str(i))

    counts = migration_flows.run_migration_flows(db, world_id="verge", tick_number=5, rng=random.Random(7))
    after_pop = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]

    # Hard ceiling: total immigrants in one tick can't exceed cap * 25 (max cohort)
    assert counts["immigration"] <= cap * 25, (
        "Single-tick burst admitted " + str(counts["immigration"]) + " immigrants; cap should bound to "
        + str(cap * 25) + " (=" + str(cap) + " effects x 25 max cohort)"
    )
    # Population post-burst must be far from runaway
    assert after_pop < 100 + cap * 30, (
        "Post-burst population " + str(after_pop) + " too high; expected bounded growth"
    )
