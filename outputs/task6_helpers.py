import json,re,sys
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qs
sys.path.insert(0,str(Path.cwd()))
from scripts.resolve_creator_identities import _indexes,_account_url,_correct_trusted_links
EVIDENCE=Path('docs/evidence/creator-registry-review-2026-09-19')
BASE=Path('C:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/.tmp/new_account_review')
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
review=read(EVIDENCE/'review_bundle.json');baseline=read(EVIDENCE/'trusted_baseline_1370.json');trusted=read('C:/Users/Icezaza/Documents/GitHub/ThaiVirtualCreatorRegistry/data/registry.json')
selected={r['discovery_id']:r for r in review['rows'] if r['eligibility']=='vtuber' and r['platform'] in ('youtube','tiktok','website','instagram','facebook','ganknow')}
extracts={r['discovery_id']:r for r in read('outputs/task6_profile_extracts.json')}
api={r['url']:r for r in read('outputs/task6_youtube_lookups.json')['lookups'] if 'evidence' in r}
corrected_trusted,correction_audit=_correct_trusted_links(trusted,[read(EVIDENCE/'trusted_link_corrections.json')])
names,ids,urls,persona_urls,aliases,baseline_ids=_indexes(baseline,corrected_trusted)
all_review={r['discovery_id']:r for r in review['rows']}
watch=read(BASE/'youtube_watch.json')
about=read(BASE/'youtube_evidence.json')
def norm(url):
 p=urlsplit(_account_url(url));return urlunsplit((p.scheme,p.netloc,p.path,'',''))
def normmatch(url):
 key=norm(url)
 return [c for u,claims in urls.items() if norm(u)==key for c in claims]
def cidmatch(cid):return ids.get(('youtube',cid),[])
def unique_claim(claims):
 owners=sorted({c['persona_id'] for c in claims});return owners[0] if len(owners)==1 else None
