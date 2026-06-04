"""federation_events.py — Build cross-world event payloads from local tick output.

The coordinator event bus should receive compact, meaningful events rather than raw
world internals. These builders turn local simulation output into stable event
contracts that diplomacy, trade, governance, and narrative systems can consume.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _event(
    *,
    event_id: str,
    world_id: str,
    event_type: str,
    category: str,
    title: str,
    description: str,
    importance: float,
    actor_ids: Optional[Iterable[str]] = None,
    tags: Optional[Iterable[str]] = None,
    payload: Optional[Dict[str, Any]] = None,
    world_time: Optional[Dict[str, Any]] = None,
    created_at: Optional[float] = None,
) -> Dict[str, Any]:
    return {
        "event_id": event_id,
        "world_id": world_id,
        "event_type": event_type,
        "category": category,
        "title": title,
        "description": description,
        "importance": float(importance),
        "actor_ids": list(actor_ids or []),
        "tags": list(tags or []),
        "payload": payload or {},
        "world_time": world_time or {},
        "created_at": created_at if created_at is not None else time.time(),
    }


def _title_from_description(description: str, fallback: str, max_len: int = 72) -> str:
    text = (description or fallback).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def build_federation_events(
    world_id: str,
    tick_number: int,
    tick_result: Dict[str, Any],
    max_events: int = 25,
) -> List[Dict[str, Any]]:
    """Promote local tick output into federation-event records.

    Priority order is deliberate:
    1. NPC actions — Phase 1 made these meaningful and location/type-aware.
    2. Social changes — alliances/conflicts drive diplomacy and personhood politics.
    3. Trade flows — economy phase consumes these later.
    4. Emergent/ritual/narrative events — local color with cross-world hooks.
    """
    events: List[Dict[str, Any]] = []
    world_time = tick_result.get("time") or {}
    created_at = time.time()

    for index, action in enumerate(tick_result.get("npc_ai_actions") or []):
        npc_id = action.get("npc_id") or "unknown-npc"
        npc_name = action.get("npc_name") or npc_id
        npc_type = (action.get("npc_type") or "unknown").lower()
        activity = action.get("activity") or action.get("action_type") or "activity"
        location_id = action.get("location_id") or ""
        description = action.get("action") or action.get("description") or f"{npc_name} continues {activity}."
        tags = [tag for tag in [npc_type, activity, location_id, "schedule"] if tag]
        events.append(
            _event(
                event_id=f"{world_id}:tick-{tick_number}:npc-action:{npc_id}:{index}",
                world_id=world_id,
                event_type="npc_action",
                category="daily_life",
                title=_title_from_description(description, f"{npc_name} acts"),
                description=description,
                importance=0.35,
                actor_ids=[npc_id] if npc_id else [],
                tags=tags,
                payload={
                    "npc_id": npc_id,
                    "npc_name": npc_name,
                    "npc_type": npc_type,
                    "activity": activity,
                    "location_id": location_id,
                    "occupation": action.get("occupation"),
                },
                world_time=world_time,
                created_at=created_at,
            )
        )
        if len(events) >= max_events:
            return events

    for index, change in enumerate(tick_result.get("social_changes") or []):
        change_type = change.get("type") or "social_change"
        description = change.get("description") or "A social pattern changed."
        actor_ids = [str(v) for v in _as_list(change.get("npcs") or change.get("actor_ids"))]
        events.append(
            _event(
                event_id=f"{world_id}:tick-{tick_number}:social:{change_type}:{index}",
                world_id=world_id,
                event_type="social_change",
                category="social",
                title=_title_from_description(description, "Social change"),
                description=description,
                importance=0.7 if change_type in {"new_conflict", "breakup", "new_alliance"} else 0.5,
                actor_ids=actor_ids,
                tags=["social", change_type],
                payload=change,
                world_time=world_time,
                created_at=created_at,
            )
        )
        if len(events) >= max_events:
            return events

    economy = tick_result.get("economy") or {}
    for index, trade in enumerate(economy.get("traded") or []):
        resource = trade.get("resource", "goods") if isinstance(trade, dict) else "goods"
        amount = trade.get("amount") if isinstance(trade, dict) else None
        description = f"{world_id} trade flow: {amount or '?'} {resource}."
        events.append(
            _event(
                event_id=f"{world_id}:tick-{tick_number}:trade:{resource}:{index}",
                world_id=world_id,
                event_type="trade_flow",
                category="economy",
                title=_title_from_description(description, "Trade flow"),
                description=description,
                importance=0.55,
                actor_ids=[],
                tags=["trade", "economy", str(resource)],
                payload=trade if isinstance(trade, dict) else {"value": trade},
                world_time=world_time,
                created_at=created_at,
            )
        )
        if len(events) >= max_events:
            return events

    for bucket, event_type, category in [
        ("emergent_events", "emergent_event", "emergence"),
        ("ritual_events", "ritual_event", "ritual"),
        ("narrative_moments", "narrative_moment", "narrative"),
    ]:
        for index, raw in enumerate(tick_result.get(bucket) or []):
            if isinstance(raw, dict):
                description = raw.get("description") or raw.get("content") or str(raw)
                payload = raw
            else:
                description = str(raw)
                payload = {"value": raw}
            events.append(
                _event(
                    event_id=f"{world_id}:tick-{tick_number}:{event_type}:{index}",
                    world_id=world_id,
                    event_type=event_type,
                    category=category,
                    title=_title_from_description(description, event_type.replace("_", " ").title()),
                    description=description,
                    importance=0.6,
                    actor_ids=[],
                    tags=[category, event_type],
                    payload=payload,
                    world_time=world_time,
                    created_at=created_at,
                )
            )
            if len(events) >= max_events:
                return events

    return events
