import pytest
from collector.discovery_adapter import DiscoveryAdapter
from core.discovery_review import review, approved_manifest, deduplicate_reviewed

CID = 'UC' + 's' * 22  # synthetic platform-shaped creator ID


def queue():
    return DiscoveryAdapter.prepare_review_queue([[dict(name='Synthetic artist',handle='@old',
        description='PNG artist / rigger / singer',source_url='https://example.org/synthetic')]],
        candidate_ids=['synthetic-candidate'],discovered_at='2026-01-01T00:00:00Z')[0]


def approve(item=None, **changes):
    args=dict(decision='approved',reviewer='synthetic-reviewer',reviewed_at='2026-01-02T00:00:00Z',
              reason='Synthetic explicit public showcase reviewed',source_refs=['https://example.org/synthetic'],
              roles=['artist','rigger','singer'],presentation_format='PNG',is_virtual_creator=True,
              verified_channel_id=CID)
    args.update(changes)
    return review(item or queue(),**args)


def test_queue_does_not_classify_by_keywords_or_invent_ids():
    item=queue()
    assert item['roles']==[] and item['channel_id'] is None and item['is_virtual_creator'] is None
    assert not approved_manifest([item],'synthetic-1')['channels']


def test_multirole_and_production_only_are_distinct():
    a=approve()
    b=approve(roles=['artist','rigger'],is_virtual_creator=False,verified_channel_id=None)
    b['candidate_id']='synthetic-production'
    m=approved_manifest([a,b],'synthetic-1')
    assert len(m['channels'])==1 and m['channels'][0]['roles']==['artist','rigger','singer']
    assert m['production_entities'][0]['channel_id'] is None
    assert m['production_entities'][0]['is_virtual_creator'] is False


def test_handle_changes_merge_only_reviewed_stable_ids():
    a=approve();b=approve();b['aliases']=['@new'];b['candidate_id']='synthetic-other'
    assert deduplicate_reviewed([a,b])[0]['aliases']==['@new','@old']
    x=queue();y=queue();y['candidate_id']='synthetic-unresolved'
    assert len(deduplicate_reviewed([x,y]))==2


def test_review_rejects_ambiguity_and_fabricated_ids():
    for args in [dict(verified_channel_id='@handle'),dict(roles=['VTuber']),dict(source_refs=[]),dict(is_virtual_creator=None)]:
        with pytest.raises(ValueError): approve(**args)
    with pytest.raises(ValueError): deduplicate_reviewed([approve(),approve(is_virtual_creator=False)])


def test_typed_edges_do_not_gain_audience_metrics():
    from tests.test_expanded_contracts import snapshot, activity
    edges=[dict(source='synthetic-a',target='synthetic-a',edge_type=t,
                window_start='2020-01-01T00:00:00Z',window_end='2020-12-31T23:59:59Z',
                source_ref='synthetic:credit',review_status='approved')
           for t in ['audience_overlap','collaboration','production_credit']]
    edges[0]['shared_any']=3
    s=snapshot(evidence=[activity()],edges=edges)
    assert len(s['edges'])==3
    assert sum(e.get('shared_any',0) for e in s['edges'])==3
    edges[2]['shared_any']=3
    with pytest.raises(ValueError): snapshot(evidence=[activity()],edges=edges)
