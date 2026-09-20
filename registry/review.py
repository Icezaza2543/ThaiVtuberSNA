"""Read-only review queues and dossiers from explicitly recorded relationships."""

from collections import Counter

from .store import PLATFORMS, TABLES, rows
from .identity import account_scope_index, unresolved_account_scope

RECORD_TABLES = {'candidate': 'candidates', 'account': 'accounts', 'persona': 'personas'}
WORK_ITEM_KINDS = ('candidate', 'account_issue')
QUEUE_KINDS = (*WORK_ITEM_KINDS, 'account_scope')
QUEUE_STATUSES = ('pending', 'completed', 'all')
DEFAULT_REASON_ORDER = 99
REASON_ORDER = {
    'legacy_identity_collision': 0,
    'conflicting_ownership': 1,
    'identity_blocker': 2,
    'account_ownership_review': 3,
    'unlinked_verified_persona': 4,
    'account_resolution_review': 10,
    'stable_id_resolution': 11,
    'candidate_review': 12,
    'lifecycle_conflict': 20,
    'lifecycle_review': 21,
    'unverified_lifecycle': 22,
    'legacy_scope_review': 30,
    'persona_scope_review': 31,
    'coverage_expansion': 32,
    'virtual_creator_verified': 40,
}


PRIORITY_CLASSES = {
    1: 'identity_blocker',
    2: 'stable_id_resolution',
    3: 'lifecycle',
    4: 'coverage_expansion',
}


def classify_item_priority(item):
    """Deterministic priority assignment:
    Priority 1: Identity blockers (collisions, conflicting ownership, unlinked verified personas)
    Priority 2: Stable-ID resolution (candidates needing stable platform_id)
    Priority 3: Lifecycle claims/conflicts
    Priority 4: Coverage expansion (general candidate leads, legacy scope reviews)
    """
    reason = item.get('reason')
    if reason in ('legacy_identity_collision', 'conflicting_ownership', 'identity_blocker'):
        return 1, 'identity_blocker'
    if reason in ('account_ownership_review', 'unlinked_verified_persona'):
        return 1, 'identity_blocker'
    if reason in ('account_resolution_review', 'stable_id_resolution'):
        return 2, 'stable_id_resolution'
    if item.get('kind') == 'candidate':
        return 2, 'stable_id_resolution'
    if reason in ('lifecycle_conflict', 'lifecycle_review', 'unverified_lifecycle'):
        return 3, 'lifecycle'
    if reason in ('legacy_scope_review', 'candidate_review', 'coverage_expansion'):
        return 4, 'coverage_expansion'
    return 4, 'coverage_expansion'


def review_queue(db, *, platform=None, kind=None, status='pending', priority=None, query='', limit=50, offset=0):
    """Count work items, not people; several issues may concern the same account."""
    if platform is not None and platform not in PLATFORMS:
        raise ValueError('Unsupported platform')
    if kind is not None and kind not in QUEUE_KINDS:
        raise ValueError('Unsupported queue kind')
    if status not in QUEUE_STATUSES:
        raise ValueError('Unsupported queue status')
    if priority is not None and priority not in (1, 2, 3, 4, '1', '2', '3', '4', *PRIORITY_CLASSES.values()):
        raise ValueError('Unsupported priority')
    if not 1 <= limit <= 500 or offset < 0:
        raise ValueError('limit must be between 1 and 500 and offset must be nonnegative')
    target_priority = int(priority) if isinstance(priority, str) and priority.isdigit() else priority
    accounts = {r['id']: r for r in rows(db, 'accounts')}
    accounts_by_url = {a['url']: a for a in accounts.values() if a.get('url')}
    items = []
    for candidate in rows(db, 'candidates'):
        note = ''
        matched_account = accounts_by_url.get(candidate['url'])
        if matched_account:
            note = f"Stable account already present: {matched_account['id']}"
        items.append(dict(id=candidate['id'], kind='candidate', record_id=candidate['id'],
                          platform=candidate['platform'], name=candidate['name'], url=candidate['url'],
                          status=candidate['review_status'], reason='candidate_review', note=note,
                          matched_account_id=matched_account['id'] if matched_account else None))
    for issue in rows(db, 'review_queue'):
        account = accounts[issue['account_id']]
        items.append(dict(id=issue['id'], kind='account_issue', record_id=account['id'],
                          platform=account['platform'], name=account['name'], url=account['url'],
                          status=issue['status'], reason=issue['reason'], note=issue['note']))
    # An opt-in derived view covers every resolved account, including those
    # without legacy YouTube issues or unresolved candidates. Default work-item
    # counts remain backwards compatible and are not mixed with account counts.
    count_kinds = WORK_ITEM_KINDS
    semantics = 'Work items: candidates and account issues are distinct; an account may have several issues.'
    if kind == 'account_scope':
        count_kinds = ('account_scope',)
        semantics = 'One creator-scope review row per resolved account; platform count is not a verification criterion.'
        scope = account_scope_index(accounts.values(), rows(db, 'personas'), rows(db, 'account_links'))
        items = [dict(id='scope:' + aid, kind='account_scope', record_id=aid,
                      platform=account['platform'], name=account['name'], url=account['url'],
                      status=scope[aid]['virtual_creator_status'], reason=scope[aid]['reason'],
                      note='Reviewed virtual presentation, Thai relation and account ownership; no YouTube or second platform required.',
                      verification=scope[aid]) for aid, account in accounts.items()]
    for item in items:
        p_num, p_class = classify_item_priority(item)
        item['priority'] = p_num
        item['priority_class'] = p_class
    needle = query.casefold()
    filtered = []
    for item in items:
        pending = item['status'] in {'open', 'needs_evidence'}
        if platform is not None and item['platform'] != platform:
            continue
        if kind is not None and item['kind'] != kind:
            continue
        if status != 'all' and pending != (status == 'pending'):
            continue
        if target_priority is not None:
            if target_priority in PRIORITY_CLASSES and item['priority'] != target_priority:
                continue
            if target_priority in PRIORITY_CLASSES.values() and item['priority_class'] != target_priority:
                continue
        if needle and not any(needle in str(value).casefold() for value in item.values()):
            continue
        filtered.append(item)
    filtered.sort(key=lambda item: (item['priority'],
                                    REASON_ORDER.get(item['reason'], DEFAULT_REASON_ORDER),
                                    item['platform'],
                                    item['name'].casefold(), item['id']))
    page = filtered[offset:offset + limit]
    return {
        'count_semantics': semantics,
        'filters': {'platform': platform, 'kind': kind, 'status': status, 'priority': priority, 'query': query},
        'total': len(filtered),
        'totals_by_kind': {key: sum(item['kind'] == key for item in filtered) for key in count_kinds},
        'totals_by_priority': {
            p_class: sum(item['priority'] == p_num for item in filtered)
            for p_num, p_class in sorted(PRIORITY_CLASSES.items())
        },
        'totals_by_reason': dict(sorted(Counter(item['reason'] for item in filtered).items())),
        'limit': limit, 'offset': offset,
        'next_offset': offset + len(page) if offset + len(page) < len(filtered) else None,
        'items': page,
    }


def inspect_record(db, kind, record_id):
    """Keep original rows/statuses; never match records by names or handles."""
    if kind not in RECORD_TABLES:
        raise ValueError('Choose candidate, account or persona')
    data = {table: rows(db, table) for table in TABLES}
    subject_table = RECORD_TABLES[kind]
    record = next((r for r in data[subject_table] if r['id'] == record_id), None)
    if record is None:
        raise ValueError(f'Unknown {kind}: {record_id}')

    account_ids = set()
    persona_ids = set()
    if kind == 'account':
        account_ids.add(record_id)
    elif kind == 'candidate' and record['account_id']:
        account_ids.add(record['account_id'])
    elif kind == 'persona':
        persona_ids.add(record_id)
    links = [r for r in data['account_links']
             if r['account_id'] in account_ids or r['persona_id'] in persona_ids]
    account_ids.update(r['account_id'] for r in links)
    persona_ids.update(r['persona_id'] for r in links)

    selected = {table: [] for table in TABLES}
    selected['account_links'] = links
    selected['accounts'] = [r for r in data['accounts'] if r['id'] in account_ids]
    selected['personas'] = [r for r in data['personas'] if r['id'] in persona_ids]
    selected['candidates'] = [r for r in data['candidates']
                              if (kind == 'candidate' and r['id'] == record_id) or r['account_id'] in account_ids]
    for table in ('review_queue', 'legacy_claims'):
        selected[table] = [r for r in data[table] if r['account_id'] in account_ids]
    for table in ('lifecycle_events', 'affiliations'):
        selected[table] = [r for r in data[table] if r['persona_id'] in persona_ids]
    selected['activity_observations'] = [r for r in data['activity_observations']
                                         if (kind == 'persona' and r['persona_id'] == record_id)
                                         or (kind != 'persona' and r['account_id'] in account_ids)]
    selected['continuity_links'] = [r for r in data['continuity_links']
                                    if r['from_persona_id'] in persona_ids or r['to_persona_id'] in persona_ids]
    # Include the endpoint records as context, without following their other accounts.
    endpoint_ids = {r[key] for r in selected['continuity_links']
                    for key in ('from_persona_id', 'to_persona_id')}
    selected['personas'] = [r for r in data['personas'] if r['id'] in persona_ids | endpoint_ids]
    candidate_ids = {r['id'] for r in selected['candidates']}
    selected['discovery_hits'] = [r for r in data['discovery_hits']
                                  if r['account_id'] in account_ids or r['candidate_id'] in candidate_ids]
    run_ids = {r['run_id'] for r in selected['discovery_hits']}
    selected['discovery_runs'] = [r for r in data['discovery_runs'] if r['id'] in run_ids]
    evidence_ids = {r['evidence_id'] for records in selected.values() for r in records if 'evidence_id' in r}
    selected['evidence'] = [r for r in data['evidence'] if r['id'] in evidence_ids]
    result = {
        'subject': {'kind': kind, 'id': record_id},
        'scope': 'Stored relationships only, with their original review statuses; inclusion is not verification.',
        'record': record,
        'tables': selected,
    }
    if kind in {'account', 'candidate'}:
        aid = record_id if kind == 'account' else record.get('account_id')
        scope = account_scope_index(data['accounts'], data['personas'], data['account_links'])
        result['verification'] = scope.get(aid, unresolved_account_scope())
    return result
