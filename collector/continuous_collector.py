"""Bounded extraction in killable processes; fenced publication in the coordinator."""
import json
import multiprocessing
import time
import uuid
from multiprocessing.connection import wait
from pathlib import Path
from core.hasher import PrivacyHasher
from core.dataset_identity import bind_dataset, validate_dataset_identity
from core.file_lock import file_lock
from core.job_journal import JobJournal, OUTCOMES, utcnow
from core.scheduler import BaselinePriorityQueueScheduler, PSOScheduler
from storage.parquet_manager import ParquetStorageManager
from collector.youtube_collector import YouTubeCollector
from collector.live_chat_adapter import LiveChatAdapter
from collector.extraction_worker import extract, extraction_worker
from config.settings import DATA_DIR


class ContinuousCollector:
    def __init__(self, storage_dir=None, journal_path=None, max_workers=3,
                 scheduler_type='greedy', hasher=None, poll_interval_seconds=300,
                 clock=utcnow, comment_collector=None, live_chat_adapter=None):
        if max_workers < 1 or scheduler_type not in {'greedy', 'pso'}:
            raise ValueError('Invalid worker or scheduler policy')
        self.hasher = hasher or PrivacyHasher()
        self.storage_dir = Path(storage_dir or DATA_DIR / 'real' / 'events')
        self.key_fingerprint = bind_dataset(self.storage_dir, self.hasher)
        self.storage_mgr = ParquetStorageManager(self.storage_dir)
        self.journal = JobJournal(journal_path or self.storage_dir.parent / 'job_journal.sqlite3',
                                  clock=clock, poll_interval_seconds=poll_interval_seconds)
        self.journal.bind_identity(self.storage_dir, self.key_fingerprint)
        self.max_workers = max_workers
        self.scheduler_type = scheduler_type
        self.comment_collector = comment_collector or YouTubeCollector(hasher=self.hasher)
        self.live_chat_adapter = live_chat_adapter or LiveChatAdapter(hasher=self.hasher)
        for adapter in (self.comment_collector, self.live_chat_adapter):
            if hasattr(adapter, 'hasher') and adapter.hasher.secret_salt != self.hasher.secret_salt:
                raise RuntimeError('Adapter key continuity mismatch')
        self.journal.recover_abandoned_jobs()

    def plan_and_register_jobs(self, candidate_pool, sources=None):
        validate_dataset_identity(self.storage_dir, self.key_fingerprint)
        sources = sources or ['comment']
        if set(sources) - {'comment', 'live_chat'}:
            raise ValueError('Invalid collection source')
        items = []
        for candidate in candidate_pool:
            # Discovery is a separate operation; do not hide unbounded network I/O in planning.
            if not candidate.get('video_id'):
                raise ValueError('Explicit video_id required; discover videos before planning')
            items.append({'vtuber_channel_id': candidate['channel_id'],
                          'video_id': candidate['video_id'], 'is_live': False,
                          'vtuber': dict(candidate)})
        scheduler = (PSOScheduler(num_workers=self.max_workers, swarm_size=10, max_iter=15)
                     if self.scheduler_type == 'pso' and items
                     else BaselinePriorityQueueScheduler(num_workers=self.max_workers))
        scheduled = scheduler.schedule(items)
        priorities = {j.video_id: getattr(j, 'priority_score', 1) for j in scheduled}
        return [self.journal.register_job(item['vtuber_channel_id'], item['video_id'], source,
                                         priority=priorities.get(item['video_id'], 1))
                for item in items for source in sources]

    def _adapter(self, job):
        return self.comment_collector if job['source_type'] == 'comment' else self.live_chat_adapter

    def _accept(self, job, outcome):
        status = outcome.get('status', 'EXTRACTION_FAILURE')
        if status not in OUTCOMES:
            status = 'EXTRACTION_FAILURE'
        result = {'job_id': job['job_id'], 'status': status, 'records': 0}
        token = job['claim_token']
        if status in {'SUCCESS', 'EMPTY_RESULT', 'PARTIAL_CAPTURE'}:
            events = outcome.get('events', [])
            try:
                if status == 'EMPTY_RESULT' and events:
                    raise ValueError('Empty outcome has records')
                for event in events:
                    if any(event.get(key) != job[key] for key in
                           ('vtuber_channel_id', 'video_id', 'source_type')):
                        raise ValueError('Extractor returned another job identity')
                checkpoint = outcome.get('continuation_token')
                checkpoint = json.dumps({'continuation': checkpoint}) if checkpoint else job.get('checkpoint')
                def publish():
                    validate_dataset_identity(self.storage_dir, self.key_fingerprint)
                    if events:
                        self.storage_mgr.write_events(events)
                # All cooperative identity changes/writers serialize on this lock.
                with file_lock(self.storage_dir.parent / '.identity.lock'):
                    validate_dataset_identity(self.storage_dir, self.key_fingerprint)
                    committed = self.journal.commit_job(
                        job['job_id'], len(events), checkpoint, claim_token=token,
                        outcome=status, publish=publish)
                if committed:
                    result['records'] = len(events)
                else:
                    result['status'] = 'STALE_CLAIM'
            except Exception:
                result['status'] = 'STORAGE_FAILURE'
                if not self.journal.fail_job(job['job_id'], 'STORAGE_FAILURE', claim_token=token):
                    result['status'] = 'STALE_CLAIM'
        else:
            updated = self.journal.fail_job(job['job_id'], status, claim_token=token,
                                           retryable=status not in {'COMMENTS_DISABLED', 'LIVE_CHAT_UNAVAILABLE'},
                                           backoff_seconds=60 if status == 'RATE_LIMITED' else 30)
            if not updated:
                result['status'] = 'STALE_CLAIM'
        return result

    def process_single_job(self, job, max_events=150):
        """Synchronous helper for adapter tests. Use run_bounded_cycle for deadlines."""
        validate_dataset_identity(self.storage_dir, self.key_fingerprint)
        return self._accept(job, extract(self._adapter(job), job, max_events))

    def run_bounded_cycle(self, max_jobs_to_process=10, max_events_per_job=120,
                          max_cycle_seconds=60):
        if max_jobs_to_process < 0 or max_events_per_job < 1 or max_cycle_seconds <= 0:
            raise ValueError('Invalid cycle limits')
        validate_dataset_identity(self.storage_dir, self.key_fingerprint)
        start = time.monotonic()
        deadline = start + max_cycle_seconds
        context = multiprocessing.get_context('spawn')
        active = {}
        results = []
        launched = 0
        try:
            while time.monotonic() < deadline:
                while len(active) < self.max_workers and launched < max_jobs_to_process:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    job = self.journal.claim_next_job(uuid.uuid4().hex, lease_seconds=remaining+5)
                    if job is None:
                        break
                    launched += 1
                    receive, send = context.Pipe(duplex=False)
                    process = context.Process(target=extraction_worker,
                        args=(send, self._adapter(job), job, max_events_per_job), daemon=True)
                    try:
                        process.start()
                    except Exception:
                        receive.close()
                        send.close()
                        results.append(self._accept(job, {'status': 'EXTRACTION_FAILURE'}))
                        continue
                    send.close()
                    active[receive] = (process, job)
                if not active:
                    break
                ready = wait(list(active), timeout=max(0, deadline-time.monotonic()))
                for connection in ready:
                    process, job = active.pop(connection)
                    try:
                        outcome = connection.recv()
                    except (EOFError, OSError):
                        outcome = {'status': 'EXTRACTION_FAILURE'}
                    finally:
                        connection.close()
                        process.join(timeout=0)
                        if process.is_alive():
                            process.terminate()
                        process.join(timeout=0.1)
                        if not process.is_alive():
                            process.close()
                    if time.monotonic() >= deadline:
                        outcome = {'status': 'TIMEOUT'}
                    results.append(self._accept(job, outcome))
                if launched >= max_jobs_to_process and not active:
                    break
        finally:
            # Invalidate each attempt and terminate extraction; it never has access
            # to storage/journal, so even delayed OS teardown cannot publish.
            for connection, (process, job) in active.items():
                process.terminate()
            for connection, (process, job) in active.items():
                connection.close()
                process.join(timeout=0.1)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=0.1)
                if not process.is_alive():
                    process.close()
                results.append(self._accept(job, {'status': 'TIMEOUT'}))
        statuses = {}
        for result in results:
            statuses[result['status']] = statuses.get(result['status'], 0) + 1
        return {'elapsed_seconds': round(time.monotonic()-start, 6),
                'jobs_processed': len(results),
                'total_records_persisted': sum(r['records'] for r in results),
                'status_breakdown': statuses, 'journal_summary': self.journal.get_summary()}
