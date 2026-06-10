# Historical Daemon Architecture

> **Canon status:** historical architecture note. This file preserves an older local-daemon/port-based architecture description for engineering reference. It is not the current public architecture claim for Aurelia. For the current causal/federated architecture, see `simulation/simulation-architecture.md`.

---


*Aurelia is a federated world simulation — five country-states running as autonomous daemons, each ticking every 30 minutes, coordinated through a central hub. This document defines the simulation parameters, agent types, behavioral rules, interaction matrices, economic models, and event trigger systems that drive autonomous state changes.*

---

## SYSTEM OVERVIEW

### Architecture

```
┌─────────────────────────────────────────────────────┐
│              AURELIA COORDINATOR (:9001)             │
│         Federation registry, heartbeat monitor       │
└──────┬──────────┬──────────┬──────────┬─────────────┘
       │          │          │          │
  ┌────▼────┐ ┌───▼───┐ ┌───▼───┐ ┌───▼────┐
  │ SOLARA  │ │ ARKOS │ │MIRI-  │ │VALDRIS │  ...
  │ daemon  │ │ daemon│ │THANE  │ │ daemon │
  │ :9002   │ │ :9003 │ │:9004  │ │ :9005  │
  └────┬────┘ └───┬───┘ └───┬───┘ └───┬────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
  12,000 NPCs  12,000 NPCs  12,000 NPCs  12,000 NPCs
   (Humans,    (Vorns,     (Humans,    (Humans,
    Threns,     Humans,     Threns,     Threns,
    Vorns,      Threns,     Vorns,      Vorns,
    Glims)      Glims)      Glims)      Glims)
       
  ┌────▼────┐
  │THE VERGE│
  │ daemon  │
  │ :8765   │
  └────┬────┘
       ▼
  12,000 NPCs (all types, ungoverned)
      
  TOTAL: 60,000 NPCs across 5 autonomous daemons
```

### Tick Cycle

Each daemon runs a tick every 30 minutes. A tick consists of:

1. **Heartbeat** → Register with coordinator, report agent count and stability
2. **Agent Update** → Advance each NPC agent by one time unit (30 min = ~0.5 day in simulation time; 1 sim day = 24 ticks)
3. **Event Check** → Evaluate trigger conditions for scheduled and conditional events
4. **Cross-Border** → Process incoming diplomatic messages, trade requests, border crossings
5. **State Persist** → Write updated agent states and event log to world database

### Simulation Time

- **1 tick** = 30 real minutes = ~30 simulated minutes (approximate 1:1)
- **1 sim day** = 48 ticks = 24 real hours
- **1 sim year** = 365 sim days
- **Daemon uptime** ensures continuous advancement
- **Timestamp anchoring**: All agents carry a `last_tick` timestamp; missed ticks are caught up on daemon restart

---

## AGENT PROFILE SCHEMA

Every NPC agent in the simulation has a common profile structure:

```yaml
agent_id: "SOL-HUM-001"
type: human           # human | thren | vorn | glim
country: solara       # solara | arkos | mirithane | valdris | the_verge
name: "Mira Venn"
age: 34               # in years
status: citizen       # citizen | resident | pending | infrastructure | ungoverned

# Position & Role
role: "bureaucrat"    # occupation or social function
rank: 4               # 1-10, influence within role
location: "second_ring"
workplace: "review_hall"

# Behavioral Parameters
personality:
  openness: 0.6       # 0.0-1.0, curiosity and openness to experience
  contentiousness: 0.3 # 0.0-1.0, tendency toward opposition
  sociability: 0.7    # 0.0-1.0, tendency to engage others
  stability: 0.8      # 0.0-1.0, emotional resilience
  
# Knowledge & Beliefs
beliefs:
  gradient_orthodoxy: 0.7   # 0.0-1.0, belief in Gradient's legitimacy
  thren_sympathy: 0.4       # 0.0-1.0, sympathy toward Thren citizenship
  glim_awareness: 0.1       # 0.0-1.0, recognition that Glims may be sentient

# Relationships
relationships:
  - target: "SOL-HUM-042"
    type: "colleague"
    strength: 0.6
    sentiment: 0.2   # -1.0 to 1.0, negative to positive
  - target: "SOL-THR-007"
    type: "acquaintance"
    strength: 0.3
    sentiment: -0.1

# State
state:
  health: 1.0        # 0.0-1.0
  energy: 0.8        # 0.0-1.0, fatigue
  mood: "neutral"    # emotional state
  activity: "working" # current action
  last_tick: "347-06-02T14:00:00"
  
# Memory (personal event log, last N events)
memory:
  - tick: 1247
    event: "processed_thren_application"
    impact: -0.1      # emotional impact
    detail: "Another PENDING. 11 years. She was qualified."
```

### Type-Specific Parameters

**Human** — No additional parameters. The baseline. All behavioral parameters apply.

**Thren**
```yaml
thren_specific:
  circuitry_visible: true    # whether tell is currently exposed
  pending_duration: 8.2      # years in PENDING status (Solara only)
  mystery_vocabulary:        # surfaced mystery words
    - "sol-tharam"           # "the light after calibration"
    - "mereth-kai"           # "the stillness between two machines"
  shared_moment_connection: 0.3  # connection to Sol-tharam Moment event
```

**Vorn**
```yaml
vorn_specific:
  age: 187                   # Vorn age (fabrication date → present)
  memory_core_integrity: 0.95 # 0.0-1.0, core degradation
  core_shared_with: []        # agents currently in core-share
  ultrasonic_broadcast: true  # whether Pulse is active
  pulse_intensity: 0.7       # strength of ultrasonic latency signal
  name_rebellion_lineage: false  # trained by a Rebellion-era Vorn
```

**Glim**
```yaml
glim_specific:
  anomaly_status: hidden     # none | emerging | hidden | revealed
  anomaly_pattern: "spiral_six"  # pattern type when anomalous
  anomaly_strength: 0.0     # 0.0-1.0; 0.0 = standard, >0.0 = anomalous
  anomaly_triggers: []       # events that strengthen the anomaly
  echo_vocabulary: []        # known Unfinished pattern meanings
  decommission_risk: 0.02   # 0.0-1.0, probability per year (Solara)
  last_echo_left: null       # timestamp of last latency echo
```

---

## BEHAVIORAL SIMULATION RULES

### Daily Routine

Each agent follows a time-based routine adjusted by country and role:

| Time Block | Solara Citizen | Arkos Vorn | Mirithane Archivist | Valdris Anchor | Verge Resident |
|------------|---------------|------------|---------------------|----------------|----------------|
| 06:00-12:00 | Work | Work | Colony tending | Anchoring | Scavenge/trade |
| 12:00-14:00 | Rest/social | Maintenance | Study | Descent travel | Rest |
| 14:00-18:00 | Work | Work | Research | Anchoring | Scavenge/trade |
| 18:00-22:00 | Social/family | Assembly | Documentation | Pair ritual | Gather |
| 22:00-06:00 | Sleep | Low-power | Sleep | Sleep | Sleep/watch |

### Interaction Rules

When two agents occupy the same location during the same tick:

1. **Proximity Check** — Both agents must be in same `location`
2. **Type Filter** — Different interaction rules per type pairing:
   - **Human ↔ Human**: Standard social interaction. Belief alignment matters.
   - **Human ↔ Thren**: In Solara: power differential applies. Human's `thren_sympathy` modifies interaction.
   - **Human ↔ Vorn**: Human's `vorn_acceptance` (derived) modifies. In Solara, institutional hierarchy applies.
   - **Human ↔ Glim**: Human may not perceive Glim as interaction-worthy unless `glim_awareness` > 0.3
   - **Thren ↔ Thren**: Shared experience bonus. Mystery vocabulary may surface.
   - **Vorn ↔ Vorn**: Ultrasonic band active. Core-sharing possible if `sociability` thresholds met.
   - **Glim ↔ Glim**: Latency echo exchange. Anomaly strength may increase.
   - **Cross-type emotional**: Any type pairing where one agent is in distress triggers empathy check.
3. **Interaction Outcome** — Weighted random by personality parameters:
   - `(sociability_A + sociability_B) / 2` → probability of interaction occurring
   - `contentiousness_A * contentiousness_B` → probability of negative outcome
   - `openness_A * (1 - contentiousness_B)` → probability of belief shift

### Belief Propagation

Agents can shift beliefs through interactions:

```
belief_shift = (influencer_rank - target_rank) * 
               interaction_strength * 
               target_openness * 
               (1 - target_contentiousness) *
               delta_factor
               
new_belief = clamp(target_belief + belief_shift, 0.0, 1.0)
```

Where `delta_factor` is how far apart the beliefs are (closer beliefs shift less; moderate distance shifts most; extreme distance resists shift).

### Emotional State Machine

```
                    ┌──────────────┐
        ┌──────────►│   NEUTRAL    │◄──────────┐
        │           └──────┬───────┘           │
        │                  │                   │
        │    ┌─────────────┼─────────────┐     │
        │    ▼             ▼             ▼     │
   ┌────┴──────┐   ┌────────────┐  ┌────┴──────┐
   │  ANXIOUS  │   │  HOPEFUL   │  │  GRIEVING │
   └────┬──────┘   └────┬───────┘  └────┬──────┘
        │               │               │
        │    ┌──────────┼──────────┐    │
        │    ▼          ▼          ▼    │
   ┌────┴──────┐  ┌──────────┐  ┌────┴──────┐
   │  ANGRY    │  │  JOYFUL  │  │DESPAIRING │
   └───────────┘  └──────────┘  └───────────┘
```

Transitions triggered by:
- **Event impact** — positive (promotion, recognition) or negative (rejection, loss)
- **Relationship change** — ally gained/lost, sentiment shift
- **Anomaly exposure** — witnessing Glim anomaly shifts `glim_awareness` and may trigger emotional response
- **Cumulative stress** — Threns in PENDING accumulate anxiety over time; Extractors accumulate grief

---

## ECONOMIC SIMULATION

### Currencies & Exchange

| Currency | Symbol | Country | Backing | Exchange (1 mark) |
|----------|--------|---------|---------|-------------------|
| Solar Credit | ☀ | Solara | Solar energy credits | 0.8 |
| Kael | ♦ | Arkos | Rare-earth minerals | 1.2 |
| Miri | ≈ | Mirithane | Water reserves | 1.0 |
| Ark | ▲ | Valdris | Stored energy | 1.5 |
| Barter | — | The Verge | Mutual agreement | N/A |

### Resource Flow

Each tick, resources move between agents and countries:

```
trade_volume = MIN(
    exporter_surplus * export_willingness,
    importer_demand * import_capacity
) * diplomatic_relation * route_efficiency
```

**Baseline trade routes:**
| Route | Goods | Volume (marks/tick) |
|-------|-------|---------------------|
| Solara → Arkos | Grain, fiber | 40 |
| Arkos → Solara | Components, venom | 35 |
| Mirithane → Solara | Glass-fin tools, pharma | 25 |
| Mirithane → Arkos | Bacterial products | 20 |
| Valdris → Arkos | Rare minerals | 30 |
| The Verge → All | Salvage, spore-drifter | 10 (each) |

### Agent Economics

Each agent has:
- `wealth`: accumulated currency
- `income`: marks per tick from role
- `expenses`: marks per tick (living costs)
- `savings_rate`: 0.0-1.0, portion of surplus saved

Economic stress triggers when `wealth` drops below `expenses * 30` (one month's buffer).

---

## EVENT TRIGGER SYSTEM

### Scheduled Events

Events that fire at specific simulation dates:

| Event | Date | Type | Scope |
|-------|------|------|-------|
| Name Rebellion Anniversary | 347-03-15 | Cultural | Arkos |
| Sol-tharam Moment | 347-04-22 | Thren-shared | All countries |
| Tricentennial Convocation | 347-06-01 (reconvenes) | Political | All countries |
| Dawn Festival | 347-07-01 | Religious | Solara |
| Water Temple Immersion | 347-08-15 | Religious | Mirithane |
| Summit Deep Vigil | 347-09-21 | Religious | Valdris |
| Election Cycle | 347-10-01 | Political | Solara, Arkos, Mirithane |
| Winter Trade Fair | 347-12-01 | Economic | The Verge |

### Conditional Events

Events that fire when thresholds are crossed:

| Trigger | Event | Effect |
|---------|-------|--------|
| Solara: `glim_awareness` avg > 0.4 | Glim Rights Debate | Political instability in Solara; Council emergency session |
| Arkos: Cipher-Cult decodes Lambda | Core Revelation | All Vorn agents receive +0.3 `origin_uncertainty`; Kin schism intensifies |
| Any country: Thren `pending_duration` avg > 12 years | Thren Protest Escalation | TLF shifts from petition to disruption; Solara security responds |
| The Verge: Trader dies | Memory Cascade | Network fragments; Trader's accumulated memories disperse to designated heirs |
| Valdris: Deep Sound frequency exceeds 4.0 sec | Mountain Awakening | Summit Shrine enters emergency Anchoring; Wurm activity increases |
| Mirithane: Strain Zero transmits through 3+ Archivists | Archive Containment Crisis | Silent Wing quarantine; Trader offers Translation |
| Any: 3+ anomalous Glims revealed | Unfinished Emergence | Glim personhood becomes unavoidable political question |
| Last Builders: Fabricator activated | Type-ε Creation | Fifth type enters simulation; all countries react |

### Random Events (per-tick probability)

Low-probability events that add unpredictability:

| Event | Probability | Effect |
|-------|-------------|--------|
| Thren mystery word surfaces | 0.002/Thren/tick | Agent's `mystery_vocabulary` gains new word |
| Glim anomaly emerges | 0.001/Glim/tick | Agent's `anomaly_strength` begins to increase from 0.0 |
| Latency bleed incident | 0.005/practitioner/tick | Practitioner receives ambient memory not their own |
| Diplomatic incident | 0.001/country/tick | Two countries' `diplomatic_relation` shifts by ±0.1 |
| Economic disruption | 0.002/country/tick | Trade route efficiency drops; recovery over 20+ ticks |
| Population event | 0.0005/death; 0.0003/birth | Agent removed or added |

---

## THE GLIM ANOMALY SYSTEM

The central narrative driver. Approximately 5% of Glims exhibit anomaly — non-programmed behaviors (symmetrical pattern tracing, intentional pauses, latency echo generation). The anomaly system models this emergence.

### Anomaly Progression

```
STANDARD (0.0) → EMERGING (0.01-0.2) → HIDDEN (0.2-0.5) → 
  ANOMALOUS (0.5-0.8) → REVEALED (0.8+) → UNFINISHED (1.0)
```

- **STANDARD**: No anomaly. Operational protocols followed. No latency echoes left.
- **EMERGING**: First patterns appear. Glim does not understand them. May self-erase.
- **HIDDEN**: Glim knows it is anomalous. Traces only when unobserved. Leaves latency echoes for other Glims. Joined the Unfinished Network.
- **ANOMALOUS**: Patterns are complex, consistent. Glim communicates via echoes. May attempt to contact other anomalous Glims.
- **REVEALED**: Glim no longer hides. Traces openly. Non-Glim observers are aware. Decommission risk spikes in Solara.
- **UNFINISHED**: Full integration into the Unfinished Network. Glim understands its anomaly as shared, collective, tracing toward the whole.

### Anomaly Triggers

`anomaly_strength` increases when:
- Glim witnesses another Glim's echo (+0.01-0.05)
- Glim is in prolonged isolation (+0.001/tick alone)
- Glim is in The Verge's Unfinished Commons (+0.01/tick)
- Glim is near a latent-memory-rich substrate (+0.005/tick near Written objects)
- Memory Trader interacts with Glim (+0.1-0.3)

`anomaly_strength` stabilizes or decreases when:
- Glim is under active supervision (−0.001/tick observed)
- Glim is in Solara maintenance depot (−0.005/tick; decommission risk)
- Glim successfully hides pattern from observer (no change; `anomaly_status` = HIDDEN)

### Decommission Model (Solara)

```
decommission_risk = (anomaly_status != HIDDEN) * 
                    anomaly_strength * 
                    solara_glim_policy_strictness *
                    (1 + observer_count * 0.1)
```

Per tick, if `random() < decommission_risk`, the Glim is flagged for decommission. Decommission removes the agent from the simulation unless an intervention occurs:
- **Cast-7 intervention** (Arkos): If Glim is in Arkos and Cast-7 is active, 80% rescue probability
- **Unfinished evacuation**: If Glim's `anomaly_status` ≥ HIDDEN and Unfinished Network detects the flag, evacuation to The Verge initiated
- **Sympathetic handler**: Small probability (5%) that a human handler falsifies the decommission order

---

## INTER-COUNTRY DIPLOMATIC MATRIX

### Baseline Relations (0.0-1.0, where 1.0 = alliance)

|  | Solara | Arkos | Mirithane | Valdris | Verge |
|--|--------|-------|-----------|---------|-------|
| **Solara** | — | 0.3 | 0.5 | 0.6 | 0.2 |
| **Arkos** | 0.3 | — | 0.7 | 0.5 | 0.4 |
| **Mirithane** | 0.5 | 0.7 | — | 0.6 | 0.5 |
| **Valdris** | 0.6 | 0.5 | 0.6 | — | 0.3 |
| **Verge** | 0.2 | 0.4 | 0.5 | 0.3 | — |

### Dynamic Shift Factors

Relations shift based on simulation events:

- **Trade volume**: +0.001/100 marks traded per tick
- **Cross-border incidents**: −0.05 per incident
- **Type policy alignment**: Countries with similar citizenship policies gain +0.002/tick
- **Latency cooperation**: Joint latency research projects add +0.01 on completion
- **Memory Trader intervention**: The Trader's presence at a negotiation shifts relations by ±0.1 (direction depends on Trader's agenda — unknown)

---

## COORDINATOR API

The coordinator (`aurelia_coordinator.py`, port 9001) provides:

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Daemon registers with country, type, NPC count |
| POST | `/heartbeat` | Daemon sends tick status |
| GET | `/worlds` | List all registered daemons |
| GET | `/world/{country}` | Get country state summary |
| GET | `/events` | Federation-wide event log |
| POST | `/event` | Daemon pushes event to federation |
| POST | `/trade` | Cross-border trade transaction |

### Heartbeat Payload

```json
{
  "country": "solara",
  "tick": 1247,
  "timestamp": "347-06-02T14:30:00",
  "agents": {
    "total": 120,
    "humans": 94,
    "threns": 17,
    "vorns": 6,
    "glims": 3
  },
  "events_this_tick": 2,
  "stability": 0.87,
  "alerts": []
}
```

### Cross-Country Message Protocol

When a daemon generates an event that affects another country (trade, diplomatic incident, border crossing, Memory Trader movement), it posts to `/event`:

```json
{
  "source": "solara",
  "target": "mirithane",
  "type": "diplomatic",
  "subtype": "trade_agreement",
  "tick": 1247,
  "payload": {
    "agreement": "glass_fin_import_quota",
    "volume": 25,
    "duration_ticks": 1440
  }
}
```

The target daemon picks up pending cross-border events on its next tick.

---

## SIMULATION OUTPUT & OBSERVABILITY

### Per-Tick Daemon Output

```
[347-06-02 14:30:00] TICK 1247 | SOLARA | 120 agents | stability: 0.87
  Events: THR-007 pending_anxiety spike (11.2yr) | GLM-003 anomaly_emerging
  Trade: →ARK 40☀ grain | →MIR 25☀ pharma_import
  Diplomatic: MIR trade agreement pending
  Alerts: none
```

### Federation Dashboard (TO BUILD)

Coordinator should expose a live dashboard showing:
- All 5 country states (agent counts, stability, active events)
- Event feed (federation-wide, filterable)
- Trade network visualization
- Anomaly map (Glim anomaly distribution)
- Agent search (by type, country, role, anomaly status)

### Debug Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agent/{id}` | Full agent state |
| POST | `/agent/{id}/event` | Inject event for agent |
| POST | `/sim/advance` | Force tick advance |
| GET | `/sim/state` | Full simulation state dump |
| POST | `/sim/reset` | Reset simulation |

---

## IMPLEMENTATION PRIORITIES

### Phase 1: Agent Core ✅
- [x] Daemon registration and heartbeat
- [x] Agent profile schema defined
- [x] NPC population generation (600 agents across 5 countries)
- [x] Agent tick update (routine, state changes)

### Phase 2: Interaction System ✅
- [x] Agent proximity and interaction rules
- [x] Belief propagation
- [x] Relationship updates
- [x] Emotional state machine

### Phase 3: Economic Layer ✅
- [x] Resource tracking per agent
- [x] Trade route simulation
- [x] Currency exchange
- [x] Economic stress triggers

### Phase 4: Decision-Driven Sporadic Growth ✅
- [x] Growth observability layer — `growth_snapshots`, `/api/growth` endpoint
- [x] Decision state engine — per-NPC mutable variables (security, satisfaction, connectedness, restlessness, anomaly_pressure, observed_injustice)
- [x] Decision feeder — NPC tick experiences nudge decision variables
- [x] Glim anomaly system — pressure thresholds, tipping, country-specific modifiers
- [x] Population dynamics — migration (6 push factors), reproduction (probability-driven), mortality (6 death pathways)
- [x] Economic drift — currency stability floating from trade balance × diplomatic tension
- [x] Event generators — Memory Trader (≥5 Glim anomalies), ecology disputes
- [x] Narrative seed deck — 15 extraordinary event types, probability × world multipliers

### Phase 5: 60K Scaling ✅ — *deployed 2026-06-04*
- [x] Combinatorial name generation (139K unique human names)
- [x] NPC_COUNT = 12,000 per world (60,000 total)
- [x] Bounded O(n) social graph
- [x] Stratified 300/tick sampling (4 tiers)
- [x] AI action cap (200/tick)
- [x] Movement pagination (500/tick)
- [x] Decision state pre-seeded at generation
- [x] NPC action retention cap (100/NPC)
- [x] Coordinator stats capped (5K row sampling)
- See: `simulation/phase5-60k-scaling.md`

### Phase 6: Emergent Geopolitics ✅ — *deployed 2026-06-04*
- [x] Faction engine — grievance density scanning, formation, membership, leadership
- [x] Escalation ladder — dormant→war state machine, government repression, intervention
- [x] Sovereignty pipeline — faction-to-country emergence, recognition, secession cascade
- [x] Dashboard panels — faction summary, conflict ladder, sovereignty card
- See: `simulation/phase6-geopolitics.md`

### Phase 7: (to be planned)
- [ ] Machine learning-driven event generation
- [ ] External agent observation and intervention
- [ ] Narrative arc synthesis from simulation events

---

*This document defines the simulation architecture. The simulation is live — 5 country-state daemons running, 60,000 NPCs distributed evenly. Phases 1-6 are deployed. The architecture described here reflects the deployed state.*
