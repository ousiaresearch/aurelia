# Changelog

All notable changes to Aurelia are documented here.

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
