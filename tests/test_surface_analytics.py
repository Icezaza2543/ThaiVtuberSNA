import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_surface_analytics_strict_cohort_invariants():
    data=json.loads((ROOT/"web/research/surface_analytics_v1.json").read_text(encoding="utf-8"))
    assert data["cohort"]["strict_virtual_channels"]==229
    assert data["content"]["catalog_channels"]==229
    assert data["content"]["catalog_videos"]==70243
    assert data["network"]["nodes"]==229
    assert data["audience"]["clean_unique_pseudonyms"] is None
    assert data["audience"]["clean_interactions"] is None

def test_surface_analytics_does_not_claim_reference_frame_is_clean_cohort():
    data=json.loads((ROOT/"web/research/surface_analytics_v1.json").read_text(encoding="utf-8"))
    assert data["cohort"]["raw_reference_channels"]==1370
    assert data["cohort"]["raw_reference_channels"]!=data["cohort"]["strict_virtual_channels"]
