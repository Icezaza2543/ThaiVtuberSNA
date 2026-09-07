"""
Merge REILIM_COMMENTERS into ALL_COMMENTERS (100% In-Memory Google Sheets Operation)

1. Reads ALL_COMMENTERS (12,878 rows) and REILIM_COMMENTERS (1,055 rows) from Google Sheets.
2. Merges and deduplicates profiles:
   - Combines comment counts.
   - Ensures 'Reilim Channel' is in channels_active.
   - Preserves latest last_seen timestamp.
   - Adds 911 historical commenters from Reilim.
3. Resizes and updates ALL_COMMENTERS worksheet in Google Sheets.
4. Removes redundant REILIM_COMMENTERS worksheet.
5. Updates SYSTEM worksheet with new statistics.
6. Zero files stored on local disk.
"""
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import gspread
from config.settings import GOOGLE_SHEETS_CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MergeCommenters")

def col_to_letter(col_idx: int) -> str:
    result = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result

def safe_update_sheet(ws, data_rows, batch_size: int = 2000):
    if not data_rows:
        return

    needed_rows = max(100, len(data_rows) + 50)
    needed_cols = max(10, max(len(r) for r in data_rows))
    
    current_rows = ws.row_count
    current_cols = ws.col_count

    if current_rows < needed_rows or current_cols < needed_cols:
        target_r = max(current_rows, needed_rows)
        target_c = max(current_cols, needed_cols)
        logger.info(f"Resizing worksheet '{ws.title}' to {target_r} rows, {target_c} cols...")
        ws.resize(rows=target_r, cols=target_c)
        time.sleep(1)

    ws.clear()
    time.sleep(0.5)

    num_cols = len(data_rows[0])
    end_col_str = col_to_letter(num_cols)
    total_chunks = (len(data_rows) + batch_size - 1) // batch_size
    logger.info(f"Writing {len(data_rows)} rows to '{ws.title}' in {total_chunks} chunks...")

    for i, b in enumerate(range(0, len(data_rows), batch_size)):
        chunk = data_rows[b:b + batch_size]
        range_label = f"A{b+1}:{end_col_str}{b+len(chunk)}"
        ws.update(range_name=range_label, values=chunk)
        if total_chunks > 1 and i < total_chunks - 1:
            time.sleep(0.8)

    ws.format(f"A1:{end_col_str}1", {"textFormat": {"bold": True}})

def main():
    logger.info("Connecting to Google Sheets...")
    cred_path = GOOGLE_SHEETS_CONFIG.get("credentials_path")
    sheet_id = GOOGLE_SHEETS_CONFIG.get("spreadsheet_id")
    gc = gspread.service_account(filename=str(cred_path))
    sh = gc.open_by_key(sheet_id)

    ws_all = sh.worksheet("ALL_COMMENTERS")
    ws_reilim = sh.worksheet("REILIM_COMMENTERS")

    logger.info("Fetching existing records from ALL_COMMENTERS and REILIM_COMMENTERS...")
    all_records = ws_all.get_all_records()
    reilim_records = ws_reilim.get_all_records()

    logger.info(f"Loaded {len(all_records)} from ALL_COMMENTERS, {len(reilim_records)} from REILIM_COMMENTERS.")

    # Dictionary keyed by authorChannelUrl (fallback to displayName)
    merged_map: Dict[str, Dict[str, Any]] = {}

    for row in all_records:
        key = row.get("authorChannelUrl") or row.get("authorDisplayName")
        if not key:
            continue
        channels = [c.strip() for c in str(row.get("channels_active", "")).split(",") if c.strip()]
        merged_map[key] = {
            "authorDisplayName": row.get("authorDisplayName", ""),
            "authorChannelUrl": row.get("authorChannelUrl", ""),
            "comment_count": int(row.get("comment_count", 0) or 0),
            "channels_set": set(channels),
            "last_seen": str(row.get("last_seen", ""))
        }

    reilim_channel_name = "Reilim Channel"
    reilim_merged_count = 0
    reilim_added_count = 0

    for r in reilim_records:
        key = r.get("authorChannelUrl") or r.get("authorDisplayName")
        if not key:
            continue

        r_count = int(r.get("comment_count", 0) or 0)
        r_last = str(r.get("last_seen", ""))
        r_name = r.get("authorDisplayName", "")
        r_url = r.get("authorChannelUrl", "")

        if key in merged_map:
            # Overlapping user: combine comments and add Reilim to channels
            reilim_merged_count += 1
            merged_map[key]["comment_count"] += r_count
            merged_map[key]["channels_set"].add(reilim_channel_name)
            if r_last > merged_map[key]["last_seen"]:
                merged_map[key]["last_seen"] = r_last
            if not merged_map[key]["authorDisplayName"] and r_name:
                merged_map[key]["authorDisplayName"] = r_name
        else:
            # New unique user from Reilim's historical archives
            reilim_added_count += 1
            merged_map[key] = {
                "authorDisplayName": r_name,
                "authorChannelUrl": r_url,
                "comment_count": r_count,
                "channels_set": {reilim_channel_name},
                "last_seen": r_last
            }

    logger.info(f"Merge Complete: {reilim_merged_count} existing commenters updated, {reilim_added_count} new commenters added.")
    logger.info(f"Total Unified Commenters: {len(merged_map)}")

    # Sort descending by comment_count
    sorted_commenters = sorted(merged_map.values(), key=lambda x: x["comment_count"], reverse=True)

    header = ["authorDisplayName", "authorChannelUrl", "comment_count", "channels_active", "last_seen"]
    sheet_data = [header]

    for item in sorted_commenters:
        sorted_channels = sorted(list(item["channels_set"]))
        ch_str = ", ".join(sorted_channels[:3])
        if len(sorted_channels) > 3:
            ch_str += f" (+{len(sorted_channels)-3} others)"
        
        sheet_data.append([
            item["authorDisplayName"],
            item["authorChannelUrl"],
            item["comment_count"],
            ch_str,
            item["last_seen"]
        ])

    # Update ALL_COMMENTERS
    logger.info("Writing merged data to ALL_COMMENTERS...")
    safe_update_sheet(ws_all, sheet_data, batch_size=2000)

    # Delete redundant REILIM_COMMENTERS tab
    logger.info("Deleting redundant 'REILIM_COMMENTERS' worksheet...")
    sh.del_worksheet(ws_reilim)
    logger.info("Deleted 'REILIM_COMMENTERS' worksheet successfully.")

    # Update SYSTEM sheet
    try:
        ws_sys = sh.worksheet("SYSTEM")
        sys_vals = ws_sys.get_all_values()
        updated_sys = []
        found = False
        for r in sys_vals:
            if len(r) >= 2 and r[0] == "Total Unique Commenters":
                updated_sys.append(["Total Unique Commenters", f"{len(merged_map):,} people (Merged with Reilim Archive)"])
                found = True
            else:
                updated_sys.append(r)
        if not found:
            updated_sys.append(["Total Unique Commenters", f"{len(merged_map):,} people"])
        safe_update_sheet(ws_sys, updated_sys, batch_size=100)
        logger.info("Updated 'SYSTEM' status sheet.")
    except Exception as e:
        logger.warning(f"Could not update SYSTEM sheet: {e}")

    logger.info("==========================================================")
    logger.info(f" SUCCESS: ALL_COMMENTERS is now the single master sheet! ")
    logger.info(f" Total Commenters: {len(merged_map):,}                        ")
    logger.info("==========================================================")

if __name__ == "__main__":
    main()
