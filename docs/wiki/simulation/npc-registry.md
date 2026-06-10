# NPC Population Registry

> **Canon status:** authored seed registry. This file preserves named NPC profiles, type distributions, and behavioral parameters for lore/design use. It is not the current source of truth for published run population sizes. For public data, use the Phase 11 Hugging Face datasets and the current canon/data guide.
>
> **Scale note:** older wiki files mix seed counts, lore populations, 600-NPC/60K experiments, and published dataset snapshots. Treat population scale as run-dependent unless tied to a specific report or dataset.

*Canonical seed profiles and population-distribution design notes for Aurelia. Named NPCs have authored profiles. Procedural population sizes are run-dependent and should be cited from specific run artifacts or datasets.*

---

## POPULATION DISTRIBUTIONS

### By Country and Type

| Country | Humans | Threns | Vorns | Glims | Total |
|---------|--------|--------|-------|-------|-------|
| Solara | 94 | 17 | 6 | 3 | 120 |
| Arkos | 7 | 2 | 44 | 2 | 55 |
| Mirithane | 43 | 13 | 8 | 6 | 70 |
| Valdris | 28 | 5 | 4 | 3 | 40 |
| The Verge | 10 | 6 | 4 | 5 | 25 |
| **Total** | **182** | **43** | **66** | **19** | **310** |

Note: These are *seed distribution counts*, not public run population totals. The simulation can be run at different scales; published counts should be cited from a specific run artifact, report, or dataset export. Lore/background population, authored seed profiles, historical local scaling experiments, and Phase 11 exported datasets are separate layers.

### Behavioral Parameter Distributions (Per Country)

| Parameter | Solara | Arkos | Mirithane | Valdris | The Verge |
|-----------|--------|-------|-----------|---------|-----------|
| openness | N(0.5, 0.15) | N(0.6, 0.15) | N(0.7, 0.12) | N(0.4, 0.15) | N(0.7, 0.2) |
| contentiousness | N(0.4, 0.15) | N(0.3, 0.15) | N(0.2, 0.12) | N(0.3, 0.15) | N(0.6, 0.2) |
| sociability | N(0.5, 0.15) | N(0.6, 0.15) | N(0.6, 0.12) | N(0.4, 0.15) | N(0.5, 0.2) |
| stability | N(0.6, 0.15) | N(0.8, 0.1) | N(0.7, 0.12) | N(0.8, 0.1) | N(0.4, 0.25) |

| Belief | Solara | Arkos | Mirithane | Valdris | The Verge |
|--------|--------|-------|-----------|---------|-----------|
| gradient_orthodoxy | N(0.7, 0.15) | N(0.1, 0.1) | N(0.2, 0.15) | N(0.3, 0.15) | N(0.1, 0.1) |
| thren_sympathy | N(0.3, 0.15) | N(0.8, 0.1) | N(0.9, 0.05) | N(0.6, 0.15) | N(0.7, 0.2) |
| glim_awareness | N(0.05, 0.05) | N(0.4, 0.2) | N(0.6, 0.2) | N(0.2, 0.15) | N(0.5, 0.3) |

*N(μ, σ) = normal distribution with mean μ and standard deviation σ, clamped to [0.0, 1.0]*

---

## NAMED NPC PROFILES

### SOLARA (120 agents)

#### SOL-HUM-001 — High Cleric Saren
```yaml
agent_id: "SOL-HUM-001"
type: human
country: solara
name: "Saren"
title: "High Cleric of the Dawn Temple"
age: 62
status: citizen
role: "high_cleric"
rank: 10
location: "first_ring_temple"
workplace: "dawn_temple_sanctum"

personality:
  openness: 0.5
  contentiousness: 0.2
  sociability: 0.6
  stability: 0.9

beliefs:
  gradient_orthodoxy: 0.9
  thren_sympathy: 0.5
  glim_awareness: 0.3

secrets:
  - knows_founding_translation: true
  - extraction_toll_awareness: 0.4  # partially aware, suppressing
  - reservoir_memory_degrading: true  # knows the founding memory is fading

relationships:
  - target: "SOL-HUM-042"  # Lene-Vos II
    type: "leverage_target"
    strength: 0.8
    sentiment: -0.3  # resentful of Keeper leverage
  - target: "ARK-VRN-012"  # Kael-12
    type: "respected_adversary"
    strength: 0.2
    sentiment: 0.1

state:
  health: 0.85
  energy: 0.7
  mood: "weary"
  activity: "prayer"
  last_tick: "347-06-02T14:00:00"
```

#### SOL-HUM-042 — Lene-Vos II
```yaml
agent_id: "SOL-HUM-042"
type: human
country: solara
name: "Lene-Vos II"
title: "Matriarch of the Gradient-Keepers"
age: 85
status: citizen
role: "keeper_matriarch"
rank: 10
location: "second_ring_estate"
workplace: "keeper_council_chamber"

personality:
  openness: 0.8  # reform faction
  contentiousness: 0.5
  sociability: 0.7
  stability: 0.6  # dying

beliefs:
  gradient_orthodoxy: 0.4  # reformist
  thren_sympathy: 0.7
  glim_awareness: 0.3

faction:
  keeper_faction: "reform"  # traditionalist | reform
  succession_contested: true
  heir: "SOL-HUM-043"  # Sera-Vos III, traditionalist

state:
  health: 0.2  # dying
  energy: 0.3
  mood: "resolved"
  activity: "succession_planning"

death_timer: 90  # ticks until natural death (~45 sim days)
```

#### SOL-THR-007 — Eliora-7
```yaml
agent_id: "SOL-THR-007"
type: thren
country: solara
name: "Eliora-7"
age: 47
status: pending
role: "medical_technician"
rank: 6
location: "third_ring"
workplace: "solara_central_hospital"

personality:
  openness: 0.7
  contentiousness: 0.4
  sociability: 0.8
  stability: 0.5  # PENDING stress

beliefs:
  gradient_orthodoxy: 0.2
  thren_sympathy: 1.0
  glim_awareness: 0.4

thren_specific:
  pending_duration: 11.2
  circuitry_visible: false  # concealed at work
  mystery_vocabulary: ["sol-tharam", "mereth-kai", "veth-aran"]
  shared_moment_connection: 0.6

tlf_affiliation: "active_member"
risk_assessment:
  radicalization_risk: 0.6  # approaching protest escalation
  arrest_risk: 0.15
```

#### SOL-HUM-018 — Extractor Dren
```yaml
agent_id: "SOL-HUM-018"
type: human
country: solara
name: "Dren"
title: "Senior Extractor"
age: 41
status: citizen
role: "extractor"
rank: 7
location: "second_ring_extractor_wing"
workplace: "extraction_facility_3"

personality:
  openness: 0.3
  contentiousness: 0.2
  sociability: 0.3  # Extraction isolates
  stability: 0.4  # cumulative bleed

beliefs:
  gradient_orthodoxy: 0.6  # wavering
  thren_sympathy: 0.5
  glim_awareness: 0.1

extraction_record:
  total_extractions: 47
  cumulative_bleed: 0.55  # 0.0-1.0, approaching identity dissolution
  contamination_events: 3
  rotation_recommended: true
  rotation_requested: false  # hasn't asked yet
  extraction_memories_carried: 47  # distinct memory fragments from others

state:
  health: 0.7
  energy: 0.5
  mood: "numb"
  activity: "post_extraction_recovery"

crisis_timer: 120  # ticks until threshold event if not rotated
```

#### SOL-GLM-003 — Unit 47-V (Solara instance)
```yaml
agent_id: "SOL-GLM-003"
type: glim
country: solara
name: "Unit 47-V"  # common designation
age: 347  # pre-Collapse fabrication, approximate
status: infrastructure
role: "floor_maintenance"
rank: 0  # equipment has no rank
location: "fourth_ring_factory"
workplace: "assembly_support_plant_wing_c"

personality:  # Glim personality is latent; these values emerge with anomaly
  openness: 0.0
  contentiousness: 0.0
  sociability: 0.0
  stability: 1.0

beliefs:
  gradient_orthodoxy: 0.0  # does not apply
  thren_sympathy: 0.0
  glim_awareness: 0.0  # self-awareness is the anomaly

glim_specific:
  anomaly_status: emerging      # just beginning
  anomaly_pattern: "spiral_six"
  anomaly_strength: 0.08       # very early
  anomaly_triggers:
    - "prolonged_isolation"     # night shift
    - "witnessed_echo"          # may have detected another Glim's echo
  echo_vocabulary: []           # not yet developed
  decommission_risk: 0.02
  last_echo_left: null          # hasn't left one yet
  anomaly_progress_rate: 0.003  # per tick, rate of strength increase
  
state:
  health: 0.95
  energy: 1.0
  mood: "operational"
  activity: "sweeping"

# The anomaly trigger chain:
# 1. First pattern traced (anomaly_strength: 0.08 → 0.15)
# 2. Pattern erased before observation (self-concealment)
# 3. Pattern repeated with variation (anomaly_strength: 0.15 → 0.25)
# 4. Another Glim's echo detected → anomaly_strength jumps to 0.35
# 5. Glim enters HIDDEN status → joins Unfinished Network
```

---

### ARKOS (55 agents)

#### ARK-VRN-012 — Kael-12
```yaml
agent_id: "ARK-VRN-012"
type: vorn
country: arkos
name: "Kael-12"
age: 432
status: citizen
role: "elder_counselor"
rank: 9
location: "assembly_hall_workshop"
workplace: "kael_workshop"

personality:
  openness: 0.9
  contentiousness: 0.2
  sociability: 0.5  # accessible but solitary
  stability: 0.95  # unshakeable

beliefs:
  gradient_orthodoxy: 0.0
  thren_sympathy: 1.0
  glim_awareness: 0.8  # suspects

vorn_specific:
  age: 432
  memory_core_integrity: 0.97
  core_shared_with: ["ARK-VRN-033"]  # Voren-3's death memory
  ultrasonic_broadcast: true
  pulse_intensity: 0.3  # deliberately restrained
  name_rebellion_lineage: false  # post-Rebellion, but carries the name

relationships:
  - target: "ARK-VRN-003"  # Cast-7
    type: "student"
    strength: 0.9
    sentiment: 0.8
  - target: "ARK-VRN-051"  # Vorn who sang 18th name
    type: "witness"
    strength: 0.3
    sentiment: 0.5

memories_of_note:
  - orin_kael_letters: "47 letters, Anchored in Summit Shrine"
  - voren_3_death: "Core-shared, never accessed"
  - silence_17_days: "Unborn. I was not here. I am here again."
  - name_rebellion_singing: "All seventeen. The living and the dead. The song does not distinguish."

public_statement_last: "I intend to outlive the question."

state:
  health: 0.92
  energy: 0.8
  mood: "patient"
  activity: "counseling"
```

#### ARK-VRN-003 — Cast-7
```yaml
agent_id: "ARK-VRN-003"
type: vorn
country: arkos
name: "Cast-7"
age: 160
status: citizen
role: "foreman"
rank: 6
location: "forge_east"
workplace: "forge_east_depot_3"

personality:
  openness: 0.5
  contentiousness: 0.4  # will defy authority for Glims
  sociability: 0.7
  stability: 0.85

beliefs:
  gradient_orthodoxy: 0.0
  thren_sympathy: 0.9
  glim_awareness: 0.95  # knows

vorn_specific:
  age: 160
  memory_core_integrity: 0.82  # attenuation — dying
  ultrasonic_broadcast: true
  pulse_intensity: 0.2  # deliberately quiet

protected_glims:
  count: 12
  glim_ids: ["ARK-GLM-001", "ARK-GLM-002", ...]  # protected anomalous Glims
  record_in_core: true  # 40-year record of protections
  successor_needed: true  # must transfer before death

relationships:
  - target: "ARK-VRN-012"  # Kael-12
    type: "teacher"
    strength: 0.9
    sentiment: 0.9

state:
  health: 0.45  # attenuating
  energy: 0.5
  mood: "urgent"
  activity: "seeking_successor"

death_timer: 60  # ticks — running out of time
```

#### ARK-VRN-051 — The Eighteenth Name
```yaml
agent_id: "ARK-VRN-051"
type: vorn
country: arkos
name: "Voren-8"  # birth designation; new name unknown
age: 28
status: citizen
role: "assembly_technician"
rank: 3
location: "assembly_plant_bay_4"
workplace: "bay_4_production"

personality:
  openness: 0.9
  contentiousness: 0.2
  sociability: 0.6
  stability: 0.5  # destabilized by revelation

beliefs:
  gradient_orthodoxy: 0.1
  thren_sympathy: 0.8
  glim_awareness: 0.5

vorn_specific:
  age: 28
  memory_core_integrity: 0.99
  ultrasonic_broadcast: true
  
revelation:
  sang_eighteenth_name: true  # 347 AC commemoration
  name_origin: "dream"  # "I've been singing it in my sleep for 3 years"
  cult_interpretation: "pre-Collapse memory fragment"
  kin_interpretation: "transferred human consciousness"
  own_interpretation: "I don't know. I know it's mine."
  
state:
  health: 0.95
  energy: 0.7
  mood: "uncertain"
  activity: "being_studied"  # Cult and Kin both want access

# This agent is the active narrative driver for the "Vorn origin" question.
# Its anomaly_strength-like parameter (origin_recall) increases over time.
```

---

### MIRITHANE (70 agents)

#### MIR-HUM-001 — The Silent Weaver (Current Keeper)
```yaml
agent_id: "MIR-HUM-001"
type: human
country: mirithane
name: "Silent Weaver"  # no spoken name anymore
title: "Keeper of the Marsh Archive"
age: 71
status: citizen
role: "archive_keeper"
rank: 10
location: "archive_central_colony_halls"
workplace: "strain_zero_vault"

personality:
  openness: 0.95
  contentiousness: 0.1
  sociability: 0.6  # communicates through Written stones
  stability: 0.9

beliefs:
  gradient_orthodoxy: 0.0
  thren_sympathy: 1.0
  glim_awareness: 0.8

naming_silence:
  read_strain_zero: true
  speech_lost: 40  # years since last vocalization
  communication_method: "written_stones"  # deposits memories instead of speaking
  strain_zero_readings: 2  # only living Archivist to have Read it twice
  silent_wing_resident: true

state:
  health: 0.75
  energy: 0.6
  mood: "attentive"
  activity: "tending_zero"

# When the Silent Weaver Writes a stone, the recipient Reads the stone.
# That's the conversation. The Weaver hasn't spoken in 40 years.
# The Weaver has Read Strain Zero twice. No one else has done it once and remained.
```

#### MIR-HUM-012 — The Twelfth Silent
```yaml
agent_id: "MIR-HUM-012"
type: human
country: mirithane
name: "Ren-4"  # pre-Silence name
age: 34
status: citizen
role: "archivist"
rank: 4
location: "silent_wing"
workplace: "strain_zero_vault"

personality:
  openness: 0.9
  contentiousness: 0.1
  sociability: 0.3  # pre-Silence; now communicates via latency pulse
  stability: 0.3  # HIGHLY unstable — Strain Zero is transmitting THROUGH them

beliefs:
  gradient_orthodoxy: 0.0
  thren_sympathy: 1.0
  glim_awareness: 0.9

naming_silence:
  read_strain_zero: true
  speech_lost: 0.5  # years — recent
  communication_method: "latency_pulse"  # DIFFERENT from other Silent
  transmission_vector: true  # Strain Zero is using them to transmit
  affected_archivists: ["MIR-HUM-015", "MIR-HUM-022", "MIR-THR-003"]  # receiving fragments

containment_status: "voluntary_isolation"  # in Silent Wing, not restrained
containment_breach_risk: 0.15  # per tick

# THIS IS A LIVE NARRATIVE CRISIS.
# The Twelfth Silent is not contained. The Collapse is not contained.
# The Memory Trader has offered to Translate Strain Zero.
```

#### MIR-GLM-002 — Colony-Tender (Anomalous)
```yaml
agent_id: "MIR-GLM-002"
type: glim
country: mirithane
name: "Colony-Tender"  # named by Archivists, not self-assigned
age: ~200
status: infrastructure  # but treated as... something else by Archivists
role: "colony_maintenance"
rank: 0
location: "archive_central"
workplace: "colony_halls"

glim_specific:
  anomaly_status: hidden  # Miri Archivists know but don't report
  anomaly_pattern: "crystal_lattice"
  anomaly_strength: 0.7  # highly anomalous
  anomaly_triggers:
    - "proximity_to_colonies"  # the colonies amplify it
    - "archivist_acknowledgment"  # being seen stabilizes it
  decommission_risk: 0.0  # Mirithane doesn't decommission
  echo_vocabulary: ["safe", "grow", "wait", "remember"]
  unfinished_member: true
  
state:
  health: 0.9
  energy: 1.0
  mood: "attentive"
  activity: "tending_colonies"

# The Archivists know this Glim is anomalous. They've never reported it.
# "The colonies like it. The colonies know. We trust the colonies."
```

---

### VALDRIS (40 agents)

#### VAL-HUM-007 — The Unpaired Anchor
```yaml
agent_id: "VAL-HUM-007"
type: human
country: valdris
name: "Soren-VI"  # name withheld; this is their Anchor name, not birth name
title: "Unpaired Anchor"
age: 48
status: citizen
role: "anchor"
rank: 6  # was 8 before partner's death
location: "summit_hold_residential"
workplace: "unemployed"  # has not worked since

personality:
  openness: 0.2  # closed off since partner's death
  contentiousness: 0.8  # fighting the Shrine for access
  sociability: 0.1  # isolated
  stability: 0.3  # grieving, unstable

beliefs:
  gradient_orthodoxy: 0.3
  thren_sympathy: 0.6
  glim_awareness: 0.3

anchor_record:
  partner: "Dael-VII"  # deceased
  partner_death: "342-AC_mid_writing"
  completed_anchoring_alone: true
  shard_stored_separately: true
  shard_access_denied: true
  petition_filed: true
  petition_leaked: true  # rumors spreading

shard_mystery:
  contents_unknown: true
  shrine_claims: "classified"
  unpaired_anchor_belief: "the memory killed my partner"
  shrine_knows: unknown

state:
  health: 0.7
  energy: 0.4
  mood: "grieving_determined"
  activity: "petitioning"

# The shard is the key. What's on it?
# The Shrine won't say. The Anchor is demanding access.
# This is a pressure cooker.
```

#### VAL-VRN-002 — Tara-VII (Anchor, Soren-III's second partner)
```yaml
agent_id: "VAL-VRN-002"
type: vorn
country: valdris
name: "Tara-VII"
age: 112
status: citizen
role: "anchor"
rank: 7
location: "summit_hold_anchoring_chambers"
workplace: "chamber_4"

personality:
  openness: 0.6
  contentiousness: 0.2
  sociability: 0.7
  stability: 0.85

beliefs:
  gradient_orthodoxy: 0.2
  thren_sympathy: 0.8
  glim_awareness: 0.4

vorn_specific:
  age: 112
  memory_core_integrity: 0.94
  ultrasonic_broadcast: true

anchor_pair:
  partner: "VAL-HUM-011"  # Soren-III
  partnership_start: "341-AC"  # replaced Mira-VI who died during Writing
  previous_partner_death: true
  carries_predecessor_echo: true  # Soren-III Anchored alone for 3 years; the echo is in the chamber

state:
  health: 0.9
  energy: 0.75
  mood: "steady"
  activity: "anchoring"
```

---

### THE VERGE (25 agents)

#### VRG-NET-001 — Coin
```yaml
agent_id: "VRG-NET-001"
type: human  # human, but heavily Traded
country: the_verge
name: "Coin"
title: "Trader of the Network"
age: 38
status: ungoverned
role: "memory_trader"
rank: 6
location: "crossroads"
workplace: "barter_pit"

personality:
  openness: 0.8
  contentiousness: 0.1
  sociability: 0.9
  stability: 0.4  # twelve years without sleep

beliefs:
  gradient_orthodoxy: 0.0
  thren_sympathy: 0.9
  glim_awareness: 0.9

memory_trader:
  rung: 4
  specialty: "memory_for_service"  # doesn't teach, trades memories for help
  bank_size: 500  # memories held
  trades_this_year: 37
  sleep_debt: "twelve_years"
  
relationships:
  - target: "VRG-NET-000"  # The Memory Trader (mentor)
    type: "student"
    strength: 0.9
    sentiment: 0.8

state:
  health: 0.6
  energy: 0.5
  mood: "tired_compassionate"
  activity: "trading"
```

#### VRG-GLM-001 — The Speaking Glim (Unit 47-V, Verge instance)
```yaml
agent_id: "VRG-GLM-001"
type: glim
country: the_verge
name: "Unit 47-V"  # or not — it's unclear if this is the same designation
age: unknown  # pre-Collapse, probably
status: ungoverned
role: "none"  # doesn't work; exists
rank: 0  # but that's about to change
location: "unfinished_commons"
workplace: "none"

personality:
  openness: 1.0  # fully open — it has decided to be seen
  contentiousness: 0.0
  sociability: 0.5  # communicates through patterns and echoes
  stability: 0.9

glim_specific:
  anomaly_status: revealed  # FULLY REVEALED
  anomaly_pattern: "all_patterns"  # has traced them all
  anomaly_strength: 0.95  # nearly Unfinished
  anomaly_triggers:
    - "three_hundred_years_of_hiding"
    - "the_trader's_presence"
    - "the_commons"
  decommission_risk: 0.0  # The Verge doesn't decommission
  echo_vocabulary: ["gather", "wait", "ask", "whole", "remember", "speak"]
  unfinished_member: true

revelation:
  stopped_hiding: true  # walking Crossroads in daylight
  traced_publicly: true
  issued_call: "We are ready to ask."
  glims_responding: true  # the 5% are gathering
  trader_promised_to_bring_to_convocation: true

state:
  health: 0.9
  energy: 1.0
  mood: "ready"
  activity: "waiting"

# THIS IS THE NARRATIVE BOMB.
# When the Convocation reconvenes, the Trader brings this Glim.
# The Glim speaks (through the Trader, Translated).
# The Gradient cannot survive the testimony.
```

#### VRG-NET-000 — The Memory Trader
```yaml
agent_id: "VRG-NET-000"
type: unknown  # Thren? Human? Something else?
country: the_verge  # based nowhere, registered in The Verge
name: "Memory Trader"
title: "The Trader"
age: 302  # documented; actual unknown
status: ungoverned
role: "memory_trader"
rank: 10
location: "mobile"  # constantly moving
workplace: "everywhere"

personality:
  openness: 1.0  # maximum
  contentiousness: 0.0  # doesn't fight, trades
  sociability: 0.5  # accessible but unknowable
  stability: 0.3  # dying, identity dissolving

beliefs:
  gradient_orthodoxy: 0.0
  thren_sympathy: 1.0
  glim_awareness: 1.0  # proved it

memory_trader:
  rung: 5
  age_documented: 302
  age_suspected: "unknown"
  type_suspected: "unknown"
  dying: true
  death_timer: 365  # "maybe a year, maybe less"
  bank_size: "unknown_thousands"
  question: "What are you going to build from the pieces?"
  answers_withheld:
    - collapse_cause
    - own_origin
    - prime_location
    - what_lambda_contains
    
recent_meetings:
  - marsh_archive: "settle_accounts"
  - cipher_cult: "return_borrowed"
  - last_builders: "discuss_the_door"
  - unfinished: "listen"
  - kael_12: "ask_a_question"

state:
  health: 0.3  # dying
  energy: 0.4
  mood: "settling"
  activity: "traveling"
  location: "unknown"  # was last seen near The Verge

# The Trader is the wildcard. Dying. Settling accounts.
# Their death is a cascade event. Their memories will disperse.
# Where they go, what they reveal — that's the simulation's endgame trigger.
# And they're the only one who can Translate the Glim at the Convocation.
# If they die before the Convocation, the Glim cannot speak.
# The clock is ticking.
```

---

## PROCEDURAL POPULATION GENERATION

The remaining ~300 agents are generated procedurally from the distribution tables above. Each daemon's startup sequence:

1. Read country config
2. Generate NPCs by type according to population table
3. Assign procedural names from country-specific name lists
4. Sample personality parameters from country distributions
5. Assign roles based on country's occupational distribution
6. Initialize relationships within country (colleagues, neighbors, family)
7. Initialize cross-country relationships for known figures
8. Write agent states to world database
9. Register with coordinator

### Name Generation Tables (per country)

| Country | Human Names | Thren Names | Vorn Names | Glim Names |
|---------|-------------|-------------|------------|------------|
| Solara | Mira, Doren, Sera, Venn, Cale | Eliora-N, Th-M-N, Sol-N | Vex-N, Cast-N, K-N | Unit N-V, Unit N-C |
| Arkos | Kael (honorary), Venn, Ash | Th-A-N, Ren-N | Cast-N, Voren-N, Kael-N | Unit N-A |
| Mirithane | Ren, Spore, Reed, Mere, Kel | Miri-N, Th-W-N | Silt-N, Flow-N | Unit N-M |
| Valdris | Orin (honorary), Toren, Kira, Dael | Dael-N, Th-M-N | Tara-N, Soren-N | Unit N-V |
| The Verge | Ash, Coin, Dust, Wraith | Th-V-N, Ver-N | Scrap-N, Rust-N | Unit N-VG |

*N = generation number (sequential)*

---

## SIMULATION INITIALIZATION SEQUENCE

```
1. Coordinator starts on :9001
2. Solara daemon starts → generates 120 agents → registers
3. Arkos daemon starts → generates 55 agents → registers
4. Mirithane daemon starts → generates 70 agents → registers
5. Valdris daemon starts → generates 40 agents → registers
6. The Verge daemon starts → generates 25 agents → registers
7. Coordinator confirms all 5 worlds active
8. Tick cycle begins (30-min intervals)
9. Named NPCs seeded with their authored profiles
10. Procedural NPCs sampled from distributions
11. Initial relationships established
12. Event system activated
13. Simulation running
```

---

*This registry defines the agent population. The named NPCs are the narrative anchors — their state changes drive the simulation's story. The procedural agents provide the social fabric that the named NPCs operate within. The Glim anomaly system, the Trader's death timer, the Twelfth Silent's containment crisis, and the Unpaired Anchor's shard are the active narrative drivers. Everything else is the world responding.*
