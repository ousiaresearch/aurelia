"""Counterfactual branching tools for Aurelia completed run artifacts.

This layer creates deterministic branch directories from a baseline run, applies
explicit intervention records to SQLite causal ledgers/metric rows, and compares
baseline vs branch outcomes. It is intentionally post-run and reproducible:
same baseline + same intervention JSON => same branch artifact.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any


def load_intervention(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    data.setdefault("branch_id", Path(path).stem)
    data.setdefault("interventions", [])
    return data


def _copy_baseline(baseline: Path, branch: Path) -> None:
    if branch.exists():
        shutil.rmtree(branch)
    shutil.copytree(baseline, branch)


def _connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _event_type(intervention_type: str) -> str:
    return f"counterfactual_{intervention_type}"


def _apply_metric_delta(db: sqlite3.Connection, intervention: dict[str, Any]) -> int:
    if not _table_exists(db, "civilization_metrics"):
        return 0
    tick = int(intervention.get("tick", 0))
    payload = intervention.get("payload") or {}
    duration = int(payload.get("duration_ticks", 999999))
    end_tick = tick + max(0, duration - 1)
    metric_fields = {
        "education_level", "urbanization", "youth_bulge", "disease_pressure",
        "resource_stock", "property_rights", "path_lock_in",
    }
    rows = db.execute(
        "SELECT rowid, * FROM civilization_metrics WHERE tick_number >= ? AND tick_number <= ? ORDER BY tick_number",
        (tick, end_tick),
    ).fetchall()
    changed = 0
    for row in rows:
        updates: list[str] = []
        params: list[Any] = []
        for field, delta in payload.items():
            if field not in metric_fields:
                continue
            current = float(row[field] or 0)
            # disease pressure is allowed to decrease via negative deltas; all fields remain bounded.
            updates.append(f"{field} = ?")
            params.append(_clamp(current + float(delta)))
        if updates:
            params.append(row["rowid"])
            db.execute(f"UPDATE civilization_metrics SET {', '.join(updates)} WHERE rowid = ?", params)
            changed += 1
    return changed


def _insert_counterfactual_event(db: sqlite3.Connection, intervention: dict[str, Any], metric_rows_changed: int) -> str:
    if not _table_exists(db, "causal_events"):
        return ""
    tick = int(intervention.get("tick", 0))
    world_id = str(intervention.get("world_id"))
    itype = str(intervention.get("type", "intervention"))
    event_id = f"cf:{world_id}:{tick}:{itype}:{abs(hash(json.dumps(intervention, sort_keys=True))) & 0xffffffffffff:x}"
    payload = dict(intervention.get("payload") or {})
    payload["metric_rows_changed"] = metric_rows_changed
    now = time.time()
    db.execute(
        """
        INSERT OR REPLACE INTO causal_events
          (event_id, tick_number, world_id, layer, event_type, actor_ids, target_ids,
           scope, magnitude, valence, confidence, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id, tick, world_id, "macro", _event_type(itype), "[]", "[]",
            "world", float(payload.get("magnitude", 0.7)), float(payload.get("valence", 0.3)),
            1.0, json.dumps(payload, sort_keys=True), now,
        ),
    )
    if _table_exists(db, "causal_edges"):
        # Connect to all events at the same tick as an explicit intervention perturbation.
        rows = db.execute("SELECT event_id FROM causal_events WHERE tick_number = ? AND event_id != ? LIMIT 25", (tick, event_id)).fetchall()
        for row in rows:
            db.execute("INSERT INTO causal_edges VALUES (?, ?, ?, ?)", (event_id, row["event_id"], "counterfactual_perturbation", 0.6))
    return event_id


def apply_intervention(branch_dir: str | Path, intervention: dict[str, Any]) -> dict[str, Any]:
    branch = Path(branch_dir)
    world_id = intervention.get("world_id")
    if not world_id:
        raise ValueError("intervention missing world_id")
    db_path = branch / f"{world_id}.db"
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    db = _connect(db_path)
    metric_rows_changed = _apply_metric_delta(db, intervention)
    event_id = _insert_counterfactual_event(db, intervention, metric_rows_changed)
    db.commit(); db.close()
    return {"world_id": world_id, "type": intervention.get("type"), "tick": intervention.get("tick"), "event_id": event_id, "metric_rows_changed": metric_rows_changed}


def apply_intervention_file(baseline_dir: str | Path, branch_dir: str | Path, intervention_file: str | Path) -> dict[str, Any]:
    baseline = Path(baseline_dir)
    branch = Path(branch_dir)
    spec = load_intervention(intervention_file)
    _copy_baseline(baseline, branch)
    applied = [apply_intervention(branch, i) for i in spec.get("interventions", [])]
    manifest = {
        "branch_id": spec["branch_id"],
        "base_seed": spec.get("base_seed"),
        "baseline_dir": str(baseline),
        "branch_dir": str(branch),
        "interventions_applied": len(applied),
        "applied": applied,
    }
    (branch / "counterfactual_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def _avg_metric(db: sqlite3.Connection, field: str) -> float:
    if not _table_exists(db, "civilization_metrics"):
        return 0.0
    row = db.execute(f"SELECT AVG({field}) FROM civilization_metrics").fetchone()
    return float(row[0] or 0.0)


def _count(db: sqlite3.Connection, table: str) -> int:
    if not _table_exists(db, table):
        return 0
    return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def compare_runs(baseline_dir: str | Path, branch_dir: str | Path) -> dict[str, Any]:
    baseline = Path(baseline_dir)
    branch = Path(branch_dir)
    worlds: dict[str, Any] = {}
    for bdb in sorted(baseline.glob("*.db")):
        if bdb.name == "federation.db":
            continue
        world = bdb.stem
        cdb = branch / bdb.name
        if not cdb.exists():
            continue
        b = _connect(bdb); c = _connect(cdb)
        worlds[world] = {
            "causal_events_delta": _count(c, "causal_events") - _count(b, "causal_events"),
            "causal_edges_delta": _count(c, "causal_edges") - _count(b, "causal_edges"),
            "avg_resource_stock_delta": round(_avg_metric(c, "resource_stock") - _avg_metric(b, "resource_stock"), 6),
            "avg_education_level_delta": round(_avg_metric(c, "education_level") - _avg_metric(b, "education_level"), 6),
            "avg_disease_pressure_delta": round(_avg_metric(c, "disease_pressure") - _avg_metric(b, "disease_pressure"), 6),
        }
        b.close(); c.close()
    return {"baseline_dir": str(baseline), "branch_dir": str(branch), "worlds": worlds}


def render_comparison_report(comparison: dict[str, Any]) -> str:
    lines = ["# Aurelia Counterfactual Comparison", ""]
    lines.append(f"- baseline: `{comparison['baseline_dir']}`")
    lines.append(f"- branch: `{comparison['branch_dir']}`")
    lines.append("")
    lines.append("## World deltas")
    for world, data in comparison.get("worlds", {}).items():
        lines.append("")
        lines.append(f"### {world}")
        for key, value in data.items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"
