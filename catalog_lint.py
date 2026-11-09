#!/usr/bin/env python3
"""Stdlib-only lint for plugin-catalog/deadline-guard.yaml (Hermes admission fields)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG_YAML = ROOT / "plugin-catalog" / "deadline-guard.yaml"

REQUIRED_LINE_KEYS = (
    "name:",
    "repo:",
    "sha:",
    "description:",
    "maintainer:",
    "tier:",
    "category:",
    "version:",
    "requires_hermes:",
    "capabilities:",
)

SHA_PLACEHOLDER = "0" * 40


def lint_catalog_yaml(text: str, *, allow_placeholder_sha: bool = True) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_LINE_KEYS:
        if key not in text:
            errors.append(f"missing key line containing {key!r}")

    name_match = re.search(r"^name:\s*(\S+)", text, re.MULTILINE)
    if name_match and name_match.group(1) != "deadline-guard":
        errors.append(f"unexpected catalog name: {name_match.group(1)!r}")

    sha_match = re.search(r'^sha:\s*"?([0-9a-fA-F]{40})"?', text, re.MULTILINE)
    if not sha_match:
        errors.append("sha must be a quoted or bare 40-character hex commit")
    elif sha_match.group(1) == SHA_PLACEHOLDER:
        if not allow_placeholder_sha:
            errors.append("sha is still the placeholder; pin the public repo release tag")
    elif not re.fullmatch(r"[0-9a-f]{40}", sha_match.group(1)):
        errors.append("sha must be lowercase hex (catalog CI expectation)")

    repo_match = re.search(r"^repo:\s*(\S+)", text, re.MULTILINE)
    if repo_match and not repo_match.group(1).startswith("https://github.com/"):
        errors.append("repo must be an https://github.com/ clone URL")

    version_match = re.search(r'^version:\s*"([^"]+)"', text, re.MULTILINE)
    if not version_match:
        errors.append('version must be quoted semver, e.g. version: "0.1.7"')

    for tool in (
        "check_deadlines",
        "next_founder_steps",
        "propose_status_update",
        "deadline_guard_cron",
    ):
        if tool not in text:
            errors.append(f"capabilities must mention tool {tool!r}")

    return errors


def main() -> int:
    if not CATALOG_YAML.is_file():
        print(
            "catalog_lint: skip (plugin-catalog/deadline-guard.yaml not present; kitchen-only)",
        )
        return 0
    text = CATALOG_YAML.read_text(encoding="utf-8")
    errors = lint_catalog_yaml(text)
    if errors:
        for err in errors:
            print(f"catalog_lint: {err}", file=sys.stderr)
        return 1
    print("catalog_lint: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
