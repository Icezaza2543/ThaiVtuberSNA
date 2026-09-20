"""Collect public analytics into immutable, sanitized source batches.

No persona, ownership, affiliation or lifecycle decisions are made here.
Run with --task all or one source. Each output file must be new.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .store import ROOT
from .tiktok import EmbedState, parse_embed, public_text
from .twitch_public import request_json

CHUY = 'https://storage.googleapis.com/thaivtuberranking.appspot.com/v2/channel_data/'
HUB = 'https://api.vtuberthai.com/v1/'

def now():
    return datetime.now(timezone.utc).isoformat()

def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as response:
        body = response.read(24_000_001)
        modified = response.headers.get('Last-Modified')
    if len(body) > 24_000_000:
        raise ValueError('Response limit exceeded')
    return body.decode('utf-8'), modified

def number(value):
    return value if type(value) is int and value >= 0 else None

def selected(value, keys):
    return {k: value.get(k) for k in keys}

def envelope(url, data, modified=None):
    return {'source_url': url, 'observed_at': now(), 'http_last_modified': modified,
            'status': 'ok', 'data': data,
            'retained_sha256': hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}

def error(url, exc):
    return {'source_url': url, 'observed_at': now(), 'status': 'error',
            'reason': 'http_' + str(exc.code) if isinstance(exc, HTTPError) else type(exc).__name__}

def write(path, records):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'xt', encoding='utf-8') as stream:
        for i, row in enumerate(records, 1):
            stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            if i % 100 == 0:
                stream.flush()
                print(json.dumps({'file': path.name, 'processed': i}), flush=True)
    print(json.dumps({'file': path.name, 'complete': True, 'records': i if 'i' in locals() else 0}), flush=True)

def chuy(output, workers):
    url = CHUY + 'list.json'
    body, modified = fetch(url)
    records = json.loads(body)['result']
    clean = [selected(r, ['channel_id','title','subscribers','views','videos','published_at','updated_at','last_published_video_at']) for r in records]
    write(output/'chuy-channels.jsonl', [envelope(url, clean, modified)])
    def history(item):
        url = CHUY + 'chart_data/' + item['channel_id'] + '.json'
        try:
            body, modified = fetch(url)
            d = json.loads(body)['result']
            if d['id'] != item['channel_id']:
                raise ValueError('Channel ID mismatch')
            points = [selected(p, ['date','subscribers','views','videos']) for p in d['chart_data_points']]
            return envelope(url, {'channel_id':d['id'], 'points':points}, modified)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return error(url, exc)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        write(output/'chuy-history.jsonl.gz', pool.map(history, clean))
    result = []
    for endpoint in ['one_day_ranking','three_days_ranking','seven_days_ranking','live_videos','upcoming_videos']:
        url = CHUY + endpoint + '.json'
        try:
            body, modified = fetch(url)
            rows = [selected(r, ['id','title','channel_id','view_count','like_count','comment_count','published_at','live_status','live_schedule','live_start','live_end','live_concurrent_viewer_count']) for r in json.loads(body)['result']]
            result.append(envelope(url, rows, modified))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result.append(error(url, exc))
    write(output/'chuy-content.jsonl', result)

def tiktok(output, workers, accounts):
    def collect(a):
        url = 'https://www.tiktok.com/embed/@' + a['handle'] + '?lang=en&embedFrom=webapp_preview'
        try:
            body, modified = fetch(url)
            identity = parse_embed(body, a['handle'])
            if identity['platform_id'] != a['platform_id']:
                raise ValueError('Stable ID mismatch')
            parser = EmbedState(); parser.feed(body)
            pages = json.loads(''.join(parser.parts))['source']['data'].values()
            page = next(p for p in pages if isinstance(p,dict) and str(p.get('userInfo',{}).get('id')) == a['platform_id'])
            user = page['userInfo']
            videos = []
            for v in page.get('videoList', []):
                if v.get('privateItem') or v.get('authorUniqueId','').casefold() != a['handle'].casefold():
                    continue
                if not str(v.get('id','')).isdigit():
                    continue
                videos.append({'id':str(v['id']), 'title':public_text(v.get('desc'),250),
                               'create_time':v.get('createTime'), 'views':number(v.get('playCount')),
                               'likes':number(v.get('diggCount')), 'comments':number(v.get('commentCount')),
                               'shares':number(v.get('shareCount'))})
            return envelope(url, {'account_id':a['id'],'platform_id':a['platform_id'], 'handle':user['uniqueId'],
                'followers':number(user.get('followerCount')), 'likes_received':number(user.get('heartCount')),
                'videos':videos}, modified)
        except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
            return error(url, exc) | {'account_id':a['id']}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        write(output/'tiktok.jsonl', pool.map(collect, [a for a in accounts if a['platform']=='tiktok']))

def twitch(output, workers, accounts):
    accounts = [a for a in accounts if a['platform']=='twitch']
    body, _ = fetch(accounts[0]['url'])
    client = re.search(r'clientId="([a-zA-Z0-9]+)"', body)[1]
    fields = 'id login followers { totalCount } videos(first: 100, type: ARCHIVE, sort: TIME) { edges { node { id title createdAt lengthSeconds viewCount } } pageInfo { hasNextPage } } stream { id createdAt viewersCount game { name } }'
    def batches():
        for start in range(0,len(accounts),10):
            batch = accounts[start:start+10]
            query = 'query { ' + ' '.join('u'+str(i)+': user(id:'+json.dumps(a['platform_id'])+') { '+fields+' }' for i,a in enumerate(batch))+' }'
            try:
                result = request_json(query, client)
                if result.get('errors'):
                    raise ValueError('GraphQL query error')
                for i,a in enumerate(batch):
                    d = result.get('data',{}).get('u'+str(i))
                    if not d or str(d['id']) != a['platform_id']:
                        yield error(a['url'], ValueError()) | {'account_id':a['id']}
                        continue
                    videos = []
                    for edge in d.get('videos',{}).get('edges',[]):
                        v=edge['node']
                        videos.append({'id':str(v['id']), 'title':public_text(v.get('title'),250),
                            'published_at':v.get('createdAt'), 'duration_seconds':number(v.get('lengthSeconds')),
                            'views':number(v.get('viewCount'))})
                    live = d.get('stream')
                    yield envelope('https://www.twitch.tv/'+d['login']+'/videos',
                        {'account_id':a['id'],'platform_id':str(d['id']),'handle':d['login'],
                         'followers':number((d.get('followers') or {}).get('totalCount')),
                         'videos':videos, 'has_more_videos':d.get('videos',{}).get('pageInfo',{}).get('hasNextPage'),
                         'live': None if not live else {'id':str(live['id']), 'started_at':live.get('createdAt'),
                             'concurrent_viewers':number(live.get('viewersCount')), 'game':(live.get('game') or {}).get('name')}})
            except (OSError, ValueError, KeyError, TypeError) as exc:
                for a in batch:
                    yield error(a['url'], exc) | {'account_id':a['id']}
            print(json.dumps({'source':'twitch','processed':min(start+10,len(accounts))}), flush=True)
    write(output/'twitch.jsonl', batches())

def hub(output, workers):
    url = HUB+'vtubers'; body, modified = fetch(url)
    rows = json.loads(body)
    clean = [selected(r,['id','name','agency','tags','subscribers','channelViews','debutDate','status','youtubeChannelId','twitchLogin','tiktokUsername']) for r in rows]
    write(output/'hub-channels.jsonl',[envelope(url,clean,modified)])
    def history(r):
        url=HUB+'subscriber-tracker/'+r['id']+'?range=daily'
        try:
            body,modified=fetch(url); d=json.loads(body)
            if d.get('vtuberId') != r['id']:
                raise ValueError('Source ID mismatch')
            return envelope(url, {'source_id':r['id'],'channel_id':r['youtubeChannelId'],
                'points':[selected(p,['label','capturedAt','subscribers','views']) for p in d.get('history',[])]}, modified)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            return error(url,exc)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        write(output/'hub-history.jsonl.gz',pool.map(history,clean))

def bacharu(output):
    result=[];seen=set()
    for query in ['countries=th','languages=Thai']:
        for page in range(1,21):
            url=f'https://bacharu.io/api/vtubers?{query}&page={page}&limit=50'
            body, modified=fetch(url);d=json.loads(body);clean=[]
            for r in d['data']:
                if r['canonicalName'] in seen:continue
                seen.add(r['canonicalName'])
                row=selected(r,['canonicalName','name','countries','languages','streamingLanguages','genres','debut','graduationDate','status','updatedAt'])
                row['social']=selected(r.get('social') or {},['youtube','twitch','tiktok'])
                row['groups']=[selected(g,['name','canonicalName','status']) for g in r.get('groups',[])]
                a=r.get('activity') or {};tw=a.get('twitch') or {};yt=a.get('youtube') or {}
                row['activity']={'twitch':{'followers':number(tw.get('followerCount')),
                    'videos':[dict(selected(v,['id','createdAt','duration','viewCount','url']),title=public_text(v.get('title'),250)) for v in (tw.get('recentStreams') or [])]},
                    'youtube':{'subscribers':number(yt.get('subscriberCount')),'lastVideo':selected(yt.get('lastVideo') or {},['time','link','title'])}}
                clean.append(row)
            result.append(envelope(url,clean,modified))
            if not d.get('pagination',{}).get('hasNext'):break
    write(output/'bacharu.jsonl',result)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--task',choices=['all','chuy','tiktok','twitch','hub','bacharu'],default='all')
    parser.add_argument('--workers',type=int,choices=range(1,9),default=4)
    args=parser.parse_args(argv);args.output.mkdir(parents=True,exist_ok=True)
    accounts=json.loads((ROOT/'data/registry.json').read_text(encoding='utf-8'))['tables']['accounts']
    tasks={'chuy':lambda:chuy(args.output,args.workers),'tiktok':lambda:tiktok(args.output,args.workers,accounts),
           'twitch':lambda:twitch(args.output,args.workers,accounts),'hub':lambda:hub(args.output,args.workers),
           'bacharu':lambda:bacharu(args.output)}
    for task in (tasks if args.task=='all' else [args.task]):tasks[task]()

if __name__=='__main__':main()
