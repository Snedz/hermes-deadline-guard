#!/usr/bin/env python3
"""Stdlib-only sanity check for plugin.yaml (no PyYAML). Used in CI tests and local pre-validate."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGIN_YAML = ROOT / "plugin.yaml"

REQUIRED_KEYS = (
    "name:",
    "version:",
    "description:",
    "license:",
    "manifest_version:",
    "requires_hermes:",
    "provides_tools:",
)

TOOL_NAMES = (
    "check_deadlines",
    "next_founder_steps",
    "propose_status_update",
    "deadline_guard_cron",
)


def lint_plugin_yaml(text: str) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in text:
            errors.append(f"missing key line containing {key!r}")

    for tool in TOOL_NAMES:
        if tool not in text:
            errors.append(f"provides_tools missing {tool!r}")

    version_match = re.search(r"^version:\s*(\S+)", text, re.MULTILINE)
    if not version_match:
        errors.append("could not parse version:")
    elif not re.fullmatch(r"\d+\.\d+\.\d+", version_match.group(1)):
        errors.append(f"version not semver patch triple: {version_match.group(1)!r}")

    name_match = re.search(r"^name:\s*(\S+)", text, re.MULTILINE)
    if name_match and name_match.group(1) != "deadline-guard":
        errors.append(f"unexpected name: {name_match.group(1)!r}")

    return errors


def main() -> int:
    if not PLUGIN_YAML.is_file():
        print(f"error: missing {PLUGIN_YAML}", file=sys.stderr)
        return 2
    text = PLUGIN_YAML.read_text(encoding="utf-8")
    errors = lint_plugin_yaml(text)
    if errors:
        for err in errors:
            print(f"manifest_lint: {err}", file=sys.stderr)
        return 1
    print("manifest_lint: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
