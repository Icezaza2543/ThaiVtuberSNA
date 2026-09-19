import copy,json,hashlib,sys,subprocess,re
from pathlib import Path
from collections import Counter
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
sys.path.insert(0,str(Path.cwd()))
from scripts.package_creator_review_evidence import package_review_evidence,validate_production_counts
from scripts.resolve_creator_identities import main
root=Path.cwd();e=root/'docs/evidence/creator-registry-review-2026-09-19';out=root/'outputs/task7_determinism';out.mkdir(exist_ok=True)
repack=package_review_evidence(root/'outputs/new-account-review-2026-09-19/all_884_screening_results.json',root/'outputs/new-account-review-2026-09-19/human_review_decisions.json',e/'eligibility_corrections.json',[e/'trusted_link_corrections.json'])
validate_production_counts(repack)
actual=json.loads((e/'review_bundle.json').read_text(encoding='utf-8'));assert repack==actual
inputs=[('review-bundle',e/'review_bundle.json'),('baseline',e/'trusted_baseline_1370.json'),('trusted-registry',Path('C:/Users/Icezaza/Documents/GitHub/ThaiVirtualCreatorRegistry/data/registry.json')),('trusted-link-corrections',e/'trusted_link_corrections.json'),('legacy-decisions',e/'legacy_visual_identity_review.json'),('researched',e/'identity_research_x.json'),('researched',e/'identity_research_linked.json')]
args=[]
for flag,path in inputs:
 data=json.loads(path.read_text(encoding='utf-8-sig'))
 if isinstance(data,list):data.reverse()
 elif 'tables' in data:
  for rows in data['tables'].values():
   if isinstance(rows,list):rows.reverse()
 else:
  for field in ('rows','corrections','decisions','required_trusted_link_corrections'):
   if isinstance(data.get(field),list):data[field].reverse()
 target=out/path.name;target.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');args+=['--'+flag,str(target)]
platform_args=[]
for platform in ('youtube','tiktok','website','instagram','facebook','ganknow','x'):platform_args+=['--platform',platform]
original=root/'data/registry/identity_resolutions.json';target=out/'ledger.json'
assert main(args+platform_args+['--output',str(target)])==0
assert target.read_bytes()==original.read_bytes()
assert main(args+['--trusted-link-corrections',str(out/'trusted_link_corrections.json'),'--platform','x','--merge-existing',str(original),'--output',str(target)])==0
assert target.read_bytes()==original.read_bytes()
assert main(args+platform_args+['--validate-only'])==0
# Production inputs themselves must block missing/partial corrections before output, selection or replay.
without=[arg for i,arg in enumerate(args) if arg!='--trusted-link-corrections' and (i==0 or args[i-1]!='--trusted-link-corrections')]
corrections=json.loads((e/'trusted_link_corrections.json').read_text(encoding='utf-8'))
partial=out/'partial-corrections.json';partial.write_text(json.dumps(dict(corrections,corrections=[r for r in corrections['corrections'] if r['link_id']!='link_7562c58a16d51c0abbeb'])),encoding='utf-8')
checks=0
for kind,extra in [('omitted',[]),('without_drako',['--trusted-link-corrections',str(partial)])]:
 for mode,modeargs in [('fresh',platform_args),('filtered_validate',['--platform','x','--validate-only']),('full_validate',['--validate-only']),('merge',['--platform','x','--merge-existing',str(original)])]:
  sink=out/(kind+'-'+mode+'.json');before=sink.read_bytes() if sink.exists() else None
  stdout,stderr=StringIO(),StringIO()
  with redirect_stdout(stdout),redirect_stderr(stderr):status=main(without+extra+modeargs+['--output',str(sink)])
  assert status==1 and stdout.getvalue()=='' and 'link_7562c58a16d51c0abbeb' in stderr.getvalue()
  assert (sink.read_bytes() if sink.exists() else None)==before
  checks+=1
r=json.loads((e/'identity_research_x.json').read_text(encoding='utf-8'));l=json.loads(original.read_text(encoding='utf-8'))
old=json.loads(subprocess.check_output(['git','show','HEAD:data/registry/identity_resolutions.json']))
oldrows={x['discovery_id']:x for x in old['resolutions']};newrows={x['discovery_id']:x for x in l['resolutions']}
identity_fields=['persona_id','outcome','canonical_name','platform','account_url','platform_id','canonical_url','method']
assert all(all(oldrow.get(k)==newrows[did].get(k) for k in identity_fields) for did,oldrow in oldrows.items())
old_linked=json.loads(subprocess.check_output(['git','show','HEAD:docs/evidence/creator-registry-review-2026-09-19/identity_research_linked.json']))
new_linked=json.loads((e/'identity_research_linked.json').read_text(encoding='utf-8'));assert old_linked['rows']==new_linked['rows']
assert len(r['rows'])==126 and len({x['discovery_id'] for x in r['rows']})==126
xs=[x for x in l['resolutions'] if x['platform']=='x'];assert len(xs)==126 and actual['eligibility_counts']['vtuber']==392
assert {x['discovery_id'] for x in r['rows'] if x.get('no_existing_persona_match')}=={x['discovery_id'] for x in xs if x['outcome']=='new_persona'}
for entry in r['rows']:
 for url in entry['official_account_urls']:
  assert not url.endswith('/watch') and not url.endswith('/profile.php'),(entry['discovery_id'],url)
# Public artifact scan: fail on obvious credentials, local paths or file URLs without printing matched contents.
for path in [e/'identity_research_x.json',e/'identity_research_linked.json',e/'trusted_link_corrections.json',original]:
 raw=path.read_text(encoding='utf-8')
 assert not re.search(r'AIza[0-9A-Za-z_-]{30,}|Bearer\s+[A-Za-z0-9_.-]{20,}|file://|[A-Z]:\\\\',raw),path.name
profiles=json.loads((root/'outputs/task7_public_profiles.json').read_text(encoding='utf-8'));videos=json.loads((root/'outputs/task7_video_evidence.json').read_text(encoding='utf-8'))
summary={'review_bundle_reproduced':True,'reversed_inputs_byte_identical':True,'repeated_corrections_merge_byte_identical':True,'blocked_production_omission_partial_modes':checks,'earlier_116_identity_fields_unchanged':True,'earlier_116_research_rows_unchanged':True,'ledger_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'counts':l['counts'],'global_accepted':actual['eligibility_counts']['vtuber'],'x_by_outcome':dict(Counter(x['outcome'] for x in xs)),'x_by_method':dict(Counter(x['method'] for x in xs)),'unique_personas':len({x['persona_id'] for x in l['resolutions']}),'unique_new_personas':len({x['persona_id'] for x in l['resolutions'] if x['outcome']=='new_persona'}),'x_unique_personas':len({x['persona_id'] for x in xs}),'x_unique_new_personas':len({x['persona_id'] for x in xs if x['outcome']=='new_persona'}),'new_persona_searches':sum(bool(x.get('no_existing_persona_match')) for x in r['rows']),'evidence_records':sum(len(x['evidence']) for x in r['rows']),'evidence_kinds':dict(Counter(ev['source_kind'] for x in r['rows'] for ev in x['evidence'])),'collection_methods':dict(Counter(ev.get('collection_method') for x in r['rows'] for ev in x['evidence'])),'unique_source_urls':len({ev['source_url'] for x in r['rows'] for ev in x['evidence']}),'youtube_api_requests_quota':0,'fresh_public_profiles':len(profiles),'fresh_public_profile_statuses':dict(Counter(str(x.get('status')) for x in profiles)),'public_video_descriptions_checked':len(videos),'correction_count':len(l['trusted_link_corrections_applied'])}
(root/'outputs/task7_verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
