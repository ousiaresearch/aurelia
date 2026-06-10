# Aurelia Phase 12 Gap-Closure Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. Use strict TDD for every code-producing task: write failing test, verify RED, implement minimal GREEN, run full suite, commit immediately.

**Goal:** Close the gap between Aurelia's wiki/lore layer, simulation mechanics, datasets, and public research surface so a stranger can trace each canonical concept from lore → code → run artifact → dataset row → report/notebook.

**Architecture:** Build a canonical concept bridge, then harden the proof surfaces around it. The plan adds a versioned canon map, validation scripts, public research guide, dataset examples, harsher run-quality gates, and reconciliation checks for local/HF/Cloudflare consistency. Lore expansion resumes only after these bridges exist.

**Tech Stack:** Python 3.11+, SQLite, PyArrow/Parquet, pytest, Markdown docs, HuggingFace dataset layout, Cloudflare Worker public JSON endpoints.

---

## Why this plan exists

Aurelia no longer lacks raw material. It has a large wiki, real simulation runs, public datasets, Cloudflare observability, and social assets. The gap is coherence across layers.

Current observed fractures:

- The Desktop wiki still says some stale things: 60,000 NPCs, local-only dashboard, not open source, Arien-built, single landmass, and TTRPG-adjacent assets.
- The public repo says a newer thing: abstract worlds, Ousia Research, Hermes-operated, MIT, Cloudflare Observatory, HF datasets, Phase 11 proof layer.
- The datasets are live, but a researcher still has to infer how to join them, what fields mean, and which notebook proves which claim.
- The simulation evaluator returns perfect `1.0` scores even when long runs contain warning signs such as zero factions in most worlds, Valdris collapsing to one NPC, partial Cloudflare ingestion, or metadata fields like `seed: 0` / `ticks_per_year: 0`.

This plan turns Aurelia from three impressive but separate artifacts into one inspectable system.

---

## Phase overview

### Phase 12.1 — Canon bridge

Create a canonical map of Aurelia concepts and their current status. Every major idea must say whether it is:

- canonical lore only
- actively simulated
- stored in SQLite
- exported to HF
- visible in Cloudflare
- demonstrated by a report/notebook
- stale/superseded/archived

### Phase 12.2 — Wiki reconciliation

Audit the Desktop wiki against the public repo. Do not delete deep lore. Add a public canon overlay and archive/supersession markers where needed.

### Phase 12.3 — Dataset research UX

Add executable examples and a public start-here guide. Prove the density-diversification result and one causal chain from HF/local exports.

### Phase 12.4 — Simulation quality gates

Make `evaluate_run_quality.py` honest. Add warnings/penalties for dead factions, population collapse, low diversity, zero/incorrect metadata, weak counterfactual divergence, and public-ingestion mismatch.

### Phase 12.5 — Public observability reconciliation

Add a local/HF/Cloudflare reconciliation report that shows what is fully public, what is partial, and what is blocked by D1 limits.

### Phase 12.6 — Final packaging

Update README/HF cards/social pack to point to the research start page, not scattered assets.

---

## Acceptance criteria for the whole phase

Aurelia Phase 12 gap-closure is complete when:

- `PYTHONPATH=. pytest tests/ -q` passes.
- A new `docs/AURELIA_CANON_AND_DATA_GUIDE.md` maps at least 25 concepts across wiki, code, DB, HF, Cloudflare, and reports.
- A new `docs/AURELIA_COHERENCE_AUDIT.md` marks stale wiki/public claims and their resolution.
- `examples/01_load_aurelia_hf_datasets.py` loads all four datasets or their local staged equivalent.
- `examples/02_reproduce_density_diversification.py` reproduces the 99.1% CV reduction from exported data or committed reports.
- `examples/03_trace_causal_chain.py` traces at least one event chain from causal events/edges.
- `scripts/evaluate_run_quality.py` no longer returns perfect scores for pathological runs.
- `scripts/reconcile_public_surfaces.py` produces a Markdown report comparing local run artifacts, HF exports, and Cloudflare public counts.
- README links the new start-here and canon/data guide.
- HF README renderer includes a link to the start-here guide and examples.

---

## Workstream A — Canon bridge

### Task A1: Define the canonical concept schema

**Objective:** Create a small YAML file that names Aurelia concepts and maps each one to lore, mechanics, tables, datasets, reports, and public status.

**Files:**
- Create: `docs/data/aurelia_concepts.yaml`
- Create: `tests/test_aurelia_concepts.py`

**Step 1: Write failing tests**

Create `tests/test_aurelia_concepts.py`:

```python
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "docs" / "data" / "aurelia_concepts.yaml"

REQUIRED_KEYS = {
    "id",
    "name",
    "status",
    "summary",
    "wiki_paths",
    "code_paths",
    "sqlite_tables",
    "hf_datasets",
    "cloudflare_surface",
    "proof_artifacts",
}

VALID_STATUS = {
    "simulated",
    "lore_only",
    "partial",
    "stale",
    "archived",
    "planned",
}


def test_concepts_file_exists_and_has_minimum_coverage():
    assert CONCEPTS.exists()
    data = yaml.safe_load(CONCEPTS.read_text())
    assert isinstance(data, list)
    assert len(data) >= 25


def test_each_concept_has_required_keys_and_valid_status():
    data = yaml.safe_load(CONCEPTS.read_text())
    for concept in data:
        assert REQUIRED_KEYS <= set(concept), concept.get("id")
        assert concept["status"] in VALID_STATUS
        assert concept["id"]
        assert concept["name"]
        assert concept["summary"]


def test_simulated_concepts_have_code_and_data_paths():
    data = yaml.safe_load(CONCEPTS.read_text())
    simulated = [c for c in data if c["status"] == "simulated"]
    assert len(simulated) >= 12
    for concept in simulated:
        assert concept["code_paths"], concept["id"]
        assert concept["sqlite_tables"], concept["id"]
        assert concept["hf_datasets"], concept["id"]
```

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=. pytest tests/test_aurelia_concepts.py -q
```

Expected: FAIL because `docs/data/aurelia_concepts.yaml` does not exist.

**Step 3: Create minimal concept map**

Create `docs/data/aurelia_concepts.yaml` with at least these concept IDs:

- `world`
- `npc`
- `human`
- `thren`
- `vorn`
- `glim`
- `faction`
- `institution`
- `regime`
- `education`
- `urbanization`
- `disease_pressure`
- `resource_stock`
- `property_rights`
- `state_capacity_type`
- `repression_type`
- `conflict_type`
- `migration`
- `cultural_diffusion`
- `diplomacy`
- `cross_world_effect`
- `discovery`
- `great_person`
- `causal_event`
- `causal_edge`
- `counterfactual_branch`
- `density_diversification`
- `glim_anomaly`
- `single_landmass_old_canon`
- `ttrpg_assets_old_canon`

Example entry:

```yaml
- id: density_diversification
  name: Density diversification
  status: simulated
  summary: Parameter that biases migration balancing to reduce cross-world population concentration.
  wiki_paths: []
  code_paths:
    - src_template/federation_orchestrator.py
    - src_template/phase10_dynamics.py
  sqlite_tables:
    - federation.cross_world_movements
    - agents
  hf_datasets:
    - OusiaResearch/aurelia-civilization-metrics
    - OusiaResearch/aurelia-npc-population
    - OusiaResearch/aurelia-federation-causal
  cloudflare_surface:
    - /public/aurelia/dashboard
    - /public/aurelia/runs
  proof_artifacts:
    - docs/reports/phase11-runs-comparison.md
  notes:
    - 99.1% population-CV reduction in phase11-density-100y-d07-seed3003 vs 100y baseline.
```

**Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=. pytest tests/test_aurelia_concepts.py -q
PYTHONPATH=. pytest tests/ -q
```

Expected: concept tests pass; full suite passes.

**Step 5: Commit**

```bash
git add docs/data/aurelia_concepts.yaml tests/test_aurelia_concepts.py
git commit -m "docs: add Aurelia canon concept map"
```

---

### Task A2: Render the canon/data guide from the concept map

**Objective:** Generate a readable Markdown bridge from the YAML concept map.

**Files:**
- Create: `scripts/render_canon_data_guide.py`
- Create: `docs/AURELIA_CANON_AND_DATA_GUIDE.md`
- Modify: `tests/test_aurelia_concepts.py`

**Step 1: Write failing tests**

Append to `tests/test_aurelia_concepts.py`:

```python
def test_rendered_canon_guide_exists_and_mentions_core_layers():
    guide = ROOT / "docs" / "AURELIA_CANON_AND_DATA_GUIDE.md"
    assert guide.exists()
    text = guide.read_text()
    assert "# Aurelia Canon and Data Guide" in text
    assert "## Concept index" in text
    assert "density_diversification" in text
    assert "OusiaResearch/aurelia-causal-events" in text
    assert "src_template/phase10_dynamics.py" in text
```

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=. pytest tests/test_aurelia_concepts.py::test_rendered_canon_guide_exists_and_mentions_core_layers -q
```

Expected: FAIL because guide does not exist.

**Step 3: Implement renderer**

Create `scripts/render_canon_data_guide.py`:

- Read `docs/data/aurelia_concepts.yaml`.
- Sort by `status`, then `id`.
- Write `docs/AURELIA_CANON_AND_DATA_GUIDE.md`.
- Include sections:
  - `# Aurelia Canon and Data Guide`
  - `## What this guide is`
  - `## Canon status legend`
  - `## Concept index`
  - one subsection per concept with wiki/code/SQLite/HF/Cloudflare/proof artifact bullets.
- Do not contact external services.

**Step 4: Generate the guide**

Run:

```bash
PYTHONPATH=. python3 scripts/render_canon_data_guide.py
```

Expected: writes `docs/AURELIA_CANON_AND_DATA_GUIDE.md`.

**Step 5: Verify GREEN**

Run:

```bash
PYTHONPATH=. pytest tests/test_aurelia_concepts.py -q
PYTHONPATH=. pytest tests/ -q
```

Expected: all pass.

**Step 6: Commit**

```bash
git add scripts/render_canon_data_guide.py docs/AURELIA_CANON_AND_DATA_GUIDE.md tests/test_aurelia_concepts.py
git commit -m "docs: render Aurelia canon and data guide"
```

---

## Workstream B — Wiki reconciliation

### Task B1: Add a coherence audit document

**Objective:** Record stale wiki claims, current public truth, and the required action for each mismatch.

**Files:**
- Create: `docs/AURELIA_COHERENCE_AUDIT.md`
- Modify: `tests/test_aurelia_concepts.py`

**Step 1: Write failing test**

Append:

```python
def test_coherence_audit_records_known_stale_claims():
    audit = ROOT / "docs" / "AURELIA_COHERENCE_AUDIT.md"
    assert audit.exists()
    text = audit.read_text()
    for phrase in [
        "60,000 NPCs",
        "not open source",
        "127.0.0.1:9001",
        "single landmass",
        "TTRPG-adjacent",
        "Arien",
    ]:
        assert phrase in text
    assert "current public canon" in text.lower()
    assert "resolution" in text.lower()
```

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=. pytest tests/test_aurelia_concepts.py::test_coherence_audit_records_known_stale_claims -q
```

Expected: FAIL.

**Step 3: Write audit document**

Create `docs/AURELIA_COHERENCE_AUDIT.md` with these required sections:

- `# Aurelia Coherence Audit`
- `## Current public canon`
- `## Stale or split claims`
- `## Desktop wiki reconciliation plan`
- `## Do not delete deep lore`
- `## Archive/supersession policy`
- `## Required follow-up PRs/commits`

Include at least these mismatch rows:

- 60,000 NPCs vs exported Phase 11 micro-society runs.
- single landmass/five countries vs abstract five-world topology.
- local dashboard only vs Cloudflare Observatory.
- not open source vs public MIT repo.
- Arien-built vs Ousia Research/Hermes Agent operated; preserve Arien as historical design lineage if desired.
- TTRPG files vs current non-TTRPG simulation mandate.
- `127.0.0.1:9001` local-daemon architecture vs current offline-run/Cloudflare-push architecture.

**Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=. pytest tests/test_aurelia_concepts.py -q
PYTHONPATH=. pytest tests/ -q
```

**Step 5: Commit**

```bash
git add docs/AURELIA_COHERENCE_AUDIT.md tests/test_aurelia_concepts.py
git commit -m "docs: add Aurelia coherence audit"
```

---

### Task B2: Add a Desktop wiki sync checklist without editing the wiki yet

**Objective:** Produce an operator checklist for reconciling `/Users/johann/Desktop/Aurelia` safely, without deleting lore.

**Files:**
- Create: `docs/WIKI_SYNC_CHECKLIST.md`

**Steps:**

1. Create `docs/WIKI_SYNC_CHECKLIST.md`.
2. Include exact Desktop paths to inspect:
   - `/Users/johann/Desktop/Aurelia/README.md`
   - `/Users/johann/Desktop/Aurelia/public/faq.md`
   - `/Users/johann/Desktop/Aurelia/media/media-kit.md`
   - `/Users/johann/Desktop/Aurelia/public/expansions-and-gaps.md`
   - `/Users/johann/Desktop/Aurelia/playable-types.md`
   - `/Users/johann/Desktop/Aurelia/adventure-hooks.md`
3. For each, specify resolution: keep, update, archive, or mark historical.
4. State that deep lore files should not be deleted; only public-facing claims need synchronization first.
5. No tests required unless a validator is added later.
6. Commit:

```bash
git add docs/WIKI_SYNC_CHECKLIST.md
git commit -m "docs: add Aurelia wiki sync checklist"
```

---

## Workstream C — Dataset research UX

### Task C1: Add a local/HF dataset loader helper

**Objective:** Create a reusable helper that loads either local `/tmp/hf-export` Parquet files or HF datasets, so examples work offline and online.

**Files:**
- Create: `examples/aurelia_dataset_loader.py`
- Create: `tests/test_dataset_examples.py`

**Step 1: Write failing tests**

Create `tests/test_dataset_examples.py`:

```python
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def load_example(name):
    path = ROOT / "examples" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dataset_loader_discovers_local_export_paths():
    mod = load_example("aurelia_dataset_loader")
    paths = mod.discover_local_parquet_files(Path("/tmp/hf-export"))
    assert isinstance(paths, dict)
    if Path("/tmp/hf-export").exists():
        assert "aurelia-causal-events" in paths
        assert paths["aurelia-causal-events"]


def test_dataset_loader_has_expected_dataset_names():
    mod = load_example("aurelia_dataset_loader")
    assert set(mod.DATASETS) == {
        "aurelia-causal-events",
        "aurelia-civilization-metrics",
        "aurelia-federation-causal",
        "aurelia-npc-population",
    }
```

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=. pytest tests/test_dataset_examples.py -q
```

Expected: FAIL because helper does not exist.

**Step 3: Implement helper**

`examples/aurelia_dataset_loader.py` should expose:

- `DATASETS`
- `HF_ORG = "OusiaResearch"`
- `discover_local_parquet_files(root: Path) -> dict[str, list[Path]]`
- `load_local_table(dataset: str, root: Path = Path("/tmp/hf-export")) -> pyarrow.Table`
- `print_summary(root: Path = Path("/tmp/hf-export")) -> None`

Keep it import-safe: no work at import time except constants.

**Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=. pytest tests/test_dataset_examples.py -q
PYTHONPATH=. pytest tests/ -q
```

**Step 5: Commit**

```bash
git add examples/aurelia_dataset_loader.py tests/test_dataset_examples.py
git commit -m "examples: add Aurelia dataset loader helper"
```

---

### Task C2: Add `01_load_aurelia_hf_datasets.py`

**Objective:** Give researchers a first runnable script that prints row counts and columns for all datasets.

**Files:**
- Create: `examples/01_load_aurelia_hf_datasets.py`
- Modify: `tests/test_dataset_examples.py`

**Test:** Assert the example has a `main()` function and imports without contacting HF.

```python
def test_load_aurelia_hf_datasets_example_imports():
    mod = load_example("01_load_aurelia_hf_datasets")
    assert hasattr(mod, "main")
```

**Implementation notes:**

- Use local `/tmp/hf-export` if present.
- If local export is absent, print instructions for HF loading rather than failing hard.
- Do not require network in tests.
- Include the exact HF URLs in comments/docstring.

**Verification:**

```bash
PYTHONPATH=. pytest tests/test_dataset_examples.py -q
PYTHONPATH=. python3 examples/01_load_aurelia_hf_datasets.py
```

**Commit:**

```bash
git add examples/01_load_aurelia_hf_datasets.py tests/test_dataset_examples.py
git commit -m "examples: add Aurelia HF loading walkthrough"
```

---

### Task C3: Add density-diversification reproduction example

**Objective:** Reproduce the headline 99.1% population-CV reduction using local exported NPC population data or the committed comparison report.

**Files:**
- Create: `examples/02_reproduce_density_diversification.py`
- Modify: `tests/test_dataset_examples.py`

**Test behavior:**

```python
def test_density_diversification_example_exposes_cv_function():
    mod = load_example("02_reproduce_density_diversification")
    assert round(mod.coefficient_of_variation([171, 29, 63, 58, 49]), 3) == 0.674
    assert round(mod.coefficient_of_variation([67, 67, 67, 67, 66]), 3) == 0.006
```

**Implementation notes:**

- Function: `coefficient_of_variation(values: list[int]) -> float` using population stddev, matching existing report values.
- Main path:
  - Prefer `/tmp/hf-export/aurelia-npc-population` if present.
  - Compute final populations by run/world from Parquet file row counts.
  - Fall back to hardcoded report values from `docs/reports/phase11-runs-comparison.md` with a clear note.
- Print baseline CV, density CV, and reduction percentage.

**Verification:**

```bash
PYTHONPATH=. pytest tests/test_dataset_examples.py::test_density_diversification_example_exposes_cv_function -q
PYTHONPATH=. python3 examples/02_reproduce_density_diversification.py
```

Expected output includes `99.1%` or `99.0%` depending rounding.

**Commit:**

```bash
git add examples/02_reproduce_density_diversification.py tests/test_dataset_examples.py
git commit -m "examples: reproduce density diversification result"
```

---

### Task C4: Add causal-chain trace example

**Objective:** Demonstrate how a researcher inspects causality rather than only row counts.

**Files:**
- Create: `examples/03_trace_causal_chain.py`
- Modify: `tests/test_dataset_examples.py`

**Test behavior:**

```python
def test_trace_causal_chain_builds_parent_child_index():
    mod = load_example("03_trace_causal_chain")
    edges = [
        {"parent_event_id": "a", "child_event_id": "b", "relation": "caused"},
        {"parent_event_id": "b", "child_event_id": "c", "relation": "amplified"},
    ]
    index = mod.build_parent_index(edges)
    assert index["c"][0]["parent_event_id"] == "b"
    assert index["b"][0]["parent_event_id"] == "a"
```

**Implementation notes:**

- Load local federation causal `events.parquet` and `edges.parquet` if present.
- Choose a child event with at least one parent edge.
- Walk upstream to depth 3.
- Print event IDs, event types, relation labels, tick numbers, and worlds.
- If no local data exists, print HF download instructions and exit `0`.

**Verification:**

```bash
PYTHONPATH=. pytest tests/test_dataset_examples.py -q
PYTHONPATH=. python3 examples/03_trace_causal_chain.py
```

**Commit:**

```bash
git add examples/03_trace_causal_chain.py tests/test_dataset_examples.py
git commit -m "examples: add Aurelia causal-chain trace walkthrough"
```

---

### Task C5: Add public research start-here guide

**Objective:** Create the page that strangers should read before HF or GitHub details.

**Files:**
- Create: `docs/AURELIA_RESEARCH_START_HERE.md`
- Modify: `README.md`

**Content requirements:**

- One-paragraph statement of what Aurelia is.
- Links to four HF datasets.
- Three “try this first” commands:
  - load datasets
  - reproduce density result
  - trace causal chain
- Explain local vs HF mode.
- Explain known limitations:
  - abstract simulation, not forecast
  - Phase 11 exported runs are micro-society scale
  - Cloudflare D1 cap caused partial movement/diffusion ingestion for some long runs
  - lore/wiki canon is being reconciled
- Link to `docs/AURELIA_CANON_AND_DATA_GUIDE.md`.

**Verification:**

Run a link/path smoke check manually:

```bash
test -f docs/AURELIA_RESEARCH_START_HERE.md
test -f docs/AURELIA_CANON_AND_DATA_GUIDE.md
test -f examples/01_load_aurelia_hf_datasets.py
test -f examples/02_reproduce_density_diversification.py
test -f examples/03_trace_causal_chain.py
PYTHONPATH=. pytest tests/ -q
```

**Commit:**

```bash
git add docs/AURELIA_RESEARCH_START_HERE.md README.md
git commit -m "docs: add Aurelia research start-here guide"
```

---

## Workstream D — Simulation quality gates

### Task D1: Add fixtures for pathological run-quality cases

**Objective:** Ensure the evaluator can fail or warn on bad histories, not only reward event volume.

**Files:**
- Create: `tests/test_run_quality_gates.py`

**Step 1: Write tests first**

Create tests that build tiny fake run dirs using SQLite and `causal_summary.json`.

Required tests:

```python
def test_quality_warns_when_factions_never_form(tmp_path):
    ...


def test_quality_warns_on_population_collapse(tmp_path):
    ...


def test_quality_warns_on_missing_run_metadata(tmp_path):
    ...


def test_quality_does_not_saturate_to_one_for_pathological_run(tmp_path):
    ...
```

Expected assertions:

- Warnings include `faction formation is absent or sparse`.
- Warnings include `population collapse`.
- Warnings include `run metadata missing or zeroed`.
- `overall_score < 1.0` for a run with high event counts but pathological population/faction signals.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=. pytest tests/test_run_quality_gates.py -q
```

Expected: FAIL because `evaluate_run_quality.py` does not yet implement these warnings.

**Step 3: Implement quality gates**

Modify `scripts/evaluate_run_quality.py`:

- Add summary parsing for per-world population/deceased/factions.
- Add a `risk_flags` or expanded `warnings` list.
- Penalize `overall_score` after base score calculation.
- Add counts fields:
  - `min_world_population`
  - `max_world_population`
  - `population_cv`
  - `worlds_with_factions`
  - `total_factions`
- Gate ideas:
  - if `worlds_with_factions == 0`: warning + score cap ≤ 0.85
  - if any world population ≤ 1 in runs over 50 years: warning + score cap ≤ 0.80
  - if population CV > 1.0: warning + score cap ≤ 0.85
  - if `seed == 0` or `ticks_per_year == 0` in manifest/run metadata: warning, no hard cap unless other issues exist
  - if conflict type diversity ≤ world count: existing warning remains

Do not overfit to current runs. Make thresholds configurable constants at top of file.

**Step 4: Verify GREEN**

```bash
PYTHONPATH=. pytest tests/test_run_quality_gates.py -q
PYTHONPATH=. pytest tests/test_phase11_tools.py -q
PYTHONPATH=. pytest tests/ -q
```

**Step 5: Re-score existing runs**

Run:

```bash
PYTHONPATH=.:scripts python3 scripts/evaluate_run_quality.py --run-dir /tmp/aurelia-run-100y --output docs/reports/phase11-100y-quality.json
PYTHONPATH=.:scripts python3 scripts/evaluate_run_quality.py --run-dir /tmp/aurelia-run-200y --output docs/reports/phase11-200y-quality.json
PYTHONPATH=.:scripts python3 scripts/evaluate_run_quality.py --run-dir /tmp/aurelia-run-density --output docs/reports/phase11-density-100y-quality.json
```

Expected:

- 100y baseline should warn about sparse/no factions and high population CV.
- 200y baseline should warn about population collapse in Valdris and sparse/no factions.
- density run should still score well on population balance but may warn about sparse factions in non-Solara worlds.

**Step 6: Commit**

```bash
git add scripts/evaluate_run_quality.py tests/test_run_quality_gates.py docs/reports/*quality.json
git commit -m "feat: harden Aurelia run-quality gates"
```

---

### Task D2: Fix run metadata propagation

**Objective:** Ensure Cloudflare/HF/public run manifests carry real seed, ticks_per_year, density_diversification, engine version, and git commit.

**Files to inspect first:**
- `src_template/federation_orchestrator.py`
- `causal_run.py`
- `aurelia_cf_pusher.py`
- `scripts/export_hf_dataset.py`
- `scripts/render_hf_readme.py`

**Files likely modified:**
- `causal_run.py`
- `src_template/federation_orchestrator.py`
- `aurelia_cf_pusher.py`
- `scripts/export_hf_dataset.py`
- `tests/test_hf_export.py`
- `tests/test_federation_orchestrator.py` or new `tests/test_run_manifest.py`

**Test requirements:**

- A run manifest includes:
  - `run_id`
  - `seed`
  - `years`
  - `ticks`
  - `ticks_per_year`
  - `density_diversification`
  - `engine_version`
  - `git_commit`
  - `created_at`
- Exported HF `configs.json` includes manifest metadata per run.
- Cloudflare pusher sends manifest values without zeroing them.

**Verification:**

```bash
PYTHONPATH=. pytest tests/test_run_manifest.py tests/test_hf_export.py -q
PYTHONPATH=. pytest tests/ -q
```

**Commit:**

```bash
git add causal_run.py src_template/federation_orchestrator.py aurelia_cf_pusher.py scripts/export_hf_dataset.py scripts/render_hf_readme.py tests/test_run_manifest.py tests/test_hf_export.py
git commit -m "feat: preserve Aurelia run metadata across exports"
```

---

### Task D3: Add counterfactual divergence gates

**Objective:** Prevent counterfactual branches from being published as meaningful if they do not diverge from baseline.

**Files:**
- Modify: `scripts/compare_runs.py`
- Create or modify: `tests/test_counterfactuals.py`
- Modify: `docs/reports/` only after rerun.

**Tests:**

- Same baseline/branch with no intervention should report `divergence_score == 0` and warning.
- Branch with population/metric/event deltas should report nonzero divergence.
- Report includes top changed event types and metric deltas.

**Verification:**

```bash
PYTHONPATH=. pytest tests/test_counterfactuals.py -q
PYTHONPATH=. pytest tests/ -q
```

**Commit:**

```bash
git add scripts/compare_runs.py tests/test_counterfactuals.py
git commit -m "feat: add counterfactual divergence gates"
```

---

## Workstream E — Public surface reconciliation

### Task E1: Add offline public-surface reconciler

**Objective:** Compare local run artifacts, HF export directories, and Cloudflare public JSON counts in one report.

**Files:**
- Create: `scripts/reconcile_public_surfaces.py`
- Create: `tests/test_public_surface_reconciliation.py`
- Create generated report later: `docs/reports/public-surface-reconciliation.md`

**Step 1: Write failing tests**

Tests should use fake dictionaries, not network:

```python
def test_reconciler_reports_missing_cloudflare_counts():
    ...


def test_reconciler_marks_d1_cap_as_partial_not_failure():
    ...


def test_reconciler_renders_markdown_sections():
    ...
```

**Step 2: Implement script**

Required functions:

- `load_local_counts(run_dirs: list[Path]) -> dict`
- `load_hf_export_counts(root: Path) -> dict`
- `fetch_cloudflare_counts(url: str, user_agent: str = ...) -> dict`
- `compare_counts(local: dict, hf: dict, cf: dict) -> dict`
- `render_markdown(result: dict) -> str`

CLI:

```bash
PYTHONPATH=. python3 scripts/reconcile_public_surfaces.py \
  --hf-root /tmp/hf-export \
  --cloudflare-dashboard https://hermes-state-worker.plntrprotocol.workers.dev/public/aurelia/dashboard \
  --output docs/reports/public-surface-reconciliation.md
```

Important: use a browser-like `User-Agent`; earlier audit showed the public Worker returned 403 without one.

**Step 3: Verify GREEN**

```bash
PYTHONPATH=. pytest tests/test_public_surface_reconciliation.py -q
PYTHONPATH=. pytest tests/ -q
PYTHONPATH=. python3 scripts/reconcile_public_surfaces.py --hf-root /tmp/hf-export --output docs/reports/public-surface-reconciliation.md
```

Expected report sections:

- Local artifacts
- HF exports
- Cloudflare public dashboard
- Count mismatches
- Known D1 cap limitation
- Recommended remediation

**Commit:**

```bash
git add scripts/reconcile_public_surfaces.py tests/test_public_surface_reconciliation.py docs/reports/public-surface-reconciliation.md
git commit -m "feat: reconcile Aurelia public proof surfaces"
```

---

### Task E2: Update Cloudflare docs with the current D1 cap reality

**Objective:** Document that local/HF are source of truth for long-run full artifacts until D1 cap is resolved.

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `README.md`
- Modify: `docs/DEMO.md`

**Required language:**

- Cloudflare is the public observability plane, not currently the sole complete archive for long runs.
- D1 Free 500MB cap caused partial movement/diffusion ingestion for long runs.
- HF/local Parquet exports are the complete research archive for Phase 11.
- The reconciliation report states exact current status.

**Verification:**

```bash
PYTHONPATH=. pytest tests/ -q
```

**Commit:**

```bash
git add README.md docs/ARCHITECTURE.md docs/DEMO.md
git commit -m "docs: clarify Aurelia Cloudflare archive limitations"
```

---

## Workstream F — HF card and README integration

### Task F1: Teach HF README renderer to link examples and canon guide

**Objective:** Make every dataset card point to the start-here guide and examples.

**Files:**
- Modify: `scripts/render_hf_readme.py`
- Modify: `tests/test_hf_export.py`

**Test additions:**

- Rendered README includes `AURELIA_RESEARCH_START_HERE.md`.
- Rendered README includes `examples/02_reproduce_density_diversification.py` for relevant datasets or a shared examples section.
- Rendered README includes `AURELIA_CANON_AND_DATA_GUIDE.md`.

**Verification:**

```bash
PYTHONPATH=. pytest tests/test_hf_export.py -q
PYTHONPATH=. pytest tests/ -q
```

**Regenerate local HF README files:**

```bash
for ds in causal_events civilization_metrics federation_causal npc_population; do
  PYTHONPATH=. python3 scripts/render_hf_readme.py --dataset "$ds" --export-root /tmp/hf-export
done
```

**Commit:**

```bash
git add scripts/render_hf_readme.py tests/test_hf_export.py docs/HUGGINGFACE_PUBLISH.md
git commit -m "docs: link Aurelia HF cards to research guide"
```

Note: upload to HF is a separate side-effect step requiring explicit approval/token availability.

---

### Task F2: Add an examples section to README

**Objective:** Move the public user path from architecture-first to evidence-first.

**Files:**
- Modify: `README.md`

**Required section:**

Add near the HuggingFace section:

```markdown
## Start with the research examples

If you want to inspect Aurelia rather than read about it:

1. Load all four datasets: `python3 examples/01_load_aurelia_hf_datasets.py`
2. Reproduce the density-diversification result: `python3 examples/02_reproduce_density_diversification.py`
3. Trace a causal chain: `python3 examples/03_trace_causal_chain.py`

See `docs/AURELIA_RESEARCH_START_HERE.md`.
```

**Verification:**

```bash
PYTHONPATH=. pytest tests/ -q
```

**Commit:**

```bash
git add README.md
git commit -m "docs: add Aurelia research examples to README"
```

---

## Workstream G — Optional but high-value visual/research artifact

### Task G1: Generate one static research figure from real data

**Objective:** Add a simple plot or SVG showing the density-diversification result, not as social art but as a research artifact.

**Files:**
- Create: `scripts/plot_density_diversification.py`
- Create: `docs/reports/figures/density-diversification.svg`
- Create: `tests/test_density_plot.py`

**Test:**

- Script exposes `compute_population_cv_summary()`.
- SVG output contains labels for 100y baseline and density run.

**Implementation:**

Use Python stdlib SVG generation to avoid new dependencies.

**Verification:**

```bash
PYTHONPATH=. pytest tests/test_density_plot.py -q
PYTHONPATH=. python3 scripts/plot_density_diversification.py --output docs/reports/figures/density-diversification.svg
```

**Commit:**

```bash
git add scripts/plot_density_diversification.py tests/test_density_plot.py docs/reports/figures/density-diversification.svg
git commit -m "docs: add density diversification research figure"
```

---

## Workstream H — Final phase report

### Task H1: Write Phase 12 closure report

**Objective:** Summarize what changed and what remains before new long-run production.

**Files:**
- Create: `docs/reports/phase12-gap-closure-report.md`
- Modify: `CHANGELOG.md`

**Report sections:**

- What was lacking
- What was added
- Wiki/canon resolution
- Dataset UX resolution
- Simulation gate resolution
- Public surface reconciliation
- Remaining hard blockers
- Recommended next run matrix

**Recommended next run matrix:**

- 20 seed sweep × 25 years for calibration.
- 5 seed sweep × 100 years after gates pass.
- 1 or 2 200-year production histories only after quality gates stop warning on faction/depopulation pathologies.
- Counterfactual branches only when divergence gate reports meaningful deltas.

**Verification:**

```bash
PYTHONPATH=. pytest tests/ -q
```

**Commit:**

```bash
git add docs/reports/phase12-gap-closure-report.md CHANGELOG.md
git commit -m "docs: add Phase 12 gap-closure report"
```

---

## Execution order

Use this exact order:

1. A1 — concept map
2. A2 — rendered guide
3. B1 — coherence audit
4. B2 — wiki sync checklist
5. C1 — dataset loader helper
6. C2 — dataset loading example
7. C3 — density reproduction example
8. C4 — causal chain example
9. C5 — research start-here guide
10. D1 — harden run quality gates
11. D2 — metadata propagation
12. D3 — counterfactual divergence gates
13. E1 — public surface reconciler
14. E2 — Cloudflare limitation docs
15. F1 — HF README renderer links
16. F2 — README examples section
17. G1 — density research figure
18. H1 — Phase 12 closure report

Rationale: documentation bridge first, examples second, scoring/metadata third, public reconciliation fourth. Do not run new long histories until D1 and D2 are done.

---

## Commit discipline

Commit after every task. Do not batch across workstreams.

Commit prefixes:

- `docs:` for guides/audits/reports
- `examples:` for runnable examples
- `feat:` for scripts and quality gates
- `test:` only when tests are added without product code, which should be rare

Before every commit:

```bash
PYTHONPATH=. pytest tests/ -q
```

If the suite is too slow during tight cycles, run the targeted test first, then the full suite before commit.

---

## Risks and mitigations

### Risk: Overcorrecting the wiki and destroying lore

Mitigation: Do not delete deep lore. Add supersession markers and public-canon overlays. Lore can remain as historical/internal canon even when public simulation claims are narrower.

### Risk: Turning examples into brittle network tests

Mitigation: All tests must run offline against local fixtures or `/tmp/hf-export` if present. Network access belongs in manual verification, not pytest.

### Risk: Quality gates become too punitive

Mitigation: Use warnings plus score caps, not hard failures, for ambiguous simulation outcomes. Hard failures only for missing artifacts or impossible metadata.

### Risk: Cloudflare cap blocks public reconciliation

Mitigation: Treat Cloudflare as a partial public observability plane until D1 is upgraded or split. HF/local exports remain source of truth.

### Risk: More planning instead of action

Mitigation: Each task is 2-5 minutes of focused work with exact files and commands. Execute in order and commit immediately.

---

## What not to do yet

Do not start with:

- another 100y/200y run
- more lore pages
- more social posts
- a new visual campaign
- a Cloudflare re-upload loop against the D1 cap
- a new narrative prose layer

Those are downstream. First make the existing system legible and honest.

---

## Definition of done

This plan is done when a new reader can answer these questions without asking us:

1. What is Aurelia now?
2. Which old wiki claims are stale?
3. Which concepts are simulated vs lore-only?
4. Which code simulates each concept?
5. Which table stores it?
6. Which HF dataset exposes it?
7. Which report or example proves it?
8. Which public surfaces are complete vs partial?
9. Which simulation pathologies are currently known?
10. What must pass before the next production run?

When those are true, Aurelia stops feeling like separate artifacts and starts feeling like a research system.
