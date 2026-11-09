#!/usr/bin/env python3
"""Unit tests for deadline-guard parser."""

from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import parser as pg  # noqa: E402

HEAD = (
    "| Item | Owner | Deadline ET | Build window (open to deadline ET) | "
    "Planned build blocks | Founder-only step | Founder step by | Link | Status |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
)
TODAY = dt.date(2026, 11, 6)


def row(
    item="X",
    owner="Agent",
    due="2026-11-20",
    window="now",
    by="2026-11-18",
    status="not started",
):
    return f"| {item} | {owner} | {due} | {window} | b | founder step | {by} | https://example.com | {status} |\n"


class ParserCheckTest(unittest.TestCase):
    def test_clean_row(self):
        self.assertEqual(pg.check(HEAD + row(), TODAY), ([], []))

    def test_missing_column_is_error(self):
        errs, _ = pg.check(HEAD.replace("Owner", "Who"), TODAY)
        self.assertTrue(errs and "Owner" in errs[0])

    def test_missing_owner_is_error(self):
        errs, _ = pg.check(HEAD + row(owner="—"), TODAY)
        self.assertEqual(len(errs), 1)

    def test_due_soon_founder_not_done(self):
        _, warns = pg.check(HEAD + row(due="2026-11-08", by="2026-11-06"), TODAY)
        self.assertTrue(any("<=3 days" in w for w in warns))

    def test_past_due_open(self):
        _, warns = pg.check(HEAD + row(due="2026-11-05", by="2026-11-04"), TODAY)
        self.assertTrue(any("PAST DUE" in w for w in warns))

    def test_closed_rows_ignored(self):
        text = HEAD + row(owner="", due="2026-11-05", status="**missed**: x")
        self.assertEqual(pg.check(text, TODAY), ([], []))


class ProposeStatusTest(unittest.TestCase):
    def test_submitted_without_url_blocked(self):
        ok, msg, _ = pg.propose_status_update(
            HEAD + row(item="Demo Plugin Alpha"),
            row="Demo Plugin Alpha",
            status="submitted",
            receipt_url=None,
        )
        self.assertFalse(ok)
        self.assertIn("receipt_url", msg)

    def test_submitted_with_url_ok(self):
        ok, _, detail = pg.propose_status_update(
            HEAD + row(item="Demo Plugin Alpha"),
            row="Demo Plugin Alpha",
            status="submitted",
            receipt_url="https://example.com/receipt",
        )
        self.assertTrue(ok)
        assert detail is not None
        self.assertEqual(detail["receipt_url"], "https://example.com/receipt")


class FounderStepsTest(unittest.TestCase):
    def test_within_window(self):
        text = HEAD + row(item="Near Miss Row", by="2026-11-07")
        steps = pg.next_founder_steps(text, TODAY, within_hours=48)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["item"], "Near Miss Row")

    def test_past_step_excluded(self):
        text = HEAD + row(by="2026-11-05")
        self.assertEqual(pg.next_founder_steps(text, TODAY, within_hours=48), [])


class ExampleFixtureTest(unittest.TestCase):
    def test_hackathon_example_parses_three_plus_rows(self):
        path = ROOT / "examples" / "hackathon-deadlines.md"
        text = path.read_text(encoding="utf-8")
        _, rows = pg.parse_table(text)
        self.assertGreaterEqual(len(rows), 3)
        self.assertTrue(any("Founder" in r.get("Founder-only step", "") for r in rows))

    def test_hackathon_example_open_row_count(self):
        path = ROOT / "examples" / "hackathon-deadlines.md"
        text = path.read_text(encoding="utf-8")
        self.assertEqual(pg.count_open_rows(text), 3)


if __name__ == "__main__":
    unittest.main()
