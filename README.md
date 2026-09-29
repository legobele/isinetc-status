# isiNET status

Public uptime monitor for [isiNET](https://isipr.net) (Internet Society of Puerto Rico's school network — the thing your school internet runs on).

**Live page:** https://legobele.github.io/isinetc-status/

## What it monitors

Two surfaces, checked every 15 minutes:

| Target | URL | Check |
|---|---|---|
| `portal` (primary) | `https://isipr.net/AIM/Login.aspx` | HTTP 200 + page contains "password" |
| `uptime` | `https://portal.isipr.net/` | HTTP 200 + page contains "UP-Time" |
| `site` | `https://isipr.net/` | HTTP 200 + stub page redirects to isinet.app |
| `isinetapp` | `https://isinet.app/` | HTTP 200 (the new domain — its HTTPS was broken as of 2026-09-29) |

The banner reads "All Systems Operational" only when every target is up; the
`FLIP:up` / `FLIP:down` notification tracks the primary surface (`portal`).

## How it works

- **`check.sh`** — the probe. Hits all targets with curl (25s timeout), records up/down + HTTP code + response time, appends a line to `checks.jsonl`, regenerates `status.json` via `gen.py`, commits + pushes to GitHub. Prints `FLIP:up` / `FLIP:down` / `SAME:<status>` so the scheduler knows when the state changed.
- **`gen.py`** — takes one check's results, appends to the log, and rebuilds `status.json`: current status, per-target uptime over 24h / 7d / 30d / 90d, daily rollup bars for the last 90 days, the last 60 checks, and the **incident log** (derived by walking the full check history: up→down opens an incident, down→up closes it — so past outages backfill automatically).
- **`index.html`** — the static status page. Reads `status.json`, renders the headline, per-target cards, uptime stats, the 90-day bar strip, and recent incidents. Served by GitHub Pages.
- **`status.json`** — machine-readable output. `current.status` is `"up"` or `"down"`; `targets` breaks it down per surface; `daily` has per-day uptime + downtime minutes for 90 days; `recent` holds the last 60 raw checks; `incidents` holds the last 30 incidents (ongoing first), each with `started_at`, `ended_at` (null while ongoing), `duration_min`, and `down_checks`.

## Where the probe runs

**GitHub Actions** (`.github/workflows/probe.yml`) — every 15 minutes, plus manual runs via workflow_dispatch. The workflow checks out the repo, runs `check.sh`, and pushes the results back with the default `GITHUB_TOKEN`. Because `check.sh` commits and pushes itself, the repo is the entire system: history, state, and site all live there. The probe keeps recording even if nothing else is running anywhere.

## Incidents

Every down is auto-recorded. `gen.py` walks `checks.jsonl` on every run and derives the incident list from scratch, so the log is always consistent with the raw data — no separate incident store to drift. An incident opens on the first down check after an up (or the first observation, for newly added targets) and closes on the first up check after. The page shows ongoing incidents with a red badge and resolved ones with their duration.

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
