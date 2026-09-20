import unittest

from registry.pipeline.evidence import _confidence_for_link


class ConfidenceTests(unittest.TestCase):
    def test_x_plus_hub_is_high(self):
        self.assertEqual(
            _confidence_for_link(
                platform="tiktok",
                x_url="https://x.com/foo",
                hub_url="https://linktr.ee/foo",
                source="grok_x_search",
                is_agency=False,
            ),
            "high",
        )

    def test_youtube_about_tiktok_is_high(self):
        self.assertEqual(
            _confidence_for_link(
                platform="tiktok",
                x_url=None,
                hub_url=None,
                source="youtube_about_or_intake",
                is_agency=False,
            ),
            "high",
        )

    def test_agency_is_low(self):
        self.assertEqual(
            _confidence_for_link(
                platform="tiktok",
                x_url="https://x.com/foo",
                hub_url="https://linktr.ee/foo",
                source="youtube_about_or_intake",
                is_agency=True,
            ),
            "low",
        )

    def test_facebook_from_about_is_high_on_equal_evidence(self):
        self.assertEqual(
            _confidence_for_link(
                platform="facebook",
                x_url=None,
                hub_url=None,
                source="youtube_about_or_intake",
                is_agency=False,
            ),
            "high",
        )


if __name__ == "__main__":
    unittest.main()
