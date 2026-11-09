"""Daily cron summary — stdlib-only, unattended-safe (always exit 0)."""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import parser as pg

WRAPPER = '''#!/usr/bin/env python3
"""Generated deadline-guard daily check (stdlib only)."""
import datetime as dt
import sys
from pathlib import Path

PLUGIN_ROOT = Path({plugin_root!r})
sys.path.insert(0, str(PLUGIN_ROOT))
import parser as pg  # noqa: E402

DEADLINES = Path({deadlines!r})

if __name__ == "__main__":
    today = dt.date.today()
    text = DEADLINES.read_text(encoding="utf-8")
    errors, warns = pg.check(text, today)
    steps = pg.next_founder_steps(text, today, within_hours=48)
    lines = [pg.format_check_summary(errors, warns)]
    if steps:
        lines.append(f"Founder steps within 48h: {{len(steps)}}")
        for row in steps[:5]:
            lines.append(
                f"  - {{row['item']}} by {{row['founder_step_by']}}: {{row['founder_only_step']}}"
            )
    print("\\n".join(lines))
'''


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def run_daily_summary(deadlines_path: Path, today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    text = deadlines_path.read_text(encoding="utf-8")
    errors, warns = pg.check(text, today)
    steps = pg.next_founder_steps(text, today, within_hours=48)
    lines = [pg.format_check_summary(errors, warns)]
    if steps:
        lines.append(f"Founder steps within 48h: {len(steps)}")
        for row in steps[:5]:
            lines.append(f"  - {row['item']} by {row['founder_step_by']}: {row['founder_only_step']}")
    return "\n".join(lines)


def install_cron_script(deadlines_path: Path) -> Path:
    scripts = hermes_home() / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    plugin_root = Path(__file__).resolve().parent
    target = scripts / "deadline_guard_daily.py"
    target.write_text(
        WRAPPER.format(plugin_root=str(plugin_root), deadlines=str(deadlines_path.resolve())),
        encoding="utf-8",
    )
    target.chmod(0o755)
    return target


def main(argv: list[str] | None = None) -> int:
    """CLI entry when run as ``python -m deadline_guard_cron`` from plugin root."""
    argv = list(argv if argv is not None else sys.argv[1:])
    today: dt.date | None = None
    if "--today" in argv:
        i = argv.index("--today")
        if i + 1 >= len(argv):
            print("usage: cron.py [--today YYYY-MM-DD] <deadlines.md>", file=sys.stderr)
            return 2
        today = dt.date.fromisoformat(argv[i + 1])
        del argv[i : i + 2]
    if len(argv) != 1:
        print("usage: cron.py [--today YYYY-MM-DD] <deadlines.md>", file=sys.stderr)
        return 2
    path = Path(argv[0]).expanduser().resolve()
    print(run_daily_summary(path, today=today))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
