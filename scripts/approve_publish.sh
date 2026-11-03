#!/usr/bin/env bash
# Έγκριση & δημοσίευση προσχεδίου από τον ιδιωτικό φάκελο.
# Χρήση: scripts/approve_publish.sh <slug> [slug2 ...]   (ένα commit/deploy· DRY_RUN=1 για δοκιμή)
set -uo pipefail
cd "$(dirname "$0")/.."
export TZ=Europe/Athens
PRIV="${TEKMIRIO_PRIVATE:-/workspace/tekmirio-private}"
[ $# -ge 1 ] || { echo "Χρήση: approve_publish.sh <slug> [slug2 ...]"; exit 1; }
DESTS=(); TITLES=()
cleanup(){ for d in "${DESTS[@]}"; do git ls-files --error-unmatch "$d" >/dev/null 2>&1 || rm -f "$d"; done; python3 scripts/update_index.py >/dev/null; }
for SLUG in "$@"; do
SRC="$PRIV/drafts/$SLUG.md"
[ -f "$SRC" ] || { echo "Δεν βρέθηκε προσχέδιο: $SRC"; cleanup; exit 1; }
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
fm["date"] = d.isoformat(); lm = fm.get("lastmod")
if isinstance(lm, str): lm = datetime.datetime.fromisoformat(lm)
if not isinstance(lm, datetime.datetime) or lm.tzinfo is None or lm < d or lm > now: lm = d
fm["lastmod"] = lm.isoformat(); fm["status"] = "published"; fm["draft"] = False
dest = f"content/articles/{d.year}/{slug}.md"
if os.path.exists(dest): sys.exit(f"υπάρχει ήδη: {dest}")
os.makedirs(os.path.dirname(dest), exist_ok=True)
y = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=None, width=1000)
open(dest, "w", encoding="utf-8").write(f"---\n{y}---\n{m.group(2).lstrip()}")
print(dest)
PY
)" || { echo "Αποτυχία προετοιμασίας ($SLUG): $DEST"; cleanup; exit 1; }
echo "Μεταφέρθηκε στο $DEST"; DESTS+=("$DEST")
TITLES+=("$(python3 -c "import re,yaml;print(yaml.safe_load(re.match(r'^---\n(.*?)\n---\n',open('$DEST',encoding='utf-8').read(),re.S).group(1))['title'])")")
done
SLUGS="$(IFS=,; echo "$*")"
if [ $# -eq 1 ]; then MSG="Δημοσίευση: ${TITLES[0]}"; else MSG="Δημοσίευση $# άρθρων: $SLUGS"; fi
if PUBLISH_SLUGS="$SLUGS" scripts/publish.sh "$MSG"; then
  mkdir -p "$PRIV/drafts/published"
  if [ "${DRY_RUN:-}" = 1 ]; then cleanup; echo "(DRY RUN: τα αρχεία αφαιρέθηκαν)"
  else for SLUG in "$@"; do mv "$PRIV/drafts/$SLUG.md" "$PRIV/drafts/published/$SLUG.md"; done; fi
  printf 'OK: %s\n' "${TITLES[@]}"
else
  if [ "$(git log -1 --format=%s)" = "$MSG" ]; then
    echo "Αποτυχία μετά το commit· ελέγξτε το log και το GitHub Actions."
  else cleanup; echo "Η δημοσίευση απέτυχε· τα προσχέδια έμειναν στο $PRIV/drafts (τίποτα δεν δημοσιεύτηκε)."; fi
  exit 1
fi
