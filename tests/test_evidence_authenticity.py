#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Source Authenticity & Empirical Data Integrity in Research v2:
- Fails on invalid/pseudo YouTube video IDs for VERIFIED records.
- Fails on pseudo source references (e.g. invented slug schemes).
- Fails on generic homepage used as sole evidence for a specific number.
- Fails on hardcoded monetary aggregates (e.g. 12,500,000 THB floor).
- Fails on can_be_summed=False records being summed into a floor.
- Fails on target cohort denominator inconsistency (must match 193 target universe).
- Fails on unsupported/promotional terms ('loyalty', 'แฟนพันธุ์แท้', 'กลับมาชมซ้ำ', 'industry is NOT dying').
- Fails on forced outlook fallback (must fail closed to INSUFFICIENT_EVIDENCE when gates fail).
- Fails on conclusion without valid evidence artifact.
"""

import json
import re
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent

COLLAB_PARQUET = ROOT / "data/industry/collab_events.parquet"
COLLAB_QUARANTINE_CSV = ROOT / "data/industry/quarantine/collab_events_unverified.csv"
CREATOR_EVENTS_PARQUET = ROOT / "data/industry/creator_status_events.parquet"
MARKET_PARQUET = ROOT / "data/market/market_evidence.parquet"
SOURCE_REGISTRY_CSV = ROOT / "data/market/source_registry.csv"
OUTLOOK_PARQUET = ROOT / "data/industry/outlook_indicators.parquet"
OUTLOOK_MD = ROOT / "docs/research_v2/OUTLOOK_MODEL.md"
CONTRACT_JSON = ROOT / "web/research/data/research_v2.json"
TARGET_MANIFEST_CSV = ROOT / "data/temporal/catalog/target_manifest.csv"

YT_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')

def test_no_invalid_video_ids_in_verified_collabs():
    """All VERIFIED collab events must have a syntactically valid 11-char YouTube ID."""
    if not COLLAB_PARQUET.exists():
        pytest.skip("collab_events.parquet does not exist.")
    df = pd.read_parquet(COLLAB_PARQUET)
    verified = df[df.get("verification_status", pd.Series()) == "VERIFIED"]
    for idx, r in verified.iterrows():
        vid = str(r.get("video_id", "")).strip()
        assert YT_ID_PATTERN.match(vid), f"VERIFIED collab has invalid video ID '{vid}' at event {r.get('event_id')}"

def test_pseudo_collabs_quarantined_with_reasons():
    """Any quarantined collab event must carry a recognized reason."""
    assert COLLAB_QUARANTINE_CSV.exists(), "Collab quarantine file missing."
    q_df = pd.read_csv(COLLAB_QUARANTINE_CSV)
    assert len(q_df) > 0, "Expected quarantined collab events."
    valid_reasons = ["INVALID_VIDEO_ID", "SOURCE_NOT_RESOLVABLE", "PARTICIPANT_NOT_VERIFIED", "DATE_NOT_VERIFIED", "TITLE_NOT_VERIFIED", "OTHER"]
    for idx, r in q_df.iterrows():
        assert r["reason"] in valid_reasons, f"Invalid quarantine reason '{r['reason']}' for event {r.get('event_id')}"

def test_no_pseudo_source_references_in_creator_verified():
    """VERIFIED creator status events must not use synthetic unresolvable references."""
    df = pd.read_parquet(CREATOR_EVENTS_PARQUET)
    verified = df[df["verification_status"] == "VERIFIED"]
    for idx, r in verified.iterrows():
        src = str(r["source_reference"])
        assert not src.startswith("channel_metadata:title_has_"), f"Title audit without exact date cannot be VERIFIED: {src}"
        assert not "graduation_stream_narelle" in src, f"Synthesized slug in VERIFIED: {src}"

def test_market_evidence_specific_urls():
    """Sources in market registry must use specific verifiable URLs, not generic homepages."""
    src_df = pd.read_csv(SOURCE_REGISTRY_CSV)
    for idx, r in src_df.iterrows():
        url = str(r["source_url"]).strip()
        assert url.startswith("http"), f"Source URL must be valid HTTP(S): {url}"
        # Disallow bare homepages when specific deep paths are required
        assert url not in ["https://www.youtube.com", "https://youtube.com", "https://www.ticketmelon.com"], f"Generic homepage as source URL: {url}"

def test_no_hardcoded_monetization_summation_in_outlook():
    """Outlook must not hardcode 12.5M or 8.5M THB or sum can_be_summed=False records."""
    raw_md = OUTLOOK_MD.read_text(encoding="utf-8")
    assert "12,500,000" not in raw_md
    assert "8,500,000" not in raw_md
    
    ind_df = pd.read_parquet(OUTLOOK_PARQUET)
    mkt_ind = ind_df[ind_df["dimension"] == "MONETIZATION_EVIDENCE"]
    assert not mkt_ind.empty
    val = mkt_ind.iloc[0]["value"]
    assert val is None or pd.isna(val), f"Monetization evidence value must be None/unsummed, got {val}"

def test_cannot_sum_market_records_enforced():
    """All current unit price records must have can_be_summed=False."""
    df = pd.read_parquet(MARKET_PARQUET)
    assert not df["can_be_summed"].any(), "Found records marked can_be_summed=True when sales volumes are private."

def test_target_cohort_denominator_consistency():
    """Target cohort denominator must be 193 (the frozen target manifest size)."""
    manifest_df = pd.read_csv(TARGET_MANIFEST_CSV)
    target_len = len(manifest_df)
    assert target_len == 193
    
    contract = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    assert contract["coverage"]["target_cohort"] == 193
    assert contract["coverage"]["target_cohort_universe"] == 193
    assert contract["creator_ecosystem"]["target_cohort_total"] == 193

def test_no_unsupported_promotional_terms_in_public_research():
    """Public research outputs must not contain promotional or subjective narrative claims."""
    forbidden = ["แฟนพันธุ์แท้", "กลับมาชมซ้ำ", "market discipline", "natural market cycle", "resilient cultural niche", "industry is not dying", "loyalty"]
    
    contract_text = CONTRACT_JSON.read_text(encoding="utf-8").lower()
    for term in forbidden:
        assert term.lower() not in contract_text, f"Forbidden narrative term found in research contract: '{term}'"

def test_outlook_fails_closed_when_evidence_incomplete():
    """Outlook model classification must fail closed to INSUFFICIENT_EVIDENCE when monetization disclosures are absent."""
    contract = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    assert contract["outlook"]["verdict"] == "INSUFFICIENT_EVIDENCE"

def test_conclusions_have_source_artifacts():
    """All findings in research contract must specify an existing source artifact."""
    contract = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    pulse = contract["industry_pulse"]
    for dim in ["creators", "audience", "network", "market"]:
        finding = pulse[dim]
        art = finding["source_artifact"]
        assert art, f"Missing source artifact in pulse {dim}"
