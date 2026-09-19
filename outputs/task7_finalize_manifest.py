import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.creator_identity_corrections import trusted_link_correction_manifest
from scripts.package_creator_review_evidence import package_review_evidence, validate_production_counts
p=Path('docs/evidence/creator-registry-review-2026-09-19')
corrections=json.loads((p/'trusted_link_corrections.json').read_text(encoding='utf-8'))
profiles=json.loads(Path('outputs/task7_public_profiles.json').read_text(encoding='utf-8'))
for c in corrections['corrections']:
    if c['link_id']=='link_7562c58a16d51c0abbeb':
        c['observed_at']=max(x['observed_at'] for x in profiles if x['source_url'] in c['source_urls'])
(p/'trusted_link_corrections.json').write_text(json.dumps(corrections,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest=trusted_link_correction_manifest([corrections])
linked=json.loads((p/'identity_research_linked.json').read_text(encoding='utf-8'))
linked['required_trusted_link_corrections']=manifest
(p/'identity_research_linked.json').write_text(json.dumps(linked,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
review=package_review_evidence(Path('outputs/new-account-review-2026-09-19/all_884_screening_results.json'),Path('outputs/new-account-review-2026-09-19/human_review_decisions.json'),p/'eligibility_corrections.json',[p/'trusted_link_corrections.json'])
validate_production_counts(review)
(p/'review_bundle.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
generator=Path('outputs/task7_build_research.py')
s=generator.read_text(encoding='utf-8')
s=s.replace("  existing.update(extra)\n", "  dates=sorted(set(existing.get('observation_dates',[])+[existing['observed_at'],observed]))\n  if len(dates)>1:existing['observation_dates']=dates\n  existing['observed_at']=max(dates)\n  existing.update(extra)\n")
generator.write_text(s,encoding='utf-8')
print('Pinned',len(manifest),'corrections; accepted',review['eligibility_counts']['vtuber'])
