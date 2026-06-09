# Aurelia HuggingFace Datasets — Nous v9 Imprint Promo Bundle (v2)

This bundle supersedes `docs/assets/hf-promo/` (the v1 Risomorphism-only renders)
with a Nous-branded / **v9 imprint** version that uses the official Nous Research
underground technical-art aesthetic (xerox, risograph, screenprint, halftone,
constrained duotone palette) — but with the **OUSIA RESEARCH** wordmark, not NOUS.

Per the `nous-branding` skill, the shared v9 imprint aesthetic is the right look
for both Nous Research and Ousia Research publications, but the wordmark must
match the entity. The HuggingFace datasets are published under
`OusiaResearch/*`, so this bundle uses `OUSIA RESEARCH`.

## Per-dataset canonical picks (v9-final, post-processed)

| dataset | repo | canonical image | size | aspect |
|---|---|---|---|---|
| causal events | `ousiaresearch/aurelia-causal-events` | `causal-events-v9-final.png` | 4.1 MB | 1023×1537 (2:3) |
| civilization metrics | `ousiaresearch/aurelia-civilization-metrics` | `civilization-metrics-v9-final.png` | 4.0 MB | 1023×1537 (2:3) |
| federation causal | `ousiaresearch/aurelia-federation-causal` | `federation-causal-v9-final.png` | 4.0 MB | 1024×1536 (2:3) |
| npc population | `ousiaresearch/aurelia-npc-population` | `npc-population-v9-final.png` | 3.4 MB | 1024×1536 (2:3) |
| **omnibus** (all 4) | — | `omnibus-v9-final.png` | 4.0 MB | 1024×1536 (2:3) |

All five are **post-processed** with the nous-branding `postprocess.py --mode
imprint --intensity 0.7` (14-step pipeline: warm color grade, scanlines, film
grain, Bayer dither, vignette, chromatic aberration, screen print texture,
paper fiber, ink bleed, palette compression, xerox threshold, registration
offset, plate wobble, print scuffs).

## Raw, pre-post-process PNGs

The raw gpt-image-2 outputs are also kept alongside, prefixed `-v9-raw.png`.
Per the gpt2image-promo skill, "Never deliver a raw generated image" for the v9
imprint target — the post-process is what creates the Nous aesthetic. Raw PNGs
are kept for transparency, not for delivery.

## Style lane per image

| image | style lane | ref1 | ref2 |
|---|---|---|---|
| causal-events | xerox poster | style-cyan-xerox-poster | style-rough-print |
| civilization-metrics | manual / letterpress cover | style-cyan-xerox-poster | style-rough-print |
| federation-causal | analog newspaper direct response | style-cyan-xerox-poster | style-rough-print |
| npc-population | blue registration character | style-cyan-xerox-poster | style-rough-print |
| omnibus | ornate hermetic print artifact | style-cyan-xerox-poster | style-rough-print |

All five used the same v9 style references (cyan xerox poster + rough print)
because they're a coherent series sharing one print language. Per the v9 skill,
"choose two references from the same style lane" — this batch uses the xerox +
manual lane as a pair to keep the family look consistent.

## Self-eval results

Codex was used to self-evaluate each v9-final PNG against five checks:

| image | v9 aesthetic | OUSIA wordmark stamped | NOUS leakage | portrait | text issues |
|---|---|---|---|---|---|
| causal-events | ✓ strong | ✓ | ✓ none | ✓ | minor: "CAUSAL EVENTS" rendered as "CAJISAI EVENTS" in subtitle |
| civilization-metrics | ✓ strong | ✓ | ✓ none | ✓ | clean |
| federation-causal | ✓ newspaper/technical dossier | ✓ | ✓ none | ✓ | clean; "HF-AURELIA" accession absent but URL correct |
| npc-population | ✓ distressed/occult-tech | ✓ | ✓ none | ✓ | clean |
| omnibus | ✓ antique/archival | ✓ | ✓ none | ✓ | tiny fine-print illegible (intended per v9 spec) |

## Known text-mutation issue (informational)

The causal-events subtitle rendered "CAJISAI EVENTS" instead of "CAUSAL
EVENTS". This is a known gpt-image-2 issue when the imprint pipeline degrades
small text. Per the nous-branding skill workflow for this case, the next
iteration should be: (a) retry with shorter subtitle ("CAUSAL EVENTS / v1")
and (b) if still mutated, run a `CRITICAL CORRECTIONS` style-edit pass with
the prior render as substrate. Not done in this batch — surface the issue to
the operator and let them decide.

The v1 Risomorphism bundle (`docs/assets/hf-promo/`) is kept in the repo for
side-by-side comparison. The v2 v9 imprint bundle is the canonical deliverable.

## Generation provenance

- **Generator**: `codex exec --ignore-rules --skip-git-repo-check` (Codex CLI
  0.133.0, ChatGPT Plus auth)
- **Model**: `gpt-image-2` via Codex's built-in `image_gen` tool
- **Style refs**: `/Users/johann/Desktop/Nous-branding-refs/style-cyan-xerox-poster.jpg`
  + `style-rough-print.jpg` (passed first via `-i` so they drive the print language)
- **Post-process**: `~/.hermes/profiles/palantir/skills/creative/nous-branding/scripts/postprocess.py`
  with `--mode imprint --intensity 0.7`
- **Branding**: OUSIA RESEARCH wordmark (per the nous-branding skill's
  Ousia-vs-Nous note: Ousia publications must use OUSIA, never NOUS)
- **No `--yolo`** (sandboxed `-s workspace-write` with explicit `--add-dir`)
- **No `--ignore-rules` misuse**: included per skill guidance to prevent
  unrelated local Codex project instructions (e.g. `keep`) from intercepting
  image generation
- **Serial execution** (5 sequential `codex exec` calls, not parallel) to
  avoid the documented parallel-session write race
- **File count**: 10 PNGs (5 raw + 5 final), ~20 MB on disk
- **Date**: 2026-06-09
- **Quota consumed**: ~75k tokens of ChatGPT Plus image-gen for the canonical
  set (5 generations + 5 self-evals)

## Pipeline diagram

```
prompts/*.txt
    │
    ▼
codex exec --ignore-rules --skip-git-repo-check -s workspace-write
    --add-dir /tmp/hf-promo-v2 --add-dir /tmp/hf-promo-v2/refs
    -i refs/style-cyan-xerox-poster.jpg refs/style-rough-print.jpg
    -                                  (prompt piped via stdin, trailing dash)
    │
    ▼
*-v9-raw.png    (1023×1537 PNG, ~3-4 MB)
    │
    ▼
postprocess.py --mode imprint --intensity 0.7
    (14-step v9 imprint pipeline)
    │
    ▼
*-v9-final.png  (deliverable; ~4 MB, xerox/risograph/screenprint aesthetic)
```
