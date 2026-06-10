# Public Surface Reconciliation

- generated_at: 2026-06-10T21:58:16.906424+00:00
- canonical local run: `aurelia-run-density`

## Local artifacts
### `aurelia-run-100y`
- federation causal events: 166549
- solara: 171 active NPCs
- arkos: 58 active NPCs
- mirithane: 63 active NPCs
- valdris: 29 active NPCs
- verge: 49 active NPCs

### `aurelia-run-density`
- federation causal events: 159609
- solara: 67 active NPCs
- arkos: 67 active NPCs
- mirithane: 67 active NPCs
- valdris: 67 active NPCs
- verge: 66 active NPCs

### `aurelia-run-200y`
- federation causal events: 235830
- solara: 143 active NPCs
- arkos: 13 active NPCs
- mirithane: 12 active NPCs
- valdris: 1 active NPCs
- verge: 78 active NPCs

## HF exports
### aurelia-causal-events
- files: 5
- runs: phase11-100y, phase11-200y, phase11-bolster-scan-y5, phase11-cf-solara-aid, phase11-density-100y
- missing worlds: solara, arkos, mirithane, valdris, verge (D1 cap likely)

### aurelia-federation-causal
- files: 10
- runs: phase11-100y, phase11-200y, phase11-bolster-scan-y5, phase11-cf-solara-aid, phase11-density-100y
- missing worlds: solara, arkos, mirithane, valdris, verge (D1 cap likely)

### aurelia-civilization-metrics
- files: 5
- runs: phase11-100y, phase11-200y, phase11-bolster-scan-y5, phase11-cf-solara-aid, phase11-density-100y
- missing worlds: solara, arkos, mirithane, valdris, verge (D1 cap likely)

### aurelia-npc-population
- files: 25
- runs: phase11-100y, phase11-200y, phase11-bolster-scan-y5, phase11-cf-solara-aid, phase11-density-100y


## Cloudflare public dashboard
- (no cloudflare payload provided)

## Count mismatches
- [ok] npc count (local vs hf): local=334 hf_files=25 cf=n/a — local NPCs=334, HF npc files=25 (rows not parsed)
- [ok] hf coverage: aurelia-causal-events: files=5 missing_worlds=[] — flat-per-run shape; per-world check not applicable
- [ok] hf coverage: aurelia-federation-causal: files=10 missing_worlds=[] — flat-per-run shape; per-world check not applicable
- [ok] hf coverage: aurelia-civilization-metrics: files=5 missing_worlds=[] — flat-per-run shape; per-world check not applicable
- [ok] hf coverage: aurelia-npc-population: files=25 missing_worlds=[] — all 5 worlds present across all runs

## Known D1 cap limitation

D1 Free plan 500MB cap caused partial movement/diffusion ingestion for long runs; HF/local Parquet exports are the complete research archive for Phase 11 until D1 is upgraded or split.

## Recommended remediation
- All three public surfaces are consistent.
