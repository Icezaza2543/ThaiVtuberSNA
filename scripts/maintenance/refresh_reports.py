"""Refresh current inventory and platform reports without collecting or modifying data."""
import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from registry.store import load, rows
from registry.reports import write_report
from registry.discovery.coverage import get_platform_coverage
from registry.quality import write_data_quality_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', required=True, type=date.fromisoformat)
    args = parser.parse_args()
    source = ROOT / 'data/registry.json'
    output = ROOT / 'reports/current'
    db = load(source)
    try:
        summary = write_report(db, output, args.as_of.isoformat())
        quality_summary = write_data_quality_report(db, output, args.as_of.isoformat())
        people = {p['id']: p for p in rows(db, 'personas') if p['review_status'] == 'verified'}
        accounts = {a['id']: a for a in rows(db, 'accounts')}
        links = [l for l in rows(db, 'account_links') if l['review_status'] == 'verified' and l['persona_id'] in people]
        platforms = defaultdict(set)
        for link in links: platforms[link['persona_id']].add(accounts[link['account_id']]['platform'])
        matrix = sorted(({'persona_id': pid, 'name': p['name'], 'platforms': sorted(platforms[pid]), 'platform_count': len(platforms[pid])} for pid, p in people.items()), key=lambda r: (-r['platform_count'], r['name'], r['persona_id']))
        stamp = datetime.now(timezone.utc).isoformat()
        combinations = Counter(' + '.join(r['platforms']) if r['platforms'] else 'no_verified_account' for r in matrix)
        counts = Counter(r['platform_count'] for r in matrix)
        linked_accounts = {l['account_id'] for l in links}
        sna = {'created_at': stamp, 'verified_personas': len(people), 'verified_accounts': len(linked_accounts),
               'verified_links': len(links), 'platform_account_counts': dict(Counter(accounts[a]['platform'] for a in linked_accounts)),
               'personas_with_1_platform': counts[1], 'personas_with_2_platforms': counts[2],
               'personas_with_3plus_platforms': sum(n for k, n in counts.items() if k >= 3),
               'multi_platform_personas': sum(n for k, n in counts.items() if k >= 2),
               'platform_combinations': dict(combinations.most_common()),
               'tri_platform_yt_tw_tt': sum({'youtube', 'twitch', 'tiktok'} <= platforms[p] for p in people)}
        for plat in ('youtube', 'twitch', 'tiktok', 'x', 'facebook', 'instagram'):
            sna['missing_' + plat] = sum(plat not in platforms[p] for p in people)
        metadata = {'created_at': stamp, 'source_registry_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'count_semantics': 'Current reviewed platform presence, not dated activity. A missing platform is unknown, not absent. Coverage fields retain the registry coverage command semantics.'}
        for name, data in [('platform-coverage.json', dict(metadata, coverage=get_platform_coverage(db), sna=sna)),
                           ('creator-platform-matrix.json', dict(metadata, personas=matrix))]:
            (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'accounts': summary['inventory']['accounts'], 'verified_personas': len(people),
                          'verified_links': len(links), 'output': str(output.relative_to(ROOT))}))
    finally:
        db.close()


if __name__ == '__main__':
    main()
