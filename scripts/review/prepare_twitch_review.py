"""Build evidence excerpts for explicit review; does not change the registry."""
import json,re
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[2]
VIRTUAL=re.compile(r'v[- ]?tub(?:er|ing)|v[- ]?streamer|png[- ]?tuber|วีท[ูบป]|วีสตรีม|virtual (?:streamer|youtuber|student|hybrid)',re.I)

def norm(u):
    p=urlparse(u);return p.hostname.replace('www.','')+p.path.rstrip('/').lower() if p.hostname else ''

def main():
    t=json.loads((ROOT/'data/registry.json').read_text(encoding='utf-8'))['tables']
    evidence={x['id']:x for x in t['evidence']};personas={x['id']:x for x in t['personas']}
    account_personas={}
    for l in t['account_links']:
        if l['review_status']=='verified':account_personas.setdefault(l['account_id'],set()).add(l['persona_id'])
    social_personas={}
    for a in t['accounts']:
        if a['id'] in account_personas:social_personas[norm(a['url'])]=account_personas[a['id']]
    youtube_personas={}
    for p in t['personas']:
        m=re.search(r'youtube\.com/channel/(UC[\w-]{22})',evidence[p['evidence_id']]['url'])
        if m:youtube_personas.setdefault(m[1],set()).add(p['id'])
    ys={}
    for line in (ROOT/'intake/2026-09-13-twitch-youtube-owner-evidence.jsonl').open(encoding='utf-8'):
        y=json.loads(line)
        if len(y.get('twitch_urls',[]))==1:
            h=y['twitch_urls'][0].rstrip('/').rsplit('/',1)[1].lower();ys.setdefault(h,[]).append(y)
    expanded={x['handle']:x['sources'] for x in json.loads((ROOT/'intake/archive/2026-09-13/2026-09-13-twitch-expanded-source-queue.json').read_text(encoding='utf-8'))}
    observed={};unresolved=[]
    for path in sorted((ROOT/'intake').glob('2026-09-13-twitch-public-profiles*.jsonl')):
        for line in path.open(encoding='utf-8'):
            r=json.loads(line)
            if r['status']!='resolved':unresolved.append(r);continue
            r['sources']=expanded.get(r['handle'],r['sources'])
            observed[r['platform_id']]=r
    dossiers=[];excluded=[]
    for r in sorted(observed.values(),key=lambda x:x['handle']):
        h=r['handle'];texts=[('twitch_bio',r['source_url'],r['bio'])]
        texts.extend(('twitch_panel',r['source_url'],p['title']+'\n'+p['description']) for p in r['panels'])
        for y in ys.get(h,[]):texts.append(('youtube_owner',y['source_url'],y.get('current_name','')+'\n'+y.get('description','')))
        thai=r['broadcast_language']=='TH' or bool(re.search('[ก-๙]',r['bio'])) or any(s.get('thai_directory') for s in r['sources'])
        if not thai:excluded.append({'handle':h,'platform_id':r['platform_id'],'reason':'Thai relevance not established'});continue
        matches=[]
        for kind,url,text in texts:
            m=VIRTUAL.search(text)
            if m:matches.append({'kind':kind,'url':url,'excerpt':text[max(0,m.start()-100):m.end()+230]})
        links=[]
        for s in r['social_links']:
            for pid in social_personas.get(norm(s['url']),set()):links.append({'persona_id':pid,'persona_name':personas[pid]['name'],'kind':'twitch_social','evidence_url':r['source_url'],'target_url':s['url']})
        for y in ys.get(h,[]):
            for pid in youtube_personas.get(y.get('youtube_channel_id'),set()):links.append({'persona_id':pid,'persona_name':personas[pid]['name'],'kind':'youtube_owner','evidence_url':y['source_url'],'target_url':r['url']})
        dossiers.append({'handle':h,'platform_id':r['platform_id'],'name':r['name'],'bio':r['bio'],'broadcast_language':r['broadcast_language'],
            'scope_matches':matches,'existing_persona_links':links,'youtube_sources':[y['source_url'] for y in ys.get(h,[])],'profile':r})
    for name,value in [('twitch-review-dossiers.json',dossiers),('twitch-out-of-scope.json',excluded)]:
        (ROOT/'intake'/('2026-09-13-'+name)).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'resolved_unique_ids':len(observed),'thai_relevant_accounts':len(dossiers),'excluded_without_thai_evidence':len(excluded),'scope_excerpts':sum(bool(x['scope_matches']) for x in dossiers),'existing_persona_crosslinks':sum(bool(x['existing_persona_links']) for x in dossiers)}))

if __name__=='__main__':main()
