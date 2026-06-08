"""faction_lifecycle.py — consequences for factions, not just formation."""
from __future__ import annotations

import json
import random
import time
import uuid

try:
    from . import causal_ledger, macro_dynamics
except Exception:
    import causal_ledger
    import macro_dynamics

GRIEVANCE_SIGNALS = {"labor_unrest", "repression_visibility", "migration_pressure", "economic_stress"}


def _ensure_extra_columns(db) -> None:
    # SQLite lacks IF NOT EXISTS for ADD COLUMN on old versions; ignore duplicate-column errors.
    for ddl in [
        "ALTER TABLE factions ADD COLUMN lifecycle_stage TEXT DEFAULT 'grievance'",
        "ALTER TABLE factions ADD COLUMN consequence_score REAL DEFAULT 0.0",
        "ALTER TABLE factions ADD COLUMN last_action_tick INTEGER DEFAULT 0",
    ]:
        try:
            db.execute(ddl)
        except Exception:
            pass


def run_faction_lifecycle(
    db,
    *,
    world_id: str,
    tick_number: int,
    rng: random.Random | None = None,
) -> dict[str, int]:
    """Create/update faction consequences from meso + macro conditions."""
    causal_ledger.ensure_schema(db)
    _ensure_extra_columns(db)
    rng = rng or random.Random()
    state = macro_dynamics.latest_state(db, world_id)
    counts = {"formed": 0, "escalated": 0, "integrated": 0, "repressed": 0, "declined": 0}

    pressure_rows = db.execute(
        """
        SELECT signal_type, SUM(magnitude) AS mag, SUM(source_event_count) AS events
        FROM meso_signals
        WHERE world_id=? AND tick_number=? AND signal_type IN ('labor_unrest','repression_visibility','migration_pressure','economic_stress')
        GROUP BY signal_type
        """,
        (world_id, int(tick_number)),
    ).fetchall()
    total_pressure = sum(float(r["mag"] or 0.0) for r in pressure_rows)

    # Formation from accumulated pressure, not timer. Keep movements scarce:
    # a world should not spawn hundreds of factions just because micro pressure
    # exists every tick. Existing active/armed/ultimatum factions absorb pressure.
    pop = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    open_factions = db.execute(
        "SELECT COUNT(*) FROM factions WHERE world_id=? AND status NOT IN ('dissolved','integrated','sovereign')",
        (world_id,),
    ).fetchone()[0]
    recent_formation = db.execute(
        "SELECT COUNT(*) FROM causal_events WHERE world_id=? AND event_type='faction_formed' AND tick_number BETWEEN ? AND ?",
        (world_id, max(0, tick_number - 6), tick_number),
    ).fetchone()[0]
    max_open_factions = max(3, pop // 250)
    can_form = open_factions < max_open_factions and recent_formation == 0
    if can_form and total_pressure > 0.30 and rng.random() < min(0.18, (total_pressure - 0.30) * 0.20):
        grievance = max(pressure_rows, key=lambda r: float(r["mag"] or 0.0))["signal_type"]
        faction_id = f"{world_id}:faction:{grievance}:{tick_number}:{uuid.uuid4().hex[:8]}"
        members = max(3, int(total_pressure * 80))
        db.execute(
            """
            INSERT INTO factions (faction_id, name, world_id, region, status, primary_grievance,
                                  demand, member_count, influence, founded_tick, metadata, created_at,
                                  lifecycle_stage, consequence_score, last_action_tick)
            VALUES (?, ?, ?, 'capital', 'active', ?, ?, ?, ?, ?, ?, ?, 'organization', ?, ?)
            """,
            (
                faction_id,
                f"{grievance.replace('_', ' ').title()} Front",
                world_id,
                grievance,
                "state response and material concessions",
                members,
                min(1.0, total_pressure),
                tick_number,
                json.dumps({"source": "causal_lifecycle"}),
                time.time(),
                total_pressure,
                tick_number,
            ),
        )
        causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="meso",
            event_type="faction_formed",
            scope="faction",
            target_ids=[faction_id],
            magnitude=total_pressure,
            valence=-0.35,
            payload={"faction_id": faction_id, "grievance": grievance, "members": members},
        )
        counts["formed"] += 1

    factions = db.execute(
        "SELECT * FROM factions WHERE world_id=? AND status NOT IN ('dissolved','integrated','sovereign')",
        (world_id,),
    ).fetchall()
    for fac in factions:
        influence = float(fac["influence"] or 0.0)
        score = float(fac["consequence_score"] or 0.0) + total_pressure * 0.15 + influence * 0.02
        member_count = int(fac["member_count"] or 0)
        action = None
        valence = -0.2

        concession_prob = max(0.02, state["legitimacy"] * 0.03 + (1.0 - state["repression"]) * 0.04)
        repression_prob = max(0.02, state["repression"] * 0.08 + score * 0.02)
        escalation_prob = max(0.01, score * 0.08 + state["war_pressure"] * 0.05)

        roll = rng.random()
        if roll < concession_prob and member_count > 5:
            action = "faction_integrated"
            db.execute("UPDATE factions SET status='integrated', lifecycle_stage='integrated', dissolved_tick=?, last_action_tick=? WHERE faction_id=?",
                       (tick_number, tick_number, fac["faction_id"]))
            counts["integrated"] += 1
            valence = 0.45
        elif roll < concession_prob + repression_prob:
            action = "faction_repressed"
            member_count = max(0, int(member_count * 0.92))
            score += 0.08  # martyrdom memory
            db.execute("UPDATE factions SET member_count=?, consequence_score=?, last_action_tick=? WHERE faction_id=?",
                       (member_count, score, tick_number, fac["faction_id"]))
            counts["repressed"] += 1
            valence = -0.55
        elif roll < concession_prob + repression_prob + escalation_prob:
            action = "faction_escalated"
            new_status = "ultimatum" if fac["status"] in {"active", "forming"} else "armed_conflict"
            member_count = int(member_count * 1.05 + 2)
            db.execute("UPDATE factions SET status=?, member_count=?, influence=?, consequence_score=?, last_action_tick=? WHERE faction_id=?",
                       (new_status, member_count, min(1.0, influence + 0.03), score, tick_number, fac["faction_id"]))
            counts["escalated"] += 1
            valence = -0.65
        elif score < 0.03 and rng.random() < 0.05:
            action = "faction_declined"
            db.execute("UPDATE factions SET status='dissolved', dissolved_tick=?, last_action_tick=? WHERE faction_id=?",
                       (tick_number, tick_number, fac["faction_id"]))
            counts["declined"] += 1
            valence = 0.1
        else:
            db.execute("UPDATE factions SET consequence_score=?, last_action_tick=? WHERE faction_id=?",
                       (score, tick_number, fac["faction_id"]))

        if action:
            causal_ledger.emit_event(
                db,
                tick_number=tick_number,
                world_id=world_id,
                layer="macro",
                event_type=action,
                scope="faction",
                target_ids=[fac["faction_id"]],
                magnitude=max(0.05, score),
                valence=valence,
                payload={"faction_id": fac["faction_id"], "members": member_count, "pressure": total_pressure},
            )

    return counts
