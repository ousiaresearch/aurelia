"""Aurelia dataset loader helper.

This module is intentionally tiny and import-safe. It exposes the four
HuggingFace dataset names published by the Aurelia pipeline, plus a
small set of pure-Python helpers that read the local Parquet export
produced by ``scripts/export_hf_dataset.py``.

The helper supports two backends:

- **Parquet** — ``discover_local_parquet_files`` reads ``configs.json``
  at the export root and returns a ``{dataset: [Path, ...]}`` map.
- **SQLite** — left for example scripts that prefer the raw run
  artifacts under ``/tmp/aurelia-*`` (no helper needed).

Everything is offline by default. The HF parquet URL is only used when
the caller explicitly opts in via :func:`fetch_hf_parquet`.
"""

from __future__ import annotations

import json
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
DEFAULT_HF_PARQUET_URL = "https://huggingface.co/datasets/{org}/{ds}/resolve/main/data/{run}/{world}/train.parquet"


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

    Returns an empty table if the dataset has no files locally.
    """
    paths = discover_local_parquet_files(root).get(dataset, [])
    if not paths:
        return pa.table({})
    tables = [pq.read_table(p) for p in paths]
    return pa.concat_tables(tables, promote_options="default") if len(tables) > 1 else tables[0]


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

def print_summary(root: Path = DEFAULT_LOCAL_ROOT) -> None:
    """Print a per-dataset row count summary to stdout."""
    print(f"Aurelia dataset export summary — root: {root}")
    if not root.exists():
        print("  (export root not found — run scripts/export_hf_dataset.py first)")
        return
    for ds in DATASETS:
        try:
            table = load_local_table(ds, root)
        except Exception as exc:  # pragma: no cover — defensive
            print(f"  {ds}: ERROR {exc}")
            continue
        n_files = len(discover_local_parquet_files(root).get(ds, []))
        n_rows = len(table)
        cols = ", ".join(table.column_names[:6])
        if len(table.column_names) > 6:
            cols += f", … (+{len(table.column_names) - 6})"
        print(f"  {ds}: {n_rows} rows across {n_files} parquet files")
        print(f"    columns: {cols}")


# ---------------------------------------------------------------------------
# Small CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Print summary of local Aurelia HF export")
    p.add_argument("--export-root", default=str(DEFAULT_LOCAL_ROOT))
    args = p.parse_args(argv)
    print_summary(Path(args.export_root))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
