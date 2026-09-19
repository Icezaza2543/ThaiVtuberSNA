"""Content-bound dependencies shared by review packaging and identity resolution."""
from __future__ import annotations

import hashlib
import json
import re

REQUIRED_CORRECTIONS = 'required_trusted_link_corrections'
CORRECTION_FIELDS = {'link_id', 'account_id', 'asserted_persona_id', 'evidence_id', 'disposition',
                     'link_sha256', 'account_sha256', 'evidence_sha256', 'source_urls',
                     'summary', 'observed_at', 'reviewer'}


def record_sha256(record):
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def correction_records(payloads):
    """Deduplicate identical correction records; reject conflicting declarations."""
    records = {}
    for payload in payloads:
        if (not isinstance(payload, dict) or payload.get('schema_version') != 1
                or not isinstance(payload.get('corrections'), list)):
            raise ValueError('unsupported trusted link correction schema')
        for row in payload['corrections']:
            if (not isinstance(row, dict) or set(row) != CORRECTION_FIELDS
                    or row.get('disposition') != 'reject_identity_link'):
                raise ValueError('invalid trusted link correction fields/disposition')
            key = row['link_id']
            if not isinstance(key, str) or not key.strip():
                raise ValueError('trusted link correction missing link ID')
            if key in records and records[key] != row:
                raise ValueError('conflicting trusted link corrections')
            records[key] = row
    return records


def trusted_link_correction_manifest(payloads):
    return [{'link_id': key, 'correction_sha256': record_sha256(row)}
            for key, row in sorted(correction_records(payloads).items())]


def merge_required_trusted_link_corrections(payloads):
    """Keep dependencies when batches merge; absence preserves fixture workflows."""
    required = {}
    for payload in payloads:
        if REQUIRED_CORRECTIONS not in payload:
            continue
        manifest = payload[REQUIRED_CORRECTIONS]
        if not isinstance(manifest, list):
            raise ValueError('required trusted link corrections must be a list')
        for row in manifest:
            if (not isinstance(row, dict) or set(row) != {'link_id', 'correction_sha256'}
                    or not isinstance(row['link_id'], str) or not row['link_id'].strip()
                    or not isinstance(row['correction_sha256'], str)
                    or not re.fullmatch('[0-9a-f]{64}', row['correction_sha256'])):
                raise ValueError('invalid required trusted link correction manifest entry')
            key = row['link_id']
            if key in required and required[key] != row:
                raise ValueError(f'conflicting required trusted link correction: {key}')
            required[key] = dict(row)
    return [required[key] for key in sorted(required)]


def require_trusted_link_corrections(required, payloads, referenced_ids=()):
    """Fail before resolution if any required correction is absent or changed.

    Additional nonconflicting corrections are allowed for later research batches;
    the resolver still validates every supplied record against the trusted source.
    """
    supplied = {row['link_id']: row['correction_sha256']
                for row in trusted_link_correction_manifest(payloads)}
    missing = ({row['link_id'] for row in required} | set(referenced_ids)) - supplied.keys()
    if missing:
        raise ValueError('missing required trusted link corrections: ' + ', '.join(sorted(missing)))
    stale = [row['link_id'] for row in required if row['correction_sha256'] != supplied[row['link_id']]]
    if stale:
        raise ValueError('changed required trusted link corrections: ' + ', '.join(sorted(stale)))
