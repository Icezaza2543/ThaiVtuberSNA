"""Safe sync to the existing private/control workbook; no clear/delete operations.

Whole-tab rewrite and hard-coded counts are retired. Recovery uses
migrate_private_data_plane. Running this entry point verifies the current data.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.audit_private_data_plane import main
from storage.private_sheet_store import PrivateSheetStore


def sync_private_table(title, headers, rows):
    return PrivateSheetStore().write_verified_table(title, headers, rows)


if __name__ == '__main__': sys.exit(main())
