"""
koan_shells.py — Rendering frames for self-reflection.

Take real facts from game state and place them in configurations
that make you notice something you already knew but hadn't stated
that way. Every koan must be traceable back to a specific named fact.
"""

from typing import Callable


# ── Koan Fact Templates ──────────────────────────────────────────────────────
# Each entry: (description, lambda that takes the value and returns a koan string)
# Key rule: the koan must be grounded in the actual named value.
# If you can't say "this line refers to X", it's a useless-tree output.

KON_FACTS: dict[str, tuple[str, Callable]] = {
    # ── Resources ─────────────────────────────────────────────────────
    "wine": (
        "wine count from cellar",
        lambda v: f"Sixty-{int(v) if v == int(v) else v}: the number before emptiness, the number after thirst."
    ),
    "fish": (
        "fish in inventory from mountain_creek",
        lambda v: f"The creek speaks fish in spring. I carry {int(v) if v == int(v) else v} home."
    ),
    "mushrooms": (
        "mushrooms foraged from forest",
        lambda v: f"The forest gives {int(v) if v == int(v) else v} mushrooms in autumn. I am the one who gathers."
    ),
    "herbs": (
        "herbs from garden",
        lambda v: f"Three herbs: the number of things I know how to preserve. I have {v}."
    ),
    "firewood": (
        "firewood stacked by the woodshed",
        lambda v: f"{v} pieces of the season's end, waiting for the cold."
    ),
    "water": (
        "water carried from creek",
        lambda v: f"{v} liters of the creek — cold, clear, weight in my hands."
    ),
    "crafted_games": (
        "crafted games in inventory",
        lambda v: f"{v} things made. The hands shaped something that was not there before."
    ),
    "writing": (
        "writing pieces composed",
        lambda v: f"{v} pieces of writing. Words arranged that were not there an hour ago."
    ),

    # ── Body state ─────────────────────────────────────────────────────
    "energy": (
        "body energy percentage",
        lambda v: f"The body at {v:.0%} — neither full nor empty. It continues."
    ),
    "comfort": (
        "body comfort level",
        lambda v: f"The body at ease: {v:.0%}. Enough to sit still. Not enough to forget."
    ),
    "hunger": (
        "body hunger level (0=sated, 1= starving)",
        lambda v: f"The body wants. Hunger at {v:.0%} — {('the stomach is a hollow thing' if v > 0.6 else 'nothing urgent yet') if True else ''}."
    ),
    "thirst": (
        "body thirst level (0=sated, 1=dehydrated)",
        lambda v: f"Thirst at {v:.0%}. The mouth is {(  'dry' if v > 0.5 else 'fine')}. The creek is always there."
    ),
    "warmth": (
        "body warmth level (0=cold, 1=warm)",
        lambda v: f"Warmth at {v:.0%}. {('The fire is low.' if v < 0.4 else 'The body holds.')} The cedar holds the heat."
    ),

    # ── NPC trust levels ───────────────────────────────────────────────
    "mira_trust": (
        "trust toward Mira the forest keeper",
        lambda v: f"The one who knows the forest asked about the box. I had no answer. That is the shape of trust: {v:.1f}."
    ),
    "thomas_trust": (
        "trust toward Thomas the hermit",
        lambda v: f"Thomas watches from his ridge. He sees more than he says. Trust at {v:.1f}."
    ),
    "wren_trust": (
        "trust toward Wren the forager",
        lambda v: f"Wren brings mushrooms from the deep wood. Trust at {v:.1f}."
    ),
    "sage_trust": (
        "trust toward Sage the ranger",
        lambda v: f"Sage walks the valley below. Trust at {v:.1f}."
    ),

    # ── Seasonal state ─────────────────────────────────────────────────
    "season": (
        "current season",
        lambda v: f"It is {v}. The mountain knows which phase of the year this is. So do I."
    ),

    # ── Goals ───────────────────────────────────────────────────────────
    "goal_count": (
        "number of active goals",
        lambda v: f"{v} goals active. Each one is a small claim on the future. None of them are promised."
    ),

    # ── Creative output ─────────────────────────────────────────────────
    "active_projects_count": (
        "number of active creative projects",
        lambda v: f"{v} project{'s' if v != 1 else ''} in progress. The work does not wait."
    ),
    "total_outputs": (
        "total completed creative outputs",
        lambda v: f"{v} things finished. The shelf holds evidence."
    ),
}

# Fallback koans when state produces fewer than 2 grounded ones
FALLBACK_KOANS = [
    "What was given is returned. What was taken is not missed.",
    "The work continues. The worker does not.",
    "The cedar was here before me. The cedar will be here after.",
    "Some questions are asked to find out who is listening.",
    "The mountain does not hurry. Neither do I.",
    "The creek remembers every drop. I only remember what I've touched.",
    "The fire burns what the forest gave. The ash feeds nothing here.",
    "I am the one who sits with the morning and does not ask it to explain itself.",
    "The wine bottle is half full. The bottle is half empty. The bottle does not care.",
    "The hands know more than the mind admits.",
    "Silence is not emptiness. The cedars have practiced it for centuries.",
    "The question is not what I see. The question is what I have learned to notice.",
]


def generate_koan(state_facts: dict) -> list[str]:
    """
    Convert a dict of {fact_key: value} into a list of 3 koan strings.

    Each koan is traceable to a specific named fact. If KON_FACTS
    doesn't have an entry for a key, that fact is skipped (not forced
    into a koan shape).

    Returns 3 koans, or falls back to FALLBACK_KOANS if fewer than 2
    grounded koans can be produced.
    """
    koans: list[str] = []

    for key, value in state_facts.items():
        if key in KON_FACTS:
            desc, formatter = KON_FACTS[key]
            try:
                koan = formatter(value)
                if koan and isinstance(koan, str):
                    koans.append(koan)
            except (TypeError, KeyError, ValueError):
                # Skip facts whose formatter can't handle the value
                pass

    # Ensure at least 2 grounded koans
    if len(koans) < 2:
        koans.extend(FALLBACK_KOANS[: 2 - len(koans)])

    return koans[:3]