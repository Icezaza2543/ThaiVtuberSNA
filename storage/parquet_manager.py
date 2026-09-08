"""Canonical per-channel/video/source presence snapshots.

Appearances is the maximum observed batch count, not a unique lifetime event count.
Raw rows are aggregated within each batch; repeated snapshots reconcile by max.
"""
import os
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from config.settings import EVENTS_DIR
from core.file_lock import file_lock

EVENT_SCHEMA = pa.schema([(k, pa.string()) for k in
    ('viewer_hash', 'vtuber_channel_id', 'video_id', 'timestamp', 'source_type')])
AGGREGATED_SCHEMA = pa.schema([
    ('viewer_hash', pa.string()), ('vtuber_channel_id', pa.string()),
    ('video_id', pa.string()), ('first_seen', pa.string()), ('last_seen', pa.string()),
    ('appearances', pa.int64()), ('source_type', pa.string())])


def _timestamp(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        raise ValueError('Invalid presence timestamp') from None


def _normalize(events):
    rows = {}
    raw_counts = defaultdict(int)
    snapshot_counts = defaultdict(int)
    for event in events:
        for field in ('video_id', 'vtuber_channel_id'):
            if not re.fullmatch(r'[A-Za-z0-9_-]+', event.get(field, '')):
                raise ValueError('Invalid presence identity')
        if event.get('source_type') not in {'comment', 'live_chat'}:
            raise ValueError('Explicit source_type live_chat or comment required')
        if not isinstance(event.get('viewer_hash'), str) or not event['viewer_hash']:
            raise ValueError('Missing viewer pseudonym')
        first = _timestamp(event.get('first_seen', event.get('timestamp')))
        last = _timestamp(event.get('last_seen', event.get('timestamp')))
        count = event.get('appearances', 1)
        if type(count) is not int or count < 1 or first > last:
            raise ValueError('Invalid presence count or interval')
        key = tuple(event[k] for k in ('vtuber_channel_id', 'video_id', 'source_type', 'viewer_hash'))
        if 'timestamp' in event and 'first_seen' not in event:
            raw_counts[key] += count
        else:
            snapshot_counts[key] = max(snapshot_counts[key], count)
        row = dict(zip(('vtuber_channel_id', 'video_id', 'source_type', 'viewer_hash'), key))
        row.update(first_seen=first, last_seen=last, appearances=count)
        if key in rows:
            current = rows[key]
            current['first_seen'] = min(current['first_seen'], first)
            current['last_seen'] = max(current['last_seen'], last)
        else:
            rows[key] = row
        rows[key]['appearances'] = max(raw_counts[key], snapshot_counts[key])
    return rows


def _merge(current, incoming):
    for key, row in incoming.items():
        if key not in current:
            current[key] = dict(row)
        else:
            old = current[key]
            old['first_seen'] = min(old['first_seen'], row['first_seen'])
            old['last_seen'] = max(old['last_seen'], row['last_seen'])
            old['appearances'] = max(old['appearances'], row['appearances'])
    return current


class ParquetStorageManager:
    def __init__(self, base_dir=None):
        from core.storage_boundary import require_synthetic_local_path
        require_synthetic_local_path(base_dir or EVENTS_DIR)
        self.base_dir = Path(base_dir or EVENTS_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_partition_path(self, video_id, timestamp_str=None, *, source_type='comment',
                           vtuber_channel_id='unknown'):
        # timestamp_str is retained for callers, but never controls partition identity.
        for value in (video_id, vtuber_channel_id):
            if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
                raise ValueError('Invalid partition identity')
        if source_type not in {'comment', 'live_chat'}:
            raise ValueError('Invalid source')
        return self.base_dir / 'canonical' / vtuber_channel_id / f'{video_id}_{source_type}.parquet'

    def _path(self, row):
        return self.get_partition_path(row['video_id'], source_type=row['source_type'],
                                       vtuber_channel_id=row['vtuber_channel_id'])

    def _publish(self, rows):
        groups = defaultdict(dict)
        for key, row in rows.items():
            groups[self._path(row)][key] = row
        # Read and validate every old partition before publishing anything.
        prepared = {}
        for path, incoming in groups.items():
            existing = _normalize(pq.read_table(path).to_pylist()) if path.exists() else {}
            if any(self._path(row) != path for row in existing.values()):
                raise ValueError('Existing partition contains another identity/source')
            prepared[path] = _merge(existing, incoming)
        for path, merged in prepared.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name('.' + uuid.uuid4().hex + '.tmp')
            try:
                table = pa.Table.from_pylist(list(merged.values()), schema=AGGREGATED_SCHEMA)
                pq.write_table(table, temporary, compression='snappy')
                with temporary.open('r+b') as handle:
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        paths = sorted(prepared)
        return paths[0] if len(paths) == 1 else paths

    def write_events(self, events):
        if not events:
            raise ValueError('No events provided to write')
        rows = _normalize(events)
        with file_lock(self.base_dir / '.storage.lock'):
            if any(p.relative_to(self.base_dir).parts[0] != 'canonical'
                   for p in self.get_all_parquet_paths()):
                raise RuntimeError('Legacy partitions require explicit migration before writing')
            return self._publish(rows)

    def get_all_parquet_paths(self):
        return sorted(self.base_dir.rglob('*.parquet'))

    def migrate_legacy_partitions(self):
        """Offline, exclusive migration. Retry after interruption before reading analytics.

        Canonical rows and legacy rows reconcile by maximum batch appearances.
        Original files remain until all canonical publications have succeeded.
        """
        with file_lock(self.base_dir / '.storage.lock'):
            files = self.get_all_parquet_paths()
            merged = {}
            legacy = []
            for path in files:
                rows = _normalize(pq.read_table(path).to_pylist())
                _merge(merged, rows)
                if path.relative_to(self.base_dir).parts[0] != 'canonical':
                    legacy.append(path)
            if not legacy:
                return 0
            self._publish(merged)
            for path in legacy:
                path.unlink()
            return len(legacy)
