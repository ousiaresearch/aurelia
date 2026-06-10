# Aurelia Demo

This demo proves the engine runs, writes SQLite artifacts, produces yearly reports, and advances all five worlds through the same barrier-synchronized federation clock.

## 1. Clone and install

```bash
git clone https://github.com/ousiaresearch/aurelia.git
cd aurelia
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 2. Run the test suite

```bash
PYTHONPATH=. python -m pytest tests -q
```

Expected: all tests pass.

## 3. Run a tiny deterministic smoke simulation

```bash
PYTHONPATH=. python causal_run.py \
  --clean \
  --output /tmp/aurelia-demo \
  --years 5 \
  --npcs 200 \
  --ticks-per-year 12 \
  --max-interactions 120 \
  --seed 4242
```

Expected output shape:

```text
=== Aurelia Causal Federation Run Complete ===
Output: /tmp/aurelia-demo
Ticks: 60 | Years: 5
Cross-world effects scheduled/imported: .../...
  arkos: pop=... dead=... factions=...
  mirithane: pop=... dead=... factions=...
  solara: pop=... dead=... factions=...
  valdris: pop=... dead=... factions=...
  verge: pop=... dead=... factions=...
```

## 4. Inspect generated artifacts

```bash
python - <<'PY'
import json, sqlite3
from pathlib import Path
out = Path('/tmp/aurelia-demo')
summary = json.loads((out / 'causal_summary.json').read_text())
print('worlds:', summary['worlds'])
print('years:', summary['years'], 'ticks:', summary['ticks'])
for world_id in sorted(summary['worlds']):
    db = sqlite3.connect(out / f'{world_id}.db')
    events = db.execute('SELECT COUNT(*) FROM causal_events').fetchone()[0]
    edges = db.execute('SELECT COUNT(*) FROM causal_edges').fetchone()[0]
    print(world_id, 'events=', events, 'edges=', edges)
PY
```

## 5. Push completed run artifacts to Cloudflare

Cloudflare upload requires the local operator secret at `~/.hermes/profiles/palantir/cf-worker/.secret`. Do not put that secret in the repo.

**Note on D1 cap:** the Worker runs on the D1 Free plan (500MB cap). For long runs, the cap can cause partial movement/diffusion ingestion. The local Parquet export and the HuggingFace datasets are the complete research archive. See `docs/ARCHITECTURE.md` and `docs/reports/public-surface-reconciliation.md` for the exact status of each surface.

```bash
PYTHONPATH=. python aurelia_cf_pusher.py
```

Then check from the operator machine without copying the secret into the shell history:

```bash
python - <<'PY'
from pathlib import Path
import urllib.request
secret = Path('~/.hermes/profiles/palantir/cf-worker/.secret').expanduser().read_text().strip()
req = urllib.request.Request(
    'https://hermes-state-worker.plntrprotocol.workers.dev/aurelia/dashboard',
    headers={'User-Agent': 'Aurelia-Demo/1.0', 'X-Hermes-Secret': secret},
)
print(urllib.request.urlopen(req, timeout=20).read().decode())
PY
```

## 6. What to look for

A healthy run should show:

- all five worlds present
- world clocks advanced
- nonzero causal events
- nonzero causal edges
- nonzero yearly reports
- cross-world effects scheduled/imported
- discoveries/great persons in longer runs
- movement and diffusion in federation DBs

## Notes

- Do not stream every tick to Cloudflare. Run first, bulk-upload after completion.
- Use `/tmp/...` for long outputs to avoid iCloud/APFS locking issues.
- Purge `__pycache__` if behavior looks stale after source changes.
