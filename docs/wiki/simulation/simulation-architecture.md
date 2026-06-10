# Aurelia Simulation Architecture

> **Canon status:** current architecture summary. This supersedes older local-daemon-only architecture language while retaining the same lore/world identities.

Aurelia is a causal, five-world civilization simulation. It is built around a simple invariant:

> If a world-level outcome matters, it should be represented as data and connected to its causes.

The current architecture is a barrier-synchronized causal engine: each world advances through micro, meso, and macro dynamics; federation-level systems carry cross-world consequences; all important events are written to a causal ledger; completed run artifacts can be inspected, reported, exported, compared, and published.

---

## Runtime flow

```text
NPC/type/faction/world state
  ↓
Micro interactions and local events
  ↓
Meso aggregation
  ↓
Macro dynamics: ecology, resources, disease, education, urbanization,
regime, repression, property rights, state capacity, conflict,
discovery, great persons, migration, demography, capital
  ↓
Causal event + causal edge rows
  ↓
Barrier-synchronized federation tick
  ↓
Cross-world effects: migration, diplomacy, cultural diffusion,
trade/resource shocks, conflict spillover, aid/intervention
  ↓
SQLite world databases + federation database
  ↓
Reports, causal graph exports, event explanations, quality scans,
Hugging Face datasets, Cloudflare Observatory
```

---

## Core components

- `causal_run.py` — convenience entry point for barrier-synchronized causal runs.
- `aurelia_factory.py` — builds and seeds worlds from configuration.
- `aurelia_coordinator.py` — federation coordinator across worlds.
- `aurelia_cf_pusher.py` — bulk-upload/publication layer for Cloudflare D1/R2.
- `src_template/causal_ledger.py` — event/edge schema used by micro, meso, macro, and federation layers.
- `src_template/federation_orchestrator.py` — processes all worlds at tick `T`, resolves federation effects, then advances to `T+1`.
- `src_template/phase10_dynamics.py` — ecology/resources, disease, education, urbanization, inequality, institutions, regime, repression, discoveries, great persons, and migration carriers.
- `src_template/federation_effects.py` — applies cross-world consequences.
- `src_template/cultural_diffusion.py` — cross-world trait adoption/resistance.
- `src_template/yearly_report.py` — per-year report generation.
- `scripts/export_causal_graph.py` — graph export.
- `scripts/explain_event.py` — upstream causal explanation.
- `scripts/render_run_report.py` — human-readable run report.
- `scripts/evaluate_run_quality.py` — engine/narrative/federation quality scoring.
- `scripts/run_counterfactual.py` and `scripts/compare_runs.py` — intervention branch support.

---

## Data model

A run produces one SQLite database per world plus a federation database.

Core tables include:

- `causal_events` — event nodes with tick, world, layer, type, actor/target IDs, magnitude, valence, confidence, and payload.
- `causal_edges` — directed links between causes and consequences.
- `civilization_metrics` — per-tick world metrics.
- `agents` / NPC population tables — population and type state.
- `demographic_events` — births, deaths, immigration, emigration.
- `discoveries` and `great_persons` — discontinuous historical events.
- `factions`, `institutions`, `regime_events` — political and institutional state.
- federation tables for cross-world effects, diplomatic relations, cultural diffusion, movements, and strategy events.

---

## World identities

The five worlds retain their lore identities:

- Solara
- Arkos
- Mirithane
- Valdris
- The Verge

In current public architecture, these are best understood as abstract worlds/civilizational profiles. Older one-landmass geography may remain in lore documents if marked as narrative context, but technical/public docs should not depend on a fixed map.

---

## Time model

Aurelia supports configurable run lengths and deterministic completed-run artifacts. Avoid claiming a single always-on real-time daemon as the only source of truth.

Preferred framing:

- simulations advance through ticks/years according to run configuration;
- completed runs are persisted as SQLite artifacts;
- reports, graph slices, HF exports, and Cloudflare samples derive from those artifacts.

---

## Scale model

Aurelia’s population scale is run-dependent.

Use the standard taxonomy:

1. **Lore population** — fictional demographic background.
2. **Authored seed registry** — named characters, distributions, cultural archetypes.
3. **Historical daemon experiments** — 600/60K local scaling experiments.
4. **Published Phase 11 datasets** — current public research surface.
5. **Future production scale** — only claimed after quality gates pass.

Do not present old 600 or 60K numbers as the single permanent scale of Aurelia.

---

## Causality discipline

Aurelia distinguishes three artifacts:

1. **Event sequence** — what happened in tick order.
2. **Causal graph** — which event contributed to which later or same-tick effect.
3. **Narrative chronicle** — human-readable summary generated from the data.

The graph is primary. Narrative is downstream.

---

## Cloudflare and Hugging Face

Cloudflare is a public observability and durability layer, not the hot simulation loop. Completed run artifacts are exported or ingested after local execution.

Hugging Face datasets expose the research surface:

- `OusiaResearch/aurelia-causal-events`
- `OusiaResearch/aurelia-civilization-metrics`
- `OusiaResearch/aurelia-federation-causal`
- `OusiaResearch/aurelia-npc-population`

Local and HF artifacts remain the complete archive when public edge surfaces show only samples or summaries.

---

## Verification gates

A credible Aurelia run should pass:

1. unit suite: `PYTHONPATH=. pytest tests -q`;
2. causal smoke run;
3. run-quality scan;
4. report render;
5. causal graph/event explanation spot checks;
6. dataset export validation;
7. Cloudflare verification if publishing to the Observatory.

---

## Historical architecture note

Older wiki docs described five live local daemons, fixed ports, a local dashboard, and 600/60K NPC experiments. Those notes are useful engineering history but should not be presented as the current public architecture without a historical banner.
