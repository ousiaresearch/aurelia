#!/usr/bin/env python3
"""
render_hf_readme.py — Render a HuggingFace dataset card (README.md) for one of
the four Aurelia HF datasets.

Usage:
    PYTHONPATH=. python3 scripts/render_hf_readme.py \\
        --dataset causal_events \\
        --export-root /tmp/hf-export \\
        --out /tmp/hf-export/aurelia-causal-events/README.md

The README includes YAML frontmatter required by HF (license, task_categories,
size_categories, tags, language) plus a Schema section, a Loading example, and
per-run row counts discovered from the exported files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DATASET_HYPHEN = {
    "causal_events": "aurelia-causal-events",
    "civilization_metrics": "aurelia-civilization-metrics",
    "federation_causal": "aurelia-federation-causal",
    "npc_population": "aurelia-npc-population",
}

DATASET_TITLE = {
    "causal_events": "Aurelia — Causal Event Stream",
    "civilization_metrics": "Aurelia — Civilization Metrics Trajectories",
    "federation_causal": "Aurelia — Federation Causal Graph (Events + Edges)",
    "npc_population": "Aurelia — NPC Population Snapshot",
}

# size_categories values from HF's official taxonomy
SIZE_CATEGORIES_BUCKETS = [
    (1_000, "n<1K"),
    (5_000, "1K<n<5K"),
    (10_000, "5K<n<10K"),
    (100_000, "10K<n<100K"),
    (1_000_000, "100K<n<1M"),
]


def size_category(n: int) -> str:
    for cap, label in SIZE_CATEGORIES_BUCKETS:
        if n < cap:
            return label
    return "n>1M"


SCHEMAS: dict[str, dict[str, Any]] = {
    "causal_events": {
        "primary_file": "data/<run_id>/train.parquet",
        "row_count_unit": "causal events",
        "task_categories": ["other"],
        "description": (
            "Per-tick causal events emitted by Aurelia world daemons. Each row is "
            "one event from one world, with a (micro|meso|macro|federation) layer, "
            "an event_type label, magnitude/valence/confidence scores, and a JSON "
            "payload for type-specific deltas. The causal graph is reconstructed "
            "from the separate federation_causal dataset."
        ),
        "related_examples": ["01_load_aurelia_hf_datasets", "03_trace_causal_chain"],
        "schema": [
            ("run_id", "string", "Run label (e.g. phase11-100y)"),
            ("event_id", "string", "Globally unique event id (primary key)"),
            ("tick_number", "int64", "Simulation tick; 6 ticks = 1 year by default"),
            ("world_id", "string", "World this event belongs to (arkos, mirithane, solara, valdris, verge)"),
            ("layer", "string", "Causal layer: micro|meso|macro|federation"),
            ("event_type", "string", "Event-type label (e.g. wage_dispute, sovereignty_charter)"),
            ("actor_ids", "list<string>", "NPC or world ids that triggered the event"),
            ("target_ids", "list<string>", "NPC or world ids affected"),
            ("scope", "string", "Scope of the event (npc, region, world)"),
            ("magnitude", "float32", "Raw magnitude of the event"),
            ("valence", "float32", "Signed valence in [-1, 1]"),
            ("confidence", "float32", "Engine confidence in [0, 1]"),
            ("payload", "object", "Type-specific extra fields as JSON"),
            ("created_at", "float64", "Unix timestamp of the simulation tick"),
        ],
        "tags": [
            "synthetic", "multi-agent", "simulation", "causal-inference",
            "civilization", "agent-based-modeling", "civilization-data",
            "causal-graphs", "world-model", "tabular",
        ],
    },
    "civilization_metrics": {
        "primary_file": "data/<run_id>/train.parquet",
        "row_count_unit": "metric snapshots",
        "task_categories": ["other"],
        "description": (
            "Yearly per-world civilization state trajectories. Each row captures "
            "the macro indicators (education, urbanization, youth bulge, disease "
            "pressure, resource stock, property rights) and the categorical state "
            "(state capacity type, repression type, conflict type) at one tick of "
            "one world. A natural input for time-series forecasting, regime "
            "classification, and path-dependence analyses."
        ),
        "related_examples": ["01_load_aurelia_hf_datasets", "02_reproduce_density_diversification"],
        "schema": [
            ("run_id", "string", "Run label (e.g. phase11-100y)"),
            ("world_id", "string", "World id (arkos, mirithane, solara, valdris, verge)"),
            ("tick_number", "int64", "Simulation tick"),
            ("education_level", "float32", "Composite education indicator"),
            ("urbanization", "float32", "Urban share of population"),
            ("youth_bulge", "float32", "Demographic youth bulge indicator"),
            ("disease_pressure", "float32", "Disease ecology pressure"),
            ("resource_stock", "float32", "Aggregate resource stock"),
            ("property_rights", "float32", "Property-rights index"),
            ("state_capacity_type", "string", "State capacity categorical (bureaucratic, patrimonial, etc.)"),
            ("repression_type", "string", "Repression categorical (legal, propaganda, ...)"),
            ("conflict_type", "string", "Conflict categorical (latent, organized, ...)"),
            ("path_lock_in", "float32", "Path-dependence lock-in score"),
            ("payload", "object", "Per-tick extra fields (deltas)"),
            ("created_at", "float64", "Unix timestamp"),
        ],
        "tags": [
            "synthetic", "multi-agent", "simulation", "civilization",
            "time-series", "state-trajectories", "macro-indicators",
            "regime-classification", "path-dependence", "tabular",
        ],
    },
    "federation_causal": {
        "primary_file": "data/<run_id>/events.parquet + data/<run_id>/edges.parquet",
        "row_count_unit": "federation events + edges",
        "task_categories": ["other"],
        "description": (
            "Cross-world and federation-level causal events (events.parquet) plus "
            "the causal edges (edges.parquet) that connect them. The federation "
            "graph captures trade shocks, migrations, cultural diffusion, and "
            "diplomatic relations across the five Aurelian worlds. Edges are "
            "filtered to the federation events in this run."
        ),
        "related_examples": ["01_load_aurelia_hf_datasets", "03_trace_causal_chain"],
        "schema": [
            ("events.event_id", "string", "Federation event id (primary key)"),
            ("events.tick_number", "int64", "Simulation tick"),
            ("events.world_id", "string", "Always 'federation' for these events"),
            ("events.layer", "string", "Always 'federation' for these events"),
            ("events.event_type", "string", "Type: cross_world_movement, cultural_diffusion, diplomatic_*, etc."),
            ("events.actor_ids", "list<string>", "World ids that triggered"),
            ("events.target_ids", "list<string>", "World ids affected"),
            ("events.magnitude", "float32", "Magnitude"),
            ("events.valence", "float32", "Signed valence"),
            ("events.payload", "object", "Type-specific extra fields (source_world, target_world, etc.)"),
            ("edges.parent_event_id", "string", "FK to events.event_id"),
            ("edges.child_event_id", "string", "FK to events.event_id"),
            ("edges.relation", "string", "Edge type (e.g. migration_to_cultural_change)"),
            ("edges.weight", "float32", "Edge weight in [0, 1]"),
        ],
        "tags": [
            "synthetic", "multi-agent", "simulation", "causal-graphs",
            "federation", "cross-world", "migration", "diplomacy",
            "cultural-diffusion", "graph", "tabular",
        ],
    },
    "npc_population": {
        "primary_file": "data/<run_id>/<world>/train.parquet",
        "row_count_unit": "NPC snapshot rows",
        "task_categories": ["other"],
        "description": (
            "One row per NPC at the end of a simulation run, with a count of the "
            "NPC's own `events` log entries. The properties JSON captures "
            "birth, migration, household, and demographic metadata. Useful for "
            "agent-level demography, mortality, and migration studies."
        ),
        "related_examples": ["01_load_aurelia_hf_datasets", "02_reproduce_density_diversification"],
        "schema": [
            ("run_id", "string", "Run label (e.g. phase11-100y)"),
            ("npc_id", "string", "Globally unique NPC id (primary key)"),
            ("name", "string", "NPC display name"),
            ("npc_type", "string", "Always 'npc' for this dataset"),
            ("location_id", "string", "Location at end of run (or null if emigrated)"),
            ("final_state", "string", "State at end of run: active, dead, emigrated"),
            ("properties", "object", "JSON: born_tick, migrated_tick, household_id, origin_world, target_world, etc."),
            ("travel_state", "string", "In-transit state, or null"),
            ("created_at", "float64", "Unix timestamp of NPC birth"),
            ("updated_at", "float64", "Unix timestamp of last update"),
            ("event_count", "int64", "Count of `events` rows for this NPC"),
        ],
        "tags": [
            "synthetic", "multi-agent", "simulation", "demography",
            "agents", "migration", "household", "npc-trajectories",
            "agent-based-modeling", "tabular",
        ],
    },
}


def count_rows_for_run(data_dir: Path, run_id: str) -> dict[str, int]:
    """Inspect exported files for a single run and return per-file row counts.
    Supports both Parquet (via pyarrow) and JSONL (line count)."""
    run_dir = data_dir / run_id
    if not run_dir.exists():
        return {}
    counts: dict[str, int] = {}
    # Parquet
    try:
        import pyarrow.parquet as pq
        for p in sorted(run_dir.rglob("*.parquet")):
            tbl = pq.read_table(str(p))
            counts[str(p.relative_to(data_dir))] = tbl.num_rows
    except Exception:
        pass
    # JSONL
    for p in sorted(run_dir.rglob("*.jsonl")):
        try:
            n = sum(1 for _ in open(str(p)))
            counts[str(p.relative_to(data_dir))] = n
        except Exception:
            pass
    return counts


def list_runs(data_dir: Path) -> list[str]:
    if not data_dir.exists():
        return []
    return sorted(p.name for p in data_dir.iterdir() if p.is_dir())


def render(dataset: str, export_root: Path, run_label: str = "") -> str:
    slug = DATASET_HYPHEN[dataset]
    title = DATASET_TITLE[dataset]
    info = SCHEMAS[dataset]
    data_dir = export_root / slug / "data"
    runs = list_runs(data_dir)

    # Aggregate row counts
    per_run_counts: dict[str, dict[str, int]] = {}
    grand_total = 0
    for r in runs:
        c = count_rows_for_run(data_dir, r)
        per_run_counts[r] = c
        grand_total += sum(c.values())

    sz = size_category(grand_total)
    tasks_yaml = "\n".join(f"  - {t}" for t in info["task_categories"])
    tags_yaml = "\n".join(f"  - {t}" for t in info["tags"])

    # Run table
    run_rows = []
    for r in runs:
        c = per_run_counts[r]
        if not c:
            continue
        n = sum(c.values())
        run_rows.append(f"| `{r}` | {n:,} | {', '.join(f'{k}={v:,}' for k,v in c.items())} |")
    run_table = "\n".join(run_rows) if run_rows else "_(no runs exported)_"

    # Related examples (F1)
    related = info.get("related_examples", [])
    related_block = ""
    if related:
        lines = ["## Reproducible research examples", ""]
        lines.append("Three runnable scripts in the [Aurelia repository](https://github.com/ousiaresearch/aurelia) "
                     "let you inspect this dataset end-to-end. Start with [AURELIA_RESEARCH_START_HERE.md]("
                     "https://github.com/ousiaresearch/aurelia/blob/main/docs/AURELIA_RESEARCH_START_HERE.md).")
        lines.append("")
        for ex in related:
            lines.append(f"- `examples/{ex}.py`")
        related_block = "\n".join(lines) + "\n"

    # Canon bridge (F1)
    canon_block = (
        "## Concept bridge\n\n"
        "Every concept in this dataset is mapped across wiki, code, table, and "
        "proof artifact in [AURELIA_CANON_AND_DATA_GUIDE.md](https://github.com/ousiaresearch/aurelia/blob/main/docs/AURELIA_CANON_AND_DATA_GUIDE.md). "
        "If you want to know which simulator module produced a row, or which "
        "proof artifact exercises it, the canon bridge is the index.\n"
    )

    # Schema table
    schema_rows = ["| column | type | description |", "|---|---|---|"]
    for col, typ, desc in info["schema"]:
        schema_rows.append(f"| `{col}` | {typ} | {desc} |")
    schema_table = "\n".join(schema_rows)

    # Example load snippet (parquet)
    if dataset == "npc_population":
        load_snippet = (
            "from datasets import load_dataset\n"
            "ds = load_dataset(\n"
            "    'parquet',\n"
            "    data_files={\n"
            "        'phase11-100y_solara': 'aurelia-npc-population/data/phase11-100y/solara/train.parquet',\n"
            "    },\n"
            ")\n"
            "print(ds['phase11-100y_solara'][0])\n"
        )
    elif dataset == "federation_causal":
        load_snippet = (
            "from datasets import load_dataset\n"
            "events = load_dataset(\n"
            "    'parquet',\n"
            "    data_files='aurelia-federation-causal/data/phase11-100y/events.parquet',\n"
            ")['train']\n"
            "edges = load_dataset(\n"
            "    'parquet',\n"
            "    data_files='aurelia-federation-causal/data/phase11-100y/edges.parquet',\n"
            ")['train']\n"
            "print(events[0])\n"
            "print(edges[0])\n"
        )
    else:
        load_snippet = (
            "from datasets import load_dataset\n"
            "ds = load_dataset(\n"
            "    'parquet',\n"
            "    data_files='aurelia-" + dataset.replace('_', '-') + "/data/phase11-100y/train.parquet',\n"
            ")['train']\n"
            "print(ds[0])\n"
        )

    readme = f"""---
license: cc-by-4.0
language:
  - en
task_categories:
{tasks_yaml}
tags:
{tags_yaml}
size_categories:
  - {sz}
pretty_name: {title}
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/*/train.parquet
---

# {title}

{info["description"]}

## Provenance

This dataset was generated by [Aurelia](https://github.com/ousiaresearch/aurelia),
a multi-agent civilization simulation operated by [Ousia Research](https://github.com/ousiaresearch).
The data in this repository is fully synthetic — no real humans, places, or events
are referenced. The simulation engine, schema, and reproducible configurations are
all open-sourced; see the GitHub repository for replay instructions.

The five Aurelian worlds (`arkos`, `mirithane`, `solara`, `valdris`, `verge`) interact
through a federation layer that schedules cross-world effects (trade shocks, migrations,
cultural diffusion, diplomatic relations). Each world runs an independent agent-based
simulation of NPCs with goals, factions, institutions, and macro-level state transitions.

## Schema

Primary file: `{info["primary_file"]}`

{schema_table}

## Runs included

| run_id | total rows | breakdown |
|---|---|---|
{run_table}

Total rows across runs: **{grand_total:,}** ({sz} bucket).

To load a specific run, point `data_files` at the run's directory.

## Loading

```python
{load_snippet}```

{related_block}{canon_block}
## Run provenance map

Each `run_id` corresponds to a deterministic Aurelia simulation with a specific
configuration. See the [Aurelia Phase 11 comparison report](https://github.com/ousiaresearch/aurelia/blob/main/docs/reports/phase11-runs-comparison.md)
for the demographics and population coefficient-of-variation across these runs.

| run_id | config | years | density_diversification |
|---|---|---|---|
| `phase11-bolster-scan-y5` | baseline (5y) | 5 | 0.0 |
| `phase11-100y` | baseline (100y) | 100 | 0.0 |
| `phase11-200y` | baseline (200y) | 200 | 0.0 |
| `phase11-density-100y` | density-diversification (100y) | 100 | 0.7 |
| `phase11-cf-solara-aid` | counterfactual: solara federation aid early | 5 | 0.0 (counterfactual intervention) |

## Licensing

Released under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). You may
use, share, and adapt the data for any purpose, including commercial, with
attribution. Attribution: "Aurelia Simulation Dataset, Ousia Research, 2026."

If you use this dataset in a publication, please cite the companion technical
report and link back to the [Aurelia repository](https://github.com/ousiaresearch/aurelia).

## Limitations

- The simulation models abstract civilization dynamics; it is **not** a forecast
  of any real-world society.
- All names, world ids, and event labels are fictional.
- The number of NPCs is small (≤ 200 active per world) by design — this is a
  micro-society scale, not a planet-scale demographic model.
- Results are sensitive to RNG seed and engine version; pin both when reporting.
"""
    return readme


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True, choices=list(SCHEMAS.keys()))
    ap.add_argument("--export-root", required=True, help="parent dir containing the four dataset dirs")
    ap.add_argument("--out", help="output path; default = <export-root>/<slug>/README.md")
    args = ap.parse_args()

    slug = DATASET_HYPHEN[args.dataset]
    out = Path(args.out) if args.out else Path(args.export_root) / slug / "README.md"
    text = render(args.dataset, Path(args.export_root))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"[ok] wrote {out} ({len(text):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
