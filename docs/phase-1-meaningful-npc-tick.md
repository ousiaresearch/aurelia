# Aurelia Phase 1 — Meaningful NPC Tick

## Goal

Fix the first critical federation gap: world ticks completed, but `npc_ai_actions` returned zero because the legacy NPC AI used pre-Aurelia locations such as `marketplace`, `workshop`, and `ridgeline`. Those locations do not exist in Aurelia country databases, causing foreign-key failures that were swallowed silently.

## Root Cause

`src/npc_ai.py` was inherited from an older world template. `NPCMind.think()` attempted to move NPCs to hard-coded legacy locations. `run_npc_ai_tick()` caught all per-NPC exceptions and continued, causing ticks to appear healthy while producing no meaningful behavior.

Confirmed failure:

- Solara NPC with wealth goal tried to move to `marketplace`
- SQLite raised `FOREIGN KEY constraint failed`
- `run_npc_ai_tick()` swallowed the exception
- Tick returned `npc_ai_actions=[]`

## Fix

`/Users/johann/aurelia/src_template/npc_ai.py` now uses a schedule-first action model:

1. Read the NPC's deep-seeded `npc_schedules` row for the current hour
2. Validate the target location exists in the local country DB
3. Move the NPC to that real local location
4. Generate type-aware action prose from:
   - NPC type (`thren`, `vorn`, `glim`, `human`)
   - occupation
   - schedule activity
   - schedule description
   - location name
5. Insert a structured `npc_actions` row with JSON properties:
   - `npc_type`
   - `occupation`
   - `activity`
   - `schedule_id`
   - `source: deep_seed_schedule`
6. Fall back to legacy goal AI only when no schedule exists
7. If legacy goal AI fails, log a local rhythm fallback instead of returning silence

The fixed `npc_ai.py` was propagated to all five live world source trees:

- `/Users/johann/.hermes/agents/solara/aurelia-world/src/npc_ai.py`
- `/Users/johann/.hermes/agents/valdris/aurelia-world/src/npc_ai.py`
- `/Users/johann/.hermes/agents/mirithane/aurelia-world/src/npc_ai.py`
- `/Users/johann/.hermes/agents/arkos/aurelia-world/src/npc_ai.py`
- `/Users/johann/.hermes/agents/verge/aurelia-world/src/npc_ai.py`

## Tests

Added regression tests:

- `/Users/johann/aurelia/tests/test_npc_ai_aurelia.py`

Test coverage:

1. `run_npc_ai_tick()` uses deep-seeded schedule locations instead of old template locations
2. Returned actions include `npc_type`, `activity`, and valid local `location_id`
3. Actions are logged to `npc_actions` with JSON properties
4. Glim action language stays functional/task-oriented instead of inner-life language

Current result:

```text
2 passed
```

## Verification

Forced deterministic pass (`random.random=0.0`) produced 120 schedule actions in each world.

Normal stochastic tick pass produced meaningful NPC actions:

- Solara: 15 actions
- Valdris: 22 actions
- Mirithane: 13 actions
- Arkos: 17 actions
- The Verge: 20 actions

Fresh daemons were restarted and wrote new heartbeats. Recent action rows show deep-seed schedule behavior across all types and worlds.

## Current State

Phase 1 is complete: the tick is no longer silent. NPCs now act according to their deep-seeded schedules, move through valid local country locations, and produce type-aware action prose suitable for later narrative, governance, diplomacy, and federation event systems.
