"""Expand Thai Twitch discovery using supplied directories and owner links."""
import json,re,html
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from collect_twitch_sources import fetch

ROOT=Path(__file__).resolve().parents[2]
DAY='2026-09-13'

def main():
    queue={x['handle']:x for x in json.loads((ROOT/'intake'/f'{DAY}-twitch-source-queue.json').read_text(encoding='utf-8'))}
    initial=set(queue);audit=[];observations=[]
    def add(url,source,name='',kind='secondary_source',youtube_id=None):
        m=re.fullmatch(r'https?://(?:www\.)?twitch\.tv/([A-Za-z0-9_]{1,25})/?',url)
        if not m or m[1].lower() in {'hololist','directory','videos','team','teams','settings','products','downloads'}:return
        h=m[1].lower();row=queue.setdefault(h,{'url':'https://www.twitch.tv/'+h,'handle':h,'sources':[]})
        s={'url':source,'name':name,'kind':kind,'observed_at':datetime.now(timezone.utc).isoformat(),'thai_directory':True,'youtube_ids':[youtube_id] if youtube_id else []}
        if not any(x['url']==source for x in row['sources']):row['sources'].append(s)
    for line in (ROOT/'intake'/f'{DAY}-twitch-youtube-owner-evidence.jsonl').open(encoding='utf-8'):
        r=json.loads(line)
        for u in r.get('twitch_urls',[]):add(u,r['source_url'],r.get('current_name',r['name']),'self_statement',r.get('youtube_channel_id'))
    audit.append({'source':'YouTube owner pages','new_handles_so_far':len(set(queue)-initial)})
    profiles={}
    for page in range(1,10):
        url='https://hololist.net/category/th/'+(f'page/{page}/' if page>1 else '')
        body=fetch(url)
        for u,n in re.findall(r'<a class="[^"]*text-truncate w-100[^"]*" href="(https://hololist.net/[^"/]+/)" title="([^"]+)"',body):profiles[u]=html.unescape(n)
    def profile(item):
        url,name=item
        try:
            body=fetch(url)
            urls=sorted(set(re.findall(r'https?://(?:www\.)?twitch\.tv/[A-Za-z0-9_]+',body))-{'https://www.twitch.tv/hololist'})
            return {'source_url':url,'name':name,'twitch_urls':urls,'observed_at':datetime.now(timezone.utc).isoformat()}
        except Exception as e:return {'source_url':url,'name':name,'error':type(e).__name__}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for r in pool.map(profile,profiles.items()):
            observations.append(r)
            for u in r.get('twitch_urls',[]):add(u,r['source_url'],r['name'])
    audit.append({'source':'HoloList Thai category','category_pages':9,'profile_pages':len(profiles),'profiles_with_twitch':sum(bool(x.get('twitch_urls')) for x in observations),'errors':sum('error' in x for x in observations)})
    seen=set()
    for query in ['countries=th','languages=Thai']:
        count=0;page=1
        while page<=20:
            url=f'https://bacharu.io/api/vtubers?{query}&page={page}&limit=50'
            d=json.loads(fetch(url));items=d.get('data',[]);count+=len(items)
            for r in items:
                slug=r['canonicalName']
                if slug in seen:continue
                seen.add(slug)
                social=r.get('social') or {}
                urls=sorted(set(re.findall(r'https?://(?:www\.)?twitch\.tv/[A-Za-z0-9_]+',json.dumps(social))))
                observation={'source_url':'https://bacharu.io/vtuber/'+slug,'name':r.get('name',''),'twitch_urls':urls,'observed_at':datetime.now(timezone.utc).isoformat()}
                observations.append(observation)
                for u in urls:add(u,observation['source_url'],observation['name'])
            if not d.get('pagination',{}).get('hasNext') or not items:break
            page+=1
        audit.append({'source':'Bacharu '+query,'pages':page,'records_read':count})
    for name,data in [('twitch-expanded-source-queue.json',list(queue.values())),('twitch-additional-queue.json',[r for h,r in queue.items() if h not in initial]),('twitch-expanded-source-audit.json',audit)]:
        with (ROOT/'intake'/f'{DAY}-{name}').open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    with (ROOT/'intake'/f'{DAY}-extra-directory-links.jsonl').open('x',encoding='utf-8') as f:
        for r in observations:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    print(json.dumps({'sources':audit,'all_handles':len(queue),'new_handles':len(set(queue)-initial)}),flush=True)

if __name__=='__main__':main()
