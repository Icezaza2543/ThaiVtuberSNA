"""Targeted SYSTEM and data dictionary updates; no worksheet clearing/deletion."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from storage.private_sheet_store import PrivateSheetStore
from core.data_security import assert_sheet_rows


def main():
    report=json.loads((ROOT/'docs/evidence/private_data_migration.json').read_text())
    stats=report['recovery'];store=PrivateSheetStore()
    ws=store.spreadsheet.worksheet('SYSTEM')
    values=store._write(ws.get_values,'A1:B25')
    updates={
        3:['Status','Private-data recovery complete; T20 ON HOLD'],
        7:['Historical commenter records','38,240 recovered rows; 28,762 distinct URL candidates; 9,478 duplicate URL rows'],
        11:['Storage Policy','LEVEL A: local/external credentials. LEVEL B: existing private workbook. LEVEL C: public research artifacts.'],
        13:['Privacy Model','Viewer-level data restricted to project workbook; public research exports contain aggregates and public channel/video metadata'],
        14:['Viewer Identity Model','Original HMAC-SHA256 continuity; pseudonyms are PRIVATE_DATA, not anonymous public data'],
        15:['Historical Purge (superseded)','2026-09-07 18:03:47 UTC; destructive purge retired; revision 380 recovered'],
        16:['Storage Model','Google Sheets Private Data Plane + GitHub Public Research Artifacts'],
        17:['Private Viewer Storage','ALL_COMMENTERS / VIEWER_INDEX / VIEWER_CHANNEL_PRESENCE / VIEWER_ACTIVITY_SUMMARY / PRIVATE_DATA_ARCHIVE'],
        18:['Credential Storage','Local environment / encrypted local storage / secret manager; NEVER Google Sheets or Git'],
        19:['Workbook Access','Anyone granted workbook access may potentially access private viewer tabs.'],
        20:['T20 Status','ON HOLD; production collection/publication has not been started'],
        21:['HMAC Fingerprint',stats['hmac_fingerprint']],
        22:['Recovery Source','Drive revision 380 (missing viewer dataset only); verified local private archives'],
        23:['Canonical Hash Identities',str(stats['canonical_hash_identities_preserved'])],
        24:['Historical Raw IDs Reconstructed',str(stats['viewer_hash_identities_reconstructed'])],
        25:['Unmatched Historical Handles',str(stats['unmatched_handle_candidates'])],
    }
    for row,record in updates.items():
        assert_sheet_rows(['Metric','Value'],[record],store.known_secrets)
        store._write(ws.update,range_name=f'A{row}:B{row}',values=[record],value_input_option='RAW')
    actual=store._write(ws.get_values,'A1:B25')
    if any(actual[row-1]!=record for row,record in updates.items()):raise RuntimeError('SYSTEM readback mismatch')
    if any(actual[i]!=values[i] for i in (0,1,3,4,5,7,8,9,11)):raise RuntimeError('Unrelated SYSTEM cells changed')
    dictionary=store.spreadsheet.worksheet('DATA_DICTIONARY')
    entries=store._write(dictionary.get_values,'A2:D31')
    descriptions={
        'viewer_hash':'Deterministic HMAC under the original project key; PRIVATE pseudonym, never public. Blank for unresolved historical handles.',
        'raw_channel_id':'Verified raw UC channel ID only. Historical revision 380 contains handles, so this is blank for those candidates.',
        'authorChannelUrl':'Original historical handle/profile URL, preserved verbatim; does not prove an immutable raw channel ID.',
        'channel_url':'Historical handle URL candidate; not a verified immutable raw ID.',
        'comment_count':'Historical reported count, preserved verbatim in ALL_COMMENTERS; duplicate snapshots are not summed.',
        'total_interactions':'Canonical rows for HASH_ONLY entries (distinct viewer/channel/video/source presence); maximum historical count per URL for unresolved candidates. Not a verified lifetime message count.',
        'interaction_count':'Number of canonical viewer/channel/video/source presence records. Not a raw message count.',
        'channels_observed_count':'Distinct channels in canonical evidence. Blank for unresolved historical candidates.',
        'channels_active':'Original historical presentation string; may be truncated and cannot establish an exact channel count.',
        'first_seen':'Earliest available canonical interaction timestamp; blank when unknown.',
        'last_seen':'Latest available observation; original historical timestamp text is retained for historical candidates.',
        'source_types_seen':'Comma-separated comment/live_chat evidence types; source sets can overlap.',
        'recovery_source':'Revision 380 or existing canonical HMAC observations. These populations are not assumed matched.',
        'recovery_status':'UNRESOLVED_HANDLE, RAW_ID_RECONSTRUCTED, or HASH_ONLY_RAW_ID_UNAVAILABLE; blank identities are never invented.',
        'first_observed_year':'Earliest year with a known canonical interaction timestamp; blank if all timestamps are unknown.',
        'last_observed_year':'Latest year with a known canonical interaction timestamp; blank if unknown.',
        'active_year_count':'Count of distinct observed interaction years; does not imply continuous attendance.',
        'channel_count':'Number of distinct channels in canonical evidence.',
        'source_path':'Original relative dataset path. Archived worktree, synthetic and unverified data retain separate provenance.',
        'source_table':'Original table name or parquet; source copies are not independently additive.',
        'row_number':'One-based row position within the original source table.',
        'record_json':'Original structured observation/control record; no raw comment/chat text. Analytics includes only explicitly approved provenance paths.',
        'display_name':'Historical presentation label; never used as an identity merge key.',
        'authorDisplayName':'Original historical presentation label, preserved verbatim and never used as a merge key.',
    }
    changed=[[descriptions.get(r[1],'Private row attribute; workbook access controls apply to the entire workbook.')] for r in entries]
    store._write(dictionary.update,range_name='D2:D31',values=changed,value_input_option='RAW')
    if store._write(dictionary.get_values,'D2:D31')!=changed:raise RuntimeError('Dictionary readback mismatch')
    (ROOT/'docs/evidence/private_control_update.json').write_text(json.dumps({'status':'PASS','system_rows_updated':list(updates),
        'dictionary_descriptions_updated':len(changed),'unrelated_system_rows_preserved':True},indent=2))
    print('SYSTEM_AND_DICTIONARY_VERIFIED')


if __name__=='__main__':main()
