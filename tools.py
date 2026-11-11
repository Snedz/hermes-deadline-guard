"""Tool handlers for the deadline-guard Hermes plugin."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable


def _import_sibling(name: str):
    if __package__:
        try:
            return importlib.import_module(f".{name}", __package__)
        except ModuleNotFoundError:
            pass
    if name != "parser":
        try:
            return importlib.import_module(name)
        except ModuleNotFoundError:
            pass
    mod_path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_deadline_guard_{name}", mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cron_mod = _import_sibling("cron")
pg = _import_sibling("parser")

DEFAULT_REL = "examples/hackathon-deadlines.md"


def _plugin_root() -> Path:
    return Path(__file__).resolve().parent


def resolve_deadlines_path(get_config: Callable[[str, Any], Any], override: str | None) -> Path:
    if override and override.strip():
        p = Path(override.strip()).expanduser()
        if not p.is_absolute():
            p = (_plugin_root() / p).resolve()
        return p
    cfg = get_config("deadlines_path", DEFAULT_REL)
    if cfg is None or (isinstance(cfg, str) and not str(cfg).strip()):
        cfg = DEFAULT_REL
    p = Path(str(cfg)).expanduser()
    if not p.is_absolute():
        p = (_plugin_root() / p).resolve()
    return p


def _read_deadlines(path: Path) -> tuple[str | None, str | None]:
    try:
        return _read(path), None
    except OSError as exc:
        hint = "Set Hermes plugin config deadlines_path to your markdown table, or pass path in the tool call."
        if isinstance(exc, FileNotFoundError):
            return None, f"deadlines table not found at {path}. {hint}"
        return None, f"cannot read {path}: {exc}. {hint}"


def _parse_today(value: str | None) -> tuple[dt.date | None, str | None]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return dt.date.today(), None
    if not isinstance(value, str):
        return None, f"today must be ISO YYYY-MM-DD, got {type(value).__name__}"
    try:
        return dt.date.fromisoformat(value.strip()), None
    except ValueError:
        return None, f"today must be ISO YYYY-MM-DD, got {value!r}"


def _parse_within_hours(value: Any) -> tuple[int | None, str | None]:
    if value is None or value == "":
        return 48, None
    try:
        hours = int(value)
    except (TypeError, ValueError):
        return None, "within_hours must be an integer"
    if hours < 1:
        return None, "within_hours must be at least 1"
    return hours, None


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _ok(**fields: Any) -> str:
    return json.dumps({"ok": True, **fields})


def _err(msg: str, **fields: Any) -> str:
    return json.dumps({"ok": False, "error": msg, **fields})


def check_deadlines(args: dict[str, Any], get_config: Callable[[str, Any], Any]) -> str:
    path = resolve_deadlines_path(get_config, args.get("path"))
    text, read_err = _read_deadlines(path)
    if read_err:
        return _err(read_err, path=str(path))
    today, today_err = _parse_today(args.get("today"))
    if today_err:
        return _err(today_err)
    assert today is not None
    errors, warns = pg.check(text, today)
    open_row_count = pg.count_open_rows(text)
    return _ok(
        path=str(path),
        today=today.isoformat(),
        error_count=len(errors),
        warn_count=len(warns),
        open_row_count=open_row_count,
        errors=errors,
        warnings=warns,
        summary=pg.format_check_summary(errors, warns),
    )


def next_founder_steps(args: dict[str, Any], get_config: Callable[[str, Any], Any]) -> str:
    path = resolve_deadlines_path(get_config, args.get("path"))
    text, read_err = _read_deadlines(path)
    if read_err:
        return _err(read_err, path=str(path))
    today, today_err = _parse_today(args.get("today"))
    if today_err:
        return _err(today_err)
    assert today is not None
    hours, hours_err = _parse_within_hours(args.get("within_hours"))
    if hours_err:
        return _err(hours_err)
    assert hours is not None
    rows = pg.next_founder_steps(text, today, within_hours=hours)
    return _ok(
        path=str(path),
        today=today.isoformat(),
        within_hours=hours,
        count=len(rows),
        rows=rows,
    )


def propose_status_update(args: dict[str, Any], get_config: Callable[[str, Any], Any]) -> str:
    path = resolve_deadlines_path(get_config, args.get("path"))
    text, read_err = _read_deadlines(path)
    if read_err:
        return _err(read_err, path=str(path))
    ok, msg, detail = pg.propose_status_update(
        text,
        row=str(args.get("row") or ""),
        status=str(args.get("status") or ""),
        receipt_url=args.get("receipt_url"),
    )
    if not ok:
        return _err(msg)
    return _ok(proposal=detail, message=msg)


def deadline_guard_cron(args: dict[str, Any], get_config: Callable[[str, Any], Any]) -> str:
    action = (args.get("action") or "").strip()
    path = resolve_deadlines_path(get_config, args.get("path"))
    today, today_err = _parse_today(args.get("today"))
    if today_err:
        return _err(today_err)
    assert today is not None
    if action == "run":
        summary = cron_mod.run_daily_summary(path, today)
        return _ok(summary=summary, path=str(path), today=today.isoformat())
    if action == "install":
        script = cron_mod.install_cron_script(path)
        return _ok(
            script=str(script),
            attach_hint=(f'hermes cron add --name deadline-guard-daily --schedule "0 8 * * *" --script {script.name}'),
            note="Script is stdlib-only; exits 0 even when warnings are present.",
        )
    return _err("action must be run or install")


def handle(name: str, args: dict[str, Any] | None, get_config: Callable[[str, Any], Any], **_kw: Any) -> str:
    args = args or {}
    dispatch = {
        "check_deadlines": check_deadlines,
        "next_founder_steps": next_founder_steps,
        "propose_status_update": propose_status_update,
        "deadline_guard_cron": deadline_guard_cron,
    }
    fn = dispatch.get(name)
    if fn is None:
        return _err(f"unknown tool {name!r}")
    try:
        return fn(args, get_config)
    except Exception as exc:  # tool surface must not crash the agent loop
        return _err(f"{type(exc).__name__}: {exc}")
