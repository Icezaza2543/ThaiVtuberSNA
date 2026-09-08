#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Research v2 Public Aggregate Data Contract:
- Validates web/research/data/research_v2.json
- Enforces zero Level-A secrets and zero Level-B private viewer identities
- Enforces finding contract: [metric, period, value, comparison, interpretation, confidence, source_artifact, limitation]
- Enforces non-causal collab framing and market non-summing rules
"""

import json
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "web/research/data/research_v2.json"

@pytest.fixture(scope="module")
def contract_data():
    assert CONTRACT_PATH.exists(), f"Contract file missing at {CONTRACT_PATH}"
    content = CONTRACT_PATH.read_text(encoding="utf-8")
    return json.loads(content)

def test_contract_json_exists_and_valid(contract_data):
    assert isinstance(contract_data, dict)
    assert contract_data["metadata"]["version"] == "2.0.0"
    assert contract_data["metadata"]["privacy_class"] == "PUBLIC_RESEARCH_DATA"

def test_mandatory_top_level_sections(contract_data):
    mandatory = [
        "metadata", "coverage", "industry_pulse", "creator_ecosystem",
        "audience_behavior", "network_structure", "mobility",
        "market", "outlook", "methodology"
    ]
    for section in mandatory:
        assert section in contract_data, f"Missing required section: {section}"

def test_zero_private_viewer_identifiers():
    raw_text = CONTRACT_PATH.read_text(encoding="utf-8")
    
    # 1. No viewer_hash strings
    assert "viewer_hash" not in raw_text
    
    # 2. No HMAC SHA256 hashes of private viewers
    hmac_pattern = re.compile(r'\b[0-9a-f]{64}\b')
    matches = hmac_pattern.findall(raw_text)
    assert len(matches) == 0, f"Found raw 64-char hashes in public contract: {matches[:3]}"
    
    # 3. No secrets or email patterns
    secret_pattern = re.compile(r'(AIza[0-9A-Za-z-_]{35}|ghp_[0-9A-Za-z]{36}|client_secret|private_key)')
    assert not secret_pattern.search(raw_text), "Found potential secret credential pattern in contract"
    
    email_pattern = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    # Filter out any schema/example
    real_emails = [e for e in email_pattern.findall(raw_text) if "example" not in e]
    assert len(real_emails) == 0, f"Found emails in public contract: {real_emails}"

def test_findings_schema(contract_data):
    """Every analytical finding must carry required fields."""
    required_keys = ["metric", "period", "value", "comparison", "interpretation", "confidence", "source_artifact", "limitation"]
    
    pulse = contract_data["industry_pulse"]
    for key in ["creators", "audience", "network", "market"]:
        finding = pulse[key]
        for rk in required_keys:
            assert rk in finding, f"Pulse finding {key} missing key {rk}"
        assert finding["confidence"] in ["HIGH", "MEDIUM", "LOW", "NEEDS_VERIFICATION"]

def test_partial_ytd_contract_preserved(contract_data):
    """2026 must always be marked as YTD / partial window."""
    cov = contract_data["coverage"]
    assert "YTD" in cov["data_coverage"]
    assert "YTD" in cov["observation_window"]
    
    # Yearly coverage chart has 2026 note
    y2026 = [y for y in cov["yearly_coverage_chart"] if y["year"] == 2026]
    assert len(y2026) == 1
    assert "YTD" in y2026[0].get("note", "").upper()

def test_collab_dataset_connected_and_non_causal(contract_data):
    """Collab analysis must be connected and strictly non-causal."""
    collab = contract_data["mobility"]
    assert "CONNECTED" in collab["collab_dataset_status"]
    
    # Check COLLAB_ANALYSIS.md exists and enforces BEFORE_AFTER_DESCRIPTIVE
    collab_md = (ROOT / "docs/research_v2/COLLAB_ANALYSIS.md").read_text(encoding="utf-8")
    assert "BEFORE_AFTER_DESCRIPTIVE" in collab_md
    assert "not claim or demonstrate causality" in collab_md.lower()

def test_market_monetization_guards(contract_data):
    """Market size must not be claimed as verified fact without disclosures."""
    market = contract_data["market"]
    assert market["estimated_size"] == "INSUFFICIENT_EVIDENCE"
    assert "Awaiting" in market["estimate_status"]
    
    # Scenarios must specify explicit conversion bounds
    scenarios = market["scenarios"]
    for sc_name in ["conservative", "base", "upside"]:
        assert sc_name in scenarios
        assert "payer_conversion_pct" in scenarios[sc_name]
        assert "arpu_thb_annual" in scenarios[sc_name]
        assert scenarios[sc_name]["payer_conversion_pct"] > 0

def test_audience_behavior_segments_not_demographics(contract_data):
    """Audience segments are behavioral, never demographic inferences."""
    aud = contract_data["audience_behavior"]
    assert "segment_breadth" in aud
    assert "segment_modality" in aud
    assert "segment_time" in aud
    
    # No demographic keys
    raw_aud_json = json.dumps(aud)
    assert "gender" not in raw_aud_json.lower()
    assert "income" not in raw_aud_json.lower()

def test_outlook_taxonomy_valid(contract_data):
    """Outlook scorecard must feature 11 indicators and valid taxonomy."""
    outlook = contract_data["outlook"]
    valid_states = ["EXPANSION", "HEALTHY_STABLE", "NICHE_STABLE", "CONSOLIDATING", "CONTRACTING", "FRAGILE", "INSUFFICIENT_EVIDENCE"]
    
    verdict = outlook["verdict"]
    assert any(s in verdict for s in valid_states)
    
    scorecard = outlook["scorecard"]
    assert len(scorecard) == 11, f"Expected 11 outlook indicators, found {len(scorecard)}"
    for item in scorecard:
        assert "dimension" in item
        assert "direction" in item
        assert item["direction"] in ["EXPANDING", "STABLE", "CONTRACTING", "CONCENTRATING", "DISPERSING"]

def test_methodology_pointers_exist(contract_data):
    """All 14 methodology artifacts must resolve to valid paths on disk."""
    artifacts = contract_data["methodology"]["artifacts"]
    assert len(artifacts) == 14
    for key, rel_path in artifacts.items():
        p = ROOT / rel_path
        assert p.exists(), f"Methodology artifact for {key} missing on disk: {rel_path}"
