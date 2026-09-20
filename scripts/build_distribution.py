"""Master Distribution Builder for ThaiVtuberSNA & Thai Virtual Creator Registry.

Coordinates validation and data export across both the Social Network Analysis (SNA)
Observatory and the Evidence-Backed Virtual Creator Registry.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from registry.store import load, rows, validate
from scripts.maintenance.export_frontend import build_catalog, safe_url
from core.creator_catalog import CreatorCatalog
from config.settings import CREATOR_REGISTRY_PATH


def build_unified_distribution(as_of: str | None = None, check_only: bool = False) -> dict:
    summary = {
        "status": "PASS",
        "registry": {},
        "sna_cohort": {},
        "web_distribution": {},
    }

    # 1. Validate Canonical Cross-Platform Registry (data/registry.json)
    reg_path = ROOT / "data/registry.json"
    if not reg_path.exists():
        raise FileNotFoundError(f"Missing canonical registry: {reg_path}")

    raw_bytes = reg_path.read_bytes()
    reg_checksum = hashlib.sha256(raw_bytes).hexdigest()
    db = load(reg_path)
    try:
        validate(db)

        all_personas = rows(db, "personas")
        verified_personas = [p for p in all_personas if p["review_status"] == "verified"]
        all_accounts = rows(db, "accounts")

        summary["registry"] = {
            "valid": True,
            "sha256": reg_checksum[:12],
            "total_personas": len(all_personas),
            "verified_personas": len(verified_personas),
            "total_accounts": len(all_accounts),
        }

        # 2. Export Frontend Projection Dataset for Creator Directory
        catalog = build_catalog(db, reg_checksum)
    finally:
        db.close()

    web_catalog_out = ROOT / "web/public/data/registry.json"
    if not check_only:
        web_catalog_out.parent.mkdir(parents=True, exist_ok=True)
        web_catalog_out.write_text(
            json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    summary["web_distribution"]["creator_catalog_exported"] = {
        "path": str(web_catalog_out.relative_to(ROOT)),
        "published_personas": len(catalog["creators"]),
        "published_accounts": catalog["published"]["accounts"],
    }

    # 3. Verify SNA Canonical Catalog & Cohort
    if CREATOR_REGISTRY_PATH.exists():
        sna_catalog = CreatorCatalog.from_path(CREATOR_REGISTRY_PATH)
        sna_creators = len(sna_catalog.creators())
        sna_accounts = len(sna_catalog.accounts())
        summary["sna_cohort"] = {
            "canonical_path": str(CREATOR_REGISTRY_PATH.relative_to(ROOT)),
            "creators": sna_creators,
            "accounts": sna_accounts,
            "fingerprint": sna_catalog.source_fingerprint()[:12],
        }

    # 4. Check Web Entrypoints
    index_html = ROOT / "web/index.html"
    registry_html = ROOT / "web/registry.html"
    summary["web_distribution"]["entrypoints"] = {
        "sna_network": index_html.exists(),
        "creator_registry": registry_html.exists(),
    }

    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Validate without writing files")
    args = parser.parse_args(argv)

    try:
        res = build_unified_distribution(check_only=args.check_only)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
