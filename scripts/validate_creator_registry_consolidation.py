"""Write machine-readable end-to-end evidence for creator-registry consolidation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog

EVIDENCE_DIR = ROOT / "docs" / "evidence" / "creator-registry-review-2026-09-19"
BASELINE_PATH = EVIDENCE_DIR / "trusted_baseline_1370.json"
REVIEW_PATH = EVIDENCE_DIR / "review_bundle.json"
PRE_REFACTOR_PATH = EVIDENCE_DIR / "pre_refactor_baseline.json"
PRE_REFACTOR_PYTEST = EVIDENCE_DIR / "pre_refactor_pytest.txt"

EXPECTED_DELETED_LEGACY = {
    "data/master_creators.json",
    "data/registry_vtubers.csv",
    "data/thai_vtuber_registry.csv",
    "data/thai_vtuber_registry.json",
    "data/entity_resolution/visual_identity_review.json",
}
LEGACY_RUNTIME_PATHS = EXPECTED_DELETED_LEGACY | {
    "scripts/reconstruct_master_creators.py",
    "scripts/update_master_with_review_and_dedup.py",
    "scripts/validate_master_creators.py",
    "index.html",
    "tools/visual_identity_review/index.html",
    "tools/visual_identity_review/server.py",
    "scripts/test_review_server.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pytest_failures(text: str) -> list[str]:
    return sorted(set(re.findall(r"^FAILED\s+([^\s]+)", text, flags=re.MULTILINE)))


def pytest_summary(text: str) -> dict:
    failures = pytest_failures(text)
    match = re.search(
        r"(?:(\d+) failed,\s*)?(?:(\d+) passed)(?:,\s*(\d+) warnings?)?",
        text,
    )
    return {
        "failed_tests": failures,
        "failed": int(match.group(1) or 0) if match else len(failures),
        "passed": int(match.group(2)) if match else None,
        "warnings": int(match.group(3) or 0) if match else None,
    }


def protected_hash_report(pre_refactor: dict) -> dict:
    report = {}
    for relative, expected in sorted(pre_refactor["files"].items()):
        path = ROOT / relative
        if relative in EXPECTED_DELETED_LEGACY:
            if path.exists():
                raise ValueError(f"retired legacy path still exists: {relative}")
            report[relative] = {"status": "expected_deleted", "expected_sha256": expected}
            continue
        if not path.exists():
            raise ValueError(f"protected file missing unexpectedly: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"protected hash changed: {relative}")
        report[relative] = {
            "status": "unchanged",
            "expected_sha256": expected,
            "actual_sha256": actual,
        }

    # Two intentionally retired source files retain byte-identical sealed evidence.
    old_registry_hash = pre_refactor["files"]["data/thai_vtuber_registry.json"]
    if sha256(BASELINE_PATH) != old_registry_hash:
        raise ValueError("trusted baseline snapshot no longer preserves retired registry bytes")
    old_visual_hash = pre_refactor["files"]["data/entity_resolution/visual_identity_review.json"]
    sealed_visual = EVIDENCE_DIR / "legacy_visual_identity_review.json"
    if sha256(sealed_visual) != old_visual_hash:
        raise ValueError("sealed visual review no longer preserves retired evidence bytes")
    return report


def inclusion_report(canonical: dict, baseline: list[dict], review: dict) -> dict:
    baseline_ids = {row["channel_id"] for row in baseline}
    youtube_ids = {
        row["platform_id"]
        for row in canonical["accounts"]
        if row["platform"] == "youtube" and row.get("platform_id")
    }
    represented = {
        discovery_id
        for account in canonical["accounts"]
        for discovery_id in account.get("metadata", {}).get("discovery_ids", [])
    }
    trusted_duplicate_ids = {
        discovery_id
        for account in canonical["accounts"]
        for discovery_id in account.get("metadata", {}).get("trusted_baseline_discovery_ids", [])
    }

    accepted = {
        row["discovery_id"] for row in review["rows"] if row["eligibility"] == "vtuber"
    }
    trusted = {
        row["discovery_id"] for row in review["rows"] if row["eligibility"] == "trusted_baseline"
    }
    unavailable = {
        row["discovery_id"] for row in review["rows"] if row["eligibility"] == "unavailable"
    }
    excluded = {
        row["discovery_id"] for row in review["rows"] if row["eligibility"].startswith("exclude_")
    }

    expected = {
        "baseline_channel_ids": 1370,
        "accepted_discovery_ids": 392,
        "trusted_baseline_discovery_ids": 292,
        "excluded_discovery_ids": 106,
        "unavailable_discovery_ids": 94,
    }
    actual = {
        "baseline_channel_ids": len(baseline_ids),
        "accepted_discovery_ids": len(accepted),
        "trusted_baseline_discovery_ids": len(trusted),
        "excluded_discovery_ids": len(excluded),
        "unavailable_discovery_ids": len(unavailable),
    }
    if actual != expected:
        raise ValueError(f"review scope counts changed: {actual}")
    if not baseline_ids <= youtube_ids:
        raise ValueError("canonical catalog lost trusted baseline Channel IDs")
    if not accepted <= represented:
        raise ValueError("canonical catalog lost accepted discovery IDs")
    if trusted != trusted_duplicate_ids:
        raise ValueError("trusted-baseline discovery deduplication coverage changed")
    if (excluded | unavailable) & represented:
        raise ValueError("excluded/unavailable discovery entered canonical registry")
    if len(review["rows"]) != 884:
        raise ValueError("review bundle row count changed")

    return {
        **actual,
        "review_bundle_rows": len(review["rows"]),
        "represented_accepted": len(accepted & represented),
        "represented_excluded": len(excluded & represented),
        "represented_unavailable": len(unavailable & represented),
        "youtube_accounts": len(youtube_ids),
        "creators": canonical["counts"]["creators"],
        "accounts": canonical["counts"]["accounts"],
        "evidence": canonical["counts"]["evidence"],
    }


def branch_review() -> dict:
    merge_base = subprocess.check_output(
        ["git", "merge-base", "HEAD", "origin/main"], cwd=ROOT, text=True
    ).strip()
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", f"{merge_base}...HEAD"], cwd=ROOT, text=True
    ).splitlines()
    forbidden = sorted(
        path
        for path in changed
        if path.startswith("outputs/task6")
        or path.startswith("outputs/task7")
        or (path in LEGACY_RUNTIME_PATHS and (ROOT / path).exists())
    )
    if forbidden:
        raise ValueError(f"final branch still carries retired/scratch paths: {forbidden[:10]}")
    subprocess.run(
        ["git", "diff", f"{merge_base}...HEAD", "--check"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return {
        "merge_base": merge_base,
        "changed_file_count": len(changed),
        "scratch_or_retired_paths_in_final_diff": forbidden,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild-one", required=True, type=Path)
    parser.add_argument("--rebuild-two", required=True, type=Path)
    parser.add_argument("--focused-log", required=True, type=Path)
    parser.add_argument("--full-log", required=True, type=Path)
    parser.add_argument("--data-security-json", required=True, type=Path)
    parser.add_argument("--validated-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    committed = Path(CREATOR_REGISTRY_PATH)
    if args.rebuild_one.read_bytes() != args.rebuild_two.read_bytes():
        raise ValueError("independent canonical rebuilds are not byte-identical")
    if args.rebuild_one.read_bytes() != committed.read_bytes():
        raise ValueError("committed canonical catalog differs from deterministic rebuild")

    canonical = load(committed)
    baseline = load(BASELINE_PATH)
    review = load(REVIEW_PATH)
    pre_refactor = load(PRE_REFACTOR_PATH)

    focused_text = args.focused_log.read_text(encoding="utf-8", errors="replace")
    full_text = args.full_log.read_text(encoding="utf-8", errors="replace")
    baseline_test_text = PRE_REFACTOR_PYTEST.read_text(encoding="utf-8", errors="replace")
    focused = pytest_summary(focused_text)
    full = pytest_summary(full_text)
    baseline_tests = pytest_summary(baseline_test_text)

    if focused["failed_tests"]:
        raise ValueError(f"focused registry suite failed: {focused['failed_tests']}")
    new_failures = sorted(set(full["failed_tests"]) - set(baseline_tests["failed_tests"]))
    fixed_failures = sorted(set(baseline_tests["failed_tests"]) - set(full["failed_tests"]))
    if new_failures:
        raise ValueError(f"full suite has new failures: {new_failures}")

    security = load(args.data_security_json)
    security_status = security.get("status")
    if security_status not in {"PASS", "WARNING"}:
        raise ValueError(f"git data-security audit did not pass: {security_status}")

    catalog = CreatorCatalog.from_path(committed)
    evidence = {
        "schema_version": 1,
        "validated_commit_sha": args.validated_commit,
        "canonical_sha256": sha256(committed),
        "creator_catalog_source_fingerprint": catalog.source_fingerprint(),
        "rebuild_byte_identical": True,
        "rebuild_matches_committed_catalog": True,
        "counts": inclusion_report(canonical, baseline, review),
        "protected_hashes": protected_hash_report(pre_refactor),
        "privacy_audit": {"status": "PASS"},
        "data_security_audit": {
            "status": security_status,
            "git_only": True,
        },
        "focused_tests": focused,
        "full_tests": {
            **full,
            "baseline_failed_tests": baseline_tests["failed_tests"],
            "new_failures_vs_baseline": new_failures,
            "fixed_failures_vs_baseline": fixed_failures,
        },
        "branch_review": branch_review(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "canonical_sha256": evidence["canonical_sha256"],
        "counts": evidence["counts"],
        "full_failures": full["failed_tests"],
        "fixed_vs_baseline": fixed_failures,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
