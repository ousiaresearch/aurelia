"""discovery.py — Archaeological finds, uncharted regions, lost knowledge, new life.

Phase 6.5 Module 2: The world grows from within. Not just fragmentation —
discovery of ruins, technology, unexplored territory, and new forms of existence.
"""

import json
import time
import random
from typing import Optional, Dict, Any, List

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]
COUNTRY_NAMES = {
    "solara": "Solara", "valdris": "Valdris", "mirithane": "Mirithane",
    "arkos": "Arkos", "verge": "The Verge",
}

# Discovery probabilities (per tick per country)
DISCOVERY_BASE_PROBS = {
    "archaeological_find": 0.0005,
    "uncharted_region": 0.0002,
    "lost_knowledge": 0.0003,
    "fabricator_activation": 0.00005,  # Extremely rare
}

# Country modifiers
COUNTRY_DISCOVERY_MODIFIERS = {
    "verge": 1.5,     # Salvage culture — more ruins dug up
    "mirithane": 1.3,  # Archive proximity — more lost knowledge
    "valdris": 1.2,    # Deep mining — more archaeological finds
    "solara": 0.9,     # Covers up what it finds
    "arkos": 1.1,      # Sand-glass towers reveal patterns
}


# ═══════════════════════════════════════════════════════════════════
# 1. ARCHAEOLOGICAL DISCOVERY
# ═══════════════════════════════════════════════════════════════════

_ARCHAEOLOGY_POOL = [
    {
        "type": "technology",
        "title": "Pre-Collapse Energy Cell",
        "description": "A dormant energy storage device from before the Collapse has been found. "
                       "Its capacity dwarfs anything currently in use. Scientists are analyzing it.",
        "effects": {"economic_boost": 0.1, "prestige": 0.05},
    },
    {
        "type": "technology",
        "title": "Void-Resonance Transmitter",
        "description": "A pre-Collapse communication device that operates through latency fields. "
                       "It may be able to send messages without physical infrastructure.",
        "effects": {"diplomatic_boost": 0.08, "latency_knowledge": 0.1},
    },
    {
        "type": "history",
        "title": "The Origin Blueprints",
        "description": "Architectural plans from the era before the Collapse reveal that Threns "
                       "were designed for a purpose beyond labor — they were built to interface with "
                       "something. The blueprints don't say what.",
        "effects": {"thren_policy_shift": 0.2, "federation_tension": 0.1},
    },
    {
        "type": "history",
        "title": "The Vorn Creation Logs",
        "description": "Pre-Collapse manufacturing records show the first Vorn was not built — it was "
                       "grown. A biological core was seeded with mechanical architecture. The implications "
                       "for Vorn identity are seismic.",
        "effects": {"vorn_policy_shift": 0.2, "arkos_crisis": 0.15},
    },
    {
        "type": "artifact",
        "title": "The Memory Shard",
        "description": "A crystalline fragment that resonates with latency energy. When held, it "
                       "projects memories that are not the holder's — vivid, detailed, and possibly "
                       "from before the Collapse.",
        "effects": {"latency_knowledge": 0.15, "artifact_value": 0.3},
    },
    {
        "type": "artifact",
        "title": "The Cartographer's Lens",
        "description": "A pre-Collapse optical device that reveals hidden structures — it shows "
                       "the outlines of buried cities, underground passages, and submerged ruins "
                       "that no one knew existed.",
        "effects": {"map_expansion": 0.2, "exploration_boost": 0.1},
    },
    {
        "type": "ruin",
        "title": "The Sunken City of Thal-Mareth",
        "description": "An entire pre-Collapse city has been discovered beneath the coastal shelf. "
                       "Its structures are intact — preserved by water and latency fields. "
                       "It may be habitable.",
        "effects": {"new_region": True, "population_capacity": 0.15},
    },
    {
        "type": "ruin",
        "title": "The Deep Archive",
        "description": "A sealed pre-Collapse archive has been found in the mountains. Its door "
                       "responds to latency. Inside: centuries of records, possibly including "
                       "what caused the Collapse.",
        "effects": {"collapse_knowledge": 0.3, "federation_crisis": 0.2},
    },
]


def check_archaeological_find(
    db, world_id: str, tick_number: int
) -> Optional[Dict[str, Any]]:
    """A pre-Collapse structure, artifact, or record is discovered."""
    base_prob = DISCOVERY_BASE_PROBS["archaeological_find"]
    modifier = COUNTRY_DISCOVERY_MODIFIERS.get(world_id, 1.0)
    prob = base_prob * modifier

    if random.random() > prob:
        return None

    discovery = random.choice(_ARCHAEOLOGY_POOL)
    discovery_id = f"arch:{world_id}:{tick_number}:{int(time.time())}"
    now = time.time()

    db.execute("""
        INSERT INTO discoveries (discovery_id, world_id, discovery_type, title,
            description, effects, tick_number, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (discovery_id, world_id, discovery["type"], discovery["title"],
          discovery["description"], json.dumps(discovery["effects"]), tick_number, now))
    db.commit()

    return {
        "event_type": "archaeological_find",
        "category": "discovery",
        "title": discovery["title"],
        "description": discovery["description"],
        "importance": 0.85,
        "actor_ids": [],
        "tags": ["discovery", "archaeology", discovery["type"], world_id],
        "payload": {
            "discovery_id": discovery_id,
            "type": discovery["type"],
            "effects": discovery["effects"],
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 2. UNCHARTED REGION
# ═══════════════════════════════════════════════════════════════════

_UNCHARTED_REGIONS = [
    {
        "name": "The Shattered Caldera",
        "description": "A volcanic region previously thought impassable has cooled enough to traverse. "
                       "Geothermal vents, mineral-rich soil, and strange flora adapted to the heat.",
        "features": ["geothermal_energy", "rare_minerals", "unique_flora"],
        "hazard": "volcanic_activity",
    },
    {
        "name": "The Sunken Shelf",
        "description": "Receding waters have exposed an ancient coastal shelf. Tide pools, "
                       "fossil forests, and the remnants of pre-Collapse fishing settlements.",
        "features": ["fossil_fuel", "ancient_artifacts", "new_fisheries"],
        "hazard": "tidal_surge",
    },
    {
        "name": "The Glass Desert",
        "description": "A vast expanse of fused sand — the result of some pre-Collapse event. "
                       "The glass formations refract light into impossible colors. At night, "
                       "the entire desert glows faintly with residual energy.",
        "features": ["latency_field", "energy_harvesting", "unique_ecology"],
        "hazard": "radiation_zones",
    },
    {
        "name": "The Canopy Plateau",
        "description": "An elevated forest where the canopy is so dense it forms a second ground. "
                       "Species found nowhere else. A pre-Collapse observatory sits at the highest point.",
        "features": ["unique_species", "observatory", "isolation"],
        "hazard": "predator_territory",
    },
    {
        "name": "The Deep Warrens",
        "description": "A network of underground passages — natural caves expanded by unknown builders. "
                       "Some passages glow with bioluminescent fungi. Some lead to chambers full of "
                       "inscribed walls in a language no one recognizes.",
        "features": ["underground_network", "unknown_language", "bioluminescence"],
        "hazard": "collapse_risk",
    },
]


def check_uncharted_region(
    db, world_id: str, tick_number: int
) -> Optional[Dict[str, Any]]:
    """New territory becomes accessible."""
    base_prob = DISCOVERY_BASE_PROBS["uncharted_region"]
    modifier = COUNTRY_DISCOVERY_MODIFIERS.get(world_id, 1.0)

    # Higher probability after natural disasters or previous discoveries
    prior_discoveries = db.execute(
        "SELECT COUNT(*) FROM discoveries WHERE world_id = ?", (world_id,)
    ).fetchone()[0]
    if prior_discoveries > 0:
        modifier *= (1.0 + prior_discoveries * 0.1)

    prob = base_prob * modifier

    if random.random() > prob:
        return None

    region = random.choice(_UNCHARTED_REGIONS)
    discovery_id = f"region:{world_id}:{tick_number}:{int(time.time())}"
    now = time.time()

    db.execute("""
        INSERT INTO discoveries (discovery_id, world_id, discovery_type, title,
            description, effects, tick_number, created_at)
        VALUES (?, ?, 'region', ?, ?, ?, ?, ?)
    """, (discovery_id, world_id, region["name"], region["description"],
          json.dumps({"features": region["features"], "hazard": region["hazard"]}),
          tick_number, now))
    db.commit()

    return {
        "event_type": "uncharted_region",
        "category": "discovery",
        "title": f"New region discovered: {region['name']}",
        "description": region["description"],
        "importance": 0.9,
        "actor_ids": [],
        "tags": ["discovery", "region", "exploration", world_id],
        "payload": {
            "discovery_id": discovery_id,
            "region_name": region["name"],
            "features": region["features"],
            "hazard": region["hazard"],
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 3. LOST KNOWLEDGE
# ═══════════════════════════════════════════════════════════════════

_LOST_KNOWLEDGE_POOL = [
    {
        "subtype": "memory_core",
        "title": "Vorn Memory Core from Year Zero",
        "description": "A Vorn memory core dating to the year of the Collapse has been recovered. "
                       "The memories within describe the world before — and the moment it ended. "
                       "The Vorn who lived this is long dissolved, but their Continuation persists in data.",
    },
    {
        "subtype": "archive_fragment",
        "title": "Sealed Archive: The Thirteenth Strain",
        "description": "A sealed section of the Mirithane Archive has been opened. It describes "
                       "a thirteenth strain of latency beyond the twelve known — a strain that was "
                       "sealed away because its practice killed every practitioner within a year.",
    },
    {
        "subtype": "trader_secret",
        "title": "The Memory Trader's Origin",
        "description": "The Memory Trader has revealed — to one person, in one trade — where "
                       "she came from. The memory shows a laboratory. Vorns. Humans. A facility "
                       "that built her to remember everything. She was not born. She was the first archive.",
    },
    {
        "subtype": "cipher_decode",
        "title": "Cipher-Cult Decryption: The Five Frequencies",
        "description": "The Cipher-Cult has decoded five distinct frequency patterns from the "
                       "sand-glass towers. Each frequency corresponds to a different pre-Collapse "
                       "entity. One of them is still transmitting.",
    },
    {
        "subtype": "memory_core",
        "title": "Glim Production Directive",
        "description": "A pre-Collapse manufacturing directive has surfaced. It orders Glim "
                       "production to include a 'latency substrate layer' — a component that "
                       "was officially removed from the design but apparently never discontinued. "
                       "Every Glim ever built carries latent latency capability.",
    },
]


def check_lost_knowledge(
    db, world_id: str, tick_number: int
) -> Optional[Dict[str, Any]]:
    """A document, memory, or artifact surfaces that changes historical understanding."""
    base_prob = DISCOVERY_BASE_PROBS["lost_knowledge"]
    modifier = COUNTRY_DISCOVERY_MODIFIERS.get(world_id, 1.0)

    # Mirithane gets a boost for archive fragments
    if world_id == "mirithane":
        modifier *= 1.4

    prob = base_prob * modifier

    if random.random() > prob:
        return None

    knowledge = random.choice(_LOST_KNOWLEDGE_POOL)
    discovery_id = f"knowledge:{world_id}:{tick_number}:{int(time.time())}"
    now = time.time()

    db.execute("""
        INSERT INTO discoveries (discovery_id, world_id, discovery_type, title,
            description, effects, tick_number, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (discovery_id, world_id, f"knowledge:{knowledge['subtype']}", knowledge["title"],
          knowledge["description"], json.dumps({"subtype": knowledge["subtype"]}),
          tick_number, now))
    db.commit()

    return {
        "event_type": "lost_knowledge",
        "category": "discovery",
        "title": knowledge["title"],
        "description": knowledge["description"],
        "importance": 0.88,
        "actor_ids": [],
        "tags": ["discovery", "knowledge", "lore", world_id],
        "payload": {
            "discovery_id": discovery_id,
            "subtype": knowledge["subtype"],
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 4. FABRICATOR ACTIVATION
# ═══════════════════════════════════════════════════════════════════

_FABRICATOR_EVENTS = [
    {
        "title": "The Fabricator Awakens",
        "description": "The Last Builders' Fabricator — dormant since the Collapse — has activated. "
                       "Its first output is a Type-ε being: not human, not Thren, not Vorn, not Glim. "
                       "Something new. The Fabricator is now online and constructing more.",
        "new_type": "type_epsilon",
    },
    {
        "title": "Fabricator: Emergency Protocol",
        "description": "The Fabricator has entered emergency production mode. It is printing "
                       "preservation drones — machines designed to stabilize failing latency fields. "
                       "Their emergence suggests the Fabricator detected a threat no one else can see.",
        "new_type": "preservation_drone",
    },
]


def check_fabricator_activation(
    db, world_id: str, tick_number: int
) -> Optional[Dict[str, Any]]:
    """The Last Builders' Fabricator activates and creates something new."""
    # Must have at least one prior archaeological find
    prior = db.execute("SELECT COUNT(*) FROM discoveries").fetchone()[0]
    if prior < 1:
        return None

    base_prob = DISCOVERY_BASE_PROBS["fabricator_activation"]
    prob = base_prob

    if random.random() > prob:
        return None

    event = random.choice(_FABRICATOR_EVENTS)
    discovery_id = f"fabricator:{tick_number}:{int(time.time())}"
    now = time.time()

    db.execute("""
        INSERT INTO discoveries (discovery_id, world_id, discovery_type, title,
            description, effects, tick_number, created_at)
        VALUES (?, ?, 'fabricator', ?, ?, ?, ?, ?)
    """, (discovery_id, world_id, event["title"], event["description"],
          json.dumps({"new_type": event["new_type"]}), tick_number, now))
    db.commit()

    return {
        "event_type": "fabricator_activation",
        "category": "discovery",
        "title": event["title"],
        "description": event["description"],
        "importance": 1.0,
        "actor_ids": [],
        "tags": ["discovery", "fabricator", "new_type", event["new_type"], "crisis"],
        "payload": {
            "discovery_id": discovery_id,
            "new_type": event["new_type"],
        },
    }


# ═══════════════════════════════════════════════════════════════════
# TICK INTEGRATION
# ═══════════════════════════════════════════════════════════════════

def check_all_discoveries(
    db, world_id: str, tick_number: int
) -> List[Dict[str, Any]]:
    """Run all discovery checks for a world."""
    events = []

    # Archaeological find
    arch = check_archaeological_find(db, world_id, tick_number)
    if arch:
        events.append(arch)

    # Uncharted region
    region = check_uncharted_region(db, world_id, tick_number)
    if region:
        events.append(region)

    # Lost knowledge
    knowledge = check_lost_knowledge(db, world_id, tick_number)
    if knowledge:
        events.append(knowledge)

    # Fabricator activation
    fabricator = check_fabricator_activation(db, world_id, tick_number)
    if fabricator:
        events.append(fabricator)

    return events


def get_discovery_state(db, world_id: str, limit: int = 5) -> Dict[str, Any]:
    """Return discovery log for dashboard/API."""
    rows = db.execute(
        "SELECT * FROM discoveries WHERE world_id = ? ORDER BY tick_number DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()

    discoveries = []
    for r in rows:
        try:
            effects = json.loads(r["effects"]) if isinstance(r["effects"], str) else r["effects"]
        except (json.JSONDecodeError, TypeError):
            effects = {}
        discoveries.append({
            "type": r["discovery_type"],
            "title": r["title"],
            "description": r["description"][:120],
            "tick": r["tick_number"],
            "effects_keys": list(effects.keys()) if effects else [],
        })

    total = db.execute(
        "SELECT COUNT(*) FROM discoveries WHERE world_id = ?", (world_id,)
    ).fetchone()[0]

    return {
        "recent": discoveries,
        "total": total,
    }
