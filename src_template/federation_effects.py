"""federation_effects.py — resolve cross-world effects at a tick barrier."""
from __future__ import annotations

import json

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
    "faction_suppressed": ("ideology_diffusion", 0.05),
    "faction_exiled": ("refugee_inflow", 0.10),
    "faction_splintered": ("ideology_diffusion", 0.10),
    "faction_radicalized": ("ideology_diffusion", 0.12),
    "faction_legalized": ("recognition_pressure", 0.04),
    "faction_governing_coalition": ("recognition_pressure", 0.06),
    "faction_victorious": ("recognition_pressure", 0.12),
    "economic_stress": ("trade_shock", 0.04),
    "public_health_risk": ("disease_alert", 0.04),
    "migration_pressure": ("refugee_inflow", 0.05),
    "migration_outflow": ("refugee_inflow", 0.03),
}

MIGRATION_SOURCE_EVENTS = {"migration_pressure", "faction_repressed", "faction_exiled", "migration_outflow"}


def _targets_for(source: str, worlds: list[str]) -> list[str]:
    return [w for w in BORDERS.get(source, [w for w in worlds if w != source]) if w in worlds and w != source]


def _schedule(federation_db, *, source_event_id: str, tick_number: int, target_world_id: str,
              effect_type: str, magnitude: float, payload: dict) -> str:
    return causal_ledger.schedule_effect(
        federation_db,
        source_event_id=source_event_id,
        apply_tick=int(tick_number) + 1,
        target_world_id=target_world_id,
        target_scope="country",
        effect_type=effect_type,
        magnitude=magnitude,
        payload=payload,
    )


def _emit_scheduled(federation_db, *, tick_number: int, source: str, target: str,
                    effect_id: str, effect_type: str, magnitude: float) -> None:
    causal_ledger.emit_event(
        federation_db,
        tick_number=tick_number,
        world_id="federation",
        layer="federation",
        event_type="cross_world_effect_scheduled",
        scope="federation",
        actor_ids=[source],
        target_ids=[target],
        magnitude=magnitude,
        valence=-magnitude,
        payload={"effect_id": effect_id, "effect_type": effect_type, "source_world": source, "target_world": target},
    )


def _schedule_paired_migration(federation_db, *, row, tick_number: int, source: str, target: str, mag: float) -> int:
    group_id = f"mig:{source}:{target}:{tick_number}:{row['event_id']}"
    migration_type = "refugee" if row["event_type"] in {"migration_pressure", "faction_repressed", "faction_exiled", "migration_outflow"} else "labor"
    payload = {
        "migration_group_id": group_id,
        "source_world": source,
        "target_world": target,
        "source_event_type": row["event_type"],
        "migration_type": migration_type,
    }
    out_effect = "refugee_outflow" if migration_type == "refugee" else "labor_outflow"
    in_effect = "refugee_inflow" if migration_type == "refugee" else "labor_inflow"
    out_id = _schedule(
        federation_db,
        source_event_id=row["event_id"],
        tick_number=tick_number,
        target_world_id=source,
        effect_type=out_effect,
        magnitude=mag,
        payload=payload,
    )
    in_id = _schedule(
        federation_db,
        source_event_id=row["event_id"],
        tick_number=tick_number,
        target_world_id=target,
        effect_type=in_effect,
        magnitude=mag,
        payload=payload,
    )
    _emit_scheduled(federation_db, tick_number=tick_number, source=source, target=source, effect_id=out_id, effect_type=out_effect, magnitude=mag)
    _emit_scheduled(federation_db, tick_number=tick_number, source=source, target=target, effect_id=in_id, effect_type=in_effect, magnitude=mag)
    return 2


def resolve_outbound_effects(federation_db, *, tick_number: int, worlds: list[str]) -> int:
    """Read federation ledger events for tick and schedule next-tick effects."""
    causal_ledger.ensure_schema(federation_db)
    event_types = tuple(EVENT_EFFECTS.keys())
    placeholders = ",".join("?" for _ in event_types)
    rows = federation_db.execute(
        f"SELECT * FROM causal_events WHERE tick_number=? AND event_type IN ({placeholders})",
        (int(tick_number), *event_types),
    ).fetchall()
    scheduled = 0
    for row in rows:
        source = row["world_id"]
        if source == "federation":
            continue
        effect_type, base = EVENT_EFFECTS[row["event_type"]]
        for target in _targets_for(source, worlds):
            mag = max(0.01, float(row["magnitude"] or 0.0) * base)
            if row["event_type"] in MIGRATION_SOURCE_EVENTS:
                scheduled += _schedule_paired_migration(
                    federation_db,
                    row=row,
                    tick_number=tick_number,
                    source=source,
                    target=target,
                    mag=mag,
                )
                continue
            effect_id = _schedule(
                federation_db,
                source_event_id=row["event_id"],
                tick_number=tick_number,
                target_world_id=target,
                effect_type=effect_type,
                magnitude=mag,
                payload={"source_world": source, "target_world": target, "source_event_type": row["event_type"]},
            )
            _emit_scheduled(federation_db, tick_number=tick_number, source=source, target=target, effect_id=effect_id, effect_type=effect_type, magnitude=mag)
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
    """Copy due federation effects into a world DB so world mechanics can apply them."""
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
        causal_ledger.mark_effect_applied(federation_db, row["effect_id"])
    return len(rows)
