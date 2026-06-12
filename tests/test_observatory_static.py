from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_observatory_links_current_phase12_truth_surface():
    html = (ROOT / "docs" / "observatory" / "index.html").read_text()

    assert "0.1.6 post-fix engine" in html
    assert "phase12-seed-sweep-report.md" in html
    assert "AURELIA_COUNTERFACTUALS.md" in html
    assert "PROJECT_STATUS_2026-06-12.md" in html
    assert "D1 caveat" in html or "Cloudflare is the public observability plane" in html
