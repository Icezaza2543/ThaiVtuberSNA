"""Recover only missing private data into the existing workbook. No revision restore."""
import argparse
import collections
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from core.hasher import PrivacyHasher, compute_key_fingerprint
from core.data_security import PRIVATE_FIELDS, TEXT_FIELDS, assert_sheet_rows
from scripts.audit_private_data_plane import local_secret_values
from storage.private_sheet_store import PrivateSheetStore

INDEX_HEADERS=['viewer_hash','raw_channel_id','display_name','channel_url','first_seen','last_seen',
               'total_interactions','channels_observed_count','recovery_source','recovery_status']
PRESENCE_HEADERS=['viewer_hash','vtuber_channel_id','first_seen','last_seen','interaction_count','source_types_seen']
ACTIVITY_HEADERS=['viewer_hash','first_observed_year','last_observed_year','active_year_count','channel_count']
ARCHIVE_HEADERS=['source_path','source_table','row_number','record_json']


def clean(value):
    if isinstance(value,dict):
        return {str(k):clean(v) for k,v in value.items() if k not in TEXT_FIELDS}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value):return None
    if value is None or isinstance(value,(str,int,float,bool)):return value
    return str(value)


def number(value):
    try:return max(0,int(float(value or 0)))
    except (ValueError,TypeError):return 0


def recover_historical(path, hasher=None):
    with path.open(encoding='utf-8',newline='') as handle:
        records=[{k:v for k,v in row.items() if k} for row in csv.DictReader(handle)
                 if row.get('authorChannelUrl') or row.get('authorDisplayName')]
    grouped={}
    for row in records:
        # Preserve original URLs as unresolved identity candidates. Do not merge by name.
        key=row.get('authorChannelUrl')
        if not key: continue
        old=grouped.setdefault(key,dict(row))
        old['comment_count']=max(number(old.get('comment_count')),number(row.get('comment_count')))
        old['last_seen']=max(old.get('last_seen',''),row.get('last_seen',''))
    index=[]
    reconstructed=0
    for url,row in sorted(grouped.items()):
        match=re.search(r'/channel/(UC[A-Za-z0-9_-]{22})(?:[/?#]|$)',url)
        channel_id=match[1] if match else ''
        if channel_id and hasher is None: hasher=PrivacyHasher()
        hashed=hasher.hash_viewer_id(channel_id) if channel_id else ''
        reconstructed+=bool(hashed)
        index.append([hashed,channel_id,row.get('authorDisplayName',''),url,'',row.get('last_seen',''),
                      number(row.get('comment_count')),'','Drive revision 380',
                      'RAW_ID_RECONSTRUCTED' if hashed else 'UNRESOLVED_HANDLE'])
    stats={'expected_historical_count':38240,'raw_records_recovered':len(records),
           'unique_url_candidates':len(grouped),'unique_verified_raw_identities':reconstructed,
           'viewer_hash_identities_reconstructed':reconstructed,
           'unmatched_handle_candidates':len(grouped)-reconstructed,
           'duplicate_url_rows':len(records)-len(grouped),
           'identity_note':'Historical count is rows, not verified people; handle URLs cannot recover raw IDs or invert HMAC.'}
    return records,index,stats


def source_records():
    """Decode all local private tables, preserving source and row provenance."""
    import pyarrow.parquet as pq
    roots=[ROOT/'data']+[p/'data' for p in (ROOT/'.worktrees').iterdir() if p.is_dir()] if (ROOT/'.worktrees').exists() else [ROOT/'data']
    for root in roots:
        for path in sorted(root.rglob('*.parquet')):
            table=pq.read_table(path)
            if set(table.column_names)&PRIVATE_FIELDS and table.num_rows:
                yield path,'parquet',table.to_pylist()
        for path in sorted(root.rglob('*.duckdb')):
            import duckdb
            con=duckdb.connect(str(path),read_only=True)
            try:
                tables=con.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE'").fetchall()
                private=False
                for schema,name in tables:
                    qualified='.'.join('"'+v.replace('"','""')+'"' for v in (schema,name))
                    cursor=con.execute('SELECT * FROM '+qualified)
                    columns=[d[0] for d in cursor.description]
                    if set(columns)&PRIVATE_FIELDS:
                        private=True
                        yield path,schema+'.'+name,[dict(zip(columns,row)) for row in cursor.fetchall()]
                if not private:
                    # Pure derived views carry no durable rows; record that they can be rebuilt.
                    yield path,'derived_database',[]
            finally:con.close()
        for path in sorted(root.rglob('*.sqlite3')):
            import sqlite3
            con=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
            try:
                names=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                tables=[]
                for name in names:
                    cursor=con.execute('SELECT * FROM "'+name.replace('"','""')+'"')
                    columns=[d[0] for d in cursor.description]
                    tables.append((name,columns,cursor.fetchall()))
                if any(set(columns)&PRIVATE_FIELDS for _,columns,_ in tables):
                    for name,columns,rows in tables:
                        yield path,name,[dict(zip(columns,row)) for row in rows]
            finally:con.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--historical-csv',type=Path,default=ROOT/'data/private_recovery/revision380.csv')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    original_fp=compute_key_fingerprint(PrivacyHasher().secret_salt)
    records,index,stats=recover_historical(args.historical_csv)
    sources=[]; archive=[]
    for path,table,rows in source_records():
        relative=path.relative_to(ROOT).as_posix()
        sources.append({'path':relative,'table':table,'rows':len(rows),'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        for i,row in enumerate(rows):
            archive.append([relative,table,str(i+1),json.dumps(clean(row),ensure_ascii=False,separators=(',',':'))])
    # Canonical analytical normalization is separate from lossless source archive.
    import duckdb
    from scripts.build_duckdb_temporal_snapshots import build_unified_raw_view,build_canonical_events_view,get_sources_by_provenance
    con=duckdb.connect(':memory:')
    try:
        build_unified_raw_view(con,get_sources_by_provenance())
        build_canonical_events_view(con)
        columns=[d[0] for d in con.execute('SELECT * FROM canonical_events LIMIT 0').description]
        canonical=[dict(zip(columns,r)) for r in con.execute('SELECT * FROM canonical_events').fetchall()]
    finally:con.close()
    presence={};activity={}
    for row in canonical:
        vh=row['viewer_hash'];cid=row['vtuber_channel_id']
        when=str(row.get('interaction_time') or row.get('interaction_at') or '')
        current=presence.setdefault((vh,cid),{'first':when,'last':when,'count':0,'sources':set()})
        if when:current['first']=min(current['first'],when) if current['first'] else when;current['last']=max(current['last'],when)
        current['count']+=1;current['sources'].add(row.get('source_type','comment'))
        a=activity.setdefault(vh,{'years':set(),'channels':set(),'first':when,'last':when,'count':0})
        if when[:4].isdigit():a['years'].add(int(when[:4]))
        a['channels'].add(cid);a['count']+=1
        if when:a['first']=min(a['first'],when) if a['first'] else when;a['last']=max(a['last'],when)
    for vh,a in sorted(activity.items()):
        index.append([vh,'','','',a['first'],a['last'],a['count'],len(a['channels']),
                      'Existing canonical HMAC observations','HASH_ONLY_RAW_ID_UNAVAILABLE'])
    presence_rows=[[vh,cid,p['first'],p['last'],p['count'],','.join(sorted(p['sources']))] for (vh,cid),p in sorted(presence.items())]
    activity_rows=[[vh,min(a['years']) if a['years'] else '',max(a['years']) if a['years'] else '',len(a['years']),len(a['channels'])] for vh,a in sorted(activity.items())]
    stats.update(canonical_hash_identities_preserved=len(activity),canonical_presence_rows=len(presence_rows),
                 local_private_archive_rows=len(archive),local_private_sources=len(sources),hmac_fingerprint=original_fp)
    report={'recovery':stats,'sources':sources,'verified_tables':[]}
    print(json.dumps(stats),flush=True)
    if not args.apply:return
    store=PrivateSheetStore(known_secrets=local_secret_values())
    historical_headers=['authorDisplayName','authorChannelUrl','comment_count','channels_active','last_seen']
    tables=[('ALL_COMMENTERS',historical_headers,[[r.get(h,'') for h in historical_headers] for r in records]),
            ('VIEWER_INDEX',INDEX_HEADERS,index),('VIEWER_CHANNEL_PRESENCE',PRESENCE_HEADERS,presence_rows),
            ('VIEWER_ACTIVITY_SUMMARY',ACTIVITY_HEADERS,activity_rows),
            ('PRIVATE_DATA_ARCHIVE',ARCHIVE_HEADERS,archive),
            ('RECOVERY_METADATA',['metric','value'],[[k,str(v)] for k,v in stats.items()]),
            ('MIGRATION_AUDIT',['source_path','source_table','source_rows','file_sha256'],
             [[s['path'],s['table'],s['rows'],s['file_sha256']] for s in sources]),
            ('DATA_DICTIONARY',['tab','column','classification','description'],
             [[name,h,'PRIVATE_DATA','Private record; no independent tab confidentiality']
              for name,headers in [('ALL_COMMENTERS',historical_headers),('VIEWER_INDEX',INDEX_HEADERS),
                                   ('VIEWER_CHANNEL_PRESENCE',PRESENCE_HEADERS),('VIEWER_ACTIVITY_SUMMARY',ACTIVITY_HEADERS),
                                   ('PRIVATE_DATA_ARCHIVE',ARCHIVE_HEADERS)] for h in headers])]
    for name,headers,rows in tables:
        result=store.write_verified_table(name,headers,rows)
        report['verified_tables'].append(result)
        (ROOT/'docs/evidence/private_data_migration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(result),flush=True)
    assert original_fp==compute_key_fingerprint(PrivacyHasher().secret_salt)
    print('ALL_TABLES_VERIFIED',flush=True)


if __name__=='__main__':main()
