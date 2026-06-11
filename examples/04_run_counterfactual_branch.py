"""04 — Run a counterfactual branch and quantify the divergence.

This is the *fourth* thing a researcher should run. Pattern from
Aurelia's Phase 11.5 surface: two simulations with the same seed and
one knob changed, then `compare_runs` quantifies the divergence.

Headline question: "What if density_diversification were 1.0 the whole
time instead of 0.0?" Same seed -> same initial NPC draws and macro
state -> divergent causal histories from a single parameter change.

Wall time: ~60 seconds on an M3 Mac (two 50y npc_count=80 simulations
back-to-back). The point is reproducibility, not scale.

Usage:
    PYTHONPATH=src_template python examples/04_run_counterfactual_branch.py
    PYTHONPATH=src_template python examples/04_run_counterfactual_branch.py --years 100
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_SRC = _REPO / "src_template"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import federation_orchestrator
from counterfactuals import compare_runs, render_comparison_report


def run(out_dir: Path, *, years: int, npc_count: int, seed: int, density: float) -> dict:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    summary = federation_orchestrator.run_causal_simulation(
        output_dir=out_dir, years=years, npc_count=npc_count, seed=seed,
        density_diversification=density,
    )
    return {"summary": summary, "wall": time.time() - t0}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", type=int, default=50)
    ap.add_argument("--npc", type=int, default=80)
    ap.add_argument("--seed", type=int, default=1001)
    ap.add_argument("--out-root", default="/tmp/aurelia-cf-demo")
    args = ap.parse_args()

    out_root = Path(args.out_root)
    baseline = out_root / "baseline_density0"
    branch = out_root / "branch_density1"

    print(f"[start] baseline: density=0.0 years={args.years} npc={args.npc} seed={args.seed}")
    b = run(baseline, years=args.years, npc_count=args.npc, seed=args.seed, density=0.0)
    print(f"[done]  baseline wall={b['wall']:.1f}s  worlds={list(b['summary']['worlds'].keys())}")

    print(f"[start] branch:   density=1.0 years={args.years} npc={args.npc} seed={args.seed}")
    c = run(branch, years=args.years, npc_count=args.npc, seed=args.seed, density=1.0)
    print(f"[done]  branch   wall={c['wall']:.1f}s")

    print("\n[compare] computing divergence...")
    comparison = compare_runs(baseline, branch)

    print("\n=== Counterfactual Divergence Report ===")
    print(f"divergence_score: {comparison['divergence_score']}")
    print(f"warnings:         {comparison.get('warnings', []) or 'none'}")
    print("\nTop changed event types:")
    for row in comparison.get("top_changed_event_types", [])[:8]:
        print(f"  {row['event_type']:35s} delta={row['delta']:>+8,}")
    print("\nPer-world deltas:")
    for world, data in comparison.get("worlds", {}).items():
        print(f"  {world:10s} events={data['causal_events_delta']:+5,}  edges={data['causal_edges_delta']:+6,}  "
              f"resource={data['avg_resource_stock_delta']:+.3f}  "
              f"education={data['avg_education_level_delta']:+.3f}  "
              f"disease={data['avg_disease_pressure_delta']:+.3f}")

    # Save the comparison report alongside the runs
    report_md = render_comparison_report(comparison)
    (out_root / "comparison.md").write_text(report_md)
    print(f"\n[save] full report: {out_root / 'comparison.md'}")
    print(f"       raw JSON:    {out_root / 'comparison.json'}")
    (out_root / "comparison.json").write_text(json.dumps(comparison, indent=2, default=str))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
