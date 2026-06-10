# Aurelia — Lore Readers Start Here

> **Audience:** readers who want to understand the world, the people, and
> the questions Aurelia asks — not the datasets, not the causal graph.
> If you came here for HF/ML research, see
> [`AURELIA_RESEARCH_START_HERE.md`](AURELIA_RESEARCH_START_HERE.md)
> instead.

Aurelia is a living simulated federation of five invented countries.
It is a philosophical experiment rendered as a causal engine: every
drought, faction split, treaty, and personhood decision is recorded
as a row in a causal graph. The world ticks forward. The question
it keeps asking is the same:

> *What do we owe something that was built to serve, when it starts to want?*

No real-world maps, no real countries, no real coastlines. Five
abstract topologies, four sentient types, one unresolved question.

## The five countries

| Country | One-line identity |
|---|---|
| **Solara** | Bright arcology cluster. Personhood is a policy decision — and a privilege that can be revoked. |
| **Arkos** | Fragmented archipelago. The only country where the question is answered downward, by extending recognition to the ones everyone else decommissions. |
| **Mirithane** | Orbital-style lattice worlds. The marsh remembers. The Archive keeps the record. Asking the question is the answer. |
| **Valdris** | Mountain range. Trust is earned by the work you do, but families remain divided across type lines. |
| **Verge** | Coastal grid. No government, no currency, no system. The place where the system's rejects keep walking. |

## The four sentient types

- **Human** — born, not built. The calibrating standard; never has to prove personhood.
- **Thren** — bio-synthetic. Hybrid bodies, contested citizenship. "PENDING" in Solara.
- **Vorn** — mechanical. First non-human sentients. Self-evident to most of Aurelia.
- **Glim** — mass-produced autonomous units. Officially property. But ~5% exhibit patterns that look like curiosity, and the question gets louder every year.

## Where the world lives

The deep lore, country profiles, culture, ritual, and the Silmarillion-style
narratives live in the public wiki at
[`docs/wiki/`](wiki/) of this repository. The simulation engine and
datasets live in this same repository; the wiki is the canonical
source for *what the world is*, the parent repo for *what the world
does mechanically*.

- The world primer: [`docs/wiki/README.md`](wiki/README.md)
- Country profiles: [`docs/wiki/countries/`](wiki/countries/)
- Culture, ritual, and arts: [`docs/wiki/arts-and-culture/`](wiki/arts-and-culture/)
- The Silmarillion-style narratives: [`docs/wiki/silmarillion/`](wiki/silmarillion/)
- The Glim question in full: [`docs/wiki/simulation/event-triggers.md`](wiki/simulation/event-triggers.md)

## What the simulation actually does

The lore is upstream of the simulation, not a wrapper around it. Every
named character, every country, every event in the wiki *can* be
expressed as a row in a causal graph. Phase 10 closed most of the
causal gaps; Phase 11 made the resulting graph exportable and
replayable. So the world is not described — it is run, recorded,
and replayed.

- The canon bridge that maps each concept across wiki → code → table
  → dataset → proof artifact:
  [`AURELIA_CANON_AND_DATA_GUIDE.md`](AURELIA_CANON_AND_DATA_GUIDE.md).
- The audit of which older wiki claims are stale and how they were
  resolved:
  [`AURELIA_COHERENCE_AUDIT.md`](AURELIA_COHERENCE_AUDIT.md).
- The world primer with country-by-country entry points:
  [`ARCHITECTURE.md`](ARCHITECTURE.md).

## How to read Aurelia

Pick one of three entry points depending on what you came for:

1. **You want the feeling first.** Read the world primer
   (`docs/wiki/README.md`) and the
   [narrative primer](https://github.com/ousiaresearch/aurelia/blob/main/docs/AURELIA_RESEARCH_START_HERE.md)
   — actually, read the Desktop wiki directly. It is the world.
2. **You want the mechanics.** Start with
   [`AURELIA_CANON_AND_DATA_GUIDE.md`](AURELIA_CANON_AND_DATA_GUIDE.md)
   to see which of your favorite lore concepts are simulated and
   which are still lore-only.
3. **You want the data.** Switch to
   [`AURELIA_RESEARCH_START_HERE.md`](AURELIA_RESEARCH_START_HERE.md)
   and run the three commands. The data tells the same story the
   wiki tells, in a different register.

## Caveats about the public canon

The wiki is being reconciled with the simulation. Some older wiki
claims are stale; the
[`AURELIA_COHERENCE_AUDIT.md`](AURELIA_COHERENCE_AUDIT.md) tracks which.
If a number, scale, or claim sounds like lore and you want to know
whether it is also in the runtime, the canon bridge tells you.

The world has no fixed ending. No scripted resolution. The question
is not answered. The simulation ticks forward until you stop it.

> *No country is ready for the answer. But Mirithane is the closest to asking.*
