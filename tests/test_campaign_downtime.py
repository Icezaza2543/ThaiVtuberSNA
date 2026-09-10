import sqlite3
from scripts.process_campaign_downtime import ordered_remaining,ROLE,DEBUT
from scripts.run_campaign_interactions import choose_video


def test_exact_dates_year_spread_and_existing_jobs():
    records=[{'video_id':'a','video_published_at':'2020'}, {'video_id':'b','video_published_at':'2020'},
             {'video_id':'c','video_published_at':'2022'}, {'video_id':'d','video_published_at':None}]
    done=[{'video':'a','year':'2020','status':'CAP_REACHED'}]
    assert [r['video_id'] for r in ordered_remaining(records,done)]==['c','b','d']


def test_worker_consumes_precomputed_order_without_replaying_done(tmp_path):
    p=tmp_path/'queue.sqlite3'
    with sqlite3.connect(p) as con:
        con.execute('CREATE TABLE prepared(rank INTEGER,channel TEXT,video TEXT)')
        con.executemany('INSERT INTO prepared VALUES (?,?,?)',[(0,'channel','b'),(1,'channel','a')])
    records=[{'video_id':'a','video_published_at':'2020'},{'video_id':'b','video_published_at':'2024'}]
    assert choose_video(records,[],prepared_path=p,channel_id='channel')['video_id']=='b'
    assert choose_video(records,[{'video':'b','year':'2024'}],prepared_path=p,channel_id='channel')['video_id']=='a'


def test_terms_are_review_signals_not_identity_assignments():
    assert DEBUT.search('เปิดตัวโมเดลใหม่ model reveal')
    assert ROLE.search('Live2D rigger credit')
    assert not ROLE.search('อเมริกา')
