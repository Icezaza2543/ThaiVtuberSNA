"""Two bounded real polls into a new dataset, using a verified existing local key."""
import argparse
import importlib.metadata
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--identity-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--timeout', type=float, default=45)
    args = parser.parse_args()
    # Read only the API setting; never copy keys or print credential values.
    env_file = args.identity_root/'.env'
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            key, separator, value = line.partition('=')
            if separator and key.strip() == 'YOUTUBE_API_KEY':
                os.environ.setdefault('YOUTUBE_API_KEY', value.strip().strip('\"\''))
    import core.hasher as identity
    identity.SECRET_KEY_PATH = args.identity_root/'config'/'secret.key'
    identity.SECRET_FINGERPRINT_PATH = args.identity_root/'config'/'secret.fingerprint'
    hasher = identity.PrivacyHasher()
    from collector.continuous_collector import ContinuousCollector
    from scripts.run_continuous_collection import DEFAULT_CANDIDATE_POOL
    from scripts.privacy_audit import audit_directory
    import pyarrow.parquet as pq

    output = args.output.resolve()
    if output.exists():
        raise RuntimeError('Use a new output directory for each real verification run')
    options = dict(storage_dir=output/'events', journal_path=output/'jobs.sqlite3',
                   hasher=hasher, poll_interval_seconds=10, max_workers=2)
    candidates = DEFAULT_CANDIDATE_POOL[:2]
    collector = ContinuousCollector(**options)
    jobs = collector.plan_and_register_jobs(candidates, sources=['comment', 'live_chat'])
    report = {'evidence_type': 'real_network', 'started_at': datetime.now(timezone.utc).isoformat(),
              'channels': [{'channel_id': c['channel_id'], 'video_id': c['video_id']} for c in candidates],
              'api_configured': collector.live_chat_adapter.is_available(), 'cycles': []}
    report['runtime_versions'] = {name: importlib.metadata.version(name) for name in
                                  ('google-api-python-client', 'google-api-core', 'requests', 'pyarrow', 'duckdb')}
    snapshots = []
    for cycle in range(2):
        if cycle:
            # A real clock and a newly constructed collector exercise durable recurrence.
            time.sleep(11)
            collector = ContinuousCollector(**options)
            collector.plan_and_register_jobs(candidates, sources=['comment', 'live_chat'])
        summary = collector.run_bounded_cycle(max_jobs_to_process=4, max_events_per_job=30,
                                             max_cycle_seconds=args.timeout)
        rows = [row for path in (output/'events').rglob('*.parquet')
                for row in pq.read_table(path).to_pylist()]
        keys = {(r['viewer_hash'],r['vtuber_channel_id'],r['video_id'],r['source_type']) for r in rows}
        snapshots.append(keys)
        entry = {'cycle': cycle+1, 'summary': summary, 'presence_rows': len(rows),
                 'unique_presence_rows': len(keys),
                 'sum_max_batch_appearances': sum(r['appearances'] for r in rows),
                 'partition_count': len(list((output/'events').rglob('*.parquet'))),
                 'job_states': [{k: collector.journal.get_job(jid)[k] for k in
                                ('job_id','state','last_outcome','attempts','poll_generation',
                                 'last_success_at','next_collection_at')} for jid in jobs]}
        report['cycles'].append(entry)
        print(json.dumps(entry), flush=True)
        (output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    report['previous_presence_preserved'] = snapshots[0] <= snapshots[1]
    report['new_presence_in_second_poll'] = len(snapshots[1]-snapshots[0])
    report['comment_recurrence_verified'] = bool(snapshots[0]) and all(
        job['state'] == 'COMPLETED' and job['poll_generation'] >= 1
        for job in report['cycles'][-1]['job_states'] if job['job_id'].endswith(':comment'))
    audit = audit_directory(output)
    for item in audit:
        item['file'] = str(Path(item['file']).relative_to(output))
    report['audit'] = audit
    report['audit_passed'] = all(item['status'] in {'PASS','LOCK_FILE','SIDECAR'} for item in audit)
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    (output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'report_path': str(output/'report.json'),
                      'audit_passed': report['audit_passed'],
                      'previous_presence_preserved': report['previous_presence_preserved'],
                      'new_presence_in_second_poll': report['new_presence_in_second_poll']}), flush=True)


if __name__ == '__main__':
    main()
