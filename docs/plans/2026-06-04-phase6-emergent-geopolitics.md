# Aurelia Phase 6 — Emergent Geopolitics

> **For Palantir:** Self-execute in order. Module 1 first (always). Commit each module.

**Goal:** Add the collective-action layer that Phase 4's individual physics feeds into — factions, organized conflict, sovereignty emergence. Phase 4 generates the weather (NPC dissatisfaction, diplomatic tension, Glim anomalies, economic drift). Phase 6 turns weather into storms.

**The Core Insight:** Phase 4 is a *condition engine* — it tells you *who* is unhappy, *how much* pressure has accumulated, *which* diplomatic pair is deteriorating. But it has no mechanism for those conditions to organize into a *faction with demands*, or for a faction to *escalate through a conflict ladder*, or for a successful faction to *become a sovereign entity*. Phase 6 adds the three missing nouns:

1. **Factions** — organized groups of NPCs with shared grievances, leaders, membership, demands.
2. **Escalation Ladder** — a state machine: dormant → grievance → organization → ultimatum → skirmish → armed conflict → war.
3. **Sovereignty Pipeline** — when a faction controls territory + population + resources, it can declare independence and become a new country.

**Design Principles (carried forward):**
- **Decision-driven, not timer-driven.** Factions don't form on a schedule. They form because enough NPCs accumulate enough shared grievance.
- **Probability-modulated, not condition-gated.** Like narrative seeds, faction formation uses base probability × multipliers from existing state. No explosion of AND conditions.
- **Cascading consequences.** A rebellion in Solara degrades its trade relations, which strains Arkos's economy, which increases Glim pressure in Arkos — all through existing Phase 4 feeders.
- **Observable at every stage.** The /api/growth endpoint should show faction counts, conflict states, sovereignty progress — so we can watch the world change.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        PHASE 6 LAYER                              │
│                                                                    │
│  ┌──────────┐    ┌───────────────┐    ┌───────────────────────┐   │
│  │ Factions  │───▶│ Escalation    │───▶│ Sovereignty Pipeline   │   │
│  │ Engine    │    │ Ladder        │    │                       │   │
│  └──────────┘    └───────────────┘    └───────────────────────┘   │
│       │                 │                       │                  │
│       ▼                 ▼                       ▼                  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Federation Event Bus (POST /events)             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│       │                 │                       │                  │
└───────┼─────────────────┼───────────────────────┼──────────────────┘
        │                 │                       │
        ▼                 ▼                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                   PHASE 4 PHYSICS LAYER                             │
│  decision_feeder ◄── feeds back into ──▶ decision_state             │
│  population.py  │  economic_drift.py  │  narrative_seeds.py         │
└────────────────────────────────────────────────────────────────────┘
```

Three new modules, one new table, zero new scheduled events.

---

## Module 1: Faction Engine

### Goal
Allow NPCs with shared grievances to organize into named factions with leaders, membership rosters, demands, and influence scores. Factions become the unit of collective action that the escalation ladder and sovereignty pipeline consume.

### Why First
Without factions, there's nothing to escalate. The faction engine turns individual dissatisfaction into organized power — it's the bridge from Phase 4 "weather" to Phase 6 "storms."

### Design
- **Formation trigger:** Narrative seed "rebellion" fires → roll faction formation check (probability × grievance density). Also: organic formation when ≥N NPCs in a region share a grievance variable above threshold.
- **Membership:** NPCs join based on alignment score (weighted by grievance match, location proximity, social ties from bounded graph).
- **Leadership:** Highest-influence member becomes leader. Leader death/replacement handled.
- **Demands:** Derived from the grievance vector that spawned the faction (decommissioning abolition, citizenship, land reform, etc.).
- **Influence:** ∑ member_satisfaction × member_count × (1 - security). Grows faction power.
- **Data:** New table `factions` in each world DB. No coordinator-level schema needed — factions are visible through federation events.

### Tasks

#### Task 1.1: Add `factions` table to world DB schema

**Files:** `src_template/world_state.py` (init_db section)

```sql
CREATE TABLE IF NOT EXISTS factions (
    faction_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    world_id TEXT NOT NULL,
    region TEXT,
    status TEXT NOT NULL DEFAULT 'forming',  -- forming, active, ultimatum, skirmish, conflict, war, dissolved, sovereign
    primary_grievance TEXT,
    demand TEXT,
    leader_npc_id TEXT,
    member_count INTEGER DEFAULT 0,
    influence REAL DEFAULT 0.0,
    founded_tick INTEGER,
    dissolved_tick INTEGER,
    metadata JSON DEFAULT '{}',
    created_at REAL NOT NULL
)
```

#### Task 1.2: Create `faction_engine.py`

**New file:** `src_template/faction_engine.py`

Functions:
- `check_faction_formation(db, world_id, tick_number, growth_snapshot, decision_states, npc_locations)` — checks if conditions are ripe for a new faction to form. Uses grievance density scan: count NPCs in same region with shared grievance variable (satisfaction<0.3, security<0.3, observed_injustice>0.5) above formation threshold (≥15 NPCs in same region). Returns a formation event dict or None.
- `form_faction(db, name, world_id, region, grievance, demand, leader_id, initial_members)` — creates faction record, assigns members, sets status='active'.
- `recruit_members(db, faction_id, npc_pool)` — check alignment for unaffiliated NPCs in region, recruit aligned ones (probability-based).
- `update_faction_influence(db, faction_id)` — recalculate influence from member states.
- `select_faction_leader(db, faction_id)` — promote highest-influence member.
- `dissolve_faction(db, faction_id, reason)` — set status='dissolved', log reason.
- `get_active_factions(db, world_id)` — list all active factions.

**Grievance types (from Phase 4 decision variables):**
| Grievance | Threshold | Demand Example |
|---|---|---|
| Oppression | security < 0.3, observed_injustice > 0.5 | "End decommissioning" |
| Poverty | satisfaction < 0.3, economic_stability < 0.3 | "Land reform" |
| Displacement | restlessness > 0.7, location contains 'verge' | "Right of return" |
| Personhood | npc_type='glim', anomaly_pressure > 0.5 | "Recognition of personhood" |
| Autonomy | region identity, connectedness > 0.7 | "Regional autonomy" |

#### Task 1.3: Wire faction check into simulation tick

**Files:** `src_template/simulation.py`

After narrative seeds check, before population dynamics:
```python
# Phase 6: Faction check
from .faction_engine import check_faction_formation, update_all_factions
faction_event = check_faction_formation(db, world_id, tick_number, growth, decision_states, locations)
if faction_event:
    tick_events.append(faction_event)
update_all_factions(db, world_id, tick_number)
```

#### Task 1.4: Add faction stats to /api/growth

**Files:** `aurelia_coordinator.py` (build_growth_snapshot)

Add faction count per world to growth snapshot data.

**Verification:**
1. Start coordinator, start one world daemon
2. Let run 5+ ticks
3. Hit `/api/growth` — should see `faction_count` in snapshot
4. Force formation: inject 20 NPCs with security<0.2 in same region → next tick should form a faction

---

## Module 2: Escalation Ladder

### Goal
Define a state machine for how organized factions escalate from grievance to violence. Each step is a decision point: does the faction escalate, does the government respond, does a diplomatic incident trigger? No step fires on a timer — each is a probability check modulated by world state.

### Design
- **Ladder states:** dormant → grievance → organization → ultimatum → skirmish → armed_conflict → war → (resolution or dissolution)
- **Escalation check:** Each tick, active factions roll escalation probability. Base probability × influence multiplier × government response modifier × diplomatic tension modifier.
- **De-escalation:** Government concessions reduce influence, which reduces escalation probability.
- **Government response:** The "government" is modeled as the dominant faction or the baseline power structure. Government has: repression_capacity, concession_willingness, external_support.
- **Cross-world:** When a faction in Solara escalates to armed conflict, Arkos and Valdris roll for intervention based on their diplomatic relations with Solara.

### Tasks

#### Task 2.1: Create `escalation_ladder.py`

**New file:** `src_template/escalation_ladder.py`

Data structures:
```python
LADDER = ["dormant", "grievance", "organization", "ultimatum", "skirmish", "armed_conflict", "war"]

ESCALATION_BASE = {
    "dormant->grievance": 0.01,
    "grievance->organization": 0.005,
    "organization->ultimatum": 0.003,
    "ultimatum->skirmish": 0.002,
    "skirmish->armed_conflict": 0.0015,
    "armed_conflict->war": 0.001,
}
```

Functions:
- `check_escalation(db, faction, world_state, diplomatic_relations, tick_number)` — roll escalation check. Returns escalation event or None.
- `check_deescalation(db, faction, government_concessions)` — if government meets demands, roll de-escalation.
- `apply_escalation_effects(db, faction, new_state, world_id)` — when escalations happen, create federation events, apply population pressure (migration outflow, mortality spike at conflict+ levels).
- `check_intervention(db, faction, world_id, diplomatic_relations, all_worlds)` — other countries roll for intervention when a faction reaches 'skirmish' or above.
- `get_conflict_intensity(faction)` — returns 0.0–1.0 based on ladder position.

**Modifier sources:**
| Modifier | Source | Effect |
|---|---|---|
| Faction influence | faction_engine | × (1 + influence) |
| Government repression | world_state.government | × (1 - repression_capacity) |
| Diplomatic tension | aurelia_diplomacy | × (1 + avg_pair_tension) |
| External support | intervention check | × (1 + external_support) |
| Glim anomaly count | growth snapshot | × (1 + anomalies/100) |
| Economic instability | economic_drift | × (1 + instability) |

#### Task 2.2: Add `diplomatic_incidents` table to coordinator DB

**Files:** `aurelia_coordinator.py` (init_db)

```sql
CREATE TABLE IF NOT EXISTS diplomatic_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_type TEXT NOT NULL,
    source_world_id TEXT NOT NULL,
    target_world_id TEXT,
    faction_id TEXT,
    severity REAL DEFAULT 0.5,
    title TEXT,
    description TEXT,
    tick_number INTEGER,
    created_at REAL NOT NULL,
    resolved INTEGER DEFAULT 0
)
```

#### Task 2.3: Wire escalation into simulation tick

**Files:** `src_template/simulation.py`

After faction update:
```python
from .escalation_ladder import check_all_escalations, apply_escalation_fallout
escalations = check_all_escalations(db, world_id, tick_number, faction_engine.get_active_factions(db, world_id))
for esc in escalations:
    tick_events.append(esc)
apply_escalation_fallout(db, world_id, escalations, tick_number)
```

#### Task 2.4: Add conflict state to /api/growth

**Files:** `aurelia_coordinator.py` (build_growth_snapshot)

Add: `active_conflicts`, `conflict_intensity_max`, `factions_at_war`.

**Verification:**
1. Start with a world that has an active faction
2. Inject high influence (1.0) + low government repression
3. Run 10+ ticks — faction should escalate through ladder stages
4. Check /api/growth for conflict data
5. Verify that at 'skirmish' level, population events fire (migration, mortality)

---

## Module 3: Sovereignty Pipeline

### Goal
When a faction controls territory, population, and resources, and has survived conflict, it can declare independence and become a new sovereign country. This is the ultimate expression of emergent geopolitics: a world that started with 5 countries can become 6, 7, or more — or collapse back to fewer.

### Design
- **Sovereignty thresholds:** The faction must have: (a) territory_control ≥ 0.6, (b) member_count ≥ 500, (c) survived ≥ 3 ticks at 'armed_conflict' or higher, (d) external recognition from ≥ 1 other country.
- **Declaration:** When thresholds are met, roll declaration probability (base 0.01 × influence × territory_control × external_recognition_count).
- **Recognition:** After declaration, other countries roll recognition check based on diplomatic relations. Recognition grants trade, diplomacy, and military access.
- **New country creation:** When recognized by ≥ 2 countries, the faction becomes a new world entry. Its region splits from the parent country. New daemon can be spawned (manual — we notify but don't auto-spawn).
- **Secession cascade:** When one faction succeeds, other factions in other countries get +50% escalation modifier for 10 ticks (the "springtime of nations" effect).

### Tasks

#### Task 3.1: Create `sovereignty.py`

**New file:** `src_template/sovereignty.py`

Functions:
- `check_sovereignty_thresholds(db, faction_id, world_id)` — returns dict of {threshold_name: (current, required, met)}
- `check_declaration(db, faction_id, world_id, tick_number)` — roll for independence declaration. Returns declaration event or None.
- `process_recognition(db, declaring_faction_id, new_country_name, world_id, diplomatic_relations, all_worlds)` — other countries roll recognition. Returns list of recognizing countries.
- `apply_secession(db, faction_id, new_country_name, world_id, parent_world_id, recognized_by)` — split region, create new country entry, log sovereignty event.
- `apply_secession_cascade(db, all_worlds, tick_number)` — boost faction formation/escalation modifiers globally for 10 ticks after a successful secession.
- `get_sovereignty_candidates(db, world_id)` — list factions that could potentially declare.

#### Task 3.2: Add `sovereignty_events` table to world DB

**Files:** `src_template/world_state.py` (init_db)

```sql
CREATE TABLE IF NOT EXISTS sovereignty_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faction_id TEXT NOT NULL,
    world_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- declaration, recognition, secession, rejection, collapse
    new_country_name TEXT,
    recognized_by TEXT,  -- JSON array of country names
    territory_control REAL,
    member_count INTEGER,
    tick_number INTEGER,
    created_at REAL NOT NULL
)
```

#### Task 3.3: Wire sovereignty check into simulation tick

**Files:** `src_template/simulation.py`

After escalation fallout:
```python
from .sovereignty import check_sovereignty_candidates, process_sovereignty_tick
sovereignty_events = process_sovereignty_tick(db, world_id, tick_number, faction_engine, diplomatic_relations)
for se in sovereignty_events:
    tick_events.append(se)
```

#### Task 3.4: Add sovereignty state to /api/growth and coordinator

**Files:** `aurelia_coordinator.py`

Add: `sovereignty_candidates`, `new_countries`, `secession_cascade_active`, `secession_cascade_ticks_remaining`.

Also: the coordinator should log sovereignty events prominently — these are the most significant events in the simulation.

**Verification:**
1. Manually set a faction to meet all thresholds, inject recognition from 2 countries
2. Run 5+ ticks — faction should declare independence, become a new country
3. Check /api/growth for new country data
4. Verify secession cascade modifier is active in other worlds
5. Verify the parent country's territory and population decreased

---

## Integration Notes

### Order within simulation tick (revised):
```
1. advance_time
2. update_ecology
3. npc_schedules (stratified 300/tick)
4. npc_ai (stratified 200/tick)
5. move_npcs (paginated 500/tick)
6. decision_feeder.feed_tick_experience (all active NPCs)
7. decision_feeder.check_glim_tipping
8. narrative_seeds.draw_seed (5 draws)
9. population.check_migration + check_reproduction + check_mortality (300/tick)
10. economic_drift.apply_drift
11. event_generators.check_all
12. ── PHASE 6 ──
13. faction_engine.check_faction_formation + update_all_factions
14. escalation_ladder.check_all_escalations + apply_fallout
15. sovereignty.process_sovereignty_tick
16. ── END PHASE 6 ──
17. update_psychology
18. evolve_relationships
19. rituals
20. federation.send_events + heartbeat
```

### Data flow:
- Phase 4 feeds decision_state → faction_engine reads grievance density
- faction_engine produces factions → escalation_ladder escalates
- escalation produces diplomatic_incidents → aurelia_diplomacy updates relations
- sovereignty produces new countries → coordinator registers them

### Performance at 60K:
- Faction engine: scans only NPCs with grievance variables above threshold (typically <5% of population) — ~600 NPCs/world max. O(600) per tick.
- Escalation: only checks active factions (typically <10 per world). O(10) per tick.
- Sovereignty: only checks factions at armed_conflict+ (typically 0–2 per world). O(2) per tick.
- Total Phase 6 overhead: <50ms per tick at 60K scale.

### Git commits (one per module):
1. `feat(phase6): faction engine — NPC organization with grievance density, membership, leadership`
2. `feat(phase6): escalation ladder — dormant→war state machine with intervention mechanics`
3. `feat(phase6): sovereignty pipeline — faction-to-country emergence with recognition cascade`

---

## Success Criteria
- [ ] Factions form organically from grievance density (no manual spawning after verification)
- [ ] Factions escalate through ladder stages based on influence + world state
- [ ] Escalation produces diplomatic incidents that affect cross-world relations
- [ ] At 'skirmish' level, population effects fire (migration, mortality)
- [ ] At 'armed_conflict', other countries roll for intervention
- [ ] A faction meeting sovereignty thresholds can declare independence
- [ ] Recognition mechanics work — countries recognize based on diplomatic relations
- [ ] Secession cascade boosts faction activity globally
- [ ] All observable via /api/growth
- [ ] Zero performance regression at 60K scale
