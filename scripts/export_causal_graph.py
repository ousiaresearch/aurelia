#!/usr/bin/env python3
"""Export Aurelia causal events/edges from SQLite as graph JSON."""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


def _connect(db_path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    return db


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _json_loads(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def export_graph(
    db_path: str | Path,
    run_id: str = "local-run",
    world_id: str | None = None,
    start_tick: int | None = None,
    end_tick: int | None = None,
) -> dict[str, Any]:
    """Return a portable graph: {nodes, edges, stats}."""
    db = _connect(db_path)
    if not _table_exists(db, "causal_events"):
        raise ValueError(f"{db_path} has no causal_events table")

    where: list[str] = []
    params: list[Any] = []
    if world_id:
        where.append("world_id = ?")
        params.append(world_id)
    if start_tick is not None:
        where.append("tick_number >= ?")
        params.append(start_tick)
    if end_tick is not None:
        where.append("tick_number <= ?")
        params.append(end_tick)
    clause = " WHERE " + " AND ".join(where) if where else ""

    event_rows = db.execute(
        f"""
        SELECT event_id, tick_number, world_id, layer, event_type, actor_ids, target_ids,
               scope, magnitude, valence, confidence, payload, created_at
        FROM causal_events
        {clause}
        ORDER BY tick_number, event_id
        """,
        params,
    ).fetchall()

    nodes = []
    node_ids = set()
    layers = Counter()
    event_types = Counter()
    for row in event_rows:
        node_id = row["event_id"]
        node_ids.add(node_id)
        layer = row["layer"] or "unknown"
        event_type = row["event_type"] or "unknown"
        layers[layer] += 1
        event_types[event_type] += 1
        nodes.append(
            {
                "id": node_id,
                "tick": row["tick_number"],
                "world_id": row["world_id"],
                "layer": layer,
                "event_type": event_type,
                "actor_ids": _json_loads(row["actor_ids"], []),
                "target_ids": _json_loads(row["target_ids"], []),
                "scope": row["scope"],
                "magnitude": row["magnitude"] or 0,
                "valence": row["valence"] or 0,
                "confidence": row["confidence"] or 0,
                "payload": _json_loads(row["payload"], {}),
                "created_at": row["created_at"],
            }
        )

    edges = []
    if _table_exists(db, "causal_edges") and node_ids:
        placeholders = ",".join("?" for _ in node_ids)
        edge_rows = db.execute(
            f"""
            SELECT parent_event_id, child_event_id, relation, weight
            FROM causal_edges
            WHERE parent_event_id IN ({placeholders}) AND child_event_id IN ({placeholders})
            ORDER BY parent_event_id, child_event_id
            """,
            list(node_ids) + list(node_ids),
        ).fetchall()
        for row in edge_rows:
            edges.append(
                {
                    "source": row["parent_event_id"],
                    "target": row["child_event_id"],
                    "relation": row["relation"] or "contributed_to",
                    "weight": row["weight"] or 0,
                }
            )

    db.close()
    return {
        "run_id": run_id,
        "world_id": world_id,
        "tick_range": [start_tick, end_tick],
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "nodes": len(nodes),
            "edges": len(edges),
            "layers": dict(layers),
            "event_types": dict(event_types.most_common(50)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="SQLite DB to export")
    parser.add_argument("--run-dir", type=Path, help="Run directory containing <world>.db")
    parser.add_argument("--world", dest="world_id", help="World ID, e.g. solara")
    parser.add_argument("--run-id", default="local-run")
    parser.add_argument("--start-tick", type=int)
    parser.add_argument("--end-tick", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    db_path = args.db or (args.run_dir / f"{args.world_id}.db" if args.run_dir and args.world_id else None)
    if not db_path:
        parser.error("provide --db or --run-dir + --world")
    graph = export_graph(db_path, args.run_id, args.world_id, args.start_tick, args.end_tick)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(graph, indent=2, sort_keys=True))
    print(f"wrote {args.output} nodes={graph['stats']['nodes']} edges={graph['stats']['edges']}")


if __name__ == "__main__":
    main()
