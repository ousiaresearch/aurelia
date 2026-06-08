#!/usr/bin/env python3
"""evaluate_phase8_run.py — acceptance gates and decade summaries for Phase 8."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


GATE_DIVERGENCE_KEYS = {"gdp_proxy", "legitimacy", "repression", "public_health", "food_security", "war_pressure", "border_openness"}
REQUIRED_OUTCOME_CLASSES = {
    "faction_integrated", "faction_suppressed", "faction_exiled", "faction_splintered",
    "faction_radicalized", "faction_legalized", "faction_governing_coalition",
    "faction_victorious", "faction_dissolved",
}


def _saturation_score(reports: list[dict], world_id: str, key: str, window: int = 10) -> int:
    """Count consecutive windows where a macro key stays at exactly 0.0 or 1.0."""
    world_reports = sorted([r for r in reports if r["world_id"] == world_id], key=lambda r: r["year"])
    max_streak = 0
    streak = 0
    for r in world_reports:
        val = r.get("macro_state", {}).get(key, 0.5)
        if val <= 0.0 or val >= 1.0:
            streak += 1
        else:
            streak = 0
        max_streak = max(max_streak, streak)
    return max_streak


def _recovery_count(reports: list[dict], world_id: str) -> int:
    world_reports = [r for r in reports if r["world_id"] == world_id]
    total = sum(r.get("resilience_events", {}).get("macro_resilience_recovery", 0) for r in world_reports)
    return total


def _pairwise_divergence(reports: list[dict], year: int) -> float:
    """Average pairwise macro distance across worlds at a given year."""
    year_reports = [r for r in reports if r["year"] == year]
    if len(year_reports) < 2:
        return 0.0
    vectors = []
    for r in year_reports:
        ms = r.get("macro_state", {})
        vectors.append([ms.get(k, 0.5) for k in sorted(GATE_DIVERGENCE_KEYS)])
    dists = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            d = sum(abs(vectors[i][k] - vectors[j][k]) for k in range(len(GATE_DIVERGENCE_KEYS))) / len(GATE_DIVERGENCE_KEYS)
            dists.append(d)
    return sum(dists) / len(dists) if dists else 0.0


def evaluate_summary(summary: dict) -> dict:
    reports = summary.get("yearly_reports", [])
    worlds = sorted(set(r["world_id"] for r in reports))
    if not reports or not worlds:
        return {"passed": False, "gates": {"error": "no reports"}, "details": {}}

    # Resilience gate
    saturated_worlds = 0
    sat_details = {}
    for world_id in worlds:
        for key in GATE_DIVERGENCE_KEYS:
            streak = _saturation_score(reports, world_id, key)
            if streak >= 10:
                saturated_worlds += 1
                sat_details[f"{world_id}.{key}"] = streak
                break  # count each world once
    sat_gate_ok = saturated_worlds <= 2

    recovery_keys = 0
    for world_id in worlds:
        if _recovery_count(reports, world_id) >= 1:
            recovery_keys += 1
    recovery_gate_ok = recovery_keys >= 1

    # Divergence gate
    div_at_30 = _pairwise_divergence(reports, 30) if summary.get("years", 0) >= 30 else _pairwise_divergence(reports, max(r["year"] for r in reports) if reports else 1)
    div_gate_ok = div_at_30 >= 0.10

    # Migration gate
    total_imm = sum(r.get("immigration", 0) for r in reports)
    total_em = sum(r.get("emigration", 0) for r in reports)
    sources_em = len(set(r["world_id"] for r in reports if r.get("emigration", 0) > 0))
    targets_im = len(set(r["world_id"] for r in reports if r.get("immigration", 0) > 0))
    mig_gate_ok = total_imm > 0 and total_em > 0 and sources_em >= 1 and targets_im >= 1

    # Faction gate
    all_outcome_classes = set()
    for r in reports:
        for key, count in r.get("faction_outcomes", {}).items():
            if count > 0:
                all_outcome_classes.add(key)
    faction_gate_ok = len(all_outcome_classes & REQUIRED_OUTCOME_CLASSES) >= 4

    # Reporting gate
    report_gate_ok = any(
        r.get("macro_regime") and r.get("migration_flows") and r.get("resilience_events") and r.get("faction_outcomes")
        for r in reports[-5:]
    )

    passed = all([sat_gate_ok, recovery_gate_ok, div_gate_ok, mig_gate_ok, faction_gate_ok, report_gate_ok])

    return {
        "passed": passed,
        "gates": {
            "resilience_saturation": {"passed": sat_gate_ok, "saturated_worlds": saturated_worlds, "details": sat_details},
            "resilience_recovery": {"passed": recovery_gate_ok, "recovering_worlds": recovery_keys},
            "divergence_at_year_30": {"passed": div_gate_ok, "avg_distance": round(div_at_30, 4)},
            "migration": {"passed": mig_gate_ok, "total_immigration": total_imm, "total_emigration": total_em, "source_worlds": sources_em, "target_worlds": targets_im},
            "faction_outcomes": {"passed": faction_gate_ok, "observed_classes": sorted(all_outcome_classes), "count": len(all_outcome_classes & REQUIRED_OUTCOME_CLASSES)},
            "reporting": {"passed": report_gate_ok},
        },
        "details": {
            "total_worlds": len(worlds),
            "total_years": summary.get("years", 0),
            "effects_scheduled": summary.get("effects_scheduled", 0),
            "effects_imported": summary.get("effects_imported", 0),
        },
    }


def write_decade_summary(summary: dict, output_dir) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    reports = summary.get("yearly_reports", [])
    worlds = sorted(set(r["world_id"] for r in reports))
    decades = []
    for decade_start in range(1, summary.get("years", 0) + 1, 10):
        decade_end = min(decade_start + 9, summary.get("years", 0))
        decade_reports = [r for r in reports if decade_start <= r["year"] <= decade_end]
        if not decade_reports:
            continue
        world_summaries = {}
        for world_id in worlds:
            wr = [r for r in decade_reports if r["world_id"] == world_id]
            if not wr:
                continue
            start_r = next((r for r in wr if r["year"] == decade_start), wr[0])
            end_r = next((r for r in wr if r["year"] == decade_end), wr[-1])
            ms_start = start_r.get("macro_state", {})
            ms_end = end_r.get("macro_state", {})
            movements = {k: round(ms_end.get(k, 0.5) - ms_start.get(k, 0.5), 3) for k in sorted(ms_start)}
            world_summaries[world_id] = {
                "population": {"start": start_r["population"], "end": end_r["population"], "delta": end_r["population"] - start_r["population"]},
                "regime": {"start": start_r.get("macro_regime", "unknown"), "end": end_r.get("macro_regime", "unknown")},
                "macro_movements": movements,
                "births": sum(r["births"] for r in wr),
                "deaths": sum(r["deaths"] for r in wr),
                "immigration": sum(r["immigration"] for r in wr),
                "emigration": sum(r["emigration"] for r in wr),
                "faction_outcomes": {k: sum(r.get("faction_outcomes", {}).get(k, 0) for r in wr) for k in REQUIRED_OUTCOME_CLASSES},
                "recovery_events": sum(r.get("resilience_events", {}).get("macro_resilience_recovery", 0) for r in wr),
            }
        decades.append({"decade": f"{decade_start}-{decade_end}", "worlds": world_summaries})

    decade_data = {"run_years": summary.get("years", 0), "worlds": worlds, "decades": decades}
    (out / "decade_summary.json").write_text(json.dumps(decade_data, indent=2, sort_keys=True))

    # Markdown artifact
    md_lines = ["# Aurelia Phase 8 Decade Summary\n"]
    md_lines.append(f"**Run:** {summary.get('years', 0)} years × {len(worlds)} worlds\n")
    for dec in decades:
        md_lines.append(f"\n## Decade {dec['decade']}\n")
        for world_id, ws in dec["worlds"].items():
            md_lines.append(f"### {world_id}")
            md_lines.append(f"- **Population:** {ws['population']['start']} → {ws['population']['end']} (Δ{ws['population']['delta']:+,})")
            md_lines.append(f"- **Regime:** {ws['regime']['start']} → {ws['regime']['end']}")
            md_lines.append(f"- **Demographics:** +{ws['births']} born, -{ws['deaths']} died, +{ws['immigration']} immigrated, -{ws['emigration']} emigrated")
            md_lines.append(f"- **Recovery events:** {ws['recovery_events']}")
            top_outcomes = sorted(ws["faction_outcomes"].items(), key=lambda x: -x[1])[:5]
            outcome_str = ", ".join(f"{k.removeprefix('faction_')}:{v}" for k, v in top_outcomes if v > 0)
            md_lines.append(f"- **Faction outcomes:** {outcome_str or 'none'}")
            top_moves = sorted(ws["macro_movements"].items(), key=lambda x: -abs(x[1]))[:6]
            move_str = ", ".join(f"{k} {v:+.3f}" for k, v in top_moves if abs(v) > 0.001)
            md_lines.append(f"- **Macro moves:** {move_str or 'stagnant'}\n")
    (out / "decade_summary.md").write_text("\n".join(md_lines))

    return decade_data


if __name__ == "__main__":
    import sys
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/aurelia-causal-run/output/causal_summary.json")
    summary = json.loads(path.read_text())
    eval_result = evaluate_summary(summary)
    decade = write_decade_summary(summary, path.parent)
    print(json.dumps({"gates": eval_result, "decade_summary_written": str(path.parent / "decade_summary.json")}, indent=2))
    if not eval_result["passed"]:
        print("\n⚠️  PHASE 8 GATES FAILED — see details above")
    else:
        print("\n✅ All Phase 8 acceptance gates passed")
