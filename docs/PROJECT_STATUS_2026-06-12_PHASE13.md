# Aurelia Project Status — 2026-06-12 Phase 13 Start

Snapshot after executing the Phase 13 verified chronicle layer plan on branch `phase13-verified-chronicles`.

## 1. State of the repo

- **Branch:** `phase13-verified-chronicles`.
- **Base:** `main` after `a9218d6 docs(aurelia): plan phase 13 verified chronicle layer`.
- **Phase 13 commits on branch:**
  - `d82edc5 docs(aurelia): update quickstart test count`
  - `19e2c11 docs(aurelia): mark phase 13 as active frontier`
  - `ca821ef docs(aurelia): refresh observatory proof surface`
  - `26ac4d6 feat(aurelia): render verified chronicle cards`
  - `110da8e docs(aurelia): define phase 13 verified chronicle contract`
  - `38ba544 docs(aurelia): link phase 13 chronicle frontier`
  - `91a3918 docs(aurelia): publish first verified chronicle artifact`
  - post-review fix: renderer Markdown now includes faction counts; provenance partial-path behavior is tested; README/Observatory counts are 171.
- **Release tag:** `v0.1.6-phase12-engine-stability` exists locally.
- **Tests:** `PYTHONPATH=. pytest tests/ -q` exits 0; collection is 171 tests across 31 files.

## 2. What changed

### Truth surface closed

- README now reports the current 171-test count instead of the stale 90-test count.
- `docs/ROADMAP.md` marks Phase 11 closed, Phase 12 closed for the 0.1.6 engine-stability boundary, and Phase 13 active.
- `v0.1.6-phase12-engine-stability` was created as an annotated local tag.

### Observatory proof surface refreshed

- `docs/observatory/index.html` now has a static 0.1.6 proof panel.
- The panel names the post-fix engine boundary, 171 passing tests, 5-seed 50y sweep, counterfactual branch, and D1 caveat.
- `tests/test_observatory_static.py` guards the proof links.

### Verified chronicle renderer shipped

- New script: `scripts/render_verified_chronicles.py`.
- New tests: `tests/test_verified_chronicles.py`.
- It builds deterministic chronicle cards from `causal_summary.json` plus per-world DBs.
- Each card includes run ID, world ID, year, metrics including faction count, top event types, source paths, and `verified`/`partial` provenance status.
- A negative-path test confirms a missing world DB marks the card `partial` while keeping summary evidence visible.
- Markdown rendering and CLI output are tested.

### Phase 13 contract documented

- New doc: `docs/PHASE13_VERIFIED_CHRONICLES.md`.
- Contract: no invented history; deterministic evidence first; LLM prose only after source-backed cards exist.
- README and ROADMAP link the Phase 13 contract.

### First artifact published

- New artifact: `docs/reports/phase13-verified-chronicles.md`.
- Source run: `/tmp/aurelia-density-grid-smoke/full-diversify-seed4102`.
- It renders verified chronicle cards for Arkos, Mirithane, Solara, Valdris, and Verge.
- Each card includes source summary and source DB paths.

## 3. Remaining caveats

- The first chronicle artifact cites a `/tmp` run source. It is real local run data, but not a durable committed run archive. Future chronicle artifacts should either cite HF/local committed metadata or copy a compact provenance manifest into `docs/reports/`.
- The renderer is intentionally deterministic and minimal. It does not yet produce literary prose.
- `src_template/batch_chronicles.py` remains the future LLM layer, not yet integrated with the verified-card scaffold.
- The branch is ready to push and/or merge after review.

## 4. Next push

1. Push branch `phase13-verified-chronicles` and tag `v0.1.6-phase12-engine-stability`.
2. Merge/PR into `main` after review.
3. Add a provenance manifest mode so Phase 13 artifacts do not depend on ephemeral `/tmp` paths.
4. Build the LLM chronicle layer over deterministic cards, preserving event evidence in every generated prose output.
5. Expand into the counterfactual gallery and larger calibration sweep.
