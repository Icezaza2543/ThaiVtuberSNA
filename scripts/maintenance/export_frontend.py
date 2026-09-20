"""Build a public frontend projection without publishing or modifying source data."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from registry.store import load, rows


def safe_url(value: str | None) -> str | None:
    """Accept public HTTPS links, not credentials, private hosts or token URLs."""
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return None
    try:
        u = urlsplit(value)
        host = (u.hostname or '').lower().rstrip('.')
        if u.scheme != 'https' or not host or u.username or u.password or u.port not in (None, 443):
            return None
        if '.' not in host or host.endswith(('.localhost', '.local', '.internal', '.test', '.example', '.invalid')):
            return None
        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            pass
        for key, _ in parse_qsl(u.query, keep_blank_values=True):
            if any(word in key.lower() for word in ('token', 'secret', 'password', 'auth', 'signature', 'api_key', 'apikey', 'credential', 'session', 'jwt')):
                return None
        return value
    except (ValueError, TypeError):
        return None


def build_catalog(db, checksum: str) -> dict:
    all_people = rows(db, 'personas')
    people = {p['id']: p for p in all_people if p['review_status'] == 'verified'}
    accounts = {a['id']: a for a in rows(db, 'accounts')}
    evidence = {e['id']: e for e in rows(db, 'evidence')}
    links = [l for l in rows(db, 'account_links') if l['review_status'] == 'verified' and l['persona_id'] in people]
    grouped = defaultdict(list)
    for link in links:
        grouped[(link['persona_id'], link['account_id'])].append(link)

    def proof(eid):
        ev = evidence[eid]
        url = safe_url(ev['url'])
        return {'url': url, 'observed_at': ev['observed_at']} if url else None

    creators = {}
    for pid, p in people.items():
        creators[pid] = {
            'id': pid, 'name': p['name'], 'format': p['format'],
            'roles': json.loads(p['roles']), 'thai_relation': p['thai_relation'],
            'review_status': 'verified', 'sources': [pr] if (pr := proof(p['evidence_id'])) else [],
            'accounts': [], 'affiliations': [], 'events': [],
        }
    excluded_pairs = 0
    published_accounts = set()
    for (pid, aid), pair in sorted(grouped.items()):
        a = accounts[aid]
        url = safe_url(a['url'])
        if not url:
            excluded_pairs += 1
            continue
        records = [{'valid_from': l['valid_from'], 'valid_to': l['valid_to'], 'source': proof(l['evidence_id'])} for l in pair]
        creators[pid]['accounts'].append({
            'id': aid, 'platform': a['platform'], 'platform_id': str(a['platform_id']),
            'id_namespace': a['id_namespace'], 'handle': a['handle'],
            'name': a['name'], 'url': url, 'ownership_evidence': records,
        })
        published_accounts.add(aid)
    for table, key, fields in (
        ('affiliations', 'affiliations', ('organization', 'valid_from', 'valid_to')),
        ('lifecycle_events', 'events', ('event_type', 'event_date', 'date_precision')),
    ):
        for row in rows(db, table):
            if row['review_status'] == 'verified' and row['persona_id'] in creators:
                creators[row['persona_id']][key].append({**{k: row[k] for k in fields}, 'source': proof(row['evidence_id'])})
    for creator in creators.values():
        creator['accounts'].sort(key=lambda a: (a['platform'], a['id']))
        creator['platforms'] = sorted({a['platform'] for a in creator['accounts']})
    result = sorted(creators.values(), key=lambda p: (p['name'].casefold(), p['id']))
    return {
        'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(),
        'source_registry_sha256': checksum,
        'count_semantics': {
            'inventory': 'All catalog records, not a census or an estimate of private people.',
            'published': 'Reviewed public personas and distinct reviewed persona-account pairs.',
            'ownership': 'Reviewed association is not current control; preserve date intervals.',
            'activity': 'No live status, popularity, audience overlap or engagement is inferred.',
            'missing_platform': 'Unknown/not recorded, not proof of absence.',
        },
        'inventory': {'personas': len(all_people), 'verified_personas': len(people), 'accounts': len(accounts),
                      'accounts_by_platform': dict(sorted(Counter(a['platform'] for a in accounts.values()).items()))},
        'published': {'personas': len(result), 'accounts': len(published_accounts),
                      'persona_account_pairs': sum(len(p['accounts']) for p in result),
                      'reviewed_link_records': len(links), 'excluded_unsafe_url_pairs': excluded_pairs,
                      'accounts_by_platform': dict(sorted(Counter(accounts[a]['platform'] for a in published_accounts).items()))},
        'creators': result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/registry.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'web/public/data/registry.json')
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if not source.is_file():
        parser.error('Source registry does not exist')
    protected = ('data', 'intake', 'reviews', 'schemas', 'registry', '.agents')
    if output == source or any(output.is_relative_to(ROOT / p) for p in protected):
        parser.error('Output must be a generated frontend/dist path, not a protected source path')
    original = source.read_bytes()
    db = load(source)
    try:
        data = build_catalog(db, hashlib.sha256(original).hexdigest())
    finally:
        db.close()
    if source.read_bytes() != original:
        raise RuntimeError('Registry changed while exporting; retry from one snapshot')
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=output.parent, delete=False) as stream:
            temp = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, separators=(',', ':'))
            stream.write('\n')
        os.replace(temp, output)
    finally:
        if temp and temp.exists():
            temp.unlink()
    print(json.dumps({'output': str(output), 'bytes': output.stat().st_size,
                      'inventory': data['inventory'], 'published': data['published']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
