"""phase10_dynamics.py — runtime causal gap closure for Aurelia Phase 10.

This module deliberately concentrates the Phase 10 missing-cause surface from
`docs/analysis/2026-06-08-aurelia-causal-gaps-deep-dive.md` into one tested
runtime layer. It does not replace the older lore/narrative modules; it gives
those causal categories concrete per-tick state, events, and graph edges.
"""
from __future__ import annotations

import json
import random
import shutil
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

try:
    from . import capital_economy, causal_ledger, macro_dynamics, world_profiles
except Exception:
    import capital_economy
    import causal_ledger
    import macro_dynamics
    import world_profiles


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _loads(raw: Any, default: Any | None = None) -> Any:
    if default is None:
        default = {}
    if raw is None:
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return default


def ensure_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS civilization_metrics (
            world_id TEXT NOT NULL,
            tick_number INTEGER NOT NULL,
            education_level REAL NOT NULL,
            urbanization REAL NOT NULL,
            youth_bulge REAL NOT NULL,
            disease_pressure REAL NOT NULL,
            resource_stock REAL NOT NULL,
            property_rights REAL NOT NULL,
            state_capacity_type TEXT NOT NULL,
            repression_type TEXT NOT NULL,
            conflict_type TEXT NOT NULL,
            path_lock_in REAL NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL,
            PRIMARY KEY(world_id, tick_number)
        );
        CREATE TABLE IF NOT EXISTS counterfactual_events (
            branch_id TEXT NOT NULL,
            tick_number INTEGER NOT NULL,
            world_id TEXT NOT NULL,
            intervention TEXT NOT NULL,
            state TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS civilization_resource_stock (
            world_id TEXT PRIMARY KEY,
            stock REAL NOT NULL DEFAULT 0.75,
            last_tick INTEGER NOT NULL DEFAULT 0,
            updated_at REAL NOT NULL
        );
        """
    )


def ensure_federation_schema(db) -> None:
    causal_ledger.ensure_schema(db)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS cross_world_movements (
            npc_id TEXT NOT NULL,
            source_world TEXT NOT NULL,
            target_world TEXT NOT NULL,
            movement_type TEXT NOT NULL,
            tick_number INTEGER NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_phase10_cross_movements_tick
            ON cross_world_movements(tick_number, source_world, target_world);
        CREATE TABLE IF NOT EXISTS federation_strategy_events (
            event_id TEXT PRIMARY KEY,
            tick_number INTEGER NOT NULL,
            strategy_type TEXT NOT NULL,
            source_world TEXT,
            target_world TEXT,
            payload TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL
        );
        """
    )


def latest_metrics(db, world_id: str) -> dict[str, Any]:
    ensure_schema(db)
    row = db.execute(
        "SELECT * FROM civilization_metrics WHERE world_id=? ORDER BY tick_number DESC LIMIT 1",
        (world_id,),
    ).fetchone()
    if row is None:
        return {
            "world_id": world_id,
            "tick_number": 0,
            "education_level": 0.25,
            "urbanization": 0.25,
            "youth_bulge": 0.5,
            "disease_pressure": 0.1,
            "resource_stock": 0.75,
            "property_rights": 0.45,
            "state_capacity_type": "patrimonial",
            "repression_type": "none",
            "conflict_type": "latent",
            "path_lock_in": 0.0,
            "payload": {},
        }
    out = dict(row)
    out["payload"] = _loads(out.get("payload"), {})
    return out


def _agent_demographics(db) -> dict[str, float]:
    rows = db.execute(
        "SELECT id, properties FROM agents WHERE type='npc' AND state='active' LIMIT 5000"
    ).fetchall()
    if not rows:
        return {"education": 0.25, "urban": 0.25, "youth_bulge": 0.0, "population": 0}
    education = []
    urban = 0
    young_male = 0
    prime_male = 0
    for idx, row in enumerate(rows):
        props = _loads(row["properties"], {})
        # Most seeded Aurelia NPCs predate Phase 10 and lack explicit age/sex/
        # urban fields. Use stable deterministic cohorts from row order instead
        # of treating everyone as age-28/sex-unknown, otherwise youth bulge and
        # urbanization stay falsely zero.
        age = int(props.get("age", props.get("approx_age", 16 + (idx % 55))) or (16 + (idx % 55)))
        sex = props.get("sex", props.get("gender", "male" if idx % 2 == 0 else "female"))
        default_education = 0.20 + (idx % 8) * 0.035
        education.append(float(props.get("education", props.get("literacy", default_education)) or default_education))
        default_urban = idx % 4 == 0
        if props.get("urban", default_urban) or props.get("settlement_type") == "urban":
            urban += 1
        if sex == "male" and 15 <= age <= 30:
            young_male += 1
        if sex == "male" and 31 <= age <= 50:
            prime_male += 1
    return {
        "education": _clamp(sum(education) / max(1, len(education))),
        "urban": _clamp(urban / max(1, len(rows))),
        "youth_bulge": _clamp(young_male / max(1, prime_male)),
        "population": float(len(rows)),
    }


def _resource_stock(db, world_id: str, tick_number: int, state: dict[str, float], rng: random.Random) -> tuple[float, float]:
    ensure_schema(db)
    row = db.execute("SELECT stock, last_tick FROM civilization_resource_stock WHERE world_id=?", (world_id,)).fetchone()
    if row is None:
        profile = world_profiles.profile(world_id)
        base = float(profile.get("macro_baseline", {}).get("water_security", 0.6)) * 0.6 + 0.25
        stock = _clamp(base)
        last_tick = 0
    else:
        stock = float(row["stock"])
        last_tick = int(row["last_tick"])
    elapsed = max(1, int(tick_number) - last_tick)
    depletion = elapsed * (0.0015 + state.get("gdp_proxy", 0.5) * 0.001 + state.get("war_pressure", 0) * 0.0015)
    climate_shock = rng.random() * 0.006
    regeneration = elapsed * (state.get("infrastructure", 0.6) * 0.0008 + (1.0 - state.get("repression", 0.3)) * 0.0004)
    new_stock = _clamp(stock - depletion - climate_shock + regeneration)
    db.execute(
        "INSERT OR REPLACE INTO civilization_resource_stock (world_id, stock, last_tick, updated_at) VALUES (?, ?, ?, ?)",
        (world_id, new_stock, int(tick_number), time.time()),
    )
    return new_stock, stock - new_stock


def _classify_state_capacity(state: dict[str, float], education: float) -> str:
    fiscal = state.get("fiscal_capacity", 0.5)
    legitimacy = state.get("legitimacy", 0.5)
    repression = state.get("repression", 0.3)
    if fiscal > 0.62 and legitimacy > 0.58 and education > 0.42:
        return "developmental"
    if fiscal > 0.50 and legitimacy > 0.42 and repression < 0.50:
        return "bureaucratic"
    if repression > 0.65 or legitimacy < 0.20:
        return "prebendal"
    return "patrimonial"


def _classify_repression(state: dict[str, float], rng: random.Random) -> str:
    r = state.get("repression", 0.3)
    if r < 0.18:
        return "none"
    if r > 0.72:
        return "violent"
    if r > 0.52:
        return "surveillance" if rng.random() < 0.55 else "legal"
    if r > 0.32:
        return "propaganda" if rng.random() < 0.45 else "legal"
    return "propaganda"


def _classify_conflict(state: dict[str, float], youth_bulge: float) -> str:
    war = state.get("war_pressure", 0.0)
    tension = state.get("type_tension", 0.3)
    if war > 0.80:
        return "civil_war"
    if war > 0.55 and youth_bulge > 0.75:
        return "insurgency"
    if war > 0.38 and tension > 0.55:
        return "terrorism"
    if state.get("border_openness", 0.5) < 0.18 and war > 0.35:
        return "interstate_war"
    return "latent"


def _active_institution_lock_in(db, tick_number: int) -> float:
    try:
        rows = db.execute("SELECT founded_tick, durability FROM institutions WHERE status='active'").fetchall()
    except Exception:
        return 0.0
    if not rows:
        return 0.0
    ages = [max(0, int(tick_number) - int(r["founded_tick"] or 0)) / 80.0 + float(r["durability"] or 0.0) for r in rows]
    return _clamp(sum(ages) / len(ages))


def _write_macro_state(db, world_id: str, tick_number: int, state: dict[str, float]) -> None:
    macro_dynamics.ensure_schema(db)
    db.execute(
        "INSERT OR REPLACE INTO macro_state (world_id, tick_number, state, created_at) VALUES (?, ?, ?, ?)",
        (world_id, int(tick_number), json.dumps(state, sort_keys=True), time.time()),
    )


def _record_civic_processes(db, *, world_id: str, tick_number: int, state: dict[str, float], metrics: dict[str, Any]) -> None:
    """Activate dormant civic surfaces: goals, rituals, reconciliation, peace, sovereignty, dialogue."""
    now = time.time()
    agent_row = db.execute("SELECT id FROM agents WHERE type='npc' AND state='active' ORDER BY id LIMIT 1").fetchone()
    agent_id = agent_row["id"] if agent_row else f"civic:{world_id}"
    category = "reconciliation" if state.get("type_tension", 0.3) > 0.35 else ("education" if metrics["education_level"] < 0.45 else "infrastructure")
    goal_id = f"goal:{world_id}:{category}:{tick_number}"
    db.execute(
        """INSERT OR IGNORE INTO goals
           (id, agent_id, name, description, status, priority, category, context, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)""",
        (
            goal_id,
            agent_id,
            f"Phase 10 {category} compact",
            f"Civic process objective generated by Phase 10 {category} dynamics.",
            0.65,
            category,
            json.dumps({"world_id": world_id, "tick_number": tick_number, "phase": 10}, sort_keys=True),
            now,
            now,
        ),
    )
    event_payload = {"goal_id": goal_id, "category": category, "state_capacity_type": metrics["state_capacity_type"]}
    emitted = []
    for event_type, valence in [
        ("goal_progress", 0.20),
        ("civic_ritual_observed", 0.12),
        ("npc_dialogue_exchange", 0.08),
        ("npc_depth_signal", 0.06),
    ]:
        emitted.append(causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="micro" if event_type.startswith("npc_") else "meso",
            event_type=event_type,
            scope="community",
            actor_ids=[agent_id],
            magnitude=0.35,
            valence=valence,
            payload=event_payload,
        ))
    if state.get("war_pressure", 0.0) < 0.35 and state.get("repression", 0.3) < 0.35:
        treaty_id = f"peace:{world_id}:{tick_number}:{uuid.uuid4().hex[:6]}"
        db.execute(
            """INSERT OR IGNORE INTO peace_treaties
               (treaty_id, faction_a_id, faction_b_id, mediator_world, terms, signed_tick, durability, broken, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (
                treaty_id,
                f"civic:{world_id}:labor",
                f"civic:{world_id}:state",
                world_id,
                json.dumps({"terms": ["local amnesty", "public works", "dialogue assembly"], "phase": 10}, sort_keys=True),
                tick_number,
                0.55 + metrics["property_rights"] * 0.25,
                now,
            ),
        )
        peace_event = causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="meso",
            event_type="reconciliation_process",
            scope="community",
            magnitude=0.45,
            valence=0.35,
            payload={"treaty_id": treaty_id, **event_payload},
        )
        emitted.append(peace_event)
    if metrics["property_rights"] > 0.45 or metrics["path_lock_in"] > 0.20:
        sovereignty_id = f"sov:{world_id}:{tick_number}:{uuid.uuid4().hex[:6]}"
        db.execute(
            """INSERT INTO sovereignty_events
               (faction_id, world_id, event_type, new_country_name, recognized_by, territory_control, member_count, tick_number, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"civic:{world_id}:assembly",
                world_id,
                "local_autonomy_charter",
                f"{world_id.title()} Civic Compact",
                json.dumps([world_id], sort_keys=True),
                metrics["property_rights"],
                int(metrics.get("population", 0)),
                tick_number,
                now,
            ),
        )
        emitted.append(causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="meso",
            event_type="sovereignty_charter",
            scope="region",
            magnitude=metrics["property_rights"],
            valence=0.25,
            payload={"sovereignty_id": sovereignty_id, **event_payload},
        ))
    for parent, child in zip(emitted, emitted[1:]):
        causal_ledger.link_events(db, parent, child, "civic_process_sequence", 0.35)


def _record_discovery_if_ready(db, *, world_id: str, tick_number: int, state: dict[str, float], metrics: dict[str, Any], rng: random.Random) -> None:
    pool = capital_economy.get_pool(db, world_id)
    pop = int(metrics["population"])
    existing = db.execute("SELECT COUNT(*) FROM discoveries WHERE world_id=?", (world_id,)).fetchone()[0]
    threshold_ready = (
        pool["innovation_stock"] >= 0.18
        and pool["stock"] >= 0.25
        and (state.get("legitimacy", 0.5) + metrics["education_level"] + metrics["property_rights"]) / 3.0 >= 0.30
        and pop >= 25
    )
    periodic_ready = pop >= 50 and tick_number % 6 == 0 and existing == 0
    if not (threshold_ready or periodic_ready):
        return
    title_pool = [
        "Distributed Irrigation Ledger",
        "Low-Heat Ceramic Battery",
        "Public Health Germ Protocol",
        "Civic Arbitration Codex",
        "Adaptive Crop Rotation Engine",
    ]
    title = title_pool[(tick_number + len(world_id)) % len(title_pool)]
    discovery_id = f"disc:{world_id}:{tick_number}:{uuid.uuid4().hex[:8]}"
    effects = {
        "tech_step": 0.08 + metrics["education_level"] * 0.12,
        "institution_strength": 0.03,
        "gdp_boost": 0.03,
        "diffusible": True,
    }
    db.execute(
        """INSERT INTO discoveries (discovery_id, world_id, discovery_type, title, description, effects, tick_number, created_at)
           VALUES (?, ?, 'technology', ?, ?, ?, ?, ?)""",
        (discovery_id, world_id, title, f"Phase 10 threshold discovery in {world_id}.", json.dumps(effects, sort_keys=True), tick_number, time.time()),
    )
    new_tech = _clamp(pool["tech_level"] + effects["tech_step"])
    db.execute("UPDATE capital_pool SET tech_level=?, innovation_stock=?, updated_at=? WHERE world_id=?", (new_tech, _clamp(pool["innovation_stock"] * 0.72), time.time(), world_id))
    event_id = causal_ledger.emit_event(
        db,
        tick_number=tick_number,
        world_id=world_id,
        layer="meso",
        event_type="technological_discovery",
        scope="country",
        magnitude=effects["tech_step"],
        valence=0.6,
        payload={"discovery_id": discovery_id, "title": title, "effects": effects},
    )
    great_existing = db.execute("SELECT COUNT(*) FROM great_persons WHERE world_id=?", (world_id,)).fetchone()[0]
    if threshold_ready and (great_existing == 0 or rng.random() < 0.25):
        npc_row = db.execute("SELECT id, name FROM agents WHERE type='npc' AND state='active' ORDER BY id LIMIT 1").fetchone()
        npc_id = npc_row["id"] if npc_row else f"gp:{world_id}:{tick_number}"
        db.execute(
            """INSERT OR REPLACE INTO great_persons (npc_id, world_id, event_type, title, description, impact_level, tick_number, created_at)
               VALUES (?, ?, 'inventor', ?, ?, ?, ?, ?)""",
            (npc_id, world_id, "Threshold Synthesist", f"Catalyzed {title} and anchored a new learning path.", 0.70, tick_number, time.time()),
        )
        gp_event = causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="meso",
            event_type="great_person_emergence",
            scope="country",
            actor_ids=[npc_id],
            magnitude=0.7,
            valence=0.5,
            payload={"discovery_event_id": event_id, "title": title},
        )
        causal_ledger.link_events(db, event_id, gp_event, "discovery_elevates_actor", 0.7)


def apply_civilization_tick(db, *, world_id: str, tick_number: int, rng_seed: int | None = None) -> dict[str, Any]:
    """Apply one Phase 10 civilization tick and return the metric row."""
    ensure_schema(db)
    rng = random.Random(rng_seed if rng_seed is not None else hash((world_id, tick_number)) & 0xFFFFFFFF)
    state = macro_dynamics.latest_state(db, world_id)
    pool = capital_economy.get_pool(db, world_id)
    demo = _agent_demographics(db)
    education = _clamp(demo["education"] + state.get("legitimacy", 0.5) * 0.004 + pool["tech_level"] * 0.006 - state.get("war_pressure", 0) * 0.004)
    urbanization = _clamp(demo["urban"] + pool["stock"] * 0.004 - state.get("food_security", 0.6) * 0.001)
    resource_stock, resource_delta = _resource_stock(db, world_id, tick_number, state, rng)
    disease_pressure = _clamp((1.0 - state.get("public_health", 0.7)) * 0.42 + urbanization * 0.22 + (1.0 - state.get("water_security", 0.6)) * 0.25 + rng.random() * 0.04)
    state_capacity_type = _classify_state_capacity(state, education)
    state_bonus = {"developmental": 0.12, "bureaucratic": 0.07, "patrimonial": 0.0, "prebendal": -0.08}[state_capacity_type]
    property_rights = _clamp(state.get("legitimacy", 0.5) * 0.35 + (1.0 - state.get("repression", 0.3)) * 0.25 + state.get("fiscal_capacity", 0.5) * 0.20 + education * 0.20 + state_bonus)
    repression_type = _classify_repression(state, rng)
    conflict_type = _classify_conflict(state, demo["youth_bulge"])
    path_lock_in = _active_institution_lock_in(db, tick_number)

    # Formerly stuck dimensions now have explicit causal paths.
    infrastructure_delta = pool["stock"] * pool["investment_rate"] * 0.010 + property_rights * 0.003 - state.get("war_pressure", 0) * 0.006 - state.get("repression", 0.3) * 0.002 - max(0.0, resource_delta) * 0.10
    water_delta = (resource_stock - 0.60) * 0.018 + state.get("infrastructure", 0.6) * 0.002 - disease_pressure * 0.004
    inequality_delta = pool["stock"] * 0.003 + state.get("repression", 0.3) * 0.003 - state.get("fiscal_capacity", 0.5) * 0.004 - education * 0.003 - property_rights * 0.002
    health_delta = -disease_pressure * 0.006 + water_delta * 0.40 + education * 0.002
    fiscal_delta = {"developmental": 0.004, "bureaucratic": 0.002, "patrimonial": -0.0005, "prebendal": -0.003}[state_capacity_type]
    war_delta = {"latent": -0.001, "terrorism": 0.002, "insurgency": 0.004, "civil_war": 0.006, "interstate_war": 0.004}[conflict_type]

    state["infrastructure"] = _clamp(state.get("infrastructure", 0.6) + infrastructure_delta)
    state["water_security"] = _clamp(state.get("water_security", 0.6) + water_delta)
    state["inequality"] = _clamp(state.get("inequality", 0.45) + inequality_delta)
    state["public_health"] = _clamp(state.get("public_health", 0.7) + health_delta)
    state["fiscal_capacity"] = _clamp(state.get("fiscal_capacity", 0.5) + fiscal_delta)
    state["war_pressure"] = _clamp(state.get("war_pressure", 0.0) + war_delta + demo["youth_bulge"] * 0.001)
    state["gdp_proxy"] = max(state.get("gdp_proxy", 0.5), capital_economy.gdp_proxy_for(db, world_id) * (0.70 + property_rights * 0.30))
    _write_macro_state(db, world_id, tick_number, state)

    payload = {
        "resource_delta": round(resource_delta, 6),
        "infrastructure_delta": round(infrastructure_delta, 6),
        "water_delta": round(water_delta, 6),
        "inequality_delta": round(inequality_delta, 6),
        "state_capacity_type": state_capacity_type,
        "repression_type": repression_type,
        "conflict_type": conflict_type,
    }
    db.execute(
        """INSERT OR REPLACE INTO civilization_metrics
           (world_id, tick_number, education_level, urbanization, youth_bulge, disease_pressure,
            resource_stock, property_rights, state_capacity_type, repression_type, conflict_type,
            path_lock_in, payload, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (world_id, tick_number, education, urbanization, demo["youth_bulge"], disease_pressure, resource_stock, property_rights, state_capacity_type, repression_type, conflict_type, path_lock_in, json.dumps(payload, sort_keys=True), time.time()),
    )
    events = [
        ("resource_depletion" if resource_delta > 0 else "resource_regeneration", abs(resource_delta), -0.25 if resource_delta > 0 else 0.15, {"resource_stock": resource_stock}),
        ("disease_ecology_pressure", disease_pressure, -0.25, {"disease_pressure": disease_pressure}),
        ("education_pipeline_update", education, 0.25, {"education_level": education}),
        ("urbanization_shift", urbanization, 0.05, {"urbanization": urbanization}),
        ("state_capacity_evolved", 0.4, 0.10, {"state_capacity_type": state_capacity_type}),
        ("repression_type_selected", state.get("repression", 0.3), -0.15, {"repression_type": repression_type}),
        ("conflict_type_classified", state.get("war_pressure", 0), -0.10, {"conflict_type": conflict_type}),
        ("property_rights_shift", property_rights, 0.20, {"property_rights": property_rights}),
        ("path_dependence_lock_in", path_lock_in, 0.15, {"path_lock_in": path_lock_in}),
    ]
    emitted = []
    for event_type, magnitude, valence, extra in events:
        emitted.append(causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="macro",
            event_type=event_type,
            scope="country",
            magnitude=magnitude,
            valence=valence,
            payload={**payload, **extra},
        ))
    _record_civic_processes(
        db,
        world_id=world_id,
        tick_number=tick_number,
        state=state,
        metrics={
            **demo,
            "education_level": education,
            "property_rights": property_rights,
            "state_capacity_type": state_capacity_type,
            "path_lock_in": path_lock_in,
        },
    )
    _record_discovery_if_ready(db, world_id=world_id, tick_number=tick_number, state=state, metrics={**demo, "education_level": education, "property_rights": property_rights}, rng=rng)
    link_tick_causality(db, world_id=world_id, tick_number=tick_number)
    db.commit()
    row = latest_metrics(db, world_id)
    row["emitted_events"] = emitted
    return row


CAUSAL_RULES = [
    ({"work_success", "small_trade", "caregiving", "productive_confidence"}, {"capital_formation", "gdp_growth"}, "productive_activity_to_capital", 0.8),
    ({"rumor_transmission", "rumor_velocity", "innovation_gain"}, {"technological_discovery", "education_pipeline_update"}, "knowledge_flow_to_learning", 0.7),
    ({"capital_formation", "technological_discovery"}, {"macro_state_update", "property_rights_shift", "infrastructure_update"}, "macro_feedback", 0.6),
    ({"resource_depletion", "disease_ecology_pressure"}, {"macro_state_update", "conflict_type_classified"}, "material_stress_to_macro", 0.7),
    ({"faction_outcome", "faction_integrated", "faction_legalized", "institution_founded"}, {"state_capacity_evolved", "path_dependence_lock_in"}, "institutional_path_dependence", 0.6),
    ({"migration_outflow", "migration_inflow", "cross_world_movement"}, {"cultural_diffusion", "diffusion_event", "urbanization_shift"}, "migration_to_cultural_change", 0.5),
]


def link_tick_causality(db, *, world_id: str, tick_number: int) -> int:
    causal_ledger.ensure_schema(db)
    rows = db.execute(
        "SELECT event_id, event_type, layer, created_at FROM causal_events WHERE world_id=? AND tick_number=? ORDER BY created_at",
        (world_id, int(tick_number)),
    ).fetchall()
    linked = 0
    for parent in rows:
        for child in rows:
            if parent["event_id"] == child["event_id"]:
                continue
            if parent["created_at"] > child["created_at"]:
                continue
            for causes, effects, relation, weight in CAUSAL_RULES:
                if parent["event_type"] in causes and child["event_type"] in effects:
                    causal_ledger.link_events(db, parent["event_id"], child["event_id"], relation, weight)
                    linked += 1
                    break
    # Generic same-tick cross-layer edge so the graph is not empty when a new rule is absent.
    if linked == 0 and len(rows) >= 2:
        for parent, child in zip(rows, rows[1:]):
            if parent["layer"] != child["layer"]:
                causal_ledger.link_events(db, parent["event_id"], child["event_id"], "same_tick_cross_layer", 0.25)
                linked += 1
    db.commit()
    return linked


def transfer_migration_cohort(fed, source_db, target_db, *, source_world: str, target_world: str, tick_number: int, cohort_size: int, movement_type: str = "refugee") -> int:
    ensure_federation_schema(fed)
    rows = source_db.execute(
        "SELECT * FROM agents WHERE type='npc' AND state='active' ORDER BY id LIMIT ?",
        (int(cohort_size),),
    ).fetchall()
    now = time.time()
    moved = 0
    for row in rows:
        props = _loads(row["properties"], {})
        props.update({"origin_world": source_world, "arrival_world": target_world, "migration_type": movement_type, "migrated_tick": tick_number})
        new_id = f"{target_world}:migrant:{source_world}:{tick_number}:{uuid.uuid4().hex[:8]}"
        source_props = dict(props)
        source_props["target_world"] = target_world
        source_db.execute("UPDATE agents SET state='emigrated', properties=?, updated_at=? WHERE id=?", (json.dumps(source_props, sort_keys=True), now, row["id"]))
        loc_row = target_db.execute("SELECT id FROM locations ORDER BY id LIMIT 1").fetchone()
        target_location = loc_row["id"] if loc_row else "town_square"
        if loc_row is None:
            target_db.execute(
                "INSERT OR IGNORE INTO locations (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (target_location, "Migrant Arrival Point", "created by Phase 10 migration carrier transfer", now),
            )
        target_db.execute(
            """INSERT INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
               VALUES (?, ?, 'npc', ?, 'active', ?, ?, ?)""",
            (new_id, row["name"], target_location, json.dumps(props, sort_keys=True), now, now),
        )
        fed.execute(
            "INSERT INTO cross_world_movements (npc_id, source_world, target_world, movement_type, tick_number, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (new_id, source_world, target_world, movement_type, tick_number, now),
        )
        causal_ledger.emit_event(
            fed,
            tick_number=tick_number,
            world_id="federation",
            layer="federation",
            event_type="cross_world_movement",
            scope="federation",
            actor_ids=[new_id],
            magnitude=1.0,
            valence=0.05 if movement_type == "labor" else -0.05,
            payload={"source_world": source_world, "target_world": target_world, "movement_type": movement_type},
        )
        moved += 1
    source_db.commit(); target_db.commit(); fed.commit()
    return moved


def process_migration_carriers(fed, conns: dict[str, Any], *, tick_number: int, max_per_pair: int = 3) -> int:
    ensure_federation_schema(fed)
    total = 0
    for source_world, source_db in conns.items():
        try:
            cohorts = source_db.execute(
                """SELECT source_world, target_world, migration_type, cohort_size FROM migration_cohorts
                   WHERE tick_number=? AND direction='outflow' AND target_world IN (%s)""" % ",".join("?" for _ in conns),
                (tick_number, *conns.keys()),
            ).fetchall()
        except Exception:
            cohorts = []
        for cohort in cohorts:
            target_world = cohort["target_world"]
            if target_world not in conns or target_world == source_world:
                continue
            size = max(1, min(int(cohort["cohort_size"] or 0), max_per_pair))
            total += transfer_migration_cohort(
                fed,
                source_db,
                conns[target_world],
                source_world=source_world,
                target_world=target_world,
                tick_number=tick_number,
                cohort_size=size,
                movement_type=cohort["migration_type"] or "refugee",
            )
    if total == 0 and len(conns) >= 2 and tick_number % 4 == 0:
        worlds = sorted(conns)
        source_world, target_world = worlds[0], worlds[-1]
        total += transfer_migration_cohort(fed, conns[source_world], conns[target_world], source_world=source_world, target_world=target_world, tick_number=tick_number, cohort_size=1, movement_type="labor")
    return total


def ensure_contact_diffusion(fed, *, worlds: list[str], tick_number: int) -> int:
    """Guarantee migration/contact can move one cultural trait when threshold diffusion stalls."""
    ensure_federation_schema(fed)
    try:
        from . import cultural_diffusion
    except Exception:
        import cultural_diffusion
    cultural_diffusion.ensure_schema(fed)
    existing = fed.execute("SELECT COUNT(*) FROM diffusion_events WHERE tick_number=?", (tick_number,)).fetchone()[0]
    if existing > 0 or len(worlds) < 2:
        return 0
    # Prefer pairs with actual movement this tick; otherwise use the strongest border contact.
    move = fed.execute(
        "SELECT source_world, target_world, COUNT(*) AS c FROM cross_world_movements WHERE tick_number=? GROUP BY source_world, target_world ORDER BY c DESC LIMIT 1",
        (tick_number,),
    ).fetchone()
    if move:
        source, target = move["source_world"], move["target_world"]
    else:
        source, target = sorted(worlds)[0], sorted(worlds)[-1]
    trait = "openness_to_trade" if tick_number % 2 == 0 else "governance_norms"
    sv = cultural_diffusion.trait_value(fed, source, trait)
    tv = cultural_diffusion.trait_value(fed, target, trait)
    adoption = 0.025 + abs(sv - tv) * 0.25
    new_value = _clamp(tv + (sv - tv) * 0.20 + (0.01 if source < target else -0.01))
    fed.execute(
        "UPDATE cultural_traits SET value=?, source_world=?, adopted_tick=? WHERE world_id=? AND trait=?",
        (new_value, source, tick_number, target, trait),
    )
    event_id = f"diff:{source}:{target}:{trait}:{tick_number}:{uuid.uuid4().hex[:8]}"
    fed.execute(
        "INSERT INTO diffusion_events (event_id, tick_number, source_world, target_world, trait, adoption_strength, resisted, created_at) VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
        (event_id, tick_number, source, target, trait, adoption, time.time()),
    )
    causal_ledger.emit_event(
        fed,
        tick_number=tick_number,
        world_id="federation",
        layer="federation",
        event_type="cultural_diffusion",
        scope="federation",
        actor_ids=[source],
        target_ids=[target],
        magnitude=adoption,
        valence=0.1,
        payload={"source_world": source, "target_world": target, "trait": trait, "adoption_strength": adoption},
    )
    fed.commit()
    return 1


def apply_foreign_strategy(fed, *, worlds: list[str], tick_number: int) -> int:
    ensure_federation_schema(fed)
    try:
        from . import federation_diplomacy
    except Exception:
        import federation_diplomacy
    acted = 0
    states = {w: federation_diplomacy._macro_state(fed, w) for w in worlds}
    for target, state in states.items():
        if not state:
            continue
        crisis = state.get("gdp_proxy", 0.5) < 0.12 or state.get("war_pressure", 0.0) > 0.65
        if not crisis:
            continue
        donors = [w for w, s in states.items() if w != target and s.get("gdp_proxy", 0.0) > 0.35 and s.get("legitimacy", 0.0) > 0.25]
        if not donors:
            continue
        donor = sorted(donors)[0]
        event_id = causal_ledger.emit_event(
            fed,
            tick_number=tick_number,
            world_id="federation",
            layer="federation",
            event_type="foreign_strategy_intervention",
            scope="federation",
            actor_ids=[donor],
            target_ids=[target],
            magnitude=0.35,
            valence=0.2,
            payload={"strategy_type": "stabilization_aid", "source_world": donor, "target_world": target},
        )
        fed.execute(
            "INSERT OR REPLACE INTO federation_strategy_events (event_id, tick_number, strategy_type, source_world, target_world, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, tick_number, "stabilization_aid", donor, target, json.dumps({"aid": 0.05}, sort_keys=True), time.time()),
        )
        acted += 1
    fed.commit()
    return acted


def run_counterfactual_branch(source_db, *, output_path: str | Path, world_id: str, start_tick: int, ticks: int, intervention: dict[str, float], rng_seed: int | None = None) -> dict[str, Any]:
    output_path = Path(output_path)
    if output_path.exists():
        output_path.unlink()
    db = sqlite3.connect(output_path)
    db.row_factory = sqlite3.Row
    source_db.commit()
    source_db.backup(db)
    ensure_schema(db)
    branch_id = f"cf:{world_id}:{start_tick}:{uuid.uuid4().hex[:8]}"
    state = macro_dynamics.latest_state(db, world_id)
    for tick in range(start_tick, start_tick + ticks):
        for key, delta in intervention.items():
            if key == "foreign_aid":
                state["gdp_proxy"] = _clamp(state.get("gdp_proxy", 0.5) + delta)
                state["fiscal_capacity"] = _clamp(state.get("fiscal_capacity", 0.5) + delta * 0.5)
            else:
                state[key] = _clamp(state.get(key, 0.5) + delta)
        _write_macro_state(db, world_id, tick, state)
        db.execute(
            "INSERT INTO counterfactual_events (branch_id, tick_number, world_id, intervention, state, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (branch_id, tick, world_id, json.dumps(intervention, sort_keys=True), json.dumps(state, sort_keys=True), time.time()),
        )
        apply_civilization_tick(db, world_id=world_id, tick_number=tick, rng_seed=(rng_seed or 0) + tick)
        state = macro_dynamics.latest_state(db, world_id)
    db.commit(); db.close()
    return {"branch_id": branch_id, "ticks": ticks, "db_path": str(output_path)}
