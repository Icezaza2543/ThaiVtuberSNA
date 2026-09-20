import csv
from pathlib import Path
import tempfile
import unittest

from registry.operations import apply_change
from registry.reports import write_report
from registry.store import connect, put, rows
from test_registry import reviewed_fixture


class TikTokExportTests(unittest.TestCase):
    def test_only_date_qualified_personas_enter_verified_export(self):
        db = connect()
        self.addCleanup(db.close)
        apply_change(db, reviewed_fixture())
        account = dict(rows(db, 'accounts')[0], id='acct-tiktok', platform='tiktok',
                       platform_id='7388234864694543368', id_namespace='web_user_id',
                       handle='synthetic', url='https://www.tiktok.com/@synthetic')
        put(db, 'accounts', account)
        put(db, 'accounts', dict(account, id='acct-unreviewed', platform_id='7388234864694543369',
                                handle='unreviewed', url='https://www.tiktok.com/@unreviewed'))
        put(db, 'account_links', dict(rows(db, 'account_links')[0], id='link-tiktok', account_id='acct-tiktok'))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_report(db, output, '2026-09-11')
            with (output / 'tiktok_accounts.csv').open(encoding='utf-8') as stream:
                inventory = list(csv.DictReader(stream))
            with (output / 'verified_tiktok.csv').open(encoding='utf-8') as stream:
                verified = list(csv.DictReader(stream))
            self.assertEqual(len(inventory), 2)
            self.assertEqual(len(verified), 1)
            self.assertEqual(verified[0]['platform_id'], '7388234864694543368')
            self.assertEqual(verified[0]['id_namespace'], 'web_user_id')
            self.assertEqual(verified[0]['persona_id'], 'persona-a')
            self.assertEqual(inventory[1]['scope_review'], 'not_established_at_cutoff')
            write_report(db, output, '2026-09-12')
            with (output / 'verified_tiktok.csv').open(encoding='utf-8') as stream:
                self.assertEqual(list(csv.DictReader(stream)), [])
