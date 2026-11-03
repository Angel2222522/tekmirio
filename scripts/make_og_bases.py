#!/usr/bin/env python3
"""Φόντα 1200x630 για τις εικόνες κοινοποίησης (μία ανά ενότητα + γενική). Ο τίτλος μπαίνει από το Hugo στο build.
Τρέξτε ξανά μόνο αν αλλάξουν ενότητες/χρώματα: python3 scripts/make_og_bases.py"""
import yaml, unicodedata
from PIL import Image, ImageDraw, ImageFont
W, H, BG, INK = 1200, 630, "#15171b", "#eceef2"
F = "assets/fonts/NotoSans-Bold.ttf"; FS = "assets/fonts/NotoSerif-Bold.ttf"
def base(name, color, out):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 14], fill=color)                     # λωρίδα ενότητας
    d.rectangle([0, 14, 16, H], fill=color)                     # αριστερή λωρίδα
    if name:
        f = ImageFont.truetype(F, 30); t = "".join(c for c in unicodedata.normalize("NFD", name.upper()) if unicodedata.category(c) != "Mn")
        tw = d.textlength(t, font=f)
        d.rectangle([72, 52, 72 + tw + 36, 100], fill=color)
        d.text((90, 76), t, font=f, fill="#ffffff", anchor="lm")
    d.line([72, 540, W - 72, 540], fill="#3a3d44", width=2)
    d.rectangle([72, 562, 116, 606], fill="#b3261e")
    d.text((94, 584), "Τ", font=ImageFont.truetype(FS, 32), fill="#ffffff", anchor="mm")
    d.text((132, 584), "Τεκμήριο", font=ImageFont.truetype(FS, 32), fill=INK, anchor="lm")
    d.text((W - 72, 584), "angel2222522.github.io/tekmirio", font=ImageFont.truetype(F, 22), fill="#9a9ea8", anchor="rm")
    im.save(out, optimize=True)
for c in yaml.safe_load(open("data/categories.yaml", encoding="utf-8")):
    base(c["name"], c["color"], f"assets/og/base-{c['key']}.png")
base("", "#b3261e", "assets/og/base-default.png")
print("ok")
