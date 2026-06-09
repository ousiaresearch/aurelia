"""Live map-state contract for the PNW world GUI."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from typing import Any

VIEWBOX_WIDTH = 400
VIEWBOX_HEIGHT = 500
PADDING_X = 35
PADDING_Y = 45
DUPLICATE_SPREAD_RADIUS = 12


def _loads_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else default
    except (TypeError, json.JSONDecodeError):
        return default


def _scale(value: float, min_value: float, max_value: float, low: float, high: float) -> float:
    if max_value == min_value:
        return (low + high) / 2
    return low + ((value - min_value) / (max_value - min_value)) * (high - low)


def _round(value: float) -> float:
    return round(value, 2)


def _rows_to_dicts(rows) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def build_map_state(db) -> dict[str, Any]:
    """Build a frontend-ready map from live locations and exits tables."""
    location_rows = _rows_to_dicts(
        db.execute(
            """
            SELECT id, name, description, parent_id, x, y, elevation, indoor, tags, properties
            FROM locations
            ORDER BY id
            """
        ).fetchall()
    )

    if not location_rows:
        return {
            "locations": [],
            "edges": [],
            "bounds": {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "min_elevation": 0, "max_elevation": 0},
            "viewbox": {"width": VIEWBOX_WIDTH, "height": VIEWBOX_HEIGHT},
        }

    xs = [float(row.get("x") or 0) for row in location_rows]
    ys = [float(row.get("y") or 0) for row in location_rows]
    elevations = [float(row.get("elevation") or 0) for row in location_rows]
    bounds = {
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
        "min_elevation": min(elevations),
        "max_elevation": max(elevations),
    }

    grouped: dict[tuple[float, float], list[dict[str, Any]]] = defaultdict(list)
    for row in location_rows:
        grouped[(float(row.get("x") or 0), float(row.get("y") or 0))].append(row)

    duplicate_offsets: dict[str, tuple[float, float]] = {}
    for rows in grouped.values():
        rows.sort(key=lambda row: row["id"])
        if len(rows) == 1:
            duplicate_offsets[rows[0]["id"]] = (0, 0)
            continue
        for index, row in enumerate(rows):
            angle = (2 * math.pi * index) / len(rows)
            duplicate_offsets[row["id"]] = (
                math.cos(angle) * DUPLICATE_SPREAD_RADIUS,
                math.sin(angle) * DUPLICATE_SPREAD_RADIUS,
            )

    locations = []
    for row in location_rows:
        world_x = float(row.get("x") or 0)
        world_y = float(row.get("y") or 0)
        properties = _loads_json(row.get("properties"), {})
        tags = _loads_json(row.get("tags"), [])
        if not isinstance(tags, list):
            tags = []
        if not isinstance(properties, dict):
            properties = {}

        base_x = _scale(world_x, bounds["min_x"], bounds["max_x"], PADDING_X, VIEWBOX_WIDTH - PADDING_X)
        # SVG y grows downward. Higher world y should appear higher on the map.
        base_y = _scale(world_y, bounds["min_y"], bounds["max_y"], VIEWBOX_HEIGHT - PADDING_Y, PADDING_Y)
        dx, dy = duplicate_offsets[row["id"]]

        locations.append(
            {
                "id": row["id"],
                "name": row["name"],
                "label": properties.get("map_label") or row["name"],
                "description": row.get("description") or "",
                "parent_id": row.get("parent_id"),
                "world_x": world_x,
                "world_y": world_y,
                "elevation": float(row.get("elevation") or 0),
                "indoor": bool(row.get("indoor")),
                "tags": tags,
                "properties": properties,
                "map_x": _round(base_x + dx),
                "map_y": _round(base_y + dy),
            }
        )

    edge_rows = _rows_to_dicts(
        db.execute(
            """
            SELECT from_location, to_location, direction, description, locked, hidden,
                   travel_cost_hours, terrain_type
            FROM exits
            WHERE COALESCE(hidden, 0) = 0
            ORDER BY from_location, to_location, direction
            """
        ).fetchall()
    )
    edges = [
        {
            "from": row["from_location"],
            "to": row["to_location"],
            "direction": row.get("direction") or "",
            "description": row.get("description") or "",
            "locked": bool(row.get("locked")),
            "travel_cost_hours": float(row.get("travel_cost_hours") or 0),
            "terrain_type": row.get("terrain_type") or "trail",
        }
        for row in edge_rows
    ]

    return {
        "locations": locations,
        "edges": edges,
        "bounds": bounds,
        "viewbox": {"width": VIEWBOX_WIDTH, "height": VIEWBOX_HEIGHT},
    }
