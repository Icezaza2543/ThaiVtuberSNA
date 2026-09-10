"""Authorized expanded-v1 campaign. Public checkpoints; private events never local.

The user confirmed 10,000 general units/day with a 1,000-unit reserve.
This ledger does not depend on the Cloud Quotas introspection API.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from zoneinfo import ZoneInfo

from collector.expanded_backfill import ExpandedCatalog, encode
from collector.historical_comment_backfill import BudgetExhaustedException
from core.file_lock import file_lock

ROOT = Path('scratch/expanded-v1-campaign')


def now():
    return datetime.now(timezone.utc)


class CampaignLedger:
    """One shared general bucket, durable debit before I/O, Pacific daily windows."""
    def __init__(self, path, *, clock=now):
        self.path, self.clock = Path(path), clock
        self.window = clock().astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat()
        with self.connect() as con:
            con.execute('CREATE TABLE IF NOT EXISTS windows (day TEXT PRIMARY KEY, stopped INTEGER NOT NULL DEFAULT 0)')
            con.execute('CREATE TABLE IF NOT EXISTS debits (day TEXT, stage TEXT, units INTEGER, at TEXT)')
            con.execute('INSERT OR IGNORE INTO windows(day) VALUES (?)', (self.window,))

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def debit(self, stage, units=1):
        if stage not in {'catalog', 'interactions'} or type(units) is not int or units != 1:
            raise ValueError('Only approved one-unit collection endpoints are supported')
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            used = con.execute('SELECT COALESCE(SUM(units),0) FROM debits WHERE day=?', (self.window,)).fetchone()[0]
            stopped = con.execute('SELECT stopped FROM windows WHERE day=?', (self.window,)).fetchone()[0]
            if stopped or used + units > 9000 or self.clock().astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat() != self.window:
                raise BudgetExhaustedException('Quota window stopped; resume existing ledger in next window')
            con.execute('INSERT INTO debits VALUES (?,?,?,?)', (self.window, stage, units, self.clock().isoformat()))

    def stop(self):
        with self.connect() as con:
            con.execute('UPDATE windows SET stopped=1 WHERE day=?', (self.window,))

    def summary(self):
        with self.connect() as con:
            stages = dict(con.execute('SELECT stage,SUM(units) FROM debits WHERE day=? GROUP BY stage', (self.window,)))
            total = con.execute('SELECT COALESCE(SUM(units),0) FROM debits').fetchone()[0]
            stopped = bool(con.execute('SELECT stopped FROM windows WHERE day=?', (self.window,)).fetchone()[0])
        return {'window_pacific': self.window, 'window_units': sum(stages.values()), 'by_stage': stages,
                'all_windows_units': total, 'provider_stopped': stopped, 'ceiling': 9000}


class MeteredSession:
    def __init__(self, ledger):
        import requests
        self.session, self.ledger = requests.Session(), ledger
        self.status, self.reason = None, None

    def get(self, url, **kwargs):
        self.status, self.reason = None, None
        if url not in {'https://www.googleapis.com/youtube/v3/playlistItems',
                       'https://www.googleapis.com/youtube/v3/commentThreads',
                       'https://www.googleapis.com/youtube/v3/comments'}:
            raise ValueError('Endpoint outside authorized collection policy')
        try:
            response = self.session.get(url, **kwargs)
        except Exception:
            raise RuntimeError('YouTube transport failed') from None
        self.status = response.status_code
        if response.status_code != 200:
            try:
                reasons = {e.get('reason') for e in response.json().get('error', {}).get('errors', [])}
            except ValueError:
                reasons = set()
            if reasons & {'quotaExceeded', 'dailyLimitExceeded'}:
                self.ledger.stop()
                self.reason = 'PROVIDER_QUOTA_STOP'
            elif response.status_code == 404:
                self.reason = 'NOT_FOUND'
            else:
                self.reason = 'HTTP_ERROR'
        return response


def save_json(path, value):
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def report(root, catalog, ledger, started, initial_count, status, extra=None):
    states = catalog.states()
    counts = Counter(s['catalog_status'] for s in states.values())
    with catalog.connection() as con:
        row = con.execute("SELECT COUNT(*), MIN(json_extract(metadata,'$.video_published_at')), MAX(json_extract(metadata,'$.video_published_at')), SUM(json_extract(metadata,'$.timestamp_quality')='exact') FROM videos").fetchone()
    elapsed = time.monotonic() - started
    value = {'at': now().isoformat(), 'status': status, 'approved_channels': len(states),
             'channels_processed': sum(s['turns'] > 0 for s in states.values()),
             'terminal': counts['CAP_REACHED'] + counts['PLAYLIST_EXHAUSTED'],
             'remaining': len(states) - counts['CAP_REACHED'] - counts['PLAYLIST_EXHAUSTED'],
             'catalog_statuses': dict(counts), 'distinct_videos': row[0], 'oldest_date': row[1],
             'newest_date': row[2], 'exact_dates': row[3] or 0,
             'channels_at_or_before_2020': sum(bool(s['oldest'] and s['oldest'] < '2021') for s in states.values()),
             'quota': ledger.summary(), 'invocation_elapsed_seconds': round(elapsed, 2),
             'invocation_videos_per_minute': round((row[0]-initial_count)*60/max(elapsed, .001), 2),
             'eta': None, 'checkpoint': str(root/'catalog.sqlite3'),
             'resume_command': 'python -m scripts.run_expanded_campaign'}
    if extra:
        value.update(extra)
    save_json(root/'progress.json', value)
    print(json.dumps(value, ensure_ascii=False), flush=True)
    return value


def run(root=ROOT):
    from config.settings import YOUTUBE_API_KEY
    if not YOUTUBE_API_KEY:
        raise RuntimeError('Configured YouTube key missing')
    manifest = json.loads((root/'approved_manifest.json').read_text(encoding='utf-8'))
    ledger = CampaignLedger(root/'quota.sqlite3')
    session = MeteredSession(ledger)
    catalog = ExpandedCatalog(root/'catalog.sqlite3', manifest, session=session, api_key=YOUTUBE_API_KEY, ledger=ledger)
    with catalog.connection() as con:
        initial_count = con.execute('SELECT COUNT(*) FROM videos').fetchone()[0]
        con.execute('CREATE TABLE IF NOT EXISTS campaign_errors(channel TEXT PRIMARY KEY, attempts INTEGER, retry_at REAL, reason TEXT)')
    started, last_report = time.monotonic(), 0
    status = 'RUNNING'
    while True:
        quota = ledger.summary()
        if quota['provider_stopped'] or quota['window_units'] >= 9000:
            status = 'QUOTA_STOP'
            break
        with catalog.connection() as con:
            blocked = {r[0] for r in con.execute('SELECT channel FROM campaign_errors WHERE attempts>=3 OR retry_at>?', (time.time(),))}
        result = catalog.step(eligible=lambda cid, state: cid not in blocked)
        if result is None:
            status = 'CATALOG_TERMINAL_OR_RETRY_QUEUE'
            break
        cid, state = result
        if state['catalog_status'] == 'BUDGET_STOP':
            status = 'QUOTA_STOP'
            break
        with catalog.connection() as con:
            if state['catalog_status'] == 'PARTIAL_ERROR':
                old = con.execute('SELECT attempts FROM campaign_errors WHERE channel=?', (cid,)).fetchone()
                attempts = (old[0] if old else 0) + 1
                con.execute('INSERT OR REPLACE INTO campaign_errors VALUES (?,?,?,?)',
                            (cid, attempts, time.time()+30*2**(attempts-1), session.reason or 'TRANSPORT_ERROR'))
            else:
                con.execute('DELETE FROM campaign_errors WHERE channel=?', (cid,))
        if time.monotonic()-last_report >= 30:
            report(root, catalog, ledger, started, initial_count, status)
            last_report = time.monotonic()
    report(root, catalog, ledger, started, initial_count, status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    with file_lock(args.root/'campaign.lock'):
        run(args.root)
