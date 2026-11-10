# verify run log, Tue 2026-11-10 (America/Toronto)

## Run A: model via a self-hosted Otari gateway, pages fetched locally (dev mode)

Otari built from `mozilla-ai/otari` main, run locally on SQLite with one OpenAI-compatible provider
(open-weight models on NVIDIA's free tier). Fallback order: `gemma-4-31b-it`, then `nemotron-3-ultra-550b-a55b`.
Every request's first attempt (gemma) was refused upstream with `422 input rejected by content safety screening`
and Otari fell back to nemotron, which answered. Both attempts are in the JSON report.

```
!! MOVED      Mozilla Otari: Devs Wilding Online
     table: Wed 2026-11-11 5:59 PM | page: Wed 2026-11-11 11:59 AM ET
     why:   page is 6 h EARLIER than the table
     quote: "Deadline 2026/11/11 16:59"
     via:   local (not Otari) · model nim:nvidia/nemotron-3-ultra-550b-a55b
!! MOVED      Apart Research Agent Attribution sprint
     table: Mon 2026-11-30 6:59 AM | page: Mon 2026-12-14 6:59 AM ET
     why:   page is 14 day(s) later than the table
     quote: "Submissions close Sunday, December 13 at 11:59 PM Anywhere on Earth (AoE)."
     note:  page also shows "The submission window has closed." but states a future deadline; treated as page chrome
     via:   local (not Otari) · model nim:nvidia/nemotron-3-ultra-550b-a55b
?? UNVERIFIED RYO-CHAN Hackathon 2026
     table: Wed 2026-11-11 9:59 AM
     why:   page deadline not stated or not parseable (no date)
     via:   local (not Otari) · model nim:nvidia/nemotron-3-ultra-550b-a55b
ok UNCHANGED  Victoria VR AI Builder Hackathon
     table: Wed 2026-11-11 | page: Wed 2026-11-11 (no time on page)
     why:   page matches the table (date only)
     quote: "Submission Deadline: November 11, 2026"
     via:   local (not Otari) · model nim:nvidia/nemotron-3-ultra-550b-a55b
```

What it caught, against what our table had:
- **Mozilla Otari** moved **6 h earlier** (table 5:59 PM ET, page "2026/11/11 16:59" UTC = 11:59 AM ET).
- **Apart** moved **two weeks later** (table Nov 30, page "December 13 at 11:59 PM AoE"). The page also shows
  "The submission window has closed." in its form chrome. The verifier saw both and did not call the row closed,
  because the page states a future deadline.
- **RYO-CHAN** is a client-rendered page with only a countdown in the HTML, so the verdict is UNVERIFIED, not a guess.

## Run B: `otari_web_fetch` on the same gateway

Same gateway, with `{"type": "otari_web_fetch"}` declared. Otari ran the fetch tool for every row and reported each
attempt in `otari_tool_calls`, but every fetch came back `failed` with tag `url_invalid`: the dev machine's DNS
resolver answers with addresses in a reserved range, and Otari's SSRF guard (correctly) refuses them. No receipt
means every row was UNVERIFIED, which is the honesty rule working. The hosted gateway at otari.ai does not sit
behind that resolver. A run there is the next step.
