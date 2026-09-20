"""Tests for discover-all CLI command."""

import io
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

from registry.__main__ import main


class DiscoveryCliTests(unittest.TestCase):
    def test_discover_all_argument_parsing(self):
        # Test that CLI parses discover-all arguments without syntax error
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(io.StringIO()):
                main(["discover-all", "--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_playwright_missing_error_behavior(self):
        # Run discover-all in an environment where playwright is not importable
        # Verify exit code 1 and helpful error message
        code = (
            "import sys; "
            "sys.modules['playwright'] = None; "
            "sys.modules['playwright.async_api'] = None; "
            "from registry.__main__ import main; "
            "main(['discover-all'])"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Playwright is not installed", proc.stderr + proc.stdout)
        self.assertIn("pip install -e \".[discovery]\"", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
