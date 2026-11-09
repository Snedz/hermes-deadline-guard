# DEMO — deadline-guard (judge / local, no secrets)

Two paths: **A** works anywhere with Python 3.11+ (matches CI). **B** is the full Hermes plugin install on a machine that already has the Hermes CLI.

Demo table: `examples/hackathon-deadlines.md` (fictional rows only). Fixed demo date **`2026-11-06`** keeps WARN counts stable for screen capture.

## Path A — stdlib demo (recommended for quick review)

From the **plugin repository root** (directory containing `plugin.yaml`) — same checks as `install_smoke.py`:

```bash
python3 install_smoke.py
python3 -m unittest discover -s tests -v
python3 demo_cli.py
python3 demo_cli.py --json   # optional: single JSON document for scripts
```

Expected highlights on **`2026-11-06`**:

| Step | What you should see |
|---|---|
| `check_deadlines` | `error_count: 0`, `warn_count: 3` (Near Miss Row due soon; Receipt Gate spacing warn) |
| `next_founder_steps` | `count: 1`, item **Near Miss Row**, founder step **2026-11-07** |
| `propose_status_update` without URL | `"ok": false`, error about **http(s) receipt** |
| `propose_status_update` with URL | `"ok": true`, proposed status **submitted** |
| `deadline_guard_cron` run | Same summary plus **Founder steps within 48h: 1** |

Optional cron script smoke (writes under `$HERMES_HOME/scripts/` or `~/.hermes/scripts/`):

```bash
python3 cron.py --today 2026-11-06 examples/hackathon-deadlines.md
```

## Path B — Hermes plugin (when CLI is installed)

Replace `/path/to/hermes-deadline-guard` with this folder or your public clone.

```bash
cd /path/to/hermes-deadline-guard
hermes plugins install .
hermes plugins validate . --install-deps
```

In Hermes config for the plugin, set:

```yaml
deadlines_path: examples/hackathon-deadlines.md
```

In chat or tool UI, invoke (same semantics as Path A):

1. **`check_deadlines`** with optional `today: "2026-11-06"`
2. **`next_founder_steps`** with `within_hours: 48` and the same `today`
3. **`propose_status_update`** — row `Demo Plugin Alpha`, status `submitted`, no receipt → blocked; retry with `receipt_url: https://example.com/hackathon/receipt`
4. **`deadline_guard_cron`** with `action: run`

Daily unattended hook (optional):

```bash
# via tool deadline_guard_cron action install, then:
hermes cron add --name deadline-guard-daily --schedule "0 8 * * *" --script deadline_guard_daily.py
```

Or use the registered automation blueprint **Deadline Guard daily scan** if your Hermes build exposes blueprint installs.

## 90 s video beat sheet

On camera: show the markdown table, run Path A steps 1–4, end on repo name + “Hermes Plugin Hackathon”. Target **75–85 seconds**; tag **@NousResearch** on X when posting (founder step).

## What this plugin does *not* do

- No network, no shell, no secrets, no automatic writes to your deadlines file.
- Catalog PR and Typeform submit are **out of scope** for this demo doc (founder-only per hackathon rules).
