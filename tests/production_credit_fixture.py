"""Python-generated dated credit fixture, never default public data."""
import sys
from analytics.expanded_snapshot import build_snapshot
from scripts.build_duckdb_temporal_snapshots import export_expanded_snapshots


def snapshots():
    creators=[dict(id='synthetic-virtual',label='Synthetic virtual creator',review_status='approved'),
              dict(id='synthetic-portfolio',label='Synthetic portfolio rigger',review_status='approved',
                   roles=['rigger'],is_virtual_creator=False,channel_id=None)]
    evidence=[dict(creator_id='synthetic-virtual',evidence_id='synthetic-activity',identity_epoch_id='synthetic-epoch',
                   evidence_kind='virtual_activity',review_status='approved',source_ref='synthetic:showcase',
                   effective_from='2023-06-01T00:00:00Z',date_precision='exact')]
    results=[]
    for key,start,end in [('yearly_2020','2020','2020'),('yearly_2023','2023','2023'),('all_time','2020','2023')]:
        lo=f'{start}-01-01T00:00:00Z';hi=f'{end}-12-31T23:59:59Z'
        credit=dict(source='synthetic-virtual',target='synthetic-portfolio',edge_type='production_credit',
                    credit_role='rigger',evidence_id='synthetic-credit',source_ref='https://example.org/credit',
                    review_status='approved',event_time='2023-06-01T00:00:00Z',window_start=lo,window_end=hi)
        results.append(build_snapshot(creators=creators,evidence=evidence,edges=[credit],snapshot_id=key,
            cohort_version='synthetic-credit-1',window_start=lo,window_end=hi,
            collected_through='2024-01-01T00:00:00Z',collected_at='2024-01-02T00:00:00Z',generated_at='2024-01-03T00:00:00Z'))
    return results


if __name__=='__main__':
    export_expanded_snapshots(snapshots(),sys.argv[1],synthetic=True)
