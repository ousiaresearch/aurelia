"""federation_effects.py — resolve cross-world effects at a tick barrier."""
from __future__ import annotations

import json
import time

try:
    from . import causal_ledger
except Exception:
    import causal_ledger

BORDERS = {
    "solara": ["valdris", "arkos"],
    "valdris": ["solara", "mirithane", "verge"],
    "mirithane": ["valdris", "arkos"],
    "arkos": ["solara", "mirithane", "verge"],
    "verge": ["valdris", "arkos"],
}

EVENT_EFFECTS = {
    "faction_escalated": ("ideology_diffusion", 0.08),
    "faction_repressed": ("refugee_inflow", 0.06),
    "faction_integrated": ("recognition_pressure", 0.03),
    "economic_stress": ("trade_shock", 0.04),
    "public_health_risk": ("disease_alert", 0.04),
    "migration_pressure": ("refugee_inflow", 0.05),
}


def resolve_outbound_effects(federation_db, *, tick_number: int, worlds: list[str]) -> int:
    """Read federation ledger events for tick and schedule next-tick effects."""
    causal_ledger.ensure_schema(federation_db)
    rows = federation_db.execute(
        """
        SELECT * FROM causal_events
        WHERE tick_number=? AND event_type IN ('faction_escalated','faction_repressed','faction_integrated','economic_stress','public_health_risk','migration_pressure')
        """,
        (int(tick_number),),
    ).fetchall()
    scheduled = 0
    for row in rows:
        source = row["world_id"]
        effect = EVENT_EFFECTS.get(row["event_type"])
        if not effect:
            continue
        effect_type, base = effect
        targets = BORDERS.get(source, [w for w in worlds if w != source])
        for target in targets:
            if target not in worlds or target == source:
                continue
            mag = max(0.01, float(row["magnitude"] or 0.0) * base)
            effect_id = causal_ledger.schedule_effect(
                federation_db,
                source_event_id=row["event_id"],
                apply_tick=int(tick_number) + 1,
                target_world_id=target,
                target_scope="country",
                effect_type=effect_type,
                magnitude=mag,
                payload={"source_world": source, "source_event_type": row["event_type"]},
            )
            causal_ledger.emit_event(
                federation_db,
                tick_number=tick_number,
                world_id="federation",
                layer="federation",
                event_type="cross_world_effect_scheduled",
                scope="federation",
                actor_ids=[source],
                target_ids=[target],
                magnitude=mag,
                valence=-mag,
                payload={"effect_id": effect_id, "effect_type": effect_type, "source_world": source, "target_world": target},
            )
            scheduled += 1
    return scheduled


def copy_world_events_to_federation(world_db, federation_db, *, world_id: str, tick_number: int) -> int:
    """Copy one world's events for a tick into the central federation ledger."""
    causal_ledger.ensure_schema(federation_db)
    rows = world_db.execute(
        "SELECT * FROM causal_events WHERE world_id=? AND tick_number=?",
        (world_id, int(tick_number)),
    ).fetchall()
    copied = 0
    for row in rows:
        federation_db.execute(
            """
            INSERT OR IGNORE INTO causal_events
                (event_id, tick_number, world_id, layer, event_type, actor_ids, target_ids,
                 scope, magnitude, valence, confidence, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(row[k] for k in [
                "event_id", "tick_number", "world_id", "layer", "event_type", "actor_ids", "target_ids",
                "scope", "magnitude", "valence", "confidence", "payload", "created_at"
            ]),
        )
        copied += 1
    return copied


def import_due_effects(federation_db, world_db, *, world_id: str, tick_number: int) -> int:
    """Copy due federation effects into a world DB so macro dynamics can apply them."""
    causal_ledger.ensure_schema(world_db)
    rows = causal_ledger.due_effects(federation_db, tick_number, world_id)
    for row in rows:
        world_db.execute(
            """
            INSERT OR IGNORE INTO delayed_effects
                (effect_id, source_event_id, apply_tick, target_world_id, target_scope, target_id,
                 effect_type, magnitude, payload, applied, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            tuple(row[k] for k in [
                "effect_id", "source_event_id", "apply_tick", "target_world_id", "target_scope", "target_id",
                "effect_type", "magnitude", "payload", "created_at"
            ]),
        )
    return len(rows)
