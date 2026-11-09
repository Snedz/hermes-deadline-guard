#!/usr/bin/env python3
"""plugin.yaml lint (stdlib only)."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_YAML = ROOT / "plugin-catalog" / "deadline-guard.yaml"
sys.path.insert(0, str(ROOT))
import manifest_lint  # noqa: E402


class PluginManifestTest(unittest.TestCase):
    def test_plugin_yaml_passes_lint(self) -> None:
        text = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
        errors = manifest_lint.lint_plugin_yaml(text)
        self.assertEqual(errors, [])

    @unittest.skipUnless(
        CATALOG_YAML.is_file(),
        "plugin-catalog is kitchen-only; absent in public export smoke",
    )
    def test_version_matches_catalog_draft(self) -> None:
        plugin = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
        catalog = CATALOG_YAML.read_text(encoding="utf-8")
        pv = re.search(r"^version:\s*(\S+)", plugin, re.MULTILINE)
        cv = re.search(r'^version:\s*"([^"]+)"', catalog, re.MULTILINE)
        self.assertIsNotNone(pv)
        self.assertIsNotNone(cv)
        self.assertEqual(pv.group(1), cv.group(1))


if __name__ == "__main__":
    unittest.main()
