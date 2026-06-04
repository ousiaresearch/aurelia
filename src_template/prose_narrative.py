"""
prose_narrative.py — Prose narrative generator for the simulation daemon.

Takes raw tick results (events, conversations, weather, NPC actions) and weaves
them into cohesive, literary prose — the kind of writing that makes the world
feel lived-in rather than logged.

Design principles:
- One tick = one prose passage (not a list of bullets)
- Sensory grounding: weather, light, sound, smell — the PNW is always present
- Emotional texture: the prose reflects the mood of what happened
- Varied rhythm: short sentences for tension, longer for calm
- No "the village," no "the sea," no tavern/shop references
- The cabin and its surroundings are the center of gravity
"""

import random
from typing import Optional


# ── TIME OPENINGS — varied by time of day ──

DAWN_OPENINGS = [
    "Dawn comes slowly, the darkness thinning to gray over the mountains.",
    "The first light is thin and cold, touching the tops of the cedars.",
    "Gray light at the window. The mountains are still dark shapes.",
    "The sky lightens from the east, pale gold at the edges.",
    "Before dawn, the world holds its breath. Then the birds begin.",
]

MORNING_OPENINGS = [
    "Morning. The light is clear and the day feels open.",
    "The morning stretches ahead, full of quiet possibility.",
    "Early morning in the valley. The fog hasn't lifted yet.",
    "The sun is above the ridgeline now. The day begins in earnest.",
    "Morning light through the cabin windows. The woodstove ticks.",
]

MIDDAY_OPENINGS = [
    "Midday. The sun is at its highest and the shadows are short.",
    "The light is bright. Everything is sharp in the clear air.",
    "Noon. The valley is quiet in the way it gets when the sun is overhead.",
    "The middle of the day. The world is warm and still.",
]

AFTERNOON_OPENINGS = [
    "Afternoon light, warm and slanting through the trees.",
    "The afternoon is wide and still. The kind of still that hums.",
    "Late afternoon. The shadows are growing. The air is cooling.",
    "The sun is lowering. Everything glows.",
    "The afternoon stretches out, unhurried. The cedars hold the heat.",
]

EVENING_OPENINGS = [
    "Evening. The light is golden, the shadows long.",
    "The sun is lowering. The sky turns amber and rose.",
    "Dusk comes to the valley. The air cools. The first stars appear.",
    "The day is ending. The mountains go dark against a bright sky.",
    "Evening settles over the cabin like a blanket.",
]

NIGHT_OPENINGS = [
    "Night. The darkness is deep and full of sound.",
    "The stars are out. Francis is visible, steady and red.",
    "Night in the valley. The creek is loud in the darkness.",
    "The world is what you can hear and feel. The darkness is complete.",
    "Late night. The cabin is quiet. The fire burns low.",
]


def _get_time_opening(tod: str) -> str:
    """Get a varied opening line based on time of day."""
    openings = {
        "dawn": DAWN_OPENINGS,
        "early_morning": MORNING_OPENINGS,
        "morning": MORNING_OPENINGS,
        "mid_morning": MORNING_OPENINGS,
        "late_morning": MORNING_OPENINGS,
        "midday": MIDDAY_OPENINGS,
        "afternoon": AFTERNOON_OPENINGS,
        "late_afternoon": AFTERNOON_OPENINGS,
        "evening": EVENING_OPENINGS,
        "dusk": EVENING_OPENINGS,
        "night": NIGHT_OPENINGS,
        "late_night": NIGHT_OPENINGS,
        "deep_night": NIGHT_OPENINGS,
        "pre_dawn": DAWN_OPENINGS,
    }
    return random.choice(openings.get(tod, MORNING_OPENINGS))


# ── WEATHER INTEGRATION ──

WEATHER_PROSE = {
    "clear": {
        "dawn": "The dawn breaks clear, the sky lightening from gold to blue.",
        "morning": "A clear morning. The sun warms the cabin walls.",
        "afternoon": "The afternoon is bright and clear. Shadows are sharp on the ground.",
        "evening": "A clear evening. The sun sets in a sky of amber and rose.",
        "night": "A clear night. Stars fill the sky from horizon to horizon.",
        "default": "The sky is clear and open above the valley.",
    },
    "cloudy": {
        "dawn": "Clouds catch the dawn light — pink and gray and gold.",
        "morning": "Clouds drift across the sky. The sun appears and disappears.",
        "afternoon": "A blanket of cloud softens the light. Everything is diffuse.",
        "evening": "The clouds glow amber at their edges.",
        "night": "Clouds hide the stars. The darkness is complete.",
        "default": "Clouds cover the sky.",
    },
    "foggy": {
        "dawn": "Fog blurs the dawn. The world is soft edges and muffled sound.",
        "morning": "The fog is thick in the valley. Sounds are close. The world feels small.",
        "afternoon": "Fog still hangs over the cabin. The mountains are invisible.",
        "evening": "Fog thickens as the light fades. The world shrinks to what you can hear.",
        "night": "Fog and darkness. The world is sound and smell.",
        "default": "Fog softens everything.",
    },
    "rain": {
        "dawn": "Rain falls softly in the gray dawn light.",
        "morning": "Rain patters on the roof, on leaves, on the deck.",
        "afternoon": "Steady rain. The world smells of wet earth and cedar.",
        "evening": "Rain continues into the evening. The light is gray and fading.",
        "night": "Rain in the darkness. The sound is everywhere.",
        "default": "Rain falls.",
    },
    "storm": {
        "dawn": "Wind and rain. The dawn is gray and loud.",
        "morning": "The storm is full. Rain lashes, wind howls through the trees.",
        "afternoon": "Thunder rolls. The creek will rise. Everything feels alive.",
        "evening": "The storm begins to ease. The wind still gusts.",
        "night": "Storm in the darkness. Lightning flashes, thunder follows.",
        "default": "The storm rages.",
    },
}


def _get_weather_prose(condition: str, tod: str) -> str:
    """Get weather description woven into prose."""
    options = WEATHER_PROSE.get(condition, WEATHER_PROSE["clear"])
    return options.get(tod, options["default"])


# ── TEMPERATURE PROSE ──

def _get_temp_prose(temp: float) -> Optional[str]:
    """Get temperature felt as prose, or None if unremarkable."""
    if temp < 2:
        return "The cold bites. Your fingers are stiff. The kind of cold that comes from damp, not just temperature."
    elif temp < 6:
        return "The air has an edge to it. You pull your shoulders in."
    elif temp < 10:
        return "Cool. The mountain air has a bite, but the sun helps."
    elif temp < 15:
        return None  # Mild — unremarkable, don't mention
    elif temp < 20:
        return "Warm. The kind of warmth that feels earned after months of rain."
    elif temp < 25:
        return "Warm. The shade of the cedars is the only relief."
    else:
        return "Unusual heat. The air is still and heavy."


# ── MOVEMENT PROSE ──

def _weave_movements(moves: list, tod: str) -> Optional[str]:
    """Weave NPC movements into prose."""
    if not moves:
        return None

    if len(moves) > 6:
        return f"The valley is busy today. {len(moves)} people move through the trees, along the trails, between cabins."

    if len(moves) > 3:
        # Group them
        names = [m[0] for m in moves[:4]]
        return f"{', '.join(names)} and others move through the valley."

    # Few movements — mention specifically
    parts = []
    for name, loc in moves[:3]:
        loc_clean = loc.replace("_", " ").replace("cabin ", "")
        parts.append(f"{name} heads toward the {loc_clean}")
    if parts:
        return ". ".join(parts) + "."
    return None


# ── NPC ACTION PROSE ──

def _weave_npc_actions(actions: list) -> Optional[str]:
    """Weave NPC AI actions into prose."""
    if not actions:
        return None

    # Deduplicate similar actions
    seen = set()
    unique = []
    for action in actions:
        key = action.get("action", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(action)

    if not unique:
        return None

    if len(unique) > 4:
        return "The valley is full of activity. People working, talking, living."

    parts = []
    for action in unique[:3]:
        text = action.get("action", "")
        if text:
            # Lowercase first letter for weaving
            text = text[0].lower() + text[1:] if text else ""
            parts.append(text)

    if not parts:
        return None

    if len(parts) == 1:
        return parts[0].capitalize() + "."
    elif len(parts) == 2:
        return parts[0].capitalize() + ". " + parts[1].capitalize() + "."
    else:
        return parts[0].capitalize() + ". " + parts[1].capitalize() + ". " + parts[2].capitalize() + "."


# ── CONVERSATION PROSE ──

def _weave_conversations(conversations: list) -> Optional[str]:
    """Weave NPC conversations into prose."""
    if not conversations:
        return None

    parts = []
    for convo in conversations[:3]:
        text = convo.get("text", "")
        if text:
            parts.append(text)

    if not parts:
        return None

    return " ".join(parts)


# ── SOCIAL CHANGE PROSE ──

SOCIAL_PROSE_TEMPLATES = {
    "new_friendship": [
        "Something new is growing between {a} and {b}. You can see it in how they move around each other.",
        "{a} and {b} seem closer than before. The kind of closeness that doesn't need explaining.",
    ],
    "new_conflict": [
        "Tension between {a} and {b}. It's in the air, the way they avoid each other.",
        "Something happened between {a} and {b}. The valley feels it.",
        "{a} and {b} are not speaking. The silence between them is loud.",
    ],
    "new_alliance": [
        "{a} and {b} have found common ground. You see them talking, planning.",
        "An understanding between {a} and {b}. The kind that makes things happen.",
    ],
    "breakup": [
        "It's over between {a} and {b}. The valley feels the weight of it.",
        "{a} and {b} are no longer what they were. The space between them is different now.",
    ],
    "rivalry": [
        "A rivalry is forming between {a} and {b}. Competitive energy, sharp edges.",
        "{a} and {b} are watching each other. The kind of watching that precedes something.",
    ],
    "relationship_shift": [
        "Something has shifted between {a} and {b}. The dynamic is different now.",
        "The relationship between {a} and {b} is changing. You can feel it.",
    ],
}


def _weave_social_changes(changes: list) -> Optional[str]:
    """Weave social changes into prose."""
    if not changes:
        return None

    parts = []
    for change in changes[:2]:
        ctype = change.get("type", "")
        desc = change.get("description", "")

        # Try to extract names from description
        # The description usually contains NPC names
        template_key = ctype if ctype in SOCIAL_PROSE_TEMPLATES else None

        if template_key and "{" in " ".join(SOCIAL_PROSE_TEMPLATES.get(template_key, [])):
            # Use template if we can extract names
            parts.append(desc)
        else:
            parts.append(desc)

    if not parts:
        return None

    return " ".join(parts)


# ── EVENT PROSE ──

def _weave_events(events: list) -> Optional[str]:
    """Weave emergent events into prose."""
    if not events:
        return None

    parts = []
    for event in events[:2]:
        title = event.get("title", "")
        desc = event.get("description", "")
        if title and desc:
            parts.append(f"{title}. {desc}")
        elif desc:
            parts.append(desc)
        elif title:
            parts.append(title)

    if not parts:
        return None

    return " ".join(parts)


# ── ECOLOGY PROSE ──

def _weave_ecology(ecology_events: list) -> Optional[str]:
    """Weave ecology events into prose."""
    if not ecology_events:
        return None

    parts = []
    for eco in ecology_events[:2]:
        desc = eco.get("description", "")
        if desc:
            parts.append(desc)

    if not parts:
        return None

    return " ".join(parts)


# ── SEASON PROSE ──

SEASON_CHANGE_PROSE = {
    "spring": "Spring is coming. The days are getting longer. The first green is showing on the cedars.",
    "summer": "Summer. The light lasts until late. The valley is warm and the creek is low.",
    "autumn": "Autumn. The light is golden and the air is cooling. The first frost is coming.",
    "winter": "Winter. The days are short. The cold settles in. The valley goes quiet.",
}


def _weave_season(season_event: Optional[str], new_season: str) -> Optional[str]:
    """Weave season change into prose."""
    if season_event:
        return season_event
    if new_season:
        return SEASON_CHANGE_PROSE.get(new_season)
    return None


# ── NARRATIVE MOMENT PROSE ──

def _weave_narrative_moments(moments: list) -> Optional[str]:
    """Weave story arc moments into prose."""
    if not moments:
        return None

    parts = []
    for moment in moments[:2]:
        content = moment.get("content", "")
        if content:
            parts.append(content)

    if not parts:
        return None

    return " ".join(parts)


# ── RITUAL PROSE ──

def _weave_rituals(rituals: list) -> Optional[str]:
    """Weave ritual events into prose."""
    if not rituals:
        return None

    parts = []
    for ritual in rituals[:2]:
        desc = ritual.get("description", "")
        if desc:
            parts.append(desc)

    if not parts:
        return None

    return " ".join(parts)


# ── MAIN PROSE GENERATOR ──

def generate_tick_prose(tick_result: dict, tick_num: int) -> Optional[str]:
    """
    Generate a prose narrative passage from a simulation tick result.

    Returns a single cohesive prose string, or None if nothing notable happened.
    """
    time_info = tick_result.get("time", {})
    weather_info = tick_result.get("weather", {})

    tod = time_info.get("time_of_day", "morning")
    season = time_info.get("season", "spring")
    hour = time_info.get("hour", 8)
    condition = weather_info.get("condition", "clear")
    temp = weather_info.get("temperature", 12)

    # Collect all prose fragments
    fragments = []

    # 1. Opening: time of day
    opening = _get_time_opening(tod)
    fragments.append(opening)

    # 2. Weather (only if changed or notable)
    if weather_info.get("changed") or condition in ("storm", "foggy"):
        weather_prose = _get_weather_prose(condition, tod)
        fragments.append(weather_prose)

    # 3. Temperature (only if notable)
    temp_prose = _get_temp_prose(temp)
    if temp_prose:
        fragments.append(temp_prose)

    # 4. Season change
    if time_info.get("season_changed"):
        season_prose = _weave_season(
            tick_result.get("season_event"),
            season
        )
        if season_prose:
            fragments.append(season_prose)

    # 5. NPC movements
    moves_prose = _weave_movements(tick_result.get("npc_moves", []), tod)
    if moves_prose:
        fragments.append(moves_prose)

    # 6. NPC actions
    actions_prose = _weave_npc_actions(tick_result.get("npc_ai_actions", []))
    if actions_prose:
        fragments.append(actions_prose)

    # 7. NPC conversations
    convo_prose = _weave_conversations(tick_result.get("npc_conversations", []))
    if convo_prose:
        fragments.append(convo_prose)

    # 8. Social changes
    social_prose = _weave_social_changes(tick_result.get("social_changes", []))
    if social_prose:
        fragments.append(social_prose)

    # 9. Emergent events
    event_prose = _weave_events(tick_result.get("emergent_events", []))
    if event_prose:
        fragments.append(event_prose)

    # 10. Ecology
    eco_prose = _weave_ecology(tick_result.get("ecology_events", []))
    if eco_prose:
        fragments.append(eco_prose)

    # 11. Narrative moments
    narrative_prose = _weave_narrative_moments(tick_result.get("narrative_moments", []))
    if narrative_prose:
        fragments.append(narrative_prose)

    # 12. Rituals
    ritual_prose = _weave_rituals(tick_result.get("ritual_events", []))
    if ritual_prose:
        fragments.append(ritual_prose)

    # If nothing notable happened, return a quiet moment
    if len(fragments) <= 1:
        # Only the opening — nothing else happened
        quiet_moments = [
            "The valley is quiet. The kind of quiet that has texture — the creek, the wind, the creak of the cabin.",
            "Nothing remarkable. The day passes the way days do here — slowly, completely.",
            "The world is still. The cedars stand. The creek runs.",
            "A quiet hour. The cabin settles. The fire ticks.",
            "The valley breathes. Nothing more, nothing less.",
        ]
        fragments.append(random.choice(quiet_moments))

    # Join fragments into prose
    prose = " ".join(fragments)

    # Build header
    tod_display = tod.replace("_", " ")
    header = f"[{season.title()} — {tod_display}, hour {hour:02d}]"

    return f"{header}\n{prose}"


def generate_periodic_summary(tick_results: list, total_ticks: int, world_hours: float) -> str:
    """
    Generate a periodic summary passage from multiple ticks.
    Called every N ticks to provide a broader narrative view.
    """
    if not tick_results:
        return ""

    # Collect notable events across all ticks
    all_conversations = []
    all_events = []
    all_social = []

    for result in tick_results:
        all_conversations.extend(result.get("npc_conversations", []))
        all_events.extend(result.get("emergent_events", []))
        all_social.extend(result.get("social_changes", []))

    parts = []

    # Opening
    if world_hours >= 24:
        parts.append(f"Over the past day ({total_ticks} hours), the valley has been alive.")
    else:
        parts.append(f"The past {int(world_hours)} hours in the valley:")

    # Notable conversations
    if all_conversations:
        notable = random.sample(all_conversations, min(3, len(all_conversations)))
        for convo in notable:
            text = convo.get("text", "")
            if text:
                parts.append(text)

    # Notable events
    if all_events:
        for event in all_events[:2]:
            title = event.get("title", "")
            desc = event.get("description", "")
            if title:
                parts.append(f"{title}. {desc}" if desc else title)

    # Notable social changes
    if all_social:
        for change in all_social[:2]:
            desc = change.get("description", "")
            if desc:
                parts.append(desc)

    if len(parts) <= 1:
        parts.append("The valley continues its quiet rhythm. The cedars stand. The creek runs.")

    return "\n\n".join(parts)
