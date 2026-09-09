"""Explicit synthetic snapshot generator for offline UI exercises; never a default export.

python -m tests.expanded_fixture .tmp/expanded-v1/synthetic.json
"""
import sys
from analytics.expanded_snapshot import build_snapshot
from scripts.build_duckdb_temporal_snapshots import export_expanded_snapshots


def bundle(path):
    creators = [{'id': 'synthetic-' + name, 'label': 'synthetic-' + name,
                 'review_status': 'approved', 'discovered_at': '2026-01-01T00:00:00Z',
                 'channel_created_at': '2018-01-01T00:00:00Z', 'subscribers': 999999,
                 'agency': 'Current agency only'}
                for name in ['discovered-2026', 'isolated', 'start-2023', 'latest', 'unknown']]
    evidence = [dict(creator_id='synthetic-' + name, evidence_id='synthetic-e-' + name,
                     identity_epoch_id='synthetic-epoch-' + name, evidence_kind=kind,
                     review_status='approved', source_ref='https://example.org/synthetic',
                     effective_from=date, date_precision='exact')
                for name, date, kind in [
                    ('discovered-2026','2020-06-01T00:00:00Z','virtual_activity'),
                    ('isolated','2020-06-01T00:00:00Z','virtual_activity'),
                    ('start-2023','2023-06-01T00:00:00Z','identity_start'),
                    ('latest','2027-02-01T00:00:00Z','virtual_activity')]]
    snapshots = []
    for key, start, end in [('yearly_2020','2020','2020'),('cumulative_2020','2020','2020'),
                            ('yearly_2023','2023','2023'),('cumulative_2023','2020','2023'),
                            ('yearly_2027','2027','2027'),('all_time','2020','2027')]:
        lo = f'{start}-01-01T00:00:00Z'
        hi = f'{end}-12-31T23:59:59Z' if end != '2027' else '2027-03-01T00:00:00Z'
        edges = []
        if key == 'all_time':
            for kind in ['audience_overlap','collaboration','production_credit']:
                edge = dict(source='synthetic-start-2023',target='synthetic-discovered-2026',
                            edge_type=kind,window_start=lo,window_end=hi,
                            source_ref='https://example.org/synthetic',review_status='approved',
                            event_time='2024-06-01T00:00:00Z')
                edge.update({'shared_any':9,'jaccard_comments':.2} if kind=='audience_overlap'
                            else {'credit_role':'rigger'})
                edges.append(edge)
        snapshots.append(build_snapshot(creators=creators,evidence=evidence,edges=edges,
            snapshot_id=key,cohort_version='synthetic-1',window_start=lo,window_end=hi,
            collected_through='2027-03-01T00:00:00Z',collected_at='2027-03-02T00:00:00Z',
            generated_at='2027-03-03T00:00:00Z'))
    return export_expanded_snapshots(snapshots,path,synthetic=True)


if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit('Supply explicit expanded-v1/synthetic*.json output path')
    bundle(sys.argv[1])
