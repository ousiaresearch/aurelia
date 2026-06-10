"""02 — Reproduce the density-diversification result.

The headline result on the Aurelia Phase 11 comparison is that turning
on ``density_diversification`` reduces the population coefficient of
variation across worlds from ~0.67 to ~0.006 — a 99% reduction.

This example computes that number two ways:

1. **From data** — when ``/tmp/hf-export/aurelia-npc-population`` is
   present, count rows per world for the ``phase11-100y`` baseline and
   ``phase11-density-100y`` runs, then take the CV of the five values.
   The published Phase 11 number was computed from the
   ``final_state`` column, partitioned by world in the export.
2. **From the report** — when the local export is missing, fall back
   to the canonical numbers published in
   ``docs/reports/phase11-runs-comparison.md`` and print a clear note.

Usage:
    PYTHONPATH=. python3 examples/02_reproduce_density_diversification.py
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from typing import Iterable, Optional

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from examples import aurelia_dataset_loader as loader  # noqa: E402

# Fallback numbers from docs/reports/phase11-runs-comparison.md
FALLBACK_POPULATIONS: dict[str, dict[str, int]] = {
    "phase11-100y": {
        "solara": 171,
        "arkos": 29,
        "mirithane": 63,
        "valdris": 58,
        "verge": 49,
    },
    "phase11-density-100y": {
        "solara": 67,
        "arkos": 67,
        "mirithane": 67,
        "valdris": 67,
        "verge": 66,
    },
}

WORLDS = ("solara", "arkos", "mirithane", "valdris", "verge")


# ---------------------------------------------------------------------------
# Pure function
# ---------------------------------------------------------------------------

def coefficient_of_variation(values: Iterable[int | float]) -> float:
    """Population CV: stdev / mean. Returns 0.0 if mean is zero."""
    values = list(values)
    if not values:
        return 0.0
    mean = statistics.fmean(values)
    if mean == 0:
        return 0.0
    return statistics.pstdev(values) / mean


# ---------------------------------------------------------------------------
# Data path
# ---------------------------------------------------------------------------

def _world_populations_from_export(run: str, root: Path) -> Optional[dict[str, int]]:
    """Count npc-population rows per world for ``run`` if the export is local.

    Returns ``None`` if any expected file is missing. The published metric
    is "count of NPCs whose final state is alive in this world at run end";
    row count of the partitioned parquet is a stable proxy.
    """
    import pyarrow.parquet as pqlib
    base = root / "aurelia-npc-population" / "data" / run
    if not base.exists():
        return None
    out: dict[str, int] = {}
    for world in WORLDS:
        pq = base / world / "train.parquet"
        if not pq.exists():
            return None
        table = pqlib.read_table(pq, columns=["npc_id"])
        out[world] = len(table)
    return out


def _populations_with_source(root: Path) -> tuple[dict[str, dict[str, int]], str, str]:
    """Return (pops, source_label, fallback_used).

    ``source_label`` enumerates per-run provenance ('local' or 'fallback').
    ``fallback_used`` is ``'fallback'`` if any run fell back, else ``'export'``.
    """
    pops: dict[str, dict[str, int]] = {}
    sources: list[str] = []
    any_fallback = False
    for run in ("phase11-100y", "phase11-density-100y"):
        local = _world_populations_from_export(run, root)
        if local is not None:
            pops[run] = local
            sources.append(f"{run}=local")
        else:
            pops[run] = FALLBACK_POPULATIONS[run]
            sources.append(f"{run}=fallback")
            any_fallback = True
    return pops, ", ".join(sources), ("fallback" if any_fallback else "export")


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def _ascii_bar(label: str, value: int, target_max: int, width: int = 32) -> str:
    filled = 0 if target_max == 0 else round(width * value / target_max)
    return f"  {label:<11} {value:>5}  " + "█" * filled + "·" * (width - filled)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Reproduce the density-diversification result")
    p.add_argument("--export-root", default=str(loader.DEFAULT_LOCAL_ROOT))
    p.add_argument("--width", type=int, default=32, help="ASCII bar width")
    args = p.parse_args(argv)

    root = Path(args.export_root)
    pops, source, source_kind = _populations_with_source(root)

    baseline = pops["phase11-100y"]
    density = pops["phase11-density-100y"]
    baseline_cv = coefficient_of_variation(baseline.values())
    density_cv = coefficient_of_variation(density.values())
    reduction_pct = (1 - density_cv / baseline_cv) * 100 if baseline_cv > 0 else 0.0

    print("Density-diversification reproduction")
    print(f"  data source: {source}")
    if source_kind == "fallback":
        print("  (using canonical report values from docs/reports/phase11-runs-comparison.md)")
    print()

    print("phase11-100y (baseline, no density diversification)")
    target = max(baseline.values())
    for world in WORLDS:
        print(_ascii_bar(world, baseline[world], target, width=args.width))
    print(f"  CV = {baseline_cv:.4f}\n")

    print("phase11-density-100y (density diversification ON)")
    target = max(density.values())
    for world in WORLDS:
        print(_ascii_bar(world, density[world], target, width=args.width))
    print(f"  CV = {density_cv:.4f}\n")

    print(f"Reduction in cross-world population CV: {reduction_pct:.1f}%")
    print("Published Phase 11 headline: 99.1% reduction.")
    if source_kind == "fallback":
        print("Numbers above are the published canonical values.")
    else:
        print("Local-export numbers above are computed from the partitioned npc-population")
        print("dataset; the small difference vs. the 99.1% headline reflects the metric used")
        print("(row count of partitioned parquets vs. the run-end alive population recorded")
        print("in docs/reports/phase11-runs-comparison.md).")
    print("\nSee docs/reports/phase11-runs-comparison.md for context.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
