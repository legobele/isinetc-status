# isiNET status

Public uptime monitor for [isiNET](https://isipr.net) (Internet Society of Puerto Rico's school network — the thing your school internet runs on).

**Live page:** https://legobele.github.io/isinetc-status/

## What it monitors

Two surfaces, checked every 15 minutes:

| Target | URL | Check |
|---|---|---|
| `portal` (primary) | `https://isipr.net/AIM/Login.aspx` | HTTP 200 + page contains "password" |
| `uptime` | `https://portal.isipr.net/` | HTTP 200 + page contains "UP-Time" |

The page's headline status follows the primary surface (`portal`).

## How it works

- **`check.sh`** — the probe. Hits both URLs with curl (25s timeout), records up/down + HTTP code + response time, appends a line to `checks.jsonl`, regenerates `status.json` via `gen.py`, commits + pushes to GitHub. Prints `FLIP:up` / `FLIP:down` / `SAME:<status>` so the scheduler knows when the state changed. Run every 15 min via cron.
- **`gen.py`** — takes one check's results, appends to the log, and rebuilds `status.json`: current status, per-target uptime over 24h / 7d / 30d / 90d, daily rollup bars for the last 90 days, and the last 60 checks. Log keeps 90 days (~9000 entries at 15-min cadence).
- **`index.html`** — the static status page. Reads `status.json`, renders the headline, per-target cards, uptime stats, and the 90-day bar strip. Served by GitHub Pages.
- **`status.json`** — machine-readable output. `current.status` is `"up"` or `"down"`; `targets` breaks it down per surface; `daily` has per-day uptime + downtime minutes for 90 days; `recent` holds the last 60 raw checks.

## Files

```
check.sh       # probe + commit/push loop (runs on cron)
gen.py         # log append + status.json regeneration
index.html     # the public status page
checks.jsonl   # raw check log (one JSON object per 15-min check)
status.json    # generated summary, consumed by index.html
.prev_status   # last known state, used for FLIP detection
```

## Uptime math

Uptime percentages are just `successful checks / total checks` in the window. Downtime minutes on the daily bars assume each failed check = 15 minutes down (the probe cadence).

## Why this exists

isiNET went down on 2026-09-29 and nobody had a straight answer on when it came back. Now there's a page.
