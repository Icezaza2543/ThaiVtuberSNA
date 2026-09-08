"""The suite never needs an owner's API credentials or a live network."""
import socket
import pytest


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    monkeypatch.setenv('YOUTUBE_API_KEY', '')
    monkeypatch.setattr('collector.youtube_collector.YOUTUBE_API_KEY', '')
    monkeypatch.setattr('collector.live_chat_adapter.YOUTUBE_API_KEY', '')
    def blocked(*args, **kwargs):
        raise AssertionError('Unexpected network access in offline test suite')
    monkeypatch.setattr(socket.socket, 'connect', blocked)


@pytest.fixture
def synthetic_pipeline_data(monkeypatch):
    """Seed temporal integration tests without the owner's key or private Parquet."""
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq
    import scripts.build_duckdb_temporal_snapshots as snapshots
    import scripts.incremental_temporal_pipeline as incremental
    import scripts.observatory_controller as observatory
    from core.hasher import PrivacyHasher, compute_key_fingerprint
    key=b'offline-temporal-integration-fixture-key'
    monkeypatch.setattr(incremental,'load_persistent_secret_key',lambda:key)
    monkeypatch.setattr(observatory,'load_persistent_secret_key',lambda:key)
    monkeypatch.setattr(observatory,'EXPECTED_HMAC_KEY_FINGERPRINT','sha256_'+compute_key_fingerprint(key))
    def seed(root):
        hasher=PrivacyHasher(key);rows=[]
        channels=['UCpGtwNmbOtgmcKIY81MIX_w','UCGBkYTR4tMKS38TQHGWWLjg']
        for year in (2020,2021,2026):
            for i,channel in enumerate(channels):
                rows.append(dict(viewer_hash=hasher.hash_viewer_id('synthetic-'+str(year)),
                    vtuber_channel_id=channel,video_id=f'fixture_{year}_{i}',source_type='comment',
                    interaction_at=f'{year}-01-01T00:00:00Z',video_published_at=f'{year}-01-01T00:00:00Z'))
        rows.append(dict(viewer_hash=hasher.hash_viewer_id('synthetic-overlay'),
            vtuber_channel_id='UCompe4fS2oUss8CGTuhOSxA',video_id='oEOHgyuLgrA',source_type='comment',
            interaction_at='2026-01-01T00:00:00Z',video_published_at='2026-01-01T00:00:00Z'))
        target=root/'data/temporal/deep_observations/fixture.parquet'
        target.parent.mkdir(parents=True,exist_ok=True);pq.write_table(pa.Table.from_pylist(rows),target)
        monkeypatch.setattr(snapshots,'DATA_DIR',root/'data')
        con=duckdb.connect(':memory:')
        snapshots.build_unified_raw_view(con,snapshots.get_sources_by_provenance(root))
        snapshots.build_canonical_events_view(con)
        windows=[dict(type='yearly',start=f'{y}-01-01',end=f'{y}-12-31 23:59:59') for y in range(2020,2027)]
        windows += [dict(type='cumulative',start='2020-01-01',end=f'{y}-12-31 23:59:59') for y in range(2021,2027)]
        windows += [dict(type='all_time',start='2020-01-01',end='2026-12-31 23:59:59')]
        result=[row for w in windows for row in snapshots.compute_window_snapshots(con,w,{},'canonical_events','fixture')]
        path=root/'data/temporal/snapshots/network_snapshots.parquet';path.parent.mkdir(parents=True,exist_ok=True)
        pq.write_table(pa.Table.from_pylist(result,schema=snapshots.NETWORK_SNAPSHOT_SCHEMA),path)
        con.close()
        monkeypatch.setattr(observatory,'EXPECTED_HISTORICAL_BASELINE_HASH',observatory.compute_historical_baseline_hash(path))
        return root
    return seed
