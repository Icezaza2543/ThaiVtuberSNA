"""Behavioral reproductions compatible with the original reviewed public APIs.

The synthetic loader patches let the original code reach the defects without an
owner's key. They are unnecessary for the repaired dependency injection path.
"""
import inspect
import json
import time
from unittest.mock import patch
import pytest
from collector.continuous_collector import ContinuousCollector
from core.hasher import PrivacyHasher
from core.job_journal import JobJournal


def make_collector(root):
    hasher = PrivacyHasher('review-synthetic-key')
    with patch('collector.continuous_collector.load_persistent_secret_key',
               return_value=hasher.secret_salt, create=True), \
         patch('collector.youtube_collector.PrivacyHasher', return_value=hasher):
        return ContinuousCollector(storage_dir=root/'events', journal_path=root/'journal.sqlite3',
                                   hasher=hasher, max_workers=1)


def token_args(method, job):
    return {'claim_token': job.get('claim_token')} if 'claim_token' in inspect.signature(method).parameters else {}


def test_review_completed_job_becomes_due_again(tmp_path):
    journal = JobJournal(tmp_path/'jobs.sqlite3')
    journal.poll_interval_seconds = 0.01
    jid = journal.register_job('CH', 'VID', 'comment')
    job = journal.claim_next_job('worker')
    assert journal.commit_job(jid, 0, **token_args(journal.commit_job, job))
    time.sleep(0.02)
    journal.register_job('CH', 'VID', 'comment')
    assert journal.claim_next_job('next') is not None


def test_review_real_extractor_exception_is_failure(tmp_path):
    c = make_collector(tmp_path)
    c.journal.register_job('CH','VID','comment')
    job = c.journal.claim_next_job('worker')
    with patch('yt_dlp.YoutubeDL') as ydl:
        ydl.return_value.__enter__.return_value.extract_info.side_effect = RuntimeError('synthetic extraction failure')
        result = c.process_single_job(job)
    assert result['status'] == 'EXTRACTION_FAILURE'
    assert c.journal.get_job(job['job_id'])['state'] == 'RETRY'


@pytest.mark.parametrize('operation', ['commit', 'fail'])
def test_review_stale_worker_rejected(tmp_path, operation):
    journal = JobJournal(tmp_path/'jobs.sqlite3')
    jid = journal.register_job('CH','VID','comment')
    old = journal.claim_next_job('old')
    journal.recover_abandoned_jobs(timeout_seconds=0)
    journal.claim_next_job('new')
    if operation == 'commit':
        result = journal.commit_job(jid, 1, **token_args(journal.commit_job, old))
    else:
        result = journal.fail_job(jid, 'EXTRACTION_FAILURE', **token_args(journal.fail_job, old))
    assert result is False
    assert journal.get_job(jid)['state'] == 'CLAIMED'


class SlowComments:
    def collect_aggregated_events(self, *args, **kwargs):
        time.sleep(0.25)
        return []


def test_review_timeout_does_not_wait_for_extraction(tmp_path):
    c = make_collector(tmp_path)
    c.comment_collector = SlowComments()
    c.journal.register_job('CH','VID','comment')
    start = time.monotonic()
    summary = c.run_bounded_cycle(max_cycle_seconds=0.01)
    assert time.monotonic()-start < 0.20
    assert summary['status_breakdown'] == {'TIMEOUT': 1}


def test_review_wrong_dataset_manifest_prevents_collection(tmp_path):
    (tmp_path/'identity_manifest.json').write_text(json.dumps({'key_fingerprint': 'wrong'}))
    with pytest.raises(RuntimeError): make_collector(tmp_path)
