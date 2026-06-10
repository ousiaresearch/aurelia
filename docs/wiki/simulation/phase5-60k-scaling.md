# Phase 5 — Historical 60K Scaling Experiment

> **Canon status:** historical scaling experiment. This file records an older 60K local-daemon engineering benchmark. It is useful for stratified sampling, bounded social graph, and name-generation ideas, but it is not the current public scale claim for Aurelia.
>
> Current public scale claims should cite a specific run report or Hugging Face dataset export.

*Recorded 2026-06-04 as a local scaling benchmark: 5 worlds at 12,000 NPCs each, 60,000 total.*

## What Changed

Phase 5 answered the question: can Aurelia scale from 600 NPCs to 60,000 without breaking growth mechanics or observability? The answer is yes — through stratified sampling, bounded social graphs, and combinatorial name generation.

## Key Innovations

| Innovation | Before | After |
|---|---|---|
| NPCs per world | 120 | **12,000** |
| Total NPCs | 600 | **60,000** |
| Schedules per world | 2,880 | **288,000** |
| Relationships per world | ~154 | **~55,000** |
| DB size per world | 3MB | **~67MB** |
| Name pool capacity | ~50 unique/type | **139,000+ unique/type** |
| Population checks/tick | 25 (21% sweep) | **300 stratified (2.5% sweep)** |
| NPC AI cap | Uncapped | **200 actions/tick** |
| NPC movement | All every tick | **500/tick round-robin** |
| Decision state | Lazy-init | **Pre-seeded at generation** |
| Action retention | Unlimited | **100/NPC cap** |
| Coordinator stats | Full scan | **5K row sample** |

## Stratified Sampling

At 12,000 NPCs, checking all of them every tick would take ~4 seconds (unacceptable at 30-min tick intervals). Stratified sampling divides NPCs into 4 tiers:

- **Tier 1 (high attention):** NPCs with elevated decision variables (security < 0.3, anomaly_pressure > 0.5, restlessness > 0.6) — checked every tick. ~5% of population.
- **Tier 2 (medium attention):** NPCs in faction regions, border zones, or recent event locations — checked every 3 ticks. ~15% of population.
- **Tier 3 (baseline):** Standard NPCs — checked every 10 ticks. ~60% of population.
- **Tier 4 (stable):** NPCs with high satisfaction, high security, low restlessness — checked every 20 ticks. ~20% of population.

Total checks per tick: 300. Full sweep of all 12,000 NPCs over ~40 ticks (1.7 sim-days).

## Bounded Social Graph

The Phase 1-3 social graph was O(n²) — every NPC had a relationship with every other NPC. At 12,000 NPCs, that's 144M relationships (completely infeasible). Phase 5 replaced it with:

- **Workplace clusters:** NPCs are socially linked to others in the same location category
- **Family/kin clusters:** Pre-generated family units of 3-8 NPCs
- **Neighbor clusters:** Spatial proximity within the same region tile
- **Cap:** 10-15 relationships per NPC, stored as a bounded adjacency list

Total relationships per world: ~55,000 (15 per NPC average × 12,000, deduplicated). That's O(n) storage — sustainable.

## Combinatorial Name Generation

The old system had ~50 names per type, which wouldn't scale beyond 600 NPCs. Phase 5 uses syllable splicing:

```
human_names: ~139,000 unique combinations from 130 prefixes × 110 suffixes
thren_names: combinatorial from logic/mystery syllable pairs
vorn_names: Kael-{number} format, sequential per forge batch
glim_names: {prefix}-{number} format, sequential per production batch
```

## Performance at 60K

- Tick duration: <1 second (target: <2s)
- DB writes per tick: ~500 rows (300 pop checks + 200 AI actions)
- Coordinator `/api/growth`: <100ms (cached, 5K-row cap)
- Total storage: ~335MB (5 worlds × 67MB)
- Memory per daemon: ~200MB (Python process + SQLite WAL)

## Files Changed

- `populate_npcs.py` — combinatorial names, NPC_COUNT=12000, type-aware occupations
- `deep_seed.py` — bounded O(n) social graph, decision state seeding
- `simulation.py` — stratified sampling, AI cap, movement pagination
- `npc_ai.py` — action cap, retention cap
- `aurelia_coordinator.py` — stats capped at 5K rows

## Related Documents

- [Simulation Architecture](simulation-architecture.md) — overall architecture
- [Phase 4 Growth Engine](phase4-growth-engine.md) — decision-driven mechanics
- [Phase 6 Geopolitics](phase6-geopolitics.md) — what happens next
