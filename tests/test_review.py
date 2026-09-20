import copy
from contextlib import redirect_stderr, redirect_stdout
import csv
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from registry.__main__ import main
from registry.operations import apply_change, discover_candidate, preview_change
from registry.reports import write_report
from registry.review import inspect_record, review_queue
from registry.store import connect, load, payload, put, rows, save
from test_registry import STAMP, activity, event, reviewed_fixture


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        self.addCleanup(self.db.close)
        apply_change(self.db, reviewed_fixture())
        self.candidate_args = dict(platform='tiktok', url='https://www.tiktok.com/@synthetic',
                                   name='ครีเอเตอร์ Synthetic', source_url='https://example.org/search',
                                   observed_at=STAMP)
        self.cid = discover_candidate(self.db, **self.candidate_args)
        for reason in ('legacy_scope_review', 'lifecycle_conflict'):
            put(self.db, 'review_queue', dict(id='issue-' + reason, account_id='acct-a',
                                             reason=reason, status='open', note='Synthetic issue'))

    def test_queue_counts_items_separately_and_prioritizes_conflicts(self):
        discover_candidate(self.db, **dict(self.candidate_args, source_url='https://example.org/other'))
        put(self.db, 'review_queue', dict(id='issue-legacy_identity_collision', account_id='acct-a',
                                         reason='legacy_identity_collision', status='open', note='Collision issue'))
        result = review_queue(self.db)
        self.assertEqual(result['total'], 4)
        self.assertEqual(result['totals_by_kind'], {'candidate': 1, 'account_issue': 3})
        self.assertEqual([r['reason'] for r in result['items']],
                         ['legacy_identity_collision', 'candidate_review', 'lifecycle_conflict', 'legacy_scope_review'])

    def test_queue_filters_literal_search_and_pagination(self):
        self.assertEqual(review_queue(self.db, platform='tiktok')['total'], 1)
        self.assertEqual(review_queue(self.db, kind='account_issue')['total'], 2)
        self.assertEqual(review_queue(self.db, query='ครีเอเตอร์ SYNTHETIC')['total'], 1)
        self.assertEqual(review_queue(self.db, query="%' OR 1=1")['total'], 0)
        first = review_queue(self.db, limit=2)
        last = review_queue(self.db, limit=2, offset=first['next_offset'])
        self.assertEqual(first['total'], 3)
        self.assertEqual(last['total'], 3)
        self.assertEqual(len(last['items']), 1)
        self.assertIsNone(last['next_offset'])
        self.assertFalse({r['id'] for r in first['items']} & {r['id'] for r in last['items']})
        self.assertEqual(review_queue(self.db, offset=100)['items'], [])
        self.assertIsNone(review_queue(self.db, offset=100)['next_offset'])

    def test_queue_completed_states_keep_original_meanings(self):
        put(self.db, 'candidates', dict(id=self.cid, review_status='rejected', reviewer='test', reviewed_at=STAMP))
        put(self.db, 'review_queue', dict(id='issue-lifecycle_conflict', status='resolved'))
        self.assertEqual(review_queue(self.db)['total'], 1)
        completed = review_queue(self.db, status='completed')
        self.assertEqual({r['status'] for r in completed['items']}, {'rejected', 'resolved'})
        self.assertEqual(review_queue(self.db, status='all')['total'], 3)

    def test_queue_rejects_invalid_bounds_and_filters(self):
        for args in ({'limit': 0}, {'limit': 501}, {'offset': -1}, {'platform': 'invalid'},
                     {'kind': 'persona'}, {'status': 'verified'}, {'priority': 99}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                review_queue(self.db, **args)

    def test_queue_priority_ordering_and_filtering(self):
        put(self.db, 'review_queue', dict(id='issue-collision', account_id='acct-a',
                                         reason='legacy_identity_collision', status='open', note='Collision'))
        result = review_queue(self.db)
        self.assertEqual(result['totals_by_priority'], {
            'identity_blocker': 1,
            'stable_id_resolution': 1,
            'lifecycle': 1,
            'coverage_expansion': 1,
        })
        items = result['items']
        # 1. legacy_identity_collision -> Priority 1
        # 2. stable-ID candidate -> Priority 2
        # 3. lifecycle_conflict -> Priority 3
        # 4. legacy_scope_review -> Priority 4
        self.assertEqual([item['priority'] for item in items], [1, 2, 3, 4])
        self.assertEqual([item['priority_class'] for item in items],
                         ['identity_blocker', 'stable_id_resolution', 'lifecycle', 'coverage_expansion'])
        self.assertEqual([item['reason'] for item in items],
                         ['legacy_identity_collision', 'candidate_review', 'lifecycle_conflict', 'legacy_scope_review'])

        p1 = review_queue(self.db, priority=1)
        self.assertEqual(p1['total'], 1)
        self.assertEqual(p1['items'][0]['id'], 'issue-collision')
        self.assertEqual(p1['items'][0]['priority_class'], 'identity_blocker')

        p2 = review_queue(self.db, priority='stable_id_resolution')
        self.assertEqual(p2['total'], 1)
        self.assertEqual(p2['items'][0]['id'], self.cid)
        self.assertEqual(p2['items'][0]['priority_class'], 'stable_id_resolution')

        p3 = review_queue(self.db, priority=3)
        self.assertEqual(p3['total'], 1)
        self.assertEqual(p3['items'][0]['id'], 'issue-lifecycle_conflict')
        self.assertEqual(p3['items'][0]['priority_class'], 'lifecycle')

        p4 = review_queue(self.db, priority=4)
        self.assertEqual(p4['total'], 1)
        self.assertEqual(p4['items'][0]['id'], 'issue-legacy_scope_review')
        self.assertEqual(p4['items'][0]['priority_class'], 'coverage_expansion')

    def test_queue_unknown_reason_does_not_crash_sorting(self):
        real_rows = rows(self.db, 'review_queue')
        custom_issue = dict(id='issue-unknown-reason', account_id='acct-a',
                            reason='unlisted_custom_reason', status='open', note='Custom reason')
        with patch('registry.review.rows', side_effect=lambda db, tbl: (real_rows + [custom_issue]) if tbl == 'review_queue' else rows(db, tbl)):
            result = review_queue(self.db)
            self.assertTrue(any(item['id'] == 'issue-unknown-reason' for item in result['items']))

    def test_queue_detects_candidate_already_in_accounts(self):
        acc = rows(self.db, 'accounts')[0]
        cid = discover_candidate(self.db, platform=acc['platform'], url=acc['url'],
                                 name='Existing Account Candidate', source_url='https://example.org/dup',
                                 observed_at=STAMP)
        result = review_queue(self.db, query='Existing Account Candidate')
        self.assertEqual(result['total'], 1)
        item = result['items'][0]
        self.assertEqual(item['matched_account_id'], acc['id'])
        self.assertIn(f"Stable account already present: {acc['id']}", item['note'])

    def test_candidate_dossier_preserves_sources_without_matching_handles(self):
        discover_candidate(self.db, **dict(self.candidate_args, source_url='https://example.org/other'))
        put(self.db, 'accounts', dict(rows(self.db, 'accounts')[0], id='acct-unrelated',
            platform='tiktok', platform_id='123', id_namespace='synthetic_id',
            name=self.candidate_args['name'], url=self.candidate_args['url']))
        before = payload(self.db)
        dossier = inspect_record(self.db, 'candidate', self.cid)
        self.assertEqual(dossier['record']['review_status'], 'needs_evidence')
        self.assertEqual(dossier['tables']['accounts'], [])
        self.assertEqual(dossier['tables']['personas'], [])
        self.assertEqual(len(dossier['tables']['discovery_hits']), 2)
        self.assertEqual(len(dossier['tables']['discovery_runs']), 2)
        self.assertEqual({r['url'] for r in dossier['tables']['evidence']},
                         {'https://example.org/search', 'https://example.org/other'})
        self.assertEqual(payload(self.db), before)

    def test_dossier_uses_explicit_resolution_and_keeps_legacy_claims_separate(self):
        cid = discover_candidate(self.db, platform='youtube', url='https://www.youtube.com/@synthetic',
                                  name='Synthetic', source_url='https://example.org/crosslink', observed_at=STAMP)
        put(self.db, 'candidates', dict(id=cid, account_id='acct-a'))
        put(self.db, 'evidence', dict(id='ev-legacy', url='https://example.org/legacy', kind='legacy_import',
                                     observed_at=STAMP, summary='Synthetic legacy claim'))
        put(self.db, 'legacy_claims', dict(id='legacy-a', account_id='acct-a', source_status='CONFIRMED',
            source_activity='active', source_agency='Independent', source_names='Synthetic source',
            source_checked_at=STAMP, evidence_id='ev-legacy'))
        dossier = inspect_record(self.db, 'candidate', cid)
        self.assertEqual([r['id'] for r in dossier['tables']['accounts']], ['acct-a'])
        self.assertEqual([r['id'] for r in dossier['tables']['personas']], ['persona-a'])
        self.assertEqual(dossier['record']['review_status'], 'needs_evidence')
        self.assertEqual(dossier['tables']['legacy_claims'][0]['source_activity'], 'active')
        self.assertEqual({r['kind'] for r in dossier['tables']['evidence']},
                         {'self_statement', 'secondary_source', 'legacy_import'})
        self.assertEqual(len(dossier['tables']['review_queue']), 2)

    def test_persona_dossier_keeps_event_precision_and_link_review_status(self):
        put(self.db, 'lifecycle_events', dict(event('coarse-event', 'debut', '2026-01'), date_precision='month'))
        put(self.db, 'account_links', dict(id='link-a', review_status='needs_evidence'))
        dossier = inspect_record(self.db, 'persona', 'persona-a')
        self.assertEqual(dossier['tables']['lifecycle_events'][0]['event_date'], '2026-01')
        self.assertEqual(dossier['tables']['lifecycle_events'][0]['date_precision'], 'month')
        self.assertEqual(dossier['tables']['account_links'][0]['review_status'], 'needs_evidence')
        self.assertEqual(dossier['tables']['accounts'][0]['id'], 'acct-a')

    def test_dossier_rejects_unknown_record_and_kind(self):
        for kind, record_id in [('candidate', 'missing'), ('account', self.cid), ('invalid', 'acct-a')]:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                inspect_record(self.db, kind, record_id)

    def test_dossier_includes_direct_activity_even_without_a_reviewed_link(self):
        put(self.db, 'personas', dict(rows(self.db, 'personas')[0], id='persona-other'))
        put(self.db, 'activity_observations', dict(activity('2026-09-01'),
            persona_id='persona-other', review_status='needs_evidence'))
        for kind, record_id in [('account', 'acct-a'), ('persona', 'persona-other')]:
            with self.subTest(kind=kind):
                observations = inspect_record(self.db, kind, record_id)['tables']['activity_observations']
                self.assertEqual(len(observations), 1)
                self.assertEqual(observations[0]['review_status'], 'needs_evidence')

    def test_candidate_report_retains_ids_status_and_escapes_formula_names(self):
        put(self.db, 'candidates', dict(id=self.cid, name='=1+1'))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_report(self.db, output, '2026-09-12')
            with (output / 'candidates.csv').open(encoding='utf-8', newline='') as stream:
                candidates = list(csv.DictReader(stream))
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]['id'], self.cid)
            self.assertEqual(candidates[0]['name'], "'=1+1")
            self.assertEqual(candidates[0]['review_status'], 'needs_evidence')
            self.assertIn('candidates.csv', (output / 'README.md').read_text(encoding='utf-8'))

    def test_preview_reports_net_field_changes_and_restores_database(self):
        before = payload(self.db)
        change = {'personas': [{'id': 'persona-a', 'name': 'Updated persona'}],
                  'accounts': [{'id': 'acct-a'}],
                  'lifecycle_events': [dict(event('new-event', 'debut', '2026'), date_precision='year')]}
        original_change = copy.deepcopy(change)
        result = preview_change(self.db, change)
        self.assertEqual(result['counts'], {'added': 1, 'updated': 1, 'unchanged': 1})
        update = next(r for r in result['changes'] if r['action'] == 'updated')
        self.assertEqual(update['fields'], {'name': {'before': 'Synthetic persona', 'after': 'Updated persona'}})
        self.assertEqual(payload(self.db), before)
        self.assertEqual(change, original_change)
        apply_change(self.db, change)
        self.assertEqual(preview_change(self.db, change)['counts'], {'added': 0, 'updated': 0, 'unchanged': 3})

    def test_preview_restores_partial_changes_after_validation_and_sql_errors(self):
        before = payload(self.db)
        for invalid in ({'personas': [{'id': 'persona-a', 'reviewer': None}]},
                        {'personas': [{'id': 'persona-a', 'name': 'Changed'}],
                         'account_links': [{'id': 'link-a', 'persona_id': 'missing'}]},
                        {'not_a_table': []}):
            with self.subTest(change=invalid), self.assertRaises((ValueError, sqlite3.Error)):
                preview_change(self.db, invalid)
            self.assertEqual(payload(self.db), before)
        self.assertEqual(preview_change(self.db, {})['changes'], [])

    def test_preview_counts_repeated_row_id_once_using_final_value(self):
        change = {'personas': [{'id': 'persona-a', 'name': 'Intermediate'},
                               {'id': 'persona-a', 'name': 'Synthetic persona'}]}
        self.assertEqual(preview_change(self.db, change)['counts'], {'added': 0, 'updated': 0, 'unchanged': 1})


class ReviewCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'registry.json'
        db = connect()
        try:
            apply_change(db, reviewed_fixture())
            save(db, self.path)
        finally:
            db.close()
        self.change_file = self.path.parent / 'change.json'

    def run_cli(self, *args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(['--data', str(self.path), *args])
        self.assertEqual(code, 0)
        return json.loads(output.getvalue())

    def write_change(self, change):
        self.change_file.write_text(json.dumps(change), encoding='utf-8')

    def test_read_only_commands_and_dry_run_do_not_write_or_acquire_lock(self):
        before, modified = self.path.read_bytes(), self.path.stat().st_mtime_ns
        self.write_change({'personas': [{'id': 'persona-a', 'name': 'New name'}]})
        with patch('registry.__main__.edit', side_effect=AssertionError('Read-only command requested a write')):
            self.assertEqual(self.run_cli('queue', '--platform', 'tiktok')['total'], 0)
            self.assertEqual(self.run_cli('inspect', 'account', 'acct-a')['record']['id'], 'acct-a')
            preview = self.run_cli('apply', '--file', str(self.change_file), '--dry-run')
        self.assertTrue(preview['dry_run'])
        self.assertEqual(preview['counts']['updated'], 1)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mtime_ns, modified)
        self.assertFalse((self.path.parent / '.registry.lock').exists())
        self.run_cli('apply', '--file', str(self.change_file))
        db = load(self.path)
        try:
            self.assertEqual(rows(db, 'personas')[0]['name'], 'New name')
        finally:
            db.close()

    def test_failed_dry_run_reports_error_and_preserves_file(self):
        before = self.path.read_bytes()
        self.write_change({'personas': [{'id': 'persona-a', 'reviewer': None}]})
        error = io.StringIO()
        with redirect_stderr(error), self.assertRaises(SystemExit) as raised:
            self.run_cli('apply', '--file', str(self.change_file), '--dry-run')
        self.assertEqual(raised.exception.code, 1)
        self.assertIn('requires a reviewer', error.getvalue())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.path.parent / '.registry.lock').exists())

    def test_dry_run_missing_registry_does_not_create_it(self):
        missing = self.path.parent / 'new' / 'registry.json'
        self.write_change({})
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(['--data', str(missing), 'apply', '--file', str(self.change_file), '--dry-run'])
        self.assertEqual(raised.exception.code, 1)
        self.assertFalse(missing.parent.exists())


if __name__ == '__main__':
    unittest.main()
