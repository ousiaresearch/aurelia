"""
simulation.py — Time, weather, NPC schedules, ecology, seasons, and world update.

The simulation advances time in meaningful chunks. Each "tick" represents
a step forward in the world — time passes, weather shifts, NPCs act, ecology
changes, seasons turn.

Phase 2 additions:
- NPC schedule updates with ~200 NPCs
- Ecology updates (plants, animals, fish)
- Seasonal effects on weather and NPCs
- OWL psychology updates
- Seasonal events
"""

import time
import json
import random
from typing import Optional

from .world_state import (
    get_db, get_world, log_event, update_body, update_internal,
    get_npc_schedule, move_agent as ws_move_agent,
    move_agent_with_travel, resolve_npc_travel_state, get_exit_travel_cost,
    DB_PATH
)
from .seasons import (
    get_season_data, get_season_weather, get_season_temperature,
    describe_season_change, generate_seasonal_event
)
from .ecology import update_ecology
from .psychology import update_psychology
from .social import evolve_relationships, generate_alliances, detect_conflicts
from .npc_ai import run_npc_ai_tick
from .npc_memory import decay_all_memories
from .events import generate_events
from .narrative import update_narratives
from .rituals import check_rituals
from .npc_depth import OWLInteractionMemory
from .goals import goals_tick


# ── TIME SYSTEM ──

SEASONS = {
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
    12: "winter", 1: "winter", 2: "winter",
}

TIME_OF_DAY = [
    (0, "deep_night"), (1, "deep_night"), (2, "deep_night"), (3, "deep_night"),
    (4, "pre_dawn"), (5, "dawn"), (6, "early_morning"), (7, "morning"),
    (8, "mid_morning"), (9, "late_morning"), (10, "midday"), (11, "afternoon"),
    (12, "afternoon"), (13, "afternoon"), (14, "late_afternoon"), (15, "evening"),
    (16, "evening"), (17, "dusk"), (18, "dusk"), (19, "night"), (20, "night"),
    (21, "late_night"), (22, "late_night"), (23, "deep_night"),
]


def get_time_of_day(hour: int) -> str:
    for h, label in TIME_OF_DAY:
        if hour == h:
            return label
    return "deep_night"


def get_season(month: int) -> str:
    return SEASONS.get(month, "spring")


def advance_time(db, hours: float = 1.0) -> dict:
    """Advance world time by the given number of hours."""
    row = db.execute("SELECT * FROM world_time WHERE id = 1").fetchone()
    if not row:
        return {}

    total_minutes = row["hour"] * 60 + row["minute"] + int(hours * 60)
    new_hour = (total_minutes // 60) % 24
    new_minute = total_minutes % 60
    new_day = row["day"] + (total_minutes // 1440)

    new_month = row["month"]
    new_year = row["year"]
    while new_day > 30:
        new_day -= 30
        new_month += 1
        if new_month > 12:
            new_month = 1
            new_year += 1

    new_season = get_season(new_month)
    new_tod = get_time_of_day(new_hour)
    now = time.time()

    old_season = row["season"]
    season_changed = old_season != new_season

    db.execute("""
        UPDATE world_time SET hour = ?, minute = ?, day = ?, month = ?, year = ?,
        season = ?, time_of_day = ?, updated_at = ? WHERE id = 1
    """, (new_hour, new_minute, new_day, new_month, new_year, new_season, new_tod, now))

    db.commit()

    return {
        "hour": new_hour, "minute": new_minute, "day": new_day,
        "month": new_month, "year": new_year, "season": new_season,
        "time_of_day": new_tod, "hours_passed": hours,
        "season_changed": season_changed, "old_season": old_season,
    }


# ── WEATHER SYSTEM (Phase 2: season-driven) ──

WEATHER_STATES = {
    "clear": {"temp_mod": 0, "humidity_mod": -0.05, "next": {"clear": 0.6, "cloudy": 0.25, "foggy": 0.1, "rain": 0.05}},
    "cloudy": {"temp_mod": -1, "humidity_mod": 0.05, "next": {"clear": 0.3, "cloudy": 0.4, "foggy": 0.1, "rain": 0.2}},
    "foggy": {"temp_mod": -2, "humidity_mod": 0.1, "next": {"clear": 0.15, "cloudy": 0.25, "foggy": 0.3, "rain": 0.3}},
    "rain": {"temp_mod": -3, "humidity_mod": 0.15, "next": {"clear": 0.1, "cloudy": 0.2, "foggy": 0.2, "rain": 0.5}},
    "storm": {"temp_mod": -5, "humidity_mod": 0.2, "next": {"clear": 0.05, "cloudy": 0.15, "rain": 0.5, "storm": 0.3}},
}

WEATHER_DESCRIPTIONS = {
    "clear": {
        "dawn": "The dawn breaks clear. The sky lightens from gold to blue.",
        "morning": "A clear morning. The sun warms the stone and the sea glitters.",
        "afternoon": "The afternoon is bright and clear. Shadows are sharp.",
        "evening": "A clear evening. The sun sets in a sky of amber and rose.",
        "night": "A clear night. Stars fill the sky.",
        "default": "The sky is clear.",
    },
    "cloudy": {
        "dawn": "Clouds catch the dawn light — pink and gray.",
        "morning": "Clouds drift across the sky. The sun appears and disappears.",
        "afternoon": "A blanket of cloud softens the light.",
        "evening": "The clouds glow amber at their edges.",
        "night": "Clouds hide the stars.",
        "default": "Clouds cover the sky.",
    },
    "foggy": {
        "dawn": "Fog blurs the dawn. The world is soft edges.",
        "morning": "The fog is thick. Sounds are close. The world feels small.",
        "afternoon": "Fog still hangs over the village.",
        "evening": "Fog thickens as the light fades.",
        "night": "Fog and darkness.",
        "default": "Fog softens everything.",
    },
    "rain": {
        "dawn": "Rain falls softly in the gray dawn.",
        "morning": "Rain patters on stone and leaf and roof.",
        "afternoon": "Steady rain. The world smells of wet earth.",
        "evening": "Rain continues into the evening.",
        "night": "Rain in the darkness.",
        "default": "Rain falls.",
    },
    "storm": {
        "dawn": "Wind and rain. The dawn is gray and loud.",
        "morning": "The storm is full. Rain lashes, wind howls.",
        "afternoon": "Thunder rolls. The sea is wild.",
        "evening": "The storm begins to ease.",
        "night": "Storm in the darkness. Lightning flashes.",
        "default": "The storm rages.",
    },
}

TOD_TEMP_MOD = {
    "dawn": -3, "early_morning": -2, "morning": 0, "mid_morning": 1,
    "late_morning": 2, "midday": 3, "afternoon": 3, "late_afternoon": 2,
    "evening": 0, "dusk": -1, "night": -3, "late_night": -4, "deep_night": -5, "pre_dawn": -4,
}


def update_weather(db, time_info: dict) -> dict:
    """Update weather based on current state, season, and time of day."""
    row = db.execute("SELECT * FROM weather WHERE id = 1").fetchone()
    if not row:
        return {}

    current = row["condition"]
    season = time_info.get("season", "spring")
    tod = time_info.get("time_of_day", "morning")

    # Season-driven temperature
    new_temp = get_season_temperature(season, time_info.get("hour", 12))

    # Humidity drift
    humidity = min(1.0, max(0.1, row["humidity"] + WEATHER_STATES.get(current, {}).get("humidity_mod", 0) * 0.1))

    # Weather state transition (season-weighted)
    new_condition = current
    if random.random() < 0.15:
        # Use season weights to influence transitions
        season_weights = get_season_data(season)["weather_weights"]
        transitions = WEATHER_STATES.get(current, {}).get("next", {})
        if transitions:
            # Blend transition probabilities with season weights
            blended = {}
            for state in set(list(transitions.keys()) + list(season_weights.keys())):
                t_weight = transitions.get(state, 0.1)
                s_weight = season_weights.get(state, 0.1)
                blended[state] = t_weight * 0.6 + s_weight * 0.4

            roll = random.random()
            cumulative = 0
            total = sum(blended.values())
            for state, weight in blended.items():
                cumulative += weight / total
                if roll <= cumulative:
                    new_condition = state
                    break

    # Wind
    wind = max(0, row["wind_speed"] + random.uniform(-2, 2))
    if new_condition == "storm":
        wind = max(wind, 15)

    # Visibility
    visibility = "clear"
    if new_condition == "foggy":
        visibility = "low"
    elif new_condition == "rain":
        visibility = "moderate"
    elif new_condition == "storm":
        visibility = "poor"

    # Description
    desc_options = WEATHER_DESCRIPTIONS.get(new_condition, {})
    description = desc_options.get(tod, desc_options.get("default", ""))

    now = time.time()
    db.execute("""
        UPDATE weather SET condition = ?, temperature = ?, wind_speed = ?,
        humidity = ?, visibility = ?, description = ?, updated_at = ?
        WHERE id = 1
    """, (new_condition, round(new_temp, 1), round(wind, 1), round(humidity, 2),
          visibility, description, now))

    db.commit()

    return {
        "condition": new_condition, "temperature": round(new_temp, 1),
        "wind_speed": round(wind, 1), "humidity": round(humidity, 2),
        "visibility": visibility, "description": description,
        "changed": new_condition != current
    }


# ── BODY UPDATE ──

def update_body_state(db, time_info: dict, hours_passed: float) -> dict:
    """Update OWL's body state based on time passed and current conditions."""
    body = db.execute("SELECT * FROM body_state WHERE id = 1").fetchone()
    weather = db.execute("SELECT * FROM weather WHERE id = 1").fetchone()

    if not body:
        return {}

    energy = body["energy"]
    comfort = body["comfort"]
    hunger = body["hunger"]
    thirst = body["thirst"]
    warmth = body["warmth"]

    hunger = min(1.0, hunger + 0.03 * hours_passed)
    thirst = min(1.0, thirst + 0.04 * hours_passed)

    if body["current_action"] == "sleeping":
        energy = min(1.0, energy + 0.1 * hours_passed)
        comfort = min(1.0, comfort + 0.05 * hours_passed)
    else:
        energy = max(0.0, energy - 0.02 * hours_passed)

    if weather:
        temp = weather["temperature"]
        if temp < 5:
            warmth = max(0.0, warmth - 0.05 * hours_passed)
        elif temp > 15:
            warmth = min(1.0, warmth + 0.02 * hours_passed)

    mood = body["mood"]
    if energy < 0.3:
        mood = "tired"
    elif hunger > 0.7:
        mood = "hungry"
    elif thirst > 0.7:
        mood = "thirsty"
    elif warmth < 0.3:
        mood = "cold"
    elif comfort > 0.8 and energy > 0.6:
        mood = "content"

    update_body(db, energy=round(energy, 2), comfort=round(comfort, 2),
                hunger=round(hunger, 2), thirst=round(thirst, 2),
                warmth=round(warmth, 2), mood=mood)

    return {
        "energy": round(energy, 2), "comfort": round(comfort, 2),
        "hunger": round(hunger, 2), "thirst": round(thirst, 2),
        "warmth": round(warmth, 2), "mood": mood
    }


# ── NPC SCHEDULE SYSTEM ──

def update_npc_positions(db, hour: float) -> list:
    """
    Move NPCs to their scheduled locations based on departure times.
    Each NPC has a npc_departures record telling them when to leave home
    and how long the journey takes. They leave early enough to arrive by
    their scheduled hour.

    hour: current simulation hour (can be fractional, e.g. 5.5 = 5:30am)
    """
    arrived = []
    departed = []
    already_traveling = []

    # Round-robin: use tick_number modulo to sweep through all NPCs over N ticks
    tick_num = db.execute("SELECT COALESCE(MAX(tick_number), 0) + 1 FROM tick_log").fetchone()[0]
    offset = (tick_num * 500) % max(1, db.execute("SELECT COUNT(*) FROM agents WHERE type='npc'").fetchone()[0])
    npcs = db.execute(f"SELECT id, name, location_id FROM agents WHERE type='npc' ORDER BY id LIMIT 500 OFFSET ?", (offset,)).fetchall()
    for npc in npcs:
        npc_id = npc["id"]

        # Skip if already en route
        travel_state = db.execute(
            "SELECT travel_state FROM agents WHERE id = ?", (npc_id,)
        ).fetchone()[0]
        if travel_state:
            already_traveling.append(npc["name"])
            continue

        # Look up departure plan for this NPC
        dep_row = db.execute(
            "SELECT * FROM npc_departures WHERE npc_id = ?", (npc_id,)
        ).fetchone()
        if not dep_row:
            # No departure plan — use fallback: move instantly if scheduled
            schedule = _get_npc_schedule_flexible(db, npc_id, int(hour))
            if schedule and schedule["location_id"] and schedule["location_id"] != npc["location_id"]:
                ws_move_agent(db, npc_id, schedule["location_id"])
                arrived.append((npc["name"], schedule["location_id"]))
            continue

        dep_hour      = dep_row["departure_hour"]
        dep_location  = dep_row["departure_location"]
        arr_location  = dep_row["arrival_location"]
        travel_cost   = dep_row["travel_cost_hours"]
        arrival_time  = dep_hour + travel_cost  # simulation hour when arriving

        # Should this NPC depart now? Depart if:
        #   - current hour >= departure hour
        #   - they are currently AT their departure location
        #   - they haven't already arrived at their work location
        if (hour >= dep_hour and
                npc["location_id"] == dep_location and
                arr_location != npc["location_id"]):
            # Compute real-world departure time based on tick start
            # We bake it in as arrival_time in the travel_state so
            # resolve_npc_travel_state can compare against real time
            move_agent_with_travel(db, npc_id, arr_location, travel_cost)
            departed.append((npc["name"], dep_location, arr_location, travel_cost))

    # Resolve any NPCs who have arrived since the last tick
    just_arrived = resolve_npc_travel_state(db)
    for a in just_arrived:
        npc_name = db.execute(
            "SELECT name FROM agents WHERE id = ?", (a["npc_id"],)
        ).fetchone()
        if npc_name:
            arrived.append((npc_name[0], a["at"]))

    return departed + arrived


def _get_npc_schedule_flexible(db, npc_id: str, hour: int):
    """Get NPC schedule for given hour, with ±2h fallback."""
    for offset in [0, -2, 2, -4, 4]:
        h = (hour + offset) % 24
        row = db.execute(
            "SELECT * FROM npc_schedules WHERE npc_id = ? AND hour = ?",
            (npc_id, h)
        ).fetchone()
        if row:
            return dict(row)
    return None


# ── MAIN SIMULATION TICK ──

def tick(db, hours: float = 1.0) -> dict:
    """Advance the world by one tick. Returns a summary of what changed."""
    time_info = advance_time(db, hours)
    weather_info = update_weather(db, time_info)
    body_info = update_body_state(db, time_info, hours)

    # Move NPCs according to their schedules
    new_hour = time_info.get("hour", 0)
    npc_moves = update_npc_positions(db, new_hour)

    # Resolve NPCs who have arrived en route
    arriving = resolve_npc_travel_state(db)

    # Ecology update (every 6 hours to save processing)
    ecology_events = []
    if new_hour % 6 == 0:
        season = time_info.get("season", "spring")
        ecology_events = update_ecology(db, season, days_passed=hours/24)

    # Season change
    season_event = None
    if time_info.get("season_changed"):
        season_event = describe_season_change(
            time_info.get("old_season", ""),
            time_info.get("season", "spring")
        )
        # Generate seasonal event
        seasonal = generate_seasonal_event(db, time_info.get("season", "spring"))
        if seasonal:
            season_event = seasonal

    # OWL psychology update
    psych_events = []
    if weather_info.get("changed"):
        psych_events.append({"type": "weather_change", "description": weather_info.get("description", "")})
    for move in npc_moves[:3]:
        psych_events.append({"type": "npc_move", "description": f"{move[0]} moved to {move[1]}"})
    for eco_event in ecology_events:
        psych_events.append({"type": eco_event["type"], "description": eco_event["description"]})

    psych_changes = update_psychology(db, hours, psych_events)

    # ── PHASE 4: EMERGENCE ──
    # Cascade: social dynamics → NPC AI → emergent events → narrative arcs
    # Each system feeds into the next, creating genuine emergence.

    all_tick_events = []  # Collect everything for narrative processing

    # 1. SOCIAL DYNAMICS — evolve relationships (every 12 hours)
    social_changes = []
    try:
        if new_hour % 12 == 0:
            social_changes = evolve_relationships(db, hours)
            alliances = generate_alliances(db)
            conflicts = detect_conflicts(db)
            social_changes.extend(alliances)
            social_changes.extend(conflicts)
            all_tick_events.extend(social_changes)
    except Exception:
        pass

    # 2. NPC AI — NPCs think and act, influenced by recent social changes
    npc_ai_actions = []
    try:
        npc_ai_actions = run_npc_ai_tick(db, new_hour)
        all_tick_events.extend(npc_ai_actions)
    except Exception:
        pass

    # 2b. POPULATION DYNAMICS — migration, reproduction, mortality, Glim anomalies
    pop_events = []
    try:
        # Resolve world_id from registry
        world_reg = db.execute("SELECT world_id FROM world_registry WHERE id = 1").fetchone()
        world_id = world_reg["world_id"] if world_reg else "solara"
        tick_number = db.execute("SELECT COALESCE(MAX(tick_number), 0) + 1 FROM tick_log").fetchone()[0]
        
        from .population import check_migration, check_reproduction, check_mortality
        from .decision_feeder import check_glim_tipping
        npcs = db.execute("""
            SELECT a.id, a.type FROM agents a
            LEFT JOIN npc_decision_state ds ON ds.npc_id = a.id
            WHERE a.type = 'npc'
            ORDER BY
                CASE
                    WHEN a.type = 'glim' AND CAST(COALESCE(json_extract(ds.variables, '$.anomaly_pressure'), '0') AS REAL) > 0.4 THEN 0
                    WHEN CAST(COALESCE(json_extract(ds.variables, '$.security'), '1') AS REAL) < 0.3 THEN 1
                    WHEN CAST(COALESCE(json_extract(ds.variables, '$.satisfaction'), '0') AS REAL) > 0.7 THEN 2
                    ELSE 3
                END,
                RANDOM()
            LIMIT 300
        """).fetchall()
        for npc_id, npc_type in npcs:
            # Glim tipping check
            if npc_type == "glim":
                tip = check_glim_tipping(db, npc_id, world_id, {"tick": tick_number})
                if tip:
                    from .federation_events import build_glim_anomaly_event
                    pop_events.append(build_glim_anomaly_event(world_id, tick_number, tip, time_info))
            # Migration
            mig = check_migration(db, npc_id, npc_type, world_id, {"tick": tick_number})
            if mig:
                pop_events.append(mig)
            # Reproduction
            rep = check_reproduction(db, npc_id, npc_type, world_id, {"tick": tick_number})
            if rep:
                pop_events.append(rep)
            # Mortality
            death = check_mortality(db, npc_id, npc_type, world_id, {"tick": tick_number})
            if death:
                pop_events.append(death)
                db.execute("DELETE FROM agents WHERE id = ?", (npc_id,))
                db.execute("DELETE FROM npc_decision_state WHERE npc_id = ?", (npc_id,))
        if pop_events:
            db.commit()
            all_tick_events.extend(pop_events)
    except Exception:
        pass

    # 3. STORY CREATION — scan events for story-worthy patterns
    try:
        from .narrative_arcs import check_story_creation_from_events
        story_created = check_story_creation_from_events(db)
        if story_created:
            all_tick_events.append({
                "type": "story_born",
                "description": story_created,
            })
    except Exception:
        pass

    # 4. NPC-TO-NPC CONVERSATIONS — NPCs talk to each other
    npc_conversations = []
    try:
        from .npc_dialogue import run_npc_conversations
        # Get all locations with NPCs
        locations_with_npcs = db.execute("""
            SELECT DISTINCT location_id FROM agents WHERE type = 'npc' AND state = 'active'
        """).fetchall()
        for loc_row in locations_with_npcs:
            loc_id = loc_row[0]
            npc_ids = [r[0] for r in db.execute(
                "SELECT id FROM agents WHERE type = 'npc' AND state = 'active' AND location_id = ?",
                (loc_id,)
            ).fetchall()]
            if len(npc_ids) >= 2:
                convos = run_npc_conversations(db, loc_id, npc_ids, time_info)
                npc_conversations.extend(convos)
        all_tick_events.extend(npc_conversations)
    except Exception:
        pass

    # 2c. MEMORY DECAY — all NPC memories fade slightly with time
    try:
        decay_all_memories(db, hours)
    except Exception:
        pass

    # 3. EMERGENT EVENTS — generated from current world state (every 24 hours)
    #    These now also respond to social changes and NPC AI actions
    emergent_events = []
    if new_hour == 0:
        emergent_events = generate_events(db)
        all_tick_events.extend(emergent_events)

    # 4. EVENT CASCADE — social changes can trigger new events
    #    e.g., a new rivalry might generate an argument event
    cascade_events = []
    for change in social_changes:
        if change.get("type") == "new_conflict" and random.random() < 0.3:
            cascade_events.append({
                "type": "social_argument",
                "category": "social",
                "title": "Heated Argument",
                "description": change["description"] + " Voices were raised. The whole village heard.",
                "consequences": {"mood_effect": "tense"},
            })
        elif change.get("type") == "breakup" and random.random() < 0.5:
            cascade_events.append({
                "type": "social_sadness",
                "category": "social",
                "title": "Heartbreak",
                "description": change["description"] + " The village feels the weight of it.",
                "consequences": {"mood_effect": "melancholy"},
            })
    all_tick_events.extend(cascade_events)

    # 5. NARRATIVE — weave events into story arcs
    narrative_moments = []
    try:
        if new_hour % 6 == 0:
            narrative_moments = update_narratives(db)
    except Exception:
        pass

    # Create story arcs from all collected events
    for event in all_tick_events:
        desc = event.get("description", "")
        if not desc:
            continue
        # Determine story type from event
        story_type = None
        if event.get("type") in ("new_conflict", "social_argument", "rivalry"):
            story_type = "conflict"
        elif event.get("type") in ("breakup",):
            story_type = "hardship"
        elif "romance" in event.get("type", "") or "love" in desc.lower():
            story_type = "romance"
        elif event.get("type") in ("new_alliance", "celebration"):
            story_type = "celebration"
        elif event.get("type") in ("relationship_shift",):
            story_type = "change"

        if story_type:
            npc_names = []
            all_npcs = db.execute("SELECT id, name FROM agents WHERE type = 'npc'").fetchall()
            for npc in all_npcs:
                if npc["name"] in desc:
                    npc_names.append(npc["name"])
            if len(npc_names) >= 2:
                from .narrative import create_story_arc
                create_story_arc(db, story_type, npc_names[:4], desc)

    # Collect all events for the tick result
    all_emergent = emergent_events + cascade_events

    # ── PHASE 4.5: GOALS MAINTENANCE ──
    goal_summary = goals_tick(db)

    # ── PHASE 5: RITUALS ──
    ritual_events = check_rituals(db)

    # ── PHASE 6: ECONOMY ──
    from .economy import economy_tick
    economy_summary = economy_tick(db)

    # ── PHASE 6b: ECONOMIC DRIFT — currency stability affects NPCs
    try:
        from .economic_drift import drift_currency, stability_affects_npcs
        wreg = db.execute("SELECT world_id FROM world_registry WHERE id = 1").fetchone()
        wid = wreg["world_id"] if wreg else "solara"
        trade_balance = economy_summary.get("trade_balance", 0.0)
        import sqlite3 as _sql3
        _cdb = _sql3.connect("/Users/johann/aurelia/coordinator.db", timeout=2)
        _trow = _cdb.execute("SELECT AVG(tension) FROM diplomatic_relations").fetchone()
        dipl_tension = _trow[0] if _trow and _trow[0] else 0.3
        _cdb.close()
        drift_currency(wid, trade_balance, dipl_tension)
        stability_affects_npcs(db, wid)
    except Exception:
        pass

    # ── PHASE 6c: CROSS-BORDER EVENT GENERATORS
    growth = {}
    try:
        from .event_generators import check_memory_trader, check_ecology_dispute
        # Memory Trader: query coordinator for anomaly count
        req_url = "http://127.0.0.1:9001/api/growth"
        anomaly_count = 0
        try:
            import urllib.request, json
            resp = urllib.request.urlopen(req_url, timeout=5)
            growth = json.loads(resp.read())
            anomaly_count = growth.get("glim_anomaly_signals", 0)
        except Exception:
            pass
        rev = check_memory_trader(db, wid, anomaly_count)
        if rev:
            from .federation_events import _event as _fevent
            pop_events.append(_fevent(
                event_id=f"{wid}:tick-{tick_number}:memory-revelation:{int(time.time())}",
                world_id=wid, event_type="memory_revelation", category="memory_revelation",
                title=rev.get("description", "")[:72], description=rev.get("description", ""),
                importance=0.9, actor_ids=[], tags=["memory", "revelation", wid],
                payload=rev, world_time=time_info,
            ))
        # Ecology disputes (Valdris only)
        trade_vol = economy_summary.get("trade_volume", 0.5) if isinstance(economy_summary, dict) else 0.5
        eco = check_ecology_dispute(wid, trade_vol, 0.5)
        if eco:
            from .federation_events import _event as _fevent2
            pop_events.append(_fevent2(
                event_id=f"{wid}:tick-{tick_number}:ecology-dispute:{int(time.time())}",
                world_id=wid, event_type="ecology_dispute", category="ecology",
                title=eco.get("description", "")[:72], description=eco.get("description", ""),
                importance=0.75, actor_ids=[], tags=["ecology", "dispute", wid],
                payload=eco, world_time=time_info,
            ))
    except Exception:
        pass

    # ── PHASE 6d: NARRATIVE SEED DECK — probability-modulated extraordinary events
    try:
        from .narrative_seeds import draw_seed
        # Reuse growth data already fetched in 6c, or re-fetch
        seed_event = draw_seed(wid, growth)
        if seed_event:
            # Inject into tick events as a raw dict (will be picked up by federation event builder)
            from .federation_events import _event as _fevent3
            pop_events.append(_fevent3(
                event_id=f"{wid}:tick-{tick_number}:narrative-seed:{seed_event['event_type']}:{int(time.time())}",
                world_id=wid,
                event_type=seed_event["event_type"],
                category=seed_event["category"],
                title=seed_event["description"][:72],
                description=seed_event["description"],
                importance=seed_event.get("importance", 0.7),
                actor_ids=seed_event.get("actor_ids", []),
                tags=seed_event.get("tags", []),
                payload=seed_event.get("payload", {}),
                world_time=time_info,
            ))
    except Exception:
        pass

    # ── PHASE 6e: FACTION ENGINE — grievance-driven NPC organization
    faction_events = []
    try:
        from .faction_engine import check_faction_formation, update_all_factions
        faction_event = check_faction_formation(db, wid, tick_number, growth)
        if faction_event:
            from .federation_events import _event as _fevent_f
            pop_events.append(_fevent_f(
                event_id=f"{wid}:tick-{tick_number}:faction-formed:{int(time.time())}",
                world_id=wid,
                event_type=faction_event["event_type"],
                category=faction_event["category"],
                title=faction_event["title"][:72],
                description=faction_event["description"],
                importance=faction_event.get("importance", 0.75),
                actor_ids=faction_event.get("actor_ids", []),
                tags=faction_event.get("tags", []),
                payload=faction_event.get("payload", {}),
                world_time=time_info,
            ))
        update_all_factions(db, wid, tick_number)
    except Exception:
        pass

    # ── PHASE 6f: ESCALATION LADDER — faction conflict state machine
    try:
        from .escalation_ladder import check_all_escalations, get_conflict_state
        esc_events = check_all_escalations(db, wid, tick_number, growth)
        for ee in esc_events:
            from .federation_events import _event as _fevent_e
            pop_events.append(_fevent_e(
                event_id=f"{wid}:tick-{tick_number}:escalation:{ee['event_type']}:{int(time.time())}",
                world_id=wid,
                event_type=ee["event_type"],
                category=ee["category"],
                title=ee["title"][:72],
                description=ee["description"],
                importance=ee.get("importance", 0.8),
                actor_ids=ee.get("actor_ids", []),
                tags=ee.get("tags", []),
                payload=ee.get("payload", {}),
                world_time=time_info,
            ))
    except Exception:
        pass

    # ── PHASE 6g: SOVEREIGNTY PIPELINE — faction-to-country emergence
    try:
        from .sovereignty import process_sovereignty_tick, is_secession_cascade_active, get_cascade_ticks_remaining
        sov_events = process_sovereignty_tick(db, wid, tick_number)
        for se in sov_events:
            from .federation_events import _event as _fevent_s
            pop_events.append(_fevent_s(
                event_id=f"{wid}:tick-{tick_number}:sovereignty:{se['event_type']}:{int(time.time())}",
                world_id=wid,
                event_type=se["event_type"],
                category=se["category"],
                title=se["title"][:72],
                description=se["description"],
                importance=se.get("importance", 0.9),
                actor_ids=se.get("actor_ids", []),
                tags=se.get("tags", []),
                payload=se.get("payload", {}),
                world_time=time_info,
            ))
    except Exception:
        pass

    # ── PHASE 7: CREATIVE OUTPUT ──
    from .creative_output import creative_output_tick
    owl_loc = db.execute("SELECT location_id FROM agents WHERE type = 'player'").fetchone()
    creative_summary = creative_output_tick(db, owl_loc["location_id"] if owl_loc else None)

    # ── PHASE 8: SOCIAL PULSE ──
    # Surface the top social change to the player via event log
    if social_changes:
        # Pick the most notable change: breakups > new alliances > shifts
        notable = next(
            (c for c in social_changes if c.get("type") in ("breakup", "new_alliance", "new_conflict")),
            social_changes[0] if social_changes else None
        )
        if notable:
            log_event(db, "social_pulse", notable.get("description", ""), location_id="")

    # Log the tick
    log_event(db, "tick", f"Time advances {hours}h. {time_info.get('time_of_day', '')}.",
              location_id="")

    # ── TICK LOG — persistent audit trail ──────────────────────────────
    try:
        now_ts = time.time()
        tick_start = getattr(tick, '_tick_start_ts', now_ts)
        duration_ms = int((now_ts - tick_start) * 1000) if tick_start else 0
        db.execute("""
            INSERT INTO tick_log (
                tick_number, real_timestamp,
                world_year, world_month, world_day, world_hour, world_minute,
                season, time_of_day,
                npc_moves, npc_ai_actions, npc_conversations,
                social_changes, emergent_events, ecology_events,
                narrative_moments, ritual_events,
                economy_produced, economy_consumed, economy_traded,
                creative_outputs,
                duration_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            (db.execute("SELECT COALESCE(MAX(tick_number), 0) + 1 FROM tick_log").fetchone()[0]),
            now_ts,
            time_info.get("year", 0), time_info.get("month", 0),
            time_info.get("day", 0), time_info.get("hour", 0), time_info.get("minute", 0),
            time_info.get("season", ""), time_info.get("time_of_day", ""),
            len(npc_moves), len(npc_ai_actions), len(npc_conversations),
            len(social_changes), len(all_emergent), len(ecology_events),
            len(narrative_moments), len(ritual_events),
            len(economy_summary.get("produced", [])),
            len(economy_summary.get("consumed", [])),
            len(economy_summary.get("traded", [])),
            len(creative_summary) if isinstance(creative_summary, list) else 0,
            duration_ms, now_ts,
        ))
        db.commit()
    except Exception:
        pass  # Don't crash the tick for logging

    # ── PHASE 9: PROSE NARRATIVE — weave everything into literary prose ──
    tick_prose = None
    try:
        from .prose_narrative import generate_tick_prose
        tick_result = {
            "time": time_info,
            "weather": weather_info,
            "npc_moves": npc_moves,
            "npc_ai_actions": npc_ai_actions,
            "npc_conversations": npc_conversations,
            "social_changes": social_changes,
            "emergent_events": all_emergent,
            "ecology_events": ecology_events,
            "narrative_moments": narrative_moments,
            "ritual_events": ritual_events,
            "season_event": season_event,
        }
        tick_prose = generate_tick_prose(tick_result, db.execute(
            "SELECT COUNT(*) as cnt FROM events WHERE event_type='tick'"
        ).fetchone()["cnt"] + 1)
        if tick_prose:
            # Store in narrative_moments table for player discovery
            now_ts = time.time()
            # Get isildur's current location for the narrative moment
            isildur_loc = db.execute(
                "SELECT location_id FROM agents WHERE type='player' ORDER BY id LIMIT 1"
            ).fetchone()
            loc = isildur_loc["location_id"] if isildur_loc else ""
            db.execute("""
                INSERT INTO narrative_moments (timestamp, story_arc_id, content, location_id, discovered)
                VALUES (?, NULL, ?, ?, 0)
            """, (now_ts, tick_prose, loc))
            db.commit()
    except Exception:
        pass

    return {
        "prose_narrative": tick_prose,
        "time": time_info,
        "weather": weather_info,
        "body": body_info,
        "npc_moves": npc_moves,
        "ecology_events": ecology_events,
        "season_event": season_event,
        "psychology": psych_changes,
        # Phase 4
        "social_changes": social_changes,
        "npc_ai_actions": npc_ai_actions,
        "npc_conversations": npc_conversations,
        "emergent_events": all_emergent,
        "narrative_moments": narrative_moments,
        "ritual_events": ritual_events,
        # Phase 4.5: Goals
        "goals": goal_summary,
        # Phase 6: Economy
        "economy": economy_summary,
        # Phase 7: Creative
        "creative": creative_summary,
    }
