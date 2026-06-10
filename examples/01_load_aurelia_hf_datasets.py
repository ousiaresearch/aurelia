"""01 — Load all four Aurelia datasets and print row counts and columns.

This is the *first* thing a researcher should run. It is intentionally
short and noisy: if the local export is missing, the script tells you
exactly how to fetch it from HuggingFace rather than failing silently.

Usage:
    PYTHONPATH=. python3 examples/01_load_aurelia_hf_datasets.py
    PYTHONPATH=. python3 examples/01_load_aurelia_hf_datasets.py --export-root /tmp/hf-export
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Import the loader helper. The examples are run directly with python3,
# so we add the repo root to sys.path to make this work in any cwd.
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from examples import aurelia_dataset_loader as loader  # noqa: E402
import pyarrow as pa  # noqa: E402


HF_FALLBACK = """\
Local export not found at {root}.

To fetch the public datasets from HuggingFace, run:
    pip install -U datasets
    python3 -c 'from datasets import load_dataset; \\
        load_dataset("OusiaResearch/aurelia-causal-events"); \\
        load_dataset("OusiaResearch/aurelia-civilization-metrics"); \\
        load_dataset("OusiaResearch/aurelia-federation-causal"); \\
        load_dataset("OusiaResearch/aurelia-npc-population")'

Or pass --export-root to point at an existing local mirror."""


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    sep = "  ".join("-" * w for w in widths)
    body = "\n".join("  ".join(c.ljust(w) for c, w in zip(row, widths)) for row in rows)
    return f"{line}\n{sep}\n{body}"


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Load and summarise the four Aurelia HF datasets")
    p.add_argument(
        "--export-root",
        default=str(loader.DEFAULT_LOCAL_ROOT),
        help="Local export root (default: /tmp/hf-export)",
    )
    p.add_argument(
        "--sqlite-root",
        default=str(loader.DEFAULT_SQLITE_ROOT),
        help="Local SQLite smoke-run root (default: /tmp)",
    )
    p.add_argument(
        "--max-columns",
        type=int,
        default=8,
        help="Maximum columns to print per dataset",
    )
    args = p.parse_args(argv)

    root = Path(args.export_root)
    sqlite_root = Path(args.sqlite_root)
    if not root.exists():
        print(HF_FALLBACK.format(root=root))
        return 0

    sqlite_dir = loader._latest_sqlite_run(sqlite_root)
    parquet_paths = loader.discover_local_parquet_files(root)
    rows: list[list[str]] = []
    for ds in loader.DATASETS:
        ds_parquet = parquet_paths.get(ds, [])
        try:
            if ds_parquet:
                table = loader.load_local_table(ds, root)
                src = "parquet"
            elif sqlite_dir is not None:
                table = loader.load_local_table_from_sqlite(ds, sqlite_dir)
                src = f"sqlite:{sqlite_dir.name}"
            else:
                table = pa.table({})
                src = "missing"
        except Exception as exc:  # pragma: no cover — defensive
            rows.append([ds, "ERROR", "-", str(exc)[:40]])
            continue
        cols = ", ".join(table.column_names[: args.max_columns])
        if len(table.column_names) > args.max_columns:
            cols += f"… (+{len(table.column_names) - args.max_columns})"
        rows.append([ds, str(len(table)), src, cols])

    print("Aurelia datasets — local export summary")
    print(f"  export root: {root}")
    if sqlite_dir is not None:
        print(f"  sqlite fallback: {sqlite_dir}")
    print()
    print(_render_table(["dataset", "rows", "source", "columns"], rows))
    print("\nDatasets are published under https://huggingface.co/OusiaResearch/")
    print("See docs/AURELIA_RESEARCH_START_HERE.md for next steps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
