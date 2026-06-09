# Aurelia Architecture

Aurelia is a causal, five-world civilization simulation. It is built around a simple invariant: if a world-level outcome matters, it should be represented as data and connected to its causes.

## Runtime flow

```text
NPC interactions
  ↓
Meso signal aggregation
  ↓
Macro state update
  ↓
Faction, diplomacy, migration, capital, demography, ecology, discovery, institution dynamics
  ↓
Causal ledger rows
  ↓
Barrier-synchronized federation tick
  ↓
SQLite run artifacts
  ↓
Cloudflare D1/R2 bulk persistence
  ↓
Reports, dashboards, and graph queries
```

## Core components

- `causal_run.py` — command-line entry point for barrier-synchronized causal runs.
- `src_template/federation_orchestrator.py` — processes every world at tick `T`, resolves federation effects, then advances to `T+1`.
- `src_template/causal_ledger.py` — common event/edge schema used by micro, meso, macro, and federation layers.
- `src_template/phase10_dynamics.py` — closes Phase 10 causal gaps: ecology/resources, education, urbanization, disease, property rights, state-capacity type, repression type, conflict type, discoveries, great persons, path dependence, migration carriers, diffusion fallback, and foreign strategy.
- `src_template/yearly_report.py` — creates per-year world reports from run DBs.
- `aurelia_cf_pusher.py` — bulk-uploads completed run artifacts to Cloudflare.

## Data model

A run produces one SQLite database per world plus `federation.db`:

- `causal_events` — event nodes with tick, world, layer, type, magnitude, valence, confidence, and JSON payload.
- `causal_edges` — directed links between event nodes.
- `civilization_metrics` — Phase 10 world metrics per tick.
- `discoveries` and `great_persons` — discontinuous historical events.
- `demographic_events` — births, deaths, immigration, emigration.
- `factions`, `institutions`, `regime_events` — political and institutional state.
- Federation DB tables for cross-world effects, diplomatic relations, cultural diffusion, movements, and strategy events.

## Causality discipline

Aurelia distinguishes three artifacts:

1. **Event sequence** — what happened in tick order.
2. **Causal graph** — which event contributed to which later or same-tick effect.
3. **Narrative chronicle** — human-readable summary generated from the data.

The graph is primary. Narrative is downstream.

## Cloudflare persistence

Cloudflare is a durability and publication layer, not the hot simulation loop. The simulation runs locally/offline into SQLite, then `aurelia_cf_pusher.py` performs bulk ingestion. This avoids per-tick HTTP latency and preserves reproducible run artifacts.

Current ingestion persists world registration, yearly snapshots, discoveries, great persons, and chronicles. Phase 11 extends ingestion to raw causal events, edges, movements, diffusion, diplomacy, and run manifests.

## Verification gates

A credible Aurelia run should pass:

1. Unit suite: `PYTHONPATH=. python -m pytest tests -q`
2. Causal smoke: short deterministic `causal_run.py` execution.
3. Run-quality scan: event/edge/movement/discovery/federation richness metrics.
4. Cloudflare verification: dashboard counts match bulk-uploaded run artifacts.
