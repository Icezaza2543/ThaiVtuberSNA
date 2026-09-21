"""Bind a dataset to the actual hasher, never to inferred historical identity."""
import json
import os
import uuid
from pathlib import Path
from core.file_lock import file_lock
from core.hasher import compute_key_fingerprint


def validate_dataset_identity(events_dir, fingerprint, initialize=False):
    events_dir = Path(events_dir)
    manifest = events_dir.parent / 'identity_manifest.json'
    if manifest.exists():
        try:
            value = json.loads(manifest.read_text(encoding='utf-8'))
            matches = isinstance(value, dict) and value.get('key_fingerprint') == fingerprint
        except (ValueError, OSError):
            matches = False
        if not matches:
            raise RuntimeError('Dataset key continuity mismatch or malformed identity manifest')
    elif any(events_dir.rglob('*.parquet')):
        raise RuntimeError('Historical Parquet lacks an identity manifest; verify original run provenance')
    elif not initialize:
        raise RuntimeError('Dataset identity manifest missing')
    else:
        temporary = manifest.with_name('.identity-' + uuid.uuid4().hex + '.tmp')
        try:
            with temporary.open('x', encoding='utf-8') as out:
                json.dump({'key_fingerprint': fingerprint,
                           'purpose': 'Continuity check only; not integrity or authenticity proof'}, out)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, manifest)
        finally:
            temporary.unlink(missing_ok=True)
    return manifest


def bind_dataset(events_dir, hasher):
    fingerprint = compute_key_fingerprint(hasher.secret_salt)
    # Preflight rejects an existing invalid dataset before creating a lock file.
    events_dir = Path(events_dir)
    if (events_dir.parent / 'identity_manifest.json').exists() or any(events_dir.rglob('*.parquet')):
        validate_dataset_identity(events_dir, fingerprint)
    with file_lock(events_dir.parent / '.identity.lock'):
        validate_dataset_identity(events_dir, fingerprint, initialize=True)
    return fingerprint
