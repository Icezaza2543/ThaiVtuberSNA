"""Build and validate analytics snapshots without changing registry identity claims."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import gzip
import hashlib
import json
from pathlib import Path
import re

from .store import ROOT, load, utc_timestamp
from .analytics_collect import number, now

def read(path):
    op = gzip.open if path.suffix=='.gz' else open
    with op(path,'rt',encoding='utf-8') as stream:
        for line in stream:yield json.loads(line)

def timestamp(value):
    if value is None:return None
    try:
        if isinstance(value,(int,float)):
            return datetime.fromtimestamp(value/1000,timezone.utc).isoformat()
        return utc_timestamp(value).isoformat()
    except (ValueError,TypeError,OverflowError):
        try:
            parsed=parsedate_to_datetime(value)
            return parsed.isoformat() if parsed.utcoffset() is not None else None
        except (ValueError,TypeError,OverflowError):return None

def valid_day(value):
    try:return date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:return None

def csv_write(path,rows,fields):
    op=gzip.open if path.suffix=='.gz' else open
    with op(path,'xt',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:
            # Safe when opened in Excel; JSON retains the exact text.
            w.writerow({k: ("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v)
                        for k,v in ((k,r.get(k)) for k in fields)})

def growth(points,days,metric='subscribers'):
    usable=sorted((p for p in points if valid_day(p.get('date')) and number(p.get(metric)) is not None),key=lambda p:p['date'])
    if not usable:return None
    last=usable[-1]; target=date.fromisoformat(last['date'])-timedelta(days=days)
    before=[p for p in usable if date.fromisoformat(p['date'])<=target]
    if not before:return None
    first=before[-1]
    if (target-date.fromisoformat(first['date'])).days>3:return None
    delta=last[metric]-first[metric]
    return {'delta':delta,'percent':None if first[metric]==0 else round(delta/first[metric]*100,3),
            'from':first['date'],'to':last['date'],'days':(date.fromisoformat(last['date'])-date.fromisoformat(first['date'])).days}

def validate_inputs(input_dir,review):
    if review.get('type')!='analytics_snapshot_review' or not review.get('reviewer'):
        raise ValueError('A reviewed analytics change file is required')
    utc_timestamp(review['reviewed_at'])
    seen=set()
    for item in review['files']:
        name=item['name']
        if Path(name).name!=name or name in seen:raise ValueError('Invalid or duplicate source path')
        seen.add(name);path=input_dir/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Reviewed source changed: '+name)
        for row in read(path):
            utc_timestamp(row['observed_at'])
            if utc_timestamp(row['observed_at'])>utc_timestamp(review['reviewed_at']):
                raise ValueError('Review predates source collection')
            if row['status']=='ok':
                actual=hashlib.sha256(json.dumps(row['data'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                if actual!=row['retained_sha256']:raise ValueError('Source record hash mismatch: '+name)
    return seen

def build(input_dir,output,review_path):
    review=json.loads(review_path.read_text(encoding='utf-8'));files=validate_inputs(input_dir,review)
    if output.exists():raise ValueError('Choose a new snapshot directory')
    if review.get('registry_sha256')!=hashlib.sha256((ROOT/'data/registry.json').read_bytes()).hexdigest():
        raise ValueError('Registry differs from reviewed analytics input')
    db=load(ROOT/'data/registry.json');db.close()
    registry=json.loads((ROOT/'data/registry.json').read_text(encoding='utf-8'))['tables']
    output.mkdir(parents=True)
    by_id={r['id']:r for r in registry['accounts']}
    reviewed=defaultdict(set)
    for link in registry['account_links']:
        if link['review_status']=='verified':reviewed[link['account_id']].add(link['persona_id'])
    catalog={}
    for a in registry['accounts']:
        key=a['platform']+':'+a['platform_id']
        catalog[key]={'key':key,'platform':a['platform'],'platform_id':a['platform_id'],'name':a['name'],'url':a['url'],
            'registry_account_id':a['id'],'scope':'reviewed_persona_link' if reviewed[a['id']] else 'registry_account_scope_unreviewed',
            'persona_ids':sorted(reviewed[a['id']]),'persona_link_dates_note':'See registry: links are date bounded, not historical ownership'}
    snapshots=[];contents={};facts=[];audits=[];errors=[]
    def source_rows(name):
        for r in read(input_dir/name):
            if r['status']=='ok':yield r
            else:errors.append({'file':name,**r})
    def account(cid,name=''):
        if not re.fullmatch(r'UC[A-Za-z0-9_-]{22}',str(cid or '')):return None
        key='youtube:'+cid
        catalog.setdefault(key,{'key':key,'platform':'youtube','platform_id':cid,'name':name,'url':'https://www.youtube.com/channel/'+cid,
                               'registry_account_id':None,'scope':'directory_only','persona_ids':[]})
        return key
    def metric(key,source,row,values,updated=None):
        if not key:return
        snapshots.append({'key':key,'source':source,'source_url':row['source_url'],'observed_at':row['observed_at'],
            'source_updated_at':updated,'time_basis':'source_updated' if updated else ('retrieved_from_platform' if source in {'tiktok','twitch'} else 'source_time_unknown'),
            **{k:number(v) for k,v in values.items()}})
    def content(key,platform,vid,source,row,**values):
        if not key or not vid:return
        identity=(platform,str(vid),source)
        url={'twitch':'https://www.twitch.tv/videos/','youtube':'https://www.youtube.com/watch?v='}.get(platform,'')+str(vid)
        if platform=='tiktok':url=catalog[key]['url']+'/video/'+str(vid)
        record={'key':key,'platform':platform,'content_id':str(vid),'source':source,'source_url':row['source_url'],
            'observed_at':row['observed_at'],'source_updated_at':timestamp(row.get('http_last_modified')),
            'url':url,**values}
        prior=contents.get(identity)
        if prior and prior['key']!=key:raise ValueError('Conflicting content account')
        if not prior or record['observed_at']>prior['observed_at']:contents[identity]=record
    for r in source_rows('chuy-channels.jsonl'):
        for d in r['data']:
            key=account(d['channel_id'],d['title'])
            metric(key,'chuy',r,{'subscribers':d['subscribers'],'views':d['views'],'videos':d['videos']},timestamp(d['updated_at']))
            if key:catalog[key]['source_last_published_at']=timestamp(d.get('last_published_video_at'))
    for r in source_rows('hub-channels.jsonl'):
        for d in r['data']:
            key=account(d['youtubeChannelId'],d['name'])
            metric(key,'hub',r,{'subscribers':d['subscribers'],'views':d['channelViews']})
            facts.append({'source':'hub','source_entity_id':d['id'],'name':d['name'],'key':key,'observed_at':r['observed_at'],
                'source_url':'https://hub.vtuberthai.com/vtuber/'+d['id'],'review_status':'secondary_source_claim',
                'agency':d['agency'],'genres':d['tags'],'debut':d['debutDate'],'status':d['status']})
    for source in ['tiktok','twitch']:
        for r in source_rows(source+'.jsonl'):
            d=r['data'];a=by_id[d['account_id']]
            if a['platform']!=source or a['platform_id']!=d['platform_id']:raise ValueError('Stable ID mismatch')
            key=source+':'+d['platform_id']
            metric(key,source,r,{'followers':d['followers'],'likes_received':d.get('likes_received')})
            for v in d['videos']:
                pub=timestamp(v.get('published_at'))
                if source=='tiktok' and v.get('create_time') is not None:
                    raw=v['create_time'];pub=timestamp(raw*1000) if isinstance(raw,(int,float)) else None
                content(key,source,v['id'],source,r,title=v['title'],published_at=pub,
                    duration_seconds=v.get('duration_seconds'),views=v.get('views'),likes=v.get('likes'),comments=v.get('comments'),
                    content_type='vod' if source=='twitch' else 'video',
                    coverage='available_archive_vods' if source=='twitch' else 'embed_selected_videos')
            if d.get('live'):
                live=d['live'];catalog[key]['live_at_observation']={'observed_at':r['observed_at'],**live}
    for r in source_rows('chuy-content.jsonl'):
        for d in r['data']:
            key=account(d['channel_id'])
            content(key,'youtube',d['id'],'chuy',r,title=d['title'],published_at=timestamp(d['published_at']),
                views=number(d.get('view_count')),likes=None,comments=None,duration_seconds=None,
                content_type='scheduled' if d.get('live_status')==2 else ('live' if d.get('live_status')==1 else 'video'),
                coverage='source_ranking_selection_not_all_uploads')
    for r in source_rows('bacharu.jsonl'):
        for d in r['data']:
            facts.append({'source':'bacharu','source_entity_id':d['canonicalName'],'name':d['name'],
                'source_url':'https://bacharu.io/vtuber/'+d['canonicalName'],'observed_at':r['observed_at'],
                'review_status':'secondary_source_claim','groups':d['groups'],'genres':d['genres'],
                'debut':d['debut'],'graduation':d['graduationDate'],'status':d['status'],'references':d['social']})
    directory_facts={}
    for name in ['directory-facts.jsonl','directory-facts-retry.jsonl']:
        if name not in files:continue
        for r in source_rows(name):
            directory_facts[r['source_url']]={**r['data'],'source_url':r['source_url'],'observed_at':r['observed_at'],'review_status':'secondary_source_claim'}
    facts.extend(directory_facts.values())
    for r in read(input_dir/'source-audit.jsonl'):
        audits.append({'url':r['source_url'],'status':r['status'],'reason':r.get('reason'),
                       **(r.get('data') or {'name':r['name'],'role':r['role']})})
    # Keep source time series separate; never stitch different providers into a growth curve.
    histories={};hcounts=Counter();bounds=[];hfields=['key','source','date','captured_at','subscribers','views','videos','observed_at','source_url']
    history_path=output/'history.csv.gz'
    with gzip.open(history_path,'xt',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=hfields);writer.writeheader()
        for name in ['chuy-history.jsonl.gz','hub-history.jsonl.gz','hub-history-retry.jsonl.gz']:
            if name not in files:continue
            source='chuy' if name.startswith('chuy') else 'hub'
            for r in source_rows(name):
                d=r['data'];key=account(d['channel_id'])
                if not key:continue
                points={}
                for p in d['points']:
                    day=valid_day(p.get('date') if source=='chuy' else p.get('capturedAt'))
                    if not day:continue
                    if day>r['observed_at'][:10]:raise ValueError('Future history point')
                    point={'date':day,'captured_at':timestamp(p.get('capturedAt')),'subscribers':number(p.get('subscribers')),
                           'views':number(p.get('views')),'videos':number(p.get('videos'))}
                    if day in points and points[day]!=point:raise ValueError('Conflicting same-day source points')
                    points[day]=point
                if (key,source) in histories:raise ValueError('Duplicate successful history source')
                pts=sorted(points.values(),key=lambda p:p['date'])
                if not pts:continue
                if source=='hub':
                    metric(key,'hub_history',r,{'subscribers':pts[-1]['subscribers'],'views':pts[-1]['views']},pts[-1]['captured_at'])
                for p in pts:writer.writerow({'key':key,'source':source,**p,'observed_at':r['observed_at'],'source_url':r['source_url']})
                hcounts[source]+=len(pts);bounds.extend([pts[0]['date'],pts[-1]['date']])
                # Display all last 90 daily points and earlier month-end observations.
                monthly={}
                for p in pts[:-90]:monthly[p['date'][:7]]=p
                histories[(key,source)]={'source':source,'source_url':r['source_url'],'point_count':len(pts),
                    'first_date':pts[0]['date'],'last_date':pts[-1]['date'],
                    'points':list(monthly.values())+pts[-90:],
                    'growth':{str(n):growth(pts,n) for n in [7,30,90]},
                    'view_growth':{str(n):growth(pts,n,'views') for n in [7,30,90]}}
    by_key=defaultdict(list)
    for s in snapshots:by_key[s['key']].append(s)
    # Known dated Chuy snapshot is preferred to undated Hub values; all observations exported.
    for key,a in catalog.items():
        options=by_key[key]
        options.sort(key=lambda s:({'tiktok':3,'twitch':3,'chuy':2,'hub_history':1,'hub':0}[s['source']],s['observed_at']))
        a['metrics']=options[-1] if options else None
        series=histories.get((key,'chuy')) or histories.get((key,'hub'))
        a['history']=series
        if a['metrics']:
            stamp=a['metrics'].get('source_updated_at') or (a['metrics']['observed_at'] if a['metrics']['time_basis']=='retrieved_from_platform' else None)
            a['metrics_age_days']=None if not stamp else (date.fromisoformat(review['reviewed_at'][:10])-date.fromisoformat(stamp[:10])).days
    counts=Counter(a['platform'] for a in catalog.values() if a['metrics'])
    unique_content=Counter(p for p,v in {(r['platform'],r['content_id']) for r in contents.values()})
    summary={'generated_at':now(),'registry_accounts':len(registry['accounts']),'registry_personas':len(registry['personas']),
        'analytics_accounts':len(catalog),'accounts_with_metrics':dict(counts),'metric_observations':len(snapshots),
        'history_points_by_source':dict(hcounts),'history_channels':len({k for k,s in histories}),
        'history_first_date':min(bounds) if bounds else None,'history_last_date':max(bounds) if bounds else None,
        'content_unique_by_platform':dict(unique_content),'content_observations':len(contents),'secondary_profile_claims':len(facts),
        'source_audit':dict(Counter(r['status'] for r in audits)),
        'request_errors_recorded':dict(Counter(r['reason'] for r in errors)),
        'notes':['Accounts are not personas or unique viewers. Scope includes unreviewed directory accounts.',
                 'History describes accounts, not historical persona ownership. Growth uses one source and actual baseline dates.',
                 'TikTok embed is a selected video sample with unknown publication dates; Twitch archives depend on retention.',
                 'Source-reported affiliations/debuts/status remain secondary claims, not reviewed registry events.',
                 'Zero is preserved where reported; unavailable counts are null. YouTube ranking engagement fields are not used.',
                 'Historical cumulative count changes may be negative after removals/corrections and are not gross daily viewership.']}
    snapshot={'schema_version':1,'summary':summary,'accounts':list(catalog.values()),'contents':list(contents.values()),'facts':facts,'sources':audits}
    (output/'dashboard-data.json').write_text(json.dumps(snapshot,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    csv_write(output/'metric-observations.csv',snapshots,['key','source','source_updated_at','observed_at','time_basis','subscribers','followers','views','videos','likes_received','source_url'])
    csv_write(output/'content.csv',contents.values(),['key','platform','content_id','title','content_type','published_at','views','duration_seconds','likes','comments','coverage','source','observed_at','source_url','url'])
    latest=[]
    for a in catalog.values():
        m=a['metrics'] or {};h=a['history'] or {};g=h.get('growth',{}).get('30') or {}
        latest.append({'platform':a['platform'],'platform_id':a['platform_id'],'name':a['name'],'scope':a['scope'],
            'followers_or_subscribers':m.get('subscribers',m.get('followers')),'views':m.get('views'),
            'likes_received':m.get('likes_received'),'source':m.get('source'),'source_updated_at':m.get('source_updated_at'),
            'observed_at':m.get('observed_at'),'growth_30d':g.get('delta'),'growth_from':g.get('from'),
            'growth_to':g.get('to'),'growth_source':h.get('source'),'source_url':m.get('source_url'),'url':a['url']})
    csv_write(output/'accounts-latest.csv',latest,list(latest[0]))
    (output/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    template=(ROOT/'registry/analytics_dashboard.html').read_text(encoding='utf-8')
    embedded=json.dumps(snapshot,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    (output/'dashboard.html').write_text(template.replace('__DATA__',embedded),encoding='utf-8')
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--review',type=Path,required=True)
    args=p.parse_args(argv);build(args.input,args.output,args.review)

if __name__=='__main__':main()
