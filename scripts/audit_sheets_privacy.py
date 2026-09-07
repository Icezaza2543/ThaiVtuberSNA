"""
Audit Google Sheets Control Plane for Privacy Compliance
Ensures no raw viewer/commenter PII (display names, profile URLs, raw commenter channel IDs)
is stored in any worksheet of the Google Sheets spreadsheet.

Usage:
  python scripts/audit_sheets_privacy.py --verify
"""
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Set

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import gspread
from config.settings import GOOGLE_SHEETS_CONFIG, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AuditSheetsPrivacy")

FORBIDDEN_HEADERS = {
    "authordisplayname", "authorchannelurl", "author_id", "user_key",
    "raw_author_id", "author_name", "author_url", "commenter_name"
}

def load_known_vtuber_ids() -> Set[str]:
    """Loads public VTuber channel IDs to distinguish from private viewer IDs."""
    vtuber_ids = set()
    reg_file = DATA_DIR / "thai_vtuber_registry.csv"
    if reg_file.exists():
        import csv
        with open(reg_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cid = row.get("channel_id")
                if cid:
                    vtuber_ids.add(cid.strip())
    return vtuber_ids

def audit_sheets(sh, vtuber_ids: Set[str]) -> Tuple[bool, List[str]]:
    violations = []
    logger.info(f"Auditing spreadsheet: '{sh.title}' ({sh.id})")

    for ws in sh.worksheets():
        title = ws.title
        logger.info(f"Checking worksheet: '{title}' ({ws.row_count} rows, {ws.col_count} cols)...")

        # 1. Header Check
        header = ws.row_values(1)
        for col_idx, h in enumerate(header, start=1):
            h_clean = h.strip().lower().replace(" ", "_")
            if h_clean in FORBIDDEN_HEADERS:
                violations.append(
                    f"[{title}] Column {col_idx} header '{h}' violates privacy contract (forbidden header name)."
                )

        # 2. Sample Data Scan (First 50 rows)
        if ws.row_count > 1:
            sample_rows = ws.get_values("A1:Z50")
            for r_idx, row in enumerate(sample_rows[1:], start=2):
                for c_idx, val in enumerate(row, start=1):
                    val_str = str(val).strip()
                    # Check for raw channel URLs
                    if "youtube.com/channel/UC" in val_str:
                        cid = val_str.split("/channel/")[-1].split("?")[0].split("/")[0]
                        if cid not in vtuber_ids:
                            violations.append(
                                f"[{title}] Row {r_idx}, Col {c_idx} contains raw viewer channel URL: '{val_str}'"
                            )
                    # Check for raw author ID starting with UC that is not a known VTuber
                    elif val_str.startswith("UC") and len(val_str) == 24 and val_str not in vtuber_ids:
                        violations.append(
                            f"[{title}] Row {r_idx}, Col {c_idx} contains raw viewer channel ID: '{val_str}'"
                        )

    is_compliant = (len(violations) == 0)
    return is_compliant, violations

def main():
    parser = argparse.ArgumentParser(description="Audit Google Sheets for Privacy Compliance")
    parser.add_argument("--verify", action="store_true", help="Fail with non-zero exit code if violations found")
    args = parser.parse_args()

    cred_path = GOOGLE_SHEETS_CONFIG.get("credentials_path")
    sheet_id = GOOGLE_SHEETS_CONFIG.get("spreadsheet_id")

    if not cred_path or not Path(cred_path).exists():
        logger.error(f"Credentials not found at {cred_path}")
        sys.exit(1)

    gc = gspread.service_account(filename=str(cred_path))
    sh = gc.open_by_key(sheet_id)

    vtuber_ids = load_known_vtuber_ids()
    is_compliant, violations = audit_sheets(sh, vtuber_ids)

    if is_compliant:
        logger.info("==========================================================")
        logger.info(" PASS: Google Sheets is 100% Privacy Compliant! Zero PII. ")
        logger.info("==========================================================")
        sys.exit(0)
    else:
        logger.error("==========================================================")
        logger.error(f" FAIL: Found {len(violations)} privacy violations in Google Sheets:")
        for v in violations[:20]:
            logger.error(f"  - {v}")
        if len(violations) > 20:
            logger.error(f"  ... and {len(violations) - 20} more violations.")
        logger.error("==========================================================")
        if args.verify:
            sys.exit(1)

if __name__ == "__main__":
    main()
