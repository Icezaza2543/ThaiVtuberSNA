import json,re,sys,html
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urljoin
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import requests
from bs4 import BeautifulSoup
P=Path('docs/evidence/creator-registry-review-2026-09-19')
review=json.loads((P/'review_bundle.json').read_text(encoding='utf-8'))
rows=[r for r in review['rows'] if r['eligibility']=='vtuber' and r['platform']=='x']
assert len(rows)==126 and len({r['discovery_id'] for r in rows})==126
out=Path('outputs/task7_public_profiles.json')
prior=json.loads(out.read_text(encoding='utf-8')) if out.exists() else []
seen={r['source_url'] for r in prior if r.get('status')==200 and r.get('meta',{}).get('description')}
urls=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')) if len(sys.argv)>1 else [r['url'] for r in rows]
def walk(o):
 if isinstance(o,dict):
  yield o
  for v in o.values():yield from walk(v)
 elif isinstance(o,list):
  for v in o:yield from walk(v)
def fetch(u):
 d={'source_url':u,'observed_at':datetime.now(timezone.utc).isoformat()}
 try:
  r=requests.get(u,timeout=25,headers={'User-Agent':'Mozilla/5.0'})
  d.update(status=r.status_code,final_url=r.url)
  raw=r.content.decode('utf-8',errors='replace');soup=BeautifulSoup(raw,'html.parser')
  d['meta']={m.get('property') or m.get('name'):m.get('content') for m in soup.find_all('meta') if (m.get('property') or m.get('name')) in ('og:title','og:description','og:url','description','title')}
  links=[]
  for a in soup.find_all('a',href=True):
   link=html.unescape(a['href'])
   if '/redirect?' in link:link=parse_qs(urlsplit(link).query).get('q',[link])[0]
   if link.startswith(('http://','https://')):
    links.append({'label':a.get_text(' ',strip=True),'url':link,'title':a.get('title')})
  d['posts']=[{'text':a.get_text(' ',strip=True),'links':[{'label':v.get_text(' ',strip=True),'url':urljoin(u,v['href']),'title':v.get('title')} for v in a.find_all('a',href=True)]} for a in soup.find_all('article')]
  start=raw.find('var ytInitialData = ')
  if start>=0:
   data,_=json.JSONDecoder().raw_decode(raw[start+20:].lstrip())
   for ob in walk(data):
    if 'channelMetadataRenderer' in ob:
     m=ob['channelMetadataRenderer'];d['youtube']={k:m[k] for k in ('title','description','externalId','channelUrl','vanityChannelUrl') if k in m}
    if 'urlEndpoint' in ob:
     link=ob['urlEndpoint'].get('url','')
     if '/redirect?' in link:link=parse_qs(urlsplit(link).query).get('q',[link])[0]
     if link.startswith(('http://','https://')):links.append({'label':'channel link','url':link})
  d['links']=list({(x['label'],x['url']):x for x in links}.values())
  for el in soup(['script','style','noscript']):el.decompose()
  d['text']=soup.get_text(' ',strip=True)[:15000]
 except Exception as e:d['error']=type(e).__name__
 return d
with ThreadPoolExecutor(max_workers=6) as pool:
 for d in pool.map(fetch,[u for u in urls if u not in seen]):
  prior=[p for p in prior if p['source_url']!=d['source_url']]+[d]
  out.write_text(json.dumps(prior,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print(json.dumps({'url':d['source_url'],'status':d.get('status'),'title':d.get('meta',{}).get('og:title'),'error':d.get('error')},ensure_ascii=True),flush=True)
