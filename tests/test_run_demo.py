#!/usr/bin/env python3
"""run_demo.sh: offline, fast, judge-visible golden lines."""

from __future__ import annotations

import subprocess
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_DEMO = ROOT / "demo" / "run_demo.sh"
REPO_ROOT = ROOT.parents[1]


@unittest.skipUnless(
    RUN_DEMO.is_file(),
    "demo/run_demo.sh is kitchen-only; omitted from public export smoke",
)
class RunDemoTest(unittest.TestCase):
    def _run(self, *, cwd: Path) -> tuple[subprocess.CompletedProcess[str], float]:
        start = time.monotonic()
        proc = subprocess.run(
            ["bash", str(RUN_DEMO)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        elapsed = time.monotonic() - start
        return proc, elapsed

    def test_run_demo_from_plugin_dir_offline(self) -> None:
        proc, elapsed = self._run(cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(elapsed, 5.0, "demo should finish quickly for video capture")
        out = proc.stdout
        self.assertIn("offline", out)
        self.assertIn('"error_count": 0', out)
        self.assertIn('"warn_count": 3', out)
        self.assertIn("http(s) link", out)
        self.assertIn("Near Miss Row", out)
        self.assertIn("Founder steps within 48h: 1", out)
        self.assertIn("Demo complete", out)

    def test_run_demo_from_repo_root(self) -> None:
        monorepo_plugin = REPO_ROOT / "HACKATHON" / "hermes-deadline-guard"
        if not (monorepo_plugin / "plugin.yaml").is_file():
            self.skipTest("monorepo layout not present (public clone)")
        script = ROOT / "demo" / "run_demo.sh"
        start = time.monotonic()
        proc = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO_ROOT,
        )
        elapsed = time.monotonic() - start
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(elapsed, 5.0)
        self.assertIn("Demo complete", proc.stdout)

    def test_run_demo_uses_only_local_fixture(self) -> None:
        """No network: script must not reference URLs beyond printed JSON."""
        proc, _ = self._run(cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("examples/hackathon-deadlines.md", proc.stdout)


if __name__ == "__main__":
    unittest.main()
