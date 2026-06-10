# Technical Architecture

> *How Aurelia works under the hood — federated daemons, SQLite worlds, currency simulation, and the coordinator hub.*

## System Overview

```
┌──────────────────────────────────────────────┐
│         Aurelia Federation Coordinator        │
│              http://127.0.0.1:9001             │
│  ┌─────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Registry │  │ Exchange │  │ Dark Dashboard│ │
│  │(worlds)  │  │ (rates)  │  │   (HTML)     │ │
│  └─────────┘  └──────────┘  └──────────────┘ │
└──────┬──────────┬──────────┬──────────┬───────┘
       │          │          │          │
   heartbeat   heartbeat   heartbeat   heartbeat
   (30 min)    (30 min)    (30 min)    (30 min)
       │          │          │          │
  ┌────▼────┐ ┌──▼────┐ ┌───▼───┐ ┌───▼──────┐
  │ Solara  │ │Valdris│ │Miri-  │ │  Arkos   │  The Verge
  │ Daemon  │ │Daemon │ │thane  │ │  Daemon  │  (same arch)
  │ :8760   │ │:8761  │ │:8762  │ │  :8763   │
  └─────────┘ └───────┘ └───────┘ └──────────┘
```

## Components

### 1. Federation Coordinator (`aurelia_coordinator.py`)

**Location:** `/Users/johann/aurelia/`

A lightweight HTTP server on port 9001 that serves as the central nervous system.

**Responsibilities:**
- **World registry** — accepts registration and heartbeat POSTs from daemons
- **Health tracking** — online/degraded/offline detection (heartbeat timeout: 600s warning, 3600s offline)
- **Dark dashboard** — real-time HTML view with NPC type distribution bars, currency exchange table, per-world health status
- **Currency exchange** — reads rates from any world's `exchange_rates` table, serves a unified view
- **NPC stats** — cross-database queries into each country's `world.db` to aggregate type distributions

**API Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Dark dashboard (auto-refreshes every 30s) |
| GET | `/api/status` | All worlds with status + heartbeat age |
| GET | `/api/npc-stats` | Per-country NPC type breakdown |
| GET | `/api/rates` | All currencies + exchange rates |
| GET | `/api/health` | Coordinator uptime + world count |
| POST | `/register` | Daemon registration |
| POST | `/heartbeat` | Daemon heartbeat update |

### 2. World Factory (`aurelia_factory.py`)

**Location:** `/Users/johann/aurelia/`

Creates and initializes world databases from YAML configs. One-time setup per country.

**Responsibilities:**
- Parses `configs/<country>.yaml` — geography, locations, currency, NPC type counts
- Creates SQLite database with full schema (world_time, agents, locations, exchange_rates, social_graph, npc_memories, ecology, etc.)
- Assigns currency, initial exchange rates, starting world time (2126-03-17)
- Populates NPCs from deep seed or randomized generation
- Links daemon template scripts

**Schema highlights:**
- `world_time` — single-row table tracking year/month/day/hour/minute/season/time_of_day
- `agents` — all entities: hosted agent (world's avatar), NPCs (human/thren/vorn/glim), with properties JSON blob
- `exchange_rates` — cross-currency rates updated each tick by currency simulation
- `world_exploration` — per-agent location visit tracking
- `social_graph` — relationships between NPCs (coworker, family, rival, cross-type bond)
- `npc_memories` — formative memories and backstories for each NPC
- `world_events` — world-state-level event log

### 3. World Daemon (`world_daemon.py`)

**Location:** `~/.hermes/agents/<country>/aurelia-world/scripts/`

Each country runs one daemon process. 30-minute tick interval. Handles:

**Per-Tick Operations:**
1. **Time advance** — advances world clock by 1 hour (configurable)
2. **Agent movement** — moves the hosted agent through country-specific location pools based on time-of-day phase (morning/midday/evening/night)
3. **NPC AI** — runs NPC action resolution, social updates, dialogue triggers
4. **Currency tick** — mints new currency into wallets, drifts exchange rates, resolves NPC commerce
5. **Federation heartbeat** — POSTs to coordinator at `http://127.0.0.1:9001/heartbeat`
6. **Local heartbeat** — writes `heartbeat.json` to scripts directory
7. **Tick logging** — every 10th tick logs world date/time + NPC actions + social changes + currency minted

**Crash Recovery:**
- PID file prevents duplicate daemons
- Crash window: if a daemon restarts within 300 seconds, it resumes gracefully
- SIGTERM/SIGINT handlers for clean shutdown

### 4. Shared Engine (`src_template/`)

**Location:** `/Users/johann/aurelia/src_template/` (copied to each country's `src/`)

The ~20,000-line shared engine powering all Aurelian worlds:

| Module | Lines | Purpose |
|--------|-------|---------|
| `world_state.py` | ~1,300 | Core DB abstraction, world identity, time management |
| `simulation.py` | ~700 | Tick orchestration — NPC AI, social, ecology, events |
| `economy.py` | ~600 | Currency simulation, exchange rates, commerce |
| `npc_generation.py` | ~900 | Procedural NPC creation with backstories |
| `npc_dialogue.py` | ~800 | Context-aware dialogue generation |
| `npc_memory.py` | ~500 | Persistent memories and formative experiences |
| `ecology.py` | ~500 | Environmental systems per biome |
| `rituals.py` | ~800 | Cultural and spiritual practice simulation |
| `prose_narrative.py` | ~500 | Narrative generation from world state |
| `agent.py` | ~1,600 | Hosted agent behavior engine |
| `federation.py` | ~60 | Coordinator registration/heartbeat client |
| `currency.py` | ~600 | Multi-currency system with minting and exchange |

### 5. Deep Seed (`deep_seed.py`)

**Location:** `/Users/johann/aurelia/`

Populates all 600 NPCs across 5 countries with:
- 24-hour schedules tailored to occupation + type + country
- Social graph: coworkers, neighbors, family, rivals, cross-type bonds
- Formative memories, backstories, significant life events
- Ecological footprint: harvesting, production, protection roles
- Psychological profiles: values, fears, desires, secrets

**Country-specific location pools:** Each country has work/social/rest location sets that NPCs rotate through on schedules matching their occupation category (energy, farming, forge, research, social/civic, market, transit).

## Data Flow

```
World Config (YAML)
       │
       ▼
  Factory (aurelia_factory.py)
       │
       ├─→ Creates world.db (SQLite)
       ├─→ Copies src_template/ → country/src/
       ├─→ Populates NPCs via deep_seed.py
       │
       ▼
  Daemon (world_daemon.py)
       │
       ├─→ Every 30 min: tick(db, hours=1.0)
       │     ├─→ advance world_time
       │     ├─→ npc_ai.think() for each NPC
       │     ├─→ social.update() for relationships
       │     ├─→ ecology.tick() for environmental systems
       │     ├─→ currency_tick() for economy
       │     └─→ prose_narrative.generate() for story
       │
       ├─→ move_agent() through location pools
       │
       ├─→ POST /heartbeat → Coordinator (port 9001)
       │
       └─→ write heartbeat.json locally
```

## Running Status

As of June 2, 2026 — all 5 Aurelian daemons are running:

| World | PID | Port | Ticks | Status |
|-------|-----|------|-------|--------|
| Solara | 49221 | 8760 | 20+ | Online |
| Valdris | 49293 | 8761 | 20+ | Online |
| Mirithane | 49364 | 8762 | 20+ | Online |
| Arkos | 49395 | 8763 | 20+ | Online |
| The Verge | 49442 | 8764 | 20+ | Online |

**Coordinator:** PID 52667, port 9001

## Tech Stack

- **Language:** Python 3.13
- **Database:** SQLite (one per country, WAL mode)
- **Server:** stdlib `http.server` (zero dependencies)
- **Config:** YAML
- **Platform:** macOS 26.3
