"""Offline, synthetic two-cycle/restart/deadline evidence. No production key or network."""
import argparse
import importlib.metadata
import json
import platform
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from collector.continuous_collector import ContinuousCollector
from core.hasher import PrivacyHasher
from scripts.privacy_audit import audit_directory
from storage.duckdb_engine import DuckDBAnalyticsEngine


class Clock:
    def __init__(self): self.now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    def __call__(self): return self.now


class SyntheticComments:
    def __init__(self, viewers=('synthetic-one',), delay=0):
        self.viewers, self.delay = viewers, delay
    def collect_aggregated_events(self, job, max_comments=150):
        time.sleep(self.delay)
        return [{'viewer_hash': PrivacyHasher('offline-verification-only').hash_viewer_id(viewer),
                 **{k: job[k] for k in ('vtuber_channel_id', 'video_id', 'source_type')},
                 'first_seen': '2026-09-01T00:00:00Z', 'last_seen': '2026-09-01T00:00:00Z',
                 'appearances': 2} for viewer in self.viewers]


def verify():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        clock = Clock()
        args = dict(storage_dir=root/'events', journal_path=root/'jobs.sqlite3',
                    hasher=PrivacyHasher('offline-verification-only'), clock=clock,
                    poll_interval_seconds=10, max_workers=1)
        c = ContinuousCollector(**args, comment_collector=SyntheticComments())
        c.plan_and_register_jobs([{'channel_id': 'SYNTHETIC_CHANNEL', 'video_id': 'SYNTHETIC_VIDEO'}])
        first = c.run_bounded_cycle()
        assert first['status_breakdown'] == {'SUCCESS': 1}
        assert c.journal.claim_next_job('early') is None
        clock.now += timedelta(seconds=10)
        c = ContinuousCollector(**args, comment_collector=SyntheticComments(('synthetic-one','synthetic-two')))
        second = c.run_bounded_cycle()
        assert second['status_breakdown'] == {'SUCCESS': 1}
        engine = DuckDBAnalyticsEngine(root/'analytics.duckdb', root/'events')
        rows = engine.get_viewer_presence_summary()
        engine.close()
        assert len(rows) == 2 and sum(r['appearances'] for r in rows) == 4
        clock.now += timedelta(seconds=10)
        c = ContinuousCollector(**args, comment_collector=SyntheticComments(delay=0.25))
        timeout = c.run_bounded_cycle(max_cycle_seconds=0.01)
        assert timeout['status_breakdown'] == {'TIMEOUT': 1}
        assert timeout['elapsed_seconds'] < 0.25
        time.sleep(0.3)
        assert c.journal.get_summary()['states'] == {'RETRY': 1}
        audit = audit_directory(root, ('synthetic-one', 'synthetic-two'))
        assert all(r['status'] in {'PASS', 'LOCK_FILE', 'SIDECAR'} for r in audit)
        for row in audit:
            row['file'] = str(Path(row['file']).relative_to(root))
        return {'evidence_type': 'synthetic_offline', 'python': platform.python_version(),
                'platform': platform.platform(),
                'versions': {name: importlib.metadata.version(name) for name in
                             ('pytest','pyarrow','duckdb','yt-dlp','requests','pandas')},
                'production_key_present': (BASE_DIR/'config'/'secret.key').exists(),
                'first_cycle': first, 'second_cycle_after_restart': second,
                'unique_presence_rows': len(rows), 'sum_max_batch_appearances': 4,
                'timeout_cycle': timeout, 'audit': audit,
                'limitations': 'Synthetic evidence only; no real collection. Deadline permits process teardown and synchronous filesystem/journal commit latency.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = json.dumps(verify(), indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result+'\n', encoding='utf-8')
    print(result)
