# Aurelia HuggingFace Datasets — Promo Image Bundle

This directory holds the **raw gpt-image-2 renders** generated as promo material for
the four `ousiaresearch/aurelia-*` HuggingFace datasets, plus the prompts used to
generate them. All images are vertical 9:16 portrait, 941×1672 PNG, ~3 MB each.

**No deterministic typography overlay, no OCR-correction, no post-processing.**
Per the gpt2image-promo skill (`~/.hermes/profiles/palantir/skills/autonomous-ai-agents/codex-vision/references/gpt2image-promo.md`),
the user judges the raw output. Multiple candidates per dataset are provided so
you can pick.

## Per-dataset canonical picks

| dataset | repo | canonical image | size |
|---|---|---|---|
| causal events | `ousiaresearch/aurelia-causal-events` | `causal-events-raw-gptimage-candidate-1.png` | 3.2 MB |
| civilization metrics | `ousiaresearch/aurelia-civilization-metrics` | `civilization-metrics-raw-gptimage-candidate-1.png` | 3.2 MB |
| federation causal | `ousiaresearch/aurelia-federation-causal` | `federation-causal-raw-gptimage-candidate-3.png` | 3.0 MB |
| npc population | `ousiaresearch/aurelia-npc-population` | `npc-population-raw-gptimage-candidate-3.png` | 3.2 MB |
| **omnibus** (all 4) | — | `omnibus-raw-gptimage-candidate-3.png` | 3.4 MB |

## Alternative candidates (in same dir)

For datasets where multiple candidates were generated, additional raw PNGs
exist alongside the canonical pick:

- `causal-events-raw-gptimage-candidate-2.png`
- `civilization-metrics-raw-gptimage-candidate-2.png`
- `omnibus-raw-gptimage-candidate-1.png`
- `npc-population-raw-gptimage-candidate-1.png` (⚠ duplicate of federation-causal-c1 due to parallel Codex session race; **do not use**)
- `federation-causal-raw-gptimage-candidate-1.png` (⚠ duplicate of npc-population-c1; **do not use**)
- `federation-causal-raw-gptimage-candidate-2.png` (⚠ duplicate of causal-events-c2; **do not use**)
- `causal-events-raw-gptimage-candidate-2.png` (⚠ duplicate of federation-causal-c2; **do not use**)
- `npc-population-raw-gptimage-candidate-2.png` (⚠ duplicate of omnibus-c2; **do not use**)
- `omnibus-raw-gptimage-candidate-2.png` (⚠ duplicate of npc-population-c2; **do not use**)

The c3 canonical picks for federation-causal, npc-population, and omnibus were
generated serially (no parallelism) into separate subdirectories to break the
parallel Codex session write race; verified unique by SHA-256.

## Aesthetic

All images target the **Risomorphism 1911** palette: cream `#F7EDE3`, deep
indigo `#0B1224`, teal `#0E2723`, solar gold `#F6C65A`, burnt orange `#C15811`.
Aged-paper texture, halftone grain, deckle-edge borders, vintage scrapbook
construction. **No Earth maps, no real continents** (a fictional-only-worlds
constraint that the prompts enforce).

## Prompts

The exact prompts used to generate these images live in
[`prompts/01-causal-events.txt` through `prompts/05-omnibus.txt`](./prompts/).
Each prompt has a trailing "Do not run keep" line and a "Save as" instruction
that targets the canonical output dir.

## Generation provenance

- **Generator**: `codex exec` (Codex CLI 0.133.0, ChatGPT Plus auth)
- **Model**: `gpt-image-2` via Codex's built-in `image_gen` tool
- **Output transport**: `cat prompt.txt | codex exec --skip-git-repo-check -s workspace-write --add-dir /tmp/hf-promo/output -`
- **Resolution**: 941×1672 px (gpt-image-2 native portrait)
- **File count**: 10 unique PNGs across 5 datasets, ~17 MB total
- **Date**: 2026-06-09

## Self-eval

Codex was used to self-evaluate each canonical pick against three checks:
(1) Risomorphism 1911 palette match, (2) vertical portrait orientation,
(3) no text/typography issues. All 5 canonical images passed.

## Known issue (informational)

Parallel Codex image_gen sessions to a single `--add-dir` target occasionally
write identical PNGs to disk due to the session's `~/.codex/generated_images/<session_id>/`
intermediate file race. Workaround for future runs: serialize, or use distinct
`--add-dir` targets per parallel session.
