# Aurelia Wiki Reconciliation Review

Status: review artifact only. This document does **not** edit `~/Desktop/Aurelia`. It pulls the wiki reconciliation surface into a decision matrix so Anduril can choose what to refresh, eliminate/archive, or retain.

Source surfaces checked:

- `~/Desktop/Aurelia/README.md`
- `~/Desktop/Aurelia/public/faq.md`
- `~/Desktop/Aurelia/media/media-kit.md`
- `~/Desktop/Aurelia/public/expansions-and-gaps.md`
- `~/Desktop/Aurelia/simulation/npc-registry.md`
- `~/Desktop/Aurelia/simulation/phase5-60k-scaling.md`
- `~/Desktop/Aurelia/simulation/simulation-architecture.md`
- `~/Desktop/Aurelia/simulation/event-triggers.md`
- `~/Desktop/Aurelia/public/narrative-primer.md`
- TTRPG-adjacent files: `playable-types.md`, `adventure-hooks.md`, `equipment.md`
- Broad keyword scan across 138 wiki Markdown files.

Current repo reference points:

- `docs/data/aurelia_concepts.yaml`
- `docs/AURELIA_CANON_AND_DATA_GUIDE.md`
- `docs/plans/2026-06-10-aurelia-gap-closure-plan.md`
- HuggingFace datasets under `OusiaResearch/`
- Cloudflare Observatory/public dashboard as partial public observability surface.

---

## Executive classification

### Refresh now

These files are public-facing or simulation-status docs whose claims conflict with current Phase 11/12 public reality. Refreshing them would reduce confusion immediately.

1. `README.md`
2. `public/faq.md`
3. `media/media-kit.md`
4. `public/expansions-and-gaps.md`
5. `simulation/simulation-architecture.md`
6. `simulation/npc-registry.md`
7. `simulation/phase5-60k-scaling.md`
8. `simulation/event-triggers.md`

### Retain with minor header/context

These are lore-rich and still valuable. They should not be flattened into repo-tech language. Add only a small canon-status banner if needed.

1. `public/narrative-primer.md`
2. country/lore/culture files such as architecture, artifacts, arts, religion, war, governance, ruins, mythology, Silmarillion-style stories
3. `public/visuals/style-primer.md`
4. named-character/NPC profiles inside `simulation/npc-registry.md`, once scale claims are separated from profiles

### Eliminate from public navigation / archive as historical/internal

These are not necessarily bad, but they push Aurelia toward TTRPG/game framing, which conflicts with the current simulation/dataset positioning unless explicitly requested.

1. `playable-types.md`
2. `adventure-hooks.md`
3. `equipment.md`

Recommended action is **archive/supersede**, not delete. Move out of primary public nav or add a banner: “Historical/internal narrative seed material; Aurelia is currently framed as a simulation/research dataset, not a TTRPG.”

---

## Detailed decision matrix

### 1. `README.md`

**Decision:** refresh.

**Why:** It is the wiki’s front door and contains the densest cluster of stale public claims.

**Claims needing refresh:**

- “60,000 procedurally generated NPCs” as current/live default.
- “Five autonomous daemons tick forward in 30-minute intervals.”
- “single landmass partitioned into five distinct countries.”
- local coordinator/dashboard at port `9001` as primary access path.
- “~20,000 lines of Python” as the central proof claim.
- “Built by Arien” as the sole public authorship/operation frame.
- current status says coordinator + daemons are continuously running on macOS.

**Recommended replacement frame:**

- Aurelia is a federated civilization simulation and research artifact.
- Public Phase 11/12 surface is: GitHub repo, HF datasets, Cloudflare Observatory, run reports, and canon/data guide.
- Five worlds/civilizations remain Solara, Arkos, Mirithane, Valdris, The Verge, but public copy should avoid overcommitting to one live-daemon architecture.
- NPC scale should be described as run-dependent: wiki/lore populations, experimental 60K scale notes, and Phase 11 exported micro-society runs are different layers.
- Authorship: Ousia Research project; Arien can be credited as original lore/design lineage where appropriate.

**Keep:**

- The tagline.
- The five country summaries.
- The Glim question.
- The personhood theme.

**Eliminate/avoid:**

- “live continuous daemon” status unless verified at the moment of publication.
- local dashboard URL in public-facing README.
- hardcoded 60K as the public/default scale.

---

### 2. `public/faq.md`

**Decision:** refresh.

**Why:** This is exactly where external readers will look for project status, access, authorship, and scale.

**Claims needing refresh:**

- “Not publicly yet” for interaction/access.
- local-only dashboard at `127.0.0.1:9001`.
- “Not yet open source.”
- “no git repository, no license, no public distribution.”
- “600 NPCs across five countries” as the main scale claim.
- named real-world agent daemon locations; remove from public docs entirely.
- “Python 3.13 / stdlib http.server / zero dependencies” is outdated relative to the public repo/HF tooling.

**Recommended replacement frame:**

- Public repo is open-source MIT.
- HF datasets are live under `OusiaResearch`.
- Cloudflare Observatory exists as public/partial observability, while HF/local Parquet exports are the complete research archive for Phase 11.
- NPC count is run/export dependent. Use a short explanation:
  - lore population: fictional/background scale
  - historical local daemon experiments: 600/60K
  - Phase 11 exported datasets: rows and final population snapshots from selected runs
- Glim anomaly remains a central lore mechanic but is only partial/planned as a causal/data surface.

**Keep:**

- “It is not a game.”
- Type explanations for Human/Thren/Vorn/Glim.
- Glim question text, lightly adjusted to avoid claiming fully simulated behavior.

**Eliminate/avoid:**

- local-only access language.
- PII/location list.
- “not open source.”

---

### 3. `media/media-kit.md`

**Decision:** refresh.

**Why:** It is used for social/public copy and currently encodes old scale, old status, old brand palette, and local repo status.

**Claims needing refresh:**

- “600 procedurally generated NPCs.”
- “20 autonomous processes tick forward every 30 minutes.”
- “Repository: local path, not yet in git.”
- “Built by Arien for Ousia Research” as sole status line.
- “Map: single continent partitioned into five biomes.”
- old dark-dashboard/terminal-punk palette when the current public social layer is Risomorphism 1911 / Ousia Research, plus selected Nous-v9 imprint assets.

**Recommended replacement frame:**

- Project identity: Aurelia by Ousia Research.
- Category: civilization simulation / synthetic society dataset / causal world-modeling experiment.
- Key public statistics should use HF row counts and run-report facts, not 600/60K-only claims.
- Visual identity should match Risomorphism 1911 for social narrative and note separate Nous-v9 imprint dataset-promo assets.

**Keep:**

- Tagline.
- Core themes.
- country symbols if still used.
- suggested copy shape, rewritten in Risomorphism voice.

**Eliminate/avoid:**

- local repo path.
- “not yet in git.”
- single-continent map as current public surface unless explicitly retained as lore-only map canon.

---

### 4. `public/expansions-and-gaps.md`

**Decision:** refresh heavily or supersede.

**Why:** It is a gap analysis, but many “missing” items are now done or reframed.

**Claims needing refresh:**

- “No version control.”
- “No public distribution.”
- “No license.”
- “Only stub tests.”
- “Cross-world events documented but not implemented.”
- “Coordinator dashboard broken” as current primary bottleneck.
- “Public web dashboard optional future.”
- “External API future.”

**Current reality:**

- GitHub repo is public.
- MIT license exists.
- CI/test suite exists.
- HF datasets are live.
- Cloudflare public observability exists but is partial due to D1 capacity.
- Cross-world/federation causal exports exist.
- Current gaps are better described as canon/data legibility, strict quality gates, metadata propagation, research examples, and wiki synchronization.

**Recommended action:**

- Rename/supersede as `public/phase12-gaps.md` or update in place with an “as of Phase 12” heading.
- Preserve the narrative/lore gap sections, but distinguish them from engineering gaps.

**Keep:**

- Character gap notes.
- Glim voice note.
- “What Aurelia could become” vision.

**Eliminate/avoid:**

- old infrastructure TODOs as current blockers.

---

### 5. `simulation/simulation-architecture.md`

**Decision:** refresh / split into historical architecture vs current architecture.

**Why:** It describes an old continuous-daemon architecture with 12,000 NPCs/world and port-based daemons. Current repo has moved toward offline/sequential, barrier-synchronized causal runs and export/publication tooling.

**Claims needing refresh:**

- Coordinator at `:9001` as primary architecture.
- one daemon per country with ports.
- 12,000 NPCs per world / 60,000 total as active architecture.
- 30-minute real-time tick loop.
- 1 sim day = 48 ticks = 24 real hours.
- specific old profile schema as if it is the current DB/export schema.

**Recommended action:**

Split into two docs:

1. `simulation/historical-daemon-architecture.md` — preserve the old daemon concept and lessons.
2. `simulation/current-causal-architecture.md` — current sequential federated causal engine, Phase 10 dynamics, causal ledger, federation orchestrator, HF exports.

**Keep:**

- type-specific schemas as design/lore schema.
- behavioral simulation rules as design targets.
- economic/currency concepts if still canonical lore.

**Eliminate/avoid:**

- claiming old daemon ports/scale are current production architecture.

---

### 6. `simulation/npc-registry.md`

**Decision:** retain + refresh header and population semantics.

**Why:** This file contains valuable named NPCs and behavioral parameters, but its top-level scale framing is confusing.

**Claims needing refresh:**

- “600 agents across 5 daemons.”
- distribution table totals 310 while prose says 600.
- full lore population claim of ~310,000, separate from README’s 60,000 and FAQ’s 600.
- daemons as current runtime structure.

**Recommended replacement frame:**

- Treat this as **authored canonical seed profiles and distributions**, not the current source of truth for exported run population sizes.
- Add a banner: “NPC registry is a lore/design seed layer. Phase 11 exported population data lives in `OusiaResearch/aurelia-npc-population`.”
- Keep named profiles; they are valuable anchors for future narrative mechanics.

**Keep:**

- named NPC profiles.
- personality/belief distributions.
- type-specific parameters.
- Glim anomaly chain as design target.

**Eliminate/avoid:**

- contradictory exact population totals in the header unless reconciled.

---

### 7. `simulation/phase5-60k-scaling.md`

**Decision:** retain as historical benchmark / archive, not current canon.

**Why:** It may be technically valuable, but it conflicts with Phase 11 exported runs and current correctness-first posture.

**Claims needing refresh:**

- “Deployed” as current active state.
- “All 5 worlds running at 12,000 NPCs each.”
- performance claims that are not connected to current Phase 11 proof surface.

**Recommended action:**

- Rename or banner as “Historical scaling experiment, June 2026.”
- Add note: “Not the current published Phase 11 dataset scale; retained for scaling design reference.”

**Keep:**

- stratified sampling idea.
- bounded social graph idea.
- combinatorial names.
- performance notes as engineering reference.

**Eliminate/avoid:**

- presenting 60K as active/current public Aurelia.

---

### 8. `simulation/event-triggers.md`

**Decision:** retain as design target + map to simulated/unsimulated status.

**Why:** This is high-value world-simulation design. But it says “Every event that can fire” while some triggers are not yet active causal rows in current Phase 11 outputs.

**Claims needing refresh:**

- “Every event that can fire” as a runtime truth.
- “Intervention: Player/GM-injected” framing.
- Glim anomaly cascade as fully implemented, if not actually present in causal data.

**Recommended replacement frame:**

- “Canonical event design table; implementation status varies.”
- Add status markers per event:
  - simulated
  - partial
  - planned
  - lore-only
- Map active mechanics to `docs/data/aurelia_concepts.yaml` statuses.

**Keep:**

- scheduled cultural events.
- Glim anomaly cascade design.
- Thren pending crisis.
- extraction crisis.
- cross-world/federation hooks.

**Eliminate/avoid:**

- “Player/GM” wording unless intentionally making a game/TTRPG layer.

---

### 9. `public/narrative-primer.md`

**Decision:** retain with optional canon banner.

**Why:** It has the correct emotional/aesthetic register and should not be reduced to dataset language.

**Potential refresh:**

- “Five countries on one landmass” conflicts with the repo’s current abstract-world/no-Earth-map public surface.
- “2126” and live tick framing may need to be marked as narrative canon rather than current simulation runtime.

**Recommended action:**

- Keep the prose.
- Add a one-line banner: “Narrative/lore primer; not a current architecture or dataset schema document.”
- Decide whether “one landmass” remains lore canon or becomes old-canon.

**Keep:**

- all prose scenes.
- Glim/Thren/Memory Trader framing.
- final “To be continued by the simulation.”

**Eliminate/avoid:**

- no need to delete anything unless the landmass topology is explicitly rejected.

---

### 10. `public/visuals/style-primer.md`

**Decision:** retain and refresh brand linkage.

**Why:** The visual language is still valuable and close to Risomorphism 1911.

**Recommended refresh:**

- Align palette with current Risomorphism 1911/Ousia public layer.
- Add note distinguishing:
  - lore-world visual style
  - dataset promo style
  - Nous-v9 imprint style used for the HF bundle

**Keep:**

- parchment/ink/wash/cross-hatch direction.
- no cyberpunk/neon caution.

---

### 11. `playable-types.md`

**Decision:** eliminate from public nav / archive.

**Why:** It implies a playable game/TTRPG layer. The current mandate is world simulation and research dataset, not TTRPG unless requested.

**Recommended action:**

- Move under an archive/historical seed area or add a banner:
  - “Historical playable-design seed. Not part of current public Aurelia simulation/dataset framing.”

**Keep internally:**

- type archetypes may inform character/lore writing.

**Eliminate externally:**

- “playable” framing.

---

### 12. `adventure-hooks.md`

**Decision:** eliminate from public nav / archive.

**Why:** “Campaign seeds” strongly shifts the project into RPG presentation.

**Recommended action:**

- Archive as narrative seed material.
- If retained, rename to `narrative-seeds.md` and strip campaign/player language.

**Keep internally:**

- hook ideas can be converted into simulation interventions, counterfactuals, or event-trigger scenarios.

**Eliminate externally:**

- “campaign” framing.
- GM/player language.

---

### 13. `equipment.md`

**Decision:** eliminate from public nav / archive.

**Why:** Equipment lists read as RPG/game prep unless framed as material culture.

**Recommended action:**

- If useful, convert to `material-culture/tools-and-artifacts.md`.
- Otherwise archive as historical TTRPG-adjacent seed.

**Keep internally:**

- artifacts/tools that illuminate social systems.

**Eliminate externally:**

- item-list/game-inventory framing.

---

## Cross-cutting stale claim groups

### A. Scale claims

**Problem:** The wiki simultaneously claims 310 agents, 600 NPCs, 60,000 NPCs, 310,000 lore population, and Phase 11 exported dataset snapshots.

**Recommendation:** Introduce a standard scale taxonomy everywhere:

1. **Lore population** — fictional demographic background.
2. **Authored seed registry** — named profiles and distributions.
3. **Historical daemon experiments** — 600 and 60K local architecture attempts.
4. **Phase 11 exported runs** — the published research datasets.
5. **Future production scale** — only after quality gates pass.

### B. Runtime architecture claims

**Problem:** Old docs assert live macOS daemons and local dashboard as the main architecture.

**Recommendation:** Reframe old daemon architecture as historical/experimental. Current public proof path is sequential causal runs → reports/HF exports → Cloudflare public observability.

### C. Public access claims

**Problem:** FAQ/media kit say no public access, no git, no license, no distribution.

**Recommendation:** Replace with current public repo + HF + Cloudflare status, including the D1 cap limitation.

### D. Authorship/agent identity claims

**Problem:** Some docs say “built by Arien” as sole project identity. Current public artifact is under Ousia Research, operated by Hermes/Palantir execution, with Arien as original creative/design lineage.

**Recommendation:** Use: “Aurelia is an Ousia Research project. Arien authored much of the early lore/design layer; later simulation, publication, and data infrastructure were expanded through the Hermes agent workflow.”

### E. Topology claims

**Problem:** Old docs say one landmass/five countries. Current public repo/social guidance has emphasized no Earth maps and abstract five-world topology.

**Decision needed:** Anduril should choose one of two canon paths:

1. **Retain landmass as lore geography** while saying simulation exports use abstract world IDs.
2. **Supersede landmass** and make five worlds/federated simulation topology the current canon.

### F. TTRPG/game framing

**Problem:** Playable/adventure/equipment docs imply a game product.

**Recommendation:** Archive from public nav unless explicitly reviving a TTRPG layer.

---

## Proposed review order

Review in this order, because each decision affects the next:

1. **Topology decision:** one landmass/five countries vs abstract five-world topology.
2. **Scale taxonomy:** how to describe lore population, seed registry, 60K experiment, and Phase 11 exports.
3. **Authorship line:** Ousia Research + Arien lineage + Hermes execution.
4. **Public access/status:** GitHub/HF/Cloudflare wording.
5. **TTRPG archive decision:** archive, rename, or retain hidden.
6. **Glim anomaly status:** lore central, but partial/planned simulation surface.
7. **Rewrite priority:** README → FAQ → media kit → expansions/gaps → simulation architecture.

---

## Recommended first patch set after review

If approved, first patch only the Desktop wiki front door and do not touch deep lore:

1. `README.md`
2. `public/faq.md`
3. `media/media-kit.md`
4. `public/expansions-and-gaps.md`

Keep this as a single “public surface refresh” patch.

Second patch:

1. `simulation/simulation-architecture.md`
2. `simulation/npc-registry.md`
3. `simulation/phase5-60k-scaling.md`
4. `simulation/event-triggers.md`

Keep this as “simulation architecture/status refresh.”

Third patch:

1. archive or banner `playable-types.md`
2. archive or banner `adventure-hooks.md`
3. archive or banner `equipment.md`

Keep this as “TTRPG-adjacent archive pass.”

---

## Do not touch without explicit decision

- Deep country lore.
- Silmarillion-style narrative files.
- named character prose.
- visual style primer beyond palette/linkage notes.
- Memory Trader / Glim / Thren mythology.

Those are not the source of confusion. The confusion is mostly public status, architecture, scale, and product framing.
