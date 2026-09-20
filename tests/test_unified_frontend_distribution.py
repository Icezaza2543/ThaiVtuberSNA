"""Tests verifying the unified frontend distribution between ThaiVtuberSNA and Creator Registry."""

from pathlib import Path
import unittest

from scripts.build_distribution import build_unified_distribution

ROOT = Path(__file__).resolve().parents[1]


class UnifiedFrontendDistributionTests(unittest.TestCase):
    def test_both_entrypoints_exist_in_web(self):
        index_html = ROOT / "web/index.html"
        registry_html = ROOT / "web/registry.html"
        self.assertTrue(index_html.is_file(), "web/index.html must exist for SNA")
        self.assertTrue(registry_html.is_file(), "web/registry.html must exist for Creator Registry")

    def test_cross_navigation_links_between_frontends(self):
        index_content = (ROOT / "web/index.html").read_text(encoding="utf-8")
        self.assertIn('href="registry.html"', index_content, "index.html must link to registry.html")

        header_tsx = (ROOT / "web/src/components/Header.tsx").read_text(encoding="utf-8")
        self.assertIn('href="./index.html"', header_tsx, "Header.tsx must link back to ./index.html")

    def test_vite_config_targets_registry_entrypoint(self):
        vite_config = (ROOT / "web/vite.config.ts").read_text(encoding="utf-8")
        self.assertIn("registry.html", vite_config, "vite.config.ts must configure registry.html entrypoint")

    def test_copy_sna_assets_script_covers_core_files(self):
        script_content = (ROOT / "web/copy-sna-assets.cjs").read_text(encoding="utf-8")
        expected_assets = [
            "index.html",
            "site.css",
            "site.js",
            "design-tokens.css",
            "network.css",
            "network-ui.js",
            "research.css",
            "research.js",
            "data.json",
        ]
        for asset in expected_assets:
            self.assertIn(asset, script_content, f"copy-sna-assets.cjs must include {asset}")

    def test_build_unified_distribution_dry_run(self):
        summary = build_unified_distribution(check_only=True)
        self.assertEqual(summary["status"], "PASS")
        self.assertTrue(summary["registry"]["valid"])
        self.assertGreater(summary["registry"]["verified_personas"], 0)
        self.assertTrue(summary["web_distribution"]["entrypoints"]["sna_network"])
        self.assertTrue(summary["web_distribution"]["entrypoints"]["creator_registry"])


if __name__ == "__main__":
    unittest.main()
