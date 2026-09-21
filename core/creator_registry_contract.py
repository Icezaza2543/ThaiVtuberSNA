"""Validation and stable identifiers for the canonical creator registry."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit


SCHEMA_VERSION = 2
PLATFORMS = {
    "youtube",
    "twitch",
    "x",
    "tiktok",
    "instagram",
    "facebook",
    "bluesky",
    "website",
    "ganknow",
}
PLATFORM_ALIASES = {"twitter": "x", "carrd": "website", "linktree": "website"}
YOUTUBE_CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "dataset_name",
    "identity_policy",
    "source_fingerprints",
    "counts",
    "creators",
    "accounts",
    "evidence",
}
_CREATOR_FIELDS = {
    "persona_id",
    "canonical_name",
    "aliases",
    "agency",
    "lifecycle_status",
    "eligibility",
    "identity_status",
    "source_class",
    "evidence_ids",
}
_ACCOUNT_FIELDS = {
    "account_id",
    "persona_id",
    "platform",
    "platform_id",
    "handle",
    "url",
    "display_name",
    "account_status",
    "is_primary",
    "eligibility_source",
    "identity_resolution",
    "evidence_ids",
    "metadata",
}
_EVIDENCE_FIELDS = {
    "evidence_id",
    "source_url",
    "source_kind",
    "observed_at",
    "summary",
    "supports",
    "subject_ids",
    "provenance",
}


def normalize_platform(platform: str) -> str:
    """Return the canonical platform name, resolving supported aliases."""
    if not isinstance(platform, str) or not platform.strip():
        raise ValueError("platform is required")
    return PLATFORM_ALIASES.get(platform.strip().lower(), platform.strip().lower())


def normalize_url(url: str) -> str:
    """Return a canonical HTTP(S) URL suitable for identity comparison."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL is required")
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else ""
    if scheme not in {"http", "https"} or not host:
        raise ValueError(f"invalid URL: {url!r}")
    port = parsed.port
    netloc = host
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = f"{host}:{port}"
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def normalize_handle(handle: str) -> str:
    """Return a platform-scoped canonical handle without display decoration."""
    if not isinstance(handle, str) or not handle.strip():
        raise ValueError("handle is required")
    normalized = handle.strip().lstrip("@").casefold()
    if not normalized:
        raise ValueError("handle is required")
    return normalized


def stable_account_id(platform: str, platform_id: str | None, url: str) -> str:
    """Create an ID from a canonical platform identity, never array position."""
    canonical_platform = normalize_platform(platform)
    identity = platform_id.strip() if isinstance(platform_id, str) and platform_id.strip() else normalize_url(url)
    key = f"{canonical_platform}:{identity}"
    return "account_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]


def stable_persona_id(seed: str) -> str:
    """Create a deterministic persona ID from a resolved identity seed."""
    if not isinstance(seed, str) or not seed.strip():
        raise ValueError("persona seed is required")
    canonical_seed = " ".join(seed.split()).casefold()
    return "persona_" + hashlib.sha256(canonical_seed.encode("utf-8")).hexdigest()[:20]


def _required(record: dict[str, Any], fields: set[str], kind: str) -> None:
    if not isinstance(record, dict):
        raise ValueError(f"{kind} must be an object")
    missing = fields - record.keys()
    if missing:
        raise ValueError(f"{kind} missing required fields: {', '.join(sorted(missing))}")


def _nonempty_string(record: dict[str, Any], field: str, kind: str) -> str:
    value = record[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{kind} {field} is required")
    return value.strip()


def _string_list(record: dict[str, Any], field: str, kind: str, *, required: bool = False) -> list[str]:
    value = record[field]
    if not isinstance(value, list) or (required and not value):
        qualifier = "a non-empty array" if required else "an array"
        raise ValueError(f"{kind} {field} must be {qualifier}")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{kind} {field} must contain non-empty strings")
    return value


def _evidence_references_exist(
    owner_kind: str, owner_id: str, evidence_ids: Any, evidence_by_id: dict[str, dict[str, Any]]
) -> None:
    if not isinstance(evidence_ids, list) or not evidence_ids or any(
        not isinstance(evidence_id, str) or not evidence_id.strip() for evidence_id in evidence_ids
    ):
        raise ValueError(f"{owner_kind} {owner_id} requires evidence")
    for evidence_id in evidence_ids:
        if evidence_id not in evidence_by_id:
            raise ValueError(f"{owner_kind} {owner_id} references unknown evidence {evidence_id!r}")
        if owner_id not in evidence_by_id[evidence_id]["subject_ids"]:
            raise ValueError(f"evidence {evidence_id!r} does not support {owner_kind} {owner_id}")


def validate_registry(payload: dict) -> None:
    """Fail closed when a canonical registry violates an identity invariant."""
    if not isinstance(payload, dict):
        raise ValueError("registry payload must be an object")
    missing = _TOP_LEVEL_FIELDS - payload.keys()
    if missing:
        raise ValueError(f"registry missing required fields: {', '.join(sorted(missing))}")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema version: {payload['schema_version']!r}")
    for field in ("dataset_name", "identity_policy"):
        _nonempty_string(payload, field, "registry")
    if not isinstance(payload["source_fingerprints"], dict) or any(
        not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip()
        for key, value in payload["source_fingerprints"].items()
    ):
        raise ValueError("registry source_fingerprints must be an object of non-empty strings")
    for name in ("creators", "accounts", "evidence"):
        if not isinstance(payload[name], list):
            raise ValueError(f"registry {name} must be an array")
    if not isinstance(payload["counts"], dict):
        raise ValueError("registry counts must be an object")
    count_keys = {"creators", "accounts", "evidence"}
    if set(payload["counts"]) != count_keys:
        raise ValueError("registry counts must contain exactly creators, accounts, and evidence")
    for name in ("creators", "accounts", "evidence"):
        if not isinstance(payload["counts"][name], int) or isinstance(payload["counts"][name], bool):
            raise ValueError(f"count {name} must be an integer")
        if payload["counts"].get(name) != len(payload[name]):
            raise ValueError(f"count mismatch for {name}")

    creator_ids: set[str] = set()
    creators_by_id: dict[str, dict[str, Any]] = {}
    for creator in payload["creators"]:
        _required(creator, _CREATOR_FIELDS, "creator")
        persona_id = _nonempty_string(creator, "persona_id", "creator")
        for field in ("canonical_name", "agency", "lifecycle_status", "eligibility", "identity_status", "source_class"):
            _nonempty_string(creator, field, "creator")
        _string_list(creator, "aliases", "creator")
        _string_list(creator, "evidence_ids", "creator", required=True)
        if persona_id in creator_ids:
            raise ValueError(f"duplicate persona {persona_id!r}")
        if creator["eligibility"] != "vtuber":
            raise ValueError(f"creator {persona_id} eligibility must equal 'vtuber'")
        creator_ids.add(persona_id)
        creators_by_id[persona_id] = creator

    account_ids: set[str] = set()
    account_identity: dict[tuple[str, str], dict[str, Any]] = {}
    handle_identity: dict[tuple[str, str], dict[str, Any]] = {}
    url_identity: dict[str, dict[str, Any]] = {}
    for account in payload["accounts"]:
        _required(account, _ACCOUNT_FIELDS, "account")
        account_id = _nonempty_string(account, "account_id", "account")
        persona_id = _nonempty_string(account, "persona_id", "account")
        for field in (
            "platform",
            "handle",
            "url",
            "display_name",
            "account_status",
            "eligibility_source",
            "identity_resolution",
        ):
            _nonempty_string(account, field, "account")
        if not isinstance(account["is_primary"], bool):
            raise ValueError(f"account {account_id} is_primary must be a boolean")
        if not isinstance(account["metadata"], dict):
            raise ValueError(f"account {account_id} metadata must be an object")
        _string_list(account, "evidence_ids", "account", required=True)
        if account_id in account_ids:
            raise ValueError(f"duplicate account ID {account_id!r}")
        if persona_id not in creator_ids:
            raise ValueError(f"account {account_id} references unknown persona {persona_id!r}")
        platform = normalize_platform(account["platform"])
        if platform not in PLATFORMS:
            raise ValueError(f"unsupported platform {account['platform']!r}")
        platform_id = account["platform_id"]
        if platform_id is not None and (not isinstance(platform_id, str) or not platform_id.strip()):
            raise ValueError(f"account {account_id} platform_id must be a non-empty string or null")
        if platform == "youtube":
            if not isinstance(platform_id, str) or not YOUTUBE_CHANNEL_ID.fullmatch(platform_id):
                raise ValueError(f"account {account_id} has invalid YouTube Channel ID")
        normalized_url = normalize_url(account["url"])
        handle_key = (platform, normalize_handle(account["handle"]))
        previous_handle = handle_identity.get(handle_key)
        if previous_handle:
            if previous_handle["persona_id"] != persona_id:
                raise ValueError(f"conflicting persona for account handle {handle_key!r}")
            raise ValueError(f"duplicate account handle {handle_key!r}")
        handle_identity[handle_key] = account
        if platform_id:
            identity_key = (platform, platform_id)
            previous = account_identity.get(identity_key)
            if previous:
                if previous["persona_id"] != persona_id:
                    raise ValueError(f"conflicting persona for account identity {identity_key!r}")
                raise ValueError(f"duplicate account identity {identity_key!r}")
            account_identity[identity_key] = account
        previous_url = url_identity.get(normalized_url)
        if previous_url:
            if previous_url["persona_id"] != persona_id:
                raise ValueError(f"conflicting persona for URL {normalized_url!r}")
            raise ValueError(f"duplicate account URL {normalized_url!r}")
        url_identity[normalized_url] = account
        account_ids.add(account_id)

    evidence_by_id: dict[str, dict[str, Any]] = {}
    known_subject_ids = creator_ids | account_ids
    for evidence in payload["evidence"]:
        _required(evidence, _EVIDENCE_FIELDS, "evidence")
        evidence_id = _nonempty_string(evidence, "evidence_id", "evidence")
        for field in ("source_url", "source_kind", "observed_at", "summary", "provenance"):
            _nonempty_string(evidence, field, "evidence")
        _string_list(evidence, "supports", "evidence", required=True)
        subject_ids = _string_list(evidence, "subject_ids", "evidence", required=True)
        if evidence_id in evidence_by_id:
            raise ValueError(f"duplicate evidence {evidence_id!r}")
        normalize_url(evidence["source_url"])
        unknown_subjects = set(subject_ids) - known_subject_ids
        if unknown_subjects:
            raise ValueError(f"evidence {evidence_id} references unknown subject {sorted(unknown_subjects)!r}")
        evidence_by_id[evidence_id] = evidence

    referenced_evidence_ids: set[str] = set()
    for persona_id, creator in creators_by_id.items():
        _evidence_references_exist("creator", persona_id, creator["evidence_ids"], evidence_by_id)
        referenced_evidence_ids.update(creator["evidence_ids"])
    accounts_by_persona = {persona_id: 0 for persona_id in creator_ids}
    for account in payload["accounts"]:
        accounts_by_persona[account["persona_id"]] += 1
        _evidence_references_exist("account", account["account_id"], account["evidence_ids"], evidence_by_id)
        referenced_evidence_ids.update(account["evidence_ids"])
    for persona_id, count in accounts_by_persona.items():
        if count == 0:
            raise ValueError(f"creator {persona_id} requires an account")
    orphaned_evidence = set(evidence_by_id) - referenced_evidence_ids
    if orphaned_evidence:
        raise ValueError(f"orphan evidence {sorted(orphaned_evidence)!r}")
