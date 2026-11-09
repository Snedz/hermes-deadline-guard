#!/usr/bin/env python3
"""demo_cli.py exits 0 and prints blocked submit + founder step lines."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DemoCliTest(unittest.TestCase):
    def test_demo_cli_smoke(self) -> None:
        script = ROOT / "demo_cli.py"
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertIn("check_deadlines", out)
        self.assertIn("http(s) link", out)
        self.assertIn("Near Miss Row", out)

    def test_demo_cli_json_golden(self) -> None:
        script = ROOT / "demo_cli.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["demo_today"], "2026-11-06")
        check = payload["steps"]["check_deadlines"]
        self.assertEqual(check["error_count"], 0)
        self.assertEqual(check["warn_count"], 3)
        blocked = payload["steps"]["propose_status_update_blocked"]
        self.assertFalse(blocked["ok"])
        ok_step = payload["steps"]["propose_status_update_ok"]
        self.assertTrue(ok_step["ok"])


if __name__ == "__main__":
    unittest.main()
