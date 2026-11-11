# deadline-guard (Hermes plugin)

Hermes plugin for **markdown deadline tables**: scan for ERROR/WARN conditions, list upcoming founder-only steps, and **block “submitted” status without an http(s) receipt link**.

Built for the [Nous Hermes Agent Plugin Hackathon](https://x.com/NousResearch/status/2118094256438936062). Public MIT source: [`Snedz/hermes-deadline-guard`](https://github.com/Snedz/hermes-deadline-guard).

## Disclosure

- **Local file read only** — reads the markdown path you configure (`deadlines_path`). No network calls, no shell, no secrets.
- **Default demo data** — `examples/hackathon-deadlines.md` uses fictional rows only.
- **Does not edit your table by default** — `propose_status_update` validates; you apply changes in git or your editor.
- **Cron** — optional daily script writes under `$HERMES_HOME/scripts/` when you use `deadline_guard_cron` action `install`.

## Install (Hermes)

**[INSTALL.md](./INSTALL.md)** — clean checkout verify (`python3 install_smoke.py`), config, and Hermes install.

```bash
hermes plugins install /path/to/hermes-deadline-guard
hermes plugins validate /path/to/hermes-deadline-guard --install-deps
```

Set `deadlines_path` in plugin config to your table (absolute path or relative to the plugin directory). Empty config falls back to `examples/hackathon-deadlines.md`; missing files return a clear `deadlines_path` hint in tool JSON.

## Tools

| Tool | Purpose |
|---|---|
| `check_deadlines` | ERROR/WARN scan (missing owner, past due, founder step due ≤3 days, etc.) |
| `next_founder_steps` | Rows with founder-step-by inside `within_hours` (default 48) |
| `propose_status_update` | Validates status; requires receipt URL for submit-like statuses |
| `deadline_guard_cron` | `run` — summary now; `install` — stdlib script for `hermes cron --script` |

## Demo (judges)

**[INSTALL.md](./INSTALL.md)** — one-command verify. Step-by-step replay: **[DEMO.md](./DEMO.md)**. Kitchen **&lt;90 s video:** see **DEMO_VIDEO.md** and `bash demo/run_demo.sh` (not in the public export).

```bash
python3 install_smoke.py
python3 -m unittest discover -s tests -v
python3 demo_cli.py
```

Kitchen staging adds `python3 judge_path.py` (includes `sync_lint`); see **JUDGE.md** (not shipped in the public export).

## Tests (stdlib unittest)

From the plugin root (directory containing `plugin.yaml`):

```bash
python3 -m unittest discover -s tests -v
python3 manifest_lint.py
python3 catalog_lint.py    # kitchen catalog YAML; skips with exit 0 on public clone (no plugin-catalog/)
python3 sync_lint.py       # plugin.yaml version/tools must match catalog draft
python3 export_public.py --check   # forbidden kitchen strings + public doc link scan
```

## Table format

First markdown table in the file, with columns: Item, Owner, Deadline ET, Build window, Planned build blocks, Founder-only step, Founder step by, Link, Status.

## Publish (maintainers)

Before tagging a public release, confirm the export manifest is clean:

```bash
python3 export_public.py --json > /tmp/deadline-guard-manifest.json
python3 export_public.py --check
```

Copy every path listed in the manifest, run `hermes plugins validate . --install-deps`, tag, then pin the tag SHA in the Hermes plugin catalog (kitchen staging holds `plugin-catalog/deadline-guard.yaml`).

## License

MIT — see [LICENSE](./LICENSE).
