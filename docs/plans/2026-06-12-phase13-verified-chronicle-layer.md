# Phase 13 Verified Chronicle Layer Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Lead Aurelia from a stable causal simulation into a verified civilization chronicle system where public narrative artifacts are traceable back to reports, run artifacts, causal events, and counterfactual branches.

**Architecture:** Close the public truth boundary first, refresh the Observatory second, then build the smallest Phase 13 proof as a deterministic provenance-preserving renderer before any LLM prose. The first chronicle layer should be extractive and auditable: every card cites source paths, run IDs, world/year coordinates, metrics, and event evidence. Only after that scaffold is tested should LLM chronicle prose be allowed to sit on top.

**Tech Stack:** Python 3.11, SQLite run artifacts, Markdown/HTML docs, pytest, stdlib JSON/argparse/pathlib, existing Aurelia scripts under `scripts/`, existing Phase 13 substrate in `src_template/batch_chronicles.py`.

---

## Context from the 2026-06-12 snapshot

Source snapshot: `docs/PROJECT_STATUS_2026-06-12.md`.

Settled state:

- `pytest tests/ -q` passes with 166 collected tests.
- `CHANGELOG.md` has `0.1.6-phase12-engine-stability`.
- Counterfactual UX is shipped via `examples/04_run_counterfactual_branch.py` and `docs/AURELIA_COUNTERFACTUALS.md`.
- 5-seed 50y sweep is published in `docs/reports/phase12-seed-sweep-report.md`.
- Post-fix run comparison is published in `docs/reports/phase11-runs-comparison.md`.
- `src_template/batch_chronicles.py` exists, but Phase 13 is not wired into the current proof/publication flow.

Strategic sequence:

1. Truth-surface release pass.
2. Observatory refresh.
3. Phase 13 verified chronicle proof.
4. Counterfactual gallery and larger calibration sweep.

---

## Acceptance criteria for this plan

By the end of execution:

- `README.md`, `docs/ROADMAP.md`, and git tags agree that `0.1.6-phase12-engine-stability` is the current closed boundary and Phase 13 is active.
- `docs/observatory/index.html` visibly advertises the post-fix 0.1.6 truth surface, counterfactual demo, seed sweep, and D1 cap caveat.
- A new deterministic script, `scripts/render_verified_chronicles.py`, renders provenance-preserving Phase 13 chronicle cards from run artifacts or fallback report fixtures.
- A new docs page, `docs/PHASE13_VERIFIED_CHRONICLES.md`, explains the contract: no invented history, provenance required, LLM prose only after deterministic evidence exists.
- Tests prove the chronicle renderer emits source-backed cards and refuses/flags missing provenance.
- Full suite passes: `PYTHONPATH=. pytest tests/ -q`.
- Work is committed in logical units immediately.

---

## Phase 0: Branch and baseline verification

### Task 0.1: Create a working branch

**Objective:** Keep Phase 13 planning/execution isolated from `main` until reviewed.

**Files:** none.

**Steps:**

```bash
git status --short --branch
git pull --ff-only origin main
git checkout -b phase13-verified-chronicles
```

**Expected:** clean working tree, branch `phase13-verified-chronicles`.

**Commit:** none.

### Task 0.2: Re-run baseline tests

**Objective:** Confirm the repo is green before touching code.

**Files:** none.

**Steps:**

```bash
PYTHONPATH=. pytest tests/ -q
```

**Expected:** 166 tests pass.

**Commit:** none.

---

## Phase 1: Truth-surface release pass

### Task 1.1: Update README quickstart test count

**Objective:** Replace stale quickstart count with current test count.

**Files:**

- Modify: `README.md` around the Quickstart code block.

**Step 1: Verify current stale text**

```bash
grep -n "90 passed" README.md
```

**Expected:** one match in the Quickstart section.

**Step 2: Edit README**

Replace:

```bash
# 90 passed in ~11s
```

With:

```bash
# 166 passed
```

Keep runtime out unless re-measured in this task.

**Step 3: Verify text**

```bash
grep -n "166 passed" README.md
```

**Expected:** one match.

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs(aurelia): update quickstart test count"
```

### Task 1.2: Update ROADMAP status boundaries

**Objective:** Make the public roadmap reflect actual project state: Phase 11/12 closed, Phase 13 active.

**Files:**

- Modify: `docs/ROADMAP.md`.

**Step 1: Update Phase 11 status**

Change:

```markdown
Status: in progress.
```

Under Phase 11 to:

```markdown
Status: closed. Public observability, proof tools, report rendering, quality gates, and counterfactual branches are shipped.
```

**Step 2: Add Phase 12 status line**

Under `## Phase 12 — Calibrated production histories`, add:

```markdown
Status: closed for the 0.1.6 engine-stability boundary; continuing calibration sweeps are future research work.
```

**Step 3: Add Phase 13 status line**

Under `## Phase 13 — Narrative layer over verified history`, add:

```markdown
Status: active frontier. First target is a deterministic verified chronicle layer with provenance before any freeform LLM prose.
```

**Step 4: Verify**

```bash
grep -n "Status:" docs/ROADMAP.md
```

**Expected:** Phase 11, Phase 12, and Phase 13 each have a status line.

**Step 5: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(aurelia): mark phase 13 as active frontier"
```

### Task 1.3: Create the 0.1.6 release tag locally

**Objective:** Align git tags with the CHANGELOG release boundary.

**Files:** none.

**Step 1: Verify tag absence**

```bash
git tag --list 'v0.1.6-phase12-engine-stability'
```

**Expected:** no output.

**Step 2: Create annotated tag**

```bash
git tag -a v0.1.6-phase12-engine-stability -m "Aurelia 0.1.6: Phase 12 engine stability"
```

**Step 3: Verify tag**

```bash
git tag --list 'v0.1.6-phase12-engine-stability'
```

**Expected:** `v0.1.6-phase12-engine-stability`.

**Commit:** none; tags are pushed later with `git push origin v0.1.6-phase12-engine-stability`.

---

## Phase 2: Observatory refresh

### Task 2.1: Add static 0.1.6 proof section to Observatory

**Objective:** Make `docs/observatory/index.html` show the current truth even if Cloudflare data is stale or capped.

**Files:**

- Modify: `docs/observatory/index.html`.

**Step 1: Add HTML panel after the hero or before live metrics**

Add a section with this content, adapted to existing CSS classes:

```html
<section class="panel proof-panel">
  <div class="eyebrow">0.1.6 post-fix engine</div>
  <h2>Stable causal histories, counterfactual branches, seed-sweep evidence.</h2>
  <p>The current public proof surface is the 0.1.6 Phase 12 engine-stability boundary: feedback loops capped, reports refreshed, counterfactual demo shipped, and a five-seed sweep completed.</p>
  <ul>
    <li><strong>Tests:</strong> 166 passing tests.</li>
    <li><strong>Seed sweep:</strong> 5 seeds at 50y, D1 quality 0.85 for all five.</li>
    <li><strong>Counterfactual:</strong> same-seed density_diversification 0.0 vs 1.0 branch with measurable divergence.</li>
    <li><strong>D1 caveat:</strong> Cloudflare is the public observability plane; local/HF artifacts remain the complete research archive for long runs.</li>
  </ul>
  <p><a href="../reports/phase12-seed-sweep-report.md">Seed sweep report</a> · <a href="../AURELIA_COUNTERFACTUALS.md">Counterfactual guide</a> · <a href="../PROJECT_STATUS_2026-06-12.md">Project status</a></p>
</section>
```

**Step 2: Add minimal CSS if needed**

If the section needs spacing, add:

```css
.proof-panel { margin-bottom: 22px; }
.proof-panel ul { color: var(--muted); line-height: 1.6; }
.proof-panel strong { color: var(--ink); }
```

**Step 3: Verify static content exists**

```bash
grep -n "0.1.6 post-fix engine\|Seed sweep report\|Counterfactual guide" docs/observatory/index.html
```

**Expected:** all three terms appear.

**Step 4: Commit**

```bash
git add docs/observatory/index.html
git commit -m "docs(aurelia): refresh observatory proof surface"
```

### Task 2.2: Add a tiny Observatory smoke test

**Objective:** Prevent the Observatory from losing its static proof links.

**Files:**

- Create: `tests/test_observatory_static.py`.

**Step 1: Write failing test**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_observatory_links_current_phase12_truth_surface():
    html = (ROOT / "docs" / "observatory" / "index.html").read_text()

    assert "0.1.6 post-fix engine" in html
    assert "phase12-seed-sweep-report.md" in html
    assert "AURELIA_COUNTERFACTUALS.md" in html
    assert "PROJECT_STATUS_2026-06-12.md" in html
    assert "D1 caveat" in html or "Cloudflare is the public observability plane" in html
```

**Step 2: Run RED before the HTML edit if doing this first**

```bash
PYTHONPATH=. pytest tests/test_observatory_static.py -q
```

**Expected if run before Task 2.1:** fail on missing `0.1.6 post-fix engine`.

**Step 3: Run GREEN after Task 2.1**

```bash
PYTHONPATH=. pytest tests/test_observatory_static.py -q
```

**Expected:** pass.

**Step 4: Commit if separate from Task 2.1**

```bash
git add tests/test_observatory_static.py
git commit -m "test(aurelia): guard observatory proof links"
```

---

## Phase 3: Deterministic verified chronicle renderer

### Task 3.1: Create test fixture for a minimal run with yearly reports

**Objective:** Give Phase 13 tests a tiny synthetic run that exercises world/year/evidence extraction without needing real long-run artifacts.

**Files:**

- Create: `tests/test_verified_chronicles.py`.
- Create or reuse helper functions inside the test file.

**Step 1: Write fixture helper**

Use this as the starting helper:

```python
import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_verified_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    db = sqlite3.connect(run_dir / "solara.db")
    db.executescript(
        """
        CREATE TABLE causal_events (
            event_id TEXT PRIMARY KEY,
            tick_number INTEGER,
            world_id TEXT,
            layer TEXT,
            event_type TEXT,
            actor_ids TEXT,
            target_ids TEXT,
            scope TEXT,
            magnitude REAL,
            valence REAL,
            confidence REAL,
            payload TEXT,
            created_at REAL
        );
        CREATE TABLE causal_edges (
            parent_event_id TEXT,
            child_event_id TEXT,
            relation TEXT,
            weight REAL
        );
        CREATE TABLE civilization_metrics (
            world_id TEXT,
            tick_number INTEGER,
            education_level REAL,
            urbanization REAL,
            youth_bulge REAL,
            disease_pressure REAL,
            resource_stock REAL,
            property_rights REAL,
            state_capacity_type TEXT,
            repression_type TEXT,
            conflict_type TEXT,
            path_lock_in REAL,
            payload TEXT,
            created_at REAL
        );
        CREATE TABLE agents (id TEXT, type TEXT, state TEXT);
        """
    )
    db.executemany(
        "INSERT INTO causal_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("e1", 1, "solara", "micro", "drought_signal", "[]", "[]", "world", 0.4, -1, 0.9, "{}", 1.0),
            ("e2", 2, "solara", "macro", "food_security_decline", "[]", "[]", "world", 0.6, -1, 0.9, "{}", 2.0),
            ("e3", 3, "solara", "macro", "reconciliation_process", "[]", "[]", "world", 0.7, 1, 0.9, "{}", 3.0),
        ],
    )
    db.executemany("INSERT INTO causal_edges VALUES (?,?,?,?)", [("e1", "e2", "caused", 0.7), ("e2", "e3", "softened", 0.8)])
    db.execute("INSERT INTO civilization_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("solara", 3, 0.3, 0.25, 0.7, 0.4, 0.5, 0.45, "patrimonial", "legal", "latent", 0.1, "{}", 3.0))
    db.executemany("INSERT INTO agents VALUES (?,?,?)", [("a1", "npc", "active"), ("a2", "npc", "deceased")])
    db.commit()
    db.close()

    (run_dir / "causal_summary.json").write_text(json.dumps({
        "run_id": "phase13-fixture",
        "years": 1,
        "ticks": 3,
        "ticks_per_year": 3,
        "seed": 4242,
        "worlds": {"solara": {"population": 1, "deceased": 1, "factions": 0}},
        "yearly_reports": [
            {
                "world_id": "solara",
                "year": 1,
                "population": 1,
                "births": 0,
                "deaths": 1,
                "factions": {},
                "causal_highlights": [
                    {"event_type": "reconciliation_process", "count": 1},
                    {"event_type": "food_security_decline", "count": 1}
                ]
            }
        ]
    }))
    return run_dir
```

**Step 2: Commit only after tests and implementation pass in later tasks.**

### Task 3.2: Define the verified card contract with a failing test

**Objective:** Specify exactly what the renderer must emit before implementing it.

**Files:**

- Modify: `tests/test_verified_chronicles.py`.

**Step 1: Add failing test**

```python
def test_render_verified_chronicle_card_contains_provenance(tmp_path):
    run_dir = make_verified_run(tmp_path)
    mod = load_script("render_verified_chronicles")

    cards = mod.build_verified_chronicle_cards(run_dir)

    assert len(cards) == 1
    card = cards[0]
    assert card["run_id"] == "phase13-fixture"
    assert card["world_id"] == "solara"
    assert card["year"] == 1
    assert card["source_paths"]["summary"].endswith("causal_summary.json")
    assert card["source_paths"]["world_db"].endswith("solara.db")
    assert card["metrics"]["population"] == 1
    assert "reconciliation_process" in card["evidence"]["top_event_types"]
    assert card["provenance_status"] == "verified"
```

**Step 2: Run RED**

```bash
PYTHONPATH=. pytest tests/test_verified_chronicles.py::test_render_verified_chronicle_card_contains_provenance -q
```

**Expected:** fail because `scripts/render_verified_chronicles.py` does not exist.

### Task 3.3: Implement minimal card builder

**Objective:** Build the smallest deterministic data structure that satisfies the contract.

**Files:**

- Create: `scripts/render_verified_chronicles.py`.

**Step 1: Add implementation**

Start with:

```python
#!/usr/bin/env python3
"""Render provenance-preserving Phase 13 verified chronicle cards."""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]


def _load_summary(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "causal_summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _top_event_types(db_path: Path, world_id: str, start_tick: int | None, end_tick: int | None) -> list[str]:
    if not db_path.exists():
        return []
    db = sqlite3.connect(db_path)
    try:
        where = ["world_id = ?"]
        args: list[Any] = [world_id]
        if start_tick is not None:
            where.append("tick_number >= ?")
            args.append(start_tick)
        if end_tick is not None:
            where.append("tick_number <= ?")
            args.append(end_tick)
        sql = f"SELECT event_type, COUNT(*) FROM causal_events WHERE {' AND '.join(where)} GROUP BY event_type ORDER BY COUNT(*) DESC, event_type LIMIT 8"
        return [row[0] for row in db.execute(sql, args).fetchall()]
    finally:
        db.close()


def _year_tick_bounds(year: int, ticks_per_year: int | None) -> tuple[int | None, int | None]:
    if not ticks_per_year:
        return None, None
    start = ((year - 1) * ticks_per_year) + 1
    end = year * ticks_per_year
    return start, end


def build_verified_chronicle_cards(run_dir: str | Path) -> list[dict[str, Any]]:
    run_dir = Path(run_dir)
    summary = _load_summary(run_dir)
    ticks_per_year = summary.get("ticks_per_year")
    run_id = summary.get("run_id") or run_dir.name
    cards: list[dict[str, Any]] = []

    for report in summary.get("yearly_reports", []):
        world_id = report.get("world_id")
        year = int(report.get("year", 0))
        if not world_id or not year:
            continue
        world_db = run_dir / f"{world_id}.db"
        start_tick, end_tick = _year_tick_bounds(year, ticks_per_year)
        top_event_types = _top_event_types(world_db, world_id, start_tick, end_tick)
        if not top_event_types:
            top_event_types = [h.get("event_type") for h in report.get("causal_highlights", []) if h.get("event_type")]
        cards.append({
            "run_id": run_id,
            "world_id": world_id,
            "year": year,
            "title": f"Year {year} — {world_id.title()}",
            "metrics": {
                "population": report.get("population"),
                "births": report.get("births"),
                "deaths": report.get("deaths"),
                "factions": len(report.get("factions") or {}),
            },
            "evidence": {
                "top_event_types": top_event_types,
                "causal_highlights": report.get("causal_highlights", []),
                "tick_range": [start_tick, end_tick],
            },
            "source_paths": {
                "summary": str(run_dir / "causal_summary.json"),
                "world_db": str(world_db),
            },
            "provenance_status": "verified" if world_db.exists() and summary else "partial",
        })
    return cards
```

**Step 2: Run GREEN**

```bash
PYTHONPATH=. pytest tests/test_verified_chronicles.py::test_render_verified_chronicle_card_contains_provenance -q
```

**Expected:** pass.

### Task 3.4: Add Markdown rendering contract

**Objective:** Produce human-readable chronicle cards without losing provenance.

**Files:**

- Modify: `tests/test_verified_chronicles.py`.
- Modify: `scripts/render_verified_chronicles.py`.

**Step 1: Add failing test**

```python
def test_render_verified_chronicle_markdown_keeps_evidence_visible(tmp_path):
    run_dir = make_verified_run(tmp_path)
    mod = load_script("render_verified_chronicles")

    markdown = mod.render_verified_chronicles_markdown(run_dir)

    assert "# Aurelia Verified Chronicles" in markdown
    assert "## Year 1 — Solara" in markdown
    assert "Provenance: verified" in markdown
    assert "reconciliation_process" in markdown
    assert "Source summary:" in markdown
    assert "Source DB:" in markdown
```

**Step 2: Run RED**

```bash
PYTHONPATH=. pytest tests/test_verified_chronicles.py::test_render_verified_chronicle_markdown_keeps_evidence_visible -q
```

**Expected:** fail because `render_verified_chronicles_markdown` does not exist.

**Step 3: Implement Markdown renderer**

Add:

```python
def render_verified_chronicles_markdown(run_dir: str | Path) -> str:
    cards = build_verified_chronicle_cards(run_dir)
    lines = ["# Aurelia Verified Chronicles", ""]
    lines.append("Deterministic Phase 13 chronicle cards. These are evidence-backed summaries, not freeform invented prose.")
    lines.append("")
    for card in cards:
        lines.append(f"## Year {card['year']} — {card['world_id'].title()}")
        lines.append("")
        lines.append(f"- Run: `{card['run_id']}`")
        lines.append(f"- Provenance: {card['provenance_status']}")
        lines.append(f"- Population: {card['metrics'].get('population')}")
        lines.append(f"- Births / deaths: {card['metrics'].get('births')} / {card['metrics'].get('deaths')}")
        events = card["evidence"].get("top_event_types", [])
        lines.append(f"- Evidence event types: {', '.join(events) if events else 'none'}")
        lines.append(f"- Source summary: `{card['source_paths']['summary']}`")
        lines.append(f"- Source DB: `{card['source_paths']['world_db']}`")
        lines.append("")
    return "\n".join(lines)
```

**Step 4: Run GREEN**

```bash
PYTHONPATH=. pytest tests/test_verified_chronicles.py::test_render_verified_chronicle_markdown_keeps_evidence_visible -q
```

**Expected:** pass.

### Task 3.5: Add CLI writer

**Objective:** Let operators render verified chronicles from any run directory into docs/reports or a staging path.

**Files:**

- Modify: `tests/test_verified_chronicles.py`.
- Modify: `scripts/render_verified_chronicles.py`.

**Step 1: Add failing test**

```python
def test_cli_writes_verified_chronicle_markdown(tmp_path):
    run_dir = make_verified_run(tmp_path)
    output = tmp_path / "chronicles.md"
    mod = load_script("render_verified_chronicles")

    mod.main(["--run-dir", str(run_dir), "--output", str(output)])

    text = output.read_text()
    assert "Aurelia Verified Chronicles" in text
    assert "Year 1 — Solara" in text
```

**Step 2: Run RED**

```bash
PYTHONPATH=. pytest tests/test_verified_chronicles.py::test_cli_writes_verified_chronicle_markdown -q
```

**Expected:** fail because `main` has no argv parameter or does not exist.

**Step 3: Implement CLI**

Add:

```python
def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    text = render_verified_chronicles_markdown(args.run_dir)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(f"wrote {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
```

**Step 4: Run GREEN**

```bash
PYTHONPATH=. pytest tests/test_verified_chronicles.py::test_cli_writes_verified_chronicle_markdown -q
```

**Expected:** pass.

### Task 3.6: Commit verified renderer and tests

**Objective:** Save the deterministic Phase 13 proof foundation as one logical unit.

**Files:**

- `scripts/render_verified_chronicles.py`
- `tests/test_verified_chronicles.py`

**Step 1: Run targeted tests**

```bash
PYTHONPATH=. pytest tests/test_verified_chronicles.py -q
```

**Expected:** all tests in the file pass.

**Step 2: Run related existing tests**

```bash
PYTHONPATH=. pytest tests/test_phase11_tools.py tests/test_run_quality_gates.py -q
```

**Expected:** pass.

**Step 3: Commit**

```bash
git add scripts/render_verified_chronicles.py tests/test_verified_chronicles.py
git commit -m "feat(aurelia): render verified chronicle cards"
```

---

## Phase 4: Phase 13 documentation and first published proof page

### Task 4.1: Add Phase 13 contract doc

**Objective:** Define the rules for verified chronicles before anyone adds freeform LLM prose.

**Files:**

- Create: `docs/PHASE13_VERIFIED_CHRONICLES.md`.

**Content skeleton:**

```markdown
# Aurelia Phase 13 — Verified Chronicles

Phase 13 turns verified causal histories into readable civilization chronicles.
The rule is simple: **no invented history**.

## Chronicle contract

A verified chronicle card must include:

- run ID
- world ID
- year
- source summary path
- source world DB path
- population/birth/death/faction metrics if available
- event evidence from `causal_events` or `causal_summary.json`
- provenance status: `verified` or `partial`

## Why deterministic first

LLM prose can only be as trustworthy as the evidence scaffold beneath it.
The first renderer is deterministic so that every statement is auditable.

## Operator command

```bash
PYTHONPATH=. python3 scripts/render_verified_chronicles.py \
  --run-dir /path/to/aurelia-run \
  --output docs/reports/phase13-verified-chronicles.md
```

## LLM layer rule

`src_template/batch_chronicles.py` may generate prose only after deterministic cards exist.
Generated prose should cite or carry the card evidence, not replace it.
```

**Step 1: Write the doc.**

**Step 2: Commit**

```bash
git add docs/PHASE13_VERIFIED_CHRONICLES.md
git commit -m "docs(aurelia): define phase 13 verified chronicle contract"
```

### Task 4.2: Link Phase 13 doc from README and ROADMAP

**Objective:** Make the new Phase 13 entry point discoverable.

**Files:**

- Modify: `README.md`.
- Modify: `docs/ROADMAP.md`.

**Step 1: README link**

Add to Documentation map or Roadmap section:

```markdown
- [`docs/PHASE13_VERIFIED_CHRONICLES.md`](docs/PHASE13_VERIFIED_CHRONICLES.md) — Phase 13 contract for provenance-preserving narrative artifacts.
```

**Step 2: ROADMAP link**

Under Phase 13, add:

```markdown
- First implementation target: [`PHASE13_VERIFIED_CHRONICLES.md`](PHASE13_VERIFIED_CHRONICLES.md) and `scripts/render_verified_chronicles.py`.
```

**Step 3: Verify links**

```bash
grep -n "PHASE13_VERIFIED_CHRONICLES" README.md docs/ROADMAP.md
```

**Expected:** both files contain the link.

**Step 4: Commit**

```bash
git add README.md docs/ROADMAP.md
git commit -m "docs(aurelia): link phase 13 chronicle frontier"
```

---

## Phase 5: First generated verified chronicle artifact

### Task 5.1: Find a suitable existing run artifact

**Objective:** Render the first chronicle artifact from a real or currently staged Aurelia run, not from invented data.

**Files:** none initially.

**Step 1: Discover likely run directories**

```bash
find /tmp -maxdepth 2 -type f -name 'causal_summary.json' -print
find . -maxdepth 4 -type f -name 'causal_summary.json' -print
```

If `find` is avoided in Hermes tool mode, use `search_files('causal_summary.json', target='files', path='/tmp')` and `search_files('causal_summary.json', target='files', path='.')`.

**Step 2: Pick the most current run**

Prefer post-fix runs used for `docs/reports/phase11-*` or the Phase 12 seed sweep.

**Step 3: If no run exists, generate a tiny smoke run only if fast and deterministic**

Use existing project commands if documented. Do not invent a run path.

### Task 5.2: Render `docs/reports/phase13-verified-chronicles.md`

**Objective:** Publish the first deterministic Phase 13 artifact.

**Files:**

- Create: `docs/reports/phase13-verified-chronicles.md`.

**Step 1: Run renderer**

```bash
PYTHONPATH=. python3 scripts/render_verified_chronicles.py \
  --run-dir /path/to/selected/run \
  --output docs/reports/phase13-verified-chronicles.md
```

**Expected:** prints `wrote docs/reports/phase13-verified-chronicles.md`.

**Step 2: Inspect output**

```bash
grep -n "Provenance:\|Source summary:\|Source DB:" docs/reports/phase13-verified-chronicles.md | head -20
```

**Expected:** every card carries provenance lines.

**Step 3: Commit**

```bash
git add docs/reports/phase13-verified-chronicles.md
git commit -m "docs(aurelia): publish first verified chronicle artifact"
```

---

## Phase 6: Final verification and publish

### Task 6.1: Run full suite

**Objective:** Prove the repo is green after the plan execution.

**Files:** none.

**Steps:**

```bash
PYTHONPATH=. pytest tests/ -q
```

**Expected:** full suite passes.

### Task 6.2: Push branch and tag

**Objective:** Publish the work and release tag.

**Steps:**

```bash
git status --short --branch
git push origin phase13-verified-chronicles
git push origin v0.1.6-phase12-engine-stability
```

If direct-to-main is preferred after review:

```bash
git checkout main
git merge --ff-only phase13-verified-chronicles
git push origin main
git push origin v0.1.6-phase12-engine-stability
```

### Task 6.3: Write next status snapshot

**Objective:** Preserve the new settled boundary for future sessions.

**Files:**

- Create: `docs/PROJECT_STATUS_2026-06-13.md` or current date when executed.

**Content:** follow `project-snapshot-review` format. Record:

- 0.1.6 tag exists.
- Observatory proof surface is refreshed.
- Verified chronicle renderer exists and is tested.
- First chronicle artifact exists or note why no real run artifact was available.
- Next push: LLM prose over deterministic cards, counterfactual gallery, larger calibration sweep.

**Commit:**

```bash
git add docs/PROJECT_STATUS_YYYY-MM-DD.md
git commit -m "docs: snapshot phase 13 verified chronicle progress"
```

---

## Risk controls

- **No invented history:** deterministic cards can only cite summary/DB evidence. If evidence is missing, mark `partial`.
- **No LLM-first prose:** `src_template/batch_chronicles.py` is future integration, not Task 1.
- **No public social posting without approval:** release package can be drafted later, not posted.
- **Cloudflare D1 cap remains honest:** Observatory must say Cloudflare is an observability plane, not the full archive.
- **Frequent commits:** commit after every logical unit; do not leave plan execution as a large uncommitted diff.

---

## Recommended execution order

Do these first, in order:

1. Phase 1: truth-surface release pass.
2. Phase 2: Observatory refresh.
3. Phase 3: deterministic verified chronicle renderer.
4. Phase 4: Phase 13 docs.
5. Phase 5 only if a real run artifact is available or cheap to regenerate.
6. Phase 6: full suite, push, tag, status snapshot.

This turns Phase 13 from "narrative layer" into an auditable product surface: every chronicle starts as a verified card, and every later prose paragraph has something real to stand on.
