#!/usr/bin/env python3
"""Deterministic demo-date assertions (matches DEMO.md on 2026-11-06)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tools  # noqa: E402

DEMO_TODAY = "2026-11-06"


def cfg(_key: str, default=None):
    return default


class GoldenDemoTest(unittest.TestCase):
    def test_check_deadlines_counts(self) -> None:
        raw = tools.check_deadlines({"today": DEMO_TODAY}, cfg)
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertEqual(data["error_count"], 0)
        self.assertEqual(data["warn_count"], 3)
        self.assertEqual(data["open_row_count"], 3)

    def test_next_founder_steps_near_miss(self) -> None:
        raw = tools.next_founder_steps(
            {"today": DEMO_TODAY, "within_hours": 48},
            cfg,
        )
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["rows"][0]["item"], "Near Miss Row")
        self.assertEqual(data["rows"][0]["founder_step_by"], "2026-11-07")

    def test_propose_submit_blocks_without_receipt(self) -> None:
        raw = tools.propose_status_update(
            {
                "today": DEMO_TODAY,
                "row": "Demo Plugin Alpha",
                "status": "submitted",
            },
            cfg,
        )
        data = json.loads(raw)
        self.assertFalse(data["ok"])
        self.assertIn("http", data["error"].lower())

    def test_propose_submit_allows_with_receipt(self) -> None:
        raw = tools.propose_status_update(
            {
                "today": DEMO_TODAY,
                "row": "Demo Plugin Alpha",
                "status": "submitted",
                "receipt_url": "https://example.com/hackathon/receipt",
            },
            cfg,
        )
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertEqual(data["proposal"]["proposed_status"], "submitted")

    def test_cron_run_founder_step_count(self) -> None:
        raw = tools.deadline_guard_cron(
            {"action": "run", "today": DEMO_TODAY},
            cfg,
        )
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertIn("Founder steps within 48h: 1", data["summary"])


if __name__ == "__main__":
    unittest.main()
