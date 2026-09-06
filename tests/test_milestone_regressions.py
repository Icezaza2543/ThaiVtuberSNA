import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
from core.hasher import PrivacyHasher, compute_key_fingerprint, load_persistent_secret_key, init_persistent_secret_key
from collector.youtube_collector import YouTubeCollector
from storage.parquet_manager import ParquetStorageManager
from storage.duckdb_engine import DuckDBAnalyticsEngine
from analytics.network_graph import VTuberNetworkAnalyzer
from analytics.exporter import NetworkExporter
from scripts.privacy_audit import audit_file, run_canary_leakage_test


def event(channel='A', video='a1', source='comment', viewer='one'):
    return dict(viewer_hash=PrivacyHasher('test-only').hash_viewer_id(viewer),
        vtuber_channel_id=channel, video_id=video, source_type=source,
        timestamp='2026-09-01T00:00:00Z')


@pytest.fixture
def key_paths(tmp_path, monkeypatch):
    key, fingerprint = tmp_path / 'secret.key', tmp_path / 'secret.fingerprint'
    monkeypatch.setattr('core.hasher.SECRET_KEY_PATH', key)
    monkeypatch.setattr('core.hasher.SECRET_FINGERPRINT_PATH', fingerprint)
    return key, fingerprint


def test_environment_cannot_bypass_missing_key(key_paths, monkeypatch):
    monkeypatch.setattr('core.hasher.SALT_SECRET', 'override')
    with pytest.raises(RuntimeError, match='missing'):
        load_persistent_secret_key()
    assert not key_paths[0].exists()


def test_restart_continuity_and_no_force_rotation(key_paths):
    init_persistent_secret_key()
    first = PrivacyHasher().hash_viewer_id('viewer')
    assert PrivacyHasher().hash_viewer_id('viewer') == first
    with pytest.raises(RuntimeError):
        init_persistent_secret_key(force=True)
    key_paths[1].unlink()
    with pytest.raises(RuntimeError, match='Missing key fingerprint'):
        load_persistent_secret_key()


def test_existing_fingerprint_prevents_reinitialization(key_paths):
    key_paths[1].write_text('prior-identity')
    with pytest.raises(RuntimeError):
        init_persistent_secret_key()
    assert not key_paths[0].exists()


def test_missing_key_precedes_network(key_paths, monkeypatch):
    monkeypatch.setattr('collector.youtube_collector.YOUTUBE_API_KEY', 'would-build-api-client')
    with pytest.raises(RuntimeError, match='missing'):
        YouTubeCollector()


def test_aggregation_separates_sources_and_counts_distinct_videos(tmp_path):
    records = []
    for channel in ('A', 'B'):
        for video in ('1', '2'):
            records += [event(channel, channel+video, 'comment')]*4
        # Same viewer, same video, two evidence sources, only one live video.
        records += [event(channel, channel+'1', 'live_chat')]*8
    aggregate = YouTubeCollector.collect_aggregated_events(SimpleNamespace(collect_events=lambda *a, **k: records), {})
    assert len(aggregate) == 6
    mgr = ParquetStorageManager(tmp_path / 'events')
    for video in {r['video_id'] for r in aggregate}:
        mgr.write_events([r for r in aggregate if r['video_id'] == video])
    engine = DuckDBAnalyticsEngine(tmp_path/'a.duckdb', tmp_path/'events')
    pair = engine.compute_pairwise_overlap()[0]
    assert [pair[k] for k in ('shared_any', 'shared_comments', 'shared_live_chat')] == [1, 1, 1]
    assert [pair[k] for k in ('strong_shared_any', 'strong_shared_comments', 'strong_shared_live_chat')] == [1, 1, 0]
    summary = engine.get_viewer_presence_summary()[0]
    assert summary['videos_seen'] == 2 and summary['live_streams_seen'] == 1
    assert 'streams_seen' not in summary
    graph = VTuberNetworkAnalyzer().build_graph([{'channel_id':'A'},{'channel_id':'B'}],[pair])
    exported = json.loads(NetworkExporter(tmp_path).export_web_json(graph).read_text())
    for key in ('shared_any','shared_live_chat','shared_comments','strong_shared_any','strong_shared_live_chat','strong_shared_comments'):
        assert exported['edges'][0][key] == pair[key]
    engine.close()


def test_raw_aggregated_mixed_schema_and_source_writes_survive(tmp_path):
    mgr = ParquetStorageManager(tmp_path/'events')
    one = mgr.write_events([event()])
    aggregated = event(source='live_chat')
    aggregated.update(first_seen=aggregated.pop('timestamp'), last_seen='2026-09-01T00:00:00Z', appearances=3)
    two = mgr.write_events([aggregated])
    assert one != two and one.exists() and two.exists()
    engine = DuckDBAnalyticsEngine(tmp_path/'db.duckdb', tmp_path/'events')
    summary = engine.get_viewer_presence_summary()[0]
    assert summary['videos_seen'] == summary['live_streams_seen'] == 1
    assert summary['appearances'] == 4
    engine.close()


def test_empty_database_summary(tmp_path):
    engine = DuckDBAnalyticsEngine(tmp_path/'db.duckdb', tmp_path/'empty')
    assert engine.get_viewer_presence_summary() == []
    assert engine.compute_pairwise_overlap() == []
    engine.close()


@pytest.mark.parametrize('threshold', [0, 1, 3, '2 OR 1=1'])
def test_strong_definition_cannot_be_weakened(tmp_path, threshold):
    engine = DuckDBAnalyticsEngine(tmp_path/'db.duckdb', tmp_path/'empty')
    with pytest.raises(ValueError):
        engine.compute_pairwise_overlap(min_evidence_threshold=threshold)
    engine.close()


@pytest.mark.parametrize('source', [None, '', 'unknown'])
def test_missing_source_is_never_inferred(tmp_path, source):
    with pytest.raises(ValueError):
        ParquetStorageManager(tmp_path).write_events([event(source=source)])


def test_corrupt_parquet_fails_closed(tmp_path):
    path = tmp_path/'bad.parquet'
    path.write_bytes(b'not parquet')
    assert audit_file(path)['status'] in {'ERROR', 'FAIL'}
    with pytest.raises(Exception):
        DuckDBAnalyticsEngine(tmp_path/'db.duckdb', tmp_path)


def test_audit_decodes_compressed_values_and_duckdb(tmp_path):
    canary = 'PRIVATE_CANARY_VALUE'
    path = tmp_path/'leak.parquet'
    pq.write_table(pa.table({'innocent': [canary]*100}),path,compression='snappy')
    assert audit_file(path,(canary,))['status'] == 'FAIL'
    import duckdb
    db = tmp_path/'leak.duckdb'
    con = duckdb.connect(str(db))
    con.execute('CREATE TABLE bad AS SELECT ? AS author_id', [canary])
    con.close()
    assert audit_file(db)['status'] == 'FAIL'


def test_collector_to_disk_canary():
    assert run_canary_leakage_test()


def test_no_raw_replay_download():
    from scripts.test_live_chat_empirically import extract_live_chat_in_memory
    with pytest.raises(NotImplementedError):
        extract_live_chat_in_memory('video')
