"""Adversarial regressions for the September continuous collection review."""
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from collector.continuous_collector import ContinuousCollector
from collector.youtube_collector import YouTubeCollector
from core.hasher import PrivacyHasher
from core.job_journal import JobJournal
from scripts.privacy_audit import audit_file, run_full_privacy_audit
from storage.parquet_manager import ParquetStorageManager, AGGREGATED_SCHEMA
from storage.duckdb_engine import DuckDBAnalyticsEngine


def event(viewer='one', source='comment', month='09'):
    return {'viewer_hash': PrivacyHasher('fixture-key').hash_viewer_id(viewer),
            'vtuber_channel_id': 'CH', 'video_id': 'VID', 'source_type': source,
            'first_seen': f'2026-{month}-01T00:00:00Z',
            'last_seen': f'2026-{month}-01T00:00:00Z', 'appearances': 2}


def decoded(root):
    return [row for p in root.rglob('*.parquet') for row in pq.read_table(p).to_pylist()]


class Clock:
    def __init__(self):
        self.now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    def __call__(self): return self.now
    def advance(self, seconds): self.now += timedelta(seconds=seconds)


class Comments:
    def collect_aggregated_events(self, job, max_comments=150):
        return [event()]


class BlockingComments:
    def collect_aggregated_events(self, job, max_comments=150):
        time.sleep(2)
        return [event()]


def collector(root, **kwargs):
    return ContinuousCollector(storage_dir=root/'events', journal_path=root/'jobs.sqlite3',
                               hasher=PrivacyHasher('fixture-key'), **kwargs)


@pytest.mark.parametrize('reverse', [False, True])
def test_mixed_sources_survive_repeated_batches(tmp_path, reverse):
    mgr = ParquetStorageManager(tmp_path/'events')
    batch = [event(), event(source='live_chat')]
    if reverse: batch.reverse()
    mgr.write_events(batch)
    mgr.write_events(batch)
    assert len(decoded(tmp_path/'events')) == 2
    assert {r['source_type'] for r in decoded(tmp_path/'events')} == {'comment', 'live_chat'}
    mgr.write_events(list(reversed(batch)))
    assert len(decoded(tmp_path/'events')) == 2
    for row in batch: mgr.write_events([row])
    rows = decoded(tmp_path/'events')
    assert len(rows) == 2
    assert {r['source_type'] for r in rows} == {'comment', 'live_chat'}
    assert sum(r['appearances'] for r in rows) == 4
    engine = DuckDBAnalyticsEngine(tmp_path/'db.duckdb', tmp_path/'events')
    try:
        summary = engine.get_viewer_presence_summary()[0]
        assert summary['comment_videos_seen'] == summary['live_streams_seen'] == 1
        assert summary['appearances'] == 4
    finally: engine.close()


def test_month_order_and_restart_do_not_create_partitions(tmp_path):
    mgr = ParquetStorageManager(tmp_path)
    first = mgr.write_events([event(month='09')])
    assert mgr.write_events([event(month='10')]) == first
    assert ParquetStorageManager(tmp_path).write_events([event(month='08')]) == first
    assert len(list(tmp_path.rglob('*.parquet'))) == 1
    row = decoded(tmp_path)[0]
    assert row['first_seen'].startswith('2026-08')
    assert row['last_seen'].startswith('2026-10')
    assert row['appearances'] == 2


def test_corrupt_existing_partition_is_not_overwritten(tmp_path):
    mgr = ParquetStorageManager(tmp_path)
    path = mgr.write_events([event()])
    path.write_bytes(b'corrupt-original')
    with pytest.raises(Exception): mgr.write_events([event('new')])
    assert path.read_bytes() == b'corrupt-original'


def test_concurrent_writers_preserve_both_batches(tmp_path):
    mgr = ParquetStorageManager(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda n: mgr.write_events([event(str(n))]), range(12)))
    assert len(decoded(tmp_path)) == 12


def test_migration_mixed_sources_month_duplicates_and_retry(tmp_path, monkeypatch):
    mgr = ParquetStorageManager(tmp_path)
    for month in ('08', '09'):
        path = tmp_path/'2026'/month/'VID-old.parquet'
        path.parent.mkdir(parents=True)
        pq.write_table(pa.Table.from_pylist([event(month=month), event(source='live_chat', month=month)],
                                          schema=AGGREGATED_SCHEMA), path)
    with pytest.raises(RuntimeError, match='migration'): mgr.write_events([event()])
    original = mgr._publish
    def interrupted(rows):
        original(rows)
        raise OSError('simulated crash after canonical publication')
    monkeypatch.setattr(mgr, '_publish', interrupted)
    with pytest.raises(OSError): mgr.migrate_legacy_partitions()
    assert len(list((tmp_path/'2026').rglob('*.parquet'))) == 2
    monkeypatch.setattr(mgr, '_publish', original)
    assert mgr.migrate_legacy_partitions() == 2
    assert mgr.migrate_legacy_partitions() == 0
    assert len(decoded(tmp_path)) == 2


@pytest.mark.parametrize('manifest', ['missing', 'malformed', 'wrong'])
def test_existing_dataset_identity_fails_before_mutation(tmp_path, manifest):
    ParquetStorageManager(tmp_path/'events').write_events([event()])
    if manifest != 'missing':
        (tmp_path/'identity_manifest.json').write_text('{' if manifest == 'malformed' else
                                                     json.dumps({'key_fingerprint': 'wrong'}))
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    with patch('collector.continuous_collector.YouTubeCollector') as adapter:
        with pytest.raises(RuntimeError): collector(tmp_path)
        adapter.assert_not_called()
    after = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert before == after


def test_hasher_injection_and_manifest_revalidation(tmp_path):
    c = collector(tmp_path, comment_collector=Comments())
    c.plan_and_register_jobs([{'channel_id':'CH', 'video_id':'VID'}])
    job = c.journal.claim_next_job('worker')
    assert c.process_single_job(job)['status'] == 'SUCCESS'
    with pytest.raises(RuntimeError):
        ContinuousCollector(storage_dir=tmp_path/'events', hasher=PrivacyHasher('other-key'))
    (tmp_path/'identity_manifest.json').write_text('{}')
    with pytest.raises(RuntimeError): c.run_bounded_cycle()


def test_recurring_poll_new_viewer_restart_and_backoff(tmp_path):
    clock = Clock()
    c = collector(tmp_path, clock=clock, poll_interval_seconds=10, comment_collector=Comments())
    job_id = c.journal.register_job('CH','VID','comment')
    first = c.journal.claim_next_job('w')
    assert c.process_single_job(first)['status'] == 'SUCCESS'
    c.journal.register_job('CH','VID','comment')
    assert c.journal.claim_next_job('w') is None
    clock.advance(10)
    c = collector(tmp_path, clock=clock, poll_interval_seconds=10, comment_collector=Comments())
    second = c.journal.claim_next_job('w')
    assert second['attempts'] == 1
    assert c._accept(second, {'status':'SUCCESS','events':[event(), event('new')]})['records'] == 2
    assert len(decoded(tmp_path/'events')) == 2
    clock.advance(10)
    failed = c.journal.claim_next_job('w')
    c.journal.fail_job(job_id, 'EXTRACTION_FAILURE', claim_token=failed['claim_token'])
    c.journal.register_job('CH','VID','comment')
    assert c.journal.claim_next_job('w') is None


@pytest.mark.parametrize('backend', ['ytdlp', 'api'])
def test_extractor_failure_does_not_become_empty(tmp_path, backend, caplog):
    adapter = YouTubeCollector(api_key='', hasher=PrivacyHasher('fixture-key'))
    c = collector(tmp_path, comment_collector=adapter)
    c.journal.register_job('CH','VID','comment')
    job = c.journal.claim_next_job('w')
    secret = 'UC_PRIVATE_CANARY_AUTHOR text=PRIVATE_CANARY_BODY'
    if backend == 'api':
        adapter._youtube = MagicMock()
        adapter._youtube.commentThreads.return_value.list.return_value.execute.side_effect = RuntimeError(secret)
        result = c.process_single_job(job)
    else:
        with patch('yt_dlp.YoutubeDL') as ydl:
            ydl.return_value.__enter__.return_value.extract_info.side_effect = RuntimeError(secret)
            result = c.process_single_job(job)
    assert result['status'] == 'EXTRACTION_FAILURE'
    assert c.journal.get_job(job['job_id'])['state'] == 'RETRY'
    assert secret not in caplog.text + str(result)
    assert audit_file(tmp_path/'jobs.sqlite3', ('UC_PRIVATE_CANARY_AUTHOR','PRIVATE_CANARY_BODY'))['status'] == 'PASS'


def test_successful_empty_is_completed_and_rescheduled(tmp_path):
    c = collector(tmp_path)
    c.journal.register_job('CH','VID','comment')
    job = c.journal.claim_next_job('w')
    with patch('yt_dlp.YoutubeDL') as ydl:
        ydl.return_value.__enter__.return_value.extract_info.return_value = {'comments': []}
        assert c.process_single_job(job)['status'] == 'EMPTY_RESULT'
    saved = c.journal.get_job(job['job_id'])
    assert saved['state'] == 'COMPLETED' and saved['next_collection_at']


def test_stale_worker_cannot_commit_fail_or_publish(tmp_path):
    c = collector(tmp_path)
    c.journal.register_job('CH','VID','comment')
    old = c.journal.claim_next_job('same-worker')
    c.journal.recover_abandoned_jobs(timeout_seconds=0)
    new = c.journal.claim_next_job('same-worker')
    assert old['claim_token'] != new['claim_token']
    assert not c.journal.commit_job(old['job_id'], 0, claim_token=old['claim_token'],
                                    publish=lambda: pytest.fail('stale publication'))
    assert not c.journal.fail_job(old['job_id'], 'TIMEOUT', claim_token=old['claim_token'])
    assert c._accept(old, {'status':'SUCCESS', 'events':[event()]})['status'] == 'STALE_CLAIM'
    assert not decoded(tmp_path/'events')
    assert c.journal.get_job(new['job_id'])['claim_token'] == new['claim_token']


def test_crash_after_write_before_checkpoint_reconciles_once(tmp_path, monkeypatch):
    c = collector(tmp_path, comment_collector=Comments())
    c.journal.register_job('CH','VID','comment')
    old = c.journal.claim_next_job('w')
    def crash():
        c.storage_mgr.write_events([event()])
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        c.journal.commit_job(old['job_id'], 1, claim_token=old['claim_token'], publish=crash)
    assert c.journal.get_job(old['job_id'])['state'] == 'CLAIMED'
    c.journal.recover_abandoned_jobs(timeout_seconds=0)
    new = c.journal.claim_next_job('new')
    assert c.process_single_job(new)['status'] == 'SUCCESS'
    assert len(decoded(tmp_path/'events')) == 1
    assert decoded(tmp_path/'events')[0]['appearances'] == 2


def test_deadline_terminates_extraction_and_no_late_write(tmp_path):
    c = collector(tmp_path, max_workers=1, comment_collector=BlockingComments())
    c.journal.register_job('CH','VID','comment')
    start = time.monotonic()
    summary = c.run_bounded_cycle(max_cycle_seconds=0.01)
    elapsed = time.monotonic()-start
    assert elapsed < 0.25, summary
    assert summary['status_breakdown'] == {'TIMEOUT': 1}
    time.sleep(0.3)
    assert not decoded(tmp_path/'events')
    assert c.journal.get_summary()['states'] == {'RETRY': 1}


@pytest.mark.parametrize('kind', ['safe', 'column', 'nested', 'canary'])
def test_sqlite_audit_includes_wal_and_nested_checkpoint(tmp_path, kind):
    path = tmp_path/'journal.sqlite3'
    con = sqlite3.connect(path)
    try:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA wal_autocheckpoint=0')
        con.execute('CREATE TABLE jobs (checkpoint TEXT)')
        con.commit()
        if kind == 'column': con.execute('ALTER TABLE jobs ADD COLUMN author_id TEXT')
        value = {'nested': {'text': 'private'}} if kind == 'nested' else {'continuation': 'safe'}
        if kind == 'canary': value = {'innocent': 'RAW_CANARY'}
        con.execute('INSERT INTO jobs(checkpoint) VALUES (?)', (json.dumps(value),))
        con.commit()
        before = path.read_bytes()
        result = audit_file(path, ('RAW_CANARY',))
        assert result['status'] == ('PASS' if kind == 'safe' else 'FAIL')
        assert path.read_bytes() == before
    finally: con.close()


def test_full_audit_discovers_sqlite_and_corruption(tmp_path, capsys):
    (tmp_path/'broken.sqlite3').write_bytes(b'not a database')
    assert audit_file(tmp_path/'broken.sqlite3')['status'] == 'ERROR'
    assert not run_full_privacy_audit(roots=[tmp_path])
    assert 'broken.sqlite3' in capsys.readouterr().out


def test_claim_and_recovery_serialize_with_publication(tmp_path):
    from threading import Event
    journal = JobJournal(tmp_path/'journal.sqlite3')
    jid = journal.register_job('CH', 'VID', 'comment')
    job = journal.claim_next_job('A')
    entered, release = Event(), Event()
    def publish():
        entered.set()
        assert release.wait(3)
    with ThreadPoolExecutor(2) as pool:
        committed = pool.submit(journal.commit_job, jid, 1, claim_token=job['claim_token'], publish=publish)
        assert entered.wait(3)
        recovered = pool.submit(journal.recover_abandoned_jobs, timeout_seconds=0)
        assert not recovered.done()
        release.set()
        assert committed.result() is True
        assert recovered.result() == 0


def test_simultaneous_claims_and_recovery_retry_budget(tmp_path):
    journal = JobJournal(tmp_path/'journal.sqlite3')
    jid = journal.register_job('CH', 'VID', 'comment', max_attempts=2)
    with ThreadPoolExecutor(8) as pool:
        claimed = list(pool.map(lambda i: journal.claim_next_job(str(i)), range(8)))
    assert sum(c is not None for c in claimed) == 1
    journal.recover_abandoned_jobs(timeout_seconds=0)
    assert journal.claim_next_job('again')['attempts'] == 2
    journal.recover_abandoned_jobs(timeout_seconds=0)
    assert journal.claim_next_job('exhausted') is None
    assert journal.get_job(jid)['state'] == 'FAILED'


def test_disk_full_is_retryable_and_preserves_original(tmp_path, monkeypatch):
    c = collector(tmp_path)
    c.storage_mgr.write_events([event()])
    original = decoded(tmp_path/'events')
    c.journal.register_job('CH', 'VID', 'comment')
    job = c.journal.claim_next_job('w')
    def full(*args, **kwargs): raise OSError('disk full')
    monkeypatch.setattr('storage.parquet_manager.pq.write_table', full)
    result = c._accept(job, {'status': 'SUCCESS', 'events': [event('new')]})
    assert result['status'] == 'STORAGE_FAILURE'
    assert c.journal.get_job(job['job_id'])['state'] == 'RETRY'
    assert decoded(tmp_path/'events') == original


def test_expired_lease_without_recovery_rejects_publication(tmp_path):
    clock = Clock()
    journal = JobJournal(tmp_path/'journal.sqlite3', clock=clock)
    journal.register_job('CH', 'VID', 'comment')
    job = journal.claim_next_job('w', lease_seconds=1)
    clock.advance(2)
    assert not journal.commit_job(job['job_id'], 1, claim_token=job['claim_token'],
                                  publish=lambda: pytest.fail('expired publication'))
    assert not journal.fail_job(job['job_id'], 'TIMEOUT', claim_token=job['claim_token'])


@pytest.mark.parametrize('message,status,state', [
    ('commentsDisabled', 'COMMENTS_DISABLED', 'FAILED'),
    ('HTTP 429', 'RATE_LIMITED', 'RETRY')])
def test_comment_outcomes_are_distinct(tmp_path, message, status, state):
    c = collector(tmp_path)
    c.journal.register_job('CH','VID','comment')
    job = c.journal.claim_next_job('w')
    with patch('yt_dlp.YoutubeDL') as ydl:
        ydl.return_value.__enter__.return_value.extract_info.side_effect = RuntimeError(message)
        assert c.process_single_job(job)['status'] == status
    assert c.journal.get_job(job['job_id'])['state'] == state


def test_live_page_canaries_checkpoint_and_empty_resume(tmp_path):
    c = collector(tmp_path)
    c.live_chat_adapter.api_key = 'synthetic'
    c.journal.register_job('CH','VID','live_chat')
    job = c.journal.claim_next_job('w')
    job['active_live_chat_id'] = 'synthetic-chat'
    page = MagicMock(status_code=200)
    page.json.return_value = {'items': [
        {'authorDetails': {'channelId': 'UC_RAW_CANARY', 'displayName': 'PRIVATE_NAME'},
         'snippet': {'displayMessage': 'PRIVATE_TEXT', 'publishedAt': '2026-09-01T00:00:00Z'}}
    ]*3, 'nextPageToken': 'next-token'}
    with patch('requests.get', return_value=page) as get:
        assert c.process_single_job(job, max_events=1)['records'] == 3
        assert get.call_args.kwargs['params']['maxResults'] == 200
    row = decoded(tmp_path/'events')[0]
    assert row['appearances'] == 3
    assert audit_file(tmp_path/'jobs.sqlite3', ('UC_RAW_CANARY', 'PRIVATE_NAME', 'PRIVATE_TEXT'))['status'] == 'PASS'
    for path in (tmp_path/'events').rglob('*.parquet'):
        assert audit_file(path, ('UC_RAW_CANARY','PRIVATE_NAME','PRIVATE_TEXT'))['status'] == 'PASS'
    assert json.loads(c.journal.get_job(job['job_id'])['checkpoint'])['continuation'] == 'next-token'
    from collector.extraction_worker import extract
    job['checkpoint'] = '{"continuation":"next-token"}'
    page.json.return_value = {'items': [], 'nextPageToken': 'another-token'}
    with patch('requests.get', return_value=page) as get:
        result = extract(c.live_chat_adapter, job, 1)
        assert result['status'] == 'EMPTY_RESULT'
        assert result['continuation_token'] == 'another-token'
        assert get.call_args.kwargs['params']['pageToken'] == 'next-token'


def test_raw_and_aggregate_batch_order_does_not_change_counts(tmp_path):
    aggregate = event()
    raw = dict(aggregate)
    raw['timestamp'] = raw.pop('first_seen')
    raw.pop('last_seen')
    raw.pop('appearances')
    for i, batch in enumerate(([raw, aggregate], [aggregate, raw])):
        mgr = ParquetStorageManager(tmp_path/str(i))
        mgr.write_events(batch)
        mgr.write_events(list(reversed(batch)))
        assert decoded(tmp_path/str(i))[0]['appearances'] == 2


class StartedBlockingComments:
    def __init__(self, started): self.started = started
    def collect_aggregated_events(self, job, max_comments=150):
        self.started.set()
        time.sleep(10)
        return [event()]


def test_deadline_kills_already_running_extractor(tmp_path):
    import multiprocessing
    started = multiprocessing.get_context('spawn').Event()
    c = collector(tmp_path, comment_collector=StartedBlockingComments(started))
    c.journal.register_job('CH', 'VID', 'comment')
    summary = c.run_bounded_cycle(max_cycle_seconds=2)
    assert started.is_set(), 'Fixture must enter extraction before its deadline'
    assert 2 <= summary['elapsed_seconds'] < 2.5
    assert summary['status_breakdown'] == {'TIMEOUT': 1}
    assert not decoded(tmp_path/'events')


def test_multiple_processes_and_pending_budget(tmp_path):
    c = collector(tmp_path, max_workers=2, comment_collector=Comments())
    for video in ('VID', 'VID2', 'VID3'):
        c.journal.register_job('CH', video, 'comment')
    # Fixture intentionally returns VID for every job: identity mismatch must fail.
    summary = c.run_bounded_cycle(max_jobs_to_process=2)
    assert summary['jobs_processed'] == 2
    assert summary['status_breakdown'] == {'SUCCESS': 1, 'STORAGE_FAILURE': 1}
    assert summary['journal_summary']['states']['PENDING'] == 1


def test_capped_comments_report_partial_and_poll_newest(tmp_path):
    c = collector(tmp_path)
    c.journal.register_job('CH', 'VID', 'comment')
    job = c.journal.claim_next_job('w')
    with patch('yt_dlp.YoutubeDL') as ydl:
        ydl.return_value.__enter__.return_value.extract_info.return_value = {
            'comments': [{'author_id': 'UC_FIXTURE', 'timestamp': 1}], 'comment_count': 10}
        result = c.process_single_job(job, max_events=1)
        assert result['status'] == 'PARTIAL_CAPTURE'
        assert ydl.call_args.args[0]['extractor_args']['youtube']['comment_sort'] == ['new']
    saved = c.journal.get_job(job['job_id'])
    assert saved['last_outcome'] == 'PARTIAL_CAPTURE' and saved['next_collection_at']
