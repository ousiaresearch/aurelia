#!/usr/bin/env python3
"""Render a human-readable Markdown report from an Aurelia run directory."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aurelia_run_inspect import inspect_run


def _fmt_top(items: list[tuple[str, int]], empty: str = "none") -> str:
    if not items:
        return empty
    return ", ".join(f"{name} ({count})" for name, count in items[:6])


def render_report(run_dir: str | Path, *, run_id: str | None = None) -> str:
    data = inspect_run(run_dir)
    summary: dict[str, Any] = data["summary"]
    totals: dict[str, int] = data["totals"]
    lines: list[str] = []
    lines.append("# Aurelia Run Report")
    lines.append("")
    if run_id:
        lines.append(f"**Run ID:** `{run_id}`")
        lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append(f"- run_dir: `{Path(run_dir)}`")
    if summary:
        lines.append(f"- years: {summary.get('years', 'unknown')}")
        lines.append(f"- ticks: {summary.get('ticks', 'unknown')}")
        if summary.get("seed") is not None:
            lines.append(f"- seed: {summary.get('seed')}")
    lines.append("")
    lines.append("## Executive summary")
    lines.append("")
    lines.append(f"- worlds: {len(data['worlds'])}")
    lines.append(f"- causal events: {totals.get('causal_events', 0)}")
    lines.append(f"- causal edges: {totals.get('causal_edges', 0)}")
    lines.append(f"- civilization metric rows: {totals.get('metrics', 0)}")
    lines.append(f"- discoveries: {totals.get('discoveries', 0)}")
    lines.append(f"- great persons: {totals.get('great_persons', 0)}")
    fed = data["federation"]
    if fed.get("present"):
        lines.append(f"- cross-world movements: {fed.get('cross_world_movements', 0)}")
        lines.append(f"- diffusion events: {fed.get('diffusion_events', 0)}")
        lines.append(f"- diplomatic relations: {fed.get('diplomatic_relations', 0)}")
    lines.append("")
    lines.append("## World outcomes")
    for world in data["worlds"]:
        lines.append("")
        lines.append(f"### {world['world_id']}")
        lines.append(f"- causal events: {world.get('causal_events', 0)}")
        lines.append(f"- causal edges: {world.get('causal_edges', 0)}")
        lines.append(f"- event type diversity: {world.get('event_type_diversity', 0)}")
        lines.append(f"- discoveries: {world.get('discoveries', 0)}")
        lines.append(f"- great persons: {world.get('great_persons', 0)}")
        lines.append(f"- top event types: {_fmt_top(world.get('top_event_types', []))}")
    lines.append("")
    lines.append("## Federation dynamics")
    lines.append("")
    if fed.get("present"):
        lines.append(f"- cross-world movements: {fed.get('cross_world_movements', 0)}")
        lines.append(f"- movement types: {_fmt_top(fed.get('movement_types', []))}")
        lines.append(f"- diffusion events: {fed.get('diffusion_events', 0)}")
        lines.append(f"- diffusion traits: {_fmt_top(fed.get('diffusion_traits', []))}")
        lines.append(f"- diplomatic relations: {fed.get('diplomatic_relations', 0)}")
        lines.append(f"- relation types: {_fmt_top(fed.get('relation_types', []))}")
    else:
        lines.append("- federation.db not present")
    lines.append("")
    lines.append("## Causal graph")
    lines.append("")
    lines.append(f"- total nodes/events: {totals.get('causal_events', 0) + totals.get('federation_causal_events', 0)}")
    lines.append(f"- total edges: {totals.get('causal_edges', 0) + totals.get('federation_causal_edges', 0)}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--run-id", type=str, default="")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = render_report(args.run_dir, run_id=args.run_id or None)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report)
        print(f"wrote {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
