# Aurelia Run Comparison

Side-by-side comparison of completed Aurelia runs. Population stats use the active NPC count from each world's SQLite DB.

## Population balance across the 5 worlds

| run | solara | valdris | mirithane | arkos | verge | mean | stddev | range | cv |
|---|---|---|---|---|---|---|---|---|---|
| 100y-baseline | 171 | 29 | 63 | 58 | 49 | 74.0 | 49.9 | 142 | 0.674 |
| 200y-baseline | 143 | 1 | 12 | 13 | 78 | 49.4 | 54.1 | 142 | 1.096 |
| density-100y-d07 | 67 | 67 | 67 | 67 | 66 | 66.8 | 0.4 | 1 | 0.006 |

## Per-run causal + civilization totals

| run | causal events | causal edges | metric rows | discoveries | great persons | movements | diffusion |
|---|---|---|---|---|---|---|---|
| 100y-baseline | 306025 | 129203 | 3000 | 65 | 19 | 3066 | 600 |
| 200y-baseline | 433012 | 155660 | 6000 | 68 | 19 | 3629 | 1200 |
| density-100y-d07 | 293267 | 123234 | 3000 | 75 | 22 | 3644 | 600 |

## Civilization metric means (per world, last 5 ticks)

### 100y-baseline

| world | avg_education | avg_urbanization | avg_youth_bulge | avg_disease_pressure | avg_resource_stock | avg_property_rights |
|---|---|---|---|---|---|---|
| arkos | 0.322 | 0.259 | 0.82 | 0.756 | 0.349 | 0.198 |
| mirithane | 0.328 | 0.257 | 1.0 | 0.16 | 0.613 | 0.547 |
| solara | 0.33 | 0.252 | 0.853 | 0.189 | 0.698 | 0.685 |
| valdris | 0.323 | 0.263 | 1.0 | 0.334 | 0.596 | 0.6 |
| verge | 0.322 | 0.254 | 0.9 | 0.749 | 0.351 | 0.208 |

### 200y-baseline

| world | avg_education | avg_urbanization | avg_youth_bulge | avg_disease_pressure | avg_resource_stock | avg_property_rights |
|---|---|---|---|---|---|---|
| arkos | 0.311 | 0.282 | 1.0 | 0.751 | 0.35 | 0.195 |
| mirithane | 0.307 | 0.25 | 1.0 | 0.074 | 0.685 | 0.554 |
| solara | 0.33 | 0.252 | 0.799 | 0.07 | 0.949 | 0.689 |
| valdris | 0.208 | 1.0 | 1.0 | 0.247 | 0.831 | 0.65 |
| verge | 0.321 | 0.258 | 1.0 | 0.746 | 0.35 | 0.201 |

### density-100y-d07

| world | avg_education | avg_urbanization | avg_youth_bulge | avg_disease_pressure | avg_resource_stock | avg_property_rights |
|---|---|---|---|---|---|---|
| arkos | 0.322 | 0.253 | 1.0 | 0.754 | 0.35 | 0.394 |
| mirithane | 0.327 | 0.257 | 1.0 | 0.156 | 0.615 | 0.555 |
| solara | 0.327 | 0.253 | 1.0 | 0.266 | 0.63 | 0.681 |
| valdris | 0.327 | 0.257 | 1.0 | 0.21 | 0.652 | 0.647 |
| verge | 0.324 | 0.251 | 1.0 | 0.748 | 0.351 | 0.258 |

## Diversification effect

- **baseline** (e.g. `/tmp/aurelia-run-100y`) mean=74.0 stddev=49.9 cv=0.674 range=142
- **density** (e.g. `/tmp/aurelia-run-density`) mean=66.8 stddev=0.4 cv=0.006 range=1

- **coefficient of variation reduction**: 0.668 (99.1% lower)
- **stddev reduction**: 49.5

Interpretation: lower stddev/CV means the density_diversification knob successfully equalized the world populations.

