"""Fail-closed eligibility export across historical registries and discovery accounts.

This is a filter, not a new evidence review. Historical identity/CONFIRMED labels
never promote an account. Original Git blobs remain the evidence provenance.
"""
import csv
import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'docs/evidence/expanded-v1/public-review-2026-09-10/channel_eligibility_v1.json'
OUT = ROOT / 'docs/evidence/expanded-v1/historical-eligibility-2026-09-19'
MASTER_REVISIONS = ('4a1db6212de59d497d2a998baff29bd2c436a55a',
                    '97116ca274a6940ba3919c13c8e7fd5778322cca')
BASE = '80378402588c6e9429effc4bce7c4e977f9221b8'
CHANNEL = re.compile(r'UC[A-Za-z0-9_-]{22}')


def youtube_id(row):
    if row.get('platform', 'youtube') != 'youtube':
        return None
    for field in ('channel_id', 'platform_id'):
        value = row.get(field) or ''
        if CHANNEL.fullmatch(value):
            return value
    parsed = urlparse(row.get('url') or row.get('channel_url') or '')
    if parsed.hostname in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}:
        match = re.fullmatch(r'/channel/(UC[A-Za-z0-9_-]{22})/?', parsed.path)
        if match:
            return match[1]
    return None


def classify(row, reviews):
    cid = youtube_id(row)
    if cid in reviews:
        return reviews[cid]['eligibility_status'], 'EXACT_CHANNEL_ID_REVIEW'
    return 'HOLD_NEEDS_CHANNEL_REVIEW', 'NO_CHANNEL_ELIGIBILITY_REVIEW' if cid else 'NO_REVIEWED_PLATFORM_ACCOUNT_ID'


def historical_sources():
    specs = [(BASE, 'data/thai_vtuber_registry.csv', None),
             (BASE, 'data/registry_vtubers.csv', None),
             (BASE, 'data/industry/discovery_universe.csv', None),
             (BASE, 'data/industry/discovery_candidates_new.csv', None),
             (BASE, 'data/excluded_channels.csv', None)]
    for rev in MASTER_REVISIONS:
        for section in ('canonical_accounts', 'unresolved_discovery_accounts'):
            specs.append((rev, 'data/master_creators.json', section))
    for rev, path, section in specs:
        blob = subprocess.check_output(['git', 'show', f'{rev}:{path}'], cwd=ROOT)
        rows = json.loads(blob)[section] if section else list(csv.DictReader(io.StringIO(blob.decode('utf-8-sig'))))
        yield {'revision': rev, 'path': path, 'section': section,
               'sha256': hashlib.sha256(blob).hexdigest(), 'records': len(rows)}, rows


def build(out=OUT):
    review_blob = REVIEW.read_bytes()
    reviews = {r['channel_id']: r for r in json.loads(review_blob)['rows']}
    sources, grouped = [], {}
    for source, rows in historical_sources():
        source_index = len(sources)
        sources.append(source)
        for index, raw in enumerate(rows):
            platform = raw.get('platform', 'youtube')
            cid = youtube_id(raw)
            # Only channel IDs merge YouTube records. Handles never prove identity.
            stable_id = raw.get('account_id') or raw.get('discovery_id')
            key = 'youtube:' + cid if cid else (f'{platform}:{stable_id}' if stable_id else f'{platform}:record:{source_index}:{index}')
            status, reason = classify(raw, reviews)
            row = grouped.setdefault(key, {
                'account_key': key, 'platform': platform, 'channel_id': cid,
                'label': raw.get('name') or raw.get('handle') or '',
                'url': raw.get('url') or raw.get('channel_url') or (f'https://www.youtube.com/channel/{cid}' if cid else ''),
                'eligibility_status': status, 'reason_code': reason,
                'included': status == 'STRICT_VIRTUAL', 'origins': [],
            })
            row['origins'].append({'source_index': source_index, 'row_index': index,
                                   'record_id': raw.get('account_id') or raw.get('discovery_id') or cid,
                                   'source_url': raw.get('source_reference') or raw.get('source_url'),
                                   'evidence_id': raw.get('evidence_id')})
    rows = sorted(grouped.values(), key=lambda r: r['account_key'])
    result = {
        'schema_version': 'historical-account-eligibility-v1',
        'policy': 'Only exact YouTube channel IDs with existing STRICT_VIRTUAL eligibility pass. No new evidence review. HOLD is not a non-VTuber finding. Non-ID records deduplicate only by their original stable record ID, not by names or handles; counts are not unique people or channels. No identity merging by name or handle.',
        'review_path': str(REVIEW.relative_to(ROOT)).replace('\\', '/'),
        'review_sha256': hashlib.sha256(review_blob).hexdigest(),
        'sources': sources, 'status_counts': dict(Counter(r['eligibility_status'] for r in rows)),
        'unique_youtube_channel_ids': sum(r['channel_id'] is not None for r in rows),
        'records_without_channel_id': sum(r['channel_id'] is None for r in rows),
        'rows': rows,
    }
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'historical_account_eligibility_v1.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    fields = ['account_key', 'platform', 'channel_id', 'label', 'url', 'eligibility_status', 'reason_code', 'included']
    for filename, selected in [('all_accounts.csv', rows), ('strict_virtual_channels.csv', [r for r in rows if r['included']]),
                               ('held_or_excluded.csv', [r for r in rows if not r['included']])]:
        with (out / filename).open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(selected)
    return result


if __name__ == '__main__':
    result = build()
    print(json.dumps({k: result[k] for k in ('status_counts', 'unique_youtube_channel_ids', 'records_without_channel_id')}, indent=2))
