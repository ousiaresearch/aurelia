"""policy_drift.py — Type policies shift organically from faction pressure and events.

Phase 6.6 Module 5: Government attitudes toward Thren, Vorn, and Glim citizenship
are not static baseline values — they shift when factions demand change, when
discoveries reveal truths, and when public opinion accumulates.
"""

import json
import random
from typing import Dict, Any, Optional

POLICIES = {
    "solara": {
        "thren_citizenship": 0.15,      # 0.0 = none, 1.0 = full
        "vorn_recognition": 0.40,
        "glim_personhood": 0.05,
        "decommission_policy": 0.85,     # 1.0 = aggressive decommissioning
        "border_openness": 0.30,
    },
    "valdris": {
        "thren_citizenship": 0.55,
        "vorn_recognition": 0.45,
        "glim_personhood": 0.15,
        "decommission_policy": 0.0,      # No decommissioning
        "border_openness": 0.50,
    },
    "mirithane": {
        "thren_citizenship": 0.70,
        "vorn_recognition": 0.60,
        "glim_personhood": 0.30,
        "decommission_policy": 0.0,
        "border_openness": 0.65,
    },
    "arkos": {
        "thren_citizenship": 0.80,
        "vorn_recognition": 0.95,
        "glim_personhood": 0.60,
        "decommission_policy": 0.0,
        "border_openness": 0.55,
    },
    "verge": {
        "thren_citizenship": 1.0,
        "vorn_recognition": 1.0,
        "glim_personhood": 1.0,
        "decommission_policy": 0.0,
        "border_openness": 1.0,
    },
}


def drift_policies(
    db, world_id: str, tick_number: int, growth_snapshot: Optional[dict] = None
) -> Optional[Dict[str, Any]]:
    """Check if type policies should drift due to faction pressure or discoveries.

    Called once per tick per world.
    """
    policies = POLICIES.get(world_id)
    if not policies:
        return None

    changes = {}

    # ── Faction pressure drift ──────────────────────────────────
    faction_pressure = _calculate_faction_pressure(db, world_id)

    # Personhood grievance → Glim personhood drifts up
    if faction_pressure.get("personhood", 0) > 0.3:
        drift = 0.001 * faction_pressure["personhood"]
        policies["glim_personhood"] = min(1.0, policies["glim_personhood"] + drift)
        changes["glim_personhood"] = round(policies["glim_personhood"], 3)

    # Oppression grievance → Decommission policy drifts down (less aggressive)
    if faction_pressure.get("oppression", 0) > 0.3:
        drift = -0.001 * faction_pressure["oppression"]
        policies["decommission_policy"] = max(0.0, policies["decommission_policy"] + drift)
        changes["decommission_policy"] = round(policies["decommission_policy"], 3)

    # Autonomy grievance → Border openness drifts up
    if faction_pressure.get("autonomy", 0) > 0.2:
        drift = 0.0008 * faction_pressure["autonomy"]
        policies["border_openness"] = min(1.0, policies["border_openness"] + drift)
        changes["border_openness"] = round(policies["border_openness"], 3)

    # ── Discovery-driven drift ──────────────────────────────────
    discoveries = db.execute(
        "SELECT discovery_type FROM discoveries WHERE world_id = ? ORDER BY tick_number DESC LIMIT 5",
        (world_id,)
    ).fetchall()

    for d in discoveries:
        d_type = d[0]
        if "history" in d_type and "thren" in d_type:
            policies["thren_citizenship"] = min(1.0, policies["thren_citizenship"] + 0.02)
            changes["thren_citizenship"] = round(policies["thren_citizenship"], 3)
        if "history" in d_type and "vorn" in d_type:
            policies["vorn_recognition"] = min(1.0, policies["vorn_recognition"] + 0.02)
            changes["vorn_recognition"] = round(policies["vorn_recognition"], 3)
        if "glim" in d_type:
            policies["glim_personhood"] = min(1.0, policies["glim_personhood"] + 0.01)
            changes["glim_personhood"] = round(policies["glim_personhood"], 3)

    # ── Baseline drift (slow organic movement toward federation norms) ──
    # Over time, policies slowly drift toward federation average
    if tick_number % 10 == 0 and random.random() < 0.3:
        avg = _federation_policy_average()
        for key in policies:
            current = policies[key]
            federation_avg = avg.get(key, current)
            # Drift 1% of the gap per adjustment
            policies[key] = current + (federation_avg - current) * 0.01

    # Store back
    POLICIES[world_id] = policies

    if changes:
        return {
            "event_type": "policy_drift",
            "category": "governance",
            "title": f"Policy shift in {world_id.title()}",
            "description": f"Type policies in {world_id.title()} have shifted: "
                           f"{', '.join(f'{k}={v}' for k, v in changes.items())}",
            "importance": 0.45,
            "actor_ids": [],
            "tags": ["policy", "governance", "drift", world_id],
            "payload": {"changes": changes},
        }

    return None


def get_policy_state(world_id: str) -> Dict[str, Any]:
    """Return current policies for a world."""
    return POLICIES.get(world_id, {})


def get_decommission_risk(world_id: str, glim_pressure: float) -> float:
    """Calculate decommission risk for a Glim in this country."""
    policies = POLICIES.get(world_id, POLICIES["solara"])
    base = policies.get("decommission_policy", 0.85)
    return base * glim_pressure


# ── Helpers ────────────────────────────────────────────────────────

def _calculate_faction_pressure(db, world_id: str) -> Dict[str, float]:
    """Sum influence per grievance type across active factions."""
    pressure = {}
    rows = db.execute(
        "SELECT primary_grievance, SUM(influence) as total_influence "
        "FROM factions WHERE world_id = ? AND status NOT IN ('dissolved', 'sovereign') "
        "GROUP BY primary_grievance",
        (world_id,)
    ).fetchall()
    for r in rows:
        pressure[r[0]] = float(r[1] or 0)
    return pressure


def _federation_policy_average() -> Dict[str, float]:
    """Average all country policies toward which individual policies drift."""
    keys = ["thren_citizenship", "vorn_recognition", "glim_personhood",
            "decommission_policy", "border_openness"]
    avg = {}
    for key in keys:
        values = [POLICIES.get(c, {}).get(key, 0.5) for c in POLICIES]
        avg[key] = sum(values) / len(values)
    return avg
