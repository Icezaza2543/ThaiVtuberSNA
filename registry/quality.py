"""Registry data-quality, freshness monitoring, and unresolved review inventory.

Data quality and evidence freshness monitoring measures registry observability
and backlog prioritization, NOT creator activity or absence. Old evidence indicates
the registry has not recently re-observed a claim; it does not prove the claim
is no longer true.
"""
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
import json
from pathlib import Path

from .store import PLATFORMS, rows


def _parse_date(date_val):
    if not date_val:
        return None
    try:
        return date.fromisoformat(str(date_val)[:10])
    except Exception:
        return None


def generate_data_quality_report(db, as_of='2026-09-17'):
    """Analyze registry quality, backlog, and evidence freshness without mutating data."""
    cutoff = _parse_date(as_of) or date.today()
    personas = {p['id']: p for p in rows(db, 'personas')}
    accounts = {a['id']: a for a in rows(db, 'accounts')}
    account_links = rows(db, 'account_links')
    candidates = rows(db, 'candidates')
    evidence = {e['id']: e for e in rows(db, 'evidence')}
    lifecycle = rows(db, 'lifecycle_events')

    verified_personas = {pid: p for pid, p in personas.items() if p['review_status'] == 'verified'}
    needs_ev_personas = {pid: p for pid, p in personas.items() if p['review_status'] == 'needs_evidence'}

    # 1. Account ownership mapping
    persona_verified_accounts = defaultdict(set)
    persona_all_accounts = defaultdict(set)
    account_to_links = defaultdict(list)
    needs_ev_links = []

    for link in account_links:
        aid = link['account_id']
        pid = link['persona_id']
        account_to_links[aid].append(link)
        persona_all_accounts[pid].add(aid)
        if link['review_status'] == 'verified' and pid in verified_personas:
            persona_verified_accounts[pid].add(aid)
        if link['review_status'] == 'needs_evidence':
            acc = accounts.get(aid, {})
            ev = evidence.get(link['evidence_id'], {})
            needs_ev_links.append({
                'link_id': link['id'],
                'persona_id': pid,
                'persona_name': personas.get(pid, {}).get('name', 'Unknown'),
                'account_id': aid,
                'platform': acc.get('platform', 'unknown'),
                'handle': acc.get('handle') or acc.get('platform_id', ''),
                'evidence_kind': ev.get('kind', 'unknown'),
                'evidence_url': ev.get('url', '')
            })

    # Shared accounts (linked to multiple personas)
    shared_accounts = []
    for aid, links_for_acc in account_to_links.items():
        distinct_personas = {l['persona_id'] for l in links_for_acc}
        if len(distinct_personas) > 1:
            acc = accounts.get(aid, {})
            shared_accounts.append({
                'account_id': aid,
                'platform': acc.get('platform', 'unknown'),
                'platform_id': acc.get('platform_id', ''),
                'name': acc.get('name', ''),
                'classification': 'shared_account_review_context',
                'linked_personas': [
                    {
                        'persona_id': l['persona_id'],
                        'persona_name': personas.get(l['persona_id'], {}).get('name', 'Unknown'),
                        'review_status': l['review_status']
                    }
                    for l in links_for_acc
                ]
            })

    # Unlinked accounts (not in any account_link)
    linked_account_ids = set(account_to_links.keys())
    unlinked_accounts = [a for aid, a in accounts.items() if aid not in linked_account_ids]
    unlinked_by_platform = dict(Counter(a['platform'] for a in unlinked_accounts))

    # Personas: 0 verified accounts vs 1 verified account
    zero_account_personas = []
    single_platform_personas = []
    stale_evidence_personas = []

    for pid, p in verified_personas.items():
        v_accounts = persona_verified_accounts[pid]
        p_platforms = {accounts[aid]['platform'] for aid in v_accounts if aid in accounts}
        if len(v_accounts) == 0:
            zero_account_personas.append({
                'persona_id': pid,
                'name': p['name'],
                'format': p['format'],
                'thai_relation': p['thai_relation'],
                'reviewed_at': p['reviewed_at']
            })
        elif len(p_platforms) == 1:
            single_platform_personas.append({
                'persona_id': pid,
                'name': p['name'],
                'platform': next(iter(p_platforms)),
                'reviewed_at': p['reviewed_at']
            })

        # Check evidence age
        ev = evidence.get(p.get('evidence_id'))
        if ev and ev.get('observed_at'):
            obs_date = _parse_date(ev['observed_at'])
            if obs_date and (cutoff - obs_date).days > 180:
                stale_evidence_personas.append({
                    'persona_id': pid,
                    'name': p['name'],
                    'evidence_observed_at': ev['observed_at'],
                    'days_since_observation': (cutoff - obs_date).days
                })

    # 2. Candidates
    unresolved_candidates = [c for c in candidates if c['review_status'] == 'needs_evidence' or not c['account_id']]
    unresolved_by_platform = dict(Counter(c['platform'] for c in unresolved_candidates))

    # Check for missing stable IDs in candidates
    missing_stable_id = []
    for c in unresolved_candidates:
        pid = c.get('platform_id')
        plat = c.get('platform')
        is_missing = False
        if plat == 'youtube' and (not pid or not pid.startswith('UC')):
            is_missing = True
        elif plat == 'twitch' and (not pid or not str(pid).isdigit()):
            is_missing = True
        elif plat == 'tiktok' and (not pid or not str(pid).isdigit()):
            is_missing = True
        if is_missing:
            missing_stable_id.append({
                'candidate_id': c['id'],
                'platform': plat,
                'name': c['name'],
                'url': c['url']
            })

    # Duplicate candidate URLs
    candidate_urls = defaultdict(list)
    for c in candidates:
        candidate_urls[c['url']].append(c['id'])
    duplicate_candidate_urls = [{'url': u, 'candidate_ids': ids} for u, ids in candidate_urls.items() if len(ids) > 1]

    # 3. Lifecycle
    needs_ev_lifecycle = []
    secondary_source_lifecycle = []
    unverified_graduations = []

    for ev_item in lifecycle:
        pid = ev_item['persona_id']
        ev = evidence.get(ev_item['evidence_id'], {})
        if ev_item['review_status'] == 'needs_evidence':
            needs_ev_lifecycle.append({
                'event_id': ev_item['id'],
                'persona_id': pid,
                'persona_name': personas.get(pid, {}).get('name', 'Unknown'),
                'event_type': ev_item['event_type'],
                'event_date': ev_item['event_date'],
                'evidence_kind': ev.get('kind', 'unknown'),
                'note': ev_item.get('note', '')
            })
        if ev.get('kind') == 'secondary_source':
            secondary_source_lifecycle.append({
                'event_id': ev_item['id'],
                'persona_id': pid,
                'persona_name': personas.get(pid, {}).get('name', 'Unknown'),
                'event_type': ev_item['event_type'],
                'event_date': ev_item['event_date'],
                'evidence_url': ev.get('url', ''),
                'review_status': ev_item['review_status']
            })
        if ev_item['event_type'] == 'graduation' and ev_item['review_status'] != 'verified' and pid in verified_personas:
            unverified_graduations.append({
                'persona_id': pid,
                'persona_name': verified_personas[pid]['name'],
                'event_id': ev_item['id'],
                'event_date': ev_item['event_date'],
                'review_status': ev_item['review_status'],
                'note': ev_item.get('note', '')
            })

    # 4. Evidence Freshness Buckets
    freshness_buckets = {
        '0_30_days': 0,
        '31_90_days': 0,
        '91_180_days': 0,
        '181_365_days': 0,
        'over_365_days': 0,
        'unknown': 0
    }
    buckets_by_kind = defaultdict(lambda: {k: 0 for k in freshness_buckets})

    for ev_record in evidence.values():
        kind = ev_record.get('kind', 'unknown')
        obs_date = _parse_date(ev_record.get('observed_at'))
        if not obs_date:
            freshness_buckets['unknown'] += 1
            buckets_by_kind[kind]['unknown'] += 1
            continue
        age_days = (cutoff - obs_date).days
        if age_days < 0:
            bucket = '0_30_days'
        elif age_days <= 30:
            bucket = '0_30_days'
        elif age_days <= 90:
            bucket = '31_90_days'
        elif age_days <= 180:
            bucket = '91_180_days'
        elif age_days <= 365:
            bucket = '181_365_days'
        else:
            bucket = 'over_365_days'
        freshness_buckets[bucket] += 1
        buckets_by_kind[kind][bucket] += 1

    distinct_verified_accounts = {aid for aids in persona_verified_accounts.values() for aid in aids}

    return {
        'metadata': {
            'as_of': as_of,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'semantics': (
                'Data quality and evidence freshness monitoring. Measures registry observability and '
                'unresolved review backlog, not creator activity or absence. Old evidence indicates '
                'the registry has not recently re-observed a claim; it does not prove the claim is no longer true.'
            )
        },
        'summary_counts': {
            'total_personas': len(personas),
            'verified_personas': len(verified_personas),
            'needs_evidence_personas': len(needs_ev_personas),
            'verified_personas_with_no_verified_accounts': len(zero_account_personas),
            'verified_personas_with_single_platform': len(single_platform_personas),
            'total_accounts': len(accounts),
            'distinct_verified_accounts': len(distinct_verified_accounts),
            'verified_account_links': sum(1 for l in account_links if l['review_status'] == 'verified'),
            'needs_evidence_account_links': len(needs_ev_links),
            'rejected_account_links': sum(1 for l in account_links if l['review_status'] == 'rejected'),
            'unlinked_accounts': len(unlinked_accounts),
            'shared_accounts_count': len(shared_accounts),
            'total_candidates': len(candidates),
            'unresolved_candidates': len(unresolved_candidates),
            'needs_evidence_lifecycle_events': len(needs_ev_lifecycle),
            'secondary_source_lifecycle_events': len(secondary_source_lifecycle),
            'unverified_graduation_claims': len(unverified_graduations)
        },
        'personas': {
            'no_verified_accounts': zero_account_personas,
            'single_platform_count': len(single_platform_personas),
            'needs_evidence_count': len(needs_ev_personas),
            'stale_evidence_count': len(stale_evidence_personas)
        },
        'account_ownership': {
            'ownership_review_status': {
                'verified': sum(1 for l in account_links if l['review_status'] == 'verified'),
                'needs_evidence': len(needs_ev_links),
                'rejected': sum(1 for l in account_links if l['review_status'] == 'rejected'),
            },
            'needs_evidence_links_count': len(needs_ev_links),
            'needs_evidence_links_sample': needs_ev_links[:50],
            'rejected_links_count': sum(1 for l in account_links if l['review_status'] == 'rejected'),
            'shared_accounts': shared_accounts,
            'unlinked_accounts_by_platform': unlinked_by_platform
        },
        'candidates': {
            'unresolved_by_platform': unresolved_by_platform,
            'missing_stable_id_count': len(missing_stable_id),
            'missing_stable_id_items': missing_stable_id,
            'duplicate_urls': duplicate_candidate_urls
        },
        'lifecycle': {
            'needs_evidence_events_count': len(needs_ev_lifecycle),
            'secondary_source_events_count': len(secondary_source_lifecycle),
            'unverified_graduations': unverified_graduations
        },
        'evidence_freshness': {
            'buckets': freshness_buckets,
            'buckets_by_kind': dict(buckets_by_kind)
        }
    }


def write_data_quality_report(db, output_dir, as_of='2026-09-17'):
    """Generate and write data-quality.json and data-quality.csv."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report = generate_data_quality_report(db, as_of=as_of)

    json_file = output_path / 'data-quality.json'
    json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    csv_file = output_path / 'data-quality.csv'
    csv_rows = []
    for cat, val in report['summary_counts'].items():
        csv_rows.append({'category': 'summary', 'metric': cat, 'value': val})
    for bucket, count in report['evidence_freshness']['buckets'].items():
        csv_rows.append({'category': 'evidence_freshness', 'metric': bucket, 'value': count})
    for plat, count in report['candidates']['unresolved_by_platform'].items():
        csv_rows.append({'category': 'unresolved_candidates', 'metric': plat, 'value': count})

    with csv_file.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['category', 'metric', 'value'])
        writer.writeheader()
        writer.writerows(csv_rows)

    return report
