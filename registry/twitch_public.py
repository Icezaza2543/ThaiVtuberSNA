"""Read public Twitch profiles without login; keep no tokens, chats or viewers.

The public website application ID is read from Twitch's own page at runtime.
It is not an OAuth access token. Private fields are never requested.
"""
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from .tiktok import public_text

FIELDS = 'id login displayName description broadcastSettings { language title } channel { socialMedias { name url } } panels { ... on DefaultPanel { title description } }'

def request_json(query, client_id):
    req = Request('https://gql.twitch.tv/gql', data=json.dumps({'query':query}).encode(),
        headers={'Client-ID':client_id, 'Content-Type':'application/json'})
    with urlopen(req,timeout=30) as r:
        body=r.read(4_000_001)
    if len(body)>4_000_000: raise ValueError('Response size limit')
    return json.loads(body)

def parse_user(user, expected_handle, expected_id=None):
    if not isinstance(user,dict): raise ValueError('Profile unavailable')
    if expected_id is None and user.get('login','').casefold()!=expected_handle.casefold(): raise ValueError('Login mismatch')
    identifier=str(user.get('id',''))
    if not re.fullmatch(r'\d{1,30}',identifier): raise ValueError('Numeric user ID absent')
    if expected_id is not None and identifier!=str(expected_id): raise ValueError('User ID mismatch')
    broadcast=user.get('broadcastSettings') or {}
    panels=[]
    for p in (user.get('panels') or []):
        title=public_text(p.get('title'),120)
        # Omit entire donor/subscriber acknowledgement panels rather than names.
        description=public_text(p.get('description'),1800)
        text=title+' '+description
        if re.search(r'donat|donor|support|subscrib|special thanks|thank you|thanks to|credits?|moderator|ผู้บริจาค|โดเนท|ขอบคุณ|ผู้สนับสนุน',text,re.I): continue
        if re.search(r'about|intro|profile|เกี่ยวกับ|แนะนำ|รู้จัก|vtuber|vstream|pngtuber|วีท[ูบป]|วีสตรีม|live2d',text,re.I):
            panels.append({'title':title,'description':description})
    profile={'platform_id':identifier,'id_namespace':'user_id','handle':user['login'],
        'name':public_text(user.get('displayName'),150),'bio':public_text(user.get('description'),1500),
        'broadcast_language':broadcast.get('language'), 'broadcast_title':public_text(broadcast.get('title'),500),
        'social_links':[{'name':public_text(s.get('name'),60),'url':s['url']} for s in (user.get('channel') or {}).get('socialMedias',[]) if s.get('url','').startswith('https://')],
        'panels':panels[:20]}
    return profile

_PUBLIC_CLIENT_ID_CACHE = None


def get_public_twitch_client_id(seed_handle='twitch', timeout=15.0):
    """Retrieve Twitch public website application identifier from webpage and cache in runtime."""
    global _PUBLIC_CLIENT_ID_CACHE
    if _PUBLIC_CLIENT_ID_CACHE:
        return _PUBLIC_CLIENT_ID_CACHE
    req = Request('https://www.twitch.tv/' + seed_handle, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=timeout) as r:
        page = r.read(2_000_000).decode('utf-8', errors='ignore')
    match = re.search(r'clientId="([a-zA-Z0-9]+)"', page)
    if not match:
        raise ValueError('Public website application identifier unavailable')
    _PUBLIC_CLIENT_ID_CACHE = match[1]
    return _PUBLIC_CLIENT_ID_CACHE


def resolve_public_twitch_user_id(handle, client_id=None, timeout=10.0):
    """Resolve numeric user_id for a Twitch handle via public GQL endpoint without hardcoded credentials."""
    if not handle or not re.fullmatch(r'[a-zA-Z0-9_]{1,30}', handle):
        return None
    try:
        cid = client_id or get_public_twitch_client_id(handle, timeout=timeout)
        query = f'query {{ user(login: "{handle}") {{ id login }} }}'
        response = request_json(query, cid)
        user = response.get('data', {}).get('user')
        if user and str(user.get('id', '')).isdigit():
            return str(user['id'])
    except Exception:
        pass
    return None


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    queue=json.loads(args.input.read_text(encoding='utf-8-sig'))
    handles=[x['handle'].lower() for x in queue]
    if len(set(handles))!=len(handles) or any(not re.fullmatch(r'[a-z0-9_]{1,25}',x) for x in handles): raise ValueError('Invalid/duplicate handles')
    if args.output.exists(): raise ValueError('Choose a new observation file')
    client_id = get_public_twitch_client_id(handles[0], timeout=30.0)
    counts={'requested':len(queue),'resolved':0,'unresolved':0}
    with args.output.open('x',encoding='utf-8') as out:
        for start in range(0,len(queue),20):
            batch=queue[start:start+20]
            arguments=[]
            for x in batch:
                lookup=x.get('lookup_user_id')
                if lookup and not re.fullmatch(r'\d{1,30}',str(lookup)): raise ValueError('Invalid lookup ID')
                arguments.append('id:'+json.dumps(str(lookup)) if lookup else 'login:'+json.dumps(x['handle']))
            query='query { '+' '.join(f'u{i}: user({arg}) {{ {FIELDS} }}' for i,arg in enumerate(arguments))+' }'
            response=request_json(query,client_id)
            if response.get('errors'): raise ValueError('Public profile query failed: '+str(response['errors'])[:300])
            for i,item in enumerate(batch):
                result={'url':item['url'],'source_url':item['url']+'/about','observed_at':datetime.now(timezone.utc).isoformat(),'sources':item.get('sources',[])}
                try:
                    profile=parse_user(response.get('data',{}).get('u'+str(i)),item['handle'],item.get('lookup_user_id'))
                    result.update(status='resolved',**profile)
                    if item.get('lookup_user_id'):
                        result['requested_url']=item['url']
                        result['url']='https://www.twitch.tv/'+profile['handle']
                        result['source_url']=result['url']+'/about'
                    result['public_profile_sha256']=hashlib.sha256(json.dumps(profile,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                except ValueError as e: result.update(status='unresolved',reason=str(e))
                out.write(json.dumps(result,ensure_ascii=False)+'\n');counts[result['status']]+=1
            out.flush();print(json.dumps(counts),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
