# Aurelia Run Comparison

Side-by-side comparison of completed Aurelia runs. Population stats use the active NPC count from each world's SQLite DB. **Post-fix** (2026-06-11, CHANGELOG 0.1.6) — the engine stability work capped four feedback loops, so numbers here are smaller and more honest than the pre-fix baseline.

## Population balance across the 5 worlds

| run | solara | valdris | mirithane | arkos | verge | mean | stddev | range | cv |
|---|---|---|---|---|---|---|---|---|---|
| 100y-baseline | 21 | 0 | 3 | 30 | 38 | 18.4 | 14.8 | 38 | 0.807 |
| 200y-baseline | 35 | 4 | 3 | 8 | 12 | 12.4 | 11.7 | 32 | 0.947 |
| density-100y-d07 | 27 | 28 | 27 | 27 | 27 | 27.2 | 0.4 | 1 | 0.015 |

## Per-run causal + civilization totals

| run | causal events | causal edges | metric rows | discoveries | great persons | movements | diffusion |
|---|---|---|---|---|---|---|---|
| 100y-baseline | 92632 | 65133 | 3000 | 16 | 4 | 1479 | 600 |
| 200y-baseline | 142178 | 82509 | 6000 | 11 | 3 | (see quality.json) | 1200 |
| density-100y-d07 | 90028 | 63928 | 3000 | 12 | 4 | (see quality.json) | 600 |

## Civilization metric means (per world, last 5 ticks)

### 100y-baseline

| world | avg_education | avg_urbanization | avg_youth_bulge | avg_disease_pressure | avg_resource_stock | avg_property_rights |
|---|---|---|---|---|---|---|
| arkos | 0.319 | 0.258 | 0.922 | 0.602 | 0.431 | 0.349 |
| mirithane | 0.307 | 0.310 | 0.951 | 0.232 | 0.601 | 0.524 |
| solara | 0.318 | 0.272 | 0.970 | 0.228 | 0.695 | 0.650 |
| valdris | 0.310 | 0.279 | 0.939 | 0.536 | 0.471 | 0.356 |
| verge | 0.315 | 0.270 | 0.927 | 0.605 | 0.429 | 0.239 |

### 200y-baseline

| world | avg_education | avg_urbanization | avg_youth_bulge | avg_disease_pressure | avg_resource_stock | avg_property_rights |
|---|---|---|---|---|---|---|
| arkos | 0.273 | 0.362 | 0.734 | 0.704 | 0.388 | 0.207 |
| mirithane | 0.282 | 0.397 | 0.904 | 0.242 | 0.615 | 0.531 |
| solara | 0.323 | 0.259 | 0.826 | 0.154 | 0.802 | 0.667 |
| valdris | 0.268 | 0.372 | 0.836 | 0.678 | 0.398 | 0.411 |
| verge | 0.316 | 0.266 | 0.985 | 0.681 | 0.389 | 0.209 |

### density-100y-d07

| world | avg_education | avg_urbanization | avg_youth_bulge | avg_disease_pressure | avg_resource_stock | avg_property_rights |
|---|---|---|---|---|---|---|
| arkos | 0.318 | 0.260 | 0.925 | 0.615 | 0.427 | 0.231 |
| mirithane | 0.323 | 0.263 | 0.922 | 0.246 | 0.589 | 0.522 |
| solara | 0.321 | 0.262 | 0.925 | 0.288 | 0.630 | 0.613 |
| valdris | 0.319 | 0.260 | 0.915 | 0.573 | 0.452 | 0.336 |
| verge | 0.318 | 0.261 | 0.932 | 0.615 | 0.427 | 0.221 |

## Diversification effect

- **baseline** (e.g. `/tmp/aurelia-run-100y`) mean=18.4 stddev=14.8 cv=0.807 range=38
- **density** (e.g. `/tmp/aurelia-run-density`) mean=27.2 stddev=0.4 cv=0.015 range=1

- **coefficient of variation reduction**: 0.792 (98.1% lower)
- **stddev reduction**: 14.4

Interpretation: lower stddev/CV means the density_diversification knob successfully equalized the world populations. The absolute populations are smaller than the original Phase 11 report (post-fix) but the diversification effect is preserved.

## Differences from the pre-fix report

The original Phase 11 reports (2026-06-09) showed 100y at 139,476 events with
populations [171, 29, 63, 58, 49]. The post-fix reports (2026-06-11) show
100y at 92,632 events with populations [30, 21, 3, 0, 38]. The 33% drop in
event volume is from the four feedback loops being capped; the population
differences are from the engine dynamics interacting differently once the
loops no longer dominate. The diversification effect (CV reduction
98.1%, stddev reduction 14.4) is the headline behavior and is preserved.

## Multi-seed sweep (Phase 12)

Five seeds at npc_count=100, years=50, density=0.0, ticks_per_year=6:

| seed | D1 | events | edges | pop CV | discoveries | great persons |
|---|---|---|---|---|---|---|
| 1001 | 0.85 | 63,452 | 53,437 | 0.583 | 15 | 4 |
| 1002 | 0.85 | 62,587 | 53,377 | 0.391 | 12 | 5 |
| 1003 | 0.85 | 62,041 | 52,481 | 0.457 | 19 | 7 |
| 1004 | 0.85 | 59,969 | 50,356 | 1.022 | 10 | 2 |
| 1005 | 0.85 | 61,884 | 51,529 | 0.401 | 11 | 3 |

Aggregate: mean events 61,987 ± 1,284 (2.1% stdev/mean), mean D1 0.85 (zero
variance — all five seeds cleared the same gates). The full sweep
report is at `docs/reports/phase12-seed-sweep-report.md`.

