#!/usr/bin/env python3
"""Έλεγχος άρθρων πριν το build. Αποτυγχάνει (exit 1) σε σφάλματα.
Χρήση: validate.py [--private-sources slug1,slug2|all-published] [αρχεία/φάκελοι...]
--private-sources: (μόνο τοπικά) απαιτεί /workspace/tekmirio-private/sources/<slug>.json με >=2 πηγές."""
import sys, re, glob, json, yaml, datetime, unicodedata, os
PRIV = os.environ.get("TEKMIRIO_PRIVATE", "/workspace/tekmirio-private")
args = sys.argv[1:]; need_priv = None
if "--private-sources" in args:
    i = args.index("--private-sources"); need_priv = args[i+1]; del args[i:i+2]
from urllib.parse import urlparse

CATS = {c["key"] for c in yaml.safe_load(open("data/categories.yaml", encoding="utf-8"))}
TYPES = {t["key"] for t in yaml.safe_load(open("data/types.yaml", encoding="utf-8"))}
REQ = ["title", "slug", "date", "lastmod", "category", "article_type", "summary", "risk", "status", "draft"]
errors, warns, slugs, titles = [], [], {}, {}

def norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return re.sub(r"[^\w]+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()

files = []
for a in (args or ["content/articles"]):
    files += [a] if a.endswith(".md") else glob.glob(f"{a}/**/*.md", recursive=True)
files = sorted(set(files))
def check_private(f, slug):
    p = f"{PRIV}/sources/{slug}.json"
    try: d = json.load(open(p, encoding="utf-8"))
    except Exception as e: errors.append(f"{f}: λείπει/άκυρο ιδιωτικό αρχείο πηγών {p}: {e}"); return
    items = d.get("sources", d) if isinstance(d, dict) else d
    good = [s for s in items if isinstance(s, dict) and all(s.get(k) for k in ("title","url","publisher","accessed"))
            and urlparse(str(s["url"])).scheme in ("http","https")]
    if len(good) < 2: errors.append(f"{f}: χρειάζονται >=2 έγκυρες ιδιωτικές πηγές (title,url,publisher,accessed), βρέθηκαν {len(good)}")
for f in files:
    if f.endswith("_index.md"):
        continue
    raw = open(f, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        errors.append(f"{f}: λείπει front matter"); continue
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception as e:
        errors.append(f"{f}: μη έγκυρο YAML: {e}"); continue
    body = m.group(2).strip()
    E = lambda msg: errors.append(f"{f}: {msg}")
    for k in REQ:
        if k not in fm or fm[k] in (None, ""):
            E(f"λείπει το πεδίο '{k}'")
    if fm.get("category") not in CATS: E(f"άγνωστη κατηγορία '{fm.get('category')}'")
    if fm.get("article_type") not in TYPES: E(f"άγνωστος τύπος '{fm.get('article_type')}'")
    st = fm.get("status")
    if st not in ("draft", "published"): E("status πρέπει draft|published")
    if (st == "draft") != bool(fm.get("draft")): E("status και draft δεν συμφωνούν")
    if fm.get("risk") not in ("low", "medium", "high"): E("risk πρέπει low|medium|high")
    if fm.get("risk") == "high" and st == "published" and fm.get("approved_by_owner") is not True: E("άρθρο υψηλού κινδύνου δεν δημοσιεύεται χωρίς έγκριση (risk: high)")
    for k in ("date", "lastmod"):
        v = fm.get(k)
        if isinstance(v, str):
            try: v = fm[k] = datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError: pass
        if not isinstance(v, datetime.datetime) or v.tzinfo is None: E(f"'{k}' χρειάζεται πλήρη ημερομηνία με ζώνη ώρας, π.χ. 2026-11-03T09:00:00+02:00")
    if isinstance(fm.get("date"), datetime.datetime) and isinstance(fm.get("lastmod"), datetime.datetime):
        try:
            if fm["lastmod"] < fm["date"]: E("lastmod πριν από date")
        except TypeError: pass
    slug = str(fm.get("slug", ""))
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug): E("slug: μόνο λατινικά πεζά, αριθμοί, παύλες")
    if slug in slugs: E(f"διπλότυπο slug με {slugs[slug]}")
    slugs[slug] = f
    nt = norm(fm.get("title", ""))
    if nt in titles: E(f"διπλότυπος τίτλος με {titles[nt]}")
    titles[nt] = f
    if "sources" in fm: E("το πεδίο 'sources' δεν επιτρέπεται (το αποθετήριο είναι δημόσιο· οι πηγές μένουν στο ιδιωτικό αρχείο)")
    if need_priv and (need_priv == "all-published" and st == "published" or slug in need_priv.split(",")): check_private(f, slug)
    if st == "published" and len(body) < 600: E("πολύ σύντομο κείμενο (<600 χαρακτήρες)")
    if fm.get("image") and (not fm.get("image_alt") or not fm.get("image_credit")):
        E("εικόνα χωρίς image_alt ή image_credit (απαιτείται περιγραφή και πίστωση/άδεια)")
    if len(str(fm.get("summary", ""))) > 300: E("summary > 300 χαρακτήρες")
    if re.search(r"(ghp_|github_pat_)[A-Za-z0-9_]{20,}", raw): E("ΠΙΘΑΝΟ ΜΥΣΤΙΚΟ ΣΤΟ ΚΕΙΜΕΝΟ")

# Σύγκριση με data/published-index.json (αποφυγή επαναδημοσίευσης)
try:
    json.load(open("data/published-index.json", encoding="utf-8"))
except Exception as e:
    errors.append(f"data/published-index.json: {e}")

for w in warns: print("ΠΡΟΕΙΔΟΠΟΙΗΣΗ:", w)
for e in errors: print("ΣΦΑΛΜΑ:", e)
print(f"Ελέγχθηκαν {len([f for f in files if not f.endswith('_index.md')])} άρθρα · {len(errors)} σφάλματα · {len(warns)} προειδοποιήσεις")
sys.exit(1 if errors else 0)
