"""Compatibility audit for the authorized single-sheet PRIVATE data plane."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.audit_private_data_plane import audit_private_sheet, main, local_secret_values


def load_known_vtuber_ids():
    import csv
    from config.settings import DATA_DIR
    path = DATA_DIR/'thai_vtuber_registry.csv'
    if not path.exists(): return set()
    return {row.get('channel_id','') for row in csv.DictReader(path.open(encoding='utf-8-sig'))}


def audit_sheets(sh, vtuber_ids=None):
    result = audit_private_sheet(sh, local_secret_values())
    return result['status'] != 'FAIL', result['findings']


if __name__ == '__main__': sys.exit(main())
