#!/usr/bin/env python3
"""List files for the public Snedz/hermes-deadline-guard repo and scan for kitchen leaks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Kitchen-only paths (stay in private staging; omit from public copy).
KITCHEN_ONLY_REL = (
    "FOUNDER_HANDOFF.md",
    "JUDGE.md",
    "DEMO_SCRIPT.md",
    "DEMO_VIDEO.md",
    "VIDEO_BEATS.md",
    "catalog_pr_pack.py",
    "judge_path.py",
    "tests/test_judge_path.py",
    "plugin-catalog",
    "spike",
)

# Substrings that must not appear in files destined for the public plugin repo.
FORBIDDEN_SUBSTRINGS = (
    "program-67",
    "OS/BRAIN",
    "snowden",
    "snowdenzeng",
    "MissionWinning/67",
    "Snedz/program-67",
    "HACKATHON/hermes-deadline-guard",
    "scripts.test_deadline_guard_hackathon",
)

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".yaml",
    ".yml",
    ".txt",
    ".json",
    ".mjs",
    ".sh",
}


def iter_public_files() -> list[Path]:
    out: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if "__pycache__" in rel.parts:
            continue
        if rel.parts and rel.parts[0] in {".git", "__pycache__"}:
            continue
        if rel.parts and rel.parts[0] in KITCHEN_ONLY_REL:
            continue
        if rel.parts and rel.parts[0] == "demo":
            continue
        if any(rel.as_posix().startswith(prefix) for prefix in KITCHEN_ONLY_REL):
            continue
        out.append(path)
    return out


_MD_LINK = re.compile(r"\]\(([^)#]+\.md(?:#[^)]*)?)\)")


def scan_broken_doc_links(paths: list[Path]) -> list[str]:
    """Relative .md links in public export must resolve to another exported file."""
    allowed = {p.relative_to(ROOT).as_posix() for p in paths}
    errors: list[str] = []
    for path in paths:
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        rel_doc = path.relative_to(ROOT)
        for raw in _MD_LINK.findall(text):
            target = raw.split("#", 1)[0].strip()
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("./"):
                target = target[2:]
            resolved = (rel_doc.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{rel_doc}: link escapes plugin root: {raw!r}")
                continue
            rel_target = resolved.relative_to(ROOT).as_posix()
            if rel_target not in allowed:
                errors.append(f"{rel_doc}: broken public link {raw!r} (missing from export manifest)")
    return errors


def scan_leaks(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    self_name = Path(__file__).name
    for path in paths:
        if path.name == self_name:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "LICENSE",
            "NOTICE",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lower = text.lower()
        for needle in FORBIDDEN_SUBSTRINGS:
            if needle.lower() in lower:
                errors.append(f"{path.relative_to(ROOT)}: forbidden substring {needle!r}")
    return errors


def build_manifest(paths: list[Path]) -> dict[str, object]:
    rows = []
    total = 0
    for path in paths:
        data = path.read_bytes()
        size = len(data)
        total += size
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": size,
            }
        )
    return {
        "plugin": "deadline-guard",
        "file_count": len(rows),
        "total_bytes": total,
        "kitchen_only_excluded": list(KITCHEN_ONLY_REL),
        "files": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print manifest JSON (paths + byte counts)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if kitchen leak substrings found in public files",
    )
    args = parser.parse_args(argv)

    paths = iter_public_files()
    leaks = scan_leaks(paths)
    link_errors = scan_broken_doc_links(paths)
    all_errors = leaks + link_errors

    if args.json:
        payload = build_manifest(paths)
        payload["leak_scan_ok"] = not all_errors
        if all_errors:
            payload["leaks"] = all_errors
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for row in build_manifest(paths)["files"]:
            print(f"{row['bytes']:8d}  {row['path']}")

    if args.check and all_errors:
        for err in all_errors:
            print(f"export_public: {err}", file=sys.stderr)
        return 1

    if args.check:
        print("export_public: ok", file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
