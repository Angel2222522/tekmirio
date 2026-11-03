#!/usr/bin/env python3
"""Έλεγχος του παραγόμενου public/: εσωτερικοί σύνδεσμοι, lang, UTF-8, απαραίτητα αρχεία,
απουσία απαγορευμένων όρων και απουσία κουτιού πηγών."""
import sys, os, re, glob
from urllib.parse import urlparse, unquote, urljoin
base = sys.argv[1] if len(sys.argv) > 1 else "/"
pub = "public"; errs = []
for need in ["index.html", "index.xml", "sitemap.xml", "robots.txt", "index.json", "404.html"]:
    if not os.path.exists(os.path.join(pub, need)): errs.append(f"λείπει {need}")
for f in glob.glob(f"{pub}/**/*.html", recursive=True):
    h = open(f, encoding="utf-8").read()
    if not re.search(r'<html[^>]*lang="?el\b', h):
        # Επιτρέπεται lang=en μόνο σε αγγλικό άρθρο που συνδέεται με ελληνικό πρωτότυπο.
        if not (re.search(r'<html[^>]*lang="?en\b', h) and re.search(r'<link rel="?alternate"? hreflang="?el"? ', h)): errs.append(f"{f}: χωρίς lang=el")
    for a, b in re.findall(r'(?:href|src)=(?:"([^"]+)"|([^\s>"]+))', h):
        href = a or b
        u = urlparse(href)
        if u.scheme or href.startswith(("#", "mailto:", "//")): continue
        page = base + os.path.relpath(f, pub).replace('index.html', '')
        p = unquote(urlparse(urljoin(page, href)).path)
        if not p.startswith(base): errs.append(f"{f}: σύνδεσμος εκτός baseURL {href}"); continue
        t = os.path.join(pub, p[len(base):])
        if not (os.path.isfile(t) or os.path.isfile(os.path.join(t, "index.html"))): errs.append(f"{f}: σπασμένος σύνδεσμος {href}")
_P = lambda *x: "".join(x)
_T = [_P("τεχν","ητ[ήής]+ νοημ","οσύν"), _P(r"\b","Τ","Ν",r"\b"), _P(r"\b","A","I",r"\b"), _P("artificial"," intelligence"),
      _P(r"\b","L","LM",r"\b"), _P(r"\b","Gr","ok",r"\b"), _P("diafaneia","-tn"), r'class="?sources', r'id="?src-h', r'"citation"', _P("αυτοματοποιημένο"," συντακτικό")]
BAN = re.compile("|".join(_T), re.I)
# Άρθρα με θέμα την ΤΝ (front matter topic_ai: true → <meta name="tk-topic" content="ai">): οι γενικοί όροι επιτρέπονται
# μόνο στο ίδιο το άρθρο και στον τίτλο/περίληψή του όπου εμφανίζονται αλλού. Οι υπόλοιποι απαγορευμένοι όροι ισχύουν παντού.
BAN_STRICT = re.compile("|".join(_T[4:]), re.I)
import html as _html, json as _json
topic_urls, topic_strs = set(), set()
TOPIC = re.compile(r'<meta name="?tk-topic"? content="?ai"?>')
for f in glob.glob(f"{pub}/**/index.html", recursive=True):
    h = open(f, encoding="utf-8").read()
    if not TOPIC.search(h): continue
    topic_urls.add(base + os.path.relpath(f, pub).replace("index.html", ""))
    for k in ("og:title", "og:description"):
        mm = re.search(r'<meta property="?%s"? content=(?:"([^"]*)"|([^\s>"]+))' % k, h)
        if mm and (mm.group(1) or mm.group(2)): v = _html.unescape(mm.group(1) or mm.group(2)); topic_strs |= {v, _html.escape(v), _html.escape(v, quote=False), _json.dumps(v)[1:-1]}
def strip_topic(f, txt):
    if f.endswith(".json"):
        try: d = _json.loads(txt)
        except Exception: d = None
        if isinstance(d, list): txt = _json.dumps([x for x in d if not (isinstance(x, dict) and x.get("u") in topic_urls)], ensure_ascii=False)
    if f.endswith(".xml"):
        txt = re.sub(r"<item>.*?</item>", lambda m: "" if any(u in m.group(0) for u in topic_urls) else m.group(0), txt, flags=re.S)
    for v in sorted(topic_strs, key=len, reverse=True): txt = txt.replace(v, "")
    return txt
for f in glob.glob(f"{pub}/**/*", recursive=True):
    if not f.endswith((".html", ".xml", ".json", ".txt")) or f.startswith(f"{pub}/admin"): continue
    raw = open(f, encoding="utf-8").read()
    txt = re.sub(r"<script(?![^>]*ld\+json)[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", raw, flags=re.S)
    if f.endswith("index.html") and TOPIC.search(raw): pat = BAN_STRICT
    else: pat = BAN; txt = strip_topic(f, txt) if topic_urls else txt
    for m in set(pat.findall(txt)): errs.append(f"{f}: απαγορευμένο κείμενο '{m}'")
if os.path.exists(f"{pub}/" + _P("diafaneia","-tn")): errs.append("υπάρχει ακόμη η καταργημένη σελίδα")
for e in errs: print("ΣΦΑΛΜΑ:", e)
print(f"Έλεγχος build: {len(errs)} σφάλματα"); sys.exit(1 if errs else 0)
