"""Read-only, cached YouTube channel identity resolution."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

from config.settings import CREATOR_IDENTITY_CACHE_DIR, YOUTUBE_API_KEY


_CHANNEL_ID = re.compile(r"UC[A-Za-z0-9_-]{22}\Z")
_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}


@dataclass(frozen=True)
class ChannelEvidence:
    channel_id: str
    canonical_url: str
    title: str
    description: str
    source_resource: str
    quota_units: int


class YouTubeIdentityClient:
    """Resolve YouTube URLs without mutating YouTube or quota-control state."""

    def __init__(self, api_key: str | None = None, *, cache_dir: Path | None = None, service=None):
        self._api_key = YOUTUBE_API_KEY if api_key is None else api_key
        self._cache_dir = Path(cache_dir or CREATOR_IDENTITY_CACHE_DIR) / "youtube"
        self._service = service

    def resolve(self, url: str) -> ChannelEvidence:
        kind, identifier, api_identifier, source_resource = self._parse_url(url)
        cached = self._read_cache(source_resource)
        if cached is not None:
            return cached
        if not self._api_key:
            raise RuntimeError("YOUTUBE_API_KEY is required for an uncached YouTube identity lookup")

        service = self._service or self._build_service()
        try:
            if kind == "channel":
                evidence = self._channel_evidence(service, api_identifier, source_resource, quota_units=1)
            elif kind == "handle":
                response = self._execute(service.channels().list(part="snippet", forHandle=api_identifier))
                evidence = self._evidence_from_channel_response(response, source_resource, quota_units=1)
            else:
                video = self._execute(service.videos().list(part="snippet", id=identifier))
                owner = self._video_owner(video)
                evidence = self._channel_evidence(service, owner, source_resource, quota_units=2)
        except RuntimeError:
            raise
        except Exception as error:
            raise RuntimeError("YouTube identity lookup failed") from None

        self._write_cache(evidence)
        return evidence

    def _build_service(self):
        try:
            from googleapiclient.discovery import build
            return build("youtube", "v3", developerKey=self._api_key, cache_discovery=False)
        except Exception:
            raise RuntimeError("YouTube identity lookup failed") from None

    @staticmethod
    def _parse_url(url: str) -> tuple[str, str, str, str]:
        if not isinstance(url, str):
            raise RuntimeError("A valid YouTube URL is required")
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in _YOUTUBE_HOSTS:
            raise RuntimeError("A valid YouTube URL is required")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "channel" and _CHANNEL_ID.fullmatch(parts[1]):
            channel_id = parts[1]
            return "channel", channel_id, channel_id, f"channel:{channel_id}"
        if parts and parts[0].startswith("@") and len(parts[0]) > 1:
            handle = parts[0]
            return "handle", handle.casefold(), handle, f"handle:{handle.casefold()}"
        if parts and parts[0] == "watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif len(parts) >= 2 and parts[0] == "shorts":
            video_id = parts[1]
        else:
            video_id = ""
        if _VIDEO_ID.fullmatch(video_id):
            return "video", video_id, video_id, f"video:{video_id}"
        raise RuntimeError("A valid YouTube URL is required")

    @staticmethod
    def _video_owner(response: object) -> str:
        try:
            channel_id = response["items"][0]["snippet"]["channelId"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("YouTube identity lookup returned no matching video") from None
        if not isinstance(channel_id, str) or not _CHANNEL_ID.fullmatch(channel_id):
            raise RuntimeError("YouTube identity lookup returned an invalid video owner")
        return channel_id

    def _channel_evidence(self, service, channel_id: str, source_resource: str, *, quota_units: int) -> ChannelEvidence:
        response = self._execute(service.channels().list(part="snippet", id=channel_id))
        return self._evidence_from_channel_response(response, source_resource, quota_units=quota_units)

    @staticmethod
    def _execute(request):
        try:
            return request.execute()
        except Exception:
            raise RuntimeError("YouTube identity lookup failed") from None

    @staticmethod
    def _evidence_from_channel_response(response: object, source_resource: str, *, quota_units: int) -> ChannelEvidence:
        try:
            item = response["items"][0]
            channel_id = item["id"]
            snippet = item["snippet"]
            title = snippet["title"]
            description = snippet["description"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("YouTube identity lookup returned no matching channel") from None
        if not isinstance(channel_id, str) or not _CHANNEL_ID.fullmatch(channel_id):
            raise RuntimeError("YouTube identity lookup returned an invalid channel")
        if not isinstance(title, str) or not isinstance(description, str):
            raise RuntimeError("YouTube identity lookup returned invalid channel metadata")
        return ChannelEvidence(
            channel_id=channel_id,
            canonical_url=f"https://www.youtube.com/channel/{channel_id}",
            title=title,
            description=description,
            source_resource=source_resource,
            quota_units=quota_units,
        )

    def _cache_path(self, source_resource: str) -> Path:
        digest = hashlib.sha256(source_resource.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{digest}.json"

    def _read_cache(self, source_resource: str) -> ChannelEvidence | None:
        path = self._cache_path(source_resource)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            evidence = ChannelEvidence(**payload)
        except Exception:
            raise RuntimeError("Invalid cached YouTube identity evidence") from None
        expected_url = f"https://www.youtube.com/channel/{evidence.channel_id}"
        if (evidence.source_resource != source_resource or
                not _CHANNEL_ID.fullmatch(evidence.channel_id) or
                evidence.canonical_url != expected_url or
                not isinstance(evidence.title, str) or
                not isinstance(evidence.description, str) or
                not isinstance(evidence.quota_units, int) or evidence.quota_units < 0):
            raise RuntimeError("conflicting cached evidence")
        return evidence

    def _write_cache(self, evidence: ChannelEvidence) -> None:
        path = self._cache_path(evidence.source_resource)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(evidence), ensure_ascii=False, sort_keys=True), encoding="utf-8")
        except Exception:
            raise RuntimeError("Unable to cache YouTube identity evidence") from None
