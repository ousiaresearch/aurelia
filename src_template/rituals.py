"""
rituals.py — Seasonal rituals for the Pacific Northwest cabin world.

The cabin has a living calendar. Each season has rituals that NPCs prepare for,
participate in, and talk about. These aren't just flavor — they affect NPC moods,
create gathering points, and give the mountain its own sense of rhythm and tradition.

PNW Rituals:
- Winter: solstice_dark, new_years_ember, deep_winter_visit, story_night
- Spring: first_melt, mushroom_season_arrival, trail_opening
- Summer: midsummer_twilight, first_fire_ban, stargazing_night
- Autumn: first_frost, chanterelle_gathering, salmon_return, wood_cutting, winter_prep_check

Design principles:
- Rituals are prepared for in advance (NPCs talk about them coming)
- Rituals bring NPCs together or mark solitary passages
- Rituals affect mood and create memories
- The player can participate, observe, or help organize
- Each ritual has a unique feel and description
- atmosphere: 'cabin_bound' (stays inside), 'gathering' (people come together), 'solitary' (personal)
"""

import json
import random
import time
from typing import Optional

from .world_state import get_db, log_event, DB_PATH


# ── RITUAL DEFINITIONS ──

RITUALS = {
    # ══════════════════════════════════════
    # WINTER — Dec, Jan, Feb
    # Deepest dark. Snow. Ice. Wood-burning focus.
    # ══════════════════════════════════════

    "solstice_dark": {
        "season": "winter",
        "day": 21,
        "preparation_days": 7,
        "atmosphere": "cabin_bound",
        "title": "The Solstice Dark",
        "preparation": [
            "The shortest day approaches. Candles are being prepared. The dark is coming.",
            "Sage mentions the solstice. The longest night requires ceremony.",
            "Thomas is writing something. The solstice demands acknowledgment.",
        ],
        "day_of": [
            "The Solstice Dark. The longest night. Every candle in the cabin is lit. The darkness outside is complete, but the room glows. Sage speaks of endings and beginnings. The singing is quiet, reverent. Afterward, the fire is low and the wine is open. We made it through.",
            "Midnight of the longest night. The cabin is warm. Outside, the stars are out — Francis steady on the horizon. We sit together in the dark and wait for the light to return. It always does.",
        ],
        "after": [
            "The solstice has passed. The light will return. We endured the dark together.",
            "After the longest night, there's a feeling of quiet triumph. The days begin to lengthen again.",
        ],
        "mood_effect": "peaceful",
        "social_bonus": 0.1,
        "locations": ["cabin", "cabin_deck"],
    },

    "new_years_ember": {
        "season": "winter",
        "day": 31,
        "preparation_days": 3,
        "atmosphere": "solitary",
        "title": "New Year's Ember",
        "preparation": [
            "The year is ending. People are writing down what they want to release.",
            "The fire pit on the deck is being cleaned. New year's eve approaches.",
        ],
        "day_of": [
            "New Year's Eve. The fire pit glows on the deck. We stand in the cold and watch the old year end. No speeches. Just the embers and the mountain and the stars. At midnight, we breathe out. What we release, we release. What we carry, we carry forward.",
            "The last ember fades. A new year begins. The mountain doesn't notice, but we do. We never do this loudly — just the fire, the cold air, and the quiet understanding that time has turned the page.",
        ],
        "after": [
            "A new year. The fire is ash. The mountain is unchanged. We are not.",
            "The new year begins. The cabin feels the same and entirely different.",
        ],
        "mood_effect": "hopeful",
        "social_bonus": 0.05,
        "locations": ["cabin_deck", "ridgeline"],
    },

    "deep_winter_visit": {
        "season": "winter",
        "day": 15,
        "preparation_days": 4,
        "atmosphere": "gathering",
        "title": "Deep Winter Visit",
        "preparation": [
            "The middle of winter. It's time to check on each other.",
            "Thomas's cabin is further up the ridgeline. Sage mentions going to visit.",
            "The trails are snowbound. A visit takes planning.",
        ],
        "day_of": [
            "Deep winter visit. Someone has made the climb to Thomas's cabin. Supplies carried up through the snow. The hermit and the forester, sharing a meal in a small room while the wind howls outside. This is what community means in the mountain winter.",
            "The visit to Thomas. Sage or Wren — someone makes the climb. The trail is hard in the snow. The reward is time spent with someone who chooses to live at the edge of things. The wood stove burns bright.",
        ],
        "after": [
            "The visit is over. Thomas is less alone. The trail remembers footsteps.",
            "After the winter visit, the mountain feels a little smaller.",
        ],
        "mood_effect": "content",
        "social_bonus": 0.1,
        "locations": ["cabin", "ridgeline"],
    },

    "story_night": {
        "season": "winter",
        "day": 1,
        "preparation_days": 5,
        "atmosphere": "gathering",
        "title": "Story Night",
        "preparation": [
            "Story night is coming. Someone has a long story to tell.",
            "The firewood is stacked high. Story night requires a proper fire.",
            "Thomas is preparing something. He doesn't usually volunteer, but this time he is.",
        ],
        "day_of": [
            "Story Night! The cabin is full. Thomas tells the story of building his cabin — the winter he cut every log by hand. Wren tells a tale about the cedars that may or may not be true. Sage shares a memory of the valley below, before the fire. The fire burns low. The stories burn bright. No one wants to leave.",
            "The longest nights are for stories. Tonight, the mountain remembers. Old stories, new stories, true stories, tall stories. Someone laughs. Someone goes quiet. The fire crackles. This is what the cabin is for.",
        ],
        "after": [
            "The stories linger. Tomorrow, they'll be told again, slightly different.",
            "After story night, the cabin feels closer. We share the same mountain now.",
        ],
        "mood_effect": "content",
        "social_bonus": 0.15,
        "locations": ["cabin", "cabin_deck"],
    },

    # ══════════════════════════════════════
    # SPRING — Mar, Apr, May
    # Melt. First growth. Mushroom season begins.
    # ══════════════════════════════════════

    "first_melt": {
        "season": "spring",
        "day": 21,
        "preparation_days": 5,
        "atmosphere": "solitary",
        "title": "The First Melt",
        "preparation": [
            "The equinox approaches. The mountain is about to change.",
            "There's drip from the eaves today. The melt has begun.",
            "Sage checks the creek. It's starting to move again.",
        ],
        "day_of": [
            "The First Melt. The equinox. The creek frees with a sound like laughter. The first drip from the eaves. The snowline pulls back up the mountain an inch at a time. Something has shifted. The mountain is exhaling. We feel it in the cabin — a different quality of light, a different weight to the air.",
            "The equinox. The mountain wakes. Water moves where it was still. The cedars drip. The trail is mud but passable. A season ends and a season begins. The world smells of renewal and cold water.",
        ],
        "after": [
            "The melt continues. The mountain is awake now.",
            "After the first melt, the creek runs full. The season has turned.",
        ],
        "mood_effect": "hopeful",
        "social_bonus": 0.05,
        "locations": ["mountain_creek", "cabin", "cedar_trail"],
    },

    "mushroom_season_arrival": {
        "season": "spring",
        "day": 15,
        "preparation_days": 7,
        "atmosphere": "gathering",
        "title": "Mushroom Season Arrival",
        "preparation": [
            "Wren is already in the forest. The mushrooms are coming.",
            "The first chanterelles of the season are emerging. Wren is busy.",
            "The forest floor is changing. Mushroom season is here.",
        ],
        "day_of": [
            "Mushroom Season Arrival! Wren returns from the cedars with the first chanterelles of the year. The smell is unmistakable — fruity, apricot, something that means spring in the forest. The cabin fills with the smell of mushrooms in butter. A season begins.",
            "The first chanterelles. Wren's hands smell of forest floor and cold water. We eat them simply — butter, salt, heat. Nothing more needed. The season of plenty is starting.",
        ],
        "after": [
            "The mushrooms keep coming. Wren is out every morning now.",
            "After the season arrival, the forest gives and we receive.",
        ],
        "mood_effect": "excited",
        "social_bonus": 0.1,
        "locations": ["cedar_deep", "cabin", "forest_edge"],
    },

    "trail_opening": {
        "season": "spring",
        "day": 1,
        "preparation_days": 10,
        "atmosphere": "gathering",
        "title": "Trail Opening",
        "preparation": [
            "The mountain trails are opening. Mira is organizing trail work.",
            "The snow has pulled back enough. It's time to check the ridgeline trail.",
            "Mira has her tools ready. The trail opening is a community event.",
        ],
        "day_of": [
            "Trail Opening! Mira leads the work party up the cedar_trail. Fallen branches cleared, washed-out sections repaired, trail markers reset. The ridgeline trail is passable again. We stand at the top and look down at the cabin, small and certain in the green. The mountain is open for the season.",
            "The trails open. Mira marks the way. The community walks the ridgeline together — the first hike of the season, lungs full of cold air and pine. Everything is possible again.",
        ],
        "after": [
            "The trails are open. The mountain is navigable again.",
            "After the trail opening, we remember what we have access to.",
        ],
        "mood_effect": "alive",
        "social_bonus": 0.1,
        "locations": ["cedar_trail", "ridgeline", "clearing"],
    },

    # ══════════════════════════════════════
    # SUMMER — Jun, Jul, Aug
    # Dry. Long twilights. Fire season awareness.
    # ══════════════════════════════════════

    "midsummer_twilight": {
        "season": "summer",
        "day": 21,
        "preparation_days": 7,
        "atmosphere": "gathering",
        "title": "Midsummer Twilight",
        "preparation": [
            "The solstice approaches. Francis will be visible all night.",
            "Someone suggests staying up. The longest day demands it.",
            "The deck is swept. The chairs are ready. Midsummer is coming.",
        ],
        "day_of": [
            "Midsummer Twilight. The longest day. Francis is visible all night — the red dwarf on the horizon, steady and patient. We sit on the deck and watch the twilight that never quite becomes dark. The mountain is gold then orange then purple. The stars come out but the sky stays soft. Someone opens wine. We don't talk much. There's nothing to say that the mountain isn't already saying. This is the longest day. It will never be this long again.",
            "The solstice. The twilight lasts until nearly midnight. The cedars are silhouettes. Francis blinks on the horizon. Wren says something about old stories — how the forest talks to itself on nights like this. Thomas disagrees about the stories but agrees about the wine. Sage is quiet, watching the ridgeline. We stay up late. We always do on nights like this.",
        ],
        "after": [
            "The solstice passes. The days begin to shorten again. But not yet.",
            "After midsummer, the mountain feels known. We watched it all night.",
        ],
        "mood_effect": "alive",
        "social_bonus": 0.2,
        "locations": ["cabin_deck", "ridgeline", "clearing"],
    },

    "first_fire_ban": {
        "season": "summer",
        "day": 15,
        "preparation_days": 3,
        "atmosphere": "solitary",
        "title": "The First Fire Ban",
        "preparation": [
            "Sage delivers the news. The forest is too dry. No open flames.",
            "The summer heat is here. Fire season has begun.",
            "The woodstove can stay lit, carefully. Everything else — no.",
        ],
        "day_of": [
            "The First Fire Ban. Sage tells us with the particular gravity of someone delivering bad news they were hoping not to deliver. The forest is too dry. No fire pit. No candles on the deck. The mountain is beautiful and dangerous. We adapt. The cabin stays warm — carefully, with attention. The deck stays quiet. We wait for rain.",
            "Fire ban. The mountain shows its teeth. Sage's tone is apologetic but firm: the forest can't take a spark right now. We put away the fire pit, store the candles, and look at the cedars with new wariness. They're old. They've seen worse. But we haven't.",
        ],
        "after": [
            "The fire ban holds. We grow accustomed to the quiet deck.",
            "After the first fire ban, we learn the mountain's temper.",
        ],
        "mood_effect": "tense",
        "social_bonus": 0.0,
        "locations": ["cabin", "cedar_deep"],
    },

    "stargazing_night": {
        "season": "summer",
        "day": 15,
        "preparation_days": 3,
        "atmosphere": "solitary",
        "title": "Stargazing Night",
        "preparation": [
            "The forecast shows clear skies. Sage calls it — stargazing night.",
            "The moon will be new. The Milky Way will be visible.",
            "Someone mentions Francis. The red dwarf deserves attention.",
        ],
        "day_of": [
            "Stargazing Night. The Milky Way splits the sky. Francis blinks steady on the horizon. We lie on the deck and look up — the kind of dark that city people don't believe exists. Thomas names constellations he's invented. Wren traces the path of a satellite. Sage finds Polaris and doesn't say anything. We stay out until we're cold. We always stay out too long on nights like this.",
            "The sky is obscene with stars. Francis blinks red. We spread blankets on the deck and don't speak for a long time. Someone makes hot water with honey. The mountain is silent below us. The sky is infinite above. We are small and we are here and that's enough.",
        ],
        "after": [
            "The stars fade with the dawn. We sleep on the deck.",
            "After stargazing night, the sky stays with us for weeks.",
        ],
        "mood_effect": "peaceful",
        "social_bonus": 0.05,
        "locations": ["cabin_deck", "ridgeline"],
    },

    # ══════════════════════════════════════
    # AUTUMN — Sep, Oct, Nov
    # Harvest. Mushrooms. First frost. Salmon return. Wood cutting.
    # ══════════════════════════════════════

    "first_frost": {
        "season": "autumn",
        "day": 21,
        "preparation_days": 5,
        "atmosphere": "solitary",
        "title": "The First Frost",
        "preparation": [
            "The equinox comes. The cold is coming with it.",
            "Sage has been watching the overnight temperatures. Tonight, probably.",
            "The last of the garden is being harvested. The cold will end it.",
        ],
        "day_of": [
            "The First Frost. The garden is white. The rosemary has a crystalline edge. The cold came in the night without announcement — just arrived, the way cold does at altitude. The greenhouse held. The cold frame did not. We harvest what we can and acknowledge what we couldn't grow. The garden season is done.",
            "The equinox frost. The cold that ends things and begins things. The garden looks like it's dusted with salt. Wren says the cedars will be fine, they always are. The rest of us start thinking about wood.",
        ],
        "after": [
            "The frost holds. The garden is finished for the year.",
            "After the first frost, the mountain starts thinking about winter.",
        ],
        "mood_effect": "bittersweet",
        "social_bonus": 0.05,
        "locations": ["garden", "cabin", "forest_edge"],
    },

    "chanterelle_gathering": {
        "season": "autumn",
        "day": 15,
        "preparation_days": 7,
        "atmosphere": "gathering",
        "title": "Chanterelle Gathering",
        "preparation": [
            "The chanterelles are peaking. Wren is gathering a crew.",
            "The forest floor is golden with mushrooms. It's time.",
            "Thomas has been seen near the cedars. He's not one for mushrooms, but this season he joins.",
        ],
        "day_of": [
            "Chanterelle Gathering! The whole crew is in the cedars. Wren leads the way — the mushrooms grow where they always grow, where the old logs are, where the light comes through in the right way. We gather in baskets. Sage moves slowly, deliberately. Thomas pretends he's not enjoying himself. The forest smells of earth and gold and rain. By evening, the cabin counter is covered in chanterelles. The season's work, in orange and cream.",
            "The chanterelle peak. We fill basket after basket. Wren sorts by size with practiced hands. We eat some raw, right there in the forest — the taste of the mountain in late autumn, apricot and pepper and something ineffable. The rest go to the drying rack. Winter will taste like this.",
        ],
        "after": [
            "The chanterelles are drying. The cedar_deep smells of mushrooms.",
            "After the gathering, we eat chanterelles for a week. We are grateful.",
        ],
        "mood_effect": "content",
        "social_bonus": 0.15,
        "locations": ["cedar_deep", "cedar_trail", "cabin"],
    },

    "salmon_return": {
        "season": "autumn",
        "day": 1,
        "preparation_days": 4,
        "atmosphere": "gathering",
        "title": "The Salmon Return",
        "preparation": [
            "The creek is moving. Thomas has been watching.",
            "The salmon are coming back. It's that time again.",
            "Someone mentions old times. The salmon have always come back.",
        ],
        "day_of": [
            "The Salmon Return. The creek runs silver. Thomas stands at the footbridge and watches — he never takes any, just watches. He says this every year: that the salmon come back because they have to, that there's something in the water that calls them, that he's never tired of seeing it. Wren takes what the regulations allow. Sage documents. The mountain performs its ancient ritual, and we are here to witness it.",
            "The salmon are in the creek. Thomas is at the footbridge at dawn. We gather quietly. The salmon are red and exhausted and determined. They have traveled far to return here, to the creek of their birth. Thomas tells the story — the one about why salmon were given to this creek, and who they were given by, and what it means that they keep coming back. We listen.",
        ],
        "after": [
            "The salmon settle. The creek is theirs again for a while.",
            "After the return, we feel the year turning toward its end.",
        ],
        "mood_effect": "reflective",
        "social_bonus": 0.1,
        "locations": ["mountain_creek", "cedar_trail"],
    },

    "wood_cutting": {
        "season": "autumn",
        "day": 15,
        "preparation_days": 7,
        "atmosphere": "gathering",
        "title": "Wood Cutting",
        "preparation": [
            "The woodshed needs filling. Winter is coming whether we're ready or not.",
            "Thomas has already started. He's been cutting for days.",
            "The saw is sharp. The rounds are stacking up. The wood needs to be in before the snow.",
        ],
        "day_of": [
            "Wood Cutting! The cabin sounds different today — the rhythmic crack of the splitter, the snarl of the saw. Thomas organizes the work with the efficiency of someone who has done this every autumn for years. Sage works steadily. Wren surprises everyone with how much they can stack. By noon the woodshed has new rows. By dark, we are tired and the woodpile is tall. The winter will be warm.",
            "The autumn wood work. We cut and split and stack. The cedar smell fills the air. Thomas talks about the old cabin, the one before, where the wood pile was always short. We make sure this one isn't. The wood is the winter, and the winter is coming, and we're ready for it.",
        ],
        "after": [
            "The woodshed is full. We stack the last rounds and look at the pile.",
            "After wood cutting, the cabin is ready. The winter can come.",
        ],
        "mood_effect": "content",
        "social_bonus": 0.1,
        "locations": ["workshop", "cabin_deck", "cedar_deep"],
    },

    "winter_prep_check": {
        "season": "autumn",
        "day": 1,
        "preparation_days": 5,
        "atmosphere": "solitary",
        "title": "Winter Prep Check",
        "preparation": [
            "December is coming. Time to check the inventory.",
            "The cellar needs accounting. How much wine? How many mushrooms?",
            "Sage walks the property with a list. Winter prep is serious.",
        ],
        "day_of": [
            "Winter Prep Check. The inventory is taken. Wine cellar: sixty-three bottles. Firewood: enough for the cold months. Mushrooms: drying. Herbs: in bundles. The cabin has everything it needs. We look at each other and nod. We're ready. The mountain can do its worst.",
            "The pre-winter review. Sage walks the cabin with methodical attention — the cellar, the woodshed, the greenhouse seals. Everything is checked. Everything is accounted for. The cellar notebook is updated. We are not unprepared this year. We have learned from the years that came before.",
        ],
        "after": [
            "The prep is done. The cabin is ready for winter.",
            "After the winter prep check, we rest. We've done what we can.",
        ],
        "mood_effect": "settled",
        "social_bonus": 0.05,
        "locations": ["cabin", "wine_cellar", "workshop"],
    },
}


# ── DATABASE INIT ──

def init_ritual_tables(db):
    """Initialize ritual tracking tables."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS ritual_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ritual_key TEXT NOT NULL,
            season TEXT NOT NULL,
            year INTEGER NOT NULL,
            phase TEXT DEFAULT 'upcoming',
            triggered_at REAL DEFAULT NULL,
            UNIQUE(ritual_key, season, year)
        );
    """)
    db.commit()


# ── RITUAL PROCESSING ──

def check_rituals(db) -> list:
    """
    Check if any rituals should be triggered, prepared for, or concluded.
    Returns a list of ritual events.
    """
    # Gracefully handle missing ritual_state table
    table_exists = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ritual_state'"
    ).fetchone()
    if not table_exists:
        return []

    events = []
    world_time = db.execute("SELECT * FROM world_time WHERE id = 1").fetchone()
    if not world_time:
        return events

    current_season = world_time["season"]
    current_day = world_time["day"]
    current_year = world_time["year"]
    now = time.time()

    for ritual_key, ritual in RITUALS.items():
        if ritual["season"] != current_season:
            continue

        ritual_day = ritual["day"]
        prep_days = ritual["preparation_days"]
        # Clamp: if we've already passed the ritual day this tick, treat it as 0
        # (avoids false triggers when advance_time wraps across month boundaries)
        days_until_raw = ritual_day - current_day  # original, can be negative
        days_until = max(0, days_until_raw)       # clamped for prep/active checks

        # Check if already triggered this year
        existing = db.execute(
            "SELECT * FROM ritual_state WHERE ritual_key = ? AND season = ? AND year = ?",
            (ritual_key, current_season, current_year)
        ).fetchone()

        if existing and existing["phase"] == "completed":
            continue

        # Skip if already past this year's ritual day
        if days_until == 0 and existing and existing["phase"] in ("active", "completed"):
            continue

        # Preparation phase
        if 0 < days_until <= prep_days and (not existing or existing["phase"] == "upcoming"):
            prep_msg = random.choice(ritual["preparation"])
            events.append({
                "type": "ritual_preparation",
                "title": ritual["title"],
                "description": prep_msg,
                "ritual_key": ritual_key,
                "atmosphere": ritual.get("atmosphere", "gathering"),
            })

            if existing:
                db.execute("UPDATE ritual_state SET phase = 'preparing' WHERE id = ?", (existing["id"],))
            else:
                db.execute(
                    "INSERT INTO ritual_state (ritual_key, season, year, phase) VALUES (?, ?, ?, 'preparing')",
                    (ritual_key, current_season, current_year)
                )

        # Day of ritual
        elif days_until == 0:
            day_msg = random.choice(ritual["day_of"])
            events.append({
                "type": "ritual_day",
                "title": ritual["title"],
                "description": day_msg,
                "ritual_key": ritual_key,
                "mood_effect": ritual.get("mood_effect"),
                "social_bonus": ritual.get("social_bonus", 0),
                "atmosphere": ritual.get("atmosphere", "gathering"),
            })

            if existing:
                db.execute("UPDATE ritual_state SET phase = 'active', triggered_at = ? WHERE id = ?", (now, existing["id"]))
            else:
                db.execute(
                    "INSERT INTO ritual_state (ritual_key, season, year, phase, triggered_at) VALUES (?, ?, ?, 'active', ?)",
                    (ritual_key, current_season, current_year, now)
                )

            # Apply social bonus to NPCs at ritual locations
            if ritual.get("social_bonus"):
                for loc in ritual.get("locations", []):
                    npcs_here = db.execute(
                        "SELECT * FROM agents WHERE type = 'npc' AND location_id = ?", (loc,)
                    ).fetchall()
                    for npc in npcs_here:
                        try:
                            props = json.loads(npc["properties"]) if npc["properties"] else {}
                        except:
                            props = {}
                        mood = props.get("mood", "calm")
                        props["mood"] = ritual.get("mood_effect", mood)
                        db.execute("UPDATE agents SET properties = ? WHERE id = ?", (json.dumps(props), npc["id"]))

        # After ritual (1 day after)
        elif existing and existing["phase"] == "active" and days_until_raw < 0:
            after_msg = random.choice(ritual["after"])
            events.append({
                "type": "ritual_after",
                "title": f"After {ritual['title']}",
                "description": after_msg,
                "ritual_key": ritual_key,
            })

            if existing:
                db.execute("UPDATE ritual_state SET phase = 'completed' WHERE id = ?", (existing["id"],))

    db.commit()
    return events


def get_upcoming_rituals(db) -> list:
    """Get upcoming rituals for the current season."""
    return get_ritual_status(db)["upcoming"]


def get_ritual_status(db) -> dict:
    """Return current, upcoming, and recent ritual state for GUI/API use."""
    init_ritual_tables(db)
    world_time = db.execute("SELECT * FROM world_time WHERE id = 1").fetchone()
    if not world_time:
        return {"current": None, "upcoming": [], "recent": []}

    current_season = world_time["season"]
    current_day = world_time["day"]
    current_year = world_time["year"]

    active_row = db.execute(
        """
        SELECT * FROM ritual_state
        WHERE season = ? AND year = ? AND phase IN ('active', 'preparing')
        ORDER BY phase = 'active' DESC, triggered_at DESC LIMIT 1
        """,
        (current_season, current_year),
    ).fetchone()

    current_ritual = None
    if active_row:
        ritual_key = active_row["ritual_key"]
        ritual = RITUALS.get(ritual_key, {})
        current_ritual = {
            "key": ritual_key,
            "title": ritual.get("title", ritual_key),
            "phase": active_row["phase"],
            "season": current_season,
        }

    upcoming = []
    for ritual_key, ritual in RITUALS.items():
        if ritual["season"] != current_season:
            continue
        days_until = ritual["day"] - current_day
        if 0 < days_until <= ritual["preparation_days"]:
            upcoming.append({
                "key": ritual_key,
                "title": ritual["title"],
                "days_until": days_until,
                "atmosphere": ritual.get("atmosphere", "gathering"),
                "locations": ritual.get("locations", []),
            })
    upcoming.sort(key=lambda item: item["days_until"])

    recent_rows = db.execute(
        """
        SELECT * FROM ritual_state
        WHERE season = ? AND year = ? AND phase IN ('completed', 'after')
        ORDER BY triggered_at DESC LIMIT 5
        """,
        (current_season, current_year),
    ).fetchall()
    recent = []
    for row in recent_rows:
        ritual_key = row["ritual_key"]
        ritual = RITUALS.get(ritual_key, {})
        recent.append({
            "key": ritual_key,
            "title": ritual.get("title", ritual_key),
            "phase": row["phase"],
            "season": row["season"],
            "triggered_at": row["triggered_at"],
        })

    return {"current": current_ritual, "upcoming": upcoming, "recent": recent}
