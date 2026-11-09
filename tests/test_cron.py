#!/usr/bin/env python3
"""Cron helper tests."""

from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cron  # noqa: E402


class CronTest(unittest.TestCase):
    def test_run_daily_summary_completes_under_30s(self):
        path = ROOT / "examples" / "hackathon-deadlines.md"
        out = cron.run_daily_summary(path, dt.date(2026, 11, 6))
        self.assertIn("deadline-guard:", out)

    def test_install_writes_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "hermes"
            os.environ["HERMES_HOME"] = str(home)
            try:
                path = ROOT / "examples" / "hackathon-deadlines.md"
                script = cron.install_cron_script(path)
                self.assertTrue(script.is_file())
                self.assertEqual(oct(script.stat().st_mode)[-3:], "755")
            finally:
                os.environ.pop("HERMES_HOME", None)


if __name__ == "__main__":
    unittest.main()
