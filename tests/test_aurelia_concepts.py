from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "docs" / "data" / "aurelia_concepts.yaml"
GUIDE = ROOT / "docs" / "AURELIA_CANON_AND_DATA_GUIDE.md"

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

REQUIRED_CONCEPT_IDS = {
    "world",
    "npc",
    "human",
    "thren",
    "vorn",
    "glim",
    "faction",
    "institution",
    "regime",
    "education",
    "urbanization",
    "disease_pressure",
    "resource_stock",
    "property_rights",
    "state_capacity_type",
    "repression_type",
    "conflict_type",
    "migration",
    "cultural_diffusion",
    "diplomacy",
    "cross_world_effect",
    "discovery",
    "great_person",
    "causal_event",
    "causal_edge",
    "counterfactual_branch",
    "density_diversification",
    "glim_anomaly",
    "single_landmass_old_canon",
    "ttrpg_assets_old_canon",
}


def load_concepts():
    return yaml.safe_load(CONCEPTS.read_text())


def test_concepts_file_exists_and_has_minimum_coverage():
    assert CONCEPTS.exists()
    data = load_concepts()
    assert isinstance(data, list)
    assert len(data) >= 25
    ids = {concept["id"] for concept in data}
    assert REQUIRED_CONCEPT_IDS <= ids


def test_each_concept_has_required_keys_and_valid_status():
    data = load_concepts()
    for concept in data:
        assert REQUIRED_KEYS <= set(concept), concept.get("id")
        assert concept["status"] in VALID_STATUS
        assert concept["id"]
        assert concept["name"]
        assert concept["summary"]
        for list_key in [
            "wiki_paths",
            "code_paths",
            "sqlite_tables",
            "hf_datasets",
            "cloudflare_surface",
            "proof_artifacts",
        ]:
            assert isinstance(concept[list_key], list), (concept["id"], list_key)


def test_simulated_concepts_have_code_and_data_paths():
    data = load_concepts()
    simulated = [c for c in data if c["status"] == "simulated"]
    assert len(simulated) >= 12
    for concept in simulated:
        assert concept["code_paths"], concept["id"]
        assert concept["sqlite_tables"], concept["id"]
        assert concept["hf_datasets"], concept["id"]


def test_stale_concepts_are_not_mapped_to_active_hf_datasets():
    data = load_concepts()
    stale = [c for c in data if c["status"] in {"stale", "archived"}]
    assert stale
    for concept in stale:
        assert concept["proof_artifacts"], concept["id"]
        assert not concept["hf_datasets"], concept["id"]


def test_rendered_canon_guide_exists_and_mentions_core_layers():
    assert GUIDE.exists()
    text = GUIDE.read_text()
    assert "# Aurelia Canon and Data Guide" in text
    assert "## Concept index" in text
    assert "## Status summary" in text
    assert "density_diversification" in text
    assert "OusiaResearch/aurelia-causal-events" in text
    assert "src_template/phase10_dynamics.py" in text
    assert "single_landmass_old_canon" in text
    assert "Do not treat this as wiki reconciliation" in text
