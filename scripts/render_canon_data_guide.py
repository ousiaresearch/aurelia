#!/usr/bin/env python3
"""Render Aurelia's canon concept bridge into a Markdown guide.

This script intentionally does not edit the Desktop wiki. It turns the repo's
versioned concept map into a public guide that maps lore concepts to code,
SQLite tables, HuggingFace datasets, Cloudflare surfaces, and proof artifacts.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS_PATH = ROOT / "docs" / "data" / "aurelia_concepts.yaml"
OUTPUT_PATH = ROOT / "docs" / "AURELIA_CANON_AND_DATA_GUIDE.md"

STATUS_ORDER = {
    "simulated": 0,
    "partial": 1,
    "planned": 2,
    "lore_only": 3,
    "stale": 4,
    "archived": 5,
}

STATUS_MEANINGS = {
    "simulated": "Active in runtime code and represented in data artifacts.",
    "partial": "Present, but not yet fully bridged across lore, simulation, and data.",
    "planned": "Canonical direction, but not yet a sufficient runtime/data surface.",
    "lore_only": "Canon/lore exists, but no active simulation/data representation yet.",
    "stale": "Older claim that should not be treated as current public canon without review.",
    "archived": "Historical/internal material retained for context, not current public surface.",
}


def _load_concepts(path: Path = CONCEPTS_PATH) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, list):
        raise TypeError(f"{path} must contain a YAML list")
    return data


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "  - None"
    return "\n".join(f"  - `{item}`" for item in items)


def _plain_bullet_list(items: list[str]) -> str:
    if not items:
        return "  - None"
    return "\n".join(f"  - {item}" for item in items)


def _status_badge(status: str) -> str:
    return {
        "simulated": "SIMULATED",
        "partial": "PARTIAL",
        "planned": "PLANNED",
        "lore_only": "LORE ONLY",
        "stale": "STALE",
        "archived": "ARCHIVED",
    }.get(status, status.upper())


def _render_status_summary(concepts: list[dict[str, Any]]) -> str:
    counts = Counter(c["status"] for c in concepts)
    lines = ["## Status summary", ""]
    for status in sorted(counts, key=lambda s: STATUS_ORDER.get(s, 99)):
        lines.append(f"- **{_status_badge(status)}**: {counts[status]} — {STATUS_MEANINGS.get(status, '')}")
    return "\n".join(lines)


def _render_dataset_index(concepts: list[dict[str, Any]]) -> str:
    datasets: dict[str, list[str]] = defaultdict(list)
    for concept in concepts:
        for dataset in concept.get("hf_datasets", []):
            datasets[dataset].append(concept["id"])

    lines = ["## Dataset index", ""]
    if not datasets:
        lines.append("No HuggingFace dataset mappings yet.")
        return "\n".join(lines)

    for dataset in sorted(datasets):
        ids = ", ".join(f"`{cid}`" for cid in sorted(datasets[dataset]))
        lines.append(f"- `{dataset}`: {ids}")
    return "\n".join(lines)


def _render_code_index(concepts: list[dict[str, Any]]) -> str:
    paths: dict[str, list[str]] = defaultdict(list)
    for concept in concepts:
        for code_path in concept.get("code_paths", []):
            paths[code_path].append(concept["id"])

    lines = ["## Code index", ""]
    for path in sorted(paths):
        ids = ", ".join(f"`{cid}`" for cid in sorted(paths[path]))
        lines.append(f"- `{path}`: {ids}")
    return "\n".join(lines)


def _render_concept_index(concepts: list[dict[str, Any]]) -> str:
    lines = ["## Concept index", ""]
    for concept in sorted(concepts, key=lambda c: (STATUS_ORDER.get(c["status"], 99), c["id"])):
        status = _status_badge(concept["status"])
        lines.append(f"### `{concept['id']}` — {concept['name']} [{status}]")
        lines.append("")
        lines.append(concept["summary"])
        lines.append("")
        lines.append("**Wiki paths:**")
        lines.append(_bullet_list(concept.get("wiki_paths", [])))
        lines.append("")
        lines.append("**Runtime/code paths:**")
        lines.append(_bullet_list(concept.get("code_paths", [])))
        lines.append("")
        lines.append("**SQLite / storage tables:**")
        lines.append(_bullet_list(concept.get("sqlite_tables", [])))
        lines.append("")
        lines.append("**HuggingFace datasets:**")
        lines.append(_bullet_list(concept.get("hf_datasets", [])))
        lines.append("")
        lines.append("**Cloudflare/public surface:**")
        lines.append(_bullet_list(concept.get("cloudflare_surface", [])))
        lines.append("")
        lines.append("**Proof artifacts:**")
        lines.append(_bullet_list(concept.get("proof_artifacts", [])))
        notes = concept.get("notes", [])
        if notes:
            lines.append("")
            lines.append("**Notes:**")
            lines.append(_plain_bullet_list(notes))
        lines.append("")
    return "\n".join(lines).rstrip()


def render_guide(concepts: list[dict[str, Any]]) -> str:
    lines = [
        "# Aurelia Canon and Data Guide",
        "",
        "This is the canon bridge for Aurelia Phase 12. It maps each major concept across lore/wiki files, runtime code, SQLite tables, HuggingFace datasets, Cloudflare public surfaces, and proof artifacts.",
        "",
        "Do not treat this as wiki reconciliation. This guide records the bridge and flags stale/split concepts for review; it does not edit or supersede the Desktop wiki by itself.",
        "",
        "## How to read this guide",
        "",
        "- If a concept is **SIMULATED**, it has active runtime and data surfaces.",
        "- If a concept is **PARTIAL**, it exists but lacks a complete bridge across all layers.",
        "- If a concept is **PLANNED**, it is a desired canonical mechanic but still needs implementation/proof.",
        "- If a concept is **STALE** or **ARCHIVED**, review it before using it in public copy.",
        "",
        _render_status_summary(concepts),
        "",
        _render_dataset_index(concepts),
        "",
        _render_code_index(concepts),
        "",
        _render_concept_index(concepts),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    concepts = _load_concepts()
    OUTPUT_PATH.write_text(render_guide(concepts))
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
