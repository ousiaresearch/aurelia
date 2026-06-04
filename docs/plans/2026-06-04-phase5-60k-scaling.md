# Aurelia — 60K NPC Scaling Plan

> **For Hermes:** Implement Phase 5 AFTER Phase 4 is fully stabilized. This plan assumes Phase 4 modules are deployed and running.

**Goal:** Scale from 600 NPCs (120/world × 5) to 60,000 NPCs (12,000/world) while preserving decision-driven sporadic growth. Every scaling choice must maintain the Phase 4 invariant: nothing fires on a schedule, everything fires because conditions tipped.

**Architecture:** 6 scaling modules. Tier 1 makes generation possible. Tier 2 fixes runtime bottlenecks. Tier 3 ensures growth observability still works. No module changes growth mechanics — only throughput.

**Tech Stack:** Python 3.13, SQLite (per-world DBs), `deep_seed.py`, `populate_npcs.py`, `simulation.py`

---

## Current Limits (Baseline at 600 NPCs)

| Resource | Current | At 12k/world | Bottleneck? |
|---|---|---|---|
| DB size per world | 3MB | ~250MB | No |
| Schedule rows | 2,880 | 288,000 | No (18MB) |
| Relationship rows | ~154 | 3,000 (capped) | **Yes — pairwise O(n²)** |
| Pop dynamics sweep | 25/tick | 300/tick target | **Yes — LIMIT 25 hardcoded** |
| NPC AI tick | 120 iterated | 12,000 iterated | **Yes — 100× linear** |
| NPC movement | 120 iterated | 12,000 iterated | **Yes — 100× linear** |
| Name pools | ~55 given names | Exhaust at ~50 | **Yes — too small** |
| Deep-seed runtime | <1s | ~30s (estimated) | No |
| Coordinator ingestion | ~25/tick | ~300/tick with pop events | No (just more events) |

---

## Module S1: Name Pool Expansion & Parametric NPC Generation

### Goal
Name pools currently exhaust at ~50 NPCs per category (55 human given, 35 Thren, 30 Vorn, 25 Glim IDs). Need combinatorial generation producing 12,000 unique NPCs per world.

### Why First
Can't scale if you can't name them. Also need a system that doesn't require hand-authoring 12,000 occupation-type-location tuples.

---

### Task S1.1: Combinatorial name generation

**Objective:** Replace hardcoded name lists with a combinatorial generator using prefix/suffix pools.

**Files:**
- Modify: `populate_npcs.py`

**Approach:**
```python
# Human names: given (55 prefixes) × surnames (35 suffixes) = 1,925 combinations
# With middle-name toggle: 55 × 2 × 35 = 3,850 unique full names
# Not enough — need 12k.

# Instead: given name pool × 4 with combinatorial syllable splicing
HUMAN_GIVEN_SYLLABLES = [
    "Ar", "Ka", "No", "Ze", "Ly", "Or", "Ve", "Ru",
    "Ta", "So", "Em", "Ash", "Ter", "Lu", "Vae", "Ny",
    "Se", "Mi", "Tha", "Jo", "Kes", "Pax", "Si", "Za",
    "Iv", "Ek", "Zin", "Fa", "Qui", "Re", "Ga", "Ha",
    "Tes", "Dex", "Ne", "Fen", "Orl", "Br", "Sa", "Ven",
    "Ro", "Cle", "Fli", "In", "Jun", "Lio", "Me", "Na",
    "Ore", "Pet", "Rai", "Su", "Teo", "Um", "Vos", "Wy",
    "Xe", "Cy", "Zel", "Tor", "Val", "Mar", "Del", "Fae",
]

# 64 syllables → 2-syllable given names = 4,096 unique names
# × 34 surnames = 139,264 unique full names per world
# Add 3-syllable variant for variability
```

**Thren, Vorn, Glim:** Same approach with type-appropriate syllable pools (soft/breathy for Thren, hard/consonant-heavy for Vorn, functional/alphanumeric for Glim).

**Step 1: Test combinatorial generation**
```bash
cd /Users/johann/aurelia && python3 -c "
from populate_npcs import generate_human_name, generate_thren_name, generate_vorn_name, generate_glim_id
# Generate 100 unique names of each type
human = set()
for _ in range(1000):
    human.add(generate_human_name())
print(f'Human: {len(human)} unique from 1000 attempts')
# Repeat for thren, vorn, glim
"
```

**Step 2: Commit**
```bash
git add populate_npcs.py
git commit -m "feat(scaling): combinatorial name generation — 64-syllable pools per type"
```

---

### Task S1.2: Parametric occupation-type-location assignment

**Objective:** Don't list every NPC's occupation. Generate from weighted distributions seeded by country-type weights.

**Files:**
- Modify: `populate_npcs.py`

**Approach:**
```python
# Occupation × type compatibility matrix
# Thren-heavy jobs: biofuel_chemist, reef_cultivator, filtration_tech, biosynth_lab
# Vorn-heavy jobs: forge_operator, metal_smith, sand_glass_engineer, drone_station_op
# Glim-heavy jobs: solar_panel_cleaner, kelp_harvester, salvage_sort, warehouse_loader
# Human-heavy jobs: bureaucrat, merchant, teacher, medic, guide, trader

# For each NPC: roll type from country weights, then roll occupation from
# type-compatible pool, then assign location from country-specific location map
```

**Step 1: Verify distribution at 12k**
```bash
python3 -c "
# Generate 12k NPCs for solara, print distribution
types = {'thren': 0, 'vorn': 0, 'glim': 0, 'human': 0}
for _ in range(12000):
    t = weighted_choice(TYPE_WEIGHTS['solara'], ['thren','vorn','glim','human'])
    types[t] += 1
print(types)
# Expected: ~4200 thren, ~1200 vorn, ~1800 glim, ~4800 human
"
```

**Step 2: Commit**
```bash
git add populate_npcs.py
git commit -m "feat(scaling): parametric NPC generation — type-weight × occupation-matrix × location-map"
```

---

## Module S2: Relationship Generation Reform

### Goal
Current `generate_relationships()` is pairwise O(n²). At 12k NPCs, that's 144M candidate pairs — will time out. Replace with bounded social graph generation.

### Why Critical
`deep_seed.py` runs `generate_relationships()` which loops all pairs. At 12k this will hang.

---

### Task S2.1: Bounded social graph

**Objective:** Replace full pairwise iteration with stratified random sampling targeting a fixed relationship count per NPC.

**Files:**
- Modify: `deep_seed.py` — `generate_relationships()`

**Approach:**
```python
# TARGET: ~5 relationships per NPC (was ~1.3 at 120)
# At 12k: 12,000 × 5 / 2 = 30,000 relationship rows per world
# (not 144M)

# Coworkers: group by occupation, pick 3 random colleagues per NPC
# Neighbors: group by location, pick 2 random neighbors per NPC  
# Type-bonds: group by type, pick 1 random type-sibling per NPC (Thren/Vorn only)
# Cross-type: pick 1 random cross-type ally per NPC
# Rivals: pick 1 random rival per NPC (20% chance)

# Use reservoir sampling — never materialize the full pairwise list
def generate_relationships_bounded(npcs_by_id, country_id, max_per_npc=5):
    relationships = []
    npc_list = list(npcs_by_id.keys())
    
    # Build index: occupation → [npc_ids], location → [npc_ids], type → [npc_ids]
    occ_index = {}
    loc_index = {}
    type_index = {}
    for nid, info in npcs_by_id.items():
        occ = info.get("occupation", "")
        loc = info.get("location_id", "")
        t = info.get("npc_type", "human")
        occ_index.setdefault(occ, []).append(nid)
        loc_index.setdefault(loc, []).append(nid)
        type_index.setdefault(t, []).append(nid)
    
    for nid, info in npcs_by_id.items():
        occ = info.get("occupation", "")
        loc = info.get("location_id", "")
        t = info.get("npc_type", "human")
        
        candidates = set()
        # 2 coworkers
        coworkers = [c for c in occ_index.get(occ, []) if c != nid]
        if coworkers:
            candidates.update(random.sample(coworkers, min(2, len(coworkers))))
        # 1 neighbor  
        neighbors = [c for c in loc_index.get(loc, []) if c != nid]
        if neighbors:
            candidates.update(random.sample(neighbors, min(1, len(neighbors))))
        # 1 type-bond
        if t in ("thren", "vorn"):
            bonds = [c for c in type_index.get(t, []) if c != nid and c not in candidates]
            if bonds:
                candidates.update(random.sample(bonds, min(1, len(bonds))))
        # 1 cross-type
        other_types = [ot for ot in type_index if ot != t]
        if other_types:
            cross = [c for ot in other_types for c in type_index[ot] if c != nid and c not in candidates]
            if cross:
                candidates.update(random.sample(cross, min(1, len(cross))))
        
        for other in candidates:
            rtype = _determine_relation_type(nid, other, npcs_by_id)
            relationships.append(_rel(nid, other, rtype, 0.2, 0.7))
    
    return relationships
```

**Step 1: Benchmark at 12k**
```bash
cd /Users/johann/aurelia && python3 -c "
import time
# Mock 12k NPCs
npcs = {f'npc_sol_{i:05d}': {
    'occupation': random.choice(['biofuel_chemist', 'kelp_farmer', 'bureaucrat', 'forge_operator']),
    'location_id': random.choice(['lumen_plaza', 'kelp_farms', 'second_ring', 'solar_farm_alpha']),
    'npc_type': random.choice(['thren', 'vorn', 'glim', 'human']),
} for i in range(12000)}
t0 = time.time()
rels = generate_relationships_bounded(npcs, 'solara')
print(f'12k NPCs: {len(rels)} relationships in {time.time()-t0:.2f}s')
"
# Expected: ~30k relationships in <2s
```

**Step 2: Commit**
```bash
git add deep_seed.py
git commit -m "perf(scaling): bounded social graph — O(n) reservoir sampling, 5 rels/NPC"
```

---

## Module S3: Tick Loop Throughput

### Goal
Three linear-scaling hotspots in `simulation.py` tick(): NPC AI (iterates ALL), NPC movement (iterates ALL), pop dynamics (LIMIT 25). Need to scale the cap and batch the full sweeps.

---

### Task S3.1: Stratified pop dynamics sampling

**Objective:** Replace `LIMIT 25` with stratified batch of 300/tick, weighted toward high-pressure NPCs.

**Files:**
- Modify: `src_template/simulation.py` — pop dynamics section

**Approach:**
```python
# POP SAMPLING — batch 300/tick stratified
# Priority tiers:
#   Tier 1 (100 slots): Glims with anomaly_pressure > 0.4 (closest to tipping)
#   Tier 2 (100 slots): NPCs with security < 0.3 (at risk of migration/death)  
#   Tier 3 (50 slots):  NPCs with satisfaction > 0.7 (reproduction candidates)
#   Tier 4 (50 slots):  Random sample (catch everything else)

pop_batch_size = 300
tier1 = db.execute("""
    SELECT a.id, a.type FROM agents a
    JOIN npc_decision_state ds ON ds.npc_id = a.id
    WHERE a.type = 'npc' AND json_extract(ds.variables, '$.anomaly_pressure') > 0.4
    LIMIT 100
""").fetchall()

tier2 = db.execute("""
    SELECT a.id, a.type FROM agents a
    JOIN npc_decision_state ds ON ds.npc_id = a.id
    WHERE a.type = 'npc' AND json_extract(ds.variables, '$.security') < 0.3
    AND a.id NOT IN (SELECT id FROM ...)
    LIMIT 100
""").fetchall()

# ... tier3, tier4

sampled = tier1 + tier2 + tier3 + tier4
# Full sweep: 12,000 / 300 = 40 ticks = ~1 sim-day
```

**Step 1: Test sampling speed**
```bash
cd /Users/johann/.hermes/agents/solara/aurelia-world && python3 -c "
from src.world_state import get_db
import time
db = get_db()
t0 = time.time()
# Simulate tiered sampling (will be slow on 120 NPCs with no decision_state yet)
count = db.execute('SELECT COUNT(*) FROM agents WHERE type=\"npc\"').fetchone()[0]
print(f'{count} NPCs, query time: {time.time()-t0:.4f}s')
"
```

**Step 2: Commit**
```bash
git add src_template/simulation.py
git commit -m "perf(scaling): stratified pop dynamics — 300/tick, 4 priority tiers"
```

---

### Task S3.2: NPC AI tick batching

**Objective:** `run_npc_ai_tick` currently queries ALL NPCs. At 12k, the 15% filter means ~1,800 AI actions per tick. Keep the filter but cap action count.

**Files:**
- Modify: `src_template/npc_ai.py`

**Approach:**
```python
def run_npc_ai_tick(db, hour: int, world_id: str = "solara", max_actions: int = 200) -> list:
    # ... existing logic ...
    npcs = db.execute("SELECT * FROM agents WHERE type = 'npc' AND state = 'active'").fetchall()
    
    for npc in npcs:
        if len(actions) >= max_actions:
            break
        if random.random() > 0.15:
            continue
        # ... existing action generation ...
```

At 12k: 15% × 12,000 = 1,800 candidates, but capped at 200 actions/tick. The feeder still nudges decision_state for the 200 that act. The remaining 11,800 still get scheduled movement via `update_npc_positions`.

**Step 3: Commit**
```bash
git add src_template/npc_ai.py
git commit -m "perf(scaling): NPC AI capped at 200 actions/tick"
```

---

### Task S3.3: NPC movement pagination

**Objective:** `update_npc_positions` loops ALL NPCs every tick. Add hourly cap.

**Files:**
- Modify: `src_template/simulation.py` — `update_npc_positions()`

**Approach:**
The current function iterates ALL NPCs. Add a `LIMIT` clause and round-robin across ticks:

```python
def update_npc_positions(db, hour, max_npcs=500):
    # Round-robin: use tick_number % offset to cover different NPCs
    offset = (db.execute("SELECT COALESCE(MAX(tick_number), 0) FROM tick_log").fetchone()[0]) * max_npcs
    npcs = db.execute(f"""
        SELECT * FROM agents WHERE type = 'npc' AND state = 'active'
        ORDER BY id LIMIT {max_npcs} OFFSET {offset}
    """).fetchall()
    # Full sweep: 12,000 / 500 = 24 ticks = ~12 sim-hours
```

**Step 3: Commit**
```bash
git add src_template/simulation.py
git commit -m "perf(scaling): NPC movement paginated — 500/tick round-robin"
```

---

## Module S4: Decision State Initialization

### Goal
New NPCs start with decision_state already populated. Don't wait for first tick.

### Why
At 12k NPCs, `ensure_decision_state` called lazily per NPC causes 12k first-tick DB writes. Front-load it.

---

### Task S4.1: Seed decision_state during NPC generation

**Objective:** `deep_seed.py` or `populate_npcs.py` writes initial decision_state for every NPC.

**Files:**
- Modify: `deep_seed.py`

**Approach:**
After NPC insertion, batch-insert decision_state rows:

```python
# After all NPCs inserted:
now = time.time()
for nid, info in npc_data.items():
    base = GLIM_BASE if info["npc_type"] == "glim" else BASE_STATE
    # Add per-country modifier
    if info["npc_type"] == "glim":
        modifier = GLIM_PRESSURE_MODIFIERS.get(country_id, 1.0)
        base["anomaly_pressure"] = 0.001 * modifier  # tiny seed
    db.execute(
        "INSERT OR IGNORE INTO npc_decision_state (npc_id, variables, last_updated) VALUES (?, ?, ?)",
        (nid, json.dumps(base), now)
    )
```

**Step 2: Commit**
```bash
git add deep_seed.py
git commit -m "feat(scaling): seed decision_state during NPC generation"
```

---

## Module S5: DB Growth Management

### Goal
At 12k NPCs, each world produces ~1,800 AI actions/tick × capped at 200 = faster growth. `npc_actions` table will balloon. Need retention policy.

---

### Task S5.1: NPC actions retention cap

**Objective:** Keep last 100 actions per NPC, delete older.

**Files:**
- Modify: `src_template/npc_ai.py` — `_insert_npc_action()`

**Approach:**
After inserting, delete excess:

```python
db.execute("""
    DELETE FROM npc_actions WHERE id IN (
        SELECT id FROM npc_actions WHERE npc_id = ?
        ORDER BY timestamp ASC
        LIMIT max(0, (SELECT COUNT(*) - 100 FROM npc_actions WHERE npc_id = ?))
    )
""", (npc_id, npc_id))
```

**Step 2: Commit**
```bash
git add src_template/npc_ai.py
git commit -m "perf(scaling): retain last 100 actions per NPC"
```

---

## Module S6: Growth Snapshot Scaling

### Goal
`/api/growth` queries all 5 world DBs for NPC stats. At 12k NPCs per world, these queries need to be fast.

---

### Task S6.1: Coordinator NPC stats caching

**Objective:** The coordinator already has `get_npc_stats_cached()` with 60s TTL. Verify it handles 12k.

**Files:**
- Modify: `aurelia_coordinator.py` — `_load_world_npc_stats()`

**Approach:**
The current implementation queries `SELECT COUNT(*) FROM agents WHERE type='npc'` and loops properties. At 12k, looping 12k rows per world × 5 worlds = 60k rows per query. That's fine at 60s cache TTL. Add `LIMIT` to property loop if needed:

```python
rows = db.execute("SELECT properties FROM agents WHERE type='npc' LIMIT 5000").fetchall()
```

At 5k sample for 12k population = 41% sample, good enough for distribution estimates. The exact `total` is still from `COUNT(*)`.

**Step 1: Verify at current scale**
```bash
curl -s http://127.0.0.1:9001/api/growth | python3 -c "import json,sys; d=json.load(sys.stdin); print('populations populated:', all(p.get('total',0)>0 for p in d['populations'].values()))"
```

**Step 2: Commit**
```bash
git add aurelia_coordinator.py
git commit -m "perf(scaling): NPC stats sampling capped at 5k rows per world"
```

---

## Module S7: Population Script — 60K Generation

### Goal
The actual generator script that produces 12,000 NPCs per world.

---

### Task S7.1: Scale configuration

**Objective:** `populate_npcs.py` parameter `NPC_COUNT = 120` → `NPC_COUNT = 12000`.

**Files:**
- Modify: `populate_npcs.py`

**Step 1: Change the constant**
```python
NPC_COUNT = 12000  # was 120
```

**Step 2: Add progress output**
Scale operations need visibility. Add progress prints every 1,000 NPCs:

```python
if i % 1000 == 0:
    print(f"  ... {i}/{NPC_COUNT} NPCs created")
```

**Step 3: Test generation (dry run — 500 NPCs)**
```bash
cd /Users/johann/aurelia
python3 -c "
NPC_COUNT = 500  # test
import populate_npcs
# verify no errors
print('500 NPC generation: OK')
"
```

**Step 4: Full generation**
```bash
cd /Users/johann/aurelia
python3 populate_npcs.py --all  # generates 60k across 5 worlds
python3 deep_seed.py --all      # schedules + relationships + memories
```

**Step 5: Commit**
```bash
git add populate_npcs.py
git commit -m "feat(scaling): NPC_COUNT → 12,000 per world, progress output"
```

---

## Scaling Summary

| Module | Change | Complexity | Risk |
|---|---|---|---|
| S1: Name pools | Combinatorial syllable splicing | Low | None |
| S1: Parametric gen | Weighted distribution × occupation matrix | Low | Validate type ratios |
| S2: Relationships | Bounded reservoir sampling O(n) | Medium | **Must test 12k pairs** |
| S3.1: Pop sampling | 300/tick stratified 4-tier | Medium | Verify coverage rate |
| S3.2: AI batching | 200 actions/tick cap | Low | Already stochastic |
| S3.3: Movement pagination | 500/tick round-robin | Low | Full sweep in 12 sim-hours |
| S4: Decision state seed | Batch init during gen | Low | Prevent 12k first-tick writes |
| S5: Action retention | 100 actions/NPC cap | Low | Just a DELETE |
| S6: Stats sampling | 5k row cap in coordinator | Low | 41% sample still accurate |
| S7: Generation | 12k NPCs per world | Medium | **Test with 500 first, then full** |

**Total: 11 tasks, 6 files modified, 0 new files.** No change to growth mechanics — only throughput.

---

## Verification Milestones

### Milestone 1: 500 NPC test generation (per world)
```bash
cd /Users/johann/aurelia
for world in solara valdris mirithane arkos verge; do
    echo "$world: $(sqlite3 ~/.hermes/agents/$world/aurelia-world/world/world.db 'SELECT COUNT(*) FROM agents WHERE type="npc"')"
done
```
Expected: All return the test count (500 or 12,000 after full run).

### Milestone 2: Relationship generation at scale
```bash
python3 -c "
import time, random
# Mock 12k
npcs = {f'npc_{i:05d}': {'occupation': random.choice(['a','b','c','d']), 'location_id': random.choice(['x','y','z']), 'npc_type': random.choice(['thren','vorn','glim','human'])} for i in range(12000)}
t0=time.time()
# Run bounded generation
rels = generate_relationships_bounded(npcs, 'solara')
print(f'{len(rels)} relationships in {time.time()-t0:.2f}s (target ~30k)')
"
```
Expected: ~30k relationships in <2s.

### Milestone 3: Tick duration at 12k
```bash
# After deploying all modules, observe daemon log
grep "duration" daemon.log | tail -5
```
Expected: <5s per tick (well within 30-min interval).

### Milestone 4: Growth observability still works
```bash
curl -s http://127.0.0.1:9001/api/growth | python3 -c "
import json,sys; d=json.load(sys.stdin)
for w,p in sorted(d['populations'].items()):
    print(f'{w}: {p[\"total\"]}')
"
```
Expected: All 5 worlds show ~12,000.

### Milestone 5: Full sweep coverage
- Pop dynamics: 300/tick → full sweep in 40 ticks (~1 sim-day)
- NPC movement: 500/tick → full sweep in 24 ticks (~12 sim-hours)
- NPC AI: 200/tick → 15% of 12k = 1,800 candidates, 200 actions = ~11% of candidates act
