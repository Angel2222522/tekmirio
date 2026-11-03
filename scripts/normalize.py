#!/usr/bin/env python3
"""Συγχρονίζει το τεχνικό πεδίο draft με το status (για άρθρα από το CMS). Αλλάζει μόνο τη γραμμή draft."""
import glob, re
n = 0
for f in glob.glob("content/articles/**/*.md", recursive=True):
    if f.endswith("_index.md"): continue
    raw = open(f, encoding="utf-8").read()
    m = re.match(r"^(---\n)(.*?)(\n---\n)", raw, re.S)
    if not m: continue
    fm = m.group(2)
    st = re.search(r"^status:\s*['\"]?(\w+)", fm, re.M)
    if not st: continue
    want = "false" if st.group(1) == "published" else "true"
    if re.search(r"^draft:", fm, re.M):
        new = re.sub(r"^draft:.*$", f"draft: {want}", fm, flags=re.M)
    else:
        new = fm + f"\ndraft: {want}"
    if new != fm:
        open(f, "w", encoding="utf-8").write(m.group(1) + new + m.group(3) + raw[m.end():]); n += 1
print(f"normalize: {n} αρχεία ενημερώθηκαν")
