# Install and verify (clean checkout)

Use this when you only have the **public** plugin tree (for example `git clone` of `Snedz/hermes-deadline-guard`) or a copy exported from the kitchen staging folder. Requires **Python 3.11+** and **no pip packages**.

## Quick verify (one command)

From the plugin root (directory containing `plugin.yaml`):

```bash
python3 install_smoke.py
```

Expect: `install_smoke: ok (...)` and exit code **0**. This copies the public file set into a temp directory, runs unit tests, `manifest_lint`, and the golden `demo_cli.py --json` path.

Machine-readable output:

```bash
python3 install_smoke.py --json
```

## Manual steps (same as CI)

```bash
python3 -m unittest discover -s tests -v
python3 demo_cli.py
python3 manifest_lint.py
python3 catalog_lint.py            # skips with exit 0 on public clone (no plugin-catalog/)
python3 export_public.py --check   # forbidden kitchen strings + public doc link scan
```

## Hermes plugin install

When the [Hermes Agent](https://github.com/NousResearch/hermes-agent) CLI is installed:

```bash
hermes plugins install /path/to/deadline-guard
hermes plugins validate /path/to/deadline-guard --install-deps
```

### Config: `deadlines_path`

In Hermes plugin config, set the markdown table path (local read only):

```yaml
deadlines_path: examples/hackathon-deadlines.md
```

Paths are resolved relative to the plugin directory unless absolute. If the file is missing, tools return `ok: false` with a message to fix `deadlines_path` or pass `path` on the tool call.

Empty or whitespace `deadlines_path` in config falls back to `examples/hackathon-deadlines.md`.

## Walkthrough

Step-by-step demo replay: **[DEMO.md](./DEMO.md)**.
