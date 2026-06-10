# Aurelia Federation

> *Five worlds. Five answers to “who counts as a person.” Five different failures, five different kinds of grace.*

**Aurelia** is a causal civilization simulation and worldbuilding research project by **Ousia Research**. It began as a lore-rich federation of five societies — Solara, Arkos, Mirithane, Valdris, and The Verge — and now operates as a five-world causal engine whose histories can be run, inspected, exported, and compared.

It is not a game, not a fixed map, and not a static setting. Aurelia is a research-grade simulation substrate: ecology, resources, disease, education, migration, factions, diplomacy, discoveries, conflict, demography, institutions, and sovereignty all evolve together through recorded causal events.

---

## The current public frame

Aurelia’s current public surface is built around **causal proof**:

- **Open-source repository:** `https://github.com/ousiaresearch/aurelia`
- **License:** MIT
- **Simulation core:** Python + SQLite-per-world run artifacts
- **Federation engine:** barrier-synchronized five-world causal orchestration
- **Proof tools:** causal graph export, event explanation, run reports, run-quality scoring, counterfactual comparison
- **Public datasets:** Hugging Face datasets under `OusiaResearch/`
- **Public observability:** Cloudflare Observatory and read-only JSON endpoints

The graph is primary. Narrative is downstream.

---

## The five worlds

Aurelia’s five worlds are abstract civilizational profiles. They carry lore, culture, economy, institutions, and species politics, but they are not real-world maps or fixed geographic claims.

### ☀ Solara — *The Progressive Ceiling*

Solar civic modernism, citizenship review, official progressivism with structural limits. Solara asks who can be granted personhood — and who can have it revoked.

### ▲ Arkos — *The Inverted Hierarchy*

Arcology discipline, Vorn memory, manufacturing, stored power, and solidarity with those built to serve. Arkos remembers the line between tool and person because it crossed it first.

### ≈ Mirithane — *The Rejection of the Question*

Estuary ecology, distributed memory, rewilded politics, and consensus practice. Mirithane’s answer to “who counts?” is to refuse the premise that anyone gets to ask.

### ♦ Valdris — *The Pragmatic Middle*

Highland labor, guild recognition, mineral wealth, earned trust, and hard institutional compromise. Valdris makes personhood legible through work, obligation, and endurance.

### — The Verge — *The Drain*

Frontier refuge, discarded systems, barter, ghosts, exiles, and unfinished beings. The Verge lets everything exist because the Verge lets everything fail.

---

## The beings of Aurelia

Aurelia tracks four major sentient or contested-sentient types:

- **Humans** — biological baseline populations and institutions.
- **Threns** — bio-synthetic beings whose citizenship and belonging vary by world.
- **Vorns** — mechanical beings whose personhood is often self-evident but politically uneven.
- **Glims** — mass-produced autonomous units officially classified as non-sentient in much of the lore, while anomalous behavior raises the central question.

The **Glim question** remains Aurelia’s moral engine:

> What do we owe something built to serve, when it starts to want?

In current public data, Glims and Glim anomaly concepts are represented in the dataset/canon bridge, but not every narrative implication is fully simulated in every run.

---

## How the simulation works now

Aurelia no longer depends on a single always-on local dashboard or one fragile live daemon story. The current architecture is reproducible and data-first:

1. worlds are built from configuration and seeded state;
2. each world advances through micro, meso, and macro dynamics;
3. federation-level effects carry migration, diplomacy, cultural diffusion, trade shocks, and cross-world consequences;
4. events and causal edges are written into SQLite;
5. run artifacts are exported to reports, graph files, Hugging Face datasets, and Cloudflare public surfaces.

Key runtime systems include:

- `src_template/causal_ledger.py`
- `src_template/federation_orchestrator.py`
- `src_template/phase10_dynamics.py`
- `src_template/federation_effects.py`
- `src_template/cultural_diffusion.py`
- `scripts/export_causal_graph.py`
- `scripts/explain_event.py`
- `scripts/render_run_report.py`
- `scripts/evaluate_run_quality.py`
- `scripts/compare_runs.py`

---

## Scale and population

Aurelia’s scale is **run-dependent**. Do not treat any single historical NPC count as the permanent scale of the project.

Use this taxonomy:

1. **Lore population** — fictional demographic background.
2. **Authored seed registry** — named characters, type distributions, cultural archetypes.
3. **Historical daemon experiments** — older 600/60K local scaling experiments retained as engineering reference.
4. **Published Phase 11 datasets** — the current public research surface.
5. **Future production scale** — only claimed after quality gates pass.

The current public proof is not “trust this NPC count.” It is: inspect the run artifacts, causal events, reports, and datasets.

---

## Public datasets

Aurelia publishes four dataset families under `OusiaResearch/`:

- `aurelia-causal-events`
- `aurelia-civilization-metrics`
- `aurelia-federation-causal`
- `aurelia-npc-population`

These datasets expose causal events, civilization metrics, federation-level effects, NPC/type populations, and run metadata for analysis.

---

## Project status

**Active.** Aurelia is open-source, MIT-licensed, tested, documented, and published through GitHub, Hugging Face, and Cloudflare public surfaces.

Aurelia is an **Ousia Research** project. Arien authored much of the early lore/design layer; the simulation, publication, and data infrastructure were expanded through the Hermes agent workflow.

---

*No country is ready for the answer. But the graph is finally recording the question.*
