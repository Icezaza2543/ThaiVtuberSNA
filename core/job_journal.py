"""Durable polling journal with generation-fenced publication and recovery."""
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from config.settings import DATA_DIR

DEFAULT_JOURNAL_DB = DATA_DIR / 'real' / 'job_journal.sqlite3'
OUTCOMES = {'SUCCESS', 'EMPTY_RESULT', 'COMMENTS_DISABLED', 'LIVE_CHAT_UNAVAILABLE',
            'RATE_LIMITED', 'EXTRACTION_FAILURE', 'TIMEOUT', 'STORAGE_FAILURE', 'PARTIAL_CAPTURE'}


def utcnow():
    return datetime.now(timezone.utc)


def validate_checkpoint(checkpoint):
    if checkpoint is None:
        return
    try:
        obj = json.loads(checkpoint)
        if not isinstance(obj, dict) or set(obj) - {'continuation', 'page', 'token'}:
            raise ValueError()
        for key, value in obj.items():
            if key == 'page':
                if type(value) is not int or value < 0:
                    raise ValueError()
            elif (not isinstance(value, str) or len(value) > 4096
                  or not re.fullmatch(r'[A-Za-z0-9_+=./%-]*', value)
                  or value.startswith('UC')):
                raise ValueError()
    except (TypeError, ValueError):
        raise ValueError('Privacy violation: invalid checkpoint schema') from None


class JobJournal:
    def __init__(self, db_path=None, *, clock=utcnow, poll_interval_seconds=300):
        if poll_interval_seconds <= 0:
            raise ValueError('Polling interval must be positive')
        self.clock = clock
        self.poll_interval_seconds = poll_interval_seconds
        self.db_path = Path(db_path or DEFAULT_JOURNAL_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as con:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute("""CREATE TABLE IF NOT EXISTS collection_jobs (
                job_id TEXT PRIMARY KEY, vtuber_channel_id TEXT NOT NULL,
                video_id TEXT NOT NULL, source_type TEXT NOT NULL, state TEXT NOT NULL,
                worker_id TEXT, attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3, priority REAL NOT NULL DEFAULT 1,
                checkpoint TEXT, error_reason TEXT, records_committed INTEGER NOT NULL DEFAULT 0,
                last_attempt_at TEXT, last_success_at TEXT, next_retry_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            columns = {r[1] for r in con.execute('PRAGMA table_info(collection_jobs)')}
            for name, declaration in (
                ('claim_token', 'TEXT'), ('lease_until', 'TEXT'),
                ('next_collection_at', 'TEXT'), ('last_outcome', 'TEXT'),
                ('poll_generation', 'INTEGER NOT NULL DEFAULT 0')):
                if name not in columns:
                    con.execute(f'ALTER TABLE collection_jobs ADD COLUMN {name} {declaration}')
            con.execute('CREATE INDEX IF NOT EXISTS idx_jobs_state ON collection_jobs(state, next_retry_at)')
            con.execute('CREATE TABLE IF NOT EXISTS journal_identity (singleton INTEGER PRIMARY KEY CHECK(singleton=1), dataset TEXT NOT NULL, key_fingerprint TEXT NOT NULL)')
            for row in con.execute("SELECT job_id,last_success_at FROM collection_jobs WHERE state='COMPLETED' AND next_collection_at IS NULL").fetchall():
                last = datetime.fromisoformat(row['last_success_at']) if row['last_success_at'] else self.clock()
                con.execute('UPDATE collection_jobs SET next_collection_at=? WHERE job_id=?',
                            ((last+timedelta(seconds=poll_interval_seconds)).isoformat(), row['job_id']))

    @contextmanager
    def _get_connection(self, timeout=5):
        con = sqlite3.connect(str(self.db_path), timeout=timeout)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    def bind_identity(self, dataset, fingerprint):
        identity = (str(Path(dataset).resolve()), fingerprint)
        with self._get_connection() as con:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute('SELECT dataset, key_fingerprint FROM journal_identity').fetchone()
            if row and tuple(row) != identity:
                raise RuntimeError('Journal dataset identity mismatch')
            con.execute('INSERT OR IGNORE INTO journal_identity VALUES (1, ?, ?)', identity)

    @staticmethod
    def make_job_id(vtuber_channel_id, video_id, source_type):
        return f'{vtuber_channel_id}:{video_id}:{source_type}'

    def register_job(self, vtuber_channel_id, video_id, source_type, priority=1, max_attempts=3):
        if source_type not in {'comment', 'live_chat'} or max_attempts < 1:
            raise ValueError('Invalid job policy')
        if any(not re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in (vtuber_channel_id, video_id)):
            raise ValueError('Invalid job identity')
        job_id = self.make_job_id(vtuber_channel_id, video_id, source_type)
        now = self.clock().isoformat()
        with self._get_connection() as con:
            con.execute("""INSERT INTO collection_jobs
                (job_id, vtuber_channel_id, video_id, source_type, state,
                 max_attempts, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET priority=excluded.priority,
                updated_at=excluded.updated_at""",
                (job_id, vtuber_channel_id, video_id, source_type, max_attempts, priority, now, now))
        return job_id

    def claim_next_job(self, worker_id, lease_seconds=300, *, job_id=None):
        if lease_seconds <= 0:
            raise ValueError('Lease must be positive')
        dt = self.clock()
        now = dt.isoformat()
        token = uuid.uuid4().hex
        with self._get_connection() as con:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute("""SELECT * FROM collection_jobs
                WHERE (? IS NULL OR job_id=?) AND (state='PENDING'
                OR (state='RETRY' AND next_retry_at<=?)
                OR (state='COMPLETED' AND next_collection_at<=?))
                ORDER BY priority DESC, created_at, job_id LIMIT 1""", (job_id, job_id, now, now)).fetchone()
            if row is None:
                return None
            fresh = row['state'] == 'COMPLETED'
            attempts = 1 if fresh else row['attempts'] + 1
            con.execute("""UPDATE collection_jobs SET state='CLAIMED', worker_id=?,
                claim_token=?, lease_until=?, attempts=?, last_attempt_at=?, updated_at=?,
                poll_generation=poll_generation+? WHERE job_id=?""",
                (worker_id, token, (dt+timedelta(seconds=lease_seconds)).isoformat(),
                 attempts, now, now, int(fresh), row['job_id']))
            return dict(con.execute('SELECT * FROM collection_jobs WHERE job_id=?',
                                    (row['job_id'],)).fetchone())

    def commit_job(self, job_id, records_committed, checkpoint=None, *, claim_token,
                   outcome='SUCCESS', publish=None):
        validate_checkpoint(checkpoint)
        if outcome not in {'SUCCESS', 'EMPTY_RESULT', 'PARTIAL_CAPTURE'}:
            raise ValueError('Invalid success outcome')
        dt = self.clock()
        now = dt.isoformat()
        with self._get_connection() as con:
            # Recovery and another publisher cannot change ownership during publication.
            con.execute('BEGIN IMMEDIATE')
            row = con.execute("""SELECT * FROM collection_jobs WHERE job_id=?
                AND state='CLAIMED' AND claim_token=? AND lease_until>?""",
                (job_id, claim_token, now)).fetchone()
            if row is None:
                return False
            if publish is not None:
                publish()
            con.execute("""UPDATE collection_jobs SET state='COMPLETED',
                records_committed=?, checkpoint=?, last_success_at=?, updated_at=?,
                next_collection_at=?, next_retry_at=NULL, error_reason=NULL,
                last_outcome=?, worker_id=NULL, claim_token=NULL, lease_until=NULL
                WHERE job_id=? AND claim_token=?""",
                (records_committed, checkpoint, now, now,
                 (dt+timedelta(seconds=self.poll_interval_seconds)).isoformat(),
                 outcome, job_id, claim_token))
            return True

    def fail_job(self, job_id, error_reason, retryable=True, backoff_seconds=30, *, claim_token, publish=None):
        if error_reason not in OUTCOMES:
            error_reason = 'EXTRACTION_FAILURE'
        dt = self.clock()
        now = dt.isoformat()
        with self._get_connection() as con:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute("""SELECT attempts,max_attempts FROM collection_jobs
                WHERE job_id=? AND state='CLAIMED' AND claim_token=? AND lease_until>?""",
                (job_id, claim_token, now)).fetchone()
            if row is None:
                return False
            if publish is not None:
                publish()
            retry = retryable and row['attempts'] < row['max_attempts']
            delay = min(3600, max(0, backoff_seconds) * 2**min(row['attempts']-1, 10))
            con.execute("""UPDATE collection_jobs SET state=?, error_reason=?, last_outcome=?,
                next_retry_at=?, updated_at=?, worker_id=NULL, claim_token=NULL, lease_until=NULL
                WHERE job_id=? AND claim_token=?""",
                ('RETRY' if retry else 'FAILED', error_reason, error_reason,
                 (dt+timedelta(seconds=delay)).isoformat() if retry else None,
                 now, job_id, claim_token))
            return True

    def recover_abandoned_jobs(self, timeout_seconds=300):
        dt = self.clock()
        threshold = (dt-timedelta(seconds=timeout_seconds)).isoformat()
        with self._get_connection() as con:
            con.execute('BEGIN IMMEDIATE')
            cursor = con.execute("""UPDATE collection_jobs SET
                state=CASE WHEN attempts<max_attempts THEN 'PENDING' ELSE 'FAILED' END,
                worker_id=NULL, claim_token=NULL, lease_until=NULL, updated_at=?
                WHERE state='CLAIMED' AND
                (lease_until<=? OR (lease_until IS NULL AND last_attempt_at<=?) OR ?=0)""",
                (dt.isoformat(), dt.isoformat(), threshold, timeout_seconds))
            return cursor.rowcount

    def get_job(self, job_id):
        with self._get_connection() as con:
            row = con.execute('SELECT * FROM collection_jobs WHERE job_id=?', (job_id,)).fetchone()
            return dict(row) if row else None

    def get_summary(self):
        with self._get_connection() as con:
            rows = con.execute('SELECT state,COUNT(*) AS n,SUM(records_committed) AS records FROM collection_jobs GROUP BY state').fetchall()
            return {'states': {r['state']: r['n'] for r in rows},
                    'total_records_committed': sum(r['records'] or 0 for r in rows)}
