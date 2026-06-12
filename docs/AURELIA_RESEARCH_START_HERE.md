# Aurelia — Research Start Here

> **Audience:** researchers who want to inspect Aurelia's data, reproduce
> a headline result, or trace a causal chain. Not the lore reader page —
> see [`AURELIA_LORE_READERS_START_HERE.md`](AURELIA_LORE_READERS_START_HERE.md)
> for that.

Aurelia is a causal civilization simulation published by **Ousia Research**
and operated by **Hermes Agent**. Five abstract worlds tick forward under
a federation clock; every event is recorded as a first-class `causal_event`
row. Four HuggingFace datasets expose the same artifacts as a queryable
research archive.

## Six commands, in order

```bash
# 1. Load and inspect all four datasets (rows, files, columns)
PYTHONPATH=. python3 examples/01_load_aurelia_hf_datasets.py

# 2. Reproduce the headline density-diversification result
PYTHONPATH=. python3 examples/02_reproduce_density_diversification.py

# 3. Trace a causal chain from the federation graph
PYTHONPATH=. python3 examples/03_trace_causal_chain.py

# 4. Run a counterfactual branch (paired-simulation comparison)
PYTHONPATH=src_template python3 examples/04_run_counterfactual_branch.py

# 5. Run the density-diversification grid (3 settings × 2 seeds)
PYTHONPATH=. python3 examples/05_run_density_diversification_grid.py --dry-run

# 6. Plan the Phase 13 post-run narrative chronicle batch
PYTHONPATH=src_template python3 src_template/batch_chronicles.py --output /tmp/aurelia-run/output --years 200 --dry-run
```

If `/tmp/hf-export` does not exist locally, the first example prints the
HuggingFace download instructions; the second falls back to the canonical
numbers from `docs/reports/phase11-runs-comparison.md`; the third exits
cleanly with the same download instructions. The fourth and fifth examples
self-run and need no prior artifact. Use `--dry-run` on example 05 to preview
the 6-run battery before spending simulation time. The sixth command is a
planning-only Phase 13 narrative pass; it does not load a model or require a
GPU. See [`AURELIA_PHASE13_NARRATIVE.md`](AURELIA_PHASE13_NARRATIVE.md) for the
full chronicle workflow.

## The four datasets

| HuggingFace repo | Content |
|---|---|
| `OusiaResearch/aurelia-causal-events` | per-world causal event stream |
| `OusiaResearch/aurelia-civilization-metrics` | yearly world state trajectories |
| `OusiaResearch/aurelia-federation-causal` | federation events + causal edges |
| `OusiaResearch/aurelia-npc-population` | NPC snapshots at end of run |

All four are CC-BY-4.0 (synthetic data).

## Local mode vs HuggingFace mode

The helper at `examples/aurelia_dataset_loader.py` is the single source
of truth for paths. It works in two modes:

- **Local mode** (default): reads `/tmp/hf-export/<dataset>/data/.../*.parquet`
  if the export exists. Use this for offline reproducibility and CI.
- **HuggingFace mode**: pass a Parquet URL to `fetch_hf_parquet()` or
  load via the `datasets` library as the README snippets show.

Examples do not call `fetch_hf_parquet()` automatically; researchers
opt into network access manually.

## What the examples prove

| Example | What it proves |
|---|---|
| `01_load_aurelia_hf_datasets.py` | The four datasets exist, are partitioned by run and world, and have stable column schemas. |
| `02_reproduce_density_diversification.py` | The published Phase 11 headline: turning on `density_diversification` reduces cross-world population CV from 0.807 to 0.015, a 98.1% reduction. |
| `03_trace_causal_chain.py` | Federation causal edges are real, queryable, and have a useful starting structure (cultural diffusion fed by cross-world movement). |
| `04_run_counterfactual_branch.py` | Same-seed paired runs with one knob changed produce a measurable divergence; see [`AURELIA_COUNTERFACTUALS.md`](AURELIA_COUNTERFACTUALS.md) for the full pattern. |
| `05_run_density_diversification_grid.py` | A copy-paste 3×2 simulation battery: no / mid / full diversification across two seeds, with JSON + Markdown reports. |
| `src_template/batch_chronicles.py --dry-run` | Phase 13 narrative planning: counts post-run yearly chronicles and computes local GPU worker fit without loading a model. |

## Known limitations

- **Abstract simulation, not forecast.** Aurelia's worlds are invented
  topologies — no real Earth, no real countries. Numbers are illustrative
  of causal mechanics, not predictions about any real society.
- **Micro-society scale.** The exported runs (Phase 11) cap populations
  in the hundreds per world. Larger-scale claims require longer or
  larger production runs that have not yet cleared Phase 12 quality gates.
- **Cloudflare D1 cap.** The public Observatory is the live observability
  plane but is not currently the complete archive for long runs. Local
  Parquet exports and HuggingFace are the source of truth until the
  D1 cap is upgraded.
- **Lore/wiki canon is being reconciled.** Some older wiki claims
  (e.g., 60,000 NPCs, single-landmass topology) are stale. See
  [`AURELIA_COHERENCE_AUDIT.md`](AURELIA_COHERENCE_AUDIT.md) for the
  full list of resolutions.

## Where to go next

- **Counterfactuals** — same-seed paired runs and post-run ledger interventions: [`AURELIA_COUNTERFACTUALS.md`](AURELIA_COUNTERFACTUALS.md).
- **Canon bridge** — which concept is in which code, table, dataset,
  and proof artifact: [`AURELIA_CANON_AND_DATA_GUIDE.md`](AURELIA_CANON_AND_DATA_GUIDE.md).
- **Architecture** — runtime + data-plane overview: [`ARCHITECTURE.md`](ARCHITECTURE.md).
- **Phase 11 reports** — the run quality and density comparison reports:
  `docs/reports/phase11-runs-comparison.md`.
- **Hermes Agent** — the operator: [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).
- **Public dashboard** — `https://hermes-state-worker.plntrprotocol.workers.dev/public/aurelia/dashboard`.

If you want to read the world rather than the data, the
[lore reader start page](AURELIA_LORE_READERS_START_HERE.md) is the
right on-ramp.
