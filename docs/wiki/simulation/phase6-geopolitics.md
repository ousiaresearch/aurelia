# Phase 6 — Emergent Geopolitics

*Deployed 2026-06-04. Factions, conflict escalation, and sovereignty emergence layered over 60,000 NPCs across 5 worlds.*

## The Core Insight

Phase 4 was a **condition engine** — it told you *who* was unhappy, *how much* pressure had accumulated, *which* diplomatic pair was deteriorating. But it had no mechanism for those conditions to organize into collective action. Phase 6 adds the three missing nouns:

1. **Factions** — organized groups of NPCs with shared grievances, leaders, membership, demands
2. **Escalation Ladder** — a state machine from dormant grievance through to full war
3. **Sovereignty Pipeline** — when a faction controls territory+population+resources, it can become a country

## Architecture

```
┌──────────────────────────────────────────────────┐
│  Module 1: Faction Engine                        │
│  Grievance density scan → faction formation      │
│  Membership, leadership, recruitment, influence  │
│  5 grievance types, ≥10 NPC formation threshold  │
├──────────────────────────────────────────────────┤
│  Module 2: Escalation Ladder                     │
│  dormant→grievance→organization→ultimatum        │
│  →skirmish→armed_conflict→war                    │
│  Government repression, intervention, mortality  │
├──────────────────────────────────────────────────┤
│  Module 3: Sovereignty Pipeline                  │
│  Territory + population + survival thresholds    │
│  Declaration → recognition → secession           │
│  Springtime of Nations cascade boost             │
└──────────────────────────────────────────────────┘
```

All three modules are probability-driven, not timer-driven. Nothing fires on a schedule — everything fires because conditions tipped.

## Faction Engine

### Grievance Types

Factions form around shared grievances detected through NPC decision state variables:

| Grievance | Trigger Condition | Example Demand |
|---|---|---|
| **Oppression** | security < 0.3, observed_injustice > 0.5 | "End decommissioning of sentient beings" |
| **Poverty** | satisfaction < 0.3, economic_stability < 0.3 | "Land reform and redistribution" |
| **Displacement** | restlessness > 0.7 | "Right of return to ancestral territories" |
| **Personhood** | anomaly_pressure > 0.5 (Glim only) | "Recognition of Glim personhood" |
| **Autonomy** | connectedness > 0.7, restlessness > 0.4 | "Regional autonomy and self-governance" |

### Formation Mechanics

1. Every tick, the grievance density scanner counts NPCs with shared grievances in each region
2. When ≥10 NPCs in the same region share a grievance, a formation check fires
3. Base probability (0.3%) × density multiplier × world state modifiers (Glim anomalies, diplomatic incidents)
4. On success: faction forms with up to 20 initial members, a leader, and a randomly assigned demand
5. Factions recruit new members each tick from aligned NPCs in their region

### Influence

Faction influence = Σ (1 - security) × (1 + connectedness) per member. Higher influence accelerates escalation and increases recruitment. Government repression counterbalances.

## Escalation Ladder

Seven rungs, probability-modulated. No timer fires any step.

| Rung | Base Probability | Effects |
|---|---|---|
| Dormant | — | No active grievance expression |
| Grievance | 1.0%→Organization | Complaints, petitions |
| Organization | 0.5%→Ultimatum | Structured demands, public presence |
| Ultimatum | 0.3%→Skirmish | Deadline, threat of action |
| Skirmish | 0.2%→Armed Conflict | Low-level violence, property damage |
| Armed Conflict | 0.1%→War | Organized combat, casualties begin |
| War | — | Full-scale conflict, mass migration |

### Modifiers

- **Faction influence** — more members, more escalation pressure
- **Government repression** — Solara (high) suppresses; Verge (low) enables
- **Diplomatic tension** — higher regional tension → faster escalation
- **Government stability** — lower stability → more likely to crack
- **Glim anomalies** — chaos multiplier
- **Economic instability** — financial strain drives radicalization

### Intervention

When a faction reaches skirmish level, other countries roll for intervention:
- High tension with parent country → support the rebels
- High trust with parent country → diplomatic mediation
- Arkos protects autonomy/personhood movements
- Verge recognizes most secessionist factions

## Sovereignty Pipeline

The ultimate expression of emergent geopolitics: a faction becomes a country.

### Thresholds

| Requirement | Threshold |
|---|---|
| Territory control | ≥ 60% of region |
| Member count | ≥ 300 NPCs |
| Conflict survival | ≥ 3 ticks at armed_conflict+ |
| External recognition | ≥ 1 country |

### Process

1. **Declaration** — Faction meets thresholds → rolls for independence (base 1% × influence × territory × recognition)
2. **Recognition** — Other countries roll recognition (20% base, +30% if tension with parent > 0.5, +20% for Verge)
3. **Secession** — ≥1 recognition → faction becomes sovereign country. Members gain new nationality. Parent country loses population.
4. **Cascade** — Successful secession triggers a "Springtime of Nations" effect: +50% faction formation probability globally for 10 ticks.

## Government Profiles

| Country | Repression | Concession Willingness | Stability |
|---|---|---|---|
| Solara | 0.7 (high) | 0.3 (low) | 0.65 |
| Arkos | 0.5 | 0.6 (high) | 0.75 |
| Mirithane | 0.4 (low) | 0.55 | 0.7 |
| Valdris | 0.55 | 0.45 | 0.6 |
| The Verge | 0.2 (very low) | 0.7 (highest) | 0.4 (lowest) |

## Population Effects

- **Skirmish+** : Migration pressure on NPCs in faction region (restlessness +0.02/tick)
- **Armed Conflict+** : 0.5% mortality/tick for faction members
- **War** : 2% mortality/tick for members, mass migration for all NPCs in country

## Dashboard Observability

Phase 6 panels are live at `http://127.0.0.1:9001`:

- **Faction Summary** — active factions, total members, at-war count, per-country table
- **Conflict Ladder** — 7-rung visualization with per-world positions
- **Sovereignty Card** — secession count, new countries, declaring factions, cascade status

API endpoint: `GET /api/growth` returns `faction_counts`, `conflict_state`, `sovereignty`.

## Code

| File | Lines | Purpose |
|---|---|---|
| `faction_engine.py` | 570 | Faction formation, membership, influence |
| `escalation_ladder.py` | 510 | 7-rung state machine, intervention, fallout |
| `sovereignty.py` | 460 | Declaration, recognition, secession, cascade |

## Design Principles

- **Decision-driven, not timer-driven.** Factions don't form on a schedule. They form because enough NPCs accumulate enough shared grievance.
- **Probability-modulated, not condition-gated.** Like narrative seeds, faction formation uses base probability × multipliers from existing state.
- **Cascading consequences.** A rebellion in Solara degrades trade relations → strains Arkos's economy → increases Glim pressure → more anomalies.
- **Observable at every stage.** All metrics visible through dashboard and API.

## Related Documents

- [Simulation Architecture](simulation-architecture.md) — overall architecture
- [Phase 4 Growth Engine](phase4-growth-engine.md) — the condition layer Phase 6 consumes
- [Phase 5 60K Scaling](phase5-60k-scaling.md) — the population scale Phase 6 operates on
