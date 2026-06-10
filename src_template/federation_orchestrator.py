"""federation_orchestrator.py — barrier-synchronized Aurelia causal runner.

This runner preserves cross-world causality even when compute is sequential:
all worlds process tick T from the same federation snapshot, then cross-world
effects resolve and become visible at tick T+1.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Engine identity (exposed for the run manifest)
# ---------------------------------------------------------------------------

ENGINE_VERSION = "aurelia-phase12"


def _git_commit() -> str:
    """Return the current short git commit hash, or ``"unknown"`` if not in a repo."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


GIT_COMMIT = _git_commit()


def make_run_id(label: str, years: int, ticks_per_year: int, seed: int) -> str:
    """Construct a deterministic run id from the manifest fields."""
    return f"{label}-y{years}-tpy{ticks_per_year}-seed{seed}-{GIT_COMMIT}"

try:
    from . import (
        causal_ledger,
        demography,
        faction_lifecycle,
        federation_diplomacy,
        federation_effects,
        capital_economy,
        institutions,
        cultural_diffusion,
        macro_dynamics,
        meso_aggregator,
        micro_interactions,
        migration_flows,
        regime_transitions,
        phase10_dynamics,
        world_profiles,
        world_state,
        yearly_report,
    )
except Exception:
    import causal_ledger
    import demography
    import faction_lifecycle
    import federation_diplomacy
    import federation_effects
    import capital_economy
    import institutions
    import cultural_diffusion
    import macro_dynamics
    import meso_aggregator
    import micro_interactions
    import migration_flows
    import regime_transitions
    import phase10_dynamics
    import world_profiles
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
    db.execute(
        """
        INSERT OR IGNORE INTO world_time
            (id, year, month, day, hour, minute, season, time_of_day, created_at, updated_at)
        VALUES (1, 2026, 1, 15, 12, 0, 'winter', 'midday', ?, ?)
        """,
        (now, now),
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


def _advance_world_time(db, tick_number: int, ticks_per_year: int) -> None:
    """Advance world_time on the shared historical frontier."""
    base_year = 2026
    month = ((tick_number - 1) % ticks_per_year) + 1
    # Map arbitrary ticks/year into 12 calendar months for reporting.
    calendar_month = max(1, min(12, int(((month - 1) / max(1, ticks_per_year)) * 12) + 1))
    year = base_year + (tick_number - 1) // ticks_per_year
    seasons = {3: "spring", 4: "spring", 5: "spring", 6: "summer", 7: "summer", 8: "summer",
               9: "autumn", 10: "autumn", 11: "autumn", 12: "winter", 1: "winter", 2: "winter"}
    now = time.time()
    db.execute(
        """
        UPDATE world_time
        SET year=?, month=?, day=15, hour=12, minute=0, season=?, time_of_day='midday', updated_at=?
        WHERE id=1
        """,
        (year, calendar_month, seasons.get(calendar_month, "spring"), now),
    )


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
    _advance_world_time(db, tick_number, ticks_per_year)
    micro_ids = micro_interactions.run_micro_interactions(
        db, world_id=world_id, tick_number=tick_number, max_interactions=max_interactions, rng=rng
    )
    meso_ids = meso_aggregator.aggregate_meso_signals(db, world_id=world_id, tick_number=tick_number)
    # Phase 9: capital economy converts micro productive events into persistent value
    capital_economy.apply_capital_flows(db, world_id=world_id, tick_number=tick_number)
    macro_id = macro_dynamics.apply_macro_dynamics(db, world_id=world_id, tick_number=tick_number)
    # Phase 9: regime transitions when world is in sustained collapse
    regime_transitions.check_and_resolve_crisis(db, world_id=world_id, tick_number=tick_number, rng=rng)
    migration = migration_flows.run_migration_flows(
        db,
        world_id=world_id,
        tick_number=tick_number,
        rng=rng,
    )
    demo = demography.run_demography(
        db,
        world_id=world_id,
        tick_number=tick_number,
        rng=rng,
        birth_scale=birth_scale,
        death_scale=death_scale,
    )
    faction_counts = faction_lifecycle.run_faction_lifecycle(db, world_id=world_id, tick_number=tick_number, rng=rng)
    # Phase 9: institutions provide ongoing macro benefits from constructive faction outcomes
    institutions.apply_institution_benefits(db, world_id=world_id, tick_number=tick_number)
    # Phase 10: close missing causal factors — ecology/resources, demographics,
    # education, urbanization, inequality/infrastructure/water dynamics,
    # repression/conflict/state-capacity types, discoveries, great persons, and
    # path dependence. Then link same-tick causes to effects.
    phase10_dynamics.apply_civilization_tick(
        db,
        world_id=world_id,
        tick_number=tick_number,
        rng_seed=_seed_int(seed, world_id, "phase10", tick_number),
    )
    phase10_dynamics.link_tick_causality(db, world_id=world_id, tick_number=tick_number)
    db.commit()
    return {
        "world_id": world_id,
        "tick": tick_number,
        "micro_events": len(micro_ids),
        "meso_events": len(meso_ids),
        "macro_event": macro_id,
        "births": demo["births"],
        "deaths": demo["deaths"],
        "immigration": migration["immigration"],
        "emigration": migration["emigration"],
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
    density_diversification: float = 0.0,
) -> dict:
    """Run the causal federation simulation.

    density_diversification in [0.0, 1.0] controls how aggressively the
    federation migration layer balances world populations. At 0.0 the
    simulation behaves exactly as before. At >0, an extra migration
    carrier is scheduled each tick that pulls from the most overpopulated
    world to the most underpopulated world, scaled by the knob.
    """
    worlds = sorted(worlds or list(DEFAULT_WORLDS))
    if density_diversification < 0 or density_diversification > 1:
        raise ValueError("density_diversification must be in [0.0, 1.0]")
    output_dir = Path(output_dir)
    conns = initialize_worlds(output_dir, worlds, npc_count)
    fed = sqlite3.connect(output_dir / "federation.db")
    fed.row_factory = sqlite3.Row
    causal_ledger.ensure_schema(fed)
    phase10_dynamics.ensure_federation_schema(fed)
    # Phase 9: seed cultural traits from world profiles
    for world_id in worlds:
        profile = world_profiles.profile(world_id)
        macro_baseline = profile.get("macro_baseline", {})
        resilience = profile.get("resilience", {})
        migration = profile.get("migration", {})
        cultural_seed = {
            "openness_to_trade": migration.get("border_friction", 0.5),
            "institutional_memory": resilience.get("shock_absorption", 0.5),
            "xenophobia": 1.0 - migration.get("refugee_tolerance", 0.5),
            "innovation_culture": resilience.get("recovery_rate", 0.01) * 10.0,
            "governance_norms": macro_baseline.get("legitimacy", 0.5),
        }
        cultural_diffusion.seed_traits(fed, world_id, cultural_seed)
    for a in worlds:
        for b in worlds:
            if a != b:
                cultural_diffusion.ensure_borders(fed, a, b)
                federation_diplomacy.ensure_borders(fed, a, b)
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
        # Phase 10: turn migration cohorts into actual cross-world NPC carriers.
        phase10_dynamics.process_migration_carriers(
            fed, conns, tick_number=tick,
            density_diversification=density_diversification,
        )
        # Phase 9/10: cultural learning and institution diffusion across federation.
        diffusion_rng = random.Random(_seed_int(seed, "federation", tick))
        cultural_diffusion.apply_diffusion_tick(fed, worlds=worlds, tick_number=tick, rng=diffusion_rng)
        phase10_dynamics.ensure_contact_diffusion(fed, worlds=worlds, tick_number=tick)
        # Phase 9/10: federation diplomacy — trade, aid, defense, sanctions, strategy
        # Seed world macro snapshots for diplomacy evaluation.
        for world_id in worlds:
            world_state_cur = macro_dynamics.latest_state(conns[world_id], world_id)
            federation_diplomacy.seed_world_diplo_state(fed, world_id, world_state_cur, tick_number=tick)
        federation_diplomacy.ensure_schema(fed)
        federation_diplomacy.evaluate_and_update_relations(fed, worlds=worlds, tick_number=tick)
        phase10_dynamics.apply_foreign_strategy(fed, worlds=worlds, tick_number=tick)
        phase10_dynamics.link_tick_causality(fed, world_id="federation", tick_number=tick)
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
        "ticks_per_year": ticks_per_year,
        "seed": seed,
        "density_diversification": density_diversification,
        "max_interactions": max_interactions,
        "birth_scale": birth_scale,
        "death_scale": death_scale,
        "engine_version": ENGINE_VERSION,
        "git_commit": GIT_COMMIT,
        "run_id": make_run_id("aurelia", years, ticks_per_year, seed),
        "created_at": time.time(),
        "effects_scheduled": effects_scheduled,
        "effects_imported": effects_imported,
        "yearly_reports": yearly_reports,
        "output_dir": str(output_dir),
    }
    with open(output_dir / "causal_summary.json", "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    return summary
