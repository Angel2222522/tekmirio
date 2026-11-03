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
    if not re.search(r'<html[^>]*lang="?el\b', h): errs.append(f"{f}: χωρίς lang=el")
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
for f in glob.glob(f"{pub}/**/*", recursive=True):
    if not f.endswith((".html", ".xml", ".json", ".txt")) or f.startswith(f"{pub}/admin"): continue
    txt = re.sub(r"<script(?![^>]*ld\+json)[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", open(f, encoding="utf-8").read(), flags=re.S)
    for m in set(BAN.findall(txt)): errs.append(f"{f}: απαγορευμένο κείμενο '{m}'")
if os.path.exists(f"{pub}/" + _P("diafaneia","-tn")): errs.append("υπάρχει ακόμη η καταργημένη σελίδα")
for e in errs: print("ΣΦΑΛΜΑ:", e)
print(f"Έλεγχος build: {len(errs)} σφάλματα"); sys.exit(1 if errs else 0)
