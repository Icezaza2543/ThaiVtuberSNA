"""Canonical contracts and evidence preservation for the accepted 45 reviews."""
import csv
import hashlib
import json
from pathlib import Path

from core.expanded_contracts import FORMATS, ROLES

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'docs/evidence/expanded-v1/public-review-2026-09-10'


def load_review():
    return json.loads((REVIEW / 'provisional_resolution_v1.json').read_text(encoding='utf-8'))


def digest(value):
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def test_all_accepted_reviews_follow_expanded_contracts():
    rows = load_review()['rows']
    assert len(rows) == len({row['channel_id'] for row in rows}) == 45
    for row in rows:
        assert row['old_status'] == 'PROVISIONAL_VIRTUAL'
        assert row['new_status'] == 'STRICT_VIRTUAL'
        assert row['entity_type'] == 'virtual_creator'
        assert set(row['roles']) <= ROLES
        assert len(row['roles']) == len(set(row['roles']))
        assert row['presentation_format'] in FORMATS
        assert row['conflict_flag'] is False


def test_normalization_preserves_all_non_normalized_evidence():
    review = load_review()
    for row in review['rows']:
        for key in ('roles', 'presentation_format', 'additional_descriptors'):
            row.pop(key, None)
    # Fingerprints of accepted evidence at 8c8a006. Includes source URLs,
    # summaries, reasons, reviewer, timestamps, decisions and all metadata.
    assert digest(review) == 'ee9070b0695afeb33aa4ce2d7c5454092067db4ad6a898e2f1bc62cd536fdbe4'
    sources = json.loads((REVIEW / 'provisional_resolution_sources_v1.json').read_text(encoding='utf-8'))
    assert digest(sources) == 'b70a4c806a96999b65d276cbbfed00861bb37ef0814194f6464b25806cd29bdf'


def test_descriptors_survive_outside_canonical_roles():
    rows = {row['channel_id']: row for row in load_review()['rows']}
    rainnie = rows['UCqu5twYqzKGrRyIrcvg4YXA']
    peko = rows['UCXddo8vgPHBsEkDMqRwcYSQ']
    assert rainnie['additional_descriptors'] == ['brand_ambassador']
    assert peko['additional_descriptors'] == ['cosplayer']
    assert peko['roles'].count('artist') == 1
    assert rows['UCRjdIz5ngcJVDZ-bjs2mEzg']['presentation_format'] == '3D'
    for channel_id in ('UCjgiHXaBeeuWfxZpNMCJioQ', 'UCdPOgLoE_grESHHrpHDNsEg', 'UCNW0brB5G5GcBDXuJ1iDglw'):
        assert rows[channel_id]['presentation_format'] == 'unknown'


def test_normalized_csv_matches_json_including_descriptors():
    rows = load_review()['rows']
    with (REVIEW / 'provisional_resolution_v1.csv').open(encoding='utf-8-sig', newline='') as f:
        csv_rows = list(csv.DictReader(f))
    assert len(csv_rows) == len(rows)
    for row, csv_row in zip(rows, csv_rows):
        assert csv_row['channel_id'] == row['channel_id']
        for key, value in row.items():
            if isinstance(value, list):
                assert json.loads(csv_row[key]) == value
            else:
                assert csv_row[key] == str(value)
        if 'additional_descriptors' not in row:
            assert csv_row['additional_descriptors'] == ''


def test_surface_defaults_to_exact_strict_set():
    eligibility = json.loads((REVIEW / 'channel_eligibility_v1.json').read_text(encoding='utf-8'))
    cohort = json.loads((REVIEW / 'surface_virtual_cohort_v1.json').read_text(encoding='utf-8'))
    strict = {row['channel_id'] for row in eligibility['rows'] if row['eligibility_status'] == 'STRICT_VIRTUAL'}
    other = {row['channel_id'] for row in eligibility['rows'] if row['eligibility_status'] != 'STRICT_VIRTUAL'}
    assert set(cohort['strict_channel_ids']) == strict
    assert not strict & other
    assert len(strict) == 274
    assert cohort['provisional_virtual_count'] == 0
    assert cohort['hold_count'] == 132
    assert cohort['explicitly_excluded_non_persona_count'] == 2
    assert cohort['explicitly_excluded_non_virtual_count'] == 0
