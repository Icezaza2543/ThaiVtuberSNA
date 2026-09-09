"""
Regression tests for Research Integrity Hotfix:
1. Generic official profile != event-specific evidence
2. Secondary source cannot become strict primary evidence
3. Registered-company claim requires appropriate evidence (authoritative disclosure/registry)
4. Incomplete collab detector cannot claim completeness (catalog recall = INSUFFICIENT_EVIDENCE)
5. Public audience wording uses observed-interaction semantics (observed commenter/chat participant accounts)
"""

import json
import re
from pathlib import Path
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

AGENCY_EVENTS_PARQUET = REPO_ROOT / "data/industry/agency_events.parquet"
AGENCY_HISTORY_PARQUET = REPO_ROOT / "data/industry/agency_history.parquet"
CREATOR_EVENTS_PARQUET = REPO_ROOT / "data/industry/creator_status_events.parquet"
SOURCE_LEDGER_CSV = REPO_ROOT / "docs/research_v2/SOURCE_LEDGER.csv"
COLLAB_METRICS_JSON = REPO_ROOT / "data/industry/collab_validation_metrics.json"
OUTLOOK_HYPOTHESES_MD = REPO_ROOT / "docs/research_v2/OUTLOOK_HYPOTHESES.md"
RESEARCH_REPORT_MD = REPO_ROOT / "docs/research_v2/LONG_RUNNING_RESEARCH_REPORT.md"


def test_generic_official_profile_cannot_be_event_specific():
    """Rule 1: A URL like x.com/AgencyName or youtube.com/@AgencyName alone must NEVER become PRIMARY_EVENT_SPECIFIC."""
    # 1. Check agency_events
    if AGENCY_EVENTS_PARQUET.exists():
        df_agency = pd.read_parquet(AGENCY_EVENTS_PARQUET)
        for _, r in df_agency.iterrows():
            tier = r.get("evidence_tier", "")
            purl = str(r.get("primary_source_url", "")).strip()
            # If URL is a bare profile URL (no /status/ or /watch?v=), it must not be PRIMARY_EVENT_SPECIFIC
            if purl and purl != "nan":
                is_generic_profile = bool(re.search(r'^(https?://)?(www\.)?(x\.com|twitter\.com)/[A-Za-z0-9_]+/?$', purl)) or \
                                     bool(re.search(r'^(https?://)?(www\.)?youtube\.com/@[A-Za-z0-9_]+/?$', purl))
                if is_generic_profile:
                    assert tier != "PRIMARY_EVENT_SPECIFIC", (
                        f"Generic profile URL '{purl}' was incorrectly marked as PRIMARY_EVENT_SPECIFIC in agency event {r.get('event_id')}"
                    )

    # 2. Check creator_status_events
    if CREATOR_EVENTS_PARQUET.exists():
        df_creator = pd.read_parquet(CREATOR_EVENTS_PARQUET)
        for _, r in df_creator.iterrows():
            tier = r.get("evidence_tier", "")
            sref = str(r.get("source_reference", "")).strip()
            if sref and sref != "nan":
                is_generic_profile = bool(re.search(r'^(https?://)?(www\.)?(x\.com|twitter\.com)/[A-Za-z0-9_]+/?$', sref)) or \
                                     bool(re.search(r'^(https?://)?(www\.)?youtube\.com/@[A-Za-z0-9_]+/?$', sref))
                if is_generic_profile:
                    assert tier != "PRIMARY_EVENT_SPECIFIC", (
                        f"Generic profile URL '{sref}' was marked PRIMARY_EVENT_SPECIFIC in creator event {r.get('event_id')}"
                    )

    # 3. Check SOURCE_LEDGER.csv
    if SOURCE_LEDGER_CSV.exists():
        df_ledger = pd.read_csv(SOURCE_LEDGER_CSV)
        for _, r in df_ledger.iterrows():
            tier = r.get("verification_tier", "")
            url = str(r.get("source_url", "")).strip()
            is_generic_profile = bool(re.search(r'^(https?://)?(www\.)?(x\.com|twitter\.com)/[A-Za-z0-9_]+/?$', url)) or \
                                 bool(re.search(r'^(https?://)?(www\.)?youtube\.com/@[A-Za-z0-9_]+/?$', url))
            if is_generic_profile:
                assert tier != "PRIMARY_EVENT_SPECIFIC", (
                    f"Generic profile URL '{url}' marked PRIMARY_EVENT_SPECIFIC in source ledger (ID: {r.get('source_id')})"
                )
                assert tier == "PRIMARY_ENTITY_GENERAL", (
                    f"Generic profile URL '{url}' must be PRIMARY_ENTITY_GENERAL in source ledger, got '{tier}'"
                )


def test_secondary_source_cannot_become_strict_primary():
    """Rule 2: Secondary source (Fandom/wiki) alone must NEVER become PRIMARY_EVENT_SPECIFIC."""
    assert CREATOR_EVENTS_PARQUET.exists(), "creator_status_events.parquet must exist"
    df_creator = pd.read_parquet(CREATOR_EVENTS_PARQUET)
    
    for _, r in df_creator.iterrows():
        tier = r.get("evidence_tier", "")
        sref = str(r.get("source_reference", "")).lower()
        stype = str(r.get("source_type", ""))
        
        # If the cited source is only Fandom/wiki without a primary status URL
        if "fandom.com" in sref and not ("status/" in sref or "twitter.com" in sref):
            assert tier != "PRIMARY_EVENT_SPECIFIC", (
                f"Secondary Fandom source '{sref}' was improperly elevated to PRIMARY_EVENT_SPECIFIC in event {r.get('event_id')}"
            )
            assert tier == "SECONDARY_DOCUMENTED", (
                f"Secondary Fandom source '{sref}' must be SECONDARY_DOCUMENTED, got '{tier}'"
            )


def test_registered_company_claim_requires_appropriate_evidence():
    """Rule 3: Do not call an organization a 'registered corporate entity' unless supported by authoritative disclosure or registry."""
    assert AGENCY_HISTORY_PARQUET.exists(), "agency_history.parquet must exist"
    df_agency = pd.read_parquet(AGENCY_HISTORY_PARQUET)
    
    assert "corporate_entity_status" in df_agency.columns
    assert "corporate_registration_status" in df_agency.columns
    
    for _, r in df_agency.iterrows():
        aname = r["agency_name"]
        reg_status = r["corporate_registration_status"]
        ent_status = r["corporate_entity_status"]
        
        if reg_status == "CORPORATE_DISCLOSURE_VERIFIED":
            # Only agencies with verifiable public corporate parent disclosures are allowed
            assert ent_status == "AUTHORITATIVE_CORPORATE_DISCLOSURE", (
                f"Agency {aname} has verified corporate registration without AUTHORITATIVE_CORPORATE_DISCLOSURE"
            )
            assert aname in ["AStars Production", "WACTOR"], (
                f"Unexpected agency {aname} marked CORPORATE_DISCLOSURE_VERIFIED without registry documentation"
            )
        else:
            # All other agencies must remain unverified corporate registration (or NOT_APPLICABLE for Independent)
            assert reg_status in ["CORPORATE_REGISTRATION_UNVERIFIED", "NOT_APPLICABLE"], (
                f"Agency {aname} must be CORPORATE_REGISTRATION_UNVERIFIED or NOT_APPLICABLE, got {reg_status}"
            )
            assert ent_status in ["OFFICIAL_BRAND_ENTITY", "INDEPENDENT_COLLECTIVE", "UNKNOWN"], (
                f"Agency {aname} must be OFFICIAL_BRAND_ENTITY or INDEPENDENT_COLLECTIVE, got {ent_status}"
            )


def test_incomplete_collab_detector_cannot_claim_completeness():
    """Rule 4: Full catalog scan must NOT claim complete collaboration network; recall must be INSUFFICIENT_EVIDENCE."""
    assert COLLAB_METRICS_JSON.exists(), "collab_validation_metrics.json must exist"
    with open(COLLAB_METRICS_JSON, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    
    # 1. Scan must be called 'full historical catalog scan'
    assert metrics.get("catalog_scan_type") == "full historical catalog scan"
    
    # 2. Detected subset must be called 'verified observed collaboration subset'
    assert metrics.get("detected_subset_label") == "verified observed collaboration subset"
    
    # 3. Completeness claim forbidden
    assert metrics.get("forbidden_claim_audit", {}).get("complete_collaboration_network") is False
    
    # 4. Recall must be explicitly INSUFFICIENT_EVIDENCE
    assert metrics.get("catalog_wide_recall") == "INSUFFICIENT_EVIDENCE"
    assert metrics.get("recall_status") == "INSUFFICIENT_EVIDENCE"


def test_public_audience_wording_uses_observed_interaction_semantics():
    """Rule 5: Audience findings must refer to 'observed commenter/chat participant accounts', never total population or all viewers."""
    assert OUTLOOK_HYPOTHESES_MD.exists(), "OUTLOOK_HYPOTHESES.md must exist"
    text = OUTLOOK_HYPOTHESES_MD.read_text(encoding="utf-8")
    
    # Disallow unqualified population overclaims in outlook report prose
    assert "every audience finding refers strictly to **\"observed commenter/chat participant accounts\"**" in text.lower()
    assert "demographic ceiling" in text.lower()
    
    # Demographic ceiling must be downgraded to HYPOTHESIS and require external evidence
    assert "[HYPOTHESIS]" in text
    assert "EXTERNAL_EVIDENCE_REQUIRED" in text
    assert "demographic ceiling" in text.lower() and "requires external" in text.lower()
    
    # Disallow claiming passive viewership observation
    assert "observed interaction" in text.lower() and "watching" in text.lower()
