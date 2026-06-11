"""faction_lifecycle.py — consequences for factions, not just formation."""
from __future__ import annotations

import json
import random
import sqlite3
import time
import uuid

try:
    from . import causal_ledger, institutions, macro_dynamics, meso_aggregator, world_profiles
except Exception:
    import causal_ledger
    import institutions
    import macro_dynamics
    import meso_aggregator
    import world_profiles

GRIEVANCE_SIGNALS = {"labor_unrest", "repression_visibility", "migration_pressure", "economic_stress"}
TERMINAL_STATUSES = {"dissolved", "integrated", "sovereign", "legalized", "governing_coalition", "exiled", "victorious"}

#: How many recent ticks of meso pressure a faction needs to accumulate before
#: formation can fire. Real social movements form from *sustained* grievance,
#: not a single bad day. With ticks_per_year in [4, 12] this window covers
#: roughly 1.3 to 4 years of recent history.
CUMULATIVE_PRESSURE_WINDOW_TICKS = 16

#: Cumulative pressure threshold for formation (sum of magnitudes across the
#: recent window). 0.30 is calibrated so that a 16-tick window of
#: 0.018-0.020 average pressure (~1 micro-event per tick of any grievance
#: type) will cross it -- which is a realistic sustained-stress baseline
#: for a long federation run.
CUMULATIVE_PRESSURE_THRESHOLD = 0.30

OUTCOME_KEYS = [
    "formed",
    "integrated",
    "legalized",
    "governing_coalition",
    "suppressed",
    "exiled",
    "splintered",
    "radicalized",
    "victorious",
    "dissolved",
    "escalated",
    "repressed",  # backward-compatible alias
    "declined",   # backward-compatible alias
]
OUTCOME_VALENCE = {
    "integrated": 0.45,
    "legalized": 0.35,
    "governing_coalition": 0.50,
    "suppressed": -0.55,
    "exiled": -0.45,
    "splintered": -0.50,
    "radicalized": -0.65,
    "victorious": 0.20,
    "dissolved": 0.10,
    "escalated": -0.65,
}


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


def cumulative_pressure(
    db,
    *,
    world_id: str,
    current_tick: int,
    window: int = CUMULATIVE_PRESSURE_WINDOW_TICKS,
) -> float:
    """Sum of grievance-signal magnitudes over the last ``window`` ticks.

    Real social movements form from sustained grievance, not a single
    bad day. The federation's per-tick meso-signal magnitudes are tiny
    (a single ``migration_plan`` event contributes ~0.013), so reading
    only the current tick makes the formation threshold
    (``CUMULATIVE_PRESSURE_THRESHOLD``) effectively unreachable.

    A rolling window of recent ticks captures the same dynamics the
    gate would see in a multi-year sustained-stress scenario.

    Returns a non-negative float. Old signals (outside the window) and
    non-grievance signals (e.g. ``state_messaging``, ``rumor_velocity``)
    are excluded.
    """
    if window <= 0:
        return 0.0
    floor_tick = max(0, int(current_tick) - window)
    placeholders = ",".join("?" for _ in GRIEVANCE_SIGNALS)
    try:
        row = db.execute(
            f"""
            SELECT COALESCE(SUM(magnitude), 0.0)
            FROM meso_signals
            WHERE world_id=?
              AND tick_number >= ?
              AND tick_number <= ?
              AND signal_type IN ({placeholders})
            """,
            (world_id, floor_tick, int(current_tick), *sorted(GRIEVANCE_SIGNALS)),
        ).fetchone()
    except sqlite3.OperationalError:
        # meso_signals table may not exist yet on a fresh world.
        return 0.0
    return float(row[0] or 0.0)


def dominant_grievance(
    db,
    *,
    world_id: str,
    current_tick: int,
    window: int = CUMULATIVE_PRESSURE_WINDOW_TICKS,
) -> str | None:
    """Return the grievance signal_type with the largest cumulative magnitude in the window.

    Used by ``run_faction_lifecycle`` to pick the primary_grievance label
    for a newly-formed faction. Returns ``None`` if there is no pressure
    in the window.
    """
    if window <= 0:
        return None
    floor_tick = max(0, int(current_tick) - window)
    placeholders = ",".join("?" for _ in GRIEVANCE_SIGNALS)
    try:
        row = db.execute(
            f"""
            SELECT signal_type, SUM(magnitude) AS mag
            FROM meso_signals
            WHERE world_id=?
              AND tick_number >= ?
              AND tick_number <= ?
              AND signal_type IN ({placeholders})
            GROUP BY signal_type
            ORDER BY mag DESC
            LIMIT 1
            """,
            (world_id, floor_tick, int(current_tick), *sorted(GRIEVANCE_SIGNALS)),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return str(row[0]) if row else None


def _weighted_choice(options: list[tuple[str, float]], rng: random.Random) -> str | None:
    options = [(name, max(0.0, float(weight))) for name, weight in options if weight > 0]
    total = sum(weight for _, weight in options)
    if total <= 0:
        return None
    roll = rng.random() * total
    acc = 0.0
    for name, weight in options:
        acc += weight
        if roll <= acc:
            return name
    return options[-1][0]


def _choose_outcome(state: dict, profile: dict, fac, score: float, rng: random.Random) -> str | None:
    members = int(fac["member_count"] or 0)
    if members <= 0:
        return "dissolved"

    # Deterministic guardrails make extreme regimes legible and testable.
    if state.get("legitimacy", 0.5) < 0.20 and state.get("repression", 0.3) > 0.80:
        return _weighted_choice([
            ("suppressed", 0.46),
            ("radicalized", 0.30 + state.get("war_pressure", 0.0) * 0.20),
            ("exiled", 0.18 + max(0.0, state.get("border_openness", 0.5)) * 0.10),
            ("splintered", 0.16 if score > 0.75 else 0.03),
        ], rng)
    if state.get("legitimacy", 0.5) > 0.75 and state.get("repression", 0.3) < 0.15:
        return _weighted_choice([
            ("integrated", 0.40),
            ("legalized", 0.30),
            ("governing_coalition", 0.22 if score > 0.55 else 0.06),
            ("dissolved", 0.04),
        ], rng)

    biases = profile.get("factions", {})
    concession = float(biases.get("concession_bias", 0.25)) + state.get("legitimacy", 0.5) * 0.18 + (1.0 - state.get("repression", 0.3)) * 0.12
    repression = float(biases.get("repression_bias", 0.25)) + state.get("repression", 0.3) * 0.28
    legalization = float(biases.get("legalization_bias", 0.15)) + state.get("legitimacy", 0.5) * 0.10
    splinter = float(biases.get("splinter_bias", 0.15)) + max(0.0, score - 0.6) * 0.14
    exile = float(biases.get("exile_bias", 0.10)) + state.get("border_openness", 0.5) * 0.05
    radical = float(biases.get("radicalization_bias", 0.10)) + state.get("war_pressure", 0.0) * 0.22 + score * 0.08

    return _weighted_choice([
        ("integrated", concession * 0.30 if members > 5 else 0.0),
        ("legalized", legalization),
        ("governing_coalition", concession * 0.12 if score > 0.55 else 0.0),
        ("suppressed", repression * 0.42),
        ("exiled", exile),
        ("splintered", splinter),
        ("radicalized", radical),
        ("victorious", 0.04 if score > 0.85 and state.get("legitimacy", 0.5) < 0.30 else 0.0),
        ("dissolved", 0.08 if score < 0.15 else 0.0),
    ], rng)


def _emit_outcome_signal(db, *, world_id: str, tick_number: int, outcome: str, magnitude: float, faction_id: str) -> None:
    meso_aggregator.ensure_schema(db)
    signal_id = f"sig:{world_id}:{tick_number}:faction:{outcome}:{faction_id}"
    db.execute(
        """
        INSERT OR REPLACE INTO meso_signals
            (signal_id, tick_number, world_id, location_id, signal_type, magnitude, source_event_count, payload, created_at)
        VALUES (?, ?, ?, 'capital', ?, ?, 1, ?, ?)
        """,
        (signal_id, tick_number, world_id, f"faction_outcome:{outcome}", magnitude, json.dumps({"faction_id": faction_id}), time.time()),
    )


def _create_splinter(db, *, fac, world_id: str, tick_number: int, member_count: int, score: float) -> tuple[str, int, int]:
    child_id = f"{fac['faction_id']}:splinter:{tick_number}:{uuid.uuid4().hex[:6]}"
    child_members = max(3, int(member_count * 0.25))
    parent_members = max(0, member_count - child_members)
    db.execute("UPDATE factions SET member_count=?, consequence_score=?, last_action_tick=? WHERE faction_id=?",
               (parent_members, score, tick_number, fac["faction_id"]))
    db.execute(
        """
        INSERT INTO factions (faction_id, name, world_id, region, status, primary_grievance,
                              demand, member_count, influence, founded_tick, metadata, created_at,
                              lifecycle_stage, consequence_score, last_action_tick)
        VALUES (?, ?, ?, ?, 'radicalized', ?, ?, ?, ?, ?, ?, ?, 'splinter', ?, ?)
        """,
        (
            child_id,
            f"Splinter of {fac['name']}",
            world_id,
            fac["region"] or "capital",
            fac["primary_grievance"] or "autonomy",
            "radical redress and recognition",
            child_members,
            min(1.0, float(fac["influence"] or 0.0) + 0.08),
            tick_number,
            json.dumps({"parent_faction_id": fac["faction_id"], "source": "phase8_splinter"}),
            time.time(),
            max(score, 0.5),
            tick_number,
        ),
    )
    return child_id, parent_members, child_members


def _apply_outcome(db, *, fac, world_id: str, tick_number: int, outcome: str, score: float, member_count: int, influence: float) -> tuple[int, dict]:
    payload_extra = {}
    if outcome == "integrated":
        db.execute("UPDATE factions SET status='integrated', lifecycle_stage='integrated', dissolved_tick=?, last_action_tick=? WHERE faction_id=?",
                   (tick_number, tick_number, fac["faction_id"]))
    elif outcome == "legalized":
        db.execute("UPDATE factions SET status='legalized', lifecycle_stage='legalized', consequence_score=?, last_action_tick=? WHERE faction_id=?",
                   (max(0.0, score * 0.55), tick_number, fac["faction_id"]))
    elif outcome == "governing_coalition":
        db.execute("UPDATE factions SET status='governing_coalition', lifecycle_stage='coalition', influence=?, consequence_score=?, last_action_tick=? WHERE faction_id=?",
                   (min(1.0, influence + 0.10), max(0.0, score * 0.50), tick_number, fac["faction_id"]))
    elif outcome == "suppressed":
        member_count = max(0, int(member_count * 0.78))
        db.execute("UPDATE factions SET status='suppressed', lifecycle_stage='suppressed', member_count=?, consequence_score=?, last_action_tick=? WHERE faction_id=?",
                   (member_count, score + 0.12, tick_number, fac["faction_id"]))
    elif outcome == "exiled":
        member_count = max(0, int(member_count * 0.70))
        db.execute("UPDATE factions SET status='exiled', lifecycle_stage='exiled', member_count=?, consequence_score=?, dissolved_tick=?, last_action_tick=? WHERE faction_id=?",
                   (member_count, score + 0.05, tick_number, tick_number, fac["faction_id"]))
    elif outcome == "splintered":
        child_id, member_count, child_members = _create_splinter(db, fac=fac, world_id=world_id, tick_number=tick_number, member_count=member_count, score=score)
        payload_extra.update({"child_faction_id": child_id, "child_members": child_members})
    elif outcome == "radicalized":
        member_count = int(member_count * 1.08 + 2)
        db.execute("UPDATE factions SET status='armed_conflict', lifecycle_stage='radicalized', member_count=?, influence=?, consequence_score=?, last_action_tick=? WHERE faction_id=?",
                   (member_count, min(1.0, influence + 0.06), score + 0.10, tick_number, fac["faction_id"]))
    elif outcome == "victorious":
        db.execute("UPDATE factions SET status='victorious', lifecycle_stage='regime_reform', influence=1.0, consequence_score=?, dissolved_tick=?, last_action_tick=? WHERE faction_id=?",
                   (max(score, 0.9), tick_number, tick_number, fac["faction_id"]))
    elif outcome == "dissolved":
        db.execute("UPDATE factions SET status='dissolved', lifecycle_stage='dissolved', dissolved_tick=?, last_action_tick=? WHERE faction_id=?",
                   (tick_number, tick_number, fac["faction_id"]))
    elif outcome == "escalated":
        new_status = "ultimatum" if fac["status"] in {"active", "forming", "suppressed"} else "armed_conflict"
        member_count = int(member_count * 1.05 + 2)
        db.execute("UPDATE factions SET status=?, member_count=?, influence=?, consequence_score=?, last_action_tick=? WHERE faction_id=?",
                   (new_status, member_count, min(1.0, influence + 0.03), score, tick_number, fac["faction_id"]))
    return member_count, payload_extra


def run_faction_lifecycle(
    db,
    *,
    world_id: str,
    tick_number: int,
    rng: random.Random | None = None,
    force_outcome: str | None = None,
) -> dict[str, int]:
    """Create/update faction consequences from meso + macro conditions."""
    causal_ledger.ensure_schema(db)
    _ensure_extra_columns(db)
    rng = rng or random.Random()
    state = macro_dynamics.latest_state(db, world_id)
    profile = world_profiles.profile(world_id)
    counts = {key: 0 for key in OUTCOME_KEYS}

    pressure_rows = db.execute(
        """
        SELECT signal_type, SUM(magnitude) AS mag, SUM(source_event_count) AS events
        FROM meso_signals
        WHERE world_id=? AND tick_number=? AND signal_type IN ('labor_unrest','repression_visibility','migration_pressure','economic_stress')
        GROUP BY signal_type
        """,
        (world_id, int(tick_number)),
    ).fetchall()
    # Current-tick pressure is preserved for consequence scoring (per-tick
    # intensity) and for the influence update on existing factions.
    current_tick_pressure = sum(float(r["mag"] or 0.0) for r in pressure_rows)
    # Formation, however, is driven by sustained pressure over a recent
    # window. Per-tick magnitudes are small (~0.013 per micro-event), so
    # a single-tick threshold of 0.30 was effectively unreachable in
    # realistic runs. The rolling-window sum restores the contract:
    # "factions form from accumulated grievance, not a single bad tick."
    cumulative = cumulative_pressure(
        db, world_id=world_id, current_tick=int(tick_number)
    )

    # Formation from accumulated pressure, not timer. Keep movements scarce.
    pop = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    placeholders = ",".join("?" for _ in TERMINAL_STATUSES)
    open_factions = db.execute(
        f"SELECT COUNT(*) FROM factions WHERE world_id=? AND status NOT IN ({placeholders})",
        (world_id, *sorted(TERMINAL_STATUSES)),
    ).fetchone()[0]
    recent_formation = db.execute(
        "SELECT COUNT(*) FROM causal_events WHERE world_id=? AND event_type='faction_formed' AND tick_number BETWEEN ? AND ?",
        (world_id, max(0, tick_number - 6), tick_number),
    ).fetchone()[0]
    max_open_factions = max(3, pop // 250)
    can_form = open_factions < max_open_factions and recent_formation == 0
    if (
        can_form
        and cumulative > CUMULATIVE_PRESSURE_THRESHOLD
        and rng.random() < min(0.18, (cumulative - CUMULATIVE_PRESSURE_THRESHOLD) * 0.20)
    ):
        grievance = (
            dominant_grievance(db, world_id=world_id, current_tick=int(tick_number))
            or "labor_unrest"
        )
        faction_id = f"{world_id}:faction:{grievance}:{tick_number}:{uuid.uuid4().hex[:8]}"
        members = max(3, int(cumulative * 80))
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
                min(1.0, cumulative),
                tick_number,
                json.dumps({"source": "causal_lifecycle", "pressure_window": CUMULATIVE_PRESSURE_WINDOW_TICKS}),
                time.time(),
                cumulative,
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
            magnitude=cumulative,
            valence=-0.35,
            payload={"faction_id": faction_id, "grievance": grievance, "members": members},
        )
        counts["formed"] += 1

    factions = db.execute(
        f"SELECT * FROM factions WHERE world_id=? AND status NOT IN ({placeholders})",
        (world_id, *sorted(TERMINAL_STATUSES)),
    ).fetchall()
    for fac in factions:
        influence = float(fac["influence"] or 0.0)
        score = float(fac["consequence_score"] or 0.0) + current_tick_pressure * 0.15 + influence * 0.02
        member_count = int(fac["member_count"] or 0)
        outcome = force_outcome or _choose_outcome(state, profile, fac, score, rng)
        if not outcome:
            db.execute("UPDATE factions SET consequence_score=?, last_action_tick=? WHERE faction_id=?",
                       (score, tick_number, fac["faction_id"]))
            continue
        member_count, payload_extra = _apply_outcome(
            db,
            fac=fac,
            world_id=world_id,
            tick_number=tick_number,
            outcome=outcome,
            score=score,
            member_count=member_count,
            influence=influence,
        )
        counts[outcome] += 1
        if outcome == "suppressed":
            counts["repressed"] += 1
        if outcome == "dissolved":
            counts["declined"] += 1
        if outcome == "radicalized":
            counts["escalated"] += 1
        magnitude = max(0.05, score)
        _emit_outcome_signal(db, world_id=world_id, tick_number=tick_number, outcome=outcome, magnitude=magnitude, faction_id=fac["faction_id"])
        causal_ledger.emit_event(
            db,
            tick_number=tick_number,
            world_id=world_id,
            layer="macro",
            event_type=f"faction_{outcome}",
            scope="faction",
            target_ids=[fac["faction_id"]],
            magnitude=magnitude,
            valence=OUTCOME_VALENCE.get(outcome, -0.2),
            payload={"faction_id": fac["faction_id"], "members": member_count, "pressure": current_tick_pressure, **payload_extra},
        )
        # Phase 9: constructive outcomes can crystallize into durable institutions
        if outcome in {"legalized", "governing_coalition", "victorious", "integrated"}:
            grievance = fac["primary_grievance"] or "general"
            institutions.process_faction_outcome(
                db,
                world_id=world_id,
                tick_number=tick_number,
                faction_id=fac["faction_id"],
                outcome=outcome,
                grievance=grievance,
                rng=rng,
            )

    return counts
