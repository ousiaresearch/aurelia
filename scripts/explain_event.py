#!/usr/bin/env python3
"""Explain an Aurelia causal event by walking upstream causal_edges."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


def _connect(db_path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    return db


def _row_to_event(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def _upstream(db: sqlite3.Connection, event_id: str, depth: int, seen: set[str]) -> list[dict[str, Any]]:
    if depth <= 0 or event_id in seen:
        return []
    seen.add(event_id)
    rows = db.execute(
        """
        SELECT e.parent_event_id, e.child_event_id, e.relation, e.weight,
               c.*
        FROM causal_edges e
        JOIN causal_events c ON c.event_id = e.parent_event_id
        WHERE e.child_event_id = ?
        ORDER BY e.weight DESC, c.tick_number DESC
        """,
        (event_id,),
    ).fetchall()
    chain = []
    for row in rows:
        parent_id = row["parent_event_id"]
        event = {k: row[k] for k in row.keys() if k not in {"parent_event_id", "child_event_id", "relation", "weight"}}
        chain.append(
            {
                "relation": row["relation"],
                "weight": row["weight"],
                "event": event,
                "upstream": _upstream(db, parent_id, depth - 1, seen.copy()),
            }
        )
    return chain


def explain_event(db_path: str | Path, event_id: str, depth: int = 3) -> dict[str, Any]:
    db = _connect(db_path)
    target = _row_to_event(db.execute("SELECT * FROM causal_events WHERE event_id = ?", (event_id,)).fetchone())
    if target is None:
        db.close()
        raise ValueError(f"event not found: {event_id}")
    explanation = {"target": target, "upstream": _upstream(db, event_id, depth, set())}
    db.close()
    return explanation


def render_text(explanation: dict[str, Any]) -> str:
    lines = ["Target event:"]
    target = explanation["target"]
    lines.append(f"  {target.get('event_type')} at tick {target.get('tick_number')} ({target.get('event_id')})")
    lines.append("\nUpstream causes:")

    def walk(items: list[dict[str, Any]], indent: int = 1) -> None:
        for item in items:
            ev = item["event"]
            prefix = "  " * indent + "- "
            lines.append(f"{prefix}{ev.get('event_type')} tick {ev.get('tick_number')} [{item.get('relation')} w={item.get('weight')}] ({ev.get('event_id')})")
            walk(item.get("upstream", []), indent + 1)

    walk(explanation.get("upstream", []))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    explanation = explain_event(args.db, args.event_id, args.depth)
    print(json.dumps(explanation, indent=2) if args.json else render_text(explanation))


if __name__ == "__main__":
    main()
