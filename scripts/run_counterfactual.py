#!/usr/bin/env python3
"""Create an Aurelia counterfactual branch from a baseline run directory."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src_template.counterfactuals import apply_intervention_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-output", type=Path, required=True)
    parser.add_argument("--branch-output", type=Path, required=True)
    parser.add_argument("--intervention", type=Path, required=True)
    parser.add_argument("--run-baseline", action="store_true", help="run causal_run.py before branching")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--npcs", type=int, default=200)
    parser.add_argument("--ticks-per-year", type=int, default=12)
    parser.add_argument("--max-interactions", type=int, default=120)
    parser.add_argument("--seed", type=int, default=4242)
    args = parser.parse_args()

    if args.run_baseline:
        cmd = [
            sys.executable, str(ROOT / "causal_run.py"), "--clean",
            "--output", str(args.baseline_output),
            "--years", str(args.years),
            "--npcs", str(args.npcs),
            "--ticks-per-year", str(args.ticks_per_year),
            "--max-interactions", str(args.max_interactions),
            "--seed", str(args.seed),
        ]
        subprocess.run(cmd, cwd=ROOT, check=True)

    manifest = apply_intervention_file(args.baseline_output, args.branch_output, args.intervention)
    print(f"created counterfactual branch {manifest['branch_id']} at {args.branch_output}")
    print(f"interventions applied: {manifest['interventions_applied']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
