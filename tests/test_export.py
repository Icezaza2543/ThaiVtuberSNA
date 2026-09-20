"""Tests for thaivtubersna.export"""
import csv
import tempfile
import unittest
from pathlib import Path

import duckdb

from thaivtubersna.store import _DDL, open_db, upsert, utc_now
from thaivtubersna.export import export_vtubers, export_network, export_platform_verified


def _test_db_with_data():
    """Create a temporary DuckDB with a minimal verified creator."""
    import os
    f = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
    tmp_path = Path(f.name)
    f.close()
    tmp_path.unlink(missing_ok=True)  # DuckDB must create it fresh

    con = open_db(tmp_path)
    now = utc_now()

    # Evidence
    upsert(con, "evidence", {
        "id": "ev001", "url": "https://example.com/bio",
        "kind": "official_profile", "observed_at": now,
        "published_on": None, "sha256": None,
        "summary": "Creator bio confirming VTuber status"
    })

    # Persona
    upsert(con, "personas", {
        "id": "p001", "name": "TestVtuber", "format": "live2d",
        "roles": '["streamer"]', "thai_relation": "self_declared_thai",
        "review_status": "verified", "evidence_id": "ev001",
        "reviewer": "test", "reviewed_at": now, "canonical_name": "TestVtuber"
    })

    # YouTube account
    upsert(con, "accounts", {
        "id": "acct_yt001", "platform": "youtube",
        "platform_id": "UCaaaaaaaaaaaaaaaaaaaaaaaa",
        "id_namespace": "channel_id", "handle": "@testvtuber",
        "name": "TestVtuber", "url": "https://www.youtube.com/channel/UCaaaaaaaaaaaaaaaaaaaaaaaa",
        "first_discovered_at": now, "evidence_id": "ev001"
    })

    # TikTok account
    upsert(con, "accounts", {
        "id": "acct_tt001", "platform": "tiktok",
        "platform_id": "12345678", "id_namespace": "web_user_id",
        "handle": "@testvtuber_tt", "name": "TestVtuber TikTok",
        "url": "https://www.tiktok.com/@testvtuber_tt",
        "first_discovered_at": now, "evidence_id": "ev001"
    })

    # Account link (YouTube → persona)
    upsert(con, "account_links", {
        "id": "link_yt001", "account_id": "acct_yt001", "persona_id": "p001",
        "valid_from": None, "valid_to": None, "evidence_id": "ev001",
        "review_status": "verified", "reviewer": "test", "reviewed_at": now
    })

    # Account link (TikTok → persona)
    upsert(con, "account_links", {
        "id": "link_tt001", "account_id": "acct_tt001", "persona_id": "p001",
        "valid_from": None, "valid_to": None, "evidence_id": "ev001",
        "review_status": "verified", "reviewer": "test", "reviewed_at": now
    })

    # Network edge
    upsert(con, "network_edges", {
        "id": "edge001",
        "creator_a": "UCaaaaaaaaaaaaaaaaaaaaaaaa",
        "creator_b": "UCbbbbbbbbbbbbbbbbbbbbbbbb",
        "shared_any": 250, "shared_live_chat": 200, "shared_comments": 50,
        "strong_shared_any": 80, "strong_shared_live_chat": 60, "strong_shared_comments": 20,
        "jaccard": 0.08, "simpson": 0.15,
        "agency_a": None, "agency_b": None,
        "calculated_at": now
    })

    con.commit()
    con.close()
    return tmp_path


class TestExportVtubers(unittest.TestCase):
    def setUp(self):
        self.tmp_db = _test_db_with_data()
        self.out_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        self.tmp_db.unlink(missing_ok=True)
        import shutil
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def test_exports_verified_youtube_accounts(self):
        from thaivtubersna.store import connect
        with connect(self.tmp_db) as con:
            n = export_vtubers(con, self.out_dir / "VTUBERS.csv")
        self.assertEqual(n, 1)
        rows = list(csv.DictReader((self.out_dir / "VTUBERS.csv").open(encoding="utf-8-sig")))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["channel_id"], "UCaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertEqual(rows[0]["name"], "TestVtuber")

    def test_export_network_produces_correct_rows(self):
        from thaivtubersna.store import connect
        with connect(self.tmp_db) as con:
            n = export_network(con, self.out_dir / "NETWORK_RESULT.csv")
        self.assertEqual(n, 1)
        rows = list(csv.DictReader((self.out_dir / "NETWORK_RESULT.csv").open(encoding="utf-8-sig")))
        self.assertEqual(int(rows[0]["Shared Viewers"]), 250)

    def test_export_tiktok_verified(self):
        from thaivtubersna.store import connect
        with connect(self.tmp_db) as con:
            n = export_platform_verified(con, "tiktok", self.out_dir / "TIKTOK.csv")
        self.assertEqual(n, 1)
        rows = list(csv.DictReader((self.out_dir / "TIKTOK.csv").open(encoding="utf-8-sig")))
        self.assertEqual(rows[0]["platform_id"], "12345678")

    def test_export_all_creates_5_files(self):
        from thaivtubersna.export import export_all
        counts = export_all(output_dir=self.out_dir, db_path=self.tmp_db)
        self.assertEqual(len(counts), 5)
        for fname in counts:
            self.assertTrue((self.out_dir / fname).exists(), f"{fname} missing")


if __name__ == "__main__":
    unittest.main()
