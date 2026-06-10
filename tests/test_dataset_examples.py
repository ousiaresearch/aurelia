"""Tests for the dataset research UX examples and the loader helper.

All tests run offline against local fixtures or /tmp/hf-export if present.
No network access belongs in pytest.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_example(name: str):
    path = ROOT / "examples" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"missing example module: {path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# C1 — aurelia_dataset_loader
# ---------------------------------------------------------------------------

def test_dataset_loader_has_expected_dataset_names():
    mod = load_example("aurelia_dataset_loader")
    assert set(mod.DATASETS) == {
        "aurelia-causal-events",
        "aurelia-civilization-metrics",
        "aurelia-federation-causal",
        "aurelia-npc-population",
    }


def test_dataset_loader_has_hf_org_constant():
    mod = load_example("aurelia_dataset_loader")
    assert mod.HF_ORG == "OusiaResearch"


def test_dataset_loader_discovers_local_export_paths(tmp_path):
    export_root = _make_fake_export(tmp_path)
    mod = load_example("aurelia_dataset_loader")
    paths = mod.discover_local_parquet_files(export_root)
    assert isinstance(paths, dict)
    assert "aurelia-causal-events" in paths
    assert paths["aurelia-causal-events"]
    # Every path must exist
    for p in paths["aurelia-causal-events"]:
        assert p.exists()


def test_dataset_loader_returns_empty_dict_for_missing_root(tmp_path):
    mod = load_example("aurelia_dataset_loader")
    paths = mod.discover_local_parquet_files(tmp_path / "does-not-exist")
    assert paths == {}


def test_dataset_loader_loads_local_table(tmp_path):
    export_root = _make_fake_export(tmp_path)
    mod = load_example("aurelia_dataset_loader")
    table = mod.load_local_table("aurelia-npc-population", export_root)
    assert isinstance(table, pa.Table)
    assert len(table) > 0
    assert len(table.column_names) > 0


def test_dataset_loader_print_summary_runs(tmp_path, capsys):
    export_root = _make_fake_export(tmp_path)
    mod = load_example("aurelia_dataset_loader")
    mod.print_summary(export_root)
    out = capsys.readouterr().out
    assert "aurelia-causal-events" in out
    assert "rows" in out.lower()


# ---------------------------------------------------------------------------
# C2 — 01_load_aurelia_hf_datasets
# ---------------------------------------------------------------------------

def test_load_hf_datasets_example_has_main():
    mod = load_example("01_load_aurelia_hf_datasets")
    assert hasattr(mod, "main")
    assert callable(mod.main)


def test_load_hf_datasets_main_runs_against_local_export(tmp_path, capsys):
    export_root = _make_fake_export(tmp_path)
    mod = load_example("01_load_aurelia_hf_datasets")
    rc = mod.main(["--export-root", str(export_root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "aurelia-causal-events" in out
    assert "aurelia-npc-population" in out


# ---------------------------------------------------------------------------
# C3 — 02_reproduce_density_diversification
# ---------------------------------------------------------------------------

def test_density_diversification_example_exposes_cv_function():
    mod = load_example("02_reproduce_density_diversification")
    # Plan-mandated assertions (baseline-vs-density active NPC counts)
    assert round(mod.coefficient_of_variation([171, 58, 63, 29, 49]), 3) == 0.674
    assert round(mod.coefficient_of_variation([67, 67, 67, 67, 66]), 3) == 0.006


def test_density_diversification_reports_reduction_above_99_percent(tmp_path, capsys):
    export_root = _make_fake_export(tmp_path)
    mod = load_example("02_reproduce_density_diversification")
    rc = mod.main(["--export-root", str(export_root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "99" in out  # 99.1% or 99.0% reduction


# ---------------------------------------------------------------------------
# C4 — 03_trace_causal_chain
# ---------------------------------------------------------------------------

def test_trace_causal_chain_builds_parent_child_index():
    mod = load_example("03_trace_causal_chain")
    edges = [
        {"parent_event_id": "a", "child_event_id": "b", "relation": "caused"},
        {"parent_event_id": "b", "child_event_id": "c", "relation": "amplified"},
    ]
    index = mod.build_parent_index(edges)
    assert index["c"][0]["parent_event_id"] == "b"
    assert index["b"][0]["parent_event_id"] == "a"


def test_trace_causal_chain_walks_to_root():
    mod = load_example("03_trace_causal_chain")
    edges = [
        {"parent_event_id": "a", "child_event_id": "b", "relation": "caused"},
        {"parent_event_id": "b", "child_event_id": "c", "relation": "amplified"},
        {"parent_event_id": "c", "child_event_id": "d", "relation": "triggered"},
    ]
    index = mod.build_parent_index(edges)
    chain = mod.walk_ancestors("d", index, depth=3)
    seen = {n["event_id"] for n in chain}
    assert {"a", "b", "c"} <= seen


def test_trace_causal_chain_main_runs_against_local_export(tmp_path, capsys):
    export_root = _make_fake_export(tmp_path)
    mod = load_example("03_trace_causal_chain")
    rc = mod.main(["--export-root", str(export_root)])
    out = capsys.readouterr().out
    assert rc == 0
    # Either we found a chain, or we explicitly printed a fallback note.
    assert "causal" in out.lower() or "no edges" in out.lower()


# ---------------------------------------------------------------------------
# C5 — start-here pages and README links
# ---------------------------------------------------------------------------

def test_research_start_here_mentions_core_examples():
    text = (ROOT / "docs" / "AURELIA_RESEARCH_START_HERE.md").read_text()
    assert "01_load_aurelia_hf_datasets" in text
    assert "02_reproduce_density_diversification" in text
    assert "03_trace_causal_chain" in text
    assert "AURELIA_CANON_AND_DATA_GUIDE" in text


def test_lore_readers_start_here_mentions_world_primer_and_bridge():
    text = (ROOT / "docs" / "AURELIA_LORE_READERS_START_HERE.md").read_text()
    assert "AURELIA_CANON_AND_DATA_GUIDE" in text
    assert "AURELIA_COHERENCE_AUDIT" in text
    # Lore readers should be pointed at the wiki, not at the dataset CLI
    assert "Desktop/Aurelia" in text or "wiki" in text.lower()


def test_readme_links_both_start_here_pages():
    text = (ROOT / "README.md").read_text()
    assert "AURELIA_RESEARCH_START_HERE" in text
    assert "AURELIA_LORE_READERS_START_HERE" in text


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

def _make_fake_export(root: Path) -> Path:
    """Build a minimal /tmp/hf-export-shaped fixture with the four datasets.

    Each dataset gets a small population-causal style table and a configs.json
    pointing at the parquet files. This is enough for the loader to discover
    paths and for examples to compute aggregates.
    """
    base = root / "export"
    for ds in (
        "aurelia-causal-events",
        "aurelia-civilization-metrics",
        "aurelia-federation-causal",
        "aurelia-npc-population",
    ):
        ds_dir = base / ds
        data_dir = ds_dir / "data" / "phase11-100y"
        data_dir.mkdir(parents=True, exist_ok=True)
        if ds == "aurelia-npc-population":
            # Per-world active-NPC counts engineered to mirror the headline
            # baseline-vs-density result (filter by final_state == "active").
            tables = {
                "solara": pa.table({"npc_id": [f"solara_{i}" for i in range(171)], "final_state": ["active"] * 171}),
                "arkos": pa.table({"npc_id": [f"arkos_{i}" for i in range(58)], "final_state": ["active"] * 58}),
                "mirithane": pa.table({"npc_id": [f"mirithane_{i}" for i in range(63)], "final_state": ["active"] * 63}),
                "valdris": pa.table({"npc_id": [f"valdris_{i}" for i in range(29)], "final_state": ["active"] * 29}),
                "verge": pa.table({"npc_id": [f"verge_{i}" for i in range(49)], "final_state": ["active"] * 49}),
            }
        elif ds == "aurelia-causal-events":
            tables = {
                w: pa.table(
                    {
                        "event_id": [f"e{i}_{w}" for i in range(4)],
                        "parent_event_id": [None, "e0_a", "e1_a", "e2_b"],
                        "world": [w] * 4,
                        "tick": [i * 10 for i in range(4)],
                    }
                )
                for w in ("solara", "arkos", "mirithane", "valdris", "verge")
            }
        elif ds == "aurelia-federation-causal":
            tables = {
                w: pa.table(
                    {
                        "parent_event_id": ["e0", "e1", "e2", "e3"],
                        "child_event_id": ["e1", "e2", "e3", "e4"],
                        "relation": ["caused", "amplified", "triggered", "caused"],
                    }
                )
                for w in ("solara", "arkos", "mirithane", "valdris", "verge")
            }
        else:  # civilization-metrics
            tables = {
                w: pa.table(
                    {
                        "world": [w] * 3,
                        "year": [0, 50, 100],
                        "population": [100, 110, 120],
                    }
                )
                for w in ("solara", "arkos", "mirithane", "valdris", "verge")
            }
        files: list[str] = []
        for world, table in tables.items():
            world_dir = data_dir / world
            world_dir.mkdir(parents=True, exist_ok=True)
            pq.write_table(table, world_dir / "train.parquet")
            files.append(f"data/phase11-100y/{world}/train.parquet")
        (ds_dir / "configs.json").write_text(
            '{"data": {"phase11-100y": ' + _json_array(files) + "}}"
        )
    return base


def _json_array(items: list[str]) -> str:
    import json
    return json.dumps(items)
