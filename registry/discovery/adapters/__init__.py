"""Adapter registry for multi-platform discovery."""

from typing import Dict, List, Type

from .base import PlatformAdapter
from .bilibili import BilibiliAdapter
from .facebook import FacebookAdapter
from .ganknow import GankNowAdapter
from .instagram import InstagramAdapter
from .kick import KickAdapter
from .niconico import NiconicoAdapter
from .tiktok import TikTokAdapter
from .twitch import TwitchAdapter
from .x import XAdapter
from .youtube import YouTubeAdapter

ADAPTER_REGISTRY: Dict[str, Type[PlatformAdapter]] = {
    "youtube": YouTubeAdapter,
    "twitch": TwitchAdapter,
    "tiktok": TikTokAdapter,
    "facebook": FacebookAdapter,
    "instagram": InstagramAdapter,
    "x": XAdapter,
    "kick": KickAdapter,
    "ganknow": GankNowAdapter,
    "bilibili": BilibiliAdapter,
    "niconico": NiconicoAdapter,
}


def get_adapter(platform: str) -> PlatformAdapter:
    """Return an instance of the adapter for the given platform name."""
    if platform not in ADAPTER_REGISTRY:
        raise ValueError(f"No discovery adapter registered for platform: {platform}")
    return ADAPTER_REGISTRY[platform]()


def list_available_platforms() -> List[str]:
    """Return the list of all registered discovery platform names."""
    return list(ADAPTER_REGISTRY.keys())
