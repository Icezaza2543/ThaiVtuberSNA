import copy,json,hashlib,sys
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path.cwd()))
from scripts.package_creator_review_evidence import package_review_evidence,validate_production_counts
from scripts.resolve_creator_identities import main
root=Path.cwd();e=root/'docs/evidence/creator-registry-review-2026-09-19';out=root/'outputs/task6_determinism';out.mkdir(exist_ok=True)
repack=package_review_evidence(root/'outputs/new-account-review-2026-09-19/all_884_screening_results.json',root/'outputs/new-account-review-2026-09-19/human_review_decisions.json',e/'eligibility_corrections.json', [e/'trusted_link_corrections.json'])
validate_production_counts(repack)
actual=json.loads((e/'review_bundle.json').read_text());assert repack==actual
# Reversing all relevant input row arrays and repeating the same correction cannot change bytes.
inputs={'review-bundle':e/'review_bundle.json','baseline':e/'trusted_baseline_1370.json','trusted-registry':Path('C:/Users/Icezaza/Documents/GitHub/ThaiVirtualCreatorRegistry/data/registry.json'),'trusted-link-corrections':e/'trusted_link_corrections.json','legacy-decisions':e/'legacy_visual_identity_review.json','researched':e/'identity_research_linked.json'}
args=[]
for flag,path in inputs.items():
 data=json.loads(path.read_text(encoding='utf-8-sig'))
 if isinstance(data,list):data.reverse()
 elif 'tables' in data:
  for rows in data['tables'].values():
   if isinstance(rows,list):rows.reverse()
 else:
  for field in ('rows','corrections','decisions','required_trusted_link_corrections'):
   if isinstance(data.get(field),list):data[field].reverse()
 target=out/(flag+'.json');target.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');args+=['--'+flag,str(target)]
for platform in ('youtube','tiktok','website','instagram','facebook','ganknow'):args+=['--platform',platform]
original=root/'data/registry/identity_resolutions.json';target=out/'ledger.json'
assert main(args+['--output',str(target)])==0
assert target.read_bytes()==original.read_bytes()
assert main(args+['--trusted-link-corrections',str(out/'trusted-link-corrections.json'),'--merge-existing',str(original),'--output',str(target)])==0
assert target.read_bytes()==original.read_bytes()
assert main(args+['--validate-only'])==0
r=json.loads((e/'identity_research_linked.json').read_text());l=json.loads(original.read_text())
api=json.loads((root/'outputs/task6_youtube_lookups.json').read_text())
profiles=json.loads((root/'outputs/task6_fresh_profiles.json').read_text());videos=json.loads((root/'outputs/task6_historical_video_evidence.json').read_text())
summary={'review_bundle_reproduced':True,'reversed_inputs_byte_identical':True,'repeated_corrections_merge_byte_identical':True,'ledger_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'counts':l['counts'],'unique_personas':len({x['persona_id'] for x in l['resolutions']}),'unique_new_personas':len({x['persona_id'] for x in l['resolutions'] if x['outcome']=='new_persona'}),'new_persona_searches':sum(bool(x.get('no_existing_persona_match')) for x in r['rows']),'evidence_records':sum(len(x['evidence']) for x in r['rows']),'evidence_kinds':dict(Counter(ev['source_kind'] for x in r['rows'] for ev in x['evidence'])),'collection_methods':dict(Counter(ev.get('collection_method') for x in r['rows'] for ev in x['evidence'])),'unique_source_urls':len({ev['source_url'] for x in r['rows'] for ev in x['evidence']}),'youtube_api_requests_quota':api['requests'],'successful_lookup_url_forms':sum('evidence' in x for x in api['lookups']),'no_match_api_results':sum(x.get('requests',0)>0 and 'error' in x for x in api['lookups']),'dependency_failures_with_no_requests':sum(x.get('requests',0)==0 and 'error' in x for x in api['lookups']),'fresh_public_profiles':len(profiles),'fresh_public_profile_statuses':dict(Counter(str(x.get('status')) for x in profiles)),'public_video_descriptions_checked':sum(bool(x.get('channel_id')) for x in videos),'correction_count':len(l['trusted_link_corrections_applied'])}
(root/'outputs/task6_verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
