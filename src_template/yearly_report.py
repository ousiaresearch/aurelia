"""yearly_report.py — causal yearly summaries for Aurelia."""
from __future__ import annotations

import json

try:
    from . import demography, macro_dynamics
except Exception:
    import demography
    import macro_dynamics


def build_yearly_report(db, *, world_id: str, year_number: int, start_tick: int, end_tick: int) -> dict:
    demo = demography.yearly_counts(db, world_id, start_tick, end_tick)
    pop = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    deceased = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='deceased'").fetchone()[0]
    factions = db.execute("SELECT status, COUNT(*) FROM factions WHERE world_id=? GROUP BY status", (world_id,)).fetchall()
    faction_counts = {row[0] or "unknown": row[1] for row in factions}
    events = db.execute(
        """
        SELECT event_type, COUNT(*) AS c, SUM(magnitude) AS mag
        FROM causal_events
        WHERE world_id=? AND tick_number BETWEEN ? AND ?
        GROUP BY event_type ORDER BY c DESC, mag DESC LIMIT 20
        """,
        (world_id, int(start_tick), int(end_tick)),
    ).fetchall()
    causal_highlights = [
        {"event_type": r["event_type"], "count": r["c"], "magnitude": round(float(r["mag"] or 0.0), 4)}
        for r in events
    ]
    migrations = 0
    try:
        migrations = db.execute(
            "SELECT COUNT(*) FROM demographic_events WHERE world_id=? AND tick_number BETWEEN ? AND ? AND event_type IN ('immigration','emigration')",
            (world_id, start_tick, end_tick),
        ).fetchone()[0]
    except Exception:
        pass
    macro = macro_dynamics.latest_state(db, world_id)
    return {
        "world_id": world_id,
        "year": year_number,
        "tick_range": [start_tick, end_tick],
        "population": pop,
        "deceased_total": deceased,
        "births": demo["births"],
        "deaths": demo["deaths"],
        "immigration": demo["immigration"],
        "emigration": demo["emigration"],
        "migrations": migrations,
        "factions": faction_counts,
        "macro_state": macro,
        "causal_highlights": causal_highlights,
    }


def format_yearly_report(report: dict) -> str:
    factions = ", ".join(f"{k}:{v}" for k, v in sorted(report["factions"].items())) or "none"
    top = "; ".join(f"{h['event_type']}×{h['count']}" for h in report["causal_highlights"][:6]) or "none"
    return (
        f"{report['world_id']} Y{report['year']}: pop={report['population']} "
        f"births={report['births']} deaths={report['deaths']} "
        f"imm={report['immigration']} em={report['emigration']} "
        f"factions=[{factions}] causes=[{top}]"
    )
