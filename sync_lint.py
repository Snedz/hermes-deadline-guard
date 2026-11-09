#!/usr/bin/env python3
"""Cross-check plugin.yaml against plugin-catalog/deadline-guard.yaml (stdlib only)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGIN_YAML = ROOT / "plugin.yaml"
CATALOG_YAML = ROOT / "plugin-catalog" / "deadline-guard.yaml"

LIST_ITEM_RE = re.compile(r"^\s+-\s+(\S+)")


def _extract_scalar(text: str, key: str, *, quoted: bool) -> str | None:
    if quoted:
        match = re.search(rf'^{re.escape(key)}:\s*"([^"]+)"', text, re.MULTILINE)
    else:
        match = re.search(rf"^{re.escape(key)}:\s*(\S+)", text, re.MULTILINE)
    return match.group(1) if match else None


def _normalize_scalar(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def _scalar_value(text: str, key: str, *, catalog_version: bool = False) -> str | None:
    if catalog_version:
        value = _extract_scalar(text, key, quoted=True)
    else:
        single = re.search(rf"^{re.escape(key)}:\s*'([^']+)'", text, re.MULTILINE)
        if single:
            value = single.group(1)
        else:
            value = _extract_scalar(text, key, quoted=True) or _extract_scalar(text, key, quoted=False)
    if not value:
        return None
    return _normalize_scalar(value)


def _extract_yaml_list(text: str, header: str) -> list[str] | None:
    lines = text.splitlines()
    header_re = re.compile(rf"^{re.escape(header)}:\s*$")
    start: int | None = None
    for idx, line in enumerate(lines):
        if header_re.match(line):
            start = idx + 1
            break
    if start is None:
        return None

    items: list[str] = []
    for line in lines[start:]:
        if line and not line[0].isspace():
            break
        item = LIST_ITEM_RE.match(line)
        if item:
            items.append(item.group(1))
    return items


def _extract_catalog_tools(text: str) -> list[str] | None:
    lines = text.splitlines()
    in_capabilities = False
    in_tools = False
    items: list[str] = []
    for line in lines:
        if re.match(r"^capabilities:\s*$", line):
            in_capabilities = True
            in_tools = False
            continue
        if in_capabilities and re.match(r"^\s+provides_tools:\s*$", line):
            in_tools = True
            continue
        if in_tools:
            if line and not line.startswith(" "):
                break
            if re.match(r"^\s{2}\S", line) and not LIST_ITEM_RE.match(line):
                in_tools = False
                continue
            item = LIST_ITEM_RE.match(line)
            if item:
                items.append(item.group(1))
    return items if items else None


def lint_sync(
    plugin_text: str,
    catalog_text: str,
) -> list[str]:
    errors: list[str] = []

    plugin_version = _scalar_value(plugin_text, "version")
    catalog_version = _scalar_value(catalog_text, "version", catalog_version=True)
    if not plugin_version:
        errors.append("plugin.yaml missing version")
    if not catalog_version:
        errors.append("catalog missing quoted version")
    elif plugin_version and plugin_version != catalog_version:
        errors.append(f"version mismatch: plugin.yaml {plugin_version!r} vs catalog {catalog_version!r}")

    plugin_requires = _scalar_value(plugin_text, "requires_hermes")
    catalog_requires = _scalar_value(catalog_text, "requires_hermes")
    if not plugin_requires:
        errors.append("plugin.yaml missing requires_hermes")
    if not catalog_requires:
        errors.append("catalog missing quoted requires_hermes")
    elif plugin_requires and catalog_requires:
        if plugin_requires != catalog_requires:
            errors.append(f"requires_hermes mismatch: plugin.yaml {plugin_requires!r} vs catalog {catalog_requires!r}")

    plugin_tools = _extract_yaml_list(plugin_text, "provides_tools")
    catalog_tools = _extract_catalog_tools(catalog_text)
    if plugin_tools is None:
        errors.append("plugin.yaml missing provides_tools list")
    if catalog_tools is None:
        errors.append("catalog missing capabilities.provides_tools list")
    if plugin_tools is not None and catalog_tools is not None:
        plugin_set = set(plugin_tools)
        catalog_set = set(catalog_tools)
        if plugin_set != catalog_set:
            only_plugin = sorted(plugin_set - catalog_set)
            only_catalog = sorted(catalog_set - plugin_set)
            if only_plugin:
                errors.append(f"tools only in plugin.yaml: {only_plugin}")
            if only_catalog:
                errors.append(f"tools only in catalog: {only_catalog}")

    return errors


def main() -> int:
    if not PLUGIN_YAML.is_file():
        print(f"error: missing {PLUGIN_YAML}", file=sys.stderr)
        return 2
    if not CATALOG_YAML.is_file():
        print("sync_lint: ok (no catalog file)")
        return 0

    plugin_text = PLUGIN_YAML.read_text(encoding="utf-8")
    catalog_text = CATALOG_YAML.read_text(encoding="utf-8")
    errors = lint_sync(plugin_text, catalog_text)
    if errors:
        for err in errors:
            print(f"sync_lint: {err}", file=sys.stderr)
        return 1
    print("sync_lint: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
