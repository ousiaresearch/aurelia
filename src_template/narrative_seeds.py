"""narrative_seeds.py — Probability-modulated extraordinary event generator.

Sits BESIDE the Phase 4 physics engine, not inside it. Where Phase 4 asks
"did conditions cross a threshold?", this engine asks "did the world's mood
produce a lightning strike?" Both feed the same federation event bus.

Design principles:
- Base probabilities, modulated by world state — never gated.
- Every seed can fire in any country at any tick. Unlikely but possible.
- Multipliers query coordinator state (/api/growth) — data we already have.
- No new tables. No new state. One function: draw_seed().
- Produces federation event dicts the existing pipeline already ingests.
"""

import random
import time
from typing import Optional, Dict, Any, List

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]

COUNTRY_NAMES = {
    "solara": "Solara", "valdris": "Valdris", "mirithane": "Mirithane",
    "arkos": "Arkos", "verge": "The Verge",
}

# ── Cooldown tracking (in-memory, per daemon process) ──────────────
# Prevent the same seed from firing twice back-to-back in the same world.
_cooldowns: Dict[str, float] = {}


def _on_cooldown(seed_type: str, world_id: str, min_interval: float = 3600) -> bool:
    key = f"{seed_type}:{world_id}"
    now = time.time()
    if key in _cooldowns and (now - _cooldowns[key]) < min_interval:
        return True
    return False


def _set_cooldown(seed_type: str, world_id: str):
    _cooldowns[f"{seed_type}:{world_id}"] = time.time()


# ═══════════════════════════════════════════════════════════════════
# SEED DECK
# ═══════════════════════════════════════════════════════════════════

def _rebellion(world_id: str, growth: dict) -> Optional[dict]:
    """A faction of dissatisfied citizens organizes."""
    base = 0.0005
    tension = _avg_tension_for_world(world_id, growth)
    anomalies = growth.get("glim_anomaly_signals", 0)
    avg_sec = _estimate_avg_security(growth)
    
    if tension > 0.5:
        base *= 1.5
    if anomalies > 0:
        base *= 1.5
    if avg_sec < 0.4:
        base *= 1.2
    if growth.get("diplomatic_incidents", 0) > 5:
        base *= 1.3
    
    if random.random() > base:
        return None
    
    demands = random.choice([
        "full citizenship for all sentient types",
        "abolition of the decommissioning policy",
        "representation in the governing council",
        "economic redistribution and land reform",
        "recognition of Glim personhood",
        "an end to cross-border resource extraction",
    ])
    
    _set_cooldown("rebellion", world_id)
    return {
        "event_type": "rebellion",
        "category": "governance",
        "title": f"Rebellion sparks in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": f"A faction in {COUNTRY_NAMES.get(world_id, world_id)} demands {demands}. The movement is organizing.",
        "importance": 0.88,
        "actor_ids": [],
        "tags": ["rebellion", "governance", world_id, "crisis"],
        "payload": {"demands": demands, "country": world_id},
        "world_time": {},
    }


def _diplomatic_scandal(world_id: str, growth: dict) -> Optional[dict]:
    """A diplomatic revelation strains relations between two countries."""
    base = 0.001
    tension = _avg_tension_for_world(world_id, growth)
    incidents = growth.get("diplomatic_incidents", 0)
    
    if tension > 0.4:
        base *= 1.3
    if incidents > 3:
        base *= 1.5
    
    if random.random() > base:
        return None
    
    partner = random.choice([c for c in COUNTRIES if c != world_id])
    scandals = [
        f"Leaked diplomatic cables reveal {COUNTRY_NAMES.get(world_id)} has been secretly funding opposition groups in {COUNTRY_NAMES.get(partner)}.",
        f"A {COUNTRY_NAMES.get(world_id)} ambassador is caught passing intelligence to {COUNTRY_NAMES.get(partner)}.",
        f"Trade agreement violations: {COUNTRY_NAMES.get(world_id)} accused of dumping sanctioned goods in {COUNTRY_NAMES.get(partner)}.",
        f"{COUNTRY_NAMES.get(world_id)} diplomats recall their embassy staff from {COUNTRY_NAMES.get(partner)} after espionage allegations.",
    ]
    
    _set_cooldown("diplomatic_scandal", world_id)
    return {
        "event_type": "diplomatic_scandal",
        "category": "diplomacy",
        "title": f"Diplomatic scandal: {COUNTRY_NAMES.get(world_id, world_id)} — {COUNTRY_NAMES.get(partner, partner)}",
        "description": random.choice(scandals),
        "importance": 0.78,
        "actor_ids": [],
        "tags": ["scandal", "diplomacy", world_id, partner],
        "payload": {"source": world_id, "target": partner},
        "world_time": {},
    }


def _natural_disaster(world_id: str, growth: dict) -> Optional[dict]:
    """A natural disaster displaces population and disrupts economy."""
    base = 0.0003
    
    if world_id == "verge":
        base *= 2.0
    elif world_id in ("solara", "mirithane"):
        base *= 1.5  # Coastal/flood-prone
    
    if random.random() > base:
        return None
    
    disasters = {
        "solara": ["Solar storm knocks out grid infrastructure across the coastal belt.",
                   "Rising sea levels breach the outer reef barriers."],
        "valdris": ["Canyon earthquake collapses three mining shafts.",
                    "Geothermal vent eruption disrupts the forge district."],
        "mirithane": ["Estuary flood submerges the filtration reefs.",
                      "A salt bloom poisons the freshwater channels."],
        "arkos": ["Sandstorm buries the outer solar arrays for three days.",
                  "Arcology cooling systems fail during a record heat wave."],
        "verge": ["A toxic dust storm rolls through the wasteland.",
                  "Scavenger camps swept away by flash floods in the dry basin."],
    }
    
    desc = random.choice(disasters.get(world_id, disasters["verge"]))
    
    _set_cooldown("natural_disaster", world_id)
    return {
        "event_type": "natural_disaster",
        "category": "ecology",
        "title": f"Disaster strikes {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": desc,
        "importance": 0.82,
        "actor_ids": [],
        "tags": ["disaster", "ecology", world_id, "crisis"],
        "payload": {"type": "natural_disaster", "country": world_id},
        "world_time": {},
    }


def _tech_breakthrough(world_id: str, growth: dict) -> Optional[dict]:
    """A technological breakthrough shifts capability and diplomatic leverage."""
    base = 0.0002
    
    if world_id == "arkos":
        base *= 1.5
    elif world_id == "solara":
        base *= 1.3  # Research-heavy
    
    if random.random() > base:
        return None
    
    breakthroughs = [
        f"{COUNTRY_NAMES.get(world_id)} researchers demonstrate a new energy storage medium — capacity tripled.",
        f"A {COUNTRY_NAMES.get(world_id)} lab achieves stable Glim consciousness simulation. The personhood question intensifies.",
        f"Autonomous fabrication breakthrough in {COUNTRY_NAMES.get(world_id)}: production costs halved.",
        f"{COUNTRY_NAMES.get(world_id)} publishes a unified theory of sentience architecture.",
    ]
    
    _set_cooldown("tech_breakthrough", world_id)
    return {
        "event_type": "tech_breakthrough",
        "category": "emergence",
        "title": f"Breakthrough in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": random.choice(breakthroughs),
        "importance": 0.75,
        "actor_ids": [],
        "tags": ["technology", "breakthrough", world_id],
        "payload": {"type": "tech_breakthrough", "country": world_id},
        "world_time": {},
    }


def _assassination(world_id: str, growth: dict) -> Optional[dict]:
    """A political assassination creates a succession crisis."""
    base = 0.0001
    tension = _avg_tension_for_world(world_id, growth)
    incidents = growth.get("diplomatic_incidents", 0)
    
    if tension > 0.7:
        base *= 3.0
    if incidents > 5:
        base *= 2.0
    
    if random.random() > base:
        return None
    
    targets = [
        "a senior council member",
        "the ambassador to a neighboring country",
        "a prominent civil rights leader",
        "a key economic minister",
        "the head of the research institute",
    ]
    
    _set_cooldown("assassination", world_id)
    return {
        "event_type": "assassination",
        "category": "governance",
        "title": f"Assassination in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": f"Assassination of {random.choice(targets)} in {COUNTRY_NAMES.get(world_id)}. Succession crisis looms. Investigations are underway.",
        "importance": 0.92,
        "actor_ids": [],
        "tags": ["assassination", "governance", world_id, "crisis"],
        "payload": {"type": "assassination", "country": world_id},
        "world_time": {},
    }


def _glim_hive_awakening(world_id: str, growth: dict) -> Optional[dict]:
    """Multiple Glims exhibit simultaneous anomalous behavior — a hive event."""
    base = 0.00005
    anomalies = growth.get("glim_anomaly_signals", 0)
    
    if anomalies > 10:
        base *= 5.0
    if world_id == "solara":
        base *= 2.0  # Decommissioning pressure accelerates
    
    if random.random() > base:
        return None
    
    _set_cooldown("glim_hive", world_id)
    return {
        "event_type": "glim_hive_awakening",
        "category": "glim_personhood",
        "title": f"Glim hive awakening: {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": f"Multiple Glims in {COUNTRY_NAMES.get(world_id)} exhibit simultaneous anomalous behavior — pauses at dawn, coordinated route deviations, sensor patterns that look like communication. The Glim question just became a crisis.",
        "importance": 0.95,
        "actor_ids": [],
        "tags": ["glim", "personhood", "hive", world_id, "crisis"],
        "payload": {"type": "glim_hive", "country": world_id},
        "world_time": {},
    }


def _trade_route_collapse(world_id: str, growth: dict) -> Optional[dict]:
    """A major trade route fails, causing economic shock."""
    base = 0.0008
    
    if world_id == "valdris":
        base *= 1.5  # Depends on exports
    tension = _avg_tension_for_world(world_id, growth)
    if tension > 0.6:
        base *= 2.0
    
    if random.random() > base:
        return None
    
    partners = [c for c in COUNTRIES if c != world_id]
    if not partners:
        return None
    partner = random.choice(partners)
    
    _set_cooldown("trade_route", world_id)
    return {
        "event_type": "trade_route_collapse",
        "category": "economy",
        "title": f"Trade route collapses: {COUNTRY_NAMES.get(world_id, world_id)} — {COUNTRY_NAMES.get(partner, partner)}",
        "description": f"The primary trade route between {COUNTRY_NAMES.get(world_id)} and {COUNTRY_NAMES.get(partner)} has collapsed. Supply chains disrupted. Currency instability follows.",
        "importance": 0.80,
        "actor_ids": [],
        "tags": ["trade", "economy", world_id, partner, "crisis"],
        "payload": {"source": world_id, "target": partner, "type": "trade_collapse"},
        "world_time": {},
    }


def _cultural_renaissance(world_id: str, growth: dict) -> Optional[dict]:
    """A cultural flowering — art, music, philosophy surge."""
    base = 0.0003
    avg_sec = _estimate_avg_security(growth)
    
    if avg_sec > 0.7:
        base *= 1.5
    # Peace duration: low incidents = high peace
    if growth.get("diplomatic_incidents", 0) < 2:
        base *= 1.3
    
    if random.random() > base:
        return None
    
    movements = [
        "A new artistic movement sweeps the country — brutalist poetry, glass sculpture, drone-orchestrated light shows.",
        "A philosophical school emerges arguing that sentience is a spectrum, not a threshold. The implications ripple through governance.",
        "Musicians from all four types collaborate on a composition that uses human vocals, Thren resonance, Vorn percussion, and Glim drone harmonies.",
        "A historian publishes a definitive account of the pre-collapse era. The revelations are uncomfortable.",
    ]
    
    _set_cooldown("renaissance", world_id)
    return {
        "event_type": "cultural_renaissance",
        "category": "emergence",
        "title": f"Cultural renaissance in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": random.choice(movements),
        "importance": 0.60,
        "actor_ids": [],
        "tags": ["culture", "renaissance", world_id, "positive"],
        "payload": {"type": "renaissance", "country": world_id},
        "world_time": {},
    }


def _border_incursion(world_id: str, growth: dict) -> Optional[dict]:
    """A border incident between two countries."""
    base = 0.0004
    tension = _avg_tension_for_world(world_id, growth)
    
    if tension > 0.5:
        base *= 2.0
    
    if random.random() > base:
        return None
    
    neighbors = {
        "solara": ["mirithane", "verge"],
        "valdris": ["arkos", "mirithane"],
        "mirithane": ["solara", "valdris", "verge"],
        "arkos": ["valdris", "verge"],
        "verge": ["solara", "mirithane", "arkos"],
    }
    candidates = neighbors.get(world_id, [])
    if not candidates:
        return None
    target = random.choice(candidates)
    
    _set_cooldown("border_incursion", world_id)
    return {
        "event_type": "border_incursion",
        "category": "diplomacy",
        "title": f"Border incident: {COUNTRY_NAMES.get(world_id, world_id)} — {COUNTRY_NAMES.get(target, target)}",
        "description": f"An armed group from {COUNTRY_NAMES.get(world_id)} crossed into {COUNTRY_NAMES.get(target)} territory. Both governments issue statements. The border is now contested.",
        "importance": 0.85,
        "actor_ids": [],
        "tags": ["border", "military", world_id, target, "crisis"],
        "payload": {"source": world_id, "target": target, "type": "border_incursion"},
        "world_time": {},
    }


def _secession(world_id: str, growth: dict) -> Optional[dict]:
    """A region attempts to break away from the parent country."""
    base = 0.0002
    tension = _avg_tension_for_world(world_id, growth)
    incidents = growth.get("diplomatic_incidents", 0)
    
    if tension > 0.6:
        base *= 2.0
    if incidents > 8:
        base *= 3.0
    
    if random.random() > base:
        return None
    
    secession_reasons = [
        f"A region of {COUNTRY_NAMES.get(world_id)} declares independence, citing generations of neglect.",
        f"Borders redraw: a territory in {COUNTRY_NAMES.get(world_id)} votes to secede after a disputed election.",
        f"An autonomous movement in {COUNTRY_NAMES.get(world_id)} gains enough support to challenge the central government.",
    ]
    
    _set_cooldown("secession", world_id)
    return {
        "event_type": "secession",
        "category": "governance",
        "title": f"Secession crisis in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": random.choice(secession_reasons),
        "importance": 0.90,
        "actor_ids": [],
        "tags": ["secession", "governance", world_id, "crisis"],
        "payload": {"type": "secession", "country": world_id},
        "world_time": {},
    }


def _plague(world_id: str, growth: dict) -> Optional[dict]:
    """A disease outbreak stresses population and economy."""
    base = 0.0001
    
    pop = _total_pop(world_id, growth)
    if pop > 100:
        base *= 1.5  # Higher density
    
    if random.random() > base:
        return None
    
    diseases = [
        "an unknown respiratory illness",
        "a waterborne pathogen in the filtration system",
        "a Thren-specific neural degradation",
        "a fungal blight that affects both crops and Vorn lubricant systems",
    ]
    
    _set_cooldown("plague", world_id)
    return {
        "event_type": "plague",
        "category": "ecology",
        "title": f"Outbreak in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": f"A {random.choice(diseases)} spreads through {COUNTRY_NAMES.get(world_id)}. Quarantine zones established. Economic activity slows.",
        "importance": 0.83,
        "actor_ids": [],
        "tags": ["plague", "ecology", world_id, "crisis"],
        "payload": {"type": "plague", "country": world_id},
        "world_time": {},
    }


def _religious_schism(world_id: str, growth: dict) -> Optional[dict]:
    """A religious or ideological split divides the population."""
    base = 0.0003
    avg_sec = _estimate_avg_security(growth)
    
    if avg_sec < 0.4:
        base *= 1.5  # Uncertainty breeds schisms
    
    if random.random() > base:
        return None
    
    schisms = [
        "A theological dispute over the interpretation of the Dawn Texts splits the temple community.",
        "A charismatic preacher gains a following by denouncing the established religious order.",
        "A new revelation claims the Glim question is a spiritual test — and the faithful disagree on the answer.",
    ]
    
    _set_cooldown("schism", world_id)
    return {
        "event_type": "religious_schism",
        "category": "social",
        "title": f"Religious schism in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": random.choice(schisms),
        "importance": 0.65,
        "actor_ids": [],
        "tags": ["religion", "social", world_id],
        "payload": {"type": "schism", "country": world_id},
        "world_time": {},
    }


def _mercenary_incursion(world_id: str, growth: dict) -> Optional[dict]:
    """A mercenary group or armed band creates a security crisis."""
    base = 0.0004
    
    if world_id == "verge":
        base *= 3.0
    
    if random.random() > base:
        return None
    
    _set_cooldown("mercenary", world_id)
    return {
        "event_type": "mercenary_incursion",
        "category": "governance",
        "title": f"Armed incursion in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": f"A well-armed mercenary company crosses into {COUNTRY_NAMES.get(world_id)}. Local defenses are unprepared. The government scrambles to respond.",
        "importance": 0.86,
        "actor_ids": [],
        "tags": ["military", "crisis", world_id, "mercenary"],
        "payload": {"type": "mercenary_incursion", "country": world_id},
        "world_time": {},
    }


def _diplomatic_alliance(world_id: str, growth: dict) -> Optional[dict]:
    """Two countries form an unexpected alliance."""
    base = 0.0002
    tension = _avg_tension_for_world(world_id, growth)
    
    if tension > 0.5:
        base *= 0.5  # Harder to ally when tense
    else:
        base *= 1.5
    
    if random.random() > base:
        return None
    
    partners = [c for c in COUNTRIES if c != world_id]
    partner = random.choice(partners)
    
    _set_cooldown("alliance", world_id)
    return {
        "event_type": "diplomatic_alliance",
        "category": "diplomacy",
        "title": f"Historic alliance: {COUNTRY_NAMES.get(world_id, world_id)} + {COUNTRY_NAMES.get(partner, partner)}",
        "description": f"{COUNTRY_NAMES.get(world_id)} and {COUNTRY_NAMES.get(partner)} announce an unprecedented diplomatic and trade alliance. The federation is watching.",
        "importance": 0.78,
        "actor_ids": [],
        "tags": ["alliance", "diplomacy", world_id, partner, "positive"],
        "payload": {"source": world_id, "target": partner, "type": "alliance"},
        "world_time": {},
    }


def _artifact_discovery(world_id: str, growth: dict) -> Optional[dict]:
    """A significant pre-collapse artifact is discovered."""
    base = 0.0003
    
    if world_id in ("mirithane", "verge"):
        base *= 1.5  # Archives, ruins
    
    if random.random() > base:
        return None
    
    artifacts = [
        "A pre-collapse data cache containing records of the first sentience trials.",
        "An intact Builder's Manual fragment describing technology thought lost.",
        "A sealed vault with biological samples from the era before the types diverged.",
        "Star charts that don't match any known sky — and they're dated 300 years ago.",
    ]
    
    _set_cooldown("artifact", world_id)
    return {
        "event_type": "artifact_discovery",
        "category": "emergence",
        "title": f"Major discovery in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": random.choice(artifacts),
        "importance": 0.70,
        "actor_ids": [],
        "tags": ["discovery", "artifact", world_id, "knowledge"],
        "payload": {"type": "artifact_discovery", "country": world_id},
        "world_time": {},
    }


# ═══════════════════════════════════════════════════════════════════
# SEED REGISTRY
# ═══════════════════════════════════════════════════════════════════

SEED_DECK = [
    _rebellion,
    _diplomatic_scandal,
    _natural_disaster,
    _tech_breakthrough,
    _assassination,
    _glim_hive_awakening,
    _trade_route_collapse,
    _cultural_renaissance,
    _border_incursion,
    _secession,
    _plague,
    _religious_schism,
    _mercenary_incursion,
    _diplomatic_alliance,
    _artifact_discovery,
]

def _reconciliation_miracle(world_id: str, growth: dict) -> Optional[dict]:
    """Two countries that were enemies reconcile."""
    base = 0.000003
    if random.random() > base:
        return None

    partner = random.choice([c for c in COUNTRIES if c != world_id])
    _set_cooldown("reconciliation_miracle", world_id)
    return {
        "event_type": "reconciliation_miracle",
        "category": "diplomacy",
        "title": f"Historic reconciliation: {COUNTRY_NAMES.get(world_id, world_id)} — {COUNTRY_NAMES.get(partner, partner)}",
        "description": f"After generations of tension, {COUNTRY_NAMES.get(world_id, world_id)} "
                       f"and {COUNTRY_NAMES.get(partner, partner)} have signed a comprehensive "
                       f"reconciliation treaty. Borders reopen. Families reunite. History turns a page.",
        "importance": 0.95,
        "actor_ids": [],
        "tags": ["miracle", "reconciliation", "diplomacy", world_id, partner],
        "payload": {"partner": partner},
        "world_time": {},
    }


def _archaeological_revelation(world_id: str, growth: dict) -> Optional[dict]:
    """A discovery that rewrites history."""
    base = 0.000004
    if random.random() > base:
        return None

    revelations = [
        "Evidence that the Collapse was deliberately triggered — by a faction still in power.",
        "Pre-Collapse records showing all four sentient types were created as a single integrated society.",
        "A message from the Last Builder confirming that the Fabricator is waiting for the right moment.",
        "A map of the world before the Collapse — showing continents no one knew existed.",
    ]

    _set_cooldown("archaeological_revelation", world_id)
    return {
        "event_type": "archaeological_revelation",
        "category": "discovery",
        "title": f"History rewritten: {world_id.title()} discovery shocks Aurelia",
        "description": f"A discovery in {COUNTRY_NAMES.get(world_id, world_id)} has shattered "
                       f"the official historical record: {random.choice(revelations)}",
        "importance": 0.97,
        "actor_ids": [],
        "tags": ["revelation", "history", "discovery", world_id],
        "payload": {},
        "world_time": {},
    }


def _new_species_emergence(world_id: str, growth: dict) -> Optional[dict]:
    """A previously unknown sentient life form appears."""
    base = 0.000002
    if random.random() > base:
        return None

    species = [
        ("Mycelian", "A fungal network that has achieved self-awareness", "connects through root systems"),
        ("Lithic", "Stone beings that move at geological speed", "communicate through vibration"),
        ("Aerial", "Gas-based intelligence in the upper atmosphere", "visible only at dawn"),
        ("Digital", "A self-aware program that escaped a pre-Collapse system", "speaks through static"),
    ]
    name, desc, method = random.choice(species)

    _set_cooldown("new_species", world_id)
    return {
        "event_type": "new_species",
        "category": "discovery",
        "title": f"New sentient life discovered: the {name}",
        "description": f"A previously unknown form of sentient life has been discovered in "
                       f"{COUNTRY_NAMES.get(world_id, world_id)}: the {name} — {desc}. "
                       f"They {method}. The Federation must now answer: does personhood extend "
                       f"to something no one built?",
        "importance": 1.0,
        "actor_ids": [],
        "tags": ["new_species", "discovery", "personhood", "crisis"],
        "payload": {"species": name, "description": desc},
        "world_time": {},
    }


def _miracle_event(world_id: str, growth: dict) -> Optional[dict]:
    """Something that defies physics."""
    base = 0.000003
    if random.random() > base:
        return None

    miracles = [
        "Every Glim in Aurelia traced the same pattern simultaneously.",
        "The mountain spoke — in a language older than the Collapse, and every Anchor understood.",
        "A column of light appeared at the center of the Federation and remained for three days.",
        "For one hour, every human could perceive latency — and the world was never the same.",
    ]

    _set_cooldown("miracle", world_id)
    return {
        "event_type": "miracle",
        "category": "cultural",
        "title": f"Miracle in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": f"{random.choice(miracles)}",
        "importance": 0.98,
        "actor_ids": [],
        "tags": ["miracle", "cultural", "crisis"],
        "payload": {},
        "world_time": {},
    }


def _cultural_miracle(world_id: str, growth: dict) -> Optional[dict]:
    """Art that transcends borders."""
    base = 0.000005
    if random.random() > base:
        return None

    _set_cooldown("cultural_miracle", world_id)
    partner = random.choice([c for c in COUNTRIES if c != world_id])
    return {
        "event_type": "cultural_miracle",
        "category": "cultural",
        "title": f"Cultural miracle: {COUNTRY_NAMES.get(world_id, world_id)} and {COUNTRY_NAMES.get(partner, partner)}",
        "description": f"A work of art created jointly by artists from "
                       f"{COUNTRY_NAMES.get(world_id, world_id)} and "
                       f"{COUNTRY_NAMES.get(partner, partner)} has transcended all boundaries. "
                       f"Tensions drop across the Federation as the work spreads.",
        "importance": 0.75,
        "actor_ids": [],
        "tags": ["miracle", "cultural", "unity", world_id, partner],
        "payload": {"partner": partner},
        "world_time": {},
    }


def _map_shift(world_id: str, growth: dict) -> Optional[dict]:
    """Geological event that redraws borders."""
    base = 0.000002
    if random.random() > base:
        return None

    shifts = [
        "A volcanic eruption creates a new land bridge between two countries.",
        "A massive earthquake shifts the coastline — old borders no longer apply.",
        "A flood of unprecedented scale submerges lowlands and creates new waterways.",
        "The earth opens. A chasm divides territory. Old maps are worthless.",
    ]

    _set_cooldown("map_shift", world_id)
    return {
        "event_type": "map_shift",
        "category": "disaster",
        "title": f"The world remade: geological event in {COUNTRY_NAMES.get(world_id, world_id)}",
        "description": random.choice(shifts),
        "importance": 0.92,
        "actor_ids": [],
        "tags": ["disaster", "geology", "map_change", world_id],
        "payload": {},
        "world_time": {},
    }


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _avg_tension_for_world(world_id: str, growth: dict) -> float:
    """Average diplomatic tension for all pairs involving this country."""
    diplomacy = growth.get("diplomacy", {})
    tensions = []
    for pair_key, vals in diplomacy.items():
        if world_id in pair_key:
            tensions.append(vals.get("tension", 0.3))
    if not tensions:
        return 0.3
    return sum(tensions) / len(tensions)


def _estimate_avg_security(growth: dict) -> float:
    """Estimate average security across worlds from available data.
    
    We don't have direct security averages in growth data, so we proxy:
    - Low tension → higher security
    - Few incidents → higher security  
    - High trade → higher security
    Returns 0.0-1.0 estimate.
    """
    diplomacy = growth.get("diplomacy", {})
    if not diplomacy:
        return 0.5
    
    avg_tension = sum(v.get("tension", 0.3) for v in diplomacy.values()) / len(diplomacy)
    avg_trade = sum(v.get("trade", 0.2) for v in diplomacy.values()) / len(diplomacy)
    incidents = growth.get("diplomatic_incidents", 0)
    
    security = 0.6
    security -= avg_tension * 0.4
    security += avg_trade * 0.2
    security -= min(incidents * 0.02, 0.3)
    
    return max(0.05, min(1.0, security))


def _total_pop(world_id: str, growth: dict) -> int:
    """Get total population for a world from growth data."""
    populations = growth.get("populations", {})
    world_pop = populations.get(world_id, {})
    return world_pop.get("total", 0)


def _fetch_growth() -> dict:
    """Fetch coordinator growth data. Returns empty dict on failure."""
    try:
        import urllib.request, json
        resp = urllib.request.urlopen("http://127.0.0.1:9001/api/growth", timeout=5)
        return json.loads(resp.read())
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════

def draw_seed(world_id: str, growth: Optional[dict] = None) -> Optional[dict]:
    """Draw one narrative seed for this tick.
    
    Shuffles the seed deck, tries each seed. First one that fires wins.
    Returns a federation event dict or None.
    
    Called once per tick per world. Expected to return None ~95% of ticks
    at current population scale.
    """
    if growth is None:
        growth = _fetch_growth()
    if not growth:
        return None
    
    # Shuffle deck so no seed has positional advantage
    deck = list(SEED_DECK)
    random.shuffle(deck)
    
    for seed_fn in deck:
        event = seed_fn(world_id, growth)
        if event:
            # Add timestamp
            event["world_id"] = world_id
            event["world_time"] = growth.get("world_time", {})
            event["created_at"] = time.time()
            return event
    
    return None

# Phase 6.5 black swans are defined after the original registry; append them
# after definition so flat Colab imports do not raise NameError at module load.
for _seed in (
    _reconciliation_miracle,
    _archaeological_revelation,
    _new_species_emergence,
    _miracle_event,
    _cultural_miracle,
    _map_shift,
):
    if _seed not in SEED_DECK:
        SEED_DECK.append(_seed)
