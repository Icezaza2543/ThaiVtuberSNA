"""Remove only source copies proven present in the verified authorized archive."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from scripts.migrate_private_data_plane import source_records, clean, ARCHIVE_HEADERS, recover_historical


def main():
    report=json.loads((ROOT/'docs/evidence/private_data_migration.json').read_text())
    validation=json.loads((ROOT/'docs/evidence/private_migration_validation.json').read_text())
    if validation['status']!='PASS':raise RuntimeError('Canonical Sheet verification required')
    tables={t['tab']:t for t in report['verified_tables'] if t['verified']}
    required={'ALL_COMMENTERS','VIEWER_INDEX','VIEWER_CHANNEL_PRESENCE','VIEWER_ACTIVITY_SUMMARY',
              'PRIVATE_DATA_ARCHIVE','RECOVERY_METADATA','MIGRATION_AUDIT','DATA_DICTIONARY'}
    if not required<=tables.keys():raise RuntimeError('All migration tables must be verified first')
    values=[ARCHIVE_HEADERS];files=set()
    for path,table,rows in source_records():
        relative=path.relative_to(ROOT).as_posix()
        matches=[s for s in report['sources'] if s['path']==relative and s['table']==table]
        if len(matches)!=1 or hashlib.sha256(path.read_bytes()).hexdigest()!=matches[0]['file_sha256']:
            raise RuntimeError('Source changed since archive verification; preserve it')
        files.add(path.resolve())
        for i,row in enumerate(rows):
            values.append([relative,table,str(i+1),json.dumps(clean(row),ensure_ascii=False,separators=(',',':'))])
    digest=hashlib.sha256(json.dumps(values,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    if digest!=tables['PRIVATE_DATA_ARCHIVE']['content_sha256'] or digest!=validation['archive_sha256_verified']:
        raise RuntimeError('Current decoded sources differ from the verified Sheet archive')
    historical=ROOT/'data/private_recovery/revision380.csv'
    records,_,_=recover_historical(historical)
    headers=['authorDisplayName','authorChannelUrl','comment_count','channels_active','last_seen']
    hist_digest=hashlib.sha256(json.dumps([headers]+[[r.get(h,'') for h in headers] for r in records],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    if hist_digest!=tables['ALL_COMMENTERS']['content_sha256']:raise RuntimeError('Historical recovery differs')
    files.add(historical.resolve())
    for p in list(files):
        if p.suffix in ('.sqlite','.sqlite3','.db','.duckdb'):
            files.update(q.resolve() for q in (Path(str(p)+'-wal'),Path(str(p)+'-shm'),Path(str(p)+'.wal')) if q.exists())
    # Validate every absolute target before deleting anything. No recursive directory deletion.
    allowed=[(ROOT/'data').resolve(),(ROOT/'.worktrees').resolve()]
    if any(not any(p.is_relative_to(root) for root in allowed) or p.suffix=='.key' for p in files):
        raise RuntimeError('Cleanup target escaped the authorized data roots')
    removed=[]
    for path in sorted(files):
        path.unlink();removed.append(path.relative_to(ROOT).as_posix())
    result={'status':'PASS','files_removed':len(removed),'paths':removed,
            'archive_sha256_verified':digest,'history_rewritten':False,
            'notice':'Deletion is of verified working copies only; Git history remains as documented. Credentials were not removed.'}
    (ROOT/'docs/evidence/private_migration_cleanup.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='paths'},indent=2))


if __name__=='__main__':main()
