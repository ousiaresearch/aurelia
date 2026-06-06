#!/usr/bin/env python3
"""
speed_run.py — Aurelia Colab speed-runner. Self-contained, no external deps.

Runs 5 worlds simultaneously at 1 tick = 1 sim-day (360 ticks/year).
All modules copied flat into colab/src/ with coordinator path patched out.

Usage:
  python3 speed_run.py --years 200 --npcs 12000 --output /content/output
"""

import sys, os, time, json, random, argparse, sqlite3, copy
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]
TICKS_PER_YEAR = 360  # 1 tick = 1 day
DEFAULT_NPC = 12000
OUTPUT_DIR = Path("output")

# ═══════════════════════════════════════════════════════════════════
# MONKEY-PATCH: Fix coordinator paths for Colab
# ═══════════════════════════════════════════════════════════════════

# All hardcoded paths must become ":memory:" or return empty dicts.
# We do this by patching sqlite3.connect globals in loaded modules.
import sqlite3 as _sql
_ORIG_CONNECT = _sql.connect

def _patched_connect(path, *args, **kwargs):
    """Replace any /Users/johann/... coordinator path with :memory:"""
    if isinstance(path, str) and ("coordinator.db" in path or "johann" in path):
        # Return an in-memory DB that will be empty
        return _ORIG_CONNECT(":memory:", *args, **kwargs)
    return _ORIG_CONNECT(path, *args, **kwargs)

_sql.connect = _patched_connect

# Also patch the specific _load_diplomatic_relations functions at import time
# by providing a module-level override
def _empty_diplomatic_relations():
    return {}

# We'll inject this after importing each module

# ═══════════════════════════════════════════════════════════════════
# MODULE LOADER
# ═══════════════════════════════════════════════════════════════════

def load_simulation_modules(src_dir: str):
    """Import all simulation modules and patch coordinator dependencies."""
    src = Path(src_dir)
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    # Import world_state first (schema)
    import world_state
    import simulation
    import simulation as sim

    # Patch _load_diplomatic_relations in all modules that have it
    modules_to_patch = []
    for name in ["simulation", "sovereignty", "escalation_ladder", "reconciliation",
                  "federation_dynamics", "cross_world", "policy_drift"]:
        try:
            mod = __import__(name)
            if hasattr(mod, "_load_diplomatic_relations"):
                mod._load_diplomatic_relations = _empty_diplomatic_relations
            modules_to_patch.append(name)
        except ImportError:
            pass

    return world_state, simulation


# ═══════════════════════════════════════════════════════════════════
# WORLD SETUP
# ═══════════════════════════════════════════════════════════════════

def setup_world(world_id: str, db_path: str, src_dir: str, npc_count: int = DEFAULT_NPC):
    """Initialize fresh world DB with schema, world identity, NPCs, and deep seeding."""
    print(f"  Setting up {world_id}...")

    src = Path(src_dir)
    sys.path.insert(0, str(src))

    import world_state
    world_state.DB_PATH = Path(db_path)

    # Init schema
    db = world_state.init_world(Path(db_path))
    db.row_factory = sqlite3.Row

    # Register world identity
    now = time.time()
    try:
        db.execute("""
            INSERT OR REPLACE INTO world_registry (id, world_id, name, region, timezone,
                hosted_agent_id, entry_location_id, api_port, created_at, updated_at)
            VALUES (1, ?, ?, ?, 'UTC', ?, 'town_square', 8765, ?, ?)
        """, (world_id, world_id.title(), world_id.title(), world_id, now, now))
    except Exception:
        pass

    # Seed initial world state
    world_state.seed_world(db)
    db.commit()
    db.close()

    # Generate NPCs inline — Colab can't use populate_npcs (hardcoded paths)
    _inline_generate_npcs(db_path, world_id, npc_count)

    # Deep seed inline
    _inline_deep_seed(db_path, world_id, npc_count)

    # Verify
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    npcs = db.execute("SELECT COUNT(*) as c FROM agents WHERE type='npc'").fetchone()
    fac_tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    required = ['factions', 'faction_members', 'sovereignty_events', 'peace_treaties',
                'discoveries', 'great_persons', 'cross_world_movements', 'npc_decision_state']
    missing = [t for t in required if t not in fac_tables]
    db.close()

    print(f"    {world_id}: {npcs['c']} NPCs, {len(required)-len(missing)}/{len(required)} Phase 6 tables"
          + (f", MISSING: {missing}" if missing else ""))


# ═══════════════════════════════════════════════════════════════════
# ACCELERATED TICK
# ═══════════════════════════════════════════════════════════════════

def _inline_generate_npcs(db_path: str, world_id: str, npc_count: int):
    """Inline NPC generation — no hardcoded paths."""
    src_dir = Path(__file__).resolve().parent.parent / "src"
    sys.path.insert(0, str(src_dir))

    try:
        if npc_count > 1000:
            raise RuntimeError("skip slow populate_village at Colab scale")
        from npc_generation import populate_village
        import world_state
        old_path = world_state.DB_PATH
        world_state.DB_PATH = Path(db_path)

        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        n = populate_village(db, npc_count)
        db.commit()
        db.close()
        world_state.DB_PATH = old_path
        if n > 0:
            print(f"    Generated {n} NPCs via populate_village")
        return
    except Exception:
        pass

    # Fallback: minimal NPC generation
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    now = time.time()
    names = [f"{world_id.capitalize()}_{i:04d}" for i in range(npc_count)]
    types = ["human", "thren", "vorn", "glim"]
    locs = [r["id"] for r in db.execute("SELECT id FROM locations LIMIT 20").fetchall()] or ["town_square"]
    for i in range(npc_count):
        npc_type = types[i % len(types)]
        db.execute("""
            INSERT INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
            VALUES (?, ?, 'npc', ?, 'active', ?, ?, ?)
        """, (f"{world_id}_{i:05d}", names[i], random.choice(locs),
              json.dumps({"npc_type": npc_type, "occupation": "citizen"}), now, now))
    db.commit()
    db.close()
    print(f"    Generated {npc_count} NPCs (fallback)")


def _inline_deep_seed(db_path: str, world_id: str, npc_count: int):
    """Inline deep seeding — schedules, decision states, relationships."""
    src_dir = Path(__file__).resolve().parent.parent / "src"
    sys.path.insert(0, str(src_dir))

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    now = time.time()
    npcs = db.execute("SELECT * FROM agents WHERE type='npc'").fetchall()

    # Sanitize legacy cabin/village location ids before schedules, movement, births.
    valid_locs = {r["id"] for r in db.execute("SELECT id FROM locations").fetchall()}
    fallback_loc = next(iter(valid_locs), "town_square")
    legacy_map = {
        "cabin": "town_square", "workshop": "boat_shed", "clearing": "forest_clearing",
        "ridgeline": "hillside_overlook", "cabin_kitchen": "general_store",
        "cabin_bedroom": "fisher_house", "cabin_main_room": "town_square",
        "cabin_deck": "dock", "garden": "farm_edge", "cedar_deep": "forest_deep",
        "cedar_trail": "forest_trail", "mountain_creek": "creek", "wine_cellar": "general_store",
    }
    for bad, good in legacy_map.items():
        target = good if good in valid_locs else fallback_loc
        db.execute("UPDATE agents SET location_id=? WHERE location_id=?", (target, bad))
        db.execute("UPDATE npc_schedules SET location_id=? WHERE location_id=?", (target, bad))
    db.execute("DELETE FROM npc_schedules WHERE location_id IS NOT NULL AND location_id NOT IN (SELECT id FROM locations)")
    db.commit()
    npcs = db.execute("SELECT * FROM agents WHERE type='npc'").fetchall()

    try:
        from npc_generation import generate_npc_schedule
        import world_state, decision_state
        old_path = world_state.DB_PATH
        world_state.DB_PATH = Path(db_path)

        for npc in npcs:
            try:
                props = json.loads(npc["properties"]) if isinstance(npc["properties"], str) else npc["properties"]
            except (json.JSONDecodeError, TypeError):
                props = {}
            npc_dict = {"id": npc["id"], "name": npc["name"],
                        "type": props.get("npc_type", "human"),
                        "location_id": npc["location_id"], "properties": props}

            # Schedule for waking hours (skip at 12K scale; schedules are not required for speed-run population drift)
            for h in (() if npc_count > 1000 else range(6, 22)):
                try:
                    sched = generate_npc_schedule(npc_dict, h)
                    if sched:
                        db.execute("""
                            INSERT OR IGNORE INTO npc_schedules (npc_id, hour, activity, location_id, description)
                            VALUES (?, ?, ?, ?, ?)
                        """, (npc["id"], h, sched.get("activity", "idle"),
                              sched.get("location_id", npc["location_id"]),
                              sched.get("description", "")))
                except Exception:
                    pass

            # Decision state
            base = decision_state.GLIM_BASE if props.get("npc_type") == "glim" else decision_state.BASE_STATE
            db.execute("INSERT OR IGNORE INTO npc_decision_state (npc_id, variables, last_updated) VALUES (?, ?, ?)",
                      (npc["id"], json.dumps(base), now))

        world_state.DB_PATH = old_path
    except Exception:
        # Fallback: just decision states
        from decision_state import BASE_STATE
        for npc in npcs:
            db.execute("INSERT OR IGNORE INTO npc_decision_state (npc_id, variables, last_updated) VALUES (?, ?, ?)",
                      (npc["id"], json.dumps(BASE_STATE), now))

    # Bounded relationships. Important at 120K scale: do NOT build
    # `others = [oid for oid in all_ids if oid != npc]` per NPC — that is O(n²).
    # Pick by random index instead and batch INSERT.
    all_ids = [n["id"] for n in npcs]
    rel_cap = 3 if npc_count > 1000 else 10
    rel_rows = []
    n_ids = len(all_ids)
    if n_ids > 1:
        for npc in npcs:
            max_rels = min(rel_cap, n_ids - 1)
            chosen = set()
            attempts = 0
            while len(chosen) < max_rels and attempts < max_rels * 8:
                other = all_ids[random.randrange(n_ids)]
                attempts += 1
                if other != npc["id"]:
                    chosen.add(other)
            for other in chosen:
                rel_rows.append((npc["id"], other, round(random.uniform(0.3, 0.7), 2)))
    if rel_rows:
        db.executemany("""
            INSERT OR IGNORE INTO npc_relationships (npc_a, npc_b, relationship, affinity)
            VALUES (?, ?, 'acquaintance', ?)
        """, rel_rows)

    db.commit()
    db.close()
    print(f"    Deep-seeded {len(npcs)} NPCs: schedules, decision states, {min(rel_cap,len(all_ids)-1) if len(all_ids)>1 else 0} relationships/NPC")



def _poisson(lmbda: float) -> int:
    """Small stdlib Poisson sampler; Gaussian approximation for large means."""
    import math
    if lmbda <= 0:
        return 0
    if lmbda < 30:
        L = math.exp(-lmbda)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1
    return max(0, round(random.gauss(lmbda, math.sqrt(lmbda))))


def _drift_decision_states(db, sample: int = 300) -> None:
    """Random-walk decision variables so threshold-gated systems can diverge."""
    rows = db.execute(
        "SELECT npc_id, variables FROM npc_decision_state ORDER BY RANDOM() LIMIT ?",
        (sample,),
    ).fetchall()
    now = time.time()
    for row in rows:
        try:
            variables = json.loads(row["variables"] or "{}")
        except Exception:
            variables = {}
        changed = False
        for key, value in list(variables.items()):
            if isinstance(value, (int, float)):
                variables[key] = max(0.0, min(1.0, float(value) + random.uniform(-0.02, 0.02)))
                changed = True
        if changed:
            db.execute(
                "UPDATE npc_decision_state SET variables=?, last_updated=? WHERE npc_id=?",
                (json.dumps(variables), now, row["npc_id"]),
            )


def _mutate_population(db) -> Dict[str, int]:
    """Probabilistic birth/death per tick with FK-safe newborn locations."""
    npc_count = db.execute(
        "SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'"
    ).fetchone()[0]
    if npc_count < 2:
        return {"births": 0, "deaths": 0}

    now = time.time()
    birth_attempts = _poisson(npc_count * 0.0005)
    death_attempts = _poisson(npc_count * 0.00045)

    valid_locs = {r[0] for r in db.execute("SELECT id FROM locations").fetchall()}
    fallback = next(iter(valid_locs), None)

    # Type distribution from active population.
    type_counts = {}
    for row in db.execute(
        "SELECT json_extract(properties, '$.npc_type') AS t, COUNT(*) AS c "
        "FROM agents WHERE type='npc' AND state='active' GROUP BY 1"
    ).fetchall():
        if row[0]:
            type_counts[row[0]] = row[1]
    if type_counts:
        total_typed = sum(type_counts.values()) or 1
        types = list(type_counts.keys())
        weights = [type_counts[t] / total_typed for t in types]
    else:
        types = ["human"]
        weights = [1.0]

    from decision_state import BASE_STATE, GLIM_BASE

    births = 0
    for _ in range(birth_attempts):
        parent = db.execute(
            "SELECT id, location_id FROM agents WHERE type='npc' AND state='active' "
            "AND location_id IS NOT NULL ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        if not parent:
            continue
        loc = parent["location_id"] if parent["location_id"] in valid_locs else fallback
        if not loc:
            continue
        npc_type = random.choices(types, weights=weights, k=1)[0]
        new_id = f"b_{int(now * 1_000_000):012d}_{random.randint(0, 999999):06d}"
        try:
            db.execute(
                "INSERT INTO agents (id, name, type, location_id, state, properties, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (new_id, f"Child_{int(now)}_{births:04d}", "npc", loc, "active",
                 json.dumps({"npc_type": npc_type, "occupation": "child", "parent": parent["id"]}), now, now),
            )
            base = GLIM_BASE.copy() if npc_type == "glim" else BASE_STATE.copy()
            db.execute(
                "INSERT OR IGNORE INTO npc_decision_state (npc_id, variables, last_updated) VALUES (?,?,?)",
                (new_id, json.dumps(base), now),
            )
            births += 1
        except Exception:
            pass

    fk_tables = [
        "npc_decision_state", "npc_departures", "npc_schedules", "npc_relationships",
        "npc_actions", "agent_inventory", "trade_log", "faction_members",
    ]
    deaths = 0
    for _ in range(death_attempts):
        victim = db.execute(
            "SELECT id FROM agents WHERE type='npc' AND state='active' ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        if not victim:
            continue
        vid = victim["id"]
        for table in fk_tables:
            for col in ("npc_id", "npc_a", "npc_b", "agent_id", "buyer_id", "seller_id"):
                try:
                    db.execute(f"DELETE FROM {table} WHERE {col} = ?", (vid,))
                except Exception:
                    pass
        try:
            db.execute("DELETE FROM agents WHERE id = ?", (vid,))
            deaths += 1
        except Exception:
            pass
    return {"births": births, "deaths": deaths}


def run_world_tick(world_id: str, db_path: str, src_dir: str, tick_number: int, tick_start: float) -> Tuple[dict, float]:
    """Run one accelerated tick for one world. Returns (result, duration_seconds)."""
    src = Path(src_dir)
    sys.path.insert(0, str(src))

    import world_state
    world_state.DB_PATH = Path(db_path)

    db = world_state.get_db(Path(db_path))
    db.row_factory = sqlite3.Row

    try:
        _drift_decision_states(db)
        pop_delta = _mutate_population(db)
        from simulation import tick
        tick._tick_start_ts = tick_start
        result = tick(db, hours=24.0)
        if isinstance(result, dict):
            result["population_delta"] = pop_delta
        db.commit()
        duration = time.time() - tick_start
        return result, duration
    except Exception as e:
        db.rollback()
        return {"error": str(e), "world": world_id, "tick": tick_number}, time.time() - tick_start
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════
# SNAPSHOT
# ═══════════════════════════════════════════════════════════════════

def save_snapshot(out_dir: Path, worlds: List[str], world_dbs: Dict[str, str],
                  tick_num: int, sim_year: float, final: bool = False):
    """Save world state snapshot."""
    snap = {"tick": tick_num, "sim_year": round(sim_year, 1), "timestamp": time.time(), "worlds": {}}

    for w in worlds:
        try:
            db = sqlite3.connect(world_dbs[w])
            db.row_factory = sqlite3.Row

            pop = db.execute("SELECT COUNT(*) as c FROM agents WHERE type='npc' AND state='active'").fetchone()["c"]

            types = {}
            for t in ["human", "thren", "vorn", "glim"]:
                tc = db.execute("SELECT COUNT(*) FROM agents a WHERE a.type='npc' AND a.state='active' AND json_extract(a.properties, '$.npc_type') = ?", (t,)).fetchone()
                types[t] = tc[0] if tc else 0

            active = db.execute("SELECT COUNT(*) FROM factions WHERE status NOT IN ('dissolved','sovereign')").fetchone()[0]
            at_war = db.execute("SELECT COUNT(*) FROM factions WHERE status='war'").fetchone()[0]
            integrated = db.execute("SELECT COUNT(*) FROM factions WHERE status='integrated'").fetchone()[0]
            discoveries = db.execute("SELECT COUNT(*) FROM discoveries").fetchone()[0]
            great = db.execute("SELECT COUNT(*) FROM great_persons").fetchone()[0]
            treaties = db.execute("SELECT COUNT(*) FROM peace_treaties WHERE broken=0").fetchone()[0]
            migrations = db.execute("SELECT COUNT(*) FROM cross_world_movements").fetchone()[0]

            wt = db.execute("SELECT year, month, day, season, time_of_day FROM world_time WHERE id=1").fetchone()
            wt_dict = {"year": wt["year"], "month": wt["month"], "day": wt["day"],
                       "season": wt["season"], "time_of_day": wt["time_of_day"]} if wt else {}

            snap["worlds"][w] = {
                "population": pop, "types": types,
                "factions_active": active, "factions_at_war": at_war, "factions_integrated": integrated,
                "discoveries": discoveries, "great_persons": great, "active_treaties": treaties,
                "migrations": migrations, "world_time": wt_dict,
            }
            db.close()
        except Exception as e:
            snap["worlds"][w] = {"error": str(e)}

    suffix = "final" if final else f"tick_{tick_num:07d}"
    with open(out_dir / f"snapshot_{suffix}.json", "w") as f:
        json.dump(snap, f, indent=2)
    return snap


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def speed_run(worlds: List[str], sim_years: int, src_dir: str, output_dir: str = "output",
              npc_count: int = DEFAULT_NPC, log_interval: int = 50):
    """Run accelerated simulation."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    world_dbs = {}
    src = Path(src_dir)

    print("=" * 60)
    print(f"AURELIA SPEED RUN")
    print(f"  Worlds: {worlds}")
    print(f"  Sim-years: {sim_years} ({sim_years * TICKS_PER_YEAR:,} ticks)")
    print(f"  NPCs/world: {npc_count} (total: {npc_count * len(worlds):,})")
    print(f"  Output: {out}")
    print("=" * 60)

    # Phase 1: Setup
    print("\n── SETUP ──")
    t0 = time.time()
    for world_id in worlds:
        db_path = str(out / f"{world_id}.db")
        setup_world(world_id, db_path, src_dir, npc_count)
        world_dbs[world_id] = db_path
    setup_time = time.time() - t0
    print(f"  Setup: {setup_time:.0f}s")

    # Phase 2: Speed run
    total_ticks = sim_years * TICKS_PER_YEAR
    print(f"\n── RUN ({sim_years} sim-years, {total_ticks:,} ticks) ──")
    t0 = time.time()
    tick_times: List[float] = []
    yearly_events: Dict[str, Dict[str, Any]] = {}

    for tick_num in range(1, total_ticks + 1):
        tick_start = time.time()

        for world_id in worlds:
            run_world_tick(world_id, world_dbs[world_id], src_dir, tick_num, tick_start)

        tick_times.append(time.time() - tick_start)

        if tick_num % log_interval == 0 or tick_num == 1:
            elapsed = time.time() - t0
            avg_ms = sum(tick_times[-min(log_interval, len(tick_times)):]) / min(log_interval, len(tick_times)) * 1000
            sim_yr = tick_num / TICKS_PER_YEAR
            remaining = total_ticks - tick_num
            eta_sec = remaining * (sum(tick_times[-min(50, len(tick_times)):]) / min(50, len(tick_times)))
            eta = f"{eta_sec/60:.0f}m" if eta_sec < 3600 else f"{eta_sec/3600:.1f}h"

            # Quick stats
            pop_total = 0
            fac_total = 0
            for w in worlds:
                db = sqlite3.connect(world_dbs[w])
                pop_total += db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
                fac_total += db.execute("SELECT COUNT(*) FROM factions WHERE status NOT IN ('dissolved','sovereign')").fetchone()[0]
                db.close()

            print(f"  T{tick_num:7d} Yr{sim_yr:5.0f} | {avg_ms:5.0f}ms | pop:{pop_total:6,d} fac:{fac_total:3d} | ETA:{eta}")

        # Record per-year summaries for post-hoc batch chronicles.
        if tick_num % TICKS_PER_YEAR == 0:
            year = tick_num // TICKS_PER_YEAR
            snap = save_snapshot(out, worlds, world_dbs, tick_num, tick_num / TICKS_PER_YEAR, final=False) if year % 10 == 0 else None
            yearly_events[str(year)] = {}
            for w in worlds:
                db = sqlite3.connect(world_dbs[w])
                db.row_factory = sqlite3.Row
                yearly_events[str(year)][w] = {
                    "population": db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0],
                    "births": db.execute("SELECT COUNT(*) FROM agents WHERE name LIKE 'Child_%'").fetchone()[0],
                    "factions": db.execute("SELECT COUNT(*) FROM factions WHERE status NOT IN ('dissolved','sovereign')").fetchone()[0],
                    "discoveries": db.execute("SELECT COUNT(*) FROM discoveries").fetchone()[0],
                    "great_persons": db.execute("SELECT COUNT(*) FROM great_persons").fetchone()[0],
                    "migrations": db.execute("SELECT COUNT(*) FROM cross_world_movements").fetchone()[0],
                }
                db.close()

    # Done
    total_time = time.time() - t0
    avg_ms = sum(tick_times) / len(tick_times) * 1000

    print(f"\n── DONE ──")
    print(f"  Ticks: {total_ticks:,}")
    print(f"  Time: {total_time/60:.0f}m {total_time%60:.0f}s ({total_time/3600:.1f}h)")
    print(f"  Avg: {avg_ms:.0f}ms/tick")

    # Save accumulated yearly summaries for batch chronicle generation.
    with open(out / "yearly_events.json", "w") as f:
        json.dump(yearly_events, f, indent=2)

    # Final snapshot
    final = save_snapshot(out, worlds, world_dbs, total_ticks, sim_years, final=True)

    print(f"\n── FINAL STATE (Year {sim_years}) ──")
    for w in worlds:
        ws = final["worlds"].get(w, {})
        if "error" in ws:
            print(f"  {w}: ERROR - {ws['error']}")
        else:
            print(f"  {w}: pop={ws.get('population',0):,} factions={ws['factions_active']} "
                  f"war={ws['factions_at_war']} integrated={ws['factions_integrated']} "
                  f"discoveries={ws['discoveries']} great={ws['great_persons']}")
    print(f"\n  Output: {out}/")
    print(f"  Snapshots: {len(list(out.glob('snapshot_*.json')))} files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=200)
    parser.add_argument("--worlds", type=str, default="solara,valdris,mirithane,arkos,verge")
    parser.add_argument("--npcs", type=int, default=DEFAULT_NPC)
    parser.add_argument("--output", type=str, default="output")
    parser.add_argument("--src-dir", type=str, default="src")
    parser.add_argument("--log-interval", type=int, default=50)
    parser.add_argument("--llm-api-key", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--llm-base-url", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--llm-model", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--llm-chronicles", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--llm-daily", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--llm-local", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--llm-model-path", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--llm-n-gpu-layers", type=int, default=-1, help=argparse.SUPPRESS)
    args = parser.parse_args()

    worlds = [w.strip() for w in args.worlds.split(",")]
    speed_run(worlds, args.years, args.src_dir, args.output, args.npcs, args.log_interval)
