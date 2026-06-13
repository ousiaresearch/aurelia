# Aurelia Project Status — 2026-06-12 Phase 13 Verified + LLM Scaffold

Snapshot after executing the Phase 13 verified chronicle layer, durable provenance manifest, and LLM prompt scaffold.

## 1. State of the repo

- **Branch:** `phase13-llm-chronicle-layer` during the LLM scaffold push; intended base is current `main` after PR #5.
- **Phase 13 merged boundaries:**
  - PR #4: verified chronicle cards and first artifact.
  - PR #5: durable provenance manifest and no host-local committed artifact paths.
  - Current push: evidence-locked LLM prompt packets, grounded draft scaffold, and validation tests.
- **Release tag:** `v0.1.6-phase12-engine-stability` exists locally.
- **Tests:** `PYTHONPATH=. pytest tests/ -q` exits 0; collection is 176 tests across 31 files.

## 2. What changed

### Truth surface closed

- README now reports the current 176-test count instead of the stale 90-test count.
- `docs/ROADMAP.md` marks Phase 11 closed, Phase 12 closed for the 0.1.6 engine-stability boundary, and Phase 13 active.
- `v0.1.6-phase12-engine-stability` was created as an annotated local tag.

### Observatory proof surface refreshed

- `docs/observatory/index.html` now has a static 0.1.6 proof panel.
- The panel names the post-fix engine boundary, 176 passing tests, 5-seed 50y sweep, counterfactual branch, and D1 caveat.
- `tests/test_observatory_static.py` guards the proof links.

### Verified chronicle renderer shipped

- New script: `scripts/render_verified_chronicles.py`.
- New tests: `tests/test_verified_chronicles.py`.
- It builds deterministic chronicle cards from `causal_summary.json` plus per-world DBs.
- Each card includes run ID, world ID, year, metrics including faction count, top event types, source paths, and `verified`/`partial` provenance status.
- A negative-path test confirms a missing world DB marks the card `partial` while keeping summary evidence visible.
- Markdown rendering and CLI output are tested.
- The renderer now also emits LLM-layer prompt packets and offline grounded draft sections.
- Prompt packets use schema `aurelia.phase13.llm_prompt.v1` and carry the "do not invent" evidence contract.
- The LLM draft validator rejects prose that drops required evidence terms or card metadata.

### Phase 13 contract documented

- New doc: `docs/PHASE13_VERIFIED_CHRONICLES.md`.
- Contract: no invented history; deterministic evidence first; LLM prose only after source-backed cards exist.
- README and ROADMAP link the Phase 13 contract.

### First artifact published

- New artifact: `docs/reports/phase13-verified-chronicles.md`.
- New durable provenance manifest: `docs/reports/phase13-verified-chronicles.provenance.json`.
- New LLM scaffold artifact: `docs/reports/phase13-llm-chronicles.md`.
- New LLM prompt packets: `docs/reports/phase13-llm-prompts.jsonl`.
- Source run: `/tmp/aurelia-density-grid-smoke/full-diversify-seed4102`.
- It renders verified chronicle cards for Arkos, Mirithane, Solara, Valdris, and Verge.
- Each card includes source summary and source DB paths.
- The committed manifest embeds run metadata, world metrics, event evidence, and source file names without host-local absolute paths.
- The LLM artifacts preserve evidence ledgers for the same five world cards and contain no host-local `/tmp` or `/private` paths.

## 3. Remaining caveats

- The first chronicle artifact still cites the original `/tmp` run source for operator traceability, but the committed `.provenance.json` manifest now preserves compact durable evidence without depending on that path.
- The renderer is intentionally deterministic and minimal. The committed LLM chronicle artifact is an evidence-preserving scaffold, not an external model call.
- A future model pass can consume `phase13-llm-prompts.jsonl`, but outputs must pass the evidence validator before publication.

## 4. Next push

1. Merge the LLM scaffold push after review and CI.
2. Add a real model/command adapter for prompt packets once compute spend is approved or a local model is selected.
3. Expand into the counterfactual gallery and larger calibration sweep.
