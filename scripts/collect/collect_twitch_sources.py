"""Collect public directory leads; no directory entry constitutes verification."""
import json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
DAY = '2026-09-13'

def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as r:
        body = r.read(16_000_001)
    if len(body) > 16_000_000:
        raise ValueError('Response size limit')
    return body.decode('utf-8')

def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values(): yield from walk(v)
    elif isinstance(x, list):
        for v in x: yield from walk(v)

def flight_objects(body):
    parts = []
    for m in re.finditer(r'self\.__next_f\.push\((.*?)\)</script>', body, re.S):
        try:
            x = json.loads(m[1])
            if len(x) > 1 and isinstance(x[1], str): parts.append(x[1])
        except ValueError: pass
    for line in ''.join(parts).split('\n'):
        try: yield from walk(json.loads(line.split(':', 1)[1]))
        except (ValueError, IndexError): pass

def main():
    queue = {}
    audit = []
    timestamp = datetime.now(timezone.utc).isoformat()
    def add(handle, source, name='', known_id=None, youtube_ids=None, thai_directory=False):
        handle = str(handle).lower().strip()
        if not re.fullmatch(r'[a-z0-9_]{1,25}', handle) or handle in {'directory','videos','downloads','settings','subscriptions','p','products','team','teams'}: return
        row = queue.setdefault(handle, {'url': 'https://www.twitch.tv/' + handle, 'handle': handle, 'sources': []})
        s = {'url': source, 'name': name, 'kind': 'secondary_source', 'observed_at': timestamp,
             'claimed_user_id': str(known_id) if known_id else None, 'youtube_ids': youtube_ids or [], 'thai_directory': thai_directory}
        if s not in row['sources']: row['sources'].append(s)
    url = 'https://vtuberthaiinfo-archive.pages.dev/talent'
    records = [r for r in flight_objects(fetch(url)) if 'twitchMain' in r]
    for r in records:
        t = r.get('twitchMain')
        if t:
            y = r.get('youtubeMain') or {}
            add(t.get('username'), url + '/' + r['slug'], r.get('name',''), t.get('channelId'), [y['channelId']] if y.get('channelId') else [], True)
    audit.append({'source_url': url, 'records_read': len(records), 'twitch_entries': sum(bool(r.get('twitchMain')) for r in records)})
    url = 'https://vdb.vtbs.moe/json/list.json'
    records = json.loads(fetch(url))['vtbs']
    n = 0
    for r in records:
        accounts = r.get('accounts', [])
        youtube_ids = [a['id'] for a in accounts if a.get('platform') == 'youtube']
        for a in accounts:
            if a.get('platform') == 'twitch':
                n += 1
                names = r.get('name', {})
                name = names.get(names.get('default',''), '')
                add(a['id'], url, name, youtube_ids=youtube_ids)
    audit.append({'source_url': url, 'records_read': len(records), 'twitch_entries': n})
    url = 'https://storage.googleapis.com/thaivtuberranking.appspot.com/v2/channel_data/list.json'
    records = json.loads(fetch(url))['result']
    n = 0
    youtube = {}
    for r in records:
        cid = r.get('channel_id')
        if re.fullmatch(r'UC[A-Za-z0-9_-]{22}', cid or ''):
            youtube[cid] = {'url': 'https://www.youtube.com/channel/' + cid, 'platform_id': cid, 'name': r.get('title',''), 'retain_description': True}
        for h in re.findall(r'(?:www\.)?twitch\.tv/([A-Za-z0-9_]+)', r.get('description','')):
            add(h, url, r.get('title',''), youtube_ids=[cid] if cid else [], thai_directory=True); n += 1
    audit.append({'source_url': url, 'records_read': len(records), 'twitch_links': n})
    registry = json.loads((ROOT/'data/registry.json').read_text(encoding='utf-8'))['tables']
    for a in registry['accounts']:
        if a['platform'] == 'youtube':
            youtube.setdefault(a['platform_id'], {'url': a['url'], 'platform_id': a['platform_id'], 'name': a['name'], 'retain_description': True})
    # Previously retained first-party descriptions provide leads with original provenance.
    for p in (ROOT/'intake').glob('*.jsonl'):
        if not ('tiktok-public-profiles' in p.name or 'youtube-persona-evidence' in p.name): continue
        for line in p.open(encoding='utf-8'):
            r = json.loads(line)
            text = r.get('bio','') + '\n' + r.get('description','')
            for h in re.findall(r'(?:www\.)?twitch\.tv/([A-Za-z0-9_]+)', unquote(text)):
                add(h, r['source_url'], r.get('name',''), youtube_ids=[r['youtube_channel_id']] if r.get('youtube_channel_id') else [], thai_directory=True)
    for name, value in [('twitch-source-queue.json', list(queue.values())), ('twitch-source-audit.json', audit), ('twitch-youtube-queue.json', list(youtube.values()))]:
        with (ROOT/'intake'/f'{DAY}-{name}').open('x',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,indent=2)
    print(json.dumps({'sources': audit, 'unique_twitch_handles':len(queue), 'youtube_owner_pages':len(youtube)}),flush=True)

if __name__ == '__main__': main()
