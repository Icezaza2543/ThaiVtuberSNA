"""Read-only indexes and compatibility exports for the creator registry."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from core.creator_registry_contract import normalize_handle, normalize_platform, normalize_url, validate_registry


class CreatorCatalog:
    """A validated registry held behind defensive, deterministic accessors."""

    def __init__(self, payload: dict[str, Any], source_bytes: bytes) -> None:
        validate_registry(payload)
        self._source_fingerprint = hashlib.sha256(source_bytes).hexdigest()
        self._creators = tuple(copy.deepcopy(payload["creators"]))
        self._accounts = tuple(self._normalized_account(account) for account in payload["accounts"])
        self._creators_by_id = {creator["persona_id"]: creator for creator in self._creators}
        self._accounts_by_persona: dict[str, tuple[dict[str, Any], ...]] = {}
        grouped: dict[str, list[dict[str, Any]]] = {}
        self._accounts_by_platform_id: dict[tuple[str, str], dict[str, Any]] = {}
        self._accounts_by_handle: dict[tuple[str, str], dict[str, Any]] = {}
        self._accounts_by_url: dict[str, dict[str, Any]] = {}
        for account in self._accounts:
            grouped.setdefault(account["persona_id"], []).append(account)
            if account["platform_id"]:
                self._accounts_by_platform_id[(account["platform"], account["platform_id"])] = account
            self._accounts_by_handle[(account["platform"], normalize_handle(account["handle"]))] = account
            self._accounts_by_url[normalize_url(account["url"])] = account
        self._accounts_by_persona = {
            persona_id: tuple(accounts) for persona_id, accounts in grouped.items()
        }

    @classmethod
    def from_path(cls, path: Path) -> "CreatorCatalog":
        source_bytes = Path(path).read_bytes()
        try:
            payload = json.loads(source_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid creator registry JSON: {path}") from exc
        return cls(payload, source_bytes)

    @staticmethod
    def _normalized_account(account: dict[str, Any]) -> dict[str, Any]:
        normalized = copy.deepcopy(account)
        normalized["platform"] = normalize_platform(normalized["platform"])
        return normalized

    @staticmethod
    def _copy(record: dict[str, Any] | None) -> dict[str, Any] | None:
        return copy.deepcopy(record) if record is not None else None

    def source_fingerprint(self) -> str:
        return self._source_fingerprint

    def creators(self) -> tuple[dict[str, Any], ...]:
        return tuple(copy.deepcopy(creator) for creator in self._creators)

    def accounts(self) -> tuple[dict[str, Any], ...]:
        return tuple(copy.deepcopy(account) for account in self._accounts)

    def creator(self, persona_id: str) -> dict[str, Any] | None:
        return self._copy(self._creators_by_id.get(persona_id))

    def accounts_for(self, persona_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(copy.deepcopy(account) for account in self._accounts_by_persona.get(persona_id, ()))

    def account_by_platform_id(self, platform: str, platform_id: str) -> dict[str, Any] | None:
        return self._copy(self._accounts_by_platform_id.get((normalize_platform(platform), platform_id)))

    def account_by_handle(self, platform: str, handle: str) -> dict[str, Any] | None:
        return self._copy(self._accounts_by_handle.get((normalize_platform(platform), normalize_handle(handle))))

    def account_by_url(self, url: str) -> dict[str, Any] | None:
        return self._copy(self._accounts_by_url.get(normalize_url(url)))

    def youtube_accounts(self) -> tuple[dict[str, Any], ...]:
        accounts = (account for account in self._accounts if account["platform"] == "youtube")
        return tuple(copy.deepcopy(account) for account in sorted(accounts, key=lambda account: account["platform_id"]))

    def youtube_rows(self) -> tuple[dict[str, Any], ...]:
        rows = []
        for account in self.youtube_accounts():
            creator = self._creators_by_id[account["persona_id"]]
            metadata = account["metadata"]
            rows.append(
                {
                    "channel_id": account["platform_id"],
                    "name": account["display_name"],
                    "handle": account["handle"],
                    "channel_url": account["url"],
                    "agency": creator["agency"],
                    "activity_status": metadata.get("activity_status", creator["lifecycle_status"]),
                    "vtuber_status": metadata.get("vtuber_status", "CONFIRMED"),
                    "person_id": creator["persona_id"],
                    "canonical_name": creator["canonical_name"],
                    "channel_type": metadata.get("channel_type", "main"),
                    "subscriber_count": metadata.get("subscriber_count"),
                    "video_count": metadata.get("video_count"),
                    "view_count": metadata.get("view_count"),
                    "last_video_published_at": metadata.get("last_video_published_at"),
                    "country": metadata.get("country"),
                    "thai_confidence": metadata.get("thai_confidence"),
                    "reference_sources": metadata.get("reference_sources"),
                    "checked_date": metadata.get("checked_date"),
                    "evidence_notes": metadata.get("evidence_notes"),
                    "enabled": metadata.get("enabled", True),
                }
            )
        return tuple(rows)
