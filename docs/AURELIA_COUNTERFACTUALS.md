# Aurelia Counterfactuals

A counterfactual branch is a *paired run*: same seed, same initial draws,
one knob changed. The point is to put a number on how much one
parameter actually moves the simulation.

The simulation is deterministic per seed. Replay the same seed with
different settings and you get a different history. The two histories
are siblings: their first tick is identical, their last tick is not.
Aurelia's `compare_runs` quantifies how far they drifted.

## Headline demo

```bash
PYTHONPATH=src_template python examples/04_run_counterfactual_branch.py
```

This runs two 50-year simulations at `npc_count=80` and `seed=1001`:

- **baseline**: `density_diversification=0.0` (the default — worlds drift
  on their own demographic trajectories)
- **branch**: `density_diversification=1.0` (the federation explicitly
  rebalances populations each tick)

Then it calls `compare_runs` and prints a divergence report.

Expected wall time on an M3 Mac: ~90 seconds. The point is
reproducibility, not scale.

### What the output looks like

```
=== Counterfactual Divergence Report ===
divergence_score: 5104.4062
warnings:         none

Top changed event types:
  reconciliation_process              delta=    +219
  institution_benefit_applied         delta=    -129
  sovereignty_charter                 delta=    +110
  capital_formation                   delta=    +106
  emigration                          delta=     -86
  migration_outflow                   delta=     -86
  macro_tension_decay                 delta=     +67
  immigration                         delta=     -45

Per-world deltas:
  arkos      events= +248  edges=  +328  resource=+0.009  education=+0.006  disease=-0.020
  mirithane  events= -408  edges=  -454  resource=-0.009  education=+0.003  disease=+0.012
  solara     events=+2,080  edges=+2,275  resource=-0.033  education=+0.000  disease=+0.033
  valdris    events= -523  edges=  -382  resource=+0.074  education=+0.027  disease=-0.151
  verge      events=-1,483  edges=-1,252  resource=-0.009  education=+0.003  disease=+0.016
```

Reading this: under density_diversification=1.0, **solara absorbs 2,080
extra events and 2,275 extra causal edges** (it's the destination of
the federation's rebalancing carrier); **verge loses 1,483 events**
(it's a chronic source of migration). The migration flow deltas confirm
the story: `emigration -86`, `immigration -45`, `migration_outflow -86`.

The **divergence score** is `total_event_delta + total_metric_delta +
0.25 × type_churn`. A zero score means the branch is a no-op (the
intervention had no observable effect) and triggers a warning. A large
score like 5,104 means the two histories genuinely diverged.

## The two patterns

There are two ways to produce a counterfactual pair.

### 1. Paired simulation (the example above)

Same seed, two `run_causal_simulation` calls with one parameter
different, then `compare_runs`. Use this for "what if this knob were
different?" questions.

Knobs that produce interesting counterfactuals:

| Knob | Range | What changes |
|---|---|---|
| `density_diversification` | 0.0–1.0 | how aggressively the federation rebalances populations |
| `seed` | any int | the entire history (use this for diversity sweeps, not for "what if") |
| `npc_count` | int | how many NPCs each world starts with |
| `ticks_per_year` | int | temporal resolution |
| `max_interactions` | int | per-tick micro-interaction cap |

### 2. Post-run intervention (modify the ledger)

For when you want to ask "what if this specific metric had been
different at this specific tick?" without re-running the simulation.
The intervention is a JSON file that names which world, which tick,
which fields, and by how much.

```python
from src_template.counterfactuals import apply_intervention_file, compare_runs

manifest = apply_intervention_file(
    baseline_dir="/path/to/baseline",
    branch_dir="/path/to/branch",
    intervention_file="my_intervention.json",
)
comparison = compare_runs("/path/to/baseline", "/path/to/branch")
```

The intervention file format:

```json
{
  "branch_id": "double_education_tick_50",
  "base_seed": 1001,
  "interventions": [
    {
      "type": "metric_delta",
      "world_id": "verge",
      "tick": 50,
      "payload": {
        "duration_ticks": 12,
        "education_level": 0.10
      }
    }
  ]
}
```

`apply_intervention_file` copies the baseline directory, applies each
intervention to the SQLite ledger, and writes a `counterfactual_manifest.json`
to the branch directory recording what was changed.

### Which pattern to use

- **Paired simulation** for parameter sweeps (any knob in
  `run_causal_simulation`).
- **Post-run intervention** for "what if this specific thing had
  happened" history rewrites.

Both produce the same `compare_runs` output. The script chooses the
pattern; the analysis layer is the same.

## What `compare_runs` actually measures

For each world, `compare_runs` reports:

- `causal_events_delta` and `causal_edges_delta` — the most direct
  measure of "how much happened" differently
- `avg_resource_stock_delta`, `avg_education_level_delta`,
  `avg_disease_pressure_delta` — average of the metric over the full
  run, baseline vs branch

The deltas are summed across worlds to produce the `divergence_score`,
combined with `0.25 × type_churn` (total absolute change in
event-type counts across all worlds). A score near zero means the
branch is a no-op.

## See also

- [`src_template/counterfactuals.py`](../src_template/counterfactuals.py) —
  the underlying module
- [`tests/test_counterfactuals.py`](../tests/test_counterfactuals.py) —
  test coverage of the intervention format
- [`scripts/run_counterfactual.py`](../scripts/run_counterfactual.py) —
  CLI entry point for the post-run intervention pattern
- [`examples/04_run_counterfactual_branch.py`](../examples/04_run_counterfactual_branch.py) —
  the headline demo
- [`AURELIA_RESEARCH_START_HERE.md`](AURELIA_RESEARCH_START_HERE.md) —
  where this guide fits in the researcher track
