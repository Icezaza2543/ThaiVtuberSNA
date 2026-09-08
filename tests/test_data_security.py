"""Real regressions for the single-workbook boundary, using synthetic identities only."""
import csv
import json
import re
import sqlite3
import pytest
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from core.data_security import (SPREADSHEET_ID, SPREADSHEET_TITLE, assert_sheet_rows,
                                assert_public, inspect_blob, inspect_database)
from core.hasher import PrivacyHasher
from core.storage_boundary import REPO_ROOT, require_synthetic_local_path, require_t20_sandbox
from scripts.migrate_private_data_plane import recover_historical
from storage.private_sheet_store import PrivateSheetStore
from storage.private_sheet_analytics import build_sheet_unified_raw
from scripts.build_duckdb_temporal_snapshots import build_canonical_events_view


class FakeTab:
    def __init__(self,title,rows=10,cols=2):
        self.title=title; self.row_count=rows; self.col_count=cols
        self.cells={}; self.writes=0; self.corrupt=False
    def get_values(self,a1):
        numbers=[int(x) for x in re.findall(r'\d+',a1)]
        result=[self.cells.get(i,[])[:] for i in range(numbers[0],numbers[1]+1)]
        while result and not result[-1]:result.pop()
        if self.corrupt and self.writes and result: result[-1]=['corrupted']
        return result or [[]]  # Actual gspread blank range representation.
    def update(self,*,range_name,values,value_input_option):
        assert value_input_option=='RAW'
        start=int(re.search(r'\d+',range_name)[0]);self.writes+=1
        for i,row in enumerate(values):self.cells[start+i]=row[:]
    def resize(self,*,rows,cols):self.row_count=rows;self.col_count=cols
    def freeze(self,**kwargs):pass
    def format(self,*args):pass


class FakeBook:
    id=SPREADSHEET_ID;title=SPREADSHEET_TITLE
    def __init__(self):self.tabs=[]
    def worksheets(self):return self.tabs
    def worksheet(self,title):return next(t for t in self.tabs if t.title==title)
    def add_worksheet(self,*,title,rows,cols):
        t=FakeTab(title,rows,cols);self.tabs.append(t);return t


def store(book):return PrivateSheetStore(book,known_secrets=(),request_interval=0)


def test_exact_workbook_only():
    b=FakeBook();b.id='unauthorized'
    with pytest.raises(RuntimeError):store(b)


def test_blank_header_resume_raw_formulas_and_no_duplicate_rows():
    b=FakeBook();s=store(b)
    rows=[['synthetic_hash','=1+1'],['synthetic_other','+123']]
    first=s.write_verified_table('VIEWER_INDEX',['viewer_hash','display_name'],rows,batch_size=2)
    tab=b.tabs[0]; writes=tab.writes
    second=s.write_verified_table('VIEWER_INDEX',['viewer_hash','display_name'],rows,batch_size=2)
    assert first==second and tab.writes==writes
    assert len(tab.cells)==3 and tab.cells[2][1]=='=1+1'


def test_conflicting_private_records_are_never_overwritten():
    b=FakeBook();s=store(b)
    s.write_verified_table('ALL_COMMENTERS',['authorDisplayName'],[['original']])
    with pytest.raises(RuntimeError,match='Conflicting'):
        s.write_verified_table('ALL_COMMENTERS',['authorDisplayName'],[['different']])
    assert b.tabs[0].cells[2]==['original']


def test_failed_readback_does_not_claim_verified():
    b=FakeBook();t=b.add_worksheet(title='VIEWER_INDEX',rows=3,cols=1);t.corrupt=True
    with pytest.raises(RuntimeError,match='readback'):
        store(b).write_verified_table('VIEWER_INDEX',['viewer_hash'],[['synthetic']])


def test_shorter_sync_preserves_extra_records_and_rejects_false_verified_count():
    b=FakeBook();s=store(b)
    s.write_verified_table('VIEWER_INDEX',['viewer_hash'],[['one'],['two']])
    with pytest.raises(RuntimeError,match='Additional'):
        s.write_verified_table('VIEWER_INDEX',['viewer_hash'],[['one']])
    assert b.tabs[0].cells[3]==['two']


def test_private_rows_cannot_be_synced_to_aggregate_control_tabs():
    with pytest.raises(ValueError,match='LEVEL_B'):
        store(FakeBook()).write_verified_table('NETWORK_RESULT',['viewer_hash'],[['synthetic']])


@pytest.mark.parametrize('headers,rows',[
    (['private_key'],[]),(['Metric','Value'],[['password','synthetic-value']]),
    (['record_json'],[[json.dumps({'refresh_token':'synthetic-value'})]]),
    (['viewer_hash','text'],[['synthetic','message']]),
    (['record_json'],[[json.dumps({'comment_text':'message'})]])])
def test_credentials_and_message_text_forbidden_inside_private_workbook(headers,rows):
    with pytest.raises(ValueError):assert_sheet_rows(headers,rows)


def test_known_hmac_secret_forbidden_but_fingerprint_allowed():
    secret='synthetic-test-secret-do-not-use'
    with pytest.raises(ValueError):assert_sheet_rows(['value'],[[secret]],[secret])
    assert_sheet_rows(['hmac_fingerprint'],[['safe-public-digest']],[secret])


def test_private_sheet_is_allowed_public_viewer_rows_are_not():
    assert_sheet_rows(['viewer_hash'],[['synthetic']])
    with pytest.raises(ValueError):assert_public({'nested':[{'viewer_hash':'synthetic'}]})
    assert_public({'vtuber_channel_id':'public-channel','video_id':'public-video','shared_any':3})


def test_compressed_parquet_and_sqlite_are_decoded(tmp_path):
    p=tmp_path/'events.parquet'
    pq.write_table(pa.Table.from_pylist([{'viewer_hash':'synthetic'}]),p,compression='gzip')
    assert inspect_blob(str(p),p.read_bytes())[0]=='PRIVATE_DATA'
    db=tmp_path/'journal.sqlite3';con=sqlite3.connect(db)
    con.execute('PRAGMA journal_mode=WAL');con.execute('CREATE TABLE staging (payload TEXT)')
    con.execute('INSERT INTO staging VALUES (?)',[json.dumps({'viewer_hash':'synthetic'})]);con.commit()
    assert inspect_database(db)[0]=='PRIVATE_DATA'
    con.close()


def test_recovery_preserves_duplicates_and_never_hashes_handles_or_names(tmp_path):
    p=tmp_path/'recovery.csv'
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['authorDisplayName','authorChannelUrl','comment_count','last_seen'])
        w.writerows([['same','https://youtube.com/@synthetic-one',2,'2026'],
                     ['same','https://youtube.com/@synthetic-one',3,'2026'],
                     ['same','https://youtube.com/@synthetic-two',1,'2026']])
    original,index,stats=recover_historical(p)
    assert len(original)==3 and len(index)==2 and all(not r[0] for r in index)
    assert stats['duplicate_url_rows']==1 and stats['unmatched_handle_candidates']==2
    assert index[0][6]==3  # Repeated snapshots cannot be summed as disjoint events.


def test_recovery_hashes_only_verified_raw_id_with_injected_key(tmp_path):
    cid='UC'+'s'*22;p=tmp_path/'verified.csv'
    p.write_text('authorChannelUrl\nhttps://youtube.com/channel/'+cid+'\n')
    hasher=PrivacyHasher('synthetic-only-key')
    _,rows,stats=recover_historical(p,hasher=hasher)
    assert rows[0][0]==hasher.hash_viewer_id(cid) and stats['viewer_hash_identities_reconstructed']==1


def test_sheet_analytics_preserves_sources_precedence_and_has_no_disk_database(tmp_path):
    records=[]
    for tier,viewer,source in [('observations','superseded','comment'),('deep_observations','retained','comment'),
                                ('deep_observations','retained','live_chat')]:
        records.append({'source_path':'data/temporal/'+tier+'/fixture.parquet','source_table':'parquet',
                        'row_number':'1','record_json':json.dumps({'viewer_hash':viewer,'vtuber_channel_id':'channel',
                        'video_id':'video','source_type':source,'interaction_at':'2026-01-01T00:00:00Z'})})
    class Archive:
        def read_records(self,*args):return iter(records)
    con=duckdb.connect(':memory:')
    assert build_sheet_unified_raw(con,Archive())==3
    build_canonical_events_view(con)
    assert con.execute('SELECT viewer_hash,source_type FROM canonical_events ORDER BY source_type').fetchall()==[
        ('retained','comment'),('retained','live_chat')]
    assert con.execute("SELECT current_setting('temp_directory')").fetchone()[0]==''
    con.close()
    con=duckdb.connect(str(tmp_path/'forbidden.duckdb'))
    with pytest.raises(ValueError,match='in-memory'):build_sheet_unified_raw(con,Archive())
    con.close()


def test_legacy_production_private_storage_and_t20_are_blocked(tmp_path):
    with pytest.raises(RuntimeError):require_synthetic_local_path(REPO_ROOT/'data/events')
    with pytest.raises(RuntimeError):require_t20_sandbox(REPO_ROOT)
    require_synthetic_local_path(tmp_path)


def test_legacy_purge_and_merge_entrypoints_cannot_delete_tabs():
    from pathlib import Path
    for name in ('purge_sheets_pii.py','merge_reilim_into_all_commenters.py','sync_to_google_sheets.py'):
        source=(REPO_ROOT/'scripts'/name).read_text()
        assert 'del_worksheet' not in source and '.clear(' not in source
