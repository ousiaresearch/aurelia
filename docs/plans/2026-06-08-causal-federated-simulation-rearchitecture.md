# Aurelia Causal Federated Simulation Rearchitecture Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Replace the current minimal speed-run/faction-bypass path with a causal, federated, multi-scale simulation where mundane NPC interactions propagate through meso-level institutions into geopolitical and socioeconomic dynamics, with cross-world causality preserved even when compute is sequential.

**Architecture:** Introduce a deterministic federation tick orchestrator with a shared event ledger, causal graph, delayed effects queue, and world-level state vectors. Each tick has phases: local micro interactions, aggregation into household/workplace/neighborhood signals, institutional response, cross-world federation exchange, delayed causal effects, and yearly reporting. Sequential execution remains allowed for memory, but causality is parallel-by-barrier: all worlds read the same tick-start federation snapshot and publish effects that apply on the next barrier.

**Tech Stack:** Python 3.13, SQLite/WAL per world, coordinator SQLite/D1-compatible schema, Cloudflare Worker/D1/R2 for durable summaries/artifacts, pytest for correctness and calibration tests.

---

## Diagnosis

The latest 200-year Aurelia run completed technically but failed the intended simulation standard:

1. **NPC count was static.** Population was initialized at 12,015/world and stayed there. Birth/death/migration are absent from the speed-run hot path.
2. **Factions formed without consequences.** Faction creation is wired as a direct bypass in `speed_run.py`, but escalation, repression, concession, treaty, sovereignty, violence, economic shock, membership churn, and state response are not part of the actual tick path.
3. **Cross-world causality is fake.** Sequential one-world-at-a-time execution solves OOM but isolates histories. Solara can finish 200 years before Valdris begins, so Valdris cannot react to Solara's refugees, revolutions, trade shocks, discoveries, wars, or policy shifts in the same historical timeline.
4. **Minute interactions do not matter.** Current `_minimal_tick()` advances time and applies random JSON drift. It does not route conversations, trade, workplace conflict, illness, crime, propaganda, kinship, local resource use, or mundane decisions into larger systems.
5. **Cloudflare stores summaries but is not the causal data plane.** The Worker currently receives final/annual snapshots; it does not maintain a federation event stream that future ticks consume.

This is not a calibration problem. It is an architecture problem.

---

## Target Model

Aurelia needs four explicit layers:

1. **Micro layer — NPCs and relationships**
   - Individuals have needs, beliefs, wealth, health, job, household, faction sympathies, social ties, local trust, grievance, fatigue, memory fragments.
   - Each tick samples mundane interactions: work, trade, argument, care, rumor, arrest, worship, illness, debt, migration planning, family formation, breakups, injury, theft, teaching, propaganda exposure.

2. **Meso layer — groups and institutions**
   - Households, workplaces, neighborhoods, temples, councils, guilds, security forces, labs, ports, media nodes, factions.
   - Micro interactions aggregate into signals: prices, unemployment, faction recruitment, strikes, crime, local trust, public health, food stress, rumor velocity, type tension.

3. **Macro layer — country systems**
   - Economy, demography, legitimacy, repression, policy drift, infrastructure, ecology, public health, technological capacity, security, fiscal capacity, inequality.
   - Institutions react: concessions, crackdowns, subsidies, border closures, military deployment, propaganda, recognition of rights, emergency powers.

4. **Federation layer — cross-world causality**
   - Trade, diplomacy, migration/refugees, asylum crises, contagion, ecological spillovers, technology diffusion, ideology diffusion, sanctions, intervention, recognition, federation charter changes.
   - All worlds share a tick-start federation snapshot and publish next-tick effects to a central event ledger.

---

## Core Rule: Sequential Compute, Parallel Causality

Sequential execution is acceptable only if causality is barrier-synchronized.

For each tick `T`:

1. Load federation snapshot `S_T`.
2. For each world, run local tick using only local state + `S_T`.
3. Each world publishes local events and outbound intents to the federation ledger for tick `T`.
4. Coordinator resolves cross-world effects after all worlds complete tick `T`.
5. Effects become `S_{T+1}` and apply to all worlds on the next tick.

This means worlds may compute sequentially, but no world advances to tick `T+1` until all worlds have completed tick `T`.

---

## New Modules

### `src/causal_ledger.py`

Central local module for writing causal events and delayed effects.

Tables:

```sql
CREATE TABLE IF NOT EXISTS causal_events (
    event_id TEXT PRIMARY KEY,
    tick_number INTEGER NOT NULL,
    world_id TEXT NOT NULL,
    layer TEXT NOT NULL,              -- micro|meso|macro|federation
    event_type TEXT NOT NULL,
    actor_ids TEXT DEFAULT '[]',
    target_ids TEXT DEFAULT '[]',
    scope TEXT NOT NULL,              -- npc|household|location|faction|country|federation
    magnitude REAL DEFAULT 0.0,
    valence REAL DEFAULT 0.0,         -- negative..positive
    confidence REAL DEFAULT 1.0,
    payload TEXT DEFAULT '{}',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS delayed_effects (
    effect_id TEXT PRIMARY KEY,
    source_event_id TEXT NOT NULL,
    apply_tick INTEGER NOT NULL,
    target_world_id TEXT NOT NULL,
    target_scope TEXT NOT NULL,
    target_id TEXT,
    effect_type TEXT NOT NULL,
    magnitude REAL DEFAULT 0.0,
    payload TEXT DEFAULT '{}',
    applied INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS causal_edges (
    parent_event_id TEXT NOT NULL,
    child_event_id TEXT NOT NULL,
    relation TEXT NOT NULL,           -- caused|amplified|suppressed|translated_into
    weight REAL DEFAULT 1.0,
    PRIMARY KEY(parent_event_id, child_event_id)
);
```

### `src/federation_orchestrator.py`

Barrier-synchronized tick runner. Replaces one-world-at-a-time historical isolation.

Responsibilities:

- Open persistent connection per world.
- Initialize `federation_state` for tick `T`.
- Run each world for the same tick before any world advances further.
- Resolve outbound effects and queue delayed effects.
- Apply queued effects at the start of each tick.
- Emit per-year report with births, deaths, migrations, factions, conflicts, discoveries, policy shifts, price shocks, epidemics, and diplomacy.

### `src/micro_interactions.py`

Mundane interaction sampler.

Event types:

- `work_success`, `work_failure`, `wage_dispute`, `price_argument`
- `caregiving`, `illness_seen`, `death_in_household`, `birth_in_household`
- `rumor_transmission`, `propaganda_exposure`, `public_insult`, `solidarity_gesture`
- `small_theft`, `security_stop`, `bribe`, `arrest_witnessed`
- `teaching`, `religious_service`, `lab_accident`, `trade_deal`, `migration_plan`

Output: causal events + NPC decision state deltas, not prose.

### `src/meso_aggregator.py`

Rolls up micro events into location/institution/faction signals.

Signals:

- price pressure
- unemployment pressure
- food/water/fuel stress
- public health risk
- neighborhood trust
- faction recruitment pressure
- repression visibility
- rumor velocity
- type tension
- strike probability
- migration pressure

### `src/macro_dynamics.py`

Country-level state transition module.

State vector per world/year/tick:

```json
{
  "population": 12015,
  "births_ytd": 0,
  "deaths_ytd": 0,
  "immigration_ytd": 0,
  "emigration_ytd": 0,
  "gdp_proxy": 0.55,
  "inequality": 0.45,
  "food_security": 0.60,
  "water_security": 0.60,
  "public_health": 0.70,
  "legitimacy": 0.55,
  "repression": 0.30,
  "fiscal_capacity": 0.50,
  "infrastructure": 0.60,
  "border_openness": 0.50,
  "type_tension": 0.30,
  "war_pressure": 0.00
}
```

### `src/demography.py`

Real birth/death/migration mechanics.

Rules:

- Births derive from household pairing, health, security, economic confidence, age band, cultural norms, resource stress.
- Deaths derive from age/health/injury/disease/war/famine/disaster/decommissioning.
- Migration removes or soft-transfers NPCs according to federation policy.
- Every yearly snapshot reports real births/deaths/migrations from event counters, never approximations.

### `src/faction_lifecycle.py`

Factions must have consequences.

Lifecycle:

1. grievance clustering
2. recruitment
3. organization
4. demand publication
5. state response: ignore/concede/repress/co-opt
6. consequences: trust shift, migration, violence, strike, election/council shift, treaty, integration, splintering, sovereignty
7. memory: faction reputation and martyrdom persist

### `src/federation_effects.py`

Cross-world effect resolver.

Outbound intents:

- refugee flow
- asylum crisis
- trade disruption
- sanction
- recognition
- intervention
- ideology diffusion
- disease spread
- technology diffusion
- ecological spillover
- currency shock

Resolution uses adjacency, diplomacy, border policy, trade weights, and source-event magnitude.

---

## Task Plan

### Task 1: Freeze the current run as a baseline fixture

**Objective:** Preserve the current Year 2032 output as a known-bad baseline for regression comparison.

**Files:**
- Create: `tests/fixtures/aurelia_static_2032_summary.json`
- Modify: none

**Steps:**

1. Extract summary from `/tmp/aurelia-seq-run/output/*.db`.
2. Store per-world population, factions, chronicles, current_year.
3. Add a note: static population and faction-without-consequence are expected baseline failures.
4. Commit.

Verification:

```bash
python3 -m json.tool tests/fixtures/aurelia_static_2032_summary.json
```

### Task 2: Add causal ledger schema to world initialization

**Objective:** Every world DB can store causal events, delayed effects, and parent-child causal edges.

**Files:**
- Modify: `src_template/world_state.py`
- Modify: `~/.openclaw/workspace/aurelia-colab/src/world_state.py`
- Test: `tests/test_causal_ledger_schema.py`

Verification:

```bash
pytest tests/test_causal_ledger_schema.py -v
```

Expected: creates all three tables and indexes.

### Task 3: Implement `causal_ledger.py`

**Objective:** Provide typed helper functions for event insertion and delayed effect scheduling.

**Files:**
- Create: `src_template/causal_ledger.py`
- Create/copy: `~/.openclaw/workspace/aurelia-colab/src/causal_ledger.py`
- Test: `tests/test_causal_ledger.py`

Required API:

```python
def emit_event(db, *, tick_number, world_id, layer, event_type, scope, actor_ids=None,
               target_ids=None, magnitude=0.0, valence=0.0, payload=None) -> str: ...

def schedule_effect(db, *, source_event_id, apply_tick, target_world_id, target_scope,
                    effect_type, target_id=None, magnitude=0.0, payload=None) -> str: ...

def link_events(db, parent_event_id, child_event_id, relation, weight=1.0): ...
```

### Task 4: Implement micro interaction sampling

**Objective:** Produce mundane NPC-level events that update decision state.

**Files:**
- Create: `src_template/micro_interactions.py`
- Test: `tests/test_micro_interactions.py`

Constraints:

- Sample bounded population slice per tick (`max_interactions=500` default).
- Every event must either modify an NPC state variable or schedule a delayed effect.
- No prose generation inside this module.

Acceptance tests:

- Running 20 ticks changes satisfaction/security/economic_stability for sampled NPCs.
- At least 5 event types appear in a 100-tick smoke test.
- Same seed produces deterministic event counts.

### Task 5: Implement meso aggregation

**Objective:** Convert micro events into location/institution/faction signals.

**Files:**
- Create: `src_template/meso_aggregator.py`
- Test: `tests/test_meso_aggregator.py`

Required outputs:

- `location_signals`
- `institution_signals`
- `faction_pressure_signals`
- `market_signals`

### Task 6: Implement real demography

**Objective:** NPC count must change from actual births, deaths, and migrations.

**Files:**
- Create: `src_template/demography.py`
- Modify: `src_template/world_state.py` for `demographic_events` table
- Test: `tests/test_demography.py`

Rules:

- Birth creates a new NPC row + decision state row + household relation.
- Death marks existing NPC inactive/deceased and records cause.
- Migration records source/target and changes country/nationality accounting.
- Yearly report derives from `demographic_events` only.

Acceptance:

```bash
pytest tests/test_demography.py -v
```

Must prove population can rise and fall under different scenarios.

### Task 7: Replace faction bypass with faction lifecycle

**Objective:** Factions affect and are affected by the world.

**Files:**
- Create: `src_template/faction_lifecycle.py`
- Modify: `src_template/faction_engine.py`
- Test: `tests/test_faction_lifecycle.py`

Acceptance:

- A faction with unmet demands can escalate.
- A conceded faction can integrate.
- Repression can reduce recruitment short-term but increase martyrdom/restlessness.
- Factions can split or merge.
- Faction activity changes macro legitimacy/security/economy.

### Task 8: Implement macro dynamics state vector

**Objective:** Country-level economy/governance/public-health/resource dynamics evolve and feed back to NPCs.

**Files:**
- Create: `src_template/macro_dynamics.py`
- Modify: `src_template/world_state.py` for `macro_state` table
- Test: `tests/test_macro_dynamics.py`

Acceptance:

- A food shock increases price pressure and lowers satisfaction.
- High legitimacy lowers recruitment pressure.
- Repression improves short-term security but worsens trust/restlessness.

### Task 9: Implement federation barrier orchestrator

**Objective:** Restore cross-world causality while keeping memory-safe sequential execution.

**Files:**
- Create: `src_template/federation_orchestrator.py`
- Modify: `colab/speed_run.py` or create `colab/causal_run.py`
- Test: `tests/test_federation_barrier.py`

Algorithm:

```python
for tick in range(1, total_ticks + 1):
    federation_snapshot = coordinator.load_snapshot(tick)
    local_outputs = []
    for world in worlds:
        local_outputs.append(run_world_tick(world, tick, federation_snapshot))
    coordinator.resolve_tick(tick, local_outputs)
    coordinator.apply_effects_for_tick(tick + 1)
```

Acceptance:

- Solara event at tick 10 can affect Valdris at tick 11.
- Valdris cannot react to Solara's tick 20 event at tick 10.
- Sequential processing order does not change final results for same random seed.

### Task 10: Implement cross-world hard/soft migration

**Objective:** Migration must affect both source and target worlds.

**Files:**
- Modify: `src_template/cross_world.py`
- Test: `tests/test_cross_world_migration.py`

Modes:

- Soft migration: original NPC remains in source DB but counted under target nationality.
- Hard migration: NPC profile transferred or mirrored into target DB with source reference.

Acceptance:

- Source population decreases or emigrant counter increases.
- Target immigrant counter increases.
- Diplomatic asylum event schedules relation delta.

### Task 11: Add yearly causal report

**Objective:** Yearly output must show the user's required changes: births, deaths, species, factions, discoveries, migrations, and the causal chain that produced them.

**Files:**
- Create: `src_template/yearly_report.py`
- Modify: `aurelia_cf_pusher.py` to push causal yearly summaries
- Test: `tests/test_yearly_report.py`

Report sections:

- demographics
- species/type breakdown
- factions formed/escalated/integrated/dissolved
- conflicts/peace treaties
- discoveries/great persons
- migrations/refugees/asylum
- economy/resources/public health
- diplomacy/federation effects
- top causal chains

### Task 12: Add calibration tests for non-static worlds

**Objective:** Prevent another run where 200 years pass with static population and inert factions.

**Files:**
- Create: `tests/test_200_year_calibration.py`

Acceptance on a fast 20-year, 1,000-NPC smoke run:

- population changes by at least ±1%
- births > 0 OR deaths > 0
- at least one faction consequence event occurs if factions form
- at least one cross-world effect is queued/applied
- yearly report has non-empty causal chains

### Task 13: Replace current `aurelia-seq-run.py` with causal runner wrapper

**Objective:** Production runs use barrier causality, not isolated sequential worlds.

**Files:**
- Modify: `~/.hermes/scripts/aurelia-seq-run.py`
- Create: `~/.hermes/scripts/aurelia-causal-run.py`
- Modify: `aurelia-sequential-runner` skill after implementation

Acceptance:

- Runner processes one tick across all worlds before advancing any world to the next tick.
- Memory remains bounded.
- Completion pushes D1/R2 as before.

---

## Implementation Order

1. Ledger + schema.
2. Micro interactions.
3. Demography.
4. Meso aggregation.
5. Macro state vector.
6. Faction lifecycle.
7. Federation barrier orchestrator.
8. Cross-world effect resolver.
9. Yearly causal report.
10. Cloudflare ingestion expansion.
11. Calibration tests.
12. Production runner replacement.

---

## Non-Negotiable Acceptance Criteria

A future successful run must show:

- NPC count changes for principled reasons.
- Births and deaths are real event records, not approximations.
- Factions have consequences: concession, repression, escalation, peace, integration, fracture, sovereignty, or decline.
- Mundane actions aggregate into macro dynamics.
- Cross-world effects occur under barrier-synchronized causality.
- Sequential execution order does not alter results for a fixed seed.
- The yearly report explains causal chains, not just counts.
- Cloudflare receives not only final snapshots but causal summaries/artifacts.

---

## First Milestone

Build a 20-year, 1,000-NPC, 5-world causal smoke run that finishes in under 10 minutes and proves:

```text
population_delta != 0
births + deaths > 0
faction_consequence_events > 0
cross_world_effects_applied > 0
yearly_causal_chains > 0
```

Only after this passes should we run the 12K NPC / 200-year production scale again.
