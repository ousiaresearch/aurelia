# Aurelia — Phase 12 Gaps & Reconciliation

> *A candid assessment of what is public, what is proven, what is lore-only, and what still needs bridge work.*

This supersedes older “expansions and gaps” language that described Aurelia as local-only, not-yet-git, not-yet-licensed, or not-yet-public. Those claims are stale.

---

## Current state assessment

### Solid public surface

- **Open-source repository:** live under `ousiaresearch/aurelia`.
- **License:** MIT.
- **Test suite:** pytest coverage for causal mechanics, Hugging Face export invariants, counterfactuals, Phase 10 dynamics, and Phase 11 proof tooling.
- **Architecture:** barrier-synchronized five-world causal engine.
- **Storage:** SQLite-per-world run artifacts plus federation database.
- **Cloudflare:** Observatory and read-only public JSON endpoints.
- **Hugging Face:** four published dataset families under `OusiaResearch/`.
- **Proof tools:** graph export, event explanation, run reports, quality scoring, counterfactual comparison.
- **Canon bridge:** `docs/AURELIA_CANON_AND_DATA_GUIDE.md` maps lore/wiki concepts to code, data, Cloudflare, HF, and proof artifacts.

### Still incomplete or partial

- **Wiki reconciliation:** Desktop wiki still contains stale local-daemon, scale, access, authorship, and game/TTRPG framing.
- **Scale language:** older docs mix lore population, seed registry counts, 600/60K experiments, and Phase 11 exports.
- **Glim anomaly:** central lore concept, represented in data/canon, but not fully bridged across every simulation layer.
- **Narrative prose layer:** run data is strong; human-readable longform chronicle prose remains a downstream layer.
- **Cloudflare limits:** the public Observatory is a useful surface, but local/HF artifacts remain the complete archive when edge storage limits constrain public samples.
- **Long-run calibration:** 100-year and 200-year runs exist; larger production calibration should continue only behind quality gates.

---

## Current architecture direction

Aurelia’s current architecture is not “five always-on local web daemons are the only truth.”

The current architecture is:

1. build and seed worlds;
2. run a barrier-synchronized federation tick;
3. write micro/meso/macro/federation events to the causal ledger;
4. persist completed run artifacts locally as SQLite;
5. render reports and graph exports;
6. publish selected surfaces to Hugging Face and Cloudflare.

The old daemon/dashboard architecture should be retained as historical engineering context, not the primary public framing.

---

## Current gaps by category

### Canon and documentation

**Priority:** high

- Apply the wiki reconciliation review.
- Add status banners to stale or historical files.
- Replace old scale claims with the scale taxonomy.
- Separate narrative/lore canon from current runtime/data proof.

### Simulation proof

**Priority:** high

- Keep enforcing causal-edge integrity.
- Continue run-quality evaluation before publication.
- Extend counterfactual branch examples.
- Keep federation effects visible in reports and HF exports.

### Dataset polish

**Priority:** medium

- Keep dataset cards synchronized with current schemas.
- Add more loading/analysis examples.
- Provide compact “what question can this dataset answer?” examples for each dataset family.

### Cloudflare Observatory

**Priority:** medium

- Treat as public sample/inspection layer, not complete archive.
- Keep endpoint documentation current.
- Add clearer links from Observatory to HF datasets and run reports.

### Narrative layer

**Priority:** medium

- Build prose from causal data, not from vibes.
- Use yearly reports and causal graph explanations as source material.
- Keep Glim/Thren/Vorn narrative tension anchored to actual simulated evidence where public data claims are made.

### Visual/public layer

**Priority:** medium

- Align visuals with Risomorphism 1911 / Ousia Research style.
- Avoid generic sci-fi neon, stock fantasy maps, or fixed Earthlike geography.
- Make public diagrams feel like archive artifacts and causal evidence.

---

## What should be archived or reframed

### Archive from public nav

- `playable-types.md`
- `adventure-hooks.md`
- `equipment.md`

Reason: these imply TTRPG/game product framing. They can remain as historical narrative seed material, but they should not be a public first impression.

### Retain as historical engineering notes

- 600-NPC local daemon notes
- 60K scaling experiment notes
- old coordinator/dashboard route notes

Reason: they contain useful lessons, but should not be presented as current production architecture.

### Retain as lore

- country/world profiles
- species/type-politics docs
- Memory Trader / Glim / Thren mythology
- Silmarillion-style narrative files
- visual style primer

Reason: the deep lore is not the stale layer.

---

## Recommended next implementation patches

### Patch 1 — Public front door

Replace/update:

- `README.md`
- `public/faq.md`
- `media/media-kit.md`
- `public/expansions-and-gaps.md`

Goal: remove stale public status, access, authorship, scale, and topology claims.

### Patch 2 — Simulation status layer

Update/banner:

- `simulation/simulation-architecture.md`
- `simulation/npc-registry.md`
- `simulation/phase5-60k-scaling.md`
- `simulation/event-triggers.md`

Goal: distinguish current architecture, historical experiments, seed registries, and design targets.

### Patch 3 — Archive pass

Archive/banner:

- `playable-types.md`
- `adventure-hooks.md`
- `equipment.md`

Goal: prevent accidental TTRPG/game framing.

---

## Current north star

Aurelia should be described as:

> a five-world causal civilization simulation whose histories are recorded as data, inspected as graphs, exported as datasets, and only then rendered as narrative.

The world still has myth. But the myth now has a ledger.
