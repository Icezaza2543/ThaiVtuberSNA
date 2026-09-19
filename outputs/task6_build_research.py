import json,re,sys,hashlib
from pathlib import Path
from collections import defaultdict
from task6_helpers import *
from scripts.resolve_creator_identities import _account_url
fresh={r['source_url']:r for r in read('outputs/task6_fresh_profiles.json')}
historical=read('outputs/task6_historical_video_evidence.json')
entries={};channels=defaultdict(set);reviewer='codex:task-6-linked-identity-research'
api_norm={norm(u.removesuffix('/about')):r for u,r in api.items()}

def findid(prefix):return next(d for d in selected if d.startswith('candidate_'+prefix))
def doc(did,fragment):return next(d for d in extracts[did]['docs'] if fragment in d['source_url'])
def linkurls(d):
 result=[]
 for v in d.get('all_labeled_links',d.get('links',[])):
  u=v['url'] if isinstance(v,dict) else v
  if u.startswith(('http://','https://')):result.append(u)
 for field in (d.get('youtube',{}).get('description',''),d.get('meta',{}).get('og:description',''),d.get('profile',{}).get('description','')):
  result.extend(re.findall(r'https?://[^\s<>]+',field))
 return result

def start(did,name):
 e={'discovery_id':did,'canonical_name':name,'checked_urls':[selected[did]['url']], 'evidence_urls':[], 'official_account_urls':[selected[did]['url']], 'reviewer':reviewer,'evidence':[]}
 entries[did]=e;return e

def add(e,url,summary,kind='official_profile',observed='2026-09-19',**extra):
 evidence={'source_url':url,'source_kind':kind,'summary':summary,'supports':['account_ownership','persona_identity'],'observed_at':observed,**extra}
 prior=next((x for x in e['evidence'] if x['source_url']==url),None)
 if prior:
  if summary not in prior['summary']:prior['summary']+=' '+summary
  old_collection=prior.get('collection_method')
  prior.update(extra)
  if old_collection=='public_video_description' and kind=='youtube_api':prior['collection_method']='public_video_description_and_youtube_identity_client'
 else:e['evidence'].append(evidence)
 e['evidence_urls'].append(url);e['checked_urls'].append(url)

def apiadd(e,url,account=False):
 a=api.get(url) or api_norm.get(norm(url.removesuffix('/about')))
 if not a:return None
 p=a['evidence'];cid=p['channel_id'];channels[cid].add(e['discovery_id'])
 add(e,a['url'],f"Read-only YouTube Data API resolves {p['source_resource']} to the owning Channel ID {cid}; the owner-written channel title is {p['title']!r}.",'youtube_api',a['observed_at'],owner_channel_id=cid,owner_canonical_url=p['canonical_url'],source_resource=p['source_resource'],collection_method='youtube_identity_client_sanitized')
 e['official_account_urls'] += [p['canonical_url']]
 if account:e.update(platform_id=cid,canonical_url=p['canonical_url'])
 return cid

def attach(e,cid,sources,method='official_crosslink'):
 pid=unique_claim(cidmatch(cid));channels[cid].add(e['discovery_id'])
 canonical='https://www.youtube.com/channel/'+cid;e['official_account_urls'].append(canonical)
 if pid:e.setdefault('assertions',[]).append({'method':method,'persona_id':pid,'source_urls':sources})
 return pid

def incoming(e,d):
 yt=d.get('youtube',{});cid=yt.get('externalId')
 if not cid:
  a=api.get(d['source_url']) or api_norm.get(norm(d['source_url'].removesuffix('/about')))
  if a:cid=a['evidence']['channel_id']
 if not cid:return False
 add(e,d['source_url'],f"The owner-written {yt.get('title') or d.get('meta',{}).get('og:title')} channel profile identifies its creator and directly lists {selected[e['discovery_id']]['url']} among that creator's own social links. The public channel metadata identifies Channel ID {cid}.",observed=d.get('observed_at','2026-09-19'),owner_channel_id=cid,collection_method='public_profile' if 'observed_at' in d else 'retained_public_profile_capture')
 attach(e,cid,[d['source_url']]);return True

# Exact accepted YouTube accounts, including every watch/Short owner returned by the API.
for did,r in selected.items():
 if r['platform']!='youtube':continue
 lookup=r['url'] if '/c/' not in r['url'] else 'https://www.youtube.com/channel/'+r['channel_id']
 a=api.get(lookup) or api_norm.get(norm(lookup));assert a,(did,lookup)
 e=start(did,a['evidence']['title'].strip());cid=apiadd(e,a['url'],True)
 for v in watch:
  if v['discovery_id']==did and v.get('channelId')==cid:
   add(e,v['url'],f"The channel's own published video {v['title']!r} identifies the {e['canonical_name']} persona. Public video metadata gives author {v['author']!r} and owning Channel ID {cid}.",observed=v['retrieved_at'],owner_channel_id=cid,collection_method='retained_public_video_capture')
 if did in (findid('4ad08'),findid('b297')):
  e['identity_notes']='The discovery label names another creator. Identity follows the actual API-confirmed video owner; no merge uses that discovery label.'
  e['evidence'][0]['summary'] += (' The owner-written description welcomes viewers as little fish to the Derya world.' if did==findid('4ad08') else ' The owner-written description explicitly introduces CzarBooHan as a soul-eating slime persona.')
 if did==findid('f1e631'):
  e['identity_notes']='Izumi Karin is explicitly presented as an Axia roleplay persona. Contact links to the creator do not equate this character with Mitsuki Rinna or the unrelated baseline Karin Tsutsuji.'

# Existing verified registry links are independently retained as provenance.
for did,r in selected.items():
 if did in entries:continue
 claims=urls.get(_account_url(r['url']),[])
 if not claims:continue
 pid=unique_claim(claims)
 if not pid:continue
 e=start(did,names[pid])
 for claim in claims:
  for ev in claim['evidence']:
   if ev['source_kind'] in ('official_profile','official_website','self_statement','youtube_api'):
    add(e,ev['source_url'],ev['summary'],ev['source_kind'],ev['observed_at'],collection_method='verified_registry_evidence')
 if not e['evidence']:del entries[did]

# Direct incoming YouTube owner crosslinks captured during eligibility review.
for did,r in selected.items():
 if did in entries or r['platform'] not in ('tiktok','facebook'):continue
 for d in extracts[did]['docs']:
  if 'youtube.com/' not in d['source_url']:continue
  own=[]
  for u in linkurls(d):
   try:
    if norm(u)==norm(r['url']):own.append(u)
   except ValueError:pass
  if not own:continue
  e=start(did,d.get('youtube',{}).get('title') or d['meta']['og:title'])
  assert incoming(e,d),(did,d['source_url']);break

# Official websites with named social buttons, manually checked to exclude friends/model credits.
hubs={
 '1d513':('Kagemaru 404','kagemaru404.carrd.co','https://www.youtube.com/@Kagemaru404'),
 '1d861':('Mellovie','linktr.ee/mellovie',None),
 '224c':('Potia PBT','linktr.ee/potia_pbt1','https://www.youtube.com/@potiaht'),
 '3d726':('Fortuna Leah','linktr.ee/fortuna_leah',None),
 '5dc706':('Mainazzaya','linktr.ee/mainazzayach',None),
 '774e':('gingerbelle','gingerbelle.carrd.co','https://www.youtube.com/@ging3rbelle'),
 '9db4':('SHIRO K.','shirokumacafe.carrd.co','https://www.youtube.com/@SHIROKChannel'),
 'ad6fac':('SaiMaiZ','saimaiz.carrd.co','https://www.youtube.com/@SaiMaiZ'),
 'b8fc':('Atsuko Meron','linktr.ee/atsukomeron','https://www.youtube.com/@AtsukoMeron_SRV'),
 'bfe449':('Kamashi','kamashi.carrd.co',None),
 'ee5dd':('Puinoon','linktr.ee/PuinoonDesu','https://www.youtube.com/@PuinoonDesu'),
 'f6b284':('ALhong','alhong.carrd.co','https://www.youtube.com/@ALhongVTG'),
 'fa17':('Fuyu','linktr.ee/_fuyu1102','https://www.youtube.com/channel/UCqsI2kWRlvSe1jpeS3PoGwA'),
 'fdfb':('Zenaida XETA-102','zenaidaxeta102.carrd.co','https://www.youtube.com/channel/UCH6Fib1kQUaR2qurlEXnZMA')}
for pre,(name,fragment,yt) in hubs.items():
 did=findid(pre);r=selected[did];d=doc(did,fragment)
 assert any(norm(u)==norm(r['url']) for u in linkurls(d) if not any(c.isspace() for c in u)),did
 e=start(did,name);e['official_account_urls'].append(d['source_url'])
 text=f"The creator's own site explicitly presents {name} and labels the accepted TikTok URL {r['url']} as its TikTok account. Other creators' model credits, project members and Linktree recommendations were excluded."
 if yt:text+=f" Its own YouTube button links {yt}."
 add(e,d['source_url'],text,'official_website',collection_method='retained_public_profile_capture')
 if yt:
  cid=apiadd(e,yt);assert cid,yt;attach(e,cid,[d['source_url'],api_norm[norm(yt)]['url']])

# Fresh first-party channel crosslinks used to close unavailable TikTok profile pages.
for pre,url in [('3fa12','https://www.youtube.com/@Kylanz_KLZ/about'),('836837','https://www.youtube.com/channel/UCZsXl4d82Yx76SeGNtWGjlQ/about'),('f8b9','https://www.youtube.com/channel/UCRiS4VWQedLfgE1g1AKD1DQ/about')]:
 did=findid(pre);d=fresh[url];assert any(norm(u)==norm(selected[did]['url']) for u in linkurls(d))
 e=start(did,d['youtube']['title']);assert incoming(e,d)

# Explicit X-owner posts/bios, not mentions or rigger credits.
for pre,name,fragment,summary in [
 ('120ee','Oneiros Norr','x.com/OneirosNorr','The self-described sandman VTuber publishes a live announcement with its own YouTube live link and the exact TikTok oneiros.norr link.'),
 ('9d974','Nanako','x.com/Nanako_SLR','The creator\'s pinned own follow-links post explicitly labels TikTok nanako_npt, YouTube Nanako_NPT and Instagram nanako_npt. Other Solar Roar members mentioned elsewhere are not ownership evidence.'),
 ('7e6da','SmallC','x.com/SmallC69','The official SmallC profile identifies the creator and links its own Facebook SmallC69. Holie\'s separate rigger credit is not a persona-equivalence claim.')]:
 did=findid(pre);d=doc(did,fragment);e=start(did,name)
 add(e,d['source_url'],summary,collection_method='retained_public_profile_capture');e['official_account_urls'].append(d['source_url'])

# The successful TikTok embed is an owner-written identity source; third-party recorder omitted.
did=findid('6c71');d=doc(did,'tiktok.com/embed');e=start(did,'Pattivia')
add(e,d['source_url'],'The public TikTok creator embed identifies pattivia_live, renders this account\'s own videos and states that its main channel is Pattivia Ch. This is positive official self-identification, independent of the third-party recording site.',collection_method='retained_public_profile_capture')

# Historical exact handles from each creator's own channel videos.
did=findid('5d85');e=start(did,'Rei Quasar');v=next(v for v in historical if v['source_url'].endswith('dbQV5w4jO0E'))
add(e,v['source_url'],'The owner-written Socials section explicitly links https://www.tiktok.com/@reiquasar0; Who am I identifies Rei Quasar as the interstellar entertainer. This establishes the historical accepted account even though the current Carrd links a different handle.',observed=v['observed_at'],owner_channel_id=v['channel_id'],collection_method='public_video_description')
apiadd(e,v['source_url']);e['official_account_urls'] += ['https://www.twitch.tv/reiquasar0','https://x.com/ReiQuasar']
e['identity_notes']='Rei Quasar is a client in Neonsten\'s portfolio, not the Neonsten/Nyeeeon persona. No merge uses the mislabeled discovery name.'
did=findid('cf2e');e=start(did,'Kyoya Kieran');evs=[]
for suffix in ('NtfW1Hzl6fE','y0eI06HogTw'):
 v=next(v for v in historical if v['source_url'].endswith(suffix));evs.append(v['source_url'])
 add(e,v['source_url'],'The owner-written description introduces KYOYA KIERAN as a Thai VTuber and explicitly lists TikTok: / kyoya.vtuber under the creator\'s own follow accounts. This records the former exact handle; the current Linktree has kyoya.kieran.',observed=v['observed_at'],owner_channel_id=v['channel_id'],collection_method='public_video_description')
apiadd(e,evs[0]);attach(e,'UCd6bx1YwqNRzfaMoMB5nOHg',evs,'explicit_official_identity')
# Scythringe's own hub supplies the identity that the client portfolio cannot.
did=findid('d4ffc');d=fresh['https://linktr.ee/scythringe'];e=start(did,'Scythringe (ˣˣˣ)')
add(e,d['source_url'],'The owner-controlled scythringe hub, displayed as ˣˣˣ, labels its own Twitch scythringe, TikTok scythringe, X scythringe and YouTube scythringe links. The accepted TikTok URL differs only by tracking parameters. The Neonsten portfolio is a client relationship and supplies no merge.', 'official_website',d['observed_at'],collection_method='public_profile')
e['official_account_urls'] += ['https://linktr.ee/scythringe','https://www.twitch.tv/scythringe','https://x.com/scythringe']

# Instagram owner biographies.
ig_names={'41ca':'Fi Sword','4d6a':'Kess','8476':'Panda','996c':'Earendel','d7fe':'AmaLee (Monarch)'}
for pre,name in ig_names.items():
 did=findid(pre);d=doc(did,'instagram.com/'+selected[did]['url'].split('/')[-1]);e=start(did,name)
 add(e,d['source_url'],f"The account's own Instagram biography explicitly identifies {name} and describes its VTuber persona. General hashtag pages and secondary search results are not identity evidence.",collection_method='retained_public_profile_capture')
did=findid('dca7');e=start(did,'Bishamon Kuroneko');d=doc(did,'instagram.com/')
add(e,d['source_url'],'The Instagram owner bio explicitly points readers to its YouTube channel @BishamonKuroneko_AS. The corresponding public YouTube metadata identifies the exact known channel, rather than using display-name similarity.',collection_method='retained_public_profile_capture')
d=doc(did,'youtube.com/');cid=d['youtube']['externalId']
add(e,d['source_url'],'The official channel metadata binds vanity URL @BishamonKuroneko_AS to Channel ID '+cid+'.',owner_channel_id=cid,collection_method='retained_public_profile_capture')
attach(e,cid,[x['source_url'] for x in e['evidence']])

# Facebook owner identity, resolved from the actual X profile's outbound short link.
did=findid('9db208');e=start(did,'พี่เป็นหมี (I\'m A Mee)');d=doc(did,'x.com/ImAbearAbear')
add(e,d['source_url'],'The owner identifies as I\'m A Mee/หมี, a Thai VFacebook fox persona, and its profile website link t.co/iOq6R3grZl resolves to the exact accepted Facebook account IamBearBearAndBear.',collection_method='retained_public_profile_capture')
f=fresh['https://t.co/iOq6R3grZl'];add(e,f['source_url'],'The public owner-profile link redirects to https://www.facebook.com/IamBearBearAndBear; the page title identifies พี่เป็นหมี.',observed=f['observed_at'],collection_method='public_redirect')
e['official_account_urls'].append('https://x.com/ImAbearAbear')

# Bluesky profiles explicitly identify their own personas. Only declared own links are included.
web_config={
 '14e37':('Muerto Tarde','https://www.youtube.com/@MuertoTarde','https://muert.carrd.co/'),
 '1e734':('Fuyu','https://www.youtube.com/channel/UCqsI2kWRlvSe1jpeS3PoGwA','https://linktr.ee/fuyu_1102'),
 '2aa70':('Lucrezia','https://www.youtube.com/@lucreziacheckmate',None),
 '452ad':('Shikár Dawg','https://www.youtube.com/@Shikar_Dawg',None),
 '4eab':('JiYuu',None,None),
 '4f413':('Tsuma',None,None),
 '51ac':('Kyoya Kieran','https://www.youtube.com/@kyoyavtuber',None),
 '9caa':('Ruby de Laria','https://www.youtube.com/@rubyreth',None),
 'a568':('Xsaysir',None,None),
 'cf0b':('Kaneaki Arina',None,None),
 'd6a':('Agito Izanagi',None,None),
 'f7cc':('Okuran',None,None)}
for pre,(name,yt,hub) in web_config.items():
 did=findid(pre);r=selected[did];d=doc(did,'bsky.app/profile');e=start(did,name)
 add(e,d['source_url'],f"The owner-written Bluesky display name and biography explicitly present the {name} virtual persona. Credits to model artists, riggers and agencies were read as credits, not as persona ownership.",collection_method='retained_public_profile_capture')
 if hub:
  h=fresh[hub];e['official_account_urls'].append(hub)
  add(e,hub,f"The {name} creator hub explicitly links back to the accepted Bluesky profile and labels {yt} as its own YouTube channel.",'official_website',h['observed_at'],collection_method='public_profile')
  e['evidence'][0]['summary']+=f" Its biography links its official hub {hub}."
 if yt:
  if not hub:e['evidence'][0]['summary']+=f" It explicitly links its own YouTube account {yt}."
  cid=apiadd(e,yt);assert cid,yt;attach(e,cid,list(e['evidence_urls']))
 if pre=='4f413':e['official_account_urls'].append('https://www.twitch.tv/karatsuma');e['evidence'][0]['summary']+=' Its bio labels twitch.tv/karatsuma as its streaming channel.'
 if pre=='f7cc':e['official_account_urls']+=['https://www.twitch.tv/okurannn','https://www.bento.me/okurannuble'];e['evidence'][0]['summary']+=' Its own follow links are twitch.tv/okurannn and bento.me/okurannuble.'
 if pre=='cf0b':
  f=fresh['https://www.youtube.com/channel/UCDdYlO59uiphs8QUL7I88Rg/about'];incoming(e,f)

# Websites whose own channel or backlinks establish the exact baseline persona.
for pre,name,yt in [('67359','LittleBunnie','https://www.youtube.com/@LittleBunnieCh'),('7778','Zephyros Abysswalker','https://www.youtube.com/@ZephyrosLV'),('cb308','Hoshimura Himawari','https://www.youtube.com/@HimawariWhiteOwl')]:
 did=findid(pre);r=selected[did];d=doc(did,r['url']);e=start(did,name)
 add(e,r['url'],f"The creator-controlled site introduces {name} and explicitly labels {yt} as its own YouTube channel. Project members, manager links and artwork credits are not treated as the owner.",'official_website',collection_method='retained_public_profile_capture')
 cid=apiadd(e,yt);assert cid;attach(e,cid,list(e['evidence_urls']))
did=findid('c2d0');e=start(did,'Aina');d=doc(did,'bsky.app/profile')
add(e,d['source_url'],'The owner identifies as Aina (ไอนะ), VTuberTH, and explicitly supplies https://solo.to/aina_vtuber as its own link hub.',collection_method='retained_public_profile_capture')
f=fresh['https://www.youtube.com/channel/UCZBylMHjwaeTNJTLPxl6VgA/about'];cid=f['youtube']['externalId']
add(e,f['source_url'],'The baseline Aina channel directly lists https://bsky.app/profile/ainavtuber.bsky.social as its own profile, whose biography links the exact accepted Solo hub. This is an owner crosslink chain.',observed=f['observed_at'],owner_channel_id=cid,collection_method='public_profile')
e['official_account_urls'] += [d['source_url']];attach(e,cid,list(e['evidence_urls']))
did=findid('cc56');e=start(did,'SOLID');d=doc(did,'bsky.app/profile')
add(e,d['source_url'],'The owner-written profile identifies SOLID as a VTuberTH and directly links https://www.openlink.co/solid as its own hub.',collection_method='retained_public_profile_capture')
e['official_account_urls'].append(d['source_url'])

# Mortifer's official X links both the historic accepted /c/ URL and baseline channel.
did=findid('d611');e=entries[did];f=fresh['https://x.com/MortyBathory']
add(e,f['source_url'],'The official Mortifer Bathory self-introduction pins the exact accepted /c/MortiferBathoryChParabellum URL and its profile website points via t.co/5D5qzeTfjP to baseline channel UCoOMJUZ5plQtVQDYbicD3dw. Both are explicitly Mortifer\'s own channel links.',observed=f['observed_at'],collection_method='public_profile')
f=fresh['https://t.co/5D5qzeTfjP'];add(e,f['source_url'],'The official Mortifer profile website redirect lands on the baseline YouTube Channel ID UCoOMJUZ5plQtVQDYbicD3dw.',observed=f['observed_at'],owner_channel_id='UCoOMJUZ5plQtVQDYbicD3dw',collection_method='public_redirect')
attach(e,'UCoOMJUZ5plQtVQDYbicD3dw',['https://x.com/MortyBathory','https://t.co/5D5qzeTfjP'])

# Search leads are converted to matches only after a concrete official owner link.
for pre,url in [('120ee','https://www.youtube.com/channel/UCBsUODmi56ijq4o4imeZuwg/about'),('3d726','https://www.youtube.com/c/FortunaLeah/about'),('9db208','https://www.youtube.com/channel/UC_4Kw9UFTDz_Hv7K_rH9DQg/about'),('5dc706','https://www.youtube.com/channel/UCEZZl5ozactQATI4iIx2mOg/about')]:
 e=entries[findid(pre)];f=fresh[url]
 assert any(norm(u)==norm(selected[e['discovery_id']]['url']) for u in linkurls(f))
 incoming(e,f)
# Nanako's current channel links the X profile whose pinned post identifies the old TikTok.
e=entries[findid('9d974')];f=fresh['https://www.youtube.com/channel/UCVxPzerhZ7g_OL_5okEk08g/about']
add(e,f['source_url'],'The baseline channel directly links its own X profile Nanako_SLR. That profile pinned follow-links post supplies the exact accepted former TikTok nanako_npt; current channel social links use nanako_slr.',observed=f['observed_at'],owner_channel_id=f['youtube']['externalId'],collection_method='public_profile')
attach(e,f['youtube']['externalId'],list(e['evidence_urls']))
# Kamashi's current channel links the old owner-controlled Carrd carrying the TikTok.
e=entries[findid('bfe449')];f=fresh['https://www.youtube.com/channel/UClsrtReeDeC9WGR926fICZA/about']
add(e,f['source_url'],'The baseline Kamashi channel directly links kamashi.carrd.co as its own hub and its previous YouTube Kamashi_AKIA handle. The hub supplies the exact accepted TikTok kamashi_akia.',observed=f['observed_at'],owner_channel_id=f['youtube']['externalId'],collection_method='public_profile')
attach(e,f['youtube']['externalId'],list(e['evidence_urls']))
# Kylanz already has a trusted verified X persona, even though its YouTube is not indexed.
e=entries[findid('3fa12')];f=fresh['https://www.youtube.com/@Kylanz_KLZ/about'];known='https://x.com/Kylanz_KLZ'
assert any(norm(u)==norm(known) for u in linkurls(f))
pid=unique_claim(normmatch(known));assert pid
add(e,f['source_url'],'The same channel social links explicitly include its own X Kylanz_KLZ, which is the exact current verified account of the existing Kylanz persona.',observed=f['observed_at'],collection_method='public_profile')
e['official_account_urls'].append(known);e.setdefault('assertions',[]).append({'method':'official_crosslink','persona_id':pid,'source_urls':[f['source_url']]})

# Co-owned accepted accounts connect only through a proven common exact channel.
for cid,dids in channels.items():
 if len(dids)<2 or unique_claim(cidmatch(cid)):continue
 anchor=min(dids)
 for did in sorted(dids-{anchor}):
  e=entries[did];a=entries[anchor]
  # Both owner-controlled hubs/profile records form the explicit chain through this channel.
  peer_evs=[v for v in a['evidence'] if v['source_kind']!='youtube_api']
  for v in peer_evs:
   if v['source_url'] not in e['evidence_urls']:e['evidence'].append(dict(v));e['evidence_urls'].append(v['source_url']);e['checked_urls'].append(v['source_url'])
  e['official_account_urls'] += [selected[anchor]['url']]
  e.setdefault('assertions',[]).append({'method':'official_crosslink','target_discovery_id':anchor,'source_urls':list(e['evidence_urls'])})

# Record exact no-existing-match searches, not name-based decisions.
for did,e in entries.items():
 r=selected[did];ownclaims=[]
 for u in e['official_account_urls']:
  ownclaims+=urls.get(_account_url(u),[])
 if not e.get('assertions') and not ownclaims and not (r['platform']=='youtube' and unique_claim(cidmatch(e.get('platform_id')))):
  e['no_existing_persona_match']=True
  e['existing_persona_search']={'corpora':['trusted_baseline_1370.json','ThaiVirtualCreatorRegistry verified personas/current verified account_links','review_bundle.json accepted accounts'], 'exact_channel_ids':sorted(cid for cid,dids in channels.items() if did in dids),'official_urls_checked':sorted(set(e['official_account_urls'])),'name_leads_use':'Search leads only; name, handle, avatar and agency similarity never establish a merge.','result':'No exact stable-ID or supported owner-link match to an existing persona; the cited official source positively identifies this persona.'}
 if did in (findid('5d85'),findid('d4ffc')):
  e['existing_persona_search']['rejected_trusted_link_corrections']=[a['correction']['link_id'] for a in correction_audit if a['original_account']['handle'] in selected[did]['url']]
 # Retain unsuccessful original URLs as checked, never positive evidence.
 e['checked_urls']+=r['evidence_urls']
 for k in ('checked_urls','evidence_urls','official_account_urls'):e[k]=sorted(set(e[k]))
 e['evidence'].sort(key=lambda x:x['source_url'])
 for a in e.get('assertions',[]):a['source_urls']=sorted(set(a['source_urls']))
missing=sorted(set(selected)-set(entries));print('MISSING',[(d,selected[d]['url']) for d in missing])
payload={'schema_version':1,'batch':'linked-platforms-2026-09-19','selected_count':len(selected),'research_policy':'Exact stable IDs, current verified registry links, owner-controlled crosslinks or explicit official self-identification only. Eligibility corrections are separately retained. No display-name, handle, avatar, agency or fuzzy merges.','rows':[entries[d] for d in sorted(entries)]}
(EVIDENCE/'identity_research_linked.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('RESEARCH_ROWS',len(entries))
