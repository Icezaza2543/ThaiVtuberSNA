import copy
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from registry.store import connect, put, rows
from test_registry import STAMP, reviewed_fixture


class DataQualityTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        self.addCleanup(self.db.close)
        from registry.operations import apply_change
        apply_change(self.db, reviewed_fixture())

    def test_report_does_not_mutate_registry(self):
        from registry.quality import generate_data_quality_report
        from registry.store import payload
        before = copy.deepcopy(payload(self.db))
        report = generate_data_quality_report(self.db, as_of='2026-09-17')
        after = payload(self.db)
        self.assertEqual(before, after)
        self.assertIn('metadata', report)
        self.assertIn('evidence_freshness', report)
        self.assertIn('personas', report)
        self.assertIn('account_ownership', report)
        self.assertIn('candidates', report)
        self.assertIn('lifecycle', report)

    def test_shared_account_classified_as_review_context_not_error(self):
        from registry.quality import generate_data_quality_report
        # Add a second persona and link the same account
        put(self.db, 'personas', dict(id='persona-second', name='Second Persona', format='live2d',
                                      roles='["streamer"]', thai_relation='thai_language',
                                      review_status='verified', evidence_id='ev-official',
                                      reviewer='test', reviewed_at=STAMP))
        put(self.db, 'account_links', dict(id='link-second', persona_id='persona-second',
                                           account_id='acct-a', valid_from=None, valid_to=None,
                                           evidence_id='ev-official', review_status='verified',
                                           reviewer='test', reviewed_at=STAMP))
        report = generate_data_quality_report(self.db, as_of='2026-09-17')
        shared = report['account_ownership']['shared_accounts']
        self.assertTrue(any(s['account_id'] == 'acct-a' for s in shared))
        item = next(s for s in shared if s['account_id'] == 'acct-a')
        self.assertEqual(item['classification'], 'shared_account_review_context')

    def test_evidence_freshness_buckets(self):
        from registry.quality import generate_data_quality_report
        # ev-1 in reviewed_fixture is 2026-09-16T12:00:00+00:00, which is 1 day before 2026-09-17
        report = generate_data_quality_report(self.db, as_of='2026-09-17')
        freshness = report['evidence_freshness']['buckets']
        self.assertGreaterEqual(freshness['0_30_days'], 1)

    def test_write_data_quality_report_outputs_files(self):
        from registry.quality import write_data_quality_report
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            result = write_data_quality_report(self.db, out_dir, as_of='2026-09-17')
            self.assertTrue((out_dir / 'data-quality.json').exists())
            self.assertTrue((out_dir / 'data-quality.csv').exists())
            data = json.loads((out_dir / 'data-quality.json').read_text(encoding='utf-8'))
            self.assertIn('summary_counts', data)

    def test_rejected_account_links_metrics(self):
        from registry.quality import generate_data_quality_report
        # Add a rejected account link
        put(self.db, 'accounts', dict(id='acct-rej', platform='tiktok', platform_id='777777',
                                      id_namespace='web_user_id', handle='rej_handle',
                                      name='Rejected Account', url='https://www.tiktok.com/@rej_handle',
                                      first_discovered_at=STAMP, evidence_id='ev-official'))
        put(self.db, 'account_links', dict(id='link-rej', persona_id='persona-a', account_id='acct-rej',
                                           valid_from=None, valid_to=None, evidence_id='ev-official',
                                           review_status='rejected', reviewer='test-reviewer', reviewed_at=STAMP))
        report = generate_data_quality_report(self.db, as_of='2026-09-17')
        self.assertIn('rejected_account_links', report['summary_counts'])
        self.assertEqual(report['summary_counts']['rejected_account_links'], 1)
        self.assertIn('ownership_review_status', report['account_ownership'])
        self.assertEqual(report['account_ownership']['ownership_review_status']['rejected'], 1)


if __name__ == '__main__':
    unittest.main()

