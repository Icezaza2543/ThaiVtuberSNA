"""Prevent retired production paths from recreating local private datasets.

Explicit external temporary paths remain usable for synthetic/offline tests.
Real private ingestion must use PrivateSheetStore; T20 has not been released.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def require_synthetic_local_path(path):
    resolved = Path(path).resolve()
    if resolved.is_relative_to(REPO_ROOT):
        raise RuntimeError('Local private project storage is retired. Use the existing Google Sheets private data plane. T20 remains on hold.')


def require_t20_sandbox(base_dir):
    if Path(base_dir).resolve() == REPO_ROOT:
        raise RuntimeError('T20 is on hold: production ingestion/release must be adapted to the private Sheet transaction model before resuming.')
