"""Single-platform creators and source-neutral ownership review regressions.

All evidence here is synthetic. No network requests or registry writes occur
outside temporary fixtures.
"""
import copy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from registry.__main__ import main
from registry.operations import apply_change, discover_candidate, preview_change
from registry.pipeline.evidence import build_proposals_for_record, build_review_batch, _confidence_for_link
from registry.reports import temporal_summary
from registry.review import inspect_record, review_queue
from registry.store import connect, payload, put, rows, save, validate
from scripts.review import stage4_classify_and_apply as stage4
from test_registry import reviewed_fixture, STAMP


def single_platform_fixture(platform='twitch'):
    fixture = reviewed_fixture()
    values = {
        'twitch': ('1234567', 'user_id', 'https://www.twitch.tv/synthetic_creator'),
        'tiktok': ('7654321', 'web_user_id', 'https://www.tiktok.com/@synthetic_creator'),
        'youtube': ('UC' + 'a' * 22, 'channel_id', 'https://www.youtube.com/channel/UC' + 'a' * 22),
        'ganknow': ('synthetic_creator', 'handle', 'https://ganknow.com/synthetic_creator'),
    }
    platform_id, namespace, url = values[platform]
    fixture['accounts'][0].update(platform=platform, platform_id=platform_id,
                                   id_namespace=namespace, url=url, handle='synthetic_creator')
    # The one owner profile supplies scope and ownership. No second platform,
    # hub, YouTube URL, audience size or outbound cross-link is required.
    fixture['evidence'][0].update(url=url, kind='official_profile',
        summary='Synthetic owner profile: Thai-language VStreamer presenting a virtual persona.')
    return fixture


class PlatformIndependentReviewTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        self.addCleanup(self.db.close)

    def test_twitch_only_and_tiktok_only_are_valid_reviewed_creators(self):
        for platform in ('twitch', 'tiktok', 'ganknow'):
            with self.subTest(platform=platform):
                db = connect()
                try:
                    apply_change(db, single_platform_fixture(platform))
                    validate(db)
                    report = temporal_summary(db, '2026-09-11')
                    self.assertEqual(report['inventory']['verified_personas'], 1)
                    self.assertEqual(report['persona_platform_count_distribution'], {'1': 1})
                    dossier = inspect_record(db, 'account', 'acct-a')
                    status = dossier.get('verification', {})
                    self.assertEqual(status.get('virtual_creator_status'), 'verified')
                    self.assertEqual(status.get('verified_persona_ids'), ['persona-a'])
                    self.assertEqual({a['platform'] for a in rows(db, 'accounts')}, {platform})
                finally:
                    db.close()

    def test_resolved_candidate_does_not_automatically_verify_creator_scope(self):
        fixture = single_platform_fixture('tiktok')
        fixture.pop('personas')
        fixture.pop('account_links')
        apply_change(self.db, fixture)
        cid = discover_candidate(self.db, platform='tiktok', url=fixture['accounts'][0]['url'],
            name='Synthetic', source_url=fixture['evidence'][0]['url'], observed_at=STAMP)
        put(self.db, 'candidates', dict(id=cid, account_id='acct-a', review_status='verified',
                                       reviewer='test', reviewed_at=STAMP))
        validate(self.db)
        dossier = inspect_record(self.db, 'candidate', cid)
        self.assertEqual(dossier['record']['review_status'], 'verified')
        self.assertTrue(dossier.get('verification', {}).get('account_resolved'))
        self.assertEqual(dossier.get('verification', {}).get('virtual_creator_status'), 'needs_evidence')

    def test_unresolved_candidate_is_not_rejected_for_missing_platforms(self):
        cid = discover_candidate(self.db, platform='twitch', url='https://www.twitch.tv/synthetic',
            name='Synthetic', source_url='https://www.twitch.tv/synthetic', observed_at=STAMP)
        dossier = inspect_record(self.db, 'candidate', cid)
        self.assertEqual(dossier.get('verification', {}).get('virtual_creator_status'), 'needs_evidence')
        self.assertFalse(dossier.get('verification', {}).get('account_resolved', True))

    def test_scope_queue_includes_resolved_standalone_accounts_without_legacy_issues(self):
        fixture = single_platform_fixture('twitch')
        fixture.pop('personas')
        fixture.pop('account_links')
        apply_change(self.db, fixture)
        # This view must work even if candidates/review_queue have no rows.
        from registry.review import QUEUE_KINDS
        self.assertIn('account_scope', QUEUE_KINDS)
        before = payload(self.db)
        result = review_queue(self.db, kind='account_scope', platform='twitch')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['record_id'], 'acct-a')
        self.assertEqual(result['items'][0]['status'], 'needs_evidence')
        self.assertEqual(result['items'][0]['reason'], 'account_ownership_review')
        self.assertEqual(payload(self.db), before)

    def test_scope_queue_does_not_require_youtube_or_crosslinks_to_complete(self):
        apply_change(self.db, single_platform_fixture('tiktok'))
        from registry.review import QUEUE_KINDS
        self.assertIn('account_scope', QUEUE_KINDS)
        self.assertEqual(review_queue(self.db, kind='account_scope')['total'], 0)
        done = review_queue(self.db, kind='account_scope', status='completed')
        self.assertEqual(done['total'], 1)
        self.assertEqual(done['items'][0]['status'], 'verified')

    def test_youtube_and_multiple_platforms_do_not_replace_scope_review(self):
        fixture = single_platform_fixture('youtube')
        fixture['personas'][0].update(review_status='needs_evidence', reviewer=None, reviewed_at=None)
        apply_change(self.db, fixture)
        second = single_platform_fixture('twitch')['accounts'][0]
        second['id'] = 'acct-twitch'
        put(self.db, 'accounts', second)
        put(self.db, 'account_links', dict(fixture['account_links'][0], id='link-twitch', account_id='acct-twitch'))
        validate(self.db)
        for aid in ('acct-a', 'acct-twitch'):
            with self.subTest(account=aid):
                status = inspect_record(self.db, 'account', aid).get('verification', {})
                self.assertEqual(status.get('virtual_creator_status'), 'needs_evidence')
                self.assertEqual(status.get('reason'), 'persona_scope_review')

    def test_unreviewed_ownership_link_does_not_borrow_persona_verification(self):
        fixture = single_platform_fixture('twitch')
        fixture['account_links'][0].update(review_status='needs_evidence', reviewer=None, reviewed_at=None)
        apply_change(self.db, fixture)
        status = inspect_record(self.db, 'account', 'acct-a').get('verification', {})
        self.assertEqual(status.get('virtual_creator_status'), 'needs_evidence')

    def test_single_platform_still_requires_first_party_ownership_and_thai_scope(self):
        for changed in ('secondary_ownership', 'unknown_thai', 'no_reviewer'):
            with self.subTest(changed=changed):
                fixture = single_platform_fixture('twitch')
                if changed == 'secondary_ownership':
                    fixture['evidence'][0]['kind'] = 'secondary_source'
                elif changed == 'unknown_thai':
                    fixture['personas'][0]['thai_relation'] = 'unknown'
                else:
                    fixture['personas'][0]['reviewer'] = None
                with self.assertRaises(ValueError):
                    preview_change(self.db, fixture)
                self.assertEqual(rows(self.db, 'accounts'), [])

    def test_scope_cli_is_offline_read_only_and_platform_filterable(self):
        apply_change(self.db, single_platform_fixture('twitch'))
        from registry.review import QUEUE_KINDS
        self.assertIn('account_scope', QUEUE_KINDS)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'registry.json'
            save(self.db, path)
            original = path.read_bytes()
            output = io.StringIO()
            with patch('registry.__main__.edit', side_effect=AssertionError('must be read-only')):
                with redirect_stdout(output):
                    rc = main(['--data', str(path), 'queue', '--kind', 'account_scope',
                               '--platform', 'twitch', '--status', 'all'])
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(output.getvalue())['total'], 1)
            self.assertEqual(path.read_bytes(), original)


class SourceNeutralPipelineTests(unittest.TestCase):
    def test_owner_profile_evidence_is_not_penalized_for_platform_choice(self):
        for platform in ('youtube', 'twitch', 'tiktok', 'facebook', 'instagram', 'ganknow'):
            with self.subTest(platform=platform):
                confidence = _confidence_for_link(platform=platform, x_url=None, hub_url=None,
                                                  source='owner_profile', is_agency=False)
                self.assertEqual(confidence, 'high')

    def test_twitch_source_can_propose_a_youtube_target(self):
        record = dict(source_account_id='acct-twitch', source_platform='twitch',
            source_url='https://www.twitch.tv/synthetic', source_platform_id='123',
            source='owner_profile', observed_at=STAMP,
            platform_links=[dict(platform='youtube', url='https://www.youtube.com/channel/UC' + 'z' * 22)])
        before = copy.deepcopy(record)
        proposals = build_proposals_for_record(record, {}, set(), resolve_ids=False)
        self.assertEqual(len(proposals), 1)
        source = proposals[0]['evidence_chain'][0]
        self.assertEqual(source['platform'], 'twitch')
        self.assertEqual(source['account_id'], 'acct-twitch')
        self.assertTrue(proposals[0]['needs_human_review'])
        self.assertEqual(record, before)

    def test_only_actual_seed_is_skipped_not_every_account_on_its_platform(self):
        record = dict(source_account_id='acct-twitch', source_platform='twitch',
            source_url='https://www.twitch.tv/first', source='owner_profile', observed_at=STAMP,
            platform_links=[dict(platform='twitch', url='https://www.twitch.tv/first'),
                            dict(platform='twitch', url='https://www.twitch.tv/second')])
        result = build_proposals_for_record(record, {}, set(), resolve_ids=False)
        self.assertEqual([p['url'] for p in result], ['https://www.twitch.tv/second'])

    def test_first_party_proposal_is_never_automatic_creator_verification(self):
        record = dict(youtube_account_id='acct-youtube', youtube_url='https://www.youtube.com/@synthetic',
            source='youtube_about_or_intake', observed_at=STAMP,
            platform_links=[dict(platform='twitch', url='https://www.twitch.tv/synthetic')])
        prop = build_proposals_for_record(record, {}, set(), resolve_ids=False)[0]
        self.assertEqual(prop['confidence'], 'high')
        self.assertTrue(prop['needs_human_review'])
        self.assertIsNone(prop['reviewer'])

    def test_multiple_source_records_keep_distinct_ownership_proposals(self):
        records = [dict(source_account_id=aid, source_platform='twitch',
            source_url='https://www.twitch.tv/' + aid, source='owner_profile', observed_at=STAMP,
            platform_links=[dict(platform='tiktok', url='https://www.tiktok.com/@shared')])
            for aid in ('source-a', 'source-b')]
        with tempfile.TemporaryDirectory() as tmp:
            db = connect()
            path = Path(tmp) / 'registry.json'
            save(db, path)
            db.close()
            with redirect_stdout(io.StringIO()):
                result = build_review_batch(records, data_path=path, resolve_ids=False)
        self.assertEqual(len(result['changes']), 2)

    def test_stage4_can_anchor_to_verified_twitch_without_any_youtube(self):
        fixture = single_platform_fixture('twitch')
        target = single_platform_fixture('tiktok')['accounts'][0]
        target['id'] = 'acct-target'
        fixture['accounts'].append(target)
        db = connect()
        self.addCleanup(db.close)
        apply_change(db, fixture)
        record = dict(source_account_id='acct-a', source_platform='twitch',
            source_url=fixture['accounts'][0]['url'], source='owner_profile',
            source_evidence_id='ev-official', observed_at=STAMP,
            platform_links=[dict(platform='tiktok', url=target['url'], handle=target['handle'])])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'registry.json'
            inputs = Path(tmp) / 'sources.jsonl'
            save(db, path)
            inputs.write_text(json.dumps(record) + '\n', encoding='utf-8')
            with patch.object(stage4, 'REGISTRY', path), patch.object(stage4, 'S3', inputs):
                reg, _, _, changes, high = stage4.classify()
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0]['persona_id'], 'persona-a')
            self.assertEqual(changes[0].get('source_account_id'), 'acct-a')
            self.assertEqual(len(high), 1)
            with redirect_stdout(io.StringIO()), patch.object(stage4, 'resolve_twitch', side_effect=AssertionError('no network')):
                change, skipped = stage4.build_apply(reg, high)
            self.assertEqual(len(change['account_links']), 1)
            self.assertEqual(change['account_links'][0]['review_status'], 'needs_evidence')
            self.assertIsNone(change['account_links'][0]['reviewer'])
            self.assertEqual(change['account_links'][0]['evidence_id'], 'ev-official')
            self.assertEqual(change['evidence'], [])
            with redirect_stdout(io.StringIO()):
                reviewed, _ = stage4.build_apply(reg, high, reviewer='test', reviewed_at=STAMP)
            self.assertEqual(reviewed['account_links'][0]['review_status'], 'verified')
            self.assertTrue(preview_change(db, reviewed)['valid'])
            self.assertNotIn('no_verified_youtube_persona', skipped)
            # A generated change remains a proposal; the canonical db is untouched.
            self.assertEqual(len(rows(db, 'account_links')), 1)
            self.assertTrue(preview_change(db, change)['valid'])

    def test_stage4_never_selects_one_persona_arbitrarily_from_a_shared_source(self):
        fixture = single_platform_fixture('youtube')
        fixture['personas'].append(dict(fixture['personas'][0], id='persona-b'))
        fixture['account_links'].append(dict(fixture['account_links'][0], id='link-b', persona_id='persona-b'))
        db = connect()
        self.addCleanup(db.close)
        apply_change(db, fixture)
        record = dict(youtube_account_id='acct-a', youtube_url=fixture['accounts'][0]['url'],
            source='x_profile_direct', x_url='https://x.com/shared_synthetic',
            platform_links=[])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'registry.json'
            inputs = Path(tmp) / 'sources.jsonl'
            save(db, path)
            inputs.write_text(json.dumps(record) + '\n', encoding='utf-8')
            with patch.object(stage4, 'REGISTRY', path), patch.object(stage4, 'S3', inputs):
                _, _, _, changes, _ = stage4.classify()
        self.assertTrue(changes)
        self.assertIsNone(changes[0]['persona_id'])
        self.assertEqual(changes[0].get('identity_reason'), 'ambiguous_source_persona')


if __name__ == '__main__':
    unittest.main()
