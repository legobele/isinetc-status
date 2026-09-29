#!/usr/bin/env python3
"""Append one check (two surfaces), regenerate status.json. Keeps 90 days."""
import json, sys, os
from datetime import datetime, timedelta, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(DIR, "checks.jsonl")

TARGETS = {
    "portal": {"name": "portal login", "url": "https://isipr.net/AIM/Login.aspx"},
    "uptime": {"name": "UP-Time portal", "url": "https://portal.isipr.net/"},
    "site": {"name": "main site redirect", "url": "https://isipr.net/"},
    "isinetapp": {"name": "isinet.app", "url": "https://isinet.app/"},
}

ts = sys.argv[1]
vals = sys.argv[2:]  # p_* u_* s_* a_* (3 values each)
p_up, p_code, p_ms = vals[0] == "true", int(vals[1]), int(vals[2])
u_up, u_code, u_ms = vals[3] == "true", int(vals[4]), int(vals[5])
s_up, s_code, s_ms = vals[6] == "true", int(vals[7]), int(vals[8])
a_up, a_code, a_ms = vals[9] == "true", int(vals[10]), int(vals[11])

entry = {
    "t": ts, "up": p_up, "code": p_code, "ms": p_ms,  # top-level = primary surface
    "targets": {
        "portal": {"up": p_up, "code": p_code, "ms": p_ms},
        "uptime": {"up": u_up, "code": u_code, "ms": u_ms},
        "site": {"up": s_up, "code": s_code, "ms": s_ms},
        "isinetapp": {"up": a_up, "code": a_code, "ms": a_ms},
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

# Daily rollup per surface, last 90 days (for the bar strips).
per_day = {k: {} for k in TARGETS}
for c in checks:
    d = c["t"][:10]
    tg = c.get("targets") or {}
    ups = {}
    if tg:
        for k in TARGETS:
            if k in tg:
                ups[k] = tg[k]["up"]
    else:  # legacy entries predate per-target tracking → primary surface
        ups["portal"] = c["up"]
    for k, u in ups.items():
        acc = per_day[k].setdefault(d, [0, 0])
        acc[1] += 1
        if u:
            acc[0] += 1
today = datetime.now(timezone.utc).date()
day_list = [(today - timedelta(days=i)).isoformat() for i in range(89, -1, -1)]
daily = {}
for k in TARGETS:
    rows = []
    for d in day_list:
        if d in per_day[k]:
            up_n, n = per_day[k][d]
            rows.append({"d": d, "uptime": round(100.0 * up_n / n, 1),
                         "down_min": (n - up_n) * 15})
        else:
            rows.append({"d": d, "uptime": None, "down_min": 0})
    daily[k] = rows

# Incident detection: walk the log per target, open on up->down, close on down->up.
# Backfills history automatically, including targets added later (their incident
# opens at the first observed down check, not before).
def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

incidents = []
open_inc = {}
prev_state = {}
for c in checks:
    tg = c.get("targets") or {"portal": {"up": c["up"]}}
    for k in TARGETS:
        if k not in tg:
            continue
        up = tg[k]["up"]
        was = prev_state.get(k)
        if up is False and k not in open_inc and was is not False:
            # down, and previous state was up (transition) or unknown (first observation)
            open_inc[k] = {"target": k, "started_at": c["t"], "down_checks": 1}
        elif up is False and k in open_inc:
            open_inc[k]["down_checks"] += 1
        elif up is True and k in open_inc:
            inc = open_inc.pop(k)
            inc["ended_at"] = c["t"]
            incidents.append(inc)
        prev_state[k] = up
for k, inc in open_inc.items():
    inc["ended_at"] = None
    incidents.append(inc)
for inc in incidents:
    inc["target_name"] = TARGETS[inc["target"]]["name"]
    inc["url"] = TARGETS[inc["target"]]["url"]
    if inc["ended_at"]:
        mins = int((parse_ts(inc["ended_at"]) - parse_ts(inc["started_at"])).total_seconds() // 60)
        inc["duration_min"] = max(mins, 15)
    else:
        inc["duration_min"] = None
ongoing = sorted([i for i in incidents if i["ended_at"] is None],
                 key=lambda i: i["started_at"])
resolved = sorted([i for i in incidents if i["ended_at"] is not None],
                  key=lambda i: i["started_at"], reverse=True)
incidents = (ongoing + resolved)[:30]

status = {
    "name": "isiNET",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "current": {"status": "up" if p_up else "down", "checked_at": ts,
                "http_code": p_code, "response_ms": p_ms},
    "targets": {k: target_status(k) for k in TARGETS},
    "daily": daily,
    "incidents": incidents,
    "uptime_24h": uptime(24),
    "uptime_7d": uptime(7 * 24),
    "uptime_30d": uptime(30 * 24),
    "uptime_90d": uptime(90 * 24),
    "total_checks": len(checks),
    "recent": checks[-60:][::-1],
}
with open(os.path.join(DIR, "status.json"), "w") as f:
    json.dump(status, f, indent=2)
