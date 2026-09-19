"""Compatibility audit for the authorized single-sheet PRIVATE data plane."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog
from scripts.audit_private_data_plane import audit_private_sheet, main, local_secret_values


def load_known_vtuber_ids():
    return {
        row["platform_id"]
        for row in CreatorCatalog.from_path(CREATOR_REGISTRY_PATH).youtube_accounts()
        if row.get("platform_id")
    }


def audit_sheets(sh, vtuber_ids=None):
    result = audit_private_sheet(sh, local_secret_values())
    return result["status"] != "FAIL", result["findings"]


if __name__ == "__main__":
    sys.exit(main())
