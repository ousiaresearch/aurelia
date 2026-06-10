# Aurelia Wiki Status Banners

Use these banners for files that should be retained but contextualized during wiki reconciliation.

---

## `simulation/npc-registry.md`

Insert below title:

```markdown
> **Canon status:** authored seed registry. This file preserves named NPC profiles, type distributions, and behavioral parameters for lore/design use. It is not the current source of truth for published run population sizes. For public data, use the Phase 11 Hugging Face datasets and `docs/AURELIA_CANON_AND_DATA_GUIDE.md`.
>
> **Scale note:** older wiki files mix seed counts, lore populations, 600-NPC/60K experiments, and published dataset snapshots. Treat population scale as run-dependent unless tied to a specific report or dataset.
```

Recommended header correction:

```markdown
*Canonical seed profiles and population-distribution design notes for Aurelia. Named NPCs have authored profiles. Procedural population sizes are run-dependent and should be cited from specific run artifacts or datasets.*
```

---

## `simulation/phase5-60k-scaling.md`

Insert below title:

```markdown
> **Canon status:** historical scaling experiment. This file records an older 60K local-daemon engineering benchmark. It is useful for stratified sampling, bounded social graph, and name-generation ideas, but it is not the current public scale claim for Aurelia.
>
> Current public scale claims should cite a specific run report or Hugging Face dataset export.
```

Recommended title:

```markdown
# Phase 5 — Historical 60K Scaling Experiment
```

---

## `simulation/event-triggers.md`

Insert below title:

```markdown
> **Canon status:** event design table. These events are canonical design targets and lore mechanics, but implementation status varies by concept and run. Treat each event as `simulated`, `partial`, `planned`, or `lore_only` using `docs/AURELIA_CANON_AND_DATA_GUIDE.md` before citing it as active runtime behavior.
```

Recommended wording change:

```markdown
*Event designs for the Aurelia simulation, with trigger conditions, effects, and dependencies. Some are actively simulated; others remain lore/design targets.*
```

Replace “Player/GM-injected” category with:

```markdown
| Intervention | Researcher/agent-injected counterfactual or scenario branch | On demand |
```

---

## `public/narrative-primer.md`

Insert below title:

```markdown
> **Canon status:** narrative/lore primer. This is prose worldbuilding, not a current architecture or dataset schema document. Treat geographic language here as narrative context unless the public topology decision explicitly preserves it as technical canon.
```

Do not rewrite the prose unless topology is being deliberately changed across the whole lore layer.

---

## `public/visuals/style-primer.md`

Insert below title:

```markdown
> **Canon status:** lore-world visual direction. Preserve the ink, paper, wash, cross-hatch, and artifact-like visual grammar. Align public-facing assets with Risomorphism 1911 / Ousia Research styling and avoid generic cyberpunk UI or fixed real-world cartography.
```

Recommended addition under “What To Avoid”:

```markdown
- Fixed Earthlike maps presented as technical simulation truth
- Generic blue-neon sci-fi dashboards
- Game HUD language unless a separate game/TTRPG layer is explicitly revived
```

---

## `playable-types.md`

Insert above title or replace title block:

```markdown
> **Archive status:** historical playable-design seed. Aurelia is currently framed as a causal civilization simulation and research dataset, not a TTRPG/game product. Retain this file for internal character-archetype inspiration only; do not include it in the primary public navigation without reframing.
```

Recommended action: archive from public nav. If reused, rename/reframe as type-archetype notes.

---

## `adventure-hooks.md`

Insert above title or replace title block:

```markdown
> **Archive status:** historical narrative seed material. These hooks may inspire simulation scenarios, counterfactual branches, or event-trigger tests, but “campaign/adventure” framing is not current public Aurelia positioning.
```

Recommended action: archive from public nav or rename to `narrative-seeds.md` after removing campaign/player language.

---

## `equipment.md`

Insert above title or replace title block:

```markdown
> **Archive status:** historical game-adjacent material. If retained publicly, reframe this as material culture / tools / artifacts rather than inventory or equipment for play.
```

Recommended action: archive from public nav or convert to `material-culture/tools-and-artifacts.md`.

---

## Generic stale-status banner

For files with old local-dashboard, no-git, no-license, no-public-access, or always-on-daemon claims:

```markdown
> **Stale status note:** this file predates Aurelia’s current public GitHub/Hugging Face/Cloudflare publication layer. Local daemon, dashboard, scale, and access claims should be checked against the current repo README, `docs/ARCHITECTURE.md`, and `docs/AURELIA_CANON_AND_DATA_GUIDE.md` before reuse.
```

---

## Generic lore-only banner

For lore documents that should be preserved but not cited as simulation proof:

```markdown
> **Lore status:** this document is part of Aurelia’s narrative/worldbuilding layer. It may describe themes, institutions, geography, characters, or myths that are not fully represented as active runtime/data surfaces in every simulation run.
```
