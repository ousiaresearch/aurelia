"""
economy.py — resource production, consumption, and trade.

The cabin economy is small, personal, and seasonal. Resources flow between
agents (OWL + NPCs) through production, consumption, and direct trade.
"""

import json
import time
import random
from typing import Optional

from .world_state import get_db


# ── Resource Definitions ───────────────────────────────────────────────────────

# Resource IDs — used everywhere as foreign keys
RESOURCE_FIREWOOD = "firewood"
RESOURCE_MUSHROOMS = "mushrooms"
RESOURCE_HERBS = "herbs"
RESOURCE_FISH = "fish"
RESOURCE_WINE = "wine"
RESOURCE_WATER = "water"
RESOURCE_GAMES = "crafted_games"
RESOURCE_WRITING = "writing"

RESOURCE_DEFINITIONS = {
    RESOURCE_FIREWOOD: {
        "name": "Firewood",
        "unit": "bundle",
        "category": "fuel",
        "perishable": 0,
        "decay_rate": 0.0,
    },
    RESOURCE_MUSHROOMS: {
        "name": "Mushrooms",
        "unit": "handful",
        "category": "food",
        "perishable": 1,
        "decay_rate": 0.04,  # ~4% decay per tick (24h real time)
    },
    RESOURCE_HERBS: {
        "name": "Herbs",
        "unit": "bunch",
        "category": "food",
        "perishable": 1,
        "decay_rate": 0.03,
    },
    RESOURCE_FISH: {
        "name": "Fish",
        "unit": "fillets",
        "category": "food",
        "perishable": 1,
        "decay_rate": 0.05,
    },
    RESOURCE_WINE: {
        "name": "Wine",
        "unit": "bottle",
        "category": "luxury",
        "perishable": 0,
        "decay_rate": 0.0,
    },
    RESOURCE_WATER: {
        "name": "Water",
        "unit": "liter",
        "category": "essential",
        "perishable": 0,
        "decay_rate": 0.0,
    },
    RESOURCE_GAMES: {
        "name": "Games",
        "unit": "item",
        "category": "crafted",
        "perishable": 0,
        "decay_rate": 0.0,
    },
    RESOURCE_WRITING: {
        "name": "Writing",
        "unit": "piece",
        "category": "creative",
        "perishable": 0,
        "decay_rate": 0.0,
    },
}


# ── NPC Production Profiles ────────────────────────────────────────────────────

# Occupation → resource production mapping (applied dynamically to any world).
# Each NPC with a matching occupation gets the listed production profile.
# Format: {resource_id: {weight: float, seasons: list, weathers: list}}
OCCUPATION_PRODUCTION = {
    # Gatherers / foragers
    "forager": {
        RESOURCE_MUSHROOMS: {"weight": 0.6, "seasons": ["spring", "autumn"], "weathers": ["rainy", "foggy"]},
        RESOURCE_HERBS: {"weight": 0.3, "seasons": ["spring", "summer", "autumn"], "weathers": []},
    },
    "forest_keeper": {
        RESOURCE_FIREWOOD: {"weight": 0.4, "seasons": ["autumn", "winter"], "weathers": []},
        RESOURCE_HERBS: {"weight": 0.3, "seasons": ["spring", "summer"], "weathers": []},
    },
    "forest_ranger": {
        RESOURCE_FIREWOOD: {"weight": 0.3, "seasons": ["autumn", "winter"], "weathers": []},
        RESOURCE_MUSHROOMS: {"weight": 0.2, "seasons": ["spring", "autumn"], "weathers": ["rainy", "foggy"]},
    },
    "park_ranger": {
        RESOURCE_FIREWOOD: {"weight": 0.3, "seasons": ["autumn", "winter"], "weathers": []},
    },
    # Farmers / growers
    "farmer": {
        RESOURCE_MUSHROOMS: {"weight": 0.5, "seasons": ["spring", "summer", "autumn"], "weathers": []},
        RESOURCE_HERBS: {"weight": 0.4, "seasons": ["spring", "summer"], "weathers": []},
    },
    "gardener": {
        RESOURCE_HERBS: {"weight": 0.5, "seasons": ["spring", "summer"], "weathers": []},
    },
    # Anglers / fishers
    "fisherman": {
        RESOURCE_FISH: {"weight": 0.6, "seasons": ["spring", "summer", "autumn"], "weathers": []},
    },
    "fishing_guide": {
        RESOURCE_FISH: {"weight": 0.5, "seasons": ["spring", "summer", "autumn"], "weathers": []},
    },
    "surf_instructor": {
        RESOURCE_FISH: {"weight": 0.3, "seasons": ["spring", "summer"], "weathers": []},
    },
    # Creatives
    "writer": {
        RESOURCE_WRITING: {"weight": 0.8, "seasons": ["any"], "weathers": []},
    },
    "artist": {
        RESOURCE_WRITING: {"weight": 0.4, "seasons": ["any"], "weathers": []},
    },
    "musician": {
        RESOURCE_WRITING: {"weight": 0.3, "seasons": ["any"], "weathers": []},
    },
    "painter_printmaker": {
        RESOURCE_WRITING: {"weight": 0.5, "seasons": ["any"], "weathers": []},
    },
    # Hermits / retirees
    "hermit": {
        RESOURCE_FIREWOOD: {"weight": 0.4, "seasons": ["any"], "weathers": []},
        RESOURCE_WRITING: {"weight": 0.5, "seasons": ["any"], "weathers": []},
    },
    "retired_ranger": {
        RESOURCE_FIREWOOD: {"weight": 0.2, "seasons": ["autumn", "winter"], "weathers": []},
    },
    "retired_rancher": {
        RESOURCE_FIREWOOD: {"weight": 0.2, "seasons": ["autumn", "winter"], "weathers": []},
    },
    # Bakers / food
    "baker": {
        RESOURCE_MUSHROOMS: {"weight": 0.3, "seasons": ["any"], "weathers": []},
    },
    "barista": {
        RESOURCE_HERBS: {"weight": 0.2, "seasons": ["any"], "weathers": []},
    },
    "coffee_shop_owner": {
        RESOURCE_HERBS: {"weight": 0.2, "seasons": ["any"], "weathers": []},
    },
    # Uncategorized producers — give them something low-key
    "mechanic": {
        RESOURCE_FIREWOOD: {"weight": 0.1, "seasons": ["any"], "weathers": []},
    },
    "hardware_store_owner": {
        RESOURCE_FIREWOOD: {"weight": 0.1, "seasons": ["any"], "weathers": []},
    },
}

# ── Dynamic producer discovery (replaces hardcoded NPC_PRODUCTION) ──────

def _build_npc_production(db) -> dict:
    """Discover which NPCs in THIS world are producers based on their occupations."""
    import json
    production = {}
    all_npcs = db.execute("SELECT id, properties FROM agents WHERE type='npc'").fetchall()
    for npc in all_npcs:
        try:
            props = json.loads(npc["properties"]) if isinstance(npc["properties"], str) else (npc["properties"] or {})
        except (json.JSONDecodeError, TypeError):
            props = {}
        occupation = (props.get("occupation") or props.get("role") or "").lower().replace(" ", "_")
        if occupation in OCCUPATION_PRODUCTION:
            production[npc["id"]] = OCCUPATION_PRODUCTION[occupation]
    return production

# Seasonal consumption rates per agent per tick (in resource units)
# Each tick = 1 hour world time
CONSUMPTION_RATES = {
    "firewood": {"winter": 0.05, "autumn": 0.02, "other": 0.0},
    "food": {"winter": 0.03, "autumn": 0.02, "summer": 0.015, "spring": 0.02},
    "water": {"any": 0.04},
    "wine": {"any": 0.01},  # occasional glass, not daily necessity
}


# ── Initialization ─────────────────────────────────────────────────────────────

def seed_resources(db) -> None:
    """Insert all resource definitions into the resources table."""
    now = time.time()
    for rid, defn in RESOURCE_DEFINITIONS.items():
        db.execute(
            """INSERT OR IGNORE INTO resources
               (id, name, unit, category, perishable, decay_rate, properties, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (rid, defn["name"], defn["unit"], defn["category"],
             defn["perishable"], defn["decay_rate"], json.dumps(defn), now)
        )


def seed_resource_nodes(db) -> None:
    """
    Create resource nodes at harvestable locations.
    Only inserts nodes whose location_id already exists in the database.
    """
    from src.world_state import DB_PATH
    import sqlite3

    # Check which locations actually exist
    ref = sqlite3.connect(DB_PATH)
    existing_locs = {r[0] for r in ref.execute("SELECT id FROM locations").fetchall()}
    ref.close()

    now = time.time()

    # All node definitions — mismatched ones are silently skipped
    node_inserts = [
        ("node_creek_fish",              "mountain_creek", "fish",      "summer", 2.0, 48),
        ("node_forest_mushrooms_autumn", "forest_edge",    "mushrooms", "autumn", 3.0, 36),
        ("node_forest_mushrooms_spring", "forest_edge",    "mushrooms", "spring", 2.0, 48),
        ("node_garden_herbs_summer",     "garden",         "herbs",     "summer", 2.0, 72),
        ("node_garden_herbs_autumn",     "garden",         "herbs",     "autumn", 1.5, 72),
        ("node_trail_firewood",          "cedar_trail",    "firewood",  "autumn", 4.0, 168),
    ]

    for node in node_inserts:
        node_id, loc_id, res_id, season, yield_h, cooldown = node
        if loc_id not in existing_locs:
            continue  # skip — location doesn't exist yet
        db.execute(
            """INSERT OR IGNORE INTO resource_nodes
               (id, location_id, resource_id, season, yield_per_harvest, cooldown_hours, last_harvested, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 0, ?)""",
            (node_id, loc_id, res_id, season, yield_h, cooldown, now)
        )


def seed_initial_inventory(db) -> None:
    """Seed starting inventory for OWL and NPCs."""
    now = time.time()

    starting_inventory = {
        "attilleo": {
            RESOURCE_WATER: 10.0,
            RESOURCE_HERBS: 3.0,
            RESOURCE_WRITING: 5.0,
            RESOURCE_WINE: 6.0,          # NW wine country
        },
        "npc_ivy": {
            RESOURCE_HERBS: 4.0,
            RESOURCE_WATER: 5.0,
        },
        "npc_robin": {
            RESOURCE_MUSHROOMS: 6.0,
            RESOURCE_FIREWOOD: 8.0,
        },
        "npc_dom": {
            RESOURCE_WRITING: 3.0,      # ex-software dev
        },
        "npc_solomon": {
            RESOURCE_FISH: 4.0,
        },
    }

    for agent_id, inv in starting_inventory.items():
        for resource_id, qty in inv.items():
            db.execute(
                """INSERT OR REPLACE INTO agent_inventory
                   (agent_id, resource_id, quantity, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (agent_id, resource_id, qty, now)
            )


# ── Core Economy Functions ─────────────────────────────────────────────────────

def get_inventory(db, agent_id: str) -> dict:
    """Return a dict of {resource_id: quantity} for an agent."""
    rows = db.execute(
        "SELECT resource_id, quantity FROM agent_inventory WHERE agent_id = ?",
        (agent_id,)
    ).fetchall()
    return {r["resource_id"]: r["quantity"] for r in rows}


def adjust_inventory(db, agent_id: str, resource_id: str, delta: float) -> float:
    """
    Adjust an agent's inventory by delta units.
    Returns the new quantity (0 if not enough, clamped to 0).
    """
    now = time.time()
    row = db.execute(
        "SELECT quantity FROM agent_inventory WHERE agent_id = ? AND resource_id = ?",
        (agent_id, resource_id)
    ).fetchone()

    if row is None:
        if delta < 0:
            return 0.0
        db.execute(
            """INSERT INTO agent_inventory (agent_id, resource_id, quantity, updated_at)
               VALUES (?, ?, ?, ?)""",
            (agent_id, resource_id, max(0, delta), now)
        )
        return max(0, delta)

    new_qty = max(0, row["quantity"] + delta)
    db.execute(
        "UPDATE agent_inventory SET quantity = ?, updated_at = ? WHERE agent_id = ? AND resource_id = ?",
        (new_qty, now, agent_id, resource_id)
    )
    return new_qty


def transfer(db, from_agent: str, to_agent: str, resource_id: str, quantity: float) -> bool:
    """
    Transfer resources from one agent to another.
    Returns True if successful, False if insufficient.
    """
    from_qty = db.execute(
        "SELECT quantity FROM agent_inventory WHERE agent_id = ? AND resource_id = ?",
        (from_agent, resource_id)
    ).fetchone()
    if from_qty is None or from_qty["quantity"] < quantity:
        return False

    adjust_inventory(db, from_agent, resource_id, -quantity)
    adjust_inventory(db, to_agent, resource_id, quantity)

    db.execute(
        """INSERT INTO trade_log (buyer_id, seller_id, resource_id, quantity, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (to_agent, from_agent, resource_id, quantity, f"direct transfer", time.time())
    )
    return True


# ── Economy Tick ──────────────────────────────────────────────────────────────

def economy_tick(db) -> dict:
    """
    Run one economy tick (called from simulation.tick()).
    Handles: NPC production, NPC consumption, NPC buying/selling, perishable decay.
    Returns a summary dict of what happened.
    """
    now = time.time()
    summary = {"produced": [], "consumed": [], "decayed": [], "traded": []}

    # Get current season and time
    time_row = db.execute("SELECT season FROM world_time WHERE id = 1").fetchone()
    season = time_row["season"] if time_row else "spring"

    # 1. NPC PRODUCTION — each NPC with a matching occupation produces resources
    npc_production = _build_npc_production(db)
    for npc_id, profile in npc_production.items():
        for resource_id, cfg in profile.items():
            # Check season match
            if "any" not in cfg["seasons"] and season not in cfg["seasons"]:
                continue

            # Check weather match
            weather_row = db.execute("SELECT condition FROM weather WHERE id = 1").fetchone()
            if weather_row and cfg["weathers"] and weather_row["condition"] not in cfg["weathers"]:
                continue

            # Produce with some randomness (70% chance per tick when conditions met)
            if random.random() < 0.7:
                yield_amount = random.uniform(0.5, 1.5)
                old_qty = adjust_inventory(db, npc_id, resource_id, yield_amount)
                summary["produced"].append({
                    "agent": npc_id,
                    "resource": resource_id,
                    "amount": round(yield_amount, 2)
                })

    # 2. CONSUMPTION — all agents consume food/water at basic rates
    all_agents = db.execute("SELECT id FROM agents").fetchall()
    for agent_row in all_agents:
        agent_id = agent_row["id"]

        # Water — consumed every tick
        water_rate = CONSUMPTION_RATES.get("water", {}).get("any", 0.04)
        adjust_inventory(db, agent_id, RESOURCE_WATER, -water_rate)

        # Food — seasonal rate (approximated as total food categories)
        food_rate = CONSUMPTION_RATES.get("food", {}).get(season,
            CONSUMPTION_RATES.get("food", {}).get("spring", 0.02))
        food_resources = [RESOURCE_MUSHROOMS, RESOURCE_HERBS, RESOURCE_FISH]
        for fr in food_resources:
            inv = get_inventory(db, agent_id)
            if inv.get(fr, 0) > 0:
                consumed = min(food_rate, inv.get(fr, 0))
                adjust_inventory(db, agent_id, fr, -consumed)
                if consumed > 0:
                    summary["consumed"].append({
                        "agent": agent_id,
                        "resource": fr,
                        "amount": round(consumed, 3)
                    })

        # Firewood in winter
        if season == "winter":
            fw_rate = CONSUMPTION_RATES.get("firewood", {}).get("winter", 0.05)
            adjust_inventory(db, agent_id, RESOURCE_FIREWOOD, -fw_rate)

        # Wine — occasional small consumption for the active player.
        agent_type_row = db.execute("SELECT type FROM agents WHERE id = ?", (agent_id,)).fetchone()
        if agent_type_row and agent_type_row["type"] == "player" and random.random() < 0.1:
            wine_rate = CONSUMPTION_RATES.get("wine", {}).get("any", 0.01)
            inv = get_inventory(db, agent_id)
            if inv.get(RESOURCE_WINE, 0) > 0:
                adjust_inventory(db, agent_id, RESOURCE_WINE, -wine_rate)
                summary["consumed"].append({
                    "agent": agent_id,
                    "resource": RESOURCE_WINE,
                    "amount": wine_rate
                })

    # 3. NPC BUYING/SELLING — each NPC periodically buys what they need and sells surplus
    all_npcs = db.execute("SELECT id, location_id FROM agents WHERE type = 'npc' AND state = 'active'").fetchall()
    for npc_row in all_npcs:
        npc_id = npc_row["id"]
        inv = get_inventory(db, npc_id)

        # Consume needs: firewood in winter, food categories
        season_row = db.execute("SELECT season FROM world_time WHERE id = 1").fetchone()
        current_season = season_row["season"] if season_row else "spring"

        # Low firewood in winter → try to buy from someone who has surplus
        if current_season == "winter":
            fw = inv.get(RESOURCE_FIREWOOD, 0)
            if fw < 1.0:
                # Find someone with surplus (more than 5 units)
                surplus_rows = db.execute(
                    "SELECT agent_id, quantity FROM agent_inventory WHERE resource_id = ? AND quantity > 5 AND agent_id != ?",
                    (RESOURCE_FIREWOOD, npc_id)
                ).fetchall()
                if surplus_rows:
                    donor = surplus_rows[0]
                    amount = min(0.5, donor["quantity"] - 5, inv.get(RESOURCE_FIREWOOD, 0) + 0.5)
                    if amount > 0:
                        transfer(db, donor["agent_id"], npc_id, RESOURCE_FIREWOOD, amount)
                        summary["traded"].append({
                            "from": donor["agent_id"], "to": npc_id,
                            "resource": RESOURCE_FIREWOOD, "amount": round(amount, 2)
                        })

        # Low food → try to buy mushrooms, herbs, or fish
        food_qty = sum(inv.get(r, 0) for r in [RESOURCE_MUSHROOMS, RESOURCE_HERBS, RESOURCE_FISH])
        if food_qty < 1.0:
            for food_res in [RESOURCE_MUSHROOMS, RESOURCE_HERBS, RESOURCE_FISH]:
                surplus_rows = db.execute(
                    "SELECT agent_id, quantity FROM agent_inventory WHERE resource_id = ? AND quantity > 3 AND agent_id != ?",
                    (food_res, npc_id)
                ).fetchall()
                if surplus_rows:
                    donor = surplus_rows[0]
                    amount = min(0.3, donor["quantity"] - 3, 1.0 - food_qty)
                    if amount > 0:
                        transfer(db, donor["agent_id"], npc_id, food_res, amount)
                        summary["traded"].append({
                            "from": donor["agent_id"], "to": npc_id,
                            "resource": food_res, "amount": round(amount, 2)
                        })
                        break

        # Surplus food → move to market_stall for the player to collect
        for food_res in [RESOURCE_MUSHROOMS, RESOURCE_HERBS, RESOURCE_FISH]:
            qty = inv.get(food_res, 0)
            if qty > 4.0 and random.random() < 0.3:
                # Drop surplus at market_stall — player can pick it up
                adjust_inventory(db, npc_id, food_res, -0.5)
                summary["traded"].append({
                    "from": npc_id, "to": "market_stall",
                    "resource": food_res, "amount": 0.5
                })

    # 4. PERISHABLE DECAY — resources with decay_rate lose quantity over time
    perishable_resources = [RESOURCE_MUSHROOMS, RESOURCE_HERBS, RESOURCE_FISH]
    for rid in perishable_resources:
        res_def = RESOURCE_DEFINITIONS.get(rid, {})
        decay = res_def.get("decay_rate", 0)
        if decay <= 0:
            continue

        rows = db.execute("SELECT agent_id, quantity FROM agent_inventory WHERE resource_id = ?", (rid,)).fetchall()
        for row in rows:
            decayed = row["quantity"] * decay
            adjust_inventory(db, row["agent_id"], rid, -decayed)
            if decayed > 0.001:
                summary["decayed"].append({
                    "agent": row["agent_id"],
                    "resource": rid,
                    "amount": round(decayed, 4)
                })

    return summary


# ── Resource Node Harvesting ───────────────────────────────────────────────────

def harvest_node(db, agent_id: str, node_id: str) -> dict:
    """
    Attempt to harvest a resource node.
    Returns result dict with success/failure info.
    """
    now = time.time()

    node = db.execute(
        "SELECT * FROM resource_nodes WHERE id = ?",
        (node_id,)
    ).fetchone()

    if not node:
        return {"success": False, "reason": "node_not_found"}

    # Check cooldown
    if node["last_harvested"] > 0:
        elapsed = now - node["last_harvested"]
        if elapsed < node["cooldown_hours"] * 3600:
            remaining = (node["cooldown_hours"] * 3600 - elapsed) / 3600
            return {"success": False, "reason": "on_cooldown", "hours_remaining": round(remaining, 1)}

    # Check season
    season_row = db.execute("SELECT season FROM world_time WHERE id = 1").fetchone()
    if node["season"] != "any" and node["season"] != season_row["season"]:
        return {"success": False, "reason": "wrong_season", "required": node["season"]}

    # Harvest
    yield_amount = node["yield_per_harvest"]
    adjust_inventory(db, agent_id, node["resource_id"], yield_amount)
    db.execute(
        "UPDATE resource_nodes SET last_harvested = ? WHERE id = ?",
        (now, node_id)
    )

    return {
        "success": True,
        "resource": node["resource_id"],
        "amount": yield_amount,
        "location": node["location_id"]
    }


# ── Query Helpers ─────────────────────────────────────────────────────────────

def get_all_inventories(db) -> dict:
    """Return {agent_id: {resource_id: qty}} for all agents with inventory."""
    rows = db.execute("""
        SELECT ai.agent_id, ai.resource_id, ai.quantity, r.name, r.unit
        FROM agent_inventory ai
        JOIN resources r ON r.id = ai.resource_id
        WHERE ai.quantity > 0
        ORDER BY ai.agent_id
    """).fetchall()

    result = {}
    for row in rows:
        if row["agent_id"] not in result:
            result[row["agent_id"]] = {}
        result[row["agent_id"]][row["resource_id"]] = {
            "qty": row["quantity"],
            "name": row["name"],
            "unit": row["unit"]
        }
    return result


def get_trade_log(db, limit: int = 20) -> list:
    """Return recent trade events."""
    rows = db.execute(
        "SELECT * FROM trade_log ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    return [dict(r) for r in rows]