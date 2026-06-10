#!/usr/bin/env python3
"""Generate a static SVG research figure for density diversification.

This is the Phase 12 visual research artifact (G1). It loads the
``aurelia-npc-population`` dataset from the local Parquet export at
``/tmp/hf-export``, computes the cross-world population CV for the
``phase11-100y`` baseline and the ``phase11-density-100y`` run, and
renders a small SVG with two bar panels and the headline reduction.

The output is dependency-free: pure Python stdlib + PyArrow for the
data. Embed it in a paper, a notebook, or a README without a heavy
plotting library.

Usage:
    PYTHONPATH=. python3 scripts/plot_density_diversification.py \\
        --output docs/reports/figures/density-diversification.svg
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))
from aurelia_dataset_loader import load_local_table  # noqa: E402

WORLDS = ("solara", "arkos", "mirithane", "valdris", "verge")
RUNS = ("phase11-100y", "phase11-density-100y")

CANVAS_W = 720
CANVAS_H = 360
PANEL_PAD = 60
BAR_GAP = 14
BAR_H = 22


def _coefficient_of_variation(values: Iterable[int | float]) -> float:
    values = list(values)
    if not values:
        return 0.0
    mean = statistics.fmean(values)
    if mean == 0:
        return 0.0
    return statistics.pstdev(values) / mean


def _load_active_population_per_world(run: str, root: Path) -> list[int]:
    """Return active-NPC counts per world for ``run`` from the local export.

    The npc-population dataset is partitioned by world: each per-world
    parquet file under ``data/<run>/<world>/train.parquet`` carries one
    ``run_id`` and one ``final_state`` per row. We read the row count
    of each partition directly and filter by ``final_state == "active"``.
    """
    pops: list[int] = []
    for w in WORLDS:
        pq_path = root / "aurelia-npc-population" / "data" / run / w / "train.parquet"
        if not pq_path.exists():
            return []
        try:
            import pyarrow.parquet as pqlib
            table = pqlib.read_table(pq_path, columns=["final_state"])
            n = sum(1 for s in table.column("final_state").to_pylist() if s == "active")
            pops.append(n)
        except Exception:
            return []
    return pops


def compute_population_cv_summary(
    populations_by_run: dict[str, list[int]],
) -> dict[str, dict]:
    """Compute CV + reduction% per run.

    Input is a ``{run_id: [pops_by_world]}`` mapping. Output is a
    structured per-run record with cv, populations, label, and (for
    the density run) the reduction percentage.
    """
    if not populations_by_run:
        return {}
    summary: dict[str, dict] = {}
    baseline = populations_by_run.get("phase11-100y", [])
    baseline_cv = _coefficient_of_variation(baseline) if baseline else 0.0
    for run, pops in populations_by_run.items():
        cv = _coefficient_of_variation(pops)
        label = "100y baseline" if run == "phase11-100y" else (
            "density 100y" if run == "phase11-density-100y" else run
        )
        reduction = (1 - cv / baseline_cv) * 100 if baseline_cv > 0 else 0.0
        summary[run] = {
            "label": label,
            "populations": pops,
            "cv": cv,
            "reduction_pct": reduction,
        }
    return summary


def render_svg(summary: dict[str, dict], title: str = "Aurelia density diversification") -> str:
    """Render the figure as a self-contained SVG string."""
    if not summary:
        return "<svg xmlns='http://www.w3.org/2000/svg' width='200' height='60'><text>no data</text></svg>"

    panels = list(summary.items())
    panel_w = (CANVAS_W - 2 * PANEL_PAD) / max(1, len(panels))
    svg: list[str] = []
    svg.append(
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {CANVAS_W} {CANVAS_H}' "
        f"width='{CANVAS_W}' height='{CANVAS_H}' font-family='sans-serif'>"
    )
    # Background
    svg.append(f"<rect width='{CANVAS_W}' height='{CANVAS_H}' fill='#0d0d1a'/>")
    # Title
    svg.append(
        f"<text x='{PANEL_PAD}' y='30' fill='#e2e8f0' font-size='18' font-weight='bold'>{title}</text>"
    )
    svg.append(
        f"<text x='{PANEL_PAD}' y='50' fill='#888' font-size='11'>"
        "active NPCs per world at run end (final_state == 'active')</text>"
    )

    # Find the global max so the two panels share a scale.
    max_pop = max((max(d["populations"]) for d in summary.values() if d["populations"]), default=1)

    for i, (run, data) in enumerate(panels):
        panel_x = PANEL_PAD + i * panel_w
        # Panel title
        svg.append(
            f"<text x='{panel_x:.0f}' y='85' fill='#e2e8f0' font-size='13' font-weight='bold'>"
            f"{data['label']}</text>"
        )
        # CV sub-line
        svg.append(
            f"<text x='{panel_x:.0f}' y='102' fill='#4ecdc4' font-size='11'>"
            f"CV = {data['cv']:.4f}</text>"
        )
        # Bars
        for j, w in enumerate(WORLDS):
            value = data["populations"][j] if j < len(data["populations"]) else 0
            y = 120 + j * (BAR_H + BAR_GAP)
            bar_full = (panel_w - 30) - 80  # leave room for label + value
            bar_w = bar_full * (value / max_pop) if max_pop > 0 else 0
            color = "#f6c343" if i == 0 else "#a78bfa"  # baseline gold, density violet
            svg.append(
                f"<rect x='{panel_x + 70:.0f}' y='{y:.0f}' width='{bar_full:.0f}' height='{BAR_H}' "
                f"fill='#1a1a2e' rx='2'/>"
            )
            svg.append(
                f"<rect x='{panel_x + 70:.0f}' y='{y:.0f}' width='{bar_w:.0f}' height='{BAR_H}' "
                f"fill='{color}' rx='2'/>"
            )
            svg.append(
                f"<text x='{panel_x + 5:.0f}' y='{y + 16:.0f}' fill='#e2e8f0' font-size='11'>{w}</text>"
            )
            svg.append(
                f"<text x='{panel_x + 75 + bar_full + 6:.0f}' y='{y + 16:.0f}' fill='#e2e8f0' font-size='11'>"
                f"{value}</text>"
            )

    # Headline reduction
    if len(panels) >= 2 and panels[1][1]["reduction_pct"] > 0:
        reduction_text = f"Cross-world population CV reduction: {panels[1][1]['reduction_pct']:.1f}%"
        svg.append(
            f"<text x='{PANEL_PAD}' y='{CANVAS_H - 16}' fill='#f6c343' font-size='14' font-weight='bold'>"
            f"{reduction_text}</text>"
        )

    svg.append("</svg>")
    return "\n".join(svg)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--export-root",
        default="/tmp/hf-export",
        help="Local HF export root (default: /tmp/hf-export)",
    )
    p.add_argument(
        "--output",
        default="docs/reports/figures/density-diversification.svg",
        help="Output SVG path",
    )
    p.add_argument(
        "--no-pretty",
        action="store_true",
        help="Skip pretty-printing the SVG (for tests)",
    )
    args = p.parse_args(argv)

    populations: dict[str, list[int]] = {}
    for run in RUNS:
        pops = _load_active_population_per_world(run, Path(args.export_root))
        if pops:
            populations[run] = pops

    if not populations:
        print(
            f"No npc-population data found at {args.export_root}. "
            "Run a Phase 11 export first."
        )
        return 1

    summary = compute_population_cv_summary(populations)
    svg = render_svg(summary)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.no_pretty:
        out.write_text(svg)
    else:
        # Pretty-print with a 2-space indent for human inspection.
        from xml.dom import minidom
        try:
            pretty = minidom.parseString(svg).toprettyxml(indent="  ")
        except Exception:
            pretty = svg
        out.write_text(pretty)
    print(f"wrote {out} ({len(svg):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
