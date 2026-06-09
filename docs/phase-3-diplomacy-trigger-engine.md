# Aurelia Phase 3 — Diplomacy & Personhood Trigger Engine

Date: 2026-06-01

## Purpose

Phase 1 made world ticks produce meaningful NPC behavior.
Phase 2 promoted those local behaviors into a coordinator-level federation event bus.
Phase 3 adds the first political interpretation layer: a diplomacy/personhood trigger engine.

Aurelia's central question is:

> Who counts as a person?

The Phase 3 engine watches federation events for patterns that matter politically, especially around Glims, memory revelations, trade flows, ecological disputes, and country-specific ideological flashpoints.

## What Phase 3 Adds

The coordinator now has:

1. Baseline bilateral diplomatic relations for all 10 country pairs.
2. A processor that reviews federation events and classifies politically meaningful ones.
3. Persistent diplomatic incidents.
4. Relation deltas that mutate trust, tension, cooperation, and trade values.
5. An event-review table so routine events are marked reviewed and not rescanned forever.
6. API endpoints to inspect and process diplomacy state.
7. Automatic diplomacy processing whenever daemons publish new federation events.

## New Files

```text
/Users/johann/aurelia/aurelia_diplomacy.py
/Users/johann/aurelia/tests/test_diplomacy_engine.py
/Users/johann/aurelia/docs/phase-3-diplomacy-trigger-engine.md
```

## Changed Files

```text
/Users/johann/aurelia/aurelia_coordinator.py
```

## New Coordinator Tables

Database:

```text
/Users/johann/aurelia/coordinator.db
```

Tables:

```text
diplomatic_relations
diplomatic_incidents
diplomatic_event_reviews
```

### `diplomatic_relations`

One row per bilateral country pair. Keys are sorted, e.g.:

```text
arkos|solara
arkos|mirithane
mirithane|valdris
```

Fields include:

- `status`
- `baseline_trust`
- `baseline_tension`
- `baseline_cooperation`
- `baseline_trade`
- mutable `trust`
- mutable `tension`
- mutable `cooperation`
- mutable `trade`
- lore notes

### `diplomatic_incidents`

Stores politically meaningful events promoted from the event bus.

Fields include:

- `incident_id`
- `source_event_id`
- `source_world`
- `category`
- `title`
- `description`
- `severity`
- `affected_worlds`
- `relation_deltas`
- `payload`
- `world_time`

### `diplomatic_event_reviews`

Marks every reviewed federation event, including routine events that do not produce incidents. This prevents the processor from repeatedly rescanning ordinary daily-life events forever.

## New / Updated API

### Inspect diplomacy state

```bash
curl 'http://127.0.0.1:9001/api/diplomacy?limit=10'
```

Optional filters for incidents:

```bash
curl 'http://127.0.0.1:9001/api/diplomacy?world_id=arkos&category=glim_personhood&limit=10'
```

Response shape:

```json
{
  "relations": {
    "arkos|solara": {
      "trust": 0.45,
      "tension": 0.65,
      "cooperation": 0.55,
      "trade": 0.75
    }
  },
  "incidents": []
}
```

### Manually process backlog

```bash
curl -X POST 'http://127.0.0.1:9001/api/diplomacy/process' \
  -H 'Content-Type: application/json' \
  -d '{"limit": 500}'
```

### Automatic processing

`POST /events` now uses:

```python
STATE.ingest_federation_events(world_id, events)
```

That means daemon-published event batches are recorded and immediately passed through the diplomacy trigger engine.

## Trigger Categories Implemented

### `glim_personhood`

The central political trigger. Created by events involving Glims plus anomaly/personhood language:

- anomalous Glim
- dreaming Glim
- decommission review
- shelter/refuge
- confused / not broken
- abandoned drone graveyard

Country-specific effects:

- **Arkos** shelter events increase Arkos ↔ Mirithane trust/cooperation and raise Arkos ↔ Solara tension.
- **Mirithane** advocacy events increase Arkos ↔ Mirithane alignment and raise Mirithane ↔ Solara tension.
- **Solara** decommission events raise tension with Arkos, Mirithane, and The Verge.
- **The Verge** abandoned-Glim events increase pressure on Arkos and Solara while slightly aligning Mirithane with The Verge.

### `memory_revelation`

Triggered by Verge memory-trader revelations, especially if Solara, council politics, Glims, or decommissioning are involved.

Effects:

- raises Solara ↔ Verge tension
- raises Arkos/Solara and Mirithane/Solara tension
- strengthens Arkos ↔ Mirithane cooperation around the Glim question

### `trade`

Triggered by `trade_flow` / economy events that include a source and target country.

Effects:

- increases trade
- increases cooperation
- slightly lowers tension

### `ecology_dispute`

Currently implemented for Valdris mining/runoff pressure reaching Mirithane waters.

Effects:

- raises Mirithane ↔ Valdris tension
- lowers trust/cooperation modestly

## Tests

```bash
pytest tests -q
```

Current result:

```text
9 passed
```

Coverage includes:

- Glim sanctuary incident creation.
- Relation deltas for Arkos/Solara and Arkos/Mirithane.
- Idempotent diplomacy processing.
- Trade-flow relation updates.
- Verge memory-trader revelation classification.
- Automatic event ingest + diplomacy processing.
- Existing Phase 1 and Phase 2 tests.

## Live Verification

Coordinator and five daemons are running.

```text
GET /api/health → status ok, worlds 5
```

Worlds online:

- Arkos
- Mirithane
- Solara
- Valdris
- The Verge

Live diplomacy state:

```text
relations: 10
incidents: 0
```

Live event-review state:

```text
federation_events: 398
diplomatic_event_reviews: 398
diplomatic_incidents: 0
```

Zero incidents is currently correct: the live stream so far is routine schedule-driven daily life, not personhood crisis, trade diplomacy, memory revelations, or ecological disputes.

## Current Baseline Examples

```text
arkos|solara:
  trust: 0.45
  tension: 0.65
  cooperation: 0.55
  trade: 0.75

arkos|mirithane:
  trust: 0.68
  tension: 0.34
  cooperation: 0.62
  trade: 0.30

arkos|valdris:
  trust: 0.72
  tension: 0.20
  cooperation: 0.76
  trade: 0.82
```

## What Phase 3 Enables

Future phases can now ask higher-order questions:

- Which country pairs are becoming unstable?
- Is the Glim question becoming a federation-wide crisis?
- Are trade flows lowering tension or masking deeper ideological conflict?
- Is The Verge turning from ignored borderland into a source of diplomatic revelations?
- Which incidents should become governance agenda items?

Good next phase candidates:

1. Governance engines consuming diplomatic incidents.
2. A narrative escalation engine that turns repeated incidents into arcs.
3. Glim anomaly mechanics that deliberately generate `glim_personhood` events.
4. Dashboard visualization for diplomatic relations and active incidents.

## Important Pitfalls

- Do not treat every Glim event as a crisis. Routine Glim work/commuting should stay routine.
- Events with no incident must still be reviewed; otherwise the processor will rescan them forever.
- Relation deltas are intentionally small and cumulative. They should drift, not jump.
- The coordinator remains the shared read surface; future systems should use `/api/diplomacy`, not open every country DB.
