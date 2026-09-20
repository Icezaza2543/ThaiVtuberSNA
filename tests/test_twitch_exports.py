import csv,tempfile,unittest
from pathlib import Path
from registry.operations import apply_change
from registry.reports import write_report
from registry.store import connect,put,rows
from test_registry import reviewed_fixture

class TwitchExportTests(unittest.TestCase):
    def test_only_qualified_twitch_links_export_and_keep_numeric_ids_as_text(self):
        db=connect();self.addCleanup(db.close)
        apply_change(db,reviewed_fixture())
        a=dict(rows(db,'accounts')[0],id='acct-twitch',platform='twitch',platform_id='9007199254740993',id_namespace='user_id',handle='fixture',url='https://www.twitch.tv/fixture')
        put(db,'accounts',a)
        put(db,'accounts',dict(a,id='acct-unreviewed',platform_id='12345',handle='unreviewed',url='https://www.twitch.tv/unreviewed'))
        put(db,'account_links',dict(rows(db,'account_links')[0],id='link-twitch',account_id=a['id']))
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);write_report(db,out,'2026-09-11')
            with (out/'twitch_accounts.csv').open(encoding='utf-8') as f:inventory=list(csv.DictReader(f))
            with (out/'verified_twitch.csv').open(encoding='utf-8') as f:verified=list(csv.DictReader(f))
            self.assertEqual(len(inventory),2);self.assertEqual(len(verified),1)
            self.assertEqual(verified[0]['platform_id'],'9007199254740993')
            self.assertEqual(verified[0]['id_namespace'],'user_id')
            write_report(db,out,'2026-09-12')
            with (out/'verified_twitch.csv').open(encoding='utf-8') as f:self.assertEqual(list(csv.DictReader(f)),[])
