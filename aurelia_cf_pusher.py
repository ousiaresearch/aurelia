#!/usr/bin/env python3
"""
aurelia_cf_pusher.py — Push live Aurelia daemon state to Cloudflare D1+R2.
Reads per-world SQLite DBs, POSTs to hermes-state-worker.plntrprotocol.workers.dev.
Works with both live daemon DBs and speed_run output DBs.
"""
import os, sys, json, sqlite3
import urllib.request
import urllib.error

BASE_URL = "https://hermes-state-worker.plntrprotocol.workers.dev"
SECRET_FILE = os.path.expanduser("~/.hermes/profiles/palantir/cf-worker/.secret")
WORLDS = ["solara", "arkos", "mirithane", "valdris", "verge"]
RUN_OUTPUT = os.environ.get("AURELIA_RUN_OUTPUT", "").strip()
RUN_ID = os.environ.get("AURELIA_RUN_ID", "").strip()
DAEMON_DB = os.path.expanduser("~/.hermes/agents/{w}/aurelia-world/world/world.db")
CAUSALRUN_DB = "/tmp/aurelia-causal-run/output/{w}.db"
PHASE8_DB = "/tmp/aurelia-phase8-50y/{w}.db"
PHASE8_SUMMARY = "/tmp/aurelia-phase8-50y/causal_summary.json"
PHASE9_DB = "/tmp/aurelia-phase9-50y-final/{w}.db"
PHASE9_SUMMARY = "/tmp/aurelia-phase9-50y-final/causal_summary.json"
PHASE10_DB = "/tmp/aurelia-phase10-50y/{w}.db"
PHASE10_SUMMARY = "/tmp/aurelia-phase10-50y/causal_summary.json"
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
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
        except Exception:
            body = ""
        if body and body.lstrip().startswith(("{", "[")):
            return e.code, json.loads(body)
        return e.code, {"_raw": body[:400], "_error": True}
    except urllib.error.URLError as e:
        return 0, {"_error": True, "_reason": str(e)}
    except json.JSONDecodeError as e:
        return 200, {"_error": True, "_decode": str(e)}

        return 0, {"error": str(e)}


def find_db(world_id):
    # Explicit run output wins, then phase outputs, then daemon fallback.
    paths = []
    if RUN_OUTPUT:
        paths.append(os.path.join(RUN_OUTPUT, f"{world_id}.db"))
    paths.extend([
        PHASE10_DB.format(w=world_id),
        PHASE9_DB.format(w=world_id),
        PHASE8_DB.format(w=world_id),
        CAUSALRUN_DB.format(w=world_id),
        SEQRUN_DB.format(w=world_id),
        SPEEDRUN_DB.format(w=world_id),
        DAEMON_DB.format(w=world_id),
    ])
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
    """Return final living population/faction totals from the newest causal summary."""
    for summary_path in summary_paths():
        if not os.path.exists(summary_path):
            continue
        try:
            with open(summary_path) as f:
                summary = json.load(f)
            world = (summary.get("worlds") or {}).get(world_id)
            if isinstance(world, dict):
                return world
        except Exception:
            continue
    return None


def summary_paths():
    paths = []
    if RUN_OUTPUT:
        paths.append(os.path.join(RUN_OUTPUT, "causal_summary.json"))
    paths.extend([PHASE10_SUMMARY, PHASE9_SUMMARY, PHASE8_SUMMARY, CAUSAL_SUMMARY])
    return paths


def latest_summary():
    for summary_path in summary_paths():
        if not os.path.exists(summary_path):
            continue
        try:
            with open(summary_path) as f:
                return summary_path, json.load(f)
        except Exception:
            continue
    return None, {}


def current_run_id(summary=None):
    if RUN_ID:
        return RUN_ID
    summary = summary or {}
    out = summary.get("output_dir") or RUN_OUTPUT or "aurelia-run"
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in os.path.basename(str(out).rstrip("/")))
    years = summary.get("years", 0)
    ticks = summary.get("ticks", 0)
    return f"{safe}-y{years}-t{ticks}"


def post_records(path, key, rows, batch_size=250):
    ingested = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        s, b = call("POST", path, {key: batch})
        if s not in (200, 201):
            print(f"    push failed {path}: {s} {b}")
            continue
        ingested += int(b.get("ingested", 0))
    return ingested


def rowdicts(rows):
    return [dict(r) for r in rows]


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
    """Return causal yearly reports from the latest selected causal runner output."""
    for summary_path in summary_paths():
        if not os.path.exists(summary_path):
            continue
        try:
            with open(summary_path) as f:
                summary = json.load(f)
            reports = [r for r in summary.get("yearly_reports", []) if r.get("world_id") == world_id]
            if reports:
                return reports
        except Exception:
            continue
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


def push_run_manifest(run_id, summary_path, summary):
    worlds = sorted((summary.get("worlds") or {}).keys()) or WORLDS
    payload = {
        "run_id": run_id,
        "label": os.path.basename(str(summary.get("output_dir") or RUN_OUTPUT or run_id).rstrip("/")),
        "seed": summary.get("seed", 0),
        "years": summary.get("years", 0),
        "ticks": summary.get("ticks", 0),
        "ticks_per_year": summary.get("ticks_per_year", 0),
        "worlds": worlds,
        "output_dir": summary.get("output_dir") or RUN_OUTPUT or "",
        "summary": {k: v for k, v in summary.items() if k != "yearly_reports"},
        "summary_path": summary_path,
    }
    s, b = call("POST", "/aurelia/runs", payload)
    return 1 if s in (200, 201) else 0


def push_causal_events(run_id, world_id, db, federation=False):
    if not table_exists(db, "causal_events"):
        return 0
    rows = rowdicts(db.execute("SELECT * FROM causal_events ORDER BY tick_number, event_id").fetchall())
    endpoint = f"/aurelia/runs/{run_id}/federation/causal-events" if federation else f"/aurelia/runs/{run_id}/worlds/{world_id}/causal-events"
    return post_records(endpoint, "causal_events", rows)


def push_causal_edges(run_id, world_id, db, federation=False):
    if not table_exists(db, "causal_edges"):
        return 0
    rows = rowdicts(db.execute(
        """
        SELECT e.parent_event_id, e.child_event_id, e.relation, e.weight,
               COALESCE(c.world_id, ?) AS world_id,
               COALESCE(c.tick_number, 0) AS tick_number,
               COALESCE(c.created_at, strftime('%s','now')) AS created_at
        FROM causal_edges e
        LEFT JOIN causal_events c ON c.event_id = e.child_event_id
        ORDER BY tick_number, parent_event_id, child_event_id
        """,
        (world_id,),
    ).fetchall())
    endpoint = f"/aurelia/runs/{run_id}/federation/causal-edges" if federation else f"/aurelia/runs/{run_id}/worlds/{world_id}/causal-edges"
    return post_records(endpoint, "causal_edges", rows)


def push_civilization_metrics(run_id, world_id, db):
    if not table_exists(db, "civilization_metrics"):
        return 0
    rows = rowdicts(db.execute("SELECT * FROM civilization_metrics ORDER BY tick_number").fetchall())
    return post_records(f"/aurelia/runs/{run_id}/worlds/{world_id}/metrics", "metrics", rows)


def push_federation_table(run_id, fed, table, endpoint_kind, payload_key):
    if not table_exists(fed, table):
        return 0
    order = "created_at" if table == "diplomatic_relations" else "tick_number"
    rows = rowdicts(fed.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall())
    return post_records(f"/aurelia/runs/{run_id}/federation/{endpoint_kind}", payload_key, rows)


def push_phase11_observability(run_id):
    totals = {
        "run_manifest": 0,
        "causal_events": 0,
        "causal_edges": 0,
        "metrics": 0,
        "movements": 0,
        "diffusion": 0,
        "diplomacy": 0,
    }
    summary_path, summary = latest_summary()
    if summary:
        totals["run_manifest"] = push_run_manifest(run_id, summary_path, summary)

    for w in WORLDS:
        db_path = find_db(w)
        if not db_path:
            continue
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        totals["causal_events"] += push_causal_events(run_id, w, db)
        totals["causal_edges"] += push_causal_edges(run_id, w, db)
        totals["metrics"] += push_civilization_metrics(run_id, w, db)
        db.close()

    fed_path = os.path.join(RUN_OUTPUT, "federation.db") if RUN_OUTPUT else None
    if fed_path and os.path.exists(fed_path):
        fed = sqlite3.connect(fed_path)
        fed.row_factory = sqlite3.Row
        totals["causal_events"] += push_causal_events(run_id, "federation", fed, federation=True)
        totals["causal_edges"] += push_causal_edges(run_id, "federation", fed, federation=True)
        totals["movements"] += push_federation_table(run_id, fed, "cross_world_movements", "movements", "movements")
        totals["diffusion"] += push_federation_table(run_id, fed, "diffusion_events", "diffusion", "diffusion")
        totals["diplomacy"] += push_federation_table(run_id, fed, "diplomatic_relations", "diplomacy", "diplomacy")
        fed.close()
    return totals


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
    summary_path, summary = latest_summary()
    run_id = current_run_id(summary)
    phase11 = push_phase11_observability(run_id)
    totals_report = {"legacy": totals, "phase11": phase11}
    print(f"  phase11[{run_id}]: {json.dumps(phase11, sort_keys=True)}")
    print(f"\nTotals: {json.dumps(totals_report)}")
    s, b = call("GET", "/aurelia/dashboard")
    print(f"\nDashboard: {json.dumps(b)[:300]}")
    return totals


if __name__ == "__main__":
    push_all()
