"""Tests for Hub VTuber Thai public directory collector."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "collect" / "collect_vtuberthai_directory.py"
SPEC = importlib.util.spec_from_file_location("collect_vtuberthai_directory", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(collector)


class VtuberThaiDirectoryCollectorTests(unittest.TestCase):
    def test_extract_profile_links_filters_and_deduplicates(self):
        html = """
        <a href="/vtuber/alice-abc">Alice</a>
        <a href="https://vtuberthai.com/vtuber/alice-abc/">Alice duplicate</a>
        <a href="/vtuber/bob-def?lang=en">Bob</a>
        <a href="/agency/example">Agency</a>
        <a href="https://example.com/vtuber/mallory">External</a>
        """
        self.assertEqual(
            collector.extract_profile_links(html),
            [
                "https://vtuberthai.com/vtuber/alice-abc",
                "https://vtuberthai.com/vtuber/bob-def",
            ],
        )

    def test_extract_profile_observations_keeps_creator_accounts_only(self):
        html = """
        <h1> Example VTuber </h1>
        <a href="https://www.youtube.com/channel/UC1234567890123456789012">YouTube</a>
        <a href="https://www.youtube.com/watch?v=abc">Latest video</a>
        <a href="https://x.com/example_vt">X</a>
        <a href="https://twitter.com/example_vt?ref_src=twsrc">X duplicate alias</a>
        <a href="https://www.tiktok.com/@example_vt">TikTok</a>
        <a href="https://discord.gg/example">Discord</a>
        """
        name, rows = collector.extract_profile_observations(
            html,
            profile_url="https://vtuberthai.com/vtuber/example",
            observed_at="2026-09-19T00:00:00+00:00",
        )
        self.assertEqual(name, "Example VTuber")
        self.assertEqual([row["platform"] for row in rows], ["youtube", "x", "tiktok"])
        youtube = rows[0]
        self.assertEqual(youtube["id_namespace"], "channel_id")
        self.assertEqual(youtube["platform_id"], "UC1234567890123456789012")
        self.assertEqual(youtube["source_kind"], "secondary_source")
        self.assertEqual(rows[1]["url"], "https://x.com/example_vt")

    def test_identity_keys_equate_youtube_channel_id(self):
        row = {
            "platform": "youtube",
            "url": "https://www.youtube.com/channel/UC1234567890123456789012/",
        }
        keys = collector.identity_keys(row)
        self.assertIn(
            "id:youtube:channel_id:UC1234567890123456789012",
            keys,
        )

    def test_next_batch_number_and_emit_batch_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            intake = root / "intake"
            intake.mkdir()
            (intake / "2026-09-19-discovery-web-batch-8.jsonl").write_text(
                "{}\n", encoding="utf-8"
            )
            (intake / "2026-09-19-discovery-web-batch-12.jsonl").write_text(
                "{}\n", encoding="utf-8"
            )
            self.assertEqual(collector.next_batch_number(root), 13)
            records = [
                {"platform": "youtube", "url": f"https://youtube.com/@test{i}"}
                for i in range(7)
            ]
            paths = collector.emit_batch_files(
                records,
                root=root,
                batch_size=6,
                batch_date="2026-09-19",
            )
            self.assertEqual(
                [path.name for path in paths],
                [
                    "2026-09-19-discovery-web-batch-13.jsonl",
                    "2026-09-19-discovery-web-batch-14.jsonl",
                ],
            )
            self.assertEqual(
                len(paths[0].read_text(encoding="utf-8").splitlines()),
                6,
            )
            self.assertEqual(
                len(paths[1].read_text(encoding="utf-8").splitlines()),
                1,
            )


if __name__ == "__main__":
    unittest.main()
