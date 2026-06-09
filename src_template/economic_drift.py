"""economic_drift.py — Currency stability drift from trade, diplomacy, and events."""
import random
from typing import Dict, Any

CURRENCY_DATA = {
    "solara": {"name": "Lumen", "symbol": "☀", "backing": "Solar energy + biofuel", "stability": 0.78},
    "arkos": {"name": "Ark", "symbol": "▲", "backing": "Stored solar energy + manufacturing", "stability": 0.82},
    "mirithane": {"name": "Miri", "symbol": "≈", "backing": "Purified water reserves", "stability": 0.75},
    "valdris": {"name": "Kael", "symbol": "♦", "backing": "Rare earth minerals + refined metals", "stability": 0.80},
    "verge": {"name": "None", "symbol": "—", "backing": "Barter only", "stability": 0.30},
}


def drift_currency(world_id: str, trade_balance: float, diplomatic_tension: float, event_impact: float = 0.0) -> Dict[str, Any]:
    """Compute new currency stability based on economic and diplomatic factors."""
    currency = CURRENCY_DATA.get(world_id, {"stability": 0.5, "symbol": "?", "name": "Unknown"})
    current = currency["stability"]

    drift = random.uniform(-0.003, 0.003)
    drift += trade_balance * 0.005
    drift -= diplomatic_tension * 0.002
    drift += event_impact

    new_stability = max(0.05, min(1.0, current + drift))
    currency["stability"] = new_stability

    return {
        "world_id": world_id,
        "currency": currency["name"],
        "symbol": currency["symbol"],
        "stability": new_stability,
        "drift": drift,
        "trade_balance": trade_balance,
    }


def stability_affects_npcs(db, world_id: str):
    """Apply currency stability effects to NPC decision variables."""
    from .decision_state import nudge_variable
    currency = CURRENCY_DATA.get(world_id, {"stability": 0.5})
    stability = currency["stability"]

    if stability < 0.3:
        npcs = db.execute("SELECT id FROM agents WHERE type = 'npc' LIMIT 50").fetchall()
        for (npc_id,) in npcs:
            nudge_variable(db, npc_id, "satisfaction", -0.002 * (0.3 - stability))

    if stability < 0.15:
        npcs = db.execute("SELECT id FROM agents WHERE type = 'npc' LIMIT 50").fetchall()
        for (npc_id,) in npcs:
            nudge_variable(db, npc_id, "security", -0.003 * (0.15 - stability))
