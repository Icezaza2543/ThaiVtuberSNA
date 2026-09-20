"""Tests for discovery browser fallback without Playwright browser downloads."""
import asyncio
import os
import unittest
from unittest.mock import patch

from registry.discovery.browser import BrowserSession, browser_channel_candidates


class _FakeContext:
    def __init__(self):
        self.timeout = None
        self.closed = False

    def set_default_timeout(self, timeout):
        self.timeout = timeout

    async def close(self):
        self.closed = True


class _FakeBrowser:
    def __init__(self, context):
        self.context = context
        self.closed = False

    async def new_context(self, **kwargs):
        return self.context

    async def close(self):
        self.closed = True


class _FakeChromium:
    def __init__(self):
        self.calls = []
        self.context = _FakeContext()
        self.browser = _FakeBrowser(self.context)

    async def launch(self, **kwargs):
        self.calls.append(dict(kwargs))
        if kwargs.get("channel") == "chrome":
            raise RuntimeError("Chrome not installed")
        if kwargs.get("channel") == "msedge":
            return self.browser
        raise AssertionError("Bundled Chromium should not be reached after Edge succeeds")


class _FakePlaywright:
    def __init__(self):
        self.chromium = _FakeChromium()
        self.stopped = False

    async def stop(self):
        self.stopped = True


class _AsyncFactory:
    def __init__(self, playwright):
        self.playwright = playwright

    async def start(self):
        return self.playwright


class BrowserFallbackTests(unittest.TestCase):
    def test_default_channel_order_prefers_system_browsers(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                browser_channel_candidates(),
                ["chrome", "msedge", None],
            )

    def test_environment_can_force_edge(self):
        with patch.dict(
            os.environ,
            {"REGISTRY_BROWSER_CHANNEL": "msedge"},
            clear=True,
        ):
            self.assertEqual(browser_channel_candidates(), ["msedge"])

    def test_session_falls_back_from_chrome_to_edge(self):
        fake = _FakePlaywright()
        factory = _AsyncFactory(fake)

        async def scenario():
            with patch(
                "registry.discovery.browser.check_playwright",
                return_value=lambda: factory,
            ), patch.dict(os.environ, {}, clear=True):
                session = BrowserSession(headless=True, timeout=12)
                context = await session.__aenter__()
                try:
                    self.assertEqual(session.browser_backend, "msedge")
                    self.assertEqual(context.timeout, 12000)
                    self.assertEqual(
                        fake.chromium.calls,
                        [
                            {"headless": True, "channel": "chrome"},
                            {"headless": True, "channel": "msedge"},
                        ],
                    )
                finally:
                    await session.__aexit__(None, None, None)

        asyncio.run(scenario())
        self.assertTrue(fake.stopped)


if __name__ == "__main__":
    unittest.main()
