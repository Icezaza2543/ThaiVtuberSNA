"""Fail-closed curated subject identity audit; no network or private data access."""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog
from core.creator_identity import normalize, validate_creator_identities


def audit_identity(intel=None):
    if intel is None:
        from scripts.build_creator_lifecycle_evidence import VERIFIED_CREATOR_INTEL
        intel = VERIFIED_CREATOR_INTEL
    manifest = pd.read_csv(ROOT / "data/temporal/catalog/target_manifest.csv").set_index("channel_id")
    registry = {
        row["channel_id"]: row
        for row in CreatorCatalog.from_path(CREATOR_REGISTRY_PATH).youtube_rows()
    }
    return validate_creator_identities(intel, manifest, registry)


if __name__ == "__main__":
    print(f"PASS: {audit_identity()} curated events have consistent subject identities.")
