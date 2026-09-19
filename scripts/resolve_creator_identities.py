"""Resolve accepted creator accounts from recorded, positive identity evidence.

No network is performed here; ``youtube_client`` is a reserved interface. Research
collectors must persist sanitized public evidence before calling this resolver.

Research files have ``rows`` containing discovery_id, canonical_name, checked_urls,
evidence_urls, official_account_urls, reviewer, and evidence records (source_url,
source_kind, summary, supports, observed_at). New personas additionally require
no_existing_persona_match=true. Ownership assertions contain method
(official_crosslink or explicit_official_identity), source_urls, and exactly one
of persona_id / target_discovery_id. Explicit identity merges require two official
sources. Crosslinked discovery components get one deterministic new persona ID.
Optional platform_id/canonical_url record a publicly evidenced stable account ID.
Repeated research files are merged by discovery ID; disagreements fail closed.
Legacy visual decisions are advisory only and never supply positive evidence.
Repeatable trusted-link correction files reject only named, hash-bound verified
links whose cited owner-controlled source disproves ownership; original facts
remain in the audit ledger.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from datetime import datetime
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import parse_qsl, urlsplit, urlunsplit

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.creator_registry_contract import normalize_platform, YOUTUBE_CHANNEL_ID

METHOD_PRIORITY = ('exact_platform_id', 'verified_registry_link', 'official_crosslink', 'explicit_official_identity')
OFFICIAL_KINDS = {'official_profile', 'official_website', 'self_statement', 'youtube_api'}


class ResolutionError(ValueError):
    """A failed resolution retains its audit ledger for queue/reporting tools."""
    def __init__(self, message, ledger):
        super().__init__(message)
        self.ledger = ledger


def normalize_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError('canonical name is required for identity evidence')
    return ' '.join(unicodedata.normalize('NFKC', name).split()).casefold()


def new_persona_id(discovery_id, canonical_name):
    seed = f'{discovery_id}:{normalize_name(canonical_name)}'
    return 'persona_' + hashlib.sha256(seed.encode()).hexdigest()[:20]


def _url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise ValueError('invalid evidence/account URL')
    parsed = urlsplit(value)
    host = (parsed.hostname or '').lower().rstrip('.')
    if parsed.scheme not in {'https', 'http'} or not host or parsed.username or parsed.password:
        raise ValueError('unsafe evidence/account URL')
    if host == 'localhost' or host.endswith('.localhost') or '\\' in value:
        raise ValueError('unsafe evidence/account URL')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError('unsafe evidence/account URL')
    if any(re.search(r'key|token|secret|password|credential|authorization', key, re.I) for key, _ in parse_qsl(parsed.query)):
        raise ValueError('unsafe credential-bearing evidence URL')
    port = parsed.port
    netloc = host + (f':{port}' if port and port not in {80, 443} else '')
    return urlunsplit((parsed.scheme, netloc, parsed.path.rstrip('/') or '/', parsed.query, ''))


def _urls(values):
    if not isinstance(values, list):
        raise ValueError('evidence URLs must be a list')
    return sorted({_url(v) for v in values})


def _account_url(value):
    parsed = urlsplit(_url(value))
    host = parsed.hostname.removeprefix('www.')
    host = {'twitter.com': 'x.com', 'm.youtube.com': 'youtube.com'}.get(host, host)
    path = parsed.path
    if host in {'x.com', 'twitch.tv', 'tiktok.com', 'instagram.com'}:
        path = path.casefold()
    return urlunsplit(('https', host, path, parsed.query, ''))


def _platform_id(row):
    platform = normalize_platform(row['platform'])
    value = row.get('channel_id') if platform == 'youtube' else row.get('platform_id')
    value = value or row.get('platform_id')
    if row.get('id_namespace') == 'handle':
        return None
    if platform == 'youtube':
        if value and not YOUTUBE_CHANNEL_ID.fullmatch(value):
            raise ValueError('invalid YouTube Channel ID')
        parsed = urlsplit(row.get('url', ''))
        match = re.fullmatch(r'/channel/(UC[A-Za-z0-9_-]{22})/?', parsed.path)
        from_url = match.group(1) if parsed.hostname in {'youtube.com', 'www.youtube.com', 'm.youtube.com'} and match else None
        if value and from_url and value != from_url:
            raise ValueError('conflicting persona identifiers in channel URL')
        value = value or from_url
    return (platform, value) if value else None


def _records(payload, key='rows'):
    rows = payload.get(key, [])
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError(f'{key} must be a list of objects')
    return rows


def merge_research(payloads):
    """Combine immutable research batches without silently overwriting decisions."""
    entries = {}
    for payload in payloads:
        for row in _records(payload):
            did = row.get('discovery_id')
            if not isinstance(did, str) or not did:
                raise ValueError('research missing discovery_id')
            if did in entries and entries[did] != row:
                raise ValueError(f'conflicting research for {did}')
            entries[did] = row
    return {'rows': [entries[key] for key in sorted(entries)]}


def _unique_records(payload, table):
    indexed = {}
    for row in _records(payload, table):
        key = row.get('id')
        if not isinstance(key, str) or not key:
            raise ValueError(f'trusted {table} missing ID')
        if key in indexed:
            raise ValueError(f'duplicate trusted {table} ID: {key}')
        indexed[key] = row
    return indexed



def _record_sha256(record):
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def _correct_trusted_links(registry, payloads):
    """Reject explicitly disproved links while retaining immutable original facts.

    Corrections bind to hashes of the original link, account and cited evidence.
    Registry updates therefore require a reviewed correction, never a silent reuse.
    """
    corrections = {}
    fields = {'link_id', 'account_id', 'asserted_persona_id', 'evidence_id', 'disposition',
              'link_sha256', 'account_sha256', 'evidence_sha256', 'source_urls',
              'summary', 'observed_at', 'reviewer'}
    for payload in payloads:
        if payload.get('schema_version') != 1 or 'corrections' not in payload:
            raise ValueError('unsupported trusted link correction schema')
        for row in _records(payload, 'corrections'):
            if set(row) != fields or row.get('disposition') != 'reject_identity_link':
                raise ValueError('invalid trusted link correction fields/disposition')
            key = row['link_id']
            if not isinstance(key, str) or not key:
                raise ValueError('trusted link correction missing link ID')
            if key in corrections and corrections[key] != row:
                raise ValueError('conflicting trusted link corrections')
            corrections[key] = row
    if not corrections:
        return registry, []
    tables = registry.get('tables', registry)
    accounts = _unique_records(tables, 'accounts')
    evidence = _unique_records(tables, 'evidence')
    personas = _unique_records(tables, 'personas')
    # Legacy fixture links may omit IDs, but every corrected link must be unique.
    links = defaultdict(list)
    for link in _records(tables, 'account_links'):
        if isinstance(link.get('id'), str):
            links[link['id']].append(link)
    audit = []
    for key, correction in sorted(corrections.items()):
        matches = links.get(key, [])
        if len(matches) != 1:
            raise ValueError('trusted link correction names unknown/duplicate link')
        link = matches[0]
        account = accounts.get(link.get('account_id'))
        ev = evidence.get(link.get('evidence_id'))
        persona = personas.get(link.get('persona_id'))
        if (link.get('review_status') != 'verified' or link.get('valid_to') or not account
                or not ev or not persona or persona.get('review_status') != 'verified'
                or correction['account_id'] != link.get('account_id')
                or correction['asserted_persona_id'] != link.get('persona_id')
                or correction['evidence_id'] != link.get('evidence_id')):
            raise ValueError('stale or mismatched trusted link correction')
        if any(correction[field] != _record_sha256(record) for field, record in
               [('link_sha256', link), ('account_sha256', account), ('evidence_sha256', ev)]):
            raise ValueError('stale trusted link correction content hash')
        sources = _urls(correction['source_urls'])
        if _account_url(ev['url']) not in {_account_url(u) for u in sources}:
            raise ValueError('trusted link correction must cite the original evidence')
        if any(not isinstance(correction[f], str) or not correction[f].strip()
               for f in ('summary', 'reviewer', 'observed_at')):
            raise ValueError('trusted link correction requires observed review provenance')
        try:
            observed = datetime.fromisoformat(correction['observed_at'].replace('Z', '+00:00'))
            if observed.tzinfo is None:
                raise ValueError
        except ValueError:
            raise ValueError('trusted link correction requires timezone-aware observed_at') from None
        audit.append({'correction': correction, 'original_link': link,
                      'original_account': account, 'original_evidence': ev})
    corrected = dict(tables, account_links=[link for link in _records(tables, 'account_links')
                                           if link.get('id') not in corrections])
    return ({**registry, 'tables': corrected} if 'tables' in registry else corrected), audit


def _indexes(baseline, trusted_registry, excluded_urls=frozenset()):
    names, id_index, url_index, persona_urls = {}, defaultdict(list), defaultdict(list), defaultdict(set)
    baseline_ids = set()
    def register(row, pid, method, evidence):
        key = _platform_id(row)
        claim_urls = {_account_url(row['url'])} | {_account_url(e['source_url']) for e in evidence}
        claim = {'persona_id': pid, 'method': method, 'evidence': evidence, 'excluded': bool(claim_urls & excluded_urls)}
        if key:
            id_index[key].append(claim)
        url_index[_account_url(row['url'])].append(claim)
        if not claim['excluded']:
            persona_urls[pid].add(_account_url(row['url']))
    for row in baseline:
        cid = row.get('channel_id')
        if not isinstance(cid, str) or not YOUTUBE_CHANNEL_ID.fullmatch(cid):
            raise ValueError('invalid baseline Channel ID')
        if cid in baseline_ids:
            raise ValueError('duplicate baseline Channel ID')
        baseline_ids.add(cid)
        name = row.get('canonical_name') or row.get('name')
        pid = row.get('person_id') or new_persona_id(cid, name)
        names[pid] = name
        url = row.get('channel_url') or f'https://www.youtube.com/channel/{cid}'
        ev = {'source_url': url, 'source_kind': 'trusted_baseline', 'summary': 'Trusted baseline exact YouTube Channel ID ownership.',
              'supports': ['account_ownership', 'persona_identity'], 'observed_at': row.get('checked_date')}
        register({'platform': 'youtube', 'channel_id': cid, 'url': url}, pid, 'exact_platform_id', [ev])
    tables = trusted_registry.get('tables', trusted_registry)
    personas = {pid: p for pid, p in _unique_records(tables, 'personas').items() if p.get('review_status') == 'verified'}
    accounts = _unique_records(tables, 'accounts')
    evidence = _unique_records(tables, 'evidence')
    links = []
    for link in _records(tables, 'account_links'):
        ev = evidence.get(link.get('evidence_id'))
        if (link.get('review_status') != 'verified' or link.get('valid_to') or link.get('persona_id') not in personas
                or link.get('account_id') not in accounts or not ev or ev.get('kind') not in OFFICIAL_KINDS or not ev.get('summary')):
            continue
        links.append((link, accounts[link['account_id']], ev))
    aliases = {}
    for link, account, ev in links:
        if {_account_url(account['url']), _account_url(ev['url'])} & excluded_urls:
            continue
        exact = id_index.get(_platform_id(account), [])
        for claim in exact:
            if claim['excluded']:
                continue
            pid = link['persona_id']
            target = claim['persona_id']
            if pid in aliases and aliases[pid] != target:
                raise ValueError(f'conflicting persona baseline mappings for {pid}')
            aliases[pid] = target
    for link, account, ev in links:
        source_pid = link['persona_id']
        pid = aliases.get(source_pid, source_pid)
        names.setdefault(pid, personas[source_pid]['name'])
        record = {'source_url': _url(ev['url']), 'source_kind': ev['kind'], 'summary': ev['summary'],
                  'supports': ['account_ownership', 'persona_identity'], 'observed_at': ev.get('observed_at')}
        register(account, pid, 'verified_registry_link', [record])
    return names, id_index, url_index, persona_urls, aliases, baseline_ids


def _research_evidence(entry, row):
    name = entry.get('canonical_name')
    normalize_name(name)
    if not isinstance(entry.get('reviewer'), str) or not entry['reviewer'].strip():
        raise ValueError('identity evidence requires reviewer')
    checked = _urls(entry.get('checked_urls', []))
    urls = _urls(entry.get('evidence_urls', []))
    official = _urls(entry.get('official_account_urls', []))
    if not checked or not urls or not set(urls) <= set(checked):
        raise ValueError('identity evidence URLs must have been checked')
    if _account_url(row['url']) not in {_account_url(u) for u in official}:
        raise ValueError('identity evidence must identify the accepted official account')
    records = []
    seen = {}
    for evidence in _records(entry, 'evidence'):
        url = _url(evidence.get('source_url'))
        if url not in urls:
            raise ValueError('identity evidence source is missing from checked evidence URLs')
        if evidence.get('source_kind') not in OFFICIAL_KINDS or not evidence.get('summary') or not evidence.get('observed_at'):
            raise ValueError('missing positive official identity evidence')
        if not isinstance(evidence.get('supports'), list):
            raise ValueError('identity evidence requires supports')
        normalized = dict(evidence, source_url=url, supports=sorted(set(evidence['supports'])))
        if url in seen and seen[url] != normalized:
            raise ValueError('conflicting identity evidence for source URL')
        seen[url] = normalized
    records = [seen[key] for key in sorted(seen)]
    if set(seen) != set(urls) or not any('persona_identity' in e['supports'] for e in records):
        raise ValueError('missing positive persona identity evidence')
    return {'canonical_name': name.strip(), 'checked_urls': checked, 'evidence_urls': urls,
            'official_account_urls': official, 'evidence': records, 'reviewer': entry['reviewer']}


def _attachment_path(start, roots, edges):
    queue = deque([(start, [start], [])])
    visited = {start}
    while queue:
        node, path, proofs = queue.popleft()
        if node in roots:
            return path, proofs
        for target, proof in sorted(edges[node], key=lambda item: (METHOD_PRIORITY.index(item[1]['method']), item[0], json.dumps(item[1], sort_keys=True, ensure_ascii=False))):
            if target not in visited:
                visited.add(target)
                queue.append((target, path + [target], proofs + [proof]))
    raise ValueError('missing identity attachment path')


def _establishing_claim(claims):
    if not claims:
        return None
    method = min((claim['method'] for claim in claims), key=METHOD_PRIORITY.index)
    # Every equally establishing source is retained. Registry array order never
    # selects one claim's proof while discarding another equally valid proof.
    evidence = {json.dumps(e, sort_keys=True, ensure_ascii=False): e
                for claim in claims if claim['method'] == method for e in claim['evidence']}
    return {'method': method, 'evidence': [evidence[key] for key in sorted(evidence)]}


def _summary(ledger, selected):
    rows = ledger['resolutions']
    return {'accepted': len(selected), 'resolved': len(rows),
            'by_platform': dict(sorted(Counter(r['platform'] for r in selected).items())),
            'by_outcome': dict(sorted(Counter(r['outcome'] for r in rows).items())),
            'by_method': dict(sorted(Counter(r['method'] for r in rows).items())),
            'unresolved': len(ledger['unresolved']), 'conflicts': len(ledger['conflicts'])}


def resolve_accounts(baseline, review_bundle, trusted_registry, legacy_decisions, researched, youtube_client=None, trusted_link_corrections=None):
    """Produce schema-v1 ledger or raise ResolutionError with its failed audit rows."""
    review = {}
    for row in _records(review_bundle):
        did = row.get('discovery_id')
        if not isinstance(did, str) or not did:
            raise ValueError('review row missing discovery_id')
        if did in review:
            raise ValueError(f'duplicate discovery ID: {did}')
        _url(row['url'])
        review[did] = dict(row, platform=normalize_platform(row['platform']))
    excluded_urls = {_account_url(url) for row in review.values()
                     if row.get('eligibility') not in {'vtuber', 'trusted_baseline'}
                     for url in [row['url'], *row.get('evidence_urls', [])]}
    trusted_registry, correction_audit = _correct_trusted_links(trusted_registry, trusted_link_corrections or [])
    names, id_index, url_index, persona_urls, aliases, baseline_ids = _indexes(baseline, trusted_registry, excluded_urls)
    accepted = {did: r for did, r in review.items() if r.get('eligibility') == 'vtuber'}
    research = {r['discovery_id']: r for r in merge_research([researched])['rows']}
    for did in research:
        if did not in accepted:
            raise ValueError(f'research references excluded/ineligible or unknown discovery: {did}')
    legacy = {r['discovery_id']: r for r in _records(legacy_decisions, 'decisions') if r.get('discovery_id') in accepted}
    ledger = {'schema_version': 1, 'resolutions': [], 'trusted_baseline_verified': [], 'unresolved': [], 'conflicts': []}
    if correction_audit:
        ledger['trusted_link_corrections_applied'] = correction_audit
    for did, row in sorted(review.items()):
        if row.get('eligibility') == 'trusted_baseline':
            key = _platform_id(row)
            if not key or key[0] != 'youtube' or key[1] not in baseline_ids:
                raise ValueError(f'trusted_baseline discovery does not match baseline Channel ID: {did}')
            ledger['trusted_baseline_verified'].append(did)
    parents = {did: did for did in accepted}
    def find(did):
        while parents[did] != did:
            did = parents[did]
        return did
    def union(left, right):
        left, right = sorted((find(left), find(right)))
        parents[right] = left
    claims, material, errors, edges = defaultdict(list), {}, {}, defaultdict(list)
    resolved_accounts = {did: dict(row) for did, row in accepted.items()}
    for did, row in sorted(accepted.items()):
        try:
            if did in research:
                entry = research[did]
                material[did] = _research_evidence(entry, row)
                official_urls = {_account_url(u) for u in material[did]['official_account_urls']}
                identity_urls = official_urls | {_account_url(u) for u in material[did]['evidence_urls']}
                if identity_urls.intersection(excluded_urls):
                    raise ValueError('official identity evidence references excluded/ineligible account')
                if entry.get('platform_id') or entry.get('canonical_url'):
                    resolved = resolved_accounts[did]
                    original_id = _platform_id(row)
                    if entry.get('platform_id'):
                        resolved['platform_id'] = entry['platform_id']
                        if row['platform'] == 'youtube':
                            resolved['channel_id'] = entry['platform_id']
                    if entry.get('canonical_url'):
                        canonical = _url(entry['canonical_url'])
                        if _account_url(canonical) not in official_urls:
                            raise ValueError('resolved canonical URL requires official identity evidence')
                        resolved['url'] = canonical
                    if original_id and original_id != _platform_id(resolved):
                        raise ValueError('conflicting persona account identifiers')
                    row = resolved
            matches = list(id_index.get(_platform_id(row), [])) + list(url_index.get(_account_url(row['url']), []))
            if any(c['excluded'] for c in matches):
                raise ValueError('exact/trusted identity claim references excluded/ineligible account or evidence')
            claims[did].extend(matches)
            if did not in research:
                if not matches:
                    raise ValueError('missing identity evidence')
                continue
            evidences = {e['source_url']: e for e in material[did]['evidence']}
            for assertion in _records(entry, 'assertions'):
                method = assertion.get('method')
                if method not in {'official_crosslink', 'explicit_official_identity'}:
                    raise ValueError('unsupported identity evidence method')
                source_urls = _urls(assertion.get('source_urls', []))
                if not source_urls or any(u not in evidences or 'account_ownership' not in evidences[u]['supports'] for u in source_urls):
                    raise ValueError('missing official account ownership evidence for assertion')
                if method == 'explicit_official_identity' and len({_account_url(u) for u in source_urls}) < 2:
                    raise ValueError('explicit identity merge requires two official sources')
                target, pid = assertion.get('target_discovery_id'), assertion.get('persona_id')
                if bool(target) == bool(pid):
                    raise ValueError('identity assertion must specify one target')
                if target:
                    if target not in accepted:
                        raise ValueError('identity assertion references excluded/ineligible discovery')
                    target_urls = {_account_url(accepted[target]['url'])}
                else:
                    pid = aliases.get(pid, pid)
                    if pid not in names:
                        raise ValueError('identity assertion references unknown persona')
                    target_urls = persona_urls[pid]
                if not target_urls.intersection(_account_url(u) for u in material[did]['official_account_urls']):
                    raise ValueError('official identity evidence does not record target account URL')
                if target:
                    union(did, target)
                    edge = {'method': method, 'evidence': [evidences[u] for u in source_urls]}
                    edges[did].append((target, edge))
                    edges[target].append((did, edge))
                else:
                    claims[did].append({'persona_id': pid, 'method': method, 'evidence': [evidences[u] for u in source_urls]})
        except ValueError as exc:
            errors[did] = str(exc)
    account_owners = {}
    for did, row in sorted(resolved_accounts.items()):
        try:
            keys = [('url', _account_url(row['url']))]
            if _platform_id(row):
                keys.append(('id', _platform_id(row)))
            for key in keys:
                if key in account_owners:
                    errors[did] = errors[account_owners[key]] = 'duplicate accepted account identity'
                account_owners[key] = did
        except ValueError as exc:
            errors[did] = str(exc)
    groups = defaultdict(list)
    for did in sorted(accepted):
        groups[find(did)].append(did)
    for members in groups.values():
        all_claims = [c for did in members for c in claims[did]]
        pids = {c['persona_id'] for c in all_claims}
        problem = next((errors[did] for did in members if did in errors), None)
        conflict = len(pids) > 1 or (problem and 'conflicting persona' in problem)
        if conflict:
            problem = 'conflicting persona links'
        if not pids and not problem and not any(research.get(did, {}).get('no_existing_persona_match') is True for did in members):
            problem = 'missing documented search for an existing persona'
        if problem:
            for did in members:
                ledger['conflicts' if conflict else 'unresolved'].append({'discovery_id': did, 'platform': accepted[did]['platform'],
                    'reason': problem, 'persona_ids': sorted(pids), 'conflict': bool(conflict)})
            continue
        anchor = min(members)
        pid = next(iter(pids)) if pids else new_persona_id(anchor, material[anchor]['canonical_name'])
        name = names[pid] if pids else material[anchor]['canonical_name']
        roots = {did for did in members if claims[did]} if pids else {anchor}
        for did in members:
            # Only this discovery's route to an identity root establishes its
            # attachment. A peer's exact-ID method is never inherited.
            path, path_edges = _attachment_path(did, roots, edges)
            root_claims = claims[path[-1]]
            root_claim = _establishing_claim(root_claims)
            establishing = path_edges[0] if path_edges else root_claim
            method = establishing['method'] if establishing else 'explicit_official_identity'
            method_evidence = establishing['evidence'] if establishing else material[did]['evidence']
            evidence_by_content, checked, official = {}, set(), set()
            for peer in path:
                data = material.get(peer, {})
                checked.update(data.get('checked_urls', []))
                official.update(data.get('official_account_urls', []))
                official.add(accepted[peer]['url'])
                all_evidence = data.get('evidence', []) + [e for c in claims[peer] for e in c['evidence']]
                for e in all_evidence:
                    normalized = dict(e, source_url=_url(e['source_url']))
                    evidence_by_content[json.dumps(normalized, sort_keys=True, ensure_ascii=False)] = normalized
                    checked.add(normalized['source_url'])
            evidence = [evidence_by_content[key] for key in sorted(evidence_by_content)]
            row = resolved_accounts[did]
            record = {'discovery_id': did, 'platform': row['platform'], 'platform_id': (_platform_id(row) or (None, None))[1],
                      'url': _url(row['url']), 'outcome': 'existing_persona' if pids else 'new_persona',
                      'persona_id': pid, 'canonical_name': name, 'method': method, 'conflict': False,
                      'identity_path': path, 'method_evidence_urls': _urls([e['source_url'] for e in method_evidence]),
                      'checked_urls': _urls(list(checked)), 'evidence_urls': _urls([e['source_url'] for e in evidence]),
                      'official_account_urls': _urls(list(official)), 'evidence': evidence,
                      'reviewer': material.get(did, {}).get('reviewer', f'automated:{method}')}
            if did in legacy:
                record['legacy_decision'] = legacy[did].get('decision')
            ledger['resolutions'].append(record)
    for key in ('resolutions', 'unresolved', 'conflicts'):
        ledger[key].sort(key=lambda r: r['discovery_id'])
    ledger['counts'] = _summary(ledger, list(accepted.values()))
    if ledger['unresolved'] or ledger['conflicts']:
        reasons = sorted({r['reason'] for r in ledger['unresolved'] + ledger['conflicts']})
        raise ResolutionError('; '.join(reasons), ledger)
    return ledger


def _valid_prior_path(old, current, entries, peer_ids):
    path = old.get('identity_path')
    if (not isinstance(path, list) or not path or any(not isinstance(node, str) for node in path)
            or path[0] != old['discovery_id'] or len(path) != len(set(path)) or not set(path) <= peer_ids):
        return False
    verified_edges = defaultdict(list)
    for source in peer_ids:
        for assertion in entries.get(source, {}).get('assertions', []):
            target = assertion.get('target_discovery_id')
            if target in peer_ids:
                verified_edges[frozenset((source, target))].append(assertion)
    if any(frozenset(pair) not in verified_edges for pair in zip(path, path[1:])):
        return False
    if len(path) > 1:
        first_edge = verified_edges[frozenset(path[:2])]
        if not any(assertion['method'] == old['method'] and
                   set(_urls(old.get('method_evidence_urls', []))) <= set(_urls(assertion['source_urls']))
                   for assertion in first_edge):
            return False
    endpoint = path[-1]
    if old['outcome'] == 'new_persona':
        # A historical provisional anchor can cease to be the chosen anchor
        # after a later verified crosslink, but must still prove the old ID.
        return endpoint in entries and old['persona_id'] == new_persona_id(endpoint, entries[endpoint]['canonical_name'])
    return (current[endpoint]['identity_path'] == [endpoint]
            and current[endpoint]['outcome'] == 'existing_persona'
            and current[endpoint]['persona_id'] == old['persona_id'])


def _verify_previous(previous, current, research, review):
    """Authenticate old facts against current evidence, then regenerate output.

    A formerly separate new persona may now be a member of a larger component.
    Its earlier deterministic anchor remains a valid historical identity claim;
    arbitrary persona IDs and unsupported source material never do.
    """
    entries = {r['discovery_id']: r for r in _records(research)}
    discoveries = {r['discovery_id']: r for r in _records(review)}
    prior_ids = set()
    components = defaultdict(list)
    for row in current.values():
        components[row['persona_id']].append(row)
    for old in _records(previous, 'resolutions'):
        did = old.get('discovery_id')
        now = current.get(did)
        if not now or did in prior_ids:
            raise ValueError(f'conflicting or unverifiable previous resolution: {did}')
        peers = components[now['persona_id']]
        peer_ids = {r['discovery_id'] for r in peers}
        evidence = {json.dumps(e, sort_keys=True, ensure_ascii=False) for r in peers for e in r['evidence']}
        prior_evidence = old.get('evidence', [])
        valid = bool(prior_evidence) and all(json.dumps(e, sort_keys=True, ensure_ascii=False) in evidence for e in prior_evidence)
        valid &= old.get('conflict') is False and old.get('platform') == now['platform']
        original = discoveries[did]
        original_id = (_platform_id(original) or (None, None))[1]
        own_ids = {original_id, now['platform_id']}
        valid &= old.get('platform_id') in own_ids
        own_urls = {_account_url(original['url']), _account_url(now['url'])}
        if entries.get(did, {}).get('canonical_url'):
            own_urls.add(_account_url(entries[did]['canonical_url']))
        valid &= _account_url(old['url']) in own_urls
        if 'canonical_url' in old:
            valid &= _account_url(old['canonical_url']) in own_urls
        for field in ('checked_urls', 'official_account_urls'):
            allowed = {_account_url(u) for r in peers for u in r[field]}
            valid &= bool(old.get(field)) and {_account_url(u) for u in old[field]} <= allowed
        valid &= _urls(old.get('evidence_urls', [])) == _urls([e['source_url'] for e in prior_evidence])
        valid &= set(_urls(old.get('evidence_urls', []))) <= set(_urls(old.get('checked_urls', [])))
        historical_names = {r['canonical_name'] for r in peers} | {entries[p]['canonical_name'].strip() for p in peer_ids if p in entries}
        valid &= old.get('canonical_name') in historical_names
        if old.get('outcome') == 'new_persona':
            anchors = {new_persona_id(p, entries[p]['canonical_name']) for p in peer_ids if p in entries}
            valid &= old.get('persona_id') in anchors
        elif old.get('outcome') == 'existing_persona':
            valid &= now['outcome'] == 'existing_persona' and old.get('persona_id') == now['persona_id']
        else:
            valid = False
        allowed_methods = {now['method']}
        method_sources = set(now['method_evidence_urls']) if old.get('method') == now['method'] else set()
        if old.get('outcome') == 'new_persona':
            allowed_methods.add('explicit_official_identity')
            if old.get('method') == 'explicit_official_identity':
                method_sources.update(e['source_url'] for e in entries.get(did, {}).get('evidence', []) if 'persona_identity' in e.get('supports', []))
        for peer in peer_ids:
            for assertion in entries.get(peer, {}).get('assertions', []):
                if peer == did or assertion.get('target_discovery_id') == did:
                    allowed_methods.add(assertion['method'])
                    if assertion['method'] == old.get('method'):
                        method_sources.update(assertion['source_urls'])
        valid &= old.get('method') in allowed_methods
        valid &= old.get('reviewer') in {now['reviewer'], f"automated:{old.get('method')}"}
        if 'method_evidence_urls' in old:
            valid &= bool(old['method_evidence_urls']) and set(_urls(old['method_evidence_urls'])) <= set(old['evidence_urls']) & set(_urls(list(method_sources)))
        valid &= _valid_prior_path(old, current, entries, peer_ids)
        if not valid:
            raise ValueError(f'conflicting or unverifiable previous resolution: {did}')
        prior_ids.add(did)
    return prior_ids


def _load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('review-bundle', 'baseline', 'trusted-registry', 'legacy-decisions'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--researched', action='append', type=Path, default=[])
    parser.add_argument('--trusted-link-corrections', action='append', type=Path, default=[],
                        help='Explicit, hash-bound rejection of disproved verified ownership links.')
    parser.add_argument('--platform', action='append', default=[])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--merge-existing', type=Path)
    parser.add_argument('--queue', action='store_true', help='Write a partial audit ledger including unresolved/conflicting rows.')
    parser.add_argument('--validate-only', action='store_true', help='Require declared eligibility counts to match the complete bundle and resolve the selected platforms; write no files.')
    args = parser.parse_args(argv)
    try:
        review = _load(args.review_bundle)
        research = merge_research([_load(path) for path in args.researched])
        try:
            ledger = resolve_accounts(_load(args.baseline), review, _load(args.trusted_registry), _load(args.legacy_decisions), research,
                                      trusted_link_corrections=[_load(path) for path in args.trusted_link_corrections])
        except ResolutionError as exc:
            ledger = exc.ledger
        all_rows = {r['discovery_id']: r for r in ledger['resolutions']}
        platforms = {normalize_platform(p) for p in args.platform}
        selected = {r['discovery_id']: r for r in review['rows'] if r['eligibility'] == 'vtuber' and (not platforms or normalize_platform(r['platform']) in platforms)}
        if args.merge_existing:
            previous = _load(args.merge_existing)
            if previous.get('schema_version') != 1:
                raise ValueError('unsupported previous resolution schema')
            current_corrections = {json.dumps(row, sort_keys=True, ensure_ascii=False)
                                   for row in ledger.get('trusted_link_corrections_applied', [])}
            if any(json.dumps(row, sort_keys=True, ensure_ascii=False) not in current_corrections
                   for row in previous.get('trusted_link_corrections_applied', [])):
                raise ValueError('previous ledger requires its verified trusted link corrections')
            prior_ids = _verify_previous(previous, all_rows, research, review)
            selected.update({r['discovery_id']: r for r in review['rows'] if r['discovery_id'] in prior_ids})
        for key in ('resolutions', 'unresolved', 'conflicts'):
            ledger[key] = [r for r in ledger[key] if r['discovery_id'] in selected]
        ledger['counts'] = _summary(ledger, list(selected.values()))
        print(json.dumps(ledger['counts'], sort_keys=True))
        failed = bool(ledger['unresolved'] or ledger['conflicts'])
        if args.validate_only:
            actual_counts = dict(Counter(r.get('eligibility') for r in review['rows']))
            declared_counts = review.get('eligibility_counts')
            valid_counts = (isinstance(declared_counts, dict)
                            and all(type(value) is int and value > 0 for value in declared_counts.values())
                            and declared_counts == actual_counts)
            expected = len(selected) if platforms else actual_counts.get('vtuber', 0)
            return int(failed or not valid_counts or not expected or len(ledger['resolutions']) != expected)
        if args.output and (not failed or args.queue):
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.output.with_suffix(args.output.suffix + '.tmp')
            temporary.write_text(json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
            temporary.replace(args.output)
        return int(failed)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
