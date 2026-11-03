#!/usr/bin/env bash
# Ιδιωτική προεπισκόπηση προσχεδίου: τοπικό build με το προσχέδιο + στιγμιότυπα PNG (κινητό/υπολογιστής) + PDF.
# Χρήση: scripts/preview_draft.sh <slug>   → /workspace/tekmirio-private/previews/<slug>-{desktop,mobile}.png, <slug>.pdf
set -euo pipefail
cd "$(dirname "$0")/.."
PRIV="${TEKMIRIO_PRIVATE:-/workspace/tekmirio-private}"
SLUG="${1:?Χρήση: preview_draft.sh <slug>}"
SRC="$PRIV/drafts/$SLUG.md"; [ -f "$SRC" ] || { echo "Δεν βρέθηκε: $SRC"; exit 1; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/site"; for x in *; do case "$x" in public|resources) ;; *) cp -a "$x" "$TMP/site/";; esac; done; rm -f "$TMP"/site/content/articles/*/demo-*.md
mkdir -p "$TMP/site/content/articles/preview"; cp "$SRC" "$TMP/site/content/articles/preview/$SLUG.md"
# Αν το προσχέδιο έχει μετάφραση (translation: <slug>), μπαίνει κι αυτή στο build για να φαίνεται το κουμπί γλώσσας.
TR="$(sed -n '/^---$/,/^---$/{s/^translation: *//p}' "$SRC" | head -1 | tr -d '"'"'"' ')"
if [ -n "$TR" ] && [ -f "$PRIV/drafts/$TR.md" ]; then cp "$PRIV/drafts/$TR.md" "$TMP/site/content/articles/preview/$TR.md"; fi
python3 scripts/validate.py --private-sources "$SLUG" "$TMP/site/content/articles/preview/$SLUG.md" || echo "ΠΡΟΣΟΧΗ: ο έλεγχος βρήκε σφάλματα (δείτε παραπάνω)"
(cd "$TMP/site" && hugo -D --quiet --baseURL "file://$TMP/site/public/" -d public)
PAGE="$(find "$TMP/site/public" -path "*/$SLUG/index.html" | head -1)"
[ -n "$PAGE" ] || { echo "Δεν βρέθηκε η σελίδα στο build"; exit 1; }
mkdir -p "$PRIV/previews"; CH="$(command -v google-chrome || command -v chromium)"
O=(--headless=new --no-sandbox --disable-gpu --hide-scrollbars --virtual-time-budget=3000)
"$CH" "${O[@]}" --window-size=1366,4000 --screenshot="$PRIV/previews/$SLUG-desktop.png" "file://$PAGE" 2>/dev/null
"$CH" "${O[@]}" --window-size=390,6000 --screenshot="$PRIV/previews/$SLUG-mobile.png" "file://$PAGE" 2>/dev/null
"$CH" "${O[@]}" --no-pdf-header-footer --print-to-pdf="$PRIV/previews/$SLUG.pdf" "file://$PAGE" 2>/dev/null
[ -n "${KEEP_BUILD:-}" ] && { rm -rf "$KEEP_BUILD"; cp -a "$TMP/site/public" "$KEEP_BUILD"; }
ls -1 "$PRIV/previews/$SLUG"*
