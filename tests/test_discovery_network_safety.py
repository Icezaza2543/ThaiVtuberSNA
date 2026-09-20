"""Tests for SSRF network safety guards, concurrent single-flight resolver, and same-host crosslink filtering."""

import asyncio
import time
import unittest
from typing import Dict, List, Optional, Tuple

from registry.discovery.crosslinks import extract_crosslinks
from registry.discovery.enrich import StableIdResolver
from registry.discovery.models import DiscoveryLead
from registry.discovery.network_safety import (
    is_safe_ip,
    is_safe_public_http_url,
    safe_goto,
    validate_public_navigation_url,
)


class NetworkSafetyTests(unittest.TestCase):
    """Regression tests for SSRF prevention, IP validation, and safe public URL navigation."""

    def test_direct_localhost_rejected(self):
        """Rejects localhost, localdomain, and loopback hostnames."""
        unsafe_urls = [
            "https://localhost",
            "https://localhost:8443",
            "https://localhost/path",
            "https://localhost.localdomain",
            "https://service.localhost",
            "https://broadcasthost",
            "https://myhost.local",
            "https://cluster.internal",
            "https://router.lan",
        ]
        for u in unsafe_urls:
            with self.subTest(url=u):
                self.assertFalse(is_safe_public_http_url(u, resolve_dns=False))
                with self.assertRaises(ValueError):
                    validate_public_navigation_url(u, resolve_dns=False)

    def test_ipv4_private_rejected(self):
        """Rejects IPv4 loopback, private (RFC 1918), link-local, and unspecified addresses."""
        unsafe_ips = [
            "https://127.0.0.1",
            "https://127.0.0.2",
            "https://127.1.2.3:8080",
            "https://0.0.0.0",
            "https://10.0.0.1",
            "https://10.254.0.1",
            "https://172.16.0.1",
            "https://172.31.255.255",
            "https://192.168.1.1",
            "https://192.168.0.100",
            "https://169.254.169.254",  # Cloud metadata IP
            "https://100.64.0.1",       # CGNAT (RFC 6598)
        ]
        for u in unsafe_ips:
            with self.subTest(url=u):
                self.assertFalse(is_safe_public_http_url(u, resolve_dns=False))
                with self.assertRaises(ValueError):
                    validate_public_navigation_url(u, resolve_dns=False)

    def test_ipv6_local_rejected(self):
        """Rejects IPv6 loopback, unique local (ULA), link-local, and unspecified addresses."""
        unsafe_v6 = [
            "https://[::1]",
            "https://[::]",
            "https://[fc00::1]",
            "https://[fd12:3456:789a::1]",
            "https://[fe80::1]",
            "https://[fe80::a00:27ff:fe8e:e8f8]",
            "https://[::ffff:127.0.0.1]",       # IPv4-mapped loopback
            "https://[::ffff:192.168.1.1]",     # IPv4-mapped private
        ]
        for u in unsafe_v6:
            with self.subTest(url=u):
                self.assertFalse(is_safe_public_http_url(u, resolve_dns=False))
                with self.assertRaises(ValueError):
                    validate_public_navigation_url(u, resolve_dns=False)

    def test_public_host_mock_accepted(self):
        """Mock DNS resolving to public test network (RFC 5737 203.0.113.x) is accepted."""
        dns_mock = lambda host: ["203.0.113.42"]
        url = "https://creator.example/profile"
        self.assertTrue(
            is_safe_public_http_url(url, resolve_dns=True, dns_resolver=dns_mock, allow_test_networks=True)
        )
        self.assertEqual(
            validate_public_navigation_url(url, resolve_dns=True, dns_resolver=dns_mock, allow_test_networks=True),
            url,
        )

    def test_hostname_resolves_private_rejected(self):
        """Mock DNS resolving to private 127.0.0.1 is rejected."""
        dns_mock = lambda host: ["127.0.0.1"]
        url = "https://creator.example/profile"
        self.assertFalse(
            is_safe_public_http_url(url, resolve_dns=True, dns_resolver=dns_mock)
        )
        with self.assertRaises(ValueError):
            validate_public_navigation_url(url, resolve_dns=True, dns_resolver=dns_mock)

    def test_non_https_and_credentials_rejected(self):
        """Rejects non-HTTPS schemes, empty hostnames, and embedded credentials."""
        self.assertFalse(is_safe_public_http_url("http://creator.example", resolve_dns=False))
        self.assertFalse(is_safe_public_http_url("ftp://creator.example", resolve_dns=False))
        self.assertFalse(is_safe_public_http_url("https://user:pass@creator.example", resolve_dns=False))
        self.assertFalse(is_safe_public_http_url("https://:secret@creator.example", resolve_dns=False))
        self.assertFalse(is_safe_public_http_url("https://", resolve_dns=False))
        self.assertFalse(is_safe_public_http_url("", resolve_dns=False))

    def test_safe_goto_blocks_initial_unsafe_url(self):
        """safe_goto aborts immediately when initial URL targets private network."""
        class DummyPage:
            def __init__(self):
                self.goto_called = False

            async def goto(self, url, **kwargs):
                self.goto_called = True

        page = DummyPage()
        res = asyncio.run(safe_goto(page, "https://127.0.0.1"))
        self.assertFalse(res)
        self.assertFalse(page.goto_called)

    def test_safe_goto_intercepts_redirect_to_private(self):
        """safe_goto intercepts route requests redirecting to private network."""
        class MockRoute:
            def __init__(self, request):
                self.request = request
                self.aborted = False
                self.abort_reason = None
                self.continued = False

            async def abort(self, error_code="failed"):
                self.aborted = True
                self.abort_reason = error_code

            async def continue_(self):
                self.continued = True

        class MockRequest:
            def __init__(self, url: str, is_navigation: bool = True):
                self.url = url
                self._is_navigation = is_navigation

            def is_navigation_request(self) -> bool:
                return self._is_navigation

        class MockPlaywrightPage:
            def __init__(self, redirect_url: Optional[str] = None):
                self.route_handler = None
                self.current_url = "https://public.example"
                self.redirect_url = redirect_url
                self.last_url = self.current_url

            async def route(self, pattern, handler):
                self.route_handler = handler

            async def unroute(self, pattern, handler):
                self.route_handler = None

            async def goto(self, url: str, **kwargs):
                self.current_url = url
                self.last_url = url
                if self.redirect_url and self.route_handler:
                    # Simulate redirect event dispatched to router
                    req = MockRequest(self.redirect_url, is_navigation=True)
                    route = MockRoute(req)
                    await self.route_handler(route, req)
                    if route.aborted:
                        raise Exception("Navigation aborted: blockedbyclient")
                    self.current_url = self.redirect_url
                    self.last_url = self.redirect_url

            def url(self) -> str:
                return self.current_url

        page = MockPlaywrightPage(redirect_url="https://127.0.0.1/admin")
        dns_mock = lambda h: ["203.0.113.1"]

        # Navigation to public domain that attempts redirect to 127.0.0.1
        res = asyncio.run(
            safe_goto(page, "https://public.example", dns_resolver=dns_mock)
        )
        self.assertFalse(res)

    def test_safe_goto_accepts_safe_public_navigation(self):
        """safe_goto succeeds when destination and routes are public."""
        class MockPlaywrightPage:
            def __init__(self):
                self.current_url = "https://creator.example"

            async def route(self, pattern, handler):
                pass

            async def unroute(self, pattern, handler):
                pass

            async def goto(self, url: str, **kwargs):
                self.current_url = url

            def url(self) -> str:
                return self.current_url

        page = MockPlaywrightPage()
        dns_mock = lambda h: ["203.0.113.1"]
        res = asyncio.run(
            safe_goto(page, "https://creator.example", dns_resolver=dns_mock, allow_test_networks=True)
        )
        self.assertTrue(res)


class ConcurrentResolverTests(unittest.TestCase):
    """Regression tests for concurrent bounded enrichment and single-flight deduplication."""

    def test_concurrent_single_flight_deduplication(self):
        """Multiple concurrent tasks for the same handle invoke network resolver exactly once."""
        call_count = 0

        def slow_resolver(platform: str, handle: str) -> Optional[Tuple[str, str]]:
            nonlocal call_count
            call_count += 1
            time.sleep(0.04)  # Simulate network latency
            if handle == "alice_streamer":
                return ("12345678", "user_id")
            return None

        resolver = StableIdResolver(custom_resolver=slow_resolver, max_concurrency=4)

        async def run_concurrent():
            # 5 concurrent leads for the exact same handle
            leads = [
                DiscoveryLead(
                    platform="twitch",
                    name="Alice Streamer",
                    url="https://twitch.tv/alice_streamer",
                    handle="alice_streamer",
                    observed_at="2026-09-15T00:00:00+00:00",
                )
                for _ in range(5)
            ]
            enriched = await asyncio.gather(*(resolver.enrich_lead_async(ld) for ld in leads))
            return enriched

        results = asyncio.run(run_concurrent())

        # Network resolver must have been called exactly ONCE
        self.assertEqual(call_count, 1)
        self.assertEqual(resolver.stats["twitch"]["attempted"], 1)
        self.assertEqual(resolver.stats["twitch"]["resolved"], 1)
        self.assertEqual(resolver.stats["twitch"]["cache_hits"], 4)
        self.assertEqual(resolver.stats["twitch"]["failed"], 0)

        # All 5 leads must have received the resolved platform_id
        for r in results:
            self.assertEqual(r.platform_id, "12345678")
            self.assertEqual(r.id_namespace, "user_id")

    def test_bounded_concurrency_semaphore(self):
        """Confirms that unique concurrent requests run concurrently up to semaphore limit."""
        import threading
        thread_lock = threading.Lock()
        thread_current = 0
        thread_max = 0

        def sync_tracker(platform: str, handle: str) -> Optional[Tuple[str, str]]:
            nonlocal thread_current, thread_max
            with thread_lock:
                thread_current += 1
                if thread_current > thread_max:
                    thread_max = thread_current
            time.sleep(0.04)
            with thread_lock:
                thread_current -= 1
            return (f"uid_{handle}", "user_id")

        resolver = StableIdResolver(custom_resolver=sync_tracker, max_concurrency=4)

        async def run_batch():
            leads = [
                DiscoveryLead(
                    platform="twitch",
                    name=f"Streamer {i}",
                    url=f"https://twitch.tv/streamer_{i}",
                    handle=f"streamer_{i}",
                    observed_at="2026-09-15T00:00:00+00:00",
                )
                for i in range(8)
            ]
            return await asyncio.gather(*(resolver.enrich_lead_async(ld) for ld in leads))

        results = asyncio.run(run_batch())

        self.assertEqual(len(results), 8)
        self.assertLessEqual(thread_max, 4, "Concurrent active resolvers must not exceed semaphore limit (4)")
        self.assertGreater(thread_max, 1, "Resolver must run concurrently (> 1 active at peak)")


class SameHostCrosslinkFilteringTests(unittest.TestCase):
    """Regression tests for excluding same-host internal navigation links in crosslink discovery."""

    def test_same_host_crosslink_filtering_ganknow(self):
        """GankNow creator profile page does not extract GankNow internal navigation links."""
        parent_url = "https://ganknow.com/alice"
        html = """
        <html><body>
            <a href="https://ganknow.com/terms">Terms of Service</a>
            <a href="https://ganknow.com/shop">Creator Shop</a>
            <a href="https://ganknow.com/feed">Activity Feed</a>
            <a href="https://youtube.com/@alice_official">YouTube Channel</a>
            <a href="https://twitter.com/alice_vtuber">Twitter Profile</a>
        </body></html>
        """
        leads = extract_crosslinks(
            html,
            parent_url=parent_url,
            observed_at="2026-09-15T00:00:00+00:00",
            allow_websites=True,
            allow_same_host=False,
        )

        urls = [l.url for l in leads]
        platforms = [l.platform for l in leads]

        # External platforms are extracted
        self.assertIn("https://youtube.com/@alice_official", urls)
        self.assertIn("https://x.com/alice_vtuber", urls)

        # Same-host GankNow internal links are skipped
        for u in urls:
            self.assertFalse(u.startswith("https://ganknow.com"))
        self.assertNotIn("ganknow", platforms)

    def test_same_host_crosslink_filtering_personal_site(self):
        """Personal website does not extract same-host pages but extracts outbound social links."""
        parent_url = "https://creator.example"
        html = """
        <html><body>
            <a href="https://creator.example/about">About Me</a>
            <a href="https://creator.example/merch">Merchandise Store</a>
            <a href="https://twitch.tv/alice_live">Twitch Channel</a>
        </body></html>
        """
        leads = extract_crosslinks(
            html,
            parent_url=parent_url,
            observed_at="2026-09-15T00:00:00+00:00",
            allow_websites=True,
            allow_same_host=False,
        )

        urls = [l.url for l in leads]
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0].platform, "twitch")
        self.assertEqual(leads[0].url, "https://twitch.tv/alice_live")
        self.assertNotIn("https://creator.example/about", urls)
        self.assertNotIn("https://creator.example/merch", urls)

    def test_link_hub_retains_outbound_skips_same_host(self):
        """Link hub (Linktree, Carrd) extracts external social & website links, skipping internal hub pages."""
        parent_url = "https://linktr.ee/creator_alice"
        html = """
        <html><body>
            <a href="https://linktr.ee/privacy">Privacy Policy</a>
            <a href="https://linktr.ee/pricing">Pricing</a>
            <a href="https://youtube.com/@creator_alice">YouTube</a>
            <a href="https://alice-official.com">Official Personal Site</a>
        </body></html>
        """
        leads = extract_crosslinks(
            html,
            parent_url=parent_url,
            observed_at="2026-09-15T00:00:00+00:00",
            allow_websites=True,
            allow_same_host=False,
        )

        urls = [l.url for l in leads]
        self.assertIn("https://youtube.com/@creator_alice", urls)
        self.assertIn("https://alice-official.com", urls)
        self.assertNotIn("https://linktr.ee/privacy", urls)
        self.assertNotIn("https://linktr.ee/pricing", urls)


if __name__ == "__main__":
    unittest.main()
