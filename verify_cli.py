#!/usr/bin/env python3
"""deadline-guard verify — re-check every open deadline row against its official page via Otari.

  OTARI_API_KEY=... OTARI_MODELS=<open-weight model ids, comma-separated> \
      python3 verify_cli.py --deadlines examples/real-rows-2026-11-10.md

Dev: --local-fetch fetches pages here and only uses the gateway for the model (labelled).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from otari_client import OtariClient
from verify import format_report, open_rows, verify_row


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--deadlines", default="examples/real-rows-2026-11-10.md")
    p.add_argument("--base-url", help="override OTARI_BASE_URL (default https://api.otari.ai/api/v1)")
    p.add_argument("--models", help="comma-separated fallback order (overrides OTARI_MODELS)")
    p.add_argument("--local-fetch", action="store_true", help="dev only: fetch pages locally, not through Otari")
    p.add_argument("--code-exec", action="store_true", help="also declare otari_code_execution for time-zone math")
    p.add_argument("--search", action="store_true", help="also declare otari_web_search")
    p.add_argument("--json-out", help="write the full report (receipts, attempts) here")
    p.add_argument("--only", help="substring filter on Item")
    a = p.parse_args(argv)
    client = OtariClient(base_url=a.base_url, models=[m.strip() for m in a.models.split(",")] if a.models else None)
    rows = open_rows(Path(a.deadlines).read_text())
    if a.only:
        rows = [r for r in rows if a.only.lower() in r["item"].lower()]
    results = []
    for r in rows:
        res = verify_row(r, client, local=a.local_fetch, code_exec=a.code_exec, search=a.search)
        results.append(res)
        print(res["verdict"].ljust(10) + " " + r["item"], file=sys.stderr)
    print(format_report(results))
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(results, indent=2, default=str))
    return 1 if any(r["verdict"] in ("MOVED", "CLOSED") for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
