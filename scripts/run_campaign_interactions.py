"""Fair comments/replies consumer of acknowledged campaign catalog records.

Run alongside run_expanded_campaign. Quota ledger is shared; private archive
is cached only in RAM under the campaign's single-writer lock. No search/chat.
"""
from collections import Counter
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


class CampaignBatches(ExpandedSheetBatches):
    """Exclusive writer RAM index; remote target/readback checks remain mandatory.

Reload from the workbook on every process restart. An ambiguous write invalidates
the index and stops this worker, so stale state is never used to retry publication.
"""
    def __init__(self, store, **kwargs):
        super().__init__(store, **kwargs)
        self.records = []
        self.extent = 1
        self.ws = next((w for w in store.spreadsheet.worksheets() if w.title == TAB), None)
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
        _, rejected = validated_expanded_batches(self.records)
        if rejected:
            raise RuntimeError('Existing expanded batches require reconciliation')

    def _scan(self):
        if not self.valid:
            raise RuntimeError('Restart required to reconcile workbook')
        return self.ws, iter(self.records)

    def _occupied_extent(self, ws):
        return self.extent

    def commit(self, job_id, expected_sequence, events, state):
        try:
            result = super().commit(job_id, expected_sequence, events, state)
            if not result.get('reconciled'):
                path = f'expanded-v1/{job_id}/{state["sequence"]}'
                rows = [[path, 'event', str(i), encode(event)] for i,event in enumerate(events)]
                rows.append([path,'state',str(len(rows)),encode(state)])
                digest = hashlib.sha256(encode(rows).encode()).hexdigest()
                rows.append([path,'batch_manifest',str(len(rows)),encode({'sha256':digest,'rows':len(rows)})])
                self.records.extend(dict(zip(ARCHIVE_HEADERS,r)) for r in rows)
                self.extent += len(rows)
                self.ws = next(w for w in self.store.spreadsheet.worksheets() if w.title == TAB)
            return result
        except Exception:
            self.valid = False
            raise


def choose_video(records, completed):
    """One newest representative per known year, then deepen by stable video ID."""
    done = {r['video'] for r in completed}
    years = {r['year'] for r in completed}
    available = [r for r in records if r['video_id'] not in done]
    def key(r):
        year = (r.get('video_published_at') or 'unknown')[:4]
        return (year in years, year == 'unkn', year, r['video_id'])
    return min(available, key=key) if available else None


def run(root=ROOT):
    from config.settings import YOUTUBE_API_KEY
    from storage.private_sheet_store import PrivateSheetStore
    manifest = json.loads((root/'approved_manifest.json').read_text(encoding='utf-8'))
    hasher = PrivacyHasher()
    ledger = CampaignLedger(root/'quota.sqlite3')
    store = PrivateSheetStore()
    allocated = sum(w.row_count*w.col_count for w in store.spreadsheet.worksheets())
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
    engine = ExpandedInteractions(transport=transport,batches=batches,hasher=hasher)
    journal = JobJournal(root/'interaction_journal.sqlite3',poll_interval_seconds=.01)
    journal.recover_abandoned_jobs()
    con = sqlite3.connect(root/'interaction_queue.sqlite3')
    con.row_factory = sqlite3.Row
    con.execute('CREATE TABLE IF NOT EXISTS jobs (channel TEXT, video TEXT, year TEXT, job TEXT, digest TEXT UNIQUE, status TEXT, turns INTEGER DEFAULT 0, PRIMARY KEY(channel,video))')
    con.commit()
    status = 'RUNNING'
    baseline = None
    while True:
        quota = ledger.summary()
        if quota['provider_stopped'] or quota['window_units'] >= 9000:
            status = 'QUOTA_STOP'
            break
        # Channels with fewer distinct attempted videos go first, then page turns.
        catalog = sqlite3.connect(root/'catalog.sqlite3')
        available_channels = [r[0] for r in catalog.execute('SELECT DISTINCT channel FROM videos ORDER BY channel')]
        counters = {r['channel']:(r['n'],r['turns']) for r in con.execute('SELECT channel,COUNT(*) n,SUM(turns) turns FROM jobs GROUP BY channel')}
        available_channels.sort(key=lambda c:(*counters.get(c,(0,0)),c))
        selected = None
        for cid in available_channels:
            active = con.execute("SELECT * FROM jobs WHERE channel=? AND status='RUNNING' ORDER BY turns,video LIMIT 1",(cid,)).fetchone()
            if active:
                selected = active
                break
            done = list(con.execute('SELECT video,year FROM jobs WHERE channel=?',(cid,)))
            records = [json.loads(r[0]) for r in catalog.execute('SELECT metadata FROM videos WHERE channel=?',(cid,))]
            video = choose_video(records,done)
            if video:
                job = interaction_job(cohort_version=manifest['cohort_version'],channel_id=cid,video_id=video['video_id'],
                    window_start=None,window_end=None,policy_version='bulk-fair-channel-year-v1',
                    provenance='expanded-v1/bulk-history-2026-09-10/youtube-api')
                digest = hashlib.sha256(encode(job).encode()).hexdigest()
                con.execute('INSERT INTO jobs(channel,video,year,job,digest,status) VALUES (?,?,?,?,?,?)',
                            (cid,video['video_id'],(video.get('video_published_at') or 'unknown')[:4],encode(job),digest,'RUNNING'))
                con.commit()
                selected = con.execute('SELECT * FROM jobs WHERE digest=?',(digest,)).fetchone()
                break
        catalog.close()
        if selected is None:
            status = 'WAITING_FOR_CATALOG_OR_COMPLETE'
            break
        job = json.loads(selected['job'])
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
            result = engine.step(job=job,journal=journal,claim=claim)
        except Exception as error:
            status = 'STORAGE_CAPACITY_STOP' if 'INSUFFICIENT' in str(error) else 'PERSISTENCE_STOP'
            break
        state, _ = batches.load(selected['digest'])
        terminal = ('CAP_REACHED' if state.get('count',0)>=500 else
                    'EXHAUSTED' if state.get('comment_status')==state.get('reply_status')=='EXHAUSTED' else
                    'PARTIAL_UNAVAILABLE' if state.get('reply_status')=='PARTIAL_UNAVAILABLE' else
                    'UNAVAILABLE' if state.get('comment_status') in {'COMMENTS_DISABLED','VIDEO_UNAVAILABLE','VIDEO_NOT_FOUND'} else 'RUNNING')
        con.execute('UPDATE jobs SET status=?,turns=turns+1 WHERE digest=?',(terminal,selected['digest']))
        con.commit()
        accepted, rejected = validated_expanded_batches(batches.records)
        digests = {r[0] for r in con.execute('SELECT digest FROM jobs')}
        events = [e for path,b in accepted.items() if path.split('/')[1] in digests for e in b['events']]
        totals = Counter(e.get('interaction_kind') for e in events)
        if baseline is None:
            baseline = 0
        allocated = sum(w.row_count*w.col_count for w in store.spreadsheet.worksheets())
        elapsed = time.monotonic()-started
        public = {'at':now().isoformat(),'status':status,'videos_processed':con.execute('SELECT COUNT(*) FROM jobs WHERE turns>0').fetchone()[0],
                  'job_statuses':dict(con.execute('SELECT status,COUNT(*) FROM jobs GROUP BY status')),
                  'comments':totals['comment'],'replies':totals['reply'],'records_acknowledged':len(events),
                  'distinct_pseudonyms':len({e['viewer_hash'] for e in events}),
                  'workbook_allocated_cells':allocated,'safe_remaining_cells':max(0,8000000-allocated),
                  'elapsed_seconds':round(elapsed,2),'records_per_minute':round(len(events)*60/max(elapsed,.001),2),
                  'quota':ledger.summary(),'selection_policy':'bulk-fair-channel-year-v1',
                  'resume_command':'python -m scripts.run_campaign_interactions'}
        save_json(root/'interactions_progress.json',public)
        print(json.dumps(public),flush=True)
    public.update(status=status,at=now().isoformat(),quota=ledger.summary())
    save_json(root/'interactions_progress.json',public)
    print(json.dumps(public),flush=True)


if __name__ == '__main__':
    with file_lock(ROOT/'private-writer.lock'):
        run()
