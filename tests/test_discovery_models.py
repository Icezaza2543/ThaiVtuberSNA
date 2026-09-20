"""Tests for discovery models, normalization, deduplication, and crosslink extraction."""

import unittest

from registry.discovery.crosslinks import extract_crosslinks, extract_urls_from_html
from registry.discovery.dedupe import deduplicate_leads
from registry.discovery.models import DiscoveryBatch, DiscoveryLead, DiscoveryLimits
from registry.discovery.normalize import (
    infer_platform,
    normalize_handle,
    normalize_url,
    strip_tracking_params,
)
from registry.discovery.queries import DEFAULT_DISCOVERY_QUERIES, resolve_queries


class DiscoveryModelsTests(unittest.TestCase):
    def test_normalize_handle(self):
        self.assertEqual(normalize_handle("@Creator"), "Creator")
        self.assertEqual(normalize_handle("  @Creator_TH  "), "Creator_TH")
        self.assertEqual(normalize_handle("NoAt"), "NoAt")
        self.assertIsNone(normalize_handle(None))
        self.assertIsNone(normalize_handle(""))
        self.assertIsNone(normalize_handle("   "))

    def test_infer_platform(self):
        self.assertEqual(infer_platform("https://www.youtube.com/@test"), "youtube")
        self.assertEqual(infer_platform("https://twitch.tv/test"), "twitch")
        self.assertEqual(infer_platform("https://tiktok.com/@test"), "tiktok")
        self.assertEqual(infer_platform("https://facebook.com/testpage"), "facebook")
        self.assertEqual(infer_platform("https://instagram.com/test"), "instagram")
        self.assertEqual(infer_platform("https://twitter.com/test"), "x")
        self.assertEqual(infer_platform("https://x.com/test"), "x")
        self.assertEqual(infer_platform("https://kick.com/test"), "kick")
        self.assertEqual(infer_platform("https://ganknow.com/test"), "ganknow")
        self.assertEqual(infer_platform("https://space.bilibili.com/123"), "bilibili")
        self.assertEqual(infer_platform("https://www.nicovideo.jp/user/123"), "niconico")
        self.assertEqual(infer_platform("https://myprofile.carrd.co"), "carrd")
        self.assertEqual(infer_platform("https://linktr.ee/test"), "linktree")
        self.assertEqual(infer_platform("https://lit.link/test"), "litlink")
        self.assertEqual(infer_platform("https://ko-fi.com/test"), "kofi")
        self.assertEqual(infer_platform("https://patreon.com/test"), "patreon")
        self.assertEqual(infer_platform("https://vgen.co/test"), "vgen")
        self.assertEqual(infer_platform("https://custom-vtuber-site.in.th/home"), "website")

    def test_normalize_url(self):
        # Tracking stripped
        raw = "https://www.youtube.com/@Creator?utm_source=twitter&utm_medium=social&si=abc12345"
        norm = normalize_url("youtube", raw)
        self.assertEqual(norm, "https://www.youtube.com/@Creator")

        # Host alias twitter.com -> x.com
        raw_x = "https://twitter.com/VirtualCreator?ref_src=twsrc%5Etfw"
        norm_x = normalize_url("x", raw_x)
        self.assertEqual(norm_x, "https://x.com/VirtualCreator")

        # Trailing slash removed
        raw_fb = "https://www.facebook.com/VirtualAgency/"
        norm_fb = normalize_url("facebook", raw_fb)
        self.assertEqual(norm_fb, "https://www.facebook.com/VirtualAgency")

        # Generic website allows arbitrary public HTTPS
        raw_site = "https://agency.example.org/vtubers"
        self.assertEqual(normalize_url("website", raw_site), raw_site)

    def test_resolve_queries(self):
        # Default terms
        defaults = resolve_queries()
        self.assertIn("VTuberTH", defaults)
        self.assertIn("วีทูบเบอร์ไทย", defaults)

        # Custom queries override
        custom = resolve_queries(["CustomVTuber", "  ThaiStreamer  ", ""])
        self.assertEqual(custom, ["CustomVTuber", "ThaiStreamer"])

    def test_deduplicate_leads(self):
        lead1 = DiscoveryLead(
            platform="youtube",
            name="Creator 1",
            url="https://www.youtube.com/@creator1",
            handle="creator1",
            platform_id="UC1111111111111111111111",
            id_namespace="channel_id",
        )
        # Duplicate with same channel_id but different display name / url format
        lead2 = DiscoveryLead(
            platform="youtube",
            name="Creator 1 Official",
            url="https://www.youtube.com/channel/UC1111111111111111111111",
            platform_id="UC1111111111111111111111",
            id_namespace="channel_id",
        )
        # Duplicate with same canonical URL
        lead3 = DiscoveryLead(
            platform="youtube",
            name="Creator 1",
            url="https://www.youtube.com/@creator1?utm_source=share",
        )
        # Different lead
        lead4 = DiscoveryLead(
            platform="youtube",
            name="Creator 2",
            url="https://www.youtube.com/@creator2",
            handle="creator2",
        )

        deduped = deduplicate_leads([lead1, lead2, lead3, lead4])
        self.assertEqual(len(deduped), 2)
        # Verify first lead was enriched with channel_id
        self.assertEqual(deduped[0].platform_id, "UC1111111111111111111111")
        self.assertEqual(deduped[1].url, "https://www.youtube.com/@creator2")

    def test_extract_crosslinks(self):
        sample_html = """
        <html>
            <body>
                <h1>About Creator</h1>
                <a href="https://twitter.com/CreatorTH">Twitter</a>
                <a href="https://www.twitch.tv/creator_live">Twitch Channel</a>
                <a href="https://www.tiktok.com/@creator_tiktok">TikTok</a>
                <a href="https://myprofile.carrd.co">Carrd Hub</a>
                <a href="https://irrelevant-shop.com/buy">Merch</a>
                <!-- Self link should be ignored -->
                <a href="https://linktr.ee/mycreatorlink">Self</a>
            </body>
        </html>
        """
        parent_url = "https://linktr.ee/mycreatorlink"
        observed_at = "2026-09-15T12:00:00+00:00"

        leads = extract_crosslinks(sample_html, parent_url=parent_url, observed_at=observed_at, max_links=10)

        found_platforms = {l.platform for l in leads}
        self.assertIn("x", found_platforms)
        self.assertIn("twitch", found_platforms)
        self.assertIn("tiktok", found_platforms)
        self.assertIn("carrd", found_platforms)
        # Non-creator website is not extracted as a platform lead
        self.assertNotIn("website", found_platforms)
        # Self link is ignored
        self.assertNotIn(parent_url, [l.url for l in leads])
        # Provenance source_url points to parent
        for l in leads:
            self.assertEqual(l.source_url, parent_url)
            self.assertEqual(l.observed_at, observed_at)


if __name__ == "__main__":
    unittest.main()
