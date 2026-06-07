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
SPEEDRUN_DB = "/tmp/aurelia_run/output/{w}.db"


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
    paths = [DAEMON_DB.format(w=world_id), SPEEDRUN_DB.format(w=world_id)]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def get_world_ident(db):
    """Read world_registry handling 4-col (factory JSON blob) and 10-col schemas."""
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
        pop = db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        s, b = call("POST", "/aurelia/worlds", {
            "world_id": w,
            "name": ident.get("name", w.title()),
            "current_year": time_row["year"] if time_row else 2126,
            "population_count": pop,
            "species_breakdown": {"human": 0, "thren": 0, "vorn": 0, "glim": 0},
        })
        print(f"  {w}: {s}")
        db.close()


def push_yearly(world_id, db):
    ticks = db.execute(
        "SELECT world_year, COUNT(*) as ct FROM tick_log "
        "WHERE world_year IS NOT NULL GROUP BY world_year ORDER BY world_year"
    ).fetchall()
    pushed = 0
    for year, tc in ticks:
        pop = db.execute("SELECT COUNT(*) FROM agents WHERE state='active'").fetchone()[0]
        s, b = call("POST", f"/aurelia/worlds/{world_id}/yearly", {
            "year": int(year), "population_count": pop or 0,
            "births": 0, "deaths": 0,
            "immigration": 0, "emigration": 0,
            "tick_count": tc, "notable_events": [],
            "faction_count": 0, "settlement_count": 0,
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


def push_all():
    print(f"Pushing to {BASE_URL}\n")
    register_worlds()
    print()
    totals = {"yearly": 0, "discoveries": 0, "great_persons": 0, "fed_events": 0}
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
        print(f"  {w}: yearly={y} discoveries={d} great_persons={g} fed_events={f}")
        totals["yearly"] += y
        totals["discoveries"] += d
        totals["great_persons"] += g
        totals["fed_events"] += f
        db.close()
    print(f"\nTotals: {json.dumps(totals)}")
    s, b = call("GET", "/aurelia/dashboard")
    print(f"\nDashboard: {json.dumps(b)[:300]}")
    return totals


if __name__ == "__main__":
    push_all()
