#!/usr/bin/env python3
"""Smoke-test Hermes register() wiring without the Hermes runtime."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import schemas  # noqa: E402


class _FakeCtx:
    def __init__(self) -> None:
        self.tools: list[tuple[str, dict, str]] = []
        self.config: dict = {}
        self.blueprints: list[str] = []
        self.skills: list[str] = []

    def register_tool(self, *, name: str, schema: dict, handler, toolset: str) -> None:
        self.tools.append((name, schema, toolset))

    def get_config(self, key: str, default=None):
        return self.config.get(key, default)

    def register_automation_blueprint(self, slug: str, **_kw) -> None:
        self.blueprints.append(slug)

    def register_skill(self, name: str, path: Path) -> None:
        self.skills.append(name)


def _load_plugin():
    import importlib.util

    init_path = ROOT / "__init__.py"
    spec = importlib.util.spec_from_file_location("deadline_guard_plugin", init_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {init_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RegisterTest(unittest.TestCase):
    def test_register_exposes_all_tools(self) -> None:
        plugin = _load_plugin()
        ctx = _FakeCtx()
        plugin.register(ctx)
        names = {t[0] for t in ctx.tools}
        self.assertEqual(names, set(schemas.TOOLS.keys()))
        for name, schema, toolset in ctx.tools:
            self.assertEqual(schema["name"], name)
            self.assertEqual(toolset, "deadline-guard")

    def test_handlers_return_json(self) -> None:
        import json

        import tools as tool_mod

        raw = tool_mod.handle("check_deadlines", {"today": "2026-11-06"}, lambda _k, d=None: d)
        data = json.loads(raw)
        self.assertTrue(data["ok"])


if __name__ == "__main__":
    unittest.main()
