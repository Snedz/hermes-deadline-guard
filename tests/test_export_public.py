#!/usr/bin/env python3
"""Public export manifest + leak scan tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import export_public  # noqa: E402


class ExportPublicTest(unittest.TestCase):
    def test_public_manifest_non_empty(self) -> None:
        paths = export_public.iter_public_files()
        self.assertGreaterEqual(len(paths), 10)
        names = {p.name for p in paths}
        self.assertIn("plugin.yaml", names)
        self.assertIn("README.md", names)
        self.assertNotIn("FOUNDER_HANDOFF.md", names)
        self.assertNotIn("FOUNDER_STEPS.md", names)

    def test_no_kitchen_leaks_in_public_files(self) -> None:
        paths = export_public.iter_public_files()
        leaks = export_public.scan_leaks(paths)
        self.assertEqual(leaks, [], "\n".join(leaks))

    def test_no_broken_relative_md_links_in_public_export(self) -> None:
        paths = export_public.iter_public_files()
        errors = export_public.scan_broken_doc_links(paths)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_public_readme_demo_uses_plugin_root_commands(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_paths = [p for p in export_public.iter_public_files() if p.name == "README.md"]
        self.assertEqual(export_public.scan_leaks(readme_paths), [])
        self.assertIn("python3 install_smoke.py", readme)

    def test_judge_path_excluded_from_public_export(self) -> None:
        paths = export_public.iter_public_files()
        rels = {p.relative_to(ROOT).as_posix() for p in paths}
        self.assertNotIn("judge_path.py", rels)
        self.assertNotIn("tests/test_judge_path.py", rels)
        self.assertIn("DEMO.md", rels)
        demo = (ROOT / "DEMO.md").read_text(encoding="utf-8")
        self.assertNotIn("python3 judge_path.py", demo)
        self.assertNotIn("Kitchen staging", demo)
        self.assertIn("python3 install_smoke.py", demo)

    def test_kitchen_only_paths_excluded(self) -> None:
        paths = export_public.iter_public_files()
        rels = {p.relative_to(ROOT).as_posix() for p in paths}
        self.assertFalse(any(r.startswith("plugin-catalog/") for r in rels))
        self.assertFalse(any(r.startswith("spike/") for r in rels))

    def test_public_manifest_includes_catalog_lint_without_catalog_yaml(self) -> None:
        paths = export_public.iter_public_files()
        names = {p.name for p in paths}
        self.assertIn("catalog_lint.py", names)
        rels = {p.relative_to(ROOT).as_posix() for p in paths}
        self.assertFalse(any(r == "plugin-catalog/deadline-guard.yaml" for r in rels))


if __name__ == "__main__":
    unittest.main()
