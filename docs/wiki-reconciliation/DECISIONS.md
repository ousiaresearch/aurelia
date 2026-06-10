# Aurelia Wiki Reconciliation Decisions

Status: review package. These decisions are intended to guide a later patch to `~/Desktop/Aurelia`; this file does not modify the wiki.

## Decisions applied in the draft package

### 1. Public topology

**Decision:** Use **five abstract worlds** for public and technical framing.

The old “single landmass / five countries” language should be treated as lore-era geography. It can remain inside narrative/lore documents only if marked as narrative context, not as the current public architecture.

Preferred phrasing:

> Aurelia is a five-world causal civilization simulation. Solara, Arkos, Mirithane, Valdris, and The Verge are abstract worlds/civilizational profiles, not real maps or fixed geographic claims.

### 2. Scale taxonomy

**Decision:** Stop using one hardcoded NPC count as “the” scale.

Use this taxonomy everywhere:

1. **Lore population** — fictional demographic background.
2. **Authored seed registry** — named characters, type distributions, cultural archetypes.
3. **Historical daemon experiments** — 600/60K local scaling experiments retained for engineering reference.
4. **Published Phase 11 datasets** — current public research surface on Hugging Face.
5. **Future production scale** — only claimed after quality gates pass.

Preferred phrasing:

> Aurelia’s scale is run-dependent. The current public proof surface is the Phase 11 dataset suite and run reports, not a single permanent NPC count.

### 3. Authorship line

**Decision:** Use Ousia Research as the public owner, with Arien as creative/design lineage and Hermes/Palantir as execution/runtime lineage.

Preferred phrasing:

> Aurelia is an Ousia Research project. Arien authored much of the early lore/design layer; the simulation, publication, and data infrastructure were expanded through the Hermes agent workflow.

### 4. Public access/status

**Decision:** Replace “not public / no git / no license” claims.

Current public surface:

- GitHub repository: `https://github.com/ousiaresearch/aurelia`
- License: MIT
- Hugging Face datasets under `OusiaResearch/`
- Cloudflare Observatory and public JSON endpoints
- Local SQLite run artifacts remain the complete research archive for each run

### 5. TTRPG/game framing

**Decision:** Archive from public nav, do not delete.

Files:

- `playable-types.md`
- `adventure-hooks.md`
- `equipment.md`

Recommended treatment: add an archive banner or move under an internal/historical folder. If reused, convert “campaign/playable/equipment” language into “scenario seeds/material culture.”

### 6. Glim anomaly status

**Decision:** Keep central to lore; mark as **partial/planned** for simulation proof where appropriate.

The Glim question remains core Aurelia canon. But public docs should distinguish:

- lore/theme: central
- seed registry: represented
- runtime/data: partial, depending on the run and dataset

### 7. Rewrite order

1. Public front door:
   - `README.md`
   - `public/faq.md`
   - `media/media-kit.md`
   - `public/expansions-and-gaps.md`
2. Simulation/status layer:
   - `simulation/simulation-architecture.md`
   - `simulation/npc-registry.md`
   - `simulation/phase5-60k-scaling.md`
   - `simulation/event-triggers.md`
3. Archive/banner pass:
   - `playable-types.md`
   - `adventure-hooks.md`
   - `equipment.md`
4. Optional minor context banners:
   - `public/narrative-primer.md`
   - `public/visuals/style-primer.md`

## Draft outputs in this package

- `drafts/README.md`
- `drafts/public/faq.md`
- `drafts/media/media-kit.md`
- `drafts/public/expansions-and-gaps.md`
- `drafts/simulation/simulation-architecture.md`
- `drafts/status-banners.md`

## Non-goals

Do not rewrite deep lore in this pass. The problem is stale status, architecture, scale, and product framing — not the emotional/literary core of Aurelia.
