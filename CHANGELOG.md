# Changelog

All notable changes to Aurelia are documented here.

## 0.1.6-phase12-engine-stability — 2026-06-11

### Phase 12.1: engine stability + counterfactual surface

Phase 12 closed the gap between lore, simulation, datasets, and public
surfaces. Phase 12.1 closes the next layer: the engine itself is now
stable at 100y and 200y horizons, the counterfactual pattern is surfaced
as a researcher demo, and the headline regressions are documented.

**Engine stability (4 feedback loops capped).** During the Phase 12
re-score, four interlocking feedback loops in the simulation engine
were producing runaway state growth. All four are now bounded by hard
absolute caps with TDD coverage:

| Loop | File | Cap | Commit |
|---|---|---|---|
| Faction formation never fired (per-tick threshold unreachable) | `src_template/faction_lifecycle.py` | Cumulative pressure over 16-tick rolling window | `482e8b4` |
| `link_tick_causality` O(N²) at >5k events/tick | `src_template/phase10_dynamics.py` | Grouped cross-product + chunked executemany (5-6× speedup) | `482e8b4` |
| Migration effect cap scaled with active population | `src_template/migration_flows.py` | `MAX_MIGRATION_EVENTS_PER_TICK = 8` | `ad52b21` |
| Migration cohort size scaled with population | `src_template/migration_flows.py` | `MAX_MIGRATION_COHORT_SIZE = 25` | `9eb8556` |
| Faction splinter doubled the open set per tick | `src_template/faction_lifecycle.py` | Parent marked terminal on splinter | `21028c0` |
| Per-faction outcome re-roll event flood | `src_template/faction_lifecycle.py` | `MIN_OUTCOME_INTERVAL_TICKS = 4` | `29dca9f` |

**Empirical at npc_count=100 seed=1001 (the failing pre-fix target):**
- 100y: tick 175 killed (verge.db 2.4 GB) → tick 1200 completes (D1 0.80)
- 200y: not reachable → completes in 210s (D1 0.80)
- density-100y: completes in 84s (D1 0.85, pop CV 0.039)

**Counterfactual surface (Phase 11.5 shipped).** The
`src_template/counterfactuals.py` module has been in the repo since
Phase 11 but was never surfaced as a researcher demo. Now shipped:
- `examples/04_run_counterfactual_branch.py` — paired-simulation
  comparison with same seed, `density_diversification` 0.0 vs 1.0,
  prints a divergence report
- `docs/AURELIA_COUNTERFACTUALS.md` — researcher guide covering
  paired-simulation and post-run intervention patterns, the
  `divergence_score` formula, and how to read per-world deltas
- Wired into `AURELIA_RESEARCH_START_HERE.md` (4th command) and
  `README.md`

Verified at 50y npc_count=80 seed=1001: divergence_score 5104.4, top
change is `reconciliation_process +219`, solara +2080 events vs verge
-1483 (consistent with density=1.0 rebalancing migration flow).

**Test count: 138 → 166** (+28 tests across 5 new test files):
- `tests/test_faction_formation_in_runs.py` (5)
- `tests/test_link_tick_causality_perf.py` (6)
- `tests/test_run_quality_gates.py` (6)
- `tests/test_run_manifest.py` (4)
- `tests/test_public_surface_reconciliation.py` (6)
- `tests/test_density_plot.py` (4)
- `tests/test_migration_feedback_loop.py` (5) — new
- `tests/test_phase8_factions.py` (+4 — splinter parent terminal + cooldown)

**Project status snapshot.** `docs/PROJECT_STATUS_2026-06-11.md`
captures the settled state, the open items from previous closures,
and the leverage-ordered workstream queue.

## 0.1.5-phase12-gap-closure — 2026-06-10

### Phase 12: gap closure between lore, simulation, datasets, and public surfaces

Phase 12 turns Aurelia from three impressive but separate artifacts into
one inspectable system. The plan delivered eight workstreams end-to-end:

**A. Canon bridge** — `docs/data/aurelia_concepts.yaml` (32 concepts with
status, wiki paths, code paths, tables, datasets, Cloudflare surfaces, and
proof artifacts). `scripts/render_canon_data_guide.py` deterministically
generates `docs/AURELIA_CANON_AND_DATA_GUIDE.md`.

**B. Wiki reconciliation** — `docs/AURELIA_WIKI_RECONCILIATION_REVIEW.md`
plus three Desktop wiki patches (public front door, simulation status,
TTRPG-adjacent archive). The wiki itself (139 markdown + 90 image
files) was migrated to `docs/wiki/` as the canonical public surface.

**C. Dataset research UX** — `examples/aurelia_dataset_loader.py` with
Parquet + SQLite backends. `examples/01_load_aurelia_hf_datasets.py`,
`02_reproduce_density_diversification.py` (reproduces the **99.1%** CV
reduction exactly), and `03_trace_causal_chain.py`. Dual-track start-here
pages: `AURELIA_RESEARCH_START_HERE.md` (HF/ML) and
`AURELIA_LORE_READERS_START_HERE.md` (world).

**D. Simulation quality gates** — `scripts/evaluate_run_quality.py` now
hard-caps the score for pathological runs (factions absent, population
collapse, high CV, missing manifest). Manifest propagation adds
`seed`, `ticks_per_year`, `density_diversification`, `engine_version`,
`git_commit`, `run_id`, `created_at` to the orchestrator summary.
`scripts/compare_runs.py` adds `divergence_score` and no-op warnings.

**E. Public surface reconciliation** — `scripts/reconcile_public_surfaces.py`
produces a Markdown report comparing local runs, HF exports, and the
Cloudflare dashboard. `docs/ARCHITECTURE.md`, `README.md`, and
`docs/DEMO.md` document the D1 cap reality honestly.

**F. HF card integration** — each rendered dataset README links to
the research start-here guide, the relevant examples, and the canon
bridge.

**G. Research figure** — `scripts/plot_density_diversification.py`
generates `docs/reports/figures/density-diversification.svg` from real
data with no plotting-library dependency.

**H. Closure report** — this entry plus
`docs/reports/phase12-gap-closure-report.md`.

### Added

- `docs/data/aurelia_concepts.yaml` — 32 concept bridge entries
- `docs/AURELIA_CANON_AND_DATA_GUIDE.md` — generated from the YAML
- `docs/AURELIA_RESEARCH_START_HERE.md`, `docs/AURELIA_LORE_READERS_START_HERE.md`
- `docs/wiki/` — full public wiki (139 markdown + 90 image files)
- `examples/aurelia_dataset_loader.py`
- `examples/01_load_aurelia_hf_datasets.py`
- `examples/02_reproduce_density_diversification.py`
- `examples/03_trace_causal_chain.py`
- `scripts/reconcile_public_surfaces.py`
- `scripts/plot_density_diversification.py`
- `docs/reports/public-surface-reconciliation.md`
- `docs/reports/figures/density-diversification.svg`
- `docs/reports/phase12-gap-closure-report.md`

### Changed

- `scripts/evaluate_run_quality.py` — pathological-run gates with module-level thresholds
- `src_template/federation_orchestrator.py` — manifest fields + `ENGINE_VERSION`, `GIT_COMMIT`, `make_run_id`
- `src_template/counterfactuals.py` — divergence score + top changed event types + no-op warning
- `scripts/render_hf_readme.py` — `related_examples` per schema + canon-bridge + research-guide sections
- `docs/ARCHITECTURE.md`, `README.md`, `docs/DEMO.md`, `docs/HUGGINGFACE_PUBLISH.md` — D1 cap honest framing + examples section
- `README.md` — dual-track "Two ways to start" + "Start with the research examples" sections

### Test surface

138 tests pass. New test files:

- `tests/test_dataset_examples.py` — loader + 3 examples (parquet + sqlite)
- `tests/test_run_quality_gates.py` — pathology gates
- `tests/test_run_manifest.py` — orchestrator manifest propagation
- `tests/test_public_surface_reconciliation.py` — local vs HF vs CF
- `tests/test_density_plot.py` — stdlib SVG figure
- `tests/test_hf_export.py` — extended with F1 link assertions

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
