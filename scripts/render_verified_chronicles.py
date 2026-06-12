#!/usr/bin/env python3
"""Render provenance-preserving Phase 13 verified chronicle cards."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]


def _load_summary(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "causal_summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _year_tick_bounds(year: int, ticks_per_year: int | None) -> tuple[int | None, int | None]:
    if not ticks_per_year:
        return None, None
    start = ((year - 1) * ticks_per_year) + 1
    end = year * ticks_per_year
    return start, end


def _top_event_types(
    db_path: Path,
    world_id: str,
    start_tick: int | None,
    end_tick: int | None,
) -> list[str]:
    if not db_path.exists():
        return []
    db = sqlite3.connect(db_path)
    try:
        where = ["world_id = ?"]
        args: list[Any] = [world_id]
        if start_tick is not None:
            where.append("tick_number >= ?")
            args.append(start_tick)
        if end_tick is not None:
            where.append("tick_number <= ?")
            args.append(end_tick)
        sql = (
            "SELECT event_type, COUNT(*) AS n "
            f"FROM causal_events WHERE {' AND '.join(where)} "
            "GROUP BY event_type ORDER BY n DESC, event_type LIMIT 8"
        )
        return [row[0] for row in db.execute(sql, args).fetchall()]
    finally:
        db.close()


def _highlight_event_types(report: dict[str, Any]) -> list[str]:
    return [
        h.get("event_type")
        for h in report.get("causal_highlights", [])
        if h.get("event_type")
    ]


def build_verified_chronicle_cards(run_dir: str | Path) -> list[dict[str, Any]]:
    """Build deterministic, source-backed chronicle cards for a run directory."""
    run_dir = Path(run_dir)
    summary = _load_summary(run_dir)
    ticks_per_year = summary.get("ticks_per_year")
    run_id = summary.get("run_id") or run_dir.name
    cards: list[dict[str, Any]] = []

    for report in summary.get("yearly_reports", []):
        world_id = report.get("world_id")
        year = int(report.get("year", 0))
        if not world_id or not year:
            continue

        world_db = run_dir / f"{world_id}.db"
        start_tick, end_tick = _year_tick_bounds(year, ticks_per_year)
        top_event_types = _top_event_types(world_db, world_id, start_tick, end_tick)
        if not top_event_types:
            top_event_types = _highlight_event_types(report)

        cards.append(
            {
                "run_id": run_id,
                "world_id": world_id,
                "year": year,
                "title": f"Year {year} — {world_id.title()}",
                "metrics": {
                    "population": report.get("population"),
                    "births": report.get("births"),
                    "deaths": report.get("deaths"),
                    "factions": len(report.get("factions") or {}),
                },
                "evidence": {
                    "top_event_types": top_event_types,
                    "causal_highlights": report.get("causal_highlights", []),
                    "tick_range": [start_tick, end_tick],
                },
                "source_paths": {
                    "summary": str(run_dir / "causal_summary.json"),
                    "world_db": str(world_db),
                },
                "provenance_status": "verified" if summary and world_db.exists() else "partial",
            }
        )
    return cards


def render_verified_chronicles_markdown(run_dir: str | Path) -> str:
    """Render verified chronicle cards as auditable Markdown."""
    cards = build_verified_chronicle_cards(run_dir)
    lines = ["# Aurelia Verified Chronicles", ""]
    lines.append(
        "Deterministic Phase 13 chronicle cards. These are evidence-backed "
        "summaries, not freeform invented prose."
    )
    lines.append("")
    for card in cards:
        lines.append(f"## Year {card['year']} — {card['world_id'].title()}")
        lines.append("")
        lines.append(f"- Run: `{card['run_id']}`")
        lines.append(f"- Provenance: {card['provenance_status']}")
        lines.append(f"- Population: {card['metrics'].get('population')}")
        lines.append(
            f"- Births / deaths: {card['metrics'].get('births')} / "
            f"{card['metrics'].get('deaths')}"
        )
        events = card["evidence"].get("top_event_types", [])
        lines.append(
            f"- Evidence event types: {', '.join(events) if events else 'none'}"
        )
        lines.append(f"- Source summary: `{card['source_paths']['summary']}`")
        lines.append(f"- Source DB: `{card['source_paths']['world_db']}`")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    text = render_verified_chronicles_markdown(args.run_dir)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(f"wrote {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
