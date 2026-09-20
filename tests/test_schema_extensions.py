"""Tests for SQL schema extensions: platforms, discovery methods, and stop reasons."""

import unittest
from urllib.parse import urlparse

from registry.store import PLATFORMS, account_url, connect, put, rows, validate


class SchemaExtensionTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        # Seed an evidence row for foreign key references
        put(
            self.db,
            "evidence",
            dict(
                id="ev_test_seed",
                url="https://example.com/test",
                kind="platform_observation",
                observed_at="2026-09-15T10:00:00+00:00",
                published_on=None,
                sha256=None,
                summary="Test seed evidence",
            ),
        )

    def tearDown(self):
        self.db.close()

    def test_all_17_platforms_in_constants(self):
        expected_platforms = {
            "youtube", "twitch", "tiktok", "facebook",
            "instagram", "x", "kick", "ganknow", "bilibili", "niconico",
            "carrd", "linktree", "litlink", "kofi", "patreon", "vgen",
            "website",
        }
        self.assertEqual(set(PLATFORMS), expected_platforms)

    def test_database_accepts_all_platforms_in_candidates(self):
        for idx, platform in enumerate(PLATFORMS):
            url = f"https://example.com/{platform}" if platform == "website" else None
            if platform == "youtube":
                url = "https://www.youtube.com/@test"
            elif platform == "twitch":
                url = "https://www.twitch.tv/test"
            elif platform == "tiktok":
                url = "https://www.tiktok.com/@test"
            elif platform == "facebook":
                url = "https://www.facebook.com/test"
            elif platform == "instagram":
                url = "https://www.instagram.com/test"
            elif platform == "x":
                url = "https://x.com/test"
            elif platform == "kick":
                url = "https://kick.com/test"
            elif platform == "ganknow":
                url = "https://ganknow.com/test"
            elif platform == "bilibili":
                url = "https://space.bilibili.com/12345"
            elif platform == "niconico":
                url = "https://www.nicovideo.jp/user/12345"
            elif platform == "carrd":
                url = "https://test.carrd.co"
            elif platform == "linktree":
                url = "https://linktr.ee/test"
            elif platform == "litlink":
                url = "https://lit.link/test"
            elif platform == "kofi":
                url = "https://ko-fi.com/test"
            elif platform == "patreon":
                url = "https://www.patreon.com/test"
            elif platform == "vgen":
                url = "https://vgen.co/test"

            put(
                self.db,
                "candidates",
                dict(
                    id=f"cand_{idx}_{platform}",
                    platform=platform,
                    platform_id=None,
                    id_namespace=None,
                    name=f"Candidate {platform}",
                    url=url,
                    review_status="needs_evidence",
                    account_id=None,
                    evidence_id="ev_test_seed",
                    reviewer=None,
                    reviewed_at=None,
                ),
            )
        validate(self.db)
        self.assertEqual(len(rows(self.db, "candidates")), 17)

    def test_discovery_methods_and_stop_reasons_in_discovery_runs(self):
        new_methods = ["playwright_search", "crosslink_crawl"]
        new_stop_reasons = [
            "completed", "partial", "login_required", "captcha",
            "rate_limited", "selector_changed", "timeout", "blocked",
        ]

        idx = 0
        for method in new_methods:
            for stop_reason in new_stop_reasons:
                put(
                    self.db,
                    "discovery_runs",
                    dict(
                        id=f"run_test_{idx}",
                        platform="youtube",
                        method=method,
                        query="VTuberTH",
                        observed_at="2026-09-15T10:00:00+00:00",
                        stop_reason=stop_reason,
                        pages=1,
                        records_seen=10,
                    ),
                )
                idx += 1
        validate(self.db)
        self.assertEqual(len(rows(self.db, "discovery_runs")), len(new_methods) * len(new_stop_reasons))

    def test_generic_website_url_validation(self):
        # Website allows any valid public HTTPS URL
        account_url("website", "https://personal-domain.me/about")
        account_url("website", "https://agency.co.th/roster")

        # Invalid schemes or non-HTTPS rejected
        with self.assertRaises(ValueError):
            account_url("website", "http://insecure.com")
        with self.assertRaises(ValueError):
            account_url("website", "not-a-url")

    def test_named_platforms_enforce_domain(self):
        account_url("x", "https://x.com/creator")
        account_url("bilibili", "https://space.bilibili.com/123456")
        account_url("vgen", "https://vgen.co/creator")

        with self.assertRaises(ValueError):
            account_url("x", "https://otherdomain.com/creator")
        with self.assertRaises(ValueError):
            account_url("youtube", "https://vimeo.com/channel")


if __name__ == "__main__":
    unittest.main()
