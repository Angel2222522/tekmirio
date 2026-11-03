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
trans = {}  # slug -> (αρχείο, translation, lang)

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
    lang = fm.get("lang", "el")
    if lang not in ("el", "en"): E("lang πρέπει el|en")
    tr = fm.get("translation")
    if tr is not None and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(tr)): E("translation: πρέπει να είναι slug άλλου άρθρου")
    if tr is not None and str(tr) == slug: E("translation δείχνει στο ίδιο άρθρο")
    if lang == "en":
        if not tr: E("αγγλικό άρθρο χωρίς 'translation' (πρέπει να συνδέεται με το ελληνικό)")
        if (fm.get("build") or {}).get("list") != "never": E("αγγλικό άρθρο: χρειάζεται 'build: {list: never}' ώστε να μη μπαίνει σε αρχική/λίστες/RSS")
    if "topic_ai" in fm and not isinstance(fm["topic_ai"], bool): E("topic_ai πρέπει true|false")
    trans[slug] = (f, str(tr) if tr else None, lang, st)
    if fm.get("image") and (not fm.get("image_alt") or not fm.get("image_credit")):
        E("εικόνα χωρίς image_alt ή image_credit (απαιτείται περιγραφή και πίστωση/άδεια)")
    if len(str(fm.get("summary", ""))) > 300: E("summary > 300 χαρακτήρες")
    if re.search(r"(ghp_|github_pat_)[A-Za-z0-9_]{20,}", raw): E("ΠΙΘΑΝΟ ΜΥΣΤΙΚΟ ΣΤΟ ΚΕΙΜΕΝΟ")

# Ζεύγη μεταφράσεων: ο σύνδεσμος πρέπει να είναι αμοιβαίος, σε διαφορετική γλώσσα, με το ελληνικό ως βάση.
def find_slug(sl):
    for g in glob.glob("content/articles/**/*.md", recursive=True) + glob.glob(f"{PRIV}/drafts/*.md"):
        mm = re.match(r"^---\n(.*?)\n---\n", open(g, encoding="utf-8").read(), re.S)
        try: y = yaml.safe_load(mm.group(1)) if mm else {}
        except Exception: continue
        if str((y or {}).get("slug")) == sl: return (g, str(y.get("translation")) if y.get("translation") else None, y.get("lang", "el"), y.get("status"))
for sl, (f, tr, lang, st) in trans.items():
    if not tr: continue
    o = trans.get(tr) or find_slug(tr)
    if not o: errors.append(f"{f}: η μετάφραση '{tr}' δεν βρέθηκε"); continue
    if o[1] != sl: errors.append(f"{f}: η μετάφραση '{tr}' δεν δείχνει πίσω σε '{sl}'")
    if o[2] == lang: errors.append(f"{f}: η μετάφραση '{tr}' έχει την ίδια γλώσσα ({lang})")
    if lang == "en" and st == "published" and o[3] != "published": errors.append(f"{f}: αγγλικό άρθρο δημοσιεύεται χωρίς δημοσιευμένο το ελληνικό '{tr}'")

# Σύγκριση με data/published-index.json (αποφυγή επαναδημοσίευσης)
try:
    json.load(open("data/published-index.json", encoding="utf-8"))
except Exception as e:
    errors.append(f"data/published-index.json: {e}")

for w in warns: print("ΠΡΟΕΙΔΟΠΟΙΗΣΗ:", w)
for e in errors: print("ΣΦΑΛΜΑ:", e)
print(f"Ελέγχθηκαν {len([f for f in files if not f.endswith('_index.md')])} άρθρα · {len(errors)} σφάλματα · {len(warns)} προειδοποιήσεις")
sys.exit(1 if errors else 0)
