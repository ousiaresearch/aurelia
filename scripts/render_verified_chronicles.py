#!/usr/bin/env python3
"""Render provenance-preserving Phase 13 verified chronicle cards."""
from __future__ import annotations

import argparse
import json
import os
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


def _summary_metadata(summary: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    return {
        "run_id": summary.get("run_id") or run_dir.name,
        "seed": summary.get("seed"),
        "engine_version": summary.get("engine_version"),
        "git_commit": summary.get("git_commit"),
        "density_diversification": summary.get("density_diversification"),
        "years": summary.get("years"),
        "ticks": summary.get("ticks"),
        "ticks_per_year": summary.get("ticks_per_year"),
        "worlds": summary.get("worlds", {}),
        "source_files": {"summary": "causal_summary.json"},
    }


def build_provenance_manifest(run_dir: str | Path) -> dict[str, Any]:
    """Build a durable provenance manifest without host-local absolute paths."""
    run_dir = Path(run_dir)
    summary = _load_summary(run_dir)
    cards = build_verified_chronicle_cards(run_dir)

    manifest_cards = []
    for card in cards:
        world_db = Path(card["source_paths"]["world_db"])
        manifest_cards.append(
            {
                "run_id": card["run_id"],
                "world_id": card["world_id"],
                "year": card["year"],
                "title": card["title"],
                "metrics": card["metrics"],
                "evidence": card["evidence"],
                "provenance_status": card["provenance_status"],
                "source_files": {
                    "summary": "causal_summary.json",
                    "world_db": world_db.name,
                },
            }
        )

    return {
        "schema": "aurelia.phase13.provenance.v1",
        "source_run": _summary_metadata(summary, run_dir),
        "cards": manifest_cards,
    }


def _manifest_link(manifest_path: str | Path, output_path: str | Path | None = None) -> str:
    manifest = Path(manifest_path)
    label = manifest.name
    if output_path:
        target = os.path.relpath(manifest, start=Path(output_path).parent)
    elif manifest.is_absolute():
        target = manifest.name
    else:
        target = str(manifest)
    return f"[{label}]({target})"


def render_verified_chronicles_markdown(
    run_dir: str | Path,
    *,
    manifest_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> str:
    """Render verified chronicle cards as auditable Markdown."""
    cards = build_verified_chronicle_cards(run_dir)
    lines = ["# Aurelia Verified Chronicles", ""]
    lines.append(
        "Deterministic Phase 13 chronicle cards. These are evidence-backed "
        "summaries, not freeform invented prose."
    )
    if manifest_path:
        lines.append("")
        lines.append(f"Committed provenance manifest: {_manifest_link(manifest_path, output_path)}")
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
        lines.append(f"- Factions: {card['metrics'].get('factions')}")
        events = card["evidence"].get("top_event_types", [])
        lines.append(
            f"- Evidence event types: {', '.join(events) if events else 'none'}"
        )
        source_summary = "causal_summary.json" if manifest_path else card["source_paths"]["summary"]
        source_db = Path(card["source_paths"]["world_db"]).name if manifest_path else card["source_paths"]["world_db"]
        lines.append(f"- Source summary: `{source_summary}`")
        lines.append(f"- Source DB: `{source_db}`")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest-output", type=Path)
    args = parser.parse_args(argv)

    text = render_verified_chronicles_markdown(
        args.run_dir,
        manifest_path=args.manifest_output,
        output_path=args.output,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(f"wrote {args.output}")
    else:
        print(text)
    if args.manifest_output:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        manifest = build_provenance_manifest(args.run_dir)
        args.manifest_output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(f"wrote {args.manifest_output}")


if __name__ == "__main__":
    main()
