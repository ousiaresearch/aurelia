# Aurelia Federation: Causal Gaps Deep-Dive

**Date:** 2026-06-08
**Source data:** `/tmp/aurelia-phase9-50y/` (50-year calibration, 5 worlds, ~5,000 ticks)
**Method:** Empirical inspection of all populated modules, code audit of un-called modules, cross-reference with real-world civilizational causal literature.

---

## Executive Summary

Phase 9 broke the single-attractor collapse basin. But the 50-year run reveals that the simulation is **not yet a federation of five real civilizations** — it's a federation of five **shadows** that share the same skeleton, the same stuck dimensions, and the same handful of event types.

**Three classes of missing causal factors:**

1. **Modules that exist in code but are never called** — discoveries, great persons, peace treaties, sovereignty, escalation, rituals, ecology, reconciliation, dialogue, depth, goals, narrative. These represent ~30% of the codebase and zero percent of the causal dynamics.
2. **Stuck dimensions** — `infrastructure`, `water_security`, and `inequality` are **constants** across 50 years × 5 worlds. They appear in the macro state but no causal path can change them.
3. **Weak/null mechanisms in wired modules** — diplomatic relations form with `strength=0.0` and dissolve by tick 38; 3,672 migration cohorts create zero `cross_world_movements`; the causal graph has 0 edges; `world_macro_snapshot` stores 5 rows of initial states.

The simulation produces variety in **legitimacy, repression, war pressure, and regime** — but variety is not causation. The "phase space" of outcomes is real but tiny: ~5 reachable regime trajectories in 50 years.

---

## Part 1: The Empirical Map (50-year Phase 9 run)

### What actually fires (top 20 event types, verge)

| Event type | Count | What it represents |
|------------|-------|--------------------|
| work_success | 7,104 | Productive labor outcome |
| rumor_transmission | 5,031 | Social info flow |
| work_failure | 5,019 | Failed productive labor |
| small_trade | 4,653 | Market exchange |
| caregiving | 3,915 | Interpersonal support |
| wage_dispute | 3,183 | Class tension |
| security_stop | 3,134 | Repression |
| propaganda_exposure | 2,760 | State messaging |
| illness_seen | 2,247 | Health stress |
| migration_plan | 1,932 | Departure intent |
| emigration | 420 | Departure execution |
| migration_outflow | 412 | Aggregate departure |
| migration_inflow | 386 | Aggregate arrival |
| immigration | 386 | Arrival execution |
| state_messaging | 200 | Macro meso signal |
| social_solidarity | 200 | Macro meso signal |
| rumor_velocity | 200 | Macro meso signal |
| repression_visibility | 200 | Macro meso signal |
| public_health_risk | 200 | Macro meso signal |
| productive_confidence | 200 | Macro meso signal |

**43-48 distinct event types per world.** That's the causal vocabulary. Anything not in this list (and not in the 3,672 migration_cohorts or 5 institutions) doesn't happen.

### What does NOT fire

| Module | Lines of code | Wired in? | Rows in 50y × 5 worlds |
|--------|---------------|-----------|------------------------|
| `discovery.py` | 432 | ❌ | **0** |
| `great_persons.py` | 413 | ❌ | **0** |
| `escalation_ladder.py` | 521 | ❌ | (n/a — internal) |
| `cross_world.py` | ? | ❌ | **0** movements |
| `peace_treaties` insert | schema only | ❌ | **0** treaties |
| `sovereignty_events` | 481 | ❌ | **0** events |
| `rituals.py` | 624 | ❌ | (n/a — no table) |
| `ecology.py` | 462 | ❌ | (n/a — no table) |
| `reconciliation.py` | 568 | ❌ | (n/a — no table) |
| `npc_dialogue.py` | 617 | ❌ | (n/a — no table) |
| `npc_depth.py` | 614 | ❌ | (n/a — no table) |
| `goals.py` | 419 | ❌ | (goal rows exist but inactive) |
| `narrative_arcs.py` | 546 | ❌ | (post-hoc only) |
| `batch_chronicles.py` | 507 | ❌ | (post-hoc only) |
| `prose_narrative.py` | 563 | ❌ | (post-hoc only) |
| `ghost.py` | 409 | ❌ | (post-hoc only) |

**~30% of the codebase is never invoked in the per-tick loop.** These modules represent causal mechanisms that the architecture plans to support but the runtime doesn't exercise.

### What fires but is stuck

Across all 5 worlds, 50 years:

| Dimension | min | max | std | Verdict |
|-----------|-----|-----|-----|---------|
| `infrastructure` | 0.600 | 0.600 | 0.0000 | **CONSTANT** |
| `water_security` | 0.600 | 0.600 | 0.0000 | **CONSTANT** |
| `inequality` | 0.45 | 0.45 | 0.0000 | **CONSTANT** |
| `gdp_proxy` | 0.001 | 0.22 | varies | works |
| `legitimacy` | 0.10 | 0.44 | varies | works |
| `food_security` | 0.10 | 0.62 | varies | works |
| `public_health` | 0.46 | 0.75 | varies | works |
| `fiscal_capacity` | 0.10 | 0.50 | varies | works |

`infrastructure`, `water_security`, and `inequality` are **in the macro state schema but not in any causal path.** They are dead variables — visible to the user, invisible to the simulation.

### What fires but is null

| Field | Issue |
|-------|-------|
| `diplomatic_relations.strength` | Always `0.0` — relations form with no actual strength signal |
| `world_macro_snapshot.tick_number` | All 5 rows have `tick_number=0` — only the initial state is snapshotted |
| `federation.causal_edges` | **0 rows** — the causal graph has edges in the schema but none are inserted |
| `federation.diffusion_events` | **0 rows** — cultural diffusion module runs but never logs an event |
| `worlds.npc_actions` | **0 rows** — NPC-level actions not persisted (only events are) |
| `worlds.tick_log` | **0 rows** — per-tick log not written |

---

## Part 2: The Three Causal Gaps

### Gap 1: No Innovation Pathway

**What real civilizations have:** cumulative technological learning, with compound returns. The Solow residual — the unexplained residual in economic growth — is largely technological progress. The Industrial Revolution took 10,000 years of accumulated knowledge, then released 200 years of compound growth.

**What Aurelia has:** `tech_level` exists in `capital_pool` and ranges 0.25-0.37 across 50 years. It moves slowly. But there is no **discrete invention** event — no "smelted iron", "printed press", "antibiotic", "semiconductor", "LLM" event that fires from accumulated knowledge + institutional conditions + population density + trade access.

**Why this matters:** without an innovation axis, the simulation has no compounding growth engine. Capital can accumulate, but its returns can't increase. Phase 9 added capital, but the productivity of capital is constant.

**Module gap:** `discovery.py` (432 lines) and `great_persons.py` (413 lines) exist but are never called. `capital_economy` increments `innovation_stock` by `rumor_velocity` but no module actually triggers a discovery when innovation crosses a threshold.

**Proposed fix (Phase 10.1):** Wire `discovery.py` into the per-tick loop. Trigger a discovery when:
- `innovation_stock > 0.5` AND
- `capital_stock > 0.3` AND
- `institutional_memory > 0.4` (some peace lasts) AND
- `population > 50` (knowledge concentrated)

The discovery should provide:
- A one-time `tech_level` step (+0.1 to +0.3)
- A causal event that increases `gdp_flow` permanently
- An institution-strengthening effect
- Optional diffusion to other federation worlds

**Real-world precedent:** this is the J-curve pattern. Most societies are stuck; a few cross the threshold and diverge.

### Gap 2: No Environmental Floor

**What real civilizations have:** water, soil, climate, and disease as binding constraints. The fall of Rome, the Bronze Age collapse, the Maya, the Norse in Greenland — all are environmental stories dressed as political ones.

**What Aurelia has:** `water_security` is a constant 0.6. `infrastructure` is a constant 0.6. `food_security` works (it can degrade with repression) but isn't tied to anything *physical* — there's no ecology, no climate, no resource depletion.

**Why this matters:** without an environmental axis, the simulation has no exogenous shock generator. All shocks are *political* (faction, war, repression). Real civilizations get hit by droughts, pandemics, soil exhaustion, climate shifts. The fact that all 5 worlds have identical `water_security=0.6` for 50 years is the most damning evidence that the simulation has no material substrate.

**Module gap:** `ecology.py` (462 lines) exists but is never called. `weather` table exists in the schema and is populated at world init, but `weather` is not consulted in any module.

**Proposed fix (Phase 10.2):** Wire `ecology.py` and `weather` into the loop. Generate per-tick:
- Drought events (random + climate baseline): reduce `water_security`, then `food_security`, then `legitimacy`
- Pest/crop failure: same chain
- Pandemic events: reduce `public_health`, increase `mortality_rate`
- Resource depletion: extract from `resources` table, limit population carrying capacity

**Real-world precedent:** the climate-change literature is unambiguous: environmental shocks are first-order drivers of civilizational change. Turchin's "Ages of Discord" identifies elite overproduction + popular immiserization + state fiscal distress as the three structural drivers, but he also identifies climate as the exogenous trigger.

### Gap 3: No Inter-Generational / Demographic Dynamics

**What real civilizations have:** demographic transition (high birth/high death → low birth/low death), urbanization, family structure, age cohorts, education. The demographic transition took 200 years in the West and is now the single most reliable predictor of regime stability.

**What Aurelia has:** `births` and `deaths` fire as point events (8 births and 14 deaths in arkos, 50 years). Population goes from ~200 to 5-192 across worlds. The mechanism is event-driven, not demographic.

**Why this matters:** without demographic dynamics, the simulation has no timescale for family formation, no concept of youth bulge (which Turchin and Goldstone identify as a major driver of instability), no intergenerational transmission of trauma, no urban/rural distinction, no concept of *how many* young men with nothing to lose a society can absorb.

**Module gap:** `population.py` is called for births/deaths, but only as point events. There's no age structure, no cohort tracking, no fertility rate, no education pipeline, no urban/rural split.

**Proposed fix (Phase 10.3):** Add an age-structured population:
- Track agent age (already in schema)
- Fertility rate = function of (food_security, public_health, legitimacy, repression)
- Mortality = function of (age, public_health, food_security, water_security, war_pressure)
- Education level per agent (or aggregated per world)
- Youth bulge = (males aged 15-30) / (males aged 30-50) — Turchin's structural demo indicator
- Urbanization = (population in cities) / (total population) — affects surveillance, food supply, regime type

**Real-world precedent:** youth bulge is the single most robust predictor of civil conflict onset. This is not a nice-to-have, it's the central finding of the political demography literature.

---

## Part 3: The Wired-But-Null Mechanisms

These aren't missing modules — they're modules that exist in the per-tick loop but produce no signal.

### Gap 4: Diplomatic Relations with `strength=0.0`

**What happens:** 9 diplomatic relations form. All have `strength=0.0`. All 6 initial trade agreements dissolve by tick 38. 2 aid pacts form in tick 27, dissolve in tick 30. 1 more trade agreement forms at tick 48, dissolves at tick 58. By tick 200: zero active relations.

**Why this matters:** the federation is *named* "federation" but has no persistent bonds. This is the single biggest gap between the simulation's name and its behavior. Phase 9 added diplomacy code, but the strength signal was never populated.

**Root cause:** the `strength` field is set in the schema but no module writes to it. Trade, aid, defense pacts form via `_can_form` checks but accumulate no strength over time.

**Proposed fix:** Make strength = f(years_active, trade_volume, no_war_period, joint_discoveries). With strength, you get:
- A diplomatic gravity well: relations with strength > 0.4 are hard to dissolve
- A trust signal: high-strength relations enable joint actions (joint research, joint institutions)
- A breakup story: when strength crosses 0, the relation dissolves with a causal event
- A civilizational anchor: world pairs that trade for decades develop entanglements

### Gap 5: Migration Without Movement

**What happens:** 3,672 migration_cohorts are planned across 5 worlds. Zero `cross_world_movements` actually execute.

**Why this matters:** migration is the *primary vector* for cross-world influence. The simulation has thousands of NPCs who *want* to move, but they never arrive. This is the equivalent of a country with closed borders at the individual level.

**Root cause:** `migration_cohorts` table is populated, but no code path actually transfers NPC records between world DBs. The schema supports it (`npc_departures` table exists) but the transfer logic isn't called.

**Proposed fix:** When a migration_cohort is finalized:
1. Select N NPCs from `agents` matching the cohort criteria
2. Insert into the destination `agents` table
3. Log in `npc_departures` (source) and `cross_world_movements` (federation)
4. The destination world gains population, possibly with new grievances (refugees), new skills, new cultural traits
5. This enables Phase 9's cultural diffusion to *actually have carriers*

### Gap 6: Cultural Diffusion With No Events

**What happens:** 25 cultural traits are seeded (5 per world × 5 traits). The `diffusion_events` table is empty.

**Why this matters:** Phase 9's `cultural_diffusion.apply_diffusion_tick` runs every tick, but no `diffusion_events` are recorded. The mechanism exists but doesn't actually diffuse.

**Root cause:** diffusion is rate-limited to a threshold of 0.12 trait difference. With all worlds seeded with `world_profiles` values, the actual trait differences are ~0.02-0.08 — below threshold. Even when the threshold was lowered to 0.06, no diffusion fired.

**Proposed fix:** Two complementary changes:
1. **Amplify trait differences at seeding time** — instead of using profile values directly (which are 0.0-1.0), amplify the world-specific spread (e.g. `xenophobia = (1 - refugee_tolerance) * 1.5` for high-xenophobia worlds)
2. **Add a noise term** — even with similar profiles, contact over decades creates drift; a small per-tick random walk on trait values creates natural divergence and contact-induced convergence

### Gap 7: The Causal Graph is Empty

**What happens:** 178,051 causal events are recorded in the federation DB. The `causal_edges` table is empty. There is no causal graph — only a sequence of events.

**Why this matters:** a sequence is not causation. The user asked for "causal factors" — but the simulation doesn't even *have* a causal graph. Every event is treated as independent. The "causal_summary" in the output is just frequency counts, not actual causal chains.

**Root cause:** no module writes to `causal_edges`. The schema supports it (`parent_event_id`, `child_event_id`, `relation`, `weight`) but nothing populates it.

**Proposed fix:** Add edge generation:
- When `event_type='X'` causes `event_type='Y'` in the same tick (e.g. work_success causes small_trade), insert an edge
- When a delayed_effect is scheduled, insert an edge from cause to scheduled effect
- When a faction outcome causes a regime change, insert an edge
- When a migration causes a cultural diffusion, insert an edge

This would enable **actual causal analysis** — "what causes regime transitions?" could be answered by walking the graph, not by counting co-occurrences.

---

## Part 4: The Mis-Modeled Dimensions

### Gap 8: Inequality as a Constant

`inequality` is a critical real-world driver (Piketty, Milanovic, Turchin's elite overproduction). It exists in the macro state but is hard-coded at 0.45 (or 0.55 for valdris) for 50 years.

**Proposed fix:** inequality should be a function of:
- Distribution of `capital_pool` (gains accrue to capital owners)
- Regime type (democratic vs autocratic)
- `fiscal_capacity` (redistributive capacity)
- `legitimacy` (consent reduces need for extraction)
- Faction power balance (counter-elites can extract concessions)

### Gap 9: Infrastructure as a Constant

`infrastructure` is the physical substrate of civilization. It's at 0.6 for 50 years. Real infrastructure *decays* without maintenance and *grows* with investment.

**Proposed fix:** infrastructure should:
- Decay slowly (0.001/tick)
- Grow with `capital_pool` investment
- Decay faster during war
- Decay faster during repression (the roads/bridges don't get maintained)
- Be damaged by environmental shocks (Gap 2)

### Gap 10: Repression as a Toggle, Not a Dial

In the data, `repression` ranges 0.19-0.59. That's a 3x range but only at the level of "how much", not "what kind". Real repression has *types*: secret police vs mass surveillance vs legal harassment vs outright violence. The *type* determines its consequences for legitimacy, dissent, and economic productivity.

**Proposed fix:** introduce `repression_type` with consequences:
- `surveillance` (high cost, low visibility, slow legitimacy decay)
- `legal` (low cost, high visibility, fast legitimacy decay if discovered)
- `violent` (high cost, high visibility, fast legitimacy decay, high emigration)
- `propaganda` (low cost, medium visibility, contested effect on legitimacy)

This would also explain *why* the simulation's repression saturates at ~0.5 — there's no *type*, so there's no qualitative break, just a quantitative one.

---

## Part 5: The Long Tail — Smaller Gaps

### Gap 11: No Urbanization

All NPCs are field-dwelling. There's no urban/rural distinction. Real cities are where:
- Surveillance is cheaper (regimes collapse in cities faster)
- Markets are thicker (productivity jumps)
- Disease spreads faster
- Faction activity concentrates

`locations` exists in the schema but is generic (loc_0, loc_1...) not urban/rural.

### Gap 12: No Education / Human Capital

There's no education module. No literacy, no numeracy, no skill transmission. This means `tech_level` is exogenous (driven only by `rumor_velocity` × `innovation_stock`) rather than endogenous to the population's capacity to absorb it.

### Gap 13: No Disease Ecology

`public_health` exists but is driven by `legitimacy` and `repression` rather than by population density, mobility, and pathogen dynamics. `illness_seen` is a signal event but doesn't actually cause death.

### Gap 14: No Resource Depletion

`resources` table exists with per-location quantities. Nothing drains them. So a world can produce work_success forever without resource constraint. This is the kind of assumption that makes simulations *too easy*.

### Gap 15: No Conflict Asymmetry

`war_pressure` exists but there's no distinction between:
- Civil war (factions within a state)
- Interstate war (between worlds)
- Insurgency (small group vs state)
- Terrorism (asymmetric)

Each has different causal logic. Phase 8 added civil conflict as a regime type, but the *mechanism* of how factions become violent is undifferentiated.

### Gap 16: No Property Rights / Contract Enforcement

Real economies run on contracts and property rights. These are not modeled. So trade happens (`small_trade`) but there's no mechanism for contract enforcement, no concept of "trust" in counterparties, no slow-building merchant class.

### Gap 17: No State Capacity Variation

`fiscal_capacity` exists but is just a number. Real states vary in *kind*:
- Patrimonial (ruler's household is the state)
- Bureaucratic (Weberian)
- Prebendal (office as rent)
- Developmental (state-led growth)

This determines whether fiscal_capacity can *grow* (bureaucratic, developmental) or just *extract* (patrimonial, prebendal).

### Gap 18: No Foreign Actor Strategy

When mirithane's GDP collapses, does the federation do something? Right now no — there's no foreign policy logic that says "if neighbor is in crisis, intervene (or don't)". The federation is a *containment* layer, not a *policy* layer.

### Gap 19: No Path Dependence / Lock-In

The simulation is fairly Markovian — current state → next state, with limited memory. But real institutions, technologies, and cultures have *hysteresis*: once you're on a path, the cost of switching grows over time. A constitutional_court that's been active for 30 years is much harder to disband than one that's been active for 5.

### Gap 20: No Counterfactual Branching

The simulation runs *one* history per world. But the most interesting question is: what would have happened if federation intervention had come 10 years earlier? Or if the constitutional court had been founded 20 years later? There's no mechanism for counterfactual branching.

---

## Part 6: The Causal Factor Inventory (consolidated)

| Factor | Real-world weight | Currently modeled | Gap |
|--------|-------------------|-------------------|-----|
| Factional politics | High | ✅ Strong | — |
| Macro economy (GDP, capital) | High | ✅ Strong (P9) | — |
| Repression | High | ⚠️ Toggle only | Type missing |
| Inequality | High | ❌ Constant | G8 |
| Infrastructure | High | ❌ Constant | G9 |
| Migration | High | ⚠️ Cohorts but no movement | G5 |
| Diplomacy | High | ⚠️ strength=0 | G4 |
| Cultural diffusion | Medium | ⚠️ No events | G6 |
| Innovation | High | ❌ Module dormant | G1 |
| Environment / climate | High | ❌ weather ignored | G2 |
| Demographics / age | High | ❌ Events only | G3 |
| Disease | Medium | ❌ Signal only | G13 |
| Education | High | ❌ Missing | G12 |
| Resources | Medium | ❌ Undepleted | G14 |
| Urbanization | Medium | ❌ No urban/rural | G11 |
| Foreign policy | High | ❌ No strategy | G18 |
| Path dependence | Medium | ❌ Markovian | G19 |
| State capacity type | High | ❌ Number only | G17 |
| Property rights | High | ❌ Missing | G16 |
| Conflict type | High | ❌ Undifferentiated | G15 |
| Counterfactual branching | Research value | ❌ None | G20 |
| Great persons / contingency | Medium | ❌ Module dormant | (w/ G1) |
| Peace treaties | Medium | ❌ Schema only | (G4 family) |
| Sovereignty | Medium | ❌ Schema only | (G3 family) |
| Escalation ladder | Medium | ❌ Module dormant | (G15 family) |
| Reconciliation | Medium | ❌ Module dormant | (G19 family) |
| Rituals / ceremony | Low | ❌ Module dormant | — |
| NPC dialogue | Low (post-hoc) | ❌ Module dormant | — |
| NPC depth | Low (post-hoc) | ❌ Module dormant | — |
| Goals | Medium | ❌ Schema only | — |

---

## Part 7: The Top-3 Highest-Impact Next Steps

If I had to pick three causal factors to add that would most change the simulation's behavior:

### #1: Innovation / Discovery (G1)

**Why:** without it, there is no growth engine. Every world can recover from collapse but none can grow past the initial capital baseline. Phase 9 made recovery possible; Phase 10.1 needs to make *growth* possible.

**Effort:** wire `discovery.py` into the loop, add threshold conditions, add a discovery record + effect. ~200 lines of code.

**Expected impact:** the federation will bifurcate. Some worlds will hit the discovery threshold and diverge into sustained growth; others will oscillate without crossing it. This is the single most important civilizational mechanism.

### #2: Environment / Ecology (G2)

**Why:** without it, all shocks are political. Real civilizations get hit by droughts, pandemics, soil exhaustion. The fact that all 5 worlds have `water_security=0.6` for 50 years means the simulation has no material substrate.

**Effort:** wire `ecology.py` + `weather` into the loop. Add drought/pandemic/resource events. ~300 lines of code.

**Expected impact:** the federation will have exogenous variation. Some worlds will collapse from drought, not politics. Some will *thrive* from a climate shift. This breaks the assumption that all collapse is governance failure.

### #3: Demographics / Age Structure (G3)

**Why:** youth bulge is the single most robust predictor of civil conflict onset. Without age structure, the simulation has no timescale for the 20-30 year lag between demographic stress and political crisis.

**Effort:** add age column to agents, add fertility/mortality functions, add education pipeline. ~400 lines of code.

**Expected impact:** the timing of regime transitions will become predictable. A world with a youth bulge in year 20 will have a crisis in year 30-35. This is the foundation of political demography.

---

## Part 8: Why This Matters (the meta-question)

The user asked: "the point was not merely civil conflict but to understand where AI is led."

Where AI is led: by the *causal factors we encode*. The current simulation is led by:
- Repression
- Faction politics
- Capital accumulation
- Migration pressure
- Diplomatic bonds (weakly)
- Cultural diffusion (weakly)

But it is NOT led by:
- Innovation
- Environment
- Demographics
- Education
- Path dependence

This means the simulation *cannot tell us* what happens when AI is led by those forces. The questions "what if AI development is bottlenecked by materials, not by data?" or "what if AI deployment is constrained by demographic transition, not by politics?" are unanswerable with the current architecture.

To answer those questions, the simulation needs the missing causal factors.

---

## Appendix A: Module Census

| Module | Lines | Wired? | Active in 50y? |
|--------|-------|--------|----------------|
| `simulation.py` | 1065 | ✅ | yes |
| `agent.py` | 1156 | ✅ | yes |
| `world_state.py` | 1672 | ✅ | yes |
| `micro_interactions.py` | 410 | ✅ | yes |
| `meso_aggregator.py` | 410 | ✅ | yes |
| `macro_dynamics.py` | ? | ✅ | yes |
| `regime_transitions.py` | (P9) | ✅ | yes |
| `demography.py` | ? | ✅ | yes (point events) |
| `faction_lifecycle.py` | ? | ✅ | yes |
| `migration_flows.py` | (P8) | ✅ | partial |
| `capital_economy.py` | (P9) | ✅ | yes |
| `institutions.py` | (P9) | ✅ | yes |
| `cultural_diffusion.py` | (P9) | ✅ | weak |
| `federation_diplomacy.py` | (P9) | ✅ | weak |
| `federation_dynamics.py` | 432 | ✅ | yes (top-level) |
| `causal_ledger.py` | ? | ✅ | yes |
| `decision_feeder.py` | ? | ✅ | yes |
| `economy.py` | 634 | partial | ? |
| `ecology.py` | 462 | ❌ | NO |
| `discovery.py` | 432 | ❌ | NO |
| `great_persons.py` | 413 | ❌ | NO |
| `escalation_ladder.py` | 521 | ❌ | NO |
| `sovereignty.py` | 481 | ❌ | NO |
| `rituals.py` | 624 | ❌ | NO |
| `narrative.py` | 379 | post-hoc | n/a |
| `narrative_arcs.py` | 546 | post-hoc | n/a |
| `narrative_seeds.py` | 832 | post-hoc | n/a |
| `reconciliation.py` | 568 | ❌ | NO |
| `npc_dialogue.py` | 617 | ❌ | NO |
| `npc_depth.py` | 614 | ❌ | NO |
| `npc_ai.py` | 538 | partial | ? |
| `npc_memory.py` | 555 | partial | ? |
| `npc_generation.py` | 568 | init only | n/a |
| `goals.py` | 419 | partial | ? |
| `decision_state.py` | ? | partial | ? |
| `identity_game.py` | ? | partial | ? |
| `psychology.py` | ? | partial | ? |
| `batch_chronicles.py` | 507 | post-hoc | n/a |
| `prose_narrative.py` | 563 | post-hoc | n/a |
| `ghost.py` | 409 | post-hoc | n/a |
| `text_engine.py` | 506 | post-hoc | n/a |
| `events.py` | 472 | ✅ | yes |
| `world_template.py` | 433 | init only | n/a |
| `world_profiles.py` | 100+ | ✅ | yes |
| `web_server.py` | 583 | not run | n/a |
| `setup_wizard.py` | 646 | not run | n/a |
| `local_llm.py` | ? | optional | n/a |
| `persistence.py` | ? | yes | yes |
| `cross_world.py` | ? | ❌ | NO |
| `policy_drift.py` | ? | partial | ? |
| `faction_engine.py` | 465 | partial | ? |
| `seasons.py` | ? | partial | ? |
| `sovereignty.py` | 481 | ❌ | NO |
| `federation_orchestrator.py` | 308 | ✅ | yes (top-level) |

**Total: ~25,000 lines of simulation code. ~10,000 lines are dead code (modules that exist but don't run). ~15,000 lines drive the actual loop.**

## Appendix B: Recommended Phase 10 Scope

| Task | Name | Effort | Impact |
|------|------|--------|--------|
| 10.1 | Innovation / Discovery | M | High |
| 10.2 | Environment / Ecology | M | High |
| 10.3 | Demographics / Age structure | L | High |
| 10.4 | Diplomatic strength signal | S | High |
| 10.5 | Cross-world NPC movement | M | High |
| 10.6 | Causal graph edges | S | Med (analysis) |
| 10.7 | Inequality dynamics | S | High |
| 10.8 | Infrastructure dynamics | S | Med |
| 10.9 | Repression types | M | Med |
| 10.10 | Urbanization | L | Med |
| 10.11 | Education pipeline | L | Med |
| 10.12 | Disease ecology | M | Med |
| 10.13 | Resource depletion | S | Med |
| 10.14 | Conflict type differentiation | M | Med |
| 10.15 | Property rights / contract | L | Med |
| 10.16 | State capacity type | M | Med |
| 10.17 | Foreign policy | M | High |
| 10.18 | Path dependence / hysteresis | M | Med |
| 10.19 | Counterfactual branching | L | Research |

Where S = ~1 day, M = ~3 days, L = ~1 week.

**Phase 10 should focus on 10.1, 10.2, 10.3** as the high-impact trio. The other tasks can be sequenced afterward.
