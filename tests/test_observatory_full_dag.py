import hashlib
import json
import shutil
import os
from pathlib import Path
import pandas as pd
import pytest
from scripts.analysis_dag import ROOT, run_dag, public_artifact_paths, analysis_context, rebuild_canonical_snapshots
from scripts.observatory_controller import ObservatoryController


def save_evidence(name, result):
    directory = os.environ.get('SNA_HOTFIX_EVIDENCE_DIR')
    if directory:
        path = Path(directory)/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,indent=2),encoding='utf-8')




def checksums(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in public_artifact_paths(root)}


def test_future_update_full_dag_publish_and_exact_rollback(full_sandbox):
    root = full_sandbox
    ctrl = ObservatoryController(root)
    before = checksums(root)
    state_before = ctrl.obs_state_file.read_bytes()
    pipeline_state = root/'data/temporal/state/pipeline_state.json'
    pipeline_before = pipeline_state.read_bytes() if pipeline_state.exists() else None
    events = [dict(author_id='synthetic-future-integration',vtuber_channel_id=c,
                   video_id='future-' + str(i),interaction_time='2027-02-01T00:00:00Z')
              for i,c in enumerate(('UCpGtwNmbOtgmcKIY81MIX_w','UCGBkYTR4tMKS38TQHGWWLjg'))]
    result = ctrl.update('future_complete',events)
    assert result['status'] == 'SUCCESS'
    assert result['version_after'] == 'v1.1.0'
    for rel, field in [('analysis/community_snapshots.parquet','year'),
                       ('analysis/community_lineage_v2.parquet','to_year'),
                       ('cohorts/cohort_retention_matrix.parquet','observation_year'),
                       ('centrality/yearly_centrality.parquet','year'),
                       ('ecosystem/yearly_ecosystem_metrics.parquet','year'),
                       ('quality/yearly_evidence_quality.parquet','year')]:
        df = pd.read_parquet(root/'data/temporal'/rel)
        assert 2027 in set(df[field]), rel
    dashboard = json.loads((root/'web/research/dashboard_data.json').read_text(encoding='utf-8'))
    assert 2027 in dashboard['meta']['years']
    assert any(r['year'] == 2027 for r in dashboard['ecosystem']['yearly_metrics'])
    after = pd.read_parquet(root/'data/temporal/snapshots/network_snapshots.parquet')
    assert int(after[after.window_type == 'all_time'].shared_any.iloc[0]) == 16
    assert set(after[after.window_end.str.startswith('2027')].window_type) == {'yearly','cumulative','all_time'}
    assert checksums(root) != before
    ctrl.rollback(result['run_id'])
    assert checksums(root) == before
    restored = pd.read_parquet(root/'data/temporal/snapshots/network_snapshots.parquet')
    assert int(restored[restored.window_type == 'all_time'].shared_any.iloc[0]) == 15
    assert ctrl.obs_state_file.read_bytes() == state_before
    assert (pipeline_state.read_bytes() if pipeline_state.exists() else None) == pipeline_before
    assert not (root/'data/temporal/incremental/batch_future_complete.parquet').exists()
    save_evidence('hotfix_full_e2e.json',dict(status='PASS',input_kind='synthetic',
        downstream_skipped=False,year=2027,version_after_update=result['version_after'],
        shared_before=15,shared_after=16,shared_after_rollback=15,
        public_files_restored=len(before),all_public_checksums_restored=True,
        observatory_state_restored=True,pipeline_state_restored=True,batch_absent_after_rollback=True,
        before_checksums={k:'sha256_'+v for k,v in before.items()}))


def test_reproduce_two_clean_roots_from_same_inputs(full_sandbox):
    from scripts.reproduce_temporal_dataset import reproduce_twice
    evidence = reproduce_twice(full_sandbox)
    assert evidence['status'] == 'REPRODUCIBLE_FROM_INPUTS', evidence['differences']
    assert len(evidence['artifact_hashes']) >= 25
    assert {'T7','T12','T19'} <= set(evidence['pipeline_steps'])
    save_evidence('hotfix_synthetic_reproducibility.json',dict(evidence,input_kind='synthetic'))


def test_snapshot_rebuild_preserves_existing_window_contract(full_sandbox):
    path = full_sandbox/'data/temporal/snapshots/network_snapshots.parquet'
    cols = ['window_type','window_start','window_end']
    before = set(pd.read_parquet(path)[cols].itertuples(index=False,name=None))
    with analysis_context(full_sandbox):
        rebuild_canonical_snapshots(full_sandbox)
    after = set(pd.read_parquet(path)[cols].itertuples(index=False,name=None))
    assert after == before


def test_failure_after_downstream_write_restores_whole_generation(full_sandbox, monkeypatch):
    ctrl = ObservatoryController(full_sandbox)
    before = checksums(full_sandbox)
    state_before = ctrl.obs_state_file.read_bytes()
    from scripts import analyze_audience_cohorts as cohorts
    original = cohorts.run_audience_cohort_analysis
    def fail_after_cohorts():
        original()
        raise RuntimeError('synthetic failure after T12 output')
    monkeypatch.setattr(cohorts,'run_audience_cohort_analysis',fail_after_cohorts)
    with pytest.raises(RuntimeError,match='after T12'):
        ctrl.update('failed_downstream',[dict(author_id='synthetic-failure',vtuber_channel_id='synthetic-channel',
                                            video_id='synthetic-failure',interaction_time='2027-01-01T00:00:00Z')])
    assert checksums(full_sandbox) == before
    assert ctrl.obs_state_file.read_bytes() == state_before
    assert not (full_sandbox/'data/temporal/incremental/batch_failed_downstream.parquet').exists()


def test_controller_recovers_nested_ingestion_crash(full_sandbox, monkeypatch):
    from scripts.incremental_temporal_pipeline import IncrementalTemporalPipeline
    ctrl = ObservatoryController(full_sandbox)
    before = checksums(full_sandbox)
    original = IncrementalTemporalPipeline._ingest_batch
    def crash(self, *args, **kwargs):
        return original(self,*args,**kwargs,crash_at='C')
    monkeypatch.setattr(IncrementalTemporalPipeline,'_ingest_batch',crash)
    with pytest.raises(RuntimeError,match='CRASH_C'):
        ctrl.update('nested_crash',[dict(author_id='synthetic-nested',vtuber_channel_id='synthetic-channel',
                                       video_id='synthetic-nested',interaction_time='2027-01-01T00:00:00Z')])
    assert checksums(full_sandbox) == before
    assert not (full_sandbox/'data/temporal/state/.ingestion_transaction').exists()
    assert not (full_sandbox/'data/temporal/incremental/batch_nested_crash.parquet').exists()
