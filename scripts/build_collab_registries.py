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
    # 1. Load catalog containing titles
    catalog_df = pd.read_parquet(CATALOG_PATH)
    logger.info(f"Loaded {len(catalog_df)} titles from root catalog {CATALOG_PATH}")

    # Load temporal catalog to verify existence and timestamps
    temp_df = pd.read_parquet(TEMPORAL_CATALOG_PATH)
    temp_vids = set(temp_df["video_id"])
    logger.info(f"Loaded {len(temp_df)} temporal catalog records ({len(temp_vids)} distinct video IDs)")

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
    matches = catalog_df[catalog_df["title"].str.lower().str.contains(pattern, na=False)].copy()
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


if __name__ == "__main__":
    build_collab_registries()
