"""Append-only expanded batches in the existing archive, using injected PrivateSheetStore.

No workbook discovery/creation, no local event persistence. The caller must hold
the shared journal publication fence and a single workbook writer lock. Existing
production orchestration remains disabled until live capacity/transaction review.
"""
import hashlib
import json
import re
from core.expanded_contracts import capacity_estimate
from core.data_security import assert_sheet_rows
from storage.private_sheet_analytics import ARCHIVE_HEADERS
from collector.expanded_backfill import encode

TAB = 'PRIVATE_DATA_ARCHIVE'


def validated_expanded_batches(records, *, max_batch_records=502):
    """Validate whole batches before exposing any row; quarantine conflicts by batch ID.

    RAM only. Scan the whole input before returning so a later conflicting copy
    cannot invalidate events already exposed to analytics. Return only batch IDs
    for rejected groups, never private contents in diagnostics.
    """
    groups, rejected = {}, set()
    for record in records:
        path = record.get('source_path', '')
        if not path.startswith('expanded-v1/'):
            continue
        if path in rejected:
            continue
        rows = groups.setdefault(path, [])
        rows.append([record.get(k, '') for k in ARCHIVE_HEADERS])
        if len(rows) > max_batch_records:
            rejected.add(path)
            del groups[path]
    accepted = {}
    for path, rows in groups.items():
        try:
            match = re.fullmatch(r'expanded-v1/([a-f0-9]{64})/([1-9][0-9]*)', path)
            if not match or len(rows) < 2:
                raise ValueError()
            if [r[2] for r in rows] != [str(i) for i in range(len(rows))]:
                raise ValueError()
            if rows[-1][1] != 'batch_manifest' or rows[-2][1] != 'state':
                raise ValueError()
            if any(r[1] != 'event' for r in rows[:-2]):
                raise ValueError()
            manifest = json.loads(rows[-1][3])
            digest = hashlib.sha256(encode(rows[:-1]).encode()).hexdigest()
            if (set(manifest) != {'sha256', 'rows'} or type(manifest['rows']) is not int
                    or manifest['rows'] != len(rows)-1 or manifest['sha256'] != digest):
                raise ValueError()
            state = json.loads(rows[-2][3])
            if type(state.get('sequence')) is not int or state['sequence'] != int(match[2]):
                raise ValueError()
            events = [json.loads(r[3]) for r in rows[:-2]]
            allowed = {'record_id', 'viewer_hash', 'vtuber_channel_id', 'video_id', 'source_type',
                       'interaction_kind', 'interaction_time', 'provenance', 'video_published_at'}
            for event in events:
                if (not isinstance(event, dict) or set(event)-allowed
                        or any(not isinstance(event.get(k), str) or not event[k]
                               for k in ('record_id','viewer_hash','vtuber_channel_id','video_id','provenance'))
                        or event.get('source_type') not in {'comment', 'live_chat'}):
                    raise ValueError()
            accepted[path] = {'events': events, 'state': state, 'digest': digest}
        except (ValueError, TypeError, KeyError, AttributeError):
            rejected.add(path)
    identities = {}
    for path, batch in accepted.items():
        for event in batch['events']:
            key = tuple(event[k] for k in ('vtuber_channel_id', 'video_id', 'source_type', 'record_id'))
            payload = encode(event)
            identity = identities.setdefault(key, {'payload': payload, 'paths': set(), 'conflict': False})
            identity['paths'].add(path)
            identity['conflict'] |= identity['payload'] != payload
    for identity in identities.values():
        if identity['conflict']:
            rejected.update(identity['paths'])
    return {p: b for p, b in accepted.items() if p not in rejected}, sorted(rejected)


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

    def _job_records(self, job_id):
        _, records = self._scan()
        prefix = 'expanded-v1/' + job_id + '/'
        return (r for r in records if r.get('source_path', '').startswith(prefix))

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
            records = self._job_records(job_id)
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
        end = self._occupied_extent(ws)
        required_rows = end + len(rows)
        allocation_rows = self._allocation_rows(required_rows, ws)
        existing_alloc = sum(w.row_count * w.col_count for w in self.store.spreadsheet.worksheets())
        growth = max(0, allocation_rows * max(4, ws.col_count) - ws.row_count * ws.col_count) if ws else allocation_rows * 4
        capacity = capacity_estimate(archive_rows=0, control_cells=growth + self.reserved_growth_cells,
                                     allocated_cells=max(existing_alloc, self.measured_allocated_cells))
        if capacity['state'] != 'PASS':
            raise RuntimeError('INSUFFICIENT workbook capacity; no truncation or second workbook')
        ws = self.store.ensure_tab(TAB, 4, allocation_rows)
        if end == 1 and self.store._write(ws.get_values, 'A1:D1') != [ARCHIVE_HEADERS]:
            self.store._write(ws.update, range_name='A1:D1', values=[ARCHIVE_HEADERS], value_input_option='RAW')
        target = f'A{end+1}:D{required_rows}'
        if any(any(row) for row in self.store._write(ws.get_values, target)):
            raise RuntimeError('Conflicting populated batch range')
        self.store._write(ws.update, range_name=target, values=rows, value_input_option='RAW')
        if self.store._write(ws.get_values, target) != rows:
            raise RuntimeError('Ambiguous acknowledgement; reconcile batch before retry')
        self._after_verified_write(ws)
        return {'verified': True, 'content_sha256': digest, 'rows': len(events)}

    def _after_verified_write(self, ws):
        pass

    def _allocation_rows(self, required_rows, ws):
        return required_rows

    def _occupied_extent(self, ws):
        end = 1
        if ws:
            for start in range(2, ws.row_count + 1, 500):
                values = self.store._write(ws.get_values, f'A{start}:D{min(start+499, ws.row_count)}')
                for offset, row in enumerate(values):
                    if any(row): end = start + offset
        return end
