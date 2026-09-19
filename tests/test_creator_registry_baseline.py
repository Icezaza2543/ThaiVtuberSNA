import hashlib
import json
from pathlib import Path


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
    assert baseline["trusted_youtube_channels"] == 1370
    assert baseline["trusted_unique_channel_ids"] == 1370
    assert baseline["files"]["data/temporal/catalog/target_manifest.csv"] == sha(
        ROOT / "data/temporal/catalog/target_manifest.csv"
    )
    assert baseline["files"]["data/thai_vtuber_registry.json"] == sha(snapshot_path)
    assert len(registry) == 1370
