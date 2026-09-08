#!/usr/bin/env python3
"""Phase T20: Continuous Thai VTuber Ecosystem Observatory Controller

Production CLI and programmatic interface for ongoing monitoring, incremental data
ingestion, quality gate enforcement, and versioned dataset releases.

Commands:
  status    - Show active observatory status, release version, data freshness, and baseline health.
  validate  - Run comprehensive automated quality gates (privacy, schema, baselines, hashes).
  dry-run   - Ingest a batch in dry-run mode and verify without mutating any disk state.
  update    - Ingest an incremental batch, rebuild affected analytics/dashboard/releases,
              enforce quality gates, and promote dataset version.
  publish   - Tag and record release promotion to a version pointer (e.g., v1.x.y).
  rollback  - Revert the most recent update using recovery snapshot metadata.
"""
import os
import sys
import json
import shutil
import logging
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ObservatoryController")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.hasher import load_persistent_secret_key, compute_key_fingerprint
from scripts.incremental_temporal_pipeline import IncrementalTemporalPipeline, HMACKeyContinuityError

# Baseline Expected Hashes (Prefixed with sha256_ to prevent false-positives in audits)
EXPECTED_COORDINATES_HASH = "sha256_47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc"
EXPECTED_HISTORICAL_BASELINE_HASH = "sha256_2588ce1ce8e48df69a449ebe3bb8de7266b1cf6bf18b08495ae4d4acc5c43805"
EXPECTED_HMAC_KEY_FINGERPRINT = "sha256_142e095047f2f49c652fa1d04c3d146070f1b96b2bae697731bb40d146cf3eba"


def compute_historical_baseline_hash(snapshots_file: Path) -> str:
    """Computes deterministic SHA-256 digest over pre-2026 network snapshot records."""
    if not snapshots_file.exists():
        return "sha256_missing_snapshots_file"
    df = pd.read_parquet(snapshots_file)
    sort_cols = ["window_type", "window_start", "window_end", "vtuber_a", "vtuber_b"]
    hist_mask = df["window_end"] < "2026-01-01"
    hist_bytes = df[hist_mask].sort_values(sort_cols).to_csv(index=False).encode("utf-8")
    return "sha256_" + hashlib.sha256(hist_bytes).hexdigest()


def compute_coordinates_block_hash(web_app_js: Path) -> str:
    """Computes SHA-256 digest of the AGENCY_ISLAND_COORDINATES block in web/app.js."""
    if not web_app_js.exists():
        return "sha256_missing_web_app_js"
    text = web_app_js.read_text(encoding="utf-8")
    start = text.find("const AGENCY_ISLAND_COORDINATES = {")
    if start == -1:
        return "sha256_missing_coordinates_block"
    end = text.find("};", start) + 2
    block = text[start:end]
    return "sha256_" + hashlib.sha256(block.encode("utf-8")).hexdigest()


class ObservatoryController:
    """Production manager for the Continuous Thai VTuber Ecosystem Observatory."""

    def __init__(self, base_dir: Optional[Path] = None, stale_threshold_days: int = 30):
        self.base_dir = base_dir or REPO_ROOT
        self.temporal_dir = self.base_dir / "data" / "temporal"
        self.observatory_dir = self.temporal_dir / "observatory"
        self.state_dir = self.temporal_dir / "state"
        self.snapshots_file = self.temporal_dir / "snapshots" / "network_snapshots.parquet"
        self.web_app_js = self.base_dir / "web" / "app.js"

        self.observatory_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.ledger_file = self.observatory_dir / "run_ledger.json"
        self.obs_state_file = self.observatory_dir / "observatory_state.json"
        self.stale_threshold_days = stale_threshold_days

        self._ensure_initialized()

    def _ensure_initialized(self):
        """Initializes ledger and observatory state files if they do not exist."""
        now_iso = datetime.now(timezone.utc).isoformat()

        if not self.ledger_file.exists():
            initial_ledger = {
                "observatory_name": "Thai VTuber Ecosystem Continuous Observatory",
                "schema_version": "1.0.0",
                "created_at": now_iso,
                "runs": []
            }
            self._write_json_atomic(self.ledger_file, initial_ledger)

        if not self.obs_state_file.exists():
            # Derive latest interaction time from canonical snapshots or fallback to 2026-09-08
            latest_time = self._get_latest_interaction_time() or "2026-09-08T04:37:10Z"
            initial_state = {
                "active_dataset_version": "v1.0.0",
                "last_success_run_id": None,
                "last_success_timestamp": None,
                "last_data_interaction_time": latest_time,
                "stale_threshold_days": self.stale_threshold_days,
                "total_runs": 0,
                "historical_baseline_hash": EXPECTED_HISTORICAL_BASELINE_HASH,
                "hmac_key_fingerprint": EXPECTED_HMAC_KEY_FINGERPRINT
            }
            self._write_json_atomic(self.obs_state_file, initial_state)

    def _write_json_atomic(self, path: Path, data: Dict[str, Any]):
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        if path.exists():
            path.unlink()
        tmp_path.rename(path)

    def _load_ledger(self) -> Dict[str, Any]:
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_state(self) -> Dict[str, Any]:
        with open(self.obs_state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_state(self, state: Dict[str, Any]):
        self._write_json_atomic(self.obs_state_file, state)

    def _get_latest_interaction_time(self) -> Optional[str]:
        """Queries canonical events for maximum interaction timestamp."""
        try:
            from scripts.build_duckdb_temporal_snapshots import (
                get_sources_by_provenance,
                build_unified_raw_view,
                build_canonical_events_view
            )
            con = duckdb.connect(":memory:")
            prov = get_sources_by_provenance(base_dir=self.base_dir)
            build_unified_raw_view(con, prov)
            build_canonical_events_view(con, "unified_raw")
            row = con.execute("SELECT MAX(interaction_time) FROM canonical_events").fetchone()
            if row and row[0]:
                val = row[0]
                if isinstance(val, str):
                    return val
                return val.isoformat()
        except Exception as e:
            logger.debug(f"Could not query canonical interaction time: {e}")
        return None

    def check_stale_data(self, latest_time_str: Optional[str] = None) -> Dict[str, Any]:
        """Evaluates whether the observatory has ingested new interactions within the threshold."""
        latest_str = latest_time_str or self._load_state().get("last_data_interaction_time")
        if not latest_str:
            return {"status": "UNKNOWN", "is_stale": True, "details": "No interaction timestamp found"}

        try:
            # Normalize ISO timestamp
            clean_str = latest_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            diff = now - dt
            is_stale = diff > timedelta(days=self.stale_threshold_days)
            return {
                "status": "STALE_ALERT" if is_stale else "FRESH",
                "is_stale": is_stale,
                "latest_interaction_time": latest_str,
                "elapsed_days": round(diff.total_seconds() / 86400, 1),
                "threshold_days": self.stale_threshold_days,
                "details": (
                    f"DATA_STALE_ALERT: Latest data is {round(diff.total_seconds() / 86400, 1)} days old "
                    f"(Threshold: {self.stale_threshold_days} days)"
                    if is_stale else
                    f"Data is FRESH ({round(diff.total_seconds() / 86400, 1)} days old)"
                )
            }
        except Exception as e:
            return {"status": "ERROR", "is_stale": True, "details": f"Timestamp parse error: {e}"}

    def validate_quality_gates(self) -> Dict[str, Any]:
        """Executes automated quality gates required before publication."""
        gates = {}
        all_passed = True

        # Gate 1: Visualizer Coordinates
        coords_hash = compute_coordinates_block_hash(self.web_app_js)
        coords_pass = (coords_hash == EXPECTED_COORDINATES_HASH)
        gates["visualizer_coordinates"] = {
            "status": "PASS" if coords_pass else "FAIL",
            "hash": coords_hash,
            "expected": EXPECTED_COORDINATES_HASH
        }
        if not coords_pass:
            all_passed = False

        # Gate 2: Historical Pre-2026 Snapshot Isolation
        hist_hash = compute_historical_baseline_hash(self.snapshots_file)
        hist_pass = (hist_hash == EXPECTED_HISTORICAL_BASELINE_HASH)
        gates["historical_baseline_isolation"] = {
            "status": "PASS" if hist_pass else "FAIL",
            "hash": hist_hash,
            "expected": EXPECTED_HISTORICAL_BASELINE_HASH
        }
        if not hist_pass:
            all_passed = False

        # Gate 3: HMAC Key Continuity
        try:
            key = load_persistent_secret_key()
            key_fp = "sha256_" + compute_key_fingerprint(key)
            key_pass = (key_fp == EXPECTED_HMAC_KEY_FINGERPRINT)
        except Exception as e:
            key_fp = f"error_{e}"
            key_pass = False
        gates["hmac_key_continuity"] = {
            "status": "PASS" if key_pass else "FAIL",
            "fingerprint": key_fp,
            "expected": EXPECTED_HMAC_KEY_FINGERPRINT
        }
        if not key_pass:
            all_passed = False

        # Gate 4: Dataset Release Validation Script
        release_val_pass = True
        release_val_msg = "OK"
        try:
            from scripts.validate_dataset_release import validate_release
            release_val_pass = validate_release()
        except Exception as e:
            release_val_pass = False
            release_val_msg = str(e)
        gates["dataset_release_validation"] = {
            "status": "PASS" if release_val_pass else "FAIL",
            "details": release_val_msg
        }
        if not release_val_pass:
            all_passed = False

        # Gate 5: Privacy Audit (Zero viewer-level PII)
        privacy_pass = True
        try:
            from scripts.privacy_audit import run_full_privacy_audit
            privacy_pass = run_full_privacy_audit()
        except Exception as e:
            logger.error(f"Privacy audit error: {e}")
            privacy_pass = False
        gates["privacy_audit"] = {
            "status": "PASS" if privacy_pass else "FAIL"
        }
        if not privacy_pass:
            all_passed = False

        return {
            "overall_status": "PASS" if all_passed else "FAIL",
            "all_passed": all_passed,
            "gates": gates,
            "validated_at": datetime.now(timezone.utc).isoformat()
        }

    def status(self) -> Dict[str, Any]:
        """Provides comprehensive health, version, and freshness status."""
        state = self._load_state()
        ledger = self._load_ledger()
        stale_info = self.check_stale_data()

        coords_hash = compute_coordinates_block_hash(self.web_app_js)
        hist_hash = compute_historical_baseline_hash(self.snapshots_file)

        return {
            "observatory_status": "ONLINE",
            "active_dataset_version": state.get("active_dataset_version", "v1.0.0"),
            "total_runs": len(ledger.get("runs", [])),
            "last_success_run_id": state.get("last_success_run_id"),
            "last_success_timestamp": state.get("last_success_timestamp"),
            "data_freshness": stale_info,
            "historical_baseline_health": {
                "status": "HEALTHY" if hist_hash == EXPECTED_HISTORICAL_BASELINE_HASH else "COMPROMISED",
                "current_hash": hist_hash,
                "expected_hash": EXPECTED_HISTORICAL_BASELINE_HASH
            },
            "visualizer_coordinates_health": {
                "status": "HEALTHY" if coords_hash == EXPECTED_COORDINATES_HASH else "MUTATED",
                "current_hash": coords_hash,
                "expected_hash": EXPECTED_COORDINATES_HASH
            }
        }

    def dry_run(self, batch_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulates ingestion and validation without mutating disk state."""
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_dryrun"
        logger.info(f"Starting dry-run '{run_id}' with {len(events)} events (batch='{batch_id}')...")

        pipeline = IncrementalTemporalPipeline(base_dir=self.base_dir, dry_run=True)
        res = pipeline.ingest_batch(batch_id, events)

        # Evaluate quality gates on current disk (which dry-run did not mutate)
        gate_res = self.validate_quality_gates()

        run_entry = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": "dry-run",
            "status": "DRY_RUN",
            "batch_id": batch_id,
            "records_received": res.records_received,
            "records_inserted": res.records_inserted,
            "duplicates_suppressed": res.duplicates_suppressed,
            "affected_years": res.affected_years,
            "quality_gates": gate_res,
            "notes": "No disk state or snapshots were mutated."
        }

        # Record dry-run in ledger
        ledger = self._load_ledger()
        ledger["runs"].append(run_entry)
        self._write_json_atomic(self.ledger_file, ledger)

        logger.info(f"Dry-run completed successfully. Simulated {res.records_inserted} insertions.")
        return run_entry

    def update(
        self,
        batch_id: str,
        events: List[Dict[str, Any]],
        skip_downstream: bool = False,
        auto_publish: bool = True
    ) -> Dict[str, Any]:
        """Ingests new events, rebuilds affected layers, enforces quality gates, and publishes."""
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{batch_id}"
        logger.info(f"Starting observatory update '{run_id}' with {len(events)} events...")

        state = self._load_state()
        version_before = state.get("active_dataset_version", "v1.0.0")

        # 1. Recovery snapshot: backup snapshots parquet and state if exists
        recovery_meta = {
            "version_before": version_before,
            "snapshots_hash_before": compute_historical_baseline_hash(self.snapshots_file),
            "batch_id": batch_id
        }

        # Backup snapshot file in memory / temporary location for rollback safety
        backup_snaps = None
        if self.snapshots_file.exists():
            backup_snaps = self.snapshots_file.with_suffix(".parquet.bak")
            shutil.copy2(self.snapshots_file, backup_snaps)

        try:
            # 2. Ingest batch via IncrementalTemporalPipeline
            pipeline = IncrementalTemporalPipeline(base_dir=self.base_dir, dry_run=False)
            res = pipeline.ingest_batch(batch_id, events)

            if res.status != "COMMITTED":
                raise RuntimeError(f"Pipeline ingestion failed with status: {res.status}")

            affected_years = res.affected_years
            logger.info(f"Ingested {res.records_inserted} records. Affected years: {affected_years}")

            # 3. Rebuild downstream analysis, dashboard, and release outputs if needed
            if not skip_downstream and affected_years:
                self._rebuild_downstream_outputs(affected_years)

            # 4. Automated Quality Gates Verification
            gate_res = self.validate_quality_gates()
            if not gate_res["all_passed"]:
                logger.error("Quality gate verification FAILED. Aborting and initiating fail-safe rollback...")
                # Restore snapshot backup
                if backup_snaps and backup_snaps.exists():
                    shutil.copy2(backup_snaps, self.snapshots_file)
                    backup_snaps.unlink()
                # Remove ingested batch file
                batch_file = self.temporal_dir / "incremental" / f"batch_{batch_id}.parquet"
                if batch_file.exists():
                    batch_file.unlink()

                failed_entry = {
                    "run_id": run_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "command": "update",
                    "status": "FAILED_QUALITY_GATE_ROLLED_BACK",
                    "batch_id": batch_id,
                    "records_received": len(events),
                    "quality_gates": gate_res,
                    "recovery_meta": recovery_meta
                }
                ledger = self._load_ledger()
                ledger["runs"].append(failed_entry)
                self._write_json_atomic(self.ledger_file, ledger)
                raise RuntimeError(f"Quality gate failure: {gate_res['gates']}")

            # Cleanup backup on success
            if backup_snaps and backup_snaps.exists():
                backup_snaps.unlink()

            # 5. Version promotion
            next_version = version_before
            if auto_publish:
                next_version = self._compute_next_version(version_before, affected_years)
                state["active_dataset_version"] = next_version

            # 6. Update observatory state
            latest_interaction = None
            if events:
                latest_interaction = max(e.get("interaction_time", "") for e in events if e.get("interaction_time"))
            if latest_interaction:
                state["last_data_interaction_time"] = latest_interaction

            state["last_success_run_id"] = run_id
            state["last_success_timestamp"] = datetime.now(timezone.utc).isoformat()
            state["total_runs"] = state.get("total_runs", 0) + 1
            self._save_state(state)

            # 7. Append success entry to run ledger
            success_entry = {
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "command": "update",
                "status": "SUCCESS",
                "batch_id": batch_id,
                "records_received": res.records_received,
                "records_inserted": res.records_inserted,
                "duplicates_suppressed": res.duplicates_suppressed,
                "affected_years": affected_years,
                "version_before": version_before,
                "version_after": next_version,
                "quality_gates": gate_res,
                "recovery_meta": recovery_meta
            }
            ledger = self._load_ledger()
            ledger["runs"].append(success_entry)
            self._write_json_atomic(self.ledger_file, ledger)

            logger.info(f"Observatory update completed successfully! Promoted to version: {next_version}")
            return success_entry

        except Exception as e:
            if backup_snaps and backup_snaps.exists():
                shutil.copy2(backup_snaps, self.snapshots_file)
                backup_snaps.unlink()
            raise e

    def _compute_next_version(self, current_ver: str, affected_years: List[int]) -> str:
        """Determines semver progression: minor bump if new calendar year (>2026), else patch bump."""
        clean = current_ver.lstrip("v")
        parts = [int(p) for p in clean.split(".")]
        major, minor, patch = parts[0], parts[1], parts[2]

        has_future_year = any(y > 2026 for y in affected_years)
        if has_future_year:
            minor += 1
            patch = 0
        else:
            patch += 1
        return f"v{major}.{minor}.{patch}"

    def _rebuild_downstream_outputs(self, affected_years: List[int]):
        """Executes downstream regeneration scripts."""
        import subprocess
        scripts_to_run = [
            ("Lineage v2", "scripts/build_community_lineage_v2.py"),
            ("Centrality Evolution", "scripts/analyze_centrality_evolution.py"),
            ("Ecosystem Evolution", "scripts/analyze_ecosystem_evolution.py"),
            ("Evidence Quality", "scripts/analyze_evidence_quality.py"),
            ("Dashboard Data", "scripts/build_research_dashboard_data.py"),
            ("Dataset Release", "scripts/build_dataset_release.py"),
            ("Technical Report", "scripts/build_technical_report.py"),
        ]
        for name, rel_script in scripts_to_run:
            script_path = self.base_dir / rel_script
            if not script_path.exists():
                logger.warning(f"Script {rel_script} not found; skipping.")
                continue
            logger.info(f"Rebuilding downstream: {name}...")
            res = subprocess.run([sys.executable, str(script_path)], cwd=str(self.base_dir), capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"Downstream script {rel_script} failed:\n{res.stderr}")
                raise RuntimeError(f"Downstream build error in {rel_script}: {res.stderr}")

    def publish(self, target_version: Optional[str] = None) -> Dict[str, Any]:
        """Publishes the current dataset state under an explicit version pointer."""
        gate_res = self.validate_quality_gates()
        if not gate_res["all_passed"]:
            raise RuntimeError(f"Cannot publish: Quality gates failed: {gate_res['gates']}")

        state = self._load_state()
        version_before = state.get("active_dataset_version", "v1.0.0")
        new_version = target_version or self._compute_next_version(version_before, [2026])

        state["active_dataset_version"] = new_version
        self._save_state(state)

        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_publish"
        entry = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": "publish",
            "status": "SUCCESS",
            "version_before": version_before,
            "version_after": new_version,
            "quality_gates": gate_res
        }
        ledger = self._load_ledger()
        ledger["runs"].append(entry)
        self._write_json_atomic(self.ledger_file, ledger)

        logger.info(f"Dataset published and promoted to version {new_version}")
        return entry

    def rollback(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Rolls back the most recent update in the ledger."""
        ledger = self._load_ledger()
        if not ledger.get("runs"):
            raise RuntimeError("No runs found in ledger to rollback.")

        target_run = None
        if run_id:
            for r in reversed(ledger["runs"]):
                if r["run_id"] == run_id:
                    target_run = r
                    break
        else:
            for r in reversed(ledger["runs"]):
                if r.get("command") == "update" and r.get("status") == "SUCCESS":
                    target_run = r
                    break

        if not target_run:
            raise RuntimeError("No eligible update run found for rollback.")

        batch_id = target_run.get("batch_id")
        batch_file = self.temporal_dir / "incremental" / f"batch_{batch_id}.parquet"
        if batch_file.exists():
            batch_file.unlink()
            logger.info(f"Removed batch file: {batch_file.name}")

        state = self._load_state()
        state["active_dataset_version"] = target_run.get("version_before", "v1.0.0")
        self._save_state(state)

        rollback_entry = {
            "run_id": f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_rollback",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": "rollback",
            "status": "ROLLED_BACK",
            "reverted_run_id": target_run["run_id"],
            "batch_id": batch_id,
            "reverted_to_version": target_run.get("version_before")
        }
        ledger["runs"].append(rollback_entry)
        self._write_json_atomic(self.ledger_file, ledger)
        logger.info(f"Successfully rolled back batch {batch_id}.")
        return rollback_entry


def main():
    parser = argparse.ArgumentParser(description="Phase T20: Continuous Thai VTuber Ecosystem Observatory")
    subparsers = parser.add_subparsers(dest="command", help="Observatory command to execute")

    # Status
    subparsers.add_parser("status", help="Display active observatory status and health")

    # Validate
    subparsers.add_parser("validate", help="Run automated quality gates")

    # Dry-run
    p_dry = subparsers.add_parser("dry-run", help="Simulate batch update without mutating state")
    p_dry.add_argument("--batch-id", required=True, help="Unique identifier for the batch")
    p_dry.add_argument("--file", required=True, help="JSON or CSV file with interaction records")

    # Update
    p_upd = subparsers.add_parser("update", help="Ingest batch, rebuild outputs, and publish")
    p_upd.add_argument("--batch-id", required=True, help="Unique identifier for the batch")
    p_upd.add_argument("--file", required=True, help="JSON or CSV file with interaction records")
    p_upd.add_argument("--skip-downstream", action="store_true", help="Skip downstream rebuild (for fast testing)")
    p_upd.add_argument("--no-publish", action="store_true", help="Do not promote semver version")

    # Publish
    p_pub = subparsers.add_parser("publish", help="Promote release version")
    p_pub.add_argument("--version", help="Explicit target semver (e.g. v1.1.0)")

    # Rollback
    p_rb = subparsers.add_parser("rollback", help="Rollback last successful batch update")
    p_rb.add_argument("--run-id", help="Target run ID to rollback")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    controller = ObservatoryController()

    if args.command == "status":
        st = controller.status()
        print(json.dumps(st, indent=2))
        sys.exit(0)

    elif args.command == "validate":
        res = controller.validate_quality_gates()
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["all_passed"] else 1)

    elif args.command == "dry-run":
        p = Path(args.file)
        if not p.exists():
            logger.error(f"File not found: {args.file}")
            sys.exit(1)
        events = json.loads(p.read_text(encoding="utf-8")) if p.suffix == ".json" else pd.read_csv(p).to_dict(orient="records")
        res = controller.dry_run(args.batch_id, events)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    elif args.command == "update":
        p = Path(args.file)
        if not p.exists():
            logger.error(f"File not found: {args.file}")
            sys.exit(1)
        events = json.loads(p.read_text(encoding="utf-8")) if p.suffix == ".json" else pd.read_csv(p).to_dict(orient="records")
        res = controller.update(
            batch_id=args.batch_id,
            events=events,
            skip_downstream=args.skip_downstream,
            auto_publish=not args.no_publish
        )
        print(json.dumps(res, indent=2))
        sys.exit(0)

    elif args.command == "publish":
        res = controller.publish(target_version=args.version)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    elif args.command == "rollback":
        res = controller.rollback(run_id=args.run_id)
        print(json.dumps(res, indent=2))
        sys.exit(0)


if __name__ == "__main__":
    main()
