#!/usr/bin/env python3
"""Run Aurelia with barrier-synchronized causal federation mechanics."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src_template"))

import federation_orchestrator


def main() -> int:
    p = argparse.ArgumentParser(description="Aurelia causal federated simulation runner")
    p.add_argument("--output", default="/tmp/aurelia-causal-run/output")
    p.add_argument("--years", type=int, default=20)
    p.add_argument("--npcs", type=int, default=1000)
    p.add_argument("--ticks-per-year", type=int, default=12)
    p.add_argument("--worlds", default=",".join(federation_orchestrator.DEFAULT_WORLDS))
    p.add_argument("--seed", type=int, default=777)
    p.add_argument("--max-interactions", type=int, default=500)
    p.add_argument("--birth-scale", type=float, default=1.0)
    p.add_argument("--death-scale", type=float, default=1.0)
    p.add_argument("--clean", action="store_true", help="wipe output dir before running")
    args = p.parse_args()

    out = Path(args.output)
    if args.clean and out.exists():
        shutil.rmtree(out)
    worlds = [w.strip() for w in args.worlds.split(",") if w.strip()]
    summary = federation_orchestrator.run_causal_simulation(
        output_dir=out,
        worlds=worlds,
        years=args.years,
        npc_count=args.npcs,
        ticks_per_year=args.ticks_per_year,
        seed=args.seed,
        max_interactions=args.max_interactions,
        birth_scale=args.birth_scale,
        death_scale=args.death_scale,
    )
    print("=== Aurelia Causal Federation Run Complete ===")
    print(f"Output: {summary['output_dir']}")
    print(f"Ticks: {summary['ticks']} | Years: {summary['years']}")
    print(f"Cross-world effects scheduled/imported: {summary['effects_scheduled']}/{summary['effects_imported']}")
    for world_id, data in summary["worlds"].items():
        print(f"  {world_id}: pop={data['population']:,} dead={data['deceased']:,} factions={data['factions']}")
    print("\nLatest yearly report sample:")
    for report in summary["yearly_reports"][-len(worlds):]:
        print("  " + json.dumps({
            "world": report["world_id"],
            "year": report["year"],
            "pop": report["population"],
            "births": report["births"],
            "deaths": report["deaths"],
            "factions": report["factions"],
            "top_causes": report["causal_highlights"][:3],
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
