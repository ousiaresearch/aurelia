"""Tests for run metadata propagation across the run → export → Cloudflare chain.

The Phase 11 export layer and the Cloudflare run manifest must carry
real seed, ticks_per_year, density_diversification, engine version, and
git commit. A run with zeroed or missing metadata is pathological and
the quality gate in ``evaluate_run_quality.py`` will flag it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src_template"
sys.path.insert(0, str(SRC))


def load_src(name: str):
    spec = importlib.util.spec_from_file_location(name, SRC / f"{name}.py")
    assert spec and spec.loader
    # The src_template modules use both relative and absolute imports of
    # sibling modules. Make sure both forms can resolve.
    sys.path.insert(0, str(SRC))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# federation_orchestrator.run_causal_simulation must populate the manifest
# ---------------------------------------------------------------------------

def test_orchestrator_summary_includes_manifest_fields(tmp_path):
    orch = load_src("federation_orchestrator")
    summary = orch.run_causal_simulation(
        output_dir=tmp_path,
        years=1,
        npc_count=10,
        ticks_per_year=4,
        seed=4242,
        max_interactions=10,
    )
    for key in ("run_id", "seed", "years", "ticks", "ticks_per_year",
                "density_diversification", "engine_version", "git_commit", "created_at"):
        assert key in summary, f"missing manifest key: {key}"
    assert summary["seed"] == 4242
    assert summary["ticks_per_year"] == 4
    assert summary["years"] == 1
    assert summary["ticks"] == 4
    assert summary["density_diversification"] == 0.0
    assert summary["engine_version"], "engine_version should be non-empty"
    assert summary["git_commit"], "git_commit should be non-empty (HEAD or short SHA)"
    assert summary["run_id"], "run_id should be non-empty"
    assert summary["created_at"], "created_at should be non-empty"


def test_orchestrator_persists_manifest_to_causal_summary_json(tmp_path):
    orch = load_src("federation_orchestrator")
    orch.run_causal_simulation(
        output_dir=tmp_path,
        years=1,
        npc_count=10,
        ticks_per_year=4,
        seed=1234,
        max_interactions=10,
    )
    on_disk = json.loads((tmp_path / "causal_summary.json").read_text())
    for key in ("run_id", "seed", "ticks_per_year", "engine_version", "git_commit"):
        assert key in on_disk, f"causal_summary.json missing manifest key: {key}"
    assert on_disk["seed"] == 1234
    assert on_disk["ticks_per_year"] == 4


def test_orchestrator_density_diversification_propagates_to_summary(tmp_path):
    orch = load_src("federation_orchestrator")
    summary = orch.run_causal_simulation(
        output_dir=tmp_path,
        years=1,
        npc_count=10,
        ticks_per_year=4,
        seed=1,
        max_interactions=10,
        density_diversification=0.7,
    )
    assert summary["density_diversification"] == 0.7
    on_disk = json.loads((tmp_path / "causal_summary.json").read_text())
    assert on_disk["density_diversification"] == 0.7


# ---------------------------------------------------------------------------
# Helpers exposed for the manifest
# ---------------------------------------------------------------------------

def test_orchestrator_exposes_engine_version_helper():
    orch = load_src("federation_orchestrator")
    assert hasattr(orch, "ENGINE_VERSION")
    assert isinstance(orch.ENGINE_VERSION, str) and orch.ENGINE_VERSION
    assert hasattr(orch, "GIT_COMMIT")
    assert isinstance(orch.GIT_COMMIT, str) and orch.GIT_COMMIT
    assert hasattr(orch, "make_run_id")
    rid = orch.make_run_id("phase11-test", 1, 4, 1234)
    assert rid.startswith("phase11-test")
    assert "seed1234" in rid
    assert "tpy4" in rid
