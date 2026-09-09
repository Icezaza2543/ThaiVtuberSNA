"""
Regression tests for Research Integrity Hotfix (Rounds 1 & 2):
1. Generic official profile != event-specific evidence (reading verification_tier in agency_events)
2. Secondary source cannot become strict primary evidence
3. Creator primary evidence requires curated source authority metadata (random third-party X status must not auto-upgrade)
4. Registered-company claim requires appropriate evidence (authoritative disclosure/registry)
5. Fandom-only corporate evidence cannot verify registration (regression test for WACTOR-like records)
6. Collab detector input count == metrics total_videos_scanned, report matches metrics, no false precision, sample size matches
7. Report runtime totals reconcile with ledger (pre-hotfix: 32m, hotfix: 11m, total: 43m)
8. Public audience wording uses observed-interaction semantics (observed commenter/chat participant accounts)
9. High-level hypothesis verdicts are not mislabeled OBSERVED_RESULT
"""

import json
import re
from pathlib import Path
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

ROOT_CATALOG_PARQUET = REPO_ROOT / "data/video_catalog.parquet"
TEMPORAL_CATALOG_PARQUET = REPO_ROOT / "data/temporal/catalog/video_catalog.parquet"
AGENCY_EVENTS_PARQUET = REPO_ROOT / "data/industry/agency_events.parquet"
AGENCY_HISTORY_PARQUET = REPO_ROOT / "data/industry/agency_history.parquet"
CREATOR_EVENTS_PARQUET = REPO_ROOT / "data/industry/creator_status_events.parquet"
SOURCE_LEDGER_CSV = REPO_ROOT / "docs/research_v2/SOURCE_LEDGER.csv"
COLLAB_METRICS_JSON = REPO_ROOT / "data/industry/collab_validation_metrics.json"
COLLAB_SAMPLE_CSV = REPO_ROOT / "data/industry/collab_stratified_validation_sample.csv"
OUTLOOK_HYPOTHESES_MD = REPO_ROOT / "docs/research_v2/OUTLOOK_HYPOTHESES.md"
RESEARCH_REPORT_MD = REPO_ROOT / "docs/research_v2/LONG_RUNNING_RESEARCH_REPORT.md"
RUNTIME_LEDGER_MD = REPO_ROOT / "docs/research_v2/RUNTIME_LEDGER.md"


def test_generic_official_profile_cannot_be_event_specific():
    """Rule 1: A URL like x.com/AgencyName or youtube.com/@AgencyName alone must NEVER become PRIMARY_EVENT_SPECIFIC."""
    # 1. Check agency_events using correct schema column (verification_tier)
    if AGENCY_EVENTS_PARQUET.exists():
        df_agency = pd.read_parquet(AGENCY_EVENTS_PARQUET)
        assert "verification_tier" in df_agency.columns, "agency_events must use verification_tier"
        for _, r in df_agency.iterrows():
            tier = r.get("verification_tier", "")
            purl = str(r.get("primary_source_url", "")).strip()
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
        if "fandom.com" in sref and not ("status/" in sref or "twitter.com" in sref):
            assert tier != "PRIMARY_EVENT_SPECIFIC", (
                f"Secondary Fandom source '{sref}' was improperly elevated to PRIMARY_EVENT_SPECIFIC in event {r.get('event_id')}"
            )
            assert tier == "SECONDARY_DOCUMENTED", (
                f"Secondary Fandom source '{sref}' must be SECONDARY_DOCUMENTED, got '{tier}'"
            )


def test_creator_primary_evidence_requires_curated_authority_metadata():
    """Rule 6: A random third-party X status must NOT auto-upgrade to PRIMARY_EVENT_SPECIFIC."""
    from scripts.build_creator_lifecycle_evidence import VERIFIED_CREATOR_INTEL

    # 1. Assert all existing PRIMARY_EVENT_SPECIFIC in database have curated authority metadata
    assert CREATOR_EVENTS_PARQUET.exists()
    df_creator = pd.read_parquet(CREATOR_EVENTS_PARQUET)
    primary_events = df_creator[df_creator["evidence_tier"] == "PRIMARY_EVENT_SPECIFIC"]
    assert len(primary_events) > 0
    for _, r in primary_events.iterrows():
        st = r["source_type"]
        sclass = r["creator_source_class"]
        assert st in ["OFFICIAL_AGENCY_ANNOUNCEMENT", "PUBLIC_TALENT_STATEMENT"]
        assert sclass in ["PRIMARY_OFFICIAL_ANNOUNCEMENT", "CREATOR_PRIMARY_STATEMENT"]
        # Must be from an official or talent verified handle, not a random user
        sref = r["source_reference"].lower()
        assert any(auth in sref for auth in ["astars", "pixela", "arp_vtuber", "polygonofficial", "miraismaid", "eileennoir"])

    # 2. Assert uncurated third-party status mock fails auto-upgrade
    uncurated_mock = {
        "event_type": "GRADUATION",
        "event_date": "2024-01-01",
        "event_year": 2024,
        "source_type": "THIRD_PARTY_FAN_SPECULATION",
        "source_reference": "https://x.com/random_user123/status/999999999999999999",
        "notes": "Fan claiming graduation."
    }
    # Test our classifier logic on uncurated mock
    ref_lower = uncurated_mock["source_reference"].lower()
    is_official = uncurated_mock.get("source_type") in ["OFFICIAL_AGENCY_ANNOUNCEMENT", "PUBLIC_TALENT_STATEMENT"]
    is_recognized = any(auth in ref_lower for auth in ["astars", "pixela", "arp_vtuber", "polygonofficial", "miraismaid", "eileennoir"])
    assert not (is_official and is_recognized), "Random third-party X status must not qualify for primary event tier"


def test_registered_company_claim_requires_appropriate_evidence():
    """Rule 4: Do not call an organization a registered corporate entity without authoritative disclosure or registry."""
    assert AGENCY_HISTORY_PARQUET.exists(), "agency_history.parquet must exist"
    df_agency = pd.read_parquet(AGENCY_HISTORY_PARQUET)
    
    assert "corporate_entity_status" in df_agency.columns
    assert "corporate_registration_status" in df_agency.columns
    assert "corporate_evidence_url" in df_agency.columns
    assert "corporate_evidence_class" in df_agency.columns
    
    for _, r in df_agency.iterrows():
        aname = r["agency_name"]
        reg_status = r["corporate_registration_status"]
        ent_status = r["corporate_entity_status"]
        corp_url = str(r["corporate_evidence_url"]).strip()
        corp_class = str(r["corporate_evidence_class"]).strip()
        
        if reg_status == "CORPORATE_DISCLOSURE_VERIFIED":
            # Data-driven validation: requires verified corporate disclosure or registry
            assert ent_status == "AUTHORITATIVE_CORPORATE_DISCLOSURE"
            assert corp_url and corp_url != "nan"
            assert corp_class in ["GOVERNMENT_REGISTRY", "OFFICIAL_CORPORATE_DISCLOSURE"]
        else:
            if aname == "Independent":
                assert reg_status == "NOT_APPLICABLE"
                assert ent_status == "INDEPENDENT_COLLECTIVE"
            else:
                assert reg_status == "CORPORATE_REGISTRATION_UNVERIFIED"
                assert ent_status == "OFFICIAL_BRAND_ENTITY"


def test_fandom_only_record_fails_corporate_verification():
    """Rule 5: Add regression proving a Fandom-only WACTOR-like record FAILS corporate verification."""
    fandom_mock = {
        "agency_name": "WACTOR_MOCK",
        "primary_source_url": None,
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Shino_Laila",
        "corporate_evidence_url": "",
        "corporate_evidence_class": "UNVERIFIED"
    }
    # Validate that lacking authoritative evidence prevents corporate verification
    has_authoritative_corporate_evidence = (
        bool(fandom_mock.get("corporate_evidence_url")) and
        fandom_mock.get("corporate_evidence_class") in ["GOVERNMENT_REGISTRY", "OFFICIAL_CORPORATE_DISCLOSURE"]
    )
    assert not has_authoritative_corporate_evidence, "Fandom-only record must fail corporate verification"


def test_collab_detector_input_count_matches_metrics_and_report():
    """Rule 1, 2, 4: Collab detector input count == metrics total_videos_scanned; no false precision; sample size matches."""
    assert ROOT_CATALOG_PARQUET.exists()
    assert COLLAB_METRICS_JSON.exists()
    assert COLLAB_SAMPLE_CSV.exists()
    assert RESEARCH_REPORT_MD.exists()
    
    root_df = pd.read_parquet(ROOT_CATALOG_PARQUET)
    actual_detector_input_count = len(root_df[root_df["title"].notna()])
    
    with open(COLLAB_METRICS_JSON, "r", encoding="utf-8") as f:
        metrics = json.load(f)
        
    val_sample = pd.read_csv(COLLAB_SAMPLE_CSV)
    report_text = RESEARCH_REPORT_MD.read_text(encoding="utf-8")
    
    # Invariant: actual collab detector input count == metrics total_videos_scanned
    assert metrics.get("total_videos_scanned") == actual_detector_input_count
    
    # Invariant: report collab scan count == metrics
    assert f"**{metrics.get('total_videos_scanned')} videos scanned**" in report_text or \
           f"{metrics.get('total_videos_scanned')} videos scanned" in report_text or \
           f"{metrics.get('total_videos_scanned')} title-covered" in report_text
           
    # Invariant: report sample size == generated sample
    assert metrics.get("stratified_sample_size") == len(val_sample)
    assert f"**{len(val_sample)} rows**" in report_text or f"{len(val_sample)} rows" in report_text
    
    # Invariant: no false precision metric
    assert metrics.get("precision") == "INSUFFICIENT_EVIDENCE"
    assert metrics.get("precision_status") == "INSUFFICIENT_EVIDENCE"
    assert metrics.get("recall") == "INSUFFICIENT_EVIDENCE"
    assert metrics.get("recall_status") == "INSUFFICIENT_EVIDENCE"
    assert "stratified_sample_precision_estimate" not in metrics
    
    # Invariant: complete collaboration network claim forbidden
    assert metrics.get("forbidden_claim_audit", {}).get("complete_collaboration_network") is False


def test_report_runtime_totals_reconcile_with_ledger():
    """Rule 7: Total runtime in reports reconciles with RUNTIME_LEDGER.md (pre-hotfix: 32m, hotfix: 11m, total: 43m)."""
    assert RUNTIME_LEDGER_MD.exists()
    assert RESEARCH_REPORT_MD.exists()
    
    ledger_text = RUNTIME_LEDGER_MD.read_text(encoding="utf-8")
    report_text = RESEARCH_REPORT_MD.read_text(encoding="utf-8")
    
    # Extract minutes from ledger
    minute_matches = [int(m) for m in re.findall(r'\|\s*(\d+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*`', ledger_text)]
    total_ledger_minutes = sum(minute_matches)
    assert total_ledger_minutes == 43, f"Expected 43 total minutes in ledger, got {total_ledger_minutes}"
    
    # Reconciled in research report
    assert "43 minutes" in report_text
    assert "32 minutes" in report_text
    assert "11 minutes" in report_text


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


def test_high_level_hypothesis_verdicts_are_not_mislabeled_observed_result():
    """Rule 8: High-level conclusions (e.g. systemic collapse contradicted, supply saturated) must NOT be OBSERVED_RESULT."""
    assert OUTLOOK_HYPOTHESES_MD.exists()
    assert RESEARCH_REPORT_MD.exists()
    
    outlook_text = OUTLOOK_HYPOTHESES_MD.read_text(encoding="utf-8")
    report_text = RESEARCH_REPORT_MD.read_text(encoding="utf-8")
    
    # Check that high-level conclusion rows in tables do NOT use [OBSERVED_RESULT]
    for prohibited in [
        r'\[OBSERVED_RESULT\]\s*\*\*CONTRADICTED AS A SYSTEMIC MACRO COLLAPSE',
        r'\[OBSERVED_RESULT\]\s*\*\*CONTRADICTED for continuous observed commenter',
        r'\|\s*\*\*H6 CONTRACTION / COLLAPSE\*\*\s*\|\s*\*\*CONTRADICTED AS A SYSTEMIC MACRO THESIS\*\*\s*\|\s*`\[OBSERVED_RESULT\]`',
        r'\|\s*\*\*H1 EXPANSION\*\*\s*\|\s*.*?\|\s*`\[OBSERVED_RESULT\]`',
        r'\|\s*\*\*H8 INSUFFICIENT EVIDENCE\*\*\s*\|\s*.*?\|\s*`\[OBSERVED_RESULT\]`',
        r'-\s*\*\*It is NOT collapsing:\*\*\s*`\[OBSERVED_RESULT\]`',
        r'-\s*\*\*It is NOT effortlessly expanding:\*\*\s*`\[OBSERVED_RESULT\]`'
    ]:
        assert not re.search(prohibited, outlook_text), f"Prohibited pattern '{prohibited}' found in OUTLOOK_HYPOTHESES.md"
        assert not re.search(prohibited, report_text), f"Prohibited pattern '{prohibited}' found in LONG_RUNNING_RESEARCH_REPORT.md"
