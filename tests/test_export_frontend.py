"""Security and boundary tests for frontend public catalog export."""

import json
import unittest

from registry.store import connect, put, rows
from test_registry import STAMP, reviewed_fixture
from registry.operations import apply_change
import scripts.maintenance.export_frontend as exporter


class ExportFrontendSecurityTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        self.addCleanup(self.db.close)
        apply_change(self.db, reviewed_fixture())

    def test_safe_url_filtering(self):
        # Valid public HTTPS
        self.assertEqual(exporter.safe_url("https://youtube.com/@test"), "https://youtube.com/@test")
        self.assertEqual(exporter.safe_url("https://twitter.com/test"), "https://twitter.com/test")

        # Invalid schemes
        self.assertIsNone(exporter.safe_url("http://youtube.com/@test"))
        self.assertIsNone(exporter.safe_url("javascript:alert(1)"))
        self.assertIsNone(exporter.safe_url("file:///C:/secret/path.txt"))

        # Private or local hosts
        self.assertIsNone(exporter.safe_url("https://localhost/api"))
        self.assertIsNone(exporter.safe_url("https://127.0.0.1/admin"))
        self.assertIsNone(exporter.safe_url("https://192.168.1.1/secret"))
        self.assertIsNone(exporter.safe_url("https://internal.test/dashboard"))

        # Query credentials, tokens, secrets
        self.assertIsNone(exporter.safe_url("https://youtube.com/channel/UC123?token=secret123"))
        self.assertIsNone(exporter.safe_url("https://twitch.tv/test?api_key=secret_key"))
        self.assertIsNone(exporter.safe_url("https://example.com/profile?jwt=eyJhbGci..."))
        self.assertIsNone(exporter.safe_url("https://example.com/profile?session=abcdef"))

    def test_catalog_never_exposes_internal_or_unreviewed_data(self):
        # Add a needs_evidence account link
        put(
            self.db,
            "accounts",
            dict(
                id="acct-unreviewed",
                platform="twitch",
                platform_id="9999999",
                id_namespace="user_id",
                handle="unreviewed_handle",
                name="Unreviewed Name",
                url="https://twitch.tv/unreviewed_handle",
                first_discovered_at=STAMP,
                evidence_id="ev-official",
            ),
        )
        put(
            self.db,
            "account_links",
            dict(
                id="link-unreviewed",
                account_id="acct-unreviewed",
                persona_id="persona-a",
                valid_from=None,
                valid_to=None,
                evidence_id="ev-official",
                review_status="needs_evidence",
                reviewer="internal_agent",
                reviewed_at=STAMP,
            ),
        )

        catalog = exporter.build_catalog(self.db, "test_checksum")
        catalog_json = json.dumps(catalog)

        # 1. Unreviewed link account should NOT be in persona-a's accounts
        creator_a = next(c for c in catalog["creators"] if c["id"] == "persona-a")
        acct_ids = [a["id"] for a in creator_a["accounts"]]
        self.assertNotIn("acct-unreviewed", acct_ids)

        # 2. Reviewer names and notes should NEVER appear in published JSON
        self.assertNotIn("internal_agent", catalog_json)
        self.assertNotIn("reviewed_fixture_reviewer", catalog_json)

        # 3. No local file paths
        self.assertNotIn("C:\\", catalog_json)
        self.assertNotIn("file://", catalog_json)

        # 4. Raw review_queue and legacy_claims tables must not be present
        self.assertNotIn("review_queue", catalog)
        self.assertNotIn("legacy_claims", catalog)
        self.assertNotIn("candidates", catalog)

    def test_rejected_link_never_exported_to_public_creator(self):
        # Add a rejected account link
        put(
            self.db,
            "accounts",
            dict(
                id="acct-rejected",
                platform="tiktok",
                platform_id="8888888",
                id_namespace="web_user_id",
                handle="rejected_handle",
                name="Rejected Name",
                url="https://www.tiktok.com/@rejected_handle",
                first_discovered_at=STAMP,
                evidence_id="ev-official",
            ),
        )
        put(
            self.db,
            "account_links",
            dict(
                id="link-rejected",
                account_id="acct-rejected",
                persona_id="persona-a",
                valid_from=None,
                valid_to=None,
                evidence_id="ev-official",
                review_status="rejected",
                reviewer="internal_agent",
                reviewed_at=STAMP,
            ),
        )

        catalog = exporter.build_catalog(self.db, "test_checksum")
        creator_a = next(c for c in catalog["creators"] if c["id"] == "persona-a")
        acct_ids = [a["id"] for a in creator_a["accounts"]]
        self.assertNotIn("acct-rejected", acct_ids)


if __name__ == "__main__":
    unittest.main()

