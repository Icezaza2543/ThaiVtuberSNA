import json
from pathlib import Path
import subprocess

from config.settings import CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog


ROOT = Path(__file__).resolve().parents[1]


def git_blob_oid(ref, relative_path):
    return subprocess.check_output(
        ["git", "rev-parse", f"{ref}:{relative_path}"],
        cwd=ROOT,
        text=True,
    ).strip()


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

    # Protected files are compared as Git blobs rather than working-tree bytes.
    # Task 1 captured SHA-256 on Windows (CRLF), while CI runs on Linux (LF);
    # identical repository content must therefore be checked at the Git-object
    # boundary to avoid a platform-specific false positive.
    manifest = "data/temporal/catalog/target_manifest.csv"
    assert git_blob_oid(baseline["commit"], manifest) == git_blob_oid("HEAD", manifest)

    # The sealed trusted snapshot preserves the exact retired registry Git blob.
    retired_registry = next(
        path
        for path in baseline["files"]
        if path.startswith("data/") and path.endswith("_registry.json")
    )
    sealed_snapshot = (
        "docs/evidence/creator-registry-review-2026-09-19/"
        "trusted_baseline_1370.json"
    )
    assert git_blob_oid(baseline["commit"], retired_registry) == git_blob_oid(
        "HEAD", sealed_snapshot
    )

    assert len(registry) == 1370
    assert len(snapshot_ids) == 1370
    assert snapshot_ids <= catalog_ids
