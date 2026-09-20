"""Unit tests for platform discovery adapters using synthetic HTML fixtures."""

import asyncio
import unittest

from registry.discovery.adapters.bilibili import BilibiliAdapter
from registry.discovery.adapters.facebook import FacebookAdapter
from registry.discovery.adapters.ganknow import GankNowAdapter
from registry.discovery.adapters.instagram import InstagramAdapter
from registry.discovery.adapters.kick import KickAdapter
from registry.discovery.adapters.niconico import NiconicoAdapter
from registry.discovery.adapters.tiktok import TikTokAdapter
from registry.discovery.adapters.twitch import TwitchAdapter
from registry.discovery.adapters.x import XAdapter
from registry.discovery.adapters.youtube import YouTubeAdapter
from registry.discovery.models import DiscoveryLimits


class MockPage:
    def __init__(self, html: str, should_timeout: bool = False):
        self._html = html
        self._should_timeout = should_timeout
        self.visited_url = None

    async def goto(self, url: str, **kwargs):
        self.visited_url = url
        if self._should_timeout:
            raise Exception("Timeout 30000ms exceeded")

    async def content(self):
        return self._html


class DiscoveryAdaptersTests(unittest.TestCase):
    def setUp(self):
        self.limits = DiscoveryLimits(max_results=10, max_pages=1, timeout=5.0)

    def test_youtube_adapter_extraction_and_captcha(self):
        adapter = YouTubeAdapter()

        html_success = """
        <html>
            <body>
                <a href="/@ThaiVTuberCat"><span>Thai VTuber Cat</span></a>
                <a href="/channel/UC1234567890123456789012"><span>Thai Channel Official</span></a>
            </body>
        </html>
        """
        page = MockPage(html_success)
        batch = asyncio.run(adapter.discover(page, "VTuberTH", self.limits))
        self.assertEqual(batch.status, "completed")
        self.assertEqual(len(batch.leads), 2)
        self.assertEqual(batch.leads[0].handle, "ThaiVTuberCat")
        self.assertEqual(batch.leads[1].platform_id, "UC1234567890123456789012")
        self.assertEqual(batch.leads[1].id_namespace, "channel_id")

        # Captcha detection
        html_captcha = "<html><body>recaptcha security check to continue</body></html>"
        page_captcha = MockPage(html_captcha)
        batch_captcha = asyncio.run(adapter.discover(page_captcha, "VTuberTH", self.limits))
        self.assertEqual(batch_captcha.status, "captcha")

    def test_twitch_adapter_extraction_and_reserved(self):
        adapter = TwitchAdapter()
        html = """
        <html>
            <body>
                <a href="/directory">Directory</a>
                <a href="/thaivtuber_stream">Thai VTuber Streamer</a>
            </body>
        </html>
        """
        page = MockPage(html)
        batch = asyncio.run(adapter.discover(page, "ThaiVTuber", self.limits))
        self.assertEqual(batch.status, "completed")
        self.assertEqual(len(batch.leads), 1)
        self.assertEqual(batch.leads[0].handle, "thaivtuber_stream")
        self.assertEqual(batch.leads[0].url, "https://www.twitch.tv/thaivtuber_stream")

    def test_tiktok_adapter_extraction_and_walls(self):
        adapter = TikTokAdapter()
        html_success = """
        <html>
            <body>
                <a href="/@vtuber_thailand"><span>VTuber Thailand</span></a>
            </body>
        </html>
        """
        page = MockPage(html_success)
        batch = asyncio.run(adapter.discover(page, "VTuber Thailand", self.limits))
        self.assertEqual(batch.status, "completed")
        self.assertEqual(len(batch.leads), 1)
        self.assertEqual(batch.leads[0].handle, "vtuber_thailand")

        # Captcha verify bar
        page_captcha = MockPage("<html><div class='verify-bar'>Verify to continue</div></html>")
        batch_captcha = asyncio.run(adapter.discover(page_captcha, "VTuber", self.limits))
        self.assertEqual(batch_captcha.status, "captcha")

        # Login wall
        page_login = MockPage("<html><div class='login-modal'>Please log in to continue</div></html>")
        batch_login = asyncio.run(adapter.discover(page_login, "VTuber", self.limits))
        self.assertEqual(batch_login.status, "login_required")

    def test_facebook_adapter_extraction_and_login_wall(self):
        adapter = FacebookAdapter()
        html_success = """
        <html>
            <body>
                <a href="/ThaiVirtualIdol">Thai Virtual Idol Page</a>
            </body>
        </html>
        """
        page = MockPage(html_success)
        batch = asyncio.run(adapter.discover(page, "Thai Virtual Idol", self.limits))
        self.assertEqual(batch.status, "completed")
        self.assertEqual(len(batch.leads), 1)
        self.assertEqual(batch.leads[0].handle, "ThaiVirtualIdol")

        # Login required
        page_login = MockPage("<html><div id='login_popup_cta_element'>Log In to Facebook</div></html>")
        batch_login = asyncio.run(adapter.discover(page_login, "Thai", self.limits))
        self.assertEqual(batch_login.status, "login_required")

    def test_instagram_adapter_extraction_and_login_wall(self):
        adapter = InstagramAdapter()
        html_success = """
        <html>
            <body>
                <a href="/vtuber_insta_th">VTuber Insta TH</a>
            </body>
        </html>
        """
        page = MockPage(html_success)
        batch = asyncio.run(adapter.discover(page, "vtuber", self.limits))
        self.assertEqual(batch.status, "completed")
        self.assertEqual(len(batch.leads), 1)
        self.assertEqual(batch.leads[0].handle, "vtuber_insta_th")

        # Login form
        page_login = MockPage("<html><form id='loginForm'>Log in to see photos</form></html>")
        batch_login = asyncio.run(adapter.discover(page_login, "vtuber", self.limits))
        self.assertEqual(batch_login.status, "login_required")

    def test_x_adapter_extraction_and_rate_limit(self):
        adapter = XAdapter()
        html_success = """
        <html>
            <body>
                <a href="/VirtualCreatorTH"><span>Virtual Creator TH</span></a>
            </body>
        </html>
        """
        page = MockPage(html_success)
        batch = asyncio.run(adapter.discover(page, "VirtualCreator", self.limits))
        self.assertEqual(batch.status, "completed")
        self.assertEqual(len(batch.leads), 1)
        self.assertEqual(batch.leads[0].handle, "VirtualCreatorTH")

        # Rate limit
        page_rate = MockPage("<html><div>Rate limit exceeded. Too many requests.</div></html>")
        batch_rate = asyncio.run(adapter.discover(page_rate, "VirtualCreator", self.limits))
        self.assertEqual(batch_rate.status, "rate_limited")

    def test_kick_adapter_extraction(self):
        adapter = KickAdapter()
        html = """
        <html>
            <body>
                <a href="/categories">Browse</a>
                <a href="/thai_streamer_kick">Thai Streamer on Kick</a>
            </body>
        </html>
        """
        page = MockPage(html)
        batch = asyncio.run(adapter.discover(page, "Thai", self.limits))
        self.assertEqual(batch.status, "completed")
        self.assertEqual(len(batch.leads), 1)
        self.assertEqual(batch.leads[0].handle, "thai_streamer_kick")

    def test_ganknow_adapter_extraction_and_crosslinks(self):
        adapter = GankNowAdapter()
        html = """
        <html>
            <body>
                <a href="/vtuber_gank">Gank Creator</a>
                <a href="https://twitter.com/vtuber_twitter">Twitter Link</a>
            </body>
        </html>
        """
        page = MockPage(html)
        batch = asyncio.run(adapter.discover(page, "VTuber", self.limits))
        self.assertEqual(batch.status, "completed")
        platforms = {l.platform for l in batch.leads}
        self.assertIn("ganknow", platforms)
        self.assertIn("x", platforms)

    def test_bilibili_adapter_extraction_and_uid(self):
        adapter = BilibiliAdapter()
        html_success = """
        <html>
            <body>
                <a href="//space.bilibili.com/987654321"><span>Thai UP Host</span></a>
            </body>
        </html>
        """
        page = MockPage(html_success)
        batch = asyncio.run(adapter.discover(page, "Thai", self.limits))
        self.assertEqual(batch.status, "completed")
        self.assertEqual(len(batch.leads), 1)
        self.assertEqual(batch.leads[0].platform_id, "987654321")
        self.assertEqual(batch.leads[0].id_namespace, "uid")

        # Captcha
        page_captcha = MockPage("<html><div>geetest challenge required</div></html>")
        batch_captcha = asyncio.run(adapter.discover(page_captcha, "Thai", self.limits))
        self.assertEqual(batch_captcha.status, "captcha")

    def test_niconico_adapter_extraction(self):
        adapter = NiconicoAdapter()
        html = """
        <html>
            <body>
                <a href="/user/88776655">Niconico User 88776655</a>
            </body>
        </html>
        """
        page = MockPage(html)
        batch = asyncio.run(adapter.discover(page, "Thai", self.limits))
        self.assertEqual(batch.status, "completed")
        self.assertEqual(len(batch.leads), 1)
        self.assertEqual(batch.leads[0].platform_id, "88776655")
        self.assertEqual(batch.leads[0].id_namespace, "user_id")

    def test_adapter_timeout_handling(self):
        adapter = YouTubeAdapter()
        page = MockPage("", should_timeout=True)
        batch = asyncio.run(adapter.discover(page, "query", self.limits))
        self.assertEqual(batch.status, "timeout")
        self.assertEqual(len(batch.leads), 0)


if __name__ == "__main__":
    unittest.main()
