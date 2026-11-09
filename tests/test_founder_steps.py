#!/usr/bin/env python3
"""FOUNDER_STEPS.md kitchen checklist shape."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "FOUNDER_STEPS.md"

REQUIRED_PHRASES = (
    "@NousResearch",
    "form.typeform.com/to/FwJLvOln",
    "catalog_pr_pack.py",
    "Public repo go-ahead",
    "Typeform",
)


@unittest.skipUnless(DOC.is_file(), "FOUNDER_STEPS.md is kitchen-only (not in public export)")
class FounderStepsDocTest(unittest.TestCase):
    def test_founder_steps_exists_with_required_handoff_lines(self) -> None:
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        for phrase in REQUIRED_PHRASES:
            self.assertIn(phrase, text, f"missing {phrase!r} in FOUNDER_STEPS.md")


if __name__ == "__main__":
    unittest.main()
