"""federation_orchestrator.py — barrier-synchronized Aurelia causal runner.

This runner preserves cross-world causality even when compute is sequential:
all worlds process tick T from the same federation snapshot, then cross-world
effects resolve and become visible at tick T+1.
"""
from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import time
from pathlib import Path
from typing import Iterable

try:
    from . import (
        causal_ledger,
        demography,
        faction_lifecycle,
        federation_effects,
        macro_dynamics,
        meso_aggregator,
        micro_interactions,
        world_state,
        yearly_report,
    )
except Exception:
    import causal_ledger
    import demography
    import faction_lifecycle
    import federation_effects
    import macro_dynamics
    import meso_aggregator
    import micro_interactions
    import world_state
    import yearly_report

DEFAULT_WORLDS = ["solara", "valdris", "mirithane", "arkos", "verge"]


def _seed_int(seed: int, *parts: object) -> int:
    h = hashlib.sha256((str(seed) + ":" + ":".join(map(str, parts))).encode()).hexdigest()
    return int(h[:16], 16)


def _seed_world(db, world_id: str, npc_count: int) -> None:
    db.row_factory = sqlite3.Row
    now = time.time()
    db.execute(
        "INSERT OR IGNORE INTO locations (id, name, description, created_at) VALUES ('town_square', 'Town Square', 'central civic space', ?)",
        (now,),
    )
    db.execute(
        """
        INSERT OR REPLACE INTO world_registry
            (id, world_id, name, region, timezone, hosted_agent_id, entry_location_id, api_port, created_at, updated_at)
        VALUES (1, ?, ?, 'aurelia', 'UTC', 'palantir', 'town_square', 8765, ?, ?)
        """,
        (world_id, world_id.title(), now, now),
    )
    existing = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc'").fetchone()[0]
    if existing >= npc_count:
        return
    agent_rows = []
    ds_rows = []
    for i in range(existing, npc_count):
        npc_id = f"{world_id}:npc:{i:06d}"
        npc_type = ["human", "thren", "vorn", "glim"][i % 4]
        props = {"npc_type": npc_type, "nationality": world_id, "household_id": f"{world_id}:hh:{i//4}"}
        agent_rows.append((npc_id, f"{world_id.title()} NPC {i}", "npc", "town_square", "active", json.dumps(props), now, now))
        # 5% grievance-adjacent seed, but not deterministic stagnation.
        near_grievance = i % 20 == 0
        ds_rows.append((npc_id, json.dumps({
            "security": 0.34 if near_grievance else 0.58,
            "satisfaction": 0.31 if near_grievance else 0.56,
            "connectedness": 0.50,
            "restlessness": 0.62 if near_grievance else 0.24,
            "economic_stability": 0.32 if near_grievance else 0.55,
            "observed_injustice": 0.48 if near_grievance else 0.05,
            "anomaly_pressure": 0.15 if npc_type == "glim" else 0.02,
        }), now, "[]"))
    db.executemany(
        "INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        agent_rows,
    )
    db.executemany(
        "INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated, decision_log) VALUES (?, ?, ?, ?)",
        ds_rows,
    )
    db.commit()


def initialize_worlds(output_dir: Path, worlds: Iterable[str], npc_count: int) -> dict[str, sqlite3.Connection]:
    output_dir.mkdir(parents=True, exist_ok=True)
    conns: dict[str, sqlite3.Connection] = {}
    for world_id in worlds:
        db_path = output_dir / f"{world_id}.db"
        db = world_state.init_world(db_path)
        db.row_factory = sqlite3.Row
        _seed_world(db, world_id, npc_count)
        conns[world_id] = db
    return conns


def run_world_barrier_tick(
    db,
    *,
    world_id: str,
    tick_number: int,
    ticks_per_year: int,
    seed: int,
    max_interactions: int,
    birth_scale: float = 1.0,
    death_scale: float = 1.0,
) -> dict:
    rng = random.Random(_seed_int(seed, world_id, tick_number))
    imported_effects = 0  # populated by orchestrator before call
    micro_ids = micro_interactions.run_micro_interactions(
        db, world_id=world_id, tick_number=tick_number, max_interactions=max_interactions, rng=rng
    )
    meso_ids = meso_aggregator.aggregate_meso_signals(db, world_id=world_id, tick_number=tick_number)
    macro_id = macro_dynamics.apply_macro_dynamics(db, world_id=world_id, tick_number=tick_number)
    demo = demography.run_demography(
        db,
        world_id=world_id,
        tick_number=tick_number,
        rng=rng,
        birth_scale=birth_scale,
        death_scale=death_scale,
    )
    faction_counts = faction_lifecycle.run_faction_lifecycle(db, world_id=world_id, tick_number=tick_number, rng=rng)
    db.commit()
    return {
        "world_id": world_id,
        "tick": tick_number,
        "micro_events": len(micro_ids),
        "meso_events": len(meso_ids),
        "macro_event": macro_id,
        "births": demo["births"],
        "deaths": demo["deaths"],
        "factions": faction_counts,
        "imported_effects": imported_effects,
    }


def run_causal_simulation(
    *,
    output_dir: str | Path,
    worlds: list[str] | None = None,
    years: int = 20,
    npc_count: int = 1000,
    ticks_per_year: int = 12,
    seed: int = 777,
    max_interactions: int = 500,
    birth_scale: float = 1.0,
    death_scale: float = 1.0,
) -> dict:
    worlds = worlds or list(DEFAULT_WORLDS)
    output_dir = Path(output_dir)
    conns = initialize_worlds(output_dir, worlds, npc_count)
    fed = sqlite3.connect(output_dir / "federation.db")
    fed.row_factory = sqlite3.Row
    causal_ledger.ensure_schema(fed)
    total_ticks = years * ticks_per_year
    yearly_reports = []
    per_tick = []
    effects_scheduled = 0
    effects_imported = 0

    for tick in range(1, total_ticks + 1):
        tick_outputs = []
        for world_id in worlds:
            imported = federation_effects.import_due_effects(fed, conns[world_id], world_id=world_id, tick_number=tick)
            effects_imported += imported
            out = run_world_barrier_tick(
                conns[world_id],
                world_id=world_id,
                tick_number=tick,
                ticks_per_year=ticks_per_year,
                seed=seed,
                max_interactions=max_interactions,
                birth_scale=birth_scale,
                death_scale=death_scale,
            )
            out["imported_effects"] = imported
            federation_effects.copy_world_events_to_federation(conns[world_id], fed, world_id=world_id, tick_number=tick)
            tick_outputs.append(out)
        scheduled = federation_effects.resolve_outbound_effects(fed, tick_number=tick, worlds=worlds)
        effects_scheduled += scheduled
        fed.commit()
        per_tick.append({"tick": tick, "worlds": tick_outputs, "effects_scheduled": scheduled})

        if tick % ticks_per_year == 0:
            year = tick // ticks_per_year
            for world_id in worlds:
                yearly_reports.append(yearly_report.build_yearly_report(
                    conns[world_id], world_id=world_id, year_number=year,
                    start_tick=tick - ticks_per_year + 1, end_tick=tick,
                ))

    world_summaries = {}
    for world_id, db in conns.items():
        pop = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
        dead = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='deceased'").fetchone()[0]
        fac = db.execute("SELECT COUNT(*) FROM factions WHERE world_id=?", (world_id,)).fetchone()[0]
        world_summaries[world_id] = {"population": pop, "deceased": dead, "factions": fac}
        db.commit()

    summary = {
        "worlds": world_summaries,
        "years": years,
        "ticks": total_ticks,
        "effects_scheduled": effects_scheduled,
        "effects_imported": effects_imported,
        "yearly_reports": yearly_reports,
        "output_dir": str(output_dir),
    }
    with open(output_dir / "causal_summary.json", "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    return summary
