"""yearly_report.py — causal yearly summaries for Aurelia."""
from __future__ import annotations

import json

try:
    from . import demography, macro_dynamics, capital_economy
except Exception:
    import demography
    import macro_dynamics
    import capital_economy


def classify_macro_regime(macro: dict[str, float]) -> str:
    """Classify macro state into a political regime label."""
    w = macro.get("war_pressure", 0.0)
    l = macro.get("legitimacy", 0.5)
    r = macro.get("repression", 0.3)
    gdp = macro.get("gdp_proxy", 0.5)
    ph = macro.get("public_health", 0.6)
    fs = macro.get("food_security", 0.6)
    bo = macro.get("border_openness", 0.5)
    tt = macro.get("type_tension", 0.3)

    if w > 0.70 or (w > 0.45 and l < 0.30):
        return "civil_conflict"
    if l < 0.25 and r > 0.75:
        return "authoritarian"
    if l < 0.35 and r > 0.55:
        return "repressive_regime"
    if l > 0.70 and r < 0.20 and gdp > 0.55:
        return "stable_growth"
    if r < 0.15 and l > 0.55 and ph > 0.65:
        return "welfare_state"
    if bo > 0.65 and l > 0.55:
        return "open_market"
    if tt > 0.60 and l < 0.45:
        return "ethnic_tensions"
    if fs < 0.35 and ph < 0.40:
        return "humanitarian_crisis"
    if r < 0.25 and l > 0.45 and gdp > 0.45:
        return "managed_pluralism"
    if l < 0.45 and r > 0.40:
        return "competitive_authoritarianism"
    if bo < 0.30 and r > 0.50:
        return "closed_regime"
    return "transitional"


def build_yearly_report(db, *, world_id: str, year_number: int, start_tick: int, end_tick: int) -> dict:
    demo = demography.yearly_counts(db, world_id, start_tick, end_tick)
    pop = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
    deceased = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='deceased'").fetchone()[0]
    emigrated = db.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='emigrated'").fetchone()[0]
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
    migrations_total = 0
    try:
        migrations_total = db.execute(
            "SELECT COUNT(*) FROM demographic_events WHERE world_id=? AND tick_number BETWEEN ? AND ? AND event_type IN ('immigration','emigration')",
            (world_id, start_tick, end_tick),
        ).fetchone()[0]
    except Exception:
        pass

    resilience_events = {}
    try:
        resilience_rows = db.execute(
            "SELECT event_type, COUNT(*) FROM causal_events WHERE world_id=? AND tick_number BETWEEN ? AND ? AND event_type IN ('macro_resilience_recovery','macro_tension_decay') GROUP BY event_type",
            (world_id, start_tick, end_tick),
        ).fetchall()
        resilience_events = {row[0]: row[1] for row in resilience_rows}
    except Exception:
        pass

    faction_outcome_events = {}
    try:
        faction_rows = db.execute(
            "SELECT event_type, COUNT(*) FROM causal_events WHERE world_id=? AND tick_number BETWEEN ? AND ? AND event_type LIKE 'faction_%' GROUP BY event_type",
            (world_id, start_tick, end_tick),
        ).fetchall()
        faction_outcome_events = {row[0]: row[1] for row in faction_rows}
    except Exception:
        pass

    macro = macro_dynamics.latest_state(db, world_id)

    # Phase 9: capital economy snapshot
    capital_snapshot = {}
    try:
        pool = capital_economy.get_pool(db, world_id)
        capital_snapshot = {
            "stock": round(pool["stock"], 3),
            "gdp_flow": round(pool["gdp_flow"], 4),
            "investment_rate": round(pool["investment_rate"], 3),
            "tech_level": round(pool["tech_level"], 3),
            "innovation_stock": round(pool["innovation_stock"], 3),
        }
    except Exception:
        pass

    # Phase 9: institutions snapshot
    institutions_snapshot = []
    try:
        inst_rows = db.execute(
            "SELECT institution_id, type, status, durability, influence FROM institutions WHERE world_id=? AND status='active'",
            (world_id,),
        ).fetchall()
        institutions_snapshot = [
            {"type": r["type"], "durability": round(r["durability"], 2), "influence": round(r["influence"], 2)}
            for r in inst_rows
        ]
    except Exception:
        pass

    # Phase 9: regime events in this year
    regime_events_yr = []
    try:
        re_rows = db.execute(
            "SELECT event_type, resolution_path FROM regime_events WHERE world_id=? AND tick_number BETWEEN ? AND ?",
            (world_id, start_tick, end_tick),
        ).fetchall()
        regime_events_yr = [{"event_type": r["event_type"], "path": r["resolution_path"]} for r in re_rows]
    except Exception:
        pass

    return {
        "world_id": world_id,
        "year": year_number,
        "tick_range": [start_tick, end_tick],
        "population": pop,
        "deceased_total": deceased,
        "emigrated_total": emigrated,
        "births": demo["births"],
        "deaths": demo["deaths"],
        "immigration": demo["immigration"],
        "emigration": demo["emigration"],
        "migration_flows": {"immigration": demo["immigration"], "emigration": demo["emigration"], "net": demo["immigration"] - demo["emigration"]},
        "migrations": migrations_total,
        "factions": faction_counts,
        "faction_outcomes": faction_outcome_events,
        "resilience_events": resilience_events,
        "macro_state": macro,
        "macro_regime": classify_macro_regime(macro),
        "capital": capital_snapshot,
        "institutions": institutions_snapshot,
        "regime_events": regime_events_yr,
        "causal_highlights": causal_highlights,
    }


def format_yearly_report(report: dict) -> str:
    factions = ", ".join(f"{k}:{v}" for k, v in sorted(report["factions"].items())) or "none"
    top = "; ".join(f"{h['event_type']}×{h['count']}" for h in report["causal_highlights"][:6]) or "none"
    return (
        f"{report['world_id']} Y{report['year']}: pop={report['population']} "
        f"births={report['births']} deaths={report['deaths']} "
        f"imm={report['immigration']} em={report['emigration']} "
        f"regime={report['macro_regime']} "
        f"factions=[{factions}] causes=[{top}]"
    )
