"""Post-fix re-score of the Phase 11 targets.

Reproduces the original Phase 11 reports' parameters:
  - 100y: 600 ticks (6 tpy), npc=100, seed=1001
  - 200y: 1200 ticks (6 tpy), npc=100, seed=2002
  - density-100y: 600 ticks (6 tpy), npc=100, seed=3003, density=0.7

Writes fresh quality JSONs and report markdowns to /tmp for
inspection, then the script's stdout can be used to update
docs/reports/phase11-*-{quality.json,report.md}.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path("/Users/johann/aurelia")
sys.path.insert(0, str(ROOT / "src_template"))

import federation_orchestrator
sys.path.insert(0, str(ROOT))
from evaluate_run_quality import evaluate_run  # type: ignore


def run(label: str, *, years: int, npc_count: int, seed: int, density: float, out_dir: Path) -> dict:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    summary = federation_orchestrator.run_causal_simulation(
        output_dir=out_dir, years=years, npc_count=npc_count, seed=seed,
        ticks_per_year=6, density_diversification=density,
    )
    quality = evaluate_run(out_dir)
    return {"label": label, "wall": time.time() - t0, "summary": summary, "quality": quality, "out_dir": out_dir}


def main():
    base = Path("/tmp/aurelia-postfix")
    base.mkdir(parents=True, exist_ok=True)
    runs = []
    for spec in [
        {"label": "phase11-100y-seed1001", "years": 100, "npc": 100, "seed": 1001, "density": 0.0},
        {"label": "phase11-200y-seed2002", "years": 200, "npc": 100, "seed": 2002, "density": 0.0},
        {"label": "phase11-density-100y-d07-seed3003", "years": 100, "npc": 100, "seed": 3003, "density": 0.7},
    ]:
        print(f"[start] {spec['label']}", flush=True)
        out_dir = base / spec["label"]
        r = run(spec["label"], years=spec["years"], npc_count=spec["npc"],
                seed=spec["seed"], density=spec["density"], out_dir=out_dir)
        r["label"] = spec["label"]
        runs.append(r)
        print(f"[done]  {spec['label']} wall={r['wall']:.0f}s  D1={r['quality'].get('overall_score')}",
              flush=True)
        # Save quality JSON
        qpath = out_dir / "quality.json"
        qpath.write_text(json.dumps(r["quality"], indent=2))
        print(f"[save]  {qpath}")

    print("\n=== Summary ===")
    for r in runs:
        q = r["quality"]
        c = q["counts"]
        print(f"{r['label']:42s}  events={c['causal_events']:>7,}  edges={c['causal_edges']:>7,}  "
              f"D1={q['overall_score']}  pop_cv={c['population_cv']:.3f}  "
              f"discoveries={c['discoveries']}  great_persons={c['great_persons']}")


if __name__ == "__main__":
    main()
