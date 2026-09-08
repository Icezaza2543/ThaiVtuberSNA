#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression test suite for DATA_DICTIONARY semantic correctness and reproducibility.
Ensures definitions strictly adhere to analytical and privacy contracts.

Required coverage:
1. Exact 15-column schema
2. strong_shared uses >= 2 DISTINCT videos/streams, not messages
3. No generic all-audience Jaccard substitution
4. ARI is not described as statistical significance
5. HMAC is never described as decryptable
6. Evidence HIGH does not imply truth/no bias
7. viewer_hash counts are not humans ('คน')
8. comment != VOD viewing proof
9. live_chat != watch duration, and no 'สายดูสด'
10. weighted_degree != audience flow/migration
11. VIEWER_INDEX dual-population semantics documented
12. No "reconciled final identities" claim before reconciliation completion
13. Exactly 3 privacy conditional-format rules
"""
import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_full_data_dictionary import (
    build_dictionary_records,
    run_semantic_regression_audit,
    DICTIONARY_HEADERS,
)

EXPECTED_15_HEADERS = [
    'category',
    'tab_or_artifact',
    'field',
    'thai_name',
    'definition_th',
    'calculation_or_source',
    'data_type_unit',
    'example_value',
    'high_value_means',
    'low_value_means',
    'blank_null_means',
    'allowed_values',
    'interpretation_warning',
    'privacy_class',
    'used_for',
]

@pytest.fixture(scope="module")
def dictionary_rows():
    return build_dictionary_records()

# 1. Exact 15-column schema
def test_exact_fifteen_column_schema(dictionary_rows):
    """Headers must match the exact 15 live column names and every row must have 15 non-null columns."""
    assert DICTIONARY_HEADERS == EXPECTED_15_HEADERS, f"Headers mismatch: {DICTIONARY_HEADERS}"
    assert len(DICTIONARY_HEADERS) == 15
    for idx, row in enumerate(dictionary_rows, 1):
        assert len(row) == 15, f"Row {idx} has {len(row)} columns; expected exactly 15."
        assert all(c is not None for c in row), f"Row {idx} contains None values."

# 2. strong_shared uses >=2 DISTINCT videos/streams, not messages
def test_strong_shared_distinct_videos_semantics(dictionary_rows):
    """strong_shared must use >= 2 distinct video_ids/streams, never message counts or rows."""
    for idx, row in enumerate(dictionary_rows, 1):
        field = row[2]
        thai_name = row[3]
        def_th = row[4]
        calc = row[5]
        row_str = " ".join(str(c) for c in row)

        if 'strong_shared' in field.lower() or 'strong shared' in thai_name.lower():
            assert 'video_id' in row_str or 'วิดีโอ' in row_str or 'streams' in row_str, (
                f"Row {idx} ({field}) must mention distinct video_id / วิดีโอ / streams."
            )
            assert '>= 2 comments' not in row_str.lower(), f"Row {idx} ({field}) must not define as >= 2 comments"
            assert '>= 2 chat messages' not in row_str.lower(), f"Row {idx} ({field}) must not define as >= 2 chat messages"
            assert 'ความภักดี' not in def_th, f"Row {idx} ({field}) must not claim loyalty/ความภักดี"
            assert 'แฟนคลับตัวจริง' not in def_th, f"Row {idx} ({field}) must not claim แฟนคลับตัวจริง"

# 3. No generic all-audience Jaccard substitution
def test_no_generic_jaccard_substitution(dictionary_rows):
    """Jaccard must be disaggregated into comments and live_chat, explicitly warning against generic audience claims."""
    jaccard_rows = [r for r in dictionary_rows if 'jaccard' in r[2].lower()]
    assert len(jaccard_rows) >= 2, "Must contain disaggregated jaccard metrics"
    fields = [r[2] for r in jaccard_rows]
    assert 'jaccard_comments' in fields
    assert 'jaccard_live_chat' in fields
    for r in jaccard_rows:
        warn = r[12]
        assert 'ห้ามนำไปอ้างอิงเป็นดัชนีของผู้ชมทั้งหมด' in warn or 'generic' in warn.lower(), (
            f"Jaccard field {r[2]} must warn against generic all-audience claim."
        )

# 4. ARI is not described as statistical significance
def test_ari_not_described_as_statistical_significance(dictionary_rows):
    """ARI must never claim statistical significance or hypothesis testing."""
    ari_rows = [r for r in dictionary_rows if r[2] == 'ARI']
    assert len(ari_rows) >= 1
    for r in ari_rows:
        row_str = " ".join(str(c) for c in r)
        assert 'มีนัยสำคัญทางสถิติ' not in row_str, "ARI must not claim มีนัยสำคัญทางสถิติ"
        assert 'statistically significant' not in row_str.lower(), "ARI must not claim statistically significant"
        assert 'ความบังเอิญ' in row_str or 'chance' in row_str.lower(), "ARI must mention adjustment for chance"

# 5. HMAC is never described as decryptable
def test_hmac_never_described_as_decryptable(dictionary_rows):
    """HMAC must be described as irreversible; pepper is not a decryption key."""
    hmac_rows = [r for r in dictionary_rows if r[2] == 'viewer_hash']
    assert len(hmac_rows) >= 1
    for r in hmac_rows:
        row_str = " ".join(str(c) for c in r)
        if 'ถอดรหัส' in row_str:
            assert 'ไม่สามารถถอดรหัส' in row_str, "HMAC must state that it is not decryptable"
        if 'กุญแจ' in row_str:
            assert 'ไม่ใช่กุญแจถอดรหัส' in row_str, "Secret key must explicitly not be called a decryption key"
        assert 'PRIVATE_DATA' in r[13], "viewer_hash must be PRIVATE_DATA"

# 6. Evidence HIGH does not imply truth/no bias
def test_evidence_high_does_not_imply_truth(dictionary_rows):
    """HIGH evidence tier must not claim probability of truth or absence of bias."""
    tier_rows = [r for r in dictionary_rows if r[2] == 'HIGH' or (r[2] == 'evidence_support_tier' and r[0] == 'QUICK_REFERENCE_METRIC')]
    assert len(tier_rows) >= 1
    forbidden = ['ความจริงแน่นอน', 'probability of truth', 'guaranteed reliable', 'ปราศจากอคติ', 'very low bias', 'ไม่มีความเสี่ยงต่ออคติ']
    for r in tier_rows:
        row_str = " ".join(str(c) for c in r)
        for claim in forbidden:
            assert claim not in row_str.lower(), f"Evidence tier row must not claim '{claim}'"

# 7. viewer_hash counts are not humans ('คน')
def test_viewer_counts_not_labeled_humans(dictionary_rows):
    """viewer_hash counts must use observed accounts / บัญชี and not 'คน'."""
    account_count_fields = ['shared_any', 'strong_shared_any', 'shared_comments', 'shared_live_chat', 'strong_shared_comments', 'strong_shared_live_chat', 'Shared Viewers', 'Strong Shared']
    for r in dictionary_rows:
        if r[2] in account_count_fields:
            unit = r[6]
            assert unit != 'Integer (คน)', f"Field {r[2]} unit must not be 'Integer (คน)'"
            assert 'บัญชี' in unit or 'accounts' in unit.lower(), f"Field {r[2]} unit should specify บัญชี/accounts"

# 8. comment != VOD viewing proof
def test_comment_not_equated_with_vod_viewing(dictionary_rows):
    """Comments reflect textual posting, not proof of VOD viewing or watch time."""
    for idx, r in enumerate(dictionary_rows, 1):
        field = r[2]
        row_str = " ".join(str(c) for c in r)
        if 'comment' in field.lower() and ('ดูคลิปย้อนหลัง' in row_str or 'vod viewing' in row_str.lower()):
            assert ('ไม่ใช่วัดการรับชม' in row_str or 'ไม่ได้พิสูจน์การดูคลิปย้อนหลัง' in row_str or 'ไม่ใช่การวัดการรับชมคลิปย้อนหลัง' in row_str), (
                f"Row {idx} ({field}): Comment must not be equated with VOD viewing proof."
            )

# 9. live_chat != watch duration, and no 'สายดูสด'
def test_live_chat_not_watch_duration_and_no_residual_language(dictionary_rows):
    """live_chat metrics reflect participation, not watch duration, and forbid 'สายดูสด'."""
    for idx, r in enumerate(dictionary_rows, 1):
        field = r[2]
        row_str = " ".join(str(c) for c in r)
        assert 'สายดูสด' not in row_str, f"Row {idx} ({field}): Found forbidden phrase 'สายดูสด'."
        if 'live_chat' in field.lower() and 'strong_shared' in field.lower():
            assert 'ระยะเวลาการรับชม' in row_str or 'watch duration' in row_str.lower(), (
                f"Row {idx} ({field}): Must explicitly caveat watch duration."
            )

# 10. weighted_degree != audience flow/migration
def test_weighted_degree_not_audience_flow(dictionary_rows):
    """weighted_degree must not be defined as traffic flow or audience migration."""
    wd_rows = [r for r in dictionary_rows if r[2] == 'weighted_degree']
    assert len(wd_rows) >= 1
    for r in wd_rows:
        def_th = r[4]
        calc = r[5]
        for term in ['traffic flow', 'viewer movement', 'audience exchange', 'การเคลื่อนย้ายคนดู', 'การไหลเวียนของผู้ชม']:
            assert term not in def_th.lower(), f"weighted_degree definition must not contain '{term}'"
            assert term not in calc.lower(), f"weighted_degree calculation must not contain '{term}'"

# 11. VIEWER_INDEX dual-population semantics documented
def test_viewer_index_dual_population_semantics(dictionary_rows):
    """VIEWER_INDEX total_interactions and channels_observed_count must document dual population semantics."""
    vi_total = [r for r in dictionary_rows if r[1] == 'VIEWER_INDEX' and r[2] == 'total_interactions']
    assert len(vi_total) >= 1
    warn = vi_total[0][12]
    assert 'HASH_ONLY' in warn and 'UNRESOLVED_HANDLE' in warn, "VIEWER_INDEX total_interactions must document dual population"
    assert 'ไม่สามารถเปรียบเทียบกันตรงๆ ได้' in warn or 'not directly comparable' in warn.lower()

# 12. No "reconciled final identities" claim before reconciliation completion
def test_no_reconciled_final_identities_claim(dictionary_rows):
    """Must not claim 'หลังการกระทบยอด' or final unique identities for 108,480 rows."""
    for idx, r in enumerate(dictionary_rows, 1):
        field = r[2]
        row_str = " ".join(str(c) for c in r)
        assert 'หลังการกระทบยอด' not in row_str, (
            f"Row {idx} ({field}): Found forbidden phrase 'หลังการกระทบยอด'. Use Candidate Index / Pending Reconciliation."
        )
        if '108,480' in row_str or '108480' in row_str:
            assert ('ไม่ใช่ตัวตนที่ไม่ซ้ำกันขั้นสุดท้าย' in row_str or 'ไม่ใช่จำนวนตัวตนที่ไม่ซ้ำกันขั้นสุดท้าย' in row_str or 'ไม่สามารถตีความ' in row_str or 'ห้ามตีความ' in row_str or 'ไม่ใช่จำนวน' in row_str), (
                f"Row {idx} ({field}): Row count 108,480 must never be described as final unique identities."
            )
        # Also check VIEWER_INDEX total_interactions high_value_means does not claim 'สม่ำเสมอ'
        if field == 'total_interactions' and r[1] == 'VIEWER_INDEX':
            assert 'สม่ำเสมอ' not in r[8], f"Row {idx} ({field}): high_value_means must not claim 'สม่ำเสมอ'."

# 13. Exactly 3 privacy conditional-format rules
def test_exactly_three_privacy_conditional_format_rules():
    """Verify that sheet formatter generates exactly 3 privacy conditional formatting rules."""
    from scripts.build_full_data_dictionary import format_data_dictionary_sheet
    import inspect
    src = inspect.getsource(format_data_dictionary_sheet)
    assert src.count('addConditionalFormatRule') == 3, "Formatter must register exactly 3 addConditionalFormatRule"
    assert 'SECRET_CREDENTIAL' in src
    assert 'PRIVATE_DATA' in src
    assert 'PUBLIC_RESEARCH_DATA' in src
    assert 'deleteConditionalFormatRule' in src, "Formatter must clear stale conditional format rules"

def test_semantic_regression_audit_built_in(dictionary_rows):
    """The built-in regression audit must pass with 0 errors."""
    run_semantic_regression_audit(dictionary_rows)
