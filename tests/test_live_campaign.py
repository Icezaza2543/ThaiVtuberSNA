from datetime import datetime, timezone, timedelta
import hashlib
import pytest
from scripts.run_expanded_campaign import CampaignLedger, MeteredSession
from scripts.run_campaign_interactions import CampaignBatches, choose_video
from collector.historical_comment_backfill import BudgetExhaustedException
from collector.expanded_backfill import encode
from tests.test_expanded_backfill import setup_interactions, Comments, next_claim, Response
from tests.test_data_security import store


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
