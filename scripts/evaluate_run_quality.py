#!/usr/bin/env python3
"""Score an Aurelia run for engine health and civilizational richness.

The evaluator returns ``overall_score`` in [0.0, 1.0]. It is *not* a
truth claim about the world — it is a self-check for engine health and
civilizational richness. The score must be honest about pathology:
high event volume cannot mask a factionless, depopulated run. The
gates below are the contract.

The thresholds are exposed as module-level constants so an operator
can tune them without editing the scoring logic.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aurelia_run_inspect import inspect_run


# ---------------------------------------------------------------------------
# Tunable thresholds
# ---------------------------------------------------------------------------

#: Fraction of worlds with at least one active faction below which we treat
#: faction formation as absent or sparse.
FRACTION_CRITICAL = 0.5

#: Hard score cap when fewer than ``FRACTION_CRITICAL`` of worlds have factions.
FRACTION_CRITICAL_CAP = 0.85

#: Hard score cap when any world drops to 1 or fewer NPCs in a long run.
POP_COLLAPSE_CAP = 0.80

#: Population-CV threshold above which we treat the run as unbalanced.
POP_CV_HIGH = 1.0

#: Hard score cap when population CV exceeds ``POP_CV_HIGH``.
POP_CV_HIGH_CAP = 0.85

#: A run must run for at least this many years before population collapse
#: warnings are treated as hard caps (a short smoke run is allowed to be empty).
LONG_RUN_YEARS = 50

#: A long run is also expected to have at least this many world-years of history.
LONG_RUN_MIN_WORLD_YEARS = LONG_RUN_YEARS * 5


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Run-shape readers
# ---------------------------------------------------------------------------

def _factions_per_world(run_dir: Path) -> dict[str, dict[str, int]]:
    """Return ``{world_id: count}`` from each per-world DB, keyed by kind.

    Returns a dict with two sub-dicts:
      - ``active``: per-world count of rows in ``factions`` with
        ``status='active'``.
      - ``formed_events``: per-world count of ``faction_formed`` rows in
        ``causal_events``.

    A faction can be formed (``faction_formed`` event) and then resolved
    to a terminal status (integrated / legalized / dissolved) on the
    same tick -- so the canonical "did a faction emerge in this world?"
    signal is the count of ``faction_formed`` events in
    ``causal_events``, not the ``status='active'`` row count. Both
    numbers are exposed so downstream gates can use whichever signal
    matches their contract.
    """
    active: dict[str, int] = {}
    formed_events: dict[str, int] = {}
    for db_path in sorted(Path(run_dir).glob("*.db")):
        if db_path.name == "federation.db":
            continue
        world = db_path.stem
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM factions WHERE status = 'active'"
                ).fetchone()
            except sqlite3.OperationalError:
                # No factions table at all → 0.
                row = (0,)
            active[world] = int(row[0]) if row else 0
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM causal_events WHERE event_type='faction_formed'"
                ).fetchone()
            except sqlite3.OperationalError:
                row = (0,)
            formed_events[world] = int(row[0]) if row else 0
            conn.close()
        except sqlite3.Error:
            active[world] = 0
            formed_events[world] = 0
    return {"active": active, "formed_events": formed_events}


def _factions_summary(factions_per_world: dict[str, dict[str, int]]) -> dict[str, int]:
    """Aggregate active vs formed counts across worlds for the gate."""
    active = factions_per_world.get("active", {})
    formed = factions_per_world.get("formed_events", {})
    worlds_active = sum(1 for n in active.values() if n > 0)
    worlds_formed = sum(1 for n in formed.values() if n > 0)
    return {
        "worlds_with_active_factions": worlds_active,
        "worlds_with_faction_formations": worlds_formed,
        "total_active_factions": sum(active.values()),
        "total_faction_formations": sum(formed.values()),
    }


def _population_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Extract per-world population and aggregate stats from causal_summary.json."""
    worlds = (summary or {}).get("worlds", {}) or {}
    pops: dict[str, int] = {}
    for w, info in worlds.items():
        if isinstance(info, dict) and "population" in info:
            try:
                pops[w] = int(info["population"])
            except (TypeError, ValueError):
                pops[w] = 0
    if not pops:
        return {
            "populations": {},
            "min_population": None,
            "max_population": None,
            "population_cv": None,
        }
    values = list(pops.values())
    mean = statistics.fmean(values)
    if mean == 0:
        cv: float | None = 0.0
    else:
        cv = statistics.pstdev(values) / mean
    return {
        "populations": pops,
        "min_population": min(values),
        "max_population": max(values),
        "population_cv": cv,
    }


def _metadata_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Inspect the run manifest fields exposed via causal_summary.json."""
    if not isinstance(summary, dict):
        return {
            "seed": None, "ticks_per_year": None, "years": None,
            "engine_version": None, "git_commit": None,
        }
    return {
        "seed": summary.get("seed"),
        "ticks_per_year": summary.get("ticks_per_year"),
        "years": summary.get("years"),
        "engine_version": summary.get("engine_version"),
        "git_commit": summary.get("git_commit"),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def evaluate_run(run_dir: str | Path) -> dict[str, Any]:
    data = inspect_run(run_dir)
    worlds = data["worlds"]
    fed = data["federation"]
    totals = data["totals"]
    summary = data["summary"] if isinstance(data.get("summary"), dict) else {}
    warnings: list[str] = []

    # -----------------------------------------------------------------------
    # Base scoring (existing logic, kept identical so old tests stay green)
    # -----------------------------------------------------------------------
    world_count = len(worlds)
    worlds_with_events = sum(1 for w in worlds if w.get("causal_events", 0) > 0)
    worlds_with_metrics = sum(1 for w in worlds if w.get("metrics", 0) > 0)
    worlds_with_edges = sum(1 for w in worlds if w.get("causal_edges", 0) > 0)

    engine_health = 0.0
    if world_count:
        engine_health += 0.35
        engine_health += 0.25 * (worlds_with_events / world_count)
        engine_health += 0.20 * (worlds_with_edges / world_count)
        engine_health += 0.20 * (worlds_with_metrics / world_count)
    if not fed.get("present"):
        warnings.append("federation.db missing")

    total_events = int(totals.get("causal_events", 0))
    total_edges = int(totals.get("causal_edges", 0))
    event_diversity = sum(int(w.get("event_type_diversity", 0)) for w in worlds)
    causal_richness = clamp(
        (total_events / max(100, world_count * 20)) * 0.35
        + (total_edges / max(100, world_count * 20)) * 0.35
        + (event_diversity / max(20, world_count * 5)) * 0.30
    )
    if total_events == 0:
        warnings.append("no causal events recorded")
    if total_edges == 0:
        warnings.append("no causal edges recorded")

    discoveries = int(totals.get("discoveries", 0))
    great_persons = int(totals.get("great_persons", 0))
    state_types = sum(int(w.get("state_capacity_types", 0)) for w in worlds)
    repression_types = sum(int(w.get("repression_types", 0)) for w in worlds)
    conflict_types = sum(int(w.get("conflict_types", 0)) for w in worlds)
    civilization_richness = clamp(
        discoveries / max(5, world_count) * 0.25
        + great_persons / max(3, world_count) * 0.20
        + state_types / max(5, world_count) * 0.20
        + repression_types / max(5, world_count) * 0.15
        + conflict_types / max(5, world_count) * 0.20
    )
    if conflict_types <= world_count:
        warnings.append("conflict_type diversity is low")

    movements = int(fed.get("cross_world_movements", 0) or 0)
    diffusion = int(fed.get("diffusion_events", 0) or 0)
    diplomacy = int(fed.get("diplomatic_relations", 0) or 0)
    fed_events = int(fed.get("causal_events", 0) or 0)
    federation_richness = clamp(
        movements / 10 * 0.35
        + diffusion / 5 * 0.25
        + diplomacy / 3 * 0.25
        + fed_events / 50 * 0.15
    )
    if movements == 0:
        warnings.append("cross-world movements are zero")
    if diffusion == 0:
        warnings.append("diffusion events are zero")
    if diplomacy == 0:
        warnings.append("diplomatic relations are zero")

    reports = summary.get("yearly_reports", []) if isinstance(summary, dict) else []
    narrative_richness = clamp(
        len(reports) / max(5, world_count) * 0.7 + discoveries / max(5, world_count) * 0.3
    )
    if not reports:
        warnings.append("yearly_reports missing from causal_summary.json")

    overall = (
        engine_health * 0.25
        + causal_richness * 0.30
        + civilization_richness * 0.20
        + federation_richness * 0.15
        + narrative_richness * 0.10
    )

    # -----------------------------------------------------------------------
    # Phase 12 quality gates
    # -----------------------------------------------------------------------
    pop_stats = _population_summary(summary)
    factions_per_world = _factions_per_world(Path(run_dir))
    factions_summary = _factions_summary(factions_per_world)
    worlds_with_factions = factions_summary["worlds_with_active_factions"]
    total_factions = factions_summary["total_active_factions"]
    metadata = _metadata_summary(summary)
    years = int(metadata.get("years") or 0)
    is_long_run = years >= LONG_RUN_YEARS

    # Gate 1: faction formation is absent or sparse.
    if world_count and worlds_with_factions / world_count < FRACTION_CRITICAL:
        warnings.append(
            f"faction formation is absent or sparse "
            f"({worlds_with_factions}/{world_count} worlds have active factions; "
            f"threshold {FRACTION_CRITICAL:.0%})"
        )
        overall = min(overall, FRACTION_CRITICAL_CAP)

    # Gate 2: population collapse in a long run.
    min_pop = pop_stats.get("min_population")
    if is_long_run and min_pop is not None and min_pop <= 1:
        worst_world = min(pop_stats["populations"], key=pop_stats["populations"].get)
        warnings.append(
            f"population collapse in {worst_world} "
            f"(min_world_population={min_pop}, years={years})"
        )
        overall = min(overall, POP_COLLAPSE_CAP)

    # Gate 3: population CV too high.
    cv = pop_stats.get("population_cv")
    if cv is not None and cv > POP_CV_HIGH:
        warnings.append(
            f"population cross-world CV is high (cv={cv:.3f} > {POP_CV_HIGH})"
        )
        overall = min(overall, POP_CV_HIGH_CAP)

    # Gate 4: run metadata missing or zeroed.
    metadata_warnings: list[str] = []
    if metadata.get("seed") in (None, 0):
        metadata_warnings.append("seed missing or zero in causal_summary.json")
    if metadata.get("ticks_per_year") in (None, 0):
        metadata_warnings.append("ticks_per_year missing or zero in causal_summary.json")
    if metadata.get("engine_version") in (None, ""):
        metadata_warnings.append("engine_version missing in causal_summary.json")
    if metadata.get("git_commit") in (None, ""):
        metadata_warnings.append("git_commit missing in causal_summary.json")
    if not summary:
        metadata_warnings.append("causal_summary.json missing entirely")
    if metadata_warnings:
        warnings.append("run metadata missing or zeroed: " + "; ".join(metadata_warnings))

    # -----------------------------------------------------------------------
    # Output
    # -----------------------------------------------------------------------
    return {
        "overall_score": round(overall, 3),
        "engine_health": round(engine_health, 3),
        "causal_richness": round(causal_richness, 3),
        "civilization_richness": round(civilization_richness, 3),
        "federation_richness": round(federation_richness, 3),
        "narrative_richness": round(narrative_richness, 3),
        "counts": {
            "worlds": world_count,
            "causal_events": total_events,
            "causal_edges": total_edges,
            "discoveries": discoveries,
            "great_persons": great_persons,
            "cross_world_movements": movements,
            "diffusion_events": diffusion,
            "diplomatic_relations": diplomacy,
            "min_world_population": min_pop,
            "max_world_population": pop_stats.get("max_population"),
            "population_cv": (round(cv, 3) if cv is not None else None),
            "worlds_with_factions": worlds_with_factions,
            "total_factions": total_factions,
            "worlds_with_faction_formations": factions_summary["worlds_with_faction_formations"],
            "total_faction_formations": factions_summary["total_faction_formations"],
        },
        "metadata": metadata,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate_run(args.run_dir)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
        print(f"wrote {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
