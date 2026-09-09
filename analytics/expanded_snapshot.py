"""Dated public membership layered over existing aggregate overlap calculations.

Inputs are reviewed public identity evidence and window-specific aggregate edges.
Discovery timestamps and channel creation dates deliberately cannot grant membership.
"""
from copy import deepcopy
from core.expanded_contracts import DATASET_VERSION, EDGE_TYPES, instant
from core.data_security import assert_public

PERIOD_ATTRIBUTES = ('subscribers', 'agency', 'status', 'priority')


def build_snapshot(*, creators, evidence, edges, snapshot_id, cohort_version,
                   window_start, window_end, collected_through, collected_at,
                   generated_at, known_secrets=()):
    start, end, cutoff = map(instant, (window_start, window_end, collected_through))
    if start > end or cutoff > instant(collected_at) or instant(collected_at) > instant(generated_at):
        raise ValueError('Invalid snapshot chronology')
    if len({c['id'] for c in creators}) != len(creators):
        raise ValueError('Duplicate creator ID')
    if len({e['evidence_id'] for e in evidence}) != len(evidence):
        raise ValueError('Duplicate evidence ID')
    # Future requested windows are unavailable, never synthetic empty observations.
    result = dict(snapshot_id=snapshot_id, dataset_version=DATASET_VERSION,
                  cohort_version=cohort_version, window_start=window_start, window_end=window_end,
                  collected_through=collected_through, collected_at=collected_at,
                  generated_at=generated_at, coverage_state='NO_SNAPSHOT' if start > cutoff else 'PARTIAL',
                  nodes=[], edges=[], unknown_history=[], confirmed_not_started=[])
    if start > cutoff:
        return result
    end = min(end, cutoff)
    for creator in creators:
        if creator.get('review_status') != 'approved':
            continue
        relevant = [e for e in evidence if e['creator_id'] == creator['id'] and e.get('review_status') == 'approved']
        starts = [instant(e['effective_from']) for e in relevant
                  if e.get('evidence_kind') == 'identity_start' and e.get('date_precision') == 'exact'
                  and e.get('effective_from')]
        # Contradictory exact starts require review, never choose a convenient date.
        if len(set(starts)) > 1:
            result['unknown_history'].append(creator['id'])
            continue
        if starts and starts[0] > end:
            result['confirmed_not_started'].append(creator['id'])
            continue
        members = []
        for e in relevant:
            if e.get('evidence_kind') not in {'virtual_activity', 'identity_start'}:
                continue
            if not e.get('source_ref') or not e.get('identity_epoch_id') or e.get('date_precision') != 'exact':
                continue
            lo = instant(e['effective_from'])
            hi = instant(e.get('effective_to') or e['effective_from'])
            if hi < lo:
                raise ValueError('Reversed evidence interval')
            if starts and lo < starts[0]:
                continue
            if lo <= end and hi >= start:
                members.append(e)
        if not members:
            result['unknown_history'].append(creator['id'])
            continue
        node = {k: creator[k] for k in ('id', 'label', 'handle') if k in creator}
        node.update(membership_evidence_refs=[e['evidence_id'] for e in members],
                    visibility_state='EVIDENCED', **{k: None for k in PERIOD_ATTRIBUTES})
        # Only explicit reviewed effective intervals qualify attributes, no carry-forward.
        for attr in PERIOD_ATTRIBUTES:
            observations = [e for e in relevant if e.get('evidence_kind') == 'attribute'
                            and e.get('attribute') == attr and e.get('source_ref')
                            and e.get('date_precision') == 'exact' and e.get('effective_to')
                            and instant(e['effective_from']) <= end <= instant(e['effective_to'])]
            if len(observations) == 1:
                node[attr] = observations[0]['value']
        node.update(degree=None, betweenness=None, pagerank=None)
        result['nodes'].append(node)
    ids = {n['id'] for n in result['nodes']}
    for edge in edges:
        if edge.get('edge_type') not in EDGE_TYPES:
            raise ValueError('Unknown relationship type')
        if edge['source'] not in ids or edge['target'] not in ids:
            continue
        # Aggregate edges are accepted only for this exact window, not upload dates.
        if edge.get('window_start') != window_start or edge.get('window_end') != window_end:
            raise ValueError('Edge window differs from selected snapshot')
        if edge['edge_type'] != 'audience_overlap':
            if not edge.get('source_ref') or edge.get('review_status') != 'approved':
                raise ValueError('Relationship evidence must be reviewed')
            if any(k.startswith(('shared_', 'jaccard', 'overlap')) for k in edge):
                raise ValueError('Relationship evidence cannot contain audience metrics')
        result['edges'].append(deepcopy(edge))
    assert_public(result, known_secrets)
    return result


def snapshot_bundle(snapshots, *, synthetic=False):
    if not snapshots or len({s['snapshot_id'] for s in snapshots}) != len(snapshots):
        raise ValueError('Snapshots must have unique IDs')
    if any(s['dataset_version'] != DATASET_VERSION for s in snapshots):
        raise ValueError('Wrong expanded namespace')
    return {'dataset_version': DATASET_VERSION, 'synthetic': synthetic,
            'snapshots': deepcopy(snapshots)}
