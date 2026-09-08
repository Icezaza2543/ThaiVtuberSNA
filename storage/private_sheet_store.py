"""Single authorized private workbook. No spreadsheet creation or tab deletion API."""
import hashlib
import json
import time
from core.data_security import (SPREADSHEET_ID, SPREADSHEET_TITLE, PRIVATE_TABS,
                                CONTROL_TABS, assert_sheet_rows)


def column_name(number):
    result = ''
    while number:
        number, rem = divmod(number-1, 26)
        result = chr(65+rem) + result
    return result


class PrivateSheetStore:
    def __init__(self, spreadsheet=None, *, known_secrets=None, request_interval=1.05):
        if spreadsheet is None:
            import gspread
            from config.settings import GOOGLE_SHEETS_CONFIG
            configured = GOOGLE_SHEETS_CONFIG.get('spreadsheet_id')
            if configured and configured != SPREADSHEET_ID:
                raise RuntimeError('Wrong configured spreadsheet; only ThaiVtuber_SNA is authorized')
            spreadsheet = gspread.service_account(filename=GOOGLE_SHEETS_CONFIG['credentials_path']).open_by_key(SPREADSHEET_ID)
        if spreadsheet.id != SPREADSHEET_ID or spreadsheet.title != SPREADSHEET_TITLE:
            raise RuntimeError('Wrong private data plane')
        self.spreadsheet = spreadsheet
        if known_secrets is None:
            from scripts.audit_private_data_plane import local_secret_values
            known_secrets = local_secret_values()
        self.known_secrets = known_secrets
        self.request_interval = request_interval
        self._last_write = 0

    def _write(self, function, *args, **kwargs):
        time.sleep(max(0, self.request_interval-(time.monotonic()-self._last_write)))
        for attempt in range(6):
            try:
                result = function(*args, **kwargs)
                self._last_write = time.monotonic()
                return result
            except Exception as error:
                code = getattr(error, 'code', None)
                if code not in (429, 500, 502, 503, 504) or attempt == 5:
                    raise RuntimeError('Sheets request failed: '+type(error).__name__) from None
                time.sleep(min(30, 2**(attempt+1)))

    def ensure_tab(self, title, columns, rows=1000):
        if title not in PRIVATE_TABS | CONTROL_TABS:
            raise ValueError('Unapproved tab')
        tabs = {w.title: w for w in self.spreadsheet.worksheets()}
        if title in tabs:
            ws = tabs[title]
            if ws.row_count < rows or ws.col_count < columns:
                self._write(ws.resize, rows=max(rows, ws.row_count), cols=max(columns, ws.col_count))
            return ws
        return self._write(self.spreadsheet.add_worksheet, title=title, rows=rows, cols=columns)

    def write_verified_table(self, title, headers, rows, *, batch_size=5000):
        """Resume deterministic writes; never clear a worksheet. Refuse conflicting data."""
        rows = [['' if x is None else str(x) for x in row] for row in rows]
        if not headers or any(len(row) != len(headers) for row in rows):
            raise ValueError('Table rows must match the declared schema')
        assert_sheet_rows(headers, rows, self.known_secrets)
        ws = self.ensure_tab(title, len(headers), len(rows)+1)
        end = column_name(len(headers))
        existing_header = self._write(ws.get_values, f'A1:{end}1')
        if existing_header and any(existing_header[0]) and existing_header[0] != headers:
            raise RuntimeError('Existing worksheet schema differs; preserve it for explicit migration')
        values = [headers] + rows
        for start in range(0, len(values), batch_size):
            chunk = values[start:start+batch_size]
            a1 = f'A{start+1}:{end}{start+len(chunk)}'
            current = self._write(ws.get_values, a1)
            normalized = [row+['']*(len(headers)-len(row)) for row in current]
            if normalized == chunk: continue
            if any(any(cell for cell in row) and row != chunk[i] for i,row in enumerate(normalized)):
                raise RuntimeError('Conflicting populated range; refusing to overwrite private records')
            self._write(ws.update, range_name=a1, values=chunk, value_input_option='RAW')
            readback = self._write(ws.get_values, a1)
            normalized = [row+['']*(len(headers)-len(row)) for row in readback]
            if normalized != chunk:
                raise RuntimeError('Private worksheet readback mismatch')
        self._write(ws.freeze, rows=1)
        self._write(ws.format, f'A1:{end}1', {'textFormat': {'bold': True},
                                            'backgroundColor': {'red': .93, 'green': .93, 'blue': .93}})
        digest = hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(',',':')).encode()).hexdigest()
        return {'tab': title, 'rows': len(rows), 'columns': len(headers), 'content_sha256': digest, 'verified': True}

    def read_records(self, title, headers, *, batch_size=5000):
        ws = self.spreadsheet.worksheet(title)
        end = column_name(len(headers))
        if self._write(ws.get_values, f'A1:{end}1') != [headers]:
            raise RuntimeError('Private worksheet schema mismatch')
        for start in range(2, ws.row_count+1, batch_size):
            for row in self._write(ws.get_values, f'A{start}:{end}{min(ws.row_count,start+batch_size-1)}'):
                yield dict(zip(headers, row+['']*(len(headers)-len(row))))
