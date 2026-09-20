"""Prepare bounded new-tab Google Sheets requests from a reviewed snapshot."""
import argparse
import hashlib
import json
from pathlib import Path

SPREADSHEET='1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE'

def prepare(snapshot,output):
    if output.exists():raise ValueError('Choose a new publish directory')
    manifest=json.loads((snapshot/'manifest.json').read_text(encoding='utf-8'))
    for name,digest in manifest.items():
        if hashlib.sha256((snapshot/name).read_bytes()).hexdigest()!=digest:raise ValueError('Snapshot hash mismatch')
    d=json.loads((snapshot/'dashboard-data.json').read_text(encoding='utf-8'));s=d['summary']
    metrics=[['platform','platform_id','name','scope','followers_or_subscribers','views','likes_received','metric_time','time_basis','observed_at','source','source_url','account_url']]
    growth=[['channel_id','name','scope','source','first_date','last_date','history_points','subscribers_delta_7d','baseline_7d','subscribers_delta_30d','baseline_30d','subscribers_delta_90d','baseline_90d','views_delta_30d','views_baseline_30d','source_url','account_url']]
    for a in sorted(d['accounts'],key=lambda a:(a['platform'],a['name'].casefold())):
        m=a['metrics'];h=a['history']
        if m:
            metrics.append([a['platform'],a['platform_id'],a['name'],a['scope'],m.get('subscribers',m.get('followers')),m.get('views'),m.get('likes_received'),m.get('source_updated_at') or (m['observed_at'] if m['time_basis']=='retrieved_from_platform' else None),m['time_basis'],m['observed_at'],m['source'],m['source_url'],a['url']])
        if h:
            g=h['growth'];v=h['view_growth']['30'] or {};row=[a['platform_id'],a['name'],a['scope'],h['source'],h['first_date'],h['last_date'],h['point_count']]
            for n in ['7','30','90']:
                x=g[n] or {};row.extend([x.get('delta'),x.get('from')])
            growth.append(row+[v.get('delta'),v.get('from'),h['source_url'],a['url']])
    sources=[['source','url','access_status','reason','role','inspection_scope']]+[[r['name'],r['url'],r['status'],r.get('reason'),r['role'],r.get('inspection','Access failed')] for r in d['sources']]
    notes=[['item','value','meaning'],['snapshot',s['generated_at'],'Static snapshot; no automatic sync'],
        ['registry_personas',s['registry_personas'],'Reviewed public personas, not private people'],
        ['registry_accounts',s['registry_accounts'],'Identity source of truth remains data/registry.json'],
        ['metrics_accounts',len(metrics)-1,'Unique platform IDs including unreviewed directory scope'],
        ['history_channels',s['history_channels'],'Account-level history; not historical persona ownership'],
        ['history_points',sum(s['history_points_by_source'].values()),'Source observations; same account-day may exist in two providers'],
        ['first_history_date',s['history_first_date'],'Earliest source observation, not industry founding date'],
        ['last_history_date',s['history_last_date'],'Some accounts end earlier; see each row'],
        ['content_items',sum(s['content_unique_by_platform'].values()),'Selected content, not a full upload/stream census'],
        ['profile_claims',s['secondary_profile_claims'],'Secondary source records; cross-source duplicates are retained'],
        ['directory_only','scope label','ID/statistics reported by directory; not a reviewed VTuber persona'],
        ['registry_account_scope_unreviewed','scope label','Known registry account, persona/Thai scope not certified'],
        ['reviewed_persona_link','scope label','A reviewed link exists; its actual date range is in registry'],
        ['growth_baseline','up to 3 days before target','Each delta ends at last_date; subtract baseline date to get actual interval'],
        ['growth_source','one provider per series','Do not sum Chuy and Hub or stitch different providers'],
        ['negative_growth','retained as reported','May reflect removals/corrections, not gross views or creator decline'],
        ['blank_metric','unknown/unavailable','Never interpreted as zero'],
        ['followers_or_subscribers','platform-specific count','Do not sum into unique people or rank across platforms'],
        ['TikTok_content','embed-selected videos','Publication dates, likes and comments frequently unavailable'],
        ['Twitch_content','available archive VODs','Retention-limited; VOD views are not concurrent viewers'],
        ['affiliation_and_lifecycle','secondary claims only','No verified registry affiliations or lifecycle changes were made'],
        ['license','Internal Research / All Rights Reserved','Original creators/sources retain their rights']]
    tabs=[('ANALYTICS_METRICS',26091305,metrics,[4,5,6]),('ANALYTICS_GROWTH',26091306,growth,[6,7,9,11,13]),
          ('ANALYTICS_SOURCES',26091307,sources,[]),('ANALYTICS_NOTES',26091308,notes,[])]
    output.mkdir(parents=True);setup=[];batches=[]
    for title,sid,rows,numeric in tabs:
        width=len(rows[0]);height=len(rows);rg={'sheetId':sid,'startRowIndex':0,'endRowIndex':height,'startColumnIndex':0,'endColumnIndex':width}
        setup.extend([{'addSheet':{'properties':{'sheetId':sid,'title':title,'gridProperties':{'rowCount':height,'columnCount':width,'frozenRowCount':1,'frozenColumnCount':2}}}},
            {'repeatCell':{'range':rg,'cell':{'userEnteredFormat':{'numberFormat':{'type':'TEXT'},'wrapStrategy':'WRAP','verticalAlignment':'TOP','textFormat':{'fontFamily':'Arial','fontSize':10},'backgroundColor':{'red':1,'green':1,'blue':1}}},'fields':'userEnteredFormat'}},
            {'repeatCell':{'range':dict(rg,endRowIndex=1),'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'backgroundColor':{'red':0.94,'green':0.94,'blue':0.94}}},'fields':'userEnteredFormat.textFormat.bold,userEnteredFormat.backgroundColor'}},
            {'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':0,'endIndex':width},'properties':{'pixelSize':190},'fields':'pixelSize'}},
            {'setBasicFilter':{'filter':{'range':rg}}}])
        for col in numeric:setup.append({'repeatCell':{'range':dict(rg,startRowIndex=1,startColumnIndex=col,endColumnIndex=col+1),'cell':{'userEnteredFormat':{'numberFormat':{'type':'NUMBER','pattern':'#,##0'}}},'fields':'userEnteredFormat.numberFormat'}})
        for col in ([2,11,12] if title=='ANALYTICS_METRICS' else [1,15,16] if title=='ANALYTICS_GROWTH' else [1,5] if title=='ANALYTICS_SOURCES' else [2]):
            setup.append({'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':col,'endIndex':col+1},'properties':{'pixelSize':340},'fields':'pixelSize'}})
        # Exactly typed values; ID strings cannot be rounded by Sheets.
        for start in range(0,height,45):
            block=rows[start:start+45];values=[]
            for row in block:
                values.append({'values':[{} if v is None else {'userEnteredValue':{'numberValue':v} if type(v) in (int,float) else {'stringValue':str(v)}} for v in row]})
            request={'spreadsheet_id':SPREADSHEET,'requests':[{'updateCells':{'range':dict(rg,startRowIndex=start,endRowIndex=start+len(block)),'rows':values,'fields':'userEnteredValue'}}]}
            batches.append({'tab':title,'start':start,'end':start+len(block),'request':request})
        (output/(title+'.json')).write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
    (output/'setup.json').write_text(json.dumps({'spreadsheet_id':SPREADSHEET,'requests':setup},ensure_ascii=False),encoding='utf-8')
    jsonl_content = ''.join(json.dumps(b, ensure_ascii=False) + '\n' for b in batches)
    (output/'batches.jsonl').write_text(jsonl_content, encoding='utf-8')
    manifest = {'consolidated_file': 'batches.jsonl', 'record_count': len(batches),
                'sha256': hashlib.sha256(jsonl_content.encode('utf-8')).hexdigest(),
                'notes': 'Consolidated batch requests for Google Sheets update.'}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    plan={'spreadsheet_id':SPREADSHEET,'snapshot':str(snapshot),'tabs':[{'title':t,'sheet_id':i,'rows':len(r),'columns':len(r[0])} for t,i,r,n in tabs],
        'batches':len(batches),'max_request_bytes':max(len(json.dumps(b['request'],ensure_ascii=False).encode()) for b in batches)}
    (output/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print(json.dumps(plan))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.snapshot,a.output)
