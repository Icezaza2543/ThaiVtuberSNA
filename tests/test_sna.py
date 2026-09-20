"""Tests for thaivtubersna.sna"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

from thaivtubersna.store import _DDL
from thaivtubersna import sna


def _test_db():
    con = duckdb.connect(":memory:")
    con.execute(_DDL)
    return con


def _fresh_tmp_db():
    """Return a Path to a fresh (non-existent) temp duckdb file."""
    f = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
    tmp_path = Path(f.name)
    f.close()
    tmp_path.unlink(missing_ok=True)  # DuckDB must create it fresh
    return tmp_path


class TestSNASummary(unittest.TestCase):
    def test_summary_on_empty_db(self):
        tmp_path = _fresh_tmp_db()
        try:
            s = sna.summary(db_path=tmp_path)
            self.assertEqual(s["total_edges"], 0)
            self.assertEqual(s["max_shared_viewers"], 0)
            self.assertFalse(s["parquet_data_present"])
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_summary_with_seeded_edges(self):
        from thaivtubersna.store import open_db, upsert, utc_now
        tmp_path = _fresh_tmp_db()
        try:
            con = open_db(tmp_path)
            upsert(con, "network_edges", {
                "id": "edge_001",
                "creator_a": "UCaaa",
                "creator_b": "UCbbb",
                "shared_any": 150,
                "shared_live_chat": 100,
                "shared_comments": 50,
                "strong_shared_any": 30,
                "strong_shared_live_chat": 20,
                "strong_shared_comments": 10,
                "jaccard": 0.12,
                "simpson": 0.25,
                "agency_a": None,
                "agency_b": None,
                "calculated_at": utc_now(),
            })
            con.commit()
            con.close()

            s = sna.summary(db_path=tmp_path)
            self.assertEqual(s["total_edges"], 1)
            self.assertEqual(s["max_shared_viewers"], 150)
        finally:
            tmp_path.unlink(missing_ok=True)


class TestRecalculateIfNeeded(unittest.TestCase):
    def test_skips_when_no_parquet(self):
        tmp_path = _fresh_tmp_db()
        try:
            with patch.object(sna, "_has_parquet_data", return_value=False):
                result = sna.recalculate_if_needed(db_path=tmp_path)
            self.assertTrue(result["skipped"])
            self.assertEqual(result["reason"], "no_parquet_data")
        finally:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
