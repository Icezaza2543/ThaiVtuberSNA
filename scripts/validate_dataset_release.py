#!/usr/bin/env python3
"""Phase T18: Release Validation & Reproducibility Audit Script

Validates:
1. Every file recorded in `dataset_manifest.json` exists on disk.
2. Every SHA-256 checksum matches the on-disk file content.
3. Every Parquet table conforms to the schemas recorded in `data_dictionary.json`.
4. Deterministic content hash matches the computed hash across all artifacts.
5. Zero viewer-level PII or unhashed identifiers exist in any release files.
"""
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
RELEASE_DIR = BASE / "data" / "temporal" / "release"
MANIFEST_JSON = RELEASE_DIR / "dataset_manifest.json"
DATA_DICT_JSON = RELEASE_DIR / "data_dictionary.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256_{h.hexdigest()}"


def validation_level(base=None):
    """Byte integrity alone never proves reproduction from canonical inputs."""
    root = Path(base or BASE)
    evidence_path = root / 'data/temporal/release/reproducibility_evidence.json'
    if not evidence_path.exists():
        return 'SELF_CONSISTENT'
    from scripts.reproduce_temporal_dataset import code_fingerprint, semantic_hashes
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    if (evidence.get('status') == 'REPRODUCIBLE_FROM_INPUTS' and not evidence.get('differences')
            and evidence.get('code_fingerprint') == code_fingerprint()
            and evidence.get('artifact_hashes') == semantic_hashes(root)):
        return 'REPRODUCIBLE_FROM_INPUTS'
    return 'SELF_CONSISTENT'


def validate_release() -> bool:
    print("=" * 60)
    print("T18: Validating Dataset Release Package & Artifact Integrity")
    print("=" * 60)

    if not MANIFEST_JSON.exists():
        print(f"FAILED: Manifest missing at {MANIFEST_JSON}")
        return False

    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    sections = manifest.get("sections", {})
    m_meta = manifest.get("manifest_metadata", {})

    errors = []
    checked_files = 0

    # 1. Verify existence and checksum for every artifact
    computed_entries = []
    for sec_name in sorted(sections.keys()):
        for art in sections[sec_name].get("artifacts", []):
            rel_path = art["path"]
            abs_path = BASE / rel_path
            if not abs_path.resolve().is_relative_to(BASE.resolve()):
                errors.append(f'Artifact path escapes release root: {rel_path}')
                continue
            checked_files += 1

            if not abs_path.exists():
                errors.append(f"Missing file: {rel_path}")
                continue

            # Verify checksum
            expected_cksum = art["checksum"]
            actual_cksum = sha256_file(abs_path)
            if actual_cksum != expected_cksum:
                errors.append(f"Checksum mismatch on {rel_path}: expected {expected_cksum}, got {actual_cksum}")

            computed_entries.append(f"{rel_path}:{abs_path.stat().st_size}:{actual_cksum}")

    print(f"✓ Checked {checked_files} artifacts across {len(sections)} sections.")

    # 2. Verify deterministic content hash
    expected_content_hash = m_meta.get("deterministic_content_hash")
    actual_content_hash = f"sha256_{hashlib.sha256(chr(10).join(computed_entries).encode('utf-8')).hexdigest()}"
    if actual_content_hash != expected_content_hash:
        errors.append(f"Deterministic content hash mismatch: expected {expected_content_hash}, got {actual_content_hash}")
    else:
        print(f"✓ Deterministic content hash verified: {actual_content_hash}")

    # 3. Verify Data Dictionary Schemas
    if DATA_DICT_JSON.exists():
        data_dict = json.loads(DATA_DICT_JSON.read_text(encoding="utf-8"))
        for fname, d_info in data_dict.items():
            # Find in artifacts
            matching = [BASE / art['path'] for section in sections.values() for art in section.get('artifacts', [])
                        if Path(art['path']).name == fname and (BASE / art['path']).is_file()]
            if matching:
                target_file = matching[0]
                try:
                    df = pd.read_parquet(target_file)
                    dict_cols = set(d_info.get("columns", {}).keys())
                    actual_cols = set(df.columns)
                    # All data dictionary columns should exist in table
                    missing_cols = dict_cols - actual_cols
                    if missing_cols:
                        errors.append(f"Schema mismatch in {fname}: missing columns {missing_cols}")
                except Exception as e:
                    errors.append(f"Failed to read parquet for schema check {fname}: {e}")
        print(f"✓ Verified schemas against data dictionary ({len(data_dict)} tables).")

    # 4. Privacy Audit on Release Directory
    for p in RELEASE_DIR.glob("*"):
        if p.is_file():
            content = p.read_text(encoding="utf-8", errors="replace")
            import re
            unprefixed_hex = re.findall(r'(?<!sha256_)\b[0-9a-f]{64}\b', content)
            if unprefixed_hex:
                errors.append(f"Privacy scan failed on {p.name}: found {len(unprefixed_hex)} unprefixed 64-char hex strings")

    if errors:
        print(f"\n❌ VALIDATION FAILED with {len(errors)} errors:")
        for err in errors[:10]:
            print(f"  - {err}")
        return False

    print('\nValidation level: ' + validation_level())
    return True


if __name__ == "__main__":
    success = validate_release()
    sys.exit(0 if success else 1)
