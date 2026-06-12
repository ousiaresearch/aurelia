# Aurelia Roadmap

## Phase 10 — Causal-gap closure

Status: implemented and tested in the canonical development tree.

Phase 10 made dormant causal categories active at runtime:

- innovation and discoveries
- great-person emergence
- ecology/resource stock
- disease pressure
- education and human capital
- urbanization
- inequality, infrastructure, water-security movement
- property rights
- state-capacity type
- repression type
- conflict type
- path dependence
- migration carriers
- cultural diffusion fallback
- foreign strategy
- causal graph edges

## Phase 11 — Observatory and counterfactual proof layer

Status: closed. Public observability, proof tools, report rendering,
quality gates, and counterfactual branches are shipped.

Goal: make Aurelia undeniable as an observable causal system.

### 11.1 Canonical public release

- Merge public README/cover/license/changelog into the real Phase 10 tree.
- Add CI and project metadata.
- Remove runtime artifacts from git.
- Push and tag `v0.1.0-phase10`.

### 11.2 Cloudflare causal ingestion

- Add run manifests.
- Bulk-upload causal events, edges, civilization metrics, cross-world movements, diffusion events, and diplomatic relations.
- Extend dashboard counts so the public data plane shows nonzero causal event/edge state.

### 11.3 Local proof tools

- `scripts/export_causal_graph.py`
- `scripts/explain_event.py`
- `scripts/render_run_report.py`
- `scripts/evaluate_run_quality.py`

### 11.4 Aurelia Observatory

- Public Cloudflare Pages dashboard backed by Worker/D1/R2.
- World cards, timeline, chronicles, graph preview, and run summaries.

### 11.5 Counterfactual branches

- Intervention config format.
- Paired baseline/branch runner.
- Delta report comparing same-seed histories.

## Phase 12 — Calibrated production histories

Status: closed for the 0.1.6 engine-stability boundary; continuing
calibration sweeps are future research work.

- 50-year calibration gates before 200-year production runs.
- Seed sweeps for richness/divergence.
- Quality thresholds for conflict diversity, foreign strategy, institution formation, discovery cadence, movement, and causal edge density.

## Phase 13 — Narrative layer over verified history

Status: active frontier. First target is a deterministic verified
chronicle layer with provenance before any freeform LLM prose.

- Chronicle/prose generation from verified run artifacts.
- First implementation target: [`PHASE13_VERIFIED_CHRONICLES.md`](PHASE13_VERIFIED_CHRONICLES.md) and `scripts/render_verified_chronicles.py`.
- Social-thread extract mode.
- Public reports and media assets generated from real histories, not invented summaries.
