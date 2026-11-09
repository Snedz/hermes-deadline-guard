#!/usr/bin/env python3
"""Tests for plugin.yaml ↔ catalog sync lint."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_YAML = ROOT / "plugin-catalog" / "deadline-guard.yaml"
sys.path.insert(0, str(ROOT))

import schemas  # noqa: E402
import sync_lint  # noqa: E402


class SyncLintTest(unittest.TestCase):
    @unittest.skipUnless(
        CATALOG_YAML.is_file(),
        "plugin-catalog is kitchen-only; absent in public export smoke",
    )
    def test_staging_tree_in_sync(self) -> None:
        plugin = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
        catalog = CATALOG_YAML.read_text(encoding="utf-8")
        errors = sync_lint.lint_sync(plugin, catalog)
        self.assertEqual(errors, [])

    def test_plugin_tools_match_schemas(self) -> None:
        plugin = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
        tools = sync_lint._extract_yaml_list(plugin, "provides_tools")
        self.assertIsNotNone(tools)
        self.assertEqual(set(tools), set(schemas.TOOLS.keys()))

    @unittest.skipUnless(
        CATALOG_YAML.is_file(),
        "plugin-catalog is kitchen-only; absent in public export smoke",
    )
    def test_detects_version_mismatch(self) -> None:
        plugin = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
        catalog = CATALOG_YAML.read_text(encoding="utf-8")
        catalog_bad = catalog.replace('version: "0.1.7"', 'version: "9.9.9"')
        errors = sync_lint.lint_sync(plugin, catalog_bad)
        self.assertTrue(any("version mismatch" in e for e in errors))

    def test_reordered_tools_ok(self) -> None:
        plugin = (
            "name: deadline-guard\n"
            "version: 0.1.0\n"
            "requires_hermes: '>=0.21.4'\n"
            "provides_tools:\n"
            "  - deadline_guard_cron\n"
            "  - check_deadlines\n"
        )
        catalog = (
            'version: "0.1.0"\n'
            'requires_hermes: ">=0.21.4"\n'
            "capabilities:\n"
            "  provides_tools:\n"
            "    - check_deadlines\n"
            "    - deadline_guard_cron\n"
        )
        self.assertEqual(sync_lint.lint_sync(plugin, catalog), [])

    def test_detects_tool_only_in_plugin(self) -> None:
        plugin = "version: 0.1.0\nrequires_hermes: '>=0.21.4'\nprovides_tools:\n  - check_deadlines\n  - extra_tool\n"
        catalog = (
            'version: "0.1.0"\nrequires_hermes: ">=0.21.4"\ncapabilities:\n  provides_tools:\n    - check_deadlines\n'
        )
        errors = sync_lint.lint_sync(plugin, catalog)
        self.assertTrue(any("only in plugin" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
