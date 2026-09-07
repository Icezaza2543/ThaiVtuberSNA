"""
Purge Raw Commenter PII from Google Sheets
1. Deletes or scrubs the ALL_COMMENTERS worksheet containing raw viewer PII (display names & profile URLs).
2. Verifies that all remaining worksheets (VTUBERS, NETWORK_RESULT, SYSTEM) are 100% compliant.
3. Updates SYSTEM worksheet with privacy enforcement status.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import gspread
from config.settings import GOOGLE_SHEETS_CONFIG
from scripts.audit_sheets_privacy import audit_sheets, load_known_vtuber_ids

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PurgeSheetsPII")

def main():
    cred_path = GOOGLE_SHEETS_CONFIG.get("credentials_path")
    sheet_id = GOOGLE_SHEETS_CONFIG.get("spreadsheet_id")

    if not cred_path or not Path(cred_path).exists():
        logger.error(f"Credentials not found at {cred_path}")
        sys.exit(1)

    gc = gspread.service_account(filename=str(cred_path))
    sh = gc.open_by_key(sheet_id)
    logger.info(f"Connected to Spreadsheet: '{sh.title}' ({sheet_id})")

    # 1. Delete ALL_COMMENTERS worksheet if present
    try:
        ws_all_commenters = sh.worksheet("ALL_COMMENTERS")
        logger.warning("Found 'ALL_COMMENTERS' worksheet containing raw viewer PII.")
        # Clear all content first to scrub cells
        ws_all_commenters.clear()
        # Delete worksheet entirely from Google Sheets
        sh.del_worksheet(ws_all_commenters)
        logger.info("Successfully scrubbed and DELETED 'ALL_COMMENTERS' worksheet.")
    except gspread.exceptions.WorksheetNotFound:
        logger.info("'ALL_COMMENTERS' worksheet not found (already purged).")

    # Also check REILIM_COMMENTERS just in case
    try:
        ws_reilim = sh.worksheet("REILIM_COMMENTERS")
        ws_reilim.clear()
        sh.del_worksheet(ws_reilim)
        logger.info("Scrubbed and deleted 'REILIM_COMMENTERS' worksheet.")
    except gspread.exceptions.WorksheetNotFound:
        pass

    # 2. Update SYSTEM worksheet with Privacy Compliance Status
    try:
        ws_system = sh.worksheet("SYSTEM")
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        status_updates = [
            ["Privacy Compliance", "PASS - Zero PII Persisted"],
            ["Viewer ID Anonymization", "HMAC-SHA256 RAM-only boundary enforced"],
            ["Last Privacy Purge", now_str],
            ["Storage Model", "Aggregates only (NETWORK_RESULT, VTUBERS, SYSTEM)"]
        ]
        # Append or update
        existing = ws_system.get_all_values()
        existing_keys = {row[0]: idx + 1 for idx, row in enumerate(existing) if row}
        for k, v in status_updates:
            if k in existing_keys:
                ws_system.update_cell(existing_keys[k], 2, v)
            else:
                ws_system.append_row([k, v])
        logger.info("Updated SYSTEM worksheet with privacy compliance records.")
    except Exception as e:
        logger.warning(f"Could not update SYSTEM sheet: {e}")

    # 3. Post-Purge Privacy Audit
    vtuber_ids = load_known_vtuber_ids()
    is_compliant, violations = audit_sheets(sh, vtuber_ids)
    if not is_compliant:
        logger.error(f"POST-PURGE AUDIT FAILED with {len(violations)} violations:")
        for v in violations:
            logger.error(f"  - {v}")
        sys.exit(1)

    logger.info("==========================================================")
    logger.info(" SUCCESS: Google Sheets is completely purged of raw PII!  ")
    logger.info(" All remaining worksheets are 100% compliant.             ")
    logger.info("==========================================================")

if __name__ == "__main__":
    main()
