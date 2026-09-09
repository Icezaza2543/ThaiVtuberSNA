from copy import deepcopy
import pytest
from tests.test_expanded_backfill import setup_interactions, Comments, next_claim
import hashlib
import json
import duckdb
from collector.expanded_backfill import encode
from tests.test_expanded_backfill import Response, comment
from storage.private_sheet_analytics import build_sheet_unified_raw, ARCHIVE_HEADERS
from scripts.build_duckdb_temporal_snapshots import build_canonical_events_view, build_expanded_window


def test_replay_compares_events_not_only_state(tmp_path):
    engine, job, journal, jid, book = setup_interactions(tmp_path, Comments())
    captured = []
    original = engine.batches.commit
    def capture(*args):
        captured.append(deepcopy(args))
        return original(*args)
    engine.batches.commit = capture
    engine.step(job=job, journal=journal, claim=next_claim(journal, jid))
    before = deepcopy(book.tabs[0].cells)
    writes = book.tabs[0].writes
    assert original(*captured[0])['reconciled'] is True
    assert book.tabs[0].cells == before and book.tabs[0].writes == writes

    changed = deepcopy(captured[0])
    changed[2][0]['viewer_hash'] = 'synthetic-conflicting-participant'
    with pytest.raises(RuntimeError, match='Conflicting replay content'):
        original(*changed)
    assert book.tabs[0].cells == before and book.tabs[0].writes == writes


def test_backfill_workbook_canonical_snapshot_end_to_end(tmp_path):
    class Shared:
        def get(self, url, params, timeout):
            return Response({'items':[{'snippet':{'topLevelComment':comment('shared'), 'totalReplyCount':0}}]})
    engine, job, journal, jid, book = setup_interactions(tmp_path, Shared())
    second = {**job, 'channel_id':'UC'+'b'*22}
    # Existing evidence for the SAME video must survive the additive expanded path.
    legacy = dict(viewer_hash='synthetic-historical-only', vtuber_channel_id=job['channel_id'],
                  video_id=job['video_id'], source_type='comment', first_seen='2020-01-01T00:00:00Z')
    engine.batches.store.write_verified_table('PRIVATE_DATA_ARCHIVE', ARCHIVE_HEADERS,
        [['data/real/events/synthetic.parquet','parquet','0',encode(legacy)]])
    engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    jid2=journal.register_job(second['channel_id'],hashlib.sha256(encode(second).encode()).hexdigest(),'comment')
    engine.step(job=second,journal=journal,claim=next_claim(journal,jid2))
    con=duckdb.connect(':memory:')
    def read():
        count=build_sheet_unified_raw(con,engine.batches.store,include_expanded=True)
        build_canonical_events_view(con)
        return count,con.execute('SELECT viewer_hash,vtuber_channel_id,interaction_time,provenance FROM canonical_events ORDER BY 1,2').fetchall()
    count,events=read()
    assert count==3 and len(events)==3
    assert any(r[0]=='synthetic-historical-only' for r in events)
    assert sum(r[3]=='synthetic:T6' for r in events)==2
    assert all(r[2].year==2020 for r in events)
    creators=[dict(id=j['channel_id'],label='Synthetic creator',review_status='approved') for j in (job,second)]
    evidence=[dict(creator_id=c['id'],evidence_id='synthetic-e'+str(i),identity_epoch_id='synthetic-epoch',
                   evidence_kind='virtual_activity',review_status='approved',source_ref='synthetic:review',
                   effective_from='2020-01-01T00:00:00Z',date_precision='exact') for i,c in enumerate(creators)]
    def snapshot():
        return build_expanded_window(con,dict(type='yearly',start='2020-01-01T00:00:00Z',end='2020-12-31T23:59:59Z'),
            creators,evidence,snapshot_id='yearly_2020',cohort_version='synthetic-1',
            collected_through='2026-01-01T00:00:00Z',collected_at='2026-01-02T00:00:00Z',generated_at='2026-01-03T00:00:00Z')
    result=snapshot()
    assert len(result['edges'])==1 and result['edges'][0]['shared_any']==1
    assert result['edges'][0]['shared_comments']==1 and result['edges'][0]['shared_live_chat']==0
    cells=deepcopy(book.tabs[0].cells)
    engine.step(job=second,journal=journal,claim=next_claim(journal,jid2))
    assert book.tabs[0].cells==cells and read()==(count,events)
    assert snapshot()==result
    # A plausible event with no manifest is never exposed.
    ws=book.tabs[0]
    original=next(row for row in ws.cells.values() if len(row)==4 and row[1]=='event')
    incomplete=deepcopy(original);incomplete[0]='expanded-v1/'+'c'*64+'/1'
    payload=json.loads(incomplete[3]);payload['viewer_hash']='synthetic-unacknowledged'
    incomplete[3]=encode(payload)
    index=max(ws.cells)+1;ws.cells[index]=incomplete;ws.row_count=index
    assert read()==(count,events) and snapshot()==result
    # Default reader/frozen selection still excludes every expanded row.
    assert build_sheet_unified_raw(con,engine.batches.store)==1
    assert con.execute("SELECT current_setting('temp_directory')").fetchone()[0]==''
    con.close()


@pytest.mark.parametrize('damage',['checksum','duplicate_manifest','wrong_row_number','state_sequence'])
def test_conflicting_or_incomplete_batches_are_not_exposed(tmp_path,damage):
    from storage.expanded_sheet_batches import validated_expanded_batches
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    records=list(engine.batches.store.read_records('PRIVATE_DATA_ARCHIVE',ARCHIVE_HEADERS))
    if damage=='checksum': records[0]['record_json']=records[0]['record_json'].replace('synthetic-comment-0','synthetic-tampered')
    elif damage=='duplicate_manifest': records.append(deepcopy(records[-1]))
    elif damage=='wrong_row_number': records[0]['row_number']='3'
    else: records[-2]['record_json']=encode({'sequence':99})
    accepted,rejected=validated_expanded_batches(records)
    assert not accepted and len(rejected)==1
