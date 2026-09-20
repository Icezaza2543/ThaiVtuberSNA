"""Audit the supplied sources and collect selected Thai directory facts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import html
import json
import re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from registry.analytics_collect import fetch, envelope, error, write

SOURCES = [
('vdb','https://vdb.vtbs.moe/json/list.json','directory'),
('vdb GitHub','https://github.com/dd-center/vdb','directory_code'),
('vdb editor','https://submit.vtbs.moe','submission'),
('Holodex','https://holodex.net/','statistics'),
('Holodex GitHub','https://github.com/HolodexNet/Holodex','code'),
('Holodex API','https://holodex.net/api/v2/channels?type=vtuber&lang=th&limit=1','statistics'),
('HoloList Thai','https://hololist.net/category/th','directory'),
('USADA Thai','https://usadanews.com/en/countries/th/','directory'),
('Bacharu Thai','https://bacharu.io/api/vtubers?countries=th&page=1&limit=1','directory_and_statistics'),
('VTuber Fandom','https://virtualyoutuber.fandom.com/wiki/Virtual_YouTuber_Wiki','wiki'),
('Wikiru','https://vtuber-database.wikiru.jp/','wiki'),
('Oshitan','https://oshitan.com/','directory'),
('Chuy-san','https://vtuber.chuysan.com/','statistics'),
('Chuy-san API','https://storage.googleapis.com/thaivtuberranking.appspot.com/v2/channel_data/list.json','statistics'),
('Chuy-san docs','https://github.com/chuymaster/thaivtuberranking-docs','api_docs'),
('Hub VTuber Thai','https://hub.vtuberthai.com/ranking','statistics'),
('Kerlos Thai VTuber','https://github.com/kerlos/thai-vtuber','code'),
('Playboard Thai','https://playboard.co/en/youtube-ranking/most-popular-v-tuber-channels-in-thailand-daily','ranking'),
('TierMaker Thai','https://tiermaker.com/categories/youtube-and-streaming/thai-vtuber-19010542','community_list'),
('User Local','https://virtual-youtuber.userlocal.jp/document/ranking','ranking'),
('Playboard','https://playboard.co/','ranking'),
('VSTATS','https://blog.vstats.jp/','statistics_articles'),
('FlashCounts','https://flashcounts.jp/','statistics'),
('Awesome VTuber','https://github.com/sigvt/awesome-vtuber','resource_list'),
('Awesome VTuber dd-center','https://github.com/dd-center/awesome-vtuber','resource_list'),
('vtbs.moe GitHub','https://github.com/dd-center/vtbs.moe','bilibili_code'),
('Taiwan VTuber Data','https://taiwanvtuberdata.github.io/','taiwan_directory'),
('Taiwan VTuber site GitHub','https://github.com/TaiwanVtuberData/TaiwanVTuberData.github.io','code'),
('Taiwan VTuber JSON','https://github.com/TaiwanVtuberData/TaiwanVTuberTrackingDataJson','taiwan_data'),
('Virtual YouTuber API','https://github.com/Imamachi-n/Virtual-Youtuber-API','api_code'),
('VTuber Handbook','https://github.com/phantom-software-AZ/vtuber-handbook','directory_code'),
('VTuber Wiki GitHub','https://github.com/vtuberwiki/wiki','wiki_code'),
('Holodex helper','https://github.com/HolodexNet/holodex.js','api_client'),
('VTuber Tracker','https://github.com/EriEriel/VTuber-Tracker','api_client'),
('GitHub VTuber topic','https://github.com/topics/vtuber','resource_list'),
('Danbooru list','https://danbooru.donmai.us/wiki_pages/list_of_virtual_youtubers','wiki'),
('NamuWiki list','https://en.namu.wiki/w/%EB%B2%84%EC%B6%94%EC%96%BC%20%EC%9C%A0%ED%8A%9C%EB%B2%84/%EB%AA%A9%EB%A1%9D','wiki'),
('Wotaku','https://wotaku.wiki/vtuber','resource_list'),
]

def plain(text):
    return html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',text))).strip()

def audit(item):
    name,url,kind=item
    try:
        body,modified=fetch(url)
        match=re.search(r'<title[^>]*>(.*?)</title>',body,re.S|re.I)
        data={'name':name,'role':kind,'page_title':plain(match[1]) if match else None,
              'inspection':'Reachability only; success does not imply bulk data imported'}
        if name=='vdb':
            rows=json.loads(body)['vtbs'];data['records']=len(rows)
            data['thai_named_records']=sum(bool(re.search('[\u0e00-\u0e7f]',json.dumps(r.get('name',{}),ensure_ascii=False))) for r in rows)
        return envelope(url,data,modified)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        return error(url,exc)|{'name':name,'role':kind}

def profiles(output):
    found={}
    for i in range(1,10):
        url='https://hololist.net/category/th/'+(f'page/{i}/' if i>1 else '')
        body,_=fetch(url)
        for u,n in re.findall(r'<a class="[^"]*text-truncate w-100[^"]*" href="(https://hololist.net/[^"/]+/)" title="([^"]+)"',body):
            found[u]=('hololist',html.unescape(n))
    # Read only the Thai taxonomy results, not global related-profile widgets.
    for i in range(1,9):
        body,_=fetch('https://usadanews.com/en/countries/th/'+(f'?page={i}' if i>1 else ''))
        body=body.split('Related News')[0]
        for u in re.findall(r'href="(https://usadanews.com/(?:en/|ja/)?vtuber/[^"/]+/)"',body):
            found[u]=('usada','')
    def read(item):
        url,(source,name)=item
        try:
            body,modified=fetch(url);fields={}
            h=re.search(r'<h1[^>]*>(.*?)</h1>',body,re.S)
            if h:name=plain(h[1])
            if source=='hololist':
                for key in ['type','category','content','debut','retirement','affiliation','language','model']:
                    m=re.search(r'<section id="'+key+r'"[^>]*>(.*?)</section>',body,re.S)
                    if m:fields[key]=plain(re.sub(r'<h2[^>]*>.*?</h2>','',m[1],flags=re.S).split('<br>')[0])[:300]
                # Links are references from the directory, not reviewed ownership links.
                part=body.split('<h1',1)[-1].split('Related VTubers')[0]
            else:
                part=body.split('Related VTubers')[0]
                for label,value in re.findall(r'<div class="label">(.*?)</div>\s*<div class="value">(.*?)</div>',part,re.S):
                    key=plain(label)
                    if key in {'Affiliation','Debut Years','Country / Region','Platforms','Common Hashtags'}:fields[key]=plain(value)[:300]
            links=sorted(set(html.unescape(u) for u in re.findall(r'href="(https://(?:www\.)?(?:youtube\.com|twitch\.tv|tiktok\.com)/[^"<>]+)"',part)))
            return envelope(url,{'source':source,'name':name,'fields':fields,'directory_account_references':links},modified)
        except (OSError,ValueError,KeyError,TypeError) as exc:return error(url,exc)
    with ThreadPoolExecutor(max_workers=4) as pool:write(output/'directory-facts.jsonl',pool.map(read,found.items()))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    with ThreadPoolExecutor(max_workers=4) as pool:write(args.output/'source-audit.jsonl',pool.map(audit,SOURCES))
    profiles(args.output)
