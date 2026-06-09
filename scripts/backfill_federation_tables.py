#!/usr/bin/env python3
"""Upload only cross_world_movements, diffusion_events, and diplomatic_relations for a run.

Used to backfill the federation-level causal tables when the full pusher
hits Cloudflare rate limits during parallel multi-run pushes.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.request
import urllib.error
from pathlib import Path

SECRET_FILE = os.path.expanduser("~/.hermes/profiles/palantir/cf-worker/.secret")
BASE_URL = "https://hermes-state-worker.plntrprotocol.workers.dev"
BATCH = 250


def call(path, body):
    secret = Path(SECRET_FILE).read_text().strip()
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode() if body is not None else None,
        method="POST",
        headers={"X-Hermes-Secret": secret, "User-Agent": "Aurelia-Backfill/1.0", "Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body_txt = e.read().decode()
        except Exception:
            body_txt = ""
        return e.code, {"_error": True, "_code": e.code, "_body": body_txt[:200]}
    except Exception as e:
        return 0, {"_error": True, "_reason": str(e)}


def post_records(path, key, rows):
    ingested = 0
    failed = 0
    last_error = None
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        s, b = call(path, {key: batch})
        if s in (200, 201):
            ingested += len(batch)
        else:
            failed += len(batch)
            last_error = b
    return ingested, failed, last_error


def rowdicts(rows):
    return [dict(r) for r in rows]


def push_federation_table(run_id, fed, table, endpoint_kind, payload_key, order_col="tick_number"):
    if not table_exists(fed, table):
        return 0, 0, None
    cols = {r[1] for r in fed.execute(f"PRAGMA table_info({table})").fetchall()}
    if order_col not in cols:
        order_col = next((c for c in ("created_at", "id") if c in cols), next(iter(cols)))
    rows = rowdicts(fed.execute(f"SELECT * FROM {table} ORDER BY {order_col}").fetchall())
    return post_records(f"/aurelia/runs/{run_id}/federation/{endpoint_kind}", payload_key, rows)


def table_exists(db, table):
    return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def main():
    run_dir = os.environ.get("AURELIA_RUN_OUTPUT")
    run_id = os.environ.get("AURELIA_RUN_ID")
    if not run_dir or not run_id:
        print("set AURELIA_RUN_OUTPUT and AURELIA_RUN_ID", file=sys.stderr)
        return 2
    fed_path = Path(run_dir) / "federation.db"
    if not fed_path.exists():
        print(f"missing {fed_path}", file=sys.stderr)
        return 2
    fed = sqlite3.connect(fed_path)
    fed.row_factory = sqlite3.Row
    out = {}
    for table, kind, key in [
        ("cross_world_movements", "movements", "movements"),
        ("diffusion_events", "diffusion", "diffusion"),
        ("diplomatic_relations", "diplomacy", "diplomacy"),
    ]:
        ingested, failed, last_error = push_federation_table(run_id, fed, table, kind, key)
        out[table] = (ingested, failed)
        print(f"  {table}: ingested={ingested} failed={failed}")
        if failed and last_error:
            print(f"    last_error: {json.dumps(last_error)[:300]}")
    fed.close()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
