"""Process acknowledged campaign data without any YouTube transport.

Only private workbook reads are live. Private analytics stays in RAM with DuckDB
spill disabled. Outputs are local, versioned aggregate previews and review signals.
"""
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3

ROOT = Path('scratch/expanded-v1-campaign')
IDENTITY = re.compile(r're[ -]?debut|debut|初配信|初放送|เดบิว[ตต์]*|เปิดตัว(?:โมเดล)?|model\s*reveal|live\s*2d|png\s*tuber|vtuber(?:th)?|thai\s*vtuber|新モデル|新衣装|rebrand', re.I)
DEBUT = re.compile(r'debut|初配信|初放送|เดบิว|เปิดตัว|reveal|新モデル|rebrand', re.I)
ROLE = re.compile(r'png\s*tuber|v[ -]?artist|v[ -]?singer|v[ -]?rigger|virtual\s*(?:singer|artist)|live\s*2d|rigger|rigging|illustrator|modell?er|นักวาด|วาดโมเดล|(?<![ก-๙])ริก(?:เกอร์)?(?![ก-๙])|คนวาด|คนริก|イラスト|モデリング', re.I)


def ro(path):
    return sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True)


def write_json(path, obj):
    from core.data_security import assert_public
    assert_public(obj)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def write_csv(path, rows, fields):
    with path.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def ordered_remaining(records, existing):
    """Exact dates first; unseen years first, then stable chronological deepening."""
    used={r['video'] for r in existing}
    years={r['year'] for r in existing}
    candidates=sorted((r for r in records if r['video_id'] not in used),
                      key=lambda r:(not bool(r.get('video_published_at')),r.get('video_published_at') or '',r['video_id']))
    representatives=[]; rest=[]
    for row in candidates:
        year=(row.get('video_published_at') or 'unknown')[:4]
        if year not in years:
            representatives.append(row); years.add(year)
        else: rest.append(row)
    return sorted(representatives+rest,key=lambda r:not bool(r.get('video_published_at')))


def catalog_processing(root, out):
    con=ro(root/'catalog.sqlite3')
    states={cid:json.loads(s) for cid,s in con.execute('SELECT id,state FROM channels')}
    errors={cid:(attempts,reason) for cid,attempts,reason in con.execute('SELECT channel,attempts,reason FROM campaign_errors')}
    inactive=dict(con.execute('SELECT channel,COUNT(*) FROM unavailable GROUP BY channel'))
    jobs=ro(root/'interaction_queue.sqlite3'); jobs.row_factory=sqlite3.Row
    existing=defaultdict(list)
    for row in jobs.execute('SELECT * FROM jobs'): existing[row['channel']].append(dict(row))
    summary=[]; yearly=[]; candidates=[]; roles=[]; pending=[]; resume=[]
    years_total=Counter(); triage=Counter(); earliest=[]
    for cid in sorted(states):
        records=[json.loads(r[0]) for r in con.execute('SELECT metadata FROM videos WHERE channel=?',(cid,))]
        records.sort(key=lambda r:(r.get('video_published_at') or '9999',r['video_id']))
        dates=[r['video_published_at'] for r in records if r.get('video_published_at')]
        ys=Counter((r.get('video_published_at') or 'unknown')[:4] for r in records)
        for year,n in sorted(ys.items()):
            yearly.append(dict(channel_id=cid,year=year,video_count=n)); years_total[year]+=n
        state=states[cid]; err=errors.get(cid)
        category=('NOT_FOUND' if err and err[1]=='NOT_FOUND' else
                  'TRANSIENT_HTTP' if err and err[1] in {'HTTP_ERROR','TRANSPORT_ERROR'} else
                  'PENDING_PAGINATION' if state['catalog_status']=='PENDING' and state.get('token') else
                  'TERMINAL' if state['catalog_status'] in {'CAP_REACHED','PLAYLIST_EXHAUSTED'} else 'UNKNOWN')
        triage[category]+=1
        summary.append(dict(channel_id=cid,video_count=len(records),exact_timestamps=len(dates),
             missing_timestamps=len(records)-len(dates),oldest=min(dates) if dates else None,newest=max(dates) if dates else None,
             at_or_before_2020=any(d<'2021' for d in dates),catalog_status=state['catalog_status'],error_category=category,
             inaccessible_unique=inactive.get(cid,0),inaccessible_encounters=state.get('inaccessible',0),
             duplicates=state.get('duplicates',0),ordering=state.get('ordering'),near_cap=len(records)>=900,
             remaining_depth_known=0 if state['catalog_status']=='PLAYLIST_EXHAUSTED' else None,
             remaining_first_pass_allowance=max(0,1000-len(records)),recheck_eligible=False if category=='NOT_FOUND' else None))
        previous=None; previous_signals=set()
        for index,row in enumerate(records):
            title=row['title']; date=row.get('video_published_at')
            signals=sorted(set(m.group(0).lower() for m in IDENTITY.finditer(title)))
            role_signals=sorted(set(m.group(0).lower() for m in ROLE.finditer(title)))
            gap=0
            if previous and date:
                gap=(datetime.fromisoformat(date)-datetime.fromisoformat(previous)).days
            if signals or index==0:
                types=[]
                if index==0: types.append('EARLIEST_VIDEO_CONTEXT')
                if DEBUT.search(title): types.append('POSSIBLE_DEBUT_OR_MODEL_CHANGE')
                elif signals: types.append('VIRTUAL_TERMINOLOGY_ONLY')
                if gap>=180 and DEBUT.search(title): types.append('GAP_THEN_IDENTITY_TERM')
                if signals and previous_signals and set(signals)!=previous_signals and DEBUT.search(title): types.append('POSSIBLE_MODEL_ERA_CHANGE')
                candidates.append(dict(channel_id=cid,video_id=row['video_id'],title=title,published_at=date,
                    matched_signal=' | '.join(signals or ['earliest available video']),candidate_type=' | '.join(types),
                    confidence_for_review='high' if DEBUT.search(title) else 'low',review_status='UNREVIEWED'))
                if DEBUT.search(title) and date: earliest.append(date)
            if role_signals:
                roles.append(dict(channel_id=cid,video_id=row['video_id'],title=title,published_at=date,
                    matched_signal=' | '.join(role_signals),candidate_type='PUBLIC_ROLE_OR_CREDIT_SIGNAL',confidence_for_review='low',review_status='UNREVIEWED'))
            if date: previous=date
            if signals: previous_signals=set(signals)
        for rank,row in enumerate(ordered_remaining(records,existing[cid])):
            pending.append((len(existing[cid])+rank,cid,row['video_id'],(row.get('video_published_at') or 'unknown')[:4]))
        for job in existing[cid]:
            if job['status']!='EXHAUSTED':
                resume.append({k:job[k] for k in ('channel','video','digest','status','turns')})
    prepared=sqlite3.connect(out/'prepared_interactions.sqlite3')
    prepared.execute('CREATE TABLE IF NOT EXISTS prepared(rank INTEGER PRIMARY KEY,channel TEXT,video TEXT,year TEXT,UNIQUE(channel,video))')
    prepared.execute('DELETE FROM prepared')  # Derived selection only; never collection cursors.
    prepared.executemany('INSERT INTO prepared VALUES (?,?,?,?)',[(n,c,v,y) for n,(_,c,v,y) in enumerate(sorted(pending))])
    prepared.execute('CREATE INDEX IF NOT EXISTS by_channel ON prepared(channel,rank)');prepared.commit();prepared.close()
    write_json(out/'resume_existing_jobs.json',resume)
    write_csv(out/'channel_coverage.csv',summary,list(summary[0]))
    write_csv(out/'channel_year_coverage.csv',yearly,['channel_id','year','video_count'])
    observed={(r['channel_id'],r['year']):r['video_count'] for r in yearly}
    write_csv(out/'channel_year_coverage_dense.csv',
        [dict(channel_id=cid,year=year,video_count=observed.get((cid,year),0)) for cid in sorted(states) for year in sorted(years_total)],
        ['channel_id','year','video_count'])
    fields=['channel_id','video_id','title','published_at','matched_signal','candidate_type','confidence_for_review','review_status']
    write_csv(out/'identity_review_queue.csv',candidates,fields);write_csv(out/'role_review_queue.csv',roles,fields)
    priority=[r for r in candidates if r['confidence_for_review']=='high' or 'EARLIEST' in r['candidate_type']]
    priority.sort(key=lambda r:('GAP_THEN' not in r['candidate_type'],r['confidence_for_review']!='high',r['published_at'] or '9999',r['channel_id']))
    write_csv(out/'identity_priority_review.csv',priority,fields)
    result=dict(catalog_records=sum(r['video_count'] for r in summary),channels=len(states),year_counts=dict(sorted(years_total.items())),
        channel_year_rows=len(yearly),exact_timestamps=sum(r['exact_timestamps'] for r in summary),
        missing_timestamps=sum(r['missing_timestamps'] for r in summary),at_or_before_2020_channels=sum(r['at_or_before_2020'] for r in summary),
        triage=dict(triage),malformed_channel_ids=sum(not bool(re.fullmatch(r'UC[A-Za-z0-9_-]{22}',cid)) for cid in states),
        identity_candidates=len(candidates),priority_identity_candidates=len(priority),identity_signal_types=dict(Counter(r['candidate_type'] for r in candidates)),
        earliest_debut_term_candidate=min(earliest) if earliest else None,role_candidates=len(roles),
        role_signal_counts=dict(Counter(signal for r in roles for signal in r['matched_signal'].split(' | '))),
        new_interaction_jobs=len(pending),resumable_or_held_existing_jobs=len(resume),
        completed_excluded=sum(j['status']=='EXHAUSTED' for group in existing.values() for j in group),
        inaccessible_unique=sum(inactive.values()),duplicate_encounters=sum(r['duplicates'] for r in summary),
        non_monotonic_channels=sum(r['ordering']=='NON_MONOTONIC' for r in summary),
        unknown_remaining_depth_channels=sum(r['remaining_depth_known'] is None for r in summary),
        near_cap_channels=sum(r['near_cap'] for r in summary))
    write_json(out/'catalog_summary.json',result)
    return result


def analytics_processing(out):
    import duckdb
    from storage.private_sheet_store import PrivateSheetStore
    from storage.private_sheet_analytics import build_sheet_unified_raw,ARCHIVE_HEADERS
    from storage.expanded_sheet_batches import validated_expanded_batches
    from scripts.build_duckdb_temporal_snapshots import build_canonical_events_view,compute_window_snapshots
    from core.hasher import load_persistent_secret_key
    load_persistent_secret_key()
    store=PrivateSheetStore()
    records=list(store.read_records('PRIVATE_DATA_ARCHIVE',ARCHIVE_HEADERS))
    batches,rejected=validated_expanded_batches(records)
    class CachedStore:
        def read_records(self,*args,**kwargs): return iter(records)
    con=duckdb.connect(':memory:');con.execute("SET temp_directory=''")
    raw=build_sheet_unified_raw(con,CachedStore(),include_expanded=True)
    def totals():
        r=con.execute('SELECT COUNT(*),COUNT(DISTINCT viewer_hash),COUNT(DISTINCT vtuber_channel_id),COUNT(DISTINCT video_id),COUNT(*) FILTER(WHERE interaction_time IS NULL) FROM canonical_events').fetchone()
        return dict(zip(['canonical_interactions','unique_pseudonyms','channels','videos','undated_interactions'],r))
    con.execute('CREATE VIEW before_expanded AS SELECT * FROM unified_raw WHERE NOT append_only')
    build_canonical_events_view(con,'before_expanded'); baseline=totals()
    cutoff=json.loads((ROOT/'progress.json').read_text())['at']
    baseline_edges=compute_window_snapshots(con,{'type':'all_time','start':'1900-01-01','end':cutoff},{})
    build_canonical_events_view(con);current=totals()
    current.update(raw_records=raw,validated_expanded_batches=len(batches),rejected_expanded_batches=len(rejected),
                   baseline_without_expanded=baseline,delta={k:current[k]-v for k,v in baseline.items()})
    years=con.execute('SELECT YEAR(interaction_time),COUNT(*),COUNT(DISTINCT vtuber_channel_id),COUNT(DISTINCT video_id) FROM canonical_events WHERE interaction_time IS NOT NULL GROUP BY 1 ORDER BY 1').fetchall()
    current['yearly_coverage']=[dict(zip(['year','interactions','channels','videos'],r)) for r in years]
    current['source_counts']=dict(con.execute('SELECT source_type,COUNT(*) FROM canonical_events GROUP BY source_type').fetchall())
    windows=[{'type':'all_time','start':'1900-01-01','end':cutoff}]
    for year,*_ in years:
        for typ,start in [('yearly',f'{year}-01-01'),('cumulative','1900-01-01')]:
            windows.append(dict(type=typ,start=start,end=f'{year}-12-31 23:59:59+00' if year<2026 else cutoff))
    previews=[]
    for w in windows:
        edges=compute_window_snapshots(con,w,{})
        for edge in edges:
            edge['coverage_a']=None;edge['coverage_b']=None
        nodes=[{'channel_id':r[0],'interaction_count':r[1],'historical_virtual_identity':'UNKNOWN'} for r in con.execute(
            'SELECT vtuber_channel_id,COUNT(*) FROM canonical_events WHERE interaction_time BETWEEN ? AND ? GROUP BY 1 ORDER BY 1',[w['start'],w['end']]).fetchall()]
        previews.append(dict(dataset_version='expanded-v1',collected_through=cutoff,scope='OBSERVED_CHANNEL_AUDIENCE_NOT_VTUBER_IDENTITY',window=w,nodes=nodes,edges=edges))
    all_edges=previews[0]['edges']
    current.update(edge_count=len(all_edges),strong_edge_count=sum(e['strong_shared_any']>0 for e in all_edges),
                   strong_comment_edges=sum(e['strong_shared_comments']>0 for e in all_edges),
                   baseline_edge_count=len(baseline_edges),edge_count_delta=len(all_edges)-len(baseline_edges),
                   snapshots=len(previews),snapshot_identity_limitation='Channel audience previews; no automatic virtual identity membership',
                   acknowledged_expanded_events=sum(len(b['events']) for b in batches.values()))
    write_json(out/'audience_snapshots.json',previews)
    return finalize_public_preview(out,current)


def finalize_public_preview(out,current):
    """Render/compare only public aggregates, with no second workbook read."""
    all_edges=json.loads((out/'audience_snapshots.json').read_text(encoding='utf-8'))[0]['edges']
    import pyarrow.parquet as pq
    frozen=Path('data/temporal/snapshots/network_snapshots.parquet')
    frozen_rows=pq.read_table(frozen).to_pylist()
    frozen_all=[r for r in frozen_rows if r['window_type']=='all_time']
    previous_pairs={(r['vtuber_a'],r['vtuber_b']) for r in frozen_all}
    current_pairs={(r['vtuber_a'],r['vtuber_b']) for r in all_edges}
    current['frozen_comparison']=dict(source=str(frozen),sha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),
        previous_edges=len(frozen_all),added_pairs=len(current_pairs-previous_pairs),removed_pairs=len(previous_pairs-current_pairs),
        previous_strong_edges=sum(r['strong_shared_any']>0 for r in frozen_all),
        caveat='Expanded collection changes coverage; this is not a temporal growth inference.')
    write_json(out/'analytics_summary.json',current)
    summary=json.loads((out/'catalog_summary.json').read_text(encoding='utf-8'))
    rows=''.join(f'<tr><td>{r["year"]}</td><td>{r["interactions"]:,}</td><td>{r["channels"]}</td><td>{r["videos"]}</td></tr>' for r in current['yearly_coverage'])
    page=f'''<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ผลประมวลผลช่วงพักโควตา</title>
<style>body{{font:18px system-ui;max-width:1050px;margin:40px auto;padding:20px;background:#101728;color:#edf2ff}}table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;border-bottom:1px solid #47516a;text-align:left}}a{{color:#b5d7ff}}p{{line-height:1.8}}</style>
<h1>ผลประมวลผลข้อมูลที่เก็บแล้ว</h1><p>พรีวิวภายใน • ยังไม่เผยแพร่ • expanded-v1</p>
<p>วิเคราะห์ catalog <b>{summary['catalog_records']:,} วิดีโอ</b> จาก {summary['channels']:,} ช่อง<br>
หลัง deduplicate: <b>{current['canonical_interactions']:,} interactions</b> / {current['unique_pseudonyms']:,} pseudonyms / {current['edge_count']:,} audience-overlap edges</p>
<p>วันที่วิดีโอไม่ใช่วันเริ่มเป็น VTuber; signals เปิดตัวและ role/credit ทั้งหมดยังรอตรวจ ไม่มีการอนุมัติ identity หรือ agency อัตโนมัติ<br>
กราฟชุดนี้แสดงหลักฐานผู้ชมของช่อง ไม่ใช่การยืนยันสมาชิก VTuber ในอดีต และไม่เติม subscribers/agency/status ปัจจุบันย้อนเวลา</p>
<p>คิวใหม่ {summary['new_interaction_jobs']:,} วิดีโอ / งานเดิมที่ยังรอดำเนินการ {summary['resumable_or_held_existing_jobs']} งาน<br>Identity review ชุดอ่านก่อน {summary['priority_identity_candidates']:,} รายการ / Role signals {summary['role_candidates']:,} รายการ</p>
<h2>หลักฐาน interactions รายปี</h2><table><tr><th>ปี</th><th>Interactions</th><th>ช่อง</th><th>วิดีโอ</th></tr>{rows}</table>
<p><a href="audience_snapshots.json">Snapshots รายปี / สะสม</a> · <a href="identity_priority_review.csv">คิวตรวจเปิดตัว</a> · <a href="channel_coverage.csv">สถานะทุกช่อง</a> · <a href="role_review_queue.csv">คิวตรวจ role/credit</a></p></html>'''
    (out/'preview.html').write_text(page,encoding='utf-8')
    return current


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--analytics',action='store_true');args=p.parse_args()
    out=ROOT/'expanded-v1'/'downtime-2026-09-10';out.mkdir(parents=True,exist_ok=True)
    if args.analytics:
        print(json.dumps(analytics_processing(out),ensure_ascii=False))
    else:
        print(json.dumps(catalog_processing(ROOT,out),ensure_ascii=False))


if __name__=='__main__':main()
