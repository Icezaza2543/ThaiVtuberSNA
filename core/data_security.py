"""Three-level, destination-aware project data policy. Findings never echo values."""
import csv
import io
import json
import re
from enum import Enum

SPREADSHEET_ID = '1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE'
SPREADSHEET_TITLE = 'ThaiVtuber_SNA'


class Classification(str, Enum):
    SECRET_CREDENTIAL = 'SECRET_CREDENTIAL'
    PRIVATE_DATA = 'PRIVATE_DATA'
    PUBLIC_RESEARCH_DATA = 'PUBLIC_RESEARCH_DATA'


PRIVATE_FIELDS = {'viewer_hash', 'raw_channel_id', 'raw_author_id', 'author_id',
                  'authorDisplayName', 'authorChannelUrl', 'authorChannelId',
                  'authorExternalChannelId', 'viewer_id', 'commenter_name', 'user_key'}
TEXT_FIELDS = {'text', 'comment_text', 'chat_text', 'message_body', 'displayMessage', 'comment_body'}
SECRET_FIELDS = {'private_key', 'client_secret', 'access_token', 'refresh_token',
                 'password', 'api_key', 'youtube_api_key', 'secret_key', 'secret_salt'}
SECRET_PATTERNS = [
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'AIza[0-9A-Za-z_-]{35}'),
    re.compile(r'ya29\.[A-Za-z0-9._-]{20,}'),
    re.compile(r'github_pat_[A-Za-z0-9_]{30,}'),
    re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),
]
PRIVATE_TABS = {'ALL_COMMENTERS', 'VIEWER_INDEX', 'VIEWER_CHANNEL_PRESENCE',
                'VIEWER_ACTIVITY_SUMMARY', 'VIEWER_EVENT_ARCHIVE', 'PRIVATE_DATA_ARCHIVE',
                'REILIM_COMMENTERS', 'REILIM_COMMENTERS_ARCHIVE'}
CONTROL_TABS = {'NETWORK_RESULT', 'VTUBERS', 'SYSTEM', 'RECOVERY_METADATA',
                'DATA_DICTIONARY', 'MIGRATION_AUDIT'}


def contains_secret(value, known_secrets=()):
    if isinstance(value, str):
        if any(secret and len(secret) >= 12 and secret in value for secret in known_secrets):
            return True
        return any(pattern.search(value) for pattern in SECRET_PATTERNS)
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in SECRET_FIELDS and item not in (None, ''):
                return True
            if contains_secret(item, known_secrets): return True
    elif isinstance(value, (list, tuple)):
        return any(contains_secret(item, known_secrets) for item in value)
    return False


# Fields of the completeness summary, not a filename/path exemption.
FIELD_COUNT_FIELDS = frozenset({
    'viewer_hash', 'raw_channel_id', 'display_name', 'channel_url',
    'first_seen', 'last_seen', 'total_interactions', 'channels_observed_count',
    'recovery_source', 'recovery_status',
})
FIELD_COUNT_KEYS = frozenset({'TOTAL_ROWS', 'NON_EMPTY', 'MISSING', 'INVALID'})


def is_field_count_summary(value):
    """Recognize only a nonempty field-to-counter map, never sample/identity payloads.

    bool is an int subclass, so counters require exact integer types. Every field
    must have the complete counter schema; no filename or directory exemptions.
    """
    return (
        isinstance(value, dict) and bool(value)
        and all(
            isinstance(field, str) and field in FIELD_COUNT_FIELDS
            and isinstance(counts, dict) and set(counts) == FIELD_COUNT_KEYS
            and all(type(count) is int and count >= 0 for count in counts.values())
            for field, counts in value.items()
        )
    )


def contains_private(value):
    if isinstance(value, str) and value.lstrip().startswith(('{', '[')):
        try: return contains_private(json.loads(value))
        except ValueError: return False
    if isinstance(value, dict):
        summary = is_field_count_summary(value)
        if not summary and any(k in PRIVATE_FIELDS and v not in (None, '') for k, v in value.items()):
            return True
        if not summary and value.get('channel_url') and value.get('display_name') and not value.get('vtuber_channel_id'):
            return True
        return any(contains_private(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_private(v) for v in value)
    return False


def assert_sheet_rows(headers, rows, known_secrets=()):
    if any(str(h).lower() in SECRET_FIELDS for h in headers):
        raise ValueError('LEVEL_A_FIELD_FORBIDDEN')
    if set(headers) & TEXT_FIELDS:
        raise ValueError('MESSAGE_TEXT_FORBIDDEN')
    for row in rows:
        if len(row) > len(headers):
            # Unknown cells must still pass value-level credential checks.
            if contains_secret(row, known_secrets): raise ValueError('LEVEL_A_VALUE_FORBIDDEN')
        record = dict(zip(headers, row))
        if len(row) >= 2 and str(row[0]).strip().lower() in SECRET_FIELDS and row[1]:
            raise ValueError('LEVEL_A_METRIC_FORBIDDEN')
        if contains_secret(record, known_secrets):
            raise ValueError('LEVEL_A_VALUE_FORBIDDEN')
        for cell in row:
            if isinstance(cell, str) and cell.lstrip().startswith(('{','[')):
                try: nested = json.loads(cell)
                except ValueError: continue
                if contains_secret(nested, known_secrets):
                    raise ValueError('LEVEL_A_NESTED_VALUE_FORBIDDEN')
                if _has_text(nested): raise ValueError('MESSAGE_TEXT_FORBIDDEN')


def _has_text(value):
    if isinstance(value, dict):
        return bool(set(value) & TEXT_FIELDS) or any(_has_text(v) for v in value.values())
    return isinstance(value, list) and any(_has_text(v) for v in value)


def assert_public(value, known_secrets=()):
    if contains_secret(value, known_secrets): raise ValueError('LEVEL_A_PUBLIC_EXPORT')
    if contains_private(value): raise ValueError('LEVEL_B_PUBLIC_EXPORT')


def inspect_blob(path, data, known_secrets=()):
    """Classify actual artifact rows, not column names appearing in source/docs."""
    suffix = path.lower().rsplit('.', 1)[-1]
    text = data.decode('utf-8', errors='replace')
    if contains_secret(text, known_secrets):
        return Classification.SECRET_CREDENTIAL.value, 'Credential material or exact local secret match'
    try:
        if suffix == 'parquet':
            import pyarrow.parquet as pq
            table = pq.read_table(io.BytesIO(data))
            if contains_secret(table.to_pylist(), known_secrets):
                return Classification.SECRET_CREDENTIAL.value, 'Credential material in decoded table'
            if set(table.column_names) & PRIVATE_FIELDS and table.num_rows:
                return Classification.PRIVATE_DATA.value, f'Viewer-level table ({table.num_rows} rows)'
            return Classification.PUBLIC_RESEARCH_DATA.value, f'Public/aggregate table ({table.num_rows} rows)'
        if suffix in ('duckdb', 'sqlite', 'sqlite3', 'db'):
            import tempfile
            from pathlib import Path
            with tempfile.TemporaryDirectory() as directory:
                temporary = Path(directory) / ('audit.'+suffix)
                temporary.write_bytes(data)
                return inspect_database(temporary, known_secrets)
        if suffix == 'json': value = json.loads(text)
        elif suffix == 'jsonl': value = [json.loads(line) for line in text.splitlines() if line.strip()]
        elif suffix == 'csv': value = list(csv.DictReader(io.StringIO(text.lstrip('\ufeff'))))
        else:
            value = None
            if suffix in ('js', 'html', 'txt', 'log') and re.search(r'''["']viewer_hash["']\s*:\s*["'][a-f0-9]{64}["']''', text):
                return Classification.PRIVATE_DATA.value, 'Embedded individual viewer pseudonym'
        if contains_secret(value, known_secrets):
            return Classification.SECRET_CREDENTIAL.value, 'Credential field in structured artifact'
        if contains_private(value):
            return Classification.PRIVATE_DATA.value, 'Individual viewer identity records'
    except Exception:
        return Classification.PUBLIC_RESEARCH_DATA.value, 'UNREADABLE: manual review required'
    return Classification.PUBLIC_RESEARCH_DATA.value, 'Source/schema/methodology or public channel/aggregate data'


def inspect_database(path, known_secrets=()):
    """Scan durable tables, including committed SQLite WAL data; never print cells."""
    if path.suffix == '.duckdb':
        import duckdb
        con = duckdb.connect(str(path), read_only=True)
        names = con.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE'").fetchall()
        qualified = ['.'.join('"'+x.replace('"','""')+'"' for x in row) for row in names]
    else:
        import sqlite3
        con = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
        con.execute('BEGIN')
        qualified = ['"'+r[0].replace('"','""')+'"' for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    private = False
    count = 0
    try:
        for name in qualified:
            cur = con.execute('SELECT * FROM '+name)
            columns = [d[0] for d in cur.description]
            while rows := cur.fetchmany(4096):
                count += len(rows)
                records = [dict(zip(columns, row)) for row in rows]
                if contains_secret(records, known_secrets):
                    return Classification.SECRET_CREDENTIAL.value, 'Credential in decoded database'
                private |= contains_private(records)
    finally: con.close()
    return (Classification.PRIVATE_DATA.value if private else Classification.PUBLIC_RESEARCH_DATA.value,
            f'Durable database rows scanned: {count}')
