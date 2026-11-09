"""Parse DEADLINES.md-style markdown tables and evaluate founder-step discipline.

Stdlib only. Ported from Program 67 draft deadline_check (PR #5289), trimmed for a
public Hermes plugin (no kitchen pack paths or kaizen gates).
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

REQUIRED = (
    "Item",
    "Owner",
    "Deadline ET",
    "Build window",
    "Planned build blocks",
    "Founder step by",
    "Founder-only step",
    "Link",
    "Status",
)
CLOSED = ("done", "submitted", "missed", "parked", "dropped", "won", "cancelled")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
EMPTY = {"", "-", "—", "tbd", "n/a"}
SUBMIT_MARKERS = ("submitted", "submission confirmed")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_table(text: str) -> tuple[list[str], list[dict[str, str]]]:
    """Return (headers, rows) for the first markdown table in text."""
    lines = [ln for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return [], []
    headers = _cells(lines[0])
    rows: list[dict[str, str]] = []
    for ln in lines[2:]:
        cells = _cells(ln)
        cells += [""] * (len(headers) - len(cells))
        rows.append(dict(zip(headers, cells)))
    return headers, rows


def _col(headers: list[str], name: str) -> str | None:
    for h in headers:
        if h == name or h.startswith(name + " ("):
            return h
    return None


def parse_date(value: str) -> dt.date | None:
    m = DATE_RE.search(value or "")
    return dt.date.fromisoformat(m.group(1)) if m else None


def is_open(status: str) -> bool:
    s = status.lower().replace("*", "")
    return not any(s.strip().startswith(w) for w in CLOSED)


def founder_done(status: str) -> bool:
    s = status.lower()
    return "founder done" in s or "founder step done" in s or "submitted" in s


def _row_get(row: dict[str, str], cols: dict[str, str | None], name: str) -> str:
    key = cols.get(name)
    return row.get(key or "", "").strip() if key else ""


def count_open_rows(text: str) -> int:
    """Count table rows whose Status is still open (not done/submitted/etc.)."""
    headers, rows = parse_table(text)
    cols = {name: _col(headers, name) for name in REQUIRED}
    status_col = cols.get("Status")
    if status_col is None:
        return 0
    return sum(1 for row in rows if is_open(row.get(status_col, "")))


def check(text: str, today: dt.date) -> tuple[list[str], list[str]]:
    headers, rows = parse_table(text)
    errors: list[str] = []
    warns: list[str] = []
    cols = {name: _col(headers, name) for name in REQUIRED}
    missing = [n for n, c in cols.items() if c is None]
    if missing:
        return [f"schema: missing column(s) {', '.join(missing)}"], warns

    for row in rows:
        item = _row_get(row, cols, "Item") or "<unnamed>"
        status = _row_get(row, cols, "Status")
        if not is_open(status):
            continue
        if _row_get(row, cols, "Owner").lower() in EMPTY:
            errors.append(f"{item}: open row has no owner")
        window = _row_get(row, cols, "Build window")
        if window.lower() in EMPTY:
            warns.append(f"{item}: no build window")
        step_by = parse_date(_row_get(row, cols, "Founder step by"))
        due = parse_date(_row_get(row, cols, "Deadline ET"))
        if step_by is None:
            warns.append(f"{item}: no founder-step-by date")
        elif due and (due - step_by).days < 2:
            warns.append(f"{item}: founder-step-by is <2 days before deadline")
        if due is None:
            continue
        if due < today:
            warns.append(f"{item}: PAST DUE ({due}) but status still open")
        elif (due - today).days <= 3 and not founder_done(status):
            warns.append(f"{item}: due {due} (<=3 days), founder step not done — raise yes/no to founder")
    return errors, warns


def next_founder_steps(
    text: str,
    today: dt.date,
    *,
    within_hours: int = 48,
) -> list[dict[str, Any]]:
    headers, rows = parse_table(text)
    cols = {name: _col(headers, name) for name in REQUIRED}
    if any(cols[n] is None for n in REQUIRED):
        return []
    window = dt.timedelta(hours=max(1, within_hours))
    out: list[dict[str, Any]] = []
    for row in rows:
        item = _row_get(row, cols, "Item")
        status = _row_get(row, cols, "Status")
        if not item or not is_open(status) or founder_done(status):
            continue
        step_by = parse_date(_row_get(row, cols, "Founder step by"))
        if step_by is None:
            continue
        step_dt = dt.datetime.combine(step_by, dt.time.min, tzinfo=dt.timezone.utc)
        now_dt = dt.datetime.combine(today, dt.time.min, tzinfo=dt.timezone.utc)
        if step_dt < now_dt:
            continue
        if step_dt - now_dt > window:
            continue
        out.append(
            {
                "item": item,
                "founder_step_by": step_by.isoformat(),
                "founder_only_step": _row_get(row, cols, "Founder-only step"),
                "status": status,
                "deadline_et": _row_get(row, cols, "Deadline ET"),
            }
        )
    out.sort(key=lambda r: r["founder_step_by"])
    return out


def requires_receipt_url(status: str) -> bool:
    s = status.lower().replace("*", "").strip()
    return any(m in s for m in SUBMIT_MARKERS)


def valid_receipt_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    u = url.strip().lower()
    return u.startswith("http://") or u.startswith("https://")


def propose_status_update(
    text: str,
    *,
    row: str,
    status: str,
    receipt_url: str | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Validate a status change. Does not write the file."""
    headers, rows = parse_table(text)
    cols = {name: _col(headers, name) for name in REQUIRED}
    status_col = cols.get("Status")
    if status_col is None:
        return False, "schema: missing Status column", None
    needle = (row or "").strip().lower()
    if not needle:
        return False, "row (item name) is required", None
    new_status = (status or "").strip()
    if not new_status:
        return False, "status is required", None
    if requires_receipt_url(new_status) and not valid_receipt_url(receipt_url):
        return (
            False,
            "status marks submission but receipt_url must be an http(s) link",
            None,
        )
    match: dict[str, str] | None = None
    for r in rows:
        item = _row_get(r, cols, "Item")
        if item.lower() == needle or needle in item.lower():
            match = r
            break
    if match is None:
        return False, f"no row matching item {row!r}", None
    item = _row_get(match, cols, "Item")
    old = match.get(status_col, "")
    detail = {
        "item": item,
        "previous_status": old,
        "proposed_status": new_status,
        "receipt_url": receipt_url.strip() if receipt_url else None,
    }
    return True, "ok", detail


def format_check_summary(errors: list[str], warns: list[str]) -> str:
    lines = [
        f"deadline-guard: {len(errors)} error(s), {len(warns)} warning(s)",
    ]
    for w in warns:
        lines.append(f"WARN  {w}")
    for e in errors:
        lines.append(f"ERROR {e}")
    return "\n".join(lines)
