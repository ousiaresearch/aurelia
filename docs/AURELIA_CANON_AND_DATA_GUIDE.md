# Aurelia Canon and Data Guide

This is the canon bridge for Aurelia Phase 12. It maps each major concept across lore/wiki files, runtime code, SQLite tables, HuggingFace datasets, Cloudflare public surfaces, and proof artifacts.

Do not treat this as wiki reconciliation. This guide records the bridge and flags stale/split concepts for review; it does not edit or supersede the Desktop wiki by itself.

## How to read this guide

- If a concept is **SIMULATED**, it has active runtime and data surfaces.
- If a concept is **PARTIAL**, it exists but lacks a complete bridge across all layers.
- If a concept is **PLANNED**, it is a desired canonical mechanic but still needs implementation/proof.
- If a concept is **STALE** or **ARCHIVED**, review it before using it in public copy.

## Status summary

- **SIMULATED**: 25 — Active in runtime code and represented in data artifacts.
- **PARTIAL**: 7 — Present, but not yet fully bridged across lore, simulation, and data.
- **PLANNED**: 1 — Canonical direction, but not yet a sufficient runtime/data surface.
- **STALE**: 1 — Older claim that should not be treated as current public canon without review.
- **ARCHIVED**: 1 — Historical/internal material retained for context, not current public surface.

## Dataset index

- `OusiaResearch/aurelia-causal-events`: `causal_event`, `conflict_type`, `counterfactual_branch`, `cross_world_effect`, `discovery`, `disease_pressure`, `faction`, `great_person`, `huggingface_export`, `institution`, `migration`, `npc`, `regime`, `resource_stock`, `run_quality`, `world`, `yearly_report`
- `OusiaResearch/aurelia-civilization-metrics`: `conflict_type`, `counterfactual_branch`, `density_diversification`, `disease_pressure`, `education`, `faction`, `huggingface_export`, `institution`, `property_rights`, `regime`, `repression_type`, `resource_stock`, `run_quality`, `state_capacity_type`, `urbanization`, `world`, `yearly_report`
- `OusiaResearch/aurelia-federation-causal`: `causal_edge`, `causal_event`, `cross_world_effect`, `cultural_diffusion`, `density_diversification`, `diplomacy`, `huggingface_export`, `migration`, `run_quality`
- `OusiaResearch/aurelia-npc-population`: `counterfactual_branch`, `density_diversification`, `glim`, `glim_anomaly`, `huggingface_export`, `human`, `migration`, `npc`, `thren`, `vorn`, `world`

## Code index

- `aurelia_cf_pusher.py`: `cloudflare_observatory`
- `aurelia_diplomacy.py`: `diplomacy`
- `aurelia_factory.py`: `world`
- `populate_npcs.py`: `glim`, `glim_anomaly`, `human`, `npc`, `thren`, `vorn`
- `scripts/aurelia_run_inspect.py`: `run_quality`
- `scripts/compare_runs.py`: `counterfactual_branch`
- `scripts/evaluate_run_quality.py`: `run_quality`
- `scripts/explain_event.py`: `causal_edge`
- `scripts/export_causal_graph.py`: `causal_edge`
- `scripts/export_hf_dataset.py`: `causal_event`, `huggingface_export`
- `scripts/render_hf_readme.py`: `huggingface_export`
- `scripts/render_run_report.py`: `yearly_report`
- `scripts/run_counterfactual.py`: `counterfactual_branch`
- `src_template/causal_ledger.py`: `causal_edge`, `causal_event`
- `src_template/counterfactuals.py`: `counterfactual_branch`
- `src_template/cultural_diffusion.py`: `cultural_diffusion`
- `src_template/discovery.py`: `discovery`
- `src_template/ecology.py`: `disease_pressure`, `resource_stock`
- `src_template/economy.py`: `resource_stock`
- `src_template/escalation_ladder.py`: `conflict_type`
- `src_template/factions.py`: `faction`
- `src_template/federation_diplomacy.py`: `diplomacy`
- `src_template/federation_effects.py`: `cross_world_effect`, `migration`
- `src_template/federation_orchestrator.py`: `cross_world_effect`, `cultural_diffusion`, `density_diversification`, `diplomacy`, `migration`, `world`
- `src_template/great_persons.py`: `great_person`
- `src_template/institutions.py`: `institution`, `property_rights`, `state_capacity_type`
- `src_template/macro_dynamics.py`: `education`, `urbanization`
- `src_template/npc_ai.py`: `npc`
- `src_template/npc_generation.py`: `glim`, `glim_anomaly`, `human`, `npc`, `thren`, `vorn`
- `src_template/phase10_dynamics.py`: `causal_event`, `conflict_type`, `density_diversification`, `discovery`, `disease_pressure`, `education`, `faction`, `great_person`, `institution`, `migration`, `property_rights`, `regime`, `repression_type`, `resource_stock`, `state_capacity_type`, `urbanization`
- `src_template/regime.py`: `regime`, `repression_type`
- `src_template/world_state.py`: `npc`, `world`
- `src_template/yearly_report.py`: `faction`, `yearly_report`
- `~/.hermes/profiles/palantir/cf-worker/`: `cloudflare_observatory`

## Concept index

### `causal_edge` — Causal edge [SIMULATED]

Directed relation between parent and child causal events.

**Wiki paths:**
  - `~/Desktop/Aurelia/simulation/simulation-architecture.md`

**Runtime/code paths:**
  - `src_template/causal_ledger.py`
  - `scripts/export_causal_graph.py`
  - `scripts/explain_event.py`

**SQLite / storage tables:**
  - `causal_edges`
  - `federation.causal_edges`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-federation-causal`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/examples/phase11-solara-graph.json`
  - `docs/reports/phase11-runs-comparison.md`

### `causal_event` — Causal event [SIMULATED]

First-class event node written by micro, meso, macro, and federation systems.

**Wiki paths:**
  - `~/Desktop/Aurelia/simulation/simulation-architecture.md`

**Runtime/code paths:**
  - `src_template/causal_ledger.py`
  - `src_template/phase10_dynamics.py`
  - `scripts/export_hf_dataset.py`

**SQLite / storage tables:**
  - `causal_events`
  - `federation.causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-causal-events`
  - `OusiaResearch/aurelia-federation-causal`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/ARCHITECTURE.md`
  - `docs/reports/phase11-runs-comparison.md`

### `conflict_type` — Conflict type [SIMULATED]

Categorical conflict state such as latent, insurgency, or civil war.

**Wiki paths:**
  - `~/Desktop/Aurelia/warfare.md`
  - `~/Desktop/Aurelia/war-and-military/overview.md`

**Runtime/code paths:**
  - `src_template/escalation_ladder.py`
  - `src_template/phase10_dynamics.py`

**SQLite / storage tables:**
  - `civilization_metrics`
  - `causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`
  - `OusiaResearch/aurelia-causal-events`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `counterfactual_branch` — Counterfactual branch [SIMULATED]

Deterministic branch over a baseline run where an intervention is applied and deltas are compared.

**Wiki paths:**
  - None

**Runtime/code paths:**
  - `src_template/counterfactuals.py`
  - `scripts/run_counterfactual.py`
  - `scripts/compare_runs.py`

**SQLite / storage tables:**
  - `causal_events`
  - `civilization_metrics`
  - `agents`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-causal-events`
  - `OusiaResearch/aurelia-civilization-metrics`
  - `OusiaResearch/aurelia-npc-population`

**Cloudflare/public surface:**
  - None

**Proof artifacts:**
  - `configs/interventions/solara_federation_aid_early.json`
  - `tests/test_counterfactuals.py`

### `cross_world_effect` — Cross-world effect [SIMULATED]

Scheduled/imported federation-level effect that carries causality between worlds.

**Wiki paths:**
  - `~/Desktop/Aurelia/simulation/event-triggers.md`

**Runtime/code paths:**
  - `src_template/federation_effects.py`
  - `src_template/federation_orchestrator.py`

**SQLite / storage tables:**
  - `federation.causal_events`
  - `federation.causal_edges`
  - `federation.cross_world_movements`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-federation-causal`
  - `OusiaResearch/aurelia-causal-events`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`
  - `/public/aurelia/runs`

**Proof artifacts:**
  - `docs/ARCHITECTURE.md`
  - `docs/reports/phase11-runs-comparison.md`

### `cultural_diffusion` — Cultural diffusion [SIMULATED]

Cross-world adoption/resistance of cultural traits and norms.

**Wiki paths:**
  - `~/Desktop/Aurelia/arts-and-culture/literature-and-story.md`

**Runtime/code paths:**
  - `src_template/cultural_diffusion.py`
  - `src_template/federation_orchestrator.py`

**SQLite / storage tables:**
  - `federation.diffusion_events`
  - `federation.causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-federation-causal`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `density_diversification` — Density diversification [SIMULATED]

Migration-balancing knob that reduces cross-world population concentration by moving pressure toward underpopulated worlds.

**Wiki paths:**
  - None

**Runtime/code paths:**
  - `src_template/federation_orchestrator.py`
  - `src_template/phase10_dynamics.py`

**SQLite / storage tables:**
  - `federation.cross_world_movements`
  - `agents`
  - `civilization_metrics`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`
  - `OusiaResearch/aurelia-npc-population`
  - `OusiaResearch/aurelia-federation-causal`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`
  - `/public/aurelia/runs`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`
  - `tests/test_density_diversification.py`

**Notes:**
  - Phase 11 density run reduced population coefficient of variation from 0.674 to 0.006.

### `diplomacy` — Diplomacy [SIMULATED]

Cross-world relations, strategies, treaties, and trust accumulation.

**Wiki paths:**
  - `~/Desktop/Aurelia/diplomatic-matrix.md`

**Runtime/code paths:**
  - `aurelia_diplomacy.py`
  - `src_template/federation_diplomacy.py`
  - `src_template/federation_orchestrator.py`

**SQLite / storage tables:**
  - `federation.diplomatic_relations`
  - `federation.causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-federation-causal`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/diplomatic-matrix.md`
  - `docs/reports/phase11-runs-comparison.md`

### `discovery` — Discovery [SIMULATED]

Innovation or breakthrough event that changes local or cross-world dynamics.

**Wiki paths:**
  - `~/Desktop/Aurelia/technology.md`

**Runtime/code paths:**
  - `src_template/discovery.py`
  - `src_template/phase10_dynamics.py`

**SQLite / storage tables:**
  - `discoveries`
  - `causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-causal-events`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `disease_pressure` — Disease pressure [SIMULATED]

Macro health/ecology pressure that evolves by world and affects civilization trajectories.

**Wiki paths:**
  - `~/Desktop/Aurelia/medicine/disease.md`
  - `~/Desktop/Aurelia/medicine-comprehensive.md`

**Runtime/code paths:**
  - `src_template/phase10_dynamics.py`
  - `src_template/ecology.py`

**SQLite / storage tables:**
  - `civilization_metrics`
  - `causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`
  - `OusiaResearch/aurelia-causal-events`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `education` — Education [SIMULATED]

Macro civilization indicator updated by Phase 10 dynamics and exported as a time-series field.

**Wiki paths:**
  - `~/Desktop/Aurelia/education.md`
  - `~/Desktop/Aurelia/education/overview.md`

**Runtime/code paths:**
  - `src_template/phase10_dynamics.py`
  - `src_template/macro_dynamics.py`

**SQLite / storage tables:**
  - `civilization_metrics`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `faction` — Faction [SIMULATED]

Organized political/social group formed from grievances and recorded in world tables and reports.

**Wiki paths:**
  - `~/Desktop/Aurelia/factions/overview.md`

**Runtime/code paths:**
  - `src_template/factions.py`
  - `src_template/phase10_dynamics.py`
  - `src_template/yearly_report.py`

**SQLite / storage tables:**
  - `factions`
  - `causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-causal-events`
  - `OusiaResearch/aurelia-civilization-metrics`

**Cloudflare/public surface:**
  - `/public/aurelia/runs`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

**Notes:**
  - Phase 12 quality gates should warn when factions remain zero across long runs.

### `great_person` — Great person [SIMULATED]

Emergent historical actor linked to discontinuous breakthroughs or institutional changes.

**Wiki paths:**
  - `~/Desktop/Aurelia/mythology/legendary-figures.md`

**Runtime/code paths:**
  - `src_template/great_persons.py`
  - `src_template/phase10_dynamics.py`

**SQLite / storage tables:**
  - `great_persons`
  - `causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-causal-events`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `huggingface_export` — HuggingFace export [SIMULATED]

Offline Parquet export pipeline that publishes Aurelia run artifacts as four research datasets.

**Wiki paths:**
  - None

**Runtime/code paths:**
  - `scripts/export_hf_dataset.py`
  - `scripts/render_hf_readme.py`

**SQLite / storage tables:**
  - `causal_events`
  - `causal_edges`
  - `civilization_metrics`
  - `agents`
  - `federation.causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-causal-events`
  - `OusiaResearch/aurelia-civilization-metrics`
  - `OusiaResearch/aurelia-federation-causal`
  - `OusiaResearch/aurelia-npc-population`

**Cloudflare/public surface:**
  - None

**Proof artifacts:**
  - `docs/HUGGINGFACE_PUBLISH.md`
  - `tests/test_hf_export.py`

### `institution` — Institution [SIMULATED]

Durable governance/social structure affecting state capacity, property rights, and macro resilience.

**Wiki paths:**
  - `~/Desktop/Aurelia/governance.md`

**Runtime/code paths:**
  - `src_template/institutions.py`
  - `src_template/phase10_dynamics.py`

**SQLite / storage tables:**
  - `institutions`
  - `civilization_metrics`
  - `causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`
  - `OusiaResearch/aurelia-causal-events`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/analysis/2026-06-08-aurelia-causal-gaps-deep-dive.md`

### `migration` — Migration [SIMULATED]

Cross-world movement of NPCs/populations caused by pressure, opportunity, and density-balancing dynamics.

**Wiki paths:**
  - `~/Desktop/Aurelia/geography/locations.md`

**Runtime/code paths:**
  - `src_template/phase10_dynamics.py`
  - `src_template/federation_orchestrator.py`
  - `src_template/federation_effects.py`

**SQLite / storage tables:**
  - `federation.cross_world_movements`
  - `agents`
  - `causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-federation-causal`
  - `OusiaResearch/aurelia-npc-population`
  - `OusiaResearch/aurelia-causal-events`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`
  - `/public/aurelia/runs`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `npc` — NPC [SIMULATED]

Procedural inhabitant tracked through agent rows, events, movement, deaths, and exported population snapshots.

**Wiki paths:**
  - `~/Desktop/Aurelia/simulation/npc-registry.md`
  - `~/Desktop/Aurelia/simulation/simulation-architecture.md`

**Runtime/code paths:**
  - `populate_npcs.py`
  - `src_template/npc_generation.py`
  - `src_template/npc_ai.py`
  - `src_template/world_state.py`

**SQLite / storage tables:**
  - `agents`
  - `demographic_events`
  - `causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-npc-population`
  - `OusiaResearch/aurelia-causal-events`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`
  - `/public/aurelia/runs`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `property_rights` — Property rights [SIMULATED]

Macro institutional indicator used to model economic security and state/citizen relations.

**Wiki paths:**
  - `~/Desktop/Aurelia/governance.md`
  - `~/Desktop/Aurelia/crime-and-legal/legal-systems.md`

**Runtime/code paths:**
  - `src_template/phase10_dynamics.py`
  - `src_template/institutions.py`

**SQLite / storage tables:**
  - `civilization_metrics`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `regime` — Regime [SIMULATED]

Political regime or transition path tracked through regime events, institutions, and macro state variables.

**Wiki paths:**
  - `~/Desktop/Aurelia/governance.md`

**Runtime/code paths:**
  - `src_template/regime.py`
  - `src_template/phase10_dynamics.py`

**SQLite / storage tables:**
  - `regime_events`
  - `civilization_metrics`
  - `causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`
  - `OusiaResearch/aurelia-causal-events`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/plans/2026-06-08-phase9-positive-sum-dynamics.md`

### `repression_type` — Repression type [SIMULATED]

Categorical coercion/control mode exported as part of civilization metrics.

**Wiki paths:**
  - `~/Desktop/Aurelia/governance.md`
  - `~/Desktop/Aurelia/crime-and-legal/crime-and-punishment.md`

**Runtime/code paths:**
  - `src_template/phase10_dynamics.py`
  - `src_template/regime.py`

**SQLite / storage tables:**
  - `civilization_metrics`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `resource_stock` — Resource stock [SIMULATED]

Aggregate resource availability and ecological/economic substrate for macro dynamics.

**Wiki paths:**
  - `~/Desktop/Aurelia/trade-economy.md`
  - `~/Desktop/Aurelia/flora-agriculture.md`

**Runtime/code paths:**
  - `src_template/phase10_dynamics.py`
  - `src_template/economy.py`
  - `src_template/ecology.py`

**SQLite / storage tables:**
  - `civilization_metrics`
  - `resources`
  - `causal_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`
  - `OusiaResearch/aurelia-causal-events`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `state_capacity_type` — State capacity type [SIMULATED]

Categorical government capacity state such as patrimonial, prebendal, or bureaucratic.

**Wiki paths:**
  - `~/Desktop/Aurelia/governance.md`

**Runtime/code paths:**
  - `src_template/phase10_dynamics.py`
  - `src_template/institutions.py`

**SQLite / storage tables:**
  - `civilization_metrics`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `urbanization` — Urbanization [SIMULATED]

Macro civilization indicator representing urban share/settlement concentration over ticks.

**Wiki paths:**
  - `~/Desktop/Aurelia/geography/locations.md`

**Runtime/code paths:**
  - `src_template/phase10_dynamics.py`
  - `src_template/macro_dynamics.py`

**SQLite / storage tables:**
  - `civilization_metrics`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`

### `world` — World [SIMULATED]

One of Aurelia's five abstract simulation arenas: arkos, mirithane, solara, valdris, or verge.

**Wiki paths:**
  - `~/Desktop/Aurelia/README.md`
  - `~/Desktop/Aurelia/geography/overview.md`

**Runtime/code paths:**
  - `aurelia_factory.py`
  - `src_template/world_state.py`
  - `src_template/federation_orchestrator.py`

**SQLite / storage tables:**
  - `per_world.sqlite.world_state`
  - `per_world.sqlite.civilization_metrics`
  - `federation.runs`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-civilization-metrics`
  - `OusiaResearch/aurelia-causal-events`
  - `OusiaResearch/aurelia-npc-population`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`
  - `/public/aurelia/runs`

**Proof artifacts:**
  - `docs/reports/phase11-runs-comparison.md`
  - `docs/ARCHITECTURE.md`

**Notes:**
  - Public repo now frames worlds as abstract topologies rather than real-world maps.

### `yearly_report` — Yearly report [SIMULATED]

Human-readable yearly chronicle generated from run data and summary artifacts.

**Wiki paths:**
  - `~/Desktop/Aurelia/simulation/simulation-architecture.md`

**Runtime/code paths:**
  - `src_template/yearly_report.py`
  - `scripts/render_run_report.py`

**SQLite / storage tables:**
  - `causal_events`
  - `civilization_metrics`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-causal-events`
  - `OusiaResearch/aurelia-civilization-metrics`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/reports/phase11-100y-report.md`
  - `docs/reports/phase11-200y-report.md`
  - `docs/reports/phase11-density-100y-report.md`

### `cloudflare_observatory` — Cloudflare observatory [PARTIAL]

Public dashboard and JSON plane exposing snapshots, counts, causal rows, and run metadata; long-run completeness is limited by D1 capacity.

**Wiki paths:**
  - None

**Runtime/code paths:**
  - `aurelia_cf_pusher.py`
  - `~/.hermes/profiles/palantir/cf-worker/`

**SQLite / storage tables:**
  - `D1.aurelia_worlds`
  - `D1.aurelia_runs`
  - `D1.aurelia_causal_events`
  - `D1.aurelia_causal_edges`

**HuggingFace datasets:**
  - None

**Cloudflare/public surface:**
  - `/public/aurelia/observatory`
  - `/public/aurelia/dashboard`
  - `/public/aurelia/runs`

**Proof artifacts:**
  - `docs/DEMO.md`
  - `docs/ARCHITECTURE.md`

**Notes:**
  - Public Worker requires a browser-like User-Agent for anonymous fetches.

### `glim` — Glim [PARTIAL]

Mass-produced autonomous units from the lore; population identity exists, but awakening/anomaly dynamics remain partial/planned.

**Wiki paths:**
  - `~/Desktop/Aurelia/types/glim.md`
  - `~/Desktop/Aurelia/lore/glim-narrative.md`

**Runtime/code paths:**
  - `populate_npcs.py`
  - `src_template/npc_generation.py`

**SQLite / storage tables:**
  - `agents`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-npc-population`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/AURELIA_CANON_AND_DATA_GUIDE.md`

### `human` — Human [PARTIAL]

Legacy/species identity from the wiki and NPC generator; present in population records but not yet a central Phase 11 analytic axis.

**Wiki paths:**
  - `~/Desktop/Aurelia/types/human.md`
  - `~/Desktop/Aurelia/types/design-sheets/human.md`

**Runtime/code paths:**
  - `populate_npcs.py`
  - `src_template/npc_generation.py`

**SQLite / storage tables:**
  - `agents`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-npc-population`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/AURELIA_CANON_AND_DATA_GUIDE.md`

### `public_branding` — Public branding [PARTIAL]

Ousia Research / Risomorphism / Nous-v9-derived public presentation layer for posts, promo images, and dataset launch materials.

**Wiki paths:**
  - `~/Desktop/Aurelia/media/media-kit.md`

**Runtime/code paths:**
  - None

**SQLite / storage tables:**
  - None

**HuggingFace datasets:**
  - None

**Cloudflare/public surface:**
  - None

**Proof artifacts:**
  - `docs/social/aurelia-hf-dataset-posts.md`
  - `docs/assets/hf-promo/README.md`
  - `docs/assets/hf-promo-v2/README.md`

### `run_quality` — Run quality evaluation [PARTIAL]

Scoring layer for causal, civilization, federation, and narrative richness; currently needs stricter pathology gates.

**Wiki paths:**
  - None

**Runtime/code paths:**
  - `scripts/evaluate_run_quality.py`
  - `scripts/aurelia_run_inspect.py`

**SQLite / storage tables:**
  - `causal_events`
  - `causal_edges`
  - `civilization_metrics`
  - `federation.cross_world_movements`
  - `federation.diffusion_events`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-causal-events`
  - `OusiaResearch/aurelia-civilization-metrics`
  - `OusiaResearch/aurelia-federation-causal`

**Cloudflare/public surface:**
  - None

**Proof artifacts:**
  - `docs/reports/phase11-100y-quality.json`
  - `docs/reports/phase11-200y-quality.json`
  - `docs/reports/phase11-density-100y-quality.json`

**Notes:**
  - Phase 12 should prevent perfect scores on pathological runs.

### `thren` — Thren [PARTIAL]

Bio-synthetic people from the lore; represented in NPC generation/population but not yet exposed as a dedicated research slice.

**Wiki paths:**
  - `~/Desktop/Aurelia/types/thren.md`
  - `~/Desktop/Aurelia/types/design-sheets/thren.md`

**Runtime/code paths:**
  - `populate_npcs.py`
  - `src_template/npc_generation.py`

**SQLite / storage tables:**
  - `agents`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-npc-population`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/AURELIA_CANON_AND_DATA_GUIDE.md`

### `vorn` — Vorn [PARTIAL]

Mechanical people from the lore; represented in NPC generation/population but not yet a full causal analysis dimension.

**Wiki paths:**
  - `~/Desktop/Aurelia/types/vorn.md`
  - `~/Desktop/Aurelia/types/design-sheets/vorn.md`

**Runtime/code paths:**
  - `populate_npcs.py`
  - `src_template/npc_generation.py`

**SQLite / storage tables:**
  - `agents`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-npc-population`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/AURELIA_CANON_AND_DATA_GUIDE.md`

### `glim_anomaly` — Glim anomaly / awakening [PLANNED]

Central philosophical lore mechanic for Glims showing curiosity or awakening; not yet sufficiently represented as a Phase 11 causal mechanism.

**Wiki paths:**
  - `~/Desktop/Aurelia/lore/glim-narrative.md`
  - `~/Desktop/Aurelia/public/faq.md`

**Runtime/code paths:**
  - `populate_npcs.py`
  - `src_template/npc_generation.py`

**SQLite / storage tables:**
  - `agents`

**HuggingFace datasets:**
  - `OusiaResearch/aurelia-npc-population`

**Cloudflare/public surface:**
  - `/public/aurelia/dashboard`

**Proof artifacts:**
  - `docs/plans/2026-06-10-aurelia-gap-closure-plan.md`

**Notes:**
  - Treat as planned/partial until anomaly events become causal rows and quality-gated outputs.

### `single_landmass_old_canon` — Single-landmass old canon [STALE]

Older public/wiki framing that described Aurelia as a single landmass partitioned into five countries; current public repo emphasizes abstract worlds/topologies.

**Wiki paths:**
  - `~/Desktop/Aurelia/README.md`
  - `~/Desktop/Aurelia/media/media-kit.md`

**Runtime/code paths:**
  - None

**SQLite / storage tables:**
  - None

**HuggingFace datasets:**
  - None

**Cloudflare/public surface:**
  - None

**Proof artifacts:**
  - `docs/plans/2026-06-10-aurelia-gap-closure-plan.md`

**Notes:**
  - Do not resolve without wiki reconciliation review.

### `ttrpg_assets_old_canon` — TTRPG-adjacent old canon assets [ARCHIVED]

Older playable/adventure/equipment docs that should remain historical/internal unless the user explicitly asks for TTRPG content.

**Wiki paths:**
  - `~/Desktop/Aurelia/playable-types.md`
  - `~/Desktop/Aurelia/adventure-hooks.md`
  - `~/Desktop/Aurelia/equipment.md`

**Runtime/code paths:**
  - None

**SQLite / storage tables:**
  - None

**HuggingFace datasets:**
  - None

**Cloudflare/public surface:**
  - None

**Proof artifacts:**
  - `docs/plans/2026-06-10-aurelia-gap-closure-plan.md`

**Notes:**
  - Mark for review only; do not edit Desktop wiki in this canon-bridge pass.
