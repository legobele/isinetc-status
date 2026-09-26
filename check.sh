#!/bin/bash
# isiNET uptime probe — two surfaces. Run every 15 min via cron.
# Appends a check to checks.jsonl, regenerates status.json, pushes to GitHub.
# Prints FLIP:up / FLIP:down / SAME:<status> for the cron wrapper.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1

probe() { # url, content-match -> "up code ms"
  local url=$1 match=$2
  local body out code secs ms up
  body=$(mktemp)
  out=$(curl -sL -m 25 -o "$body" -w "%{http_code} %{time_total}" "$url" 2>/dev/null || echo "000 0")
  code=$(echo "$out" | awk '{print $1}')
  secs=$(echo "$out" | awk '{print $2}')
  ms=$(python3 -c "print(int(float('$secs')*1000))" 2>/dev/null || echo 0)
  up=false
  if [ "$code" = "200" ] && grep -qi "$match" "$body"; then up=true; fi
  rm -f "$body"
  echo "$up $code $ms"
}

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
read -r P_UP P_CODE P_MS <<< "$(probe "https://isipr.net/AIM/Login.aspx" "password")"
read -r U_UP U_CODE U_MS <<< "$(probe "https://portal.isipr.net/" "UP-Time")"

PREV="unknown"
[ -f .prev_status ] && PREV=$(cat .prev_status)

python3 gen.py "$TS" "$P_UP" "$P_CODE" "$P_MS" "$U_UP" "$U_CODE" "$U_MS"

echo "$([ "$P_UP" = "true" ] && echo up || echo down)" > .prev_status
git add -A >/dev/null 2>&1
git commit -qm "check $TS portal=$P_UP uptime-portal=$U_UP" >/dev/null 2>&1
git push -q origin main >/dev/null 2>&1

NOW="$([ "$P_UP" = "true" ] && echo up || echo down)"
if [ "$PREV" != "$NOW" ] && [ "$PREV" != "unknown" ]; then
  echo "FLIP:$NOW"
else
  echo "SAME:$NOW"
fi
