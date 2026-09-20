"""Tests for incremental discovery checking and source fingerprinting."""

import unittest
from datetime import datetime, timezone, timedelta

from registry.store import connect, put
from registry.discovery.incremental import (
    compute_content_hash,
    get_last_run,
    is_source_unchanged,
    should_skip_discovery,
)


class IncrementalDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        self.addCleanup(self.db.close)

    def test_compute_content_hash(self):
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash(b"hello world")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_is_source_unchanged(self):
        source_url = "https://example.org/intake.jsonl"
        content_hash = compute_content_hash("content batch 1")

        # No evidence yet
        self.assertFalse(is_source_unchanged(self.db, source_url, content_hash))

        # Insert evidence with hash
        put(
            self.db,
            "evidence",
            dict(
                id="ev-inc-1",
                url=source_url,
                kind="secondary_source",
                observed_at="2026-09-15T00:00:00+00:00",
                published_on=None,
                sha256=content_hash,
                summary="Batch 1 evidence",
            ),
        )

        self.assertTrue(is_source_unchanged(self.db, source_url, content_hash))
        self.assertFalse(is_source_unchanged(self.db, source_url, "different_hash"))

    def test_should_skip_discovery(self):
        platform = "twitch"
        query = "VTuberTH"
        method = "playwright_search"

        # 1. No previous run -> do not skip
        skip, reason, run = should_skip_discovery(
            self.db, platform=platform, query=query, method=method, as_of="2026-09-17T00:00:00+00:00"
        )
        self.assertFalse(skip)
        self.assertEqual(reason, "no_previous_run")

        # 2. Add completed run 2 days ago -> should skip (within 7-day default)
        put(
            self.db,
            "discovery_runs",
            dict(
                id="run-1",
                platform=platform,
                method=method,
                query=query,
                observed_at="2026-09-15T00:00:00+00:00",
                stop_reason="completed",
                pages=2,
                records_seen=10,
            ),
        )

        skip, reason, run = should_skip_discovery(
            self.db, platform=platform, query=query, method=method, as_of="2026-09-17T00:00:00+00:00"
        )
        self.assertTrue(skip)
        self.assertIn("recently_checked", reason)

        # 3. If as_of is 10 days later -> stale, do not skip
        skip, reason, run = should_skip_discovery(
            self.db, platform=platform, query=query, method=method, as_of="2026-09-26T00:00:00+00:00"
        )
        self.assertFalse(skip)
        self.assertIn("stale", reason)

        # 4. If previous run stopped with error (e.g. rate_limited) -> do not skip
        put(
            self.db,
            "discovery_runs",
            dict(
                id="run-2",
                platform=platform,
                method=method,
                query=query,
                observed_at="2026-09-16T12:00:00+00:00",
                stop_reason="rate_limited",
                pages=1,
                records_seen=2,
            ),
        )

        skip, reason, run = should_skip_discovery(
            self.db, platform=platform, query=query, method=method, as_of="2026-09-17T00:00:00+00:00"
        )
        self.assertFalse(skip)
        self.assertIn("rate_limited", reason)


if __name__ == "__main__":
    unittest.main()
