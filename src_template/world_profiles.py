"""world_profiles.py — Phase 8 per-world political metabolism priors.

These profiles are calibration inputs, not lore text. They let the Phase 7
causal runner produce divergent histories while preserving the same mechanics
for every world.
"""
from __future__ import annotations

from copy import deepcopy

DEFAULT_PROFILE = {
    "macro_baseline": {
        "gdp_proxy": 0.55,
        "inequality": 0.45,
        "food_security": 0.60,
        "water_security": 0.60,
        "public_health": 0.70,
        "legitimacy": 0.55,
        "repression": 0.30,
        "fiscal_capacity": 0.50,
        "infrastructure": 0.60,
        "border_openness": 0.50,
        "type_tension": 0.30,
        "war_pressure": 0.00,
    },
    "resilience": {
        "shock_absorption": 0.50,
        "recovery_rate": 0.010,
        "health_resilience": 0.010,
        "food_resilience": 0.010,
        "fiscal_resilience": 0.010,
    },
    "migration": {
        "push_sensitivity": 1.00,
        "pull_attractiveness": 1.00,
        "border_friction": 0.50,
        "refugee_tolerance": 0.50,
    },
    "factions": {
        "concession_bias": 0.25,
        "repression_bias": 0.25,
        "legalization_bias": 0.15,
        "splinter_bias": 0.15,
        "exile_bias": 0.10,
        "radicalization_bias": 0.10,
    },
}

WORLD_PROFILES = {
    "solara": {
        "macro_baseline": {
            "legitimacy": 0.62,
            "repression": 0.45,
            "fiscal_capacity": 0.58,
            "border_openness": 0.35,
            "type_tension": 0.38,
        },
        "resilience": {"shock_absorption": 0.65, "recovery_rate": 0.012, "fiscal_resilience": 0.016},
        "migration": {"push_sensitivity": 0.80, "pull_attractiveness": 0.70, "border_friction": 0.75, "refugee_tolerance": 0.30},
        "factions": {"concession_bias": 0.20, "repression_bias": 0.45, "legalization_bias": 0.10, "splinter_bias": 0.15, "exile_bias": 0.20, "radicalization_bias": 0.20},
    },
    "valdris": {
        "macro_baseline": {"gdp_proxy": 0.66, "fiscal_capacity": 0.60, "inequality": 0.55, "legitimacy": 0.48},
        "resilience": {"shock_absorption": 0.55, "recovery_rate": 0.014, "food_resilience": 0.008},
        "migration": {"push_sensitivity": 1.00, "pull_attractiveness": 1.15, "border_friction": 0.45, "refugee_tolerance": 0.50},
        "factions": {"concession_bias": 0.32, "repression_bias": 0.25, "legalization_bias": 0.20, "splinter_bias": 0.20, "exile_bias": 0.08, "radicalization_bias": 0.15},
    },
    "mirithane": {
        "macro_baseline": {"public_health": 0.78, "food_security": 0.68, "legitimacy": 0.58, "repression": 0.20, "war_pressure": 0.02},
        "resilience": {"shock_absorption": 0.60, "recovery_rate": 0.016, "health_resilience": 0.020, "food_resilience": 0.016},
        "migration": {"push_sensitivity": 0.75, "pull_attractiveness": 1.05, "border_friction": 0.40, "refugee_tolerance": 0.70},
        "factions": {"concession_bias": 0.42, "repression_bias": 0.12, "legalization_bias": 0.28, "splinter_bias": 0.12, "exile_bias": 0.05, "radicalization_bias": 0.08},
    },
    "arkos": {
        "macro_baseline": {"border_openness": 0.62, "war_pressure": 0.08, "type_tension": 0.22, "legitimacy": 0.52},
        "resilience": {"shock_absorption": 0.45, "recovery_rate": 0.012, "fiscal_resilience": 0.010},
        "migration": {"push_sensitivity": 1.20, "pull_attractiveness": 1.20, "border_friction": 0.30, "refugee_tolerance": 0.80},
        "factions": {"concession_bias": 0.35, "repression_bias": 0.18, "legalization_bias": 0.22, "splinter_bias": 0.20, "exile_bias": 0.08, "radicalization_bias": 0.12},
    },
    "verge": {
        "macro_baseline": {"border_openness": 0.72, "legitimacy": 0.45, "repression": 0.12, "type_tension": 0.18, "fiscal_capacity": 0.38},
        "resilience": {"shock_absorption": 0.35, "recovery_rate": 0.018, "health_resilience": 0.012},
        "migration": {"push_sensitivity": 1.35, "pull_attractiveness": 1.35, "border_friction": 0.20, "refugee_tolerance": 0.90},
        "factions": {"concession_bias": 0.45, "repression_bias": 0.08, "legalization_bias": 0.32, "splinter_bias": 0.25, "exile_bias": 0.04, "radicalization_bias": 0.10},
    },
}


def profile(world_id: str) -> dict:
    merged = deepcopy(DEFAULT_PROFILE)
    custom = WORLD_PROFILES.get(world_id, {})
    for section, values in custom.items():
        merged.setdefault(section, {}).update(values)
    return merged


def macro_baseline(world_id: str) -> dict[str, float]:
    return profile(world_id)["macro_baseline"]
