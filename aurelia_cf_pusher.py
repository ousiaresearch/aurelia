#!/usr/bin/env python3
"""
aurelia_cf_pusher.py — Push live Aurelia daemon state to Cloudflare D1+R2.
Reads per-world SQLite DBs, POSTs to hermes-state-worker.plntrprotocol.workers.dev.
Works with both live daemon DBs and speed_run output DBs.
"""
import os, sys, json, sqlite3
import urllib.request

BASE_URL = "https://hermes-state-worker.plntrprotocol.workers.dev"
SECRET_FILE = os.path.expanduser("~/.hermes/profiles/palantir/cf-worker/.secret")
WORLDS = ["solara", "arkos", "mirithane", "valdris", "verge"]
DAEMON_DB = os.path.expanduser("~/.hermes/agents/{w}/aurelia-world/world/world.db")
CAUSALRUN_DB = "/tmp/aurelia-causal-run/output/{w}.db"
PHASE8_DB = "/tmp/aurelia-phase8-50y/{w}.db"
PHASE8_SUMMARY = "/tmp/aurelia-phase8-50y/causal_summary.json"
SPEEDRUN_DB = "/tmp/aurelia-run/output/{w}.db"
SEQRUN_DB = "/tmp/aurelia-seq-run/output/{w}.db"
CAUSAL_SUMMARY = "/tmp/aurelia-causal-run/output/causal_summary.json"


def load_secret():
    with open(SECRET_FILE) as f:
        return f.read().strip()


def call(method, path, body=None):
    """Return (status_code, response_body)."""
    secret = load_secret()
    url = BASE_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"X-Hermes-Secret": secret,
                                          "User-Agent": "Aurelia-Runner/2.0"})
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status, json.loads(resp.read())
    except urllib.request.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"error": str(e)}


def find_db(world_id):
    # Prefer phase8, then causal-run, then seq-run, then speed-run, then daemon (freshest first)
    paths = [
        PHASE8_DB.format(w=world_id),
        CAUSALRUN_DB.format(w=world_id),
        SEQRUN_DB.format(w=world_id),
        SPEEDRUN_DB.format(w=world_id),
        DAEMON_DB.format(w=world_id),
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def table_exists(db, table_name):
    return db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    ).fetchone() is not None


def count_table(db, table_name, where_clause=""):
    """Safe count — returns 0 if table missing or empty."""
    try:
        return db.execute(f"SELECT COUNT(*) FROM {table_name} {where_clause}").fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def count_npcs(db):
    """Count NPCs: prefer npc_decision_state, fall back to agents."""
    n = count_table(db, "npc_decision_state")
    if n > 0:
        return n
    n = count_table(db, "agents")
    if n <= 1:
        return 0  # Just the world registry agent
    return n


def get_world_ident(db):
    """Read world_registry handling 4-col (factory JSON blob) and 10-col schemas."""
    if not table_exists(db, "world_registry"):
        return {}
    row = db.execute("SELECT * FROM world_registry LIMIT 1").fetchone()
    if not row:
        return {}
    cols = [c[1] for c in db.execute("PRAGMA table_info(world_registry)")]
    if "data" in cols:
        try:
            return json.loads(row["data"]) if isinstance(row["data"], str) else dict(row["data"])
        except Exception:
            return {}
    return {"world_id": row["world_id"], "name": row["name"] or row["world_id"]}


def load_causal_world_summary(world_id):
    """Return final living population/faction totals from causal_summary.json, if present."""
    if not os.path.exists(CAUSAL_SUMMARY):
        return None
    try:
        with open(CAUSAL_SUMMARY) as f:
            summary = json.load(f)
        world = (summary.get("worlds") or {}).get(world_id)
        return world if isinstance(world, dict) else None
    except Exception:
        return None


def register_worlds():
    print("=== Register Worlds ===")
    for w in WORLDS:
        db_path = find_db(w)
        if not db_path:
            print(f"  {w}: no DB")
            continue
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        ident = get_world_ident(db)
        time_row = db.execute("SELECT year FROM world_time WHERE id=1").fetchone()
        causal_world = load_causal_world_summary(w)
        if causal_world:
            pop = int(causal_world.get("population", 0))
            faction_ct = int(causal_world.get("factions", 0))
        else:
            pop = count_npcs(db)
            faction_ct = count_table(db, "factions")
        settlement_ct = count_table(db, "settlements")
        s, b = call("POST", "/aurelia/worlds", {
            "world_id": w,
            "name": ident.get("name", w.title()),
            "current_year": time_row["year"] if time_row else 2126,
            "population_count": pop,
            "species_breakdown": {"human": 0, "thren": 0, "vorn": 0, "glim": 0},
            "faction_count": faction_ct,
            "settlement_count": settlement_ct,
        })
        print(f"  {w}: {s} (pop={pop} factions={faction_ct})")
        db.close()


def load_causal_reports(world_id):
    """Return causal yearly reports from the latest causal runner output."""
    if not os.path.exists(CAUSAL_SUMMARY):
        return []
    try:
        with open(CAUSAL_SUMMARY) as f:
            summary = json.load(f)
        return [r for r in summary.get("yearly_reports", []) if r.get("world_id") == world_id]
    except Exception:
        return []


def push_yearly(world_id, db):
    causal_reports = load_causal_reports(world_id)
    if causal_reports:
        pushed = 0
        for report in causal_reports:
            year = 2026 + int(report.get("year", 1)) - 1
            fac_count = sum(int(v) for v in report.get("factions", {}).values())
            notable = report.get("causal_highlights", [])[:10]
            s, b = call("POST", f"/aurelia/worlds/{world_id}/yearly", {
                "year": year,
                "population_count": int(report.get("population", 0)),
                "births": int(report.get("births", 0)),
                "deaths": int(report.get("deaths", 0)),
                "immigration": int(report.get("immigration", 0)),
                "emigration": int(report.get("emigration", 0)),
                "tick_count": 12,
                "notable_events": notable,
                "faction_count": fac_count,
                "settlement_count": count_table(db, "locations"),
            })
            if s in (200, 201):
                pushed += 1
        return pushed
    if not table_exists(db, "tick_log"):
        return 0
    ticks = db.execute(
        "SELECT world_year, COUNT(*) as ct FROM tick_log "
        "WHERE world_year IS NOT NULL GROUP BY world_year ORDER BY world_year"
    ).fetchall()
    if not ticks:
        # Fallback: push single snapshot from world_time
        time_row = db.execute("SELECT year, month FROM world_time WHERE id=1").fetchone()
        if not time_row:
            return 0
        pop = count_npcs(db)
        faction_ct = count_table(db, "factions")
        settlement_ct = count_table(db, "settlements")
        s, b = call("POST", f"/aurelia/worlds/{world_id}/yearly", {
            "year": int(time_row["year"]), "population_count": pop or 0,
            "births": 0, "deaths": 0,
            "immigration": 0, "emigration": 0,
            "tick_count": 0, "notable_events": [],
            "faction_count": faction_ct, "settlement_count": settlement_ct,
        })
        return 1 if s in (200, 201) else 0
    pushed = 0
    for year, tc in ticks:
        pop = count_npcs(db)
        faction_ct = count_table(db, "factions")
        settlement_ct = count_table(db, "settlements")
        s, b = call("POST", f"/aurelia/worlds/{world_id}/yearly", {
            "year": int(year), "population_count": pop or 0,
            "births": 0, "deaths": 0,
            "immigration": 0, "emigration": 0,
            "tick_count": tc, "notable_events": [],
            "faction_count": faction_ct, "settlement_count": settlement_ct,
        })
        if s in (200, 201):
            pushed += 1
    return pushed


def push_discoveries(world_id, db):
    try:
        discs = db.execute(
            "SELECT discovery_id, discovery_type, title, description, tick_number "
            "FROM discoveries LIMIT 50"
        ).fetchall()
    except sqlite3.OperationalError:
        return 0
    if not discs:
        return 0
    payload = []
    for did, dtype, title, desc, tick in discs:
        payload.append({
            "discovery_id": did, "discovery_type": dtype, "title": title,
            "description": desc or "", "tick_number": tick or 0,
            "sim_year": (tick or 0) // 360 + 2026,
        })
    s, b = call("POST", f"/aurelia/worlds/{world_id}/discoveries", {"discoveries": payload})
    return b.get("ingested", 0)


def push_great_persons(world_id, db):
    try:
        gps = db.execute(
            "SELECT npc_id, event_type, title, description, tick_number "
            "FROM great_persons LIMIT 50"
        ).fetchall()
    except sqlite3.OperationalError:
        return 0
    if not gps:
        return 0
    payload = []
    for nid, etype, title, desc, tick in gps:
        payload.append({
            "npc_id": nid, "event_type": etype, "title": title,
            "description": desc or "", "tick_number": tick or 0,
            "sim_year": (tick or 0) // 360 + 2026,
        })
    s, b = call("POST", f"/aurelia/worlds/{world_id}/great-persons", {"great_persons": payload})
    return b.get("ingested", 0)


def push_federation_events(world_id, db):
    try:
        feds = db.execute(
            "SELECT event_type, description, tick_number "
            "FROM federation_events_log LIMIT 50"
        ).fetchall()
    except sqlite3.OperationalError:
        return 0
    if not feds:
        return 0
    payload = []
    for etype, desc, tick in feds:
        payload.append({
            "event_type": etype, "world_id": world_id,
            "description": desc or "", "tick_number": tick or 0,
            "sim_year": (tick or 0) // 360 + 2026,
        })
    s, b = call("POST", "/aurelia/federation/events", {"events": payload})
    return b.get("ingested", 0)


def push_chronicles(world_id):
    """Upload chronicle .txt files to CF R2 — batched with concurrency."""
    import glob as _glob
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    
    chronicle_globs = [
        f"/tmp/aurelia-seq-run/output/chronicles/{world_id}_Y*.txt",
        f"/tmp/aurelia-run/output/chronicles/{world_id}_Y*.txt",
        f"{os.path.expanduser('~/.openclaw/workspace/aurelia-colab')}/output/chronicles/{world_id}_Y*.txt",
    ]
    files = []
    for pattern in chronicle_globs:
        for fpath in sorted(_glob.glob(pattern)):
            files.append(fpath)
    if not files:
        return 0
    
    pushed = [0]
    lock = threading.Lock()
    
    def upload_one(fpath):
        try:
            basename = os.path.basename(fpath)
            year_str = basename.split("_Y")[1].replace(".txt", "")
            year = int(year_str)
            with open(fpath, "r") as f:
                text = f.read()
            s, b = call("POST", f"/aurelia/worlds/{world_id}/chronicles?year={year}", {
                "text": text, "year": year, "filename": basename
            })
            if s in (200, 201):
                with lock:
                    pushed[0] += 1
                return True
        except Exception:
            pass
        return False
    
    with ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(upload_one, files))
    
    return pushed[0]


def push_all():
    print(f"Pushing to {BASE_URL}\n")
    register_worlds()
    print()
    totals = {"yearly": 0, "discoveries": 0, "great_persons": 0, "fed_events": 0, "chronicles": 0}
    for w in WORLDS:
        db_path = find_db(w)
        if not db_path:
            continue
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        y = push_yearly(w, db)
        d = push_discoveries(w, db)
        g = push_great_persons(w, db)
        f = push_federation_events(w, db)
        c = push_chronicles(w)
        print(f"  {w}: yearly={y} discoveries={d} great_persons={g} fed_events={f} chronicles={c}")
        totals["yearly"] += y
        totals["discoveries"] += d
        totals["great_persons"] += g
        totals["fed_events"] += f
        totals["chronicles"] += c
        db.close()
    print(f"\nTotals: {json.dumps(totals)}")
    s, b = call("GET", "/aurelia/dashboard")
    print(f"\nDashboard: {json.dumps(b)[:300]}")
    return totals


if __name__ == "__main__":
    push_all()
