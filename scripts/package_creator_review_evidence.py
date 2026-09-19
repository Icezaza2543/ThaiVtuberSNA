"""Package final creator-screening decisions as compact, safe review evidence."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


AUTO_MAP = {
    "TRUSTED_BASELINE": "trusted_baseline",
    "VTUBER": "vtuber",
    "NON_VTUBER": "exclude_non_vtuber",
    "NON_PERSONA_ACCOUNT": "exclude_non_persona",
    "INVALID_ACCOUNT_URL": "exclude_invalid_account",
    "VIRTUAL_GROUP": "exclude_virtual_group",
    "VTUBER_ASSOCIATED_ACCOUNT": "exclude_associated_account",
    "UNRESOLVED": "unresolved",
}
HUMAN_MAP = {
    "vtuber": "vtuber",
    "unrelated": "exclude_unrelated",
    "non_persona": "exclude_non_persona",
    "unavailable": "unavailable",
    "unsure": "unresolved",
}

STABLE_FIELDS = (
    "discovery_id",
    "platform",
    "display_name",
    "original_name",
    "url",
    "channel_id",
    "eligibility",
    "reason",
    "evidence_urls",
    "decision_provenance",
    "reviewed_at",
)
PRODUCTION_COUNTS = {
    "exclude_associated_account": 1,
    "exclude_invalid_account": 2,
    "exclude_non_persona": 30,
    "exclude_non_vtuber": 3,
    "exclude_unrelated": 67,
    "exclude_virtual_group": 3,
    "trusted_baseline": 292,
    "unavailable": 94,
    "vtuber": 392,
}
_LOCAL_PATH = re.compile(r"(?:\b[A-Za-z]:[\\/]|\\\\|\bfile:)", re.IGNORECASE)
_UNIX_PATH_IN_TEXT = re.compile(
    r"(?<![\w\u0E00-\u0E7F])/(?!/)[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*"
)
_HTTP_URL_IN_TEXT = re.compile(r"""https?://[^\s<>"']+""", re.IGNORECASE)
_SECRET = re.compile(
    r"(?:api[_ -]?key|token|secret|password|credential|authorization)\s*(?:[:=]|\b(?:is|was|equals)\b)\s*\S+|\bbearer\s+",
    re.IGNORECASE,
)


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_duplicate_rejecting_object)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _validate_safe_text(value: Any, field: str, discovery_id: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"unsafe {field} for {discovery_id}: expected text")
    has_unix_path = False
    if field not in {"url", "evidence_urls"}:
        # Validate embedded URLs before excluding their paths from the text scan.
        # URL fields skip this scan and receive their own public-host validation.
        def exclude_public_url(match: re.Match[str]) -> str:
            _validate_public_url(match.group(), "url", discovery_id)
            return " "

        text_without_urls = _HTTP_URL_IN_TEXT.sub(exclude_public_url, value)
        has_unix_path = bool(_UNIX_PATH_IN_TEXT.search(text_without_urls))
    if _LOCAL_PATH.search(value) or has_unix_path or _SECRET.search(value):
        raise ValueError(f"unsafe {field} for {discovery_id}")
    return value


def _validate_public_url(value: Any, field: str, discovery_id: str) -> str:
    text = _validate_safe_text(value, field, discovery_id)
    parsed = urlparse(text)
    hostname = parsed.hostname.rstrip(".") if parsed.hostname else None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or parsed.username
        or parsed.password
        or hostname.lower() == "localhost"
        or hostname.lower().endswith(".localhost")
    ):
        raise ValueError(f"unsafe {field} for {discovery_id}")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError(f"unsafe {field} for {discovery_id}")
    return text


def _validate_evidence_urls(value: Any, discovery_id: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"unsafe evidence_urls for {discovery_id}: expected list")
    return [_validate_public_url(url, "evidence_urls", discovery_id) for url in value]


def _latest_human_decisions(human: dict[str, Any]) -> dict[str, dict[str, Any]]:
    decision_ids = human.get("decisions", [])
    if isinstance(decision_ids, dict):
        latest = dict(decision_ids)
        for discovery_id, entry in latest.items():
            if not isinstance(entry, dict) or entry.get("discovery_id") != discovery_id:
                raise ValueError(f"invalid human decision entry for {discovery_id!r}")
    elif isinstance(decision_ids, list):
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("human decisions contain duplicate discovery IDs")
        active_ids = set(decision_ids)
        latest = {}
        history = human.get("history", [])
        if not isinstance(history, list):
            raise ValueError("human history must be a list")
        for entry in history:
            if not isinstance(entry, dict):
                raise ValueError("human history entries must be JSON objects")
            discovery_id = entry.get("discovery_id")
            if discovery_id in active_ids:
                latest[discovery_id] = entry

        missing = active_ids - latest.keys()
        if missing:
            raise ValueError(f"human decisions missing history for {sorted(missing)!r}")
    else:
        raise ValueError("human decisions must be a list or object")
    for discovery_id, entry in latest.items():
        if entry.get("decision") not in HUMAN_MAP:
            raise ValueError(f"unknown human decision for {discovery_id}: {entry.get('decision')!r}")
    return latest


def _apply_explicit_corrections(rows: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    """Apply reviewed account-owner contradictions without altering raw decisions."""
    corrections = payload.get("corrections")
    if payload.get("schema_version") != 1 or not isinstance(corrections, list):
        raise ValueError("invalid eligibility correction schema")
    indexed = {row["discovery_id"]: row for row in rows}
    seen = set()
    fields = {"discovery_id", "old_eligibility", "new_eligibility", "account_url",
              "owner_channel_id", "owner_canonical_url", "source_url", "source_kind",
              "summary", "observed_at", "reviewer", "ruling"}
    for entry in corrections:
        if not isinstance(entry, dict) or set(entry) != fields:
            raise ValueError("invalid eligibility correction fields")
        did = entry["discovery_id"]
        if not isinstance(did, str) or did not in indexed or did in seen:
            raise ValueError("unknown or duplicate eligibility correction")
        seen.add(did)
        row = indexed[did]
        if (entry["old_eligibility"] != "vtuber" or row["eligibility"] != "vtuber"
                or entry["new_eligibility"] != "exclude_virtual_group" or row["platform"] != "youtube"):
            raise ValueError("unsupported eligibility correction transition")
        if entry["account_url"] != row["url"] or entry["source_kind"] != "youtube_api":
            raise ValueError("eligibility correction is not bound to the reviewed account")
        cid = entry["owner_channel_id"]
        if not isinstance(cid, str) or not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", cid):
            raise ValueError("invalid correction owner Channel ID")
        canonical = f"https://www.youtube.com/channel/{cid}"
        if entry["owner_canonical_url"] != canonical:
            raise ValueError("correction owner URL does not match Channel ID")
        for field in ("account_url", "owner_canonical_url", "source_url"):
            _validate_public_url(entry[field], "url", did)
        if entry["source_url"] not in {row["url"], canonical}:
            raise ValueError("correction evidence must identify this account or its owner")
        for field in ("summary", "observed_at", "reviewer", "ruling"):
            value = _validate_safe_text(entry[field], field, did)
            if not value.strip():
                raise ValueError("eligibility correction requires explicit evidence and review provenance")
        try:
            observed = datetime.fromisoformat(entry["observed_at"].replace("Z", "+00:00"))
            if observed.tzinfo is None:
                raise ValueError
        except ValueError:
            raise ValueError("invalid correction observation timestamp") from None
        row["eligibility"] = entry["new_eligibility"]
        row["correction_provenance"] = dict(entry)
        row["evidence_urls"] = sorted(set(row["evidence_urls"] + [entry["source_url"], canonical]))


def package_review_evidence(screening_path: Path, human_path: Path, corrections_path: Path | None = None) -> dict[str, Any]:
    """Return final eligibility rows without cache paths or private review details."""
    screening = _load_object(Path(screening_path))
    human = _load_object(Path(human_path))
    source_rows = screening.get("rows", [])
    if not isinstance(source_rows, list):
        raise ValueError("screening rows must be a list")
    human_decisions = _latest_human_decisions(human)

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for source in source_rows:
        if not isinstance(source, dict):
            raise ValueError("screening rows must be JSON objects")
        discovery_id = source.get("discovery_id")
        if not isinstance(discovery_id, str) or not discovery_id:
            raise ValueError("screening row is missing discovery_id")
        if discovery_id in seen_ids:
            raise ValueError(f"duplicate discovery ID: {discovery_id}")
        seen_ids.add(discovery_id)

        automated_decision = source.get("decision")
        if automated_decision not in AUTO_MAP:
            raise ValueError(f"unknown automated decision for {discovery_id}: {automated_decision!r}")

        human_entry = human_decisions.pop(discovery_id, None)
        if human_entry is not None and automated_decision != "UNRESOLVED":
            raise ValueError(f"human decision for non-UNRESOLVED row: {discovery_id}")

        if human_entry is None:
            eligibility = AUTO_MAP[automated_decision]
            provenance = {"source": "automated_screening", "decision": automated_decision}
            reviewed_at = None
        else:
            human_decision = human_entry["decision"]
            eligibility = HUMAN_MAP[human_decision]
            provenance = {"source": "human_review", "decision": human_decision}
            reviewed_at = human_entry.get("reviewed_at")

        row = {
            "discovery_id": discovery_id,
            "platform": source.get("platform"),
            "display_name": source.get("name"),
            "original_name": source.get("original_name"),
            "url": _validate_public_url(source.get("url"), "url", discovery_id),
            "channel_id": source.get("channel_id"),
            "eligibility": eligibility,
            "reason": _validate_safe_text(source.get("reason"), "reason", discovery_id),
            "evidence_urls": _validate_evidence_urls(source.get("evidence_urls", []), discovery_id),
            "decision_provenance": provenance,
            "reviewed_at": reviewed_at,
        }
        rows.append({field: row[field] for field in STABLE_FIELDS})

    if human_decisions:
        raise ValueError(f"human decisions reference unknown screening rows: {sorted(human_decisions)!r}")

    if corrections_path is not None:
        _apply_explicit_corrections(rows, _load_object(Path(corrections_path)))

    counts = dict(sorted(Counter(row["eligibility"] for row in rows).items()))
    return {
        "schema_version": 1,
        "rows": rows,
        "eligibility_counts": counts,
    }


def validate_production_counts(bundle: dict[str, Any]) -> None:
    rows = bundle.get("rows", [])
    counts = Counter(row.get("eligibility") for row in rows)
    if len(rows) != 884:
        raise ValueError(f"expected 884 review rows, found {len(rows)}")
    if dict(sorted(counts.items())) != PRODUCTION_COUNTS:
        raise ValueError(
            f"eligibility distribution does not match production counts: {dict(sorted(counts.items()))!r}"
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_legacy_review(legacy_source: Path, output_dir: Path, baseline_path: Path) -> None:
    legacy_destination = output_dir / "legacy_visual_identity_review.json"
    shutil.copyfile(legacy_source, legacy_destination)
    source_hash = _sha256(legacy_source)
    if _sha256(legacy_destination) != source_hash:
        raise ValueError("legacy visual identity review copy does not match source")

    baseline = _load_object(baseline_path)
    files = baseline.setdefault("files", {})
    files["data/entity_resolution/visual_identity_review.json"] = source_hash
    files["docs/evidence/creator-registry-review-2026-09-19/legacy_visual_identity_review.json"] = source_hash
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screening", type=Path, required=True)
    parser.add_argument("--human", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, help="Explicit reviewed eligibility corrections applied after human decisions.")
    parser.add_argument(
        "--legacy-source",
        type=Path,
        default=Path("data/entity_resolution/visual_identity_review.json"),
    )
    args = parser.parse_args()

    bundle = package_review_evidence(args.screening, args.human, args.corrections)
    validate_production_counts(bundle)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _copy_legacy_review(args.legacy_source, args.output.parent, args.output.parent / "pre_refactor_baseline.json")

    print("eligibility\tcount")
    for eligibility, count in bundle["eligibility_counts"].items():
        print(f"{eligibility}\t{count}")
    print(f"total\t{len(bundle['rows'])}")


if __name__ == "__main__":
    main()
