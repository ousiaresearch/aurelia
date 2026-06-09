#!/usr/bin/env python3
"""Score an Aurelia run for engine health and civilizational richness."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aurelia_run_inspect import inspect_run


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def evaluate_run(run_dir: str | Path) -> dict[str, Any]:
    data = inspect_run(run_dir)
    worlds = data["worlds"]
    fed = data["federation"]
    totals = data["totals"]
    warnings: list[str] = []

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
    causal_richness = clamp((total_events / max(100, world_count * 20)) * 0.35 + (total_edges / max(100, world_count * 20)) * 0.35 + (event_diversity / max(20, world_count * 5)) * 0.30)
    if total_events == 0:
        warnings.append("no causal events recorded")
    if total_edges == 0:
        warnings.append("no causal edges recorded")

    discoveries = int(totals.get("discoveries", 0))
    great_persons = int(totals.get("great_persons", 0))
    state_types = sum(int(w.get("state_capacity_types", 0)) for w in worlds)
    repression_types = sum(int(w.get("repression_types", 0)) for w in worlds)
    conflict_types = sum(int(w.get("conflict_types", 0)) for w in worlds)
    civilization_richness = clamp(discoveries / max(5, world_count) * 0.25 + great_persons / max(3, world_count) * 0.20 + state_types / max(5, world_count) * 0.20 + repression_types / max(5, world_count) * 0.15 + conflict_types / max(5, world_count) * 0.20)
    if conflict_types <= world_count:
        warnings.append("conflict_type diversity is low")

    movements = int(fed.get("cross_world_movements", 0) or 0)
    diffusion = int(fed.get("diffusion_events", 0) or 0)
    diplomacy = int(fed.get("diplomatic_relations", 0) or 0)
    fed_events = int(fed.get("causal_events", 0) or 0)
    federation_richness = clamp(movements / 10 * 0.35 + diffusion / 5 * 0.25 + diplomacy / 3 * 0.25 + fed_events / 50 * 0.15)
    if movements == 0:
        warnings.append("cross-world movements are zero")
    if diffusion == 0:
        warnings.append("diffusion events are zero")
    if diplomacy == 0:
        warnings.append("diplomatic relations are zero")

    reports = data["summary"].get("yearly_reports", []) if isinstance(data.get("summary"), dict) else []
    narrative_richness = clamp(len(reports) / max(5, world_count) * 0.7 + discoveries / max(5, world_count) * 0.3)
    if not reports:
        warnings.append("yearly_reports missing from causal_summary.json")

    overall = round((engine_health * 0.25 + causal_richness * 0.30 + civilization_richness * 0.20 + federation_richness * 0.15 + narrative_richness * 0.10), 3)
    return {
        "overall_score": overall,
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
        },
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
