import json,requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
r=json.loads(Path('outputs/task7_public_profiles.json').read_text(encoding='utf-8'))
profiles=[]
for p in r:
 posturls={z['url'] for a in p.get('posts',[]) for z in a['links']}
 links=[a for a in p.get('links',[]) if a['url'] not in posturls and not any(s in a['url'] for s in ('x.com/','twitter.com/','twimg.com/'))]
 for l in links:profiles.append({'source_url':p['source_url'],**l})
def expand(l):
 d=dict(l,observed_at=datetime.now(timezone.utc).isoformat())
 try:
  if 't.co/' in l['url']:
   r=requests.get(l['url'],timeout=20,allow_redirects=False);d['status']=r.status_code;d['expanded_url']=r.headers.get('location')
  else:d['expanded_url']=l['url']
 except Exception as e:d['error']=type(e).__name__
 return d
with ThreadPoolExecutor(max_workers=8) as pool:d=list(pool.map(expand,profiles))
Path('outputs/task7_profile_links.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for a in d:print(a['source_url'],a.get('expanded_url'),a['label'])
