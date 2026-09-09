"""Append-only expanded batches in the existing archive, using injected PrivateSheetStore.

No workbook discovery/creation, no local event persistence. The caller must hold
the shared journal publication fence and a single workbook writer lock. Existing
production orchestration remains disabled until live capacity/transaction review.
"""
import hashlib
import json
from core.expanded_contracts import capacity_estimate
from core.data_security import assert_sheet_rows
from storage.private_sheet_analytics import ARCHIVE_HEADERS
from collector.expanded_backfill import encode

TAB = 'PRIVATE_DATA_ARCHIVE'


class ExpandedSheetBatches:
    def __init__(self, store, *, measured_allocated_cells=None, max_cell_chars=50000,
                 max_buffer_records=500, reserved_growth_cells=0):
        self.store = store
        self.measured_allocated_cells = measured_allocated_cells
        self.max_cell_chars, self.max_buffer_records = max_cell_chars, max_buffer_records
        self.reserved_growth_cells = reserved_growth_cells

    def _scan(self):
        tabs = {ws.title: ws for ws in self.store.spreadsheet.worksheets()}
        if TAB not in tabs:
            return None, []
        ws = tabs[TAB]
        header = self.store._write(ws.get_values, 'A1:D1')
        if header and header != [ARCHIVE_HEADERS]:
            raise RuntimeError('Preserve existing archive schema; migration not authorized')
        if not header:
            for start in range(2, ws.row_count + 1, 500):
                if any(any(row) for row in self.store._write(ws.get_values, f'A{start}:D{min(start+499, ws.row_count)}')):
                    raise RuntimeError('Populated archive with missing header; explicit reconciliation required')
            return ws, []
        # Generator keeps scanning memory bounded; no workbook data is written locally.
        return ws, self.store.read_records(TAB, ARCHIVE_HEADERS)

    def load(self, job_id):
        _, records = self._scan()
        state, seen, batch = {}, set(), []
        prefix = 'expanded-v1/' + job_id + '/'
        for record in records:
            if not record.get('source_path', '').startswith(prefix): continue
            if record['source_table'] == 'batch_manifest':
                manifest = json.loads(record['record_json'])
                digest = hashlib.sha256(encode(batch).encode()).hexdigest()
                if digest != manifest['sha256'] or len(batch) != manifest['rows']:
                    raise RuntimeError('Ambiguous workbook batch: reconcile before retry')
                for row in batch:
                    obj = json.loads(row[3])
                    if row[1] == 'state': state = obj
                    elif row[1] == 'event': seen.add(obj['record_id'])
                batch = []
            else:
                batch.append([record.get(k, '') for k in ARCHIVE_HEADERS])
                if len(batch) > self.max_buffer_records + 1:
                    raise RuntimeError('Memory bound reached; pause without private spill')
        if batch: raise RuntimeError('Incomplete workbook batch; reconcile before retry')
        if len(seen) > self.max_buffer_records:
            raise RuntimeError('Job identity buffer exceeds approved bound; do not truncate')
        return state, seen

    def commit(self, job_id, expected_sequence, events, state):
        if self.measured_allocated_cells is None:
            raise RuntimeError('NOT_MEASURED: capacity approval required before writing')
        if len(events) > self.max_buffer_records:
            raise RuntimeError('Memory bound reached; no local private spill')
        if type(state.get('sequence')) is not int or state['sequence'] != expected_sequence + 1:
            raise ValueError('Batch sequence must follow expected sequence')
        batch_id = f'expanded-v1/{job_id}/{state["sequence"]}'
        rows = [[batch_id, 'event', str(i), encode(event)] for i, event in enumerate(events)]
        rows.append([batch_id, 'state', str(len(rows)), encode(state)])
        digest = hashlib.sha256(encode(rows).encode()).hexdigest()
        rows.append([batch_id, 'batch_manifest', str(len(rows)), encode({'sha256': digest, 'rows': len(rows)})])
        current, _ = self.load(job_id)
        if current.get('sequence', 0) == state['sequence']:
            _, records = self._scan()
            committed = [[r.get(k, '') for k in ARCHIVE_HEADERS] for r in records
                         if r.get('source_path') == batch_id]
            if current != state or committed != rows:
                raise RuntimeError('Conflicting replay content; preserve committed batch')
            return {'verified': True, 'reconciled': True, 'content_sha256': digest}
        if current.get('sequence', 0) != expected_sequence:
            raise RuntimeError('Stale workbook sequence')
        if any(len(str(cell)) > self.max_cell_chars for row in rows for cell in row):
            raise RuntimeError('Cell limit exceeded; pause without truncating')
        assert_sheet_rows(ARCHIVE_HEADERS, rows, self.store.known_secrets)
        ws, records = self._scan()
        # Find occupied extent, not a count that could overwrite a sparse row.
        # Scan physical ranges in bounded chunks through the existing store transport.
        end = 1
        if ws:
            for start in range(2, ws.row_count + 1, 500):
                values = self.store._write(ws.get_values, f'A{start}:D{min(start+499, ws.row_count)}')
                for offset, row in enumerate(values):
                    if any(row): end = start + offset
        required_rows = end + len(rows)
        existing_alloc = sum(w.row_count * w.col_count for w in self.store.spreadsheet.worksheets())
        growth = max(0, required_rows * max(4, ws.col_count) - ws.row_count * ws.col_count) if ws else required_rows * 4
        capacity = capacity_estimate(archive_rows=0, control_cells=growth + self.reserved_growth_cells,
                                     allocated_cells=max(existing_alloc, self.measured_allocated_cells))
        if capacity['state'] != 'PASS':
            raise RuntimeError('INSUFFICIENT workbook capacity; no truncation or second workbook')
        ws = self.store.ensure_tab(TAB, 4, required_rows)
        if end == 1 and self.store._write(ws.get_values, 'A1:D1') != [ARCHIVE_HEADERS]:
            self.store._write(ws.update, range_name='A1:D1', values=[ARCHIVE_HEADERS], value_input_option='RAW')
        target = f'A{end+1}:D{required_rows}'
        if any(any(row) for row in self.store._write(ws.get_values, target)):
            raise RuntimeError('Conflicting populated batch range')
        self.store._write(ws.update, range_name=target, values=rows, value_input_option='RAW')
        if self.store._write(ws.get_values, target) != rows:
            raise RuntimeError('Ambiguous acknowledgement; reconcile batch before retry')
        return {'verified': True, 'content_sha256': digest, 'rows': len(events)}
