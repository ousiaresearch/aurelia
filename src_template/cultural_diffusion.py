"""cultural_diffusion.py — cultural learning and technology diffusion across worlds."""
from __future__ import annotations

import json
import random
import time
import uuid

try:
    from . import causal_ledger, institutions
except Exception:
    import causal_ledger
    import institutions

CULTURAL_TRAITS = [
    "openness_to_trade",
    "institutional_memory",
    "xenophobia",
    "innovation_culture",
    "governance_norms",
]

DEFAULT_TRAITS = {
    "openness_to_trade": 0.5,
    "institutional_memory": 0.5,
    "xenophobia": 0.5,
    "innovation_culture": 0.2,
    "governance_norms": 0.5,
}

BORDERS = {
    "solara": ["valdris", "arkos"],
    "valdris": ["solara", "mirithane", "verge"],
    "mirithane": ["valdris", "arkos"],
    "arkos": ["solara", "mirithane", "verge"],
    "verge": ["valdris", "arkos"],
}


def ensure_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS cultural_traits (
            world_id TEXT NOT NULL,
            trait TEXT NOT NULL,
            value REAL NOT NULL DEFAULT 0.5,
            source_world TEXT,
            adopted_tick INTEGER,
            PRIMARY KEY (world_id, trait)
        );
        CREATE TABLE IF NOT EXISTS diffusion_events (
            event_id TEXT PRIMARY KEY,
            tick_number INTEGER NOT NULL,
            source_world TEXT NOT NULL,
            target_world TEXT NOT NULL,
            trait TEXT NOT NULL,
            adoption_strength REAL NOT NULL,
            resisted INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL
        );
    """)


def ensure_borders(db, world_a: str, world_b: str) -> None:
    """Ensure two worlds are considered bordering for diffusion."""
    if world_a not in BORDERS:
        BORDERS[world_a] = []
    if world_b not in BORDERS[world_a]:
        BORDERS[world_a].append(world_b)
    if world_b not in BORDERS:
        BORDERS[world_b] = []
    if world_a not in BORDERS[world_b]:
        BORDERS[world_b].append(world_a)


def seed_traits(db, world_id: str, traits: dict[str, float] | None = None) -> None:
    """Insert initial trait values for a world."""
    ensure_schema(db)
    now = time.time()
    vals = dict(DEFAULT_TRAITS)
    if traits:
        vals.update(traits)
    for trait, value in vals.items():
        db.execute(
            "INSERT OR IGNORE INTO cultural_traits (world_id, trait, value, source_world, adopted_tick) VALUES (?, ?, ?, NULL, 0)",
            (world_id, trait, value),
        )


def trait_value(db, world_id: str, trait: str) -> float:
    """Get a world's current trait value."""
    ensure_schema(db)
    row = db.execute(
        "SELECT value FROM cultural_traits WHERE world_id=? AND trait=?",
        (world_id, trait),
    ).fetchone()
    if not row:
        seed_traits(db, world_id)
        return DEFAULT_TRAITS.get(trait, 0.5)
    return float(row["value"])


def cultural_distance(db, world_a: str, world_b: str) -> float:
    """Compute cultural distance between two worlds."""
    dist = 0.0
    for trait in CULTURAL_TRAITS:
        va = trait_value(db, world_a, trait)
        vb = trait_value(db, world_b, trait)
        dist += abs(va - vb)
    return dist / len(CULTURAL_TRAITS)


def _diffuse_one_trait(db, *, source_world: str, target_world: str,
                       trait: str, tick_number: int) -> bool:
    sv = trait_value(db, source_world, trait)
    tv = trait_value(db, target_world, trait)
    diff = abs(sv - tv)
    if diff < 0.12:
        return False  # Too similar, no diffusion pressure

    xenophobia = trait_value(db, target_world, "xenophobia")
    gov_norms = trait_value(db, source_world, "governance_norms")
    openness = trait_value(db, source_world, "openness_to_trade")
    adoption_strength = min(1.0, gov_norms * 0.30 + openness * 0.20 + (1.0 - xenophobia) * 0.25)
    resistance = xenophobia * 0.35 + (1.0 - trait_value(db, target_world, "institutional_memory")) * 0.10

    if adoption_strength > resistance:
        # Adopt — shift target toward source
        shift = adoption_strength * 0.02
        new_value = tv + (sv - tv) * shift
        new_value = max(0.0, min(1.0, new_value))
        db.execute(
            "INSERT OR REPLACE INTO cultural_traits (world_id, trait, value, source_world, adopted_tick) VALUES (?, ?, ?, ?, ?)",
            (target_world, trait, new_value, source_world, tick_number),
        )
        causal_ledger.emit_event(
            db, tick_number=tick_number, world_id=target_world, layer="federation",
            event_type="cultural_trait_adopted", scope="federation",
            actor_ids=[source_world], target_ids=[target_world],
            magnitude=shift, valence=shift,
            payload={"trait": trait, "from": sv, "to": new_value, "source": source_world},
        )
        return True
    else:
        causal_ledger.emit_event(
            db, tick_number=tick_number, world_id=target_world, layer="federation",
            event_type="cultural_trait_resisted", scope="federation",
            actor_ids=[source_world], target_ids=[target_world],
            magnitude=adoption_strength, valence=-0.1,
            payload={"trait": trait, "resistance": resistance, "source": source_world},
        )
        return False


def _diffuse_institution(db, *, source_world: str, target_world: str, tick_number: int) -> bool:
    """Copy an institution from source to target if conditions allow."""
    try:
        row = db.execute(
            "SELECT * FROM institutions WHERE world_id=? AND status='active' AND durability > 0.3 ORDER BY influence DESC LIMIT 1",
            (source_world,),
        ).fetchone()
    except Exception:
        return False
    if not row:
        return False

    gov_norms = trait_value(db, target_world, "governance_norms")
    xenophobia = trait_value(db, target_world, "xenophobia")
    if gov_norms * 0.4 + (1.0 - xenophobia) * 0.3 < 0.35:
        return False

    inst_id = f"{target_world}:institution:{row['type']}:diff:{tick_number}:{uuid.uuid4().hex[:6]}"
    now = time.time()
    db.execute(
        """
        INSERT OR REPLACE INTO institutions
            (institution_id, world_id, name, type, founded_tick, founding_faction_id,
             influence, durability, benefits, status, created_at)
        VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, 'active', ?)
        """,
        (inst_id, target_world, row["name"] + " (Adopted)", row["type"], tick_number,
         0.15, 0.35, row["benefits"], now),
    )
    causal_ledger.emit_event(
        db, tick_number=tick_number, world_id=target_world, layer="federation",
        event_type="institution_diffused", scope="federation",
        actor_ids=[source_world], target_ids=[target_world],
        magnitude=0.4, valence=0.3,
        payload={"institution_type": row["type"], "source_world": source_world},
    )
    return True


def apply_diffusion_tick(db, *, worlds: list[str], tick_number: int) -> dict:
    """Run one tick of cultural diffusion across the federation."""
    ensure_schema(db)
    results = {"adopted": 0, "resisted": 0, "institutions_diffused": 0}

    # Seed any worlds missing traits
    for world_id in worlds:
        if not db.execute(
            "SELECT COUNT(*) FROM cultural_traits WHERE world_id=?", (world_id,)
        ).fetchone()[0]:
            seed_traits(db, world_id)

    for source in worlds:
        neighbors = BORDERS.get(source, [w for w in worlds if w != source])
        for target in neighbors:
            if target not in worlds or target == source:
                continue
            # Diffuse one random trait per pair per tick
            import random as _random
            trait = _random.choice(CULTURAL_TRAITS)
            if _diffuse_one_trait(db, source_world=source, target_world=target, trait=trait, tick_number=tick_number):
                results["adopted"] += 1
            else:
                results["resisted"] += 1

            # Also attempt institution diffusion (every 4 ticks to be slower)
            if tick_number % 4 == 0:
                if _diffuse_institution(db, source_world=source, target_world=target, tick_number=tick_number):
                    results["institutions_diffused"] += 1

    return results
