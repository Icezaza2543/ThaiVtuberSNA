"""Bounded injected backfill engine. No production entry point or default clients.

Catalog and quota checkpoints contain public metadata only. Interaction cursors,
dedup identities and event rows belong to the injected authorized workbook store.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from core.expanded_contracts import DATASET_VERSION, count
from core.file_lock import file_lock
from collector.historical_catalog_builder import HistoricalCatalogBuilder
from collector.deep_comment_backfill import DeepCommentBackfiller
from collector.historical_comment_backfill import BudgetExhaustedException


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class RequestLedger:
    """Durable debit before I/O, shared across stages and restarts; never refunds failures."""
    def __init__(self, path, budgets):
        if not set(budgets).issubset({'catalog', 'interactions', 'discovery', 'live_chat'}):
            raise ValueError('Unknown request stage')
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            con.execute('CREATE TABLE IF NOT EXISTS budgets(stage TEXT PRIMARY KEY, ceiling INTEGER, spent INTEGER)')
            for stage, limit in budgets.items():
                count(limit)
                old = con.execute('SELECT ceiling FROM budgets WHERE stage=?', (stage,)).fetchone()
                if old and old[0] != limit:
                    raise ValueError('Persistent budget changed; explicit new authorization required')
                con.execute('INSERT OR IGNORE INTO budgets VALUES (?,?,0)', (stage, limit))

    @contextmanager
    def connection(self):
        con = sqlite3.connect(self.path)
        try:
            with con:
                yield con
        finally:
            con.close()

    def debit(self, stage, units=1):
        count(units)
        with self.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute('SELECT ceiling,spent FROM budgets WHERE stage=?', (stage,)).fetchone()
            if not row or row[1] + units > row[0]:
                raise BudgetExhaustedException('Persistent request ceiling reached')
            con.execute('UPDATE budgets SET spent=spent+? WHERE stage=?', (units, stage))

    def spent(self, stage):
        with self.connection() as con:
            return con.execute('SELECT spent FROM budgets WHERE stage=?', (stage,)).fetchone()[0]


class ExpandedCatalog:
    """One page per channel turn; first-pass cap is distinct accessible video IDs.

    Uses the legacy HTTP seam, not its frozen cohort, cutoff or completed-channel skip.
    A serialized coordinator owns public catalog/checkpoint changes across processes.
    """
    def __init__(self, path, manifest, *, session, api_key, ledger, cap=1000, clock=utcnow):
        if manifest.get('dataset_version') != DATASET_VERSION or not manifest.get('cohort_version'):
            raise ValueError('Expanded approved manifest required')
        if type(cap) is not int or not 0 < cap <= 1000:
            raise ValueError('First-pass policy supports 1..1000, never an implicit deeper crawl')
        self.path, self.ledger, self.cap, self.clock = Path(path), ledger, cap, clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.transport = SimpleNamespace(session=session, api_key=api_key)
        channels = manifest['channels']
        if any(c.get('review_status') != 'approved' or not re.fullmatch(r'UC[A-Za-z0-9_-]{22}', c.get('channel_id', '')) for c in channels):
            raise ValueError('Every channel must be explicitly approved with a stable ID')
        if len({c['channel_id'] for c in channels}) != len(channels):
            raise ValueError('Deduplicate approved channel IDs before collection')
        self.identity = encode({'version': DATASET_VERSION, 'cohort': manifest['cohort_version'],
                                'channels': sorted(c['channel_id'] for c in channels), 'cap': cap})
        with self.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            con.execute('CREATE TABLE IF NOT EXISTS identity(value TEXT PRIMARY KEY)')
            old = con.execute('SELECT value FROM identity').fetchone()
            if old and old[0] != self.identity:
                raise ValueError('Catalog version/cohort/policy mismatch')
            con.execute('INSERT OR IGNORE INTO identity VALUES (?)', (self.identity,))
            con.execute('CREATE TABLE IF NOT EXISTS channels(id TEXT PRIMARY KEY, state TEXT)')
            con.execute('CREATE TABLE IF NOT EXISTS videos(channel TEXT, video TEXT, metadata TEXT, PRIMARY KEY(channel,video))')
            con.execute('CREATE TABLE IF NOT EXISTS unavailable(channel TEXT, item TEXT, metadata TEXT, PRIMARY KEY(channel,item))')
            for c in channels:
                state = dict(token=None, offset=0, catalog_status='PENDING', comment_status='NOT_STARTED',
                             reply_status='NOT_STARTED', live_chat_status='NOT_STARTED', turns=0,
                             inaccessible=0, duplicates=0, ordering='NOT_VALIDATED', last_date=None,
                             oldest=None, accessible_count=0, coverage_complete_from=None)
                con.execute('INSERT OR IGNORE INTO channels VALUES (?,?)', (c['channel_id'], encode(state)))

    @contextmanager
    def connection(self):
        con = sqlite3.connect(self.path)
        try:
            with con: yield con
        finally: con.close()

    def states(self):
        with self.connection() as con:
            return {cid: json.loads(state) for cid, state in con.execute('SELECT id,state FROM channels ORDER BY id')}

    def records(self, channel):
        with self.connection() as con:
            return [json.loads(r[0]) for r in con.execute('SELECT metadata FROM videos WHERE channel=? ORDER BY video', (channel,))]

    def step(self, *, eligible=None):
        with file_lock(self.path.with_suffix('.lock')):
            pending = [(cid, s) for cid, s in self.states().items()
                       if s['catalog_status'] in {'PENDING', 'PARTIAL_ERROR', 'BUDGET_STOP'}
                       and (eligible is None or eligible(cid, s))]
            if not pending: return None
            cid, state = min(pending, key=lambda pair: (pair[1]['turns'], pair[0]))
            try:
                self.ledger.debit('catalog')
            except BudgetExhaustedException:
                state['catalog_status'] = 'BUDGET_STOP'
                self._save(cid, state)
                return cid, state
            state['turns'] += 1
            try:
                items, next_token, status = HistoricalCatalogBuilder.fetch_page_api(
                    self.transport, 'UU' + cid[2:], state['token'])
            except Exception:
                items, next_token, status = [], None, 0
            if status != 200:
                if status == 400 and state['token']:
                    state.update(token=None, offset=0)  # expired cursor: re-enumerate, dedup durable IDs
                state['catalog_status'] = 'PARTIAL_ERROR'
                self._save(cid, state)
                return cid, state
            now = self.clock()
            with self.connection() as con:
                for offset, item in enumerate(items[state['offset']:], state['offset']):
                    if state['accessible_count'] >= self.cap:
                        state.update(offset=offset, catalog_status='CAP_REACHED')
                        break
                    snippet, details = item.get('snippet', {}), item.get('contentDetails', {})
                    vid = details.get('videoId') or snippet.get('resourceId', {}).get('videoId')
                    title = snippet.get('title', '')
                    accessible = bool(vid and title and title not in {'Private video', 'Deleted video'})
                    state['offset'] = offset + 1
                    if not accessible:
                        state['inaccessible'] += 1
                        key = vid or f'page:{state["token"] or "first"}:{offset}'
                        metadata = dict(channel_id=cid, video_id=vid, title=title,
                                        availability='private_or_deleted_or_unresolved',
                                        source='playlistItems', fetched_at=now, dataset_version=DATASET_VERSION)
                        con.execute('INSERT OR REPLACE INTO unavailable VALUES (?,?,?)', (cid, key, encode(metadata)))
                        continue
                    if con.execute('SELECT 1 FROM videos WHERE channel=? AND video=?', (cid, vid)).fetchone():
                        state['duplicates'] += 1
                        continue
                    date = details.get('videoPublishedAt')
                    parsed = HistoricalCatalogBuilder.parse_iso_datetime(date)
                    if date and parsed is None:
                        raise ValueError('Ambiguous video date; preserve checkpoint for review')
                    date = parsed.isoformat() if parsed else None
                    if date and state['last_date'] and date > state['last_date']:
                        state['ordering'] = 'NON_MONOTONIC'
                    if date:
                        state['last_date'] = date
                        state['oldest'] = min(state['oldest'] or date, date)
                    metadata = dict(channel_id=cid, video_id=vid, title=title, title_source='playlistItems.snippet',
                                    title_fetched_at=now, video_published_at=date,
                                    timestamp_quality='exact' if date else 'missing',
                                    playlist_added_at=snippet.get('publishedAt'), fetched_at=now,
                                    availability='accessible', dataset_version=DATASET_VERSION,
                                    source='youtube_api_v3', cohort_policy=hashlib.sha256(self.identity.encode()).hexdigest())
                    con.execute('INSERT INTO videos VALUES (?,?,?)', (cid, vid, encode(metadata)))
                    state['accessible_count'] += 1
                else:
                    state.update(token=next_token, offset=0)
                    state['catalog_status'] = 'PENDING' if next_token else 'PLAYLIST_EXHAUSTED'
                if state['accessible_count'] == self.cap and state['catalog_status'] != 'PLAYLIST_EXHAUSTED':
                    state['catalog_status'] = 'CAP_REACHED'
                # Exhaustion means accessible playlist exhausted, never historical completeness.
                con.execute('UPDATE channels SET state=? WHERE id=?', (encode(state), cid))
            return cid, state

    def _save(self, cid, state):
        with self.connection() as con:
            con.execute('UPDATE channels SET state=? WHERE id=?', (encode(state), cid))


class InteractionTransport:
    """Reuses T6 comment extraction HTTP/error taxonomy; adds independently paged replies."""
    def __init__(self, *, session, api_key, ledger):
        self.session, self.api_key, self.ledger = session, api_key, ledger
        self.api_requests_used, self.quota_budget = 0, 10**12

    def comments(self, video, token):
        self.ledger.debit('interactions')
        result = DeepCommentBackfiller.fetch_page_api(self, video, token)
        if token and result[3] and 'HTTP 400' in result[3]:
            return [], None, 'TOKEN_EXPIRED', None
        return result

    def replies(self, parent, token):
        self.ledger.debit('interactions')
        params = dict(part='snippet', parentId=parent, maxResults=100, key=self.api_key)
        if token: params['pageToken'] = token
        response = self.session.get('https://www.googleapis.com/youtube/v3/comments', params=params, timeout=12)
        if response.status_code == 200:
            body = response.json()
            return body.get('items', []), body.get('nextPageToken'), None, None
        if response.status_code == 400 and token: return [], None, 'TOKEN_EXPIRED', None
        if response.status_code == 404: return [], None, 'REPLIES_UNAVAILABLE', None
        if response.status_code == 429 or (response.status_code == 403 and 'quotaExceeded' in response.text):
            raise BudgetExhaustedException('Reply quota unavailable')
        return [], None, None, 'REQUEST_FAILED'

    @staticmethod
    def historical_chat_capability():
        # Existing LiveChatAdapter resolves activeLiveChatId, not archived replay.
        return {'status': 'LIVE_CHAT_UNAVAILABLE', 'reason': 'ARCHIVED_REPLAY_NOT_IMPLEMENTED',
                'requests': 0}


class ExpandedInteractions:
    def __init__(self, *, transport, batches, hasher, record_cap=500):
        if type(record_cap) is not int or record_cap < 1:
            raise ValueError('Positive combined record cap required')
        self.transport, self.batches, self.hasher, self.cap = transport, batches, hasher, record_cap

    def step(self, *, job, journal, claim):
        """One bounded request/batch. Journal fences publication; private state stays in Sheet.

        Caller registers a version/cohort/channel/video/window/policy digest as journal
        video ID. All cooperating workers must share that journal and workbook lock.
        """
        expected = hashlib.sha256(encode(job).encode()).hexdigest()
        if claim['video_id'] != expected:
            raise ValueError('Claim does not match versioned interaction job')
        if job.get('dataset_version') != DATASET_VERSION:
            raise ValueError('Expanded namespace required')
        if job.get('combined_record_cap') != self.cap:
            raise ValueError('Claim policy differs from combined record cap')
        one_page = job.get('collection_mode') == 'one_comment_page'
        if job.get('collection_mode') not in (None, 'one_comment_page'):
            raise ValueError('Unsupported collection mode')
        from core.hasher import compute_key_fingerprint
        journal.bind_identity(DATASET_VERSION, compute_key_fingerprint(self.hasher.secret_salt))
        owner = journal.get_job(claim['job_id'])
        if not owner or owner['state'] != 'CLAIMED' or owner['claim_token'] != claim['claim_token']:
            return 'STALE_CLAIM'
        state, seen = self.batches.load(expected)
        if not state:
            state = dict(comment_token=None, comment_offset=0, comment_status='PENDING',
                         reply_status='PENDING', live_chat_status='NOT_REQUESTED', parents=[],
                         reply_token=None, reply_offset=0, count=0, sequence=0)
        if one_page and state.get('first_pass_status') == 'PAGE_SAMPLE_COMPLETE':
            journal.commit_job(claim['job_id'], state['count'], claim_token=claim['claim_token'],
                               outcome='PARTIAL_CAPTURE')
            return 'PAGE_SAMPLE_COMPLETE'
        def stop(reason, outcome='EXTRACTION_FAILURE'):
            failed = deepcopy(state)
            failed[source + '_status'] = reason
            failed['sequence'] += 1
            # Capacity remains fail-closed. Without measured capacity only the public
            # journal outcome is recorded, never a speculative private write.
            publish = None
            if self.batches.measured_allocated_cells is not None:
                publish = lambda: self.batches.commit(expected, state['sequence'], [], failed)
            journal.fail_job(claim['job_id'], outcome, claim_token=claim['claim_token'], publish=publish)
            return reason
        if state['count'] >= self.cap:
            journal.commit_job(claim['job_id'], state['count'], claim_token=claim['claim_token'], outcome='PARTIAL_CAPTURE')
            return 'EXHAUSTED' if state['comment_status'] == state['reply_status'] == 'EXHAUSTED' else 'CAP_REACHED'
        source = 'reply' if state['parents'] and not one_page else 'comment'
        if source == 'comment' and state['comment_status'] not in {'PENDING', 'PARTIAL_ERROR', 'BUDGET_STOP', 'EXTRACTION_FAILURE', 'IDENTITY_UNAVAILABLE'}:
            journal.commit_job(claim['job_id'], state['count'], claim_token=claim['claim_token'],
                               outcome='PARTIAL_CAPTURE')
            return state['comment_status']
        working = deepcopy(state)
        try:
            if source == 'reply':
                items, token, terminal, error = self.transport.replies(state['parents'][0], state['reply_token'])
            else:
                items, token, terminal, error = self.transport.comments(job['video_id'], state['comment_token'])
        except BudgetExhaustedException:
            return stop('BUDGET_STOP', 'RATE_LIMITED')
        except Exception:
            return stop('EXTRACTION_FAILURE')
        if error and terminal not in {'COMMENTS_DISABLED', 'VIDEO_UNAVAILABLE', 'VIDEO_NOT_FOUND', 'REPLIES_UNAVAILABLE'}:
            return stop('EXTRACTION_FAILURE')
        rows = []
        if terminal == 'TOKEN_EXPIRED':
            working[source + '_token'], working[source + '_offset'] = None, 0
            working[source + '_status'] = 'PENDING'
        elif terminal:
            working[source + '_status'] = terminal
            if source == 'reply':
                working['unavailable_replies'] = working.get('unavailable_replies', 0) + 1
                working['parents'].pop(0)
                working['reply_token'], working['reply_offset'] = None, 0
        else:
            working[source + '_status'] = 'PENDING'
            offset_key = source + '_offset'
            for index, item in enumerate(items[working[offset_key]:], working[offset_key]):
                if working['count'] >= self.cap: break
                entry = item['snippet']['topLevelComment'] if source == 'comment' else item
                snippet = entry['snippet']
                record_id = entry['id']
                if record_id not in seen:
                    raw_id = snippet.get('authorChannelId', {}).get('value')
                    if not raw_id:
                        # Never silently discard a record or claim exhausted completeness.
                        return stop('IDENTITY_UNAVAILABLE')
                    rows.append(dict(record_id=record_id, viewer_hash=self.hasher.hash_viewer_id(raw_id),
                                     vtuber_channel_id=job['channel_id'], video_id=job['video_id'],
                                     source_type='comment', interaction_kind=source,
                                     interaction_time=snippet.get('publishedAt'), provenance=job['provenance']))
                    seen.add(record_id)
                    working['count'] += 1
                    if source == 'comment' and item['snippet'].get('totalReplyCount', 0) > 0:
                        working['parents'].append(record_id)
                working[offset_key] = index + 1
            else:
                working[offset_key] = 0
                working[source + '_token'] = token
                if token is None:
                    if source == 'reply': working['parents'].pop(0)
                    else: working['comment_status'] = 'EXHAUSTED'
            if working['count'] >= self.cap and (working[source + '_token'] or working[offset_key] or working['parents']):
                working[source + '_status'] = 'PARTIAL_CAP'
            elif not working['parents'] and working['comment_status'] == 'EXHAUSTED':
                working['reply_status'] = 'PARTIAL_UNAVAILABLE' if working.get('unavailable_replies') else 'EXHAUSTED'
        if one_page and not terminal:
            # Acknowledged first-page sample, including an empty accessible page.
            # Keep pagination offsets and reply parents for an explicitly deeper pass.
            working['first_pass_status'] = 'PAGE_SAMPLE_COMPLETE'
            working['reply_status'] = 'DEFERRED'
        working['sequence'] += 1
        publish = lambda: self.batches.commit(expected, state['sequence'], rows, working)
        accepted = journal.commit_job(claim['job_id'], working['count'], claim_token=claim['claim_token'],
            outcome='PARTIAL_CAPTURE', publish=publish)
        return working if accepted else 'STALE_CLAIM'


def interaction_job(*, cohort_version, channel_id, video_id, window_start, window_end,
                    policy_version, provenance, combined_record_cap=500):
    return dict(dataset_version=DATASET_VERSION, cohort_version=cohort_version, channel_id=channel_id,
                video_id=video_id, window_start=window_start, window_end=window_end,
                policy_version=policy_version, provenance=provenance, combined_record_cap=combined_record_cap)
