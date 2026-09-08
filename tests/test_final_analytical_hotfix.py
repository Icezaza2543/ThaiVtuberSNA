import pandas as pd
import pytest
from scripts import analyze_evidence_quality as quality
from scripts import build_technical_report as report


def test_recall_uses_intersection_even_when_evidence_population_is_larger():
    r = quality.channel_recall(['a','b','c','d'], ['a','z'], ['a','b','z'])
    assert r == dict(interaction_evidence_channel_count=4, catalog_published_channel_count=2,
                     intersection_count=1, catalog_active_recall=0.5, target_manifest_coverage=2/3)


def test_modality_reads_exact_t10_configuration_and_changed_values(tmp_path):
    df = pd.read_parquet(quality.T10_SENSITIVITY)
    chosen = quality.modality_comparison()
    assert chosen['nmi_to_baseline'] == 0.8733
    assert chosen['ari_to_baseline'] == 0.8878
    df.loc[chosen.name, 'nmi_to_baseline'] = 0.4321
    path = tmp_path / 't10.parquet'; df.to_parquet(path)
    assert quality.modality_comparison(path)['nmi_to_baseline'] == 0.4321


def test_main_report_survival_exact_for_every_horizon():
    content = report.build_technical_report()
    rows = [line.split('|')[1:-1] for line in content.splitlines() if line.startswith('| +')]
    df = pd.read_parquet(report.COHORT_SURVIVAL)
    assert len(rows) == len(df)
    for cells, row in zip(rows, df.itertuples()):
        assert int(cells[0].strip().split()[0]) == row.elapsed_years
        assert int(cells[1]) == row.pooled_cohort_size
        assert int(cells[2]) == row.pooled_reobserved_viewers
        assert float(cells[3]) == row.persistence_rate
        assert float(cells[4]) == row.same_channel_persistence_rate
        assert float(cells[5]) == row.cross_channel_persistence_rate


def test_report_rejects_missing_survival_column(tmp_path, monkeypatch):
    df = pd.read_parquet(report.COHORT_SURVIVAL).drop(columns=['pooled_cohort_size'])
    path = tmp_path / 'bad.parquet'; df.to_parquet(path)
    monkeypatch.setattr(report, 'COHORT_SURVIVAL', path)
    with pytest.raises(ValueError, match='pooled_cohort_size'):
        report.build_technical_report()
