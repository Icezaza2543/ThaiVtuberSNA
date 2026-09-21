"""Fair comments/replies consumer of acknowledged campaign catalog records.

Run alongside run_expanded_campaign. Quota ledger is shared; private archive
is cached only in RAM under the campaign's single-writer lock. No search/chat.
"""
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from collector.expanded_backfill import ExpandedInteractions, InteractionTransport, interaction_job, encode
from core.file_lock import file_lock
from core.hasher import PrivacyHasher
from core.job_journal import JobJournal
from storage.expanded_sheet_batches import ExpandedSheetBatches, TAB, validated_expanded_batches
from storage.private_sheet_analytics import ARCHIVE_HEADERS
from scripts.run_expanded_campaign import ROOT, CampaignLedger, MeteredSession, now, save_json

FIRST_PASS_CAP = 15
FIRST_PASS_POLICY = 'bulk-fair-channel-year-page15-v3'


def first_pass_active(job):
    """Keep legacy checkpoints intact for a later deep pass."""
    return json.loads(job['job']).get('policy_version') == FIRST_PASS_POLICY


def refresh_quota(ledger, transport):
    """Open only a genuinely new provider day; retain every old debit/stop."""
    if ledger.summary()['window_closed']:
        ledger = CampaignLedger(ledger.path, clock=ledger.clock)
        transport.ledger = ledger
        transport.session.ledger = ledger
    return ledger


def emit_progress(root, public):
    save_json(root/'interactions_progress.json', public)
    # Background console handles can disappear when the launching UI closes.
    # The durable aggregate checkpoint remains the reporting source of truth.
    try:
        print(json.dumps(public), flush=True)
    except OSError:
        pass


class CampaignBatches(ExpandedSheetBatches):
    """Exclusive writer RAM index; remote target/readback checks remain mandatory.

Reload from the workbook on every process restart. An ambiguous write invalidates
the index and stops this worker, so stale state is never used to retry publication.
"""
    def __init__(self, store, **kwargs):
        super().__init__(store, **kwargs)
        self.records = []
        self.extent = 1
        self.tabs = store._write(store.spreadsheet.worksheets)
        self.ws = next((w for w in self.tabs if w.title == TAB), None)
        self.valid = True
        if self.ws:
            header = store._write(self.ws.get_values, 'A1:D1')
            if header != [ARCHIVE_HEADERS]:
                raise RuntimeError('Archive schema mismatch')
            for start in range(2, self.ws.row_count+1, 5000):
                rows = store._write(self.ws.get_values, f'A{start}:D{min(start+4999,self.ws.row_count)}')
                for offset, row in enumerate(rows):
                    if any(row):
                        self.extent = start+offset
                        self.records.append(dict(zip(ARCHIVE_HEADERS, row+['']*(4-len(row)))))
        accepted, rejected = validated_expanded_batches(self.records)
        if rejected:
            raise RuntimeError('Existing expanded batches require reconciliation')
        self.accepted = accepted
        self.by_job, self.states, self.seen, self.payloads = {}, {}, {}, {}
        self.tracked_jobs, self.totals, self.pseudonyms = set(), Counter(), set()
        for record in self.records:
            path = record.get('source_path', '')
            if path in accepted:
                self.by_job.setdefault(path.split('/')[1], []).append(record)
        for path, batch in accepted.items():
            self._index_batch(path, batch)

    def _index_batch(self, path, batch):
        job_id = path.split('/')[1]
        if batch['state']['sequence'] > self.states.get(job_id, {}).get('sequence', 0):
            self.states[job_id] = deepcopy(batch['state'])
        seen = self.seen.setdefault(job_id, set())
        for event in batch['events']:
            seen.add(event['record_id'])
            key = tuple(event[k] for k in ('vtuber_channel_id', 'video_id', 'source_type', 'record_id'))
            self.payloads[key] = encode(event)
            if job_id in self.tracked_jobs:
                self.totals[event.get('interaction_kind')] += 1
                self.pseudonyms.add(event['viewer_hash'])

    def track(self, job_ids):
        added = set(job_ids) - self.tracked_jobs
        self.tracked_jobs.update(added)
        for path, batch in self.accepted.items():
            if path.split('/')[1] in added:
                for event in batch['events']:
                    self.totals[event.get('interaction_kind')] += 1
                    self.pseudonyms.add(event['viewer_hash'])

    def load(self, job_id):
        if not self.valid:
            raise RuntimeError('Restart required to reconcile workbook')
        seen = self.seen.get(job_id, set())
        if len(seen) > self.max_buffer_records:
            raise RuntimeError('Job identity buffer exceeds approved bound; do not truncate')
        return deepcopy(self.states.get(job_id, {})), set(seen)

    def _job_records(self, job_id):
        if not self.valid:
            raise RuntimeError('Restart required to reconcile workbook')
        return iter(self.by_job.get(job_id, []))

    def _scan(self):
        if not self.valid:
            raise RuntimeError('Restart required to reconcile workbook')
        return self.ws, iter(self.records)

    def _occupied_extent(self, ws):
        return self.extent

    def _after_verified_write(self, ws):
        self.ws = ws

    def _allocated_cells(self):
        return sum(w.row_count*w.col_count for w in self.tabs)

    def _ensure_archive_tab(self, rows):
        # These tab objects were just refreshed through the rate-limited store.
        if self.ws is None:
            self.ws = self.store._write(self.store.spreadsheet.add_worksheet,
                                        title=TAB, rows=rows, cols=4)
            self.tabs.append(self.ws)
        elif self.ws.row_count < rows or self.ws.col_count < 4:
            self.store._write(self.ws.resize, rows=max(rows,self.ws.row_count),
                              cols=max(4,self.ws.col_count))
        return self.ws

    def _allocation_rows(self, required_rows, ws):
        # Reserve at most 2,047 extra rows, included in the live capacity check.
        # No data is dropped and populated ranges are still checked before writing.
        return ((required_rows + 2047) // 2048) * 2048

    def commit(self, job_id, expected_sequence, events, state):
        try:
            path = f'expanded-v1/{job_id}/{state["sequence"]}'
            rows = [[path, 'event', str(i), encode(event)] for i,event in enumerate(events)]
            rows.append([path,'state',str(len(rows)),encode(state)])
            digest = hashlib.sha256(encode(rows).encode()).hexdigest()
            rows.append([path,'batch_manifest',str(len(rows)),encode({'sha256':digest,'rows':len(rows)})])
            records = [dict(zip(ARCHIVE_HEADERS,r)) for r in rows]
            accepted, rejected = validated_expanded_batches(records)
            if rejected or path not in accepted:
                raise RuntimeError('Invalid incoming batch')
            for event in events:
                key = tuple(event[k] for k in ('vtuber_channel_id', 'video_id', 'source_type', 'record_id'))
                if key in self.payloads and self.payloads[key] != encode(event):
                    raise RuntimeError('Conflicting event identity; preserve committed data')
            # One live capacity/shape snapshot per batch, through the same
            # backoff/spacing path as all other Sheets requests.
            self.tabs = self.store._write(self.store.spreadsheet.worksheets)
            self.ws = next((w for w in self.tabs if w.title == TAB), None)
            result = super().commit(job_id, expected_sequence, events, state)
            if not result.get('reconciled'):
                self.records.extend(records)
                self.by_job.setdefault(job_id, []).extend(records)
                self.accepted.update(accepted)
                self._index_batch(path, accepted[path])
                self.extent += len(rows)
            return result
        except Exception:
            self.valid = False
            raise


def choose_video(records, completed, *, prepared_path=None, channel_id=None):
    """One stable representative per known year, then deepen by stable video ID."""
    done = {r['video'] for r in completed}
    if prepared_path is not None and prepared_path.exists():
        with sqlite3.connect('file:'+prepared_path.as_posix()+'?mode=ro',uri=True) as prepared:
            by_id={r['video_id']:r for r in records}
            for (video,) in prepared.execute('SELECT video FROM prepared WHERE channel=? ORDER BY rank',(channel_id,)):
                if video not in done and video in by_id:
                    return by_id[video]
    years = {r['year'] for r in completed}
    available = [r for r in records if r['video_id'] not in done]
    def key(r):
        year = (r.get('video_published_at') or 'unknown')[:4]
        return (not bool(r.get('video_published_at')), year in years, year, r['video_id'])
    return min(available, key=key) if available else None


def run(root=ROOT):
    """Caller holds private-writer.lock for this entire process invocation."""
    from config.settings import YOUTUBE_API_KEY
    from storage.private_sheet_store import PrivateSheetStore
    manifest = json.loads((root/'approved_manifest.json').read_text(encoding='utf-8'))
    hasher = PrivacyHasher()
    ledger = CampaignLedger(root/'quota.sqlite3')
    store = PrivateSheetStore()
    allocated = sum(w.row_count*w.col_count for w in store._write(store.spreadsheet.worksheets))
    started = time.monotonic()
    public = {'status':'LOADING_AUTHORIZED_ARCHIVE','at':now().isoformat(),
              'workbook_allocated_cells':allocated,'safe_remaining_cells':max(0,8000000-allocated)}
    save_json(root/'interactions_progress.json',public)
    if allocated >= 8000000:
        public['status'] = 'STORAGE_CAPACITY_STOP'
        save_json(root/'interactions_progress.json',public)
        return
    batches = CampaignBatches(store, measured_allocated_cells=allocated)
    transport = InteractionTransport(session=MeteredSession(ledger), api_key=YOUTUBE_API_KEY, ledger=ledger)
    engine = ExpandedInteractions(transport=transport,batches=batches,hasher=hasher,
                                  record_cap=FIRST_PASS_CAP)
    journal = JobJournal(root/'interaction_journal.sqlite3',poll_interval_seconds=.01)
    # The exclusive writer lock proves no previous publisher is still active;
    # the archive has already been validated above. Fence its orphaned claims
    # immediately instead of waiting on an otherwise unclaimable lease.
    journal.recover_abandoned_jobs(timeout_seconds=0)
    con = sqlite3.connect(root/'interaction_queue.sqlite3')
    con.row_factory = sqlite3.Row
    con.execute('CREATE TABLE IF NOT EXISTS jobs (channel TEXT, video TEXT, year TEXT, job TEXT, digest TEXT UNIQUE, status TEXT, turns INTEGER DEFAULT 0, PRIMARY KEY(channel,video))')
    con.commit()
    status = 'RUNNING'
    initial_digests = {r[0] for r in con.execute('SELECT digest FROM jobs')}
    batches.track(initial_digests)
    baseline = sum(batches.totals.values())
    initial_videos = con.execute('SELECT COUNT(*) FROM jobs WHERE turns>0').fetchone()[0]
    pages_acknowledged = 0
    stage_seconds = Counter()
    while True:
        if (root/'interactions.stop').exists():
            status = 'OPERATOR_STOP'
            break
        ledger = refresh_quota(ledger, transport)
        quota = ledger.summary()
        if quota['provider_stopped'] or quota['window_units'] >= 9000:
            public.update(status='QUOTA_WAIT', at=now().isoformat(), quota=quota)
            emit_progress(root, public)
            time.sleep(30)
            continue
        selection_started = time.monotonic()
        # Channels with fewer distinct attempted videos go first, then page turns.
        catalog = sqlite3.connect(root/'catalog.sqlite3')
        available_channels = [r[0] for r in catalog.execute('SELECT DISTINCT channel FROM videos ORDER BY channel')]
        counters = {r['channel']:(r['n'],r['turns']) for r in con.execute('SELECT channel,COUNT(*) n,SUM(turns) turns FROM jobs GROUP BY channel')}
        available_channels.sort(key=lambda c:(*counters.get(c,(0,0)),c))
        selected = None
        for cid in available_channels:
            active = next((row for row in con.execute(
                "SELECT * FROM jobs WHERE channel=? AND status='RUNNING' ORDER BY turns,video", (cid,))
                if first_pass_active(row)), None)
            if active:
                selected = active
                break
            done = list(con.execute('SELECT video,year FROM jobs WHERE channel=?',(cid,)))
            records = [json.loads(r[0]) for r in catalog.execute('SELECT metadata FROM videos WHERE channel=?',(cid,))]
            video = choose_video(records,done,channel_id=cid,
                prepared_path=root/'expanded-v1'/'downtime-2026-09-10'/'prepared_interactions.sqlite3')
            if video:
                job = interaction_job(cohort_version=manifest['cohort_version'],channel_id=cid,video_id=video['video_id'],
                    window_start=None,window_end=None,policy_version=FIRST_PASS_POLICY,
                    provenance='expanded-v1/bulk-history-2026-09-10/youtube-api/page15-v3',
                    combined_record_cap=FIRST_PASS_CAP)
                job['collection_mode'] = 'one_comment_page'
                digest = hashlib.sha256(encode(job).encode()).hexdigest()
                con.execute('INSERT INTO jobs(channel,video,year,job,digest,status) VALUES (?,?,?,?,?,?)',
                            (cid,video['video_id'],(video.get('video_published_at') or 'unknown')[:4],encode(job),digest,'RUNNING'))
                con.commit()
                batches.tracked_jobs.add(digest)
                selected = con.execute('SELECT * FROM jobs WHERE digest=?',(digest,)).fetchone()
                break
        catalog.close()
        if selected is None:
            status = 'WAITING_FOR_CATALOG_OR_COMPLETE'
            break
        job = json.loads(selected['job'])
        stage_seconds['selection'] += time.monotonic() - selection_started
        jid = journal.register_job(selected['channel'],selected['digest'],'comment')
        claim = journal.claim_next_job('bulk-interactions',lease_seconds=600,job_id=jid)
        if not claim:
            current = journal.get_job(jid)
            if current['state']=='FAILED':
                con.execute("UPDATE jobs SET status='ERROR' WHERE digest=?",(selected['digest'],))
                con.commit()
            else:
                time.sleep(1)
            continue
        try:
            step_started = time.monotonic()
            result = engine.step(job=job,journal=journal,claim=claim)
            stage_seconds['fetch_and_verified_commit'] += time.monotonic() - step_started
        except Exception as error:
            status = 'STORAGE_CAPACITY_STOP' if 'INSUFFICIENT' in str(error) else 'PERSISTENCE_STOP'
            import traceback
            frames = traceback.extract_tb(error.__traceback__)
            public['error_type'] = type(error).__name__
            public['error_location'] = [f'{Path(f.filename).name}:{f.lineno}:{f.name}' for f in frames]
            public['error_code'] = next((code for phrase, code in (
                ('Conflicting event identity', 'EVENT_CONFLICT'),
                ('Invalid incoming batch', 'INVALID_BATCH'),
                ('Sheets request failed', 'SHEETS_REQUEST_FAILED'),
                ('Conflicting populated batch range', 'TARGET_OCCUPIED'),
                ('Ambiguous acknowledgement', 'READBACK_MISMATCH'),
                ('Conflicting replay', 'REPLAY_CONFLICT'),
                ('Stale workbook sequence', 'STALE_SEQUENCE')) if phrase in str(error)), 'REQUIRES_INSPECTION')
            break
        state, _ = batches.load(selected['digest'])
        terminal = ('PAGE_SAMPLE_COMPLETE' if state.get('first_pass_status')=='PAGE_SAMPLE_COMPLETE' else
                    'CAP_REACHED' if state.get('count',0)>=FIRST_PASS_CAP else
                    'EXHAUSTED' if state.get('comment_status')==state.get('reply_status')=='EXHAUSTED' else
                    'PARTIAL_UNAVAILABLE' if state.get('reply_status')=='PARTIAL_UNAVAILABLE' else
                    'UNAVAILABLE' if state.get('comment_status') in {'COMMENTS_DISABLED','VIDEO_UNAVAILABLE','VIDEO_NOT_FOUND'} else 'RUNNING')
        con.execute('UPDATE jobs SET status=?,turns=turns+1 WHERE digest=?',(terminal,selected['digest']))
        con.commit()
        pages_acknowledged += int(isinstance(result, dict))
        totals = batches.totals
        report_started = time.monotonic()
        allocated = batches._allocated_cells()
        elapsed = time.monotonic()-started
        videos_processed = con.execute('SELECT COUNT(*) FROM jobs WHERE turns>0').fetchone()[0]
        deferred = con.execute("SELECT COUNT(*) FROM jobs WHERE status='RUNNING' AND json_extract(job,'$.policy_version')!=?", (FIRST_PASS_POLICY,)).fetchone()[0]
        stage_seconds['reporting'] += time.monotonic() - report_started
        public = {'at':now().isoformat(),'status':status,'videos_processed':con.execute('SELECT COUNT(*) FROM jobs WHERE turns>0').fetchone()[0],
                  'job_statuses':dict(con.execute('SELECT status,COUNT(*) FROM jobs GROUP BY status')),
                  'comments':totals['comment'],'replies':totals['reply'],'records_acknowledged':sum(totals.values()),
                  'distinct_pseudonyms':len(batches.pseudonyms),
                  'workbook_allocated_cells':allocated,'safe_remaining_cells':max(0,8000000-allocated),
                  'elapsed_seconds':round(elapsed,2),'records_per_minute':round((sum(totals.values())-baseline)*60/max(elapsed,.001),2),
                  'invocation_videos_per_hour':round((videos_processed-initial_videos)*3600/max(elapsed,.001),2),
                  'pages_acknowledged_this_invocation':pages_acknowledged,
                  'legacy_jobs_deferred':deferred,
                  'stage_seconds':{k:round(v,3) for k,v in stage_seconds.items()},
                  'quota':ledger.summary(),'selection_policy':FIRST_PASS_POLICY,
                  'combined_record_cap':FIRST_PASS_CAP,
                  'coverage_note':'One comment page, at most 15 records; replies and legacy RUNNING jobs deferred with checkpoints intact',
                  'resume_command':'python -m scripts.run_campaign_interactions'}
        emit_progress(root, public)
    public.update(status=status,at=now().isoformat(),quota=ledger.summary())
    emit_progress(root, public)
    con.close()
    return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop', action='store_true', help='Stop after the current acknowledged batch')
    args = parser.parse_args()
    if args.stop:
        (ROOT/'interactions.stop').touch()
    else:
        with file_lock(ROOT/'private-writer.lock'):
            try:
                run()
            except Exception as error:
                # No error payload, locals, identities, or credentials in diagnostics.
                path = ROOT/'interactions_progress.json'
                public = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
                public.update(status='WORKER_ERROR_STOP', at=now().isoformat(), error_type=type(error).__name__)
                code = getattr(error, 'code', None)
                if type(code) is int:
                    public['http_status'] = code
                emit_progress(ROOT, public)
                raise SystemExit(1) from None
