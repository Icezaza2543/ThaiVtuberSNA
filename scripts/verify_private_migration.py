"""Verify current private Sheet bytes and canonical equivalence without exporting rows."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import duckdb
from storage.private_sheet_store import PrivateSheetStore
from storage.private_sheet_analytics import build_sheet_unified_raw, ARCHIVE_HEADERS
from scripts.build_duckdb_temporal_snapshots import build_unified_raw_view,build_canonical_events_view,get_sources_by_provenance


def canonical_digest(con):
    build_canonical_events_view(con)
    columns=[d[0] for d in con.execute('SELECT * FROM canonical_events LIMIT 0').description]
    quoted=','.join('"'+c+'"' for c in columns)
    digest=hashlib.sha256();count=0
    for row in con.execute('SELECT * FROM canonical_events ORDER BY '+quoted).fetchall():
        digest.update(json.dumps(row,default=str,separators=(',',':')).encode());digest.update(b'\n');count+=1
    return {'rows':count,'canonical_sha256':digest.hexdigest(),
            'unique_hashes':con.execute('SELECT COUNT(DISTINCT viewer_hash) FROM canonical_events').fetchone()[0]}


def main():
    local=duckdb.connect(':memory:')
    build_unified_raw_view(local,get_sources_by_provenance())
    baseline=canonical_digest(local);local.close()
    store=PrivateSheetStore()
    report=json.loads((ROOT/'docs/evidence/private_data_migration.json').read_text())
    archive=[]
    for row in store.read_records('PRIVATE_DATA_ARCHIVE',ARCHIVE_HEADERS):
        archive.append([row.get(h,'') for h in ARCHIVE_HEADERS])
    actual=hashlib.sha256(json.dumps([ARCHIVE_HEADERS]+archive,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    expected=next(t for t in report['verified_tables'] if t['tab']=='PRIVATE_DATA_ARCHIVE')
    if actual!=expected['content_sha256'] or len(archive)!=expected['rows']:
        raise RuntimeError('Archive readback differs from the migration manifest')
    class VerifiedArchive:
        def read_records(self,*args):return (dict(zip(ARCHIVE_HEADERS,r)) for r in archive)
    cloud=duckdb.connect(':memory:')
    build_sheet_unified_raw(cloud,VerifiedArchive())
    recovered=canonical_digest(cloud);cloud.close()
    result={'status':'PASS' if baseline==recovered else 'FAIL','local_baseline':baseline,
            'private_sheet_canonical':recovered,'archive_rows_verified':len(archive),
            'archive_sha256_verified':actual,'scope':'Full private archive readback and exact sorted canonical row comparison in RAM; no T20 ingestion/publish'}
    (ROOT/'docs/evidence/private_migration_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return int(result['status']!='PASS')


if __name__=='__main__':sys.exit(main())
