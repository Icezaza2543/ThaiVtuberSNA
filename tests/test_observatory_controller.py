"""Phase T20: Tests for Continuous Thai VTuber Ecosystem Observatory Controller.

Verifies:
1. Controller status inspection (active version, baseline health, coordinates health, data freshness).
2. Automated quality gates validation (all 5 gates pass on clean repo).
3. Stale data detection (freshness within threshold, alert when beyond threshold).
4. Dry-run ingestion (simulates ingestion without mutating disk state or snapshots).
5. End-to-end synthetic batch update in sandbox (canonical overlay, snapshot mutation, quality gate, version bump).
6. Protected historical baseline isolation (pre-2026 slices remain byte-identical).
7. Future-year update triggers minor version promotion (v1.0.0 -> v1.1.0).
8. Fail-safe abort on quality gate failure (uncommitted batch rolled back, version not promoted).
9. Rollback mechanism (reverts to previous version and purges incremental batch file).
"""
import copy
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
import pandas as pd

from scripts.observatory_controller import (
    ObservatoryController,
    compute_historical_baseline_hash,
    compute_coordinates_block_hash,
    EXPECTED_COORDINATES_HASH,
    EXPECTED_HISTORICAL_BASELINE_HASH,
    EXPECTED_HMAC_KEY_FINGERPRINT
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def sandbox_observatory(tmp_path, synthetic_pipeline_data):
    """Sets up an isolated sandbox environment with snapshots, state, and web files."""
    sandbox_data = tmp_path / "data" / "temporal"
    sandbox_snaps = sandbox_data / "snapshots"
    sandbox_state = sandbox_data / "state"
    sandbox_inc = sandbox_data / "incremental"
    sandbox_obs = sandbox_data / "observatory"
    sandbox_web = tmp_path / "web"

    sandbox_snaps.mkdir(parents=True)
    sandbox_state.mkdir(parents=True)
    sandbox_inc.mkdir(parents=True)
    sandbox_obs.mkdir(parents=True)
    sandbox_web.mkdir(parents=True)

    # Copy real snapshots to sandbox
    real_snaps = REPO_ROOT / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
    assert real_snaps.exists()
    shutil.copy2(real_snaps, sandbox_snaps / "network_snapshots.parquet")

    # Copy web/app.js to sandbox
    real_web_app = REPO_ROOT / "web" / "app.js"
    assert real_web_app.exists()
    shutil.copy2(real_web_app, sandbox_web / "app.js")

    return synthetic_pipeline_data(tmp_path)


@pytest.fixture(autouse=True)
def offline_observatory_key(monkeypatch):
    import scripts.observatory_controller as module
    from core.hasher import compute_key_fingerprint
    key=b'offline-observatory-check-key'
    monkeypatch.setattr(module, 'load_persistent_secret_key', lambda: key)
    monkeypatch.setattr(module, 'EXPECTED_HMAC_KEY_FINGERPRINT', 'sha256_'+compute_key_fingerprint(key))


def test_01_controller_status_healthy():
    """1. Status returns active release version, healthy baseline, and coordinates match."""
    ctrl = ObservatoryController(base_dir=REPO_ROOT)
    st = ctrl.status()

    assert st["observatory_status"] == "ONLINE"
    assert st["active_dataset_version"] == "v1.0.0"
    assert st["historical_baseline_health"]["status"] == "HEALTHY"
    assert st["historical_baseline_health"]["current_hash"] == EXPECTED_HISTORICAL_BASELINE_HASH
    assert st["visualizer_coordinates_health"]["status"] == "HEALTHY"
    assert st["visualizer_coordinates_health"]["current_hash"] == EXPECTED_COORDINATES_HASH
    assert "data_freshness" in st


def test_02_controller_quality_gates_pass():
    """2. All 5 automated quality gates pass cleanly on the repository."""
    ctrl = ObservatoryController(base_dir=REPO_ROOT)
    res = ctrl.validate_quality_gates()

    assert res["all_passed"] is True, f"Gates failed: {res['gates']}"
    gates = res["gates"]
    assert gates["visualizer_coordinates"]["status"] == "PASS"
    assert gates["historical_baseline_isolation"]["status"] == "PASS"
    assert gates["hmac_key_continuity"]["status"] == "PASS"
    assert gates["dataset_release_validation"]["status"] == "PASS"
    assert gates["privacy_audit"]["status"] == "PASS"


def test_03_stale_data_detection():
    """3. Detects fresh data vs stale data threshold alerting."""
    ctrl = ObservatoryController(base_dir=REPO_ROOT, stale_threshold_days=30)

    # Fresh timestamp (1 day ago)
    fresh_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    fresh_check = ctrl.check_stale_data(latest_time_str=fresh_time)
    assert fresh_check["status"] == "FRESH"
    assert fresh_check["is_stale"] is False

    # Stale timestamp (45 days ago)
    stale_time = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    stale_check = ctrl.check_stale_data(latest_time_str=stale_time)
    assert stale_check["status"] == "STALE_ALERT"
    assert stale_check["is_stale"] is True
    assert "DATA_STALE_ALERT" in stale_check["details"]


def test_04_dry_run_zero_mutation(sandbox_observatory):
    """4. Dry-run simulates batch update without modifying snapshots or creating files."""
    snaps_file = sandbox_observatory / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
    snaps_hash_before = compute_historical_baseline_hash(snaps_file)

    ctrl = ObservatoryController(base_dir=sandbox_observatory)
    events = [
        {
            "author_id": "author_dryrun_test_viewer",
            "vtuber_channel_id": "UCpGtwNmbOtgmcKIY81MIX_w",
            "video_id": "vid_dryrun_99",
            "interaction_time": "2026-07-15T12:00:00Z"
        }
    ]

    res = ctrl.dry_run("batch_dryrun_001", events)
    assert res["status"] == "DRY_RUN"
    assert res["records_inserted"] == 1
    assert res["affected_years"] == [2026]

    # Check snapshots file on disk was not modified
    snaps_hash_after = compute_historical_baseline_hash(snaps_file)
    assert snaps_hash_before == snaps_hash_after

    # Check incremental dir contains no batch parquet
    inc_files = list((sandbox_observatory / "data" / "temporal" / "incremental").glob("*.parquet"))
    assert len(inc_files) == 0


def test_05_e2e_synthetic_batch_update_and_baseline_isolation(sandbox_observatory):
    """5. Ingests synthetic batch, updates 2026 edge, enforces isolation, bumps patch version."""
    snaps_file = sandbox_observatory / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
    df_before = pd.read_parquet(snaps_file)

    chan_a = min("UCpGtwNmbOtgmcKIY81MIX_w", "UCGBkYTR4tMKS38TQHGWWLjg")
    chan_b = max("UCpGtwNmbOtgmcKIY81MIX_w", "UCGBkYTR4tMKS38TQHGWWLjg")

    m_2026_before = (df_before["window_type"] == "yearly") & (df_before["window_start"].str.startswith("2026"))
    edge_before = df_before[m_2026_before & (df_before["vtuber_a"] == chan_a) & (df_before["vtuber_b"] == chan_b)]
    shared_before = int(edge_before["shared_any"].iloc[0])

    hist_hash_before = compute_historical_baseline_hash(snaps_file)

    ctrl = ObservatoryController(base_dir=sandbox_observatory)
    events = [
        {
            "author_id": "author_e2e_obs_viewer_1",
            "vtuber_channel_id": chan_a,
            "video_id": "vid_e2e_a",
            "interaction_time": "2026-08-10T14:00:00Z"
        },
        {
            "author_id": "author_e2e_obs_viewer_1",
            "vtuber_channel_id": chan_b,
            "video_id": "vid_e2e_b",
            "interaction_time": "2026-08-10T14:05:00Z"
        }
    ]

    res = ctrl.update("batch_obs_e2e_01", events, skip_downstream=True, auto_publish=True)
    assert res["status"] == "SUCCESS"
    assert res["version_before"] == "v1.0.0"
    assert res["version_after"] == "v1.0.1"
    assert res["records_inserted"] == 2

    # Verify edge incremented
    df_after = pd.read_parquet(snaps_file)
    m_2026_after = (df_after["window_type"] == "yearly") & (df_after["window_start"].str.startswith("2026"))
    edge_after = df_after[m_2026_after & (df_after["vtuber_a"] == chan_a) & (df_after["vtuber_b"] == chan_b)]
    shared_after = int(edge_after["shared_any"].iloc[0])
    assert shared_after == shared_before + 1

    # Verify pre-2026 historical slices remain strictly byte-identical
    hist_hash_after = compute_historical_baseline_hash(snaps_file)
    assert hist_hash_before == hist_hash_after

    # Verify state and ledger
    state = ctrl._load_state()
    assert state["active_dataset_version"] == "v1.0.1"
    assert state["total_runs"] == 1


def test_06_future_year_minor_version_bump(sandbox_observatory):
    """6. Future-year event (e.g. 2027) triggers semver minor bump (v1.0.0 -> v1.1.0)."""
    ctrl = ObservatoryController(base_dir=sandbox_observatory)
    events = [
        {
            "author_id": "author_future_2027",
            "vtuber_channel_id": "UCpGtwNmbOtgmcKIY81MIX_w",
            "video_id": "vid_2027_test",
            "interaction_time": "2027-02-14T10:00:00Z"
        }
    ]

    res = ctrl.update("batch_future_2027", events, skip_downstream=True, auto_publish=True)
    assert res["status"] == "SUCCESS"
    assert res["version_before"] == "v1.0.0"
    assert res["version_after"] == "v1.1.0"
    assert 2027 in res["affected_years"]


def test_07_fail_safe_on_quality_gate_violation(sandbox_observatory):
    """7. Corrupted baseline triggers fail-safe rollback, prevents version promotion."""
    ctrl = ObservatoryController(base_dir=sandbox_observatory)

    # Corrupt coordinates in web/app.js to simulate visualizer mutation
    web_app_js = sandbox_observatory / "web" / "app.js"
    web_app_js.write_text("// corrupted web app content", encoding="utf-8")

    events = [
        {
            "author_id": "author_corrupted_test",
            "vtuber_channel_id": "UCpGtwNmbOtgmcKIY81MIX_w",
            "video_id": "vid_fail_safe",
            "interaction_time": "2026-08-01T12:00:00Z"
        }
    ]

    with pytest.raises(RuntimeError, match="Quality gate failure"):
        ctrl.update("batch_fail_safe_test", events, skip_downstream=True, auto_publish=True)

    # State must not have been promoted
    state = ctrl._load_state()
    assert state["active_dataset_version"] == "v1.0.0"

    # Ledger records the failure
    ledger = ctrl._load_ledger()
    assert len(ledger["runs"]) == 1
    assert ledger["runs"][0]["status"] == "FAILED_QUALITY_GATE_ROLLED_BACK"


def test_08_rollback_mechanism(sandbox_observatory):
    """8. Rollback command successfully reverts version and cleans up batch file."""
    ctrl = ObservatoryController(base_dir=sandbox_observatory)
    events = [
        {
            "author_id": "author_rollback_test",
            "vtuber_channel_id": "UCpGtwNmbOtgmcKIY81MIX_w",
            "video_id": "vid_rollback_test",
            "interaction_time": "2026-08-01T12:00:00Z"
        }
    ]

    res = ctrl.update("batch_to_rollback", events, skip_downstream=True, auto_publish=True)
    assert res["version_after"] == "v1.0.1"

    batch_parquet = sandbox_observatory / "data" / "temporal" / "incremental" / "batch_batch_to_rollback.parquet"
    assert batch_parquet.exists()

    # Execute rollback
    rb_res = ctrl.rollback()
    assert rb_res["status"] == "ROLLED_BACK"
    assert rb_res["reverted_to_version"] == "v1.0.0"

    # Assert batch file purged and version reverted
    assert not batch_parquet.exists()
    state = ctrl._load_state()
    assert state["active_dataset_version"] == "v1.0.0"
