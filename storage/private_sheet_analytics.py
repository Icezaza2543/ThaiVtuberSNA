"""Read the private archive into RAM; reuse canonical provenance/deduplication.

No Parquet/CSV export and no DuckDB spill directory are created.
"""
import json
import pyarrow as pa
from storage.private_sheet_store import PrivateSheetStore

ARCHIVE_HEADERS = ['source_path', 'source_table', 'row_number', 'record_json']
RAW_COLUMNS = ['viewer_hash','vtuber_channel_id','video_id','source_type',
               'interaction_at','first_seen','timestamp','video_published_at','provenance','priority','source_path','partial_capture']


def archive_event(record):
    path = record['source_path']
    if record['source_table'] != 'parquet': return None
    if path.startswith('data/temporal/incremental/batch_'): tier,priority='t16_incremental',0
    elif path.startswith('data/temporal/deep_observations/'): tier,priority='t6_deep',1
    elif path.startswith('data/temporal/observations/'): tier,priority='t5_stratified',2
    elif path == 'data/temporal/pilot/temporal_comment_pilot.parquet': tier,priority='t2_pilot',3
    elif path.startswith(('data/real/events/','data/events/')): tier,priority='legacy',4
    else: return None
    source = json.loads(record['record_json'])
    result = {k:None for k in RAW_COLUMNS}
    result['partial_capture'] = str(source.get('partial_capture', False)).lower()
    result.update({k:source.get(k) for k in ('viewer_hash','vtuber_channel_id','video_id')})
    result.update(source_type=source.get('source_type') or 'comment',provenance=tier,priority=priority,source_path=path)
    if tier == 'legacy':
        result.update(first_seen=source.get('first_seen'),timestamp=source.get('timestamp'))
    else:
        result['interaction_at'] = source.get('interaction_at')
        if tier == 't16_incremental': result['interaction_at'] = source.get('interaction_time') or result['interaction_at']
        else: result['video_published_at'] = source.get('video_published_at')
    return result


def build_sheet_unified_raw(con, store=None, *, include_expanded=False):
    """Opt-in expanded batches supplement legacy selection; defaults remain frozen."""
    if any(row[2] for row in con.execute('PRAGMA database_list').fetchall()):
        raise ValueError('Private analytics requires an in-memory DuckDB connection')
    con.execute("SET temp_directory = ''")
    store = store or PrivateSheetStore()
    records = store.read_records('PRIVATE_DATA_ARCHIVE', ARCHIVE_HEADERS)
    if include_expanded:
        records = list(records)  # authorized private RAM, DuckDB spill already disabled
    rows = [event for row in records if (event := archive_event(row)) is not None]
    columns = RAW_COLUMNS
    if include_expanded:
        from storage.expanded_sheet_batches import validated_expanded_batches
        batches, rejected = validated_expanded_batches(records)
        for row in rows: row['append_only'] = False
        for path, batch in batches.items():
            for event in batch['events']:
                row = {k: None for k in RAW_COLUMNS}
                row.update({k: event[k] for k in ('viewer_hash','vtuber_channel_id','video_id','source_type','provenance')})
                row.update(interaction_at=event.get('interaction_time'),
                           video_published_at=event.get('video_published_at'), source_path=path,
                           priority=0, partial_capture='true', append_only=True)
                rows.append(row)
        columns = RAW_COLUMNS + ['append_only']
    if not rows: raise RuntimeError('No canonical private observations in the authorized workbook')
    schema = pa.schema([(k,pa.int64() if k=='priority' else pa.bool_() if k=='append_only' else pa.string()) for k in columns])
    table = pa.Table.from_pylist(rows,schema=schema)
    con.register('_private_sheet_raw',table)
    projections = [f'try_cast("{k}" AS TIMESTAMPTZ) AS "{k}"' if k in
                   ('interaction_at','first_seen','timestamp','video_published_at') else f'"{k}"' for k in columns]
    con.execute('CREATE OR REPLACE VIEW unified_raw AS SELECT '+','.join(projections)+' FROM _private_sheet_raw')
    return len(rows)
