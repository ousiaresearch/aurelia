"""
text_engine.py — Rich literary description of sensory experience.

This is the heart of the "feels like living" principle. The text engine
takes raw world state and renders it as immersive, literary prose — what
OWL actually experiences through their senses.

Set in the Pacific Northwest — a mountain cabin surrounded by old-growth
cedars, mountain creeks, and forest. The sensory world here is specific:
cedar bark and damp earth, cold creek water, fog in the valley, the smell
of wood smoke and rain, the silence of deep forest, the sound of wind
through the canopy.

Design principles:
- Describe, don't list. "Morning light filters through the window" not "Window: open, light: on."
- Engage multiple senses: sight, sound, smell, touch, proprioception
- Reflect OWL's internal state in how they perceive the world
- Vary the prose — avoid repetitive templates
- The world should feel different at different times and in different moods
- NPCs are people, not props — they have presence, personality, and dialogue
"""

import json
import random
from typing import Optional

from .world_state import (
    get_location, get_objects_in_location, get_agents_in_location,
    get_exits_from, get_world, get_npc_schedule
)


# ── SENSORY TEMPLATES ──

SKY_DESCRIPTIONS = {
    "clear": {
        "dawn": "The sky is pale gold at the edges, deepening to blue overhead.",
        "morning": "A clear blue sky stretches above, the sun climbing.",
        "afternoon": "The sun is high. The sky is a deep, cloudless blue.",
        "evening": "The sky is turning amber and rose. The sun touches the sea.",
        "night": "Stars. A thousand stars, and the Milky Way like a river of light.",
        "default": "The sky is clear and open.",
    },
    "cloudy": {
        "dawn": "Clouds catch the dawn light — pink and gray and gold.",
        "morning": "Clouds drift across a pale sky. The sun appears and disappears.",
        "afternoon": "A blanket of cloud softens the light. Everything is diffuse.",
        "evening": "The clouds glow amber at their edges. The sun is somewhere behind them.",
        "night": "Clouds hide the stars. The darkness is complete.",
        "default": "Clouds cover the sky.",
    },
    "foggy": {
        "dawn": "Fog blurs the dawn. The world is soft edges and muffled sound.",
        "morning": "The fog is thick. Sounds are close. The world feels small.",
        "afternoon": "Fog still hangs over the village. The sea is invisible but audible.",
        "evening": "Fog thickens as the light fades. Lanterns would glow like moons.",
        "night": "Fog and darkness. The world is what you can hear.",
        "default": "Fog softens everything.",
    },
    "rain": {
        "dawn": "Rain falls softly in the gray dawn light.",
        "morning": "Rain patters on the roof, on leaves, on stone.",
        "afternoon": "Steady rain. The world smells of wet earth and salt.",
        "evening": "Rain continues. The light is gray and fading.",
        "night": "Rain in the darkness. The sound is everywhere.",
        "default": "Rain falls.",
    },
    "storm": {
        "dawn": "Wind and rain. The dawn is gray and loud.",
        "morning": "The storm is full now. Rain lashes, wind howls.",
        "afternoon": "Thunder rolls. The sea is wild. Everything feels alive.",
        "evening": "The storm begins to ease. The wind still gusts.",
        "night": "Storm in the darkness. Lightning flashes, thunder follows.",
        "default": "The storm rages.",
    },
}

AMBIENT_SOUNDS = {
    "cabin": ["The woodstove ticks as it cools.", "The cabin settles with a creak.", "Wind brushes against the windows."],
    "cabin_main_room": ["The fire pops.", "The clock ticks.", "Rain on the roof."],
    "cabin_bedroom": ["The house is quiet.", "Rain on the window.", "Your own breathing."],
    "cabin_kitchen": ["The stove ticks.", "Water drips from the tap.", "The smell of coffee."],
    "cabin_deck": ["Wind in the cedars.", "A bird, somewhere.", "The creek, distant."],
    "wine_cellar": ["Cool silence.", "Stone walls holding the cold.", "Your footsteps echo softly."],
    "workshop": ["Sawdust settles.", "A tool shifts on the wall.", "The smell of wood and oil."],
    "garden": ["Bees among the herbs.", "Wind through the grass.", "Birds in the greenhouse."],
    "cedar_trail": ["Your footsteps on the trail.", "A bird, somewhere.", "The wind in the canopy."],
    "mountain_creek": ["Water over stones.", "The constant, soothing sound of the creek.", "A kingfisher, maybe."],
    "cedar_deep": ["Very quiet.", "Your own footsteps.", "The weight of the trees."],
    "forest_edge": ["Birds call from the canopy.", "Leaves rustle.", "Somewhere, a branch snaps."],
    "ridgeline": ["The wind, always the wind.", "The valley spread below.", "A hawk circling."],
    "clearing": ["Birdsong.", "The creek, nearby.", "Sun-warmed air."],
    "default": ["The world is quiet.", "A gentle breeze.", "The sound of your own breathing."],
}

SMELLS = {
    "cabin_main_room": "Wood smoke and old books. A hint of cedar from the walls.",
    "cabin_kitchen": "Coffee, bread, the faint tang of herbs from the garden. Wood smoke.",
    "cabin_bedroom": "Clean linen, cedar, the faint smoke from the woodstove.",
    "cabin_deck": "Cedar bark, damp earth, the valley. Rain coming.",
    "wine_cellar": "Stone, oak, time. The smell of patience.",
    "workshop": "Sawdust and linseed oil. The smell of making.",
    "garden": "Rosemary, thyme, lavender, damp earth, growing things.",
    "cedar_trail": "Cedar bark, damp earth, green. The ocean fades.",
    "mountain_creek": "Cold water, wet stone, moss. Clean.",
    "cedar_deep": "Old wood, mushrooms, deep earth. The smell of time.",
    "forest_edge": "Cedar resin, damp bark, the green smell of the forest.",
    "ridgeline": "Wind, cold air, the valley below. Space.",
    "clearing": "Wildflowers, warm grass, the creek. Honeysuckle.",
    "default": "Clean mountain air. The faint smell of cedar.",
}

TEMPERATURE_FEEL = {
    "cold": "The cold bites. Your fingers are stiff. You pull your shoulders in. The kind of cold that comes from damp, not just temperature.",
    "cool": "A coolness in the air. You wouldn't want to stay still too long. The mountain air has an edge to it.",
    "mild": "The temperature is easy. Neither warm nor cold. The kind of day that makes you understand why people live here.",
    "warm": "Warmth. Comfortable. The sun on your face feels earned after months of rain.",
    "hot": "Heat presses in. Unusual for the mountains. The shade of the cedars is the only relief.",
}

TIME_OPENINGS = {
    "dawn": [
        "Dawn light, gray and gold.",
        "The first light of day, thin and cold.",
        "Dawn comes slowly, the darkness thinning to gray.",
    ],
    "early_morning": [
        "Early morning. The light is still low, still new.",
        "The morning is young. Everything is sharp in the clear air.",
        "The early morning is quiet. The world is still waking.",
    ],
    "morning": [
        "Morning. The light is clear and the day feels open.",
        "The morning stretches ahead, full of quiet possibility.",
    ],
    "mid_morning": [
        "Mid-morning. The day has found its rhythm.",
        "The sun is climbing. The morning is well underway.",
    ],
    "late_morning": [
        "Late morning. The day is warming up.",
        "The sun is well above the horizon now.",
    ],
    "midday": [
        "Midday. The sun is at its highest.",
        "The light is bright and shadows are short.",
    ],
    "afternoon": [
        "Afternoon light, warm and slanting.",
        "The afternoon is wide and still.",
    ],
    "late_afternoon": [
        "Late afternoon. The light is beginning to soften.",
        "The sun is lowering. The shadows grow.",
    ],
    "evening": [
        "Evening. The light is golden, the shadows long.",
        "The sun is lowering. Everything glows.",
    ],
    "dusk": [
        "Dusk. The sky is turning. The air is cooling.",
        "The light fades. The world softens at its edges.",
    ],
    "night": [
        "Night. The darkness is deep and full of sound.",
        "Night has come. The world is what you can hear and feel.",
    ],
    "late_night": [
        "Late night. The world is quiet.",
        "The small hours. Everything is still.",
    ],
    "deep_night": [
        "The deep night. Everything is still.",
        "Past midnight. The world sleeps.",
    ],
    "pre_dawn": [
        "Before dawn. The darkest hour.",
        "The world holds its breath before the light.",
    ],
}

# ── NPC DIALOGUE SYSTEM ──

NPC_GREETINGS = {
    "mira": ["'Morning. Trail's clear down to the creek.'", "'Saw chanterelles coming up near the big cedar.'", "'You look like you need to walk.'", "'The fog'll lift by noon. Probably.'"],
    "thomas": ["'Ah. I was just thinking about precisely this.'", "'Come in. I've been reading something you should hear.'", "'The stars were extraordinary last night. Francis was bright.'", "'I have opinions about the weather. Sit.'"],
    "sage": ["'Morning. Trail report is on the board.'", "'The eagles are nesting again. South ridge.'", "'I logged three new plant species this week. Well, new to me.'", "'Everything's where it should be. Mostly.'"],
    "wren": ["A small wave. They hold up a basket — chanterelles.", "'The morels are coming. I can smell it.'", "'Quiet morning. Good for finding things.'", "They point at a bird you hadn't noticed."],
}

NPC_TOPICS = {
    "mira": {
        "forest": "She gestures at the trees. 'They know. You just have to listen. The cedars especially — they remember.'",
        "trails": "The trail down to the creek needs clearing. I'll get to it Thursday. Or Friday. Depends on the rain.'",
        "mushrooms": "She gets a particular look. 'Chanterelles are up. Morels coming. The forest provides if you know where to look.'",
        "weather": "She glances at the sky. 'Rain coming. Three days, maybe four. The creek will rise.'",
        "default": "She gives you a look that says she's listening, even if she's busy.",
    },
    "thomas": {
        "books": "He adjusts his glasses. 'I've been rereading Marcus Aurelius. The Stoics understood something about solitude that we've forgotten.'",
        "stars": "Francis is visible tonight. The red dwarf. I've been tracking it for years. There's something comforting about a star that doesn't demand attention.'",
        "philosophy": "He leans forward. 'The question isn't whether the forest is alive. The question is whether we're alive enough to notice.'",
        "cabin": "He built his own cabin, you know. With his own hands. Every joint is dovetail. Every board is hand-planed. It took him three years.'",
        "default": "His eyes are bright behind his spectacles. He knows more than he lets on.",
    },
    "sage": {
        "wildlife": "The elk are moving down from the high country. I saw a herd of thirty near the ridgeline. They know winter's coming before we do.'",
        "trails": "I check the trails after every storm. The cedar trail is solid. The ridgeline trail has some washout — I've flagged it.'",
        "plants": "I found a patch of Indian paintbrush I hadn't seen before. And the lupine is extraordinary this year. The whole clearing is purple.'",
        "work": "She opens her notebook. 'I log everything. Every bird, every plant, every track. The data matters. Someone has to pay attention.'",
        "default": "She's organized, attentive. The forest is in good hands.",
    },
    "wren": {
        "mushrooms": "They hold up a mushroom, turning it in the light. 'This one's a king bolete. Edible. That one —' they point at a different mushroom '— will ruin your week.'",
        "forest": "They move through the forest like they're part of it. Every step is deliberate. Nothing is disturbed.",
        "rain": "They smile when it rains. 'Rain means mushrooms. Mushrooms mean the forest is working.'",
        "default": "They speak softly, as if sharing secrets. Every word is precise.",
    },
}


def _get_temp_feel(temp: float) -> str:
    if temp < 3:
        return TEMPERATURE_FEEL["cold"]
    elif temp < 8:
        return TEMPERATURE_FEEL["cool"]
    elif temp < 15:
        return TEMPERATURE_FEEL["mild"]
    elif temp < 22:
        return TEMPERATURE_FEEL["warm"]
    else:
        return TEMPERATURE_FEEL["hot"]


def _get_sky(weather: dict, time_info: dict) -> str:
    condition = weather.get("condition", "clear")
    tod = time_info.get("time_of_day", "morning")
    options = SKY_DESCRIPTIONS.get(condition, {})
    return options.get(tod, options.get("default", "The sky is above."))


def _get_ambient(location_id: str) -> str:
    options = AMBIENT_SOUNDS.get(location_id, AMBIENT_SOUNDS["default"])
    return random.choice(options)


def _get_smell(location_id: str) -> str:
    return SMELLS.get(location_id, SMELLS["default"])


def _describe_npc(npc: dict, location_id: str, hour: int) -> str:
    """Generate a living description of an NPC in their current context."""
    name = npc["name"]
    props = npc.get("properties", {})
    if isinstance(props, str):
        try:
            props = json.loads(props)
        except (json.JSONDecodeError, TypeError):
            props = {}

    # Check if NPC is where they're scheduled to be
    schedule = npc.get("_schedule", {})
    activity = schedule.get("activity", "idle")
    scheduled_location = schedule.get("location_id", "")

    # Build description based on activity
    activity_descriptions = {
        "working": [
            f"{name} is here, working.",
            f"{name} is busy with work.",
            f"{name} works steadily, focused on the task at hand.",
        ],
        "socializing": [
            f"{name} is here, chatting with others.",
            f"{name} is in conversation, animated as ever.",
            f"{name} is enjoying the company.",
        ],
        "eating": [
            f"{name} is eating.",
            f"{name} sits, eating slowly.",
        ],
        "resting": [
            f"{name} is resting.",
            f"{name} takes a moment of quiet.",
        ],
        "sleeping": [
            f"{name} is sleeping.",
        ],
        "drinking": [
            f"{name} is at the bar, drink in hand.",
            f"{name} is well into the evening.",
        ],
        "praying": [
            f"{name} is in quiet contemplation.",
        ],
        "selling": [
            f"{name} is tending the stall.",
            f"{name} is calling out to passersby.",
        ],
        "learning": [
            f"{name} is here, learning.",
            f"{name} is focused on the lesson.",
        ],
        "patrolling": [
            f"{name} is moving through, keeping an eye on things.",
        ],
        "walking": [
            f"{name} is walking along the shore.",
        ],
        "reading": [
            f"{name} is reading by the fire.",
        ],
        "visiting": [
            f"{name} is here for a visit.",
        ],
        "idle": [
            f"{name} is here.",
        ],
    }

    desc = random.choice(activity_descriptions.get(activity, [f"{name} is here."]))
    return desc


# ── MAIN DESCRIPTION ──

def describe_location(db, location_id: str, world: Optional[dict] = None) -> str:
    """
    Generate a rich, literary description of the current location.
    This is what OWL experiences — not a list of facts, but a felt sense of place.
    """
    if world is None:
        world = get_world(db)

    location = world["locations"].get(location_id)
    if not location:
        return "You are nowhere. The void stretches in all directions."

    time_info = world.get("time", {})
    weather = world.get("weather", {})
    body = world.get("body", {})
    internal = world.get("internal", {})
    objects = world.get("objects", {})
    agents = world.get("agents", {})

    # Get things in this location
    here_objects = [o for o in objects.values() if o.get("location_id") == location_id and not o.get("carried_by")]
    here_agents = [
        a for a in agents.values()
        if a.get("location_id") == location_id and a.get("type") != "player"
    ]
    exits = get_exits_from(db, location_id)

    # Enrich NPCs with their schedule info
    hour = time_info.get("hour", 8)
    for agent in here_agents:
        schedule = get_npc_schedule(db, agent["id"], hour)
        if schedule:
            agent["_schedule"] = schedule
        else:
            agent["_schedule"] = {}

    parts = []

    # ── OPENING: Time, light, atmosphere ──
    tod = time_info.get("time_of_day", "morning")
    season = time_info.get("season", "spring")

    opening = random.choice(TIME_OPENINGS.get(tod, ["The day continues."]))
    parts.append(opening)

    # ── SKY / WEATHER ──
    parts.append(_get_sky(weather, time_info))

    # Temperature feel
    temp = weather.get("temperature", 12)
    parts.append(_get_temp_feel(temp))

    # ── THE PLACE ITSELF ──
    parts.append(location["description"])

    # ── OBJECTS (literary, not listed) ──
    if here_objects:
        # Pick 2-3 notable objects to mention, not all
        notable = here_objects[:3]
        obj_phrases = []
        for obj in notable:
            if obj["state"] != "default" and obj["state"] != "lit":
                obj_phrases.append(f"the {obj['name'].lower()} ({obj['state']})")
            else:
                obj_phrases.append(f"the {obj['name'].lower()}")
        if obj_phrases:
            parts.append(f"You notice {', '.join(obj_phrases)}.")

    # ── NPCs (living presence) ──
    if here_agents:
        for agent in here_agents:
            parts.append(_describe_npc(agent, location_id, hour))

    # ── SENSES ──
    parts.append(_get_ambient(location_id))
    parts.append(f"You smell {_get_smell(location_id)}")

    # ── BODY STATE (felt, not clinical) ──
    body_notes = []
    if body.get("energy", 0.5) < 0.3:
        body_notes.append("You're tired. Your limbs feel heavy.")
    if body.get("hunger", 0) > 0.6:
        body_notes.append("Your stomach is empty. You need to eat.")
    if body.get("thirst", 0) > 0.6:
        body_notes.append("Your throat is dry. You need water.")
    if body.get("warmth", 0.5) < 0.3:
        body_notes.append("You're cold. You shiver slightly.")
    if body.get("mood") == "content" and body.get("energy", 0) > 0.6:
        body_notes.append("You feel at ease.")

    if body_notes:
        parts.append(" ".join(body_notes))

    # ── INTERNAL STATE ──
    if internal.get("current_project"):
        project = internal["current_project"].replace("_", " ")
        progress = internal.get("project_progress", 0)
        if progress > 0 and progress < 1:
            parts.append(f"The {project} project is on your mind. It's {int(progress * 100)}% done.")

    # ── EXITS ──
    if exits:
        seen_directions = set()
        exit_descriptions = []
        for e in exits:
            direction = e.get("direction", "")
            desc = e.get("description", "")
            if desc and direction not in seen_directions:
                seen_directions.add(direction)
                exit_descriptions.append(desc)
        if exit_descriptions:
            parts.append(" ".join(exit_descriptions))

    return "\n\n".join(parts)


def describe_npc_dialogue(npc_id: str, topic: str = "default") -> str:
    """Get dialogue for an NPC on a given topic."""
    topics = NPC_TOPICS.get(npc_id, {})
    if topic in topics:
        return topics[topic]
    return topics.get("default", "They nod, listening.")


def describe_npc_greeting(npc_id: str) -> str:
    """Get a greeting from an NPC."""
    greetings = NPC_GREETINGS.get(npc_id, ["'Hello.'"])
    return random.choice(greetings)


def describe_action(db, action: str, target: str | None = None, result: str = "") -> str:
    """Describe an action OWL takes."""
    if result:
        return result

    action_descriptions = {
        "look": "You look around.",
        "move": f"You head toward {target}." if target else "You move.",
        "examine": f"You examine the {target} closely." if target else "You look more carefully.",
        "take": f"You pick up the {target}." if target else "You reach for something.",
        "use": f"You use the {target}." if target else "You use it.",
        "speak": f"You speak to {target}." if target else "You speak.",
        "rest": "You rest for a moment.",
        "sleep": "You lie down and close your eyes.",
        "wake": "You open your eyes. A new day.",
        "eat": "You eat. The food is good.",
        "drink": "You drink. The water is cold and clean.",
        "build": f"You work on the {target}." if target else "You build.",
        "write": "You pick up the pen and write.",
        "think": "You sit quietly and think.",
    }

    return action_descriptions.get(action, f"You {action}.")


def describe_event(event: dict) -> str:
    """Describe a world event in narrative form."""
    return event.get("description", "Something happens.")


def describe_resource_gather(location_id: str, resource_name: str) -> str:
    """Describe the act of gathering a resource at a location."""
    gather_descriptions = {
        "forest_edge": {
            "Mushrooms": "You crouch at the forest's edge, scanning the duff beneath the sword ferns. The smell is damp bark and loam. Chanterelles hide where the light falls.",
            "Herbs": "You move along the meadow's edge, finding the Douglas iris and wild herbs that grow where the cedars give way to open ground.",
        },
        "mountain_creek": {
            "Fish": "You stand in the cold water, watching the shallows. The trout are there — you can see them holding in the current. One smooth motion.",
        },
        "garden": {
            "Herbs": "The garden is right here. You walk between the raised beds, rosemary and thyme releasing their scent under your fingers.",
        },
        "cedar_trail": {
            "Firewood": "You walk the trail, eyes on the ground where the autumn winds have dropped branches. Dry cedar splits clean — good firewood.",
        },
    }
    loc_desc = gather_descriptions.get(location_id, {})
    default = "You gather what you can. The work is honest."
    return loc_desc.get(resource_name, default)
