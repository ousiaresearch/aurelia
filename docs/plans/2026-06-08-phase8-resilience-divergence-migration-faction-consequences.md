# Phase 8 Resilience, Divergence, Migration, and Faction Consequences Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make Aurelia's causal runner produce resilient, divergent, migratory, politically varied histories instead of uniform early macro collapse.

**Architecture:** Keep the Phase 7 barrier-synchronized causal runner. Add four missing political-metabolism layers: world-specific profiles, damped/recoverable macro dynamics, cohort-based cross-world migration that mutates populations, and richer faction outcomes that feed back into macro/demography/federation effects. Every new mechanic must emit causal ledger rows and appear in yearly reports.

**Tech Stack:** Python stdlib, SQLite, pytest, existing `~/aurelia/src_template/` causal modules, Cloudflare pusher remains bulk-only after run completion.

---

## Diagnosis From The 50-Year Run

The 50-year causal run proved Phase 7 works mechanically, but exposed calibration failures:

- Macro state saturated too early: legitimacy/GDP/fiscal/food hit `0`, repression/war/type tension hit `1` by the first decade.
- All worlds converged into the same collapse basin instead of diverging by institutions, geography, culture, and policy.
- Cross-world effects fired (`34,241 scheduled / 34,178 imported`) but report-level immigration/emigration stayed `0`.
- Faction lifecycle worked, but `integrated` became the dominant sink and consequences were too narrow.
- Yearly reports surface micro counters well, but not political arcs: reforms, suppression, exile, radicalization, coalitions, refugee crises.

This phase should not aim for optimism. It should aim for **dynamic range**: collapse, recovery, stagnation, reform, civil conflict, managed pluralism, flight, reception, and transnational contagion should all be reachable.

## Acceptance Gates

Before any 200-year production run, a 50-year / 1K NPC-world calibration run must satisfy these gates:

1. **Resilience gate**
   - No more than 2 of 5 worlds may pin the same macro key at exact `0.0` or `1.0` for 20 consecutive years.
   - At least 3 macro keys must show recovery after a negative shock in at least one world.

2. **Divergence gate**
   - By year 30, at least 3 worlds must have meaningfully different macro profiles.
   - Simple metric: average pairwise distance across `gdp_proxy`, `legitimacy`, `repression`, `public_health`, `food_security`, `war_pressure`, `border_openness` must be `>= 0.15`.

3. **Migration gate**
   - In a 50-year run, at least one world must record nonzero emigration and at least one target world must record nonzero immigration.
   - Source active population must actually decrease and target active population must actually increase from migration events, independent of births/deaths.

4. **Faction-consequence gate**
   - Final faction statuses may not be dominated by a single status above 75% of all factions unless the run narrative justifies it with explicit causal events.
   - At least 4 outcome classes must appear across a 50-year run: e.g. `integrated`, `suppressed`, `radicalized`, `exiled`, `splintered`, `legalized`, `governing_coalition`, `armed_conflict`, `victorious`, `dissolved`.

5. **Reporting gate**
   - `causal_summary.json` yearly reports must include `migration`, `macro_regime`, `resilience_events`, and `faction_outcomes` fields.
   - Decade summary must show macro movement and political outcomes, not only micro event counts.

---

## Task 1: Add World Profiles For Divergence

**Objective:** Give each world different macro baselines, recovery rates, migration attractiveness, border behavior, and faction-response tendencies.

**Files:**
- Create: `src_template/world_profiles.py`
- Test: `tests/test_phase8_profiles.py`

**Design:**

Create immutable per-world profiles. These are not lore prose; they are calibration priors consumed by mechanics.

```python
# src_template/world_profiles.py
from __future__ import annotations

DEFAULT_PROFILE = {
    "macro_baseline": {
        "gdp_proxy": 0.55,
        "food_security": 0.60,
        "water_security": 0.60,
        "public_health": 0.70,
        "legitimacy": 0.55,
        "repression": 0.30,
        "fiscal_capacity": 0.50,
        "infrastructure": 0.60,
        "border_openness": 0.50,
        "type_tension": 0.30,
        "war_pressure": 0.00,
    },
    "resilience": {
        "shock_absorption": 0.50,
        "recovery_rate": 0.010,
        "health_resilience": 0.010,
        "food_resilience": 0.010,
        "fiscal_resilience": 0.010,
    },
    "migration": {
        "push_sensitivity": 1.00,
        "pull_attractiveness": 1.00,
        "border_friction": 0.50,
        "refugee_tolerance": 0.50,
    },
    "factions": {
        "concession_bias": 0.25,
        "repression_bias": 0.25,
        "legalization_bias": 0.15,
        "splinter_bias": 0.15,
        "exile_bias": 0.10,
        "radicalization_bias": 0.10,
    },
}

WORLD_PROFILES = {
    "solara": {
        "macro_baseline": {"legitimacy": 0.62, "repression": 0.45, "fiscal_capacity": 0.58, "border_openness": 0.35, "type_tension": 0.38},
        "resilience": {"shock_absorption": 0.65, "recovery_rate": 0.012, "fiscal_resilience": 0.016},
        "migration": {"push_sensitivity": 0.80, "pull_attractiveness": 0.70, "border_friction": 0.75, "refugee_tolerance": 0.30},
        "factions": {"concession_bias": 0.20, "repression_bias": 0.45, "legalization_bias": 0.10, "splinter_bias": 0.15, "exile_bias": 0.20, "radicalization_bias": 0.20},
    },
    "valdris": {
        "macro_baseline": {"gdp_proxy": 0.66, "fiscal_capacity": 0.60, "inequality": 0.55, "legitimacy": 0.48},
        "resilience": {"shock_absorption": 0.55, "recovery_rate": 0.014, "food_resilience": 0.008},
        "migration": {"push_sensitivity": 1.00, "pull_attractiveness": 1.15, "border_friction": 0.45, "refugee_tolerance": 0.50},
        "factions": {"concession_bias": 0.32, "repression_bias": 0.25, "legalization_bias": 0.20, "splinter_bias": 0.20, "exile_bias": 0.08, "radicalization_bias": 0.15},
    },
    "mirithane": {
        "macro_baseline": {"public_health": 0.78, "food_security": 0.68, "legitimacy": 0.58, "repression": 0.20, "war_pressure": 0.02},
        "resilience": {"shock_absorption": 0.60, "recovery_rate": 0.016, "health_resilience": 0.020, "food_resilience": 0.016},
        "migration": {"push_sensitivity": 0.75, "pull_attractiveness": 1.05, "border_friction": 0.40, "refugee_tolerance": 0.70},
        "factions": {"concession_bias": 0.42, "repression_bias": 0.12, "legalization_bias": 0.28, "splinter_bias": 0.12, "exile_bias": 0.05, "radicalization_bias": 0.08},
    },
    "arkos": {
        "macro_baseline": {"border_openness": 0.62, "war_pressure": 0.08, "type_tension": 0.22, "legitimacy": 0.52},
        "resilience": {"shock_absorption": 0.45, "recovery_rate": 0.012, "fiscal_resilience": 0.010},
        "migration": {"push_sensitivity": 1.20, "pull_attractiveness": 1.20, "border_friction": 0.30, "refugee_tolerance": 0.80},
        "factions": {"concession_bias": 0.35, "repression_bias": 0.18, "legalization_bias": 0.22, "splinter_bias": 0.20, "exile_bias": 0.08, "radicalization_bias": 0.12},
    },
    "verge": {
        "macro_baseline": {"border_openness": 0.72, "legitimacy": 0.45, "repression": 0.12, "type_tension": 0.18, "fiscal_capacity": 0.38},
        "resilience": {"shock_absorption": 0.35, "recovery_rate": 0.018, "health_resilience": 0.012},
        "migration": {"push_sensitivity": 1.35, "pull_attractiveness": 1.35, "border_friction": 0.20, "refugee_tolerance": 0.90},
        "factions": {"concession_bias": 0.45, "repression_bias": 0.08, "legalization_bias": 0.32, "splinter_bias": 0.25, "exile_bias": 0.04, "radicalization_bias": 0.10},
    },
}

def profile(world_id: str) -> dict:
    merged = {k: dict(v) for k, v in DEFAULT_PROFILE.items()}
    custom = WORLD_PROFILES.get(world_id, {})
    for section, values in custom.items():
        merged.setdefault(section, {}).update(values)
    return merged

def macro_baseline(world_id: str) -> dict[str, float]:
    return profile(world_id)["macro_baseline"]
```

**Tests:**

```python
def test_profiles_are_distinct():
    import world_profiles
    solara = world_profiles.profile("solara")
    verge = world_profiles.profile("verge")
    assert solara["macro_baseline"]["repression"] > verge["macro_baseline"]["repression"]
    assert verge["migration"]["refugee_tolerance"] > solara["migration"]["refugee_tolerance"]
```

**Verification:**

Run:

```bash
pytest tests/test_phase8_profiles.py -v
```

Expected: profile tests pass.

**Commit:**

```bash
git add src_template/world_profiles.py tests/test_phase8_profiles.py
git commit -m "feat: add Aurelia world divergence profiles"
```

---

## Task 2: Replace Uniform Macro Baseline With World-Specific Baselines

**Objective:** Make `macro_dynamics.latest_state()` initialize from each world's profile instead of global `DEFAULT_STATE` only.

**Files:**
- Modify: `src_template/macro_dynamics.py`
- Test: `tests/test_causal_mechanics.py`

**Implementation:**

- Import `world_profiles` with the same package/flat fallback pattern used elsewhere.
- Add:

```python
def baseline_state(world_id: str) -> dict[str, float]:
    out = dict(DEFAULT_STATE)
    try:
        out.update(world_profiles.macro_baseline(world_id))
    except Exception:
        pass
    return out
```

- Change `latest_state(db, world_id)`:

```python
baseline = baseline_state(world_id)
if not row:
    return baseline
out = dict(baseline)
out.update({k: float(v) for k, v in state.items() if isinstance(v, (int, float))})
return out
```

**Tests:**

Add to `tests/test_causal_mechanics.py`:

```python
def test_macro_state_uses_world_specific_baselines(tmp_path):
    solara = make_world(tmp_path, "solara", n=20)
    verge = make_world(tmp_path, "verge", n=20)
    s = macro_dynamics.latest_state(solara, "solara")
    v = macro_dynamics.latest_state(verge, "verge")
    assert s["repression"] > v["repression"]
    assert v["border_openness"] > s["border_openness"]
```

**Verification:**

```bash
pytest tests/test_causal_mechanics.py::test_macro_state_uses_world_specific_baselines -v
```

Expected: pass.

**Commit:**

```bash
git add src_template/macro_dynamics.py tests/test_causal_mechanics.py
git commit -m "feat: initialize macro state from world profiles"
```

---

## Task 3: Add Macro Inertia, Shock Caps, and Recovery Pathways

**Objective:** Prevent macro variables from slamming to rails while allowing genuine collapse and genuine recovery.

**Files:**
- Modify: `src_template/macro_dynamics.py`
- Test: `tests/test_phase8_macro_resilience.py`

**Design:**

The current update is too direct:

```python
state[key] = clamp(state[key] + changes[key] + (baseline - state[key]) * 0.002)
```

Replace it with a political-metabolism update:

1. Aggregate raw changes as today.
2. Absorb some shock using `profile["resilience"]["shock_absorption"]`.
3. Cap per-tick movement by variable class.
4. Add conditional recovery when enabling resources exist.
5. Persist resilience events when a variable rebounds after stress.

**Suggested functions:**

```python
SHOCK_CAPS = {
    "gdp_proxy": 0.020,
    "food_security": 0.018,
    "water_security": 0.012,
    "public_health": 0.018,
    "legitimacy": 0.020,
    "repression": 0.018,
    "fiscal_capacity": 0.015,
    "infrastructure": 0.010,
    "border_openness": 0.018,
    "type_tension": 0.018,
    "war_pressure": 0.020,
}

def _cap_delta(key: str, delta: float) -> float:
    cap = SHOCK_CAPS.get(key, 0.015)
    return max(-cap, min(cap, float(delta)))

def _recovery_delta(key: str, state: dict, baseline: dict, resilience: dict) -> float:
    recovery_rate = float(resilience.get("recovery_rate", 0.010))
    fiscal = state.get("fiscal_capacity", 0.5)
    legitimacy = state.get("legitimacy", 0.5)
    repression = state.get("repression", 0.3)
    war = state.get("war_pressure", 0.0)

    # no free healing during total war/repression spiral
    governance_capacity = max(0.0, (fiscal * 0.45 + legitimacy * 0.35 + (1.0 - repression) * 0.20) - war * 0.25)
    if state[key] >= baseline[key]:
        return 0.0
    return (baseline[key] - state[key]) * recovery_rate * governance_capacity
```

For `repression`, `type_tension`, and `war_pressure`, recovery is downward toward baseline:

```python
def _tension_decay(key: str, state: dict, baseline: dict, resilience: dict) -> float:
    if state[key] <= baseline[key]:
        return 0.0
    civic_capacity = max(0.0, state.get("legitimacy", 0.5) * 0.4 + state.get("public_health", 0.6) * 0.2 + state.get("gdp_proxy", 0.5) * 0.2)
    return -(state[key] - baseline[key]) * float(resilience.get("recovery_rate", 0.010)) * civic_capacity
```

Emit `macro_resilience_recovery` causal events when recovery delta exceeds `0.002`.

**Tests:**

```python
def test_macro_shocks_are_capped(tmp_path):
    db = make_world(tmp_path, "solara", n=100)
    meso_aggregator.ensure_schema(db)
    db.execute("""
        INSERT INTO meso_signals (signal_id, tick_number, world_id, location_id, signal_type, magnitude, source_event_count, payload, created_at)
        VALUES ('shock', 1, 'solara', 'town_square', 'economic_stress', 100.0, 100, '{}', ?)
    """, (time.time(),))
    before = macro_dynamics.latest_state(db, "solara")
    macro_dynamics.apply_macro_dynamics(db, world_id="solara", tick_number=1)
    after = macro_dynamics.latest_state(db, "solara")
    assert before["gdp_proxy"] - after["gdp_proxy"] <= 0.025


def test_macro_state_can_recover_from_sub_baseline(tmp_path):
    db = make_world(tmp_path, "mirithane", n=100)
    macro_dynamics.ensure_schema(db)
    db.execute("INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)", (
        "mirithane", 0, json.dumps({"public_health": 0.30, "fiscal_capacity": 0.70, "legitimacy": 0.70, "repression": 0.10, "war_pressure": 0.0}), time.time()
    ))
    before = macro_dynamics.latest_state(db, "mirithane")["public_health"]
    macro_dynamics.apply_macro_dynamics(db, world_id="mirithane", tick_number=1)
    after = macro_dynamics.latest_state(db, "mirithane")["public_health"]
    assert after > before
```

**Verification:**

```bash
pytest tests/test_phase8_macro_resilience.py -v
pytest tests/test_causal_mechanics.py -v
```

Expected: all pass.

**Commit:**

```bash
git add src_template/macro_dynamics.py tests/test_phase8_macro_resilience.py tests/test_causal_mechanics.py
git commit -m "feat: add macro resilience and recovery dynamics"
```

---

## Task 4: Add Migration Schema and Cohort-Based Population Mutation

**Objective:** Turn migration pressure/refugee effects into actual source-world emigration and target-world immigration counts.

**Files:**
- Modify: `src_template/demography.py`
- Create: `src_template/migration_flows.py`
- Test: `tests/test_phase8_migration.py`

**Design:**

Do not attempt full identity transfer in this first pass. Use deterministic cohorts:

- Source world receives `refugee_outflow` or `labor_outflow` delayed effect.
- Source marks selected active NPCs as `emigrated`, records `demographic_events.event_type='emigration'`.
- Target world receives paired `refugee_inflow` or `labor_inflow` delayed effect.
- Target creates new active NPC rows with `properties.origin_world`, `properties.migration_group_id`, `properties.migration_type`, records `demographic_events.event_type='immigration'`.
- Both emit causal ledger events.

This preserves population mutation and yearly counts without cross-DB row copying.

**Schema:**

In `demography.ensure_schema()` add:

```sql
CREATE TABLE IF NOT EXISTS migration_cohorts (
    cohort_id TEXT PRIMARY KEY,
    tick_number INTEGER NOT NULL,
    world_id TEXT NOT NULL,
    direction TEXT NOT NULL,
    source_world TEXT NOT NULL,
    target_world TEXT NOT NULL,
    migration_type TEXT NOT NULL,
    cohort_size INTEGER NOT NULL,
    cause TEXT DEFAULT '',
    payload TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_migration_cohorts_world_tick
    ON migration_cohorts(world_id, tick_number, direction);
```

**New module outline:**

```python
# src_template/migration_flows.py
from __future__ import annotations
import json, random, time, uuid

try:
    from . import causal_ledger, demography, macro_dynamics, world_profiles
except Exception:
    import causal_ledger, demography, macro_dynamics, world_profiles


def run_migration_flows(db, *, world_id: str, tick_number: int, rng: random.Random | None = None) -> dict[str, int]:
    demography.ensure_schema(db)
    causal_ledger.ensure_schema(db)
    rng = rng or random.Random()
    counts = {"immigration": 0, "emigration": 0}

    effects = causal_ledger.due_effects(db, tick_number, world_id)
    for effect in effects:
        et = effect["effect_type"]
        if et in {"refugee_outflow", "labor_outflow"}:
            counts["emigration"] += _apply_outflow(db, world_id, tick_number, effect, rng)
            causal_ledger.mark_effect_applied(db, effect["effect_id"])
        elif et in {"refugee_inflow", "labor_inflow"}:
            counts["immigration"] += _apply_inflow(db, world_id, tick_number, effect, rng)
            causal_ledger.mark_effect_applied(db, effect["effect_id"])
    return counts
```

**Cohort sizing rule:**

```python
def _cohort_size(effect, state, profile, pop):
    mag = max(0.0, float(effect["magnitude"] or 0.0))
    pressure = mag * float(profile["migration"].get("push_sensitivity", 1.0))
    raw = int(pop * min(0.015, pressure * 0.004))
    return max(0, min(raw, max(25, pop // 50)))
```

**Important:** `demographic_events.yearly_counts()` already recognizes `immigration` and `emigration`; after this task, yearly reports will become nonzero without changing the report API.

**Tests:**

- Forced source outflow marks active NPCs as `emigrated` and records `emigration` events.
- Forced target inflow creates active immigrant NPCs and records `immigration` events.
- `demography.yearly_counts()` includes both.

**Verification:**

```bash
pytest tests/test_phase8_migration.py -v
```

Expected: migration tests pass.

**Commit:**

```bash
git add src_template/demography.py src_template/migration_flows.py tests/test_phase8_migration.py
git commit -m "feat: add causal migration population mutation"
```

---

## Task 5: Schedule Paired Source/Target Migration Effects At Federation Barrier

**Objective:** Make `federation_effects.resolve_outbound_effects()` create paired outflow/inflow effects so migration has both source and target consequences.

**Files:**
- Modify: `src_template/federation_effects.py`
- Test: `tests/test_phase8_migration.py`

**Current Problem:**

`migration_pressure` and `faction_repressed` schedule only `refugee_inflow` to neighboring targets. The source world never receives an outflow effect, so source population cannot decrease from migration.

**Implementation:**

For migration-producing events:

- Create a stable `migration_group_id`.
- Schedule `refugee_outflow` or `labor_outflow` for the source world at `tick+1`.
- Schedule matching `refugee_inflow` or `labor_inflow` for each selected target at `tick+1`.
- Include same group ID and source/target in payload.

Pseudo-code inside `resolve_outbound_effects()`:

```python
if row["event_type"] in {"migration_pressure", "faction_repressed"}:
    group_id = f"mig:{source}:{tick_number}:{row['event_id']}:{target}"
    # source effect
    causal_ledger.schedule_effect(
        federation_db,
        source_event_id=row["event_id"],
        apply_tick=tick_number + 1,
        target_world_id=source,
        target_scope="country",
        effect_type="refugee_outflow",
        magnitude=mag,
        payload={"migration_group_id": group_id, "source_world": source, "target_world": target, "source_event_type": row["event_type"]},
    )
    # target effect
    causal_ledger.schedule_effect(
        federation_db,
        source_event_id=row["event_id"],
        apply_tick=tick_number + 1,
        target_world_id=target,
        target_scope="country",
        effect_type="refugee_inflow",
        magnitude=mag,
        payload={"migration_group_id": group_id, "source_world": source, "target_world": target, "source_event_type": row["event_type"]},
    )
```

**Tests:**

```python
def test_migration_pressure_schedules_paired_outflow_and_inflow(tmp_path):
    fed = sqlite3.connect(tmp_path / "fed.db")
    fed.row_factory = sqlite3.Row
    causal_ledger.ensure_schema(fed)
    causal_ledger.emit_event(fed, tick_number=1, world_id="solara", layer="meso", event_type="migration_pressure", scope="country", magnitude=1.0, valence=-1.0)
    federation_effects.resolve_outbound_effects(fed, tick_number=1, worlds=["solara", "valdris"])
    out = causal_ledger.due_effects(fed, 2, "solara")
    incoming = causal_ledger.due_effects(fed, 2, "valdris")
    assert any(e["effect_type"] == "refugee_outflow" for e in out)
    assert any(e["effect_type"] == "refugee_inflow" for e in incoming)
```

**Verification:**

```bash
pytest tests/test_phase8_migration.py::test_migration_pressure_schedules_paired_outflow_and_inflow -v
```

Expected: pass.

**Commit:**

```bash
git add src_template/federation_effects.py tests/test_phase8_migration.py
git commit -m "feat: schedule paired migration effects across federation"
```

---

## Task 6: Insert Migration Into The Barrier Tick Pipeline

**Objective:** Run migration after macro effects are imported/applied and before yearly reports are built.

**Files:**
- Modify: `src_template/federation_orchestrator.py`
- Test: `tests/test_federation_orchestrator.py`

**Implementation:**

- Import `migration_flows`.
- In `run_world_barrier_tick()`, call after `macro_dynamics.apply_macro_dynamics()` and before `demography.run_demography()`:

```python
migration = migration_flows.run_migration_flows(
    db,
    world_id=world_id,
    tick_number=tick_number,
    rng=rng,
)
```

- Include in return payload:

```python
"immigration": migration["immigration"],
"emigration": migration["emigration"],
```

**Ordering Rationale:**

1. Federation imports delayed effects at tick start.
2. Macro applies non-migration effects and updates state.
3. Migration consumes migration effects and mutates population.
4. Demography applies births/deaths on post-migration living population.
5. Factions react to post-migration pressure.

**Tests:**

Extend `test_barrier_runner_produces_causal_smoke()` or add a new forced run test that injects migration pressure and checks yearly reports eventually show migration. Keep it small: 2 worlds, 2 years, high forced migration event if needed.

**Verification:**

```bash
pytest tests/test_federation_orchestrator.py -v
```

Expected: pass and no processing-order regression.

**Commit:**

```bash
git add src_template/federation_orchestrator.py tests/test_federation_orchestrator.py
git commit -m "feat: run migration inside causal barrier ticks"
```

---

## Task 7: Expand Faction Outcome Space

**Objective:** Replace the narrow integrated/repressed/escalated/declined lifecycle with a richer consequence state machine.

**Files:**
- Modify: `src_template/faction_lifecycle.py`
- Test: `tests/test_phase8_factions.py`

**New statuses/outcomes:**

- `integrated` — demands partially met; positive legitimacy, possible fiscal cost.
- `legalized` — faction becomes tolerated institution; reduces war pressure, keeps member count.
- `governing_coalition` — faction enters government; boosts legitimacy if repression low, raises type tension if contested.
- `suppressed` — short-term member loss; increases repression and future radicalization memory.
- `exiled` — source loses members, target receives migration pressure/refugee effect.
- `splintered` — creates child faction with more radical grievance.
- `radicalized` — influence and war pressure rise; may escalate to armed conflict.
- `victorious` — rare; faction forces regime reform or sovereignty event.
- `dissolved` — pressure decays with no major consequence.

**Implementation Design:**

Add weighted outcome selection:

```python
OUTCOME_EFFECTS = {
    "integrated": {"legitimacy": +0.012, "repression": -0.006, "fiscal_capacity": -0.004},
    "legalized": {"legitimacy": +0.008, "war_pressure": -0.008, "type_tension": -0.004},
    "governing_coalition": {"legitimacy": +0.015, "fiscal_capacity": +0.004, "repression": -0.010},
    "suppressed": {"repression": +0.014, "legitimacy": -0.010, "war_pressure": +0.006},
    "exiled": {"border_openness": -0.006, "legitimacy": -0.006, "war_pressure": +0.004},
    "splintered": {"war_pressure": +0.010, "type_tension": +0.006},
    "radicalized": {"war_pressure": +0.016, "repression": +0.006, "legitimacy": -0.008},
    "victorious": {"legitimacy": +0.020, "repression": -0.018, "fiscal_capacity": -0.010},
    "dissolved": {"war_pressure": -0.004},
}
```

Add helper:

```python
def _weighted_outcome(state, profile, fac, score, rng):
    weights = dict(profile["factions"])
    # state modifiers
    weights["repression_bias"] += state["repression"] * 0.35
    weights["concession_bias"] += state["legitimacy"] * 0.20 + (1.0 - state["repression"]) * 0.20
    weights["radicalization_bias"] += state["war_pressure"] * 0.25 + score * 0.20
    weights["splinter_bias"] += max(0.0, score - 0.5) * 0.15
    # map biases to concrete outcomes
    options = [
        ("integrated", weights["concession_bias"] * 0.45),
        ("legalized", weights["legalization_bias"]),
        ("governing_coalition", weights["concession_bias"] * 0.12 if score > 0.55 else 0.0),
        ("suppressed", weights["repression_bias"] * 0.55),
        ("exiled", weights["exile_bias"] + state["border_openness"] * 0.05),
        ("splintered", weights["splinter_bias"]),
        ("radicalized", weights["radicalization_bias"]),
        ("victorious", 0.02 if score > 0.80 and state["legitimacy"] < 0.25 else 0.0),
        ("dissolved", 0.04 if score < 0.10 else 0.0),
    ]
    return choose_weighted(options, rng)
```

**Macro consequence application:**

Options:

- Minimal: emit causal event `faction_<outcome>` and let `macro_dynamics` consume those event types in a later task.
- Better: add `apply_faction_macro_effect(db, world_id, tick_number, outcome, magnitude)` in `faction_lifecycle.py` that inserts a `meso_signals` row or emits causal event for `macro_dynamics` to consume next tick.

Use the second option only if it does not create circular imports beyond existing `macro_dynamics` import.

**Splinter behavior:**

When outcome is `splintered`, create a child faction:

```python
child_id = f"{fac['faction_id']}:splinter:{tick_number}:{uuid.uuid4().hex[:6]}"
child_members = max(3, int(member_count * 0.25))
parent_members = max(0, member_count - child_members)
```

**Exile behavior:**

When outcome is `exiled`, emit `faction_exiled` with magnitude proportional to members. `federation_effects` should map `faction_exiled` to refugee outflow/inflow.

**Tests:**

- Force low legitimacy + high repression → outcome is one of `suppressed`, `exiled`, `radicalized`, not always `integrated`.
- Force high legitimacy + low repression → outcome can be `legalized`/`integrated`/`governing_coalition`.
- Splinter creates a second faction.
- Outcome emits causal event with `event_type='faction_<outcome>'`.

**Verification:**

```bash
pytest tests/test_phase8_factions.py -v
pytest tests/test_causal_mechanics.py::test_faction_lifecycle_creates_or_changes_consequences -v
```

Expected: all pass.

**Commit:**

```bash
git add src_template/faction_lifecycle.py tests/test_phase8_factions.py tests/test_causal_mechanics.py
git commit -m "feat: expand Aurelia faction consequence outcomes"
```

---

## Task 8: Teach Federation Effects About New Faction Outcomes

**Objective:** Let richer faction outcomes propagate across worlds.

**Files:**
- Modify: `src_template/federation_effects.py`
- Test: `tests/test_phase8_factions.py`

**Add mappings:**

```python
EVENT_EFFECTS.update({
    "faction_suppressed": ("ideology_diffusion", 0.05),
    "faction_exiled": ("refugee_inflow", 0.10),
    "faction_splintered": ("ideology_diffusion", 0.10),
    "faction_radicalized": ("ideology_diffusion", 0.12),
    "faction_legalized": ("recognition_pressure", 0.04),
    "faction_governing_coalition": ("recognition_pressure", 0.06),
    "faction_victorious": ("recognition_pressure", 0.12),
})
```

Special-case `faction_exiled` to produce paired migration effects exactly like `migration_pressure`.

**Update query event list:**

The SQL in `resolve_outbound_effects()` currently hardcodes event types. Replace it with dynamic placeholders from `EVENT_EFFECTS.keys()` to avoid future omissions.

```python
event_types = tuple(EVENT_EFFECTS.keys())
placeholders = ",".join("?" for _ in event_types)
rows = federation_db.execute(f"SELECT * FROM causal_events WHERE tick_number=? AND event_type IN ({placeholders})", (tick_number, *event_types)).fetchall()
```

**Tests:**

- `faction_exiled` schedules outflow/inflow.
- `faction_radicalized` schedules ideology diffusion.
- Dynamic query catches newly added event types.

**Verification:**

```bash
pytest tests/test_phase8_factions.py tests/test_phase8_migration.py -v
```

Expected: pass.

**Commit:**

```bash
git add src_template/federation_effects.py tests/test_phase8_factions.py tests/test_phase8_migration.py
git commit -m "feat: propagate richer faction outcomes across federation"
```

---

## Task 9: Expand Yearly Reports And Decade Summaries

**Objective:** Make outputs tell the whole-run story: resilience, divergence, migration, and faction outcomes.

**Files:**
- Modify: `src_template/yearly_report.py`
- Modify or create helper: `scripts/decade_summary.py` or integrate into `causal_run.py` if one exists there
- Test: `tests/test_phase8_reporting.py`

**Yearly report additions:**

```python
"macro_regime": classify_macro_regime(macro),
"resilience_events": count/select causal_events where event_type in ('macro_resilience_recovery', 'macro_tension_decay'),
"faction_outcomes": {status: count},
"migration_flows": {
    "immigration": demo["immigration"],
    "emigration": demo["emigration"],
    "net": demo["immigration"] - demo["emigration"],
},
```

**Macro regime classifier:**

```python
def classify_macro_regime(macro: dict) -> str:
    if macro["war_pressure"] > 0.70 and macro["legitimacy"] < 0.30:
        return "civil_conflict"
    if macro["repression"] > 0.70 and macro["legitimacy"] < 0.40:
        return "authoritarian_crisis"
    if macro["gdp_proxy"] > 0.55 and macro["legitimacy"] > 0.55 and macro["war_pressure"] < 0.30:
        return "stable_growth"
    if macro["public_health"] < 0.30 or macro["food_security"] < 0.25:
        return "humanitarian_stress"
    if macro["border_openness"] > 0.60 and macro["type_tension"] < 0.35:
        return "open_pluralism"
    return "contested_stability"
```

**Decade summary additions:**

The 50-year run summary should include:

- Per-decade macro regime distribution.
- Migration net by world.
- Faction outcome diversity index.
- Macro recovery events by world.
- Divergence metric across worlds.

**Tests:**

- A known macro vector classifies correctly.
- Yearly report includes new keys.
- Migration net is computed.

**Verification:**

```bash
pytest tests/test_phase8_reporting.py -v
```

Expected: pass.

**Commit:**

```bash
git add src_template/yearly_report.py tests/test_phase8_reporting.py scripts/decade_summary.py
git commit -m "feat: report macro regimes migration and faction outcomes"
```

---

## Task 10: Add Calibration Metrics Script

**Objective:** Automatically judge whether a run passes the Phase 8 gates before pushing to production Cloudflare.

**Files:**
- Create: `scripts/evaluate_phase8_run.py`
- Test: optional `tests/test_phase8_evaluator.py`

**CLI:**

```bash
python3 scripts/evaluate_phase8_run.py /tmp/aurelia-causal-run/output/causal_summary.json
```

**Output:**

```json
{
  "passed": false,
  "gates": {
    "resilience": {"passed": true, "details": "..."},
    "divergence": {"passed": false, "pairwise_distance": 0.09},
    "migration": {"passed": true, "immigration": 144, "emigration": 144},
    "faction_consequences": {"passed": true, "outcome_classes": 6},
    "reporting": {"passed": true}
  }
}
```

**Core metrics:**

- Pairwise macro distance by year.
- Rail-pinning streak detection.
- Migration totals by world.
- Faction status entropy / diversity.
- Outcome class count.

**Verification:**

Run against current failed 50-year run first. Expected: fail migration/resilience/divergence.

```bash
python3 scripts/evaluate_phase8_run.py /tmp/aurelia-causal-run/output/causal_summary.json
```

Then after implementation run a new 50-year calibration and require pass before Cloudflare push.

**Commit:**

```bash
git add scripts/evaluate_phase8_run.py tests/test_phase8_evaluator.py
git commit -m "feat: add Phase 8 calibration evaluator"
```

---

## Task 11: Run 5-Year, 20-Year, Then 50-Year Calibration Ladder

**Objective:** Prove the system improves without wasting long-run compute.

**Commands:**

1. Unit tests:

```bash
cd ~/aurelia
pytest -v
```

2. 5-year forced sanity:

```bash
python3 causal_run.py --clean --years 5 --npcs 300 --max-interactions 200 --seed 20260608
python3 scripts/evaluate_phase8_run.py /tmp/aurelia-causal-run/output/causal_summary.json
```

Expected:

- effects scheduled/imported > 0
- at least one faction outcome beyond `integrated`
- migration may be zero unless forced by shocks; okay for 5-year smoke

3. 20-year smoke:

```bash
python3 causal_run.py --clean --years 20 --npcs 1000 --max-interactions 250 --seed 20260608
python3 scripts/evaluate_phase8_run.py /tmp/aurelia-causal-run/output/causal_summary.json
```

Expected:

- macro variables not pinned uniformly
- some divergence visible
- at least one migration event if migration pressure arises

4. 50-year calibration:

```bash
python3 causal_run.py --clean --years 50 --npcs 1000 --max-interactions 250 --seed 20260608
python3 scripts/evaluate_phase8_run.py /tmp/aurelia-causal-run/output/causal_summary.json
```

Expected:

- Phase 8 gates pass.
- Only then bulk-push to Cloudflare.

**Commit:**

If calibration changes require tuning, commit each tuning unit separately:

```bash
git add src_template/*.py tests/*.py scripts/evaluate_phase8_run.py
git commit -m "tune: calibrate Phase 8 macro and migration dynamics"
```

---

## Task 12: Update Cloudflare Pusher Only If Report Shape Changes

**Objective:** Keep Cloudflare ingestion accurate without putting HTTP in the hot loop.

**Files:**
- Modify if needed: `aurelia_cf_pusher.py`

**Rules:**

- Do not push per-tick.
- Do not push failed calibration runs to production unless explicitly requested.
- Continue using `causal_summary.json` for causal yearly reports.
- If yearly reports gain new fields not supported by D1, preserve them in `notable_events` JSON until the Worker schema gets a proper run-scoped migration.

**Recommended near-term behavior:**

- Keep D1 yearly rows simple: population/births/deaths/migration/faction_count/notable_events.
- Put rich Phase 8 fields into R2 artifacts:
  - `aurelia/runs/phase8-calibration/latest/causal_summary.json`
  - `aurelia/runs/phase8-calibration/latest/decade_summary.json`
  - `aurelia/runs/phase8-calibration/latest/evaluation.json`

**Future schema work, separate plan:**

Add `run_id` to D1 yearly snapshots and an `aurelia_runs` table. This is important, but do not block Phase 8 mechanics on Worker migrations.

---

## Implementation Order Summary

1. `world_profiles.py` — divergence priors.
2. `macro_dynamics.py` baseline integration.
3. `macro_dynamics.py` inertia/recovery/caps.
4. `migration_flows.py` + demography schema.
5. `federation_effects.py` paired migration effects.
6. `federation_orchestrator.py` migration pipeline hook.
7. `faction_lifecycle.py` richer outcome state machine.
8. `federation_effects.py` richer outcome propagation.
9. `yearly_report.py` richer reporting.
10. `scripts/evaluate_phase8_run.py` acceptance gate automation.
11. Calibration ladder: 5y → 20y → 50y.
12. Cloudflare push only after local evaluator passes.

## Non-Goals

- Do not run 200 years until a 50-year Phase 8 calibration passes.
- Do not add LLM prose during calibration; simulation first, narration second.
- Do not put Cloudflare writes in the tick loop.
- Do not implement true cross-DB individual identity transfer in this phase; cohort migration is enough to prove demographic and political flow.
- Do not make recovery guaranteed. Recovery must be possible, not scripted.

## Success Definition

A successful Phase 8 run should read like five related but distinct histories:

- Solara may suppress early unrest but pay legitimacy costs and export exiles.
- Valdris may absorb labor flows and stabilize economically while inequality strains factions.
- Mirithane may recover health/food shocks better and legalize movements earlier.
- Arkos may become a volatile refugee corridor and intervention actor.
- The Verge may receive migrants, birth new coalitions, and destabilize from openness rather than repression.

If all five worlds still collapse into the same macro state by year 10, Phase 8 has failed.
