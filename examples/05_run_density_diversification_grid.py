"""05 — Run a density-diversification grid.

Copy-paste battery for the core Phase 11/12 population-balance claim:
run the same small Aurelia setup at three density-diversification levels
(no / mid / full) across two seeds, then compare final cross-world
population CV.

This example uses the local SQLite simulation path directly. It does not
require HuggingFace exports or Cloudflare credentials.

Usage:
    PYTHONPATH=. python3 examples/05_run_density_diversification_grid.py --dry-run
    PYTHONPATH=. python3 examples/05_run_density_diversification_grid.py
    PYTHONPATH=. python3 examples/05_run_density_diversification_grid.py --years 5 --npc 50 --seeds 4101 4102
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import NamedTuple, Optional

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_SRC = _REPO / "src_template"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from src_template import density_diversification_effect, federation_orchestrator  # noqa: E402


class GridPoint(NamedTuple):
    label: str
    density: float
    seed: int


DENSITY_LEVELS: tuple[tuple[str, float], ...] = (
    ("no-diversify", 0.0),
    ("mid-diversify", 0.5),
    ("full-diversify", 1.0),
)
DEFAULT_SEEDS = (4101, 4102)


def build_grid_plan(seeds: list[int] | tuple[int, ...] = DEFAULT_SEEDS) -> list[GridPoint]:
    """Return the 3 × N density battery in stable, readable order."""
    return [GridPoint(label, density, int(seed)) for label, density in DENSITY_LEVELS for seed in seeds]


def _world_populations(summary: dict) -> dict[str, int]:
    worlds = summary.get("worlds") or {}
    return {world: int(data.get("population", 0)) for world, data in sorted(worlds.items())}


def run_one(point: GridPoint, *, years: int, npc: int, ticks_per_year: int, max_interactions: int, out_root: Path) -> dict:
    """Run one grid point and return a compact result dictionary."""
    out_dir = out_root / f"{point.label}-seed{point.seed}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    start = time.time()
    summary = federation_orchestrator.run_causal_simulation(
        output_dir=out_dir,
        years=years,
        npc_count=npc,
        ticks_per_year=ticks_per_year,
        seed=point.seed,
        max_interactions=max_interactions,
        density_diversification=point.density,
    )
    pops = _world_populations(summary)
    return {
        "label": point.label,
        "density": point.density,
        "seed": point.seed,
        "years": years,
        "npc": npc,
        "ticks_per_year": ticks_per_year,
        "wall_s": round(time.time() - start, 2),
        "populations": pops,
        "population_cv": round(density_diversification_effect.coefficient_of_variation(pops.values()), 4),
        "events_scheduled": int(summary.get("effects_scheduled", 0)),
        "effects_imported": int(summary.get("effects_imported", 0)),
        "output_dir": str(out_dir),
    }


def summarize_grid_results(results: list[dict]) -> dict:
    """Aggregate per-label CVs and reductions relative to no-diversify."""
    by_label: dict[str, list[dict]] = {}
    for result in results:
        by_label.setdefault(str(result["label"]), []).append(result)

    baseline_cvs = [float(r["population_cv"]) for r in by_label.get("no-diversify", [])]
    baseline_mean = sum(baseline_cvs) / len(baseline_cvs) if baseline_cvs else 0.0
    out: dict[str, dict] = {}
    for label, rows in by_label.items():
        cvs = [float(r["population_cv"]) for r in rows]
        mean_cv = sum(cvs) / len(cvs) if cvs else 0.0
        out[label] = {
            "runs": len(rows),
            "mean_population_cv": round(mean_cv, 4),
            "min_population_cv": round(min(cvs), 4) if cvs else 0.0,
            "max_population_cv": round(max(cvs), 4) if cvs else 0.0,
            "reduction_vs_no_diversify": round(1.0 - (mean_cv / baseline_mean), 4) if baseline_mean else 0.0,
        }
    return out


def _write_report(results: list[dict], aggregate: dict, report_dir: Path) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    qpath = report_dir / "phase12-density-grid-quality.json"
    qpath.write_text(json.dumps({"aggregate": aggregate, "runs": results}, indent=2, sort_keys=True))

    lines = [
        "# Aurelia Density-Diversification Grid — Phase 12",
        "",
        "Three density settings × two seeds. Lower population CV means the five worlds ended closer to population balance.",
        "",
        "## Aggregate",
        "",
        "| label | runs | mean CV | min CV | max CV | reduction vs no-diversify |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label in ("no-diversify", "mid-diversify", "full-diversify"):
        row = aggregate.get(label, {})
        lines.append(
            f"| {label} | {row.get('runs', 0)} | {row.get('mean_population_cv', 0):.4f} | "
            f"{row.get('min_population_cv', 0):.4f} | {row.get('max_population_cv', 0):.4f} | "
            f"{row.get('reduction_vs_no_diversify', 0) * 100:.1f}% |"
        )
    lines.extend([
        "",
        "## Per-run detail",
        "",
        "| label | seed | density | wall_s | population CV | populations |",
        "|---|---:|---:|---:|---:|---|",
    ])
    for r in results:
        lines.append(
            f"| {r['label']} | {r['seed']} | {r['density']:.2f} | {r['wall_s']:.2f} | "
            f"{r['population_cv']:.4f} | `{json.dumps(r['populations'], sort_keys=True)}` |"
        )
    mpath = report_dir / "phase12-density-grid-report.md"
    mpath.write_text("\n".join(lines) + "\n")
    return qpath, mpath


def _print_plan(plan: list[GridPoint]) -> None:
    print(f"Density-diversification grid: {len(plan)} planned runs")
    for p in plan:
        print(f"  {p.label:<15} seed={p.seed} density={p.density:.2f}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Aurelia density-diversification grid")
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--npc", type=int, default=100)
    parser.add_argument("--ticks-per-year", type=int, default=6)
    parser.add_argument("--max-interactions", type=int, default=120)
    parser.add_argument("--out-root", default="/tmp/aurelia-density-grid")
    parser.add_argument("--report-dir", default=str(_REPO / "docs" / "reports"))
    parser.add_argument("--dry-run", action="store_true", help="Print the 3×N battery without running simulation")
    args = parser.parse_args(argv)

    plan = build_grid_plan(args.seeds)
    _print_plan(plan)
    if args.dry_run:
        return 0

    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for point in plan:
        print(f"[start] {point.label} seed={point.seed} density={point.density:.2f}", flush=True)
        result = run_one(
            point,
            years=args.years,
            npc=args.npc,
            ticks_per_year=args.ticks_per_year,
            max_interactions=args.max_interactions,
            out_root=out_root,
        )
        results.append(result)
        print(
            f"[done]  {point.label} seed={point.seed} cv={result['population_cv']:.4f} "
            f"wall={result['wall_s']:.2f}s pops={result['populations']}",
            flush=True,
        )

    aggregate = summarize_grid_results(results)
    qpath, mpath = _write_report(results, aggregate, Path(args.report_dir))
    print("\nAggregate:")
    print(json.dumps(aggregate, indent=2, sort_keys=True))
    print(f"\nWrote {qpath}")
    print(f"Wrote {mpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
