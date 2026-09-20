"""Read owner-written About metadata for each known channel; no visitor records."""
import gzip,json,re,threading
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.request import Request,urlopen
from urllib.parse import unquote,urlparse,parse_qs
from urllib.error import HTTPError

root=Path(__file__).resolve().parents[2]
stop=threading.Event()
def find(x,key):
 if isinstance(x,dict):
  if key in x:yield x[key]
  for v in x.values():yield from find(v,key)
 elif isinstance(x,list):
  for v in x:yield from find(v,key)
def fetch(channel):
 url=channel['url'].rstrip('/')+'/about'
 result={'source_url':url,'youtube_channel_id':channel.get('platform_id'),'name':channel['name'],'observed_at':datetime.now(timezone.utc).isoformat()}
 if stop.is_set():return dict(result,error='stopped_after_rate_limit')
 try:
  with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'gzip'}),timeout=25) as response:
   body=response.read(4000000)
   if response.headers.get('Content-Encoding')=='gzip':body=gzip.decompress(body)
  text=body.decode('utf-8');match=re.search(r'var ytInitialData\s*=\s*',text)
  if not match:raise ValueError('No channel metadata')
  data,_=json.JSONDecoder().raw_decode(text[match.end():])
  metadata=list(find(data,'channelMetadataRenderer'))
  if len(metadata)!=1 or (channel.get('platform_id') and metadata[0].get('externalId')!=channel['platform_id']):raise ValueError('Channel ID mismatch')
  identifier=metadata[0].get('externalId','')
  if not re.fullmatch(r'UC[A-Za-z0-9_-]{22}',identifier):raise ValueError('Channel ID absent')
  result['youtube_channel_id']=identifier
  result['current_name']=metadata[0].get('title','')
  if channel.get('retain_description'):
   description=metadata[0].get('description','')
   description=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','[contact omitted]',description)
   description=re.sub(r'(?<!\w)(?:\+66|0)[ -]?[0-9](?:[ -]?[0-9]){7,8}(?!\w)','[contact omitted]',description)
   description=re.split(r'top\s*donat|special thanks|รายชื่อผู้(?:โดเนท|บริจาค)',description,flags=re.I)[0]
   result['description']=description[:1500]
  owner_sections=[metadata[0].get('description','')]
  for about in find(data,'aboutChannelViewModel'):
   if about.get('channelId')==identifier:
    owner_sections.extend([about.get('description',''),about.get('links',[])])
  owner_sections+=list(find(data.get('header',{}),'channelHeaderLinksRenderer'))
  owner_sections+=list(find(data.get('header',{}),'attributionViewModel'))
  owner_text=unquote(json.dumps(owner_sections,ensure_ascii=False).replace('\\/','/'))
  urls=set(re.findall(r'https?://[^\s<>"\\]+',owner_text))
  tiktok=set(re.findall(r'https?://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+',owner_text))
  hubs={u for u in urls if urlparse(u).hostname in {'linktr.ee','lit.link','solo.to','bio.site','beacons.ai','linkbio.co','linkbio.in','tipme.in.th','tipjai.com','easydonate.app'}}
  twitch=set(re.findall(r'https?://(?:www\.)?twitch\.tv/[A-Za-z0-9_]+',owner_text))
  x_urls=set()
  for raw in re.findall(r'https?://(?:www\.|mobile\.)?(?:twitter|x)\.com/[A-Za-z0-9_]+', owner_text):
    handle=urlparse(raw).path.strip('/').split('/')[0]
    if handle and handle.lower() not in {'i','intent','share','home','explore','search','login','signup','about'}:
      x_urls.add('https://x.com/'+handle)
  result.update(tiktok_urls=sorted(tiktok),twitch_urls=sorted(twitch),x_urls=sorted(x_urls),creator_links=sorted(hubs),status='read')
 except HTTPError as e:
  result.update(error='HTTPError',http_status=e.code)
  if e.code==429:stop.set()
 except Exception as e:result['error']=type(e).__name__
 return result
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path);parser.add_argument('--output',type=Path,default=root/'intake/2026-09-13-youtube-owner-crosslinks.jsonl');args=parser.parse_args()
 if args.input:channels=json.loads(args.input.read_text(encoding='utf-8'))
 else:channels=[r for r in json.loads((root/'data/registry.json').read_text(encoding='utf-8'))['tables']['accounts'] if r['platform']=='youtube']
 print(json.dumps({'requested':len(channels)}),flush=True)
 with args.output.open('x',encoding='utf-8') as stream,ThreadPoolExecutor(max_workers=6) as pool:
  futures={pool.submit(fetch,c):c for c in channels}
  n=0; linked=0; errors=0
  for future in as_completed(futures):
   r=future.result();n+=1;linked+=bool(r.get('tiktok_urls'));errors+='error' in r
   stream.write(json.dumps(r,ensure_ascii=False)+'\n');stream.flush()
   if n%100==0:print(json.dumps({'read':n,'channels_with_tiktok':linked,'errors':errors}),flush=True)
 print(json.dumps({'read':n,'channels_with_tiktok':linked,'errors':errors}),flush=True)
