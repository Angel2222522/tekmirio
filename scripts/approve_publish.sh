#!/usr/bin/env bash
# Έγκριση & δημοσίευση προσχεδίου από τον ιδιωτικό φάκελο.
# Χρήση: scripts/approve_publish.sh <slug>      (DRY_RUN=1 για δοκιμή χωρίς commit/push)
set -uo pipefail
cd "$(dirname "$0")/.."
export TZ=Europe/Athens
PRIV="${TEKMIRIO_PRIVATE:-/workspace/tekmirio-private}"
SLUG="${1:?Χρήση: approve_publish.sh <slug>}"
SRC="$PRIV/drafts/$SLUG.md"
[ -f "$SRC" ] || { echo "Δεν βρέθηκε προσχέδιο: $SRC"; exit 1; }
DEST="$(python3 - "$SRC" "$PRIV" <<'PY'
import sys, re, yaml, datetime, json, os
src, priv = sys.argv[1], sys.argv[2]
raw = open(src, encoding="utf-8").read()
m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
if not m: sys.exit("χωρίς front matter")
fm = yaml.safe_load(m.group(1)) or {}
slug = fm.get("slug")
if slug != os.path.basename(src)[:-3]: sys.exit(f"το slug ({slug}) δεν ταιριάζει με το όνομα αρχείου")
if "sources" in fm: sys.exit("αφαιρέστε το πεδίο sources (μένει στο ιδιωτικό αρχείο)")
now = datetime.datetime.now().astimezone().replace(microsecond=0)
d = fm.get("date")
if isinstance(d, str): d = datetime.datetime.fromisoformat(d)
if not isinstance(d, datetime.datetime) or d.tzinfo is None or d > now: d = now
fm["date"] = d.isoformat(); fm["lastmod"] = max(now, d).isoformat(); fm["status"] = "published"; fm["draft"] = False
dest = f"content/articles/{d.year}/{slug}.md"
if os.path.exists(dest): sys.exit(f"υπάρχει ήδη: {dest}")
os.makedirs(os.path.dirname(dest), exist_ok=True)
y = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=None, width=1000)
open(dest, "w", encoding="utf-8").write(f"---\n{y}---\n{m.group(2).lstrip()}")
print(dest)
PY
)" || { echo "Αποτυχία προετοιμασίας: $DEST"; exit 1; }
echo "Μεταφέρθηκε στο $DEST"
TITLE="$(python3 -c "import re,yaml,sys;print(yaml.safe_load(re.match(r'^---\n(.*?)\n---\n',open('$DEST',encoding='utf-8').read(),re.S).group(1))['title'])")"
if PUBLISH_SLUGS="$SLUG" scripts/publish.sh "Δημοσίευση: $TITLE"; then
  mkdir -p "$PRIV/drafts/published"
  if [ "${DRY_RUN:-}" = 1 ]; then rm -f "$DEST"; python3 scripts/update_index.py >/dev/null; echo "(DRY RUN: το $DEST αφαιρέθηκε)"; else mv "$SRC" "$PRIV/drafts/published/$SLUG.md"; fi
  echo "OK: $TITLE"
else
  if git ls-files --error-unmatch "$DEST" >/dev/null 2>&1 && ! git diff --quiet origin/main -- "$DEST" 2>/dev/null; then
    echo "Η δημοσίευση απέτυχε ΜΕΤΑ το commit· δείτε το log."
  elif ! git ls-files --error-unmatch "$DEST" >/dev/null 2>&1; then
    rm -f "$DEST"; python3 scripts/update_index.py >/dev/null; echo "Η δημοσίευση απέτυχε· το προσχέδιο έμεινε στο $SRC (τίποτα δεν δημοσιεύτηκε)."
  else echo "Το άρθρο έγινε commit/push αλλά δεν επιβεβαιώθηκε ζωντανό· ελέγξτε το GitHub Actions."; fi
  exit 1
fi
