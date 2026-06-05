"""
rich_narrative.py — LLM-powered prose generation for the Aurelia simulation.

Bridges the exhaustive Phase 1-6.6 mechanics to a language model that
generates rich, literary prose — daily vignettes, yearly chronicles,
and moment-specific narratives for significant events.

Design:
- Daily prose: only for ticks with notable events (LLM call ~0.5-2s)
- Yearly chronicles: comprehensive narrative at year boundaries
- Moment prose: for faction formations, wars, discoveries, great persons
- All functions return None gracefully if LLM is unavailable
- Prompt engineering: compact but information-dense state summaries
"""

import json
import time
from typing import Optional, Dict, Any, List

from llm_client import LLMClient, get_client

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]

WORLD_PROFILES = {
    "solara": "Solara, the agricultural heartland. Rolling fields, orchards, and the gentle River Luthien. "
              "The oldest continuous human settlement in the Federation. Known for its grain, its festivals, "
              "and its quiet conservatism. Population ~12,000.",
    "valdris": "Valdris, the northern industrial power. Iron mines, forges, and the smoke-stained city of "
              "Dunmir. The Vorn population is concentrated here, working the deep seams. Cold winters, "
              "hard people, harder politics. Population ~12,000.",
    "mirithane": "Mirithane, the coastal republic of scholars and sailors. The great library at Caer Myrthin, "
                 "the shipyards at Port Selwyn. A tradition of intellectual freedom and maritime trade. "
                 "Threns and humans work side by side in the scriptoria. Population ~12,000.",
    "arkos": "Arkos, the desert citadel. Sand-glass towers rise from the red wastes. Ancient, proud, "
             "isolated. The Glim population was decanted here first, and their latency fields still resonate "
             "with the sand-glass architecture. Population ~12,000.",
    "verge": "The Verge, the frontier. A wild territory of deep forests and unmapped valleys. No central "
             "government — a patchwork of settlements, outcasts, and pioneers. The Fabricator's signal "
             "originates somewhere in the northern range. Population ~12,000.",
}

SPECIES_CONTEXT = (
    "Four sentient species share this world: Humans (baseline), Threns (circuitry-integrated, "
    "emotion-reading), Vorns (stone-skinned, deep-earth attuned), and Glims (decommissioned AI, "
    "latency field capable). Species relations range from cooperation to deep-seated grievance."
)

NARRATIVE_VOICE = (
    "Write in a literary, grounded style. Avoid fantasy clichés — no taverns, no kings, no dragons. "
    "This is a post-Collapse world where something was lost and something else is being built. "
    "The tone is: elegiac but unsentimental, precise, attentive to sensory detail. "
    "Weather matters. Light matters. The weight of history matters. "
    "Use short sentences for tension, longer ones for reflection. "
    "Anchor everything in specific places and named individuals."
)


# ═══════════════════════════════════════════════════════════════════
# STATE SUMMARIZATION
# ═══════════════════════════════════════════════════════════════════

def summarize_world(db, world_id: str) -> str:
    """Build a compact state summary for LLM prompting. ~300-500 chars."""
    parts = [WORLD_PROFILES.get(world_id, f"World: {world_id}")]

    # Population
    pop = db.execute(
        "SELECT COUNT(*) as c FROM agents WHERE type='npc' AND state='active'"
    ).fetchone()
    if pop:
        parts.append(f"Population: {pop['c']:,} active NPCs.")

    # Species breakdown
    species = {}
    for t in ["human", "thren", "vorn", "glim"]:
        row = db.execute(
            "SELECT COUNT(*) as c FROM agents a WHERE a.type='npc' AND a.state='active' "
            "AND json_extract(a.properties, '$.npc_type') = ?", (t,)
        ).fetchone()
        if row and row["c"]:
            species[t] = row["c"]
    if species:
        parts.append("Species: " + ", ".join(f"{k}={v}" for k, v in species.items()))

    # Time
    wt = db.execute(
        "SELECT year, month, day, season, time_of_day FROM world_time WHERE id=1"
    ).fetchone()
    if wt:
        parts.append(
            f"Date: Year {wt['year']}, Month {wt['month']}, Day {wt['day']}. "
            f"Season: {wt['season']}. Time: {wt['time_of_day']}."
        )

    # Factions
    active = db.execute(
        "SELECT COUNT(*) as c FROM factions WHERE status NOT IN ('dissolved','sovereign')"
    ).fetchone()
    at_war = db.execute(
        "SELECT COUNT(*) as c FROM factions WHERE status='war'"
    ).fetchone()
    integrated = db.execute(
        "SELECT COUNT(*) as c FROM factions WHERE status='integrated'"
    ).fetchone()
    if active and active["c"] > 0:
        fparts = [f"{active['c']} active factions"]
        if at_war["c"] > 0:
            fparts.append(f"{at_war['c']} at war")
        if integrated["c"] > 0:
            fparts.append(f"{integrated['c']} integrated")
        parts.append("Factions: " + ", ".join(fparts))

    # Faction details (top 5)
    factions = db.execute(
        "SELECT name, status, grievance_type, member_count FROM factions "
        "WHERE status NOT IN ('dissolved','sovereign') ORDER BY member_count DESC LIMIT 5"
    ).fetchall()
    if factions:
        flines = []
        for f in factions:
            flines.append(f"  - {f['name']} ({f['status']}, {f['grievance_type']}, {f['member_count']} members)")
        parts.append("Faction details:\n" + "\n".join(flines))

    # Discoveries
    disc_count = db.execute("SELECT COUNT(*) as c FROM discoveries").fetchone()
    if disc_count and disc_count["c"] > 0:
        recent = db.execute(
            "SELECT title, description FROM discoveries ORDER BY created_at DESC LIMIT 3"
        ).fetchall()
        parts.append(f"Discoveries: {disc_count['c']} total.")
        if recent:
            for d in recent:
                parts.append(f"  - {d['title']}: {d['description'][:120]}")

    # Great persons
    gp_count = db.execute("SELECT COUNT(*) as c FROM great_persons").fetchone()
    if gp_count and gp_count["c"] > 0:
        recent = db.execute(
            "SELECT title, description FROM great_persons ORDER BY created_at DESC LIMIT 3"
        ).fetchall()
        parts.append(f"Great Persons: {gp_count['c']} total.")
        if recent:
            for gp in recent:
                parts.append(f"  - {gp['title']}: {gp['description'][:120]}")

    # Treaties
    treaties = db.execute(
        "SELECT COUNT(*) as c FROM peace_treaties WHERE broken=0"
    ).fetchone()
    if treaties and treaties["c"] > 0:
        recent = db.execute(
            "SELECT title FROM peace_treaties WHERE broken=0 ORDER BY signed_at DESC LIMIT 3"
        ).fetchall()
        parts.append(f"Active treaties: {treaties['c']}.")
        if recent:
            parts.append("  - " + ", ".join(t["title"] for t in recent))

    # Migrations
    migrations = db.execute("SELECT COUNT(*) as c FROM cross_world_movements").fetchone()
    if migrations and migrations["c"] > 0:
        parts.append(f"Cross-world migrations: {migrations['c']}.")

    # Economy
    eco = db.execute(
        "SELECT AVG(CAST(json_extract(variables, '$.economic_stability') AS REAL)) as avg_eco, "
        "AVG(CAST(json_extract(variables, '$.satisfaction') AS REAL)) as avg_sat "
        "FROM npc_decision_state"
    ).fetchone()
    if eco and eco["avg_eco"] is not None:
        parts.append(
            f"Economic stability: {eco['avg_eco']:.2f} (avg). "
            f"Satisfaction: {eco['avg_sat']:.2f} (avg)."
        )

    return "\n".join(parts)


def summarize_tick_events(tick_result: dict) -> str:
    """Summarize what happened in a single tick for LLM context. ~200-500 chars."""
    events = []

    # Emergent events (factions, escalation, sovereignty, etc.)
    emergent = tick_result.get("emergent_events", [])
    for ev in emergent:
        title = ev.get("title", "")
        desc = ev.get("description", "")
        if title and desc:
            events.append(f"- [{ev.get('category', 'event')}] {title}: {desc[:200]}")

    # NPC actions (sample)
    npc_actions = tick_result.get("npc_ai_actions", [])
    if npc_actions:
        sample = npc_actions[:5]
        events.append(f"- {len(npc_actions)} NPC actions. Notable: " +
                      "; ".join(a.get("action", "")[:100] for a in sample))

    # Social changes
    social = tick_result.get("social_changes", [])
    for sc in social[:3]:
        desc = sc.get("description", "")
        if desc:
            events.append(f"- Social: {desc[:150]}")

    # Narrative moments
    narrative = tick_result.get("narrative_moments", [])
    for nm in narrative[:3]:
        content = nm.get("content", "")
        if content:
            events.append(f"- Narrative: {content[:150]}")

    # Weather
    weather = tick_result.get("weather", {})
    if weather.get("changed"):
        events.append(f"- Weather: {weather.get('condition', 'unknown')}, {weather.get('temperature', '?')}°C")

    # Season change
    time_info = tick_result.get("time", {})
    if time_info.get("season_changed"):
        events.append(f"- Season changed to {time_info.get('season', '?')}")

    if not events:
        return "Nothing notable occurred this cycle."

    return "\n".join(events)


def summarize_year(events_log: List[Dict]) -> str:
    """Build a compact summary of a year's accumulated events. ~500-1000 chars."""
    if not events_log:
        return "A quiet year. No events of note were recorded."

    # Group by category
    by_category = {}
    for ev in events_log:
        cat = ev.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(ev)

    parts = []
    for cat, evs in sorted(by_category.items()):
        if len(evs) == 1:
            parts.append(f"{cat.title()}: {evs[0].get('title', 'event')} — {evs[0].get('description', '')[:150]}")
        else:
            parts.append(f"{cat.title()}: {len(evs)} events — " +
                        "; ".join(e.get("title", "event")[:60] for e in evs[:3]))

    # Always include at least something
    if not parts:
        return "A quiet year. Daily life continued its rhythms."

    return "\n".join(parts[:10])  # Cap at 10 lines


# ═══════════════════════════════════════════════════════════════════
# PROSE GENERATION
# ═══════════════════════════════════════════════════════════════════

def _build_system_prompt(world_id: str, world_context: str) -> str:
    """Build the system prompt for narrative generation."""
    return (
        f"You are the narrator of the Aurelia Federation simulation: {world_id.title()}.\n\n"
        f"{SPECIES_CONTEXT}\n\n"
        f"Current world state:\n{world_context}\n\n"
        f"{NARRATIVE_VOICE}"
    )


def generate_daily_prose(
    world_id: str,
    world_context: str,
    tick_events: str,
    client: LLMClient,
) -> Optional[str]:
    """
    Generate a prose vignette for a single tick's events.
    Only called when there are notable events — not every tick.
    """
    system = _build_system_prompt(world_id, world_context)

    prompt = (
        f"A cycle has passed. Here is what happened:\n\n{tick_events}\n\n"
        f"Write a brief prose vignette (3-5 sentences) capturing this moment in {world_id.title()}. "
        f"Ground it in sensory detail — weather, light, sound. "
        f"Name the people involved. Show, don't tell. "
        f"Make it feel lived-in, not reported."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    return client.try_chat(messages, temperature=0.8, max_tokens=256)


def generate_yearly_chronicle(
    world_id: str,
    world_context: str,
    year_summary: str,
    year_number: int,
    client: LLMClient,
) -> Optional[str]:
    """
    Generate a grand yearly chronicle — the definitive narrative of a sim-year.
    Called at year boundaries. This is the primary output artifact.
    """
    system = _build_system_prompt(world_id, world_context)

    prompt = (
        f"This is the end of Year {year_number} in {world_id.title()}.\n\n"
        f"Events of the year:\n{year_summary}\n\n"
        f"Current world state:\n{world_context}\n\n"
        f"Write a chronicle entry for Year {year_number}. Structure it as:\n"
        f"1. A header: 'Year {year_number} — {world_id.title()}'\n"
        f"2. A 1-2 paragraph overview of the year's major developments\n"
        f"3. Notable individuals — name them, describe their actions\n"
        f"4. The mood of the world as the year closes\n\n"
        f"This should read like a history, not a report. "
        f"Ground everything in sensory and emotional texture. "
        f"Make it feel REAL."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    return client.try_chat(messages, temperature=0.7, max_tokens=800)


def generate_moment_prose(
    world_id: str,
    world_context: str,
    event_type: str,
    event_data: Dict[str, Any],
    client: LLMClient,
) -> Optional[str]:
    """
    Generate prose for a specific significant moment:
    faction formation, war declaration, great person event, discovery, treaty.
    """
    system = _build_system_prompt(world_id, world_context)

    title = event_data.get("title", "An event")
    description = event_data.get("description", "")
    category = event_data.get("category", "event")

    prompt = (
        f"A significant event has occurred in {world_id.title()}:\n\n"
        f"Type: {category}\n"
        f"Title: {title}\n"
        f"Details: {description}\n\n"
        f"Write a prose passage (4-8 sentences) capturing this moment. "
        f"Show us: where it happened, who was there, what it felt like. "
        f"The weight of the moment should be palpable. "
        f"Anchor it in the physical world — the light at that hour, the weather, the sounds."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    return client.try_chat(messages, temperature=0.75, max_tokens=400)


# ═══════════════════════════════════════════════════════════════════
# BATCH PROCESSING
# ═══════════════════════════════════════════════════════════════════

def generate_all_year_chronicles(
    years_output: Dict[int, Dict[str, Any]],
    client: LLMClient,
) -> Dict[str, List[str]]:
    """
    After a speed run completes, generate yearly chronicles in batch
    using the accumulated summaries. Much more efficient than per-tick.
    Returns {world_id: [chronicle_texts]}.
    """
    chronicles = {w: [] for w in COUNTRIES}

    for year_num in sorted(years_output.keys()):
        year_data = years_output[year_num]
        for world_id in COUNTRIES:
            world_year = year_data.get(world_id, {})
            if not world_year:
                continue

            context = world_year.get("context", "")
            summary = world_year.get("summary", "A quiet year.")
            events_count = len(world_year.get("events", []))

            if events_count == 0 and year_num % 10 != 0:
                # Skip quiet years (unless it's a decade boundary)
                chronicles[world_id].append(f"Year {year_num}: A quiet year in {world_id.title()}.")
                continue

            chronicle = generate_yearly_chronicle(
                world_id, context, summary, year_num, client
            )
            if chronicle:
                chronicles[world_id].append(chronicle)
            else:
                # Fallback: template-based
                chronicles[world_id].append(
                    f"Year {year_num} — {world_id.title()}\n\n{summary}"
                )

    return chronicles
