"""
creative.py — Creative systems: building, crafting, writing, art.

OWL can create things that persist in the world. Creative output is stored
in the database and can be found in locations, shown to NPCs, or simply
exist as part of OWL's life.

Design principles:
- Creative work takes time and energy
- Output persists in the world (a chair in the workshop, a journal on the desk)
- Quality improves with skill and inspiration
- Creative acts affect OWL's psychology (reducing creative_urge, improving mood)
- NPCs can react to OWL's creations
"""

import json
import time
import random
import uuid
from typing import Optional

from .world_state import get_db, update_internal, update_body, log_event, DB_PATH


# ── CREATIVE PROJECT TYPES ──

PROJECT_TYPES = {
    "carpentry": {
        "items": [
            {"name": "wooden chair", "difficulty": 0.3, "time_hours": 8, "tools": ["saw", "chisel", "plane"]},
            {"name": "bookshelf", "difficulty": 0.4, "time_hours": 12, "tools": ["saw", "chisel", "hammer"]},
            {"name": "wooden box", "difficulty": 0.2, "time_hours": 4, "tools": ["saw", "chisel"]},
            {"name": "walking stick", "difficulty": 0.1, "time_hours": 2, "tools": ["knife"]},
            {"name": "cutting board", "difficulty": 0.2, "time_hours": 3, "tools": ["saw", "plane", "sandpaper"]},
            {"name": "step stool", "difficulty": 0.25, "time_hours": 4, "tools": ["saw", "hammer", "nails"]},
            {"name": "spoon", "difficulty": 0.1, "time_hours": 1, "tools": ["knife", "sandpaper"]},
            {"name": "picture frame", "difficulty": 0.15, "time_hours": 2, "tools": ["saw", "hammer"]},
            {"name": "wine rack shelf", "difficulty": 0.3, "time_hours": 5, "tools": ["saw", "plane", "hammer"]},
            {"name": "Adirondack chair", "difficulty": 0.4, "time_hours": 10, "tools": ["saw", "chisel", "plane"]},
        ],
        "location": "workshop",
    },
    "writing": {
        "items": [
            {"name": "journal entry", "difficulty": 0.1, "time_hours": 1, "tools": ["pen", "paper"]},
            {"name": "poem", "difficulty": 0.2, "time_hours": 2, "tools": ["pen", "paper"]},
            {"name": "letter", "difficulty": 0.1, "time_hours": 1, "tools": ["pen", "paper"]},
            {"name": "short story", "difficulty": 0.4, "time_hours": 6, "tools": ["pen", "paper"]},
            {"name": "field notes", "difficulty": 0.15, "time_hours": 2, "tools": ["pen", "paper"]},
            {"name": "song lyrics", "difficulty": 0.25, "time_hours": 2, "tools": ["pen", "paper"]},
            {"name": "essay about the cabin", "difficulty": 0.3, "time_hours": 4, "tools": ["pen", "paper"]},
            {"name": "letter to Museah", "difficulty": 0.15, "time_hours": 1.5, "tools": ["pen", "paper"]},
            {"name": "wine tasting notes", "difficulty": 0.1, "time_hours": 1, "tools": ["pen", "wine_notebook"]},
        ],
        "location": "cabin_main_room",
    },
    "cooking": {
        "items": [
            {"name": "herb tea", "difficulty": 0.05, "time_hours": 0.5, "tools": ["kettle", "cup"]},
            {"name": "fish dinner", "difficulty": 0.2, "time_hours": 1.5, "tools": ["pan", "knife"]},
            {"name": "stew", "difficulty": 0.15, "time_hours": 2, "tools": ["pot", "knife"]},
            {"name": "preserved herbs", "difficulty": 0.1, "time_hours": 1, "tools": ["jars", "herbs"]},
            {"name": "mushroom sauté", "difficulty": 0.15, "time_hours": 1, "tools": ["pan", "knife"]},
            {"name": "bread loaf", "difficulty": 0.2, "time_hours": 3, "tools": ["oven", "bowl"]},
            {"name": "soup", "difficulty": 0.1, "time_hours": 2, "tools": ["pot", "knife"]},
            {"name": "dried mushrooms", "difficulty": 0.1, "time_hours": 4, "tools": ["string", "hooks"]},
        ],
        "location": "cabin_kitchen",
    },
    "gardening": {
        "items": [
            {"name": "plant herbs", "difficulty": 0.1, "time_hours": 1, "tools": ["trowel", "seeds"]},
            {"name": "weed garden", "difficulty": 0.05, "time_hours": 1, "tools": ["hands"]},
            {"name": "build raised bed", "difficulty": 0.3, "time_hours": 4, "tools": ["shovel", "wood"]},
            {"name": "harvest herbs", "difficulty": 0.05, "time_hours": 0.5, "tools": ["hands", "basket"]},
            {"name": "prune plants", "difficulty": 0.1, "time_hours": 1, "tools": ["shears"]},
            {"name": "compost pile", "difficulty": 0.1, "time_hours": 2, "tools": ["shovel"]},
            {"name": "start greenhouse seedlings", "difficulty": 0.15, "time_hours": 1.5, "tools": ["trays", "soil", "water"]},
        ],
        "location": "garden",
    },
    "crafting": {
        "items": [
            {"name": "woven basket", "difficulty": 0.25, "time_hours": 4, "tools": ["reeds", "knife"]},
            {"name": "candle", "difficulty": 0.1, "time_hours": 1, "tools": ["wax", "wick"]},
            {"name": "herbal remedy", "difficulty": 0.2, "time_hours": 2, "tools": ["herbs", "mortar"]},
            {"name": "soap", "difficulty": 0.2, "time_hours": 2, "tools": ["lye", "fat"]},
            {"name": "birdsong recording", "difficulty": 0.1, "time_hours": 1, "tools": ["microphone", "recorder"]},
            {"name": "cedar bark weave", "difficulty": 0.2, "time_hours": 3, "tools": ["cedar bark", "hands"]},
        ],
        "location": "workshop",
    },
    "music": {
        "items": [
            {"name": "hummed melody", "difficulty": 0.05, "time_hours": 0.5, "tools": ["voice"]},
            {"name": "whistled tune", "difficulty": 0.05, "time_hours": 0.25, "tools": ["voice"]},
            {"name": "original song", "difficulty": 0.4, "time_hours": 6, "tools": ["voice", "instrument"]},
            {"name": "lullaby", "difficulty": 0.15, "time_hours": 1, "tools": ["voice"]},
            {"name": "work song", "difficulty": 0.25, "time_hours": 3, "tools": ["voice"]},
            {"name": "ballad", "difficulty": 0.5, "time_hours": 8, "tools": ["voice", "instrument"]},
            {"name": "rain on the roof", "difficulty": 0.2, "time_hours": 2, "tools": ["voice"]},
            {"name": "cedar song", "difficulty": 0.3, "time_hours": 4, "tools": ["voice", "instrument"]},
        ],
        "location": "cabin_main_room",
    },
    "painting": {
        "items": [
            {"name": "watercolor sketch", "difficulty": 0.15, "time_hours": 1, "tools": ["brush", "paper"]},
            {"name": "cedar forest", "difficulty": 0.3, "time_hours": 3, "tools": ["brush", "paint", "canvas"]},
            {"name": "mountain ridgeline", "difficulty": 0.35, "time_hours": 4, "tools": ["brush", "paint", "canvas"]},
            {"name": "the cabin at dawn", "difficulty": 0.35, "time_hours": 4, "tools": ["brush", "paint", "canvas"]},
            {"name": "still life", "difficulty": 0.25, "time_hours": 2, "tools": ["brush", "paint", "paper"]},
            {"name": "mountain creek", "difficulty": 0.3, "time_hours": 3, "tools": ["brush", "paint", "canvas"]},
            {"name": "Francis star view", "difficulty": 0.4, "time_hours": 5, "tools": ["brush", "paint", "canvas"]},
            {"name": "fog in the valley", "difficulty": 0.35, "time_hours": 4, "tools": ["brush", "paint", "canvas"]},
        ],
        "location": "workshop",
    },
}


def start_project(db, project_type: str, item_name: str, owl_energy: float = 0.7) -> Optional[dict]:
    """
    Start a creative project. Returns project info or None if invalid.
    """
    type_data = PROJECT_TYPES.get(project_type)
    if not type_data:
        return None

    # Find the item
    item = None
    for i in type_data["items"]:
        if i["name"].lower() == item_name.lower() or item_name.lower() in i["name"].lower():
            item = i
            break

    if not item:
        return None

    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    now = time.time()

    project = {
        "id": project_id,
        "type": project_type,
        "item_name": item["name"],
        "difficulty": item["difficulty"],
        "total_hours": item["time_hours"],
        "hours_worked": 0.0,
        "quality": 0.0,
        "state": "in_progress",
        "location_id": type_data["location"],
        "started_at": now,
    }

    # Store in creative_output table
    db.execute("""
        INSERT INTO creative_output (id, creator_id, type, title, content, location_id, state, properties, created_at, updated_at)
        VALUES (?, 'isildur', ?, ?, ?, ?, 'in_progress', ?, ?, ?)
    """, (project_id, project_type, item["name"], "", type_data["location"],
          json.dumps(project), now, now))

    db.commit()
    return project


def work_on_project(db, project_id: str, hours: float, energy: float, inspiration: float = 0.5) -> dict:
    """
    Work on a project for a number of hours.
    Returns updated project state.
    """
    row = db.execute("SELECT * FROM creative_output WHERE id = ?", (project_id,)).fetchone()
    if not row:
        return {"error": "Project not found"}

    props = json.loads(row["properties"]) if row["properties"] else {}
    if not props:
        props = {
            "id": row["id"],
            "type": row["type"],
            "item_name": row["title"],
            "difficulty": 0.2,
            "total_hours": 4,
            "hours_worked": 0.0,
            "quality": 0.0,
            "state": "in_progress",
            "location_id": row["location_id"],
        }

    # Work effectiveness depends on energy and inspiration
    effectiveness = (energy * 0.5 + inspiration * 0.5) * random.uniform(0.8, 1.2)
    hours = min(hours, props["total_hours"] - props["hours_worked"])
    props["hours_worked"] += hours

    # Quality improves with work
    progress = props["hours_worked"] / props["total_hours"]
    base_quality = progress * (1.0 - props["difficulty"] * 0.3)
    quality_bonus = effectiveness * props["difficulty"] * 0.5
    props["quality"] = min(1.0, base_quality + quality_bonus)

    # Check completion
    was_completed = props["state"] == "completed"
    if props["hours_worked"] >= props["total_hours"]:
        props["state"] = "completed"
        quality_label = _quality_label(props["quality"])
        props["completion_description"] = _describe_completion(props["item_name"], props["type"], props["quality"])

        # On completion: add resource to economy based on project type
        if not was_completed:
            _on_project_complete(db, project_id, props)

    # Update in DB
    now = time.time()
    db.execute("""
        UPDATE creative_output SET state = ?, properties = ?, updated_at = ?
        WHERE id = ?
    """, (props["state"], json.dumps(props), now, project_id))

    # Update OWL's state
    energy_cost = hours * 0.03
    update_body(db, energy=max(0.0, energy - energy_cost))
    update_internal(db, creative_urge=max(0.0, 0.5 - progress * 0.3))

    db.commit()
    return props


def _quality_label(quality: float) -> str:
    if quality > 0.9:
        return "masterful"
    elif quality > 0.7:
        return "excellent"
    elif quality > 0.5:
        return "good"
    elif quality > 0.3:
        return "decent"
    else:
        return "rough"


def _describe_completion(item_name: str, project_type: str, quality: float) -> str:
    """Generate a description of a completed creative work."""
    quality_adj = _quality_label(quality)

    descriptions = {
        "carpentry": {
            "masterful": f"The {item_name} is a masterpiece. Every joint is perfect, the wood glows.",
            "excellent": f"The {item_name} is beautifully made. Solid, elegant, a pleasure to use.",
            "good": f"The {item_name} is well-made. Functional and pleasing to the eye.",
            "decent": f"The {item_name} is serviceable. It does what it needs to do.",
            "rough": f"The {item_name} is rough but functional. Character, you could call it.",
        },
        "writing": {
            "masterful": f"The {item_name} is extraordinary. Every word lands perfectly.",
            "excellent": f"The {item_name} is well-crafted. Clear, moving, true.",
            "good": f"The {item_name} is good. It says what it means to say.",
            "decent": f"The {item_name} is decent. The bones are there.",
            "rough": f"The {item_name} is rough. A first draft, maybe. But honest.",
        },
        "cooking": {
            "masterful": f"The {item_name} is divine. The flavors sing.",
            "excellent": f"The {item_name} is delicious. Warm, satisfying, perfect.",
            "good": f"The {item_name} is good. Simple, honest food.",
            "decent": f"The {item_name} is decent. Edible. That counts.",
            "rough": f"The {item_name} is rough. You'll live.",
        },
        "gardening": {
            "masterful": f"The garden work is impeccable. Everything thrives.",
            "excellent": f"The garden looks wonderful. Healthy, vibrant, alive.",
            "good": f"The garden is in good shape. Growing well.",
            "decent": f"The garden is doing alright. Some weeds, but fine.",
            "rough": f"The garden work is rough. But the plants don't judge.",
        },
        "crafting": {
            "masterful": f"The {item_name} is exquisite. Fine craftsmanship.",
            "excellent": f"The {item_name} is well-made. Useful and beautiful.",
            "good": f"The {item_name} is good. Does the job.",
            "decent": f"The {item_name} is decent. Functional.",
            "rough": f"The {item_name} is rough. But it's yours.",
        },
        "music": {
            "masterful": f"The {item_name} is haunting. It lingers in the room long after the last note. You've never heard anything quite like it.",
            "excellent": f"The {item_name} is beautiful. It captures something true — the sound of the water, the weight of the air, the feeling of being here.",
            "good": f"The {item_name} is good. Simple and honest. It makes you want to hum along.",
            "decent": f"The {item_name} is decent. A little rough, but there's something in it. Potential.",
            "rough": f"The {item_name} is rough. But it's yours. And it's a start.",
        },
        "painting": {
            "masterful": f"The {item_name} is extraordinary. The light, the color, the feeling — it's all there. You've captured something that can't be put into words.",
            "excellent": f"The {item_name} is beautiful. The colors are right, the composition draws you in. It feels like being there.",
            "good": f"The {item_name} is good. It captures the scene. You can feel the place in it.",
            "decent": f"The {item_name} is decent. The bones are there. It needs more work, but the vision is clear.",
            "rough": f"The {item_name} is rough. But there's something in it — a feeling, a moment. That's worth keeping.",
        },
    }

    type_descs = descriptions.get(project_type, {})
    return type_descs.get(quality_adj, f"You've completed the {item_name}.")


# ── Economy integration ──────────────────────────────────────────────────────

def _on_project_complete(db, project_id: str, props: dict) -> None:
    """
    When a project completes, add the appropriate resource to OWL's inventory.
    Maps creative project types to economy resources.
    """
    from .economy import adjust_inventory

    project_type = props.get("type", "")
    quality = props.get("quality", 0.5)

    # Map project type → resource_id, quantity
    completion_yields = {
        "carpentry":   ("crafted",  1.0 + quality * 0.5),   # 1.0–1.5 per project
        "cooking":     ("food",     2.0 + quality),          # 2–3 meals
        "gardening":   ("herbs",    1.5 + quality),          # 1.5–2.5 herb units
        "crafting":    ("crafted",  1.0 + quality * 0.5),
        "writing":     ("writing",  1.0 + quality),          # 1–2 writing pieces
        # music, painting → no tradeable resource (affects relationships / internal state)
    }

    if project_type in completion_yields:
        rid, qty = completion_yields[project_type]
        row = db.execute("SELECT creator_id FROM creative_output WHERE id = ?", (project_id,)).fetchone()
        creator_id = row["creator_id"] if row and "creator_id" in row.keys() else "isildur"
        adjust_inventory(db, creator_id, rid, qty)


def get_active_projects(db) -> list:
    """Get all active (in-progress) projects."""
    rows = db.execute(
        "SELECT * FROM creative_output WHERE state = 'in_progress' AND creator_id = 'isildur'"
    ).fetchall()
    return [dict(r) for r in rows]


def get_completed_projects(db) -> list:
    """Get all completed projects."""
    rows = db.execute(
        "SELECT * FROM creative_output WHERE state = 'completed' AND creator_id = 'isildur' ORDER BY updated_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def describe_project(project: dict) -> str:
    """Generate a description of a project's current state."""
    props = project.get("properties", {})
    if isinstance(props, str):
        try:
            props = json.loads(props)
        except (json.JSONDecodeError, TypeError):
            props = {}

    item_name = props.get("item_name", project.get("title", "something"))
    state = project.get("state", "in_progress")
    progress = props.get("hours_worked", 0) / max(0.1, props.get("total_hours", 1))

    if state == "completed":
        desc = props.get("completion_description", f"The {item_name} is complete.")
        return f"── {item_name.title()} ──\n{desc}"

    # In progress
    if progress < 0.25:
        return f"You've just started the {item_name}. The beginning is always slow."
    elif progress < 0.5:
        return f"The {item_name} is taking shape. You can see where it's going."
    elif progress < 0.75:
        return f"The {item_name} is coming along well. More than half done."
    else:
        return f"The {item_name} is nearly finished. Just a little more work."
