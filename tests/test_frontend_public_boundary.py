"""Public web boundary: no private workbook references or viewer records.

Creator IDs are allowed only when present in the independent public registry.
Failures identify paths and violation categories, never private values.
"""
import csv
import html
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from core.data_security import PRIVATE_FIELDS, PRIVATE_TABS, SPREADSHEET_ID

ROOT = Path(__file__).resolve().parents[1]
CHANNEL_ID = re.compile(r"UC[A-Za-z0-9_-]{22}")


def violations(blob, creator_ids):
    text = blob.decode('utf-8', errors='replace')
    # Cover HTML attributes, URL encoding and JSON/JavaScript escape sequences.
    for _ in range(3):
        text = html.unescape(unquote(text))
        text = re.sub(r'\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})',
                      lambda m: chr(int(m[1] or m[2], 16)), text)
        text = text.replace(r'\/', '/')
    lowered = text.lower()
    findings = set()
    if SPREADSHEET_ID.lower() in lowered:
        findings.add('private workbook identifier')
    if re.search(r'docs\.google\.com\s*/\s*spreadsheets', lowered):
        findings.add('direct spreadsheet link')
    if any(re.search(r'(?<![a-z0-9_])' + re.escape(token.lower()) + r'(?![a-z0-9_])', lowered)
           for token in PRIVATE_TABS):
        findings.add('private worksheet reference')
    if any(re.search(r'(?<![a-z0-9_])' + re.escape(field.lower()) + r'(?![a-z0-9_])', lowered)
           for field in PRIVATE_FIELDS):
        findings.add('viewer identity field or row')
    if set(CHANNEL_ID.findall(text)) - creator_ids:
        findings.add('channel identity outside public creator registry')
    return findings


def test_public_web_contains_only_public_creator_identities():
    with (ROOT / 'data/thai_vtuber_registry.csv').open(encoding='utf-8-sig', newline='') as stream:
        creator_ids = {row['channel_id'] for row in csv.DictReader(stream)}
    assert creator_ids
    files = sorted(path for path in (ROOT / 'web').rglob('*') if path.is_file())
    assert files
    failures = []
    for path in files:
        found = violations(path.read_bytes(), creator_ids)
        if found:
            failures.append((str(path.relative_to(ROOT)), sorted(found)))
    assert not failures, failures


@pytest.mark.parametrize('payload', [
    SPREADSHEET_ID,
    'https://docs.google.com/spreadsheets/d/synthetic/edit',
    'https%3A%2F%2Fdocs.google.com%2Fspreadsheets%2Fd%2Fsynthetic',
    *sorted(PRIVATE_TABS),
    '{"viewer_hash":"' + 'a' * 64 + '"}',
    'viewer_hash,count\nsynthetic,1',
    r'{"viewer\u005fhash":"synthetic"}',
    '{"authorChannelId":"UC' + 'V' * 22 + '"}',
    '{"channel_id":"UC' + 'V' * 22 + '"}',
    'https://www.youtube.com/channel/UC' + 'V' * 22,
])
def test_guard_rejects_private_frontend_payloads(payload):
    assert violations(payload.encode(), {'UC' + 'C' * 22})


def test_guard_allows_public_creator_graph_and_aggregate_counts():
    creator = 'UC' + 'C' * 22
    assert not violations((' {"channel_id":"' + creator + '","shared_viewers":12}').encode(), {creator})
