"""Platform-independent projections of *recorded* identity review decisions.

Account resolution, virtual-creator scope, and ownership are separate facts.
One reviewed owner profile can establish scope and ownership; neither YouTube
nor a second platform is required. These helpers never infer or verify a claim.
"""
from collections import defaultdict


def verified_account_personas(personas, account_links):
    """Return all reviewed persona IDs per account, without choosing an owner.

A shared account may map to several personas. Callers requiring one owner must
handle that ambiguity, not select the first/last row. This is an inventory view
of retained reviews, not proof of current control or activity on a given date.
    """
    verified = {p['id'] for p in personas if p['review_status'] == 'verified'}
    result = defaultdict(set)
    for link in account_links:
        if link['review_status'] == 'verified' and link['persona_id'] in verified:
            result[link['account_id']].add(link['persona_id'])
    return {aid: sorted(pids) for aid, pids in result.items()}


def unresolved_account_scope():
    """A URL without a resolved account is unknown, not a non-virtual creator."""
    return {'account_resolved': False, 'virtual_creator_status': 'needs_evidence',
            'verified_persona_ids': [], 'reason': 'account_resolution_review'}


def account_scope_index(accounts, personas, account_links):
    """Explain creator-scope status for every account, on equal platform terms.

A resolved account/candidate alone does not establish a virtual persona. Both
persona-scope review and ownership-link review must be present. Missing reviews
remain needs_evidence; platform count and YouTube presence are never criteria.
    """
    verified = verified_account_personas(personas, account_links)
    ownership_reviewed = {l['account_id'] for l in account_links if l['review_status'] == 'verified'}
    result = {}
    for account in accounts:
        aid = account['id']
        pids = verified.get(aid, [])
        reason = ('virtual_creator_verified' if pids else
                  'persona_scope_review' if aid in ownership_reviewed else 'account_ownership_review')
        result[aid] = {'account_resolved': True,
                       'virtual_creator_status': 'verified' if pids else 'needs_evidence',
                       'verified_persona_ids': pids, 'reason': reason}
    return result
