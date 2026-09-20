"""Public web boundary: no private workbook references or viewer records.

Creator IDs are allowed only when present in the independent public registry.
Failures identify paths and violation categories, never private values.
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from config.settings import CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog
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
    creator_ids = {
        row["platform_id"]
        for row in CreatorCatalog.from_path(CREATOR_REGISTRY_PATH).youtube_accounts()
        if row.get("platform_id")
    }
    assert creator_ids
    ignored_subpaths = {("node_modules",), ("dist",), (".vite",), ("public", "data")}
    files = sorted(
        path for path in (ROOT / 'web').rglob('*')
        if path.is_file() and not any(
            path.relative_to(ROOT / 'web').parts[:len(sub)] == sub
            for sub in ignored_subpaths
        )
    )
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


@pytest.mark.parametrize(
    "relative_path",
    [
        Path("web/data.json"),
        Path("web/research/data/research_v2.json"),
    ],
)
def test_registry_derived_public_json_has_current_catalog_fingerprint(relative_path):
    path = ROOT / relative_path
    assert path.exists(), path
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = CreatorCatalog.from_path(CREATOR_REGISTRY_PATH).source_fingerprint()
    assert payload.get("metadata", {}).get("creator_registry_sha256") == expected, (
        f"{relative_path} is missing or stale against the canonical creator registry"
    )
