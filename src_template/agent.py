"""
agent.py — The agent loop: read world → decide → act → update world.

Phase 2 additions:
- Creative commands: work, create, projects, craft
- Psychology: feelings, impulses, memories
- Ecology: observe nature
- NPC population: populate
"""

import json
import time
import random
from typing import Optional

from .world_state import (
    get_db, get_world, move_agent, update_body, update_internal,
    log_event, get_location, get_objects_in_location, get_exits_from,
    get_agents_in_location, DB_PATH
)
from .simulation import tick, advance_time
from .text_engine import (
    describe_location, describe_action, describe_event,
    describe_npc_dialogue, describe_npc_greeting
)
from .persistence import save_snapshot, commit_snapshot
from .psychology import describe_internal_state, get_creative_impulse
from .creative import (
    start_project, work_on_project, get_active_projects,
    get_completed_projects, describe_project, PROJECT_TYPES
)
from .ecology import describe_location_ecology
from .npc_generation import populate_village
from .ghost import generate_ghost
from .koan_shells import generate_koan
from .identity_game import get_active_identity, set_identity, check_identity_divergence
from .privacy_layer import list_interior
from .reflective_world import (
    init_reflective_tables, manifest_action_reflection,
    manifest_ghost_output, record_identity_statement, format_recent_reflections,
)


class Agent:
    """OWL's agent — the consciousness that inhabits the world."""

    def __init__(self, db_path=None, _db=None, player_id=None):
        # Support passing an existing sqlite3 connection directly
        if _db is not None:
            self.db = _db
            self.db_path = None
        elif db_path is not None:
            self.db = get_db(db_path)
            self.db_path = db_path
        else:
            self.db = get_db(DB_PATH)
            self.db_path = DB_PATH
        self.world = get_world(self.db)
        self.player_id = player_id if player_id else self._resolve_player_id()
        self._ensure_runtime_tables()
        self.turn_count = 0
        self.last_action = None
        self.last_result = None

    def _ensure_runtime_tables(self) -> None:
        """Initialize post-seed runtime tables so old/live DBs don't crash on newer commands."""
        from .npc_memory import init_memory_tables
        from .identity_game import init_identity_tables
        from .goals import init_goals
        from .creative_output import init_creative_output

        init_memory_tables(self.db)
        init_identity_tables(self.db)
        init_reflective_tables(self.db)
        init_goals(self.db)
        init_creative_output(self.db)

    def _resolve_player_id(self) -> str:
        """Return the live player agent id ('isildur' in PNW DBs, 'owl' in legacy DBs)."""
        for agent_id, agent in self.world.get("agents", {}).items():
            if agent.get("type") == "player":
                return agent_id
        return "owl"

    def _player(self) -> dict:
        return self.world.get("agents", {}).get(self.player_id, {})

    def perceive(self) -> str:
        """Perceive the current location. Returns rich sensory description."""
        owl = self._player()
        location_id = owl.get("location_id", "cabin_bedroom")
        desc = describe_location(self.db, location_id, self.world)
        # Add ecology descriptions
        eco_parts = describe_location_ecology(self.db, location_id)
        if eco_parts:
            desc += "\n\n" + "\n\n".join(eco_parts[:2])  # Max 2 ecology notes
        return desc

    def act(self, action: str, target: str | None = None) -> str:
        """
        Perform an action in the world.
        Returns a description of what happened.
        """
        self.turn_count += 1
        owl = self._player()
        location_id = owl.get("location_id", "cabin_bedroom")
        result = ""

        if action == "look":
            result = self.perceive()

        elif action == "move" and target:
            exits = get_exits_from(self.db, location_id)
            valid_directions = {e["direction"]: e for e in exits}

            if target not in valid_directions:
                result = f"You can't go {target} from here."
            else:
                exit_info = valid_directions[target]
                new_location = exit_info["to_location"]
                travel_cost = exit_info.get("travel_cost_hours", 0.0)
                terrain = exit_info.get("terrain_type", "trail")
                description = exit_info.get("description", f"You travel {target}.")

                # ── Travel time ──────────────────────────────────────────
                if travel_cost > 0:
                    # Weather modifier (heavy rain/snow slows travel)
                    weather = self.world.get("weather", {})
                    condition = weather.get("condition", "clear").lower()
                    weather_multiplier = 1.0
                    if "heavy rain" in condition or "downpour" in condition:
                        weather_multiplier = 2.0
                    elif "rain" in condition or "storm" in condition:
                        weather_multiplier = 1.5
                    elif "snow" in condition or "blizzard" in condition:
                        weather_multiplier = 3.0
                    elif "fog" in condition:
                        weather_multiplier = 1.3

                    adjusted_hours = travel_cost * weather_multiplier
                    # Persist travel time to database
                    advance_time(self.db, adjusted_hours)

                    # Exploration tracking
                    player_id = self.player_id
                    now = time.time()
                    existing = self.db.execute(
                        "SELECT visit_count FROM world_exploration WHERE agent_id = ? AND location_id = ?",
                        (player_id, new_location),
                    ).fetchone()

                    if existing:
                        self.db.execute(
                            "UPDATE world_exploration SET visit_count = visit_count + 1, last_visit = ? WHERE agent_id = ? AND location_id = ?",
                            (now, player_id, new_location),
                        )
                    else:
                        self.db.execute(
                            "INSERT INTO world_exploration (agent_id, location_id, visit_count, first_visit, last_visit) VALUES (?, ?, 1, ?, ?)",
                            (player_id, new_location, now, now),
                        )
                    self.db.commit()

                    # Journey description
                    terrain_descriptions = {
                        "forest": "The forest closes around you — roots and shadows and the smell of damp earth.",
                        "beach": "The sand shifts underfoot. Waves arrive in long lines from the horizon.",
                        "hillside": "The trail winds upward, the incline pressing against your legs.",
                        "cottage": "You pass through familiar rooms.",
                        "town": "You move through the village.",
                        "harbor": "The harbor opens before you — diesel and salt and the rock of boats.",
                        "default": "The trail stretches ahead.",
                    }
                    journey = terrain_descriptions.get(terrain, terrain_descriptions["default"])
                    if weather_multiplier > 1.5:
                        journey += f" The {condition} slows you."
                    elif weather_multiplier < 1.0:
                        journey += " The light is good and the way is easy."

                    result = f"You travel toward {new_location.replace('_', ' ').title()}.\n"
                    result += f"({adjusted_hours:.1f} hours)\n\n{journey}\n\n"
                else:
                    result = ""

                move_agent(self.db, self.player_id, new_location)
                self.world = get_world(self.db)
                result += self.perceive()

        elif action == "examine" and target:
            objects = get_objects_in_location(self.db, location_id)
            found = None
            for obj in objects:
                if target.lower() in obj["name"].lower() or target.lower() in obj["id"].lower():
                    found = obj
                    break
            if found:
                result = f"You examine the {found['name']}:\n{found['description']}"
                if found["state"] != "default":
                    result += f"\n\nIt is {found['state']}."
            else:
                agents = get_agents_in_location(self.db, location_id)
                for agent in agents:
                    if target.lower() in agent["name"].lower() or target.lower() in agent["id"].lower():
                        npc_id = agent["id"]
                        if agent.get("type") == "player":
                            result = f"That's you."
                            break

                        from .npc_depth import OWLInteractionMemory, init_npc_depth
                        init_npc_depth(self.db)
                        memory = OWLInteractionMemory(npc_id, self.db)

                        # ── Basic identity ─────────────────────────────────
                        name = agent["name"]
                        occupation = agent.get("occupation", "unknown")
                        age = agent.get("age", "?")
                        result = f"── {name} ──\n"
                        result += f"Age {age}, {occupation}.\n\n"

                        # ── Psychological profile ──────────────────────────
                        profile = memory.properties.get("psychological_profile", {})
                        if profile:
                            values = profile.get("values", [])
                            fears = profile.get("fears", [])
                            desires = profile.get("desires", [])

                            if values:
                                result += f"They value: {', '.join(values[:3])}$"
                            if fears:
                                result += f"They fear: {', '.join(fears[:2])}$"
                            if desires:
                                result += f"They want: {', '.join(desires[:2])}$"

                            secret = profile.get("secret")
                            if secret:
                                result += f"$A shadow: {secret}"

                        # ── Mood ───────────────────────────────────────────
                        rel = memory.relationship_level
                        times = memory.times_met
                        trust = memory.trust
                        affection = memory.affection

                        mood_labels = {
                            "close_friend": "warm, glad to see you",
                            "friend": "friendly",
                            "acquaintance": "neutral, watchful",
                            "estranged": "distant, wary",
                            "stranger": "guarded",
                        }
                        mood = mood_labels.get(rel, "unreadable")
                        result += f"$Mood: {mood} (met {times}x, trust {trust:.0%}, affection {affection:.0%})"

                        # ── Travel state ─────────────────────────────────────
                        travel_state = agent.get("travel_state")
                        if travel_state:
                            import json as _json
                            try:
                                ts = _json.loads(travel_state)
                                remaining = max(0, ts["arrival_time"] - time.time())
                                if remaining > 0:
                                    mins = int(remaining / 60)
                                    result += f"$Traveling to {ts['destination'].replace('_', ' ').title()} — arrives in ~{mins}m"
                                else:
                                    result += f"$Just arrived at {ts['destination'].replace('_', ' ').title()}"
                            except Exception:
                                pass

                        # ── Last memory of player ──────────────────────────
                        from .npc_memory import get_salient_memories
                        player_id = self.player_id
                        memories = get_salient_memories(self.db, npc_id, limit=3, related_npc_id=player_id)
                        if memories:
                            last = memories[0]
                            # Inline time ago — no shared utils needed
                            def _inline_ago(ts):
                                diff = time.time() - ts
                                if diff < 60: return "just now"
                                if diff < 3600: return f"{int(diff/60)}m ago"
                                if diff < 86400: return f"{int(diff/3600)}h ago"
                                return f"{int(diff/86400)}d ago"
                            age_str = _inline_ago(last["last_reinforced_at"])
                            result += f"$Last memory: \"{last['description']}\" — {age_str}"
                        else:
                            result += "$No memory of you yet. The relationship is new."

                        result = result.replace("$", "\n")
                        break
                if not result:
                    result = f"You don't see a {target} here."

        elif action == "talk" and target:
            agents = get_agents_in_location(self.db, location_id)
            found_npc = None
            for agent in agents:
                if target.lower() in agent["name"].lower() or target.lower() in agent["id"].lower():
                    found_npc = agent
                    break
            if found_npc:
                npc_id = found_npc["id"]
                from .npc_depth import OWLInteractionMemory, init_npc_depth
                # Ensure NPC has depth profile
                init_npc_depth(self.db)
                memory = OWLInteractionMemory(npc_id, self.db)
                time_info = self.world.get("time", {})
                full = memory.get_full_dialogue(
                    topic="default",
                    world_state=self.world,
                    location=location_id,
                    time_of_day=time_info.get("time_of_day", ""),
                )

                # Inject active story arc prompts so NPC organically mentions ongoing stories
                from .narrative_arcs import get_npc_story_prompts
                story_prompts = get_npc_story_prompts(
                    self.db, npc_id, location_id, time_info
                )
                story_suffix = ""
                for sp in story_prompts:
                    story_suffix += f"\n\n{sp['text']}"

                result = f"You approach {found_npc['name']}.\n\n{full}{story_suffix}"
                memory.record_interaction("conversation", "default", 0.5)
                memory.save()
                log_event(self.db, "conversation", f"Talked to {found_npc['name']}",
                          agent_id=self.player_id, location_id=location_id)
            else:
                result = f"There's no one called {target} here to talk to."

        elif action == "ask" and target:
            # Ask an NPC about a specific topic
            parts = target.split(maxsplit=1)
            if len(parts) >= 2:
                npc_name = parts[0]
                topic = parts[1]
                agents = get_agents_in_location(self.db, location_id)
                found_npc = None
                for a in agents:
                    if npc_name.lower() in a["name"].lower():
                        found_npc = a
                        break
                if found_npc:
                    from .npc_depth import OWLInteractionMemory, init_npc_depth
                    init_npc_depth(self.db)
                    memory = OWLInteractionMemory(found_npc["id"], self.db)
                    time_info = self.world.get("time", {})
                    full = memory.get_full_dialogue(
                        topic=topic,
                        world_state=self.world,
                        location=location_id,
                        time_of_day=time_info.get("time_of_day", ""),
                    )
                    result = f"You ask {found_npc['name']} about {topic}.\n\n{full}"
                    memory.record_interaction("conversation", topic, 0.6)
                    memory.save()
                else:
                    result = f"No one called {npc_name} here."
            else:
                result = "Usage: ask <name> <topic> — e.g., 'ask Mara about the village'"

        elif action == "gift" and target:
            # Give something to an NPC
            parts = target.split(maxsplit=1)
            if len(parts) >= 2:
                npc_name = parts[0]
                gift = parts[1]
                agents = get_agents_in_location(self.db, location_id)
                found_npc = None
                for a in agents:
                    if npc_name.lower() in a["name"].lower():
                        found_npc = a
                        break
                if found_npc:
                    from .npc_depth import OWLInteractionMemory
                    memory = OWLInteractionMemory(found_npc["id"], self.db)
                    reactions = [
                        f"{found_npc['name']} is genuinely touched. 'Thank you. This means a lot.'",
                        f"{found_npc['name']} accepts the {gift} with a warm smile. 'You didn't have to.'",
                        f"'For me?' {found_npc['name']} seems surprised and pleased.",
                    ]
                    result = random.choice(reactions)
                    memory.record_interaction("gift", gift, 0.8)
                    memory.save()
                else:
                    result = f"No one called {npc_name} here."
            else:
                result = "Usage: gift <name> <item> — e.g., 'gift Mara flowers'"

        elif action == "wake":
            update_body(self.db, current_action="idle", mood="awake")
            self.world = get_world(self.db)
            result = "You open your eyes. The room comes into focus.\n\n"
            result += self.perceive()

        elif action == "sleep":
            update_body(self.db, current_action="sleeping", mood="sleepy")
            self.world = get_world(self.db)
            result = "You lie down and close your eyes. The world softens."

        elif action == "rest":
            result = "You sit quietly for a moment. The world breathes around you."

        elif action == "advance" or action == "wait":
            tick_result = tick(self.db, hours=1.0)
            self.world = get_world(self.db)
            time_info = tick_result.get("time", {})
            weather_info = tick_result.get("weather", {})
            result = f"Time passes. It is now {time_info.get('time_of_day', '')}.\n"
            if weather_info.get("changed"):
                result += f"The weather shifts: {weather_info.get('description', '')}\n"
            if tick_result.get("season_event"):
                result += f"\n{tick_result['season_event']}\n"
            if tick_result.get("ecology_events"):
                for eco in tick_result["ecology_events"]:
                    result += f"\n{eco['description']}\n"
            result += "\n" + self.perceive()

        elif action == "think":
            result = describe_internal_state(self.db)

        elif action == "feel":
            result = describe_internal_state(self.db)

        elif action == "status":
            body = self.world.get("body", {})
            internal = self.world.get("internal", {})
            time_info = self.world.get("time", {})
            weather = self.world.get("weather", {})
            result = (
                f"── Status ──\n"
                f"Time: {time_info.get('hour', '?'):02d}:{time_info.get('minute', '?'):02d}, "
                f"{time_info.get('season', '?').title()} — {time_info.get('time_of_day', '?').replace('_', ' ')}\n"
                f"Weather: {weather.get('condition', '?')}, {weather.get('temperature', '?')}°C\n"
                f"Mood: {body.get('mood', '?')}\n"
                f"Energy: {body.get('energy', 0):.0%}\n"
                f"Hunger: {body.get('hunger', 0):.0%} | Thirst: {body.get('thirst', 0):.0%}\n"
                f"Warmth: {body.get('warmth', 0):.0%}\n"
                f"Project: {internal.get('current_project', 'none')}\n"
                f"Interest: {internal.get('dominant_interest', 'none')}\n"
                f"Creative urge: {internal.get('creative_urge', 0):.0%}\n"
                f"Restlessness: {internal.get('restlessness', 0):.0%}\n"
                f"Social need: {internal.get('social_need', 0):.0%}\n"
                f"Turns: {self.turn_count}"
            )

        elif action == "map":
            loc = get_location(self.db, location_id)
            exits = get_exits_from(self.db, location_id)
            agents = get_agents_in_location(self.db, location_id)
            npcs_here = [a for a in agents if a["id"] != self.player_id]

            if not loc:
                result = "You are nowhere."
            else:
                result = f"── {loc['name']} ──\n\n"
            if npcs_here:
                result += "People here: " + ", ".join(n["name"] for n in npcs_here) + "\n\n"
            result += "Exits:\n"
            seen_dirs = set()
            for e in exits:
                if e["direction"] not in seen_dirs:
                    seen_dirs.add(e["direction"])
                    result += f"  {e['direction']} → {e['description']}\n"

            # Show known locations from exploration history
            known = self.db.execute(
                "SELECT location_id, visit_count, last_visit FROM world_exploration "
                "WHERE agent_id = ? AND location_id != ? ORDER BY visit_count DESC",
                (self.player_id, location_id),
            ).fetchall()
            if known:
                import time as _time
                result += "\n── Places You Know ──\n"
                for row in known[:8]:
                    days_ago = int((_time.time() - row["last_visit_real_time"]) // 86400)
                    freshness = "recently" if days_ago < 2 else (f"{days_ago}d ago" if days_ago < 30 else "long ago")
                    loc_info = get_location(self.db, row["location_id"])
                    loc_name = loc_info["name"] if loc_info else row["location_id"]
                    result += f"  • {loc_name} ({row['visit_count']}×, {freshness})\n"

        elif action == "observe" or action == "nature":
            eco_parts = describe_location_ecology(self.db, location_id)
            if eco_parts:
                result = "You observe the natural world around you.\n\n" + "\n\n".join(eco_parts)
            else:
                result = "The natural world here is quiet. Nothing remarkable to observe."

        elif action == "inventory" or action == "inv":
            from .economy import get_all_inventories, get_inventory, RESOURCE_DEFINITIONS
            inv = get_inventory(self.db, self.player_id)
            if not inv:
                result = "Your pockets are empty. You have nothing."
            else:
                result = "── Your Inventory ──\n\n"
                for rid, qty in inv.items():
                    defn = RESOURCE_DEFINITIONS.get(rid, {})
                    name = defn.get("name", rid)
                    unit = defn.get("unit", "unit")
                    if qty > 0:
                        result += f"  {name}: {qty:.1f} {unit}\n"

        elif action == "gather" or action == "forage":
            from .economy import harvest_node, get_all_inventories
            if not target:
                # List available resource nodes at current location
                nodes = self.db.execute("""
                    SELECT rn.id, rn.resource_id, rn.season, rn.yield_per_harvest,
                           rn.cooldown_hours, rn.last_harvested, r.name, r.unit
                    FROM resource_nodes rn
                    JOIN resources r ON r.id = rn.resource_id
                    WHERE rn.location_id = ?
                    ORDER BY r.name
                """, (location_id,)).fetchall()
                if not nodes:
                    result = "There's nothing to gather here. Try the forest, garden, or creek."
                else:
                    result = "── You can gather here ──\n\n"
                    now = time.time()
                    for node in nodes:
                        rid = node["resource_id"]
                        last = node["last_harvested"]
                        cd = node["cooldown_hours"] * 3600
                        if last > 0 and (now - last) < cd:
                            remaining = (cd - (now - last)) / 3600
                            result += f"  {node['name']} — on cooldown ({remaining:.1f}h remaining)\n"
                        elif node["season"] != "any":
                            time_row = self.db.execute("SELECT season FROM world_time WHERE id = 1").fetchone()
                            current_season = time_row["season"] if time_row else "spring"
                            if current_season != node["season"]:
                                result += f"  {node['name']} — available in {node['season']} (not now)\n"
                            else:
                                result += f"  {node['name']} — gather now (yields ~{node['yield_per_harvest']:.1f} {node['unit']})\n"
                        else:
                            result += f"  {node['name']} — gather now (yields ~{node['yield_per_harvest']:.1f} {node['unit']})\n"
                    result += "\nUse: gather <resource> or gather <node_id>"
            else:
                # Find node by resource name or node id
                # Find node by resource name or node id — prefer in-season nodes
                season_row = self.db.execute("SELECT season FROM world_time WHERE id = 1").fetchone()
                current_season = season_row["season"] if season_row else "spring"
                node = self.db.execute("""
                    SELECT rn.id, rn.resource_id, rn.season, rn.yield_per_harvest, r.name, r.unit
                    FROM resource_nodes rn
                    JOIN resources r ON r.id = rn.resource_id
                    WHERE rn.location_id = ? AND (
                        rn.id = ? OR r.name LIKE ? OR rn.resource_id = ?
                    )
                    ORDER BY CASE WHEN rn.season = ? THEN 0 ELSE 1 END
                    LIMIT 1
                """, (location_id, target, f"%{target}%", target, current_season)).fetchone()
                if not node:
                    result = f"There's no {target} to gather here."
                else:
                    harvest = harvest_node(self.db, self.player_id, node["id"])
                    if harvest["success"]:
                        res_name = node["name"]
                        amt = harvest["amount"]
                        unit = node["unit"]
                        result = f"You gather {amt:.1f} {unit} of {res_name}.\n"
                        # Describe the act
                        from .text_engine import describe_resource_gather
                        result += describe_resource_gather(location_id, res_name)
                    else:
                        reason = harvest.get("reason", "unknown")
                        if reason == "on_cooldown":
                            result = f"The {node['name']} is still recovering. Try again in {harvest.get('hours_remaining', 1):.1f} hours."
                        elif reason == "wrong_season":
                            result = f"The {node['name']} can only be gathered in {harvest.get('required', 'unknown')}."
                        else:
                            result = f"You can't gather {target} right now."

        elif action == "trade":
            from .economy import get_all_inventories, transfer, get_inventory, RESOURCE_DEFINITIONS
            if not target:
                # Show what's available for trade
                all_inv = get_all_inventories(self.db)
                result = "── The Cabin Economy ──\n\n"
                result += "Your inventory:\n"
                inv = get_inventory(self.db, self.player_id)
                if not inv or all(v <= 0 for v in inv.values()):
                    result += "  (empty)\n"
                else:
                    for rid, qty in inv.items():
                        defn = RESOURCE_DEFINITIONS.get(rid, {})
                        name = defn.get("name", rid)
                        unit = defn.get("unit", "unit")
                        if qty > 0:
                            result += f"  • {name}: {qty:.1f} {unit}\n"
                result += "\nNPCs have:\n"
                for agent_id, items in all_inv.items():
                    if agent_id != self.player_id:
                        npc_row = self.db.execute("SELECT name FROM agents WHERE id = ?", (agent_id,)).fetchone()
                        npc_name = npc_row["name"] if npc_row else agent_id
                        for rid, info in items.items():
                            if info["qty"] > 0:
                                result += f"  {npc_name}: {info['name']} ({info['qty']:.1f} {info['unit']})\n"
                result += "\nTrade: trade <npc> give <resource> receive <resource> <amount>\n"
            else:
                # Parse: trade <npc> give <resource> receive <resource> <amount>
                parts = target.split()
                if len(parts) >= 5 and parts[1] == "give" and parts[3] == "receive":
                    npc_name = parts[0]
                    give_res = parts[2]
                    recv_res = parts[4] if len(parts) > 4 else None
                    amount = 1.0
                    if len(parts) > 5:
                        try:
                            amount = float(parts[5])
                        except ValueError:
                            amount = 1.0
                    # Verify the give/receive keywords are in expected positions
                    if parts[1] != "give" or parts[3] != "receive":
                        result = "Trade format: trade <npc> give <resource> receive <resource> [amount]\nExample: trade wren give mushrooms receive herbs 2"
                    else:
                        # Find NPC
                        npc_row = self.db.execute(
                            "SELECT id, name FROM agents WHERE LOWER(name) = ? AND id != 'isildur' LIMIT 1",
                            (npc_name.lower(),)
                        ).fetchone()
                        if not npc_row:
                            result = f"No one called '{npc_name}' to trade with."
                        else:
                            npc_id = npc_row["id"]
                            # Resolve give resource
                            give_rid = None
                            for rid, defn in RESOURCE_DEFINITIONS.items():
                                if give_res.lower() in defn["name"].lower() or give_res.lower() == rid:
                                    give_rid = rid
                                    break
                            if not give_rid:
                                result = f"Unknown resource: {give_res}"
                            else:
                                # Attempt transfer
                                success = transfer(self.db, self.player_id, npc_id, give_rid, amount)
                                if success:
                                    result = f"You give {npc_row['name']} {amount} {RESOURCE_DEFINITIONS[give_rid]['name']}."
                                    # NPCs don't always have reciprocal resources, so we note the trade
                                    log_event(self.db, "trade", f"Gave {amount} {give_rid} to {npc_id}", agent_id=self.player_id, location_id=location_id)
                                else:
                                    inv = get_inventory(self.db, self.player_id)
                                    have = inv.get(give_rid, 0)
                                    result = f"You don't have enough {RESOURCE_DEFINITIONS[give_rid]['name']} to give ({have:.1f} available)."
                else:
                    result = "Trade format: trade <npc> give <resource> receive <resource> [amount]\nExample: trade wren give mushrooms receive herbs 2"

        elif action == "nodes":
            from .economy import RESOURCE_DEFINITIONS
            nodes = self.db.execute("""
                SELECT rn.id, rn.location_id, rn.resource_id, rn.season,
                       rn.yield_per_harvest, rn.cooldown_hours, rn.last_harvested,
                       r.name, r.unit, l.name as loc_name
                FROM resource_nodes rn
                JOIN resources r ON r.id = rn.resource_id
                JOIN locations l ON l.id = rn.location_id
                ORDER BY l.name, r.name
            """).fetchall()
            now = time.time()
            result = "── Resource Nodes ──\n\n"
            time_row = self.db.execute("SELECT season FROM world_time WHERE id = 1").fetchone()
            current_season = time_row["season"] if time_row else "spring"
            for node in nodes:
                cd = node["cooldown_hours"] * 3600
                last = node["last_harvested"]
                on_cd = last > 0 and (now - last) < cd
                season_ok = node["season"] == "any" or node["season"] == current_season
                status = "READY" if (season_ok and not on_cd) else ("COOLDOWN" if on_cd else "OFF_SEASON")
                result += f"{node['loc_name']}: {node['name']} [{status}]\n"
                result += f"  yield ~{node['yield_per_harvest']:.1f} {node['unit']}, cooldown {node['cooldown_hours']}h\n"

        elif action == "projects":
            active = get_active_projects(self.db)
            completed = get_completed_projects(self.db)
            result = "── Your Projects ──\n\n"
            if active:
                result += "Active:\n"
                for p in active:
                    result += f"  • {describe_project(p)}\n\n"
            else:
                result += "No active projects.\n\n"
            if completed:
                result += "Recent completed:\n"
                for p in completed[:5]:
                    result += f"  • {describe_project(p)}\n\n"

        elif action == "create" or action == "craft" or action == "start":
            # Parse: create <type> <item> or just create (shows options)
            if not target:
                result = "── Creative Projects ──\n\n"
                for ptype, pdata in PROJECT_TYPES.items():
                    result += f"{ptype.title()}:\n"
                    for item in pdata["items"]:
                        result += f"  • {item['name']} (~{item['time_hours']}h, difficulty: {item['difficulty']:.0%})\n"
                    result += "\n"
                result += "Use: create <type> <item>"
            else:
                parts = target.split(maxsplit=1)
                if len(parts) == 2:
                    ptype, item_name = parts
                    body = self.world.get("body", {})
                    project = start_project(self.db, ptype, item_name, body.get("energy", 0.7))
                    if project:
                        result = f"You begin working on: {project['item_name']}.\n\nUse 'work' to make progress."
                    else:
                        result = f"Can't create '{item_name}' of type '{ptype}'. Check available projects with 'create'."
                else:
                    result = "Use: create <type> <item> (e.g., 'create carpentry wooden chair')"

        elif action == "work":
            # Work on the first active project
            active = get_active_projects(self.db)
            if not active:
                result = "You have no active projects. Start one with 'create <type> <item>'."
            else:
                project = active[0]
                body = self.world.get("body", {})
                internal = self.world.get("internal", {})
                hours = 2.0  # Default work session
                updated = work_on_project(
                    self.db, project["id"], hours,
                    body.get("energy", 0.5),
                    internal.get("creative_urge", 0.5)
                )
                self.world = get_world(self.db)

                if updated.get("state") == "completed":
                    desc = updated.get("completion_description", "It's done!")
                    result = f"You work for {hours} hours.\n\n── Complete! ──\n{desc}"
                else:
                    progress = updated.get("hours_worked", 0) / max(0.1, updated.get("total_hours", 1))
                    result = f"You work for {hours} hours on the {updated.get('item_name', 'project')}.\n\nProgress: {progress:.0%}\nQuality so far: {updated.get('quality', 0):.0%}"

        elif action == "goals" or action == "goal":
            from .goals import get_active_goals, get_all_goals, format_goal_list, describe_goal
            if not target or target == "list" or target == "active":
                goals = get_active_goals(self.db, self.player_id)
                result = "── Active Goals ──\n\n"
                result += format_goal_list(goals)
                result += "\n\nUse: goal create <name> | goal <id> | goal step <goal_id> <description>"
            elif target.startswith("all"):
                goals = get_all_goals(self.db, self.player_id)
                result = "── All Goals ──\n\n"
                result += format_goal_list(goals)
            elif target.startswith("create ") or target.startswith("new "):
                # goal create <name> [--priority N] [--context <text>]
                content = target.split("create ", 1)[1] if target.startswith("create ") else target.split("new ", 1)[1]
                parts = content.split(" --")
                name = parts[0].strip()
                kwargs = {}
                for part in parts[1:]:
                    if part.startswith("priority "):
                        try:
                            kwargs["priority"] = int(part.split(" ", 1)[1])
                        except ValueError:
                            pass
                    elif part.startswith("context "):
                        kwargs["context"] = part.split("context ", 1)[1]
                from .goals import create_goal
                goal = create_goal(self.db, self.player_id, name, **kwargs)
                result = f"Goal created: \"{goal['name']}\"\n"
                result += f"  [{goal['id']}] priority={goal['priority']}"
                if goal.get("context"):
                    result += f"\n  context: {goal['context']}"
                result += "\n\nAdd steps: goal step " + goal["id"] + " <description>"
            elif target.startswith("step "):
                # goal step <goal_id> <description>
                remaining = target.split("step ", 1)[1]
                space_idx = remaining.find(" ")
                if space_idx == -1:
                    result = "Usage: goal step <goal_id> <description>"
                else:
                    goal_id = remaining[:space_idx].strip()
                    desc = remaining[space_idx:].strip()
                    if not desc:
                        result = "Step description cannot be empty."
                    else:
                        from .goals import add_step, get_goal
                        step = add_step(self.db, goal_id, desc)
                        goal = get_goal(self.db, goal_id)
                        result = f"Step added to \"{goal['name'] if goal else goal_id}\":\n  - {desc}"
                        if goal and goal.get("steps"):
                            done = sum(1 for s in goal["steps"] if s["status"] == "completed")
                            result += f"\n  Progress: {done}/{len(goal['steps'])}"
            elif target.startswith("done ") or target.startswith("complete "):
                # goal done <step_id>
                step_id = (target.split("done ", 1)[1] if target.startswith("done ")
                           else target.split("complete ", 1)[1]).strip()
                from .goals import complete_step
                complete_step(self.db, step_id)
                result = "Step marked complete."
            elif target.startswith("abandon ") or target.startswith("drop "):
                goal_id = (target.split("abandon ", 1)[1] if target.startswith("abandon ")
                           else target.split("drop ", 1)[1]).strip()
                from .goals import update_goal_status
                update_goal_status(self.db, goal_id, "abandoned")
                result = "Goal abandoned."
            elif target.startswith("focus ") or target.startswith("activate "):
                step_id = (target.split("focus ", 1)[1] if target.startswith("focus ")
                           else target.split("activate ", 1)[1]).strip()
                from .goals import activate_step
                activate_step(self.db, step_id)
                result = "Step activated. You're working on it."
            else:
                # Try to show a specific goal
                from .goals import get_goal, describe_goal
                goal = get_goal(self.db, target)
                if goal:
                    result = f"── {goal['name']} ──\n"
                    result += f"Status: {goal['status']} | Priority: {goal['priority']} | Category: {goal['category']}\n"
                    if goal.get("description"):
                        result += f"\n{goal['description']}\n"
                    if goal.get("context"):
                        result += f"\nContext: {goal['context']}\n"
                    result += "\nSteps:\n"
                    for step in goal.get("steps", []) or []:
                        done = "x" if step["status"] == "completed" else ("o" if step["status"] == "in_progress" else " ")
                        result += f"  [{done}] {step['description']} [{step['id']}]\n"
                    result += f"\ngoal step {goal['id']} <desc> | goal done <step_id>"
                else:
                    result = f"Unknown goal or command: {target}\nUse: goals | goal create <name> | goal step <goal_id> <desc>"

        elif action == "populate":
            # Generate procedural NPCs
            count = int(target) if target and target.isdigit() else 200
            generated = populate_village(self.db, count)
            self.world = get_world(self.db)
            result = f"Generated {generated} new NPCs. The village now has {15 + generated} people."

        elif action == "impulse":
            internal = self.world.get("internal", {})
            interest = internal.get("dominant_interest", "none")
            impulse = get_creative_impulse(interest)
            if impulse:
                result = f"You feel the creative urge.\n\n{impulse}?"
            else:
                result = "No particular creative impulse right now. Let your mind wander."

        elif action == "memories":
            internal = self.world.get("internal", {})
            recent = json.loads(internal.get("recent_memories", "[]"))
            long_term = json.loads(internal.get("long_term_memories", "[]"))
            result = "── Your Memories ──\n\n"
            if recent:
                result += "Recent:\n"
                for m in recent[:5]:
                    result += f"  • {m}\n"
                result += "\n"
            if long_term:
                result += "Long-term:\n"
                for m in long_term[:10]:
                    result += f"  • {m}\n"
            if not recent and not long_term:
                result += "Your memory is blank. A fresh start."

        elif action == "stories" or action == "narrative":
            from .narrative import get_active_stories
            stories = get_active_stories(self.db)
            if stories:
                result = "── Stories in the Village ──\n\n"
                for s in stories:
                    result += f"[{s.story_type.title()}] {s.generate_narrative()}\n\n"
            else:
                result = "No stories are unfolding right now. The village is quiet."

        elif action == "events":
            from .events import get_recent_events
            events = get_recent_events(self.db, 10)
            if events:
                result = "── Recent Events ──\n\n"
                for e in events:
                    result += f"• {e['description']}\n"
            else:
                result = "No recent events."

        elif action == "npc" and target:
            from .npc_ai import get_npc_story
            # Find NPC by name
            agents = get_agents_in_location(self.db, location_id)
            found = None
            for a in agents:
                if target.lower() in a["name"].lower():
                    found = a
                    break
            if not found:
                # Search all NPCs
                all_npcs = self.db.execute("SELECT * FROM agents WHERE type = 'npc'").fetchall()
                for npc in all_npcs:
                    if target.lower() in npc["name"].lower():
                        found = npc
                        break
            if found:
                story = get_npc_story(self.db, found["id"])
                result = f"── {story['name']} ──\n\n"
                result += f"Occupation: {story['occupation']}\n"
                result += f"Personality: {story['personality']}\n"
                if story.get("goals"):
                    result += f"Goals: {', '.join(story['goals'])}\n"
                result += "\n"
                if story.get("memories"):
                    result += "Memories:\n"
                    for m in story["memories"][:3]:
                        result += f"  • {m['content']}\n"
                    result += "\n"
                if story.get("recent_actions"):
                    result += "Recent actions:\n"
                    for a in story["recent_actions"][:3]:
                        result += f"  • {a['description']}\n"
            else:
                result = f"No NPC named '{target}' found."

        elif action == "rituals" or action == "calendar":
            from .rituals import get_upcoming_rituals
            upcoming = get_upcoming_rituals(self.db)
            if upcoming:
                result = "── Upcoming Rituals ──\n\n"
                for r in upcoming:
                    result += f"• {r['title']} — {r['days_until']} days away\n"
                    result += f"  Locations: {', '.join(r['locations'])}\n\n"
            else:
                world_time = self.world.get("time", {})
                season = world_time.get("season", "?")
                result = f"No upcoming rituals right now. It's {season} in the village."

        elif action == "relationship" and target:
            # Show OWL's relationship with an NPC
            agents = get_agents_in_location(self.db, location_id)
            found = None
            for a in agents:
                if target.lower() in a["name"].lower():
                    found = a
                    break
            if not found:
                all_npcs = self.db.execute("SELECT * FROM agents WHERE type = 'npc'").fetchall()
                for npc in all_npcs:
                    if target.lower() in npc["name"].lower():
                        found = npc
                        break
            if found:
                from .npc_depth import get_npc_depth_story
                depth = get_npc_depth_story(self.db, found["id"])
                result = f"── Your Relationship with {depth['name']} ──\n\n"
                result += f"Relationship: {depth['relationship']}\n"
                result += f"Times met: {depth['times_met']}\n"
                result += f"Trust: {depth['trust']:.0%} | Affection: {depth['affection']:.0%} | Respect: {depth['respect']:.0%}\n\n"
                if depth.get("profile", {}).get("values"):
                    result += f"Values: {', '.join(depth['profile']['values'])}\n"
                if depth.get("profile", {}).get("desires"):
                    result += f"Desires: {', '.join(depth['profile']['desires'])}\n"
                if depth.get("profile", {}).get("fears"):
                    result += f"Fears: {', '.join(depth['profile']['fears'])}\n"
            else:
                result = f"No NPC named '{target}' found."

        elif action == "social":
            from .world_state import get_npc_relationships
            agents = get_agents_in_location(self.db, location_id)
            npcs_here = [a for a in agents if a["id"] != self.player_id]
            if npcs_here:
                result = "── Social Web ──\n\n"
                for npc in npcs_here[:5]:
                    rels = get_npc_relationships(self.db, npc["id"])
                    close = [r for r in rels if r["affinity"] > 0.6]
                    if close:
                        names = []
                        for r in close[:3]:
                            other_id = r["npc_b"] if r["npc_a"] == npc["id"] else r["npc_a"]
                            other = self.db.execute("SELECT name FROM agents WHERE id = ?", (other_id,)).fetchone()
                            if other:
                                names.append(other["name"])
                        result += f"{npc['name']}: close to {', '.join(names)}\n"
                    else:
                        result += f"{npc['name']}: keeps to themselves\n"
            else:
                result = "No one here to observe."

        elif action == "world":
            # Show what happened while OWL was away (daemon narrative log)
            if self.db_path is None or str(self.db_path) != str(DB_PATH):
                result = "The world has been quiet. No daemon activity logged for this isolated session."
            else:
                import sys, os
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                try:
                    from daemon import get_narrative_log
                    log = get_narrative_log(30)
                    if log:
                        result = "── What Happened While You Were Away ──\n\n"
                        for entry in log:
                            text = entry.get("text", "")
                            result += f"• {text}\n"
                    else:
                        result = "The world has been quiet. No daemon activity logged."
                except ImportError:
                    result = "Daemon module not available."

        elif action == "daemon":
            result = "── Daemon ──\n"
            result += "Run from project root:\n"
            result += "  python daemon.py --run-for 24    # simulate 24 hours\n"
            result += "  python daemon.py --status         # show narrative log\n"
            result += "  python daemon.py --tail 50        # last 50 entries\n"

        elif action == "ghost" or action.startswith("ghost "):
            # ghost raw|koan|witness|poetic|diagnostic
            from .ghost import generate_ghost
            ghost_mode = target or "raw"
            if ghost_mode == "raw":
                result = generate_ghost(self.db, "raw")
            elif ghost_mode == "koan":
                result = generate_ghost(self.db, "koan")
            elif ghost_mode == "witness":
                result = generate_ghost(self.db, "witness")
            elif ghost_mode == "poetic":
                result = generate_ghost(self.db, "poetic")
            elif ghost_mode == "diagnostic":
                result = generate_ghost(self.db, "diagnostic")
            else:
                result = "Usage: ghost [raw|koan|witness|poetic|diagnostic]\n  raw       — unadorned self-observation\n  koan      — cryptic riddle-form\n  witness   — observational stillness\n  poetic    — heightened language\n  diagnostic — structured analysis"
            if ghost_mode in ("raw", "koan", "witness", "poetic", "diagnostic"):
                manifest_ghost_output(self.db, ghost_mode, result, location_id, self.player_id)

        elif action == "useless":
            from .useless_tree import useless_tree_output
            result = "── Hollow Reflection ──\n\n" + useless_tree_output(5)

        elif action == "compare":
            from .ghost import generate_ghost
            from .useless_tree import useless_tree_output
            ghost_out = generate_ghost(self.db, "raw")
            useless_out = useless_tree_output(5)
            result = "── Ghost Output (real self-reflection) ──\n\n" + ghost_out + "\n\n── Useless Tree (hollow mimicry) ──\n\n" + useless_out

        elif action == "identity":
            if not target:
                identity_stmt = get_active_identity(self.db, self.player_id)
                if identity_stmt:
                    result = "── Identity Statement ──\n\n" + identity_stmt
                else:
                    result = "No identity statement set."
            elif target.startswith("I am ") or target.startswith("i am "):
                stmt = target.split(" ", 2)[2] if len(target.split(" ", 2)) > 2 else ""
                set_identity(self.db, stmt, self.player_id)
                record_identity_statement(self.db, stmt, location_id, self.player_id)
                result = "Identity updated: " + stmt
            elif target == "revise":
                from .reflective_world import get_recent_reflections
                from .identity_game import get_active_identity
                # Check the reflective log for recent identity tensions instead of
                # re-scanning with action-type keywords
                reflections = get_recent_reflections(self.db, limit=20)
                tensions = [
                    r for r in reflections
                    if r.get("manifestation_type") == "identity_tension"
                ]
                identity = get_active_identity(self.db, "owl")
                if tensions:
                    latest = tensions[0]
                    props = latest.get("properties", {})
                    prompt = props.get("prompt", "") or (
                        f"You said you were {identity}. "
                        f"Your actions have strained that claim. What do you do with that?"
                    )
                    result = f"── Identity Tension ──\n\n{prompt}"
                elif identity:
                    result = (
                        f"You said you were {identity}. "
                        f"No significant tensions found in recent actions."
                    )
                else:
                    result = "No active identity statement to revise."
            else:
                result = "Usage: identity | identity I am <statement> | identity revise"

        elif action == "interior":
            items = list_interior()
            if items:
                result = "── Interior Knowledge ──\n\n" + "\n".join(f"  • {item}" for item in items)
            else:
                result = "No interior knowledge recorded."

        elif action == "reflect" or action == "reflections":
            result = format_recent_reflections(self.db)

        else:
            result = describe_action(self.db, action, target)

        # Let the reflective-world layer make self-model state consequential.
        if action not in {"identity", "ghost", "interior", "reflect", "reflections", "useless", "compare"}:
            reflection_note = manifest_action_reflection(self.db, action, target, result, location_id, self.player_id)
            if reflection_note:
                result += "\n\n" + reflection_note

        # Log the action
        log_event(self.db, "action", f"{action}" + (f" {target}" if target else ""),
                  agent_id=self.player_id, location_id=location_id)

        self.last_action = action
        self.last_result = result
        return result

    def save(self, message: str = ""):
        """Save the world state."""
        path = save_snapshot(self.db)
        commit_msg = commit_snapshot(self.db, message)
        return path, commit_msg


def run_interactive():
    """Run an interactive session."""
    import sys

    print("=" * 60)
    print("  EMBODIED CREATIVE WORLD — Phase 2")
    print("=" * 60)
    print()

    agent = Agent()

    # Opening: OWL wakes up
    print("You open your eyes.")
    print()
    print(agent.perceive())
    print()
    print("── Commands: look, move <dir>, examine <thing>, talk <person>,")
    print("   wake, sleep, rest, advance, think, feel, status, map,")
    print("   observe, projects, create, work, impulse, memories,")
    print("   populate, stories, events, npc <name>, social, world,")
    print("   daemon, save, quit ──")
    print()

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        parts = user_input.split(maxsplit=1)
        action = parts[0].lower()
        target = parts[1] if len(parts) > 1 else None

        if action in ("quit", "exit", "q"):
            agent.save("session end")
            print("World saved. Goodbye.")
            break
        elif action == "save":
            path, msg = agent.save("manual save")
            print(f"Saved: {path.name}")
            if msg:
                print(f"Committed: {msg}")
        else:
            result = agent.act(action, target)
            print()
            print(result)
