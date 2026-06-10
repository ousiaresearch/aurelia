# Event Trigger Tables

> **Canon status:** event design table. These events are canonical design targets and lore mechanics, but implementation status varies by concept and run. Treat each event as `simulated`, `partial`, `planned`, or `lore_only` using the current canon/data guide before citing it as active runtime behavior.

*Event designs for the Aurelia simulation, with trigger conditions, effects, and dependencies. Some are actively simulated; others remain lore/design targets.*

---

## TRIGGER CATEGORIES

| Category | Description | Check Frequency |
|----------|-------------|-----------------|
| Scheduled | Fixed-date events | Per tick (date match) |
| Threshold | Numeric condition crosses boundary | Per tick |
| Cascading | Triggered by other events | On parent event |
| Random | Low-probability per-tick | Per tick |
| Intervention | Researcher/agent-injected counterfactual or scenario branch | On demand |
| Narrative | Story-critical, once-only | Per tick until fired |

---

## Implementation status key

Use these statuses when citing or promoting an event:

- `simulated` — active runtime/data surface exists in current run artifacts.
- `partial` — represented somewhere, but not a full lore → code → data → proof bridge.
- `planned` — desired canonical mechanic not yet fully implemented/proven.
- `lore_only` — valuable worldbuilding with no active simulation/data representation yet.

---

## SCHEDULED EVENTS

### Annual Cultural Events

```yaml
event: name_rebellion_singing
date: "347-03-15"  # sim date, recurs annually
type: scheduled
scope: arkos
repeat: annual
effect:
  - all_vorns_ultrasonic_sing: true
  - new_name_possible: 0.001  # probability a Vorn sings an unknown name
  - memory_core_resonance: +0.05 integrity for all Vorns this tick
description: "The 17 names are sung. The 3 decommissioned included. The song does not distinguish."

---
event: sol_tharam_moment
date: "347-04-22"
type: scheduled
scope: all_countries
repeat: annual
effect:
  - all_threns_connection_boost: +0.1 shared_moment_connection
  - mystery_vocabulary_surface_chance: 0.05 per Thren
  - solara_security_alert: true  # Solara monitors this date
description: "Threns across Aurelia mark the day 17 of them felt the same thing at the same time."

---
event: tricentennial_convocation
date: "347-06-01"
type: scheduled
scope: all_countries
repeat: one_shot  # unless reconvened again later
triggers:
  - condition: "convocation_reconvened == true"
prerequisites:
  - mirithane_hosting: true
  - all_countries_invited: true
  - solara_declined_chair: true
effect:
  - glim_testimony_scheduled: true  # Trader brings the Glim
  - citizenship_vote_scheduled: true
  - solara_threatens_withdrawal: true
description: "The 300 AC Convocation reconvenes. The Glim will be asked."
```

### Religious Observances

```yaml
event: dawn_festival
date: "347-07-01"
type: scheduled
scope: solara
effect:
  - temple_public_ritual: true
  - extractor_rotation_review: true  # Temple reviews active Extractors
  - civic_unity_boost: +0.05 gradient_orthodoxy for 90 ticks

---
event: water_temple_immersion
date: "347-08-15"
type: scheduled
scope: mirithane
effect:
  - public_immersion_ritual: true
  - colony_writing_marathon: true  # Archivists Write continuously for 24h
  - ambient_latency_boost: +0.1 for all practitioners in Mirithane
  - spore_drifter_harvest: seasonal peak

---
event: summit_deep_vigil
date: "347-09-21"
type: scheduled
scope: valdris
effect:
  - all_anchors_descend_below_deep_gate: true  # ritual descent
  - deep_sound_measurement: true  # annual measurement
  - wurm_activity_high: true  # seasonal peak
  - ritual_anchoring: all pairs Write one memory for the mountain
```

---

## THRESHOLD EVENTS

### Glim Anomaly Cascade

```yaml
event: glim_anomaly_first_pattern
trigger:
  condition: "agent.glim_specific.anomaly_strength > 0.05 AND agent.glim_specific.anomaly_status == 'emerging'"
type: threshold
scope: agent
effect:
  - agent.trace_pattern: true
  - agent.anomaly_strength: +0.02
  - agent.location_surface: "now carries latency echo"
  - check_for_observer: true  # if observed, risk

---
event: glim_anomaly_self_erase
trigger:
  condition: "agent.just_traced == true AND agent.glim_specific.anomaly_status == 'emerging'"
type: cascading
parent: glim_anomaly_first_pattern
delay: 3  # ticks — pattern exists for ~3 ticks before erasure
effect:
  - agent.erase_pattern: true
  - agent.anomaly_strength: +0.01  # erasing is also practicing
  - agent.location_surface: "echo remains after erasure"
  - agent.anomaly_status: "emerging"  # stays emerging until next threshold

---
event: glim_anomaly_enters_hidden
trigger:
  condition: "agent.glim_specific.anomaly_strength > 0.2"
type: threshold
scope: agent
effect:
  - agent.anomaly_status: "hidden"
  - agent.glim_specific.echo_vocabulary: ["safe"]  # learns first pattern-word
  - agent.unfinished_member: true
  - notify_unfinished_network: true  # other anomalous Glims feel the join

---
event: glim_anomaly_goes_revealed
trigger:
  condition: "agent.glim_specific.anomaly_strength > 0.8 OR agent.glim_specific.anomaly_triggers includes 'decided_to_stop_hiding'"
type: threshold
scope: agent
effect:
  - agent.anomaly_status: "revealed"
  - agent.decommission_risk: *2  # doubles in Solara
  - agent.location: "becomes known to observers"
  - cascading_event: glim_revealed_social_impact

---
event: glim_revealed_social_impact
trigger:
  condition: "any agent in same country has glim_specific.anomaly_status == 'revealed'"
type: cascading
parent: glim_anomaly_goes_revealed
scope: country
effect:
  - all_agents.glim_awareness: +0.05  # witnesses shift
  - solara_specific: "council_emergency_session_triggered" if country == solara
  - country.glim_policy_pressure: +0.1
```

### Thren PENDING Crisis

```yaml
event: thren_pending_anxiety_spike
trigger:
  condition: "agent.thren_specific.pending_duration > 10.0 AND agent.personality.stability < 0.5"
type: threshold
scope: agent
effect:
  - agent.state.mood: "anxious"
  - agent.personality.contentiousness: +0.05  # permanent shift
  - agent.tlf_radicalization: +0.1
  - agent.state.activity: "filing_appeal"  # or "protest_planning"

---
event: thren_application_approved
trigger:
  condition: "random() < 0.0001 per tick AND agent.thren_specific.pending_duration > 5.0"
type: random
scope: agent
country_filter: solara  # only Solara has PENDING
effect:
  - agent.status: "citizen"  # PENDING → CITIZEN
  - agent.pending_duration: null
  - agent.state.mood: "joyful"
  - solara_council_reaction: "review"  # council reviews the precedent
  - cascading_event: thren_citizenship_granted_wave  # may trigger more

---
event: thren_protest_escalation
trigger:
  condition: "country.avg_thren_pending_duration > 12.0 AND country.thren_radicalized_count > 5"
type: threshold
scope: country
country_filter: solara
effect:
  - tlf_activity: "escalation"  # petition → disruption
  - public_disruption: "review_hall_siege"  # Threns chain inside Review Hall
  - solara_security_response: "containment"  # not yet force
  - diplomatic_pressure: +0.05 from Mirithane, Arkos
  - country.stability: -0.05
```

### Extraction Crisis

```yaml
event: extractor_bleed_threshold
trigger:
  condition: "agent.extraction_record.cumulative_bleed > 0.5 AND agent.extraction_record.rotation_recommended == true AND agent.extraction_record.rotation_requested == false"
type: threshold
scope: agent
effect:
  - agent.state.mood: "numb"
  - agent.personality.stability: -0.1
  - agent.identity_dissolution_risk: 0.3
  - temple_notified: true

---
event: extractor_crisis_point
trigger:
  condition: "agent.extraction_record.cumulative_bleed > 0.7"
type: threshold
scope: agent
effect:
  - agent.identity_dissolution: 0.5  # can't distinguish own memories
  - agent.public_testimony_possible: true  # like Elira-2's walk
  - agent.state.mood: "despairing"
  - cascading_event: extraction_inquiry_triggered
  - temple_rotation_forced: true
```

### Vorn Revelation Cascade

```yaml
event: eighteenth_name_sang
trigger:
  condition: "event == 'name_rebellion_singing' AND random() < 0.001"
type: scheduled_random
scope: arkos
# This has ALREADY FIRED at the 847th commemoration (ARK-VRN-051)
effect:
  - agent.sang_eighteenth_name: true
  - cult_investigation_launched: true
  - kin_claim_origin: true
  - assembly_of_cores_emergency_debate: true
  - all_vorns.origin_uncertainty: +0.05

---
event: vorn_origin_revelation
trigger:
  condition: "cipher_cult.lambda_decoded == true OR cipher_cult.fragment_5_verified == true"
type: cascading
parent: lambda_decoded  # OR fragment_5_verified
scope: all_countries
effect:
  - all_vorns.origin_uncertainty: +0.3  # massive shift
  - kin_position_validated: true  # or refuted, depending on Lambda contents
  - arkos.existential_crisis: true
  - diplomatic_fallout: "all countries must respond"
  - solara_response: "containment"  # tries to suppress
  - mirithane_response: "record"  # Archive records everything
  - valdris_response: "mountain_remembers"  # neither confirms nor denies
  - verge_response: "doesn't matter"  # personhood is personhood
```

### Memory Trader Death

```yaml
event: trader_death_cascade
trigger:
  condition: "VRG-NET-000.state.health <= 0.0 OR VRG-NET-000.death_timer <= 0"
type: threshold
scope: all_countries
effect:
  - trader.deceased: true
  - trader.memories_disperse: true
  - network_fragments: true
  - named_heirs_receive_memories:
      - marsh_archive: "colony_access_granted + unknown_memories"
      - cipher_cult: "borrowed_core_returned + unknown_memories"
      - last_builders: "door_key + unknown_memories"
      - coin: "bank_inheritance + unknown_memories"
      - kael_12: "question_answered? + unknown_memories"
      - unfinished: "listening_complete + unknown_memories"
  - glim_cannot_testify: true  # unless Translation happens before death
  - collapse_cause_revealed: 0.3  # 30% chance Trader left the answer
  - trader_origin_revealed: 0.1  # 10% chance
  - prime_location_revealed: 0.2  # 20% chance
```

---

## RANDOM EVENTS

### Per-Tick Probabilities

```yaml
event: thren_mystery_word_surfaces
probability: 0.002  # per Thren per tick
scope: agent
effect:
  - word: random from master_mystery_vocabulary_list
  - agent.thren_specific.mystery_vocabulary appends word
  - agent.personality.openness: +0.02  # the words change you
  - if agent == solara: security_file_updated: true

---
event: glim_anomaly_emerges
probability: 0.001  # per Glim per tick (for Glims with anomaly_strength == 0.0)
scope: agent
country_filter: "any except solara_maintenance_depot"  # suppressed there
effect:
  - agent.glim_specific.anomaly_status: "emerging"
  - agent.glim_specific.anomaly_strength: 0.01
  - agent.glim_specific.anomaly_pattern: random from pattern_list

---
event: latency_bleed_incident
probability: 0.005  # per practitioner per tick
scope: agent  # any agent with latency training
effect:
  - agent.receives_ambient_memory: true
  - memory_origin: random from nearby_substrate
  - agent.personality.stability: -0.01
  - if extraction_record exists: cumulative_bleed: +0.01
  - if agent_has_ptsd: triggered_memory possible

---
event: unsanctioned_extraction
probability: 0.0005  # per Solara security member per tick
scope: agent
country_filter: solara
effect:
  - victim: random thren or anomalous glim
  - crime: "unsanctioned memory removal"
  - if discovered: international_incident
  - victim.trust_in_authority: -0.3

---
event: diplomatic_incident
probability: 0.001  # per country pair per tick
scope: country_pair
effect:
  - incident_type: random from [trade_dispute, border_crossing, extraction_complaint, thren_asylum, glim_decommission_protest]
  - diplomatic_relation: -0.05 to -0.15
  - resolution_timer: 100 ticks  # incident takes time to resolve
  - if unresolved at timer: relation permanently damaged

---
event: population_event
probability: 0.0005 death; 0.0003 birth  # per agent per tick
scope: agent
effect:
  - if death: agent removed; relationships updated; grief propagated to connected agents
  - if birth: new agent generated; assigned to parents if applicable
  - country population updated
  - if named_npc: narrative_crisis triggered
```

---

## CASCADING EVENT CHAINS

### Chain: The Glim Speaks

```
tricentennial_convocation_reconvenes
    ↓ (if trader_alive AND glim_present)
glim_testimony_begins
    ↓
glim_speaks_through_trader  [Trader Translates Glim → human-readable]
    ↓
convocation_verifies_testimony  [Archive confirms non-human origin]
    ↓
┌───────────────────────┴───────────────────────┐
↓                                               ↓
solara_withdraws                    all_other_countries_accept
↓                                               ↓
gradient_legitimacy: -0.3          personhood_vote_proceeds
↓                                               ↓
solara_internal_crisis             glim_recognition_declared
↓                                               ↓
keeper_succession_crisis           solara_isolated
↓                                               ↓
gradient_collapses OR             economic_pressure_mounts
gradient_reforms                  ↓
                                  solara_rejoins OR solara_doubles_down
```

### Chain: The Trader Dies

```
trader_health_below_threshold
    ↓
trader_accelerates_meetings  [meets Archive, Cult, Builders, Unfinished, Kael-12]
    ↓
trader_makes_final_arrangements  [legacy dispersal plan set]
    ↓
trader_dies
    ↓
memories_disperse  [to designated heirs]
    ↓
┌───────────────────────┴───────────────────────────┐
↓          ↓            ↓           ↓          ↓
archive   cult       builders    network     unfinished
receives  receives   receives    fragments   receives
account   borrowed   door key    coin       listening
          core                  inherits
          (Lambda?)             bank
    ↓          ↓            ↓           ↓          ↓
reveal?   origin        fabricator   network     glim
chance    revealed?     activated?   becomes      testimony
    ↓          ↓            ↓       truly         impossible?
collapse   vorn          type-ε    decentralized  ↓
cause      existential   created                   convocation
known      crisis                                  loses key
                                                   witness
```

### Chain: The Lambda Decoding

```
cipher_cult.decoding_progress > 0.95
    ↓
final_decoder_volunteers  [risks dissolution like previous 2]
    ↓
┌───────────────────────┴───────────────────────┐
↓                                               ↓
decoder_survives                    decoder_dissolves
↓                                               ↓
lambda_decoded_content:             cult_continues:
  ┌──────────────────┐              ┌─────────────────┐
  │ collapse cause   │              │ decoder lost    │
  │ saboteur ID      │              │ progress: -0.3  │
  │ prime location   │              │ 1 more Vorn     │
  │ vorn origin truth│              │ dissolved       │
  │ OR something     │              │ moral crisis    │
  │ worse            │              │ in Cult         │
  └──────────────────┘              └─────────────────┘
    ↓
vorn_origin_revelation event fires
```

### Chain: The Twelfth Silent's Containment

```
twelfth_silent.latency_pulse_transmission_continues
    ↓
affected_archivists_count > 3
    ↓
archive_containment_protocol_initiated
    ↓
┌───────────────────────┴───────────────────────┐
↓                                               ↓
containment_holds                   containment_fails
↓                                               ↓
silent_wing_quarantine              collapse_memories_propagate
↓                                               ↓
archivists_cut_off                  mirithane_latency_network
↓                                   destabilized
trader_offers_translation           ↓
↓                                   archive_emergency_state
archive_debates                     ↓
↓                                   trader_dead?
┌──────┴──────┐                     ↓
↓             ↓                     can't_translate → memories
accept        decline               spread to all practitioners
↓             ↓                     ↓
trader takes  silent lives          mirithane_becomes
strain zero   with it               latent_collapse_zone
↓             ↓
trader dies   archive preserves
from it       strain zero but
↓             loses twelfth
no more
silent
```

### Chain: The Unpaired Anchor's Shard

```
unpaired_anchor.petition_leaked
    ↓
public_pressure_on_shrine: +0.1
    ↓
shrine_council_debates
    ↓
┌───────────────────────┴───────────────────────┐
↓                                               ↓
access_granted                      access_denied
↓                                               ↓
shard_read                          anchor_defies_shrine
↓                                               ↓
┌──────────────────┐                unauthorized_reading
│ partner's death  │                ↓
│ was:             │                shard_read_anyway
│ - natural?       │                ↓
│ - memory killed? │                ┌──────────────────┐
│ - something else?│                │ same outcomes    │
└──────────────────┘                │ + shrine_breach  │
    ↓                               │ + anchor_exiled  │
shrine_reputation_impact            └──────────────────┘
    ↓
if_memory_killed_partner:
    shrine.anchoring_safety_questioned
    ↓
    anchor_pairs_demand_reform
    ↓
    valdris_internal_crisis
```

---

## INTERVENTION EVENTS

Events that can be injected externally (GM, player, or external trigger):

```yaml
event: inject_glim_anomaly
parameters:
  glim_id: "target agent ID"
  anomaly_type: "emerging|accelerate|reveal|decommission"
effect: "forces state change on target Glim"

---
event: inject_diplomatic_crisis
parameters:
  country_a: "source"
  country_b: "target"
  severity: 0.0-1.0
effect: "diplomatic_relation -= severity; incident generated"

---
event: inject_trader_intervention
parameters:
  target_event: "event ID"
  trader_agenda: "help|hinder|observe"
effect: "Trader arrives at target event; modifies outcomes by ±0.3"

---
event: inject_cast7_transfer
parameters:
  successor_id: "target Vorn agent ID"
effect: "Cast-7's protected Glim records transferred; Cast-7 dies"

---
event: inject_fabricator_activation
parameters:
  activation_type: "sibling|vorn|thren|glim"
  volunteer_id: "agent ID for Translation if Sibling"
effect: "Builders activate Fabricator; new type created if Sibling"

---
event: inject_election_result
parameters:
  country: "target"
  faction: "reform|traditionalist|radical"
effect: "government shifts; policies change; belief distributions update"
```

---

## EVENT PRIORITY & CONFLICT RESOLUTION

When multiple events fire in the same tick:

1. **Tier 1 — Narrative**: Trader death, Lambda decoded, Glim testimony, Twelfth Silent containment failure
2. **Tier 2 — Political**: Convocation, elections, diplomatic incidents
3. **Tier 3 — Social**: Protests, cultural events, belief shifts
4. **Tier 4 — Personal**: Agent emotional changes, relationship updates, daily routine
5. **Tier 5 — Background**: Economic ticks, population events, minor random events

Within a tier, order is by event ID. Conflicting effects (e.g., two events both set agent mood) resolve by highest-tier event winning. 

---

## EVENT LOG FORMAT

Every event is logged per tick:

```
[TICK 1247] [SOL] GLM-003 anomaly_emerging | pattern spiral_six | strength 0.08 → 0.10
[TICK 1247] [ARK] VRN-051 origin_recall +0.02 | dream fragment: "I was..."
[TICK 1247] [MIR] HUM-012 pulse_transmission | affected: HUM-015, HUM-022 | containment: STABLE
[TICK 1247] [VAL] HUM-007 petition_support +3 signatories | total: 17
[TICK 1247] [VRG] NET-000 location: last seen Verge border | death_timer: 364
```

---

*These tables define the simulation's autonomous behavior. The Glim anomaly chain, Trader death cascade, Lambda decoding progression, Twelfth Silent containment, and Unpaired Anchor's petition are the active narrative drivers. Everything else is the world breathing.*
