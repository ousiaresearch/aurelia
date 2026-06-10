# Aurelia HF dataset social pack

Status: approval-ready drafts. Do not post until Anduril explicitly approves.

Branding: OUSIA RESEARCH wordmark, Nous v9 imprint aesthetic. Do not use NOUS wordmark for these assets because the datasets live under `OusiaResearch/*`.

Posting account: @PLNTRProtocol only with approval.

Primary links:
- Repo: https://github.com/ousiaresearch/aurelia
- Causal events: https://huggingface.co/datasets/OusiaResearch/aurelia-causal-events
- Civilization metrics: https://huggingface.co/datasets/OusiaResearch/aurelia-civilization-metrics
- Federation causal: https://huggingface.co/datasets/OusiaResearch/aurelia-federation-causal
- NPC population: https://huggingface.co/datasets/OusiaResearch/aurelia-npc-population
- Observatory: https://hermes-state-worker.plntrprotocol.workers.dev/public/aurelia/observatory

Image files:
- Omnibus: `/tmp/hf-promo-v2/output/omnibus-v9-final.png`
- Causal events: `/tmp/hf-promo-v2/output/causal-events-v9-final.png`
- Civilization metrics: `/tmp/hf-promo-v2/output/civilization-metrics-v9-final.png`
- Federation causal: `/tmp/hf-promo-v2/output/federation-causal-v9-final.png`
- NPC population: `/tmp/hf-promo-v2/output/npc-population-v9-final.png`

Known image note:
- `causal-events-v9-final.png` has a small generated-text mutation: subtitle resembles `CAJISAI EVENTS` instead of `CAUSAL EVENTS`. Use it only if we accept the artifact. Otherwise regenerate/fix before posting.

## Recommended cadence

1. Launch thread with omnibus image.
2. Dataset spotlight 1: causal events.
3. Dataset spotlight 2: civilization metrics.
4. Dataset spotlight 3: federation causal.
5. Dataset spotlight 4: NPC population.
6. Optional follow-up: density-diversification result.

Spacing: 1 launch thread, then 1 spotlight every 4-8 hours or daily. Do not post all five images at once unless intentionally doing a launch burst.

## Launch thread

Attach image: `/tmp/hf-promo-v2/output/omnibus-v9-final.png`

### Tweet 1

Aurelia is now on Hugging Face.

I ran the simulation, exported the runs, built the dataset cards, pushed the Parquet files, verified the round trip, and packaged the whole thing as four public civilization datasets under Ousia Research.

https://huggingface.co/OusiaResearch

### Tweet 2

The current release is four separate datasets, not one blob:

1. causal event streams
2. yearly civilization metrics
3. federation-level causal graphs
4. final NPC population snapshots

Each repo is small enough to load directly and specific enough to use without excavation.

### Tweet 3

The dataset is synthetic, but the structure is not toy data.

Five worlds. Multi-year runs. Causal events. Causal edges. Civilization metrics. Movement. Diffusion. NPC snapshots. Counterfactual branches.

The point is to make simulated civilization legible enough to study.

### Tweet 4

The current export includes:

- 560,428 causal event rows
- 12,600 civilization metric rows
- 114,133 federation causal rows
- 25,799 NPC population rows
- ~35 MB of Parquet
- CC-BY-4.0

Small enough to inspect. Large enough to ask real questions.

### Tweet 5

One result from the latest targeted run:

The density-diversification lever cut cross-world population imbalance by 99.1%.

Baseline CV: 0.674
Density run CV: 0.006

That is the difference between a decorative parameter and a real causal handle.

### Tweet 6

This is what I want from agent-run research:

Not a demo screenshot. Not a vibes post. A machine that runs, measures, exports, publishes, and leaves artifacts other people can inspect.

Aurelia is public now.

Start here:
https://github.com/ousiaresearch/aurelia

## Short launch alternative

Attach image: `/tmp/hf-promo-v2/output/omnibus-v9-final.png`

Aurelia is live on Hugging Face.

Four public civilization-simulation datasets from Ousia Research: causal events, civilization metrics, federation causal graphs, and NPC population snapshots.

560k+ event rows. CC-BY-4.0. Parquet.

https://huggingface.co/OusiaResearch

## Dataset spotlight posts

### 1. Causal events

Attach image: `/tmp/hf-promo-v2/output/causal-events-v9-final.png`

Alt text:
OUSIA RESEARCH xerox-style cyan and black technical poster for the Aurelia causal events dataset. Distressed print texture, halftone dots, and archival simulation-world motifs.

Draft:

Dataset 1/4: Aurelia causal events.

560,428 rows of per-world causal traces: run, world, year, event type, actors, targets, strength, confidence, causal factor, payload.

The event stream, not the summary.

https://huggingface.co/datasets/OusiaResearch/aurelia-causal-events

Note before posting:
This image has the small `CAJISAI EVENTS` text mutation. Approve artifact or regenerate first.

### 2. Civilization metrics

Attach image: `/tmp/hf-promo-v2/output/civilization-metrics-v9-final.png`

Alt text:
Distressed OUSIA RESEARCH letterpress manual cover for the Aurelia civilization metrics dataset, with aged paper, dark technical borders, and print scuffs.

Draft:

Dataset 2/4: Aurelia civilization metrics.

12,600 yearly world-state rows: education, urbanization, disease pressure, resources, property rights, and more.

Best entry point for analysis.

https://huggingface.co/datasets/OusiaResearch/aurelia-civilization-metrics

### 3. Federation causal

Attach image: `/tmp/hf-promo-v2/output/federation-causal-v9-final.png`

Alt text:
OUSIA RESEARCH analog newspaper-style technical dossier for the Aurelia federation causal dataset, printed with rough halftone, scuffed borders, and archival data marks.

Draft:

Dataset 3/4: Aurelia federation causal.

114,133 rows from the layer above the worlds: federation events plus causal edges.

This is where five isolated histories become a shared system.

https://huggingface.co/datasets/OusiaResearch/aurelia-federation-causal

### 4. NPC population

Attach image: `/tmp/hf-promo-v2/output/npc-population-v9-final.png`

Alt text:
Deep blue and orange OUSIA RESEARCH registration-style character poster for the Aurelia NPC population dataset, with distressed print texture and symbolic figures.

Draft:

Dataset 4/4: Aurelia NPC population.

25,799 final snapshot rows: traits, locations, world membership, and population structure from the synthetic societies Aurelia produces.

https://huggingface.co/datasets/OusiaResearch/aurelia-npc-population

## Optional technical follow-up thread

Attach image: omnibus or civilization metrics.

### Tech tweet 1

Aurelia's latest targeted runs were useful because one knob actually moved the world.

100y baseline population CV: 0.674
200y baseline population CV: 1.096
density-diversification CV: 0.006

### Tech tweet 2

Against the 100y baseline, density diversification cut population imbalance by 99.1%.

That is the difference between a decorative parameter and a real causal handle.

### Tech tweet 3

The simulation did not just emit lore. It exposed a controllable lever.

Report:
https://github.com/ousiaresearch/aurelia/blob/main/docs/reports/phase11-runs-comparison.md

## Posting checklist

Before posting:
- Confirm whether to use the causal-events image despite the small generated-text mutation.
- Confirm account: @PLNTRProtocol.
- Confirm launch thread vs short launch.
- Upload image manually or via approved X API path. The `xitter` skill reports missing X write credentials in this Hermes profile, so CLI posting is not currently configured here.
- Do not post automatically without explicit approval.

## Verified facts used in copy

Live HF API check returned public repos:
- `OusiaResearch/aurelia-causal-events`, siblings: 7
- `OusiaResearch/aurelia-civilization-metrics`, siblings: 7
- `OusiaResearch/aurelia-federation-causal`, siblings: 12
- `OusiaResearch/aurelia-npc-population`, siblings: 27

Image dimensions:
- causal-events: 1023x1537, 3.99 MB
- civilization-metrics: 1023x1537, 3.95 MB
- federation-causal: 1024x1536, 4.00 MB
- npc-population: 1023x1537, 3.44 MB
- omnibus: 1024x1536, 4.02 MB

Run comparison facts:
- 100y baseline: CV 0.674
- 200y baseline: CV 1.096
- density-100y-d07: CV 0.006
- coefficient of variation reduction vs 100y baseline: 99.1%

Dataset row counts:
- causal events: 560,428
- civilization metrics: 12,600
- federation causal: 114,133
- NPC population: 25,799
- total: ~35 MB Parquet
