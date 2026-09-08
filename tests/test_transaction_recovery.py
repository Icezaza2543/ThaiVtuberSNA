import json
import shutil
from datetime import datetime, timezone
import pandas as pd
import pytest
from scripts import incremental_temporal_pipeline as module


@pytest.mark.parametrize('point', list('ABCDE'))
def test_every_commit_boundary_recovers_to_clean_bytes(point, tmp_path, synthetic_pipeline_data, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(module, 'datetime', Clock)
    clean = synthetic_pipeline_data(tmp_path / 'clean')
    crashed = tmp_path / 'crashed'
    shutil.copytree(clean, crashed)
    events = [dict(author_id='synthetic-crash-boundary',vtuber_channel_id=c,
                   video_id='synthetic-crash-' + c,interaction_time='2027-01-01T00:00:00Z')
              for c in ('UCpGtwNmbOtgmcKIY81MIX_w','UCGBkYTR4tMKS38TQHGWWLjg')]
    module.IncrementalTemporalPipeline(clean).ingest_batch('crash_boundaries', events)
    pipeline = module.IncrementalTemporalPipeline(crashed)
    with pytest.raises(RuntimeError, match='CRASH_' + point):
        pipeline.ingest_batch('crash_boundaries', events, crash_at=point)
    recovered = module.IncrementalTemporalPipeline(crashed)
    recovered.ingest_batch('crash_boundaries', events)
    for rel in ('incremental/batch_crash_boundaries.parquet','snapshots/network_snapshots.parquet',
                'state/pipeline_state.json','state/release_manifest.json'):
        assert (clean/'data/temporal'/rel).read_bytes() == (crashed/'data/temporal'/rel).read_bytes(), rel
    state = json.loads(recovered.state_file.read_text())
    assert state['processed_batches']['crash_boundaries']['records_inserted'] == 2
    assert not recovered.transaction.journal.exists()


def test_stale_pipeline_instance_reloads_state(tmp_path, synthetic_pipeline_data):
    root = synthetic_pipeline_data(tmp_path)
    first = module.IncrementalTemporalPipeline(root)
    stale = module.IncrementalTemporalPipeline(root)
    events = [dict(author_id='synthetic-stale',vtuber_channel_id='channel_a',video_id='video_a',
                   interaction_time='2027-01-01T00:00:00Z')]
    first.ingest_batch('same_batch', events)
    assert stale.ingest_batch('same_batch',events).status == 'ALREADY_PROCESSED'


def test_shared_writer_lock_is_reentrant_but_excludes_other_threads(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from core.file_transaction import exclusive_lock
    path = tmp_path/'writer.lock'
    def competing_writer():
        with exclusive_lock(path):
            raise AssertionError('A competing writer acquired the active transaction lock')
    with exclusive_lock(path), exclusive_lock(path), ThreadPoolExecutor(max_workers=1) as executor:
        with pytest.raises(OSError):
            executor.submit(competing_writer).result()
