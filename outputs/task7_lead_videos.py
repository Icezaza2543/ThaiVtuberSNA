import requests,re,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
out=Path('outputs/task7_video_evidence.json')
rows=json.loads(out.read_text(encoding='utf-8')) if out.exists() else []
def walk(o):
 if isinstance(o,dict):
  yield o
  for v in o.values():yield from walk(v)
 elif isinstance(o,list):
  for v in o:yield from walk(v)
def obj(raw,key):
 st=raw.find(key)
 if st<0:return {}
 return json.JSONDecoder().raw_decode(raw[st+len(key):].lstrip())[0]
videos=['https://www.youtube.com/watch?v=ClV_GClhmkY']
for cid in ['UCNmZMq-4asLHHd0WvdO2iRQ','UC1o-4IZwxHOxGyUKN6xpNZA']:
 u='https://www.youtube.com/channel/'+cid+'/videos';r=requests.get(u,timeout=20)
 data=obj(r.text,'var ytInitialData = ')
 vids=list(dict.fromkeys(o['videoId'] for o in walk(data) if 'videoId' in o))[:12]
 videos+=['https://www.youtube.com/watch?v='+v for v in vids]
def get(u):
 try:
  r=requests.get(u,timeout=20);data=obj(r.text,'var ytInitialPlayerResponse = ');v=data.get('videoDetails',{})
  return {'source_url':u,'status':r.status_code,'observed_at':datetime.now(timezone.utc).isoformat(),'video':{k:v[k] for k in ['title','author','videoId','channelId','shortDescription'] if k in v}}
 except Exception as e:return {'source_url':u,'error':type(e).__name__}
with ThreadPoolExecutor(max_workers=6) as pool:
 for d in pool.map(get,videos):
  rows=[p for p in rows if p['source_url']!=d['source_url']]+[d]
  print(json.dumps({'source_url':d['source_url'],'title':d.get('video',{}).get('title'),'channel_id':d.get('video',{}).get('channelId')},ensure_ascii=False))
out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
