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


def contains_private(value):
    if isinstance(value, dict):
        if any(k in PRIVATE_FIELDS and v not in (None, '') for k, v in value.items()):
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
        record = dict(zip(headers, row))
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
            if set(table.column_names) & PRIVATE_FIELDS and table.num_rows:
                return Classification.PRIVATE_DATA.value, f'Viewer-level table ({table.num_rows} rows)'
            return Classification.PUBLIC_RESEARCH_DATA.value, f'Public/aggregate table ({table.num_rows} rows)'
        if suffix == 'json': value = json.loads(text)
        elif suffix == 'jsonl': value = [json.loads(line) for line in text.splitlines() if line.strip()]
        elif suffix == 'csv': value = list(csv.DictReader(io.StringIO(text.lstrip('\ufeff'))))
        else: value = None
        if contains_secret(value, known_secrets):
            return Classification.SECRET_CREDENTIAL.value, 'Credential field in structured artifact'
        if contains_private(value):
            return Classification.PRIVATE_DATA.value, 'Individual viewer identity records'
    except Exception:
        return Classification.PUBLIC_RESEARCH_DATA.value, 'UNREADABLE: manual review required'
    return Classification.PUBLIC_RESEARCH_DATA.value, 'Source/schema/methodology or public channel/aggregate data'
