from datetime import datetime, timezone, timedelta
import hashlib
import json
from copy import deepcopy
import pytest
from scripts.run_expanded_campaign import CampaignLedger, MeteredSession
from scripts.run_campaign_interactions import CampaignBatches, choose_video
from collector.historical_comment_backfill import BudgetExhaustedException
from collector.expanded_backfill import encode
from tests.test_expanded_backfill import setup_interactions, Comments, next_claim, Response
from tests.test_data_security import store


@pytest.mark.parametrize('size',[0,3,15,30])
def test_one_page_sample_keeps_cursor_and_defers_replies(tmp_path,size):
    from tests.test_expanded_backfill import comment
    class FirstPage:
        calls=0
        def get(self,url,params,timeout):
            self.calls+=1
            assert url.endswith('/commentThreads')
            return Response({'items':[{'snippet':{'topLevelComment':comment(i),'totalReplyCount':2}}
                                      for i in range(size)],'nextPageToken':'synthetic-next'})
    transport=FirstPage()
    engine,job,journal,jid,_=setup_interactions(tmp_path,transport,cap=15)
    job['collection_mode']='one_comment_page'
    digest=hashlib.sha256(encode(job).encode()).hexdigest()
    jid=journal.register_job(job['channel_id'],digest,'comment')
    first=engine.step(job=job,journal=journal,claim=journal.claim_next_job('worker',job_id=jid))
    assert first['count']==min(size,15)
    assert first['first_pass_status']=='PAGE_SAMPLE_COMPLETE' and first['reply_status']=='DEFERRED'
    assert first['comment_token']=='synthetic-next' if size<=15 else first['comment_offset']==15
    # Explicit scheduler retry of the SAME digest must not fetch or write again.
    with journal._get_connection() as con:
        con.execute("UPDATE collection_jobs SET state='PENDING' WHERE job_id=?",(jid,))
    assert engine.step(job=job,journal=journal,claim=journal.claim_next_job('worker',job_id=jid))=='PAGE_SAMPLE_COMPLETE'
    assert transport.calls==1


def test_disabled_comments_are_terminal_not_retried(tmp_path):
    class Disabled:
        def get(self,*a,**kw):
            r=Response({},403);r.text='commentsDisabled';return r
    engine,job,journal,jid,_=setup_interactions(tmp_path,Disabled())
    state=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert state['comment_status']=='COMMENTS_DISABLED' and state['count']==0
    assert journal.get_job(jid)['state']=='COMPLETED'


def test_indexed_campaign_replay_stats_conflicts_and_restart(tmp_path,monkeypatch):
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    batches=CampaignBatches(store(book),measured_allocated_cells=0)
    digest=hashlib.sha256(encode(job).encode()).hexdigest()
    batches.track([digest]);engine.batches=batches
    first=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert batches.totals['comment']==3 and len(batches.pseudonyms)==3
    batch=next(iter(batches.accepted.values()));events=deepcopy(batch['events'])
    writes=book.tabs[0].writes
    assert batches.commit(digest,0,events,first)['reconciled']
    assert book.tabs[0].writes==writes and batches.totals['comment']==3
    state,seen=batches.load(digest);state['count']=999;seen.clear()
    assert batches.load(digest)[0]['count']==3 and len(batches.load(digest)[1])==3
    restarted=CampaignBatches(store(book),measured_allocated_cells=0);restarted.track([digest])
    assert restarted.totals==batches.totals and restarted.load(digest)==batches.load(digest)
    # Indexed load doesn't revalidate the entire archive or perform remote reads.
    monkeypatch.setattr(batches,'_scan',lambda:pytest.fail('archive rescan'))
    assert batches.load(digest)[0]['count']==3
    events[0]['viewer_hash']='synthetic-conflict'
    with pytest.raises(RuntimeError,match='Conflicting'):
        batches.commit(digest,0,events,first)
    assert book.tabs[0].writes==writes
    with pytest.raises(RuntimeError,match='reconcile'):batches.load(digest)


def test_refresh_quota_changes_both_references_only_after_provider_day(tmp_path):
    from types import SimpleNamespace
    from scripts.run_campaign_interactions import refresh_quota
    current=[datetime(2026,9,12,8,tzinfo=timezone.utc)]
    ledger=CampaignLedger(tmp_path/'q.sqlite',clock=lambda:current[0]);ledger.debit('interactions');ledger.stop()
    transport=SimpleNamespace(ledger=ledger,session=SimpleNamespace(ledger=ledger))
    assert refresh_quota(ledger,transport) is ledger
    with pytest.raises(BudgetExhaustedException):ledger.debit('interactions')
    current[0]+=timedelta(days=1)
    fresh=refresh_quota(ledger,transport)
    assert fresh is transport.ledger is transport.session.ledger
    assert fresh.summary()['window_units']==0 and fresh.summary()['all_windows_units']==1
    assert ledger.summary()['provider_stopped']
    fresh.debit('interactions')


def test_broken_console_does_not_stop_acknowledged_checkpoint(tmp_path,monkeypatch):
    from scripts.run_campaign_interactions import emit_progress
    def broken(*a,**k):raise OSError('closed synthetic pipe')
    monkeypatch.setattr('builtins.print',broken)
    emit_progress(tmp_path,{'status':'RUNNING','records_acknowledged':15})
    assert json.loads((tmp_path/'interactions_progress.json').read_text())['records_acknowledged']==15


def test_indexed_writer_crash_after_remote_ack_reconciles_once(tmp_path,monkeypatch):
    from storage.expanded_sheet_batches import ExpandedSheetBatches
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    batches=CampaignBatches(store(book),measured_allocated_cells=0);engine.batches=batches
    digest=hashlib.sha256(encode(job).encode()).hexdigest();batches.track([digest])
    original=ExpandedSheetBatches.commit
    def acknowledged_then_crash(self,*args):
        original(self,*args)
        raise RuntimeError('synthetic process exit after acknowledgement')
    monkeypatch.setattr(ExpandedSheetBatches,'commit',acknowledged_then_crash)
    with pytest.raises(RuntimeError):engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert batches.totals['comment']==0 and not batches.valid
    monkeypatch.setattr(ExpandedSheetBatches,'commit',original)
    restored=CampaignBatches(store(book),measured_allocated_cells=0);restored.track([digest])
    assert restored.totals['comment']==3
    batch=next(iter(restored.accepted.values()));writes=book.tabs[0].writes
    assert restored.commit(digest,0,batch['events'],batch['state'])['reconciled']
    assert restored.totals['comment']==3 and book.tabs[0].writes==writes
    # A truly incomplete remote batch must remain blocked on restart.
    book.tabs[0].cells.pop(max(book.tabs[0].cells))
    with pytest.raises(RuntimeError,match='reconciliation'):
        CampaignBatches(store(book),measured_allocated_cells=0)


def test_shared_durable_quota_and_provider_stop(tmp_path):
    clock=lambda:datetime(2026,9,10,8,tzinfo=timezone.utc)
    a=CampaignLedger(tmp_path/'q.sqlite',clock=clock)
    with a.connect() as con:
        con.execute('INSERT INTO debits VALUES (?,?,?,?)',(a.window,'catalog',8998,clock().isoformat()))
    a.debit('catalog')
    b=CampaignLedger(tmp_path/'q.sqlite',clock=clock)
    b.debit('interactions')
    with pytest.raises(BudgetExhaustedException): a.debit('catalog')
    assert b.summary()['window_units']==9000
    next_day=CampaignLedger(tmp_path/'q.sqlite',clock=lambda:clock()+timedelta(days=1))
    assert next_day.summary()['window_units']==0 and next_day.summary()['all_windows_units']==9000
    next_day.stop()
    with pytest.raises(BudgetExhaustedException): next_day.debit('interactions')


def test_provider_quota_error_is_durable(tmp_path):
    ledger=CampaignLedger(tmp_path/'q.sqlite')
    session=MeteredSession(ledger)
    session.session.get=lambda *a,**kw:Response({'error':{'errors':[{'reason':'quotaExceeded'}]}},403)
    session.get('https://www.googleapis.com/youtube/v3/playlistItems')
    assert CampaignLedger(tmp_path/'q.sqlite').summary()['provider_stopped']


def test_running_window_closes_without_reset(tmp_path):
    current=[datetime(2026,9,10,8,tzinfo=timezone.utc)]
    ledger=CampaignLedger(tmp_path/'q.sqlite',clock=lambda:current[0])
    ledger.debit('catalog')
    current[0]+=timedelta(days=1)
    assert ledger.summary()['window_closed']
    with pytest.raises(BudgetExhaustedException): ledger.debit('interactions')
    assert ledger.summary()['window_units']==1


def test_ram_archive_replay_and_restart(tmp_path):
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    engine.batches=CampaignBatches(store(book),measured_allocated_cells=0)
    result=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    digest=hashlib.sha256(encode(job).encode()).hexdigest()
    restarted=CampaignBatches(store(book),measured_allocated_cells=0)
    assert restarted.load(digest)==engine.batches.load(digest)
    engine.batches=restarted
    second=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert result['count']==3 and second['count']==4
    assert len(restarted.load(digest)[1])==4


def test_temporal_spread_and_targeted_claim(tmp_path):
    records=[{'video_id':'a','video_published_at':'2020'}, {'video_id':'b','video_published_at':'2020'},
             {'video_id':'c','video_published_at':'2024'}]
    assert choose_video(records,[{'video':'a','year':'2020'}])['video_id']=='c'
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    other=journal.register_job('other','video','comment',priority=100)
    assert journal.claim_next_job('worker',job_id=jid)['job_id']==jid
    assert journal.get_job(other)['state']=='PENDING'
