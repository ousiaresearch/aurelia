"""meso_aggregator.py — roll micro events into local institutional pressure."""
from __future__ import annotations

import json
import time
from collections import defaultdict

try:
    from . import causal_ledger
except Exception:
    import causal_ledger


def ensure_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS meso_signals (
            signal_id TEXT PRIMARY KEY,
            tick_number INTEGER NOT NULL,
            world_id TEXT NOT NULL,
            location_id TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            magnitude REAL NOT NULL DEFAULT 0.0,
            source_event_count INTEGER NOT NULL DEFAULT 0,
            payload TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_meso_signals_tick_world
            ON meso_signals(tick_number, world_id, signal_type);
    """)


EVENT_TO_SIGNAL = {
    "wage_dispute": ("labor_unrest", 0.30),
    "work_failure": ("economic_stress", 0.18),
    "small_trade": ("market_activity", 0.10),
    "security_stop": ("repression_visibility", 0.35),
    "rumor_transmission": ("rumor_velocity", 0.20),
    "illness_seen": ("public_health_risk", 0.22),
    "migration_plan": ("migration_pressure", 0.25),
    "caregiving": ("social_solidarity", 0.15),
    "work_success": ("productive_confidence", 0.12),
    "propaganda_exposure": ("state_messaging", 0.10),
}


def aggregate_meso_signals(db, *, world_id: str, tick_number: int) -> list[str]:
    ensure_schema(db)
    rows = db.execute(
        """
        SELECT event_id, event_type, payload, magnitude, valence
        FROM causal_events
        WHERE tick_number = ? AND world_id = ? AND layer = 'micro'
        """,
        (int(tick_number), world_id),
    ).fetchall()
    buckets: dict[tuple[str, str], list] = defaultdict(list)
    for row in rows:
        signal = EVENT_TO_SIGNAL.get(row["event_type"])
        if not signal:
            continue
        signal_type, weight = signal
        try:
            payload = json.loads(row["payload"] or "{}")
        except Exception:
            payload = {}
        location = payload.get("location_id") or "unknown"
        buckets[(location, signal_type)].append((row, weight))

    emitted: list[str] = []
    now = time.time()
    for (location, signal_type), members in buckets.items():
        magnitude = sum(float(r["magnitude"] or 0.0) * weight for r, weight in members)
        count = len(members)
        signal_id = f"sig:{world_id}:{tick_number}:{location}:{signal_type}"
        db.execute(
            """
            INSERT OR REPLACE INTO meso_signals
                (signal_id, tick_number, world_id, location_id, signal_type,
                 magnitude, source_event_count, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (signal_id, tick_number, world_id, location, signal_type,
             magnitude, count, json.dumps({"source_events": [r["event_id"] for r, _ in members]}), now),
        )
        eid = causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="meso",
            event_type=signal_type,
            scope="location",
            target_ids=[location],
            magnitude=magnitude,
            valence=-magnitude if signal_type not in {"social_solidarity", "productive_confidence", "market_activity"} else magnitude,
            payload={"location_id": location, "source_event_count": count},
        )
        for source, _ in members[:25]:
            causal_ledger.link_events(db, source["event_id"], eid, "translated_into", min(1.0, magnitude))
        emitted.append(eid)
    return emitted
