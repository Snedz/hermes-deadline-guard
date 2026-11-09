#!/usr/bin/env python3
"""Simulate a clean public-repo checkout (stdlib only).

Copies the same file set as export_public.py into a temporary directory, then runs
unittest, manifest_lint, export_public --check, and demo_cli --json. Judges and founders can use this before
tagging Snedz/hermes-deadline-guard without the private monorepo paths.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from export_public import iter_public_files

ROOT = Path(__file__).resolve().parent
DEMO_TODAY = "2026-11-06"
# Set on the unittest subprocess so tests/test_install_smoke.py does not re-enter this runner.
INNER_ENV_FLAG = "DEADLINE_GUARD_INSTALL_SMOKE_INNER"


def _copy_export(dest: Path) -> int:
    count = 0
    for src in iter_public_files():
        rel = src.relative_to(ROOT)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        count += 1
    return count


def _run(cmd: list[str], cwd: Path, *, extra_env: dict[str, str] | None = None) -> tuple[int, str, str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        err = (exc.stderr or b"").decode("utf-8", errors="replace")
        if not err:
            err = f"command timed out after {exc.timeout}s: {' '.join(cmd)}"
        return 124, "", err
    return proc.returncode, proc.stdout, proc.stderr


def run_install_smoke(*, json_mode: bool = False) -> int:
    py = sys.executable
    report: dict[str, object] = {"plugin": "deadline-guard", "steps": []}
    steps_out: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="deadline-guard-install-") as tmp:
        stage = Path(tmp)
        file_count = _copy_export(stage)
        report["staged_file_count"] = file_count
        report["stage_root"] = str(stage)

        steps: list[tuple[str, list[str]]] = [
            ("unittest", [py, "-m", "unittest", "discover", "-s", "tests", "-q"]),
            ("manifest_lint", [py, "manifest_lint.py"]),
            ("export_check", [py, "export_public.py", "--check"]),
            ("demo_json", [py, "demo_cli.py", "--json"]),
        ]

        inner_env = {INNER_ENV_FLAG: "1"}

        for name, cmd in steps:
            extra_env = inner_env if name == "unittest" else None
            code, out, err = _run(cmd, stage, extra_env=extra_env)
            step_row: dict[str, object] = {"name": name, "exit_code": code}
            if code != 0:
                step_row["stderr"] = err[-2000:] if err else ""
                steps_out.append(step_row)
                report["steps"] = steps_out
                if json_mode:
                    print(json.dumps(report, indent=2, sort_keys=True))
                else:
                    print(f"install_smoke: {name} failed (exit {code})", file=sys.stderr)
                    if err:
                        print(err, file=sys.stderr)
                return code
            if name == "demo_json":
                try:
                    payload = json.loads(out)
                    check = payload["steps"]["check_deadlines"]
                    step_row["warn_count"] = check.get("warn_count")
                    step_row["error_count"] = check.get("error_count")
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    if json_mode:
                        step_row["demo_parse_error"] = str(exc)
                    else:
                        print(f"install_smoke: demo_json parse error: {exc}", file=sys.stderr)
                    steps_out.append(step_row)
                    report["steps"] = steps_out
                    return 1
            steps_out.append(step_row)

        report["steps"] = steps_out
        report["ok"] = True
        if json_mode:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(f"install_smoke: ok ({file_count} files staged, demo today={DEMO_TODAY})")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Machine-readable report")
    args = parser.parse_args(argv)
    return run_install_smoke(json_mode=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
