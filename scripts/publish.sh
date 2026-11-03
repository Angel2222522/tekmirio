#!/usr/bin/env bash
# Έλεγχος, commit, push και επιβεβαίωση δημοσίευσης. / Validate, commit, push, verify live.
# Χρήση: scripts/publish.sh ["μήνυμα commit"]   (DRY_RUN=1: χωρίς commit/push)
set -uo pipefail
cd "$(dirname "$0")/.."
export TZ=Europe/Athens
REPO_URL="https://github.com/Angel2222522/tekmirio.git"
SITE_URL="https://angel2222522.github.io/tekmirio"
BASE_PATH="/tekmirio/"
TOKEN_FILE="/home/box/.secrets/tekmirio_token"
MSG="${1:-Ενημέρωση περιεχομένου $(date '+%Y-%m-%d %H:%M')}"
LOG_DIR="logs/$(date +%Y)/$(date +%m)"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$(date +%Y-%m-%d-%H%M)-publish.md"
log(){ echo "$*"; echo "- $(date '+%H:%M:%S') $*" >> "$LOG"; }
fail(){ log "ΑΠΟΤΥΧΙΑ / FAILURE: $*"; echo "STATUS: FAILED" >> "$LOG"; exit 1; }
echo "# Εκτέλεση δημοσίευσης $(date '+%Y-%m-%d %H:%M %Z')" > "$LOG"

[ "${DRY_RUN:-}" = 1 ] || [ -r "$TOKEN_FILE" ] || fail "Δεν βρέθηκε το token ($TOKEN_FILE) / token file missing"
if [ "${DRY_RUN:-}" != 1 ]; then TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"; [ -n "$TOKEN" ] || fail "Κενό token / empty token"; fi

python3 scripts/normalize.py >/dev/null || fail "normalize.py"
python3 scripts/update_index.py >/dev/null || fail "update_index.py"
CHANGED="$(git status --porcelain -- content/articles | awk '{print $NF}' | grep '\.md$' | xargs -r -n1 basename | sed 's/\.md$//' | paste -sd, -)"
[ -n "${PUBLISH_SLUGS:-}" ] && CHANGED="${CHANGED:+$CHANGED,}$PUBLISH_SLUGS"
python3 scripts/validate.py ${CHANGED:+--private-sources "$CHANGED"} > /tmp/tek_validate.txt 2>&1 || { cat /tmp/tek_validate.txt; fail "Ο έλεγχος άρθρων απέτυχε / validation failed"; }
log "Έλεγχος άρθρων: OK ($(tail -1 /tmp/tek_validate.txt))"
rm -rf public
hugo --gc --minify --baseURL "$SITE_URL/" > /tmp/tek_hugo.txt 2>&1 || { cat /tmp/tek_hugo.txt; fail "Hugo build απέτυχε / build failed"; }
grep -q "ERROR" /tmp/tek_hugo.txt && fail "Hugo ανέφερε σφάλματα / Hugo reported errors"
python3 scripts/check_build.py "$BASE_PATH" > /tmp/tek_check.txt 2>&1 || { cat /tmp/tek_check.txt; fail "Έλεγχος συνδέσμων απέτυχε / link check failed"; }
log "Build & έλεγχος συνδέσμων: OK"

[ "${DRY_RUN:-}" = 1 ] && { log "DRY RUN: σταματά πριν το commit/push"; echo "STATUS: DRY-RUN" >> "$LOG"; exit 0; }
git add -A
if git diff --cached --quiet; then log "Καμία αλλαγή για commit / nothing to commit"
else git -c user.name="Τεκμήριο" -c user.email="noreply@example.invalid" commit -qm "$MSG" || fail "git commit"
     log "Commit: $(git rev-parse --short HEAD) — $MSG"; fi

AUTH="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$TOKEN" | base64 -w0)"
ok=0
for i in 1 2 3; do
  if git -c http.extraheader="$AUTH" push -q "$REPO_URL" HEAD:main 2>/tmp/tek_push.txt; then ok=1; break; fi
  sed "s/$TOKEN/***/g" /tmp/tek_push.txt | tail -3 >> "$LOG"; log "Push προσπάθεια $i απέτυχε / push attempt $i failed"; sleep $((i*15))
done
unset AUTH TOKEN; rm -f /tmp/tek_push.txt
[ $ok = 1 ] || fail "Το push απέτυχε 3 φορές / push failed 3 times"
log "Push: OK ($(git rev-parse --short HEAD))"

# Νεότερο δημοσιευμένο άρθρο από το ευρετήριο
NEWEST="$(python3 -c "import json;a=json.load(open('data/published-index.json'))['articles'];print(a[0]['file'] if a else '')")"
if [ -z "$NEWEST" ]; then URL="$SITE_URL/"; else
  URL="$(python3 - "$NEWEST" <<'PY'
import sys,re,yaml
fm=yaml.safe_load(re.match(r"^---\n(.*?)\n---\n",open(sys.argv[1],encoding="utf-8").read(),re.S).group(1))
import datetime
d=fm["date"]
if isinstance(d,str): d=datetime.datetime.fromisoformat(d)
print(f"https://angel2222522.github.io/tekmirio/{d.year}/{d.month:02d}/{fm['slug']}/")
PY
)"; fi
log "Αναμονή για δημοσίευση στο / waiting for: $URL"
for i in $(seq 1 30); do
  code="$(curl -s -o /dev/null -w '%{http_code}' -H 'Cache-Control: no-cache' "$URL?v=$(date +%s)")"
  [ "$code" = 200 ] && { log "Ζωντανό / LIVE (HTTP 200) μετά από ~$((i*10))s"; echo "STATUS: OK" >> "$LOG"; exit 0; }
  sleep 10
done
fail "Το άρθρο δεν εμφανίστηκε σε 5 λεπτά (τελευταίο HTTP $code). Ελέγξτε GitHub Actions / not live after 5 min, check Actions"
