# Phase 9 Positive-Sum Dynamics Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Break Aurelia's single-attractor collapse basin by adding mechanisms that create value, build institutions, enable recovery from collapse, and produce divergent political outcomes — not just varieties of civil conflict.

**Diagnosis from the Phase 8 50-year run:** The simulation has no way to create value. Every tick either shuffles existing value or destroys it. GDP hit zero in all five worlds by year 50. Recovery only corrects small deviations from baseline — once a world crashes through the floor, there's no ladder back up. Constructive faction outcomes (integration, legalization, coalition) accounted for only 36 of 262 resolution events (13.7%). The federation spreads problems but not solutions.

**Architecture:** Keep the Phase 7-8 barrier-synchronized causal runner. Add five positive-sum layers: value creation through capital/innovation, durable institutions that outlast founding factions, collapse-recovery pathways, cultural learning across worlds, and federation-level diplomacy/aid that creates mutual gains.

**Tech Stack:** Python stdlib, SQLite, pytest, existing `~/aurelia/src_template/` causal modules, Cloudflare pusher remains bulk-only after run completion.

---

## Acceptance Gates

Before any 200-year production run, a 50-year / 200 NPC-world calibration run must satisfy:

1. **Positive-sum gate**
   - At least 2 of 5 worlds must have GDP above 0.25 at year 50.
   - At least 3 of 5 worlds must show net positive GDP movement in at least one decade (not monotonic decline).
   - Total federation faction outcomes must be at least 30% constructive (integrated + legalized + governing_coalition) across the full run.

2. **Recovery gate**
   - At least one world that fell below GDP 0.10 or legitimacy 0.10 must recover above 0.30 in the same key by year 50.
   - At least one world must experience a regime transition from a collapsed regime (civil_conflict, repressive_regime, authoritarian) to a constructive regime (stable_growth, open_market, welfare_state, managed_pluralism).

3. **Institution gate**
   - At least 3 durable institutions must exist across the federation by year 50.
   - At least one faction must transition through legalized → governing_coalition → institutionalized (three-stage lifecycle).

4. **Learning gate**
   - At least one world must adopt a policy or cultural trait from another world via federation diffusion.
   - Cultural distance between worlds must change meaningfully over 50 years (at least one pair grows more similar, at least one pair grows more different).

5. **Diplomacy gate**
   - At least 2 trade agreements or aid pacts must be active between worlds by year 30.
   - Federation events must include at least 3 distinct diplomacy event types (not just trade_shock and ideology_diffusion).

6. **Continuity gate**
   - No new acceptance gate failures introduced in Phase 8 gates (resilience, divergence, migration, faction outcomes, reporting must all still pass).

---

## Task 1: Capital Accumulation and Economic Growth

**Objective:** Create a persistent capital pool per world that grows from productive activity, enables investment, and decays from war/repression. This is the engine that makes positive-sum outcomes possible.

**Files:**
- Create: `src_template/capital_economy.py`
- Test: `tests/test_phase9_economy.py`

**Design:**

Add a `capital_pool` table per world DB:

```sql
CREATE TABLE IF NOT EXISTS capital_pool (
    world_id TEXT PRIMARY KEY,
    stock REAL NOT NULL DEFAULT 0.5,
    gdp_flow REAL NOT NULL DEFAULT 0.0,
    investment_rate REAL NOT NULL DEFAULT 0.0,
    tech_level REAL NOT NULL DEFAULT 0.1,
    innovation_stock REAL NOT NULL DEFAULT 0.0,
    updated_at REAL NOT NULL
);
```

**Mechanics:**

1. **GDP flow** = work_success count × 0.002 + small_trade count × 0.003 + caregiving count × 0.001 per tick.
2. **Capital stock** accumulates: `stock += gdp_flow × (1.0 - war_pressure × 0.7) × investment_rate`.
3. **Investment rate** driven by legitimacy and fiscal capacity: `investment_rate = legitimacy × 0.6 + fiscal_capacity × 0.4`.
4. **Decay** from war and repression: `stock -= stock × war_pressure × 0.03 per tick`.
5. **Innovation** accumulates from rumor_velocity and productive_confidence events, multiplied by tech_level.
6. **GDP proxy** in macro_state becomes a function of `capital_stock + (innovation_stock × tech_level)` rather than an independent variable.

**Causal ledger:** Emit `capital_formation`, `capital_decay`, `innovation_gain`, `gdp_growth`, `gdp_contraction` events.

**Piggyback on existing micro events:** Work success, small_trade, caregiving, productive_confidence — all already exist at high volume (26K+ per run). We're just counting them as inputs to capital, not inventing new micro behaviors.

**Tests:**
- Capital grows from work_success + trade events.
- Capital decays under high war_pressure.
- Innovation stock increases from rumor_velocity events.
- GDP flow goes negative when capital stock is depleted.
- Two worlds with different profiles diverge in capital accumulation.

**Verification:**
```bash
pytest tests/test_phase9_economy.py -v
```

**Commit:**
```bash
git add src_template/capital_economy.py tests/test_phase9_economy.py
git commit -m "feat: add Phase 9 capital accumulation and economic growth"
```

---

## Task 2: Durable Institutions That Outlast Factions

**Objective:** When factions achieve constructive outcomes (legalized, governing_coalition, victorious), they can crystallize into durable institutions that persist beyond the faction's lifecycle and provide ongoing macro benefits.

**Files:**
- Create: `src_template/institutions.py`
- Test: `tests/test_phase9_institutions.py`

**Design:**

Add an `institutions` table:

```sql
CREATE TABLE IF NOT EXISTS institutions (
    institution_id TEXT PRIMARY KEY,
    world_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    founded_tick INTEGER NOT NULL,
    founding_faction_id TEXT,
    influence REAL NOT NULL DEFAULT 0.1,
    durability REAL NOT NULL DEFAULT 0.5,
    benefits TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    created_at REAL NOT NULL
);
```

**Institution types and their benefits:**

| Type | Trigger | Ongoing benefit |
|------|---------|-----------------|
| `labor_union` | faction_legalized with labor_unrest grievance | +0.003 GDP flow/tick, -0.002 repression/tick |
| `political_party` | faction_governing_coalition | +0.004 legitimacy/tick, +0.002 fiscal_capacity/tick |
| `civil_rights_body` | faction_legalized with repression_visibility grievance | -0.005 repression/tick, +0.003 public_health/tick |
| `trade_guild` | faction_integrated with economic_stress grievance | +0.004 GDP flow/tick, +0.002 border_openness/tick |
| `refugee_council` | faction_integrated with migration_pressure grievance | +0.003 refugee_tolerance, -0.002 type_tension/tick |
| `constitutional_court` | faction_victorious | +0.005 legitimacy/tick, -0.003 repression/tick |

**Lifecycle:**

1. **Formation:** When a faction resolves as legalized/governing_coalition/victorious, roll probability (influenced by legitimacy, fiscal_capacity). On success, create institution row.
2. **Persistence:** Institutions have `durability` that decays from war_pressure and repression. If durability hits 0, institution dissolves.
3. **Reinforcement:** If another faction of the same grievance type legalizes, existing institution durability increases.
4. **Benefits:** Each tick, active institutions apply their benefits to macro_state deltas.
5. **Cross-world:** Institutions can be "observed" by other worlds (via federation diffusion, see Task 4).

**Causal ledger events:** `institution_founded`, `institution_reinforced`, `institution_dissolved`, `institution_benefit_applied`.

**Tests:**
- Legalized faction spawns institution on favorable roll.
- Institution applies ongoing macro benefits.
- Institution dissolves under sustained war pressure.
- Second faction reinforces existing institution.
- Governing_coalition faction spawns political_party.

**Verification:**
```bash
pytest tests/test_phase9_institutions.py -v
```

**Commit:**
```bash
git add src_template/institutions.py tests/test_phase9_institutions.py
git commit -m "feat: add Phase 9 durable institutions from constructive faction outcomes"
```

---

## Task 3: Collapse Recovery and Regime Transitions

**Objective:** When a world's GDP or legitimacy hits zero, trigger a regime crisis mechanism that can produce either recovery or terminal collapse — not just permanent stasis at zero.

**Files:**
- Create: `src_template/regime_transitions.py`
- Test: `tests/test_phase9_regime.py`

**Design:**

Current problem: once GDP=0, legitimacy=0, nothing changes. The world sits at zero forever. We need crisis-resolution dynamics.

**Trigger:** When GDP < 0.05 AND legitimacy < 0.10 for 3 consecutive ticks, enter `regime_crisis`.

**Crisis resolution paths (weighted by world profile and current state):**

| Path | Weight drivers | Outcome |
|------|---------------|---------|
| `elite_defection` | High repression, low legitimacy | Regime falls, new leadership with reset legitimacy (0.40) but low fiscal_capacity |
| `popular_uprising` | High type_tension, many radicalized factions | Regime falls, legitimacy resets to 0.55, but GDP drops further, war_pressure spikes |
| `external_intervention` | High border_openness, federation aid active | GDP reset to 0.30, legitimacy to 0.45, but sovereignty penalty (type_tension +0.15) |
| `reform_from_within` | Moderate repression (0.40-0.60), some legalized factions | Gradual recovery: legitimacy +0.03/tick, GDP +0.02/tick for 10 ticks |
| `terminal_collapse` | All other cases | Population collapses, world becomes post-collapse shell (but with small chance of later revival) |

**Implementation:**

```sql
CREATE TABLE IF NOT EXISTS regime_events (
    event_id TEXT PRIMARY KEY,
    world_id TEXT NOT NULL,
    tick_number INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    from_regime TEXT,
    to_regime TEXT,
    resolution_path TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
```

**Causal ledger events:** `regime_crisis_triggered`, `elite_defection`, `popular_uprising`, `external_intervention`, `reform_from_within`, `terminal_collapse`, `regime_transition`.

**Special case — post-collapse revival:** A world at terminal_collapse status has a 2% chance per decade of a `bottom_up_reorganization` event that resets GDP to 0.15 and legitimacy to 0.25, representing grassroots rebuilding.

**Tests:**
- World at GDP=0, legitimacy=0 for 3 ticks triggers regime_crisis.
- Elite defection path resets legitimacy above 0.
- Popular uprising spikes war_pressure and drops GDP.
- External intervention requires border_openness > 0.5.
- Terminal collapse produces post-collapse status with revival chance.
- World with high legitimacy and legalized factions follows reform_from_within.

**Verification:**
```bash
pytest tests/test_phase9_regime.py -v
```

**Commit:**
```bash
git add src_template/regime_transitions.py tests/test_phase9_regime.py
git commit -m "feat: add Phase 9 collapse recovery and regime transitions"
```

---

## Task 4: Cultural Learning and Technology Diffusion

**Objective:** Worlds learn from each other. Cultural traits, institutional models, and technological innovations spread through the federation — creating convergence where beneficial and divergence where resisted.

**Files:**
- Create: `src_template/cultural_diffusion.py`
- Test: `tests/test_phase9_culture.py`

**Design:**

Add a `cultural_traits` table per world and a federation-level `diffusion_events` table:

```sql
CREATE TABLE IF NOT EXISTS cultural_traits (
    world_id TEXT NOT NULL,
    trait TEXT NOT NULL,
    value REAL NOT NULL DEFAULT 0.5,
    source_world TEXT,
    adopted_tick INTEGER,
    PRIMARY KEY (world_id, trait)
);

CREATE TABLE IF NOT EXISTS diffusion_events (
    event_id TEXT PRIMARY KEY,
    tick_number INTEGER NOT NULL,
    source_world TEXT NOT NULL,
    target_world TEXT NOT NULL,
    trait TEXT NOT NULL,
    adoption_strength REAL NOT NULL,
    resisted INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
```

**Cultural traits (per world, evolves over time):**

| Trait | Initial value | Affects |
|-------|--------------|---------|
| `openness_to_trade` | from world profile border_openness | trade agreement likelihood, GDP from trade |
| `institutional_memory` | from world profile resilience | institution durability, reform likelihood |
| `xenophobia` | 1.0 - border_openness | refugee tolerance, diffusion resistance |
| `innovation_culture` | from tech_level | innovation accumulation rate |
| `governance_norms` | from legitimacy baseline | faction concession probability, repression bias |

**Diffusion mechanics:**

1. Each tick, for each pair of bordering worlds, attempt to diffuse one trait where `|source_value - target_value| > 0.15`.
2. Adoption strength = `source_influence × (1.0 - target_xenophobia) × border_openness`.
3. If adoption_strength > resistance threshold, target world's trait shifts toward source by `adoption_strength × 0.02`.
4. Institutions can also diffuse: if source has a durable institution (durability > 0.3), target may adopt a weakened copy.
5. Federation events that spread problems (ideology_diffusion) now also have a mirror effect: high-legitimacy worlds spread `governance_norms` to neighbors.

**Causal ledger events:** `cultural_trait_adopted`, `cultural_trait_resisted`, `institution_diffused`, `governance_norms_diffusion`.

**Tests:**
- Trait diffuses from high-legitimacy world to neighbor.
- Xenophobic world resists diffusion.
- Institution model spreads between bordering worlds.
- Cultural distance between two worlds changes over a run.
- Governance norms increase in worlds bordering stable democracies.

**Verification:**
```bash
pytest tests/test_phase9_culture.py -v
```

**Commit:**
```bash
git add src_template/cultural_diffusion.py tests/test_phase9_culture.py
git commit -m "feat: add Phase 9 cultural learning and technology diffusion"
```

---

## Task 5: Federation Diplomacy and Aid

**Objective:** The federation layer currently only spreads problems (trade_shock, ideology_diffusion, disease_alert). Add positive-sum federation mechanics: trade agreements, aid pacts, mutual defense, and sanctions.

**Files:**
- Create: `src_template/federation_diplomacy.py`
- Test: `tests/test_phase9_diplomacy.py`

**Design:**

Add `diplomatic_relations` table to federation DB:

```sql
CREATE TABLE IF NOT EXISTS diplomatic_relations (
    relation_id TEXT PRIMARY KEY,
    world_a TEXT NOT NULL,
    world_b TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    strength REAL NOT NULL DEFAULT 0.5,
    established_tick INTEGER NOT NULL,
    dissolved_tick INTEGER,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
```

**Relation types and effects:**

| Type | Trigger condition | Effect on both worlds |
|------|------------------|----------------------|
| `trade_agreement` | Both GDP > 0.20, border_openness > 0.30 | +0.005 GDP/tick each, +0.002 border_openness/tick |
| `aid_pact` | One world in crisis, other GDP > 0.40 | Donor: -0.003 GDP/tick. Recipient: +0.008 GDP/tick, +0.003 legitimacy/tick |
| `mutual_defense` | Both war_pressure > 0.30 | -0.003 war_pressure/tick each, +0.002 legitimacy/tick |
| `research_cooperation` | Both tech_level > 0.15 | +0.004 innovation/tick each |
| `open_borders` | Both refugee_tolerance > 0.50 | +0.003 border_openness/tick, migration push_sensitivity × 1.5 |
| `sanctions` | One world repression > 0.70, other legitimacy > 0.50 | Target: -0.005 GDP/tick. Sender: -0.002 GDP/tick |

**Lifecycle:**

1. **Proposal:** Each year, worlds evaluate potential diplomatic relations with neighbors based on their profiles and current state.
2. **Formation:** If both worlds meet conditions, relation established with strength 0.5.
3. **Maintenance:** Strength decays at 0.01/tick. Positive interactions (trade, aid, shared institutions) increase strength.
4. **Dissolution:** When strength hits 0 or conditions no longer met (e.g., trade partner GDP crashes), relation dissolves.
5. **Escalation:** High-strength relations (>0.8) can escalate to deeper pacts (trade → mutual_defense, aid_pact → open_borders).
6. **Federation assembly:** Every 5 years, all worlds with legitimacy > 0.30 convene a federation assembly that can propose federation-wide policies.

**Causal ledger events:** `trade_agreement_signed`, `aid_pact_established`, `mutual_defense_formed`, `sanctions_imposed`, `diplomatic_relation_dissolved`, `federation_assembly_convened`, `federation_policy_adopted`.

**Tests:**
- Two worlds with GDP > 0.20 sign trade agreement and both gain GDP.
- World in crisis receives aid from stable neighbor.
- High-repression world gets sanctioned by democratic neighbor.
- Trade agreement dissolves when one world's GDP crashes.
- Federation assembly fires at year 5, 10, 15...

**Verification:**
```bash
pytest tests/test_phase9_diplomacy.py -v
```

**Commit:**
```bash
git add src_template/federation_diplomacy.py tests/test_phase9_diplomacy.py
git commit -m "feat: add Phase 9 federation diplomacy and aid mechanics"
```

---

## Task 6: Integrate All Phase 9 Modules Into the Orchestrator

**Objective:** Wire capital economy, institutions, regime transitions, cultural diffusion, and diplomacy into the barrier tick.

**Files:**
- Modify: `src_template/federation_orchestrator.py`
- Modify: `src_template/macro_dynamics.py`
- Modify: `src_template/yearly_report.py`
- Modify: `src_template/federation_effects.py`

**Integration points in `run_world_barrier_tick()`:**

```
def run_world_barrier_tick(db, fed_db, world_id, tick_number, rng):
    # ... existing micro, meso, faction, macro, migration, demo ...

    # NEW: Capital economy (after meso aggregation, before macro)
    capital_economy.apply_capital_flows(db, world_id=world_id, tick_number=tick_number)

    # NEW: Institutions (after faction lifecycle)
    institutions.apply_institution_benefits(db, world_id=world_id, tick_number=tick_number)

    # NEW: Regime transitions (after macro dynamics)
    regime_transitions.check_and_resolve_crisis(db, world_id=world_id, tick_number=tick_number)

    # NEW: Cultural diffusion (after barrier sync)
    cultural_diffusion.apply_diffusion_tick(fed_db, worlds=worlds, tick_number=tick_number)

    # NEW: Federation diplomacy (after barrier sync, yearly)
    if is_year_boundary(tick_number):
        federation_diplomacy.evaluate_and_update_relations(fed_db, worlds=worlds, tick_number=tick_number)

    # ... existing demo, report
```

**Macro dynamics modification:** GDP proxy becomes derived from capital_economy rather than an independent variable that only decays.

**Yearly report additions:**
- `capital_stock`, `gdp_flow`, `innovation_stock` from capital_economy
- `institutions` count by type
- `regime_events` count
- `cultural_traits` snapshot
- `diplomatic_relations` count by type

**Federation effects addition:** Positive diffusion events alongside existing negative contagion events.

**Tests:**
- Integration test: full 5-year run with all Phase 9 modules wired in.
- GDP is derived from capital economy, not independent.
- Institutions appear in yearly reports.
- Regime transitions fire and change macro state.
- Cultural traits change over time.
- Diplomacy events appear in federation ledger.

**Verification:**
```bash
pytest tests/ -q -k "phase9"  # all Phase 9 tests
pytest tests/ -q               # full suite including Phase 8 regression
```

**Commit:**
```bash
git add src_template/federation_orchestrator.py src_template/macro_dynamics.py src_template/yearly_report.py src_template/federation_effects.py tests/test_phase9_integration.py
git commit -m "feat: integrate Phase 9 positive-sum dynamics into orchestrator"
```

---

## Task 7: Recalibrate and Gate-Check

**Objective:** Run 5-year, 20-year, and 50-year calibration runs. Verify all Phase 9 gates pass. Verify Phase 8 gates still pass (no regression). Adjust calibration constants as needed.

**Files:**
- Modify: `scripts/evaluate_phase9_run.py` (extend Phase 8 evaluator)

**New acceptance gates to add:**

```python
# Positive-sum gate
gdp_above_025 = sum(1 for w in worlds if last_macro(w)['gdp_proxy'] > 0.25)
gdp_gate_ok = gdp_above_025 >= 2

constructive_total = sum of (integrated + legalized + governing_coalition) outcomes
total_outcomes = sum of all faction outcomes
constructive_gate_ok = constructive_total / max(total_outcomes, 1) >= 0.30

# Recovery gate
recovered = any world that fell below 0.10 and recovered above 0.30 in same key
regime_improved = any world that transitioned from collapsed to constructive regime

# Institution gate
institution_count >= 3
three_stage_faction = any faction that went legalized → governing_coalition → institutionalized

# Learning gate
cultural_convergence = any pair of worlds with decreasing cultural distance
cultural_divergence = any pair of worlds with increasing cultural distance

# Diplomacy gate
active_agreements = count of diplomatic_relations at year 30 >= 2
diplomacy_event_types >= 3
```

**Calibration run plan:**

1. `python causal_run.py --years 5 --npcs 200 --ticks 4 --clean` — quick sanity
2. `python causal_run.py --years 20 --npcs 200 --ticks 4 --clean` — divergence check
3. `python causal_run.py --years 50 --npcs 200 --ticks 4 --clean` — full gate evaluation
4. If gates fail: adjust capital accumulation rates, institution formation probabilities, recovery thresholds
5. Repeat until all Phase 8 + Phase 9 gates pass

**Verification:**
```bash
python scripts/evaluate_phase9_run.py /tmp/aurelia-phase9-50y/causal_summary.json
```

**Commit:**
```bash
git add scripts/evaluate_phase9_run.py
git commit -m "feat: add Phase 9 evaluator with positive-sum acceptance gates"
```

---

## Task 8: Push to Cloudflare

**Objective:** After all gates pass, push the 50-year run to Cloudflare D1/R2.

**Steps:**
1. Verify all gates pass.
2. `python aurelia_cf_pusher.py push-all` with Phase 9 DB path.
3. Verify dashboard shows updated world states with positive-sum dynamics visible.

**Commit:**
```bash
git add aurelia_cf_pusher.py  # if modified
git commit -m "chore: update pusher for Phase 9 output paths"
```

---

## Risk: Calibration May Require Multiple Iterations

The biggest risk is that the positive-sum mechanics are too weak to overcome the existing collapse dynamics. Mitigations:

1. **Capital sensitivity:** If GDP still hits zero across all worlds, increase `gdp_flow` multipliers by 2-3× until at least 2 worlds maintain GDP > 0.25.
2. **Recovery floor:** If regime transitions never fire, lower the crisis trigger threshold and increase recovery path probabilities.
3. **Institution formation:** If no institutions form, increase the formation probability from faction outcomes and lower the legitimacy threshold.
4. **Accept defeat gracefully:** If after 3 calibration passes the gates still fail, we've learned something important — the collapse dynamics may be structurally dominant with the current micro→macro coupling, and we need a deeper rearchitecture rather than additive layers.

---

## Summary of All New Source Files

| File | Purpose |
|------|---------|
| `src_template/capital_economy.py` | Capital accumulation, GDP flow, innovation |
| `src_template/institutions.py` | Durable institutions from faction outcomes |
| `src_template/regime_transitions.py` | Collapse recovery and regime change |
| `src_template/cultural_diffusion.py` | Trait/institution learning across worlds |
| `src_template/federation_diplomacy.py` | Trade, aid, defense, sanctions between worlds |
| `scripts/evaluate_phase9_run.py` | Extended evaluator with Phase 9 gates |

## Summary of Modified Files

| File | Changes |
|------|---------|
| `src_template/federation_orchestrator.py` | Wire all new modules into barrier tick |
| `src_template/macro_dynamics.py` | GDP derived from capital economy |
| `src_template/yearly_report.py` | New fields for Phase 9 data |
| `src_template/federation_effects.py` | Positive diffusion alongside negative contagion |
| `aurelia_cf_pusher.py` | Phase 9 output path |

## Expected Outcomes

After successful implementation and calibration, the 50-year run should show:

- **Not all worlds collapse to zero GDP.** At least 2 sustain economies above 0.25.
- **Recovery is possible.** At least one world that crashes recovers.
- **Institutions matter.** Durable institutions create persistent positive effects.
- **Constructive politics exist.** Integration, legalization, and coalition are viable faction outcomes, not just suppression and radicalization.
- **The federation helps.** Trade agreements and aid pacts create mutual gains, not just shared problems.
- **Worlds learn.** Cultural traits and institutional models spread — convergence where beneficial, maintained divergence where identity is stronger.
- **Multiple attractors.** The phase space has at least 3 distinct long-run outcomes (collapse, managed stability, growth), not just varieties of civil conflict.
