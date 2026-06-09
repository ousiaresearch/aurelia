#!/usr/bin/env python3
"""
world_daemon.py — Aurelia world simulation daemon.
Advances the world every TICK_INTERVAL seconds with federation heartbeat.
Supports all Aurelian country-states. Auto-configured by factory.
"""

import sys, os, time, signal, json, random
from datetime import datetime

DAEMON_DIR = os.path.dirname(os.path.abspath(__file__))
EW_DIR = os.path.dirname(DAEMON_DIR)
sys.path.insert(0, EW_DIR)

from src.simulation import tick
from src.world_state import get_db, DB_PATH, get_world_identity
from src.federation import register_with_coordinator, send_heartbeat, publish_federation_events
from src.federation_events import build_federation_events
from src.currency import currency_tick, get_currency

# ── CONFIG (overridden by factory) ────────────────────────────────────
TICK_INTERVAL = 30 * 60      # 30 minutes
CRASH_WINDOW = 300
PID_FILE = os.path.join(DAEMON_DIR, "daemon.pid")
HEARTBEAT_FILE = os.path.join(DAEMON_DIR, "heartbeat.json")
LOG_FILE = os.path.join(DAEMON_DIR, "daemon.log")
FEDERATION_URL = os.environ.get("FEDERATION_URL", "http://127.0.0.1:9001")
WORLD_ID = os.environ.get("WORLD_ID", "WORLD_ID_PLACEHOLDER")
AGENT_ID = os.environ.get("AGENT_ID", "AGENT_ID_PLACEHOLDER")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:API_PORT_PLACEHOLDER")

# ── Location pools per country (override these via env or factory) ────
LOCATION_POOLS = {
    "solara": {
        "morning": ["lumen_plaza", "solar_farm_alpha", "thren_quarter", "floating_market"],
        "midday": ["reef_labs", "transit_hub", "kelp_farms", "makers_district"],
        "evening": ["solar_gardens", "dawn_temple", "hydro_square", "coastal_wilds"],
    },
    "valdris": {
        "morning": ["canyon_council", "vertical_gardens", "geothermal_field", "terraced_terraces"],
        "midday": ["forge_district", "canyon_market", "deep_mines", "metal_workers_guild"],
        "evening": ["hot_springs", "ridgeline_observatory", "summit_shrine", "canyon_trail"],
    },
    "mirithane": {
        "morning": ["estuary_commons", "filtration_reefs", "floating_gardens", "reed_village"],
        "midday": ["tide_market", "biosynth_lab", "canoe_works", "memory_marsh"],
        "evening": ["water_temple", "night_barge", "heron_tower", "heron_sanctuary"],
    },
    "arkos": {
        "morning": ["arcology_core", "sand_glass_towers", "water_synthesis", "oasis_gardens"],
        "midday": ["autonomous_factory", "dune_market", "salvage_plains", "drone_station"],
        "evening": ["glass_forum", "star_observatory", "archive_sands", "sky_dock"],
    },
    "verge": {
        "morning": ["crossroads", "water_tower", "windbreak_camp", "lookout_ridge"],
        "midday": ["rust_depot", "scar_market", "salvage_kitchen", "drone_graveyard"],
        "evening": ["wayfarer_inn", "unregistered_quarter", "the_sink", "thren_sanctuary"],
    },
}

# ── Logging ───────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── PID management ────────────────────────────────────────────────────
def write_pid():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def read_pid():
    try:
        with open(PID_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None

def is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def already_running():
    pid = read_pid()
    return pid is not None and is_running(pid)

# ── Agent movement (generic across Aurelian countries) ────────────────
def move_agent(db, world_id, agent_id):
    """Move the agent according to time-of-day phases."""
    now = time.time()
    wt = db.execute("SELECT hour FROM world_time WHERE id=1").fetchone()
    if not wt:
        return
    hour = wt["hour"]
    
    pools = LOCATION_POOLS.get(world_id, {})
    if not pools:
        return
    
    # Determine phase
    if 5 <= hour < 12:
        phase = "morning"
    elif 12 <= hour < 18:
        phase = "midday"
    elif 18 <= hour < 23:
        phase = "evening"
    else:
        # Night — stay put
        return
    
    locations = pools.get(phase, [])
    if not locations:
        return
    
    current = db.execute("SELECT location_id, state FROM agents WHERE id=?", (agent_id,)).fetchone()
    if not current:
        return
    
    if random.random() < 0.70:
        current_loc = current["location_id"]
        candidates = [l for l in locations if l != current_loc]
        if candidates:
            new_loc = random.choice(candidates)
            db.execute("UPDATE agents SET location_id=?, updated_at=? WHERE id=?", (new_loc, now, agent_id))
            
            # Track exploration
            existing = db.execute(
                "SELECT visit_count FROM world_exploration WHERE agent_id=? AND location_id=?",
                (agent_id, new_loc)
            ).fetchone()
            if existing:
                db.execute(
                    "UPDATE world_exploration SET visit_count=visit_count+1, last_visit=? WHERE agent_id=? AND location_id=?",
                    (now, agent_id, new_loc))
            else:
                db.execute(
                    "INSERT INTO world_exploration (agent_id, location_id, visit_count, first_visit, last_visit) VALUES (?,?,1,?,?)",
                    (agent_id, new_loc, now, now))
            
            log(f"  {agent_id} [{phase}]: {current_loc} → {new_loc}")
    
    db.commit()

# ── Heartbeat ─────────────────────────────────────────────────────────
def write_heartbeat(tick_count, world_time):
    hb = {
        "pid": os.getpid(),
        "tick_count": tick_count,
        "world": world_time,
        "updated_at": time.time(),
        "stopped_at": None,
    }
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            json.dump(hb, f, indent=2)
    except Exception:
        pass

# ── Main loop ─────────────────────────────────────────────────────────
def run():
    log("=" * 50)
    log(f"AURELIA DAEMON — {WORLD_ID}")
    log(f"PID: {os.getpid()}")
    log(f"Tick interval: {TICK_INTERVAL}s (~{TICK_INTERVAL//60}min)")
    log(f"DB: {DB_PATH}")
    log(f"Federation: {FEDERATION_URL}")
    log("=" * 50)
    
    write_pid()
    
    # Register with federation coordinator
    db = get_db()
    identity = get_world_identity(db)
    db.close()
    if identity:
        registered = register_with_coordinator(FEDERATION_URL, WORLD_ID, API_URL, identity)
        if registered:
            log(f"Federation: registered with coordinator at {FEDERATION_URL}")
        else:
            log(f"Federation: coordinator unreachable at {FEDERATION_URL}")
    
    tick_count = 0
    running = True
    
    def signal_handler(signum, frame):
        nonlocal running
        sig = signal.Signals(signum).name
        log(f"Caught {sig} — shutting down gracefully")
        running = False
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    while running:
        tick_start = time.time()
        
        try:
            db = get_db()
            tick._tick_start_ts = tick_start
            result = tick(db, hours=1.0)
            move_agent(db, WORLD_ID, AGENT_ID)
            
            # Currency tick — mint + exchange rate drift + commerce
            npcs = [r[0] for r in db.execute("SELECT id FROM agents WHERE type='npc'").fetchall()]
            try:
                currency_summary = currency_tick(db, WORLD_ID, npcs)
            except Exception:
                currency_summary = {}
            
            db.close()
            
            tick_count += 1
            
            # Federation event bus — publish compact, meaningful tick outputs.
            federation_event_count = 0
            try:
                federation_events = build_federation_events(WORLD_ID, tick_count, result, max_events=25)
                publish_result = publish_federation_events(FEDERATION_URL, WORLD_ID, federation_events)
                federation_event_count = publish_result.get("accepted", 0)
            except Exception:
                federation_event_count = 0
            
            # Heartbeat
            try:
                db2 = get_db()
                wt = db2.execute("SELECT * FROM world_time WHERE id=1").fetchone()
                world_time = dict(wt) if wt else {}
                db2.close()
            except Exception:
                world_time = {}
            
            write_heartbeat(tick_count, world_time)
            
            # Federation heartbeat
            try:
                db3 = get_db()
                fed_identity = get_world_identity(db3)
                db3.close()
                send_heartbeat(FEDERATION_URL, WORLD_ID, fed_identity)
            except Exception:
                pass
            
            if tick_count % 10 == 0:
                wt_str = f"{world_time.get('month','?')}/{world_time.get('day','?')} {world_time.get('time_of_day','?')}"
                npc_actions = len(result.get("npc_ai_actions", []))
                social = len(result.get("social_changes", []))
                minted = currency_summary.get("minted", 0)
                log(f"TICK {tick_count:4d} | world: {wt_str} | npc_actions: {npc_actions} | social: {social} | currency_minted: {minted} | fed_events: {federation_event_count}")
        
        except Exception as e:
            log(f"ERROR in tick {tick_count}: {e}")
            import traceback
            log(traceback.format_exc())
        
        # Sleep until next tick
        elapsed = time.time() - tick_start
        sleep_time = max(1, TICK_INTERVAL - elapsed)
        
        slept = 0
        while slept < sleep_time and running:
            time.sleep(min(5, sleep_time - slept))
            slept += 5
    
    # Clean shutdown
    log("World daemon stopped.")
    try:
        os.remove(PID_FILE)
    except OSError:
        pass

if __name__ == "__main__":
    if already_running():
        print("World daemon already running. Exiting.")
        sys.exit(0)
    run()
