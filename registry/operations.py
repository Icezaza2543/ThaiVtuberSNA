"""Bounded discovery and reproducible import; review is a separate operation."""

from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request
from uuid import uuid4

from .store import TABLES, account_url, put, rows, uid, utc_timestamp, validate


def now():
    return datetime.now(timezone.utc).isoformat()


def import_legacy(db, path, commit):
    if any(db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in TABLES):
        raise ValueError('Baseline import requires an empty registry; it never replaces reviewed data')
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Provide the original full Git commit SHA')
    raw = path.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        source = list(csv.DictReader(stream))
    required = {'channel_id', 'name', 'handle', 'activity_status', 'vtuber_status', 'person_id',
                'agency', 'reference_sources', 'checked_date', 'last_video_published_at'}
    if not source or not required <= set(source[0]):
        raise ValueError('CSV is missing the ThaiVtuberSNA baseline columns')
    if len({r['channel_id'] for r in source}) != len(source):
        raise ValueError('Duplicate channel IDs in baseline')
    timestamp = now()
    evidence_id = uid('ev', checksum)
    put(db, 'evidence', dict(id=evidence_id,
        url=f'https://github.com/Icezaza2543/ThaiVtuberSNA/blob/{commit}/data/thai_vtuber_registry.csv',
        kind='legacy_import', observed_at=timestamp, published_on=None, sha256=checksum,
        summary='Imported public channel metadata; original identity and lifecycle labels require review.'))
    run_id = uid('run', checksum)
    put(db, 'discovery_runs', dict(id=run_id, platform='youtube', method='legacy_import',
        query='ThaiVtuberSNA/data/thai_vtuber_registry.csv', observed_at=timestamp,
        stop_reason='import_complete', pages=0, records_seen=len(source)))
    identity_counts = Counter(r['person_id'] for r in source if r['person_id'])
    for item in source:
        channel_id = item['channel_id']
        aid = uid('acct', 'youtube:' + channel_id)
        put(db, 'accounts', dict(id=aid, platform='youtube', platform_id=channel_id,
            id_namespace='channel_id', handle=item['handle'] or None, name=item['name'],
            url=f'https://www.youtube.com/channel/{channel_id}', first_discovered_at=timestamp,
            evidence_id=evidence_id))
        put(db, 'legacy_claims', dict(id=uid('legacy', channel_id), account_id=aid,
            source_status=item['vtuber_status'], source_activity=item['activity_status'],
            source_agency=item['agency'], source_names=item['reference_sources'],
            source_checked_at=item['checked_date'], last_video_published_at=item['last_video_published_at'] or None,
            evidence_id=evidence_id))
        put(db, 'discovery_hits', dict(id=uid('hit', run_id + aid), run_id=run_id,
            account_id=aid, candidate_id=None, evidence_id=evidence_id))
        put(db, 'review_queue', dict(id=uid('review', aid), account_id=aid, reason='legacy_scope_review',
            status='open', note='Review Thai relation, virtual presentation and public persona/account link.'))
        if item['person_id'] and identity_counts[item['person_id']] > 1:
            put(db, 'review_queue', dict(id=uid('collision', aid), account_id=aid,
                reason='legacy_identity_collision', status='open',
                note='Legacy person_id was shared by multiple accounts. No persona link was imported.'))
        if re.search(r'graduat', item['name'], re.I) and item['activity_status'] != 'graduated':
            put(db, 'review_queue', dict(id=uid('lifecycle', aid), account_id=aid,
                reason='lifecycle_conflict', status='open',
                note='Channel name and legacy lifecycle differ; inspect an official dated announcement.'))
    validate(db)
    return {'imported_accounts': len(source), 'verified_personas': 0, 'source_sha256': checksum}


def discover_candidate(db, *, platform, url, name, source_url, method='manual_search',
                       query='', observed_at=None, platform_id=None, id_namespace=None,
                       run_id=None, source_kind='secondary_source'):
    timestamp = observed_at or now()
    utc_timestamp(timestamp)
    account_url(platform, url)
    if bool(platform_id) != bool(id_namespace):
        raise ValueError('platform_id and id_namespace must be provided together')
    rid = run_id or 'run_' + uuid4().hex
    if run_id is None:
        put(db, 'discovery_runs', dict(id=rid, platform=platform, method=method,
            query=query, observed_at=timestamp, stop_reason='manual_batch', pages=0, records_seen=1))
    ev = uid('ev', rid + source_url + url)
    put(db, 'evidence', dict(id=ev, url=source_url, kind=source_kind,
        observed_at=timestamp, published_on=None, sha256=None,
        summary='Discovery lead; needs review of virtual presentation and Thai relation.'))
    known = None
    if platform_id:
        known = db.execute('SELECT id FROM accounts WHERE platform=? AND id_namespace=? AND platform_id=?',
                           (platform, id_namespace, platform_id)).fetchone()
    # A handle-only URL stays a candidate: a recycled handle cannot identify a known account.
    if known:
        put(db, 'discovery_hits', dict(id=uid('hit', rid + known['id']), run_id=rid,
            account_id=known['id'], candidate_id=None, evidence_id=ev))
        return known['id']
    key = (id_namespace + ':' + platform_id) if platform_id else url.rstrip('/')
    cid = uid('candidate', platform + ':' + key)
    if not db.execute('SELECT 1 FROM candidates WHERE id=?', (cid,)).fetchone():
        put(db, 'candidates', dict(id=cid, platform=platform, platform_id=platform_id,
            id_namespace=id_namespace, name=name, url=url, review_status='needs_evidence',
            account_id=None, evidence_id=ev, reviewer=None, reviewed_at=None))
    put(db, 'discovery_hits', dict(id=uid('hit', rid + cid), run_id=rid,
        account_id=None, candidate_id=cid, evidence_id=ev))
    return cid


def apply_change(db, change):
    if not isinstance(change, dict) or set(change) - set(TABLES):
        raise ValueError('Change file must map supported table names to row lists')
    for table in TABLES:
        items = change.get(table, [])
        if not isinstance(items, list):
            raise ValueError('Each table change must be a list')
        for row in items:
            put(db, table, row)
    validate(db)


def preview_change(db, change):
    """Validate the complete change and return its net diff without retaining writes."""
    before = {table: {row['id']: row for row in rows(db, table)} for table in TABLES}
    db.execute('SAVEPOINT review_preview')
    try:
        apply_change(db, change)
        changes = []
        counts = {'added': 0, 'updated': 0, 'unchanged': 0}
        for table in TABLES:
            touched = {row['id'] for row in change.get(table, [])}
            for after in rows(db, table):
                if after['id'] not in touched:
                    continue
                original = before[table].get(after['id'])
                if original == after:
                    counts['unchanged'] += 1
                    continue
                action = 'added' if original is None else 'updated'
                counts[action] += 1
                fields = {key: {'before': original[key] if original else None, 'after': value}
                          for key, value in after.items() if original is None or original[key] != value}
                changes.append({'table': table, 'id': after['id'], 'action': action, 'fields': fields})
        return {'valid': True, 'dry_run': True, 'counts': counts, 'changes': changes}
    finally:
        db.execute('ROLLBACK TO review_preview')
        db.execute('RELEASE review_preview')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def twitch_request(url, headers):
    # Fixed destination and no redirects prevent bearer-token forwarding.
    if urlparse(url).hostname != 'api.twitch.tv':
        raise ValueError('Unexpected Twitch API host')
    from urllib.request import build_opener
    opener = build_opener(NoRedirect())
    with opener.open(Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def twitch_discover(db, max_pages=3, language='th', fetch=twitch_request):
    if not 1 <= max_pages <= 20:
        raise ValueError('max_pages must be between 1 and 20')
    if not re.fullmatch(r'[a-z]{2}|other', language):
        raise ValueError('Use a supported language code')
    client_id, token = os.getenv('TWITCH_CLIENT_ID'), os.getenv('TWITCH_ACCESS_TOKEN')
    if not client_id or not token:
        raise ValueError('Set TWITCH_CLIENT_ID and TWITCH_ACCESS_TOKEN in your environment')
    headers = {'Client-Id': client_id, 'Authorization': 'Bearer ' + token}
    rid, timestamp = 'run_' + uuid4().hex, now()
    run = dict(id=rid, platform='twitch', method='twitch_helix', query='language=' + language,
               observed_at=timestamp, stop_reason='page_limit', pages=0, records_seen=0)
    put(db, 'discovery_runs', run)
    cursor, seen, candidates = '', set(), set()
    for _ in range(max_pages):
        params = {'language': language, 'first': 100}
        if cursor:
            params['after'] = cursor
        try:
            page = fetch('https://api.twitch.tv/helix/streams?' + urlencode(params), headers)
        except (HTTPError, URLError, TimeoutError):
            run['stop_reason'] = 'http_error'
            break
        run['pages'] += 1
        for stream in page['data']:
            sid = stream['user_id']
            if sid in seen:
                continue
            seen.add(sid)
            # All observed Thai-language broadcasters enter review, including no-tag cases.
            # This improves recall but never approves non-virtual streamers automatically.
            url = 'https://www.twitch.tv/' + stream['user_login']
            cid = discover_candidate(db, platform='twitch', platform_id=sid, id_namespace='user_id',
                url=url, name=stream['user_name'], source_url=url, run_id=rid,
                source_kind='platform_observation', observed_at=timestamp)
            candidates.add(cid)
        cursor = page.get('pagination', {}).get('cursor', '')
        if not cursor:
            run['stop_reason'] = 'end_of_results'
            break
    run['records_seen'] = len(seen)
    put(db, 'discovery_runs', run)
    validate(db)
    return {'run_id': rid, 'pages': run['pages'], 'accounts_seen': len(seen),
            'review_leads': len(candidates), 'stop_reason': run['stop_reason']}
