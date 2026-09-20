import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from registry.operations import apply_change, discover_candidate, import_legacy, twitch_discover
from registry.reports import export_bundle, temporal_summary, write_report
from registry.store import connect, edit, load, put, rows, save, validate

STAMP = '2026-09-11T00:00:00+00:00'
CID = 'UC' + 'a' * 22


def reviewed_fixture():
    return {
        'evidence': [dict(id='ev-official', url='https://example.org/announcement', kind='self_statement',
                         observed_at=STAMP, published_on='2026-09-01', sha256=None, summary='Synthetic fixture')],
        'personas': [dict(id='persona-a', name='Synthetic persona', format='png', roles='["streamer"]',
                         thai_relation='thai_language', review_status='verified', evidence_id='ev-official',
                         reviewer='test', reviewed_at=STAMP)],
        'accounts': [dict(id='acct-a', platform='youtube', platform_id=CID, id_namespace='channel_id',
                         handle='@synthetic', name='Synthetic account', url='https://www.youtube.com/channel/' + CID,
                         first_discovered_at=STAMP, evidence_id='ev-official')],
        'account_links': [dict(id='link-a', account_id='acct-a', persona_id='persona-a', valid_from='2026-01-01',
                              valid_to='2026-09-11', evidence_id='ev-official', review_status='verified',
                              reviewer='test', reviewed_at=STAMP)],
    }


def event(event_id, kind, day):
    return dict(id=event_id, persona_id='persona-a', event_type=kind, event_date=day,
                date_precision='day', evidence_id='ev-official', review_status='verified',
                reviewer='test', reviewed_at=STAMP, note='Synthetic fixture')


def activity(day, kind='live'):
    return dict(id='observation-' + day, persona_id='persona-a', account_id='acct-a',
                activity_date=day, activity_type=kind, evidence_id='ev-official',
                review_status='verified', reviewer='test', reviewed_at=STAMP)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        self.addCleanup(self.db.close)
        apply_change(self.db, reviewed_fixture())

    def test_database_rejects_duplicate_stable_id_and_foreign_keys(self):
        account = dict(rows(self.db, 'accounts')[0], id='acct-duplicate')
        with self.assertRaises(sqlite3.IntegrityError):
            put(self.db, 'accounts', account)
        with self.assertRaises(sqlite3.IntegrityError):
            put(self.db, 'lifecycle_events', dict(event('bad', 'debut', '2026-01-01'), persona_id='missing'))

    def test_unknown_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            put(self.db, 'personas', {'id': 'persona-a', 'real_name': 'Do not store'})

    def test_review_requires_explicit_public_evidence(self):
        second = dict(rows(self.db, 'personas')[0], id='persona-b')
        put(self.db, 'personas', second)
        put(self.db, 'evidence', dict(rows(self.db, 'evidence')[0], id='ev-secondary', kind='secondary_source'))
        put(self.db, 'continuity_links', dict(id='continuity', from_persona_id='persona-a', to_persona_id='persona-b',
            relation='publicly_disclosed_continuity', evidence_id='ev-secondary', review_status='verified',
            reviewer='test', reviewed_at=STAMP))
        with self.assertRaisesRegex(ValueError, 'first-party'):
            validate(self.db)

    def test_no_automatic_graduation_from_inactivity(self):
        put(self.db, 'activity_observations', activity('2026-01-01'))
        report = temporal_summary(self.db, '2026-09-11')
        self.assertEqual(report['lifecycle']['no_recent_evidence'], 1)
        self.assertEqual(report['lifecycle']['graduated'], 0)

    def test_as_of_ignores_future_graduation_and_future_activity(self):
        put(self.db, 'activity_observations', activity('2026-09-10'))
        put(self.db, 'lifecycle_events', event('grad', 'graduation', '2026-12-01'))
        self.assertEqual(temporal_summary(self.db, '2026-09-11')['lifecycle']['active_streaming'], 1)
        self.assertEqual(temporal_summary(self.db, '2026-08-01')['lifecycle']['unknown'], 1)

    def test_graduation_return_and_cross_platform_dedup(self):
        put(self.db, 'lifecycle_events', event('grad', 'graduation', '2026-05-01'))
        self.assertEqual(temporal_summary(self.db, '2026-09-11')['lifecycle']['graduated'], 1)
        put(self.db, 'activity_observations', activity('2026-09-01'))
        self.assertEqual(temporal_summary(self.db, '2026-09-11')['lifecycle']['conflict_needs_review'], 1)
        put(self.db, 'lifecycle_events', event('return', 'return', '2026-08-31'))
        put(self.db, 'accounts', dict(rows(self.db, 'accounts')[0], id='acct-twitch', platform='twitch',
                                    platform_id='12345', id_namespace='user_id', url='https://www.twitch.tv/example'))
        put(self.db, 'account_links', dict(rows(self.db, 'account_links')[0], id='link-twitch', account_id='acct-twitch'))
        report = temporal_summary(self.db, '2026-09-11')
        self.assertEqual(report['lifecycle']['active_streaming'], 1)
        self.assertEqual(report['inventory']['accounts'], 2)
        self.assertEqual(report['inventory']['verified_personas'], 1)
        self.assertEqual(report['persona_platform_count_distribution'], {'2': 1})

    def test_coarse_event_date_is_preserved_without_inventing_a_day(self):
        put(self.db, 'lifecycle_events', dict(event('grad', 'graduation', '2026'), date_precision='year'))
        report = temporal_summary(self.db, '2026-09-11')
        self.assertEqual(report['events_without_exact_day'], 1)
        self.assertEqual(report['lifecycle']['graduated'], 0)

    def test_unknown_link_dates_cannot_establish_historical_activity(self):
        put(self.db, 'account_links', {'id': 'link-a', 'valid_from': None, 'valid_to': None})
        self.assertEqual(temporal_summary(self.db, '2026-09-11')['dated_verified_personas_by_platform']['youtube'], 0)
        put(self.db, 'activity_observations', activity('2026-09-01'))
        with self.assertRaisesRegex(ValueError, 'covering its date'):
            validate(self.db)

    def test_same_date_conflicting_events_are_not_ordered_arbitrarily(self):
        put(self.db, 'lifecycle_events', event('grad', 'graduation', '2026-09-01'))
        put(self.db, 'lifecycle_events', event('return', 'return', '2026-09-01'))
        self.assertEqual(temporal_summary(self.db, '2026-09-11')['lifecycle']['conflict_needs_review'], 1)

    def test_repeated_candidate_preserves_each_discovery_source(self):
        args = dict(platform='tiktok', url='https://www.tiktok.com/@example', name='Example',
                    source_url='https://example.org/list', observed_at=STAMP)
        first = discover_candidate(self.db, **args)
        second = discover_candidate(self.db, **dict(args, source_url='https://example.org/second'))
        self.assertEqual(first, second)
        self.assertEqual(len(rows(self.db, 'candidates')), 1)
        self.assertEqual(len(rows(self.db, 'discovery_hits')), 2)

    def test_no_handle_based_cross_platform_or_recycled_handle_merge(self):
        args = dict(platform='twitch', url='https://www.twitch.tv/example', name='Example',
                    source_url='https://example.org/list', observed_at=STAMP, id_namespace='user_id')
        first = discover_candidate(self.db, **args, platform_id='111')
        second = discover_candidate(self.db, **args, platform_id='222')
        self.assertNotEqual(first, second)

    def test_atomic_failed_edit_preserves_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'registry.json'
            save(self.db, path)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                with edit(path) as db:
                    put(db, 'personas', dict(rows(db, 'personas')[0], reviewer=None))
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse((path.parent / '.registry.lock').exists())

    def test_export_checksums_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'release'
            manifest = export_bundle(self.db, output, '2026-09-11')
            for name, expected in manifest['files'].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), expected)
            with (output / 'approved_youtube.csv').open(encoding='utf-8') as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 1)
            with self.assertRaises(ValueError):
                export_bundle(self.db, output, '2026-09-11')

    def test_spreadsheet_formula_escaping(self):
        put(self.db, 'accounts', dict(rows(self.db, 'accounts')[0], name='=1+1'))
        with tempfile.TemporaryDirectory() as tmp:
            write_report(self.db, Path(tmp), '2026-09-11')
            self.assertIn("'=1+1", (Path(tmp) / 'accounts.csv').read_text(encoding='utf-8'))

    def test_twitch_bounded_partial_error_and_no_tag_leads(self):
        pages = [dict(data=[dict(user_id='123', user_login='example', user_name='Example')],
                      pagination={'cursor': 'next'}), HTTPError('https://api.twitch.tv', 429, 'Rate limit', {}, None)]
        def fetch(url, headers):
            result = pages.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        with patch.dict(os.environ, TWITCH_CLIENT_ID='synthetic', TWITCH_ACCESS_TOKEN='synthetic'):
            result = twitch_discover(self.db, 2, fetch=fetch)
        self.assertEqual(result['stop_reason'], 'http_error')
        self.assertEqual(result['accounts_seen'], 1)
        self.assertEqual(len(rows(self.db, 'candidates')), 1)
        self.assertNotIn('synthetic', json.dumps(rows(self.db, 'discovery_runs')))

    def test_twitch_page_limit_and_duplicate_ids(self):
        page = dict(data=[dict(user_id='123', user_login='example', user_name='Example')], pagination={'cursor': 'more'})
        with patch.dict(os.environ, TWITCH_CLIENT_ID='synthetic', TWITCH_ACCESS_TOKEN='synthetic'):
            result = twitch_discover(self.db, 2, fetch=lambda url, headers: page)
        self.assertEqual(result['pages'], 2)
        self.assertEqual(result['stop_reason'], 'page_limit')
        self.assertEqual(result['accounts_seen'], 1)


class ImportTests(unittest.TestCase):
    def test_baseline_identity_collisions_do_not_merge_or_certify_personas(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'baseline.csv'
            source = [dict(channel_id='UC' + letter * 22, name='Synthetic', handle='@example',
                          person_id='same_legacy_person', activity_status='active', vtuber_status='CONFIRMED',
                          agency='Independent', reference_sources='Example directory', checked_date=STAMP,
                          last_video_published_at='2026-09-01T00:00:00Z') for letter in ('a', 'b')]
            with path.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, list(source[0]))
                writer.writeheader()
                writer.writerows(source)
            db = connect()
            self.addCleanup(db.close)
            result = import_legacy(db, path, 'a' * 40)
            self.assertEqual(result['imported_accounts'], 2)
            self.assertEqual(rows(db, 'personas'), [])
            self.assertEqual(rows(db, 'lifecycle_events'), [])
            self.assertEqual(sum(r['reason'] == 'legacy_identity_collision' for r in rows(db, 'review_queue')), 2)
            with self.assertRaises(ValueError):
                import_legacy(db, path, 'a' * 40)


if __name__ == '__main__':
    unittest.main()
