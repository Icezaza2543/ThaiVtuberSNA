import json
from pathlib import Path

import pytest

from scripts.package_creator_review_evidence import package_review_evidence, validate_production_counts


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture
def review_inputs(tmp_path):
    screening = write_json(
        tmp_path / "screening.json",
        {
            "rows": [
                {
                    "discovery_id": "automated-vtuber",
                    "platform": "youtube",
                    "name": "Automated VTuber",
                    "original_name": "automated",
                    "url": "https://example.test/automated",
                    "channel_id": "UCautomated",
                    "decision": "VTUBER",
                    "reason": "automated evidence",
                    "evidence_urls": ["https://example.test/automated/about"],
                    "raw_review_file": "C:\\Users\\example\\private-cache.json",
                },
                {
                    "discovery_id": "human-vtuber",
                    "platform": "youtube",
                    "name": "Human VTuber",
                    "original_name": "human",
                    "url": "https://example.test/human",
                    "channel_id": "UChuman",
                    "decision": "UNRESOLVED",
                    "reason": "needs human review",
                    "evidence_urls": ["https://example.test/human/about"],
                },
                {
                    "discovery_id": "trusted-baseline",
                    "platform": "youtube",
                    "name": "Trusted Baseline",
                    "original_name": "trusted",
                    "url": "https://example.test/trusted",
                    "channel_id": "UCtrusted",
                    "decision": "TRUSTED_BASELINE",
                    "reason": "trusted",
                    "evidence_urls": [],
                },
                {
                    "discovery_id": "excluded",
                    "platform": "youtube",
                    "name": "Excluded",
                    "original_name": "excluded",
                    "url": "https://example.test/excluded",
                    "channel_id": "UCexcluded",
                    "decision": "NON_VTUBER",
                    "reason": "not a persona",
                    "evidence_urls": [],
                },
                {
                    "discovery_id": "human-unrelated",
                    "platform": "youtube",
                    "name": "Unrelated",
                    "original_name": "unrelated",
                    "url": "https://example.test/unrelated",
                    "channel_id": "UCunrelated",
                    "decision": "UNRESOLVED",
                    "reason": "needs human review",
                    "evidence_urls": [],
                },
                {
                    "discovery_id": "human-unavailable",
                    "platform": "youtube",
                    "name": "Unavailable",
                    "original_name": "unavailable",
                    "url": "https://example.test/unavailable",
                    "channel_id": "UCunavailable",
                    "decision": "UNRESOLVED",
                    "reason": "needs human review",
                    "evidence_urls": [],
                },
            ]
        },
    )
    human = write_json(
        tmp_path / "human.json",
        {
            "decisions": ["human-vtuber", "human-unrelated", "human-unavailable"],
            "history": [
                {"discovery_id": "human-vtuber", "decision": "vtuber", "reviewed_at": "2026-09-19T00:00:00Z"},
                {"discovery_id": "human-unrelated", "decision": "unrelated", "reviewed_at": "2026-09-19T00:01:00Z"},
                {"discovery_id": "human-unavailable", "decision": "unavailable", "reviewed_at": "2026-09-19T00:02:00Z"},
            ],
        },
    )
    return screening, human


def test_final_human_decision_overrides_unresolved_and_paths_are_sanitized(review_inputs):
    screening, human = review_inputs
    bundle = package_review_evidence(screening, human)

    rows = {row["discovery_id"]: row for row in bundle["rows"]}
    assert rows["human-vtuber"]["eligibility"] == "vtuber"
    assert rows["human-unrelated"]["eligibility"] == "exclude_unrelated"
    assert rows["human-unavailable"]["eligibility"] == "unavailable"
    assert "raw_review_file" not in json.dumps(bundle)
    assert "C:\\Users\\" not in json.dumps(bundle)


def test_excluded_legacy_new_persona_cannot_reenter_catalog(review_inputs):
    screening, human = review_inputs
    payload = json.loads(screening.read_text(encoding="utf-8"))
    excluded = next(row for row in payload["rows"] if row["discovery_id"] == "excluded")
    excluded["legacy_identity_decision"] = "new_persona"
    write_json(screening, payload)

    bundle = package_review_evidence(screening, human)

    row = next(row for row in bundle["rows"] if row["discovery_id"] == "excluded")
    assert row["eligibility"].startswith("exclude_")


def test_rejects_human_decision_for_non_unresolved_row(review_inputs, tmp_path):
    screening, _ = review_inputs
    human = write_json(
        tmp_path / "invalid-human.json",
        {
            "decisions": ["automated-vtuber"],
            "history": [{"discovery_id": "automated-vtuber", "decision": "vtuber", "reviewed_at": "2026-09-19T00:00:00Z"}],
        },
    )

    with pytest.raises(ValueError, match="non-UNRESOLVED"):
        package_review_evidence(screening, human)


def test_rejects_duplicate_human_decision_object_keys(review_inputs, tmp_path):
    screening, _ = review_inputs
    human = tmp_path / "duplicate-human.json"
    human.write_text(
        '{"decisions":{"human-vtuber":{"discovery_id":"human-vtuber","decision":"vtuber"},'
        '"human-vtuber":{"discovery_id":"human-vtuber","decision":"unavailable"}}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate JSON object key"):
        package_review_evidence(screening, human)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("url", "C:\\Users\\example\\private.json"),
        ("url", "https://localhost/private"),
        ("url", "https://localhost./private"),
        ("url", "https://127.0.0.1/private"),
        ("url", "https://127.0.0.1./private"),
        ("url", "https://[::1]/private"),
        ("url", "https://169.254.10.20/private"),
        ("reason", "token=super-secret-value"),
        ("reason", "see C:\\Users\\alice\\token.txt"),
        ("reason", "/usr"),
        ("reason", "see:/usr"),
        ("reason", "note./proc"),
        ("reason", "prefix-/root"),
        ("reason", "See https://example.com/profile and note./proc"),
        ("reason", "reviewed /proc for evidence"),
        ("reason", "source directory (/root)"),
        ("reason", "see /custom-directory"),
        ("reason", "see /root/.ssh/id_ed25519"),
        ("reason", "read /usr/local/private.txt and /proc/self/environ"),
        ("reason", "the password is hunter2"),
        ("evidence_urls", ["file:///tmp/private-cache.json"]),
    ],
)
def test_rejects_local_paths_and_secret_values_in_allowed_fields(review_inputs, field, value):
    screening, human = review_inputs
    payload = json.loads(screening.read_text(encoding="utf-8"))
    row = next(row for row in payload["rows"] if row["discovery_id"] == "automated-vtuber")
    row[field] = value
    write_json(screening, payload)

    with pytest.raises(ValueError, match="unsafe"):
        package_review_evidence(screening, human)


def test_keeps_valid_public_evidence_urls_and_reason_meaning(review_inputs):
    screening, human = review_inputs
    bundle = package_review_evidence(screening, human)
    row = next(row for row in bundle["rows"] if row["discovery_id"] == "automated-vtuber")

    assert row["reason"] == "automated evidence"
    assert row["evidence_urls"] == ["https://example.test/automated/about"]


def test_keeps_benign_english_and_thai_credential_discussion(review_inputs):
    screening, human = review_inputs
    payload = json.loads(screening.read_text(encoding="utf-8"))
    row = next(row for row in payload["rows"] if row["discovery_id"] == "automated-vtuber")
    row["reason"] = "The official profile discusses password safety; หน้าโปรไฟล์ทางการอธิบายความปลอดภัยของรหัสผ่าน"
    row["evidence_urls"] = ["https://public.example.org/evidence"]
    write_json(screening, payload)

    bundle = package_review_evidence(screening, human)
    published = next(row for row in bundle["rows"] if row["discovery_id"] == "automated-vtuber")
    assert published["reason"] == row["reason"]


@pytest.mark.parametrize(
    "reason",
    [
        "Official evidence: https://public.example.org/root/profile",
        "Official evidence: https://example.com/usr",
        "Official evidence: http://example.com/proc/self/environ",
        "Official profile/channel summary confirms singing/gaming content",
        "Summary cites https://example.com/path/to/profile?view=about#details as evidence",
        "Evidence (https://example.com/a./profile) and http://example.org/a-/channel confirms persona",
        "Official singing and/or gaming profile",
        "ข้อมูลที่มี/ไม่มีแหล่งอ้างอิง",
        "สรุปจากโปรไฟล์/ช่องทางการ พบเนื้อหาร้องเพลง/เล่นเกม",
        "Official profile / channel summary; โปรไฟล์ / ช่องทางการ",
    ],
)
def test_keeps_public_url_paths_and_benign_summaries(review_inputs, reason):
    screening, human = review_inputs
    payload = json.loads(screening.read_text(encoding="utf-8"))
    row = next(row for row in payload["rows"] if row["discovery_id"] == "automated-vtuber")
    row["reason"] = reason
    write_json(screening, payload)

    bundle = package_review_evidence(screening, human)
    published = next(row for row in bundle["rows"] if row["discovery_id"] == "automated-vtuber")
    assert published["reason"] == row["reason"]


def test_rejects_same_size_bundle_with_wrong_production_distribution(review_inputs):
    screening, human = review_inputs
    bundle = package_review_evidence(screening, human)
    bundle["rows"] = (bundle["rows"] * 148)[:884]
    bundle["rows"][0] = {**bundle["rows"][0], "eligibility": "unavailable"}

    with pytest.raises(ValueError, match="eligibility distribution"):
        validate_production_counts(bundle)



def explicit_group_correction(discovery_id='human-vtuber'):
    channel_id = 'UC' + 'g' * 22
    return {'schema_version': 1, 'corrections': [{
        'discovery_id': discovery_id, 'old_eligibility': 'vtuber',
        'new_eligibility': 'exclude_virtual_group',
        'account_url': 'https://example.test/human',
        'owner_channel_id': channel_id,
        'owner_canonical_url': 'https://www.youtube.com/channel/' + channel_id,
        'source_url': 'https://example.test/human', 'source_kind': 'youtube_api',
        'summary': 'Video owner is the official channel of a virtual group.',
        'observed_at': '2026-09-19T12:00:00Z',
        'reviewer': 'fixture:controller', 'ruling': 'Exclude group accounts from the individual catalog.',
    }]}


def test_explicit_group_correction_applies_after_human_precedence_and_retains_provenance(review_inputs, tmp_path):
    screening, human = review_inputs
    correction = write_json(tmp_path / 'corrections.json', explicit_group_correction())
    bundle = package_review_evidence(screening, human, correction)
    row = next(r for r in bundle['rows'] if r['discovery_id'] == 'human-vtuber')
    assert row['eligibility'] == 'exclude_virtual_group'
    assert row['decision_provenance'] == {'source': 'human_review', 'decision': 'vtuber'}
    assert row['correction_provenance']['old_eligibility'] == 'vtuber'
    assert row['correction_provenance']['owner_channel_id'] == 'UC' + 'g' * 22
    assert row['correction_provenance']['source_kind'] == 'youtube_api'
    assert bundle['eligibility_counts']['vtuber'] == 1
    assert bundle['eligibility_counts']['exclude_virtual_group'] == 1
    assert row['correction_provenance']['owner_canonical_url'] in row['evidence_urls']


@pytest.mark.parametrize('mutation', ['unknown', 'duplicate', 'wrong_prior', 'readmit', 'wrong_account', 'wrong_owner', 'missing_summary', 'unsafe_source'])
def test_explicit_corrections_fail_closed_when_not_supported(review_inputs, tmp_path, mutation):
    screening, human = review_inputs
    payload = explicit_group_correction()
    row = payload['corrections'][0]
    if mutation == 'unknown': row['discovery_id'] = 'missing'
    if mutation == 'duplicate': payload['corrections'].append(dict(row))
    if mutation == 'wrong_prior': row['old_eligibility'] = 'unavailable'
    if mutation == 'readmit': row['new_eligibility'] = 'vtuber'
    if mutation == 'wrong_account': row['account_url'] = 'https://example.test/another'
    if mutation == 'wrong_owner': row['owner_channel_id'] = 'invalid'
    if mutation == 'missing_summary': row['summary'] = ''
    if mutation == 'unsafe_source': row['source_url'] = 'http://127.0.0.1/private'
    correction = write_json(tmp_path / 'corrections.json', payload)
    with pytest.raises(ValueError):
        package_review_evidence(screening, human, correction)
