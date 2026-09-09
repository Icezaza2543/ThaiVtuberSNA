"""Fail-closed curated subject identity audit; no network or private data access."""
import json
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.creator_identity import normalize, validate_creator_identities

def audit_identity(intel=None):
    if intel is None:
        from scripts.build_creator_lifecycle_evidence import VERIFIED_CREATOR_INTEL
        intel = VERIFIED_CREATOR_INTEL
    manifest = pd.read_csv(ROOT / 'data/temporal/catalog/target_manifest.csv').set_index('channel_id')
    registry = {r['channel_id']: r for r in json.loads((ROOT / 'data/thai_vtuber_registry.json').read_text(encoding='utf8'))}
    return validate_creator_identities(intel, manifest, registry)

if __name__ == '__main__':
    print(f'PASS: {audit_identity()} curated events have consistent subject identities.')
