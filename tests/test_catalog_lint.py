#!/usr/bin/env python3
"""Catalog YAML lint tests."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_YAML = ROOT / "plugin-catalog" / "deadline-guard.yaml"
sys.path.insert(0, str(ROOT))
import catalog_lint  # noqa: E402


class CatalogLintTest(unittest.TestCase):
    @unittest.skipUnless(
        CATALOG_YAML.is_file(),
        "plugin-catalog is kitchen-only; absent in public export smoke",
    )
    def test_catalog_yaml_passes_lint(self) -> None:
        text = CATALOG_YAML.read_text(encoding="utf-8")
        errors = catalog_lint.lint_catalog_yaml(text)
        self.assertEqual(errors, [])

    def test_cli_skips_when_catalog_yaml_missing(self) -> None:
        """Public export includes catalog_lint.py but not plugin-catalog/."""
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            dest = stage / "catalog_lint.py"
            dest.write_text((ROOT / "catalog_lint.py").read_text(encoding="utf-8"), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(dest)],
                cwd=stage,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("catalog_lint: skip", proc.stdout)

    def test_rejects_short_sha(self) -> None:
        bad = (
            "name: deadline-guard\n"
            "repo: https://github.com/Snedz/hermes-deadline-guard\n"
            'sha: "abc"\n'
            "description: x\n"
            "maintainer: Snedz\n"
            "tier: community\n"
            "category: automation\n"
            'version: "0.1.7"\n'
            'requires_hermes: ">=0.21.4"\n'
            "capabilities:\n"
            "  provides_tools:\n"
            "    - check_deadlines\n"
            "    - next_founder_steps\n"
            "    - propose_status_update\n"
            "    - deadline_guard_cron\n"
        )
        errors = catalog_lint.lint_catalog_yaml(bad)
        self.assertTrue(any("sha" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
