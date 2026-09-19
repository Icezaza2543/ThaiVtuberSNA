"""Task 10 gates for migrating collection/control-plane registry consumers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from config.settings import CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog
from core.registry import RegistryManager

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs" / "evidence" / "creator-registry-review-2026-09-19" / "trusted_baseline_1370.json"
FIXTURE = ROOT / "tests" / "fixtures" / "creator_registry" / "baseline.json"

COLLECTION_MODULES = [
    ROOT / "core" / "registry.py",
    ROOT / "collector" / "thai_vtuber_registry_builder.py",
    ROOT / "collector" / "balanced_video_collector.py",
    ROOT / "collector" / "video_catalog_builder.py",
    ROOT / "scripts" / "run_batch_network_350.py",
    ROOT / "scripts" / "run_hybrid_crawler_30.py",
]

ANALYSIS_MODULES = [
    ROOT / "scripts" / "audit_creator_identity_mapping.py",
    ROOT / "scripts" / "audit_research_v2_consistency.py",
    ROOT / "scripts" / "audit_sheets_privacy.py",
    ROOT / "scripts" / "build_collab_registries.py",
    ROOT / "scripts" / "build_creator_ecosystem_data.py",
    ROOT / "scripts" / "build_creator_lifecycle_evidence.py",
    ROOT / "scripts" / "build_discovery_candidates_new.py",
    ROOT / "scripts" / "build_discovery_universe.py",
    ROOT / "scripts" / "build_historical_lifecycle.py",
    ROOT / "scripts" / "build_research_v2_data.py",
    ROOT / "scripts" / "build_web_data.py",
    ROOT / "scripts" / "compact_campaign_review.py",
    ROOT / "scripts" / "create_target_manifest.py",
    ROOT / "scripts" / "update_web_with_real_data.py",
]
CONSUMER_MODULES = COLLECTION_MODULES + ANALYSIS_MODULES
LEGACY_NAMES = {
    "thai_vtuber_registry.json",
    "thai_vtuber_registry.csv",
    "registry_vtubers.csv",
    "master_creators.json",
}


def test_collection_modules_do_not_reference_legacy_registry_names():
    for path in CONSUMER_MODULES:
        source = path.read_text(encoding="utf-8")
        assert not any(name in source for name in LEGACY_NAMES), path


def test_catalog_legacy_rows_preserve_baseline_shape_and_membership():
    rows = CreatorCatalog.from_path(CREATOR_REGISTRY_PATH).youtube_rows()
    original = json.loads(BASELINE.read_text(encoding="utf-8"))
    original_ids = {row["channel_id"] for row in original}
    exported = {row["channel_id"] for row in rows}
    assert original_ids <= exported
    assert len(original_ids) == 1370
    for field in (
        "channel_id",
        "name",
        "handle",
        "agency",
        "activity_status",
        "vtuber_status",
        "enabled",
    ):
        assert field in rows[0]


def _local_config(path):
    return {
        "credentials_path": str(path.parent / "missing-credentials.json"),
        "spreadsheet_id": "",
        "sheet_vtubers": "VTUBERS",
        "sheet_system": "SYSTEM",
        "sheet_network": "NETWORK_RESULT",
        "creator_registry_path": path,
    }


def test_registry_manager_local_fallback_reads_creator_catalog():
    manager = RegistryManager(_local_config(FIXTURE))
    rows = manager.load_vtubers()
    assert len(rows) == 1
    assert rows[0]["channel_id"] == "UCAAAAAAAAAAAAAAAAAAAAAA"
    assert rows[0]["vtuber_status"] == "CONFIRMED"
    assert manager.get_enabled_vtubers()[0]["channel_id"] == rows[0]["channel_id"]


def test_registry_manager_local_creator_mutation_is_forbidden():
    manager = RegistryManager(_local_config(FIXTURE))
    original = FIXTURE.read_bytes()
    with pytest.raises(RuntimeError, match="read-only"):
        manager.save_vtubers(manager.load_vtubers())
    assert FIXTURE.read_bytes() == original


def test_phase1_builder_is_intake_only():
    source = (ROOT / "collector" / "thai_vtuber_registry_builder.py").read_text(encoding="utf-8")
    assert "phase1_creator_candidates.json" in source
    assert '"review_status": "unreviewed"' in source
    assert "CREATOR_REGISTRY_PATH" not in source
