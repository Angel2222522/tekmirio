#!/usr/bin/env python3
"""Ενημερώνει το data/published-index.json (slug, τίτλος, ημερομηνία) για έλεγχο διπλοτύπων."""
import glob, re, json, yaml
out = []
for f in sorted(glob.glob("content/articles/**/*.md", recursive=True)):
    if f.endswith("_index.md"): continue
    m = re.match(r"^---\n(.*?)\n---\n", open(f, encoding="utf-8").read(), re.S)
    fm = yaml.safe_load(m.group(1))
    if fm.get("status") != "published": continue
    out.append({"slug": fm["slug"], "title": fm["title"], "date": str(fm["date"]), "category": fm["category"], "file": f})
out.sort(key=lambda a: a["date"], reverse=True)
json.dump({"articles": out}, open("data/published-index.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(out)} δημοσιευμένα άρθρα στο ευρετήριο")
