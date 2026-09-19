"""Deterministically build the schema-v2 canonical creator registry.

The builder combines the trusted YouTube baseline with the reviewed eligibility
bundle and the sealed identity-resolution ledger.  It performs no network I/O and
never resolves identity from names, handles, or agencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlsplit

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.creator_registry_contract import (
    normalize_handle,
    normalize_platform,
    normalize_url,
    stable_account_id,
    stable_persona_id,
    validate_registry,
)

DATASET_NAME = "ThaiVtuberSNA Creator Registry"
IDENTITY_POLICY = "one virtual persona or character form per creator"
BASELINE_OBSERVED_AT = "2026-09-19T00:00:00Z"
RESERVED_METADATA_FIELDS = {
    "subscriber_count",
    "video_count",
    "view_count",
    "activity_status",
    "vtuber_status",
    "country",
    "thai_confidence",
    "reference_sources",
    "checked_date",
    "evidence_notes",
    "enabled",
    "channel_type",
    "last_video_published_at",
}


def _records(payload: Any, key: str | None = None) -> list[dict[str, Any]]:
    rows = payload if key is None else payload.get(key, [])
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        label = "baseline" if key is None else key
        raise ValueError(f"{label} must be an array of objects")
    return rows


def _canonical_for_hash(value: Any) -> Any:
    """Canonicalize JSON-like values so source fingerprints ignore array order."""
    if isinstance(value, dict):
        return {key: _canonical_for_hash(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        items = [_canonical_for_hash(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return value


def _semantic_sha256(value: Any) -> str:
    canonical = _canonical_for_hash(value)
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _evidence_id(seed: dict[str, Any]) -> str:
    return "evidence_" + _semantic_sha256(seed)[:20]


def _first_text(*values: Any, default: str | None = None) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _url_handle(platform: str, url: str, platform_id: str | None = None) -> str:
    if isinstance(platform_id, str) and platform_id.strip() and platform == "youtube":
        # YouTube Channel IDs are stable and unique even when the captured URL is
        # a /channel/ URL with no public @handle.
        fallback = platform_id.strip()
    else:
        fallback = None
    parsed = urlsplit(url)
    parts = [part for part in parsed.path.split("/") if part]
    candidate = None
    if parts:
        if platform == "youtube" and parts[0] in {"channel", "c", "user"} and len(parts) > 1:
            candidate = parts[1]
        else:
            candidate = parts[-1]
    candidate = (candidate or fallback or parsed.hostname or "account").lstrip("@")
    return candidate


def _canonical_account_key(platform: str, platform_id: str | None, url: str) -> tuple[str, str, str]:
    platform = normalize_platform(platform)
    if isinstance(platform_id, str) and platform_id.strip():
        return ("id", platform, platform_id.strip())
    return ("url", platform, normalize_url(url))


def _source_provenance(evidence: dict[str, Any], reviewer: str | None = None) -> str:
    method = evidence.get("collection_method")
    if isinstance(method, str) and method.strip():
        return method.strip()
    if reviewer:
        return f"identity_resolution:{reviewer}"
    return "reviewed_public_evidence"


class _RegistryBuilder:
    def __init__(self, baseline: list[dict[str, Any]], review_bundle: dict[str, Any], resolutions: dict[str, Any]):
        self.baseline = _records(baseline)
        self.review_rows = _records(review_bundle, "rows")
        self.resolution_rows = _records(resolutions, "resolutions")
        self.review = {}
        for row in self.review_rows:
            did = row.get("discovery_id")
            if not isinstance(did, str) or not did:
                raise ValueError("review row missing discovery_id")
            if did in self.review:
                raise ValueError(f"duplicate discovery ID: {did}")
            self.review[did] = row
        self.creators: dict[str, dict[str, Any]] = {}
        self.accounts: dict[str, dict[str, Any]] = {}
        self.evidence: dict[str, dict[str, Any]] = {}
        self.account_by_key: dict[tuple[str, str, str], str] = {}
        self.account_by_url: dict[str, str] = {}
        self.accepted_seen: set[str] = set()

    def add_evidence(
        self,
        *,
        source_url: str,
        source_kind: str,
        observed_at: str,
        summary: str,
        supports: list[str],
        subject_ids: list[str],
        provenance: str,
    ) -> str:
        source_url = normalize_url(source_url)
        normalized_supports = sorted({str(value).strip() for value in supports if str(value).strip()})
        if not normalized_supports:
            raise ValueError("evidence requires supports")
        identity = {
            "source_url": source_url,
            "source_kind": source_kind,
            "observed_at": observed_at,
            "summary": summary,
            "supports": normalized_supports,
            "provenance": provenance,
        }
        eid = _evidence_id(identity)
        subjects = sorted({subject for subject in subject_ids if subject})
        if eid in self.evidence:
            existing = self.evidence[eid]
            comparison = {key: existing[key] for key in identity}
            if comparison != identity:
                raise ValueError(f"evidence hash collision for {eid}")
            existing["subject_ids"] = sorted(set(existing["subject_ids"]) | set(subjects))
        else:
            self.evidence[eid] = dict(identity, evidence_id=eid, subject_ids=subjects)
        return eid

    def ensure_creator(
        self,
        persona_id: str,
        canonical_name: str,
        *,
        agency: str = "Independent",
        lifecycle_status: str = "active",
        source_class: str,
        aliases: list[str] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(persona_id, str) or not persona_id.strip():
            raise ValueError("resolved persona_id is required")
        canonical_name = _first_text(canonical_name)
        if canonical_name is None:
            raise ValueError(f"canonical name missing for {persona_id}")
        record = self.creators.get(persona_id)
        if record is None:
            record = {
                "persona_id": persona_id,
                "canonical_name": canonical_name,
                "aliases": [],
                "agency": _first_text(agency, default="Independent"),
                "lifecycle_status": _first_text(lifecycle_status, default="active"),
                "eligibility": "vtuber",
                "identity_status": "verified",
                "source_class": source_class,
                "evidence_ids": [],
            }
            self.creators[persona_id] = record
        elif record["canonical_name"] != canonical_name and canonical_name not in record["aliases"]:
            record["aliases"].append(canonical_name)
        for alias in aliases or []:
            if isinstance(alias, str) and alias.strip():
                value = alias.strip()
                if value != record["canonical_name"] and value not in record["aliases"]:
                    record["aliases"].append(value)
        record["aliases"].sort(key=lambda value: value.casefold())
        return record

    def register_account(self, account: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        platform = normalize_platform(account["platform"])
        key = _canonical_account_key(platform, account.get("platform_id"), account["url"])
        normalized_url = normalize_url(account["url"])
        existing_ids = {self.account_by_key[key]} if key in self.account_by_key else set()
        if normalized_url in self.account_by_url:
            existing_ids.add(self.account_by_url[normalized_url])
        if len(existing_ids) > 1:
            raise ValueError(f"account identity keys disagree for {account['url']}")
        if existing_ids:
            existing = self.accounts[next(iter(existing_ids))]
            if existing["persona_id"] != account["persona_id"]:
                raise ValueError(f"conflicting persona for account {account['url']}")
            return existing, False
        aid = account["account_id"]
        if aid in self.accounts:
            raise ValueError(f"duplicate stable account ID {aid}")
        self.accounts[aid] = account
        self.account_by_key[key] = aid
        self.account_by_url[normalized_url] = aid
        return account, True

    def add_baseline(self) -> None:
        seen_channels: set[str] = set()
        baseline_rows = sorted(self.baseline, key=lambda item: str(item.get("channel_id") or ""))
        handle_counts: dict[str, int] = {}
        for row in baseline_rows:
            cid = _first_text(row.get("channel_id"))
            url = _first_text(row.get("channel_url"), row.get("url"), default=f"https://www.youtube.com/channel/{cid}")
            reported = _first_text(row.get("handle")) or _url_handle("youtube", url, cid)
            key = normalize_handle(reported)
            handle_counts[key] = handle_counts.get(key, 0) + 1
        for row in baseline_rows:
            cid = _first_text(row.get("channel_id"))
            if cid is None:
                raise ValueError("baseline row missing channel_id")
            if cid in seen_channels:
                raise ValueError(f"duplicate baseline Channel ID: {cid}")
            seen_channels.add(cid)
            name = _first_text(row.get("canonical_name"), row.get("name"), row.get("display_name"), default=cid)
            pid = _first_text(row.get("person_id")) or stable_persona_id(f"baseline:{cid}")
            url = _first_text(row.get("channel_url"), row.get("url"), default=f"https://www.youtube.com/channel/{cid}")
            creator = self.ensure_creator(
                pid,
                name,
                agency=_first_text(row.get("agency"), default="Independent"),
                lifecycle_status=_first_text(row.get("activity_status"), default="active"),
                source_class="trusted_baseline",
                aliases=[value for value in (row.get("name"), row.get("display_name")) if isinstance(value, str)],
            )
            reported_handle = _first_text(row.get("handle")) or _url_handle("youtube", url, cid)
            ambiguous_legacy_handle = handle_counts[normalize_handle(reported_handle)] > 1
            handle = cid if ambiguous_legacy_handle else reported_handle
            account = {
                "account_id": stable_account_id("youtube", cid, url),
                "persona_id": pid,
                "platform": "youtube",
                "platform_id": cid,
                "handle": handle,
                "url": url,
                "display_name": _first_text(row.get("name"), row.get("display_name"), name, default=name),
                "account_status": "available" if row.get("enabled", True) is not False else "disabled",
                "is_primary": row.get("channel_type") in (None, "", "main", "primary"),
                "eligibility_source": "trusted_baseline",
                "identity_resolution": "exact_platform_id",
                "evidence_ids": [],
                "metadata": {},
            }
            for field in sorted(RESERVED_METADATA_FIELDS):
                if field in row:
                    account["metadata"][field] = row[field]
            if ambiguous_legacy_handle:
                account["metadata"]["legacy_handle"] = reported_handle
                account["metadata"]["handle_resolution"] = "ambiguous_legacy_handle_uses_channel_id"
            actual, created = self.register_account(account)
            if not created:
                raise ValueError(f"baseline account unexpectedly deduplicated: {cid}")
            observed = _first_text(row.get("checked_date"), default=BASELINE_OBSERVED_AT)
            eid = self.add_evidence(
                source_url=url,
                source_kind="trusted_baseline",
                observed_at=observed,
                summary="Trusted pre-refactor baseline confirms this YouTube Channel ID as an eligible virtual persona account.",
                supports=["account_ownership", "persona_identity"],
                subject_ids=[pid, actual["account_id"]],
                provenance="trusted_baseline_1370",
            )
            actual["evidence_ids"].append(eid)
            creator["evidence_ids"].append(eid)

    def attach_trusted_baseline_discoveries(self) -> None:
        for row in self.review_rows:
            if row.get("eligibility") != "trusted_baseline":
                continue
            cid = _first_text(row.get("channel_id"), row.get("platform_id"))
            if cid is None:
                raise ValueError(f"trusted_baseline discovery missing Channel ID: {row.get('discovery_id')}")
            key = ("id", "youtube", cid)
            aid = self.account_by_key.get(key)
            if aid is None:
                raise ValueError(f"trusted_baseline discovery not present in baseline: {row.get('discovery_id')}")
            metadata = self.accounts[aid]["metadata"]
            ids = set(metadata.get("trusted_baseline_discovery_ids", []))
            ids.add(row["discovery_id"])
            metadata["trusted_baseline_discovery_ids"] = sorted(ids)

    def resolution_evidence(self, resolution: dict[str, Any], persona_id: str, account_id: str) -> list[str]:
        account_evidence: list[str] = []
        persona_evidence: list[str] = []
        reviewer = _first_text(resolution.get("reviewer"))
        records = resolution.get("evidence")
        if not isinstance(records, list) or not records:
            raise ValueError(f"resolution {resolution.get('discovery_id')} lacks evidence")
        for evidence in records:
            if not isinstance(evidence, dict):
                raise ValueError("resolution evidence must be objects")
            supports = evidence.get("supports", [])
            if not isinstance(supports, list):
                raise ValueError("resolution evidence supports must be an array")
            subjects = []
            if "persona_identity" in supports:
                subjects.append(persona_id)
            if "account_ownership" in supports:
                subjects.append(account_id)
            if not subjects:
                continue
            eid = self.add_evidence(
                source_url=evidence["source_url"],
                source_kind=_first_text(evidence.get("source_kind"), default="official_profile"),
                observed_at=_first_text(evidence.get("observed_at"), default=BASELINE_OBSERVED_AT),
                summary=_first_text(evidence.get("summary"), default="Reviewed official identity evidence."),
                supports=supports,
                subject_ids=subjects,
                provenance=_source_provenance(evidence, reviewer),
            )
            if account_id in subjects:
                account_evidence.append(eid)
            if persona_id in subjects:
                persona_evidence.append(eid)
        if not account_evidence:
            raise ValueError(f"resolution {resolution.get('discovery_id')} lacks account ownership evidence")
        if not persona_evidence:
            raise ValueError(f"resolution {resolution.get('discovery_id')} lacks persona identity evidence")
        creator = self.creators[persona_id]
        creator["evidence_ids"] = sorted(set(creator["evidence_ids"]) | set(persona_evidence))
        return sorted(set(account_evidence))

    def apply_resolutions(self) -> None:
        accepted = {did for did, row in self.review.items() if row.get("eligibility") == "vtuber"}
        rows_by_id: dict[str, dict[str, Any]] = {}
        for resolution in self.resolution_rows:
            did = resolution.get("discovery_id")
            if not isinstance(did, str) or not did:
                raise ValueError("resolution missing discovery_id")
            if did in rows_by_id:
                raise ValueError(f"duplicate resolution: {did}")
            rows_by_id[did] = resolution
        missing = accepted - rows_by_id.keys()
        extra = rows_by_id.keys() - accepted
        if missing or extra:
            raise ValueError(
                f"resolution coverage mismatch: missing={sorted(missing)[:5]} extra={sorted(extra)[:5]}"
            )
        if self.resolutions_have_failures():
            raise ValueError("sealed resolution ledger contains unresolved/conflicting rows")

        for did in sorted(accepted):
            review = self.review[did]
            resolution = rows_by_id[did]
            if resolution.get("conflict") is not False:
                raise ValueError(f"resolution conflict flag is not false: {did}")
            pid = _first_text(resolution.get("persona_id"))
            if pid is None:
                raise ValueError(f"resolution missing persona ID: {did}")
            canonical_name = _first_text(resolution.get("canonical_name"), review.get("display_name"))
            creator = self.ensure_creator(
                pid,
                canonical_name,
                agency=_first_text(review.get("agency"), default="Independent"),
                lifecycle_status="active",
                source_class="trusted_baseline" if pid in self.creators else "reviewed_discovery",
                aliases=[],
            )
            platform = normalize_platform(_first_text(resolution.get("platform"), review.get("platform")))
            platform_id = _first_text(resolution.get("platform_id"), review.get("channel_id"), review.get("platform_id"))
            url = _first_text(resolution.get("url"), review.get("url"))
            # Discovery labels can describe a parent portfolio/client relation and
            # are not account identifiers.  Only an explicit reviewed handle or
            # the accepted canonical URL may define the handle index.
            handle = _first_text(review.get("handle")) or _url_handle(platform, url, platform_id)
            provisional = {
                "account_id": stable_account_id(platform, platform_id, url),
                "persona_id": pid,
                "platform": platform,
                "platform_id": platform_id,
                "handle": handle,
                "url": url,
                "display_name": canonical_name,
                "account_status": "available",
                "is_primary": True,
                "eligibility_source": "review_bundle:vtuber",
                "identity_resolution": _first_text(resolution.get("method"), default="explicit_official_identity"),
                "evidence_ids": [],
                "metadata": {
                    "discovery_ids": [did],
                    "resolution_outcome": resolution.get("outcome"),
                    "reviewer": resolution.get("reviewer"),
                    "discovery_display_name": review.get("display_name"),
                    "discovery_original_name": review.get("original_name"),
                    "review_reason": review.get("reason"),
                },
            }
            actual, created = self.register_account(provisional)
            if not created:
                ids = set(actual["metadata"].get("discovery_ids", []))
                ids.add(did)
                actual["metadata"]["discovery_ids"] = sorted(ids)
                if actual["persona_id"] != pid:
                    raise ValueError(f"accepted account deduplicates to another persona: {did}")
            evidence_ids = self.resolution_evidence(resolution, pid, actual["account_id"])
            actual["evidence_ids"] = sorted(set(actual["evidence_ids"]) | set(evidence_ids))
            creator["evidence_ids"] = sorted(set(creator["evidence_ids"]))
            self.accepted_seen.add(did)

    def resolutions_have_failures(self) -> bool:
        return bool(
            self._resolution_collection("unresolved")
            or self._resolution_collection("conflicts")
        )

    def _resolution_collection(self, key: str) -> list[Any]:
        value = self._resolution_payload.get(key, []) if hasattr(self, "_resolution_payload") else []
        return value if isinstance(value, list) else [value]

    def build(self, resolution_payload: dict[str, Any]) -> dict[str, Any]:
        self._resolution_payload = resolution_payload
        self.add_baseline()
        self.attach_trusted_baseline_discoveries()
        self.apply_resolutions()
        for creator in self.creators.values():
            creator["evidence_ids"] = sorted(set(creator["evidence_ids"]))
            if not creator["evidence_ids"]:
                raise ValueError(f"creator {creator['persona_id']} lacks evidence")
        for account in self.accounts.values():
            account["evidence_ids"] = sorted(set(account["evidence_ids"]))
            if not account["evidence_ids"]:
                raise ValueError(f"account {account['account_id']} lacks evidence")
        payload = {
            "schema_version": 2,
            "dataset_name": DATASET_NAME,
            "identity_policy": IDENTITY_POLICY,
            "source_fingerprints": {
                "trusted_baseline_1370": _semantic_sha256(self.baseline),
                "review_bundle": _semantic_sha256({"schema_version": 1, "rows": self.review_rows}),
                "identity_resolutions": _semantic_sha256(resolution_payload),
            },
            "counts": {},
            "creators": sorted(self.creators.values(), key=lambda row: row["persona_id"]),
            "accounts": sorted(self.accounts.values(), key=lambda row: row["account_id"]),
            "evidence": sorted(self.evidence.values(), key=lambda row: row["evidence_id"]),
        }
        payload["counts"] = {
            "creators": len(payload["creators"]),
            "accounts": len(payload["accounts"]),
            "evidence": len(payload["evidence"]),
        }
        validate_registry(payload)
        return payload


def build_registry(baseline: list[dict[str, Any]], review_bundle: dict[str, Any], resolutions: dict[str, Any]) -> dict[str, Any]:
    """Return a validated, byte-stable canonical payload from reviewed inputs."""
    builder = _RegistryBuilder(baseline, review_bundle, resolutions)
    return builder.build(resolutions)


def write_registry_atomic(payload: dict[str, Any], path: Path) -> Path:
    """Validate and atomically replace *path*, preserving the old file on failure."""
    validate_registry(payload)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    try:
        temporary.write_text(raw, encoding="utf-8")
        temporary.replace(path)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        finally:
            raise
    return path


def _load(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _production_assertions(baseline, review, payload):
    baseline_ids = {row["channel_id"] for row in baseline}
    canonical_youtube_ids = {
        row["platform_id"] for row in payload["accounts"] if row["platform"] == "youtube"
    }
    accepted = {
        row["discovery_id"] for row in review["rows"] if row.get("eligibility") == "vtuber"
    }
    represented = {
        did
        for account in payload["accounts"]
        for did in account.get("metadata", {}).get("discovery_ids", [])
    }
    excluded = {
        row["discovery_id"]
        for row in review["rows"]
        if row.get("eligibility") not in {"vtuber", "trusted_baseline"}
    }
    if not baseline_ids <= canonical_youtube_ids:
        raise ValueError("canonical registry dropped baseline YouTube Channel IDs")
    if not accepted <= represented:
        raise ValueError("canonical registry dropped accepted discovery IDs")
    if excluded & represented:
        raise ValueError("excluded/unavailable discoveries entered canonical registry")
    return {
        "baseline_channel_ids": len(baseline_ids),
        "accepted_discovery_ids": len(accepted),
        "represented_accepted_discovery_ids": len(accepted & represented),
        "excluded_or_unavailable_represented": len(excluded & represented),
        "youtube_accounts": len(canonical_youtube_ids),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--review-bundle", required=True, type=Path)
    parser.add_argument("--resolutions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    baseline = _load(args.baseline)
    review = _load(args.review_bundle)
    resolutions = _load(args.resolutions)
    payload = build_registry(baseline, review, resolutions)
    assertions = _production_assertions(baseline, review, payload)
    write_registry_atomic(payload, args.output)
    print(json.dumps({"counts": payload["counts"], "assertions": assertions}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
