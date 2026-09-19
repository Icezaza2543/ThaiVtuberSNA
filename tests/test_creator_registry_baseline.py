import hashlib
import json
from pathlib import Path

from config.settings import CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pre_refactor_baseline_records_real_registry_and_protected_files():
    baseline = json.loads(
        (
            ROOT
            / "docs/evidence/creator-registry-review-2026-09-19/pre_refactor_baseline.json"
        ).read_text()
    )
    snapshot_path = (
        ROOT
        / "docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json"
    )
    registry = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot_ids = {row["channel_id"] for row in registry}
    catalog_ids = {
        row["platform_id"]
        for row in CreatorCatalog.from_path(CREATOR_REGISTRY_PATH).youtube_accounts()
        if row.get("platform_id")
    }

    assert baseline["trusted_youtube_channels"] == 1370
    assert baseline["trusted_unique_channel_ids"] == 1370
    assert baseline["files"]["data/temporal/catalog/target_manifest.csv"] == sha(
        ROOT / "data/temporal/catalog/target_manifest.csv"
    )
    # Historical path names remain sealed only inside the evidence manifest; the
    # trusted snapshot must retain the exact pre-refactor registry bytes.
    assert sha(snapshot_path) in set(baseline["files"].values())
    assert len(registry) == 1370
    assert len(snapshot_ids) == 1370
    assert snapshot_ids <= catalog_ids
