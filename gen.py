#!/usr/bin/env python3
"""Append one check (two surfaces), regenerate status.json. Keeps 90 days."""
import json, sys, os
from datetime import datetime, timedelta, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(DIR, "checks.jsonl")

TARGETS = {
    "portal": {"name": "portal login", "url": "https://isipr.net/AIM/Login.aspx"},
    "uptime": {"name": "UP-Time portal", "url": "https://portal.isipr.net/"},
}

ts = sys.argv[1]
vals = sys.argv[2:]  # p_up p_code p_ms u_up u_code u_ms
p_up, p_code, p_ms = vals[0] == "true", int(vals[1]), int(vals[2])
u_up, u_code, u_ms = vals[3] == "true", int(vals[4]), int(vals[5])

entry = {
    "t": ts, "up": p_up, "code": p_code, "ms": p_ms,  # top-level = primary surface
    "targets": {
        "portal": {"up": p_up, "code": p_code, "ms": p_ms},
        "uptime": {"up": u_up, "code": u_code, "ms": u_ms},
    },
}

checks = []
if os.path.exists(LOG):
    with open(LOG) as f:
        checks = [json.loads(l) for l in f if l.strip()]
checks.append(entry)
checks = checks[-9000:]  # 90 days at 15-min cadence
with open(LOG, "w") as f:
    for c in checks:
        f.write(json.dumps(c) + "\n")

def uptime(hours, key=None):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    window = [c for c in checks if c["t"] >= cutoff]
    if key:
        window = [c for c in window if "targets" in c and key in c["targets"]]
        vals = [c["targets"][key]["up"] for c in window]
    else:
        vals = [c["up"] for c in window]
    if not vals:
        return None
    return round(100.0 * sum(1 for v in vals if v) / len(vals), 2)

def target_status(key):
    t = entry["targets"][key]
    info = TARGETS[key]
    return {
        "name": info["name"], "url": info["url"],
        "status": "up" if t["up"] else "down",
        "http_code": t["code"], "response_ms": t["ms"],
        "uptime_24h": uptime(24, key), "uptime_7d": uptime(7 * 24, key),
        "uptime_30d": uptime(30 * 24, key), "uptime_90d": uptime(90 * 24, key),
    }

status = {
    "name": "isiNET",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "current": {"status": "up" if p_up else "down", "checked_at": ts,
                "http_code": p_code, "response_ms": p_ms},
    "targets": {k: target_status(k) for k in TARGETS},
    "uptime_24h": uptime(24),
    "uptime_7d": uptime(7 * 24),
    "uptime_30d": uptime(30 * 24),
    "uptime_90d": uptime(90 * 24),
    "total_checks": len(checks),
    "recent": checks[-60:][::-1],
}
with open(os.path.join(DIR, "status.json"), "w") as f:
    json.dump(status, f, indent=2)
