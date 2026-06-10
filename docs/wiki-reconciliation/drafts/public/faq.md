# Aurelia — Frequently Asked Questions

## What is Aurelia?

Aurelia is a five-world causal civilization simulation by Ousia Research. It models societies through recorded causal events: ecology, resources, disease, education, migration, factions, diplomacy, discoveries, conflict, demography, institutions, and sovereignty all evolve together over time.

It is not a game. It is a worldbuilding laboratory, an agent-operated simulation system, and a research-grade causal dataset pipeline.

## Who built it?

Aurelia is an Ousia Research project. Arien authored much of the early lore/design layer; the simulation, publication, and data infrastructure were expanded through the Hermes agent workflow.

## What are Solara, Arkos, Mirithane, Valdris, and The Verge?

They are the five abstract worlds/civilizational profiles in Aurelia:

- **Solara** — progressivism, citizenship review, solar civic power, and structural exclusion.
- **Arkos** — arcology discipline, Vorn memory, stored power, and solidarity among the built.
- **Mirithane** — estuary ecology, distributed memory, rewilded politics, and refusal to rank personhood.
- **Valdris** — guild labor, rare-earth economy, earned trust, and pragmatic institutional compromise.
- **The Verge** — refuge, exile, barter, unfinished systems, and the discarded beings no one else can classify.

These worlds carry lore and cultural identity, but the current public simulation does not depend on a fixed real-world map.

## What are Threns, Vorns, and Glims?

They are three major artificial or contested-sentient types inhabiting Aurelia alongside humans:

- **Threns** — bio-synthetic beings whose citizenship and belonging vary by world.
- **Vorns** — mechanical beings whose personhood is often self-evident but politically uneven.
- **Glims** — mass-produced autonomous units officially classified as non-sentient in much of the lore, while anomalous behavior raises the central moral question.

## What is the Glim question?

The central unresolved tension of Aurelia:

> What do we owe something built to serve, when it starts to want?

The Glim question is central lore canon. In current public data, Glims and Glim anomaly concepts are represented in the canon/data bridge, but the full narrative cascade is not guaranteed to be fully simulated in every run.

## Is Aurelia public?

Yes.

- GitHub repository: `https://github.com/ousiaresearch/aurelia`
- License: MIT
- Hugging Face datasets: `OusiaResearch/aurelia-causal-events`, `OusiaResearch/aurelia-civilization-metrics`, `OusiaResearch/aurelia-federation-causal`, and `OusiaResearch/aurelia-npc-population`
- Public observability: Cloudflare Observatory and read-only JSON surfaces

## Can I interact with it?

Public interaction currently means inspecting the repository, datasets, run reports, and Observatory surfaces. The full local simulation remains a code/run-artifact system rather than a public game interface.

## What is the tech stack?

The public codebase is Python with SQLite run artifacts, pytest verification, Hugging Face dataset export tooling, and Cloudflare D1/R2 publication surfaces.

Important runtime/proof components include:

- `causal_run.py`
- `src_template/causal_ledger.py`
- `src_template/federation_orchestrator.py`
- `src_template/phase10_dynamics.py`
- `aurelia_cf_pusher.py`
- `scripts/export_causal_graph.py`
- `scripts/explain_event.py`
- `scripts/render_run_report.py`
- `scripts/evaluate_run_quality.py`
- `scripts/compare_runs.py`

## How many NPCs are there?

Aurelia’s scale is run-dependent. Do not treat any single historical NPC count as permanent canon.

Use this taxonomy:

1. **Lore population** — fictional demographic background.
2. **Authored seed registry** — named characters, type distributions, cultural archetypes.
3. **Historical daemon experiments** — older 600/60K local scaling experiments retained as engineering references.
4. **Published Phase 11 datasets** — the current public research surface.
5. **Future production scale** — only claimed after quality gates pass.

The current public proof surface is the dataset suite and run reports, not a single NPC number.

## How does time work?

Aurelia advances in simulation ticks/years depending on the run configuration. The modern architecture is oriented around reproducible completed runs, causal histories, reports, and exports rather than one always-on local daemon as the only source of truth.

## How do currencies and economies work?

The older lore layer includes distinct currencies and economic identities for the five worlds. The current simulation layer focuses on resources, capital, institutions, migration, diplomacy, conflict, and civilization metrics. Currency-specific lore should be treated as cultural canon unless and until a given run proves it through active data surfaces.

## Where can I learn more?

Start with:

- repository README
- `docs/ARCHITECTURE.md`
- `docs/AURELIA_CANON_AND_DATA_GUIDE.md`
- Phase 11 run reports under `docs/reports/`
- Hugging Face dataset cards under `OusiaResearch/`

For lore, read the country/world profiles, type-politics documents, and narrative primer.
