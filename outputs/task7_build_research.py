import json,re,sys
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlsplit,urlunsplit
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,'outputs')
from task6_helpers import read,review,baseline,corrected_trusted,names,ids,urls,persona_urls,norm,normmatch,cidmatch,unique_claim
from scripts.resolve_creator_identities import _account_url
from urllib.parse import parse_qs
def norm(u):
 p=urlsplit(_account_url(u)); q=parse_qs(p.query)
 query=('id='+q['id'][0]) if p.path=='/profile.php' and q.get('id') else ('v='+q['v'][0]) if p.path=='/watch' and q.get('v') else ''
 return urlunsplit((p.scheme,p.netloc,p.path,query,''))
def normmatch(url):
 key=norm(url)
 return [c for u,claims in urls.items() if norm(u)==key for c in claims]
P=Path('docs/evidence/creator-registry-review-2026-09-19')
xs={r['discovery_id']:r for r in review['rows'] if r['eligibility']=='vtuber' and r['platform']=='x'}
profiles={r['source_url']:r for r in read('outputs/task7_public_profiles.json')}
profilelinks=read('outputs/task7_profile_links.json')
linked=read(P/'identity_research_linked.json')
linked_byurl=defaultdict(list)
for r in linked['rows']:
 for u in r['official_account_urls']:linked_byurl[norm(u)].append(r)
ytdocs={norm(r['source_url'].removesuffix('/about')):r for r in profiles.values() if r.get('youtube')}
excluded_accounts={norm(r['url']):r for r in review['rows'] if r['eligibility'] not in ('vtuber','trusted_baseline')}
entries={}; paths={};reviewer='codex:task-7-x-identity-research'
def clean(u):
 p=urlsplit(u);return urlunsplit((p.scheme,p.netloc,p.path.rstrip('/') or '/',p.query if p.path=='/profile.php' else '',''))
def add(e,url,summary,kind='official_profile',observed='2026-09-19',**extra):
 v={'source_url':url,'source_kind':kind,'summary':summary,'supports':['account_ownership','persona_identity'],'observed_at':observed,**extra}
 existing=next((v for v in e['evidence'] if v['source_url']==url),None)
 if existing:
  if summary not in existing['summary']:existing['summary']+=' '+summary
  dates=sorted(set(existing.get('observation_dates',[])+[existing['observed_at'],observed]))
  if len(dates)>1:existing['observation_dates']=dates
  existing['observed_at']=max(dates)
  existing.update(extra)
 else:e['evidence'].append(v)
 e['evidence_urls'].append(url);e['checked_urls'].append(url)
def owned_hub_links(d):
 out=[]
 for l in d.get('links',[]):
  if l['label']=='Privacy':break
  p=urlsplit(l['url']);host=p.netloc.removeprefix('www.').removeprefix('m.')
  if host not in ['youtube.com','twitch.tv','tiktok.com','instagram.com','facebook.com','x.com','twitter.com']:continue
  if 'linktr.ee/' in d['source_url']:
   out.append(l['url']);continue
  if any(n in l['label'].casefold() for n in ['youtube','twitch','tiktok','instagram','facebook']) or l['label'].startswith('X ') or l['label'].startswith('X Titorch'):
   out.append(l['url'])
 return out

overrides={'RousokiNouri':'Rousoki Nouri','MinkariMireen':'Minkari Mireen','4_kia4':'Fenrika Seiryu','NeoSnowhite':'NeoSnowWhite','aredhantanujo':'Aredhan Tanujo','lyrinwt_':'Lyrin','Cqueennani':'Cqueen Nani','demetriakubpom':'Demii','LiliJ_MMc':'LiliJ Mimicsaur','yunariazayu':'Yunaria Zayu','YURAburi':'YURAburi','marinringring':'Marin Morgan','Koya_VDS':'Yuzuki Koya','Titorch_ch':'Titorch'}
for did,row in xs.items():
 handle=urlsplit(row['url']).path.strip('/');p=profiles[row['url']]
 name=overrides.get(handle,row['display_name'].split('|')[0].split('〖')[0].strip())
 e={'discovery_id':did,'canonical_name':name,'checked_urls':[row['url']],'evidence_urls':[],'official_account_urls':[row['url']],'reviewer':reviewer,'evidence':[],'assertions':[]}
 entries[did]=e;paths[did]={norm(row['url']):[row['url']]}
 claims=normmatch(row['url'])
 for claim in claims:
  for ev in claim['evidence']:
   add(e,ev['source_url'],ev['summary'],ev['source_kind'],ev['observed_at'],collection_method='retained_verified_registry_evidence')
 if p.get('status')==200 and p.get('meta',{}).get('og:title'):
  title=p['meta']['og:title'].removesuffix(' on X')
  add(e,row['url'],f'The account-owned X profile identifies {name}; its visible title is {title!r}. Its own displayed identity text is retained below; names and agency labels alone are not used to join identities.',observed=p['observed_at'],collection_method='direct_public_x_profile',profile_title=title,profile_description_excerpt=' '.join(p['meta'].get('description','').split()[:15])[:120])
 for link in profilelinks:
  if link['source_url']!=row['url'] or not link.get('expanded_url'):continue
  u=clean(link['expanded_url']);e['checked_urls']+=list({link['url'],link['expanded_url'],u})
  if norm(u) in excluded_accounts:
   rejected=excluded_accounts[norm(u)]
   e.setdefault('unavailable_or_excluded_leads',[]).append({'url':u,'discovery_id':rejected['discovery_id'],'eligibility':rejected['eligibility'],'action':'Checked only; not positive identity evidence and not added to official account URLs.'})
   continue
  if any(s in u for s in ['docs.google.com/','readawrite.com','scanned.page','seinaspace.softr']):continue
  e['official_account_urls'].append(u);paths[did][norm(u)]=[row['url']]
  add(e,row['url'],f'The owner-supplied profile link {link["label"]!r} points to {u}.',observed=p['observed_at'])
  doc=profiles.get(u) or next((d for a,d in profiles.items() if norm(a)==norm(u)),None)
  if doc and doc.get('status')==200 and ('carrd.co' in u or 'linktr.ee' in u):
   accounts=[clean(v) for v in owned_hub_links(doc)]
   add(e,u,f'The creator-controlled hub presents {name} and groups these own social accounts under its profile: '+', '.join(accounts)+'. Credits, management/agency links, donation services and Linktree recommendations were not treated as persona-equivalence evidence.','official_website',doc['observed_at'],collection_method='direct_public_creator_hub')
   for account in accounts:e['official_account_urls'].append(account);paths[did][norm(account)]=[row['url'],u]
 # Resolve owner-linked YouTube handle URLs to their own canonical channel metadata.
 for u in list(e['official_account_urls']):
  d=ytdocs.get(norm(u.removesuffix('/about')))
  if not d:continue
  y=d['youtube'];canon='https://www.youtube.com/channel/'+y['externalId']
  add(e,d['source_url'],f'Public channel metadata resolves the owner-linked URL {u} to Channel ID {y["externalId"]}, with channel title {y["title"]!r}. This is the creator channel reached from the accepted X profile or its own hub.',observed=d['observed_at'],owner_channel_id=y['externalId'],owner_canonical_url=canon,collection_method='direct_public_youtube_profile')
  e['official_account_urls'].append(canon);paths[did][norm(canon)]=paths[did][norm(u)]+[d['source_url']]

# Historical owner-written video descriptions establish two old handles, not name matching.
videos={v['source_url']:v for v in read('outputs/task7_video_evidence.json')}
for handle,video in [('tsukimorihecate','https://www.youtube.com/watch?v=mUz7i6d_lx8'),('meltilda_vtuber','https://www.youtube.com/watch?v=aDnHzsx3ycI')]:
 did=next(did for did,r in xs.items() if r['url'].endswith('/'+handle));e=entries[did];d=videos[video];v=d['video'];cid=v['channelId'];canon='https://www.youtube.com/channel/'+cid
 assert handle.lower() in v['shortDescription'].lower()
 add(e,video,f'The owning channel {v["author"]!r} publishes {v["title"]!r}; its owner-written follow/Official section explicitly lists {xs[did]["url"]} as the creator\'s Twitter account. Public video metadata identifies the owner as Channel ID {cid}. This historical official link establishes the old handle even though its current profile URL returns 404.',observed=d['observed_at'],owner_channel_id=cid,collection_method='direct_public_video_description')
 e['official_account_urls'].append(canon);paths[did][norm(canon)]=[video]
 about=profiles[canon+'/about'];y=about['youtube'];add(e,about['source_url'],f'The current owner-written channel profile identifies {y["title"]!r} at the same stable Channel ID {cid}.',observed=about['observed_at'],owner_channel_id=cid,collection_method='direct_public_youtube_profile')
 e['identity_notes']='The accepted old handle is retained as reviewed. Its owner is established by the explicit historical official video link; no rename is inferred from display-name similarity.'

# Owner-written follow links, verified after names were used only to locate possible channels.
for handle,video in [('PheonyxThea_TSP','https://www.youtube.com/watch?v=nuiMINF5G5Y'),('Kimewa_yuki','https://www.youtube.com/watch?v=d98QHhWn-Vc')]:
 did=next(d for d,r in xs.items() if r['url'].endswith('/'+handle));e=entries[did];d=videos[video];v=d['video'];cid=v['channelId'];canon='https://www.youtube.com/channel/'+cid
 assert handle.lower() in v['shortDescription'].lower()
 add(e,video,f'The owner-written follow-links section of {v["title"]!r} explicitly labels @{handle} as this creator\'s X account. Public video metadata binds the author to Channel ID {cid}. The name was a search lead only; this explicit owner link establishes identity.',observed=d['observed_at'],owner_channel_id=cid,collection_method='direct_public_video_description')
 e['official_account_urls'].append(canon);paths[did][norm(canon)]=[video]
for handle,cid in [('seina_idyp','UCWw9JzEA7hdBnSFR-_Y0DlA'),('Titorch_ch','UCtHdI-Bb1OWP9VaQpBHy7kg')]:
 did=next(d for d,r in xs.items() if r['url'].endswith('/'+handle));e=entries[did];canon='https://www.youtube.com/channel/'+cid;d=profiles[canon+'/about'];y=d['youtube']
 if handle=='seina_idyp':
  assert handle.lower() in y['description'].lower()
  summary=f'The channel owner introduces Seina from IDYLLIC Project and explicitly lists https://twitter.com/Seina_IDYP under its own SNS links. Public metadata identifies Channel ID {cid}.'
  sources=[d['source_url']]
 else:
  assert any(l['url']=='https://titorch.carrd.co/' for l in d['links'])
  summary=f'The original baseline channel, Channel ID {cid}, identifies Titorch and links https://titorch.carrd.co/ as its own creator site. The accepted X profile independently links that same personal site, whose self-introduction identifies Titorch as a one-horned dragon. This is a creator-specific ownership chain, not shared agency membership.'
  sources=[xs[did]['url'],'https://titorch.carrd.co/',d['source_url']]
 add(e,d['source_url'],summary,observed=d['observed_at'],owner_channel_id=cid,collection_method='direct_public_youtube_profile')
 e['official_account_urls'].append(canon);paths[did][norm(canon)]=sources
# AI-ZON's own post supplies the current channel after its profile website's older handle stopped resolving.
did=next(d for d,r in xs.items() if r['url'].endswith('/AI_ZONN'));e=entries[did];d=profiles['https://www.youtube.com/@this-is-aizon/about'];y=d['youtube'];canon='https://www.youtube.com/channel/'+y['externalId']
p=profiles[xs[did]['url']];post=next(a for a in p['posts'] if any(l['url']=='https://youtube.com/@this-is-aizon' for l in a['links']))
add(e,xs[did]['url'],'The creator\'s own pinned follow-links post explicitly lists YouTube https://youtube.com/@this-is-aizon and Twitch twitch.tv/ai__zon as its own channels.',observed=p['observed_at'])
add(e,d['source_url'],f'Public metadata resolves the explicitly linked current AI-ZON YouTube handle to Channel ID {y["externalId"]}.',observed=d['observed_at'],owner_channel_id=y['externalId'],collection_method='direct_public_youtube_profile')
e['official_account_urls'] += [canon,'https://youtube.com/@this-is-aizon','https://www.twitch.tv/ai__zon'];paths[did][norm(canon)]=[xs[did]['url'],d['source_url']]

# The only unavailable account without a live official path uses the controller-approved retained self-statement.
did=next(did for did,r in xs.items() if r['url']=='https://x.com/KurosekiNia');e=entries[did]
post='https://x.com/KurosekiNia/status/2030301430108848205'
e['checked_urls'] += [post,'https://x.com/KurosekiNia/with_replies','https://mobile.twstalker.com/lovely_2776','https://mobile.twstalker.com/KurosekiNia/status/2030301430108848205']
add(e,post,'Retained public capture attributes a self-introduction/model-reveal post to Kuronia, exactly @KurosekiNia. The owner greets the audience and uses its own KuroNia and VTuberTH tags. The original profile and recovered post permalink now return 404. This is a cached attributed self-statement, not a live official-page confirmation.','self_statement','2026-09-19',collection_method='retained_attributed_x_post_via_mirror',attributed_owner_name='Kuronia',attributed_owner_handle='@KurosekiNia',attributed_account_url=xs[did]['url'],retained_statement='ก๊อก ก๊อก สวัสดีชาวโลก ฝากเอาผมออกไปที #VtuberTH #Vtuber #วีทูปเบอร์ไทย #KuroNia',capture_source_url='https://mobile.twstalker.com/lovely_2776',capture_date='2026-09-19',capture_provenance='Retained eligibility-research capture x_web_followups.json; web-indexed mirror page re-opened during Task 7 and its View Details link recovered the original status ID. The page attributes the post to Kuronia @KurosekiNia; lovely_2776 is the reposter, not the persona being resolved.',live_official_confirmation=False)
e['identity_notes']='Controller ruling: retained attributed self-statement may resolve this accepted account only as a separate new persona, with exact handle, quotation and cached-source provenance; no merge to an existing persona is authorized by name/handle similarity.'

# Bind exact known target URLs only after owner-controlled paths were inspected.
for did,e in entries.items():
 if e['canonical_name']=='Kuronia':continue
 for target_url,sources in paths[did].items():
  if target_url==norm(xs[did]['url']):continue
  claims=normmatch(target_url)
  for pid in sorted({c['persona_id'] for c in claims}):
   a={'method':'official_crosslink','persona_id':pid,'source_urls':list(dict.fromkeys(sources))}
   if a not in e['assertions']:e['assertions'].append(a)
  for target in linked_byurl.get(target_url,[]):
   # A target must be the accepted account itself, not a shared website mention.
   targetrow=next(r for r in review['rows'] if r['discovery_id']==target['discovery_id'])
   if norm(targetrow['url'])!=target_url and not (targetrow['platform']=='youtube' and norm(target.get('canonical_url','https://example.invalid/'))==target_url):continue
   e['official_account_urls'].append(targetrow['url'])
   a={'method':'official_crosslink','target_discovery_id':target['discovery_id'],'source_urls':list(dict.fromkeys(sources))}
   if a not in e['assertions']:e['assertions'].append(a)
 # Retain already-reviewed incoming links from the previous research batch.
 for prior in linked_byurl.get(norm(xs[did]['url']),[]):
  targetrow=next(r for r in review['rows'] if r['discovery_id']==prior['discovery_id'])
  for ev in prior['evidence']:
   add(e,ev['source_url'],ev['summary'],ev['source_kind'],ev['observed_at'],collection_method='retained_task6_official_identity_evidence')
  e['official_account_urls'].append(targetrow['url'])
  a={'method':'official_crosslink','target_discovery_id':prior['discovery_id'],'source_urls':prior['evidence_urls']}
  if a not in e['assertions']:e['assertions'].append(a)
for did,e in entries.items():
 hasdirect=bool(normmatch(xs[did]['url']))
 if not hasdirect and not any(a.get('persona_id') for a in e['assertions']):
  e['no_existing_persona_match']=True
  e['existing_persona_search']={'corpora':['trusted_baseline_1370.json: original canonical persona IDs and stable YouTube Channel IDs','ThaiVirtualCreatorRegistry: verified owner links after all required trusted-link corrections','identity_research_linked.json: previously researched accepted account URLs','review_bundle.json: accepted discovery account URLs'], 'method':'Exact normalized owner-controlled account URL and stable YouTube Channel ID comparison. Names and agency membership were used only as research leads and never as merge evidence.','official_urls_checked':sorted(set(e['checked_urls'])),'result':'No verified existing-persona attachment found through the inspected official identity paths. Retained as a separate new persona or joined only to another accepted new account through the recorded official crosslinks.'}
 for key in ['checked_urls','evidence_urls','official_account_urls']:e[key]=sorted(set(e[key]))
 e['assertions']=sorted(e['assertions'],key=lambda a:json.dumps(a,sort_keys=True))
 e['evidence'].sort(key=lambda a:a['source_url'])
 if not e['assertions']:e.pop('assertions')
artifact={'schema_version':1,'reviewed_at':'2026-09-19','platform':'x','scope':'Exactly 126 accepted X accounts in the corrected 392-account review bundle.','required_trusted_link_corrections':linked['required_trusted_link_corrections'],'rows':[entries[k] for k in sorted(entries)]}
(P/'identity_research_x.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
Path('outputs/task7_identity_paths.json').write_text(json.dumps(paths,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Wrote',len(entries),'research rows')
for did,e in entries.items():
 print(xs[did]['url'], 'EXACT' if normmatch(xs[did]['url']) else '',[(a.get('persona_id') or a.get('target_discovery_id')) for a in e.get('assertions',[])], 'EVIDENCE',len(e['evidence']))
