"""Fail-closed curated subject identity audit; no network or private data access."""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def normalize(value):
    return re.sub(r'[^\w]', '', str(value).casefold().replace('_', ''))

def audit_identity(intel=None):
    if intel is None:
        from scripts.build_creator_lifecycle_evidence import VERIFIED_CREATOR_INTEL
        intel = VERIFIED_CREATOR_INTEL
    manifest = pd.read_csv(ROOT / 'data/temporal/catalog/target_manifest.csv').set_index('channel_id')
    registry = {r['channel_id']: r for r in json.loads((ROOT / 'data/thai_vtuber_registry.json').read_text(encoding='utf8'))}
    claims = {}
    agency_pages = {'AStars', 'Algorhythm_Project', 'Virtual_Zeven'}
    for cid, events in intel.items():
        assert cid in manifest.index and cid in registry, f'Unknown frozen identity: {cid}'
        for event in events:
            assert event['subject_channel_id'] == cid, f'Key/subject mismatch: {cid}'
            name = normalize(event['subject_name'])
            subject = normalize(event['source_subject'])
            assert name and subject == name, f'Source subject mismatch: {cid}'
            for catalog_name in (manifest.loc[cid, 'name'], registry[cid]['name']):
                assert name in normalize(catalog_name), f'Creator name mismatch: {cid}'
            assert claims.setdefault(name, cid) == cid, f'Duplicate identity claim: {name}'
            ref = event['source_reference']
            slug = unquote(urlparse(ref).path.rsplit('/', 1)[-1])
            if '/wiki/' in ref and slug not in agency_pages:
                # A short page title is permitted only if it names part of this same subject.
                assert normalize(slug) in name or name in normalize(slug), f'Conflicting source slug: {cid}'
            if manifest.loc[cid, 'agency'] == 'Independent':
                assert event.get('source_agency', '').startswith('Independent'), f'Agency event on Independent: {cid}'
                agency_markers = ('arp_vtuber', 'pixelaproject', 'astarsofficial', 'polygonofficial', 'algorhythm_project', '/wiki/astars', '/wiki/virtual_zeven')
                assert not any(marker in ref.casefold() for marker in agency_markers), f'Agency source on Independent: {cid}'
    return sum(map(len, intel.values()))

if __name__ == '__main__':
    print(f'PASS: {audit_identity()} curated events have consistent subject identities.')
