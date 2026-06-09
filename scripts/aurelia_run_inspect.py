"""Shared SQLite helpers for Aurelia Phase 11 proof scripts."""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

WORLDS = ["solara", "arkos", "mirithane", "valdris", "verge"]


def connect(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    return db


def table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def count_table(db: sqlite3.Connection, table: str) -> int:
    if not table_exists(db, table):
        return 0
    return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def scalar(db: sqlite3.Connection, sql: str, default: Any = 0) -> Any:
    try:
        row = db.execute(sql).fetchone()
        if row is None:
            return default
        return row[0]
    except sqlite3.Error:
        return default


def distinct_count(db: sqlite3.Connection, table: str, column: str) -> int:
    if not table_exists(db, table):
        return 0
    return int(scalar(db, f"SELECT COUNT(DISTINCT {column}) FROM {table}", 0) or 0)


def top_counts(db: sqlite3.Connection, table: str, column: str, limit: int = 10) -> list[tuple[str, int]]:
    if not table_exists(db, table):
        return []
    try:
        return [(str(r[0]), int(r[1])) for r in db.execute(f"SELECT {column}, COUNT(*) FROM {table} GROUP BY {column} ORDER BY COUNT(*) DESC LIMIT ?", (limit,)).fetchall()]
    except sqlite3.Error:
        return []


def run_world_dbs(run_dir: str | Path) -> list[tuple[str, Path]]:
    root = Path(run_dir)
    dbs: list[tuple[str, Path]] = []
    for p in sorted(root.glob("*.db")):
        if p.name == "federation.db":
            continue
        dbs.append((p.stem, p))
    return dbs


def load_summary(run_dir: str | Path) -> dict[str, Any]:
    path = Path(run_dir) / "causal_summary.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def summarize_world_db(world_id: str, path: str | Path) -> dict[str, Any]:
    db = connect(path)
    summary = {
        "world_id": world_id,
        "causal_events": count_table(db, "causal_events"),
        "causal_edges": count_table(db, "causal_edges"),
        "metrics": count_table(db, "civilization_metrics"),
        "discoveries": count_table(db, "discoveries"),
        "great_persons": count_table(db, "great_persons"),
        "event_type_diversity": distinct_count(db, "causal_events", "event_type"),
        "layers": dict(top_counts(db, "causal_events", "layer", 20)),
        "top_event_types": top_counts(db, "causal_events", "event_type", 10),
        "state_capacity_types": distinct_count(db, "civilization_metrics", "state_capacity_type"),
        "repression_types": distinct_count(db, "civilization_metrics", "repression_type"),
        "conflict_types": distinct_count(db, "civilization_metrics", "conflict_type"),
    }
    if table_exists(db, "agents"):
        summary["agents"] = count_table(db, "agents")
    db.close()
    return summary


def summarize_federation(run_dir: str | Path) -> dict[str, Any]:
    path = Path(run_dir) / "federation.db"
    if not path.exists():
        return {"present": False}
    db = connect(path)
    summary = {
        "present": True,
        "causal_events": count_table(db, "causal_events"),
        "causal_edges": count_table(db, "causal_edges"),
        "cross_world_movements": count_table(db, "cross_world_movements"),
        "diffusion_events": count_table(db, "diffusion_events"),
        "diplomatic_relations": count_table(db, "diplomatic_relations"),
        "movement_types": top_counts(db, "cross_world_movements", "movement_type", 10),
        "diffusion_traits": top_counts(db, "diffusion_events", "trait", 10),
        "relation_types": top_counts(db, "diplomatic_relations", "relation_type", 10),
    }
    db.close()
    return summary


def inspect_run(run_dir: str | Path) -> dict[str, Any]:
    worlds = [summarize_world_db(w, p) for w, p in run_world_dbs(run_dir)]
    federation = summarize_federation(run_dir)
    totals = Counter()
    for w in worlds:
        for k in ["causal_events", "causal_edges", "metrics", "discoveries", "great_persons"]:
            totals[k] += int(w.get(k, 0) or 0)
    for k in ["causal_events", "causal_edges", "cross_world_movements", "diffusion_events", "diplomatic_relations"]:
        totals[f"federation_{k}"] += int(federation.get(k, 0) or 0)
    return {"summary": load_summary(run_dir), "worlds": worlds, "federation": federation, "totals": dict(totals)}
