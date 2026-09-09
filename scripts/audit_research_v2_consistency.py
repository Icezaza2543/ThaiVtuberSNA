#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Research v2 Cross-Artifact Consistency Audit

Validates that canonical metrics from source DataFrames match across:
- web/research/data/research_v2.json
- docs/research_v2/OUTLOOK_MODEL.md
- docs/research_v2/OUTLOOK_HYPOTHESES.md
- docs/research_v2/LONG_RUNNING_RESEARCH_REPORT.md

Enforces:
- No mislabeled metrics (videos vs observed_interactions)
- No stale yearly numbers (e.g. 164/160 active channel sequence, 9,218 YTD accounts, 1,927 returning, 874 reactivations)
- Strict graduation evidence tier taxonomy (primary verified vs secondary documented vs proxy)
- Strict agency-at-selection terminology (no bare 'agency assortativity' or 'within-agency')
- Single writer invariant for creator_status_events.*
- Collab verification semantics (exact handle match + strong collab context marker)
"""

import sys
import json
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def audit_single_canonical_writer():
    print("Checking Single Canonical Writer Invariant...")
    ecosystem_script = ROOT / "scripts/build_creator_ecosystem_data.py"
    lifecycle_script = ROOT / "scripts/build_creator_lifecycle_evidence.py"
    
    eco_code = ecosystem_script.read_text(encoding="utf-8")
    life_code = lifecycle_script.read_text(encoding="utf-8")
    
    # build_creator_ecosystem_data.py must NOT write creator_status_events
    if "creator_status_events.parquet" in eco_code and ("to_parquet" in eco_code and "creator_status_events" in eco_code.split("to_parquet")[1][:100]):
        raise AssertionError("build_creator_ecosystem_data.py contains write logic for creator_status_events.parquet!")
    if "creator_status_events.csv" in eco_code and ("to_csv" in eco_code and "creator_status_events" in eco_code.split("to_csv")[1][:100]):
        raise AssertionError("build_creator_ecosystem_data.py contains write logic for creator_status_events.csv!")
        
    # build_creator_lifecycle_evidence.py must be the canonical writer
    assert "creator_status_events.parquet" in life_code and "to_parquet" in life_code, (
        "build_creator_lifecycle_evidence.py is missing parquet writer logic!"
    )
    print("  [PASS] Single canonical writer for creator lifecycle verified.")


def audit_research_v2_json():
    print("Auditing web/research/data/research_v2.json...")
    json_path = ROOT / "web/research/data/research_v2.json"
    assert json_path.exists(), f"Missing {json_path}"
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Load canonical source artifacts
    eco_df = pd.read_parquet(ROOT / "data/temporal/ecosystem/yearly_ecosystem_metrics.parquet")
    net_df = pd.read_parquet(ROOT / "data/temporal/analysis/yearly_network_metrics.parquet")
    aud_df = pd.read_parquet(ROOT / "data/industry/audience_behavior_yearly.parquet")
    vid_cat_df = pd.read_parquet(ROOT / "data/temporal/catalog/video_catalog.parquet")
    evt_df = pd.read_parquet(ROOT / "data/industry/creator_status_events.parquet")
    with open(ROOT / "data/thai_vtuber_registry.json", "r", encoding="utf-8") as f:
        reg_data = json.load(f)

    # 1. Registered channels dynamic check
    assert data["coverage"]["registered_channels"] == len(reg_data), (
        f"registered_channels mismatch: {data['coverage']['registered_channels']} vs {len(reg_data)}"
    )

    # 2. Yearly coverage chart: videos vs interactions
    cov_chart = data["coverage"]["yearly_coverage_chart"]
    vid_years = vid_cat_df["video_published_at"].astype(str).str[:4]
    
    for item in cov_chart:
        yr = item["year"]
        canonical_vids = int((vid_years == str(yr)).sum())
        canonical_inter = int(net_df[net_df["year"] == float(yr)].iloc[0]["total_observed_interactions"])
        
        # Invariant: videos must equal canonical distinct video catalog count
        assert item["videos"] == canonical_vids, (
            f"Year {yr}: 'videos' {item['videos']} != canonical catalog videos {canonical_vids}"
        )
        # Invariant: observed_interactions must equal canonical interactions
        assert item["observed_interactions"] == canonical_inter, (
            f"Year {yr}: 'observed_interactions' {item['observed_interactions']} != canonical interactions {canonical_inter}"
        )
        # Invariant: videos != observed_interactions (not mislabeled)
        assert item["videos"] != item["observed_interactions"], (
            f"Year {yr}: 'videos' is identically labeled as 'observed_interactions' ({item['videos']})!"
        )

    # 3. Creator ecosystem graduation tiers
    ce = data["creator_ecosystem"]
    primary_grads = len(evt_df[
        (evt_df["event_type"].isin(["GRADUATION", "GRADUATION_OR_DEPARTURE"])) &
        (evt_df["evidence_tier"] == "PRIMARY_EVENT_SPECIFIC")
    ])
    sec_grads = len(evt_df[
        (evt_df["event_type"].isin(["GRADUATION", "GRADUATION_OR_DEPARTURE"])) &
        (evt_df["evidence_tier"] == "SECONDARY_DOCUMENTED")
    ])
    proxy_grads = len(evt_df[
        (evt_df["event_type"].str.contains("GRADUATION")) &
        (evt_df["evidence_tier"].isin(["INFERRED_PROXY", "PROXIMAL_COMMUNITY_PROXY"]))
    ])
    
    assert ce["verified_graduations"] == primary_grads, (
        f"verified_graduations mismatch: {ce['verified_graduations']} vs {primary_grads}"
    )
    assert ce["primary_verified_graduations"] == primary_grads, (
        f"primary_verified_graduations mismatch: {ce['primary_verified_graduations']} vs {primary_grads}"
    )
    assert ce["secondary_documented_graduations"] == sec_grads, (
        f"secondary_documented_graduations mismatch: {ce['secondary_documented_graduations']} vs {sec_grads}"
    )
    assert ce["proxy_graduation_boundaries"] == proxy_grads, (
        f"proxy_graduation_boundaries mismatch: {ce['proxy_graduation_boundaries']} vs {proxy_grads}"
    )
    print("  [PASS] web/research/data/research_v2.json public contract verified.")


def audit_outlook_model():
    print("Auditing docs/research_v2/OUTLOOK_MODEL.md...")
    md_path = ROOT / "docs/research_v2/OUTLOOK_MODEL.md"
    assert md_path.exists(), f"Missing {md_path}"
    content = md_path.read_text(encoding="utf-8")
    
    # Load canonical source DataFrames
    eco_df = pd.read_parquet(ROOT / "data/temporal/ecosystem/yearly_ecosystem_metrics.parquet")
    aud_df = pd.read_parquet(ROOT / "data/industry/audience_behavior_yearly.parquet")
    
    eco_2025 = eco_df[eco_df["year"] == 2025].iloc[0]
    aud_2021 = aud_df[aud_df["year"] == 2021].iloc[0]
    aud_2025 = aud_df[aud_df["year"] == 2025].iloc[0]
    
    # 1. Check for absence of stale hardcoded prose percentages
    stale_patterns = ["58.7%", "15.3%", "41.3%", "84.7%"]
    for sp in stale_patterns:
        assert sp not in content, f"Stale percentage '{sp}' found in OUTLOOK_MODEL.md!"
        
    # 2. Check presence of dynamically derived values
    re_obs_2025_str = f"{aud_2025['pct_re_observed']:.1f}%"
    re_obs_2021_str = f"{aud_2021['pct_re_observed']:.1f}%"
    assert re_obs_2025_str in content, f"Expected {re_obs_2025_str} in OUTLOOK_MODEL.md"
    assert re_obs_2021_str in content, f"Expected {re_obs_2021_str} in OUTLOOK_MODEL.md"
    
    # 3. Test 2 Modality Sensitivity must be INSUFFICIENT_EVIDENCE
    assert "- **Test 2: Modality Sensitivity**: **INSUFFICIENT_EVIDENCE**" in content, (
        "Test 2 Modality Sensitivity in OUTLOOK_MODEL.md is not downgraded to INSUFFICIENT_EVIDENCE!"
    )
    
    # 4. Exit pressure in scorecard must not include proxies (2024: 0.00, 2025: 6.00)
    events = pd.read_parquet(ROOT / "data/industry/creator_status_events.parquet")
    counts = [len(events[(events.event_year == year) & (events.evidence_tier == "PRIMARY_EVENT_SPECIFIC") & events.event_type.isin(["GRADUATION", "GRADUATION_OR_DEPARTURE"])]) for year in (2024, 2025)]
    assert f"| **`EXIT_PRESSURE`** | `primary_verified_graduations` | `{counts[0]:.2f}` | `{counts[1]:.2f}` |" in content
    print("  [PASS] docs/research_v2/OUTLOOK_MODEL.md verified.")


def audit_outlook_hypotheses():
    print("Auditing docs/research_v2/OUTLOOK_HYPOTHESES.md...")
    md_path = ROOT / "docs/research_v2/OUTLOOK_HYPOTHESES.md"
    assert md_path.exists(), f"Missing {md_path}"
    content = md_path.read_text(encoding="utf-8")
    
    # 1. Check for stale active-channel sequences
    stale_sequences = ["107 to 164", "164 to 160", "9,218", "1,927 / 9,218", "874 accounts"]
    for seq in stale_sequences:
        assert seq not in content, f"Stale sequence '{seq}' found in OUTLOOK_HYPOTHESES.md!"
        
    # 2. Check canonical active-channel sequence
    assert "92 to 129" in content, "Canonical active-channel growth 92 to 129 missing in Period 1"
    assert "129 to 157" in content, "Canonical active-channel growth 129 to 157 missing in Period 2"
    assert "157 to 166" in content, "Canonical active-channel growth 157 to 166 missing in Period 3"
    assert "160 (as of September 2026 YTD)" in content, "Canonical 2026 YTD active-channel count 160 missing"
    
    # 3. Check canonical audience figures
    assert "13,259 accounts" in content, "Canonical 2026 YTD population 13,259 missing"
    assert "2,773 / 13,259" in content, "Canonical 2026 YTD returning accounts 2,773 missing"
    assert "826 reactivated accounts" in content, "Canonical 2026 YTD reactivated accounts 826 missing"
    
    # 4. Check agency wording: must use 'agency-at-selection'
    bare_assort = re.findall(r"(?<!agency-at-selection\s)(?<!intra-)agency\s+assortativity", content, re.IGNORECASE)
    assert not bare_assort, f"Bare 'agency assortativity' without agency-at-selection qualifier found: {bare_assort}"
    
    assert "within-agency" not in content.lower(), "Historical wording 'within-agency' found in OUTLOOK_HYPOTHESES.md!"
    assert "agency-at-selection assortativity" in content.lower(), "agency-at-selection assortativity not found"
    assert "agency-at-selection mixing" in content.lower(), "agency-at-selection mixing not found"
    print("  [PASS] docs/research_v2/OUTLOOK_HYPOTHESES.md verified.")


def audit_long_running_report_and_ledger():
    print("Auditing docs/research_v2/LONG_RUNNING_RESEARCH_REPORT.md and RUNTIME_LEDGER.md...")
    rep_path = ROOT / "docs/research_v2/LONG_RUNNING_RESEARCH_REPORT.md"
    led_path = ROOT / "docs/research_v2/RUNTIME_LEDGER.md"
    
    rep_content = rep_path.read_text(encoding="utf-8")
    led_content = led_path.read_text(encoding="utf-8")
    
    # Invariant: 43 minutes mechanically recorded through Batch 4; subsequent hotfix runtime not mechanically captured
    assert "43 minutes mechanically recorded through Batch 4; subsequent hotfix runtime was not mechanically captured" in rep_content, (
        "Exact runtime statement missing in LONG_RUNNING_RESEARCH_REPORT.md"
    )
    assert "43 minutes mechanically recorded through Batch 4; subsequent hotfix runtime was not mechanically captured" in led_content, (
        "Exact runtime statement missing in RUNTIME_LEDGER.md"
    )
    print("  [PASS] Runtime ledger and report statements verified.")


def audit_collab_regressions():
    print("Auditing Collab Verification Semantics & Negative Regressions...")
    from scripts.build_collab_registries import verify_collab_context
    
    # Positive tests: strong collab context markers
    assert verify_collab_context("พูดคุยแลกเปลี่ยน w/@LucenePLG", "@LucenePLG")[0] is True
    assert verify_collab_context("Hack ใน Valorant? w/@mollyehe", "@mollyehe")[0] is True
    assert verify_collab_context("🔴｢LIVE｣#COLLAB PACIFY @Mallow_Ham", "@Mallow_Ham")[0] is True
    assert verify_collab_context("ทีม เบียว vs คนปกติ ft.@TsururuWorldEnd", "@TsururuWorldEnd")[0] is True
    assert verify_collab_context("เด็กหลังห้องกับ@yoinmori and เดอะแก๊ง", "@yoinmori")[0] is True
    assert verify_collab_context("ร้องเพลงร่วมกับ @KnownHandle", "@KnownHandle")[0] is True
    assert verify_collab_context("เล่นเกมกับ @KnownHandle", "@KnownHandle")[0] is True

    # Negative tests: bare @mention or generic keyword only
    ok, reason = verify_collab_context("Minecraft stream @KnownHandle", "@KnownHandle")
    assert ok is False, "Generic minecraft keyword with bare mention should not verify!"
    
    ok, reason = verify_collab_context("Festival 2024 @KnownHandle", "@KnownHandle")
    assert ok is False, "Generic festival keyword with bare mention should not verify!"

    # Negative regressions: attribution, greetings, thanks
    ok, reason = verify_collab_context("HBD @KnownHandle", "@KnownHandle")
    assert ok is False, "HBD @KnownHandle should be rejected!"
    assert "NON_COLLAB_CONTEXT" in reason

    ok, reason = verify_collab_context("art by @KnownHandle", "@KnownHandle")
    assert ok is False, "art by @KnownHandle should be rejected!"
    assert "NON_COLLAB_CONTEXT" in reason

    ok, reason = verify_collab_context("thanks @KnownHandle", "@KnownHandle")
    assert ok is False, "thanks @KnownHandle should be rejected!"
    assert "NON_COLLAB_CONTEXT" in reason

    # Collab events dataset audit
    collab_events_df = pd.read_parquet(ROOT / "data/industry/collab_events.parquet")
    assert len(collab_events_df) == 11, f"Expected 11 verified collab events, found {len(collab_events_df)}"
    assert (collab_events_df["identity_verification"] == "EXACT_HANDLE_MATCH").all(), (
        "All verified collab events must have identity_verification == EXACT_HANDLE_MATCH"
    )
    assert (collab_events_df["collab_context_verification"] == "STRONG_COLLAB_CONTEXT_VERIFIED").all(), (
        "All verified collab events must have collab_context_verification == STRONG_COLLAB_CONTEXT_VERIFIED"
    )
    print("  [PASS] Collab verification semantics & negative regressions verified.")


def main():
    print("=== STARTING RESEARCH V2 CONSISTENCY AUDIT ===")
    try:
        from scripts.audit_creator_identity_mapping import audit_identity
        from scripts.audit_research_source_integrity import audit_source_integrity
        audit_identity()
        audit_source_integrity()
        audit_single_canonical_writer()
        audit_research_v2_json()
        audit_outlook_model()
        audit_outlook_hypotheses()
        audit_long_running_report_and_ledger()
        audit_collab_regressions()
        print("\n=== ALL RESEARCH V2 CONSISTENCY AUDITS PASSED ===")
        return 0
    except Exception as e:
        print(f"\n[FAIL] Consistency audit failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
