# Aurelia Phase 12 — Gap Closure Report

> **Status:** Phase 12 closed. All eight workstreams (A through H) delivered.
> Aurelia now presents as a single inspectable system rather than three
> separate artifacts (wiki, simulation, public surface).

## What was lacking

Before Phase 12, the project had real material but no coherent bridge
between its three layers:

- The Desktop wiki still claimed 60,000 NPCs, a local-only dashboard,
  an "Arien-built" origin, a single-landmass topology, and TTRPG-adjacent
  assets. None of these matched the public repo.
- The HF datasets were live, but a researcher had to infer how to join
  them, what the columns meant, and which notebook proved which claim.
- The simulation evaluator returned perfect `1.0` scores even when
  long runs had warning signs: zero factions in most worlds, Valdris
  collapsing to one NPC, partial Cloudflare ingestion, and `seed: 0` /
  `ticks_per_year: 0` in the manifest.
- Counterfactual branches could publish as "meaningful" even when they
  were byte-identical to the baseline.

The plan turned this into a system where every major concept has a
traceable bridge from lore → code → DB → dataset → report.

## What was added

| Workstream | Deliverable |
|---|---|
| **A. Canon bridge** | `docs/data/aurelia_concepts.yaml` (32 concepts), `scripts/render_canon_data_guide.py`, generated `docs/AURELIA_CANON_AND_DATA_GUIDE.md` |
| **B. Wiki reconciliation** | `docs/AURELIA_WIKI_RECONCILIATION_REVIEW.md`, three Desktop wiki patches (front door, simulation status, TTRPG-adjacent), plus the migration of the wiki itself to `docs/wiki/` |
| **C. Dataset research UX** | `examples/aurelia_dataset_loader.py` (Parquet + SQLite backends), `examples/01_load_aurelia_hf_datasets.py`, `examples/02_reproduce_density_diversification.py` (99.1% reduction reproduced), `examples/03_trace_causal_chain.py`, dual-track start-here pages |
| **D. Simulation quality gates** | `scripts/evaluate_run_quality.py` hardened with faction/population/CV/metadata gates; `tests/test_run_manifest.py`; `federation_orchestrator.py` now populates the run manifest (seed, ticks_per_year, density_diversification, engine_version, git_commit, run_id, created_at); `scripts/compare_runs.py` adds divergence scoring |
| **E. Public surface reconciliation** | `scripts/reconcile_public_surfaces.py` with offline-counts + Cloudflare fetcher + Markdown report; ARCHITECTURE, README, DEMO updated to call out the D1 cap |
| **F. HF card integration** | `scripts/render_hf_readme.py` now links each dataset to the research guide + relevant example; `docs/HUGGINGFACE_PUBLISH.md` documents the on-ramp; README has a "Start with the research examples" section |
| **G. Research figure** | `scripts/plot_density_diversification.py` + `docs/reports/figures/density-diversification.svg` (stdlib SVG, no plotting deps) |
| **H. Closure report** | This document + CHANGELOG bump |

## Wiki / canon resolution

The Desktop wiki was the canonical lore source for years. Phase 12
preserved every file and migrated the entire wiki to the public repo
under `docs/wiki/` (139 markdown files, 90 image files, 51 MB of
visual assets, no `.DS_Store` or stray OS files). The Desktop copy
remains available for operator-side experiments, but `docs/wiki/`
is now the canonical public surface.

Stale wiki claims were addressed in three Desktop-wiki patches
(public front door, simulation status layer, TTRPG-adjacent archive)
and the canon bridge YAML was rewritten so all 46 wiki-path references
point to `docs/wiki/X` rather than `~/Desktop/Aurelia/X`.

The Desktop reconciliation review at
`docs/AURELIA_WIKI_RECONCILIATION_REVIEW.md` and the coherence audit at
`docs/AURELIA_COHERENCE_AUDIT.md` document the resolution and the
remaining "do not touch" lore boundaries.

## Dataset UX resolution

A new researcher can now go from zero to a first result in three
commands:

```bash
PYTHONPATH=. python3 examples/01_load_aurelia_hf_datasets.py
PYTHONPATH=. python3 examples/02_reproduce_density_diversification.py
PYTHONPATH=. python3 examples/03_trace_causal_chain.py
```

The loader helper at `examples/aurelia_dataset_loader.py` supports both
the published Parquet export and a zero-setup SQLite smoke-run fallback
at `/tmp/aurelia-*`. Researchers with a fresh clone can run a smoke
run (`causal_run.py --clean --years 1`) and immediately load the
data without first running a Phase 11 export.

The headline **99.1% cross-world population-CV reduction** is now
reproducible in two ways:

- From local Parquet via `final_state == "active"` filtering (the
  exact metric the Phase 11 report used).
- From the published canonical numbers in
  `docs/reports/phase11-runs-comparison.md` when no local data is
  available.

The 99.1% reproduces exactly:
`{171, 58, 63, 29, 49}` vs `{67, 67, 67, 67, 66}` → CV `0.6739` vs
`0.0060` → `99.1%` reduction.

## Simulation gate resolution

The evaluator at `scripts/evaluate_run_quality.py` no longer returns
`1.0` for pathological runs. Phase 12 added:

- **Faction gate:** if fewer than 50% of worlds have active factions,
  warn and hard-cap overall_score at `0.85`.
- **Population collapse gate:** if any world drops to 1 or fewer NPCs
  in a 50+ year run, warn and hard-cap at `0.80`.
- **Population CV gate:** if cross-world population CV exceeds 1.0,
  warn and hard-cap at `0.85`.
- **Metadata gate:** missing or zeroed seed / ticks_per_year /
  engine_version / git_commit / causal_summary.json is flagged as
  a warning (not a hard cap, but it surfaces in `metadata.*`).

These gates are exposed as module-level constants
(`FRACTION_CRITICAL`, `FRACTION_CRITICAL_CAP`, `POP_COLLAPSE_CAP`,
`POP_CV_HIGH`, `POP_CV_HIGH_CAP`, `LONG_RUN_YEARS`) so an operator can
tune them without editing the scoring logic.

Re-scoring the existing runs:

| Run | Score | Warnings |
|---|---|---|
| `phase11-100y` (baseline) | 0.85 | factions absent; missing manifest (old run) |
| `phase11-200y` (baseline) | 0.80 | factions absent; valdris collapse; high CV; missing manifest |
| `phase11-density-100y` | 0.85 | factions absent; missing manifest (old run) |
| Fresh `aurelia-d2-smoke` | 0.85 | factions absent (single-year smoke); manifest present (seed=4242, tpy=4, engine_version=aurelia-phase12) |

The run manifest now propagates end-to-end: `federation_orchestrator.run_causal_simulation()`
populates `seed`, `ticks_per_year`, `density_diversification`, `engine_version`,
`git_commit`, `run_id`, and `created_at`. The `aurelia_cf_pusher.py`
already reads those fields and propagates them to the Cloudflare
manifest.

Counterfactual divergence scoring in `scripts/compare_runs.py` now
emits a `divergence_score` (sum of event-count + metric + event-type
churn deltas), flags zero-divergence as a no-op warning, and reports
the top 10 changed event types. A counterfactual branch that does
nothing observable to the world is now explicitly flagged.

## Public surface reconciliation

`scripts/reconcile_public_surfaces.py` produces a Markdown report
that diffs:

- Local run artifacts (SQLite `*.db` under any `--run-dir`)
- HF export (Parquet files + `configs.json` under `--hf-root`)
- Cloudflare dashboard (JSON via `--cloudflare-dashboard`, only fetched
  with `--fetch-cloudflare`)

The current state is committed at
`docs/reports/public-surface-reconciliation.md`. All four HF datasets
report `ok`; local runs are fully populated; Cloudflare is not
queried in offline mode.

The D1 cap reality is now documented in three places:
`docs/ARCHITECTURE.md`, `README.md`, and `docs/DEMO.md`. Cloudflare
is the public observability plane, not the complete archive for
long runs. HF/local Parquet are the source of truth.

## Remaining hard blockers

None of these block Phase 12; they are forward-looking for Phase 13+.

- **Faction formation in long runs.** All five long runs (100y, 200y,
  density) report zero active factions. This is the single most
  important pathology. The faction-gate already surfaces it; a fix
  to the `factions` table seeding or a higher `faction_members`
  write rate is the most valuable next step.
- **D1 upgrade.** Until the Worker is moved to a paid plan or
  long-run tables are split, the public Cloudflare dashboard
  remains partial for the longest runs.
- **Micro-society scale.** Phase 11 exports cap populations in the
  hundreds per world. Larger-scale claims require longer or
  larger production runs that have not yet cleared Phase 12 gates.

## Recommended next run matrix

These are the gates-and-conditions for the next production runs, in
the order the plan recommends:

1. **20-seed sweep × 25 years** for calibration. The seed sweep
   should fix all knobs and only vary the seed. Each run is a smoke
   run that the quality gate should pass cleanly.
2. **5-seed sweep × 100 years** after the gates stop warning on
   faction/depopulation pathologies. This is the headline range
   for the density-diversification comparison.
3. **1 or 2 200-year production histories** only after the 100y
   sweep is clean. The current 200y run fails the population-collapse
   gate hard cap; this is expected and is a calibration signal, not
   a regression.
4. **Counterfactual branches only when the divergence gate reports
   meaningful deltas.** Do not publish a counterfactual that the
   gate flags as a no-op; the publication would be misleading.

## How to read the Phase 12 surface

| Path | What it is |
|---|---|
| `docs/AURELIA_RESEARCH_START_HERE.md` | HF/ML researcher on-ramp. |
| `docs/AURELIA_LORE_READERS_START_HERE.md` | World wiki on-ramp. |
| `docs/AURELIA_CANON_AND_DATA_GUIDE.md` | Concept index across wiki, code, table, dataset, artifact. |
| `docs/AURELIA_COHERENCE_AUDIT.md` | Stale wiki claims and their resolution. |
| `docs/AURELIA_WIKI_RECONCILIATION_REVIEW.md` | Pre-migration reconciliation matrix. |
| `docs/wiki/` | The world wiki, now in the public repo. |
| `examples/` | Three runnable research examples + the loader helper. |
| `scripts/evaluate_run_quality.py` | Phase 12 quality gates. |
| `scripts/reconcile_public_surfaces.py` | Public surface reconciler. |
| `scripts/plot_density_diversification.py` | Density research figure generator. |
| `docs/reports/figures/density-diversification.svg` | Static SVG research artifact. |
| `docs/reports/public-surface-reconciliation.md` | Latest reconciliation report. |
| `docs/reports/phase11-*quality.json` | Re-scored quality reports. |

## Acceptance criteria — final check

- [x] `PYTHONPATH=. pytest tests/ -q` passes (138 tests).
- [x] `docs/AURELIA_CANON_AND_DATA_GUIDE.md` maps ≥ 25 concepts across wiki, code, DB, HF, Cloudflare, reports (32 concepts).
- [x] `docs/AURELIA_COHERENCE_AUDIT.md` marks stale wiki/public claims and their resolution.
- [x] `examples/01_load_aurelia_hf_datasets.py` loads all four datasets or their local staged equivalent.
- [x] `examples/02_reproduce_density_diversification.py` reproduces the 99.1% CV reduction exactly.
- [x] `examples/03_trace_causal_chain.py` traces at least one event chain from causal events/edges.
- [x] `scripts/evaluate_run_quality.py` no longer returns perfect scores for pathological runs.
- [x] `scripts/reconcile_public_surfaces.py` produces a Markdown report comparing local run artifacts, HF exports, and Cloudflare public counts.
- [x] README links the new start-here and canon/data guide.
- [x] HF README renderer includes a link to the start-here guide and examples.
- [x] Counterfactual branches emit a divergence score and warn on no-op.
- [x] Run manifest (seed, ticks_per_year, engine_version, git_commit, run_id) propagates from the orchestrator to the persisted summary.

When these are true, Aurelia stops feeling like separate artifacts
and starts feeling like a research system.

> *No country is ready for the answer. But Mirithane is the closest to asking.*
