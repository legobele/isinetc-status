#!/bin/bash
# isiNET uptime probe. Run every 15 min via cron.
# Appends a check to checks.jsonl, regenerates status.json, pushes to GitHub.
# Prints FLIP:up / FLIP:down / SAME:<status> for the cron wrapper.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1

URL="https://isipr.net/AIM/Login.aspx"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BODY=$(mktemp)
OUT=$(curl -s -m 25 -o "$BODY" -w "%{http_code} %{time_total}" "$URL" 2>/dev/null || echo "000 0")
CODE=$(echo "$OUT" | awk '{print $1}')
SECS=$(echo "$OUT" | awk '{print $2}')
MS=$(python3 -c "print(int(float('$SECS')*1000))" 2>/dev/null || echo 0)

UP="false"
if [ "$CODE" = "200" ] && grep -qi "password" "$BODY"; then
  UP="true"
fi
rm -f "$BODY"

PREV="unknown"
[ -f .prev_status ] && PREV=$(cat .prev_status)

python3 gen.py "$TS" "$UP" "$CODE" "$MS"

echo "$([ "$UP" = "true" ] && echo up || echo down)" > .prev_status
git add -A >/dev/null 2>&1
git commit -qm "check $TS up=$UP" >/dev/null 2>&1
git push -q origin main >/dev/null 2>&1

NOW="$([ "$UP" = "true" ] && echo up || echo down)"
if [ "$PREV" != "$NOW" ] && [ "$PREV" != "unknown" ]; then
  echo "FLIP:$NOW"
else
  echo "SAME:$NOW"
fi
