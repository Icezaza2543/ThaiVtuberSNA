"""Public candidate review, separate from legacy keyword-based classification."""
from copy import deepcopy
import re
from core.expanded_contracts import DATASET_VERSION, FORMATS, ROLES, instant
from core.data_security import assert_public


def candidate(raw, *, candidate_id, discovered_at):
    instant(discovered_at)
    if not candidate_id or not raw.get('source_url'):
        raise ValueError('Candidate needs stable local ID and public source reference')
    result = {'candidate_id': candidate_id, 'channel_id': None,
              'proposed_channel_id': raw.get('channel_id') or None,
              'label': raw.get('name') or raw.get('title') or candidate_id,
              'aliases': [raw['handle']] if raw.get('handle') else [],
              'discovered_at': discovered_at, 'self_description': raw.get('description', ''),
              'source_refs': [raw['source_url']], 'review_status': 'needs-evidence',
              'roles': [], 'presentation_format': 'unknown', 'is_virtual_creator': None,
              'review_history': []}
    assert_public(result, ())
    return result


def review(item, *, decision, reviewer, reviewed_at, reason, source_refs,
           roles=(), presentation_format='unknown', is_virtual_creator=None,
           verified_channel_id=None):
    if decision not in {'approved', 'rejected', 'needs-evidence'} or not reviewer or not reason:
        raise ValueError('Explicit review decision, reviewer and reason required')
    if instant(reviewed_at) < instant(item['discovered_at']):
        raise ValueError('Review cannot precede discovery')
    if not source_refs or not set(source_refs).issubset(item['source_refs']):
        raise ValueError('Review must reference inspected candidate evidence')
    if not set(roles).issubset(ROLES) or presentation_format not in FORMATS:
        raise ValueError('Unknown role or presentation format')
    if is_virtual_creator is not None and type(is_virtual_creator) is not bool:
        raise ValueError('Virtual presentation decision must be explicit')
    if verified_channel_id is not None and not re.fullmatch(r'UC[A-Za-z0-9_-]{22}', verified_channel_id):
        raise ValueError('Do not invent channel IDs; require a verified platform ID')
    if decision == 'approved' and (not roles or is_virtual_creator is None):
        raise ValueError('Approval needs reviewed roles and virtual-presentation decision')
    result = deepcopy(item)
    result.update(review_status=decision, reviewed_at=reviewed_at,
                  roles=sorted(set(roles)), presentation_format=presentation_format,
                  is_virtual_creator=is_virtual_creator,
                  channel_id=verified_channel_id if decision == 'approved' else None)
    result['review_history'].append(dict(decision=decision, reviewer=reviewer,
        reviewed_at=reviewed_at, reason=reason, source_refs=list(source_refs)))
    assert_public(result, ())
    return result


def deduplicate_reviewed(items):
    """Only reviewed platform IDs merge; aliases and unresolved personas never do."""
    result = {}
    for item in items:
        key = ('youtube', item['channel_id']) if item.get('channel_id') and item['review_status'] == 'approved' else ('candidate', item['candidate_id'])
        if key not in result:
            result[key] = deepcopy(item)
            continue
        old = result[key]
        # Conflicting role/identity decisions remain review work, not auto-unioned facts.
        if any(old.get(k) != item.get(k) for k in ('roles', 'presentation_format', 'is_virtual_creator')):
            raise ValueError('Conflicting reviewed identity; reconcile evidence before merging')
        for k in ('aliases', 'source_refs'):
            old[k] = sorted(set(old[k]) | set(item[k]))
        old['review_history'] += deepcopy(item['review_history'])
        old['discovered_at'] = min(old['discovered_at'], item['discovered_at'], key=instant)
    return list(result.values())


def approved_manifest(items, cohort_version):
    if not cohort_version or cohort_version == 'frozen':
        raise ValueError('Expanded cohort needs a new version')
    reviewed = deduplicate_reviewed(items)
    return {'dataset_version': DATASET_VERSION, 'cohort_version': cohort_version,
            'channels': [deepcopy(i) for i in reviewed if i['review_status'] == 'approved'
                         and i.get('channel_id')],
            'production_entities': [deepcopy(i) for i in reviewed if i['review_status'] == 'approved'
                                    and i.get('is_virtual_creator') is False]}
