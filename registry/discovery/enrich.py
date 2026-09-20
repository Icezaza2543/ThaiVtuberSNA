"""Stable public ID enrichment for discovered leads (Twitch user_id, TikTok web_user_id).

Reuses existing public resolvers without hardcoded credentials or private tokens.
Employs per-run runtime caching and bounded concurrency to protect the event loop.
"""

import asyncio
import re
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.request import Request, urlopen

from ..tiktok import parse_embed
from ..twitch_public import get_public_twitch_client_id, resolve_public_twitch_user_id
from .models import DiscoveryLead


def resolve_tiktok_web_user_id(handle: str, timeout: float = 5.0) -> Optional[str]:
    """Resolve numeric web_user_id for a TikTok handle via existing public embed parser."""
    clean_handle = handle.lstrip("@")
    if not clean_handle or not re.fullmatch(r"[A-Za-z0-9_.]+", clean_handle):
        return None
    try:
        source = f"https://www.tiktok.com/embed/@{clean_handle}?lang=en&embedFrom=webapp_preview"
        req = Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as response:
            body = response.read(2_000_000)
        profile = parse_embed(body.decode("utf-8", errors="ignore"), clean_handle)
        return profile.get("platform_id")
    except Exception:
        return None


class StableIdResolver:
    """Runtime cache and bounded concurrency resolver for creator platform stable IDs."""

    def __init__(
        self,
        custom_resolver: Optional[Callable[[str, str], Optional[Tuple[str, str]]]] = None,
        max_concurrency: int = 4,
    ):
        self.custom_resolver = custom_resolver
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.cache: Dict[Tuple[str, str], Optional[Tuple[str, str]]] = {}
        self.in_flight: Dict[Tuple[str, str], asyncio.Future] = {}
        self._lock: Optional[asyncio.Lock] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.twitch_client_id: Optional[str] = None
        self.stats: Dict[str, Dict[str, int]] = {
            "twitch": {"attempted": 0, "resolved": 0, "cache_hits": 0, "failed": 0},
            "tiktok": {"attempted": 0, "resolved": 0, "cache_hits": 0, "failed": 0},
        }

    @property
    def lock(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._lock is None or self._loop != loop:
            self._lock = asyncio.Lock()
            self._loop = loop
        return self._lock

    def _get_twitch_client_id(self, seed_handle: str) -> Optional[str]:
        if not self.twitch_client_id:
            try:
                self.twitch_client_id = get_public_twitch_client_id(seed_handle)
            except Exception:
                pass
        return self.twitch_client_id

    def _sync_resolve(self, platform: str, handle: str) -> Optional[Tuple[str, str]]:
        if self.custom_resolver:
            res = self.custom_resolver(platform, handle)
            if res:
                return res
        if platform == "twitch":
            cid = self._get_twitch_client_id(handle)
            uid = resolve_public_twitch_user_id(handle, client_id=cid)
            if uid:
                return (uid, "user_id")
        elif platform == "tiktok":
            uid = resolve_tiktok_web_user_id(handle)
            if uid:
                return (uid, "web_user_id")
        return None

    async def resolve_async(self, platform: str, handle: str) -> Optional[Tuple[str, str]]:
        norm_handle = handle.lower().lstrip("@")
        cache_key = (platform, norm_handle)

        if platform not in ("twitch", "tiktok") and not self.custom_resolver:
            return None

        if platform not in self.stats:
            self.stats[platform] = {"attempted": 0, "resolved": 0, "cache_hits": 0, "failed": 0}

        async with self.lock:
            if cache_key in self.cache:
                self.stats[platform]["cache_hits"] += 1
                return self.cache[cache_key]

            if cache_key in self.in_flight:
                self.stats[platform]["cache_hits"] += 1
                fut = self.in_flight[cache_key]
                is_initiator = False
            else:
                fut = asyncio.get_running_loop().create_future()
                self.in_flight[cache_key] = fut
                is_initiator = True

        if not is_initiator:
            return await fut

        self.stats[platform]["attempted"] += 1

        res: Optional[Tuple[str, str]] = None
        try:
            async with self.semaphore:
                res = await asyncio.to_thread(self._sync_resolve, platform, handle)
        except Exception:
            res = None
        except BaseException as be:
            async with self.lock:
                self.in_flight.pop(cache_key, None)
                if not fut.done():
                    fut.set_result(None)
            raise be
        finally:
            async with self.lock:
                self.cache[cache_key] = res
                if res:
                    self.stats[platform]["resolved"] += 1
                else:
                    self.stats[platform]["failed"] += 1
                self.in_flight.pop(cache_key, None)
                if not fut.done():
                    fut.set_result(res)

        return res

    async def enrich_lead_async(self, lead: DiscoveryLead) -> DiscoveryLead:
        """Enrich a lead with stable ID asynchronously, leveraging cache and semaphore."""
        if lead.platform_id and lead.id_namespace:
            return lead
        if not lead.handle:
            return lead
        res = await self.resolve_async(lead.platform, lead.handle)
        if res:
            lead.platform_id, lead.id_namespace = res
        return lead


def enrich_lead(
    lead: DiscoveryLead,
    custom_resolver: Optional[Callable[[str, str], Optional[Tuple[str, str]]]] = None,
) -> DiscoveryLead:
    """
    Synchronous fallback for enriching a DiscoveryLead with stable ID and namespace.
    If resolution fails or is offline, retains original handle/URL lead.
    """
    if lead.platform_id and lead.id_namespace:
        return lead

    if custom_resolver:
        res = custom_resolver(lead.platform, lead.handle or "")
        if res:
            lead.platform_id, lead.id_namespace = res
            return lead

    if lead.platform == "twitch" and lead.handle:
        uid = resolve_public_twitch_user_id(lead.handle)
        if uid:
            lead.platform_id = uid
            lead.id_namespace = "user_id"
    elif lead.platform == "tiktok" and lead.handle:
        uid = resolve_tiktok_web_user_id(lead.handle)
        if uid:
            lead.platform_id = uid
            lead.id_namespace = "web_user_id"

    return lead
