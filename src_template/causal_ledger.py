"""causal_ledger.py — durable causal event graph for Aurelia Phase 7.

This module is intentionally small and dependency-light. It records what happened,
what it caused, and what should be applied later. Higher-level systems (micro,
meso, macro, federation resolver) should use this instead of writing anonymous
ad-hoc rows.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Iterable, Mapping, Optional

VALID_LAYERS = {"micro", "meso", "macro", "federation"}


def _json(value: Any, default: Any) -> str:
    if value is None:
        value = default
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _event_id(world_id: str, tick_number: int, event_type: str) -> str:
    return f"evt:{world_id}:{tick_number}:{event_type}:{uuid.uuid4().hex[:12]}"


def _effect_id(source_event_id: str, apply_tick: int, effect_type: str) -> str:
    return f"eff:{apply_tick}:{effect_type}:{uuid.uuid5(uuid.NAMESPACE_URL, source_event_id + effect_type).hex[:12]}:{uuid.uuid4().hex[:8]}"


def emit_event(
    db,
    *,
    tick_number: int,
    world_id: str,
    layer: str,
    event_type: str,
    scope: str,
    actor_ids: Optional[Iterable[str]] = None,
    target_ids: Optional[Iterable[str]] = None,
    magnitude: float = 0.0,
    valence: float = 0.0,
    confidence: float = 1.0,
    payload: Optional[Mapping[str, Any]] = None,
    event_id: Optional[str] = None,
) -> str:
    """Insert one causal event and return its event_id.

    `layer` is deliberately constrained. If a mechanic cannot decide whether an
    event is micro, meso, macro, or federation, its causal role is unclear and it
    should not be silently written.
    """
    if layer not in VALID_LAYERS:
        raise ValueError(f"invalid causal layer: {layer!r}")
    event_id = event_id or _event_id(world_id, tick_number, event_type)
    db.execute(
        """
        INSERT INTO causal_events (
            event_id, tick_number, world_id, layer, event_type,
            actor_ids, target_ids, scope, magnitude, valence, confidence,
            payload, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            int(tick_number),
            world_id,
            layer,
            event_type,
            _json(list(actor_ids or []), []),
            _json(list(target_ids or []), []),
            scope,
            float(magnitude),
            float(valence),
            float(confidence),
            _json(dict(payload or {}), {}),
            time.time(),
        ),
    )
    return event_id


def schedule_effect(
    db,
    *,
    source_event_id: str,
    apply_tick: int,
    target_world_id: str,
    target_scope: str,
    effect_type: str,
    target_id: Optional[str] = None,
    magnitude: float = 0.0,
    payload: Optional[Mapping[str, Any]] = None,
    effect_id: Optional[str] = None,
) -> str:
    """Schedule a delayed effect caused by an event."""
    effect_id = effect_id or _effect_id(source_event_id, int(apply_tick), effect_type)
    db.execute(
        """
        INSERT INTO delayed_effects (
            effect_id, source_event_id, apply_tick, target_world_id,
            target_scope, target_id, effect_type, magnitude, payload,
            applied, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (
            effect_id,
            source_event_id,
            int(apply_tick),
            target_world_id,
            target_scope,
            target_id,
            effect_type,
            float(magnitude),
            _json(dict(payload or {}), {}),
            time.time(),
        ),
    )
    return effect_id


def link_events(
    db,
    parent_event_id: str,
    child_event_id: str,
    relation: str,
    weight: float = 1.0,
) -> None:
    """Record a causal edge between events."""
    db.execute(
        """
        INSERT OR REPLACE INTO causal_edges
            (parent_event_id, child_event_id, relation, weight)
        VALUES (?, ?, ?, ?)
        """,
        (parent_event_id, child_event_id, relation, float(weight)),
    )


def due_effects(db, tick_number: int, world_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Return unapplied delayed effects due at or before `tick_number`."""
    if world_id is None:
        rows = db.execute(
            """
            SELECT * FROM delayed_effects
            WHERE applied = 0 AND apply_tick <= ?
            ORDER BY apply_tick, created_at
            """,
            (int(tick_number),),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT * FROM delayed_effects
            WHERE applied = 0 AND apply_tick <= ? AND target_world_id = ?
            ORDER BY apply_tick, created_at
            """,
            (int(tick_number), world_id),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_effect_applied(db, effect_id: str) -> None:
    db.execute("UPDATE delayed_effects SET applied = 1 WHERE effect_id = ?", (effect_id,))


def causal_chain(db, event_id: str, depth: int = 5) -> list[dict[str, Any]]:
    """Return descendant causal edges breadth-first for reporting."""
    out: list[dict[str, Any]] = []
    frontier = [(event_id, 0)]
    seen = {event_id}
    while frontier:
        current, level = frontier.pop(0)
        if level >= depth:
            continue
        rows = db.execute(
            """
            SELECT e.*, ce.relation, ce.weight
            FROM causal_edges ce
            JOIN causal_events e ON e.event_id = ce.child_event_id
            WHERE ce.parent_event_id = ?
            ORDER BY e.tick_number, e.created_at
            """,
            (current,),
        ).fetchall()
        for row in rows:
            child = dict(row)
            if child["event_id"] in seen:
                continue
            seen.add(child["event_id"])
            out.append(child)
            frontier.append((child["event_id"], level + 1))
    return out
