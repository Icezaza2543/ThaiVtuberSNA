"""Tests for thaivtubersna.collect"""
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb

from thaivtubersna.store import DB_PATH, _DDL, open_db, count, utc_now
from thaivtubersna import collect


def _test_db():
    """Fresh in-memory DuckDB with full schema."""
    con = duckdb.connect(":memory:")
    con.execute(_DDL)
    return con


class TestDiscoverFromTwitch(unittest.TestCase):
    def test_skips_when_no_credentials(self):
        con = _test_db()
        with patch.dict("os.environ", {}, clear=True):
            # Remove Twitch env vars
            import os
            os.environ.pop("TWITCH_CLIENT_ID", None)
            os.environ.pop("TWITCH_ACCESS_TOKEN", None)
            result = collect.discover_from_twitch(con)
        self.assertTrue(result.get("skipped"))
        self.assertEqual(result["reason"], "no_credentials")

    def test_adds_candidates_from_stream_page(self):
        con = _test_db()
        fake_page = {
            "data": [
                {"user_id": "111", "user_login": "testuser1", "user_name": "TestUser1"},
                {"user_id": "222", "user_login": "testuser2", "user_name": "TestUser2"},
            ],
            "pagination": {}
        }

        def fake_http(url, headers):
            return json.dumps(fake_page).encode()

        with patch.dict("os.environ", {"TWITCH_CLIENT_ID": "cid", "TWITCH_ACCESS_TOKEN": "tok"}):
            with patch.object(collect, "_http_get", fake_http):
                result = collect.discover_from_twitch(con, max_pages=1)

        self.assertEqual(result["candidates_added"], 2)
        n = con.execute("SELECT COUNT(*) FROM candidates WHERE platform='twitch'").fetchone()[0]
        self.assertEqual(n, 2)

    def test_idempotent_second_run(self):
        """Same streamers in second page should not duplicate candidates."""
        con = _test_db()
        fake_page = {
            "data": [{"user_id": "999", "user_login": "dup", "user_name": "Dup"}],
            "pagination": {}
        }

        def fake_http(url, headers):
            return json.dumps(fake_page).encode()

        with patch.dict("os.environ", {"TWITCH_CLIENT_ID": "cid", "TWITCH_ACCESS_TOKEN": "tok"}):
            with patch.object(collect, "_http_get", fake_http):
                r1 = collect.discover_from_twitch(con, max_pages=1)
                r2 = collect.discover_from_twitch(con, max_pages=1)

        self.assertEqual(r1["candidates_added"], 1)
        self.assertEqual(r2["candidates_added"], 0)  # already in DB
        n = con.execute("SELECT COUNT(*) FROM candidates WHERE platform='twitch'").fetchone()[0]
        self.assertEqual(n, 1)


class TestDiscoverFromVtuberthai(unittest.TestCase):
    def test_extracts_channel_ids(self):
        con = _test_db()
        # UC + exactly 22 chars = valid YouTube channel IDs
        fake_html = b"""
        <html><body>
        <a href="https://www.youtube.com/channel/UCaaaaaaaaaaaaaaaaaaaaaa">Creator A</a>
        <a href="https://www.youtube.com/channel/UCbbbbbbbbbbbbbbbbbbbbbb">Creator B</a>
        </body></html>
        """

        with patch.object(collect, "_http_get", return_value=fake_html):
            result = collect.discover_from_vtuberthai(con)

        self.assertEqual(result["candidates_added"], 2)
        rows = con.execute("SELECT platform_id FROM candidates WHERE platform='youtube'").fetchall()
        ids = {r[0] for r in rows}
        self.assertIn("UCaaaaaaaaaaaaaaaaaaaaaa", ids)
        self.assertIn("UCbbbbbbbbbbbbbbbbbbbbbb", ids)

    def test_handles_http_error_gracefully(self):
        con = _test_db()
        from urllib.error import URLError

        with patch.object(collect, "_http_get", side_effect=URLError("Connection refused")):
            result = collect.discover_from_vtuberthai(con)

        # Should not raise; run is recorded with http_error stop reason
        self.assertEqual(result["candidates_added"], 0)
        runs = con.execute(
            "SELECT stop_reason FROM discovery_runs WHERE stop_reason='http_error'"
        ).fetchall()
        self.assertEqual(len(runs), 1)


class TestYouTubeInteractions(unittest.TestCase):
    def test_collects_comments_and_live_chat_into_duckdb_idempotently(self):
        con = _test_db()

        def fake_api(resource, params, api_key):
            self.assertEqual(api_key, "test-key")
            if resource == "playlistItems":
                return {
                    "items": [
                        {"contentDetails": {"videoId": "video_a"}},
                        {"contentDetails": {"videoId": "video_b"}},
                    ]
                }
            if resource == "videos":
                return {
                    "items": [
                        {
                            "id": "video_a",
                            "liveStreamingDetails": {"activeLiveChatId": "chat_a"},
                        },
                        {"id": "video_b", "liveStreamingDetails": {}},
                    ]
                }
            if resource == "commentThreads":
                return {
                    "items": [
                        {
                            "snippet": {
                                "topLevelComment": {
                                    "snippet": {
                                        "authorChannelId": {"value": "viewer_comment"},
                                        "publishedAt": "2026-09-20T10:00:00Z",
                                    }
                                }
                            }
                        }
                    ]
                }
            if resource == "liveChat/messages":
                return {
                    "items": [
                        {
                            "authorDetails": {"channelId": "viewer_live"},
                            "snippet": {"publishedAt": "2026-09-20T10:01:00Z"},
                        }
                    ]
                }
            raise AssertionError(resource)

        with patch.object(collect, "_eligible_youtube_channels", return_value=["UC_test"]):
            with patch.object(collect, "_youtube_api", side_effect=fake_api):
                with patch.object(collect, "_viewer_hmac_key", return_value=b"test-secret"):
                    first = collect.collect_youtube_interactions(
                        con,
                        api_key="test-key",
                        channels_per_cycle=1,
                        max_videos=2,
                    )
                    second = collect.collect_youtube_interactions(
                        con,
                        api_key="test-key",
                        channels_per_cycle=1,
                        max_videos=2,
                    )

        self.assertEqual(first["interactions_added"], 3)
        self.assertEqual(second["interactions_added"], 0)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM interactions").fetchone()[0], 3)
        raw_ids = {"viewer_comment", "viewer_live"}
        stored = {row[0] for row in con.execute("SELECT viewer_hash FROM interactions").fetchall()}
        self.assertTrue(stored.isdisjoint(raw_ids))

    def test_skips_videos_with_zero_comments(self):
        con = _test_db()
        comment_calls = []

        def fake_api(resource, params, api_key):
            if resource == "playlistItems":
                return {"items": [{"contentDetails": {"videoId": "vid_zero"}}]}
            if resource == "videos":
                return {
                    "items": [
                        {
                            "id": "vid_zero",
                            "statistics": {"commentCount": "0"},
                            "liveStreamingDetails": {},
                        }
                    ]
                }
            if resource == "commentThreads":
                comment_calls.append(params.get("videoId"))
                return {"items": []}
            raise AssertionError(resource)

        with patch.object(collect, "_eligible_youtube_channels", return_value=["UC_test"]):
            with patch.object(collect, "_youtube_api", side_effect=fake_api):
                with patch.object(collect, "_viewer_hmac_key", return_value=b"test-secret"):
                    result = collect.collect_youtube_interactions(
                        con, api_key="test-key", channels_per_cycle=1, max_videos=1
                    )

        self.assertEqual(len(comment_calls), 0)
        self.assertEqual(result["comments_seen"], 0)


if __name__ == "__main__":
    unittest.main()
