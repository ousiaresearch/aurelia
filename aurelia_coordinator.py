#!/usr/bin/env python3
"""
aurelia_coordinator.py — Aurelia Federation Coordinator.

Central hub for all Aurelian country-states:
- Receives heartbeats from world daemons
- Tracks world health (online/offline/degraded)
- Serves a dark dashboard at http://127.0.0.1:9001
- Manages cross-world currency exchange rates
- Provides federation API for daemons and external tools

Run: python3 aurelia_coordinator.py
"""

import http.server
import json
import time
import os
import sys
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from aurelia_diplomacy import BASELINE_RELATIONS, apply_relation_deltas, classify_diplomatic_event

PORT = 9001
AGENTS_HOME = Path("/Users/johann/.hermes/agents")
AURELIA_ROOT = Path("/Users/johann/aurelia")
COORDINATOR_DB = AURELIA_ROOT / "coordinator.db"

# ── World Registry (in-memory + persisted) ────────────────────────────

class CoordinatorState:
    def __init__(self):
        self.worlds = {}
        self.exchange_rates = {}
        self.lock = threading.Lock()
        self._npc_cache = {}
        self._npc_cache_ts = 0
        self._currency_cache = {}
        self._currency_cache_ts = 0
        self.init_db()

    def get_npc_stats_cached(self, max_age=60):
        now = time.time()
        if now - self._npc_cache_ts > max_age:
            self._npc_cache = self._load_world_npc_stats()
            self._npc_cache_ts = now
        return self._npc_cache

    def get_currency_cached(self, max_age=60):
        now = time.time()
        if now - self._currency_cache_ts > max_age:
            self._currency_cache = self._load_currency_data()
            self._currency_cache_ts = now
        return self._currency_cache

    def record_federation_events(self, world_id, events):
        """Persist cross-world events from a country daemon, deduped by event_id."""
        if not isinstance(events, list):
            return {"accepted": 0, "duplicates": 0, "error": "events must be a list"}

        accepted = 0
        duplicates = 0
        received_at = time.time()
        db = sqlite3.connect(str(COORDINATOR_DB), timeout=5)
        try:
            for event in events:
                if not isinstance(event, dict):
                    continue
                event_id = event.get("event_id")
                event_world_id = event.get("world_id") or world_id
                event_type = event.get("event_type") or event.get("type") or "event"
                if not event_id:
                    event_id = f"{event_world_id}:{event_type}:{event.get('created_at', received_at)}:{accepted + duplicates}"

                try:
                    db.execute(
                        """
                        INSERT INTO federation_events (
                            event_id, world_id, event_type, category, title, description,
                            importance, actor_ids, tags, payload, world_time, created_at, received_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event_id,
                            event_world_id,
                            event_type,
                            event.get("category", ""),
                            event.get("title", ""),
                            event.get("description", ""),
                            float(event.get("importance", 0.0) or 0.0),
                            json.dumps(event.get("actor_ids", [])),
                            json.dumps(event.get("tags", [])),
                            json.dumps(event.get("payload", {})),
                            json.dumps(event.get("world_time", {})),
                            event.get("created_at", received_at),
                            received_at,
                        ),
                    )
                    accepted += 1
                except sqlite3.IntegrityError:
                    duplicates += 1
            db.commit()
        finally:
            db.close()
        return {"accepted": accepted, "duplicates": duplicates}

    def ingest_federation_events(self, world_id, events):
        """Record federation events and immediately process diplomacy triggers."""
        result = self.record_federation_events(world_id, events)
        diplomacy = self.process_diplomacy_events(limit=max(100, len(events) * 4 if isinstance(events, list) else 100))

        # Persist growth snapshot every event batch
        try:
            snapshot = self.build_growth_snapshot()
            snap_db = sqlite3.connect(str(COORDINATOR_DB), timeout=5)
            snap_db.execute(
                "INSERT OR REPLACE INTO growth_snapshots (snapshot_type, world_id, data, created_at, tick_number) VALUES (?, ?, ?, ?, ?)",
                ("growth", None, json.dumps(snapshot), snapshot["ts"], snapshot.get("tick_number", 0)),
            )
            snap_db.commit()
            snap_db.close()
        except Exception:
            pass  # Don't let snapshot failure break event ingestion

        return {**result, "diplomacy": diplomacy}

    def get_federation_events(self, limit=50, world_id=None, category=None, event_type=None):
        """Return recent federation events with JSON fields decoded."""
        try:
            limit = max(1, min(int(limit), 200))
        except (TypeError, ValueError):
            limit = 50

        where = []
        params = []
        if world_id:
            where.append("world_id = ?")
            params.append(world_id)
        if category:
            where.append("category = ?")
            params.append(category)
        if event_type:
            where.append("event_type = ?")
            params.append(event_type)

        sql = "SELECT * FROM federation_events"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY received_at DESC, id DESC LIMIT ?"
        params.append(limit)

        db = sqlite3.connect(str(COORDINATOR_DB), timeout=5)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(sql, params).fetchall()
        finally:
            db.close()

        decoded = []
        for row in rows:
            item = dict(row)
            for key, default in [("actor_ids", []), ("tags", []), ("payload", {}), ("world_time", {})]:
                try:
                    item[key] = json.loads(item.get(key) or json.dumps(default))
                except Exception:
                    item[key] = default
            decoded.append(item)
        return decoded

    def _decode_event_row(self, row):
        item = dict(row)
        for key, default in [("actor_ids", []), ("tags", []), ("payload", {}), ("world_time", {})]:
            try:
                item[key] = json.loads(item.get(key) or json.dumps(default))
            except Exception:
                item[key] = default
        return item

    def _seed_diplomatic_relations(self, db):
        now = time.time()
        for relation_key, baseline in BASELINE_RELATIONS.items():
            country_a, country_b = relation_key.split("|")
            db.execute(
                """
                INSERT OR IGNORE INTO diplomatic_relations (
                    relation_key, country_a, country_b, status,
                    baseline_trust, baseline_tension, baseline_cooperation, baseline_trade,
                    trust, tension, cooperation, trade, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relation_key,
                    country_a,
                    country_b,
                    baseline.get("status", ""),
                    baseline.get("trust", 0.5),
                    baseline.get("tension", 0.3),
                    baseline.get("cooperation", 0.4),
                    baseline.get("trade", 0.2),
                    baseline.get("trust", 0.5),
                    baseline.get("tension", 0.3),
                    baseline.get("cooperation", 0.4),
                    baseline.get("trade", 0.2),
                    baseline.get("notes", ""),
                    now,
                ),
            )

    def _unprocessed_federation_events(self, db, limit=100):
        db.row_factory = sqlite3.Row
        rows = db.execute(
            """
            SELECT fe.*
            FROM federation_events fe
            LEFT JOIN diplomatic_event_reviews der ON der.source_event_id = fe.event_id
            WHERE der.source_event_id IS NULL
            ORDER BY fe.id ASC
            LIMIT ?
            """,
            (max(1, min(int(limit), 500)),),
        ).fetchall()
        return [self._decode_event_row(row) for row in rows]

    def _apply_relation_delta(self, db, relation_key, deltas):
        row = db.execute("SELECT * FROM diplomatic_relations WHERE relation_key=?", (relation_key,)).fetchone()
        if not row:
            country_a, country_b = relation_key.split("|")
            now = time.time()
            db.execute(
                """
                INSERT INTO diplomatic_relations (
                    relation_key, country_a, country_b, status,
                    baseline_trust, baseline_tension, baseline_cooperation, baseline_trade,
                    trust, tension, cooperation, trade, notes, updated_at
                ) VALUES (?, ?, ?, 'unmapped', 0.5, 0.3, 0.3, 0.1, 0.5, 0.3, 0.3, 0.1, '', ?)
                """,
                (relation_key, country_a, country_b, now),
            )
            row = db.execute("SELECT * FROM diplomatic_relations WHERE relation_key=?", (relation_key,)).fetchone()
        current = dict(row)
        updated = apply_relation_deltas(current, deltas)
        db.execute(
            """
            UPDATE diplomatic_relations
            SET trust=?, tension=?, cooperation=?, trade=?, updated_at=?
            WHERE relation_key=?
            """,
            (updated["trust"], updated["tension"], updated["cooperation"], updated["trade"], time.time(), relation_key),
        )

    def process_diplomacy_events(self, limit=100):
        """Convert unprocessed federation events into diplomatic incidents and relation changes."""
        db = sqlite3.connect(str(COORDINATOR_DB), timeout=5)
        db.row_factory = sqlite3.Row
        incidents_created = 0
        relations_updated = 0
        try:
            self._seed_diplomatic_relations(db)
            events = self._unprocessed_federation_events(db, limit)
            for event in events:
                incident = classify_diplomatic_event(event)
                if not incident:
                    db.execute(
                        "INSERT OR IGNORE INTO diplomatic_event_reviews (source_event_id, incident_id, reviewed_at) VALUES (?, NULL, ?)",
                        (event.get("event_id"), time.time()),
                    )
                    continue
                try:
                    db.execute(
                        """
                        INSERT INTO diplomatic_incidents (
                            incident_id, source_event_id, source_world, category, title,
                            description, severity, affected_worlds, relation_deltas,
                            payload, world_time, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            incident["incident_id"],
                            incident["source_event_id"],
                            incident["source_world"],
                            incident["category"],
                            incident["title"],
                            incident["description"],
                            incident["severity"],
                            json.dumps(incident.get("affected_worlds", [])),
                            json.dumps(incident.get("relation_deltas", {})),
                            json.dumps(incident.get("payload", {})),
                            json.dumps(incident.get("world_time", {})),
                            time.time(),
                        ),
                    )
                except sqlite3.IntegrityError:
                    continue
                incidents_created += 1
                for relation_key, deltas in (incident.get("relation_deltas") or {}).items():
                    self._apply_relation_delta(db, relation_key, deltas)
                    relations_updated += 1
                db.execute(
                    "INSERT OR IGNORE INTO diplomatic_event_reviews (source_event_id, incident_id, reviewed_at) VALUES (?, ?, ?)",
                    (incident["source_event_id"], incident["incident_id"], time.time()),
                )
            db.commit()
            return {"events_scanned": len(events), "incidents_created": incidents_created, "relations_updated": relations_updated}
        finally:
            db.close()

    def build_growth_snapshot(self):
        """Return a compact growth snapshot for the growth dashboard."""
        now = time.time()
        npc_stats = self.get_npc_stats_cached()
        currency = self.get_currency_cached()

        # Per-world population by type
        populations = {}
        for world_id, stats in npc_stats.items():
            type_counts = stats.get("types", {})
            pops = {}
            for npc_type in ["human", "thren", "vorn", "glim"]:
                pops[npc_type] = type_counts.get(npc_type, 0)
            pops["total"] = stats.get("total", 0)
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
            "faction_counts": self._load_faction_counts(),
            "conflict_state": self._load_conflict_state(),
            "sovereignty": self._load_sovereignty_state(),
        }

    def _load_faction_counts(self):
        """Query each world DB for faction counts."""
        counts = {}
        for country in ["solara", "valdris", "mirithane", "arkos", "verge"]:
            db_path = AGENTS_HOME / country / "aurelia-world" / "world" / "world.db"
            if not db_path.exists():
                counts[country] = {"active": 0, "total": 0}
                continue
            try:
                wdb = sqlite3.connect(str(db_path), timeout=2)
                wdb.row_factory = sqlite3.Row
                total = wdb.execute("SELECT COUNT(*) FROM factions").fetchone()[0]
                active = wdb.execute(
                    "SELECT COUNT(*) FROM factions WHERE status NOT IN ('dissolved', 'sovereign')"
                ).fetchone()[0]
                wdb.close()
                counts[country] = {"active": active, "total": total}
            except Exception:
                counts[country] = {"active": 0, "total": 0}
        return counts

    def _load_conflict_state(self):
        """Query each world DB for conflict intensity."""
        LADDER_IDX = {"dormant": 0, "grievance": 1, "organization": 2, "ultimatum": 3, "skirmish": 4, "armed_conflict": 5, "war": 6}
        state = {}
        for country in ["solara", "valdris", "mirithane", "arkos", "verge"]:
            db_path = AGENTS_HOME / country / "aurelia-world" / "world" / "world.db"
            if not db_path.exists():
                state[country] = {"active_conflicts": 0, "max_intensity": 0, "at_war": 0, "total_faction_members": 0}
                continue
            try:
                wdb = sqlite3.connect(str(db_path), timeout=2)
                wdb.row_factory = sqlite3.Row
                rows = wdb.execute(
                    "SELECT status, member_count FROM factions WHERE status NOT IN ('dissolved', 'sovereign')"
                ).fetchall()
                active = len(rows)
                at_war = sum(1 for r in rows if r["status"] == "war")
                max_intensity = max(
                    (LADDER_IDX.get(r["status"], 0) / 6.0 for r in rows),
                    default=0.0
                )
                total_members = sum(r["member_count"] or 0 for r in rows)
                wdb.close()
                state[country] = {
                    "active_conflicts": active,
                    "max_intensity": round(max_intensity, 3),
                    "at_war": at_war,
                    "total_faction_members": total_members,
                }
            except Exception:
                state[country] = {"active_conflicts": 0, "max_intensity": 0, "at_war": 0, "total_faction_members": 0}
        return state

    def _load_sovereignty_state(self):
        """Query each world DB for sovereignty candidates and new countries."""
        state = {}
        try:
            from src_template.sovereignty import is_secession_cascade_active, get_cascade_ticks_remaining
            cascade_active = is_secession_cascade_active()
            cascade_remaining = get_cascade_ticks_remaining()
        except Exception:
            cascade_active = False
            cascade_remaining = 0

        new_countries = []
        for country in ["solara", "valdris", "mirithane", "arkos", "verge"]:
            db_path = AGENTS_HOME / country / "aurelia-world" / "world" / "world.db"
            if not db_path.exists():
                continue
            try:
                wdb = sqlite3.connect(str(db_path), timeout=2)
                wdb.row_factory = sqlite3.Row
                # Sovereignty events
                secession_rows = wdb.execute(
                    "SELECT * FROM sovereignty_events WHERE event_type = 'secession' ORDER BY id DESC LIMIT 5"
                ).fetchall()
                for row in secession_rows:
                    try:
                        recognized = json.loads(row["recognized_by"]) if isinstance(row["recognized_by"], str) else row["recognized_by"]
                    except Exception:
                        recognized = []
                    new_countries.append({
                        "name": row["new_country_name"],
                        "parent": country,
                        "faction_id": row["faction_id"],
                        "recognized_by": recognized,
                        "population": row["member_count"],
                        "tick": row["tick_number"],
                    })

                # Declaring factions
                declaring = wdb.execute(
                    "SELECT faction_id, name, member_count, influence FROM factions WHERE status = 'declaring'"
                ).fetchall()
                candidates = [
                    {"faction_id": r["faction_id"], "name": r["name"],
                     "members": r["member_count"], "influence": r["influence"]}
                    for r in declaring
                ]
                wdb.close()
                if candidates:
                    if country not in state:
                        state[country] = {}
                    state[country]["candidates"] = candidates
            except Exception:
                pass

        return {
            "new_countries": new_countries,
            "total_secessions": len(new_countries),
            "cascade_active": cascade_active,
            "cascade_ticks_remaining": cascade_remaining,
            "per_world_candidates": state,
        }

    def get_diplomatic_relations(self):
        db = sqlite3.connect(str(COORDINATOR_DB), timeout=5)
        db.row_factory = sqlite3.Row
        try:
            self._seed_diplomatic_relations(db)
            db.commit()
            rows = db.execute("SELECT * FROM diplomatic_relations ORDER BY relation_key").fetchall()
            return {row["relation_key"]: dict(row) for row in rows}
        finally:
            db.close()

    def get_diplomatic_incidents(self, limit=50, category=None, world_id=None):
        try:
            limit = max(1, min(int(limit), 200))
        except (TypeError, ValueError):
            limit = 50
        where = []
        params = []
        if category:
            where.append("category = ?")
            params.append(category)
        if world_id:
            where.append("affected_worlds LIKE ?")
            params.append(f'%"{world_id}"%')
        sql = "SELECT * FROM diplomatic_incidents"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        db = sqlite3.connect(str(COORDINATOR_DB), timeout=5)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(sql, params).fetchall()
        finally:
            db.close()
        incidents = []
        for row in rows:
            item = dict(row)
            for key, default in [("affected_worlds", []), ("relation_deltas", {}), ("payload", {}), ("world_time", {})]:
                try:
                    item[key] = json.loads(item.get(key) or json.dumps(default))
                except Exception:
                    item[key] = default
            incidents.append(item)
        return incidents

    # Compatibility aliases used by dashboard/API code.
    def load_world_npc_stats(self):
        return self.get_npc_stats_cached()

    def load_currency_data(self):
        return self.get_currency_cached()

    def init_db(self):
        db = sqlite3.connect(str(COORDINATOR_DB))
        db.executescript("""
            CREATE TABLE IF NOT EXISTS worlds (
                world_id TEXT PRIMARY KEY,
                api_url TEXT,
                identity TEXT,
                last_heartbeat REAL,
                status TEXT DEFAULT 'offline',
                registered_at REAL
            );
            CREATE TABLE IF NOT EXISTS coordinator_rates (
                from_currency TEXT,
                to_currency TEXT,
                rate REAL,
                updated_at REAL,
                PRIMARY KEY (from_currency, to_currency)
            );
            CREATE TABLE IF NOT EXISTS federation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                world_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                category TEXT DEFAULT '',
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                importance REAL DEFAULT 0.0,
                actor_ids TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                payload TEXT DEFAULT '{}',
                world_time TEXT DEFAULT '{}',
                created_at REAL,
                received_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_federation_events_received_at ON federation_events(received_at DESC);
            CREATE INDEX IF NOT EXISTS idx_federation_events_world ON federation_events(world_id, received_at DESC);
            CREATE INDEX IF NOT EXISTS idx_federation_events_category ON federation_events(category, received_at DESC);
            CREATE TABLE IF NOT EXISTS diplomatic_relations (
                relation_key TEXT PRIMARY KEY,
                country_a TEXT NOT NULL,
                country_b TEXT NOT NULL,
                status TEXT DEFAULT '',
                baseline_trust REAL DEFAULT 0.5,
                baseline_tension REAL DEFAULT 0.3,
                baseline_cooperation REAL DEFAULT 0.3,
                baseline_trade REAL DEFAULT 0.1,
                trust REAL DEFAULT 0.5,
                tension REAL DEFAULT 0.3,
                cooperation REAL DEFAULT 0.3,
                trade REAL DEFAULT 0.1,
                notes TEXT DEFAULT '',
                updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS diplomatic_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT UNIQUE NOT NULL,
                source_event_id TEXT UNIQUE NOT NULL,
                source_world TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                severity REAL DEFAULT 0.0,
                affected_worlds TEXT DEFAULT '[]',
                relation_deltas TEXT DEFAULT '{}',
                payload TEXT DEFAULT '{}',
                world_time TEXT DEFAULT '{}',
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS diplomatic_event_reviews (
                source_event_id TEXT PRIMARY KEY,
                incident_id TEXT,
                reviewed_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_diplomatic_incidents_category ON diplomatic_incidents(category, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_diplomatic_incidents_source_world ON diplomatic_incidents(source_world, created_at DESC);
            CREATE TABLE IF NOT EXISTS growth_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_type TEXT NOT NULL,
                world_id TEXT,
                data JSON NOT NULL,
                created_at REAL NOT NULL,
                tick_number INTEGER,
                UNIQUE(snapshot_type, world_id, tick_number)
            );
        """)
        self._seed_diplomatic_relations(db)
        db.commit()
        db.close()

    def register_world(self, world_id, api_url, identity):
        now = time.time()
        with self.lock:
            self.worlds[world_id] = {
                "api_url": api_url,
                "identity": identity,
                "last_heartbeat": now,
                "status": "online",
                "registered_at": now,
            }
        # Persist
        db = sqlite3.connect(str(COORDINATOR_DB))
        db.execute("""
            INSERT OR REPLACE INTO worlds (world_id, api_url, identity, last_heartbeat, status, registered_at)
            VALUES (?, ?, ?, ?, 'online', ?)
        """, (world_id, api_url, json.dumps(identity), now, now))
        db.commit()
        db.close()

    def heartbeat(self, world_id, identity=None):
        now = time.time()
        with self.lock:
            if world_id in self.worlds:
                self.worlds[world_id]["last_heartbeat"] = now
                self.worlds[world_id]["status"] = "online"
                if identity:
                    self.worlds[world_id]["identity"] = identity
            else:
                self.worlds[world_id] = {
                    "api_url": "",
                    "identity": identity or {},
                    "last_heartbeat": now,
                    "status": "online",
                    "registered_at": now,
                }

    def get_status(self):
        now = time.time()
        result = {}
        with self.lock:
            for wid, info in self.worlds.items():
                age = now - info["last_heartbeat"]
                if age > 3600:  # 1 hour
                    status = "offline"
                elif age > 600:  # 10 minutes
                    status = "degraded"
                else:
                    status = "online"
                info["status"] = status
                result[wid] = {**info, "heartbeat_age": round(age)}
        return result

    def _load_world_npc_stats(self):
        """Query each world's database for NPC type distribution."""
        stats = {}
        for country in ["solara", "valdris", "mirithane", "arkos", "verge"]:
            db_path = AGENTS_HOME / country / "aurelia-world" / "world" / "world.db"
            if not db_path.exists():
                stats[country] = {"total": 0, "types": {}}
                continue
            try:
                db = sqlite3.connect(str(db_path), timeout=2)
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA journal_mode=WAL")
                total = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc'").fetchone()[0]
                type_counts = {}
                rows = db.execute("SELECT properties FROM agents WHERE type='npc' LIMIT 5000").fetchall()
                for r in rows:
                    try:
                        props = json.loads(r["properties"])
                        t = props.get("npc_type", "human")
                        type_counts[t] = type_counts.get(t, 0) + 1
                    except:
                        type_counts["unknown"] = type_counts.get("unknown", 0) + 1
                db.close()
                stats[country] = {"total": total, "types": type_counts}
            except Exception as e:
                stats[country] = {"total": 0, "types": {}, "error": str(e)}
        return stats

    def _load_currency_data(self):
        """Load currency info and exchange rates from any world DB."""
        from src_template.currency import CURRENCIES
        currencies = {}
        for name, info in CURRENCIES.items():
            currencies[name] = {
                "symbol": info["symbol"],
                "country": info["country"],
                "backing": info["backing"],
                "base_value": info["base_value"],
            }

        # Load live rates from solara's DB (they're all synced)
        rates = {}
        db_path = AGENTS_HOME / "solara" / "aurelia-world" / "world" / "world.db"
        if db_path.exists():
            try:
                db = sqlite3.connect(str(db_path), timeout=2)
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA journal_mode=WAL")
                rows = db.execute("SELECT from_currency, to_currency, rate FROM exchange_rates").fetchall()
                for r in rows:
                    f, t, rate = r["from_currency"], r["to_currency"], r["rate"]
                    if f not in rates:
                        rates[f] = {}
                    rates[f][t] = round(rate, 4)
                db.close()
            except:
                pass
        return {"currencies": currencies, "rates": rates}


STATE = CoordinatorState()


# ── Dashboard HTML ─────────────────────────────────────────────────────

def _build_faction_summary(faction_counts, conflict_state, countries_order, country_names, country_colors):
    """Build the faction summary panel."""
    total_active = sum(faction_counts.get(c, {}).get("active", 0) for c in countries_order)
    total_members = sum(conflict_state.get(c, {}).get("total_faction_members", 0) for c in countries_order)
    total_at_war = sum(conflict_state.get(c, {}).get("at_war", 0) for c in countries_order)

    rows = ""
    for cid in countries_order:
        fc = faction_counts.get(cid, {"active": 0, "total": 0})
        cs = conflict_state.get(cid, {"active_conflicts": 0, "max_intensity": 0, "at_war": 0})
        color = country_colors.get(cid, "#666")
        active = fc.get("active", 0)
        at_war = cs.get("at_war", 0)
        members = cs.get("total_faction_members", 0)
        war_marker = " ⚡" if at_war > 0 else ""
        row_color = "#ef4444" if at_war > 0 else "#a78bfa" if active > 0 else "#555"
        rows += f"""<tr>
            <td style="padding:4px 8px;color:{color};font-size:12px">{country_names.get(cid, cid)}</td>
            <td style="padding:4px 8px;color:{row_color};font-size:12px;text-align:right">{active}{war_marker}</td>
            <td style="padding:4px 8px;color:#888;font-size:11px;text-align:right">{members}</td>
        </tr>"""

    return f"""
        <div style="display:flex;gap:12px;margin-bottom:12px">
            <div style="text-align:center;flex:1">
                <div style="font-size:28px;font-weight:bold;color:#a78bfa">{total_active}</div>
                <div style="font-size:10px;color:#666;text-transform:uppercase">Active Factions</div>
            </div>
            <div style="text-align:center;flex:1">
                <div style="font-size:28px;font-weight:bold;color:{'#ef4444' if total_at_war > 0 else '#f59e0b'}">{total_members}</div>
                <div style="font-size:10px;color:#666;text-transform:uppercase">Members</div>
            </div>
            <div style="text-align:center;flex:1">
                <div style="font-size:28px;font-weight:bold;color:{'#ef4444' if total_at_war > 0 else '#22c55e'}">{total_at_war}</div>
                <div style="font-size:10px;color:#666;text-transform:uppercase">At War</div>
            </div>
        </div>
        <table style="width:100%;font-size:12px">
            <tr><th style="padding:4px 8px">Country</th><th style="padding:4px 8px;text-align:right">Active</th><th style="padding:4px 8px;text-align:right">Members</th></tr>
            {rows}
        </table>"""


def _build_conflict_ladder(conflict_state, countries_order, country_names):
    """Build the conflict ladder visualization."""
    LADDER_LABELS = ["dormant", "grievance", "organization", "ultimatum", "skirmish", "armed_conflict", "war"]
    LADDER_COLORS = ["#22c55e", "#4ecdc4", "#f6c343", "#f59e0b", "#e87040", "#ef4444", "#dc2626"]

    # Find the highest intensity across all worlds
    max_intensity = max(
        (conflict_state.get(c, {}).get("max_intensity", 0) for c in countries_order),
        default=0
    )
    current_step = int(max_intensity * 6)  # 0-6

    steps_html = ""
    for i, (label, color) in enumerate(zip(LADDER_LABELS, LADDER_COLORS)):
        active = i <= current_step
        opacity = "1" if active else "0.3"
        glow = f"box-shadow: 0 0 8px {color}44" if active else ""
        steps_html += f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <div style="width:12px;height:12px;border-radius:50%;background:{color};opacity:{opacity};{glow}"></div>
            <span style="font-size:11px;color:{color if active else '#555'}">{label.replace('_', ' ').title()}</span>
        </div>"""

    # Per-world ladder positions
    world_positions = ""
    for cid in countries_order:
        cs = conflict_state.get(cid, {"max_intensity": 0, "at_war": 0})
        idx = int(cs.get("max_intensity", 0) * 6)
        label = LADDER_LABELS[idx] if idx < len(LADDER_LABELS) else "war"
        color = LADDER_COLORS[idx] if idx < len(LADDER_COLORS) else "#dc2626"
        war_mark = " ⚡ WAR" if cs.get("at_war", 0) > 0 else ""
        world_positions += f'<div style="font-size:11px;margin-bottom:2px"><span style="color:#888">{country_names.get(cid, cid)}:</span> <span style="color:{color}">{label.replace("_", " ").title()}{war_mark}</span></div>'

    return f"""
        <div style="margin-bottom:16px">
            {steps_html}
        </div>
        <div style="border-top:1px solid #2a2a4a;padding-top:10px">
            {world_positions}
        </div>
        <div style="margin-top:12px;font-size:10px;color:#555">
            Escalation: probability × influence × repression × tension
        </div>"""


def _build_sovereignty_card(sovereignty, country_colors):
    """Build the sovereignty pipeline panel."""
    new_countries = sovereignty.get("new_countries", [])
    total_secessions = sovereignty.get("total_secessions", 0)
    cascade_active = sovereignty.get("cascade_active", False)
    cascade_ticks = sovereignty.get("cascade_ticks_remaining", 0)
    candidates = sovereignty.get("per_world_candidates", {})

    # New countries list
    countries_html = ""
    if new_countries:
        for nc in new_countries:
            recognized = ", ".join(nc.get("recognized_by", [])) or "none"
            countries_html += f"""<div style="background:#1a1a2e;border:1px solid #4ecdc444;border-radius:4px;padding:8px;margin-bottom:6px">
                <div style="color:#4ecdc4;font-size:13px;font-weight:bold">{nc["name"]}</div>
                <div style="color:#888;font-size:10px">Seceded from {nc["parent"].title()} · Pop: {nc["population"]}</div>
                <div style="color:#666;font-size:10px">Recognized by: {recognized}</div>
            </div>"""
    else:
        countries_html = '<div style="color:#555;font-size:12px">No new countries yet</div>'

    # Sovereignty candidates
    candidate_html = ""
    for world, data in candidates.items():
        cands = data.get("candidates", [])
        for c in cands:
            candidate_html += f"""<div style="font-size:11px;margin-bottom:4px">
                <span style="color:#888">{world.title()}:</span> <span style="color:#f6c343">{c["name"]}</span>
                <span style="color:#555;font-size:10px">({c["members"]} members, influence: {c["influence"]:.2f})</span>
            </div>"""

    if not candidate_html:
        candidate_html = '<div style="color:#555;font-size:11px">No factions meet thresholds</div>'

    cascade_html = ""
    if cascade_active:
        cascade_html = f'<div style="background:#f6c34322;border:1px solid #f6c34344;border-radius:4px;padding:8px;margin-top:10px;font-size:11px;color:#f6c343">🔥 Secession Cascade Active — {cascade_ticks} ticks remaining</div>'

    return f"""
        <div style="display:flex;gap:12px;margin-bottom:12px">
            <div style="text-align:center;flex:1">
                <div style="font-size:28px;font-weight:bold;color:#4ecdc4">{total_secessions}</div>
                <div style="font-size:10px;color:#666;text-transform:uppercase">Secessions</div>
            </div>
            <div style="text-align:center;flex:1">
                <div style="font-size:28px;font-weight:bold;color:#f6c343">{len(new_countries)}</div>
                <div style="font-size:10px;color:#666;text-transform:uppercase">New Countries</div>
            </div>
        </div>
        {cascade_html}
        <div style="margin-top:12px">
            <div style="font-size:11px;color:#888;margin-bottom:6px;text-transform:uppercase">New Countries</div>
            {countries_html}
        </div>
        <div style="margin-top:12px">
            <div style="font-size:11px;color:#888;margin-bottom:6px;text-transform:uppercase">Declaring Independence</div>
            {candidate_html}
        </div>"""


def build_dashboard():
    status = STATE.get_status()
    npc_stats = STATE.load_world_npc_stats()
    currency_data = STATE.load_currency_data()

    countries_order = ["solara", "valdris", "mirithane", "arkos", "verge"]
    country_names = {
        "solara": "Solara", "valdris": "Valdris", "mirithane": "Mirithane",
        "arkos": "Arkos", "verge": "The Verge"
    }
    country_colors = {
        "solara": "#f6c343", "valdris": "#7ec8e3", "mirithane": "#4ecdc4",
        "arkos": "#e87040", "verge": "#a78bfa"
    }
    type_colors = {
        "thren": "#4ecdc4", "vorn": "#e87040", "glim": "#9ca3af", "human": "#f6c343"
    }

    # Phase 6 data
    faction_counts = STATE._load_faction_counts()
    conflict_state = STATE._load_conflict_state()
    sovereignty = STATE._load_sovereignty_state()

    now = time.time()

    # World cards
    world_cards = ""
    for cid in countries_order:
        info = status.get(cid, {})
        st = info.get("status", "offline")
        age = info.get("heartbeat_age", 9999)
        ns = npc_stats.get(cid, {"total": 0, "types": {}})
        color = country_colors.get(cid, "#666")
        fc = faction_counts.get(cid, {"active": 0, "total": 0})
        cs = conflict_state.get(cid, {"active_conflicts": 0, "max_intensity": 0, "at_war": 0, "total_faction_members": 0})

        status_dot = {"online": "#22c55e", "degraded": "#f59e0b", "offline": "#ef4444"}.get(st, "#666")
        age_str = f"{age}s ago" if age < 60 else f"{age//60}m ago" if age < 3600 else "—"

        # NPC type bar
        type_bar = ""
        total_npcs = ns["total"] or 1
        for t in ["thren", "vorn", "glim", "human"]:
            count = ns["types"].get(t, 0)
            pct = (count / total_npcs) * 100
            tc = type_colors.get(t, "#666")
            type_bar += f'<div style="display:inline-block;height:16px;width:{pct:.1f}%;background:{tc}" title="{t}: {count}"></div>'

        type_labels = " · ".join(
            f'<span style="color:{type_colors.get(t,"#666")}">{t}: {ns["types"].get(t,0)}</span>'
            for t in ["thren", "vorn", "glim", "human"]
            if ns["types"].get(t, 0) > 0
        )

        # Phase 6 per-world: conflict intensity bar + faction badge
        intensity_pct = int(cs.get("max_intensity", 0) * 100)
        intensity_color = "#22c55e" if intensity_pct < 20 else "#f59e0b" if intensity_pct < 60 else "#ef4444"
        faction_badge = ""
        if fc["active"] > 0:
            badge_color = "#ef4444" if cs.get("at_war", 0) > 0 else "#f59e0b"
            faction_badge = f'<span style="display:inline-block;background:{badge_color}22;border:1px solid {badge_color}55;border-radius:3px;padding:2px 6px;font-size:11px;color:{badge_color};margin-left:4px">⚔ {fc["active"]}</span>'

        world_cards += f"""
        <div style="background:#1a1a2e;border:1px solid {color}33;border-radius:8px;padding:16px;flex:1;min-width:200px">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                <div style="width:10px;height:10px;border-radius:50%;background:{status_dot}"></div>
                <span style="color:{color};font-size:18px;font-weight:bold">{country_names.get(cid, cid)}</span>
                <span style="color:#666;font-size:12px;margin-left:auto">{age_str}</span>
            </div>
            <div style="color:#888;font-size:13px;margin-bottom:8px">
                NPCs: {ns["total"]} · Factions: {fc["active"]}{faction_badge}
            </div>
            <div style="border-radius:4px;overflow:hidden;margin-bottom:6px">{type_bar}</div>
            <div style="font-size:11px">{type_labels}</div>
            <div style="margin-top:10px;border-top:1px solid #2a2a4a;padding-top:8px">
                <div style="display:flex;align-items:center;gap:8px">
                    <span style="font-size:10px;color:#666;text-transform:uppercase;min-width:60px">Stability</span>
                    <div style="flex:1;height:6px;background:#1a1a2e;border-radius:3px;overflow:hidden">
                        <div style="width:{100-intensity_pct}%;height:100%;background:{intensity_color};border-radius:3px"></div>
                    </div>
                    <span style="font-size:10px;color:#888">{100-intensity_pct}%</span>
                </div>
                <div style="font-size:10px;color:#555;margin-top:4px">
                    Members: {cs.get("total_faction_members", 0)} · At war: {cs.get("at_war", 0)}
                </div>
            </div>
        </div>
        """

    # Currency exchange table
    currencies = currency_data.get("currencies", {})
    rates = currency_data.get("rates", {})
    cur_names = list(currencies.keys())

    rate_rows = ""
    for from_c in cur_names:
        cells = ""
        for to_c in cur_names:
            rate = rates.get(from_c, {}).get(to_c, 1.0)
            if from_c == to_c:
                cells += '<td style="padding:6px 10px;color:#555">—</td>'
            else:
                cells += f'<td style="padding:6px 10px;color:#e2e8f0">{rate:.4f}</td>'
        sym = currencies[from_c]["symbol"]
        rate_rows += f'<tr><td style="padding:6px 10px;color:{country_colors.get(currencies[from_c]["country"],"#888")};font-weight:bold">{sym} {from_c}</td>{cells}</tr>'

    rate_headers = "".join(
        f'<th style="padding:6px 10px;color:{country_colors.get(currencies[c]["country"],"#888")}">{currencies[c]["symbol"]} {c}</th>'
        for c in cur_names
    )

    # NPC type legend
    type_legend = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:16px">'
        f'<span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:{c}"></span>'
        f'<span style="color:#ccc;font-size:12px">{t}</span></span>'
        for t, c in type_colors.items()
    )

    total_npcs_all = sum(npc_stats.get(c, {}).get("total", 0) for c in countries_order)
    total_worlds = len([w for w in status.values() if w.get("status") == "online"])

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Aurelia Federation Coordinator</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ background:#0d0d1a; color:#e2e8f0; font-family:'Inter',system-ui,sans-serif; padding:24px; }}
        h1 {{ color:#f6c343; font-size:24px; margin-bottom:4px; }}
        .subtitle {{ color:#666; font-size:13px; margin-bottom:24px; }}
        .stat {{ display:inline-block; background:#1a1a2e; border:1px solid #2a2a4a; border-radius:6px; padding:12px 20px; margin-right:12px; margin-bottom:16px; }}
        .stat-val {{ font-size:24px; font-weight:bold; color:#f6c343; }}
        .stat-label {{ font-size:11px; color:#666; text-transform:uppercase; }}
        .section {{ margin-bottom:32px; }}
        .section-title {{ color:#a78bfa; font-size:14px; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; }}
        table {{ border-collapse:collapse; background:#1a1a2e; border-radius:8px; overflow:hidden; }}
        th {{ text-align:left; padding:8px 12px; background:#222244; font-size:12px; }}
    </style>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <h1>🌍 Aurelia Federation Coordinator</h1>
    <div class="subtitle">Port {PORT} · Refreshes every 30s · {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>

    <div style="margin-bottom:20px">
        <div class="stat">
            <div class="stat-val">{total_worlds}/5</div>
            <div class="stat-label">Worlds Online</div>
        </div>
        <div class="stat">
            <div class="stat-val">{total_npcs_all}</div>
            <div class="stat-label">Total NPCs</div>
        </div>
        <div class="stat">
            <div class="stat-val">{len(cur_names)}</div>
            <div class="stat-label">Currencies</div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Country-States</div>
        <div style="display:flex;gap:12px;flex-wrap:wrap">
            {world_cards}
        </div>
        <div style="margin-top:8px">{type_legend}</div>
    </div>

    <div class="section">
        <div class="section-title">Aurelian Exchange — Live Rates</div>
        <table>
            <tr><th>From \\ To</th>{rate_headers}</tr>
            {rate_rows}
        </table>
    </div>

    <div class="section">
        <div class="section-title">⚔ Phase 6 — Geopolitics</div>
        <div style="display:flex;gap:16px;flex-wrap:wrap">
            <!-- Faction Summary Card -->
            <div style="background:#1a1a2e;border:1px solid #2a2a4a;border-radius:8px;padding:16px;flex:1;min-width:280px">
                <div style="color:#a78bfa;font-size:13px;font-weight:bold;margin-bottom:12px">Factions</div>
                {_build_faction_summary(faction_counts, conflict_state, countries_order, country_names, country_colors)}
            </div>
            <!-- Conflict Ladder Card -->
            <div style="background:#1a1a2e;border:1px solid #2a2a4a;border-radius:8px;padding:16px;flex:1;min-width:280px">
                <div style="color:#f59e0b;font-size:13px;font-weight:bold;margin-bottom:12px">Conflict Ladder</div>
                {_build_conflict_ladder(conflict_state, countries_order, country_names)}
            </div>
            <!-- Sovereignty Card -->
            <div style="background:#1a1a2e;border:1px solid #2a2a4a;border-radius:8px;padding:16px;flex:1;min-width:280px">
                <div style="color:#4ecdc4;font-size:13px;font-weight:bold;margin-bottom:12px">Sovereignty</div>
                {_build_sovereignty_card(sovereignty, country_colors)}
            </div>
        </div>
    </div>

    <div style="color:#444;font-size:11px;margin-top:32px">
        Aurelia Federation · Thren / Vorn / Glim · {len(currencies)} currencies · Phase 6 — Emergent Geopolitics
    </div>
</body>
</html>"""
    return html


# ── API Endpoints ──────────────────────────────────────────────────────

def handle_api_status():
    return json.dumps(STATE.get_status(), indent=2)

def handle_api_npc_stats():
    return json.dumps(STATE.load_world_npc_stats(), indent=2)

def handle_api_rates():
    data = STATE.load_currency_data()
    return json.dumps(data, indent=2)


# ── HTTP Handler ───────────────────────────────────────────────────────

class CoordinatorHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {args[0]}")

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            return json.loads(self.rfile.read(length))
        return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "" or path == "/":
            self._send_html(build_dashboard())
        elif path == "/api/status":
            self._send_json({"worlds": STATE.get_status()})
        elif path == "/api/npc-stats":
            self._send_json(STATE.load_world_npc_stats())
        elif path == "/api/rates":
            self._send_json(STATE.load_currency_data())
        elif path == "/api/federation-events":
            qs = parse_qs(parsed.query)
            self._send_json({
                "events": STATE.get_federation_events(
                    limit=(qs.get("limit", [50])[0]),
                    world_id=(qs.get("world_id", [None])[0]),
                    category=(qs.get("category", [None])[0]),
                    event_type=(qs.get("event_type", [None])[0]),
                )
            })
        elif path == "/api/diplomacy":
            qs = parse_qs(parsed.query)
            self._send_json({
                "relations": STATE.get_diplomatic_relations(),
                "incidents": STATE.get_diplomatic_incidents(
                    limit=(qs.get("limit", [50])[0]),
                    category=(qs.get("category", [None])[0]),
                    world_id=(qs.get("world_id", [None])[0]),
                ),
            })
        elif path == "/api/health":
            self._send_json({"status": "ok", "worlds": len(STATE.worlds), "uptime": time.time()})
        elif path == "/api/growth":
            self._send_json(STATE.build_growth_snapshot())
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/register":
            body = self._read_body()
            world_id = body.get("world_id")
            api_url = body.get("api_url", "")
            identity = body.get("identity", {})
            if not world_id:
                self._send_json({"error": "world_id required"}, 400)
                return
            STATE.register_world(world_id, api_url, identity)
            self._send_json({"status": "registered", "world_id": world_id})

        elif path == "/heartbeat":
            body = self._read_body()
            world_id = body.get("world_id")
            identity = body.get("identity")
            if not world_id:
                self._send_json({"error": "world_id required"}, 400)
                return
            STATE.heartbeat(world_id, identity)
            self._send_json({"status": "ok"})

        elif path == "/events":
            body = self._read_body()
            world_id = body.get("world_id")
            events = body.get("events", [])
            if not world_id:
                self._send_json({"error": "world_id required"}, 400)
                return
            result = STATE.ingest_federation_events(world_id, events)
            self._send_json({"status": "ok", **result})

        elif path == "/api/diplomacy/process":
            body = self._read_body()
            result = STATE.process_diplomacy_events(limit=body.get("limit", 100))
            self._send_json({"status": "ok", **result})

        else:
            self._send_json({"error": "Not found"}, 404)


# ── Main ───────────────────────────────────────────────────────────────

def main():
    # Add src_template to path for currency imports
    sys.path.insert(0, str(AURELIA_ROOT))

    server = http.server.HTTPServer(("0.0.0.0", PORT), CoordinatorHandler)
    print("=" * 50)
    print("AURELIA FEDERATION COORDINATOR")
    print(f"Port: {PORT}")
    print(f"Dashboard: http://127.0.0.1:{PORT}")
    print(f"DB: {COORDINATOR_DB}")
    print(f"Worlds: solara, valdris, mirithane, arkos, verge")
    print(f"NPC Types: Thren / Vorn / Glim / Human")
    print("=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCoordinator stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
