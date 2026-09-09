"""Synthetic characterization of the pre-refactor public snapshot writer."""
import json
from pathlib import Path
import pandas as pd
from scripts import build_creator_ecosystem_data as snapshot


def build_fixture(monkeypatch, tmp_path):
    inputs = {
        'TARGET_MANIFEST_CSV': pd.DataFrame([
            {'channel_id': f'creator-{i}', 'name': f'Creator {i}', 'agency': agency,
             'tier_at_selection': 'Tier 2', 'lifecycle_status': status}
            for i, agency, status in [(1, 'Independent', 'active'), (2, 'Pixela Project', 'hiatus'), (3, 'Other Group', 'graduated')]]),
        'CHANNEL_COVERAGE_PARQUET': pd.DataFrame([
            {'channel_id': f'creator-{i}', 'oldest_video_published_at': '2021-01-01', 'newest_video_published_at': '2025-12-31'} for i in (1, 2, 3)]),
        'CANONICAL_EVENTS_PARQUET': pd.DataFrame([
            {'creator_channel_id': 'creator-1', 'event_type': 'DEBUT', 'evidence_tier': 'SECONDARY_DOCUMENTED'},
            {'creator_channel_id': 'creator-2', 'event_type': 'GRADUATION', 'evidence_tier': 'PRIMARY_EVENT_SPECIFIC'},
            {'creator_channel_id': 'creator-3', 'event_type': 'GRADUATION_PROXY', 'evidence_tier': 'INFERRED_PROXY'}]),
        'CANONICAL_COVERAGE_PARQUET': pd.DataFrame([
            {'creator_channel_id': f'creator-{i}', 'lifecycle_status': status} for i, status in [(1, 'active'), (2, 'hiatus'), (3, 'graduated')]])}
    for key, frame in inputs.items():
        path = tmp_path / (key + ('.csv' if key.endswith('CSV') else '.parquet'))
        if key.endswith('CSV'): frame.to_csv(path, index=False)
        else: frame.to_parquet(path, index=False)
        monkeypatch.setattr(snapshot, key, path)
    registry = tmp_path / 'registry.json'
    registry.write_text(json.dumps([{'channel_id': f'creator-{i}', 'handle': f'creator{i}', 'subscriber_count': i * 100, 'video_count': i, 'view_count': i * 1000} for i in (1,2,3)]))
    monkeypatch.setattr(snapshot, 'REGISTRY_JSON', registry)
    monkeypatch.setattr(snapshot, 'OUT_SNAPSHOT_PARQUET', tmp_path / 'snapshot.parquet')
    return snapshot.build_creator_public_snapshot()


def test_snapshot_matches_pre_refactor_characterization(monkeypatch, tmp_path):
    actual = build_fixture(monkeypatch, tmp_path)
    expected = json.loads((Path(__file__).parent / 'fixtures/refactor_snapshot.json').read_text())
    assert actual.to_dict('records') == expected
    pd.testing.assert_frame_equal(actual.reset_index(drop=True), pd.read_parquet(tmp_path / 'snapshot.parquet'))
