"""Tests for the density-diversification research figure generator.

The figure is a static SVG, generated from PyArrow + stdlib, that
researchers can embed in papers or notebooks. It must work offline
against the local Parquet export at /tmp/hf-export.
"""

from __future__ import annotations

import importlib.util
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYS = ROOT / "scripts"
sys_path_inserted = False

import sys  # noqa: E402


def load_script(name: str):
    path = SYS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_compute_population_cv_summary_returns_baseline_and_density():
    mod = load_script("plot_density_diversification")
    summary = mod.compute_population_cv_summary({
        "phase11-100y": [171, 58, 63, 29, 49],
        "phase11-density-100y": [67, 67, 67, 67, 66],
    })
    assert "phase11-100y" in summary
    assert "phase11-density-100y" in summary
    assert abs(summary["phase11-100y"]["cv"] - 0.6739) < 0.01
    assert abs(summary["phase11-density-100y"]["cv"] - 0.006) < 0.01
    assert summary["phase11-100y"]["label"] == "100y baseline"
    assert summary["phase11-density-100y"]["label"] == "density 100y"


def test_compute_population_cv_summary_handles_empty_input():
    mod = load_script("plot_density_diversification")
    summary = mod.compute_population_cv_summary({})
    assert summary == {}


def test_svg_contains_required_labels(tmp_path):
    mod = load_script("plot_density_diversification")
    summary = mod.compute_population_cv_summary({
        "phase11-100y": [171, 58, 63, 29, 49],
        "phase11-density-100y": [67, 67, 67, 67, 66],
    })
    svg = mod.render_svg(summary, title="Aurelia density diversification")
    assert "<svg" in svg
    assert "100y baseline" in svg
    assert "density 100y" in svg
    assert "99.1" in svg or "99" in svg  # reduction % present
    out = tmp_path / "figure.svg"
    out.write_text(svg)
    assert out.stat().st_size > 1000


def test_main_writes_svg_file(tmp_path, monkeypatch):
    """End-to-end: load data from a stub and write the figure."""
    mod = load_script("plot_density_diversification")

    # Patch the data loader to use a fixture.
    def fake_load(run, root):
        return {"phase11-100y": [171, 58, 63, 29, 49],
                "phase11-density-100y": [67, 67, 67, 67, 66]}.get(run, [])

    monkeypatch.setattr(mod, "_load_active_population_per_world", fake_load)
    out = tmp_path / "fig.svg"
    rc = mod.main(["--output", str(out), "--no-pretty"])
    assert rc == 0
    assert out.exists()
    assert "100y baseline" in out.read_text()
    assert "density 100y" in out.read_text()
