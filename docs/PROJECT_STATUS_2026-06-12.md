# Aurelia Project Status — 2026-06-12

Snapshot after the 2026-06-11 recommendation batch shipped: counterfactual UX, CHANGELOG 0.1.6, post-fix report refresh, and the first post-fix multi-seed sweep.

## 1. State of the repo

- **Branch:** `main`, clean against `origin/main` before this status document.
- **HEAD before this status doc:** `791da10 feat(aurelia): multi-seed sweep on the stable engine`.
- **Remote:** `https://github.com/ousiaresearch/aurelia.git`.
- **Repo size:** 141 MB.
- **Tests:** `pytest tests/ --collect-only -q` collects 166 tests across 29 files; `pytest tests/ -q` exits 0.
- **Latest CHANGELOG boundary:** `0.1.6-phase12-engine-stability — 2026-06-11`.
- **Tags:** only `v0.1.0-phase10` exists locally; the release tag trail is behind the documented release boundaries.
- **Identity:** Aurelia is a causal civilization simulation: five abstract worlds, SQLite/causal-ledger substrate, Cloudflare public observability, HuggingFace/local datasets, and counterfactual branching.

## 2. Where we are settled

### Engine stability and quality gates

Aurelia is no longer in the runaway-debugging phase. The Phase 12.1 feedback-loop caps landed, and the post-fix engine completes the horizons that previously killed the process.

- Feedback-loop fixes are documented in `CHANGELOG.md` 0.1.6: faction formation pressure, O(N²) causality linking, migration event cap, migration cohort cap, splinter terminalization, and faction outcome debounce.
- `scripts/evaluate_run_quality.py` has hard caps for faction absence, population collapse, high CV, and missing manifest.
- Post-fix public reports are refreshed under `docs/reports/phase11-*`.
- Test surface is at 166 collected tests and the full suite exits 0.

### Researcher UX and counterfactual proof

The previous high-leverage gap is now shipped: counterfactual branching is no longer hidden infrastructure.

- `examples/04_run_counterfactual_branch.py` runs a same-seed paired simulation.
- `docs/AURELIA_COUNTERFACTUALS.md` explains paired simulation vs post-run intervention, divergence scoring, and no-op warnings.
- `docs/AURELIA_RESEARCH_START_HERE.md` now has four commands: load HF datasets, reproduce density diversification, trace a causal chain, run a counterfactual branch.
- README links the fourth example and the counterfactual guide.

### Seed-sweep evidence

The engine now has a small but real distributional evidence layer.

- `scripts/run_seed_sweep.py` exists.
- `docs/reports/phase12-seed-sweep-report.md` reports 5 seeds at npc_count=100, years=50, density_diversification=0.0, ticks_per_year=6.
- D1 quality was stable at 0.85 for all five seeds.
- Mean causal events: 61,987 ± 1,284; mean causal edges: 52,236 ± 1,308.
- `docs/reports/phase11-runs-comparison.md` now includes the Phase 12 seed sweep section.

### Canon, wiki, and public data surfaces

The project is publicly inspectable rather than split across a wiki, codebase, and private operator notes.

- `docs/wiki/` is the canonical public wiki surface.
- `docs/data/aurelia_concepts.yaml` and `docs/AURELIA_CANON_AND_DATA_GUIDE.md` bridge concepts across lore, code, data, datasets, Cloudflare, and proof artifacts.
- Four HuggingFace dataset families are documented in README and `docs/HUGGINGFACE_PUBLISH.md`.
- Local/Parquet/HF remain the complete research source of truth; Cloudflare D1 remains the public observability plane with known 500MB cap limitations.

### Phase 13 substrate exists, but is not yet productized

The next large layer is visible in code but not yet settled.

- `src_template/batch_chronicles.py` can generate post-simulation yearly chronicles from DBs and event logs using a local GGUF model client.
- The roadmap names Phase 13 as "narrative layer over verified history."
- This is still a build target, not a completed product surface: it is not wired into the current stable run/report/observatory publication flow.

## 3. Open items from previous closures

- **Release tags are stale.** Git only shows `v0.1.0-phase10`; CHANGELOG documents 0.1.1 through 0.1.6. At minimum, `v0.1.6-phase12-engine-stability` should exist.
- **README Quickstart test count is stale.** It still says `# 90 passed in ~11s`; current collected count is 166.
- **ROADMAP status is stale.** It still marks Phase 11 as "in progress" even though Phase 11/12 workstreams have materially shipped and Phase 13 is now the strategic frontier.
- **Cloudflare Observatory is likely behind the post-fix truth surface.** README links the Observatory, but the checked-in static dashboard is older than the current post-fix reports/counterfactual/seed-sweep layer.
- **D1 capacity remains a strategic constraint.** The public observability plane is storage-capped; complete research truth lives in local/HF artifacts.
- **Desktop wiki redundancy remains a housekeeping loose end.** The repo has the canonical public `docs/wiki/`; the old Desktop copy should be explicitly archived/ignored/deleted in an operator note if it is no longer needed.

## 4. Where we can push — leverage-ordered

### A. Phase 13: verified chronicle layer — highest leverage

**Why:** This is the next identity-level leap: turn verified causal histories into readable civilization history without inventing facts.

**Effort:** Multi-session if using LLM chronicle generation; one tight first commit if we start with an extractive/no-LLM chronicle index.

**What already exists:** `src_template/batch_chronicles.py`, yearly/event-report conventions, causal ledgers, run reports, wiki voice/material.

**Reference paths:** `src_template/batch_chronicles.py`, `docs/ROADMAP.md`, `docs/reports/phase11-*-report.md`, `docs/AURELIA_COUNTERFACTUALS.md`.

**Lead:** Build a small Phase 13 proof that reads an existing run artifact and emits a verified chronicle card per world/year with provenance links back to event IDs, report rows, or graph slices. Do not start with freeform prose. Start with provenance-preserving narrative.

### B. Truth-surface release pass — small effort, high trust

**Why:** The repo now has real 0.1.6 substance, but the public status trail lags it in tags, README quickstart count, and ROADMAP status.

**Effort:** 1 commit plus tag.

**What already exists:** CHANGELOG 0.1.6, reports, counterfactual docs, seed sweep report.

**Reference paths:** `CHANGELOG.md`, `README.md`, `docs/ROADMAP.md`, git tags.

**Lead:** Tag `v0.1.6-phase12-engine-stability`, update README Quickstart to 166 tests, and update ROADMAP so Phase 11/12 are closed and Phase 13 is the active frontier.

### C. Observatory refresh / public demo surface

**Why:** The Observatory is what a visitor sees when they want to "look at Aurelia" without running it. If it does not reflect counterfactuals, post-fix reports, and the seed sweep, it undersells the project.

**Effort:** 1-2 commits depending on whether we hand-edit or add a renderer.

**What already exists:** `docs/observatory/index.html`, public Worker URLs, run reports, seed sweep report, counterfactual guide.

**Reference paths:** `docs/observatory/index.html`, `docs/reports/phase11-runs-comparison.md`, `docs/reports/phase12-seed-sweep-report.md`, `docs/AURELIA_COUNTERFACTUALS.md`.

**Lead:** Add a visible "0.1.6 / post-fix engine" section: quality scores, five-seed sweep, counterfactual demo, D1 cap caveat, and links into reports.

### D. Counterfactual gallery

**Why:** A single density-diversification branch proves the mechanism. A gallery of 3-5 same-seed branches turns it into a research artifact.

**Effort:** 1-2 sessions depending on runtime.

**What already exists:** `examples/04_run_counterfactual_branch.py`, `src_template/counterfactuals.py`, divergence scoring, quality gates.

**Reference paths:** `examples/04_run_counterfactual_branch.py`, `scripts/run_counterfactual.py`, `tests/test_counterfactuals.py`, `docs/AURELIA_COUNTERFACTUALS.md`.

**Lead:** Run branches for density, education, disease pressure, and migration/federation aid, then publish compact comparison cards with divergence scores and top event-type deltas.

### E. Larger calibration sweep

**Why:** The 5-seed 50y sweep proves stability, but it is not yet a production-calibration layer. A larger matrix gives confidence before 100y/200y claims.

**Effort:** Bounded compute batch; may be local or Colab depending on runtime.

**What already exists:** `scripts/run_seed_sweep.py`, quality gates, post-fix reports, seed-sweep report format.

**Reference paths:** `scripts/run_seed_sweep.py`, `docs/reports/phase12-seed-sweep-report.md`, `docs/reports/phase12-gap-closure-report.md` recommended run matrix.

**Lead:** 20 seeds × 25 years for calibration, then 5 seeds × 100 years once gate warnings are acceptable. Include density variants only after the baseline matrix is clean.

### F. Social / HF release package

**Why:** Aurelia has the ingredients for a public research drop, but needs the release bundle to make it legible outside this chat.

**Effort:** 1 session.

**What already exists:** `docs/social/aurelia-hf-dataset-posts.md`, `docs/wiki/media/media-kit.md`, HF dataset cards, reports, figures, counterfactual guide.

**Reference paths:** `docs/social/`, `docs/wiki/media/`, `docs/assets/hf-promo-v2/`, `docs/reports/figures/density-diversification.svg`.

**Lead:** Package the release as "Aurelia 0.1.6: causal histories, counterfactual branches, and verified chronicle frontier" with no public posting unless explicitly approved.

## 5. Recommended next move

Lead Aurelia into **Phase 13**, but do not jump straight into invented prose. The right sequence is:

1. **B — truth-surface release pass** first: tag 0.1.6, fix README count, update ROADMAP. This closes the public boundary.
2. **C — Observatory refresh** second: make the visible public surface match the current post-fix/counterfactual/seed-sweep reality.
3. **A — Phase 13 verified chronicle proof** third: build the smallest provenance-preserving narrative artifact from existing run data.

After that, run **D + E** as the research expansion: counterfactual gallery and larger calibration sweep. The strategic direction is clear: Aurelia should become a system where a visitor can move from public dashboard → verified report → causal graph → counterfactual branch → narrative chronicle, with every sentence tied back to the run artifact that caused it.
