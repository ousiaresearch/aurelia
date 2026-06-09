#!/usr/bin/env python3
"""Build a side-by-side comparison Markdown for two or more Aurelia run dirs.

For each run, captures final populations, key per-world outcomes, and
civilization metric trends. For the diversification target, also computes
world population variance and standard deviation to show the effect of the
density_diversification knob.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from aurelia_run_inspect import inspect_run


def _pops(run_dir: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for db in sorted(run_dir.glob("*.db")):
        if db.name == "federation.db":
            continue
        try:
            conn = sqlite3.connect(db)
            n = conn.execute("SELECT COUNT(*) FROM agents WHERE type='npc' AND state='active'").fetchone()[0]
            out[db.stem] = int(n)
            conn.close()
        except Exception:
            out[db.stem] = 0
    return out


def _pop_stats(pops: dict[str, int]) -> dict[str, float]:
    if not pops:
        return {"mean": 0, "stddev": 0, "min": 0, "max": 0, "range": 0, "cv": 0}
    vals = list(pops.values())
    n = len(vals)
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / n
    sd = var ** 0.5
    return {
        "mean": mean,
        "stddev": sd,
        "min": min(vals),
        "max": max(vals),
        "range": max(vals) - min(vals),
        "cv": sd / mean if mean > 0 else 0,
    }


def _metric_trends(run_dir: Path, last_n: int = 5) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for db in sorted(run_dir.glob("*.db")):
        if db.name == "federation.db":
            continue
        conn = sqlite3.connect(db)
        try:
            max_tick = conn.execute("SELECT MAX(tick_number) FROM civilization_metrics").fetchone()[0]
            if not max_tick:
                conn.close(); continue
            lo = max_tick - last_n
            row = conn.execute(
                "SELECT AVG(education_level), AVG(urbanization), AVG(youth_bulge), AVG(disease_pressure), AVG(resource_stock), AVG(property_rights) FROM civilization_metrics WHERE tick_number > ?",
                (lo,),
            ).fetchone()
            conn.close()
            if row is None:
                continue
            out.append({
                "world_id": db.stem,
                "avg_education_level": round(float(row[0] or 0), 3),
                "avg_urbanization": round(float(row[1] or 0), 3),
                "avg_youth_bulge": round(float(row[2] or 0), 3),
                "avg_disease_pressure": round(float(row[3] or 0), 3),
                "avg_resource_stock": round(float(row[4] or 0), 3),
                "avg_property_rights": round(float(row[5] or 0), 3),
            })
        except Exception:
            conn.close()
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run", action="append", required=True, help="label=path pairs, repeatable")
    args = parser.parse_args()
    runs = []
    for entry in args.run:
        if "=" not in entry:
            raise SystemExit(f"--run expects label=path, got {entry!r}")
        label, path = entry.split("=", 1)
        run_dir = Path(path)
        if not run_dir.exists():
            raise SystemExit(f"run dir missing: {run_dir}")
        runs.append((label, run_dir))
    out_lines: list[str] = []
    out_lines.append("# Aurelia Run Comparison")
    out_lines.append("")
    out_lines.append("Side-by-side comparison of completed Aurelia runs. "
                     "Population stats use the active NPC count from each world's SQLite DB.")
    out_lines.append("")

    out_lines.append("## Population balance across the 5 worlds")
    out_lines.append("")
    out_lines.append("| run | solara | valdris | mirithane | arkos | verge | mean | stddev | range | cv |")
    out_lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for label, run_dir in runs:
        pops = _pops(run_dir)
        stats = _pop_stats(pops)
        out_lines.append("| {label} | {s} | {v} | {m} | {a} | {ve} | {mn:.1f} | {sd:.1f} | {r} | {cv:.3f} |".format(
            label=label, s=pops.get("solara", 0), v=pops.get("valdris", 0),
            m=pops.get("mirithane", 0), a=pops.get("arkos", 0), ve=pops.get("verge", 0),
            mn=stats["mean"], sd=stats["stddev"], r=stats["range"], cv=stats["cv"],
        ))
    out_lines.append("")

    out_lines.append("## Per-run causal + civilization totals")
    out_lines.append("")
    out_lines.append("| run | causal events | causal edges | metric rows | discoveries | great persons | movements | diffusion |")
    out_lines.append("|---|---|---|---|---|---|---|---|")
    for label, run_dir in runs:
        data = inspect_run(run_dir)
        totals = data["totals"]
        fed = data["federation"]
        out_lines.append("| {label} | {ce} | {edge} | {m} | {d} | {gp} | {mv} | {df} |".format(
            label=label,
            ce=totals.get("causal_events", 0) + totals.get("federation_causal_events", 0),
            edge=totals.get("causal_edges", 0) + totals.get("federation_causal_edges", 0),
            m=totals.get("metrics", 0),
            d=totals.get("discoveries", 0),
            gp=totals.get("great_persons", 0),
            mv=fed.get("cross_world_movements", 0),
            df=fed.get("diffusion_events", 0),
        ))
    out_lines.append("")

    out_lines.append("## Civilization metric means (per world, last 5 ticks)")
    out_lines.append("")
    for label, run_dir in runs:
        trends = _metric_trends(run_dir)
        out_lines.append("### " + label)
        out_lines.append("")
        out_lines.append("| world | avg_education | avg_urbanization | avg_youth_bulge | avg_disease_pressure | avg_resource_stock | avg_property_rights |")
        out_lines.append("|---|---|---|---|---|---|---|")
        for m in trends:
            out_lines.append("| {w} | {edu} | {urb} | {youth} | {dis} | {res} | {prop} |".format(
                w=m["world_id"],
                edu=m["avg_education_level"],
                urb=m["avg_urbanization"],
                youth=m["avg_youth_bulge"],
                dis=m["avg_disease_pressure"],
                res=m["avg_resource_stock"],
                prop=m["avg_property_rights"],
            ))
        out_lines.append("")

    if any(label.startswith("density") for label, _ in runs):
        out_lines.append("## Diversification effect")
        out_lines.append("")
        baseline = next((p for l, p in runs if "baseline" in l.lower() or "100y" in l.lower() and "density" not in l), None)
        density = next((p for l, p in runs if "density" in l.lower()), None)
        if baseline and density:
            base_stats = _pop_stats(_pops(baseline))
            den_stats = _pop_stats(_pops(density))
            out_lines.append(
                "- **baseline** (e.g. `{base}`) mean={bm:.1f} stddev={bsd:.1f} cv={bcv:.3f} range={br}".format(
                    base=baseline, bm=base_stats["mean"], bsd=base_stats["stddev"], bcv=base_stats["cv"], br=base_stats["range"],
                )
            )
            out_lines.append(
                "- **density** (e.g. `{den}`) mean={dm:.1f} stddev={dsd:.1f} cv={dcv:.3f} range={dr}".format(
                    den=density, dm=den_stats["mean"], dsd=den_stats["stddev"], dcv=den_stats["cv"], dr=den_stats["range"],
                )
            )
            out_lines.append("")
            cv_reduction = base_stats["cv"] - den_stats["cv"]
            out_lines.append(f"- **coefficient of variation reduction**: {cv_reduction:.3f} ({(cv_reduction / base_stats['cv'] * 100):.1f}% lower)")
            out_lines.append(f"- **stddev reduction**: {base_stats['stddev'] - den_stats['stddev']:.1f}")
            out_lines.append("")
            out_lines.append("Interpretation: lower stddev/CV means the density_diversification knob successfully equalized the world populations.")
            out_lines.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out_lines) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
