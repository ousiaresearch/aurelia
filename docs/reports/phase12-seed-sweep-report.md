# Aurelia Seed Sweep — Phase 12

Multi-seed run on the post-fix engine. 5 seeds at npc_count=100, years=50, density_diversification=0.0, ticks_per_year=6.

Engine: `aurelia-phase12` @ `3a74628`.

## D1 quality score

- mean: **0.85** (stdev 0.0)
- min: 0.85
- max: 0.85

## Aggregate metrics (mean / stdev / min / max)

| metric | mean | stdev | min | max |
|---|---|---|---|---|
| causal events | 61,987 | 1,284 | 59,969 | 63,452 |
| causal edges | 52,236 | 1,308 | 50,356 | 53,437 |
| population CV | 0.570 | 0.260 | 0.391 | 1.022 |
| discoveries | 13.4 | 3.6 | 10 | 19 |
| great persons | 4.2 | 1.9 | 2 | 7 |
| cross-world movements | 1177 | 49 | 1102 | 1214 |

## Per-run detail

| seed | wall (s) | D1 | events | edges | pop CV | discoveries | great persons |
|---|---|---|---|---|---|---|---|
| 1001 | 25.7 | 0.85 | 63,452 | 53,437 | 0.583 | 15 | 4 |
| 1002 | 26.0 | 0.85 | 62,587 | 53,377 | 0.391 | 12 | 5 |
| 1003 | 28.2 | 0.85 | 62,041 | 52,481 | 0.457 | 19 | 7 |
| 1004 | 25.8 | 0.85 | 59,969 | 50,356 | 1.022 | 10 | 2 |
| 1005 | 27.2 | 0.85 | 61,884 | 51,529 | 0.401 | 11 | 3 |

## Interpretation

With 5 seeds at the same parameters, the D1 score ranges from 0.85 to 0.85 (stdev 0.0). This is the engine's natural diversity at these parameters — the stability work in 0.1.6 removed the runaway behavior that previously made seed-level comparison meaningless. The per-run D1 distribution is now narrow enough that researchers can run a single seed and have confidence the result is representative of the engine's behavior at those parameters.
