import pytest
from core.expanded_contracts import capacity_estimate, request_estimate, count
from analytics.expanded_snapshot import build_snapshot


def snapshot(creators=None, evidence=None, **changes):
    args = dict(creators=creators or [{'id': 'synthetic-a', 'label': 'A', 'review_status': 'approved',
                                     'discovered_at': '2026-01-01', 'subscribers': 9000}],
                evidence=evidence or [], edges=[], snapshot_id='yearly_2020', cohort_version='synthetic-1',
                window_start='2020-01-01T00:00:00Z', window_end='2020-12-31T23:59:59Z',
                collected_through='2026-01-01T00:00:00Z', collected_at='2026-01-02T00:00:00Z',
                generated_at='2026-01-03T00:00:00Z')
    args.update(changes)
    return build_snapshot(**args)


def activity(date='2020-06-01T00:00:00Z', **changes):
    e = dict(creator_id='synthetic-a', evidence_id='synthetic-e', identity_epoch_id='synthetic-epoch',
             evidence_kind='virtual_activity', review_status='approved', source_ref='synthetic:bio',
             effective_from=date, date_precision='exact')
    e.update(changes)
    return e


def test_discovery_is_not_activity_and_isolated_nodes_survive():
    s = snapshot(evidence=[activity()])
    assert [n['id'] for n in s['nodes']] == ['synthetic-a']
    assert s['edges'] == [] and s['nodes'][0]['subscribers'] is None
    assert s['nodes'][0]['agency'] is None
    assert snapshot()['unknown_history'] == ['synthetic-a']


def test_known_start_and_unknown_history_are_distinct():
    assert snapshot(evidence=[activity('2023-01-01T00:00:00Z', evidence_kind='identity_start')])['confirmed_not_started'] == ['synthetic-a']
    assert snapshot(evidence=[activity('2023-01-01T00:00:00Z')])['unknown_history'] == ['synthetic-a']
    assert not snapshot(evidence=[activity(date_precision='year')])['nodes']


def test_no_interpolation_or_future_observations():
    assert not snapshot(evidence=[activity('2019-01-01T00:00:00Z'), activity('2021-01-01T00:00:00Z', evidence_id='e2')])['nodes']
    assert snapshot(window_start='2027-01-01T00:00:00Z', window_end='2027-12-31T00:00:00Z')['coverage_state'] == 'NO_SNAPSHOT'


def test_estimates_do_not_certify_unmeasured_capacity():
    e = request_estimate(12)
    assert (e['catalog_ceiling_units'], e['interaction_ceiling_units'], e['combined_record_cap']) == (303, 550, 24000)
    assert capacity_estimate(archive_rows=24000)['state'] == 'NOT_MEASURED'
    assert capacity_estimate(archive_rows=100_000_000, allocated_cells=0)['state'] == 'INSUFFICIENT'
    assert capacity_estimate(archive_rows=100, allocated_cells=100)['state'] == 'PASS'
    for value in (True, -1, 1.5):
        with pytest.raises(ValueError): count(value)


def test_mismatched_edge_window_fails():
    with pytest.raises(ValueError, match='window'):
        snapshot(evidence=[activity()], edges=[dict(source='synthetic-a', target='synthetic-a', edge_type='audience_overlap')])


def test_expanded_export_is_explicit_and_immutable(tmp_path):
    from scripts.build_duckdb_temporal_snapshots import export_expanded_snapshots
    path = tmp_path / 'expanded-v1' / 'synthetic-snapshot.json'
    s = snapshot(evidence=[activity()])
    assert export_expanded_snapshots([s], path, synthetic=True)['synthetic']
    original = path.read_bytes()
    export_expanded_snapshots([s], path, synthetic=True)
    assert path.read_bytes() == original
    with pytest.raises(ValueError): export_expanded_snapshots([s], tmp_path / 'data.json')
    with pytest.raises(ValueError): export_expanded_snapshots([snapshot()], path, synthetic=True)
