"""Read-only policy audit: viewer data is authorized here; credentials are not."""
import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.data_security import assert_sheet_rows, PRIVATE_TABS, CONTROL_TABS
from storage.private_sheet_store import PrivateSheetStore, column_name


def local_secret_values():
    """Values stay in memory and are never included in findings."""
    from config.settings import SECRET_KEY_PATH, YOUTUBE_API_KEY, GOOGLE_SHEETS_CONFIG
    values = []
    if SECRET_KEY_PATH.exists(): values.append(SECRET_KEY_PATH.read_text().strip())
    if YOUTUBE_API_KEY: values.append(YOUTUBE_API_KEY)
    path = Path(GOOGLE_SHEETS_CONFIG['credentials_path'])
    if path.exists():
        obj = json.loads(path.read_text())
        values += [str(obj[k]) for k in ('private_key','client_secret','refresh_token') if obj.get(k)]
    return values


def audit_private_sheet(spreadsheet, known_secrets=()):
    store = PrivateSheetStore(spreadsheet, known_secrets=known_secrets)
    findings, tabs, hashes = [], [], set()
    for ws in spreadsheet.worksheets():
        end = column_name(ws.col_count)
        header = store._write(ws.get_values, f'A1:{end}1')
        headers = header[0] if header else []
        count = 0
        if ws.title not in PRIVATE_TABS | CONTROL_TABS:
            findings.append({'tab': ws.title, 'status': 'WARNING', 'reason': 'UNREGISTERED_TAB'})
        try: assert_sheet_rows(headers, [], known_secrets)
        except ValueError as error:
            findings.append({'tab': ws.title, 'status': 'FAIL', 'reason': str(error)})
        size = min(5000, max(1, 45000//ws.col_count))
        for start in range(2, ws.row_count+1, size):
            rows = store._write(ws.get_values, f'A{start}:{end}{min(ws.row_count,start+size-1)}')
            count += sum(any(cell for cell in row) for row in rows)
            if 'viewer_hash' in headers:
                index=headers.index('viewer_hash')
                hashes.update(row[index] for row in rows if len(row)>index and row[index])
            try: assert_sheet_rows(headers, rows, known_secrets)
            except ValueError as error:
                findings.append({'tab': ws.title, 'start_row': start, 'status': 'FAIL', 'reason': str(error)})
        tabs.append({'tab': ws.title, 'rows': count, 'columns': len(headers)})
    root=Path(__file__).resolve().parent.parent
    public_files=0
    for directory in ('web','releases','dist'):
        for path in (root/directory).rglob('*'):
            if not path.is_file():continue
            public_files+=1
            candidates=set(re.findall(r'\b[a-f0-9]{64}\b',path.read_bytes().decode('utf-8',errors='replace')))
            if candidates & hashes:
                findings.append({'path':path.relative_to(root).as_posix(),'status':'FAIL','reason':'KNOWN_PRIVATE_PSEUDONYM_IN_PUBLIC_OUTPUT'})
    status = 'FAIL' if any(x['status']=='FAIL' for x in findings) else 'WARNING' if findings else 'PASS'
    return {'status': status, 'tabs': tabs, 'findings': findings,
            'public_output_files_compared_to_private_hashes':public_files,
            'policy': 'LEVEL_B allowed in authorized private workbook; LEVEL_A forbidden',
            'access_notice': 'Anyone granted workbook access may potentially access private viewer tabs.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    parser.parse_args()
    report = audit_private_sheet(PrivateSheetStore().spreadsheet, local_secret_values())
    print(json.dumps(report, indent=2))
    return 1 if report['status']=='FAIL' else 0


if __name__ == '__main__': sys.exit(main())
