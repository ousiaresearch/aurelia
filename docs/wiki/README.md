# Aurelia — World Wiki

> **Canonical source for Aurelia's lore, worldbuilding, and named-character history.**
> This wiki was migrated from the operator's local research directory to make the world canon
> public. The simulation engine and datasets live in the parent repository;
> this directory is the *world the engine runs*.

## How to read this wiki

This wiki is the **what the world is** layer. The simulation repository is
the **what the world does mechanically** layer. They are kept in sync via
the canon bridge:

- [`../AURELIA_CANON_AND_DATA_GUIDE.md`](../AURELIA_CANON_AND_DATA_GUIDE.md) — which wiki concept lives in which code, table, dataset, and proof artifact.
- [`../AURELIA_COHERENCE_AUDIT.md`](../AURELIA_COHERENCE_AUDIT.md) — which older wiki claims are stale and how they were resolved.
- [`../AURELIA_RESEARCH_START_HERE.md`](../AURELIA_RESEARCH_START_HERE.md) — for HF/ML researchers who want the data, not the lore.
- [`../AURELIA_LORE_READERS_START_HERE.md`](../AURELIA_LORE_READERS_START_HERE.md) — for readers who want this wiki and the world it describes.

## The world in one paragraph

Aurelia is a living simulated federation of five invented countries —
**Solara, Arkos, Mirithane, Valdris, and The Verge** — set in the year
2126, after a civilizational collapse whose exact cause is one of the
central mysteries. Four sentient types walk these lands: **Humans** (the
calibrating standard), **Threns** (bio-synthetic, contested citizenship),
**Vorns** (mechanical, first non-human sentients), and **Glims**
(mass-produced autonomous units, officially property, ~5% of whom exhibit
patterns that look like curiosity). Every country answers the central
question — *what do we owe something that was built to serve, when it
starts to want?* — differently. No answer is right. No answer is wrong.
The simulation ticks forward until you stop it.

## Where to start

| If you want… | Read this |
|---|---|
| The feeling first | [`public/narrative-primer.md`](public/narrative-primer.md) |
| Country profiles | [`countries/`](countries/) |
| Culture, ritual, arts | [`arts-and-culture/`](arts-and-culture/) |
| The deep lore (Silmarillion-style) | [`silmarillion/`](silmarillion/) |
| Named characters | [`silmarillion/`](silmarillion/) and country profiles |
| War, conflict, sovereignty | [`warfare.md`](warfare.md), [`governance.md`](governance.md) |
| Magic-adjacent mechanics (latency, Writing, Reading) | [`simulation/event-triggers.md`](simulation/event-triggers.md) |
| Cosmology and history | [`chronology.md`](chronology.md), [`deep-lore-framework.md`](deep-lore-framework.md) |
| How the world is simulated | [`simulation/simulation-architecture.md`](simulation/simulation-architecture.md) |

## What is in canon, what is lore-only

The canon bridge (`AURELIA_CANON_AND_DATA_GUIDE.md` in the parent directory)
tags each major concept with a status:

- **Simulated** — active in the runtime and exported to HuggingFace.
- **Partial** — represented somewhere, lacks a full bridge.
- **Lore-only** — exists in the wiki without a runtime/data surface.
- **Stale** — older claim, review before quoting.
- **Archived** — historical/internal material, not current public canon.

Most of this wiki is lore-only or partial. That is not a defect. The
wiki is the *world*; the simulation is one mechanical interpretation of
some of it. The bridge is the honest accounting.

## Provenance

This wiki was authored and curated as a local research document on the
operator machine and was migrated to the public repository in Phase 12
of the Aurelia gap-closure plan. Earlier wiki state and operator edits
are preserved in the local git history of the original directory; the
public copy is the canonical source going forward.

> *No country is ready for the answer. But Mirithane is the closest to asking.*
