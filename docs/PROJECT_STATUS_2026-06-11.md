# Aurelia Project Status — 2026-06-11

Snapshot after the Phase 12 closure + Phase 12.1 engine stability sprint.
Persists between sessions so future agents don't have to re-derive the
state from git log and CHANGELOG archaeology.

## TL;DR

Aurelia is in a **stable, inspectable, public** state. The engine no
longer runaways at 100y/200y horizons. The 5-world simulation produces
verifiable causal histories. The data, code, and lore are all reconciled
through a single canon bridge. The next push is research UX (counter­
factuals surfaced), then a baseline-sweep of the now-stable engine.

## State of the repo

- **Branch:** `main`, working tree clean, 166/166 tests green
- **Last commit:** `29dca9f fix(phase12): debounce per-faction outcome re-rolls`
- **Headline releases:**
  - `0.1.5-phase12-gap-closure` (2026-06-10): eight-workstream gap closure
  - `0.1.4-phase11-hf-datasets` (2026-06-09): HF publication
  - `0.1.3-phase11-targeted-runs` (2026-06-09): density-diversification knob
- **Repo size:** 141 MB (of which 59 MB is the public `docs/wiki/`)

## Where we are settled

### 1. Engine stability (Phase 12.1 — this session)

Four feedback loops identified and capped. All runs that previously
runaway now complete cleanly at the target horizon.

| Loop | File | Fix | Commit |
|---|---|---|---|
| Faction formation never fired (per-tick threshold unreachable) | `faction_lifecycle.py` | Cumulative pressure over 16-tick window | `482e8b4` |
| `link_tick_causality` O(N²) at >5k events/tick | `phase10_dynamics.py` | Grouped cross-product + chunked executemany (5-6× speedup) | `482e8b4` |
| Migration effect cap scaled with active population | `migration_flows.py` | `MAX_MIGRATION_EVENTS_PER_TICK = 8` | `ad52b21` |
| Migration cohort size scaled with population | `migration_flows.py` | `MAX_MIGRATION_COHORT_SIZE = 25` | `9eb8556` |
| Faction splinter doubled the open set per tick | `faction_lifecycle.py` | Parent marked terminal on splinter | `21028c0` |
| Per-faction outcome re-roll event flood | `faction_lifecycle.py` | `MIN_OUTCOME_INTERVAL_TICKS = 4` | `29dca9f` |

Empirical at 100y npc_count=100 seed=1001 (the failing pre-fix target):
- Pre-fix: tick 175 killed, verge.db 2.4 GB runaway
- Post-fix: tick 1200 completes, federation.db 175k events, D1 score 0.80

### 2. Public surface (Phase 12 C-H, prior sessions)

| Surface | Location | Status |
|---|---|---|
| README with dual-track entry | `README.md` | live |
| HF/ML researcher start-here | `docs/AURELIA_RESEARCH_START_HERE.md` | live |
| Lore reader start-here | `docs/AURELIA_LORE_READERS_START_HERE.md` | live |
| Canon + data guide | `docs/AURELIA_CANON_AND_DATA_GUIDE.md` | live, auto-generated |
| Architecture | `docs/ARCHITECTURE.md` | live, honest about D1 cap |
| Demo | `docs/DEMO.md` | live |
| Public wiki (139 .md + 90 images) | `docs/wiki/` | live, canonical |
| Media kit draft | `docs/media/media-kit.md` | live, awaiting social scheduling |
| HuggingFace datasets | 4 published, dual-track cards linked to research guide | live |

### 3. Dataset research UX (Phase 12 C, prior session)

| Artifact | Status |
|---|---|
| `examples/aurelia_dataset_loader.py` (Parquet + SQLite, PyArrow only) | shipped |
| `examples/01_load_aurelia_hf_datasets.py` | shipped, validated against `/tmp/hf-export` |
| `examples/02_reproduce_density_diversification.py` | shipped, reproduces 99.1% CV reduction exactly |
| `examples/03_trace_causal_chain.py` | shipped, traces 3-hop causal chains from real data |
| Density diversification SVG figure | shipped, `docs/reports/figures/density-diversification.svg` |

### 4. Quality gates (Phase 12 D, prior session)

- `scripts/evaluate_run_quality.py` now hard-caps on faction absence,
  population collapse, CV > 1.0, and missing manifest
- Manifest fields (`seed`, `ticks_per_year`, `density_diversification`,
  `engine_version`, `git_commit`, `run_id`, `created_at`) propagated
  through the orchestrator summary
- `scripts/compare_runs.py` adds `divergence_score` + no-op warning
- `scripts/reconcile_public_surfaces.py` reconciles local + HF + Cloudflare

## D1 quality scores (post-fix)

| Horizon | D1 | Notes |
|---|---|---|
| 100y | 0.80 | mirithane collapses, all 5 worlds reach tick 1200 |
| 200y | 0.80 | arkos + valdris collapse (sustained-collapse behavior preserved) |
| density-100y | 0.85 | populations balanced 22-24, CV 0.039 |
| 5y smoke | 0.85+ | 6-second runtime, factions forming |

## Open items from previous closures

- **Old reports reference pre-fix numbers** — `docs/reports/phase11-*` were
  generated before the feedback-loop fixes. The new post-fix runs
  (100y=145,858 events, 200y=309,700, density-100y) are not yet
  committed as reports.
- **Desktop wiki is redundant** — `~/Desktop/Aurelia/` is a local git
  repo with 3 patches (3045ecf, 5c7705e, a73b18d). Its content was
  migrated to `docs/wiki/` and is now canonical. The Desktop repo is
  not pushed (no remote) and is redundant with the public surface.
- **CHANGELOG is at 0.1.5** — the 0.1.6 release with the four
  feedback-loop fixes hasn't been written.
- **Cloudflare Observatory index.html** is in `docs/observatory/` but
  was last touched before the post-fix runs. Not yet refreshed.

## Where we can push this — leverage-ordered

The settled foundation above is the asset. The pushable work is below,
ordered by impact-per-effort.

### A. Counterfactual UX (Phase 11.5 surface) — HIGH leverage

The infrastructure is already in place:
- `src_template/counterfactuals.py` (apply_intervention_file, compare_runs, render_comparison_report)
- `scripts/run_counterfactual.py` (CLI entry point)
- `tests/test_counterfactuals.py` (test coverage)

What's missing: a researcher-facing example + a docs page. Pattern from
C-workstream (which the user approved): a 4th `examples/04_run_counterfactual_branch.py`
that runs a baseline and a branched scenario, prints the divergence,
plus a `docs/AURELIA_COUNTERFACTUALS.md` guide. Same dual-track pattern.

Why high leverage: counterfactual branches are the single most
compelling demo for an LLM/ML researcher audience. "Same seed, two
histories, this is what changes when density_diversification=1.0" is
the headline proof. Estimated: 1 commit, 1 example, 1 docs page,
~30 minutes.

### B. Post-fix report refresh — QUICK WIN

Replace `docs/reports/phase11-*-report.md` and the corresponding
`-quality.json` files with post-fix numbers. This is a one-shot
update that re-aligns the public proof surface with the actual current
engine. The 0.80 cap that drove the original D1 report was the
*valdris collapse* behavior, which is preserved post-fix — so the
"0.80 ceiling" story still holds, but the underlying event counts and
federation totals are different.

Why: the reports are what researchers see first. Stale numbers erode
trust. Estimated: 1 commit, 30 minutes (most of it running the
re-score). Should pair with a CHANGELOG bump to 0.1.6.

### C. CHANGELOG 0.1.6 + release tag

The current CHANGELOG goes 0.1.3 → 0.1.4 → 0.1.5, but the four
feedback-loop fixes in this session aren't in any release. Writing
`0.1.6-phase12-engine-stability` with the four fixes as the headline
gives a clean release boundary for anyone tracking the project.

Why: release tags are the unit of progress in the Ousia Research
publication model (per `AURELIA_HUGGINGFACE_PUBLISH.md`). Estimated:
10 minutes, 1 commit.

### D. Multi-seed sweep of the now-stable engine — RESEARCH LEVERAGE

The engine is now stable. Running the same 100y horizon at 5+ seeds
gives statistical power over the diversity/divergence numbers. The
Phase 12 plan called for "seed sweeps for richness/divergence" but
those were written before the engine was stable. A proper sweep on
the fixed engine produces:
- A mean ± std for `causal_richness`, `civilization_richness`,
  `total_faction_formations`, etc.
- A `phase12-seed-sweep-quality.json` and `phase12-seed-sweep-report.md`
- Updated `phase11-runs-comparison.md` with the new numbers

Why: gives researchers a confidence interval rather than a single
point. Aligns with the Phase 12 plan that was never executed. The
engine is fast enough (100y = ~2 min) that 10 seeds = 20 min wall.
Estimated: 3 commits (sweep runner, results, docs), 1 hour.

### E. Cloudflare Observatory refresh — PUBLIC SURFACE LEVERAGE

The Observatory at `docs/observatory/index.html` is the public
dashboard. It's been static since before the post-fix runs. Updating
it to reflect:
- The post-fix run numbers
- The new "Faction Lifecycle" narrative (formation → splinter → resolution)
- Links to the updated reports
- The counterfactual guide (when shipped)

Why: the Observatory is what people see when they want to "look at
Aurelia" without running it. Stale = looks dead. Estimated: 1 commit,
30-60 minutes depending on how much is auto-generated vs hand-crafted.

### F. Phase 13 narrative layer — BIG WORKSTREAM, NOT IMMEDIATE

The `batch_chronicles.py` exists but hasn't been wired into the current
stable engine. Per the CHANGELOG 0.1.4 plan, Phase 13 generates prose
chronicles from verified run artifacts. This is the "narrative layer
over verified history" workstream and was always going to be the next
big build after Phase 12.

Why listed but not immediate: it's a different class of work (LLM
batch + GPU orchestration), not an iteration on what's settled. Should
be a separate project plan, not a follow-up commit.

## Recommended next move

**A + C together** (counterfactual UX + CHANGELOG bump). Total: ~45 min,
1-2 commits, ships a researcher-facing demo and closes out the engine
stability release. The user has already approved this dual-track
pattern (C-workstream shipped the same way). Then **B** (report
refresh) is a clean follow-on. Then **D** (seed sweep) is the natural
research next-step once the public proof is updated.
