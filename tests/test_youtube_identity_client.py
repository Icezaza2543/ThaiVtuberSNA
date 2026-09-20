import json
from pathlib import Path

import pytest

from collector.youtube_identity_client import YouTubeIdentityClient


CHANNEL_ID = "UC" + "A" * 22
SECOND_CHANNEL_ID = "UC" + "B" * 22
VIDEO_ID = "abcdefghijk"
YOUTUBE_URL = f"https://www.youtube.com/channel/{CHANNEL_ID}"


class FakeRequest:
    def __init__(self, response, error=None):
        self.response = response
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return self.response


class FakeResource:
    def __init__(self, service, name):
        self.service = service
        self.name = name

    def list(self, **kwargs):
        self.service.calls.append((f"{self.name}.list", kwargs))
        self.service.execute_count += 1
        if self.service.list_error:
            raise self.service.list_error
        if self.service.error:
            return FakeRequest({}, self.service.error)
        if self.name == "videos":
            return FakeRequest({"items": [{"snippet": {"channelId": self.service.video_owner}}]})
        return FakeRequest({"items": [{"id": self.service.returned_channel_id, "snippet": {
            "title": "Test Channel", "description": "A safe description"
        }}]})


class FakeService:
    def __init__(self, error=None, *, video_owner=CHANNEL_ID, returned_channel_id=CHANNEL_ID,
                 channels_error=None, list_error=None):
        self.calls = []
        self.execute_count = 0
        self.error = error
        self.video_owner = video_owner
        self.returned_channel_id = returned_channel_id
        self.channels_error = channels_error
        self.list_error = list_error

    def videos(self):
        return FakeResource(self, "videos")

    def channels(self):
        if self.channels_error:
            raise self.channels_error
        return FakeResource(self, "channels")


@pytest.fixture
def fake_service():
    return FakeService()


def test_channel_url_resolves_channel_evidence(fake_service, tmp_path):
    """Removing the direct channel branch must fail this resolved evidence contract."""
    result = YouTubeIdentityClient("secret-test-key", cache_dir=tmp_path, service=fake_service).resolve(YOUTUBE_URL)

    assert result.channel_id == CHANNEL_ID
    assert result.canonical_url == f"https://www.youtube.com/channel/{CHANNEL_ID}"
    assert result.title == "Test Channel"
    assert result.description == "A safe description"
    assert result.source_resource == f"channel:{CHANNEL_ID}"
    assert result.quota_units == 1
    assert fake_service.calls == [("channels.list", {"part": "snippet", "id": CHANNEL_ID})]


def test_handle_url_resolves_channel_evidence(fake_service, tmp_path):
    """Dropping handle parsing or its API selector must fail this behavior."""
    result = YouTubeIdentityClient("secret-test-key", cache_dir=tmp_path, service=fake_service).resolve(
        "https://youtube.com/@Test_Handle/about"
    )

    assert result.channel_id == CHANNEL_ID
    assert result.source_resource == "handle:@test_handle"
    assert fake_service.calls == [("channels.list", {"part": "snippet", "forHandle": "@Test_Handle"})]


@pytest.mark.parametrize("url", [
    f"https://youtube.com/watch?v={VIDEO_ID}",
    f"https://youtube.com/shorts/{VIDEO_ID}",
])
def test_video_urls_resolve_and_confirm_video_owner(fake_service, tmp_path, url):
    """Skipping owner confirmation after a video lookup must fail this evidence contract."""
    result = YouTubeIdentityClient("secret-test-key", cache_dir=tmp_path, service=fake_service).resolve(url)

    assert result.channel_id == CHANNEL_ID
    assert result.source_resource == f"video:{VIDEO_ID}"
    assert fake_service.calls == [
        ("videos.list", {"part": "snippet", "id": VIDEO_ID}),
        ("channels.list", {"part": "snippet", "id": CHANNEL_ID}),
    ]
    assert result.quota_units == 2


def test_video_owner_requires_matching_confirmed_channel_id(tmp_path):
    """Returning another valid channel ID after video-owner lookup must fail closed."""
    service = FakeService(video_owner=CHANNEL_ID, returned_channel_id=SECOND_CHANNEL_ID)
    client = YouTubeIdentityClient("secret-test-key", cache_dir=tmp_path, service=service)

    with pytest.raises(RuntimeError, match="did not confirm video owner"):
        client.resolve(f"https://youtube.com/watch?v={VIDEO_ID}")
    assert not list(Path(tmp_path).rglob("*.json"))


def test_cache_avoids_second_api_call(fake_service, tmp_path):
    """Bypassing a cached successful resource must fail this no-repeat-call behavior."""
    client = YouTubeIdentityClient("secret-test-key", cache_dir=tmp_path, service=fake_service)

    assert client.resolve(YOUTUBE_URL) == client.resolve(YOUTUBE_URL)
    assert fake_service.execute_count == 1


def test_cached_success_is_usable_without_api_key(fake_service, tmp_path):
    """Requiring a key before consulting cache must fail this offline reuse behavior."""
    keyed_client = YouTubeIdentityClient("secret-test-key", cache_dir=tmp_path, service=fake_service)
    expected = keyed_client.resolve(YOUTUBE_URL)

    assert YouTubeIdentityClient("", cache_dir=tmp_path).resolve(YOUTUBE_URL) == expected


def test_cached_evidence_with_mismatched_canonical_channel_fails_closed(fake_service, tmp_path):
    """Accepting cached evidence whose channel ID disagrees with its canonical URL must fail closed."""
    client = YouTubeIdentityClient("secret-test-key", cache_dir=tmp_path, service=fake_service)
    client.resolve(f"https://youtube.com/watch?v={VIDEO_ID}")
    cache_file = next(Path(tmp_path).rglob("*.json"))
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    if payload["source_resource"] != f"video:{VIDEO_ID}":
        cache_file = next(path for path in Path(tmp_path).rglob("*.json")
                          if json.loads(path.read_text(encoding="utf-8"))["source_resource"] == f"video:{VIDEO_ID}")
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    payload["channel_id"] = "UC" + "B" * 22
    cache_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="conflicting cached evidence"):
        client.resolve(f"https://youtube.com/watch?v={VIDEO_ID}")


@pytest.mark.parametrize("url", [
    "https://example.com/channel/UC" + "A" * 22,
    "https://youtube.com/watch",
    "https://youtube.com/shorts/not a video id",
    "not a url",
])
def test_invalid_url_fails_safely(tmp_path, url):
    """Relaxing URL validation must fail this malformed-input boundary."""
    with pytest.raises(RuntimeError, match="valid YouTube"):
        YouTubeIdentityClient("secret-test-key", cache_dir=tmp_path).resolve(url)


def test_missing_key_without_cache_fails_safely(tmp_path):
    """Attempting an uncached lookup without credentials must fail before service creation."""
    with pytest.raises(RuntimeError, match="YOUTUBE_API_KEY"):
        YouTubeIdentityClient("", cache_dir=tmp_path).resolve(YOUTUBE_URL)


def test_quota_error_fails_without_persisting_secret(tmp_path):
    """Turning an API quota failure into success or cached data must fail this safety boundary."""
    client = YouTubeIdentityClient("secret-test-key", cache_dir=tmp_path,
                                   service=FakeService(error=RuntimeError("quota exceeded")))

    with pytest.raises(RuntimeError, match="YouTube identity lookup failed") as error:
        client.resolve(YOUTUBE_URL)
    assert "secret-test-key" not in str(error.value)
    assert not list(Path(tmp_path).rglob("*.json"))


def test_cache_and_errors_never_contain_api_key(tmp_path):
    """Leaking a credential through cache or an exception must fail this secret boundary."""
    secret = "secret-test-key"
    client = YouTubeIdentityClient(secret, cache_dir=tmp_path,
                                   service=FakeService(error=RuntimeError(secret)))

    with pytest.raises(RuntimeError) as error:
        client.resolve(YOUTUBE_URL)
    assert secret not in str(error.value)
    assert secret not in "".join(path.read_text(encoding="utf-8") for path in Path(tmp_path).rglob("*"))


@pytest.mark.parametrize("failure", ["channels", "list"])
def test_service_setup_errors_never_expose_api_key_or_write_cache(tmp_path, failure):
    """Letting a service accessor or list error escape would disclose its credential-bearing message."""
    secret = "secret-from-service"
    service = FakeService(
        channels_error=RuntimeError(secret) if failure == "channels" else None,
        list_error=RuntimeError(secret) if failure == "list" else None,
    )

    with pytest.raises(RuntimeError, match="YouTube identity lookup failed") as error:
        YouTubeIdentityClient(secret, cache_dir=tmp_path, service=service).resolve(YOUTUBE_URL)
    assert secret not in str(error.value)
    assert not list(Path(tmp_path).rglob("*.json"))
