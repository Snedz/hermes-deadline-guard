# deadline-guard

Use **check_deadlines** before trusting a deadlines table. Use **next_founder_steps** to see founder-only work due in the next 48 hours. Use **propose_status_update** before marking a row submitted — it requires an `http(s)` receipt URL. For unattended daily scans, call **deadline_guard_cron** with action `run` or `install`.

Default table: `examples/hackathon-deadlines.md` (fictional demo rows). Configure `deadlines_path` in plugin settings for your own markdown file.
