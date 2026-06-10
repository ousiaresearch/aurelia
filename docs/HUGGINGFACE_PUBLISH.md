# Publishing Aurelia Datasets to HuggingFace

This document is the **handoff** for the four Aurelia HuggingFace datasets. The
export pipeline is in-tree and tested; the only thing it does not do is call
`hf upload`, because that requires a write token.

## TL;DR

```bash
# 1. (one time) install pyarrow + log in to HF
python3 -m pip install pyarrow
export HF_TOKEN="hf_***"  # from https://huggingface.co/settings/tokens

hf auth login --token "$HF_TOKEN"

# 2. (one time per dataset) create the repos
for repo in aurelia-causal-events aurelia-civilization-metrics \
            aurelia-federation-causal aurelia-npc-population; do
  hf repo create ousiaresearch/$repo --repo-type dataset --no-private
done

# 3. (one time per dataset) upload README first (small, fast)
for repo in aurelia-causal-events aurelia-civilization-metrics \
            aurelia-federation-causal aurelia-npc-population; do
  hf upload ousiaresearch/$repo /tmp/hf-export/$repo/README.md README.md \
    --repo-type dataset
done

# 4. (one time per dataset) upload the data directory
for repo in aurelia-causal-events aurelia-civilization-metrics \
            aurelia-federation-causal aurelia-npc-population; do
  hf upload ousiaresearch/$repo /tmp/hf-export/$repo/data data \
    --repo-type dataset
done
```

That gets the four repos public. Verify with:

```bash
for repo in aurelia-causal-events aurelia-civilization-metrics \
            aurelia-federation-causal aurelia-npc-population; do
  echo "=== $repo ==="
  curl -s "https://huggingface.co/api/datasets/ousiaresearch/$repo" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('downloads:', d.get('downloads',0)); print('files:', [s['rfilename'] for s in d.get('siblings',[])][:10])"
done
```

## The four datasets

| repo | content | rows | size |
|---|---|---|---|
| `ousiaresearch/aurelia-causal-events` | per-world causal event stream | 560,428 | 27 MB |
| `ousiaresearch/aurelia-civilization-metrics` | yearly world state trajectories | 12,600 | 1.1 MB |
| `ousiaresearch/aurelia-federation-causal` | federation events + causal edges | 114,133 | 4.7 MB |
| `ousiaresearch/aurelia-npc-population` | NPC snapshot at end of run | 25,799 | 1.9 MB |

Total: ~35 MB of Parquet across four repos. All under `ousiaresearch/`.

## Why four separate repos (and not one big repo with configs)

- **Discoverability** — each repo is independently findable on HF search.
- **Per-dataset versioning** — different release cadences (e.g. new runs
  uploaded without touching civilization-metrics).
- **Card clarity** — each README is focused on one schema; users don't have
  to wade through unrelated columns.
- **Downloadability** — researchers can grab just the metrics, without the
  27 MB causal stream.

The pattern is "one repo per *kind* of data, one config per *run* inside the
repo", expressed as `data/<run_id>/train.parquet`.

## License

All four datasets are released under **CC-BY-4.0**. Synthetic data, no
privacy concerns, and CC-BY-4.0 is the most permissive standard HF license for
synthetic corpora.

## Research on-ramp for HF users

Before the export pipeline: researchers should start with the
[Aurelia research start-here guide](https://github.com/ousiaresearch/aurelia/blob/main/docs/AURELIA_RESEARCH_START_HERE.md)
and the three runnable examples:

- `examples/01_load_aurelia_hf_datasets.py` — load all four datasets and print row counts
- `examples/02_reproduce_density_diversification.py` — reproduce the 99.1% population-CV reduction
- `examples/03_trace_causal_chain.py` — trace a causal chain from the federation graph

Each dataset's HF README links back to the examples and to the
[canon bridge](https://github.com/ousiaresearch/aurelia/blob/main/docs/AURELIA_CANON_AND_DATA_GUIDE.md).

## Reproducing the exports

```bash
# 1. Make sure at least one Aurelia run exists
ls /tmp/aurelia-run-100y  # the 100y baseline; any will do

# 2. Re-export all four datasets
export HF_OUT=/tmp/hf-export
rm -rf $HF_OUT
mkdir -p $HF_OUT

# (ds_key is the internal arg; slug is the HF-friendly dir name)
for pair in "causal_events:causal-events" \
            "civilization_metrics:civilization-metrics" \
            "federation_causal:federation-causal" \
            "npc_population:npc-population"; do
  ds_key=${pair%%:*}
  slug=${pair##*:}

  PYTHONPATH=. python3 scripts/export_hf_dataset.py \
    --dataset "$ds_key" \
    --auto \
    --out "$HF_OUT/aurelia-$slug" \
    --format parquet \
    --manifest

  PYTHONPATH=. python3 scripts/render_hf_readme.py \
    --dataset "$ds_key" \
    --export-root "$HF_OUT"
done
```

**Note**: the exporter takes the dataset name with underscores (`causal_events`)
as a CLI arg, but the on-disk directory uses hyphens (`aurelia-causal-events`)
to match HF repo naming. Keep these straight in the loop, or HF will reject the
repo name with an "invalid name" error at upload time.

`--auto` discovers all standard run directories (`/tmp/aurelia-bolster-scan`,
`/tmp/aurelia-run-100y`, `/tmp/aurelia-run-200y`, `/tmp/aurelia-run-density`,
`/tmp/aurelia-cf-solara-aid`). Use `--runs` to export a subset:

```bash
PYTHONPATH=. python3 scripts/export_hf_dataset.py \
  --dataset causal_events \
  --runs /tmp/aurelia-run-100y,/tmp/aurelia-run-200y \
  --run-ids phase11-100y,phase11-200y \
  --out $HF_OUT/aurelia-causal-events \
  --format parquet
```

## Token handling

`scripts/export_hf_dataset.py` and `scripts/render_hf_readme.py` **never**
read or contact the HF Hub. They are pure offline transformations. The token
is only needed at the `hf upload` step.

Store the token in `~/.hermes/auth.json` as `hf_token` so that future
agent runs (e.g. a scheduled "publish new run" cron) can pick it up
without shell history leakage.

## Adding a new run later

When a new Aurelia run completes (e.g. after a Colab session), the
publishing steps are:

```bash
# 1. Export the new run into the existing dataset dirs
PYTHONPATH=. python3 scripts/export_hf_dataset.py \
  --dataset causal_events \
  --runs /tmp/aurelia-run-new \
  --run-ids phase12-new \
  --out $HF_OUT/aurelia-causal-events \
  --format parquet

# 2. Re-render the README so the per-run table picks up the new row count
PYTHONPATH=. python3 scripts/render_hf_readme.py \
  --dataset causal_events \
  --export-root $HF_OUT

# 3. Upload only the new run's directory + the new README
hf upload ousiaresearch/aurelia-causal-events \
  $HF_OUT/aurelia-causal-events/data/phase12-new \
  data/phase12-new \
  --repo-type dataset
hf upload ousiaresearch/aurelia-causal-events \
  $HF_OUT/aurelia-causal-events/README.md \
  README.md \
  --repo-type dataset
```

`hf upload` is incremental; unchanged files are not re-sent.

## Schema stability

The export schema is pinned to the SQLite `causal_events`,
`civilization_metrics`, `federation.causal_events`, `federation.causal_edges`,
and per-world `agents` + `events` tables. Schema changes upstream (column
additions, type changes) will require a coordinated bump here. Until that
happens, the dataset version on HF is "v1" (implicit; no version tag in
the repo).

## Verification after upload

```bash
# Sanity: load from HF and inspect a row
python3 -c "
from datasets import load_dataset
ds = load_dataset('ousiaresearch/aurelia-causal-events', split='train', streaming=True)
for row in ds:
    print(row)
    break
"
```

A successful round-trip means: row has the expected 14 fields, payload is a
JSON object, actor_ids is a list. The export test (`tests/test_hf_export.py`)
asserts the same shape on the local file.
