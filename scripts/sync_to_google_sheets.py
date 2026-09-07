"""
Sync Local SNA & Commenter Data to Google Sheets Control Plane
Creates and populates:
1. VTUBERS (1,372 VTuber channels)
2. NETWORK_RESULT (Audience overlap connections)
3. REILIM_COMMENTERS (1,055 unique commenters with handles & URLs)
4. SYSTEM (System status, timestamps, and key fingerprint)
"""
import sys
import csv
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import gspread
from config.settings import GOOGLE_SHEETS_CONFIG, DATA_DIR
from core.hasher import compute_key_fingerprint, load_persistent_secret_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyncGoogleSheets")

def get_or_create_worksheet(spreadsheet, title, rows=1000, cols=20):
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        logger.info(f"Creating worksheet: {title}")
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

def main():
    cred_path = GOOGLE_SHEETS_CONFIG["credentials_path"]
    sheet_id = GOOGLE_SHEETS_CONFIG["spreadsheet_id"]

    logger.info("==========================================================")
    logger.info(" Syncing Thai VTuber SNA Data to Google Sheets            ")
    logger.info("==========================================================")
    logger.info(f"Connecting using: {cred_path}")

    gc = gspread.service_account(filename=cred_path)
    sh = gc.open_by_key(sheet_id)
    logger.info(f"Opened Spreadsheet: '{sh.title}' ({sheet_id})")

    # -------------------------------------------------------------
    # 1. REILIM_COMMENTERS Sheet (1,055 unique commenters)
    # -------------------------------------------------------------
    commenters_csv = DATA_DIR / "reilim_commenters.csv"
    if commenters_csv.exists():
        logger.info("Syncing REILIM_COMMENTERS sheet...")
        ws_commenters = get_or_create_worksheet(sh, "REILIM_COMMENTERS", rows=1200, cols=6)
        with open(commenters_csv, "r", encoding="utf-8-sig") as f:
            reader = list(csv.reader(f))
        
        ws_commenters.clear()
        # Update in chunks or all at once
        ws_commenters.update(range_name=f"A1:E{len(reader)}", values=reader)
        # Format header row bold
        ws_commenters.format("A1:E1", {"textFormat": {"bold": True}})
        logger.info(f" -> Successfully synced {len(reader)-1} commenters to 'REILIM_COMMENTERS'!")

    # -------------------------------------------------------------
    # 2. NETWORK_RESULT Sheet
    # -------------------------------------------------------------
    report_json = DATA_DIR / "reilim_relationship_report.json"
    if report_json.exists():
        logger.info("Syncing NETWORK_RESULT sheet...")
        ws_network = get_or_create_worksheet(sh, "NETWORK_RESULT", rows=100, cols=6)
        with open(report_json, "r", encoding="utf-8") as f:
            rep = json.load(f)

        network_rows = [["Channel A", "Channel B", "Shared Viewers", "Strong Shared (Multi-Video)", "Calculated At"]]
        calc_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Inter-channel overlaps
        for item in rep.get("inter_channel_overlaps", []):
            network_rows.append([
                item.get("channel_a", ""),
                item.get("channel_b", ""),
                item.get("shared_any", 0),
                item.get("strong_shared_any", 0),
                calc_at
            ])

        # All pilot overlaps
        all_ov = rep.get("all_overlaps", [])
        for item in all_ov:
            pair = item.get("pair", "")
            if "<->" in pair:
                ca, cb = pair.split("<->")
                ca, cb = ca.strip(), cb.strip()
                # Skip if already in list
                if not any((r[0] == ca and r[1] == cb) or (r[0] == cb and r[1] == ca) for r in network_rows[1:]):
                    network_rows.append([ca, cb, item.get("shared_any", 0), item.get("strong_shared_any", 0), calc_at])

        ws_network.clear()
        ws_network.update(range_name=f"A1:E{len(network_rows)}", values=network_rows)
        ws_network.format("A1:E1", {"textFormat": {"bold": True}})
        logger.info(f" -> Successfully synced {len(network_rows)-1} relationship pairs to 'NETWORK_RESULT'!")

    # -------------------------------------------------------------
    # 3. VTUBERS Sheet (Active registry)
    # -------------------------------------------------------------
    registry_csv = DATA_DIR / "registry_vtubers.csv"
    if registry_csv.exists():
        logger.info("Syncing VTUBERS registry sheet...")
        ws_vtubers = get_or_create_worksheet(sh, "VTUBERS", rows=1500, cols=15)
        with open(registry_csv, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
        
        ws_vtubers.clear()
        # Upload in batches of 500 rows to avoid request payload limits
        batch_size = 500
        for i in range(0, len(reader), batch_size):
            chunk = reader[i:i + batch_size]
            start_row = i + 1
            end_row = i + len(chunk)
            ws_vtubers.update(range_name=f"A{start_row}:N{end_row}", values=chunk)
        
        ws_vtubers.format("A1:N1", {"textFormat": {"bold": True}})
        logger.info(f" -> Successfully synced {len(reader)-1} VTubers to 'VTUBERS'!")

    # -------------------------------------------------------------
    # 4. SYSTEM Sheet (Monitoring metadata)
    # -------------------------------------------------------------
    logger.info("Syncing SYSTEM status sheet...")
    ws_system = get_or_create_worksheet(sh, "SYSTEM", rows=20, cols=3)
    key_fingerprint = compute_key_fingerprint(load_persistent_secret_key())
    
    system_rows = [
        ["Metric", "Value"],
        ["Project", "Thai VTuber Audience Network (SNA)"],
        ["Control Plane", "Google Sheets Live Sync"],
        ["Last Synced", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")],
        ["HMAC Key Fingerprint", key_fingerprint],
        ["Total Commenters Extracted (Reilim)", "1,055 unique viewers"],
        ["Total Registered VTubers", "1,372 channels"],
        ["Monitored Real Channels", "8 channels"],
        ["Storage Engine", "Parquet + DuckDB OLAP"],
        ["Privacy Mode", "HMAC-SHA256 (Zero PII Persisted in Analytics)"]
    ]
    ws_system.clear()
    ws_system.update(range_name=f"A1:B{len(system_rows)}", values=system_rows)
    ws_system.format("A1:B1", {"textFormat": {"bold": True}})
    logger.info(" -> Successfully synced system metadata to 'SYSTEM'!")

    # Remove empty default 'ชีต1' if present and other sheets exist
    try:
        sheet1 = sh.worksheet("ชีต1")
        if len(sh.worksheets()) > 1:
            sh.del_worksheet(sheet1)
            logger.info("Removed empty default sheet 'ชีต1'.")
    except Exception:
        pass

    logger.info("==========================================================")
    logger.info(" Google Sheets Sync Finished Successfully!               ")
    logger.info(f" URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    logger.info("==========================================================")

if __name__ == "__main__":
    main()
