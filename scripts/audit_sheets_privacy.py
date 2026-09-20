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
    findings = list(result["findings"])
    canonical_ids = set(vtuber_ids) if vtuber_ids is not None else load_known_vtuber_ids()
    try:
        worksheet = sh.worksheet("VTUBERS")
        records = worksheet.get_all_records()
        sheet_ids = {
            str(row.get("channel_id", "")).strip()
            for row in records
            if str(row.get("channel_id", "")).strip()
        }
        unknown = sorted(sheet_ids - canonical_ids)
        missing = sorted(canonical_ids - sheet_ids)
        if unknown:
            findings.append({
                "tab": "VTUBERS",
                "status": "FAIL",
                "reason": "SHEET_CHANNEL_OUTSIDE_CANONICAL_CATALOG",
                "count": len(unknown),
            })
        if missing:
            findings.append({
                "tab": "VTUBERS",
                "status": "WARNING",
                "reason": "CANONICAL_CHANNEL_NOT_IN_SHEET_EXPORT",
                "count": len(missing),
            })
    except Exception as exc:
        findings.append({
            "tab": "VTUBERS",
            "status": "WARNING",
            "reason": f"VTUBERS_SHEET_COMPARISON_UNAVAILABLE:{type(exc).__name__}",
        })
    ok = not any(row.get("status") == "FAIL" for row in findings)
    return ok, findings


if __name__ == "__main__":
    sys.exit(main())
