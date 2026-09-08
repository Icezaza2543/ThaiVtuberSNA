"""Phase T16: Incremental Temporal Update Pipeline & State Engine

Enables append-only incremental updates beyond 2026 without full historical reruns.

Architecture:
1. Append-Only Ingestion:
   - Ingests new interaction batches without touching historical raw parquet files.
   - Preserves HMAC key continuity across all runs.
   - Enforces provenance precedence hierarchy:
     legacy (10) < t2_pilot (20) < t5_stratified (30) < t6_deep (40) < t16_incremental (50).
2. Checkpointed, Crash-Safe State:
   - Atomic state file persistence via temporary file rename.
   - Idempotent execution: reprocessing the same batch returns no-op.
   - Resumes safely if interrupted before commit.
3. Selective Snapshot Rebuild:
   - Rebuilds network snapshots ONLY for affected temporal years/windows.
   - Ensures older historical snapshots remain byte-identical.
4. Dataset Release Manifest:
   - Maintains versioned metadata, checksums, and schema invariants in:
     data/temporal/state/release_manifest.json
     data/temporal/state/pipeline_state.json
"""
import os
import sys
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional, Tuple

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("IncrementalTemporalPipeline")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "temporal"
STATE_DIR = DATA_DIR / "state"
INCREMENTAL_DIR = DATA_DIR / "incremental"
SNAPSHOTS_PARQUET = DATA_DIR / "snapshots" / "network_snapshots.parquet"

STATE_FILE = STATE_DIR / "pipeline_state.json"
RELEASE_MANIFEST_FILE = STATE_DIR / "release_manifest.json"

sys.path.insert(0, str(BASE_DIR))
from core.file_transaction import FileTransaction, exclusive_lock
from core.hasher import load_persistent_secret_key, compute_key_fingerprint, PrivacyHasher
from scripts.build_duckdb_temporal_snapshots import (
    compute_window_snapshots,
    load_channel_coverage_records,
    get_sources_by_provenance,
    build_unified_raw_view,
    build_canonical_events_view,
    NETWORK_SNAPSHOT_SCHEMA
)

# Provenance hierarchy precedence
PROVENANCE_PRECEDENCE = {
    "legacy": 10,
    "t2_pilot": 20,
    "t5_stratified": 30,
    "t6_deep": 40,
    "t16_incremental": 50
}


class HMACKeyContinuityError(Exception):
    """Raised when an active secret key differs from the historical fingerprint."""
    pass


class IngestionResult:
    def __init__(
        self,
        batch_id: str,
        status: str,
        records_received: int,
        records_inserted: int,
        duplicates_suppressed: int,
        affected_years: List[int],
        snapshot_checksum: Optional[str] = None
    ):
        self.batch_id = batch_id
        self.status = status
        self.records_received = records_received
        self.records_inserted = records_inserted
        self.duplicates_suppressed = duplicates_suppressed
        self.affected_years = affected_years
        self.snapshot_checksum = snapshot_checksum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "status": self.status,
            "records_received": self.records_received,
            "records_inserted": self.records_inserted,
            "duplicates_suppressed": self.duplicates_suppressed,
            "affected_years": self.affected_years,
            "snapshot_checksum": self.snapshot_checksum
        }


class IncrementalTemporalPipeline:
    """Manages append-only incremental updates with crash-safety, idempotency, and key continuity."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        dry_run: bool = False,
        mode: str = "incremental",
        custom_key: Optional[bytes] = None
    ):
        from core.storage_boundary import require_t20_sandbox
        require_t20_sandbox(base_dir or BASE_DIR)
        self.base_dir = base_dir or BASE_DIR
        self.state_dir = self.base_dir / "data" / "temporal" / "state"
        self.incremental_dir = self.base_dir / "data" / "temporal" / "incremental"
        self.snapshots_path = self.base_dir / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
        self.dry_run = dry_run
        self.mode = mode

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.incremental_dir.mkdir(parents=True, exist_ok=True)

        # 1. Load active HMAC secret key and compute fingerprint
        if custom_key is not None:
            self.secret_key = custom_key
        else:
            self.secret_key = load_persistent_secret_key()
        self.active_fingerprint = compute_key_fingerprint(self.secret_key)
        self.hasher = PrivacyHasher(self.secret_key)

        # 2. Load or initialize pipeline state
        self.state_file = self.state_dir / "pipeline_state.json"
        self.manifest_file = self.state_dir / "release_manifest.json"
        self.transaction = FileTransaction(self.base_dir, self.state_dir / '.ingestion_transaction')
        with exclusive_lock(self.base_dir / '.observatory.lock'), exclusive_lock(self.state_dir / '.ingestion.lock'):
            self.transaction.recover()
            for folder in (self.incremental_dir, self.snapshots_path.parent):
                for p in folder.glob('*.tmp'):
                    p.unlink()
            self.state = self._load_or_init_state()

        # 3. Enforce HMAC key continuity
        self._verify_hmac_continuity()

    def _load_or_init_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            init_state = {
                "schema_version": "1.0.0",
                "pipeline_mode": self.mode,
                "hmac_key_fingerprint": self.active_fingerprint,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_committed_at": None,
                "active_dataset_version": "v1.0.0",
                "processed_batches": {}
            }
            if not self.dry_run:
                self._save_state(init_state)
            return init_state

    def _verify_hmac_continuity(self) -> None:
        persisted_fp = self.state.get("hmac_key_fingerprint")
        if persisted_fp and persisted_fp != self.active_fingerprint:
            raise HMACKeyContinuityError(
                f"FATAL: HMAC Key Continuity Violation! "
                f"Persisted fingerprint={persisted_fp}, active fingerprint={self.active_fingerprint}. "
                "Historical pseudonyms must NEVER be regenerated with a different secret key."
            )

    def _save_state(self, state_dict: Dict[str, Any]) -> None:
        """Atomic, crash-safe state persistence."""
        tmp_file = self.state_dir / f"pipeline_state_{os.getpid()}_{int(datetime.now().timestamp() * 1000)}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2)
        # Atomic rename on POSIX and Windows (Python 3.3+)
        tmp_file.replace(self.state_file)

    def ingest_batch(self, *args, **kwargs):
        with exclusive_lock(self.base_dir / '.observatory.lock'), exclusive_lock(self.state_dir / '.ingestion.lock'):
            self.transaction.recover()
            self.state = self._load_or_init_state()
            self._verify_hmac_continuity()
            return self._ingest_batch(*args, **kwargs)

    def _ingest_batch(
        self,
        batch_id: str,
        events: List[Dict[str, Any]],
        provenance: str = "t16_incremental",
        source_type: str = "comment",
        simulate_crash_before_commit: bool = False,
        crash_at: Optional[str] = None
    ) -> IngestionResult:
        """Ingests a new batch of raw interaction events idempotently."""
        logger.info(f"Processing batch '{batch_id}' with {len(events)} events (provenance={provenance})...")

        import re
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', batch_id):
            raise ValueError('Invalid batch ID')
        # 1. Idempotency check
        if batch_id in self.state.get("processed_batches", {}):
            b_info = self.state["processed_batches"][batch_id]
            if b_info.get("status") == "COMMITTED":
                logger.info(f"Batch '{batch_id}' already COMMITTED. Idempotent no-op.")
                current_checksum = hashlib.sha256(open(self.snapshots_path, "rb").read()).hexdigest() if self.snapshots_path.exists() else ""
                return IngestionResult(
                    batch_id=batch_id,
                    status="ALREADY_PROCESSED",
                    records_received=len(events),
                    records_inserted=0,
                    duplicates_suppressed=len(events),
                    affected_years=[],
                    snapshot_checksum=current_checksum
                )

        if not events:
            current_checksum = hashlib.sha256(open(self.snapshots_path, "rb").read()).hexdigest() if self.snapshots_path.exists() else ""
            return IngestionResult(batch_id, "SUCCESS_EMPTY", 0, 0, 0, [], current_checksum)

        # 2. Pseudonymize raw author IDs on RAM boundary
        processed_rows = []
        affected_years_set: Set[int] = set()

        for ev in events:
            raw_author = ev.get("author_channel_id") or ev.get("author_id")
            if raw_author:
                v_hash = self.hasher.hash_viewer_id(str(raw_author))
            elif "viewer_hash" in ev and ev["viewer_hash"]:
                v_hash = str(ev["viewer_hash"])
            else:
                continue

            raw_time = ev.get("interaction_time") or ev.get("interaction_at")
            if isinstance(raw_time, str):
                dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            elif isinstance(raw_time, datetime):
                dt = raw_time
            else:
                continue

            yr = dt.year
            affected_years_set.add(yr)
            s_type = ev.get("source_type", source_type)

            processed_rows.append({
                "viewer_hash": v_hash,
                "vtuber_channel_id": str(ev["vtuber_channel_id"]),
                "video_id": str(ev.get("video_id", "unknown")),
                "interaction_time": dt,
                "interaction_at": dt.isoformat(),
                "interaction_year": yr,
                "source_type": s_type,
                "provenance": provenance,
                "provenance_rank": PROVENANCE_PRECEDENCE.get(provenance, 50)
            })

        if not processed_rows:
            current_checksum = hashlib.sha256(open(self.snapshots_path, "rb").read()).hexdigest() if self.snapshots_path.exists() else ""
            return IngestionResult(batch_id, "NO_VALID_RECORDS", len(events), 0, 0, [], current_checksum)

        df_incoming = pd.DataFrame(processed_rows)

        # 3. Deduplication against existing storage (both historical and incremental)
        existing_keys: Set[Tuple[str, str, str, str]] = set()

        # Check existing incremental directory files (ignore uncommitted .tmp files)
        for f in self.incremental_dir.glob("batch_*.parquet"):
            if f.name.endswith(".tmp"):
                continue
            try:
                df_ex = pd.read_parquet(f, columns=["viewer_hash", "vtuber_channel_id", "video_id", "source_type"])
                for _, r in df_ex.iterrows():
                    existing_keys.add((r["viewer_hash"], r["vtuber_channel_id"], r["video_id"], r["source_type"]))
            except Exception:
                pass

        # Check historical canonical evidence from DuckDB for affected years
        try:
            con_check = duckdb.connect(":memory:")
            prov_hist = get_sources_by_provenance(base_dir=self.base_dir)
            build_unified_raw_view(con_check, prov_hist)
            build_canonical_events_view(con_check, "unified_raw")
            years_str = ", ".join(str(y) for y in affected_years_set)
            hist_rows = con_check.execute(f"""
                SELECT DISTINCT viewer_hash, vtuber_channel_id, video_id, source_type
                FROM canonical_events
                WHERE extract(year from interaction_time) IN ({years_str})
            """).fetchall()
            for r in hist_rows:
                existing_keys.add((r[0], r[1], r[2], r[3]))
            con_check.close()
        except Exception as e:
            logger.warning(f"Could not check historical keys from DuckDB: {e}")

        # Deduplicate incoming records (including intra-batch duplicates)
        unique_rows = []
        dups_count = 0
        for _, r in df_incoming.iterrows():
            k = (r["viewer_hash"], r["vtuber_channel_id"], r["video_id"], r["source_type"])
            if k in existing_keys:
                dups_count += 1
            else:
                existing_keys.add(k)
                unique_rows.append(r)

        records_to_insert = len(unique_rows)
        affected_years = sorted(affected_years_set)

        if self.dry_run:
            logger.info(f"[DRY RUN] Would insert {records_to_insert} rows (suppressed {dups_count} duplicates).")
            current_checksum = hashlib.sha256(open(self.snapshots_path, "rb").read()).hexdigest() if self.snapshots_path.exists() else ""
            return IngestionResult(
                batch_id=batch_id,
                status="DRY_RUN",
                records_received=len(events),
                records_inserted=records_to_insert,
                duplicates_suppressed=dups_count,
                affected_years=affected_years,
                snapshot_checksum=current_checksum
            )

        if records_to_insert == 0:
            logger.info(f"Batch '{batch_id}' contains 0 new records ({dups_count} duplicates suppressed).")
            current_checksum = hashlib.sha256(open(self.snapshots_path, "rb").read()).hexdigest() if self.snapshots_path.exists() else ""
            new_version = f"v1.{len(self.state.get('processed_batches', {})) + 1}.0"
            self.state["processed_batches"][batch_id] = {
                "status": "COMMITTED",
                "committed_at": datetime.now(timezone.utc).isoformat(),
                "records_received": len(events),
                "records_inserted": 0,
                "duplicates_suppressed": dups_count,
                "affected_years": affected_years,
                "batch_file": None,
                "snapshot_checksum": current_checksum
            }
            self.state["last_committed_at"] = datetime.now(timezone.utc).isoformat()
            self._save_state(self.state)
            return IngestionResult(
                batch_id=batch_id,
                status="COMMITTED",
                records_received=len(events),
                records_inserted=0,
                duplicates_suppressed=dups_count,
                affected_years=affected_years,
                snapshot_checksum=current_checksum
            )

        # 4. Crash-safe staged append-only persistence
        batch_parquet = self.incremental_dir / f"batch_{batch_id}.parquet"
        batch_parquet_tmp = self.incremental_dir / f"batch_{batch_id}_{os.getpid()}_{int(datetime.now().timestamp() * 1000)}.parquet.tmp"
        df_unique = pd.DataFrame(unique_rows)
        df_unique.to_parquet(batch_parquet_tmp, index=False)

        # 5. Incremental Snapshot Rebuild for Affected Periods ONLY (staged file participates!)
        snapshot_checksum, staged_snapshots_tmp = self._rebuild_snapshots_for_affected_years(
            affected_years, staged_file=batch_parquet_tmp
        )

        # 6. Simulate crash before checkpoint if requested
        if simulate_crash_before_commit:
            logger.warning(f"Simulating unhandled crash before checkpoint commit for batch {batch_id}!")
            if batch_parquet_tmp.exists():
                batch_parquet_tmp.unlink()
            if staged_snapshots_tmp and staged_snapshots_tmp.exists():
                staged_snapshots_tmp.unlink()
            raise RuntimeError("CRASH_BEFORE_COMMIT")

        self.transaction.prepare([batch_parquet, self.snapshots_path, self.state_file, self.manifest_file])
        def crash(point):
            if crash_at == point:
                raise RuntimeError('CRASH_' + point)
        crash('A')
        batch_parquet_tmp.replace(batch_parquet)
        crash('B')
        if staged_snapshots_tmp:
            staged_snapshots_tmp.replace(self.snapshots_path)
        crash('C')

        # 7. Checkpointed Commit
        new_version = f"v1.{len(self.state.get('processed_batches', {})) + 1}.0"
        self.state["processed_batches"][batch_id] = {
            "status": "COMMITTED",
            "committed_at": datetime.now(timezone.utc).isoformat(),
            "records_received": len(events),
            "records_inserted": records_to_insert,
            "duplicates_suppressed": dups_count,
            "affected_years": affected_years,
            "batch_file": str(batch_parquet.name),
            "snapshot_checksum": snapshot_checksum
        }
        self.state["last_committed_at"] = datetime.now(timezone.utc).isoformat()
        self.state["active_dataset_version"] = new_version

        crash('D')
        self._save_state(self.state)
        self._update_release_manifest(new_version, affected_years)
        self.transaction.commit()
        crash('E')
        self.transaction.cleanup()

        logger.info(f"Committed batch '{batch_id}' successfully (Version: {new_version}).")
        return IngestionResult(
            batch_id=batch_id,
            status="COMMITTED",
            records_received=len(events),
            records_inserted=records_to_insert,
            duplicates_suppressed=dups_count,
            affected_years=affected_years,
            snapshot_checksum=snapshot_checksum
        )

    def _rebuild_snapshots_for_affected_years(
        self,
        affected_years: List[int],
        staged_file: Optional[Path] = None
    ) -> Tuple[str, Optional[Path]]:
        """Rebuilds network snapshots for affected years only, leaving historical slices untouched."""
        if not self.snapshots_path.exists():
            return "", None

        df_snapshots = pd.read_parquet(self.snapshots_path)

        # 1. Connect to DuckDB with all sources + staged file
        extra_inc = [str(staged_file)] if staged_file and staged_file.exists() else []
        sources_by_prov = get_sources_by_provenance(base_dir=self.base_dir, extra_incremental_files=extra_inc)

        con = duckdb.connect(":memory:")
        build_unified_raw_view(con, sources_by_prov)
        build_canonical_events_view(con, "unified_raw")
        cov_records = load_channel_coverage_records(base_dir=self.base_dir)

        # Determine latest interaction date in canonical events
        max_inter_row = con.execute("SELECT MAX(interaction_time) FROM canonical_events").fetchone()
        max_inter_dt = max_inter_row[0] if max_inter_row else None
        latest_year = max_inter_dt.year if max_inter_dt else max(affected_years)
        min_affected_year = min(affected_years)

        # 2. Build list of affected windows to recompute
        windows_to_rebuild = []

        # Yearly windows
        for yr in affected_years:
            if yr <= 2025:
                w_start = f"{yr}-01-01"
                w_end = f"{yr}-12-31 23:59:59"
            elif yr == 2026:
                w_start = "2026-01-01"
                w_end = "2026-09-08 23:59:59"
                if max_inter_dt and max_inter_dt.year == 2026:
                    ts_str = max_inter_dt.strftime("%Y-%m-%d %H:%M:%S")
                    if ts_str > w_end:
                        w_end = ts_str
            else:
                w_start = f"{yr}-01-01"
                w_end = f"{yr}-12-31 23:59:59"
            windows_to_rebuild.append({"type": "yearly", "start": w_start, "end": w_end})

        # Cumulative windows ending in year >= min_affected_year
        cum_rows = df_snapshots[df_snapshots["window_type"] == "cumulative"]
        for _, r in cum_rows[["window_start", "window_end"]].drop_duplicates().iterrows():
            end_yr = int(r["window_end"][:4])
            if end_yr >= min_affected_year:
                windows_to_rebuild.append({
                    "type": "cumulative",
                    "start": r["window_start"],
                    "end": r["window_end"]
                })

        # Future-year cumulative windows (e.g. 2027)
        for yr in affected_years:
            if yr > 2026:
                c_start = "2020-01-01"
                c_end = f"{yr}-12-31 23:59:59"
                if not any(w["type"] == "cumulative" and w["start"] == c_start and w["end"] == c_end for w in windows_to_rebuild):
                    windows_to_rebuild.append({"type": "cumulative", "start": c_start, "end": c_end})

        # All-time window: always rebuilt when affected
        all_time_end = "2026-09-08 23:59:59"
        if max_inter_dt:
            ts_str = max_inter_dt.strftime("%Y-%m-%d %H:%M:%S")
            if ts_str > all_time_end:
                all_time_end = f"{latest_year}-12-31 23:59:59" if latest_year > 2026 else ts_str
        windows_to_rebuild.append({"type": "all_time", "start": "2020-01-01", "end": all_time_end})

        # 3. Compute new snapshot rows
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        new_snapshot_rows = []
        affected_keys = set()
        for w in windows_to_rebuild:
            snap_rows = compute_window_snapshots(con, w, cov_records, "canonical_events", now_utc)
            new_snapshot_rows.extend(snap_rows)
            affected_keys.add((w["type"], w["start"], w["end"]))

        con.close()

        # 4. Atomically replace matching windows in df_snapshots
        keep_mask = pd.Series(True, index=df_snapshots.index)
        for (w_type, w_start, w_end) in affected_keys:
            if w_type == "all_time":
                match = (df_snapshots["window_type"] == "all_time")
            elif w_type == 'yearly':
                match = (df_snapshots['window_type'] == w_type) & (df_snapshots['window_start'] == w_start)
            else:
                match = ((df_snapshots['window_type'] == w_type) & (df_snapshots['window_start'] == w_start)
                         & (df_snapshots['window_end'].str[:4] == w_end[:4]))
            keep_mask = keep_mask & (~match)

        df_kept = df_snapshots[keep_mask].copy()
        if new_snapshot_rows:
            df_new = pd.DataFrame(new_snapshot_rows)
            df_combined = pd.concat([df_kept, df_new], ignore_index=True)
        else:
            df_combined = df_kept

        # 5. Write to temporary staged parquet file
        staged_snapshots_tmp = self.snapshots_path.parent / f"network_snapshots_{os.getpid()}_{int(datetime.now().timestamp() * 1000)}.parquet.tmp"
        df_combined = df_combined.sort_values(['window_type','window_start','window_end','vtuber_a','vtuber_b']).reset_index(drop=True)
        tbl = pa.Table.from_pandas(df_combined, schema=NETWORK_SNAPSHOT_SCHEMA, preserve_index=False)
        pq.write_table(tbl, staged_snapshots_tmp, compression="snappy")

        checksum = hashlib.sha256(open(staged_snapshots_tmp, "rb").read()).hexdigest()
        return checksum, staged_snapshots_tmp

    def _update_release_manifest(self, version: str, affected_years: List[int]) -> None:
        """Updates release_manifest.json with dataset metadata and audit signatures."""
        manifest = {
            "dataset_name": "ThaiVtuberSNA Longitudinal Network Dataset",
            "release_version": version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hmac_key_fingerprint": self.active_fingerprint,
            "provenance_hierarchy": PROVENANCE_PRECEDENCE,
            "active_temporal_range": [2020, 2026],
            "last_affected_years": affected_years,
            "state_file_checksum": hashlib.sha256(open(self.state_file, "rb").read()).hexdigest()
        }
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)


def run_pipeline_initialization() -> None:
    """Initializes the pipeline state and baseline release manifest."""
    pipeline = IncrementalTemporalPipeline()
    logger.info(f"Initialized Incremental Pipeline with Key Fingerprint: {pipeline.active_fingerprint[:16]}...")
    pipeline._update_release_manifest(pipeline.state["active_dataset_version"], [2026])
    logger.info(f"State saved to {STATE_FILE}")
    logger.info(f"Manifest saved to {RELEASE_MANIFEST_FILE}")


if __name__ == "__main__":
    run_pipeline_initialization()
