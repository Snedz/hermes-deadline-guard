#!/usr/bin/env python3
"""Judge-friendly demo runner (stdlib only, no Hermes required).

Runs the same tool handlers the Hermes plugin exposes, with fixed demo date
2026-11-06 so output matches DEMO.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import tools

DEMO_TODAY = "2026-11-06"
ROOT = Path(__file__).resolve().parent
DEFAULT_EXAMPLE = ROOT / "examples" / "hackathon-deadlines.md"


def _cfg(_key: str, default=None):
    return default


def _section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _pretty_json(raw: str) -> None:
    data = json.loads(raw)
    print(json.dumps(data, indent=2, sort_keys=True))


def _demo_steps(*, today: str, example: Path) -> list[tuple[str, str]]:
    path_arg = str(example)
    return [
        (
            "check_deadlines",
            tools.check_deadlines({"today": today, "path": path_arg}, _cfg),
        ),
        (
            "next_founder_steps",
            tools.next_founder_steps(
                {"today": today, "path": path_arg, "within_hours": 48},
                _cfg,
            ),
        ),
        (
            "propose_status_update_blocked",
            tools.propose_status_update(
                {
                    "today": today,
                    "path": path_arg,
                    "row": "Demo Plugin Alpha",
                    "status": "submitted",
                },
                _cfg,
            ),
        ),
        (
            "propose_status_update_ok",
            tools.propose_status_update(
                {
                    "today": today,
                    "path": path_arg,
                    "row": "Demo Plugin Alpha",
                    "status": "submitted",
                    "receipt_url": "https://example.com/hackathon/receipt",
                },
                _cfg,
            ),
        ),
        (
            "deadline_guard_cron_run",
            tools.deadline_guard_cron(
                {"action": "run", "today": today, "path": path_arg},
                _cfg,
            ),
        ),
    ]


def run_demo(*, today: str, example: Path, json_mode: bool = False) -> int:
    if not example.is_file():
        print(f"error: missing example table at {example}", file=sys.stderr)
        return 2

    steps = _demo_steps(today=today, example=example)
    if json_mode:
        payload = {
            "demo_today": today,
            "example_path": str(example),
            "steps": {name: json.loads(raw) for name, raw in steps},
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    rel = example.relative_to(ROOT) if example.is_relative_to(ROOT) else example
    titles = [
        f"1) check_deadlines (today={today}, table={rel})",
        "2) next_founder_steps (within_hours=48)",
        "3) propose_status_update — submitted WITHOUT receipt (expect block)",
        "4) propose_status_update — submitted WITH https receipt (expect ok)",
        "5) deadline_guard_cron action=run (one-screen summary)",
    ]
    for title, (_, raw) in zip(titles, steps, strict=True):
        _section(title)
        _pretty_json(raw)

    print()
    print("Demo complete. For Hermes install + validate steps see DEMO.md.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deadline-guard demo tool sequence.")
    parser.add_argument(
        "--today",
        default=DEMO_TODAY,
        help=f"ISO date for deterministic output (default {DEMO_TODAY}).",
    )
    parser.add_argument(
        "--example",
        type=Path,
        default=DEFAULT_EXAMPLE,
        help="Path to markdown deadlines table.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON document (all tool steps) for scripts and stewards.",
    )
    args = parser.parse_args(argv)
    return run_demo(
        today=args.today,
        example=args.example.expanduser().resolve(),
        json_mode=args.json,
    )


if __name__ == "__main__":
    raise SystemExit(main())
