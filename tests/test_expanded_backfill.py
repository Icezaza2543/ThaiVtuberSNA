import hashlib
from copy import deepcopy
import pytest
from collector.expanded_backfill import (ExpandedCatalog, RequestLedger, ExpandedInteractions,
    InteractionTransport, interaction_job, encode)
from core.hasher import PrivacyHasher
from core.job_journal import JobJournal
from storage.expanded_sheet_batches import ExpandedSheetBatches
from tests.test_data_security import FakeBook, store

CID = 'UC' + 's' * 22


class Response:
    def __init__(self, body, status=200): self.body, self.status_code, self.text = body, status, ''
    def json(self): return self.body


class Pages:
    def __init__(self, videos): self.videos, self.calls = videos, []
    def get(self, url, params, timeout):
        self.calls.append(deepcopy(params)); offset = int(params.get('pageToken', '0'))
        items = self.videos[offset:offset+50]
        return Response({'items':items, **({'nextPageToken':str(offset+50)} if offset+50<len(self.videos) else {})})


def video(i):
    return {'snippet': {'title':f'Synthetic title {i}', 'publishedAt':'2026-01-01T00:00:00Z'},
            'contentDetails': {'videoId':f'synthetic-video-{i}', 'videoPublishedAt':'2024-01-01T00:00:00Z'}}


def catalog(tmp_path, videos, channels=None, budget=100):
    session = Pages(videos)
    ledger = RequestLedger(tmp_path/'quota.sqlite', {'catalog':budget,'interactions':50})
    manifest = {'dataset_version':'expanded-v1','cohort_version':'synthetic-1',
                'channels':channels or [{'channel_id':CID,'review_status':'approved'}]}
    return ExpandedCatalog(tmp_path/'catalog.sqlite',manifest,session=session,api_key='synthetic',ledger=ledger), session


@pytest.mark.parametrize('size,expected',[(1001,'CAP_REACHED'),(137,'PLAYLIST_EXHAUSTED')])
def test_cap_exhaustion_and_idempotent_catalog(tmp_path,size,expected):
    engine, session = catalog(tmp_path,[video(i) for i in range(size)])
    while engine.step(): pass
    s=engine.states()[CID]
    assert s['catalog_status']==expected and s['accessible_count']==min(size,1000)
    assert len(engine.records(CID))==min(size,1000)
    assert engine.records(CID)[0]['title']=='Synthetic title 0'
    assert s['coverage_complete_from'] is None and s['comment_status']=='NOT_STARTED'
    if size>1000: assert s['token']=='1000'
    count=len(session.calls)
    engine2,_=catalog(tmp_path,[video(i) for i in range(size)])
    assert engine2.step() is None and len(session.calls)==count


def test_all_tiers_round_robin_and_no_2020_cutoff(tmp_path):
    channels=[{'channel_id':'UC'+str(i)*22,'review_status':'approved','priority':tier} for i,tier in enumerate(['S','A','C','D'])]
    videos=[video(i) for i in range(60)]
    videos[0]['contentDetails']['videoPublishedAt']='2019-01-01T00:00:00Z'
    engine,_=catalog(tmp_path,videos,channels)
    turns=[engine.step()[0] for _ in range(4)]
    assert len(set(turns))==4
    assert all(s['catalog_status']=='PENDING' and s['ordering']=='NON_MONOTONIC' for s in engine.states().values())


def test_inaccessible_duplicate_and_persistent_budget(tmp_path):
    items=[video(0),video(0),{'snippet':{'title':'Deleted video'}}]+[video(i) for i in range(1,80)]
    engine,_=catalog(tmp_path,items,budget=1)
    engine.step(); result=engine.step()[1]
    assert result['catalog_status']=='BUDGET_STOP' and result['duplicates']==1 and result['inaccessible']==1
    resumed,_=catalog(tmp_path,items,budget=1)
    assert resumed.step()[1]['catalog_status']=='BUDGET_STOP'
    assert resumed.ledger.spent('catalog')==1
    with pytest.raises(ValueError): RequestLedger(tmp_path/'quota.sqlite',{'catalog':2})


def test_accessible_video_with_unknown_date_still_counts_toward_cap(tmp_path):
    item=video(0);item['contentDetails'].pop('videoPublishedAt')
    engine,_=catalog(tmp_path,[item])
    assert engine.step()[1]['accessible_count']==1
    row=engine.records(CID)[0]
    assert row['video_published_at'] is None and row['timestamp_quality']=='missing'


def setup_interactions(tmp_path, session, cap=500, allocated=0):
    book=FakeBook(); batches=ExpandedSheetBatches(store(book),measured_allocated_cells=allocated)
    ledger=RequestLedger(tmp_path/'quota.sqlite',{'interactions':10})
    transport=InteractionTransport(session=session,api_key='synthetic',ledger=ledger)
    engine=ExpandedInteractions(transport=transport,batches=batches,hasher=PrivacyHasher('synthetic-test-key'),record_cap=cap)
    job=interaction_job(cohort_version='synthetic-1',channel_id=CID,video_id='synthetic-video',
        window_start='2020',window_end='2026',policy_version='synthetic-1',provenance='synthetic:T6',combined_record_cap=cap)
    journal=JobJournal(tmp_path/'journal.sqlite')
    jid=journal.register_job(CID,hashlib.sha256(encode(job).encode()).hexdigest(),'comment')
    return engine,job,journal,jid,book


def comment(i):
    return {'id':f'synthetic-comment-{i}','snippet':{'authorChannelId':{'value':f'synthetic-viewer-{i}'},'publishedAt':'2020-01-01T00:00:00Z'}}


class Comments:
    def get(self,url,params,timeout):
        if url.endswith('/comments'): return Response({'items':[comment('reply')]})
        return Response({'items':[{'snippet':{'topLevelComment':comment(i),'totalReplyCount':int(i==0)}} for i in range(3)]})


def next_claim(journal,jid):
    # Synthetic explicit scheduler turn; no recurring production job is started.
    with journal._get_connection() as con:
        con.execute("UPDATE collection_jobs SET state='PENDING' WHERE job_id=?",(jid,))
    return journal.claim_next_job('synthetic-worker')


def test_comments_replies_and_cap_are_separate(tmp_path):
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments(),cap=4)
    first=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert first['count']==3 and first['comment_status']=='EXHAUSTED' and first['reply_status']=='PENDING'
    second=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert second['count']==4 and second['live_chat_status']=='NOT_REQUESTED'
    state,seen=engine.batches.load(hashlib.sha256(encode(job).encode()).hexdigest())
    assert len(seen)==4
    assert len(book.tabs)==1
    local=b''.join(p.read_bytes() for p in tmp_path.iterdir() if p.is_file())
    assert b'synthetic-viewer' not in local and b'viewer_hash' not in local


def test_combined_cap_stops_mid_page_without_claiming_complete(tmp_path):
    engine,job,journal,jid,_=setup_interactions(tmp_path,Comments(),cap=2)
    state=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert state['count']==2 and state['comment_offset']==2 and state['comment_status']=='PARTIAL_CAP'
    assert state['reply_status']=='PENDING'


def test_stale_claim_never_writes(tmp_path):
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    old=next_claim(journal,jid);journal.recover_abandoned_jobs(timeout_seconds=0)
    journal.claim_next_job('new-worker')
    assert engine.step(job=job,journal=journal,claim=old)=='STALE_CLAIM'
    assert not book.tabs


@pytest.mark.parametrize('allocated,error',[(None,'NOT_MEASURED'),(9_900_000,'INSUFFICIENT')])
def test_capacity_rejected_before_write(tmp_path,allocated,error):
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments(),allocated=allocated)
    with pytest.raises(RuntimeError,match=error): engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert not book.tabs


def test_crash_after_workbook_write_reconciles_without_duplicates(tmp_path):
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    original=engine.batches.commit
    def crash(*args): original(*args);raise RuntimeError('synthetic crash after acknowledgement')
    engine.batches.commit=crash
    with pytest.raises(RuntimeError): engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    written=len(book.tabs[0].cells)
    engine.batches.commit=original
    state,seen=engine.batches.load(hashlib.sha256(encode(job).encode()).hexdigest())
    assert state['count']==3 and len(seen)==3
    result=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert result['count']==4 and len(book.tabs[0].cells)>written


def test_catalog_expired_token_reenumerates_without_duplicate_rows(tmp_path):
    engine,session=catalog(tmp_path,[video(i) for i in range(70)])
    engine.step()
    get=session.get
    session.get=lambda *a,**kw: Response({},400)
    assert engine.step()[1]['token'] is None
    session.get=get
    while engine.step(): pass
    assert len(engine.records(CID))==70 and engine.ledger.spent('catalog')==4


def test_extraction_failure_is_retryable_not_empty(tmp_path):
    class Failed:
        def get(self,*a,**kw): return Response({},500)
    engine,job,journal,jid,book=setup_interactions(tmp_path,Failed())
    assert engine.step(job=job,journal=journal,claim=next_claim(journal,jid))=='EXTRACTION_FAILURE'
    assert journal.get_job(jid)['state']=='RETRY'
    state,_=engine.batches.load(hashlib.sha256(encode(job).encode()).hexdigest())
    assert state['comment_status']=='EXTRACTION_FAILURE' and state['count']==0


def test_quota_stops_before_request_and_chat_remains_unavailable(tmp_path):
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    for _ in range(10): engine.transport.ledger.debit('interactions')
    assert engine.step(job=job,journal=journal,claim=next_claim(journal,jid))=='BUDGET_STOP'
    state,_=engine.batches.load(hashlib.sha256(encode(job).encode()).hexdigest())
    assert state['comment_status']=='BUDGET_STOP' and state['count']==0
    assert engine.transport.historical_chat_capability()=={'status':'LIVE_CHAT_UNAVAILABLE','reason':'ARCHIVED_REPLAY_NOT_IMPLEMENTED','requests':0}


def test_cell_size_limit_and_memory_bound_never_truncate(tmp_path):
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    engine.batches.max_cell_chars=10
    with pytest.raises(RuntimeError,match='Cell limit'): engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert not book.tabs


def test_hmac_key_change_fails_before_request(tmp_path):
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    spent=engine.transport.ledger.spent('interactions')
    engine.hasher=PrivacyHasher('different-synthetic-key')
    with pytest.raises(RuntimeError,match='identity mismatch'):
        engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert engine.transport.ledger.spent('interactions')==spent


def test_reply_unavailable_preserves_top_level_completion(tmp_path):
    class Unavailable(Comments):
        def get(self,url,params,timeout):
            if url.endswith('/comments'): return Response({},404)
            return super().get(url,params,timeout)
    engine,job,journal,jid,_=setup_interactions(tmp_path,Unavailable())
    engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    state=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert state['comment_status']=='EXHAUSTED' and state['reply_status']=='REPLIES_UNAVAILABLE'
    assert state['count']==3 and state['live_chat_status']=='NOT_REQUESTED'


def test_expired_comment_token_resume_deduplicates_records(tmp_path):
    class Expired:
        def __init__(self): self.expired=False
        def get(self,url,params,timeout):
            if params.get('pageToken')=='old':
                self.expired=True
                response=Response({},400);response.text='invalidPageToken';return response
            items=[{'snippet':{'topLevelComment':comment(i),'totalReplyCount':0}} for i in range(2 if self.expired else 1)]
            return Response({'items':items, **({} if self.expired else {'nextPageToken':'old'})})
    engine,job,journal,jid,_=setup_interactions(tmp_path,Expired())
    first=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert first['comment_token']=='old'
    second=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert second['comment_token'] is None
    third=engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert third['count']==2 and third['comment_status']=='EXHAUSTED'


def test_crash_before_ack_leaves_cursor_and_data_unchanged(tmp_path):
    engine,job,journal,jid,book=setup_interactions(tmp_path,Comments())
    original=engine.batches.commit
    engine.batches.commit=lambda *a: (_ for _ in ()).throw(RuntimeError('synthetic before write'))
    with pytest.raises(RuntimeError): engine.step(job=job,journal=journal,claim=next_claim(journal,jid))
    assert not book.tabs
    engine.batches.commit=original
    assert engine.step(job=job,journal=journal,claim=next_claim(journal,jid))['count']==3
