"""
scripts/build_historical_sampling_manifest.py

Phase T5-A & T5-B: Deterministic Stratified Historical Sampling Manifest Builder
Builds a reproducible, stratified sample of historical videos (2020–2026) from the
frozen T1 catalog (193 channels, 96,420 videos).

Stratification Strategy:
- Target: 6 representative videos per channel per year (where available).
- Intra-year distribution: 6 bi-monthly temporal bins (Jan-Feb, Mar-Apr, May-Jun, Jul-Aug, Sep-Oct, Nov-Dec).
- Deterministic selection: SHA-256 hash ranking within each stratum/bin guarantees 100% stable selection.
- Optional event-window oversampling: Loads verified event windows from data/temporal/backfill/event_windows.csv if present.

Outputs:
- data/temporal/backfill/sampling_manifest.parquet
- data/temporal/backfill/sampling_manifest.csv
"""
import sys
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Any, List, Optional, Set, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SamplingManifestBuilder")

TARGET_MANIFEST_CSV = DATA_DIR / "temporal" / "catalog" / "target_manifest.csv"
VIDEO_CATALOG_PARQUET = DATA_DIR / "temporal" / "catalog" / "video_catalog.parquet"
EVENT_WINDOWS_CSV = DATA_DIR / "temporal" / "backfill" / "event_windows.csv"

OUTPUT_DIR = DATA_DIR / "temporal" / "backfill"
OUTPUT_PARQUET = OUTPUT_DIR / "sampling_manifest.parquet"
OUTPUT_CSV = OUTPUT_DIR / "sampling_manifest.csv"

SUPPORTED_YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
TARGET_VIDEOS_PER_YEAR = 6
MANIFEST_VERSION = "1.0"


def get_bimonthly_bin(month: int) -> Tuple[int, str]:
    """Returns (bin_number, bin_name) for 1..12 month."""
    bin_num = (month - 1) // 2 + 1
    bin_names = {
        1: "bin_1_jan_feb",
        2: "bin_2_mar_apr",
        3: "bin_3_may_jun",
        4: "bin_4_jul_aug",
        5: "bin_5_sep_oct",
        6: "bin_6_nov_dec",
    }
    return bin_num, bin_names.get(bin_num, f"bin_{bin_num}")


def compute_deterministic_score(channel_id: str, year: int, salt: str, video_id: str) -> str:
    """Computes a stable deterministic SHA-256 hash score for sorting candidates."""
    token = f"{channel_id}:{year}:{salt}:{video_id}"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def load_target_channels(target_manifest_path: Path = TARGET_MANIFEST_CSV) -> Dict[str, Dict[str, Any]]:
    """Loads frozen T1 target cohort channels."""
    if not target_manifest_path.exists():
        raise FileNotFoundError(f"Target manifest missing: {target_manifest_path}")
    df = pd.read_csv(target_manifest_path)
    channels = {}
    for _, row in df.iterrows():
        cid = str(row["channel_id"]).strip()
        channels[cid] = {
            "channel_id": cid,
            "channel_title": str(row.get("name", "")),
            "tier": str(row.get("tier_at_selection", "Unknown")),
            "subscriber_count": row.get("subscriber_count_at_selection", 0),
            "lifecycle_status": str(row.get("lifecycle_status", "unknown")),
            "agency": str(row.get("agency", "Independent")),
            "target_reason": str(row.get("selection_reason", "")),
        }
    return channels


def load_event_windows(event_windows_path: Path = EVENT_WINDOWS_CSV) -> List[Dict[str, Any]]:
    """Loads verified event windows for optional oversampling."""
    if not event_windows_path.exists():
        return []
    try:
        df = pd.read_csv(event_windows_path)
        if df.empty or "verified" not in df.columns:
            return []
        verified_events = []
        for _, row in df.iterrows():
            is_verified = str(row.get("verified", "")).strip().lower() in ("true", "1", "yes")
            if not is_verified:
                continue
            try:
                ev_date = pd.to_datetime(row["event_date"], utc=True)
                before_days = int(row.get("window_before_days", 30))
                after_days = int(row.get("window_after_days", 30))
                verified_events.append({
                    "event_id": str(row["event_id"]).strip(),
                    "channel_id": str(row["channel_id"]).strip(),
                    "event_type": str(row.get("event_type", "event")),
                    "event_name": str(row.get("event_name", "")),
                    "event_date": ev_date,
                    "window_start": ev_date - pd.Timedelta(days=before_days),
                    "window_end": ev_date + pd.Timedelta(days=after_days),
                })
            except Exception as ex:
                logger.warning(f"Could not parse event row {row}: {ex}")
        return verified_events
    except Exception as e:
        logger.warning(f"Error loading event windows from {event_windows_path}: {e}")
        return []


def build_sampling_manifest(
    video_catalog_path: Path = VIDEO_CATALOG_PARQUET,
    target_manifest_path: Path = TARGET_MANIFEST_CSV,
    event_windows_path: Path = EVENT_WINDOWS_CSV,
    target_per_year: int = TARGET_VIDEOS_PER_YEAR,
    created_at_override: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Constructs the deterministic stratified sampling manifest.
    Returns list of manifest record dictionaries.
    """
    target_channels = load_target_channels(target_manifest_path)
    target_cids = set(target_channels.keys())

    if not video_catalog_path.exists():
        raise FileNotFoundError(f"Video catalog missing: {video_catalog_path}")

    # Load video catalog Parquet table
    cat_table = pq.read_table(video_catalog_path)
    cat_df = cat_table.to_pandas()

    # Filter to eligible videos:
    # 1. Belongs to target cohort
    # 2. Has non-null publication date
    cat_df = cat_df[cat_df["channel_id"].isin(target_cids)].copy()
    cat_df = cat_df[cat_df["video_published_at"].notna()].copy()
    cat_df["video_published_at"] = pd.to_datetime(cat_df["video_published_at"], utc=True)
    cat_df["year"] = cat_df["video_published_at"].dt.year
    cat_df = cat_df[cat_df["year"].isin(SUPPORTED_YEARS)].copy()

    now_utc = created_at_override or datetime.now(timezone.utc).isoformat()
    selected_manifest_records: List[Dict[str, Any]] = []
    selected_video_keys: Set[Tuple[str, str]] = set()  # (channel_id, video_id) to avoid duplicates

    # Group by (channel_id, year)
    grouped = cat_df.groupby(["channel_id", "year"])
    strata_map = {(cid, y): group for (cid, y), group in grouped}

    for cid in sorted(target_cids):
        ch_meta = target_channels[cid]
        for year in SUPPORTED_YEARS:
            stratum = strata_map.get((cid, year))
            if stratum is None or stratum.empty:
                continue

            available_count = len(stratum)
            vids = stratum.to_dict("records")

            if available_count <= target_per_year:
                # Select all available videos in sparse stratum
                # Sort deterministically by hash
                vids.sort(key=lambda x: compute_deterministic_score(cid, year, "sparse", str(x["video_id"])))
                for rank, v in enumerate(vids, start=1):
                    vid = str(v["video_id"])
                    v_pub = v["video_published_at"]
                    _, bin_name = get_bimonthly_bin(v_pub.month)
                    sample_id = f"smp_{cid[:8]}_{year}_{vid}"

                    selected_manifest_records.append({
                        "sample_id": sample_id,
                        "channel_id": cid,
                        "video_id": vid,
                        "video_published_at": v_pub.isoformat(),
                        "year": int(year),
                        "time_bin": bin_name,
                        "sampling_reason": "baseline_stratified",
                        "selection_method": "sparse_all_available",
                        "target_videos_per_year": target_per_year,
                        "available_videos_in_stratum": available_count,
                        "selected_rank": rank,
                        "manifest_version": MANIFEST_VERSION,
                        "created_at": now_utc,
                        "channel_title": ch_meta["channel_title"],
                        "target_reason": ch_meta["target_reason"],
                        "agency": ch_meta["agency"],
                        "tier": ch_meta["tier"],
                        "lifecycle_status": ch_meta["lifecycle_status"],
                        "event_id": None,
                    })
                    selected_video_keys.add((cid, vid))
            else:
                # Divide into bi-monthly temporal bins
                bins = defaultdict(list)
                for v in vids:
                    b_idx, _ = get_bimonthly_bin(v["video_published_at"].month)
                    bins[b_idx].append(v)

                chosen_vids = []
                pool_remainder = []

                # Pass 1: Select best candidate from each available bin
                for b_idx in sorted(bins.keys()):
                    b_vids = bins[b_idx]
                    # Sort candidates deterministically using bin salt
                    b_vids.sort(key=lambda x: compute_deterministic_score(cid, year, f"bin_{b_idx}", str(x["video_id"])))
                    chosen_vids.append(b_vids[0])
                    pool_remainder.extend(b_vids[1:])

                # Pass 2: If fewer than target_per_year bins had videos, fill slots from remaining pool
                if len(chosen_vids) < target_per_year and pool_remainder:
                    needed = target_per_year - len(chosen_vids)
                    pool_remainder.sort(key=lambda x: compute_deterministic_score(cid, year, "fill", str(x["video_id"])))
                    chosen_vids.extend(pool_remainder[:needed])

                final_chosen = chosen_vids[:target_per_year]
                for rank, v in enumerate(final_chosen, start=1):
                    vid = str(v["video_id"])
                    v_pub = v["video_published_at"]
                    _, bin_name = get_bimonthly_bin(v_pub.month)
                    sample_id = f"smp_{cid[:8]}_{year}_{vid}"

                    selected_manifest_records.append({
                        "sample_id": sample_id,
                        "channel_id": cid,
                        "video_id": vid,
                        "video_published_at": v_pub.isoformat(),
                        "year": int(year),
                        "time_bin": bin_name,
                        "sampling_reason": "baseline_stratified",
                        "selection_method": "bimonthly_deterministic_hash",
                        "target_videos_per_year": target_per_year,
                        "available_videos_in_stratum": available_count,
                        "selected_rank": rank,
                        "manifest_version": MANIFEST_VERSION,
                        "created_at": now_utc,
                        "channel_title": ch_meta["channel_title"],
                        "target_reason": ch_meta["target_reason"],
                        "agency": ch_meta["agency"],
                        "tier": ch_meta["tier"],
                        "lifecycle_status": ch_meta["lifecycle_status"],
                        "event_id": None,
                    })
                    selected_video_keys.add((cid, vid))

    # Phase T5-B: Optional Event-Window Oversampling
    event_windows = load_event_windows(event_windows_path)
    if event_windows:
        logger.info(f"Loaded {len(event_windows)} verified event windows for oversampling.")
        for ev in event_windows:
            ev_cid = ev["channel_id"]
            if ev_cid not in target_cids:
                continue
            ev_meta = target_channels[ev_cid]
            # Find matching catalog videos within event window
            ev_candidates = cat_df[
                (cat_df["channel_id"] == ev_cid) &
                (cat_df["video_published_at"] >= ev["window_start"]) &
                (cat_df["video_published_at"] <= ev["window_end"])
            ].to_dict("records")

            # Sort deterministically
            ev_candidates.sort(key=lambda x: compute_deterministic_score(ev_cid, ev["event_date"].year, ev["event_id"], str(x["video_id"])))
            ev_added = 0
            for v in ev_candidates:
                vid = str(v["video_id"])
                if (ev_cid, vid) in selected_video_keys:
                    continue  # Avoid duplicate with baseline
                v_pub = v["video_published_at"]
                _, bin_name = get_bimonthly_bin(v_pub.month)
                sample_id = f"smp_ev_{ev['event_id'][:8]}_{vid}"

                selected_manifest_records.append({
                    "sample_id": sample_id,
                    "channel_id": ev_cid,
                    "video_id": vid,
                    "video_published_at": v_pub.isoformat(),
                    "year": int(v_pub.year),
                    "time_bin": bin_name,
                    "sampling_reason": "event_window",
                    "selection_method": "event_window_deterministic_hash",
                    "target_videos_per_year": target_per_year,
                    "available_videos_in_stratum": len(ev_candidates),
                    "selected_rank": ev_added + 1,
                    "manifest_version": MANIFEST_VERSION,
                    "created_at": now_utc,
                    "channel_title": ev_meta["channel_title"],
                    "target_reason": ev_meta["target_reason"],
                    "agency": ev_meta["agency"],
                    "tier": ev_meta["tier"],
                    "lifecycle_status": ev_meta["lifecycle_status"],
                    "event_id": ev["event_id"],
                })
                selected_video_keys.add((ev_cid, vid))
                ev_added += 1
                if ev_added >= 4:  # Cap at 4 additional event videos per verified event
                    break

    logger.info(f"Generated sampling manifest: {len(selected_manifest_records):,} videos across {len(set(r['channel_id'] for r in selected_manifest_records))} channels.")
    return selected_manifest_records


def save_sampling_manifest(records: List[Dict[str, Any]], parquet_path: Path = OUTPUT_PARQUET, csv_path: Path = OUTPUT_CSV) -> None:
    """Saves sampling manifest to Parquet and CSV formats."""
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)

    # Enforce deterministic order: channel_id ASC, year ASC, selected_rank ASC
    df.sort_values(by=["channel_id", "year", "selected_rank", "video_id"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Save CSV
    df.to_csv(csv_path, index=False, encoding="utf-8")
    logger.info(f"Saved human-readable manifest CSV: {csv_path}")

    # Save Parquet
    tbl = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(tbl, parquet_path, compression="snappy")
    logger.info(f"Saved canonical manifest Parquet: {parquet_path}")


def main():
    logger.info("==========================================================")
    logger.info(" Phase T5-A: Historical Sampling Manifest Generator       ")
    logger.info("==========================================================")
    records = build_sampling_manifest()
    save_sampling_manifest(records)
    logger.info(" Sampling manifest generation complete!                   ")
    logger.info("==========================================================")


if __name__ == "__main__":
    main()
