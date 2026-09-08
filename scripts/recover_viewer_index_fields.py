"""
Thai VTuber Audience Network (SNA)
Idempotent Recovery of VIEWER_INDEX Missing Fields

Fills missing fields in the existing VIEWER_INDEX worksheet:
- channels_observed_count: Recovered from ALL_COMMENTERS!channels_active
- first_seen: Recovered from ALL_COMMENTERS!last_seen (earliest observed interaction timestamp)

Strictly adheres to:
- No LEVEL-A credentials in Google Sheets
- No raw identity fabrication or HMAC inversion
- Preserves all existing non-empty fields
- Bounded batch updates with readback verification
"""
import sys
import os
import re
import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import gspread
from config.settings import GOOGLE_SHEETS_CONFIG
from core.data_security import SPREADSHEET_ID, assert_sheet_rows
from storage.private_sheet_store import column_name

def parse_channel_names(ch_str: str):
    if not ch_str:
        return set(), 0
    other_matches = re.findall(r'\(\+(\d+)\s+others\)', ch_str)
    extra_count = sum(int(x) for x in other_matches)
    cleaned = re.sub(r'\(\+\d+\s+others\)', '', ch_str).strip()
    parts = [p.strip() for p in cleaned.split(',') if p.strip()]
    return set(parts), len(parts) + extra_count

def build_recovery_map(all_commenters_rows):
    by_url = {}
    for r in all_commenters_rows:
        if len(r) < 5:
            continue
        name, url, count, ch_str, last = r[:5]
        if not url:
            continue
        by_url.setdefault(url, []).append({
            'name': name,
            'count': int(count or 0),
            'ch_str': ch_str,
            'last': last
        })
        
    recovery_map = {}
    for url, entries in by_url.items():
        timestamps = [e['last'] for e in entries if e['last']]
        first_seen = min(timestamps) if timestamps else ''
        last_seen = max(timestamps) if timestamps else ''
        
        if len(entries) == 1:
            names, total_ch = parse_channel_names(entries[0]['ch_str'])
            channel_count = total_ch
        else:
            all_names = set()
            max_ch = 0
            for e in entries:
                names, total_ch = parse_channel_names(e['ch_str'])
                all_names.update(names)
                if total_ch > max_ch:
                    max_ch = total_ch
            channel_count = max(max_ch, len(all_names))
            
        recovery_map[url] = {
            'first_seen': first_seen,
            'last_seen': last_seen,
            'channel_count': channel_count
        }
    return recovery_map

def main():
    print("=== STARTING VIEWER_INDEX FIELD RECOVERY ===")
    cred_path = GOOGLE_SHEETS_CONFIG['credentials_path']
    gc = gspread.service_account(filename=cred_path)
    sh = gc.open_by_key(SPREADSHEET_ID)
    
    # 1. Read ALL_COMMENTERS to build recovery map
    print("Reading ALL_COMMENTERS...")
    ws_all = sh.worksheet('ALL_COMMENTERS')
    all_commenters_rows = ws_all.get_all_values()[1:]
    recovery_map = build_recovery_map(all_commenters_rows)
    print(f"Loaded recovery map for {len(recovery_map)} unique handle URLs.")
    
    # 2. Read VIEWER_INDEX header and Group 1 rows (rows 2 to 28763)
    ws_vindex = sh.worksheet('VIEWER_INDEX')
    total_sheet_rows = ws_vindex.row_count
    total_sheet_cols = ws_vindex.col_count
    print(f"VIEWER_INDEX dimension: {total_sheet_rows} x {total_sheet_cols}")
    
    headers = ws_vindex.get_values('A1:J1')[0]
    print(f"Headers: {headers}")
    assert headers == [
        'viewer_hash', 'raw_channel_id', 'display_name', 'channel_url',
        'first_seen', 'last_seen', 'total_interactions',
        'channels_observed_count', 'recovery_source', 'recovery_status'
    ], f"Unexpected headers: {headers}"
    
    # Fetch Group 1 (rows 2 to 28763)
    group1_count = 28762
    print(f"Fetching Group 1 rows (2 to {group1_count + 1})...")
    g1_rows = ws_vindex.get_values(f'A2:J{group1_count + 1}')
    print(f"Fetched {len(g1_rows)} rows from Group 1.")
    
    updates_col_e = []  # first_seen
    updates_col_h = []  # channels_observed_count
    
    recovered_first_seen_count = 0
    recovered_channels_count = 0
    
    for idx, r in enumerate(g1_rows):
        if len(r) < 10:
            r = r + [''] * (10 - len(r))
        url = r[3].strip()
        existing_first_seen = r[4].strip()
        existing_ch_count = r[7].strip()
        
        rec = recovery_map.get(url)
        if not rec:
            updates_col_e.append([existing_first_seen])
            updates_col_h.append([existing_ch_count])
            continue
            
        # Recover first_seen if empty
        if not existing_first_seen and rec['first_seen']:
            new_first_seen = rec['first_seen']
            recovered_first_seen_count += 1
        else:
            new_first_seen = existing_first_seen
            
        # Recover channels_observed_count if empty
        if not existing_ch_count and rec['channel_count'] > 0:
            new_ch_count = str(rec['channel_count'])
            recovered_channels_count += 1
        else:
            new_ch_count = existing_ch_count
            
        updates_col_e.append([new_first_seen])
        updates_col_h.append([new_ch_count])
        
    print(f"Prepared updates: first_seen={recovered_first_seen_count}, channels_observed_count={recovered_channels_count}")
    
    # Security assert: ensure no credentials/secrets in updates
    from scripts.audit_private_data_plane import local_secret_values
    known_secrets = local_secret_values()
    assert_sheet_rows(['first_seen'], updates_col_e, known_secrets)
    assert_sheet_rows(['channels_observed_count'], updates_col_h, known_secrets)
    
    # 3. Apply updates in chunks of 5000 rows
    chunk_size = 5000
    for start_idx in range(0, group1_count, chunk_size):
        end_idx = min(group1_count, start_idx + chunk_size)
        start_row = start_idx + 2
        end_row = end_idx + 1
        print(f"Updating rows {start_row} to {end_row}...")
        
        chunk_e = updates_col_e[start_idx:end_idx]
        chunk_h = updates_col_h[start_idx:end_idx]
        
        ws_vindex.update(values=chunk_e, range_name=f'E{start_row}:E{end_row}', value_input_option='RAW')
        time.sleep(1)
        ws_vindex.update(values=chunk_h, range_name=f'H{start_row}:H{end_row}', value_input_option='RAW')
        time.sleep(1)
        
    print("Group 1 updates completed successfully.")
    
    # 4. Perform complete readback verification
    print("Starting full table readback verification (108,480 rows)...")
    readback_rows = []
    chunk_size_read = 10000
    for start in range(2, total_sheet_rows + 1, chunk_size_read):
        end = min(total_sheet_rows, start + chunk_size_read - 1)
        chunk = ws_vindex.get_values(f'A{start}:J{end}')
        for r in chunk:
            if len(r) < 10:
                r = r + [''] * (10 - len(r))
            readback_rows.append(r[:10])
        print(f"  Read back rows up to {end}...")
        
    assert len(readback_rows) == 108480, f"Expected 108480 rows, got {len(readback_rows)}"
    
    # Checksum calculation
    content_json = json.dumps([headers] + readback_rows, ensure_ascii=False, separators=(',', ':'))
    new_sha256 = hashlib.sha256(content_json.encode('utf-8')).hexdigest()
    print(f"Post-recovery VIEWER_INDEX Checksum: {new_sha256}")
    
    # Compute AFTER audit stats
    stats = {h: {'TOTAL_ROWS': len(readback_rows), 'NON_EMPTY': 0, 'MISSING': 0, 'INVALID': 0} for h in headers}
    for r in readback_rows:
        for i, h in enumerate(headers):
            val = r[i].strip() if i < len(r) else ''
            if not val:
                stats[h]['MISSING'] += 1
            else:
                stats[h]['NON_EMPTY'] += 1
                if h == 'viewer_hash' and not re.match(r'^[0-9a-f]{64}$', val):
                    stats[h]['INVALID'] += 1
                elif h == 'raw_channel_id' and not re.match(r'^UC[A-Za-z0-9_-]{22}$', val):
                    stats[h]['INVALID'] += 1
                elif h in ('total_interactions', 'channels_observed_count'):
                    try:
                        n = int(float(val))
                        if n < 0:
                            stats[h]['INVALID'] += 1
                    except ValueError:
                        stats[h]['INVALID'] += 1
                        
    print("\n==========================================")
    print("AFTER AUDIT METRICS PER FIELD")
    print("==========================================")
    for h in headers:
        s = stats[h]
        pct = (s['NON_EMPTY'] / s['TOTAL_ROWS']) * 100 if s['TOTAL_ROWS'] else 0
        print(f"{h:25s} | TOTAL: {s['TOTAL_ROWS']:6d} | NON_EMPTY: {s['NON_EMPTY']:6d} ({pct:5.1f}%) | MISSING: {s['MISSING']:6d} | INVALID: {s['INVALID']:5d}")
        
    summary_path = ROOT / "docs" / "evidence" / "viewer_index_after_summary.json"
    summary_path.write_text(json.dumps(stats, indent=2), encoding='utf-8')
    print(f"\nSaved after audit summary to {summary_path}")
    
    # 5. Update RECOVERY_METADATA tab
    print("\nUpdating RECOVERY_METADATA...")
    ws_meta = sh.worksheet('RECOVERY_METADATA')
    now_iso = datetime.now(timezone.utc).isoformat()
    meta_updates = [
        ['viewer_index_rows', '108480'],
        ['viewer_index_channels_observed_recovered', str(recovered_channels_count)],
        ['viewer_index_first_seen_recovered', str(recovered_first_seen_count)],
        ['viewer_index_channels_observed_total_populated', str(stats['channels_observed_count']['NON_EMPTY'])],
        ['viewer_index_first_seen_total_populated', str(stats['first_seen']['NON_EMPTY'])],
        ['viewer_index_post_recovery_sha256', new_sha256],
        ['viewer_index_recovery_completed_at', now_iso]
    ]
    
    existing_meta = ws_meta.get_all_values()
    existing_keys = {row[0]: idx + 1 for idx, row in enumerate(existing_meta) if row}
    
    for k, v in meta_updates:
        if k in existing_keys:
            ws_meta.update_cell(existing_keys[k], 2, v)
        else:
            ws_meta.append_row([k, v])
            
    print("RECOVERY_METADATA updated successfully.")
    print("\n=== VIEWER_INDEX FIELD RECOVERY COMPLETED SUCCESSFULLY ===")

if __name__ == '__main__':
    main()
