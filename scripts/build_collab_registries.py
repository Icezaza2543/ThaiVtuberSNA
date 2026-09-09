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


STRONG_COLLAB_MARKERS = [
    r"#collab",
    r"\bcollab\b",
    r"คอลแลบ",
    r"w\s*/\s*@",
    r"with\s+@",
    r"ft\.?\s*@",
    r"feat\.?\s*@",
    r"ร่วมกับ",
    r"เล่นกับ",
    r"กับ\s*@"
]

NON_COLLAB_MARKERS = [
    r"hbd",
    r"happy\s+birthday",
    r"art\s+by",
    r"fanart\s+by",
    r"illustration\s+by",
    r"thanks",
    r"thank\s+you",
    r"ขอบคุณ"
]


def verify_collab_context(title: str, handle: str) -> tuple[bool, str]:
    """
    Verifies if a title provides strong collaboration context linked to a participant handle.
    Bare @mention or generic event/game keywords alone do not verify collaboration.
    """
    t_lower = title.lower()
    h_clean = handle.lower().replace("@", "").strip()

    # 1. Check negative attribution/greeting markers
    for n_pat in NON_COLLAB_MARKERS:
        full_n_pat = rf"{n_pat}\s*@?{re.escape(h_clean)}"
        if re.search(full_n_pat, t_lower):
            return False, f"REJECTED_NON_COLLAB_CONTEXT:{n_pat}"
        if re.search(rf"\b{n_pat}\b", t_lower) and not any(re.search(s_pat, t_lower) for s_pat in STRONG_COLLAB_MARKERS):
            return False, f"REJECTED_NON_COLLAB_CONTEXT:{n_pat}"

    # 2. Check strong collab markers
    for s_pat in STRONG_COLLAB_MARKERS:
        if re.search(s_pat, t_lower):
            return True, "STRONG_COLLAB_CONTEXT_VERIFIED"

    return False, "REJECTED_BARE_MENTION_OR_GENERIC_KEYWORD_ONLY"


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
    
    # Detector input: exact set of records with inspectable titles from root catalog
    if temp_has_titles:
        detector_input_df = temp_df[temp_df["title"].notna()].copy()
        detector_input_source = "data/temporal/catalog/video_catalog.parquet"
    else:
        # Temporal catalog lacks titles; detector evaluates auxiliary title-bearing catalog
        detector_input_df = catalog_df[catalog_df["title"].notna()].copy()
        detector_input_source = "data/video_catalog.parquet"

    root_title_catalog_records = len(catalog_df[catalog_df["title"].notna()])
    temporal_catalog_records = len(temp_df)
    temporal_title_overlap_records = int(temp_df["video_id"].isin(set(detector_input_df["video_id"])).sum())
    temporal_title_coverage_rate = temporal_title_overlap_records / temporal_catalog_records
    temporal_title_uncovered_records = temporal_catalog_records - temporal_title_overlap_records
    total_videos_scanned = len(detector_input_df)

    logger.info(
        f"Collab study: AUXILIARY TITLE-CATALOG COLLAB OBSERVATION. "
        f"Detector evaluated {total_videos_scanned} records from {detector_input_source} "
        f"({temporal_title_overlap_records} overlap with {temporal_catalog_records} temporal records; "
        f"{temporal_title_uncovered_records} temporal records uncovered)."
    )

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
        rejected_mentions = []

        identity_verification = "UNRESOLVED_HANDLE"
        collab_context_verification = "NONE"

        for m in mentions:
            ml = m.lower().strip()
            if ml in exact_handle_map:
                p_cid, p_name, p_ag = exact_handle_map[ml]
                if p_cid != host_cid:  # Disallow self-collab
                    identity_verification = "EXACT_HANDLE_MATCH"
                    is_collab, context_reason = verify_collab_context(title, f"@{m}")
                    collab_context_verification = context_reason
                    if is_collab:
                        exact_verified_participants.append((p_cid, p_name, p_ag, f"@{m}", context_reason))
                    else:
                        rejected_mentions.append(f"@{m}({context_reason})")
                else:
                    rejected_mentions.append(f"@{m}(SELF_REFERENCE)")
            else:
                unresolved_mentions.append(m)

        # Deduplicate participants
        distinct_verified = list({p[0]: p for p in exact_verified_participants}.values())

        if distinct_verified:
            verification_level = "EXACT_HANDLE_VERIFIED"
            audit_verdict = "PASSED_EXACT_HANDLE_AND_CONTEXT_VERIFICATION"
            audit_reason = (
                f"Identity: EXACT_HANDLE_MATCH {[p[3] for p in distinct_verified]}. "
                f"Context: STRONG_COLLAB_CONTEXT_VERIFIED."
            )
        elif identity_verification == "EXACT_HANDLE_MATCH":
            # Exact handle match, but failed collab context check
            verification_level = "CANDIDATE_UNRESOLVED"
            audit_verdict = "REJECTED_COLLAB_CONTEXT"
            audit_reason = f"Handle matched registry, but collab context check failed: {rejected_mentions}."
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
            "identity_verification": identity_verification if distinct_verified else ("EXACT_HANDLE_MATCH" if rejected_mentions else "UNRESOLVED_HANDLE"),
            "collab_context_verification": "STRONG_COLLAB_CONTEXT_VERIFIED" if distinct_verified else collab_context_verification,
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
            "identity_verification": candidate_record["identity_verification"],
            "collab_context_verification": candidate_record["collab_context_verification"],
            "verification_level": verification_level,
            "audit_verdict": audit_verdict,
            "resolved_participants": ";".join([f"{p[1]}({p[0]})" for p in distinct_verified]) if distinct_verified else "NONE",
            "audit_reason": audit_reason,
            "audited_at": retrieved_at
        })

        # Emit pairwise collab event records ONLY when BOTH handle resolves exactly AND strong context passes
        if distinct_verified:
            for p_cid, p_name, p_agency, p_mention, p_ctx in distinct_verified:
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
                    "identity_verification": "EXACT_HANDLE_MATCH",
                    "collab_context_verification": "STRONG_COLLAB_CONTEXT_VERIFIED",
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

    # Deterministic unflagged control sample (non-candidate videos from evaluated catalog)
    non_candidates = detector_input_df[~detector_input_df["video_id"].isin(set(candidates_df["video_id"]))].copy()
    controls_sampled = non_candidates.sample(n=min(len(non_candidates), 10), random_state=42).copy()
    controls_sampled["stratified_class"] = "NON_CANDIDATE_UNLABELED"
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

    # Separate candidate-video resolution count from pairwise event rows
    verified_pairwise_event_count = len(verified_df)
    candidate_video_count = len(candidates_df)
    verified_candidate_vids = set(candidates_df[candidates_df["verification_level"] == "EXACT_HANDLE_VERIFIED"]["video_id"])
    verified_candidate_video_count = len(verified_candidate_vids)
    candidate_video_resolution_rate = (verified_candidate_video_count / candidate_video_count) if candidate_video_count > 0 else 0.0

    validation_metrics = {
        "catalog_scan_type": "AUXILIARY TITLE-CATALOG COLLAB OBSERVATION",
        "collab_study_label": "AUXILIARY TITLE-CATALOG COLLAB OBSERVATION",
        "root_title_catalog_records": root_title_catalog_records,
        "temporal_catalog_records": temporal_catalog_records,
        "temporal_title_overlap_records": temporal_title_overlap_records,
        "temporal_title_coverage_rate": round(temporal_title_coverage_rate, 6),
        "temporal_title_uncovered_records": temporal_title_uncovered_records,
        "detector_input_records": total_videos_scanned,
        "detector_input_source": detector_input_source,
        "verified_pairwise_event_count": verified_pairwise_event_count,
        "candidate_video_count": candidate_video_count,
        "verified_candidate_video_count": verified_candidate_video_count,
        "candidate_video_resolution_rate": round(candidate_video_resolution_rate, 4),
        # Backward-compatible fields
        "temporal_catalog_total_records": temporal_catalog_records,
        "temporal_catalog_title_covered_records": temporal_title_overlap_records,
        "total_videos_scanned": total_videos_scanned,
        "detected_subset_label": "verified observed collaboration subset",
        "verified_collab_events_count": verified_pairwise_event_count,
        "candidate_videos_count": candidate_video_count,
        "exact_handle_resolution_rate": round(candidate_video_resolution_rate, 4),
        "description_queue_count": len(queue_df),
        "stratified_sample_size": len(val_sample),
        "sample_verified_in_sample": verified_in_sample,
        "sample_exact_handle_match_rate": round(sample_exact_match_rate, 4),
        "precision": "INSUFFICIENT_EVIDENCE",
        "precision_status": "INSUFFICIENT_EVIDENCE",
        "precision_limitation_rationale": (
            "Cannot compute precision without an independently labeled ground-truth collaboration dataset. "
            "Ratio of handle-verified candidate videos is an exact-handle match resolution rate, not empirical precision."
        ),
        "recall": "INSUFFICIENT_EVIDENCE",
        "recall_status": "INSUFFICIENT_EVIDENCE",
        "recall_limitation_rationale": (
            f"Cannot compute catalog-wide recall across {temporal_catalog_records} historical temporal records because "
            f"only {temporal_title_overlap_records} temporal records overlap with available title metadata "
            f"({root_title_catalog_records} records in auxiliary root catalog), leaving {temporal_title_uncovered_records} "
            "historical temporal records without inspectable title text. In addition, video descriptions remain unindexed, "
            "and unflagged streams lack ground-truth participant rosters. Stating completeness is scientifically invalid without full-catalog labels."
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

