#!/usr/bin/env python3
"""readme_quickstart.py matches README/INSTALL and exits 0."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "readme_quickstart.py"
INNER_ENV_FLAG = "DEADLINE_GUARD_README_QUICKSTART_INNER"


@unittest.skipUnless(
    SCRIPT.is_file(),
    "readme_quickstart.py is kitchen-only; absent in public export smoke",
)
@unittest.skipIf(
    os.environ.get(INNER_ENV_FLAG) == "1",
    "readme_quickstart inner unittest must not re-enter readme_quickstart",
)
class ReadmeQuickstartTest(unittest.TestCase):
    def test_readme_quickstart_exits_zero(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=240,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("readme_quickstart: ok", proc.stdout)

    def test_readme_quickstart_json_lists_manual_steps(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=240,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("ok"))
        names = {row["name"] for row in payload["steps"]}
        for want in ("unittest", "demo_cli", "manifest_lint", "catalog_lint", "export_public"):
            self.assertIn(want, names)


if __name__ == "__main__":
    unittest.main()
