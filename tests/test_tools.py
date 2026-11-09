#!/usr/bin/env python3
"""Tool handler tests (JSON surface)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tools  # noqa: E402


def cfg(_key: str, default=None):
    return default


def cfg_empty_path(_key: str, default=None):
    if _key == "deadlines_path":
        return "   "
    return default


def cfg_missing_file(_key: str, default=None):
    if _key == "deadlines_path":
        return "does-not-exist/deadlines.md"
    return default


class ToolsTest(unittest.TestCase):
    def test_check_deadlines_on_example(self):
        raw = tools.check_deadlines({"today": "2026-11-06"}, cfg)
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertIn("error_count", data)
        self.assertIn("warn_count", data)

    def test_propose_status_update_rejects_bad_submit(self):
        raw = tools.propose_status_update(
            {"row": "Demo Plugin Alpha", "status": "submitted", "today": "2026-11-06"},
            cfg,
        )
        data = json.loads(raw)
        self.assertFalse(data["ok"])

    def test_cron_run(self):
        raw = tools.deadline_guard_cron({"action": "run", "today": "2026-11-06"}, cfg)
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertIn("summary", data)

    def test_check_deadlines_rejects_bad_today(self):
        raw = tools.check_deadlines({"today": "11/06/2026"}, cfg)
        data = json.loads(raw)
        self.assertFalse(data["ok"])
        self.assertIn("YYYY-MM-DD", data["error"])

    def test_next_founder_steps_rejects_zero_window(self):
        raw = tools.next_founder_steps(
            {"today": "2026-11-06", "within_hours": 0},
            cfg,
        )
        data = json.loads(raw)
        self.assertFalse(data["ok"])
        self.assertIn("within_hours", data["error"])

    def test_empty_config_deadlines_path_uses_default_example(self):
        raw = tools.check_deadlines({"today": "2026-11-06"}, cfg_empty_path)
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertIn("examples", data["path"])

    def test_missing_configured_path_returns_actionable_error(self):
        raw = tools.check_deadlines({"today": "2026-11-06"}, cfg_missing_file)
        data = json.loads(raw)
        self.assertFalse(data["ok"])
        self.assertIn("deadlines table not found", data["error"])
        self.assertIn("deadlines_path", data["error"])

    def test_missing_override_path_returns_actionable_error(self):
        raw = tools.check_deadlines(
            {"today": "2026-11-06", "path": "/tmp/deadline-guard-no-such-file.md"},
            cfg,
        )
        data = json.loads(raw)
        self.assertFalse(data["ok"])
        self.assertIn("deadlines table not found", data["error"])


if __name__ == "__main__":
    unittest.main()
