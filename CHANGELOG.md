# Changelog

All notable changes to Aurelia are documented here.

## 0.1.4-phase11-hf-datasets — 2026-06-09

### Phase 11: HuggingFace dataset publication

Aurelia's run artifacts are now exportable as four HuggingFace-ready Parquet
datasets, targeted at the `ousiaresearch/` namespace:

| repo | content | rows | size |
|---|---|---|---|
| `ousiaresearch/aurelia-causal-events` | per-world causal event stream | 560,428 | 27 MB |
| `ousiaresearch/aurelia-civilization-metrics` | yearly world state trajectories | 12,600 | 1.1 MB |
| `ousiaresearch/aurelia-federation-causal` | federation events + causal edges | 114,133 | 4.7 MB |
| `ousiaresearch/aurelia-npc-population` | NPC snapshots at end of run | 25,799 | 1.9 MB |

All four are released under **CC-BY-4.0**. Layout per repo: `data/<run_id>/train.parquet`
(or `events.parquet` + `edges.parquet` for the federation-causal repo), one
directory per simulation run, with a per-run README that includes the schema
table and a loadable example.

The five runs currently exported are the Phase 11 runs: 5y baseline, 100y
baseline, 200y baseline, 100y density-diversification, and the 5y Solara-aid
counterfactual.

### Added

- `scripts/export_hf_dataset.py` — generic SQLite→Parquet/JSONL exporter with
  `--auto` (discovers standard run dirs) and `--runs` (explicit selection).
  Supports four dataset shapes: `causal_events`, `civilization_metrics`,
  `federation_causal`, `npc_population`. Pure offline — never reads HF_TOKEN.
- `scripts/render_hf_readme.py` — emits HF card with valid frontmatter
  (`license`, `task_categories`, `size_categories`, `tags`, `language`,
  `pretty_name`, `configs`), schema table, per-run row counts, provenance map,
  loading example, and limitations section.
- `tests/test_hf_export.py` — 10 tests covering row count, JSONL round-trip,
  Parquet round-trip, schema completeness, and frontmatter invariants. Uses an
  in-test SQLite fixture so CI is offline.
- `docs/HUGGINGFACE_PUBLISH.md` — operator handoff with token handling, repo
  creation, upload commands, and per-run incremental update procedure.
- Top-level README "HuggingFace datasets" section linking to the four repos
  with row-counts, load example, and a copy-pasteable re-export block.

### Verification

- All 90 tests pass (10 new + 80 existing), including a real Parquet
  round-trip on a 139,476-row causal_events file.
- Sample export size totals: ~35 MB Parquet across 4 datasets, 41 files.
- Schema validated against the live 100y causal_events table.

### Why four separate repos (not one)

- Per-dataset discoverability on HF search
- Per-dataset versioning and release cadence
- Cleaner cards: each README is focused on one schema
- Researchers can grab just the metrics without the 27 MB causal stream

### Token / publishing handoff

The exporter and README renderer are offline. The actual `hf upload` step is
documented in `docs/HUGGINGFACE_PUBLISH.md` and requires a write token to be
supplied by the operator. No token is committed.

## 0.1.3-phase11-targeted-runs — 2026-06-09

### Phase 11: targeted runs and density-diversification knob

- Added a real `density_diversification` parameter to `run_causal_simulation` (default `0.0`, additive, `[0, 1]`) that biases the federation migration layer to balance world populations.
- Added `_balance_migration_pair` and the `density_balance` carrier in `phase10_dynamics.process_migration_carriers`.
- Added tests for the diversification knob in `tests/test_density_diversification.py`.
- Added `scripts/compare_run_demographics.py` for side-by-side run comparison.
- Added `scripts/backfill_federation_tables.py` for partial-ingest recovery.

### Targeted runs executed (this commit)

| run id | years | ticks | seed | diversification | mean pop | stddev | range | cv |
|---|---|---|---|---|---|---|---|---|
| `phase11-100y-seed1001` | 100 | 600 | 1001 | 0.0 | 74.0 | 49.9 | 142 | 0.674 |
| `phase11-200y-seed2002` | 200 | 1200 | 2002 | 0.0 | 49.4 | 54.1 | 142 | 1.096 |
| `phase11-density-100y-d07-seed3003` | 100 | 600 | 3003 | 0.7 | 66.8 | 0.4 | 1 | 0.006 |

The diversification knob reduced population coefficient of variation by **99.1%** vs the 100y baseline. Artifacts:

- `docs/reports/phase11-100y-report.md`
- `docs/reports/phase11-200y-report.md`
- `docs/reports/phase11-density-100y-report.md`
- `docs/reports/phase11-100y-quality.json`
- `docs/reports/phase11-200y-quality.json`
- `docs/reports/phase11-density-100y-quality.json`
- `docs/reports/phase11-runs-comparison.md`

### Cloudflare notes

- All three runs were pushed to Cloudflare D1.
- D1 database hit the **500MB Free plan hard cap** during the upload. Causal events, edges, civilization metrics, run manifests, and diplomatic relations are complete; cross-world movements and diffusion for the 100y and 200y runs are partial.
- D1 currently holds 4 runs (`phase11-bolster-scan-y5-seed4242`, `phase11-100y-seed1001`, `phase11-200y-seed2002`, `phase11-density-100y-d07-seed3003`) and is at exactly 500MB. To expand observability, upgrade to a paid D1 plan or split the database.
- The local SQLite run directories are the source of truth for full detail; the Cloudflare layer is for public observability.

## 0.1.2-phase11-observatory — 2026-06-09

### Phase 11: public observability

- Added a static `docs/observatory/index.html` dashboard artifact.
- Deployed a Worker-hosted public Observatory at `https://hermes-state-worker.plntrprotocol.workers.dev/public/aurelia/observatory`.
- Added read-only public Cloudflare endpoints for dashboard, runs, run summaries, causal graph slices, movement, diffusion, and diplomacy samples.
- Kept mutation/write endpoints authenticated.

## 0.1.1-phase11-tools — 2026-06-09

### Phase 11: local proof tools

- Added `scripts/export_causal_graph.py` for graph JSON exports from SQLite causal ledgers.
- Added `scripts/explain_event.py` for upstream causal-chain explanations.
- Added `scripts/render_run_report.py` for Markdown run reports.
- Added `scripts/evaluate_run_quality.py` for engine/causal/civilization/federation/narrative quality scoring.
- Added `tests/test_phase11_tools.py` plus sample outputs under `docs/examples/` and `docs/reports/`.

## 0.1.0-phase10 — 2026-06-09

### Canonical public release

- Merged the real Phase 10 engine tree with the public README, cover art, license, changelog, CI, and project metadata.
- Removed runtime artifacts from version control and hardened `.gitignore`.
- Added documentation for architecture, demo flow, roadmap, and social proof.

## 0.1.0-prepublic — 2026-06-08

### Phase 10: Causal-gap closure

Runtime closure of the causal gaps identified in
[`docs/analysis/2026-06-08-aurelia-causal-gaps-deep-dive.md`](docs/analysis/2026-06-08-aurelia-causal-gaps-deep-dive.md).

- New module `src_template/phase10_dynamics.py` concentrates Phase 10 missing-cause surface into one tested runtime layer.
- New module `src_template/capital_economy.py` (Phase 9) makes productive value creation a first-class dynamic.
- Causal graph edges are now written by every macro snapshot path.
- Cross-world NPC movement, cultural diffusion fallback, diplomatic trust accumulation, foreign strategy intervention under environmental and public-health crises.
- Counterfactual branch schema groundwork for future causal replay and alternative history tools.
- New test suite `tests/test_phase10_causal_gaps.py` (10 tests).

### Phase 9: Positive-sum dynamics

Capital economy, culture, regime, institutions. New test suites:
`test_phase9_culture.py`, `test_phase9_diplomacy.py`, `test_phase9_economy.py`,
`test_phase9_institutions.py`, `test_phase9_regime.py`.

### Phase 8: Resilience, divergence, migration, faction consequences

NPC resilience, divergence, migration, faction lifecycle consequences. New
test suites: `test_phase8_factions.py`, `test_phase8_migration.py`,
`test_phase8_profiles_macro.py`, `test_phase8_reporting_evaluator.py`.

### Cloudflare persistence

`aurelia_cf_pusher.py` pushes per-year snapshots, chronicle entries, world
state summaries, discoveries, and great persons to Cloudflare. Phase 11 extends
that data plane to raw causal events, edges, movement, diffusion, diplomacy, and
run manifests.

### Test suite

70 tests pass in ~13s. Coverage focuses on causal mechanics, federation, and
phase-specific dynamics.
