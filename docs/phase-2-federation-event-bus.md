# Aurelia Phase 2 — Federation Event Bus

Date: 2026-06-01

## Purpose

Phase 1 made country ticks meaningful by producing type-aware NPC schedule actions. Phase 2 turns those local actions into federation-level signals that other systems can consume.

The goal is not yet diplomacy/trade/governance automation. The goal is the shared substrate those systems need:

- country daemons publish compact event records after each tick
- the coordinator persists and deduplicates those records
- external systems can query recent cross-world events by world, type, and category

## Event Contract

Coordinator table: `federation_events` in `/Users/johann/aurelia/coordinator.db`.

Fields:

- `event_id` — stable unique ID, used for dedupe
- `world_id` — country source: `solara`, `valdris`, `mirithane`, `arkos`, `verge`
- `event_type` — e.g. `npc_action`, `social_change`, `trade_flow`
- `category` — e.g. `daily_life`, `social`, `economy`, `emergence`, `ritual`, `narrative`
- `title` — short display string
- `description` — human-readable event prose
- `importance` — numeric weight for future filtering/escalation
- `actor_ids` — JSON list of NPC/agent IDs
- `tags` — JSON list, including type/location/activity terms where available
- `payload` — JSON original structured source data
- `world_time` — JSON tick world-time snapshot
- `created_at` — event-source timestamp
- `received_at` — coordinator receive timestamp

## Files Added / Changed

### Added

- `/Users/johann/aurelia/src_template/federation_events.py`
  - Builds federation event records from local tick output.
  - Priority order: NPC actions, social changes, trade flows, emergent/ritual/narrative events.

- `/Users/johann/aurelia/tests/test_federation_event_bus.py`
  - Coordinator persistence/dedupe tests.
  - Event builder tests.
  - World client publishing tests.

### Changed

- `/Users/johann/aurelia/aurelia_coordinator.py`
  - Added `federation_events` table.
  - Added `CoordinatorState.record_federation_events()`.
  - Added `CoordinatorState.get_federation_events()`.
  - Added `POST /events`.
  - Added `GET /api/federation-events` with filters:
    - `limit`
    - `world_id`
    - `category`
    - `event_type`
  - Preserved cached NPC/currency accessors to avoid prior DB-lock behavior.

- `/Users/johann/aurelia/src_template/federation.py`
  - Added `publish_federation_events()`.

- `/Users/johann/aurelia/world_daemon_template.py`
  - Imports event builder/publisher.
  - Publishes up to 25 federation events after each tick.
  - Logs `fed_events` in the 10-tick status line.

- Five live world copies under `/Users/johann/.hermes/agents/{country}/aurelia-world/`:
  - `src/federation.py`
  - `src/federation_events.py`
  - `scripts/world_daemon.py`

## Runtime Verification

Fresh coordinator and five daemons were restarted under Hermes background process tracking.

Coordinator:

- Port: `9001`
- Endpoint: `GET http://127.0.0.1:9001/api/health`
- Result: healthy, five worlds registered

Federation event counts after first restarted tick:

- Arkos: 15 `npc_action` events
- Mirithane: 13 `npc_action` events
- Solara: 19 `npc_action` events
- Valdris: 15 `npc_action` events
- The Verge: 12 `npc_action` events
- Total: 74 events

Example endpoint checks:

```bash
curl 'http://127.0.0.1:9001/api/federation-events?limit=10'
curl 'http://127.0.0.1:9001/api/federation-events?world_id=arkos&category=daily_life&limit=3'
```

## Tests

```bash
pytest tests -q
```

Current result:

```text
5 passed
```

## What Phase 2 Enables

The federation now has a live cross-country event stream. Future phases can consume it without opening all five world databases directly.

Good next consumers:

1. Diplomacy triggers
   - Arkos sheltering anomalous Glims
   - Solara citizenship tensions
   - Valdris guild conflicts
   - Verge memory-trader rumors

2. Trade/economy routing
   - Resource shortage events
   - Currency movement events
   - Inter-country supply/demand signals

3. Governance engines
   - Council agenda items generated from event patterns
   - Consensus prompts in Mirithane
   - Glass Forum referenda in Arkos

4. Narrative escalation
   - Personhood crisis arcs
   - Glim anomaly chains
   - Cross-country rumor propagation

## Important Notes

- Daemon event publishing is non-fatal. If the coordinator is down, the world tick still succeeds.
- Event IDs are deterministic per world/tick/source/index; duplicate publishes are safely ignored.
- The bus intentionally stores compact structured payloads, not raw database rows.
- The coordinator remains the read surface; future systems should query the coordinator API instead of directly opening all five world DBs.

## Known Follow-Up

Some live world configs still contain old `simulant` strings and DB location IDs such as `simulant_quarter` / `simulant_sanctuary`. Do not blindly replace those IDs in daemon movement pools until a safe DB migration updates `locations`, `agents.location_id`, schedules, events, and exploration rows together. Textual descriptions can be cleaned separately, but ID migration needs referential care.
