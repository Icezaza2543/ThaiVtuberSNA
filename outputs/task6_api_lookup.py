import json,runpy,socket,sys
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone
sys.path.insert(0,str(Path.cwd()))
sys.path.insert(0,str(Path('.tmp/task6_deps').resolve()))
settings=runpy.run_path('C:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/config/settings.py')
from collector.youtube_identity_client import YouTubeIdentityClient
socket.setdefaulttimeout(25)
class MeteredClient(YouTubeIdentityClient):
    requests=0
    def _execute(self,request):
        self.requests+=1
        return request.execute()
client=MeteredClient(settings['YOUTUBE_API_KEY'],cache_dir=Path('.tmp/creator_identity'))
review=json.loads(Path('docs/evidence/creator-registry-review-2026-09-19/review_bundle.json').read_text(encoding='utf-8-sig'))
selected=[r for r in review['rows'] if r['eligibility']=='vtuber' and r['platform'] in ('youtube','tiktok','website','instagram','facebook','ganknow')]
queue=[]
for r in selected:
    urls=([r['url']] if r['platform']=='youtube' else [])+r['evidence_urls']
    for url in urls:
        if 'youtube.com/' not in url:continue
        if '/c/' in url and r.get('channel_id'):url='https://www.youtube.com/channel/'+r['channel_id']
        try: client._parse_url(url)
        except RuntimeError:continue
        if url not in queue:queue.append(url)
extra=Path('outputs/task6_api_extra_urls.json')
if extra.exists(): queue.extend(json.loads(extra.read_text(encoding='utf-8')))
path=Path('outputs/task6_youtube_lookups.json')
prior=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'lookups':[],'requests':0}
records=prior['lookups'];seen={r['url'] for r in records if 'evidence' in r or r.get('requests',0)>0}
for url in queue:
    if url in seen:continue
    before=client.requests
    try:
        evidence=client.resolve(url)
        record={'url':url,'evidence':asdict(evidence),'observed_at':datetime.now(timezone.utc).isoformat(),'requests':client.requests-before}
    except RuntimeError as exc:record={'url':url,'error':str(exc),'requests':client.requests-before}
    records.append(record)
    path.write_text(json.dumps({'lookups':records,'requests':prior['requests']+client.requests},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'url':url,'channel_id':record.get('evidence',{}).get('channel_id'),'error':record.get('error'),'requests':client.requests},ensure_ascii=True),flush=True)
print('TOTAL',len(records),'QUOTA_UNITS',prior['requests']+client.requests)

