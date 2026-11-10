"""deadline-guard verify: re-read each open row's official page through Otari and flag
deadlines that moved, closed, or cannot be confirmed.

Flow per open row with an http(s) Link:
  1. Otari fetches the page (otari_web_fetch), optionally searches (otari_web_search)
     and converts time zones in its sandbox (otari_code_execution).
  2. The model must answer strict JSON with a verbatim quote from the page.
  3. A pure local comparator turns (table deadline, page claim) into
     UNCHANGED / MOVED / CLOSED / UNVERIFIED. The model never sets the verdict.

Honesty rule: anything we cannot back with a quote and a fetch receipt is UNVERIFIED.
Never guess a date.

Dev mode (`local_fetch=True`): the page is fetched here with urllib and pasted into the
prompt, so the flow can be tested against any OpenAI-compatible endpoint. Reports made
that way say `fetch: local (not Otari)`.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.request
from typing import Any
from zoneinfo import ZoneInfo

from parser import CLOSED, _col, parse_table

ET = ZoneInfo("America/Toronto")
SYSTEM = (
    "You check one hackathon deadline against its official page. Read the page (use the fetch tool on the URL "
    "if you have one). Answer ONLY a JSON object, no prose:\n"
    '{"deadline_text": verbatim words from the page that state the SUBMISSION deadline, or null,\n'
    ' "date": "YYYY-MM-DD" exactly as the page states it (do not convert), or null,\n'
    ' "time": "HH:MM" 24-hour exactly as the page states it (do not convert), or null if no time is stated,\n'
    ' "zone": the time zone exactly as the page writes it (e.g. "UTC", "AoE", "JST", "PT", "ET"), or null,\n'
    ' "closed": true if the page says submissions or registration are closed/ended, false if open, null if unclear,\n'
    ' "closed_text": verbatim words saying it is closed, or null,\n'
    ' "note": one short sentence}\n'
    "Never invent or convert a date. If the page does not state it, use null."
)


def _strip_html(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def local_fetch(url: str, limit: int = 30000, timeout: float = 30.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36 deadline-guard-verify/0.2",
        "accept": "text/html,application/xhtml+xml", "accept-language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = _strip_html(resp.read().decode("utf-8", "replace"))
            return {"ok": True, "http_status": resp.status, "text": text[:limit], "chars": len(text)}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__ + ": " + str(exc)[:200], "text": ""}


def parse_claim(content: str) -> dict[str, Any] | None:
    """Pull the first JSON object out of a model answer. Pure."""
    if not content:
        return None
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


_TABLE_DT = re.compile(r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{1,2}):(\d{2})\s*([AaPp][Mm]))?")


def table_deadline(value: str) -> tuple[dt.datetime | None, bool]:
    """'Wed 2026-11-11 5:59 PM' (ET) -> aware datetime, has_time. Pure."""
    m = _TABLE_DT.search(value or "")
    if not m:
        return None, False
    d = dt.date.fromisoformat(m.group(1))
    if m.group(2):
        h = int(m.group(2)) % 12 + (12 if m.group(4).lower() == "pm" else 0)
        return dt.datetime(d.year, d.month, d.day, h, int(m.group(3)), tzinfo=ET), True
    return dt.datetime(d.year, d.month, d.day, 23, 59, tzinfo=ET), False


ZONES = {"utc": 0, "gmt": 0, "z": 0, "aoe": -12, "anywhere on earth": -12, "jst": 9, "kst": 9, "sgt": 8,
         "cst (china)": 8, "ist": 5.5, "cet": 1, "cest": 2, "bst": 1, "pst": -8, "pdt": -7, "est": -5, "edt": -4,
         "cst": -6, "cdt": -5, "mst": -7, "mdt": -6}
NAMED = {"pt": "America/Los_Angeles", "pacific": "America/Los_Angeles", "pacific time": "America/Los_Angeles",
         "et": "America/Toronto", "eastern": "America/Toronto", "eastern time": "America/Toronto",
         "ct": "America/Chicago", "mt": "America/Denver"}


MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"), 1)}


def parse_page_date(value: Any, ref_year: int | None) -> tuple[dt.date | None, str]:
    """ISO, or 'December 13[, 2026]' / '13 Dec 2026'. A missing year is taken from the table row. Pure."""
    v = str(value or "").strip()
    try:
        return dt.date.fromisoformat(v[:10]), ""
    except ValueError:
        pass
    low = re.sub(r"(st|nd|rd|th)\b", "", v.lower().replace(",", " "))
    mon = next((MONTHS[m] for m in MONTHS if re.search(r"\b" + m[:3] + r"[a-z]*\b", low)), None)
    nums = [int(n) for n in re.findall(r"\b\d{1,4}\b", low)]
    day = next((n for n in nums if 1 <= n <= 31), None)
    year = next((n for n in nums if n > 1900), None)
    if mon is None or day is None:
        return None, ""
    note = ""
    if year is None:
        if ref_year is None:
            return None, ""
        year, note = ref_year, " (year not on page; taken from table)"
    try:
        return dt.date(year, mon, day), note
    except ValueError:
        return None, ""


_TIME = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?\b|\b(\d{1,2}):(\d{2})\b", re.I)


def parse_time(value: Any) -> tuple[int, int] | None:
    m = _TIME.search(str(value or ""))
    if not m:
        return None
    if m.group(3):
        h = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "p" else 0)
        return h, int(m.group(2) or 0)
    h, mi = int(m.group(4)), int(m.group(5))
    return (h, mi) if h < 24 and mi < 60 else None


def zone_in(text: str) -> str:
    low = text.lower()
    m = re.search(r"\b(?:utc|gmt)\s*[+-]\s*\d{1,2}(?::?\d{2})?", low)
    if m:
        return m.group(0).replace(" ", "")
    for z in sorted(list(ZONES) + list(NAMED), key=len, reverse=True):
        if re.search(r"\b" + re.escape(z) + r"\b", low):
            return z
    return ""


def page_deadline(claim: dict[str, Any], ref_year: int | None = None) -> tuple[dt.datetime | None, bool, str]:
    """(aware datetime, has_time, how). Time-zone math is done here, deterministically. Pure."""
    d, year_note = parse_page_date(claim.get("date"), ref_year)
    if d is None:
        return None, False, "no date"
    quote = str(claim.get("deadline_text") or "")
    hm = parse_time(claim.get("time")) or parse_time(quote)
    if hm is None:
        return dt.datetime(d.year, d.month, d.day, 23, 59, tzinfo=ET), False, "date only" + year_note
    hh, mm = hm
    z = re.sub(r"[()]", "", str(claim.get("zone") or "")).strip().lower() or zone_in(quote)
    z = re.sub(r"^(utc|gmt)\s*([+-]\d+(?::?\d{2})?)$", r"\1\2", z)
    off = re.fullmatch(r"(?:utc|gmt)([+-])(\d{1,2})(?::?(\d{2}))?", z)
    if off:
        hours = int(off.group(2)) + int(off.group(3) or 0) / 60
        tz = dt.timezone(dt.timedelta(hours=hours if off.group(1) == "+" else -hours))
    elif z in ZONES:
        tz = dt.timezone(dt.timedelta(hours=ZONES[z]))
    elif z in NAMED:
        tz = ZoneInfo(NAMED[z])
    else:
        return None, True, "zone not recognised: " + repr(claim.get("zone"))
    return dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz), True, "zone " + z + year_note


def parse_utc(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        t = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def compare(table_value: str, claim: dict[str, Any] | None, page_text: str | None,
            fetch_receipt: bool, tolerance_min: int = 5, now: dt.datetime | None = None) -> dict[str, Any]:
    """Pure verdict. The model's JSON is evidence, not the verdict."""
    if claim is None:
        return {"verdict": "UNVERIFIED", "why": "model gave no parseable JSON"}
    if not fetch_receipt:
        return {"verdict": "UNVERIFIED", "why": "no fetch receipt for the official page"}
    quote = claim.get("deadline_text")
    quote_ok = None
    if page_text is not None and quote:
        quote_ok = _norm(quote) in _norm(page_text)
        if not quote_ok:
            return {"verdict": "UNVERIFIED", "why": "quote not found verbatim on the fetched page", "quote": quote}
    ours, has_time = table_deadline(table_value)
    theirs, page_has_time, how = page_deadline(claim, ours.year if ours else None) if claim.get("deadline_text") else (None, False, "no date")
    now = now or dt.datetime.now(dt.timezone.utc)
    closed_note = None
    if claim.get("closed") is True and claim.get("closed_text"):
        ctext = claim["closed_text"]
        if page_text is not None and _norm(ctext) not in _norm(page_text):
            return {"verdict": "UNVERIFIED", "why": "closed quote not found verbatim on the fetched page", "quote": ctext}
        if theirs is None or theirs <= now:
            return {"verdict": "CLOSED", "why": "page says closed", "quote": ctext, "quote_on_page": True if page_text else None}
        closed_note = 'page also shows "' + ctext[:80] + '" but states a future deadline; treated as page chrome'
    if theirs is None or not claim.get("deadline_text"):
        return {"verdict": "UNVERIFIED", "why": "page deadline not stated or not parseable (" + how + ")", "quote": quote}
    theirs_et = theirs.astimezone(ET)
    shown = theirs_et.strftime("%a %Y-%m-%d %-I:%M %p ET") if page_has_time else theirs.strftime("%a %Y-%m-%d") + " (no time on page)"
    out = {"page_deadline_et": shown, "quote": claim.get("deadline_text"), "quote_on_page": quote_ok, "tz_math": how}
    if closed_note:
        out["note"] = closed_note
    if ours is None:
        return dict(out, verdict="UNVERIFIED", why="table deadline has no date")
    if has_time and page_has_time:
        delta = (theirs_et - ours).total_seconds() / 60
        moved = abs(delta) > tolerance_min
    else:
        page_day = theirs_et.date() if page_has_time else theirs.date()
        delta = (page_day - ours.date()).days * 1440
        moved = page_day != ours.date()
    if not moved:
        return dict(out, verdict="UNCHANGED", why="page matches the table" + ("" if has_time and page_has_time else " (date only)"))
    direction = "EARLIER" if delta < 0 else "later"
    return dict(out, verdict="MOVED", why="page is " + _human(abs(delta)) + " " + direction + " than the table",
                minutes=int(delta))


def _human(minutes: float) -> str:
    if minutes >= 1440:
        return str(round(minutes / 1440, 1)).rstrip("0").rstrip(".") + " day(s)"
    if minutes >= 60:
        return str(round(minutes / 60, 1)).rstrip("0").rstrip(".") + " h"
    return str(int(minutes)) + " min"


def open_rows(text: str) -> list[dict[str, str]]:
    headers, rows = parse_table(text)
    item, dl, link, st = (_col(headers, n) for n in ("Item", "Deadline ET", "Link", "Status"))
    out = []
    for r in rows:
        status = (r.get(st or "", "") or "").lower().replace("*", "").strip()
        if any(status.startswith(w) for w in CLOSED):
            continue
        url = (r.get(link or "", "") or "").strip()
        out.append({"item": r.get(item or "", ""), "deadline": r.get(dl or "", ""), "link": url})
    return out


def _fetch_receipt(tool_calls: list[dict[str, Any]], url: str) -> bool:
    for c in tool_calls or []:
        blob = json.dumps(c).lower()
        if "fetch" in blob and url.split("://", 1)[-1].split("?")[0].rstrip("/").lower()[:60] in blob \
                and not any(bad in blob for bad in ('"failed"', '"status": "error"')):
            return True
    return False


def verify_row(row: dict[str, str], client: Any, *, local: bool = False, code_exec: bool = False,
               search: bool = False) -> dict[str, Any]:
    base = {"item": row["item"], "table_deadline": row["deadline"], "link": row["link"]}
    if not row["link"].startswith(("http://", "https://")):
        return dict(base, verdict="UNVERIFIED", why="no official link in the table")
    page_text = None
    user = "Official page: " + row["link"] + "\nOur table says the deadline is: " + row["deadline"] + " (America/Toronto)."
    tools: list[dict[str, Any]] = []
    if local:
        page = local_fetch(row["link"])
        if not page["ok"] or not page["text"]:
            return dict(base, verdict="UNVERIFIED", why="local fetch failed: " + str(page.get("error")), fetch="local (not Otari)")
        page_text = page["text"]
        user += "\n\nPAGE TEXT (fetched locally):\n" + page_text
    else:
        tools.append({"type": "otari_web_fetch"})
        if search:
            tools.append({"type": "otari_web_search"})
        if code_exec:
            tools.append({"type": "otari_code_execution"})
            user += "\nUse code execution to convert the page's time zone to UTC."
    res = client.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], tools=tools or None)
    base["attempts"] = res.get("attempts")
    base["fetch"] = "local (not Otari)" if local else "otari_web_fetch"
    if not res.get("ok"):
        return dict(base, verdict="UNVERIFIED", why="gateway: " + str(res.get("error")))
    base["model"] = res["model"]
    base["otari_tool_calls"] = res.get("otari_tool_calls")
    claim = parse_claim(res.get("content", ""))
    base["claim"] = claim
    if claim is None:
        base["raw_content"] = (res.get("content") or "")[:600]
    receipt = True if local else _fetch_receipt(res.get("otari_tool_calls") or [], row["link"])
    return dict(base, **compare(row["deadline"], claim, page_text, receipt))


def format_report(results: list[dict[str, Any]]) -> str:
    order = {"MOVED": 0, "CLOSED": 1, "UNVERIFIED": 2, "UNCHANGED": 3}
    lines = []
    for r in sorted(results, key=lambda x: order.get(x["verdict"], 9)):
        mark = {"MOVED": "!!", "CLOSED": "XX", "UNVERIFIED": "??", "UNCHANGED": "ok"}.get(r["verdict"], "  ")
        lines.append(mark + " " + r["verdict"].ljust(10) + " " + r["item"])
        lines.append("     table: " + r["table_deadline"] + ((" | page: " + r["page_deadline_et"]) if r.get("page_deadline_et") else ""))
        lines.append("     why:   " + r.get("why", ""))
        if r.get("quote"):
            lines.append('     quote: "' + str(r["quote"])[:160] + '"' + ("" if r.get("quote_on_page") in (None, True) else " (NOT on page)"))
        if r.get("note"):
            lines.append("     note:  " + r["note"])
        lines.append("     via:   " + str(r.get("fetch")) + (" · model " + r["model"] if r.get("model") else ""))
    return "\n".join(lines)
