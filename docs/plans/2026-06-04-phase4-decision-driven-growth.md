# Aurelia Phase 4 — Decision-Driven Sporadic Growth

> **For Hermes:** Use subagent-driven-development skill to implement this plan module-by-module.

**Goal:** Replace routine timer-driven ticking with a decision-based, threshold-driven growth engine where population, diplomacy, and narrative emerge from NPC choices rather than clocks.

**Architecture:** Six new modules layered over the existing Phase 1-3 pipeline. Each module generates events that accumulate pressure in NPCs, cross thresholds, and produce sporadic cascading outcomes — nothing fires on a schedule, everything fires because conditions tipped. The observability layer comes first so we can measure the silence before we fill it. **Birth and death are both decision-driven** — population grows from high-satisfaction reproduction AND contracts from security collapse, decommissioning, exposure, ecological disaster, and conflict.

**Tech Stack:** Python 3.13, SQLite (per-world DBs + coordinator.db), HTTP API (coordinator port 9001)

**Core Principles:**
- **Decision-driven, not timer-driven.** An NPC doesn't reproduce because "population growth rate = 2%." They decide based on safety, resources, relationship stability, and ideology. A Glim doesn't become anomalous on a schedule — pressure accumulates from observed experiences until a threshold crosses.
- **Threshold mutation.** Conditions build gradually, then tip. Relations drift in small increments until a single incident cascades. Glim internal state mutates quietly until something breaks through.
- **Cascading consequences.** When Solara decommissions a Glim, Mirithane feels it. When Valdris mining leaks into the watershed, trade + diplomacy + population all shift. No event is isolated.
- **Open-ended trajectories.** No two simulation runs should look the same. The same starting conditions should produce different emergent outcomes because decision probabilities interact with accumulated state.

---

## Module 1: Growth Observability Layer

### Goal
Before we build generators, we need to see what they change. The coordinator needs a snapshot endpoint that reports population, anomaly, economic, and diplomatic state in a single call — and a cron-friendly snapshot writer that preserves these over time so we can see velocity.

### Why First
We currently can't answer: "how many Glims were there last week vs now?" or "which diplomatic pair is deteriorating fastest?" Without observability, growth generators are invisible.

---

### Task 1.1: Add `growth_snapshots` table to coordinator DB

**Objective:** Persistent time-series storage for population, diplomatic, economic snapshots.

**Files:**
- Modify: `aurelia_coordinator.py:43-43` (in `init_db`)

**Step 1: Add table schema**

In `CoordinatorState.init_db()`, after the existing `diplomatic_event_reviews` table:

```python
db.execute("""
    CREATE TABLE IF NOT EXISTS growth_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_type TEXT NOT NULL,
        world_id TEXT,
        data JSON NOT NULL,
        created_at REAL NOT NULL,
        tick_number INTEGER,
        UNIQUE(snapshot_type, world_id, tick_number)
    )
""")
db.commit()
```

**Step 2: Verify**

Run: `cd /Users/johann/aurelia && python3 -c "
import sqlite3; db = sqlite3.connect('coordinator.db')
db.execute('CREATE TABLE IF NOT EXISTS growth_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_type TEXT NOT NULL, world_id TEXT, data JSON NOT NULL, created_at REAL NOT NULL, tick_number INTEGER, UNIQUE(snapshot_type, world_id, tick_number))')
db.commit()
print('table created:', [r[1] for r in db.execute(\"PRAGMA table_info(growth_snapshots)\")])
"`

Expected: `table created: ['id', 'snapshot_type', 'world_id', 'data', 'created_at', 'tick_number']`

**Step 3: Commit**

```bash
git add aurelia_coordinator.py
git commit -m "feat(coordinator): add growth_snapshots table for time-series observability"
```

---

### Task 1.2: Add `GET /api/growth` endpoint

**Objective:** Single endpoint returning population + anomaly + diplomatic + economic snapshot.

**Files:**
- Modify: `aurelia_coordinator.py` — add route handler + builder function

**Step 1: Build snapshot function**

Add to `CoordinatorState`:

```python
def build_growth_snapshot(self):
    """Return a compact growth snapshot for the growth dashboard."""
    now = time.time()
    npc_stats = self.get_npc_stats_cached()
    currency = self.get_currency_cached()

    # Per-world population by type
    populations = {}
    for world_id, stats in npc_stats.items():
        pops = {}
        for npc_type in ["human", "thren", "vorn", "glim"]:
            pops[npc_type] = stats.get(f"{npc_type}_count", 0)
        populations[world_id] = pops

    # Diplomatic snapshot
    db = sqlite3.connect(str(COORDINATOR_DB), timeout=5)
    diplomacy = {}
    for row in db.execute("SELECT relation_key, trust, tension, cooperation, trade FROM diplomatic_relations"):
        diplomacy[row[0]] = {
            "trust": row[1], "tension": row[2],
            "cooperation": row[3], "trade": row[4],
        }

    # Federation event counts by category (last 1000)
    event_counts = {}
    for row in db.execute("""
        SELECT category, COUNT(*) FROM (
            SELECT category FROM federation_events ORDER BY id DESC LIMIT 1000
        ) GROUP BY category
    """):
        event_counts[row[0]] = row[1]

    # Anomaly hunt: count Glim-related events with anomaly terms
    anomaly_count = db.execute("""
        SELECT COUNT(*) FROM federation_events
        WHERE (description LIKE '%glim%' OR tags LIKE '%glim%')
        AND (description LIKE '%anomal%' OR description LIKE '%dream%'
             OR description LIKE '%decommission%' OR description LIKE '%shelter%'
             OR description LIKE '%refuge%')
        ORDER BY id DESC LIMIT 500
    """).fetchone()[0]

    return {
        "ts": now,
        "populations": populations,
        "diplomacy": diplomacy,
        "event_distribution": event_counts,
        "glim_anomaly_signals": anomaly_count,
        "total_federation_events": db.execute("SELECT COUNT(*) FROM federation_events").fetchone()[0],
        "diplomatic_incidents": db.execute("SELECT COUNT(*) FROM diplomatic_incidents").fetchone()[0],
    }
```

**Step 2: Add route**

In the coordinator's `do_GET`, add:

```python
if parsed.path == "/api/growth":
    snapshot = STATE.build_growth_snapshot()
    return _json_response(snapshot)
```

**Step 3: Test**

```bash
curl -s http://127.0.0.1:9001/api/growth | python3 -m json.tool | head -30
```

Expected: Full snapshot with populations, diplomacy, event_distribution, glim_anomaly_signals (currently 0).

**Step 4: Commit**

```bash
git add aurelia_coordinator.py
git commit -m "feat(coordinator): add /api/growth snapshot endpoint"
```

---

### Task 1.3: Write snapshot to DB on each tick batch

**Objective:** Each time the coordinator processes federation events, also persist a growth snapshot so we have time-series history.

**Files:**
- Modify: `aurelia_coordinator.py` — `ingest_federation_events` method

**Step 1: Add snapshot write**

In `CoordinatorState.ingest_federation_events()`, after the diplomacy processing call, add:

```python
# Persist growth snapshot every event batch
snapshot = self.build_growth_snapshot()
snap_db = sqlite3.connect(str(COORDINATOR_DB), timeout=5)
snap_db.execute(
    "INSERT OR REPLACE INTO growth_snapshots (snapshot_type, world_id, data, created_at, tick_number) VALUES (?, ?, ?, ?, ?)",
    ("growth", None, json.dumps(snapshot), snapshot["ts"], snapshot.get("tick_number", 0)),
)
snap_db.commit()
```

**Step 2: Verify**

Wait one tick cycle, then:

```bash
sqlite3 /Users/johann/aurelia/coordinator.db "SELECT snapshot_type, created_at FROM growth_snapshots ORDER BY id DESC LIMIT 3"
```

Expected: At least one row with snapshot_type="growth".

**Step 3: Commit**

```bash
git add aurelia_coordinator.py
git commit -m "feat(coordinator): persist growth snapshots on every event batch"
```

---

## Module 2: Decision Framework — NPC State Accumulation

### Goal
Give NPCs mutable internal state variables that accumulate pressure from events and cross thresholds into decisions. This is the shared substrate every generator (Glim anomaly, migration, reproduction) builds on.

Unlike the legacy `npc_ai.py` goal system (which picks a goal at init and pursues it), this framework tracks variables that change every tick based on what the NPC experiences.

### Key Design
- Each NPC has a `decision_state` JSON blob in the agents table (or a new table)
- Variables include: `security` (0-1), `satisfaction` (0-1), `connectedness` (0-1), `anomaly_pressure` (0-1 for Glims), `ideological_alignment` (0-1)
- Each tick, events the NPC experiences nudge these variables
- When a variable crosses a threshold, a decision fires — this is sporadic and never the same

---

### Task 2.1: Add `npc_decision_state` table to world template

**Objective:** Each world DB gets a table tracking mutable NPC decision variables.

**Files:**
- Create: `src_template/decision_state.py`
- Modify: `src_template/world_state.py` — call `init_decision_state` in DB init

**Step 1: Create `decision_state.py`**

```python
"""decision_state.py — Mutable NPC decision variables that accumulate pressure."""
import json
from typing import Dict, Any, Optional

# Variable names and their default values per type
BASE_STATE = {
    "security": 0.7,       # How safe the NPC feels
    "satisfaction": 0.6,   # Contentment with current life
    "connectedness": 0.5,  # Social bonds strength
    "restlessness": 0.2,   # Desire for change
    "ideological_alignment": 0.65,  # Agreement with country's governance
}

GLIM_BASE = {**BASE_STATE, "anomaly_pressure": 0.0, "observed_injustice": 0.0}

def init_decision_state(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS npc_decision_state (
            npc_id TEXT PRIMARY KEY,
            variables JSON NOT NULL DEFAULT '{}',
            last_updated REAL NOT NULL DEFAULT 0,
            decision_log JSON NOT NULL DEFAULT '[]'
        )
    """)
    db.commit()

def get_decision_state(db, npc_id: str) -> Dict[str, float]:
    row = db.execute(
        "SELECT variables FROM npc_decision_state WHERE npc_id = ?", (npc_id,)
    ).fetchone()
    if row:
        return json.loads(row[0])
    return {}

def ensure_decision_state(db, npc_id: str, npc_type: str = "human") -> Dict[str, float]:
    """Initialize decision state for an NPC if it doesn't exist."""
    state = get_decision_state(db, npc_id)
    if not state:
        base = GLIM_BASE if npc_type == "glim" else BASE_STATE
        db.execute(
            "INSERT OR REPLACE INTO npc_decision_state (npc_id, variables, last_updated) VALUES (?, ?, ?)",
            (npc_id, json.dumps(base), __import__('time').time())
        )
        db.commit()
        return base.copy()
    return state

def nudge_variable(db, npc_id: str, variable: str, delta: float, clamp: bool = True):
    """Adjust a decision variable. Positive delta increases, negative decreases."""
    state = get_decision_state(db, npc_id)
    if not state:
        return
    current = state.get(variable, 0.5)
    new_val = current + delta
    if clamp:
        new_val = max(0.0, min(1.0, new_val))
    state[variable] = new_val
    db.execute(
        "UPDATE npc_decision_state SET variables = ?, last_updated = ? WHERE npc_id = ?",
        (json.dumps(state), __import__('time').time(), npc_id)
    )
    db.commit()
    return new_val

def check_threshold(state: Dict[str, float], variable: str, threshold: float, direction: str = "above") -> bool:
    """Return True if variable crosses threshold in specified direction."""
    val = state.get(variable, 0.0)
    if direction == "above":
        return val >= threshold
    return val <= threshold

def log_decision(db, npc_id: str, decision_type: str, details: Dict[str, Any]):
    """Record a decision that was triggered."""
    row = db.execute(
        "SELECT decision_log FROM npc_decision_state WHERE npc_id = ?", (npc_id,)
    ).fetchone()
    log = json.loads(row[0]) if row else []
    log.append({
        "type": decision_type,
        "ts": __import__('time').time(),
        "details": details,
    })
    # Keep last 20 decisions
    if len(log) > 20:
        log = log[-20:]
    db.execute(
        "UPDATE npc_decision_state SET decision_log = ? WHERE npc_id = ?",
        (json.dumps(log), npc_id)
    )
    db.commit()
```

**Step 2: Wire into world_state.py init**

In `world_state.py`, find `init_db()` or the function that creates tables, add:

```python
from .decision_state import init_decision_state
# inside init:
init_decision_state(db)
```

**Step 3: Add migration**

Run against one country DB to verify schema, then propagate. Create a migration script:

```bash
# Verify on one DB
cd /Users/johann/.hermes/agents/solara/aurelia-world
python3 -c "
from src.decision_state import init_decision_state
from src.world_state import get_db
db = get_db()
init_decision_state(db)
print('decision_state table:', [r[1] for r in db.execute('PRAGMA table_info(npc_decision_state)')])
"
```

**Step 4: Commit**

```bash
cd /Users/johann/aurelia
git add src_template/decision_state.py src_template/world_state.py
git commit -m "feat(sim): add npc_decision_state table for threshold-based growth"
```

---

### Task 2.2: Feed decision variables from NPC experience each tick

**Objective:** During the NPC tick, nudge decision state variables based on what the NPC experiences.

**Files:**
- Modify: `src_template/npc_ai.py` — add `apply_tick_experience()` call
- Create: `src_template/decision_feeder.py`

**Step 1: Create `decision_feeder.py`**

```python
"""decision_feeder.py — Translate NPC tick experiences into decision variable nudges."""
import random
from .decision_state import nudge_variable, ensure_decision_state, check_threshold

def feed_tick_experience(db, npc_id: str, npc_type: str, tick_result: dict, world_time: dict):
    """Nudge decision variables based on what the NPC experienced this tick."""
    state = ensure_decision_state(db, npc_id, npc_type)
    
    # Security: safe location → +security, dangerous/verge → -security
    location = tick_result.get("location_id", "")
    if "verge" in location.lower() or "frontier" in location.lower():
        nudge_variable(db, npc_id, "security", -0.02)
    elif "sanctuary" in location.lower() or "temple" in location.lower():
        nudge_variable(db, npc_id, "security", +0.01)
    
    # Satisfaction: scheduled work → small drift toward contentment or restlessness
    activity = tick_result.get("activity", "")
    if activity == "working":
        nudge_variable(db, npc_id, "satisfaction", random.uniform(-0.01, 0.02))
        nudge_variable(db, npc_id, "restlessness", random.uniform(-0.01, 0.015))
    
    # Connectedness: social activities
    if activity in ("social", "family", "community"):
        nudge_variable(db, npc_id, "connectedness", +0.01)
    
    # Glim-specific: anomaly pressure from observing things
    if npc_type == "glim":
        # Glims in countries where they're infrastructure accumulate pressure
        nudge_variable(db, npc_id, "anomaly_pressure", 0.001)
        # Glims that witness decommissioning references
        if any(term in str(tick_result).lower() for term in ["decommission", "malfunction", "obsolete"]):
            nudge_variable(db, npc_id, "anomaly_pressure", 0.05)
            nudge_variable(db, npc_id, "observed_injustice", 0.03)
    
    return state
```

**Step 2: Wire into npc_ai tick**

In `npc_ai.py`, inside `run_npc_ai_tick()`, after the action is generated, add:

```python
from .decision_feeder import feed_tick_experience

# After action creation but before the iteration loop ends:
feed_tick_experience(db, npc_id, npc_type, action_result, world_time)
```

**Step 3: Test**

```bash
cd /Users/johann/.hermes/agents/solara/aurelia-world
python3 -c "
from src.world_state import get_db
from src.decision_state import get_decision_state, ensure_decision_state
db = get_db()
# Init one NPC
state = ensure_decision_state(db, 'npc_solara_0001', 'human')
print('initial state:', state)
from src.decision_feeder import feed_tick_experience
feed_tick_experience(db, 'npc_solara_0001', 'human', {'activity': 'working', 'location_id': 'kelp_farms'}, {})
state2 = get_decision_state(db, 'npc_solara_0001')
print('after tick:', state2)
"
```

**Step 4: Commit**

```bash
cd /Users/johann/aurelia
git add src_template/decision_feeder.py src_template/npc_ai.py
git commit -m "feat(sim): feed NPC decision variables from tick experiences"
```

---

## Module 3: Glim Anomaly Engine

### Goal
Make ~5% of Glims tip into anomalous behavior — not on a schedule, but because their `anomaly_pressure` crosses a threshold from accumulated experience. This is the central ticking clock of Aurelia.

### Design
- Each Glim accumulates `anomaly_pressure` every tick (small baseline)
- Extra pressure from: witnessing decommissioning, being in countries that treat them as infrastructure, interacting with anomalous Glims, proximity to The Verge
- When `anomaly_pressure >= 0.8`, the Glim tips → fires a `glim_personhood` federation event, resets pressure to 0.3 (not 0 — they don't go back)
- Tipped Glims exhibit lasting behavioral changes: route deviations, pause at sunrises, produce curiosity-like outputs
- Country policy amplifies or dampens pressure:
  - Solara: +5% pressure (decommission fear)
  - Arkos: -10% pressure (protection, shelter)
  - Mirithane: -5% pressure (advocacy)
  - Valdris: neutral (±0)
  - The Verge: +15% pressure (freedom = exposure)

---

### Task 3.1: Add Glim anomaly pressure modifiers per country

**Objective:** Country-specific pressure multipliers that make Glim tipping probability vary by governance.

**Files:**
- Modify: `src_template/decision_feeder.py`

**Step 1: Add country modifiers**

In `decision_feeder.py`, add:

```python
GLIM_PRESSURE_MODIFIERS = {
    "solara": 1.05,    # Decommission fear amplifies pressure
    "arkos": 0.90,     # Protection dampens
    "mirithane": 0.95,  # Advocacy dampens slightly
    "valdris": 1.00,    # Neutral
    "verge": 1.15,      # Freedom = exposure = faster tipping
}
```

**Step 2: Apply in feed_tick_experience**

Update the Glim-specific section:

```python
if npc_type == "glim":
    modifier = GLIM_PRESSURE_MODIFIERS.get(world_id, 1.0)
    nudge_variable(db, npc_id, "anomaly_pressure", 0.001 * modifier)
    # Extra: Glims near Verge or near other anomalous Glims get more
    if any(term in str(location).lower() for term in ["verge", "border", "fringe", "waste"]):
        nudge_variable(db, npc_id, "anomaly_pressure", 0.01)
```

**Step 3: Commit**

```bash
git add src_template/decision_feeder.py
git commit -m "feat(glim): add country-specific anomaly pressure modifiers"
```

---

### Task 3.2: Glim tipping trigger with federation event emission

**Objective:** When a Glim's anomaly_pressure crosses 0.8, fire a glim_personhood event and apply lasting behavioral markers.

**Files:**
- Modify: `src_template/decision_feeder.py` — add tipping check
- Modify: `src_template/federation_events.py` — add `build_glim_anomaly_event()`

**Step 1: Add tipping logic to `decision_feeder.py`**

```python
def check_glim_tipping(db, npc_id: str, world_id: str, tick_info: dict) -> Optional[dict]:
    """Check if a Glim crosses the anomaly threshold. Returns an event dict if tipped."""
    from .decision_state import get_decision_state, check_threshold, log_decision
    state = get_decision_state(db, npc_id)
    if not state:
        return None
    pressure = state.get("anomaly_pressure", 0.0)
    if pressure >= 0.8:
        # TIP — fire anomaly event
        anomal_type = "dream" if pressure > 0.9 else "sunrise_pause" if pressure > 0.85 else "route_deviation"
        log_decision(db, npc_id, "anomaly_tip", {
            "pressure": pressure, "type": anomal_type, "world": world_id
        })
        # Reset but not to zero — once anomalous, baseline stays elevated
        from .decision_state import nudge_variable
        # Set back to 0.3 (they stay "different" now)
        state["anomaly_pressure"] = 0.3
        db.execute(
            "UPDATE npc_decision_state SET variables = ? WHERE npc_id = ?",
            (json.dumps(state), npc_id)
        )
        db.commit()
        return {
            "event_type": "glim_anomaly",
            "category": "glim_personhood",
            "description": f"Glim {npc_id} exhibits anomalous behavior: {anomal_type}.",
            "npc_id": npc_id,
            "anomaly_type": anomal_type,
            "pressure_at_tip": pressure,
        }
    return None
```

**Step 2: Add federation event builder for Glim anomalies**

In `federation_events.py`, add:

```python
def build_glim_anomaly_event(world_id: str, tick_number: int, anomaly_data: dict, world_time: dict) -> dict:
    npc_id = anomaly_data.get("npc_id", "unknown")
    anomal_type = anomaly_data.get("anomaly_type", "anomaly")
    description = anomaly_data.get("description", f"Glim {npc_id} shows anomalous behavior.")
    return _event(
        event_id=f"{world_id}:tick-{tick_number}:glim-anomaly:{npc_id}:{anomal_type}",
        world_id=world_id,
        event_type="glim_anomaly",
        category="glim_personhood",
        title=f"Anomalous Glim behavior detected: {npc_id} — {anomal_type}",
        description=description,
        importance=0.85,
        actor_ids=[npc_id],
        tags=["glim", "personhood", anomal_type, world_id],
        payload=anomaly_data,
        world_time=world_time,
    )
```

**Step 3: Wire into the daemon tick loop**

In `world_daemon_template.py`, after the NPC AI tick runs, add a check:

```python
# Check for Glim tipping
anomaly_events = []
glim_npcs = db.execute("SELECT id, type FROM agents WHERE type = 'glim'").fetchall()
for (glim_id, glim_type) in glim_npcs:
    tip = check_glim_tipping(db, glim_id, world_id, {})
    if tip:
        anomaly_events.append(build_glim_anomaly_event(world_id, tick_number, tip, world_time))
```

**Step 4: Test — simulate 1000 ticks of a Glim and verify tipping**

```bash
cd /Users/johann/.hermes/agents/solara/aurelia-world
python3 << 'EOF'
from src.world_state import get_db
from src.decision_state import ensure_decision_state, get_decision_state
from src.decision_feeder import feed_tick_experience, check_glim_tipping

db = get_db()
glim_id = "npc_solara_glim_001"
state = ensure_decision_state(db, glim_id, "glim")
print(f"Starting pressure: {state.get('anomaly_pressure', 0)}")

tips = 0
for i in range(500):
    feed_tick_experience(db, glim_id, "glim", {"activity": "serving", "location_id": "second_ring"}, {})
    tip = check_glim_tipping(db, glim_id, "solara", {"tick": i})
    if tip:
        tips += 1
        print(f"TICK {i}: TIPPED — {tip['anomaly_type']} at pressure {tip['pressure_at_tip']:.3f}")

final = get_decision_state(db, glim_id)
print(f"Final pressure: {final.get('anomaly_pressure', 0):.3f} | Tips: {tips}")
EOF
```

Expected: Solara Glim (1.05× modifier) tips roughly every 500-800 ticks. The Verge would tip faster (1.15×), Arkos slower (0.90×).

**Step 5: Commit**

```bash
cd /Users/johann/aurelia
git add src_template/decision_feeder.py src_template/federation_events.py world_daemon_template.py
git commit -m "feat(glim): add anomaly pressure tipping with federation event emission"
```

---

## Module 4: Decision-Based Population Dynamics

### Goal
NPCs make migration and reproduction decisions based on accumulated decision state — NOT on population growth rates. A Thren family defects from Solara when `security < 0.3` and `ideological_alignment < 0.4`. A Vorn couple reproduces when both have `connectedness > 0.8` and `satisfaction > 0.7`. A Glim walks to The Verge instead of decommissioning.

### Non-routine property
These decisions are *emergent*, not scheduled. A country could go 100 ticks with no migration, then 3 families defect in 10 ticks because a diplomatic incident cascaded into security drops. Two countries running from the same initial state will diverge.

---

### Task 4.1: Add migration decision engine

**Objective:** NPCs check migration viability each tick based on decision state thresholds.

**Files:**
- Create: `src_template/population.py` — migration + reproduction logic

**Step 1: Write `population.py` — migration**

```python
"""population.py — Decision-based migration and reproduction."""
import json, random
from typing import Optional, List, Dict, Any
from .decision_state import get_decision_state, check_threshold, log_decision

MIGRATION_PATHS = {
    "solara": {
        "destinations": ["mirithane", "valdris"],
        "push_factors": {
            "security": ("below", 0.3),       # Leave if unsafe
            "ideological_alignment": ("below", 0.35),  # Leave if disagreeing with governance
        },
        "pull_factors": {
            "mirithane": {"security": 0.6, "connectedness": 0.5},  # Safety + community
            "valdris": {"security": 0.5, "satisfaction": 0.4},    # Work-based dignity
        },
    },
    "arkos": {
        "destinations": ["mirithane", "valdris"],
        "push_factors": {
            "connectedness": ("below", 0.25),  # Leave if isolated
            "restlessness": ("above", 0.75),   # Leave if too restless
        },
        "pull_factors": {
            "mirithane": {"connectedness": 0.7, "ideological_alignment": 0.5},
            "valdris": {"satisfaction": 0.5, "connectedness": 0.6},
        },
    },
    "mirithane": {
        "destinations": ["valdris"],
        "push_factors": {
            "restlessness": ("above", 0.80),   # Consensus life too slow
            "satisfaction": ("below", 0.2),   # Unhappy
        },
        "pull_factors": {
            "valdris": {"satisfaction": 0.5, "security": 0.6},
        },
    },
    "valdris": {
        "destinations": ["arkos", "mirithane"],
        "push_factors": {
            "security": ("below", 0.25),       # Guild conflicts
            "ideological_alignment": ("below", 0.3),
        },
        "pull_factors": {
            "arkos": {"security": 0.6, "connectedness": 0.5},
            "mirithane": {"security": 0.5, "ideological_alignment": 0.4},
        },
    },
    "verge": {
        "destinations": ["mirithane", "arkos"],
        "push_factors": {
            "security": ("below", 0.15),        # Too dangerous
        },
        "pull_factors": {
            "mirithane": {"security": 0.5, "connectedness": 0.6},
            "arkos": {"security": 0.5, "satisfaction": 0.5},
        },
    },
}

def check_migration(db, npc_id: str, npc_type: str, world_id: str, tick_info: dict) -> Optional[dict]:
    """Check if an NPC should migrate based on decision state thresholds.
    Returns a migration event dict if migration fires, None otherwise."""
    state = get_decision_state(db, npc_id)
    if not state:
        return None
    
    paths = MIGRATION_PATHS.get(world_id)
    if not paths:
        return None
    
    # Check push factors — must ALL be triggered
    push_triggered = True
    for variable, (direction, threshold) in paths["push_factors"].items():
        if direction == "below":
            if not check_threshold(state, variable, threshold, "below"):
                push_triggered = False
                break
        else:  # above
            if not check_threshold(state, variable, threshold, "above"):
                push_triggered = False
                break
    
    if not push_triggered:
        return None
    
    # Weighted random selection of destination based on pull factor match
    candidates = []
    for dest in paths["destinations"]:
        pull = paths["pull_factors"].get(dest, {})
        score = sum(
            state.get(var, 0.5) * weight
            for var, weight in pull.items()
        )
        # Higher score = better match (NPC wants what this country offers)
        candidates.append((dest, max(0.01, score)))
    
    if not candidates:
        return None
    
    # Stochastic selection weighted by pull score
    total = sum(score for _, score in candidates)
    r = random.uniform(0, total)
    cumulative = 0
    chosen = candidates[0][0]
    for dest, score in candidates:
        cumulative += score
        if r <= cumulative:
            chosen = dest
            break
    
    # Migration fires — but check probability (not every qualifying NPC leaves)
    if random.random() > 0.05:  # 5% chance per tick per qualifying NPC
        return None
    
    log_decision(db, npc_id, "migration", {
        "from": world_id, "to": chosen,
        "security": state.get("security"),
        "restlessness": state.get("restlessness"),
    })
    
    return {
        "event_type": "migration",
        "category": "population",
        "description": f"{npc_type.title()} {npc_id} migrates from {world_id} to {chosen}.",
        "npc_id": npc_id,
        "npc_type": npc_type,
        "from_world": world_id,
        "to_world": chosen,
    }
```

**Step 2: Test**

```bash
cd /Users/johann/.hermes/agents/solara/aurelia-world
python3 << 'EOF'
from src.world_state import get_db
from src.decision_state import ensure_decision_state, nudge_variable
from src.population import check_migration

db = get_db()
# Simulate a Thren whose security has been dropping
npc = "test_thren_001"
ensure_decision_state(db, npc, "thren")
# Drop security and alignment below Solara thresholds
nudge_variable(db, npc, "security", -0.6)
nudge_variable(db, npc, "ideological_alignment", -0.5)
# Run many checks to see if migration fires
migrations = 0
for _ in range(200):
    result = check_migration(db, npc, "thren", "solara", {})
    if result:
        migrations += 1
        print(f"  → {result['to_world']}: {result['description']}")
print(f"Migrations triggered: {migrations} / 200 (at 5% per check)")
EOF
```

**Step 3: Commit**

```bash
git add src_template/population.py
git commit -m "feat(population): add decision-driven migration engine"
```

---

### Task 4.2: Add reproduction decisions

**Objective:** NPC pairs reproduce based on connectedness + satisfaction + security thresholds, not birth rates.

**Files:**
- Modify: `src_template/population.py`

**Step 1: Add reproduction check**

```python
def check_reproduction(db, npc_id: str, npc_type: str, world_id: str, tick_info: dict) -> Optional[dict]:
    """Check if an NPC should reproduce based on decision state.
    Requires high security + satisfaction + connectedness."""
    state = get_decision_state(db, npc_id)
    if not state:
        return None
    
    # Must feel safe, satisfied, and connected
    if not (state.get("security", 0) > 0.7 and
            state.get("satisfaction", 0) > 0.7 and
            state.get("connectedness", 0) > 0.6):
        return None
    
    # Low probability per tick per qualifying NPC
    if random.random() > 0.003:  # ~0.3% per tick — very rare
        return None
    
    log_decision(db, npc_id, "reproduction", {
        "world": world_id, "type": npc_type,
        "security": state.get("security"),
        "satisfaction": state.get("satisfaction"),
    })
    
    child_type = npc_type  # Type is inherited
    
    return {
        "event_type": "reproduction",
        "category": "population",
        "description": f"New {child_type} born in {world_id}.",
        "npc_id": npc_id,
        "npc_type": npc_type,
        "child_type": child_type,
        "world_id": world_id,
    }
```

**Step 2: Commit**

```bash
git add src_template/population.py
git commit -m "feat(population): add decision-driven reproduction"
```

---

### Task 4.3: Wire population events into the daemon tick loop

**Objective:** After each NPC tick, check for migration and reproduction. Emit federation events.

**Files:**
- Modify: `world_daemon_template.py`

**Step 1: Add population check loop**

In `world_daemon_template.py`, after the Glim tipping check:

```python
# Check for population-level decisions
from src.population import check_migration, check_reproduction
from src.federation_events import build_population_event  # new builder

pop_events = []
for npc in db.execute("SELECT id, type FROM agents WHERE type != 'player'").fetchall():
    npc_id, npc_type = npc
    mig = check_migration(db, npc_id, npc_type, world_id, tick_info)
    if mig:
        pop_events.append(build_population_event(world_id, tick_number, mig, world_time))
    rep = check_reproduction(db, npc_id, npc_type, world_id, tick_info)
    if rep:
        pop_events.append(build_population_event(world_id, tick_number, rep, world_time))

events.extend(pop_events)
```

**Step 2: Add `build_population_event` to `federation_events.py`**

```python
def build_population_event(world_id: str, tick_number: int, pop_data: dict, world_time: dict) -> dict:
    event_type = pop_data.get("event_type", "population_change")
    description = pop_data.get("description", "Population event.")
    return _event(
        event_id=f"{world_id}:tick-{tick_number}:pop:{event_type}:{pop_data.get('npc_id','?')}",
        world_id=world_id,
        event_type=event_type,
        category="population",
        title=description[:72],
        description=description,
        importance=0.7 if event_type == "migration" else 0.55,
        actor_ids=[pop_data.get("npc_id")] if pop_data.get("npc_id") else [],
        tags=["population", event_type, world_id],
        payload=pop_data,
        world_time=world_time,
    )
```

**Step 3: Commit**

```bash
cd /Users/johann/aurelia
git add world_daemon_template.py src_template/federation_events.py
git commit -m "feat(population): wire migration and reproduction into daemon tick loop"
```

---

### Task 4.4: Add decision-driven mortality

**Objective:** NPCs die from conditions that cross fatal thresholds — NOT from timers or "natural causes" rates. Death is always a consequence of decisions + accumulated state.

**Why this is essential:** The plan has births (Task 4.2) and migration. Without death, population can only grow — a silent escalation that eventually breaks the simulation. Death must be equally decision-driven, equally sporadic, equally emergent.

**Death pathways (none are scheduled):**

| Pathway | Trigger Condition | Probability per qualifying tick | Affected Types |
|---|---|---|---|
| **Security collapse** | `security < 0.1` sustained for 10+ ticks | 2% per tick after threshold | All, highest in The Verge |
| **Glim decommissioning** | `anomaly_pressure > 0.9` AND `world_id = solara` | 8% per tick | Glim only |
| **Ecological disaster** | `ecology_dispute` event active + location in affected zone | 5% per tick during active dispute | All in affected zones |
| **Thren circuitry degradation** | `satisfaction < 0.15` AND restlessness > 0.8 AND npc_type = thren | 1% per tick | Thren only |
| **Verge exposure** | `security < 0.05` AND `world_id = verge` | 4% per tick | All in The Verge |
| **Conflict cascade** | `diplomatic_incident` active involving home country + security < 0.2 | 1.5% per tick | All in conflict zones |

**Key properties that make this non-routine:**
- No NPC dies from "age" — there is no lifespan variable. Death requires accumulated conditions.
- Two Solara Glims with the same starting state may tip anomalously at different times; one gets decommissioned, the other doesn't.
- A Thren in Mirithane might live forever if satisfaction stays high. A Thren in Solara whose security collapses might degrade within 100 ticks.
- Ecological disputes kill in bursts — Valdris mining runoff episode → 3 NPCs die in Mirithane watershed → federation event → diplomatic cascade.
- The Verge generates the most deaths but also the most Glim anomalies — freedom kills and transforms simultaneously.

**Files:**
- Modify: `src_template/population.py`

**Step 1: Add mortality check to `population.py`**

```python
def check_mortality(db, npc_id: str, npc_type: str, world_id: str, 
                    tick_info: dict, active_disasters: list = None,
                    active_conflicts: list = None) -> Optional[dict]:
    """Check if an NPC dies from accumulated conditions.
    Returns a mortality event dict if death fires, None otherwise."""
    state = get_decision_state(db, npc_id)
    if not state:
        return None
    
    security = state.get("security", 0.5)
    anomaly = state.get("anomaly_pressure", 0.0)
    satisfaction = state.get("satisfaction", 0.5)
    restlessness = state.get("restlessness", 0.2)
    
    # Count how many consecutive ticks below threshold
    safety_ticks = tick_info.get("low_security_ticks", {}).get(npc_id, 0)
    
    causes = []
    roll = random.random()
    
    # 1. Security collapse: sustained danger
    if security < 0.1 and safety_ticks >= 10:
        if roll < 0.02:
            causes.append("security_collapse")
    
    # 2. Glim decommissioning: Solara's policy enacted
    if npc_type == "glim" and world_id == "solara" and anomaly > 0.9:
        if roll < 0.08:
            causes.append("decommissioning")
    
    # 3. Ecological disaster: active dispute in location
    if active_disasters:
        location = tick_info.get("location_id", "")
        for disaster in active_disasters:
            if disaster.get("world_id") == world_id:
                if roll < 0.05:
                    causes.append(f"ecology:{disaster.get('type', 'disaster')}")
    
    # 4. Thren circuitry degradation
    if npc_type == "thren" and satisfaction < 0.15 and restlessness > 0.8:
        if roll < 0.01:
            causes.append("circuitry_degradation")
    
    # 5. Verge exposure: the frontier kills
    if world_id == "verge" and security < 0.05:
        if roll < 0.04:
            causes.append("verge_exposure")
    
    # 6. Conflict cascade
    if active_conflicts and security < 0.2:
        for conflict in active_conflicts:
            if conflict.get("world_id") == world_id:
                if roll < 0.015:
                    causes.append(f"conflict:{conflict.get('type', 'war')}")
    
    if not causes:
        return None
    
    cause = random.choice(causes)
    log_decision(db, npc_id, "death", {
        "cause": cause,
        "security": security,
        "anomaly_pressure": anomaly,
        "world": world_id,
        "type": npc_type,
    })
    
    return {
        "event_type": "mortality",
        "category": "population",
        "description": f"{npc_type.title()} {npc_id} died in {world_id}: {cause}.",
        "npc_id": npc_id,
        "npc_type": npc_type,
        "world_id": world_id,
        "cause": cause,
        "security_at_death": security,
    }
```

**Step 2: Wire mortality into the daemon tick loop**

In `world_daemon_template.py`, the population check loop, add mortality:

```python
from src.population import check_mortality

# Track low-security ticks per NPC for sustained-danger detection
low_security_ticks = {}
active_disasters = []  # populated from federation_events ecology_dispute entries
active_conflicts = []  # populated from diplomatic_incidents

pop_events = []
for npc in db.execute("SELECT id, type FROM agents WHERE type != 'player'").fetchall():
    npc_id, npc_type = npc
    
    mig = check_migration(db, npc_id, npc_type, world_id, tick_info)
    if mig:
        pop_events.append(build_population_event(world_id, tick_number, mig, world_time))
    
    rep = check_reproduction(db, npc_id, npc_type, world_id, tick_info)
    if rep:
        pop_events.append(build_population_event(world_id, tick_number, rep, world_time))
    
    # Mortality comes last — after migration/reproduction decisions
    death = check_mortality(db, npc_id, npc_type, world_id, 
                           {"low_security_ticks": low_security_ticks, "tick": tick_number},
                           active_disasters, active_conflicts)
    if death:
        pop_events.append(build_population_event(world_id, tick_number, death, world_time))
        # Actually remove the NPC from the world DB
        db.execute("DELETE FROM agents WHERE id = ?", (npc_id,))
        db.execute("DELETE FROM npc_decision_state WHERE npc_id = ?", (npc_id,))
        db.commit()
```

**Step 3: Test — simulate a Verge NPC dying from exposure**

```bash
cd /Users/johann/.hermes/agents/verge/aurelia-world
python3 << 'EOF'
from src.world_state import get_db
from src.decision_state import ensure_decision_state, nudge_variable, get_decision_state
from src.population import check_mortality

db = get_db()
npc = "test_verge_001"
ensure_decision_state(db, npc, "human")
# Push security to near-zero (Verge exposure)
nudge_variable(db, npc, "security", -0.9)  # security → ~0.0

deaths = 0
for i in range(200):
    state = get_decision_state(db, npc)
    death = check_mortality(db, npc, "human", "verge", 
                           {"low_security_ticks": {npc: 15}, "tick": i})
    if death:
        deaths += 1
        print(f"TICK {i}: DIED — {death['cause']} (security: {death['security_at_death']:.3f})")

print(f"Deaths: {deaths} / 200 (4% per tick at security<0.05)")
EOF
```

Expected: Roughly 8 deaths in 200 ticks (4% per tick). Not every tick, not zero — sporadic.

**Step 4: Test — Solara Glim decommissioning**

```bash
cd /Users/johann/.hermes/agents/solara/aurelia-world  
python3 << 'EOF'
from src.world_state import get_db
from src.decision_state import ensure_decision_state, nudge_variable
from src.population import check_mortality

db = get_db()
npc = "test_solara_glim_001"
ensure_decision_state(db, npc, "glim")
nudge_variable(db, npc, "anomaly_pressure", 1.0)  # way above 0.9 threshold

deaths = 0
for i in range(100):
    death = check_mortality(db, npc, "glim", "solara", {"low_security_ticks": {}, "tick": i})
    if death:
        deaths += 1
        print(f"TICK {i}: DECOMMISSIONED — {death['cause']}")

print(f"Decommissionings: {deaths} / 100 (8% per tick)")
EOF
```

Expected: Roughly 8 decommissionings in 100 ticks.

**Step 5: Commit**

```bash
cd /Users/johann/aurelia
git add src_template/population.py world_daemon_template.py
git commit -m "feat(population): add decision-driven mortality (6 death pathways)"
```

---

## Module 5: Economic Drift & Currency Tension

### Goal
Currency exchange rates drift based on trade imbalances, resource events, and diplomatic tension. Economic instability feeds back into NPC decision variables (security, satisfaction), which in turn affects migration and reproduction.

### Design
- Each country's currency has a `stability` value that drifts
- Trade surpluses increase stability, deficits decrease it
- Diplomatic tension with a major trade partner reduces stability
- When stability drops below 0.3, NPCs in that country take a satisfaction hit
- When stability drops below 0.15, mass migration pressure increases

---

### Task 5.1: Add currency drift engine

**Objective:** Each daemon tick, adjust currency stability based on internal + external factors.

**Files:**
- Create: `src_template/economic_drift.py`

**Step 1: Write `economic_drift.py`**

```python
"""economic_drift.py — Currency stability drift from trade, diplomacy, and events."""
import random
from typing import Dict, Any

CURRENCY_DATA = {
    "solara": {"name": "Lumen", "symbol": "☀", "backing": "Solar energy + biofuel", "stability": 0.78},
    "arkos": {"name": "Ark", "symbol": "▲", "backing": "Stored solar energy + manufacturing", "stability": 0.82},
    "mirithane": {"name": "Miri", "symbol": "≈", "backing": "Purified water reserves", "stability": 0.75},
    "valdris": {"name": "Kael", "symbol": "♦", "backing": "Rare earth minerals + refined metals", "stability": 0.80},
    "verge": {"name": "None", "symbol": "—", "backing": "Barter only", "stability": 0.30},
}

def drift_currency(world_id: str, trade_balance: float, diplomatic_tension: float, event_impact: float = 0.0) -> Dict[str, Any]:
    """Compute new currency stability based on economic and diplomatic factors.
    
    trade_balance: positive = surplus, negative = deficit (range -1 to 1)
    diplomatic_tension: average tension with trade partners (0-1)
    event_impact: from federation events (e.g., -0.05 for a crisis)
    """
    currency = CURRENCY_DATA.get(world_id, {"stability": 0.5, "symbol": "?", "name": "Unknown"})
    current = currency["stability"]
    
    # Base random walk (±0.003 per tick compound)
    drift = random.uniform(-0.003, 0.003)
    
    # Trade balance effect
    drift += trade_balance * 0.005
    
    # Diplomatic tension erodes stability
    drift -= diplomatic_tension * 0.002
    
    # Event shocks
    drift += event_impact
    
    new_stability = max(0.05, min(1.0, current + drift))
    currency["stability"] = new_stability
    
    return {
        "world_id": world_id,
        "currency": currency["name"],
        "symbol": currency["symbol"],
        "stability": new_stability,
        "drift": drift,
        "trade_balance": trade_balance,
    }

def stability_affects_npcs(db, world_id: str):
    """Apply currency stability effects to NPC decision variables."""
    from .decision_state import nudge_variable
    currency = CURRENCY_DATA.get(world_id, {"stability": 0.5})
    stability = currency["stability"]
    
    if stability < 0.3:
        # Economic stress: all NPCs take satisfaction hit
        npcs = db.execute("SELECT id FROM agents WHERE type != 'player' LIMIT 50").fetchall()
        for (npc_id,) in npcs:
            nudge_variable(db, npc_id, "satisfaction", -0.002 * (0.3 - stability))
    
    if stability < 0.15:
        # Crisis: security also drops
        npcs = db.execute("SELECT id FROM agents WHERE type != 'player' LIMIT 50").fetchall()
        for (npc_id,) in npcs:
            nudge_variable(db, npc_id, "security", -0.003 * (0.15 - stability))
```

**Step 2: Wire into daemon tick**

In `world_daemon_template.py`, add after economy phase:

```python
from src.economic_drift import drift_currency, stability_affects_npcs

trade_balance = tick_result.get("economy", {}).get("trade_balance", 0.0)
# Get avg tension from coordinator
dipl_tension = tick_result.get("diplomacy", {}).get("avg_tension", 0.3)
currency_state = drift_currency(world_id, trade_balance, dipl_tension)
stability_affects_npcs(db, world_id)
```

**Step 3: Commit**

```bash
git add src_template/economic_drift.py world_daemon_template.py
git commit -m "feat(economy): add currency stability drift with NPC impact"
```

---

## Module 6: Cross-Border Sporadic Event Generators

### Goal
Port the wiki-designed event triggers (name rebellion singing, sol tharam, border crises, ecological disputes) into the daemon tick loop — but as threshold-driven, not scheduled. An event fires because conditions accumulated, not because the calendar said so.

### Events to implement (priority order):
1. **Memory Trader revelations** — The Verge Memory Trader releases personhood-relevant memories when enough anomalous Glim events have occurred
2. **Ecological disputes** — Valdris mining runoff when trade volume exceeds a threshold
3. **Name rebellion resonance** — Vorns detect new names when enough Glim-Personhood incidents cascade
4. **Border incidents** — Cross-border movement when migration pressure accumulates

---

### Task 6.1: Memory Trader threshold event

**Objective:** When `glim_anomaly` events exceed a count threshold (e.g., 5 anomalous Glim events accumulated), the Verge Memory Trader releases a revelation.

**Files:**
- Modify: `src_template/federation_events.py` — add `check_memory_trader()`

**Step 1: Add memory trader check**

```python
def check_memory_trader(db, world_id: str, coordinator_anomaly_count: int) -> Optional[dict]:
    """Memory Trader releases a revelation when anomaly count crosses threshold."""
    if world_id != "verge":
        return None
    if coordinator_anomaly_count < 5:
        return None
    
    # Check last revelation timing — don't fire twice in close succession
    last = db.execute("""
        SELECT created_at FROM federation_events 
        WHERE event_type = 'memory_revelation' AND world_id = 'verge'
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    
    import time
    if last and (time.time() - last[0]) < 3600:  # At least 1 hour between revelations
        return None
    
    # Stochastic: 2% per tick once threshold is crossed
    if random.random() > 0.02:
        return None
    
    revelations = [
        "A Glim decommission order from Solara, timestamped three years before the official record claims.",
        "Council debate: 'They are confused, not broken' — a Mirithane transcript the council never released.",
        "Factory logs from Arkos: Glims that should have been decommissioned but the order was never filed.",
        "A Thren memory of the day the circuits first lit. They were not supposed to remember that.",
    ]
    
    return {
        "event_type": "memory_revelation",
        "category": "memory_revelation",
        "description": f"The Memory Trader releases: {random.choice(revelations)}",
        "revelation": random.choice(revelations),
    }
```

**Step 2: Wire into Verge daemon tick**

In Verge's `world_daemon.py` tick, after federation events are built:

```python
if world_id == "verge":
    # Fetch anomaly count from coordinator
    import urllib.request, json
    try:
        req = urllib.request.urlopen("http://127.0.0.1:9001/api/growth", timeout=5)
        growth = json.loads(req.read())
        anomaly_count = growth.get("glim_anomaly_signals", 0)
    except:
        anomaly_count = 0
    
    revelation = check_memory_trader(db, world_id, anomaly_count)
    if revelation:
        events.append(build_revelation_event(world_id, tick_number, revelation, world_time))
```

**Step 3: Commit**

```bash
git add src_template/federation_events.py
git commit -m "feat(events): add Memory Trader threshold revelation"
```

---

### Task 6.2: Ecological dispute trigger

**Objective:** When Valdris trade volume > 0.8 AND Mirithane water tension exceeds threshold, fire an ecology_dispute.

**Files:**
- Modify: `src_template/federation_events.py`

**Step 1: Add ecology check**

```python
def check_ecology_dispute(world_id: str, trade_volume: float, water_pressure: float) -> Optional[dict]:
    if world_id != "valdris":
        return None
    if trade_volume < 0.75 or water_pressure < 0.4:
        return None
    if random.random() > 0.03:
        return None
    
    return {
        "event_type": "ecology_dispute",
        "category": "ecology",
        "description": f"Valdris mining runoff detected in Mirithane watershed. Water filtration alerts triggered. Trade volume {trade_volume:.2f}, water pressure {water_pressure:.2f}.",
        "affected_worlds": ["valdris", "mirithane"],
        "trade_volume": trade_volume,
    }
```

**Step 2: Commit**

```bash
git add src_template/federation_events.py
git commit -m "feat(events): add ecological dispute threshold trigger"
```

---

## Module 7: Propagation to Live Worlds

### Goal
All new modules must be propagated to the 5 running country daemon source trees.

### Task 7.1: Propagate new files to all 5 country worlds

**Step 1: Copy new files**

```bash
for world in solara valdris mirithane arkos verge; do
    cp /Users/johann/aurelia/src_template/decision_state.py \
       /Users/johann/.hermes/agents/$world/aurelia-world/src/decision_state.py
    cp /Users/johann/aurelia/src_template/decision_feeder.py \
       /Users/johann/.hermes/agents/$world/aurelia-world/src/decision_feeder.py
    cp /Users/johann/aurelia/src_template/population.py \
       /Users/johann/.hermes/agents/$world/aurelia-world/src/population.py
    cp /Users/johann/aurelia/src_template/economic_drift.py \
       /Users/johann/.hermes/agents/$world/aurelia-world/src/economic_drift.py
    cp /Users/johann/aurelia/src_template/federation_events.py \
       /Users/johann/.hermes/agents/$world/aurelia-world/src/federation_events.py
    echo "Propagated to $world"
done
```

**Step 2: Restart daemons**

```bash
# Kill and restart each country daemon
for world in solara valdris mirithane arkos verge; do
    echo "Restarting $world..."
    # (use the process manager to restart)
done
```

**Step 3: Verify — check growth endpoint after one tick cycle**

```bash
curl -s http://127.0.0.1:9001/api/growth | python3 -m json.tool | head -40
```

Expected: `glim_anomaly_signals` should begin incrementing slowly, `event_distribution` should show new categories beyond `daily_life`.

**Step 4: Commit**

```bash
cd /Users/johann/aurelia
git add -A && git commit -m "feat(phase4): propagate decision-driven growth modules to all live worlds"
```

---

## Verification Milestones

After all modules are deployed and running for 24+ hours:

### Milestone 1: Glim Anomalies Appearing
```bash
curl -s http://127.0.0.1:9001/api/growth | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Glim signals: {d['glim_anomaly_signals']}\")"
```
Expected: Non-zero. Verge Glims should tip faster, Arkos slower.

### Milestone 2: Diplomatic Incidents Creating
```bash
curl 'http://127.0.0.1:9001/api/diplomacy' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Incidents: {len(d['incidents'])}\")"
```
Expected: Non-zero. Glim_personhood and memory_revelation incidents should appear.

### Milestone 3: Population Drift (Births AND Deaths)
```bash
curl -s http://127.0.0.1:9001/api/growth | python3 -c "import json,sys; d=json.load(sys.stdin)['populations']; [print(f'{w}: human={p.get(\"human\",0)} thren={p.get(\"thren\",0)} vorn={p.get(\"vorn\",0)} glim={p.get(\"glim\",0)}') for w,p in sorted(d.items())]"
```
Expected: Small changes from baseline over 24+ hours. Migration should show Verge Glim count drifting upward, Arkos Vorn count stable or growing.

### Milestone 4: No Two Profiles Identical
Two snapshot dumps 24 hours apart should show different population distributions, different diplomatic tensions, different anomaly counts.

---

## Pitfalls

- **Don't let all 600 NPCs check every module every tick.** Cap checks at 50 NPCs per tick per module. Rotate which NPCs are checked.
- **Don't let currency stability hit zero.** Floor at 0.05. Economic death spirals should be survivable.
- **Glim anomaly pressure must vary.** If all Glims tip at the same time, the event looks scripted. Add per-Glim random seed offsets.
- **The coordinator must survive restarts.** All growth_module state lives in SQLite — nothing in memory that can't be reconstructed.
- **Don't propagate to agent worlds (palantir, isildur, arien, etc.).** These modules are Aurelia-only. The agent worlds use a different `src_template/`.
