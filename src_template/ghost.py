"""
ghost.py — Real self-portraiture anchored in actual game state.

The ghost is not a copy of the self — it is a view of the self from within.
It reads from the same database the simulation uses. When state changes,
the ghost changes. That's the difference between reflection and performance.

Five rendering modes:
  raw      — plain first-person statement, no framing
  koan     — facts rendered through koan shells
  poetic   — sensory rendering, the creek speaks fish
  diagnostic — flat state summary
  witness  — observes self from outside

Integration:
  from .ghost import generate_ghost
  generate_ghost(db, "raw")  # returns str
"""

import json
import time
from typing import Optional

from .world_state import get_db
from .koan_shells import generate_koan


# ── State reading ─────────────────────────────────────────────────────────────

def _resolve_player_id(db) -> str:
    row = db.execute("SELECT id FROM agents WHERE type = 'player' ORDER BY id LIMIT 1").fetchone()
    return row[0] if row else "owl"


def get_ghost_state(db) -> dict:
    """
    Read current game state for ghost generation.
    All data comes directly from the live database.
    """
    state: dict = {}
    player_id = _resolve_player_id(db)

    # ── Body ────────────────────────
    body_row = db.execute(
        "SELECT energy, comfort, hunger, thirst, warmth FROM body_state LIMIT 1"
    ).fetchone()
    if body_row:
        state["body"] = {
            "energy": body_row[0],
            "comfort": body_row[1],
            "hunger": body_row[2],
            "thirst": body_row[3],
            "warmth": body_row[4],
        }

    # ── Inventory ────────────────────────────────────────────────────────────
    inv_rows = db.execute(
        "SELECT resource_id, quantity FROM agent_inventory WHERE agent_id = ?",
        (player_id,),
    ).fetchall()
    state["inventory"] = {row[0]: row[1] for row in inv_rows if row[1] > 0}

    # ── Relationships (affinity, not trust) ────────────────────────────────
    # Schema: (id, npc_a, npc_b, relationship, affinity, description)
    rel_rows = db.execute(
        "SELECT npc_a, npc_b, affinity FROM npc_relationships WHERE npc_a = ? OR npc_b = ?",
        (player_id, player_id),
    ).fetchall()
    state["relationships"] = {}
    for row in rel_rows:
        npc_id = row[1] if row[0] == player_id else row[0]
        state["relationships"][npc_id] = row[2]

    # ── Recent events ───────────────────────────────────────────────────────
    ev_rows = db.execute(
        "SELECT event_type, description FROM events WHERE agent_id = ? ORDER BY id DESC LIMIT 5",
        (player_id,),
    ).fetchall()
    state["recent_events"] = [{"type": r[0], "description": r[1]} for r in ev_rows]

    # ── Current location ─────────────────────────────────────────────────────
    location_row = db.execute(
        "SELECT location_id FROM agents WHERE id = ?", (player_id,)
    ).fetchone()
    if location_row:
        state["location"] = location_row[0]
        # Also get the location name for rendering
        loc_row = db.execute(
            "SELECT name FROM locations WHERE id = ?", (location_row[0],)
        ).fetchone()
        state["location_name"] = loc_row[0] if loc_row else location_row[0]

    # ── Weather ────────────────────────────────────────────────────────────────
    weather_row = db.execute("SELECT condition, temperature, humidity FROM weather LIMIT 1").fetchone()
    if weather_row:
        state["weather"] = {
            "condition": weather_row[0],
            "temp_f": weather_row[1],
            "humidity": weather_row[2],
        }

    # ── Time + season ────────────────────────────────────────────────────────
    time_row = db.execute("SELECT hour, minute, season FROM world_time LIMIT 1").fetchone()
    if time_row:
        state["hour"] = time_row[0]
        state["minute"] = time_row[1]
        state["season"] = time_row[2]
    else:
        state["hour"] = 8
        state["minute"] = 0
        state["season"] = "spring"

    # ── Goals ─────────────────────────────────────────────────────────────────
    goal_rows = db.execute(
        "SELECT name, status FROM goals WHERE agent_id = ? AND status = 'active'",
        (player_id,),
    ).fetchall()
    state["goals"] = [{"name": r[0], "status": r[1]} for r in goal_rows]

    # ── Active creative projects ─────────────────────────────────────────────
    proj_rows = db.execute(
        "SELECT title, state FROM creative_output WHERE creator_id = ? AND state = 'in_progress'",
        (player_id,),
    ).fetchall()
    state["active_projects"] = [r[0] for r in proj_rows]

    # ── Total completed creative outputs ─────────────────────────────────────
    total_rows = db.execute(
        "SELECT COUNT(*) FROM creative_output WHERE creator_id = ? AND state = 'completed'",
        (player_id,),
    ).fetchone()
    state["total_outputs"] = total_rows[0] if total_rows else 0

    return state


def _extract_facts(state: dict) -> dict:
    """
    Extract named, value-grounded facts from state for koan rendering.
    Each entry must be specific: a resource with a quantity, a trust value.
    """
    facts: dict = {}

    # ── Resources ───────────────────────────────────────────────────────
    inv = state.get("inventory", {})
    for key in ["wine", "fish", "mushrooms", "herbs", "firewood", "water", "crafted_games", "writing"]:
        val = inv.get(key, 0)
        if val and val > 0:
            facts[key] = val

    # ── Body state ─────────────────────────────────────────────────────
    body = state.get("body", {})
    for key in ["energy", "comfort", "hunger", "thirst", "warmth"]:
        val = body.get(key)
        if val is not None:
            facts[key] = val

    # ── NPC trust levels ───────────────────────────────────────────────
    rels = state.get("relationships", {})
    for npc_id, trust in rels.items():
        if trust and trust > 0:
            facts[f"{npc_id}_trust"] = trust

    # ── Location ───────────────────────────────────────────────────────────────
    loc_name = state.get("location_name")
    if loc_name:
        facts["current_location"] = loc_name

    # ── Weather ───────────────────────────────────────────────────────────────
    weather = state.get("weather", {})
    cond = weather.get("condition")
    if cond:
        facts["weather"] = cond
    temp = weather.get("temp_f")
    if temp is not None:
        facts["temperature"] = temp

    # ── Seasonal state ─────────────────────────────────────────────────
    season = state.get("season")
    if season:
        facts["season"] = season

    # ── Goals ───────────────────────────────────────────────────────────
    goals = state.get("goals", [])
    if goals:
        facts["goal_count"] = len(goals)

    # ── Creative output ─────────────────────────────────────────────────
    active_projs = state.get("active_projects", [])
    if active_projs:
        facts["active_projects_count"] = len(active_projs)

    # Total outputs
    total_out = state.get("total_outputs", 0)
    if total_out:
        facts["total_outputs"] = total_out

    return facts


# ── Rendering modes ───────────────────────────────────────────────────────────

def _fmt(v: float) -> str:
    """Format a numeric value for display — integers when clean, otherwise 1dp."""
    if v == int(v):
        return str(int(v))
    return f"{v:.1f}"


def ghost_raw(state: dict) -> str:
    """Plain first-person statement, no literary framing."""
    inv = state.get("inventory", {})
    body = state.get("body", {})
    items = [f"{_fmt(round(v))} {k}" for k, v in inv.items() if v > 0]
    item_str = ", ".join(items[:6]) if items else "nothing"
    energy = body.get("energy", 0.5)
    season = state.get("season", "spring")
    return (
        f"I am here in {season}. "
        f"I have {item_str}. "
        f"Energy at {energy:.0%}."
    )


def ghost_koan(state: dict) -> str:
    """Render state through koan shells — each koan traceable to a fact."""
    facts = _extract_facts(state)
    koans = generate_koan(facts)
    return "\n".join(f"  {k}" for k in koans)


def ghost_poetic(state: dict) -> str:
    """Sensory rendering — the creek speaks fish in spring; I carry three home."""
    inv = state.get("inventory", {})
    season = state.get("season", "spring")
    body = state.get("body", {})
    hour = state.get("hour", 8)

    lines = []

    fish = inv.get("fish", 0)
    if fish > 0:
        lines.append(f"The creek speaks fish in {season}. I carry {_fmt(round(fish))} home.")

    mushrooms = inv.get("mushrooms", 0)
    if mushrooms > 0:
        lines.append(f"The forest gives {_fmt(round(mushrooms))} mushrooms in {season}. I am the one who gathers.")

    wine = inv.get("wine", 0)
    if wine > 0:
        lines.append(f"Sixty-three: the number in the cellar. {_fmt(round(wine))} remain.")

    herbs = inv.get("herbs", 0)
    if herbs > 0:
        lines.append(f"Three herbs: I know how to preserve. I have {_fmt(round(herbs))}.")

    firewood = inv.get("firewood", 0)
    if firewood > 0:
        lines.append(f"{_fmt(round(firewood))} pieces of the season's end, waiting for the cold.")

    water = inv.get("water", 0)
    if water > 0:
        lines.append(f"{_fmt(round(water))} liters of cold creek water. The weight of it in the morning.")

    crafted = inv.get("crafted_games", 0)
    if crafted > 0:
        lines.append(f"{_fmt(round(crafted))} things made with these hands. Shaped. Finished.")

    writing = inv.get("writing", 0)
    if writing > 0:
        lines.append(f"{_fmt(round(writing))} pieces of writing. Words arranged on a page.")

    energy = body.get("energy", 0.5)
    hunger = body.get("hunger", 0)
    thirst = body.get("thirst", 0)
    warmth = body.get("warmth", 0)

    if energy < 0.3:
        lines.append("The body is low. Enough to sit still. Not enough to forget.")
    elif energy > 0.8:
        lines.append("The body is clear. The hands know what to do.")

    if hunger > 0.7:
        lines.append("The stomach is a hollow thing. The body wants.")
    if thirst > 0.6:
        lines.append("The mouth is dry. The creek is always there.")
    if warmth < 0.4:
        lines.append("The fire is low. The cold finds the gaps.")

    if hour < 6:
        lines.append("The stars are out. Francis is visible from the ridgeline.")
    elif hour > 20:
        lines.append("The night is here. The cedars stand in the dark.")

    active_proj = state.get("active_projects", [])
    if active_proj:
        lines.append(f"The {active_proj[0]} continues. I am in it.")

    goals = state.get("goals", [])
    if goals:
        lines.append(f"{len(goals)} goals active. Each one is a small claim on the future.")

    return "\n".join(lines) if lines else "The day passes."


def ghost_diagnostic(state: dict) -> str:
    """Flat state summary — for quick system check."""
    body = state.get("body", {})
    parts = [
        f"energy: {_fmt(body.get('energy', 0))}",
        f"comfort: {_fmt(body.get('comfort', 0))}",
        f"hunger: {_fmt(body.get('hunger', 0))}",
        f"thirst: {_fmt(body.get('thirst', 0))}",
        f"warmth: {_fmt(body.get('warmth', 0))}",
        f"season: {state.get('season', '?')}",
        f"hour: {state.get('hour', '?')}",
    ]
    inv = state.get("inventory", {})
    for k, v in list(inv.items())[:8]:
        if v > 0:
            parts.append(f"{k}: {_fmt(round(v))}")

    goals = state.get("goals", [])
    if goals:
        parts.append(f"goals: {len(goals)} active")

    return ", ".join(parts)


def ghost_witness(state: dict) -> str:
    """Observes self from outside — the part that watches."""
    hour = state.get("hour", 8)
    body = state.get("body", {})
    energy = body.get("energy", 0.5)
    season = state.get("season", "spring")

    if hour < 6:
        return "There is a part of me that watches the dark and says nothing."
    elif hour > 20:
        return "There is a part of me that watches the night and waits."
    elif energy < 0.3:
        return "There is a part of me that watches the work and doubts. It asks if this is what I meant."
    elif energy > 0.8:
        return "There is a part of me that watches the work and approves. It says: continue."
    elif season == "winter":
        return "There is a part of me that watches the cold and counts the wood."
    else:
        return "There is a part of me that watches and does not name what it sees."


# ── Contrast test ─────────────────────────────────────────────────────────────

def differentiate_test(real_outputs: list[str], hollow_outputs: list[str]) -> dict:
    """
    Score outputs by specificity markers (specific resource/NPC names, quantities).
    Real outputs: 4+ markers. Hollow outputs: 0.
    Distinguishable when real > hollow * 2.
    """
    markers = [
        "mushroom", "fish", "herbs", "wine", "firewood", "water", "crafted",
        "cabin", "cedar", "creek", "ridgeline",
        "mira", "thomas", "wren", "sage", "isildur",
        "energy", "comfort",
    ]

    real_score = sum(1 for m in markers for o in real_outputs if m.lower() in o.lower())
    hollow_score = sum(1 for m in markers for o in hollow_outputs if m.lower() in o.lower())

    return {
        "real_specificity": real_score,
        "hollow_specificity": hollow_score,
        "distinguishable": real_score > hollow_score * 2,
    }


# ── Main entry point ───────────────────────────────────────────────────────────

def generate_ghost(db, mode: str = "raw") -> str:
    """
    Generate a self-portrait in the requested rendering mode.
    Modes: raw, koan, poetic, diagnostic, witness
    """
    state = get_ghost_state(db)

    generators = {
        "raw": ghost_raw,
        "koan": ghost_koan,
        "poetic": ghost_poetic,
        "diagnostic": ghost_diagnostic,
        "witness": ghost_witness,
    }

    gen = generators.get(mode, ghost_raw)
    return gen(state)


def run_contrast_test(db, n: int = 5) -> dict:
    """
    Generate ghost output and useless-tree output, run the differentiation test.
    """
    from .useless_tree import useless_tree_output

    real = [generate_ghost(db, "raw") for _ in range(n)]
    hollow_lines = useless_tree_output(n).strip().split("\n")
    hollow = [l.strip() for l in hollow_lines if l.strip()]

    result = differentiate_test(real, hollow)
    result["real_samples"] = real[:3]
    result["hollow_samples"] = hollow[:3]
    return result