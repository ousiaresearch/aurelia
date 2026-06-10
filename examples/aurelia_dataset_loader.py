"""Aurelia dataset loader helper.

This module is intentionally tiny and import-safe. It exposes the four
HuggingFace dataset names published by the Aurelia pipeline, plus a
small set of pure-Python helpers that read either of two local sources:

- **Parquet export** at ``/tmp/hf-export/`` (the published research
  archive produced by ``scripts/export_hf_dataset.py``).
- **SQLite smoke runs** under ``/tmp/aurelia-*`` (the raw run artifacts
  produced by ``causal_run.py``; one SQLite file per world plus a
  ``federation.db`` for cross-world events and edges).

The Parquet backend is preferred when both exist. The SQLite backend is
the zero-setup path: a fresh ``causal_run.py --clean --years 1`` takes
~3 seconds and produces a fully queryable local archive.

The helper is offline by default. The HuggingFace parquet URL is only
hit when the caller explicitly asks via :func:`fetch_hf_parquet`.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

HF_ORG = "OusiaResearch"

DATASETS: tuple[str, ...] = (
    "aurelia-causal-events",
    "aurelia-civilization-metrics",
    "aurelia-federation-causal",
    "aurelia-npc-population",
)

DEFAULT_LOCAL_ROOT = Path("/tmp/hf-export")
DEFAULT_SQLITE_ROOT = Path("/tmp")
DEFAULT_HF_PARQUET_URL = "https://huggingface.co/datasets/{org}/{ds}/resolve/main/data/{run}/{world}/train.parquet"

# Mapping from a published dataset to the SQLite table that holds the same
# data inside a smoke-run directory (one *.db per world, plus federation.db).
# Use {"federation": "table", "per_world": null} to read the federation DB only.
SQLITE_TABLE_MAP: dict[str, dict[str, Optional[str]]] = {
    "aurelia-causal-events": {"per_world": "causal_events", "federation": "causal_events"},
    "aurelia-federation-causal": {"per_world": None, "federation": "causal_edges"},
    "aurelia-civilization-metrics": {"per_world": "civilization_metrics", "federation": "world_macro_snapshot"},
    "aurelia-npc-population": {"per_world": "agents", "federation": None},
}

WORLDS: tuple[str, ...] = ("solara", "arkos", "mirithane", "valdris", "verge")


# ---------------------------------------------------------------------------
# Parquet backend
# ---------------------------------------------------------------------------

def discover_local_parquet_files(root: Path) -> dict[str, list[Path]]:
    """Walk a local HuggingFace export root and map dataset -> parquet paths.

    The export root is expected to look like::

        /tmp/hf-export/
            aurelia-causal-events/
                configs.json
                data/.../world/train.parquet
            aurelia-civilization-metrics/
                ...

    Returns an empty dict if the root does not exist. Only datasets that
    appear in :data:`DATASETS` are returned.
    """
    if not root.exists():
        return {}
    out: dict[str, list[Path]] = {}
    for ds in DATASETS:
        configs = root / ds / "configs.json"
        if not configs.exists():
            continue
        try:
            payload = json.loads(configs.read_text())
        except json.JSONDecodeError:
            continue
        files = payload.get("data", {}) or {}
        paths: list[Path] = []
        for run, run_files in files.items():
            for rel in run_files:
                p = (root / ds / rel).resolve()
                if p.exists():
                    paths.append(p)
        out[ds] = paths
    return out


def load_local_table(dataset: str, root: Path = DEFAULT_LOCAL_ROOT) -> pa.Table:
    """Load and concatenate every Parquet file for ``dataset`` under ``root``.

    Returns an empty table if the dataset has no files locally. Prefers
    Parquet; falls back to the most recent SQLite smoke run if no
    Parquet is available and ``root`` is the default location.
    """
    paths = discover_local_parquet_files(root).get(dataset, [])
    if paths:
        tables = [pq.read_table(p) for p in paths]
        return pa.concat_tables(tables, promote_options="default") if len(tables) > 1 else tables[0]
    # Fallback to SQLite smoke runs when called with the default root.
    if root == DEFAULT_LOCAL_ROOT:
        sqlite_dir = _latest_sqlite_run(DEFAULT_SQLITE_ROOT)
        if sqlite_dir is not None:
            return load_local_table_from_sqlite(dataset, sqlite_dir)
    return pa.table({})


# ---------------------------------------------------------------------------
# SQLite backend
# ---------------------------------------------------------------------------

def discover_local_sqlite_runs(root: Path = DEFAULT_SQLITE_ROOT) -> list[Path]:
    """Return all ``/tmp/aurelia-*`` run directories that look like Aurelia runs.

    A run directory qualifies if it contains at least one of the
    ``<world>.db`` files. Sorted newest-first by mtime.
    """
    if not root.exists():
        return []
    candidates = [p for p in root.iterdir() if p.is_dir() and p.name.startswith("aurelia-")]
    qualified = [
        p for p in candidates
        if any((p / f"{w}.db").exists() for w in WORLDS) or (p / "federation.db").exists()
    ]
    qualified.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return qualified


def _latest_sqlite_run(root: Path) -> Optional[Path]:
    runs = discover_local_sqlite_runs(root)
    return runs[0] if runs else None


def _sqlite_table_to_arrow(db_path: Path, table: str, world_filter: Optional[str] = None) -> pa.Table:
    """Read a SQLite table into a PyArrow table.

    If ``world_filter`` is set, a ``world_id`` column is added or replaced
    from the parent filename (since the per-world DBs do not carry a
    world column in their causal_events table).
    """
    if not db_path.exists():
        return pa.table({})
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(f"SELECT * FROM {table}")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    finally:
        conn.close()
    arrays: dict[str, list] = {c: [] for c in cols}
    for row in rows:
        for c, v in zip(cols, row):
            arrays[c].append(v)
    table_obj = pa.table(arrays) if cols else pa.table({})
    if world_filter and "world_id" not in cols:
        # Inject a world_id column so downstream code can partition by world.
        n = len(table_obj)
        table_obj = table_obj.append_column("world_id", pa.array([world_filter] * n))
    return table_obj


def load_local_table_from_sqlite(dataset: str, run_dir: Path) -> pa.Table:
    """Load ``dataset`` from a single Aurelia smoke-run directory.

    Reads the per-world tables for every world DB and the federation DB
    where appropriate, then concatenates. Returns an empty table if
    nothing matches.
    """
    mapping = SQLITE_TABLE_MAP.get(dataset, {})
    per_world_table = mapping.get("per_world")
    fed_table = mapping.get("federation")
    if not per_world_table and not fed_table:
        return pa.table({})

    pieces: list[pa.Table] = []

    if per_world_table:
        for world in WORLDS:
            db = run_dir / f"{world}.db"
            if db.exists():
                t = _sqlite_table_to_arrow(db, per_world_table, world_filter=world)
                if len(t) > 0:
                    pieces.append(t)

    if fed_table:
        fed_db = run_dir / "federation.db"
        if fed_db.exists():
            t = _sqlite_table_to_arrow(fed_db, fed_table, world_filter="federation")
            if len(t) > 0:
                pieces.append(t)

    if not pieces:
        return pa.table({})
    return pa.concat_tables(pieces, promote_options="default") if len(pieces) > 1 else pieces[0]


# ---------------------------------------------------------------------------
# HuggingFace backend (network, only if the caller asks)
# ---------------------------------------------------------------------------

def fetch_hf_parquet(
    dataset: str,
    run: str,
    world: str,
    *,
    org: str = HF_ORG,
    timeout: float = 30.0,
) -> pa.Table:
    """Fetch a single Parquet file from a HuggingFace dataset.

    Use this only for one-off inspection. Examples should prefer the
    local export, falling back to this if asked.
    """
    url = DEFAULT_HF_PARQUET_URL.format(org=org, ds=dataset, run=run, world=world)
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 — caller asked
        data = resp.read()
    import io
    return pq.read_table(io.BytesIO(data))


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------

def _table_summary(label: str, table: pa.Table, n_files: int) -> str:
    if len(table) == 0:
        return f"  {label}: (empty)\n"
    cols = ", ".join(table.column_names[:6])
    if len(table.column_names) > 6:
        cols += f", … (+{len(table.column_names) - 6})"
    return f"  {label}: {len(table)} rows across {n_files} source file(s)\n    columns: {cols}\n"


def print_summary(
    root: Path = DEFAULT_LOCAL_ROOT,
    *,
    sqlite_root: Path = DEFAULT_SQLITE_ROOT,
) -> None:
    """Print a per-dataset row count summary to stdout.

    Prefers Parquet export under ``root``. Falls back to the most recent
    smoke run under ``sqlite_root`` for any dataset not present in the
    Parquet export.
    """
    print(f"Aurelia dataset export summary — parquet root: {root}")
    if not root.exists():
        print("  (parquet export not found — falling back to latest SQLite smoke run)")

    sqlite_dir = _latest_sqlite_run(sqlite_root)
    parquet_files = discover_local_parquet_files(root)
    for ds in DATASETS:
        parquet_paths = parquet_files.get(ds, [])
        if parquet_paths:
            table = load_local_table(ds, root)
            print(_table_summary(ds, table, len(parquet_paths)).rstrip())
        elif sqlite_dir is not None:
            table = load_local_table_from_sqlite(ds, sqlite_dir)
            label = f"{ds} (sqlite: {sqlite_dir.name})"
            print(_table_summary(label, table, 1).rstrip())
        else:
            print(f"  {ds}: (no local source — run scripts/export_hf_dataset.py or causal_run.py)")


# ---------------------------------------------------------------------------
# Small CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Print summary of local Aurelia HF export")
    p.add_argument("--export-root", default=str(DEFAULT_LOCAL_ROOT))
    p.add_argument("--sqlite-root", default=str(DEFAULT_SQLITE_ROOT))
    args = p.parse_args(argv)
    print_summary(Path(args.export_root), sqlite_root=Path(args.sqlite_root))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
