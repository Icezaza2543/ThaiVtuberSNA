"""Enforced SQL contracts with a portable, atomic JSON source of truth."""

from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TABLES = (
    'evidence', 'personas', 'accounts', 'account_links', 'lifecycle_events',
    'activity_observations', 'affiliations', 'continuity_links', 'discovery_runs',
    'candidates', 'discovery_hits', 'legacy_claims', 'review_queue',
)
PLATFORMS = (
    'youtube', 'twitch', 'tiktok', 'facebook',
    'instagram', 'x', 'kick', 'ganknow', 'bilibili', 'niconico',
    'carrd', 'linktree', 'litlink', 'kofi', 'patreon', 'vgen',
    'website',
)
ROLES = {'streamer', 'singer', 'artist', 'rigger', 'entertainer', 'educator', 'other'}
PRIMARY = {'official_profile', 'self_statement', 'agency_statement'}


def uid(prefix, value):
    return prefix + '_' + hashlib.sha256(value.encode('utf-8')).hexdigest()[:20]


def utc_timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError('Timestamp requires a timezone')
    return parsed


def public_url(value):
    parsed = urlparse(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Evidence and account URLs must be public HTTPS URLs')


def account_url(platform, value):
    public_url(value)
    if platform == 'website':
        return
    host = urlparse(value).hostname.lower()
    domains = {
        'youtube': 'youtube.com',
        'twitch': 'twitch.tv',
        'tiktok': 'tiktok.com',
        'facebook': 'facebook.com',
        'instagram': 'instagram.com',
        'x': 'x.com',
        'kick': 'kick.com',
        'ganknow': 'ganknow.com',
        'bilibili': 'bilibili.com',
        'niconico': 'nicovideo.jp',
        'carrd': 'carrd.co',
        'linktree': 'linktr.ee',
        'litlink': 'lit.link',
        'kofi': 'ko-fi.com',
        'patreon': 'patreon.com',
        'vgen': 'vgen.co',
    }
    if platform not in domains:
        raise ValueError(f'Unsupported platform: {platform}')
    domain = domains[platform]
    if host != domain and not host.endswith('.' + domain):
        raise ValueError(f'URL must belong to {domain}; resolve short links first')


def connect():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript((ROOT / 'schemas/registry.sql').read_text(encoding='utf-8'))
    return db


def put(db, table, row):
    if table not in TABLES or not isinstance(row, dict) or not row:
        raise ValueError('Invalid table or row')
    columns = {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}
    if set(row) - columns:
        raise ValueError(f'Unknown fields in {table}: {sorted(set(row) - columns)}')
    existing = db.execute(f'SELECT * FROM {table} WHERE id=?', (row.get('id'),)).fetchone()
    if existing:
        row = dict(existing) | row
    fields = list(row)
    updates = ', '.join(f'{f}=excluded.{f}' for f in fields if f != 'id')
    action = f'DO UPDATE SET {updates}' if updates else 'DO NOTHING'
    db.execute(f'INSERT INTO {table} ({", ".join(fields)}) VALUES '
               f'({", ".join("?" for _ in fields)}) ON CONFLICT(id) {action}',
               [row[f] for f in fields])


def load(path):
    db = connect()
    if not path.exists():
        return db
    payload = json.loads(path.read_text(encoding='utf-8'))
    if payload.get('schema_version') != 1 or set(payload['tables']) != set(TABLES):
        raise ValueError('Unsupported schema version or table set')
    for table in TABLES:
        for row in payload['tables'][table]:
            # Do not silently deduplicate malformed committed datasets.
            if db.execute(f'SELECT 1 FROM {table} WHERE id=?', (row['id'],)).fetchone():
                raise ValueError(f'Duplicate ID in {table}: {row["id"]}')
            put(db, table, row)
    validate(db)
    return db


def rows(db, table):
    return [dict(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY id')]


def payload(db):
    return {'schema_version': 1, 'tables': {t: rows(db, t) for t in TABLES}}


def save(db, path):
    validate(db)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(payload(db), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


@contextmanager
def edit(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.parent / '.registry.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError('Another registry edit is running; inspect the lock before retrying') from exc
    os.close(fd)
    try:
        db = load(path)
        try:
            yield db
            save(db, path)
        finally:
            db.close()
    finally:
        lock.unlink()


def validate(db):
    if list(db.execute('PRAGMA foreign_key_check')):
        raise ValueError('Broken foreign keys')
    for table in TABLES:
        for row in rows(db, table):
            if not row['id'].strip():
                raise ValueError(f'Empty ID in {table}')
            for key, value in row.items():
                if value is None:
                    continue
                if key.endswith('_at'):
                    utc_timestamp(value)
                if key in {'published_on', 'valid_from', 'valid_to', 'activity_date'}:
                    date.fromisoformat(value)
                if key == 'url':
                    public_url(value)
            if row.get('review_status') == 'verified':
                if not row.get('reviewer') or not row.get('reviewed_at'):
                    raise ValueError(f'{table}/{row["id"]}: verification requires a reviewer and timestamp')
                evidence = db.execute('SELECT * FROM evidence WHERE id=?', (row['evidence_id'],)).fetchone()
                if evidence['kind'] == 'legacy_import':
                    raise ValueError('Legacy imports cannot certify new reviewed claims')
                if utc_timestamp(row['reviewed_at']) < utc_timestamp(evidence['observed_at']):
                    raise ValueError('Review predates its evidence observation')
                if table in {'continuity_links', 'account_links'} and evidence['kind'] not in PRIMARY:
                    raise ValueError('Identity links require explicit first-party public evidence')
                if table == 'lifecycle_events' and evidence['kind'] not in {'self_statement', 'agency_statement'}:
                    raise ValueError('Verified lifecycle events require a first-party announcement')
            if table in {'accounts', 'candidates'}:
                account_url(row['platform'], row['url'])
                if table == 'accounts':
                    if not row['platform_id'] or not row['id_namespace']:
                        raise ValueError('Account IDs need a platform namespace')
                    namespace = {'youtube': 'channel_id', 'twitch': 'user_id'}.get(row['platform'])
                    if namespace and row['id_namespace'] != namespace:
                        raise ValueError(f'{row["platform"]} IDs require the {namespace} namespace')
                    if row['platform'] == 'youtube' and not re.fullmatch(r'UC[A-Za-z0-9_-]{22}', row['platform_id']):
                        raise ValueError('Invalid YouTube channel ID')
                    if row['platform'] == 'twitch' and not row['platform_id'].isdigit():
                        raise ValueError('Twitch accounts require a numeric broadcaster ID')
                    if row['platform'] in {'tiktok', 'facebook'} and row['platform_id'].startswith('@'):
                        raise ValueError('Handles are aliases, not stable platform IDs')
                elif row['review_status'] == 'verified' and not row['account_id']:
                    raise ValueError('A verified candidate requires a resolved account')
                elif table == 'candidates' and row['account_id']:
                    account = db.execute('SELECT * FROM accounts WHERE id=?', (row['account_id'],)).fetchone()
                    if account['platform'] != row['platform'] or (row['platform_id'] and
                            (account['platform_id'], account['id_namespace']) != (row['platform_id'], row['id_namespace'])):
                        raise ValueError('Candidate does not match its resolved platform account')
            if table == 'personas':
                roles = json.loads(row['roles'])
                if not isinstance(roles, list) or any(not isinstance(r, str) for r in roles) or not set(roles) <= ROLES:
                    raise ValueError('Unsupported persona roles')
                if row['review_status'] == 'verified' and (not roles or row['thai_relation'] == 'unknown'):
                    raise ValueError('Verified persona requires roles and reviewed Thai relation')
            if table == 'evidence' and row['sha256'] is not None:
                if not re.fullmatch('[0-9a-f]{64}', row['sha256']):
                    raise ValueError('Invalid SHA256')
            if table == 'lifecycle_events':
                value, precision = row['event_date'], row['date_precision']
                if precision == 'unknown':
                    if value is not None:
                        raise ValueError('Unknown event dates must be null')
                else:
                    pattern = {'day': r'\d{4}-\d{2}-\d{2}', 'month': r'\d{4}-\d{2}', 'year': r'\d{4}'}[precision]
                    if not value or not re.fullmatch(pattern, value):
                        raise ValueError('Event date does not match its precision')
                    date.fromisoformat(value + {'day': '', 'month': '-01', 'year': '-01-01'}[precision])
    # One account may be shared by several personas. The link itself must be reviewed;
    # neither a reused handle nor an old person_id automatically establishes identity.
    for observation in rows(db, 'activity_observations'):
        if observation['review_status'] == 'verified':
            links = db.execute("SELECT * FROM account_links WHERE account_id=? AND persona_id=? AND review_status='verified'",
                               (observation['account_id'], observation['persona_id'])).fetchall()
            if not any(link['valid_from'] and link['valid_to'] and
                       link['valid_from'] <= observation['activity_date'] <= link['valid_to'] for link in links):
                raise ValueError('Activity needs a reviewed account/persona link covering its date')
