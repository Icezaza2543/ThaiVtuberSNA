"""Verify discovery uses platform-specific default query sets."""
import asyncio
from collections import defaultdict
import unittest
from unittest.mock import patch

from registry.discovery.models import DiscoveryBatch
from registry.discovery.orchestrator import run_discovery_async
from registry.discovery.queries import resolve_queries
from registry.store import connect


class _Context:
    page = object()


class _Adapter:
    def __init__(self, platform, calls):
        self.platform = platform
        self.calls = calls

    async def discover(self, page, query, limits):
        self.calls[self.platform].append(query)
        return DiscoveryBatch(
            platform=self.platform,
            query=query,
            method="playwright_search",
            status="completed",
            leads=[],
            pages_seen=1,
            records_seen=0,
        )


class PlatformQueryRoutingTests(unittest.TestCase):
    def test_default_queries_are_resolved_per_platform(self):
        db = connect()
        calls = defaultdict(list)
        try:
            with patch(
                "registry.discovery.orchestrator.get_adapter",
                side_effect=lambda platform: _Adapter(platform, calls),
            ):
                asyncio.run(
                    run_discovery_async(
                        db,
                        platforms=["youtube", "twitch"],
                        queries=None,
                        browser_context=_Context(),
                    )
                )
            self.assertEqual(
                calls["youtube"],
                resolve_queries(platform="youtube"),
            )
            self.assertEqual(
                calls["twitch"],
                resolve_queries(platform="twitch"),
            )
            self.assertNotEqual(calls["youtube"], calls["twitch"])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
