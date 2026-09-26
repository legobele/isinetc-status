#!/usr/bin/env python3
"""Append one check, regenerate status.json. Keeps last 2000 checks."""
import json, sys, os
from datetime import datetime, timedelta, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(DIR, "checks.jsonl")

ts, up, code, ms = sys.argv[1], sys.argv[2] == "true", int(sys.argv[3]), int(sys.argv[4])
entry = {"t": ts, "up": up, "code": code, "ms": ms}

checks = []
if os.path.exists(LOG):
    with open(LOG) as f:
        checks = [json.loads(l) for l in f if l.strip()]
checks.append(entry)
checks = checks[-9000:]  # 90 days at 15-min cadence
with open(LOG, "w") as f:
    for c in checks:
        f.write(json.dumps(c) + "\n")

def uptime(hours):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    window = [c for c in checks if c["t"] >= cutoff]
    if not window:
        return None
    return round(100.0 * sum(1 for c in window if c["up"]) / len(window), 2)

status = {
    "target": "https://isipr.net/AIM/Login.aspx",
    "name": "isiNET",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "current": {"status": "up" if up else "down", "checked_at": ts,
                "http_code": code, "response_ms": ms},
    "uptime_24h": uptime(24),
    "uptime_7d": uptime(7 * 24),
    "uptime_30d": uptime(30 * 24),
    "uptime_90d": uptime(90 * 24),
    "total_checks": len(checks),
    "recent": checks[-60:][::-1],
}
with open(os.path.join(DIR, "status.json"), "w") as f:
    json.dump(status, f, indent=2)
