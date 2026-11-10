# deadline-guard verify, on Otari

`deadline-guard` already checks a markdown deadline table for missing owners, past-due rows and founder steps.
What it could not do was notice that **the official page changed**. A deadline that moves six hours earlier or a
sprint that slips two weeks stays wrong in the table until someone re-reads every page by hand.

`verify` re-reads each open row's official page through the **Otari** gateway and flags rows whose deadline moved,
closed, or can't be confirmed.

```
!! MOVED      Mozilla Otari: Devs Wilding Online
     table: Wed 2026-11-11 5:59 PM | page: Wed 2026-11-11 11:59 AM ET
     why:   page is 6 h EARLIER than the table
     quote: "Deadline 2026/11/11 16:59"
```
<sub>Real output from Tue 2026-11-10, model through a self-hosted Otari gateway with the page fetched locally. Full log: docs/verify-run-2026-11-10.md.</sub>

## How it uses Otari

| Otari feature | Used for |
|---|---|
| Hosted gateway, OpenAI-compatible `/api/v1/chat/completions` | one endpoint, one key (`OTARI_API_KEY`) |
| `otari_web_fetch` | Otari fetches the official page inside the request; `otari_tool_calls` is the fetch receipt |
| `otari_web_search` (optional, `--search`) | find the page when the stored link is stale |
| `otari_code_execution` (optional, `--code-exec`) | time-zone math in the sandbox, double-checked locally |
| Model fallback across open-weight models | `OTARI_MODELS=a,b,c`; every attempt is in the report |

## Honesty rule

The model never sets the verdict. It returns JSON with a **verbatim quote** and the date, time and zone *as written on
the page*. A pure local function does the time-zone math and the comparison:

- `MOVED` / `UNCHANGED`: the page states a date, and Otari's fetch receipt shows the page was read
- `CLOSED`: the page says submissions or registration closed, with a quote
- `UNVERIFIED`: no receipt, no quote, quote not on the page, gateway error, or no date stated. **Never a guess.**

## Run

```bash
export OTARI_API_KEY=tk-...                      # from otari.ai → API keys (never commit it)
export OTARI_MODELS=<open-weight model ids, comma-separated, in fallback order>
python3 verify_cli.py --deadlines examples/real-rows-2026-11-10.md --json-out verify-report.json
```

`OTARI_BASE_URL` defaults to `https://api.otari.ai/api/v1`. A self-hosted gateway works the same:
`--base-url http://localhost:8000/api/v1`.

Dev only: `--local-fetch` fetches pages on your machine and uses the gateway just for the model. Reports made that
way say `via: local (not Otari)`.

Exit code is 1 when any row MOVED or CLOSED, so it can run in cron or CI and fail loudly.

## Tests

```bash
python3 -m unittest discover -s tests -v      # verify tests: time-zone math (AoE, UTC, JST, PT with DST, UTC+8), verdicts, receipts
```
