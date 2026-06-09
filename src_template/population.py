"""population.py — Decision-based migration, reproduction, and mortality."""
import json
import random
from typing import Optional, List, Dict, Any
from .decision_state import get_decision_state, check_threshold, log_decision

MIGRATION_PATHS = {
    "solara": {
        "destinations": ["mirithane", "valdris"],
        "push_factors": {
            "security": ("below", 0.3),
            "ideological_alignment": ("below", 0.35),
        },
        "pull_factors": {
            "mirithane": {"security": 0.6, "connectedness": 0.5},
            "valdris": {"security": 0.5, "satisfaction": 0.4},
        },
    },
    "arkos": {
        "destinations": ["mirithane", "valdris"],
        "push_factors": {
            "connectedness": ("below", 0.25),
            "restlessness": ("above", 0.75),
        },
        "pull_factors": {
            "mirithane": {"connectedness": 0.7, "ideological_alignment": 0.5},
            "valdris": {"satisfaction": 0.5, "connectedness": 0.6},
        },
    },
    "mirithane": {
        "destinations": ["valdris"],
        "push_factors": {
            "restlessness": ("above", 0.80),
            "satisfaction": ("below", 0.2),
        },
        "pull_factors": {
            "valdris": {"satisfaction": 0.5, "security": 0.6},
        },
    },
    "valdris": {
        "destinations": ["arkos", "mirithane"],
        "push_factors": {
            "security": ("below", 0.25),
            "ideological_alignment": ("below", 0.3),
        },
        "pull_factors": {
            "arkos": {"security": 0.6, "connectedness": 0.5},
            "mirithane": {"security": 0.5, "ideological_alignment": 0.4},
        },
    },
    "verge": {
        "destinations": ["mirithane", "arkos"],
        "push_factors": {
            "security": ("below", 0.15),
        },
        "pull_factors": {
            "mirithane": {"security": 0.5, "connectedness": 0.6},
            "arkos": {"security": 0.5, "satisfaction": 0.5},
        },
    },
}


def check_migration(db, npc_id: str, npc_type: str, world_id: str, tick_info: dict) -> Optional[dict]:
    """Check if an NPC should migrate based on decision state thresholds."""
    state = get_decision_state(db, npc_id)
    if not state:
        return None

    paths = MIGRATION_PATHS.get(world_id)
    if not paths:
        return None

    push_triggered = True
    for variable, (direction, threshold) in paths["push_factors"].items():
        if direction == "below":
            if not check_threshold(state, variable, threshold, "below"):
                push_triggered = False
                break
        else:
            if not check_threshold(state, variable, threshold, "above"):
                push_triggered = False
                break

    if not push_triggered:
        return None

    candidates = []
    for dest in paths["destinations"]:
        pull = paths["pull_factors"].get(dest, {})
        score = sum(
            state.get(var, 0.5) * weight
            for var, weight in pull.items()
        )
        candidates.append((dest, max(0.01, score)))

    if not candidates:
        return None

    total = sum(score for _, score in candidates)
    r = random.uniform(0, total)
    cumulative = 0
    chosen = candidates[0][0]
    for dest, score in candidates:
        cumulative += score
        if r <= cumulative:
            chosen = dest
            break

    if random.random() > 0.05:
        return None

    log_decision(db, npc_id, "migration", {
        "from": world_id, "to": chosen,
        "security": state.get("security"),
        "restlessness": state.get("restlessness"),
    })

    return {
        "event_type": "migration",
        "category": "population",
        "description": f"{npc_type.title()} {npc_id} migrates from {world_id} to {chosen}.",
        "npc_id": npc_id,
        "npc_type": npc_type,
        "from_world": world_id,
        "to_world": chosen,
    }


def check_reproduction(db, npc_id: str, npc_type: str, world_id: str, tick_info: dict) -> Optional[dict]:
    """Check if an NPC should reproduce based on decision state."""
    state = get_decision_state(db, npc_id)
    if not state:
        return None

    if not (state.get("security", 0) > 0.7 and
            state.get("satisfaction", 0) > 0.7 and
            state.get("connectedness", 0) > 0.6):
        return None

    if random.random() > 0.003:
        return None

    log_decision(db, npc_id, "reproduction", {
        "world": world_id, "type": npc_type,
        "security": state.get("security"),
        "satisfaction": state.get("satisfaction"),
    })

    return {
        "event_type": "reproduction",
        "category": "population",
        "description": f"New {npc_type} born in {world_id}.",
        "npc_id": npc_id,
        "npc_type": npc_type,
        "child_type": npc_type,
        "world_id": world_id,
    }


def check_mortality(db, npc_id: str, npc_type: str, world_id: str,
                    tick_info: dict, active_disasters: Optional[List] = None,
                    active_conflicts: Optional[List] = None) -> Optional[dict]:
    """Check if an NPC dies from accumulated conditions."""
    state = get_decision_state(db, npc_id)
    if not state:
        return None

    security = state.get("security", 0.5)
    anomaly = state.get("anomaly_pressure", 0.0)
    satisfaction = state.get("satisfaction", 0.5)
    restlessness = state.get("restlessness", 0.2)

    safety_ticks = tick_info.get("low_security_ticks", {}).get(npc_id, 0)

    causes = []
    roll = random.random()

    # 1. Security collapse: sustained danger
    if security < 0.1 and safety_ticks >= 10:
        if roll < 0.02:
            causes.append("security_collapse")

    # 2. Glim decommissioning: Solara's policy
    if npc_type == "glim" and world_id == "solara" and anomaly > 0.9:
        if roll < 0.08:
            causes.append("decommissioning")

    # 3. Ecological disaster
    if active_disasters:
        location = tick_info.get("location_id", "")
        for disaster in active_disasters:
            if disaster.get("world_id") == world_id:
                if roll < 0.05:
                    causes.append(f"ecology:{disaster.get('type', 'disaster')}")

    # 4. Thren circuitry degradation
    if npc_type == "thren" and satisfaction < 0.15 and restlessness > 0.8:
        if roll < 0.01:
            causes.append("circuitry_degradation")

    # 5. Verge exposure
    if world_id == "verge" and security < 0.05:
        if roll < 0.04:
            causes.append("verge_exposure")

    # 6. Conflict cascade
    if active_conflicts and security < 0.2:
        for conflict in active_conflicts:
            if conflict.get("world_id") == world_id:
                if roll < 0.015:
                    causes.append(f"conflict:{conflict.get('type', 'war')}")

    if not causes:
        return None

    cause = random.choice(causes)
    log_decision(db, npc_id, "death", {
        "cause": cause,
        "security": security,
        "anomaly_pressure": anomaly,
        "world": world_id,
        "type": npc_type,
    })

    return {
        "event_type": "mortality",
        "category": "population",
        "description": f"{npc_type.title()} {npc_id} died in {world_id}: {cause}.",
        "npc_id": npc_id,
        "npc_type": npc_type,
        "world_id": world_id,
        "cause": cause,
        "security_at_death": security,
    }
