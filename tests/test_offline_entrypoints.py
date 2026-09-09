"""Consolidated entry point must never dispatch production work for offline modes."""
import json
import subprocess
import sys
from scripts import analysis_dag


def test_dag_listing_does_not_execute(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError('Production runner called')
    monkeypatch.setattr(analysis_dag, 'run_dag', forbidden)
    assert analysis_dag.main(['--list']) == 0
    assert [r['step'] for r in json.loads(capsys.readouterr().out)] == [r[0] for r in analysis_dag.DAG]


def test_offline_audit_dispatch_excludes_workbook(monkeypatch):
    from scripts import audit_research_v2_consistency, audit_data_security, privacy_audit
    from storage.private_sheet_store import PrivateSheetStore
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline entry point accessed production/local private data')
    monkeypatch.setattr(PrivateSheetStore, '__init__', forbidden)
    monkeypatch.setattr(analysis_dag, 'run_dag', forbidden)
    monkeypatch.setattr(audit_data_security, 'audit_local', forbidden)
    monkeypatch.setattr(audit_research_v2_consistency, 'main', lambda: 0)
    monkeypatch.setattr(privacy_audit, 'run_canary_leakage_test', lambda: True)
    monkeypatch.setattr(audit_data_security, 'audit_git', lambda: {'status': 'PASS', 'findings': []})
    assert analysis_dag.main(['--audit']) == 0
    monkeypatch.setattr(privacy_audit, 'run_canary_leakage_test', lambda: False)
    assert analysis_dag.main(['--audit']) == 1


def test_direct_and_module_cli_list_agree():
    a = subprocess.check_output([sys.executable, 'scripts/analysis_dag.py', '--list'])
    b = subprocess.check_output([sys.executable, '-m', 'scripts.analysis_dag', '--list'])
    assert json.loads(a) == json.loads(b)
