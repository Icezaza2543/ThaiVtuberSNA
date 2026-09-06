"""Bounded persisted-output audit. PASS means checked rules passed, not anonymity proof."""
import csv
import json
import re
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
import duckdb
import pyarrow.parquet as pq
from core.hasher import PrivacyHasher
from storage.parquet_manager import ParquetStorageManager

FORBIDDEN_PERSISTED_COLUMNS = {
    'message_body', 'comment_body', 'text', 'comment_text', 'chat_text', 'body',
    'display_name', 'author_name', 'author_thumbnail', 'avatar', 'emoji',
    'sentiment', 'author_url', 'author_id', 'raw_author_id', 'raw_channel_id',
    'authorExternalChannelId', 'authorChannelId', 'message', 'author',
}
SHA256_HEX_PATTERN = re.compile(r'[a-f0-9]{64}')


def inspect_value(value, canaries=()):
    """Check decoded values recursively, without echoing potentially private content."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_PERSISTED_COLUMNS:
                raise ValueError('Forbidden persisted field')
            if key == 'viewer_hash' and not SHA256_HEX_PATTERN.fullmatch(str(item)):
                raise ValueError('Invalid viewer pseudonym')
            inspect_value(item, canaries)
    elif isinstance(value, (list, tuple)):
        for item in value:
            inspect_value(item, canaries)
    elif isinstance(value, str):
        if any(canary in value for canary in canaries):
            raise ValueError('Raw canary found in decoded output')


def audit_file(path, canaries=()):
    suffix = path.suffix.lower()
    result = {'file': str(path), 'status': 'PASS', 'type': suffix}
    try:
        if suffix == '.parquet':
            table = pq.read_table(path)
            if set(table.column_names) & FORBIDDEN_PERSISTED_COLUMNS:
                raise ValueError('Forbidden persisted field')
            for batch in table.to_batches(max_chunksize=4096):
                inspect_value(batch.to_pylist(), canaries)
            result.update(rows=table.num_rows, schema=str(table.schema))
        elif suffix == '.duckdb':
            con = duckdb.connect(str(path), read_only=True)
            try:
                tables = con.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_catalog = current_database()").fetchall()
                result['tables'] = []
                for schema, name in tables:
                    qualified = '.'.join('"' + x.replace('"', '""') + '"' for x in (schema, name))
                    cursor = con.execute(f'SELECT * FROM {qualified}')
                    columns = [d[0] for d in cursor.description]
                    if set(columns) & FORBIDDEN_PERSISTED_COLUMNS:
                        raise ValueError('Forbidden DuckDB column')
                    count = 0
                    while rows := cursor.fetchmany(4096):
                        inspect_value([dict(zip(columns, row)) for row in rows], canaries)
                        count += len(rows)
                    result['tables'].append({'name': name, 'columns': columns, 'rows': count})
            finally:
                con.close()
        elif suffix == '.json':
            inspect_value(json.loads(path.read_text(encoding='utf-8')), canaries)
        elif suffix == '.csv':
            with path.open(encoding='utf-8', newline='') as file:
                reader = csv.DictReader(file)
                if set(reader.fieldnames or []) & FORBIDDEN_PERSISTED_COLUMNS:
                    raise ValueError('Forbidden CSV column')
                for row in reader:
                    inspect_value(row, canaries)
        elif suffix in {'.log', '.txt', '.jsonl'}:
            content = path.read_text(encoding='utf-8')
            inspect_value(content, canaries)
            if any(re.search(r'["\']?' + re.escape(key) + r'["\']?\s*[:=]', content) for key in FORBIDDEN_PERSISTED_COLUMNS):
                raise ValueError('Forbidden field marker in text output')
        else:
            result['status'] = 'UNSUPPORTED'
    except Exception as error:
        result.update(status='ERROR' if not isinstance(error, ValueError) else 'FAIL', reason=type(error).__name__)
    return result


def audit_directory(root, canaries=()):
    return [audit_file(path, canaries) for path in sorted(root.rglob('*')) if path.is_file()]


def run_canary_leakage_test():
    """Exercise the collector's actual in-memory extraction, aggregation and storage path."""
    from unittest.mock import patch
    from collector.youtube_collector import YouTubeCollector
    from storage.duckdb_engine import DuckDBAnalyticsEngine
    raw_id = 'UC_CANARY_RAW_VIEWER_SECRET_9999'
    raw_text = 'CANARY_PRIVATE_MESSAGE_7394'
    class FakeYDL:
        def __init__(self, options):
            assert not options.get('writeinfojson')
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def extract_info(self, *args, **kwargs):
            assert kwargs.get('download') is False
            return {'comments': [{'author_id': raw_id, 'text': raw_text, 'timestamp': 1}]}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        hasher = PrivacyHasher('audit-only-synthetic-key')
        with patch('collector.youtube_collector.PrivacyHasher', return_value=hasher), patch('yt_dlp.YoutubeDL', FakeYDL), patch('collector.youtube_collector.YOUTUBE_API_KEY', ''):
            collector = YouTubeCollector()
            events = collector.collect_aggregated_events({'video_id': 'canary_video', 'vtuber_channel_id': 'target'})
        ParquetStorageManager(root / 'events').write_events(events)
        engine = DuckDBAnalyticsEngine(root / 'audit.duckdb', root / 'events')
        engine.con.execute('CREATE TABLE persisted_presence AS SELECT * FROM raw_events')
        assert engine.get_viewer_presence_summary()[0]['viewer_hash'] == hasher.hash_viewer_id(raw_id)
        engine.close()
        (root / 'presence.json').write_text(json.dumps(events))
        return all(r['status'] == 'PASS' for r in audit_directory(root, (raw_id, raw_text)))


def run_full_privacy_audit():
    roots = [BASE_DIR / 'data', BASE_DIR / 'web', BASE_DIR / 'logs']
    supported = {'.parquet', '.duckdb', '.json', '.csv', '.log', '.txt', '.jsonl'}
    results = [audit_file(p) for root in roots if root.exists() for p in sorted(root.rglob('*')) if p.is_file() and p.suffix.lower() in supported]
    canary = run_canary_leakage_test()
    failures = [r for r in results if r['status'] != 'PASS']
    print(json.dumps({'checked_files': len(results), 'failures': failures, 'canary_passed': canary,
        'scope': 'Decoded Parquet/DuckDB/JSON/CSV and field-marker scans in text/log outputs under data, web, logs',
        'limitations': 'Does not prove absence of arbitrary unlabelled personal text, inspect OS swap/backups, or cryptographically verify hash origin; no historical real Parquet available in a fresh clone.'}, indent=2))
    return not failures and canary


if __name__ == '__main__':
    sys.exit(0 if run_full_privacy_audit() else 1)
