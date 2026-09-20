"""Materialize this round's explicitly inspected decisions into a change file.

This is a dated review record generator, not an automatic verification policy.
"""
import hashlib,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from registry.store import uid

ROOT=Path(__file__).resolve().parents[2]
DAY='2026-09-13'
REVIEWER='codex:public-persona-review'

def main():
    ds=json.loads((ROOT/'intake'/f'{DAY}-twitch-review-dossiers.json').read_text(encoding='utf-8'))
    inspected=[d for d in ds if d['scope_matches'] or d['existing_persona_links']]
    selection_hash=hashlib.sha256('\n'.join(d['handle'] for d in inspected).encode()).hexdigest()
    if selection_hash!='e397534187a4246fedb867316e58867e7fc6a419ffb8466378ff6811326171f7':raise ValueError('Review selection changed; re-review before materializing')
    deferred={6,11,20,27,32,34,38,45,47,48,57,61,62,65,66,75,76,79,82,85,87,91,92,100,109,110,115,125,126,142,149,158,163,171,172,180,193,195,200,201,221,225,229,236,247,249,257,259,261,262,264,267,269}
    excluded={'ichika_vt','izosaki','milisvt','nikkayz','unnamednow00'}
    decisions={};timestamp=datetime.now(timezone.utc).isoformat()
    for i,d in enumerate(inspected):
        if i in deferred:continue
        matches=d['scope_matches']
        selected=matches[1] if d['handle'] in {'gintheyuk','torithaiga'} else (matches[0] if matches else None)
        if d['handle']=='julius_kosmolatria':
            selected={'kind':'twitch_bio','url':d['profile']['source_url'],'excerpt':d['bio']}
        decisions[d['handle']]={'status':'verified','scope_evidence':selected,'existing_persona_links':d['existing_persona_links']}
    change={k:[] for k in ['evidence','personas','accounts','account_links','lifecycle_events','discovery_runs','discovery_hits']}
    owner_observed={r['source_url']:r['observed_at'] for r in (json.loads(line) for line in (ROOT/'intake'/f'{DAY}-twitch-youtube-owner-evidence.jsonl').open(encoding='utf-8'))}
    evid={};rid=uid('run',DAY+':twitch:public-directory-and-owner-profiles')
    change['discovery_runs'].append(dict(id=rid,platform='twitch',method='manual_search',query='Thai directories + vdb + Thai ranking + HoloList + Bacharu + owner crosslinks; 730 handles and 63 historical numeric ID lookups; public Twitch profile queries',observed_at=timestamp,stop_reason='manual_batch',pages=41,records_seen=793))
    def ev(url,kind,observed,summary,checksum=None,key=''):
        if kind=='self_statement' and url in owner_observed:observed=owner_observed[url]
        eid=uid('ev',DAY+':twitch:'+url+':'+key)
        evid[eid]=dict(id=eid,url=url,kind=kind,observed_at=observed,published_on=None,sha256=checksum,summary=summary)
        return eid
    review=[];source_runs={}
    for d in ds:
        r=d['profile'];h=r['handle'];decision=decisions.get(h)
        if h in excluded:
            review.append({'handle':h,'decision':'exclude_from_thai_intake','reason':'First-party Thai relevance not established; incidental language/topic/directory hit.'});continue
        aid=uid('acct','twitch:user_id:'+r['platform_id'])
        ae=ev(r['source_url'],'official_profile',r['observed_at'],f'Public Twitch profile returned numeric user_id {r["platform_id"]} and current login {h}. This establishes account existence at observation, not virtual scope or activity. Public retained fields in intake/2026-09-13-twitch-public-profiles*.jsonl.',r['public_profile_sha256'],'account')
        change['accounts'].append(dict(id=aid,platform='twitch',platform_id=r['platform_id'],id_namespace='user_id',handle=h,name=r['name'],url=r['url'],first_discovered_at=r['observed_at'],evidence_id=ae))
        change['discovery_hits'].append(dict(id=uid('hit',rid+aid),run_id=rid,account_id=aid,candidate_id=None,evidence_id=ae))
        for source in r['sources']:
            se=ev(source['url'],source.get('kind','secondary_source'),source.get('observed_at') or timestamp,'Discovery provenance only; no identity, nationality, virtual scope or lifecycle is adopted from directory labels.',key='source')
            srid=uid('run',DAY+':twitch:source:'+source['url'])
            run=source_runs.setdefault(srid,dict(id=srid,platform='twitch',method='official_crosslink' if source.get('kind')=='self_statement' else 'manual_search',query='Retained source reference: '+source['url'],observed_at=source.get('observed_at') or timestamp,stop_reason='manual_batch',pages=0,records_seen=0))
            run['records_seen']+=1
            change['discovery_hits'].append(dict(id=uid('hit',srid+aid),run_id=srid,account_id=aid,candidate_id=None,evidence_id=se))
        if not decision:
            reason='Account ID confirmed; no unambiguous reviewed first-party virtual-persona/Thai scope combination.'
            if h in {'alancreation','floravtuberth'}:reason='Manager/project account: not counted as an individual virtual persona.'
            if h in {'estelle_wil','zuruya_kirari'}:reason='Owner states a transition away from VTuber; conflicting/historical virtual labels retained for later lifecycle review.'
            review.append({'handle':h,'platform_id':r['platform_id'],'decision':'account_only','reason':reason});continue
        existing=decision['existing_persona_links'];scope=decision['scope_evidence']
        pids={x['persona_id'] for x in existing}
        if len(pids)>1:raise ValueError('Ambiguous persona link')
        if pids:
            pid=next(iter(pids));link=existing[0]
            le=ev(link['evidence_url'],'official_profile' if link['kind']=='twitch_social' else 'self_statement',r['observed_at'],f'Owner-controlled {link["kind"]} directly links {link["target_url"]}. Reviewed connection to existing public persona {pid}; not a private-person identity or undisclosed continuity claim.',key='link:'+aid)
        else:
            if not scope:raise ValueError('Missing reviewed scope')
            pid=uid('persona','twitch:user_id:'+r['platform_id'])
            excerpt=scope['excerpt']
            relation='thai_language'
            if r['broadcast_language']!='TH' and not re.search('[ก-๙]',excerpt) and not re.search(r'\bTH\b|Thai|Thailand',excerpt,re.I):raise ValueError('Thai scope needs explicit review: '+h)
            # Review summaries retain a short scope excerpt; profile source keeps full provenance.
            se=ev(scope['url'],'self_statement',r['observed_at'],f'Reviewed owner {scope["kind"]}: '+excerpt[:180]+f' | Thai-language scope supported by public Twitch broadcast language {r["broadcast_language"]} and/or the cited self-introduction. No activity/debut date is inferred.',key='scope:'+aid)
            fmt={'samuel1571':'3d','huntapng':'png','jisooman18':'png','sunraindre':'png'}.get(h,'unknown')
            change['personas'].append(dict(id=pid,name=r['name'],format=fmt,roles='["streamer"]',thai_relation=relation,review_status='verified',evidence_id=se,reviewer=REVIEWER,reviewed_at=timestamp))
            le=se if scope['kind']=='youtube_owner' else ae
        change['account_links'].append(dict(id=uid('link',aid+pid+DAY),account_id=aid,persona_id=pid,valid_from=DAY,valid_to=DAY,evidence_id=le,review_status='verified',reviewer=REVIEWER,reviewed_at=timestamp))
        review.append({'handle':h,'platform_id':r['platform_id'],'decision':'verified_persona_account','persona_id':pid,'scope_evidence':scope,'existing_persona_links':existing,'reviewer':REVIEWER,'reviewed_at':timestamp})
        if h=='rheaataraxia':
            ee=ev(r['source_url'],'self_statement',r['observed_at'],'Owner bio explicitly states: "Graduated 31 May 2025". Event date is day precision; the 2026 observation does not establish a return.',key='graduation')
            change['lifecycle_events'].append(dict(id=uid('event',pid+':graduation:2025-05-31'),persona_id=pid,event_type='graduation',event_date='2025-05-31',date_precision='day',evidence_id=ee,review_status='verified',reviewer=REVIEWER,reviewed_at=timestamp,note='Dated graduation statement in public Twitch bio.'))
    change['evidence']=list(evid.values())
    change['discovery_runs'].extend(source_runs.values())
    (ROOT/'reviews'/f'{DAY}-twitch-01.json').write_text(json.dumps(change,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'intake'/f'{DAY}-twitch-review-decisions.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:len(v) for k,v in change.items()}))

if __name__=='__main__':main()
