from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_surface_tab_is_default_and_loads_clean_dataset():
    html=(ROOT/"web/index.html").read_text(encoding="utf-8")
    js=(ROOT/"web/research.js").read_text(encoding="utf-8")
    assert 'data-tab="surface"' in html
    assert 'id="panel-surface"' in html
    assert "research/surface_analytics_v1.json" in js
    assert "activate('surface')" in js
    assert "STRICT_VIRTUAL" in html

def test_surface_ui_does_not_claim_clean_audience_count():
    html=(ROOT/"web/index.html").read_text(encoding="utf-8")
    assert "ยังไม่คำนวณ clean audience totals" in html
