"""Tests for the discovery orchestrator and persistence semantics."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from registry.discovery.models import DiscoveryBatch
from registry.discovery.orchestrator import run_discovery_async
from registry.discovery.queries import get_registry_expansion_seeds
from registry.store import connect, put, rows, validate


class MockPage:
    def __init__(self, html_map=None):
        self.html_map = html_map or {}
        self.last_url = None
        self.scroll_cycle = 0

    async def goto(self, url: str, **kwargs):
        self.last_url = url

    async def wait_for_selector(self, selector: str, **kwargs):
        pass

    async def wait_for_timeout(self, ms: int):
        pass

    async def evaluate(self, expr: str):
        if "scrollTo" in expr:
            self.scroll_cycle += 1

    async def content(self):
        for key, html in self.html_map.items():
            if isinstance(key, tuple):
                url_prefix, cycle = key
                if url_prefix in (self.last_url or "") and self.scroll_cycle == cycle:
                    return html
            elif isinstance(key, str):
                if key in (self.last_url or ""):
                    return html
        return "<html><body></body></html>"


class MockContext:
    def __init__(self, page):
        self.page = page

    async def new_page(self):
        return self.page


class DiscoveryOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()

    def tearDown(self):
        self.db.close()

    def test_orchestrator_multi_platform_run_and_persistence(self):
        html_map = {
            "youtube.com": """
            <html><body>
                <a href="/@NewVTuber">New VTuber</a>
                <a href="/channel/UC9999999999999999999999">Known VTuber Official</a>
            </body></html>
            """,
            "twitch.tv": """
            <html><body>
                <a href="/twitch_creator">Twitch Creator</a>
            </body></html>
            """,
        }
        page = MockPage(html_map)
        context = MockContext(page)

        # Seed an existing account and evidence in db
        put(
            self.db,
            "evidence",
            dict(
                id="ev_seed_yt",
                url="https://www.youtube.com/channel/UC9999999999999999999999",
                kind="official_profile",
                observed_at="2026-09-15T00:00:00+00:00",
                published_on=None,
                sha256=None,
                summary="Known account evidence",
            ),
        )
        put(
            self.db,
            "accounts",
            dict(
                id="acct_seed_yt",
                platform="youtube",
                platform_id="UC9999999999999999999999",
                id_namespace="channel_id",
                handle="KnownVTuber",
                name="Known VTuber Official",
                url="https://www.youtube.com/channel/UC9999999999999999999999",
                first_discovered_at="2026-09-15T00:00:00+00:00",
                evidence_id="ev_seed_yt",
            ),
        )

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["youtube", "twitch"],
                queries=["VTuberTH"],
                browser_context=context,
            )
        )

        # Verify summary structure
        self.assertIn("platforms", summary)
        self.assertEqual(summary["platforms"]["youtube"]["status"], "completed")
        self.assertEqual(summary["platforms"]["twitch"]["status"], "completed")
        self.assertEqual(summary["raw_hits"], 3)
        self.assertEqual(summary["deduplicated_leads"], 3)
        self.assertEqual(summary["new_candidates"], 2)
        self.assertEqual(summary["known_accounts"], 1)

        # Verify registry integrity and persistence
        validate(self.db)
        candidates = rows(self.db, "candidates")
        self.assertEqual(len(candidates), 2)
        runs = rows(self.db, "discovery_runs")
        self.assertTrue(len(runs) >= 2)
        hits = rows(self.db, "discovery_hits")
        self.assertTrue(len(hits) >= 3)

    def test_multi_query_provenance_same_candidate(self):
        """
        Regression: when running multiple queries on the same platform that discover
        the same candidate, entity dedupe must keep exactly 1 candidate row, but
        preserve 2 distinct discovery runs, 2 discovery hits, and 2 evidence entries.
        """
        html_map = {
            "youtube.com": """
            <html><body>
                <a href="/@AliceVT">Alice VT</a>
            </body></html>
            """,
        }
        page = MockPage(html_map)
        context = MockContext(page)

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["youtube"],
                queries=["VTuberTH", "ThaiVTuber"],
                browser_context=context,
            )
        )

        validate(self.db)
        self.assertEqual(summary["new_candidates"], 1)
        self.assertEqual(summary["raw_hits"], 2)

        # Exactly 1 candidate
        candidates = rows(self.db, "candidates")
        self.assertEqual(len(candidates), 1)
        cand = candidates[0]
        self.assertEqual(cand["url"], "https://www.youtube.com/@AliceVT")

        # Distinct discovery runs for each query
        runs = rows(self.db, "discovery_runs")
        self.assertEqual(len(runs), 2)
        run_queries = {r["query"] for r in runs}
        self.assertEqual(run_queries, {"VTuberTH", "ThaiVTuber"})

        # Exactly 2 discovery hits pointing to the single candidate from different runs
        hits = rows(self.db, "discovery_hits")
        self.assertEqual(len(hits), 2)
        hit_run_ids = {h["run_id"] for h in hits}
        self.assertEqual(hit_run_ids, {r["id"] for r in runs})
        for h in hits:
            self.assertEqual(h["candidate_id"], cand["id"])

        # Exactly 2 evidence records
        evidence = rows(self.db, "evidence")
        self.assertEqual(len(evidence), 2)

    def test_search_and_crosslink_same_candidate(self):
        """
        Regression: discovering candidate from platform search and from a GankNow
        profile crosslink preserves both evidence sources under the same candidate.
        """
        html_map = {
            "youtube.com": """
            <html><body>
                <a href="/@BobVT">Bob VTuber</a>
            </body></html>
            """,
            "ganknow.com/search": """
            <html><body>
                <a href="/bob_creator">Bob Creator</a>
            </body></html>
            """,
            "ganknow.com/bob_creator": """
            <html><body>
                <div class="bio">
                    Follow me on YouTube: <a href="https://www.youtube.com/@BobVT">YouTube Channel</a>
                </div>
            </body></html>
            """,
        }
        page = MockPage(html_map)
        context = MockContext(page)

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["youtube", "ganknow"],
                queries=["VTuberTH"],
                browser_context=context,
            )
        )

        validate(self.db)
        candidates = rows(self.db, "candidates")
        # Should have 1 YouTube candidate (@BobVT) and 1 GankNow candidate (bob_creator)
        yt_candidates = [c for c in candidates if c["platform"] == "youtube"]
        self.assertEqual(len(yt_candidates), 1)
        yt_cand = yt_candidates[0]
        self.assertEqual(yt_cand["url"], "https://www.youtube.com/@BobVT")

        # BobVT should have 2 discovery hits: YouTube search and GankNow crosslink crawl
        hits = [h for h in rows(self.db, "discovery_hits") if h["candidate_id"] == yt_cand["id"]]
        self.assertEqual(len(hits), 2)

        # Runs should include search and crosslink_crawl
        runs = rows(self.db, "discovery_runs")
        methods = {r["method"] for r in runs}
        self.assertIn("playwright_search", methods)
        self.assertIn("crosslink_crawl", methods)

    def test_selector_changed_vs_official_empty_state(self):
        """
        Regression: when search UI yields 0 hits and no official empty state message,
        return 'selector_changed', NOT 'completed: 0'.
        When official empty-state message exists, return 'completed' with 0 hits.
        """
        html_selector_changed = "<html><body><div>Unknown layout without results</div></body></html>"
        html_empty_state = "<html><body><div>Could not find any channels matching query</div></body></html>"

        page_sc = MockPage({"twitch.tv": html_selector_changed})
        summary_sc = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["twitch"],
                queries=["QueryNothing"],
                browser_context=MockContext(page_sc),
            )
        )
        self.assertEqual(summary_sc["platforms"]["twitch"]["status"], "selector_changed")
        self.assertEqual(summary_sc["platforms"]["twitch"]["hits"], 0)

        page_empty = MockPage({"twitch.tv": html_empty_state})
        summary_empty = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["twitch"],
                queries=["QueryNothing"],
                browser_context=MockContext(page_empty),
            )
        )
        self.assertEqual(summary_empty["platforms"]["twitch"]["status"], "completed")
        self.assertEqual(summary_empty["platforms"]["twitch"]["hits"], 0)

    def test_pagination_and_scrolling_bounded(self):
        """
        Regression: bounded scrolling fetches incremental results up to max_pages / max_results.
        """
        # Cycle 0 has 1 lead; cycle 1 adds a 2nd lead
        html_cycle_0 = "<html><body><a href='/@user_one'>User One</a></body></html>"
        html_cycle_1 = "<html><body><a href='/@user_one'>User One</a><a href='/@user_two'>User Two</a></body></html>"

        page = MockPage({
            ("youtube.com", 0): html_cycle_0,
            ("youtube.com", 1): html_cycle_1,
        })
        context = MockContext(page)

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["youtube"],
                queries=["ScrollTest"],
                max_pages=2,
                max_results=10,
                browser_context=context,
            )
        )
        self.assertEqual(summary["raw_hits"], 2)
        self.assertEqual(summary["new_candidates"], 2)
        runs = rows(self.db, "discovery_runs")
        yt_runs = [r for r in runs if r["platform"] == "youtube"]
        self.assertTrue(any(r["pages"] >= 2 for r in yt_runs))

    def test_stable_id_enrichment(self):
        """
        Regression: stable ID resolver enriches candidate with platform_id and id_namespace
        before persistence.
        """
        html_map = {
            "twitch.tv": "<html><body><a href='/charlie_stream'>Charlie</a></body></html>",
        }
        page = MockPage(html_map)
        context = MockContext(page)

        def mock_resolver(platform, handle):
            if platform == "twitch" and handle == "charlie_stream":
                return ("987654321", "user_id")
            return None

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["twitch"],
                queries=["VTuberTH"],
                browser_context=context,
                custom_resolver=mock_resolver,
            )
        )

        validate(self.db)
        candidates = rows(self.db, "candidates")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["platform_id"], "987654321")
        self.assertEqual(candidates[0]["id_namespace"], "user_id")

    def test_registry_expansion_seeds_no_auto_link(self):
        """
        Regression: expand_registry generates seed queries from existing accounts/personas,
        creates candidate records as 'needs_evidence', and NEVER automatically links personas.
        """
        put(
            self.db,
            "evidence",
            dict(
                id="ev_seed_exp",
                url="https://www.youtube.com/channel/UC1111111111111111111111",
                kind="official_profile",
                observed_at="2026-09-15T00:00:00+00:00",
                published_on=None,
                sha256=None,
                summary="Seed evidence",
            ),
        )
        put(
            self.db,
            "personas",
            dict(
                id="per_seed_diana",
                name="Diana VTuber",
                format="live2d",
                roles='["streamer"]',
                thai_relation="thai_language",
                review_status="needs_evidence",
                evidence_id="ev_seed_exp",
                reviewer=None,
                reviewed_at=None,
            ),
        )
        put(
            self.db,
            "accounts",
            dict(
                id="acct_seed_diana",
                platform="youtube",
                platform_id="UC1111111111111111111111",
                id_namespace="channel_id",
                handle="Diana_Official",
                name="Diana VTuber",
                url="https://www.youtube.com/channel/UC1111111111111111111111",
                first_discovered_at="2026-09-15T00:00:00+00:00",
                evidence_id="ev_seed_exp",
            ),
        )

        seeds = get_registry_expansion_seeds(self.db)
        self.assertIn("Diana_Official", seeds)
        self.assertIn("Diana VTuber", seeds)

        # Now run discovery with expand_registry=True on Twitch
        html_map = {
            "twitch.tv": "<html><body><a href='/diana_official'>Diana Stream</a></body></html>",
        }
        page = MockPage(html_map)
        context = MockContext(page)

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["twitch"],
                queries=[],  # empty custom queries, relies on expansion seeds
                expand_registry=True,
                browser_context=context,
            )
        )

        validate(self.db)
        candidates = rows(self.db, "candidates")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["review_status"], "needs_evidence")

        # Crucial assertion: NO auto-link created!
        links = rows(self.db, "account_links")
        self.assertEqual(len(links), 0)

    def test_failure_isolation_three_platforms(self):
        html_map = {
            "tiktok.com": "<html><div class='verify-bar'>Security verification required</div></html>",
            "kick.com": "<html><body><a href='/kick_creator'>Kick Creator</a></body></html>",
            "facebook.com": "<html><body><div>Unknown layout without results</div></body></html>",
        }
        page = MockPage(html_map)
        context = MockContext(page)

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["tiktok", "kick", "facebook"],
                queries=["ThaiVTuber"],
                browser_context=context,
            )
        )

        # TikTok reported captcha, Kick completed successfully, Facebook selector_changed
        self.assertEqual(summary["platforms"]["tiktok"]["status"], "captcha")
        self.assertEqual(summary["platforms"]["kick"]["status"], "completed")
        self.assertEqual(summary["platforms"]["facebook"]["status"], "selector_changed")
        self.assertEqual(summary["new_candidates"], 1)

        validate(self.db)
        runs = rows(self.db, "discovery_runs")
        self.assertTrue(any(r["platform"] == "tiktok" and r["stop_reason"] == "captcha" for r in runs))
        self.assertTrue(any(r["platform"] == "kick" and r["stop_reason"] == "completed" for r in runs))
        self.assertTrue(any(r["platform"] == "facebook" and r["stop_reason"] == "selector_changed" for r in runs))

    def test_crosslink_source_preservation_two_profiles_same_target(self):
        """
        Test A: Crosslink source preservation
        Alice Gank profile -> YouTube X
        Bob Gank profile -> same YouTube X
        assert:
        1 candidate
        2 hits
        2 runs
        2 evidence
        different source_url
        """
        html_map = {
            "ganknow.com/search": """
            <html><body>
                <a href="/alice_creator">Alice</a>
                <a href="/bob_creator">Bob</a>
            </body></html>
            """,
            "ganknow.com/alice_creator": """
            <html><body>
                <div class="links">
                    <a href="https://www.youtube.com/@SharedVTuber">Shared Channel</a>
                </div>
            </body></html>
            """,
            "ganknow.com/bob_creator": """
            <html><body>
                <div class="links">
                    <a href="https://www.youtube.com/@SharedVTuber">Shared Channel</a>
                </div>
            </body></html>
            """,
        }
        page = MockPage(html_map)
        context = MockContext(page)

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["ganknow"],
                queries=["VTuberTH"],
                browser_context=context,
            )
        )

        validate(self.db)
        candidates = rows(self.db, "candidates")
        yt_candidates = [c for c in candidates if c["platform"] == "youtube"]
        # Exactly 1 YouTube candidate
        self.assertEqual(len(yt_candidates), 1)
        yt_cand = yt_candidates[0]
        self.assertEqual(yt_cand["url"], "https://www.youtube.com/@SharedVTuber")

        # 2 distinct runs for crosslink_crawl on YouTube from different sources
        runs = rows(self.db, "discovery_runs")
        yt_crosslink_runs = [r for r in runs if r["platform"] == "youtube" and r["method"] == "crosslink_crawl"]
        self.assertEqual(len(yt_crosslink_runs), 2)
        self.assertNotEqual(yt_crosslink_runs[0]["id"], yt_crosslink_runs[1]["id"])

        # 2 distinct discovery hits pointing to the same candidate
        hits = [h for h in rows(self.db, "discovery_hits") if h["candidate_id"] == yt_cand["id"]]
        self.assertEqual(len(hits), 2)
        hit_run_ids = {h["run_id"] for h in hits}
        self.assertEqual(hit_run_ids, {r["id"] for r in yt_crosslink_runs})

        # 2 distinct evidence rows with different source_urls
        ev_ids = [h["evidence_id"] for h in hits]
        evidence_rows = [e for e in rows(self.db, "evidence") if e["id"] in ev_ids]
        self.assertEqual(len(evidence_rows), 2)
        evidence_sources = {e["url"] for e in evidence_rows}
        self.assertEqual(evidence_sources, {"https://ganknow.com/alice_creator", "https://ganknow.com/bob_creator"})

    def test_stable_id_resolver_cache_per_run(self):
        """
        Test B: Resolver cache
        Discover same Twitch handle from 5 queries.
        Resolver function is called exactly once; 5 hits preserved.
        """
        html_map = {
            "twitch.tv": "<html><body><a href='/popular_streamer'>Popular Streamer</a></body></html>",
        }
        page = MockPage(html_map)
        context = MockContext(page)

        call_count = 0

        def counting_resolver(platform, handle):
            nonlocal call_count
            if platform == "twitch" and handle == "popular_streamer":
                call_count += 1
                return ("11223344", "user_id")
            return None

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["twitch"],
                queries=["Q1", "Q2", "Q3", "Q4", "Q5"],
                browser_context=context,
                custom_resolver=counting_resolver,
            )
        )

        validate(self.db)
        # Network resolution called exactly once
        self.assertEqual(call_count, 1)
        self.assertEqual(summary["enrichment"]["twitch"]["attempted"], 1)
        self.assertEqual(summary["enrichment"]["twitch"]["cache_hits"], 4)

        # Exactly 1 candidate with stable ID
        candidates = rows(self.db, "candidates")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["platform_id"], "11223344")

        # 5 discovery runs and 5 hits pointing to the candidate
        hits = rows(self.db, "discovery_hits")
        self.assertEqual(len(hits), 5)

    def test_failed_enrichment_fallback_preserves_lead(self):
        """
        Test C: Failed enrichment fallback
        Resolver raises error / timeout; lead is preserved as needs_evidence.
        """
        html_map = {
            "twitch.tv": "<html><body><a href='/offline_streamer'>Offline Streamer</a></body></html>",
        }
        page = MockPage(html_map)
        context = MockContext(page)

        def failing_resolver(platform, handle):
            raise TimeoutError("Simulated network timeout")

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["twitch"],
                queries=["VTuberTH"],
                browser_context=context,
                custom_resolver=failing_resolver,
            )
        )

        validate(self.db)
        candidates = rows(self.db, "candidates")
        self.assertEqual(len(candidates), 1)
        self.assertIsNone(candidates[0]["platform_id"])
        self.assertIsNone(candidates[0]["id_namespace"])
        self.assertEqual(candidates[0]["review_status"], "needs_evidence")
        self.assertEqual(summary["enrichment"]["twitch"]["failed"], 1)

    def test_records_seen_preserves_adapter_reported_count(self):
        """
        Test D: records_seen reflects actual adapter-reported count, not just persisted leads.
        """
        from registry.discovery.adapters.base import PlatformAdapter
        from registry.discovery.models import DiscoveryBatch, DiscoveryLead

        class MockRecordsAdapter(PlatformAdapter):
            platform = "youtube"

            async def discover(self, page, query, limits):
                leads = [
                    DiscoveryLead(platform="youtube", name="Lead 1", url="https://www.youtube.com/@lead1"),
                    DiscoveryLead(platform="youtube", name="Lead 2", url="https://www.youtube.com/@lead2"),
                ]
                return self.create_batch(
                    query=query,
                    method="playwright_search",
                    source_url="https://www.youtube.com/results",
                    status="completed",
                    leads=leads,
                    pages_seen=3,
                    records_seen=100,  # 100 scanned, 2 leads
                )

        import registry.discovery.orchestrator as orch_mod
        orig_get_adapter = orch_mod.get_adapter
        orch_mod.get_adapter = lambda plat: MockRecordsAdapter()
        try:
            page = MockPage({})
            summary = asyncio.run(
                orch_mod.run_discovery_async(
                    self.db,
                    platforms=["youtube"],
                    queries=["TestRecords"],
                    browser_context=MockContext(page),
                )
            )
            validate(self.db)
            runs = rows(self.db, "discovery_runs")
            yt_runs = [r for r in runs if r["platform"] == "youtube"]
            self.assertEqual(len(yt_runs), 1)
            self.assertEqual(yt_runs[0]["records_seen"], 100)
            self.assertEqual(yt_runs[0]["pages"], 3)
        finally:
            orch_mod.get_adapter = orig_get_adapter

    def test_personal_website_bounded_hop(self):
        """
        Test E: Personal website hop
        Gank profile -> https://creator.example -> https://twitch.tv/example
        Twitch lead is created, source chain attributable, no auto-link.
        """
        html_map = {
            "ganknow.com/search": "<html><body><a href='/dave_creator'>Dave</a></body></html>",
            "ganknow.com/dave_creator": "<html><body><a href='https://dave-vtuber.example'>Dave Site</a></body></html>",
            "dave-vtuber.example": "<html><body><a href='https://www.twitch.tv/dave_live'>Twitch Stream</a></body></html>",
        }
        page = MockPage(html_map)
        context = MockContext(page)

        summary = asyncio.run(
            run_discovery_async(
                self.db,
                platforms=["ganknow"],
                queries=["VTuberTH"],
                browser_context=context,
            )
        )

        validate(self.db)
        candidates = rows(self.db, "candidates")
        # Should have GankNow candidate, website candidate, and Twitch candidate
        gank_cands = [c for c in candidates if c["platform"] == "ganknow"]
        web_cands = [c for c in candidates if c["platform"] == "website"]
        twitch_cands = [c for c in candidates if c["platform"] == "twitch"]

        self.assertEqual(len(gank_cands), 1)
        self.assertEqual(len(web_cands), 1)
        self.assertEqual(len(twitch_cands), 1)

        self.assertEqual(web_cands[0]["url"], "https://dave-vtuber.example")
        self.assertEqual(twitch_cands[0]["url"], "https://www.twitch.tv/dave_live")
        self.assertEqual(twitch_cands[0]["review_status"], "needs_evidence")

        # Twitch hit evidence points to the personal website
        hits = [h for h in rows(self.db, "discovery_hits") if h["candidate_id"] == twitch_cands[0]["id"]]
        self.assertEqual(len(hits), 1)
        ev = next(e for e in rows(self.db, "evidence") if e["id"] == hits[0]["evidence_id"])
        self.assertEqual(ev["url"], "https://dave-vtuber.example")

        # Crucial: NO account_links or auto-verified personas created
        self.assertEqual(len(rows(self.db, "account_links")), 0)

    def test_bounded_crawl_limits(self):
        """
        Test F: Bounded crawl limits
        A personal site or hub with 100 outbound links is bounded by max_links.
        """
        from registry.discovery.crosslinks import extract_crosslinks

        links_html = "".join(f"<a href='https://www.youtube.com/@creator_{i}'>Creator {i}</a>" for i in range(100))
        html = f"<html><body>{links_html}</body></html>"

        leads = extract_crosslinks(
            html, parent_url="https://hub.example", observed_at="2026-09-15T00:00:00+00:00", max_links=15
        )
        self.assertEqual(len(leads), 15)

    def test_incremental_orchestrator_fresh_run_skips_adapter(self):
        page = MockPage({})
        context = MockContext(page)

        # Completed run 2 days ago
        put(
            self.db,
            "discovery_runs",
            dict(
                id="run-fresh-1",
                platform="twitch",
                method="playwright_search",
                query="VTuberTH",
                observed_at="2026-09-15T00:00:00+00:00",
                stop_reason="completed",
                pages=2,
                records_seen=5,
            ),
        )

        with patch("registry.discovery.adapters.twitch.TwitchAdapter.discover", new_callable=AsyncMock) as mock_discover:
            summary = asyncio.run(
                run_discovery_async(
                    self.db,
                    platforms=["twitch"],
                    queries=["VTuberTH"],
                    browser_context=context,
                    incremental=True,
                    freshness_days=7,
                    as_of="2026-09-17T00:00:00+00:00",
                )
            )

            self.assertEqual(mock_discover.call_count, 0)
            self.assertEqual(summary["platforms"]["twitch"]["status"], "skipped_fresh")
            self.assertIn("recently_checked", summary["platforms"]["twitch"]["skip_reason"])
            self.assertEqual(len(summary["skipped_queries"]), 1)
            # Ensure no new discovery_runs or candidates were added
            runs = rows(self.db, "discovery_runs")
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["id"], "run-fresh-1")

    def test_incremental_orchestrator_stale_run_calls_adapter(self):
        page = MockPage({})
        context = MockContext(page)

        # Completed run 10 days ago (stale against freshness_days=7)
        put(
            self.db,
            "discovery_runs",
            dict(
                id="run-stale-1",
                platform="twitch",
                method="playwright_search",
                query="VTuberTH",
                observed_at="2026-09-07T00:00:00+00:00",
                stop_reason="completed",
                pages=2,
                records_seen=5,
            ),
        )

        with patch("registry.discovery.adapters.twitch.TwitchAdapter.discover", new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = DiscoveryBatch(
                platform="twitch", query="VTuberTH", method="playwright_search", status="completed", leads=[]
            )
            summary = asyncio.run(
                run_discovery_async(
                    self.db,
                    platforms=["twitch"],
                    queries=["VTuberTH"],
                    browser_context=context,
                    incremental=True,
                    freshness_days=7,
                    as_of="2026-09-17T00:00:00+00:00",
                )
            )

            self.assertEqual(mock_discover.call_count, 1)
            self.assertEqual(summary["platforms"]["twitch"]["status"], "completed")
            self.assertEqual(len(summary["skipped_queries"]), 0)

    def test_incremental_orchestrator_failed_previous_run_retried(self):
        page = MockPage({})
        context = MockContext(page)

        for failed_reason in ("timeout", "rate_limited", "partial", "blocked"):
            with self.subTest(failed_reason=failed_reason):
                put(
                    self.db,
                    "discovery_runs",
                    dict(
                        id=f"run-failed-{failed_reason}",
                        platform="twitch",
                        method="playwright_search",
                        query=f"Query_{failed_reason}",
                        observed_at="2026-09-16T00:00:00+00:00",
                        stop_reason=failed_reason,
                        pages=1,
                        records_seen=0,
                    ),
                )

                with patch("registry.discovery.adapters.twitch.TwitchAdapter.discover", new_callable=AsyncMock) as mock_discover:
                    mock_discover.return_value = DiscoveryBatch(
                        platform="twitch", query=f"Query_{failed_reason}", method="playwright_search", status="completed", leads=[]
                    )
                    summary = asyncio.run(
                        run_discovery_async(
                            self.db,
                            platforms=["twitch"],
                            queries=[f"Query_{failed_reason}"],
                            browser_context=context,
                            incremental=True,
                            freshness_days=7,
                            as_of="2026-09-17T00:00:00+00:00",
                        )
                    )

                    self.assertEqual(mock_discover.call_count, 1, f"Failed run with {failed_reason} should NOT be skipped")
                    self.assertEqual(summary["platforms"]["twitch"]["status"], "completed")

    def test_incremental_orchestrator_disabled_incremental_executes(self):
        page = MockPage({})
        context = MockContext(page)

        # Recent completed run, but incremental=False (default)
        put(
            self.db,
            "discovery_runs",
            dict(
                id="run-fresh-2",
                platform="twitch",
                method="playwright_search",
                query="VTuberTH",
                observed_at="2026-09-16T00:00:00+00:00",
                stop_reason="completed",
                pages=2,
                records_seen=5,
            ),
        )

        with patch("registry.discovery.adapters.twitch.TwitchAdapter.discover", new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = DiscoveryBatch(
                platform="twitch", query="VTuberTH", method="playwright_search", status="completed", leads=[]
            )
            summary = asyncio.run(
                run_discovery_async(
                    self.db,
                    platforms=["twitch"],
                    queries=["VTuberTH"],
                    browser_context=context,
                    incremental=False,
                )
            )

            self.assertEqual(mock_discover.call_count, 1)
            self.assertEqual(summary["platforms"]["twitch"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()

