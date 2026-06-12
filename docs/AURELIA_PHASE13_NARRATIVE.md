# Aurelia Phase 13 — Narrative Chronicle Pipeline

Phase 13 adds the narrative layer on top of the stabilized Phase 11/12 engine:
run the simulation without an LLM in the tick loop, then generate yearly
chronicles as a post-process from `yearly_events.json` and the per-world SQLite
DBs.

This keeps simulation mechanics deterministic and cheap while allowing the prose
pass to use a larger local GGUF model.

## Artifacts

- `src_template/batch_chronicles.py` — post-run chronicle generator.
- `prompts/chronicle_v1.txt` — external prompt template for the yearly voice.
- `output/yearly_events.json` — event summaries emitted by the runner.
- `output/<world>.db` — per-world state DBs used for current-state context.
- `output/chronicles/<world>_Y####.txt` — generated yearly chronicle files.

## Dry-run the narrative batch

Dry-run mode performs planning only. It does not import `llama_cpp`, open a
model, or require a GPU.

```bash
PYTHONPATH=src_template python3 src_template/batch_chronicles.py \
  --output /tmp/aurelia-run/output \
  --years 200 \
  --dry-run \
  --vram-gb 96 \
  --model-vram-gb 17
```

Expected shape for five worlds over 200 years:

```text
DRY RUN
  chronicles: 1000
  workers: 5
  estimated_vram_gb: 85.0
  fits: True
```

## Generate chronicles

After a run has produced `yearly_events.json` and `<world>.db` files:

```bash
PYTHONPATH=src_template python3 src_template/batch_chronicles.py \
  --output /tmp/aurelia-run/output \
  --model-path /models/gemma-12b-q4_k_m.gguf \
  --n-workers 5 \
  --n-ctx 4096 \
  --max-tokens 800
```

Single-worker mode loads one model and writes chronicles sequentially. Multi-worker
mode uses one llama.cpp model instance per active world, capped by `--n-workers`.

## Prompt contract

`prompts/chronicle_v1.txt` is intentionally separate from Python code. It must
keep these placeholders:

- `{world_profile}`
- `{species_context}`
- `{voice}`
- `{year_number}`
- `{world_name}`
- `{year_summary}`
- `{world_context}`

The generator renders the template into a chat message and pairs it with a system
message containing the world profile and narrative voice.

## CI-safe checks

The test suite covers the narrative layer without a real model:

```bash
python -m pytest tests/test_batch_chronicles.py -q
```

It verifies prompt rendering, fake-client chronicle writing, GPU worker planning,
and dry-run CLI output.

## Operational notes

- Do not put LLM calls back into the simulation tick loop for production runs.
- Use post-run batch generation so engine outputs remain reproducible.
- The fallback chronicle path writes a plain event summary if generation fails;
  this preserves a complete `chronicles/` directory for upload/retry.
- Cloudflare R2 upload is still handled by `aurelia_cf_pusher.py`, which scans
  `output/chronicles/<world>_Y####.txt`.
