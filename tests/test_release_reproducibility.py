"""Phase T18: Tests for Reproducibility Infrastructure and Release Manifest.

Verifies:
1. Manifest and metadata files exist and have valid structure.
2. Privacy classification is NO_VIEWER_LEVEL_DATA.
3. Methodology strictly uses interaction_time (no video published date fallback, no false 100 comments ceiling).
4. Data dictionary, provenance map, and environment dependencies exist and validate.
5. Release validation script passes cleanly.
6. A second deterministic rebuild with identical inputs produces identical content hashes.
7. Volatile timestamps are separated from deterministic content hashes.
"""
import json
import subprocess
from pathlib import Path
import pytest

from scripts.build_dataset_release import (
    build_manifest,
    compute_deterministic_manifest_hash,
    RELEASE_DIR,
    MANIFEST_JSON,
    DATA_DICTIONARY_JSON,
    PROVENANCE_MAP_JSON,
    DEPENDENCIES_JSON,
    RELEASE_NOTES_MD
)
from scripts.validate_dataset_release import validate_release

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_manifest_and_release_artifacts_exist():
    """Verify all 5 release package artifacts exist on disk."""
    assert MANIFEST_JSON.exists(), "dataset_manifest.json missing"
    assert DATA_DICTIONARY_JSON.exists(), "data_dictionary.json missing"
    assert PROVENANCE_MAP_JSON.exists(), "provenance_map.json missing"
    assert DEPENDENCIES_JSON.exists(), "environment_dependencies.json missing"
    assert RELEASE_NOTES_MD.exists(), "dataset_release_notes.md missing"


def test_privacy_classification_no_viewer_level_data():
    """Verify privacy metadata does NOT claim macro only and strictly enforces NO_VIEWER_LEVEL_DATA."""
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    assert manifest["manifest_metadata"]["privacy_level"] == "NO_VIEWER_LEVEL_DATA"
    assert manifest["privacy_and_data_classification"]["privacy_level"] == "NO_VIEWER_LEVEL_DATA"
    assert "zero" in manifest["privacy_and_data_classification"]["viewer_level_rows"].lower()


def test_methodology_interaction_time_and_no_api_ceiling():
    """Verify methodology specifies interaction_time-only slicing and removes false API ceiling."""
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    meth = manifest["methodology"]

    # Strict interaction_time slicing
    assert "interaction_time" in meth["temporal_slicing"]
    assert "NEVER" in meth["temporal_slicing"]

    # No false "100 comments API ceiling" wording
    for lim in meth["limitations"]:
        assert "100 comments API ceiling" not in lim
        assert "100 comments per standard fetch" not in lim

    assert "comment_volume_characterization" in meth
    assert "T6" in meth["comment_volume_characterization"]


def test_provenance_map_and_dependencies():
    """Verify provenance map and environment dependencies capture."""
    prov = json.loads(PROVENANCE_MAP_JSON.read_text(encoding="utf-8"))
    assert "provenance_hierarchy" in prov
    assert "t16_incremental" in prov["provenance_hierarchy"]
    assert "t6_deep" in prov["provenance_hierarchy"]
    assert "lineage_dag" in prov

    deps = json.loads(DEPENDENCIES_JSON.read_text(encoding="utf-8"))
    assert "python_runtime" in deps
    assert "core_libraries" in deps
    assert "duckdb" in deps["core_libraries"]
    assert "pandas" in deps["core_libraries"]
    assert "pyarrow" in deps["core_libraries"]
    assert "networkx" in deps["core_libraries"]


def test_release_validation_script_passes():
    """Verify release validation script passes cleanly with exit code 0."""
    assert validate_release() is True


def test_deterministic_rebuild_identical_outputs():
    """Verify a second deterministic rebuild with identical inputs produces identical content hashes."""
    m1 = build_manifest(volatile_ts="2026-09-08T12:00:00Z")
    m2 = build_manifest(volatile_ts="2026-09-08T15:30:00Z")

    h1 = m1["manifest_metadata"]["deterministic_content_hash"]
    h2 = m2["manifest_metadata"]["deterministic_content_hash"]

    # Even though timestamps differ, deterministic content hashes MUST be identical!
    assert h1 == h2, f"Deterministic hash changed across runs: {h1} != {h2}"
    assert m1["manifest_metadata"]["total_artifacts"] == m2["manifest_metadata"]["total_artifacts"]
    assert m1["manifest_metadata"]["total_bytes"] == m2["manifest_metadata"]["total_bytes"]
