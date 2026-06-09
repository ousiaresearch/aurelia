"""
npc_dialogue.py — NPC-to-NPC dialogue system.

When two NPCs are in the same location, they can initiate conversations.
Dialogue is generated from:
- Relationship type and affinity (strangers talk differently than close friends)
- Personality traits (a quiet person speaks differently than a boisterous one)
- Location context (workshop talk vs. ridgeline talk)
- Time of day (morning greetings vs. evening reflections)
- Recent events (mushroom bloom, traveling trader, weather)
- Occupation overlap (two woodworkers have different things to say than a woodworker and a ranger)
- Current goals and mood

Output is prose — actual dialogue that gets logged to the narrative.
"""

import json
import random
import time
from typing import Optional

from .world_state import get_db, log_event, get_npc_relationships, DB_PATH
from .npc_memory import (
    get_salient_memories, get_emotional_summary, remember_conversation,
    reinforce_memories, format_memory_for_dialogue, store_memory,
)


def _get_npc_relationship(db, npc_a_id: str, npc_b_id: str) -> Optional[dict]:
    """Get the relationship between two NPCs."""
    rels = get_npc_relationships(db, npc_a_id)
    for rel in rels:
        other_id = rel.get("npc_b") if rel.get("npc_a") == npc_a_id else rel.get("npc_a")
        if other_id == npc_b_id:
            return rel
    return None


# ── DIALOGUE TOPICS BY LOCATION ──

LOCATION_TOPICS = {
    "cabin": ["the fire", "the weather", "food", "the valley", "neighbors", "the wine cellar"],
    "cabin_main_room": ["work", "the news", "plans", "the weather", "supplies"],
    "cabin_kitchen": ["cooking", "food", "recipes", "the garden", "the harvest"],
    "cabin_deck": ["the view", "the mountains", "the stars", "the weather", "Francis"],
    "cabin_bedroom": ["rest", "dreams", "troubles", "plans"],
    "wine_cellar": ["wine", "patience", "time", "memories", "the collection"],
    "workshop": ["wood", "tools", "a project", "craft", "technique", "repairs"],
    "garden": ["growing things", "the soil", "the season", "weeds", "harvest"],
    "cedar_trail": ["the forest", "trail conditions", "wildlife", "mushrooms", "the old growth"],
    "mountain_creek": ["the water", "fish", "the cold", "the sound", "the stones"],
    "cedar_deep": ["the old trees", "silence", "moss", "the deep forest", "mushrooms"],
    "forest_edge": ["the meadow", "wildlife", "the tree line", "weather signs", "tracks"],
    "ridgeline": ["the view", "the stars", "the mountains", "thinking", "the world below"],
    "clearing": ["the sky", "wildflowers", "the gathering", "rest", "the view"],
}

# ── DIALOGUE TEMPLATES BY RELATIONSHIP TYPE ──

def _greeting(affinity: float, time_of_day: str) -> str:
    """Generate a greeting based on relationship and time."""
    if affinity > 0.8:
        greetings = [
            "catches their eye and smiles.",
            "waves them over.",
            "nods warmly.",
            "walks over without a word — no need for one.",
        ]
    elif affinity > 0.6:
        greetings = [
            "nods in greeting.",
            "raises a hand.",
            "smiles.",
            "says hello.",
        ]
    elif affinity > 0.4:
        greetings = [
            "acknowledges them.",
            "gives a brief nod.",
            "says hello politely.",
        ]
    elif affinity > 0.2:
        greetings = [
            "glances over.",
            "gives a curt nod.",
            "acknowledges them briefly.",
        ]
    else:
        greetings = [
            "looks away.",
            "doesn't acknowledge them.",
            "turns slightly.",
        ]
    return random.choice(greetings)


def _conversation_topic(npc_a: dict, npc_b: dict, location_id: str, world_state: dict) -> Optional[str]:
    """Determine what two NPCs talk about."""
    topics = LOCATION_TOPICS.get(location_id, ["the weather", "the day", "work"])

    # Check for shared occupation
    occ_a = npc_a.get("occupation", "")
    occ_b = npc_b.get("occupation", "")
    if occ_a == occ_b and occ_a:
        shared_occ_topics = {
            "carpenter": [
                "A joint dovetail — the kind that holds without glue.",
                "The grain on a piece of fir they're working. It's extraordinary.",
                "A client who doesn't know what they want. The usual.",
            ],
            "woodworker": [
                "The smell of fresh-cut cedar. You never get tired of it.",
                "A new technique they're trying. It's not working yet.",
                "The difference between oak and maple. It's everything.",
            ],
            "mushroom_forager": [
                "The chanterelle patch near the big cedar. It's producing.",
                "A morel they found. Small, but perfect.",
                "The rain means more coming. They can feel it.",
            ],
            "herbalist": [
                "A tincture that's not setting right. The proportions are off.",
                "The lavender is early this year. Something about the spring.",
                "A plant they can't identify. It's driving them crazy.",
            ],
            "forest_ranger": [
                "Trail washout on the south ridge. They'll need to flag it.",
                "The elk are moving early. Something's shifting.",
                "A section of trail that needs rerouting. The erosion is bad.",
            ],
            "fisher": [
                "The creek is running low. The fish are holding deep.",
                "A fly pattern that's working. They'll share it.",
                "The trout are spawning. Best to leave them alone.",
            ],
            "organic_farmer": [
                "The tomato blight. It's spreading.",
                "The compost pile needs turning. It's been weeks.",
                "The greenhouse took a frost. Lost the starts.",
            ],
        }
        if occ_a in shared_occ_topics:
            return random.choice(shared_occ_topics[occ_a])

    # Check for complementary occupations
    complementary = {
        ("forest_ranger", "mushroom_forager"): [
            "The ranger mentions a trail the forager should see. The mushrooms there are extraordinary.",
            "The forager shows the ranger a mushroom. The ranger has never seen one like it.",
        ],
        ("mushroom_forager", "herbalist"): [
            "The forager brings the herbologist a specimen. They debate its properties.",
            "They compare notes on what's growing where. The forest is generous this year.",
        ],
        ("carpenter", "woodworker"): [
            "They discuss a joint project. The wood is right but the design needs work.",
            "The carpenter admires the woodworker's latest piece. The joinery is flawless.",
        ],
        ("fisher", "naturalist"): [
            "The fisher describes the creek conditions. The naturalist takes notes.",
            "They discuss the fish population. The naturalist has data; the fisher has experience.",
        ],
        ("writer", "poet"): [
            "They argue about a word. The writer wants precision; the poet wants music.",
            "The poet reads a line aloud. The writer considers it. 'Change the second word.'",
        ],
        ("astronomer", "guide"): [
            "The astronomer points out a star. The guide knows the mountain but not the sky.",
            "They plan a night hike. The stars will be extraordinary from the ridgeline.",
        ],
        ("chef", "organic_farmer"): [
            "The chef asks about the chard. The farmer says it's the best they've grown.",
            "They discuss what to plant next season. The chef has opinions.",
        ],
        ("brewer", "beekeeper"): [
            "The brewer needs honey. The beekeeper has extra. A trade is discussed.",
            "They talk about the honey. The brewer says it will make a good mead.",
        ],
    }
    key = (occ_a, occ_b)
    key_rev = (occ_b, occ_a)
    if key in complementary:
        return random.choice(complementary[key])
    if key_rev in complementary:
        return random.choice(complementary[key_rev])

    # Default: pick a location topic
    if topics:
        topic = random.choice(topics)
        return _generic_topic_dialogue(topic, npc_a, npc_b)

    return None


def _generic_topic_dialogue(topic: str, npc_a: dict, npc_b: dict) -> str:
    """Generate generic dialogue for a topic."""
    name_a = npc_a.get("name", "Someone")
    name_b = npc_b.get("name", "Someone")

    templates = {
        "the weather": [
            f"{name_a} comments on the weather. {name_b} agrees — it's been unusual.",
            f"'Strange weather,' {name_a} says. {name_b} nods. They stand in silence for a moment.",
            f"{name_a} and {name_b} discuss the forecast. Neither is sure what's coming.",
        ],
        "the view": [
            f"{name_a} gestures at the view. {name_b} has seen it a thousand times but looks anyway.",
            f"'Never gets old,' {name_a} says. {name_b} doesn't respond, but doesn't disagree.",
            f"They stand together, looking out. The mountains don't need commentary.",
        ],
        "the stars": [
            f"{name_a} points out a constellation. {name_b} can never remember the names.",
            f"'Francis is bright tonight,' {name_a} says. {name_b} looks up. The red dwarf is clear.",
            f"They watch the sky in comfortable silence. The stars are enough.",
        ],
        "work": [
            f"{name_a} asks about {name_b}'s current project. The answer is long and detailed.",
            f"They discuss the day's work. Small frustrations, small victories.",
            f"{name_a} offers to help with something. {name_b} accepts gratefully.",
        ],
        "food": [
            f"{name_a} mentions they're hungry. {name_b} suggests the cabin — there's bread.",
            f"They discuss what to make for dinner. The garden has chard. That's something.",
            f"{name_a} offers {name_b} something from their pocket. It's still warm.",
        ],
        "neighbors": [
            f"{name_a} mentions someone they saw earlier. {name_b} has news too.",
            f"They exchange observations about the community. Nothing dramatic. Just life.",
            f"{name_a} wonders how someone is doing. {name_b} saw them yesterday. They're fine.",
        ],
        "the forest": [
            f"{name_a} mentions the cedars. {name_b} says they're the oldest things in the valley.",
            f"They discuss the trail conditions. The forest is wet. Everything is growing.",
            f"{name_a} heard something in the deep forest last night. {name_b} doesn't ask what.",
        ],
        "mushrooms": [
            f"{name_a} asks if the mushrooms are up yet. {name_b} says they've seen signs.",
            f"They discuss the best spots. Some secrets are shared. Some aren't.",
            f"{name_a} found chanterelles. {name_b} is impressed. The patch is usually barren.",
        ],
        "the water": [
            f"{name_a} mentions the creek is running low. {name_b} has noticed.",
            f"They discuss the water. It's clear. Cold. Good.",
            f"{name_a} says the fish are holding deep. {name_b} says they always do this time of year.",
        ],
        "wildlife": [
            f"{name_a} saw a black bear near the garden. {name_b} says it's been coming around.",
            f"They discuss the elk. The herd is moving. You can hear them at night.",
            f"{name_a} mentions the fox. {name_b} says it's been bold lately.",
        ],
        "the season": [
            f"{name_a} says spring is early this year. {name_b} agrees.",
            f"They discuss what to plant. The frost date is uncertain.",
            f"{name_a} says the days are getting longer. {name_b} has noticed.",
        ],
        "thinking": [
            f"{name_a} is quiet for a long time. {name_b} waits.",
            f"'I've been thinking about something,' {name_a} says. {name_b} listens.",
            f"They sit in silence. Some conversations don't need words.",
        ],
        "the mountains": [
            f"{name_a} points to the ridgeline. {name_b} knows every peak.",
            f"They discuss the mountains. The snow is melting. The passes will open soon.",
            f"{name_a} asks about a trail. {name_b} describes it in detail.",
        ],
        "Francis": [
            f"'Francis is visible tonight,' {name_a} says. {name_b} looks up.",
            f"They discuss the red dwarf. {name_a} has been tracking it for years.",
            f"{name_a} says Francis is their favorite star. {name_b} asks why. 'It doesn't demand attention.'",
        ],
        "wine": [
            f"{name_a} mentions a bottle they've been saving. {name_b} is curious.",
            f"They discuss the wine cellar. Sixty-three bottles. Each one a memory.",
            f"{name_a} asks {name_b}'s opinion on a vintage. {name_b} considers carefully.",
        ],
        "tools": [
            f"{name_a} shows {name_b} a new tool. {name_b} examines it with professional interest.",
            f"They discuss technique. The right tool makes all the difference.",
            f"{name_a} is sharpening something. {name_b} watches. It's meditative.",
        ],
        "a project": [
            f"{name_a} describes a project they're working on. {name_b} offers a suggestion.",
            f"They discuss the design. It's not quite right yet. They'll keep working.",
            f"{name_a} is stuck on something. {name_b} has an idea. It might work.",
        ],
        "craft": [
            f"{name_a} and {name_b} discuss the craft. The old ways vs. the new.",
            f"They compare techniques. Each has something the other doesn't.",
            f"{name_a} admires {name_b}'s work. {name_b} deflects the compliment.",
        ],
        "repairs": [
            f"{name_a} mentions something that needs fixing. {name_b} says they'll look at it.",
            f"They discuss what's broken. The list is long. They prioritize.",
            f"{name_a} fixed something {name_b} broke. {name_b} is grateful and embarrassed.",
        ],
        "the garden": [
            f"{name_a} asks about the garden. {name_b} says the chard is coming in strong.",
            f"They discuss what to plant next. The season is short. Every choice matters.",
            f"{name_a} offers starts from their greenhouse. {name_b} accepts.",
        ],
        "the harvest": [
            f"{name_a} mentions the harvest. {name_b} says it's been good this year.",
            f"They discuss preservation. What to dry, what to can, what to give away.",
            f"{name_a} has more than they can use. {name_b} knows someone who needs it.",
        ],
        "rest": [
            f"{name_a} looks tired. {name_b} tells them to rest. {name_a} says they will.",
            f"They sit quietly. Rest is its own kind of work.",
            f"{name_a} says they haven't been sleeping. {name_b} nods. They understand.",
        ],
        "dreams": [
            f"{name_a} had a strange dream. {name_b} listens without judgment.",
            f"They discuss dreams. {name_b} doesn't remember theirs. {name_a} remembers everything.",
            f"{name_a} says the forest was in their dream. {name_b} says that's not unusual.",
        ],
        "troubles": [
            f"{name_a} seems troubled. {name_b} doesn't push. They just stay.",
            f"Something is weighing on {name_a}. {name_b} waits. Eventually, {name_a} talks.",
            f"{name_a} shares a worry. {name_b} doesn't have answers. They listen anyway.",
        ],
        "plans": [
            f"{name_a} mentions their plans. {name_b} offers encouragement.",
            f"They discuss what's next. The future is uncertain. They plan anyway.",
            f"{name_a} is thinking of changing something. {name_b} asks questions.",
        ],
        "the news": [
            f"{name_a} shares news from town. {name_b} listens. The valley is small; news travels.",
            f"They discuss what's happening. Nothing dramatic. Just the rhythm of the community.",
            f"{name_a} heard something interesting. {name_b} wants details.",
        ],
        "supplies": [
            f"{name_a} mentions they're running low on something. {name_b} might have extra.",
            f"They discuss supplies. The next trip to town is soon. They make a list.",
            f"{name_a} offers {name_b} something they don't need. {name_b} accepts.",
        ],
        "cooking": [
            f"{name_a} asks {name_b} how they made something. {name_b} explains.",
            f"They discuss recipes. {name_a} has a new one. {name_b} is skeptical but willing.",
            f"{name_a} offers to cook. {name_b} says they'll bring wine.",
        ],
        "recipes": [
            f"{name_a} shares a recipe. {name_b} takes mental notes.",
            f"They discuss ingredients. Some are easy to get. Others require a trip to town.",
            f"{name_a} asks for {name_b}'s recipe. {name_b} says it's a secret. {name_a} laughs.",
        ],
        "the old trees": [
            f"{name_a} mentions the old-growth cedars. {name_b} says some are three hundred years old.",
            f"They discuss the deep forest. It's quiet there. The trees remember.",
            f"{name_a} asks about a specific tree. {name_b} knows it. They describe it.",
        ],
        "silence": [
            f"{name_a} and {name_b} sit in silence. It's comfortable.",
            f"Neither speaks. The forest speaks for them.",
            f"The silence between them is its own language.",
        ],
        "moss": [
            f"{name_a} points out the moss on the north side of the trees. {name_b} already knew.",
            f"They discuss the moss. It's thick this year. The rain has been good.",
            f"{name_a} says the moss tells you something about the forest. {name_b} agrees.",
        ],
        "the deep forest": [
            f"{name_a} mentions the deep forest. {name_b} says they don't go there often.",
            f"They discuss what's in the deep forest. Neither knows for sure.",
            f"{name_a} says the deep forest is different. {name_b} nods. It is.",
        ],
        "the meadow": [
            f"{name_a} mentions the meadow. {name_b} says the wildflowers are coming in.",
            f"They discuss the meadow. It's the best view in the valley.",
            f"{name_a} saw deer in the meadow. {name_b} says they're always there at dusk.",
        ],
        "the tree line": [
            f"{name_a} points to the tree line. {name_b} knows every marker.",
            f"They discuss the tree line. It's moving. The forest is reclaiming the meadow.",
            f"{name_a} asks about the tree line. {name_b} explains the ecology.",
        ],
        "weather signs": [
            f"{name_a} reads the clouds. {name_b} reads the wind. They compare notes.",
            f"They discuss the weather. {name_a} thinks rain. {name_b} thinks clear. They'll see.",
            f"{name_a} says the birds know something. {name_b} watches them.",
        ],
        "tracks": [
            f"{name_a} shows {name_b} a track. {name_b} identifies it immediately.",
            f"They discuss what passed through. The forest leaves messages.",
            f"{name_a} found a track they don't recognize. {name_b} is curious.",
        ],
        "the sky": [
            f"{name_a} looks up. {name_b} follows their gaze. The sky is wide.",
            f"They discuss the sky. Clouds moving in from the west. Something's coming.",
            f"{name_a} says the sky is the best thing about the clearing. {name_b} agrees.",
        ],
        "wildflowers": [
            f"{name_a} points out the lupine. {name_b} says it's the best bloom in years.",
            f"They discuss the wildflowers. The clearing is purple. It won't last.",
            f"{name_a} picks a flower. {name_b} says to leave them. {name_a} puts it back.",
        ],
        "the gathering": [
            f"{name_a} mentions the last gathering. {name_b} was there. They remember it differently.",
            f"They discuss the next gathering. Who will come. What to bring.",
            f"{name_a} suggests a gathering. {name_b} says they'll spread the word.",
        ],
        "the world below": [
            f"{name_a} looks down at the valley. {name_b} knows every cabin.",
            f"They discuss the world below. It looks small from up here.",
            f"{name_a} says the valley looks peaceful. {name_b} says it is. Mostly.",
        ],
        "patience": [
            f"{name_a} says patience is the hardest thing. {name_b} agrees.",
            f"They discuss patience. Wine. Wood. Growing things. All of it takes time.",
            f"{name_a} is impatient about something. {name_b} tells them to wait.",
        ],
        "time": [
            f"{name_a} says time moves differently here. {name_b} has noticed.",
            f"They discuss time. The seasons. The years. The trees that were here before them.",
            f"{name_a} says they're running out of time. {name_b} doesn't ask for what.",
        ],
        "memories": [
            f"{name_a} mentions a memory. {name_b} listens.",
            f"They share memories. Some overlap. Some are new to each other.",
            f"{name_a} remembers something {name_b} had forgotten. {name_b} is grateful.",
        ],
        "the collection": [
            f"{name_a} asks about the wine collection. {name_b} describes a few bottles.",
            f"They discuss the collection. Sixty-three bottles. Each one chosen.",
            f"{name_a} wants to try a specific bottle. {name_b} says not yet. It's not ready.",
        ],
        "wood": [
            f"{name_a} discusses a piece of wood. {name_b} can tell the species by the smell.",
            f"They discuss the wood. The grain. The age. The tree it came from.",
            f"{name_a} has a piece of old-growth fir. {name_b} is envious.",
        ],
        "technique": [
            f"{name_a} demonstrates a technique. {name_b} watches carefully.",
            f"They discuss technique. The old way vs. the new way. Both have merit.",
            f"{name_a} learned something new. {name_b} wants to know what.",
        ],
    }

    if topic in templates:
        return random.choice(templates[topic])

    # Fallback
    return f"{name_a} and {name_b} talk about {topic}."


def generate_npc_conversation(db, npc_a_id: str, npc_b_id: str, location_id: str, world_state: dict) -> Optional[str]:
    """
    Generate a conversation between two NPCs.
    Returns a prose description of the conversation, or None if they don't interact.
    """
    npc_a = db.execute("SELECT * FROM agents WHERE id = ?", (npc_a_id,)).fetchone()
    npc_b = db.execute("SELECT * FROM agents WHERE id = ?", (npc_b_id,)).fetchone()

    if not npc_a or not npc_b:
        return None

    # Get relationship
    rel = _get_npc_relationship(db, npc_a_id, npc_b_id)
    affinity = 0.5
    rel_type = "acquaintance"
    if rel:
        affinity = rel.get("affinity", 0.5)
        rel_type = rel.get("relationship", "acquaintance")

    # Low affinity NPCs might not talk
    if affinity < 0.15 and random.random() > 0.3:
        return None

    # Get time of day
    time_info = world_state.get("time", {})
    tod = time_info.get("time_of_day", "morning")

    name_a = npc_a["name"]
    name_b = npc_b["name"]

    # Build the conversation
    parts = []

    # Greeting
    greeting = _greeting(affinity, tod)
    if affinity > 0.2:
        parts.append(f"{name_a} {greeting}")

    # Conversation topic
    props_a = {}
    props_b = {}
    try:
        props_a = json.loads(npc_a["properties"]) if npc_a["properties"] else {}
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        props_b = json.loads(npc_b["properties"]) if npc_b["properties"] else {}
    except (json.JSONDecodeError, TypeError):
        pass

    # ── MEMORY INTEGRATION ──
    # Check what each NPC remembers about the other
    mem_a = get_salient_memories(db, npc_a_id, limit=3, related_npc_id=npc_b_id)
    mem_b = get_salient_memories(db, npc_b_id, limit=3, related_npc_id=npc_a_id)

    # Get emotional summaries
    emotion_a = get_emotional_summary(db, npc_a_id, npc_b_id)
    emotion_b = get_emotional_summary(db, npc_b_id, npc_a_id)

    # Use memory to shape greeting
    if mem_a and mem_a[0]["current_salience"] > 0.3:
        # A salient memory influences the greeting
        top_mem = mem_a[0]
        if top_mem["emotional_valence"] > 0.3:
            # Positive memory — warmer greeting
            greeting = random.choice([
                f"{name_a} sees {name_b} and smiles.",
                f"{name_a} waves {name_b} over.",
                f"{name_a} catches {name_b}'s eye. There's warmth there.",
            ])
        elif top_mem["emotional_valence"] < -0.3:
            # Negative memory — cooler greeting
            greeting = random.choice([
                f"{name_a} notices {name_b}. The greeting is brief.",
                f"{name_a} gives {name_b} a curt nod.",
                f"{name_a} and {name_b} acknowledge each other. The air is cool.",
            ])
        # else: neutral memory, use default greeting below

    # Conversation topic — influenced by memories
    memory_dialogue = None
    if mem_a and random.random() < 0.3:  # 30% chance to reference a memory
        memory_dialogue = format_memory_for_dialogue(mem_a[0], name_a, name_b)
    elif mem_b and random.random() < 0.2:  # 20% chance from B's side
        memory_dialogue = format_memory_for_dialogue(mem_b[0], name_b, name_a)

    npc_a_data = {"name": name_a, "occupation": props_a.get("occupation", ""), "traits": props_a.get("traits", [])}
    npc_b_data = {"name": name_b, "occupation": props_b.get("occupation", ""), "traits": props_b.get("traits", [])}

    topic_dialogue = _conversation_topic(npc_a_data, npc_b_data, location_id, world_state)
    if topic_dialogue:
        parts.append(topic_dialogue)

    # Weave in memory reference if one was generated
    if memory_dialogue:
        parts.append(memory_dialogue)

    # Closing — influenced by emotional summary
    if emotion_a["overall_valence"] > 0.5 and emotion_b["overall_valence"] > 0.3:
        closings = [
            f"They part warmly.",
            f"{name_b} squeezes {name_a}'s shoulder as they leave.",
            f"'See you tomorrow,' {name_a} says. {name_b} nods.",
        ]
    elif affinity > 0.7:
        closings = [
            f"They part warmly.",
            f"{name_b} squeezes {name_a}'s shoulder as they leave.",
            f"'See you tomorrow,' {name_a} says. {name_b} nods.",
        ]
    elif affinity > 0.4:
        closings = [
            f"They nod and go their separate ways.",
            f"'Take care,' {name_a} says.",
            f"{name_b} waves as they leave.",
        ]
    elif affinity < 0.2 or emotion_a["overall_valence"] < -0.4:
        closings = [
            f"The silence between them is heavy.",
            f"{name_a} leaves without a word.",
            f"They avoid each other for the rest of the day.",
        ]
    else:
        closings = [
            f"They nod and go their separate ways.",
            f"'Take care,' {name_a} says.",
        ]
    parts.append(random.choice(closings))

    if len(parts) < 2:
        return None

    # ── STORE MEMORY OF THIS CONVERSATION ──
    was_positive = affinity > 0.4
    topic_guess = "general"
    if topic_dialogue:
        # Extract topic from the dialogue
        for t in ["weather", "work", "food", "the forest", "mushrooms", "the stars", "the mountains"]:
            if t in topic_dialogue.lower():
                topic_guess = t
                break

    remember_conversation(db, npc_a_id, npc_b_id, location_id, topic_guess, affinity, was_positive)

    # Reinforce any existing memories about this person
    reinforce_memories(db, npc_a_id, "conversation", related_npc_id=npc_b_id, boost=0.1)
    reinforce_memories(db, npc_b_id, "conversation", related_npc_id=npc_a_id, boost=0.1)

    return " ".join(parts)


def run_npc_conversations(db, location_id: str, npc_ids: list, world_state: dict) -> list:
    """
    Run conversations between all NPCs in a location.
    Returns a list of conversation descriptions.
    """
    if len(npc_ids) < 2:
        return []

    conversations = []
    # Not every pair talks — stochastic
    for i in range(len(npc_ids)):
        for j in range(i + 1, len(npc_ids)):
            if random.random() > 0.4:  # 40% chance per pair
                continue
            convo = generate_npc_conversation(db, npc_ids[i], npc_ids[j], location_id, world_state)
            if convo:
                conversations.append({
                    "type": "npc_conversation",
                    "location_id": location_id,
                    "text": convo,
                })

    return conversations