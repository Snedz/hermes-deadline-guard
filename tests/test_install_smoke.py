#!/usr/bin/env python3
"""install_smoke.py exits 0 and stages a runnable plugin tree."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INNER_ENV_FLAG = "DEADLINE_GUARD_INSTALL_SMOKE_INNER"


@unittest.skipIf(
    os.environ.get(INNER_ENV_FLAG) == "1",
    "install_smoke inner unittest must not re-enter install_smoke",
)
class InstallSmokeTest(unittest.TestCase):
    def test_install_smoke_exits_zero(self) -> None:
        script = ROOT / "install_smoke.py"
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("install_smoke: ok", proc.stdout)

    def test_install_smoke_json_contract(self) -> None:
        script = ROOT / "install_smoke.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("ok"))
        steps = payload.get("steps")
        self.assertIsInstance(steps, list)
        names = {row["name"] for row in steps}
        self.assertIn("demo_json", names)
        demo_step = next(r for r in steps if r["name"] == "demo_json")
        self.assertEqual(demo_step.get("warn_count"), 3)
        self.assertEqual(demo_step.get("error_count"), 0)


if __name__ == "__main__":
    unittest.main()
