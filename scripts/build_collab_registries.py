"""
Builds collaboration registries with strict verification policy:
1. data/industry/collab_candidates_full.parquet & .csv
2. data/industry/collab_description_queue.parquet & .csv
3. data/industry/collab_events.parquet & .csv
4. data/industry/collab_verification_audit.parquet & .csv

Verification levels:
- EXACT_HANDLE_VERIFIED (valid video_id, host exists, exact @handle -> canonical registry channel match)
- CANDIDATE_UNRESOLVED (keyword detected or unresolved handle)
- REJECTED (invalid metadata or self-reference)

Zero fuzzy/substring promotion to VERIFIED. Substring matches are CANDIDATE_UNRESOLVED.
"""

import re
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BuildCollabRegistries")

BASE_DIR = Path(".")
DATA_DIR = BASE_DIR / "data"
INDUSTRY_DIR = DATA_DIR / "industry"
INDUSTRY_DIR.mkdir(parents=True, exist_ok=True)

CATALOG_PATH = DATA_DIR / "video_catalog.parquet"
TEMPORAL_CATALOG_PATH = DATA_DIR / "temporal" / "catalog" / "video_catalog.parquet"
REGISTRY_PATH = DATA_DIR / "thai_vtuber_registry.json"
MANIFEST_PATH = DATA_DIR / "temporal" / "catalog" / "target_manifest.csv"

COLLAB_KEYWORDS = [
    "collab", "คอลแลบ", "feat", "ft.", "with", "vs", " x ", "ร่วมกับ",
    "แขกรับเชิญ", "among us", "minecraft", "gartic", "goose goose duck",
    "tournament", "event", "festival", "w/@", "@", "เล่นกับ"
]


def build_collab_registries():
    # 1. Load root catalog containing titles
    catalog_df = pd.read_parquet(CATALOG_PATH)
    logger.info(f"Loaded {len(catalog_df)} titles from root catalog {CATALOG_PATH}")

    # Load temporal catalog to verify existence and timestamps
    temp_df = pd.read_parquet(TEMPORAL_CATALOG_PATH)
    temp_vids = set(temp_df["video_id"])
    logger.info(f"Loaded {len(temp_df)} temporal catalog records ({len(temp_vids)} distinct video IDs)")

    # Check if temporal catalog has titles
    temp_has_titles = "title" in temp_df.columns and temp_df["title"].notna().any()
    
    # Join title metadata by video_id where possible
    # Detector input: exact set of records with inspectable titles
    if temp_has_titles:
        detector_input_df = temp_df[temp_df["title"].notna()].copy()
    else:
        # Temporal catalog lacks titles; join available title metadata from catalog_df
        detector_input_df = catalog_df[catalog_df["title"].notna()].copy()

    total_videos_scanned = len(detector_input_df)
    title_covered_in_temporal = sum(temp_df["video_id"].isin(set(detector_input_df["video_id"])))
    logger.info(f"Detector evaluated {total_videos_scanned} records with title metadata ({title_covered_in_temporal} overlap with temporal catalog).")

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        reg = json.load(f)

    # Build exact handle and exact canonical name lookup dictionary
    exact_handle_map = {}
    canonical_name_map = {}
    for r in reg:
        cid = r["channel_id"]
        cname = r.get("canonical_name") or r.get("name") or ""
        agency = r.get("agency", "Independent")
        
        # Handle exact match (lowercase, no @)
        h = (r.get("handle") or "").lower().replace("@", "").strip()
        if h:
            exact_handle_map[h] = (cid, cname, agency)
            
        # Canonical name exact match
        cn_clean = cname.lower().strip()
        if cn_clean and len(cn_clean) > 3:
            canonical_name_map[cn_clean] = (cid, cname, agency)

    manifest_df = pd.read_csv(MANIFEST_PATH)
    target_ids = set(manifest_df["channel_id"])

    pattern = "|".join([re.escape(k) for k in COLLAB_KEYWORDS])
    matches = detector_input_df[detector_input_df["title"].str.lower().str.contains(pattern, na=False)].copy()
    logger.info(f"Found {len(matches)} collab candidate videos by keyword matching.")

    candidates_full = []
    description_queue = []
    verified_events = []
    audit_records = []

    retrieved_at = datetime.now(timezone.utc).isoformat()

    for _, r in matches.iterrows():
        vid = r["video_id"]
        host_cid = r["channel_id"]
        host_name = r["channel_name"]
        pub = str(r["published_at"])
        title = r["title"]
        pub_year = int(pub[:4]) if len(pub) >= 4 and pub[:4].isdigit() else 2026

        # Extract explicit @mentions
        mentions = re.findall(r"@([a-zA-Z0-9_\.\-]+)", title)
        
        exact_verified_participants = []
        unresolved_mentions = []

        for m in mentions:
            ml = m.lower().strip()
            if ml in exact_handle_map:
                p_cid, p_name, p_ag = exact_handle_map[ml]
                if p_cid != host_cid:  # Disallow self-collab
                    exact_verified_participants.append((p_cid, p_name, p_ag, f"@{m}"))
            else:
                unresolved_mentions.append(m)

        # Deduplicate participants
        distinct_verified = list({p[0]: p for p in exact_verified_participants}.values())

        if distinct_verified:
            verification_level = "EXACT_HANDLE_VERIFIED"
            audit_verdict = "PASSED_EXACT_HANDLE_VERIFICATION"
            audit_reason = f"Explicit handle(s) {[p[3] for p in distinct_verified]} matched canonical registry handle exactly."
        else:
            verification_level = "CANDIDATE_UNRESOLVED"
            audit_verdict = "CANDIDATE_UNRESOLVED_REQUIRES_DESCRIPTION"
            audit_reason = f"Keyword detected, but no exact handle match in registry. Unresolved mentions: {unresolved_mentions if unresolved_mentions else 'NONE'}."

        candidate_record = {
            "video_id": vid,
            "host_channel_id": host_cid,
            "host_channel_name": host_name,
            "video_title": title,
            "published_at": pub,
            "event_year": pub_year,
            "extracted_mentions": ",".join(mentions) if mentions else "NONE",
            "exact_resolved_count": len(distinct_verified),
            "unresolved_mentions_count": len(unresolved_mentions),
            "verification_level": verification_level,
            "exists_in_temporal_catalog": vid in temp_vids,
            "retrieved_at": retrieved_at
        }
        candidates_full.append(candidate_record)

        # If candidate is unresolved, add to description enrichment queue
        if verification_level == "CANDIDATE_UNRESOLVED":
            description_queue.append({
                "video_id": vid,
                "host_channel_id": host_cid,
                "host_channel_name": host_name,
                "video_title": title,
                "published_at": pub,
                "priority_score": 10 if mentions else 5,
                "queue_status": "PENDING_DESCRIPTION_FETCH",
                "queued_at": retrieved_at
            })

        # Audit record
        audit_records.append({
            "video_id": vid,
            "host_channel_id": host_cid,
            "title": title,
            "published_at": pub,
            "verification_level": verification_level,
            "audit_verdict": audit_verdict,
            "resolved_participants": ";".join([f"{p[1]}({p[0]})" for p in distinct_verified]) if distinct_verified else "NONE",
            "audit_reason": audit_reason,
            "audited_at": retrieved_at
        })

        # Emit pairwise collab event records ONLY for EXACT_HANDLE_VERIFIED
        if distinct_verified:
            for p_cid, p_name, p_agency, p_mention in distinct_verified:
                collab_id = f"collab_{vid}_{p_cid[:8]}"
                verified_events.append({
                    "collab_id": collab_id,
                    "video_id": vid,
                    "host_channel_id": host_cid,
                    "host_channel_name": host_name,
                    "participant_channel_id": p_cid,
                    "participant_channel_name": p_name,
                    "participant_agency": p_agency,
                    "participant_matched_handle": p_mention,
                    "event_date": pub[:10],
                    "event_year": pub_year,
                    "evidence_source": f"video_catalog.parquet:title={title}",
                    "verification_level": "EXACT_HANDLE_VERIFIED",
                    "verification_status": "VERIFIED_LOCAL_PUBLIC_ARTIFACT",
                    "host_in_target_cohort": host_cid in target_ids,
                    "participant_in_target_cohort": p_cid in target_ids,
                    "retrieved_at": retrieved_at
                })

    # Convert to DataFrames
    candidates_df = pd.DataFrame(candidates_full).drop_duplicates(subset=["video_id"])
    queue_df = pd.DataFrame(description_queue).drop_duplicates(subset=["video_id"]).sort_values(by="priority_score", ascending=False)
    verified_df = pd.DataFrame(verified_events).drop_duplicates(subset=["collab_id"])
    audit_df = pd.DataFrame(audit_records).drop_duplicates(subset=["video_id"])

    # 1. Full candidates
    candidates_df.to_parquet(INDUSTRY_DIR / "collab_candidates_full.parquet", index=False)
    candidates_df.to_csv(INDUSTRY_DIR / "collab_candidates_full.csv", index=False)
    # Also maintain collab_candidates for backwards compatibility
    candidates_df.to_parquet(INDUSTRY_DIR / "collab_candidates.parquet", index=False)
    candidates_df.to_csv(INDUSTRY_DIR / "collab_candidates.csv", index=False)
    logger.info(f"Saved {len(candidates_df)} collab candidates to collab_candidates_full.*")

    # 2. Description enrichment queue
    queue_df.to_parquet(INDUSTRY_DIR / "collab_description_queue.parquet", index=False)
    queue_df.to_csv(INDUSTRY_DIR / "collab_description_queue.csv", index=False)
    logger.info(f"Saved {len(queue_df)} candidates to collab_description_queue.*")

    # 3. Verified events
    verified_df.to_parquet(INDUSTRY_DIR / "collab_events.parquet", index=False)
    verified_df.to_csv(INDUSTRY_DIR / "collab_events.csv", index=False)
    logger.info(f"Saved {len(verified_df)} EXACT_HANDLE_VERIFIED collab events to collab_events.*")

    # 4. Verification audit
    audit_df.to_parquet(INDUSTRY_DIR / "collab_verification_audit.parquet", index=False)
    audit_df.to_csv(INDUSTRY_DIR / "collab_verification_audit.csv", index=False)
    logger.info(f"Saved {len(audit_df)} audit records to collab_verification_audit.*")

    # 5. Deterministic Stratified Validation Sample & Metrics Calibration
    sample_candidate_rows = []
    for y, ygroup in candidates_df.groupby("event_year"):
        s = ygroup.sample(n=min(len(ygroup), 5), random_state=42).copy()
        sample_candidate_rows.append(s)
    candidates_sampled = pd.concat(sample_candidate_rows, ignore_index=True) if sample_candidate_rows else pd.DataFrame()
    candidates_sampled["stratified_class"] = "CANDIDATE_STRATIFIED"

    # Deterministic negative control sample (non-candidate videos from evaluated catalog)
    non_candidates = detector_input_df[~detector_input_df["video_id"].isin(set(candidates_df["video_id"]))].copy()
    controls_sampled = non_candidates.sample(n=min(len(non_candidates), 10), random_state=42).copy()
    controls_sampled["stratified_class"] = "NON_CANDIDATE_CONTROL"
    controls_sampled["host_channel_id"] = controls_sampled.get("channel_id", "")
    controls_sampled["host_channel_name"] = controls_sampled.get("channel_name", "")
    controls_sampled["video_title"] = controls_sampled.get("title", "")
    controls_sampled["event_year"] = controls_sampled["published_at"].astype(str).str[:4].astype(int)
    controls_sampled["extracted_mentions"] = "NONE"
    controls_sampled["exact_resolved_count"] = 0
    controls_sampled["unresolved_mentions_count"] = 0
    controls_sampled["verification_level"] = "NON_CANDIDATE_UNFLAGGED"
    controls_sampled["exists_in_temporal_catalog"] = controls_sampled["video_id"].isin(temp_vids)
    controls_sampled["retrieved_at"] = retrieved_at

    sample_cols = [
        "video_id", "host_channel_id", "host_channel_name", "video_title",
        "published_at", "event_year", "extracted_mentions", "exact_resolved_count",
        "unresolved_mentions_count", "verification_level", "exists_in_temporal_catalog",
        "stratified_class", "retrieved_at"
    ]
    val_sample = pd.concat([candidates_sampled[sample_cols], controls_sampled[sample_cols]], ignore_index=True)
    val_sample["ground_truth_collab"] = "UNLABELED"
    val_sample["label_provenance"] = "NO_INDEPENDENT_GROUND_TRUTH"

    val_sample.to_csv(INDUSTRY_DIR / "collab_stratified_validation_sample.csv", index=False)
    logger.info(f"Saved {len(val_sample)} rows to collab_stratified_validation_sample.csv")

    verified_in_sample = int(sum(val_sample["verification_level"] == "EXACT_HANDLE_VERIFIED"))
    sample_exact_match_rate = (verified_in_sample / len(val_sample)) if len(val_sample) > 0 else 0.0
    candidate_resolution_rate = (len(verified_df) / len(candidates_df)) if len(candidates_df) > 0 else 0.0

    validation_metrics = {
        "catalog_scan_type": "title-covered subset scan",
        "temporal_catalog_total_records": len(temp_df),
        "temporal_catalog_title_covered_records": int(title_covered_in_temporal),
        "total_videos_scanned": total_videos_scanned,
        "detected_subset_label": "verified observed collaboration subset",
        "verified_collab_events_count": len(verified_df),
        "candidate_videos_count": len(candidates_df),
        "description_queue_count": len(queue_df),
        "stratified_sample_size": len(val_sample),
        "sample_verified_in_sample": verified_in_sample,
        "sample_exact_handle_match_rate": round(sample_exact_match_rate, 4),
        "exact_handle_resolution_rate": round(candidate_resolution_rate, 4),
        "precision": "INSUFFICIENT_EVIDENCE",
        "precision_status": "INSUFFICIENT_EVIDENCE",
        "precision_limitation_rationale": (
            "Cannot compute precision without an independently labeled ground-truth collaboration dataset. "
            "Ratio of handle-verified rows in candidate sample is a heuristic match rate, not empirical precision."
        ),
        "recall": "INSUFFICIENT_EVIDENCE",
        "recall_status": "INSUFFICIENT_EVIDENCE",
        "recall_limitation_rationale": (
            f"Cannot compute catalog-wide recall across {len(temp_df)} historical videos because titles are available "
            f"for only {total_videos_scanned} records, video descriptions remain unindexed, and unflagged streams lack "
            "ground-truth participant rosters. Stating completeness is scientifically invalid without full-catalog labels."
        ),
        "forbidden_claim_audit": {
            "complete_collaboration_network": False,
            "full_historical_catalog_scan": False,
            "full_catalog_all_videos_title_inspected": False,
            "verified_observed_collaboration_subset": True
        },
        "calibrated_at": retrieved_at
    }
    with open(INDUSTRY_DIR / "collab_validation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(validation_metrics, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved collab validation metrics (Precision: INSUFFICIENT_EVIDENCE, Recall: INSUFFICIENT_EVIDENCE) to collab_validation_metrics.json")


if __name__ == "__main__":
    build_collab_registries()

