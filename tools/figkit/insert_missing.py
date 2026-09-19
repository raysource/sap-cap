#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Place the specs that a page forgot to reference (no `<!--FIG:key-->` marker).

    python3 tools/figkit/insert_missing.py [--check]

Some pages shipped their figkit specs but not the marker lines, so `insert.py`
reported them as unused.  This script picks, for every unused spec, the `<h2>`
section whose text best matches the spec's caption/screen labels (token overlap),
then inserts the figure at the end of that section.  Deterministic: it sorts and
breaks ties by section index, never re-uses a section twice, and prints the
placement it chose so a human can re-order afterwards if needed.
"""
import glob
import json
import os
import re
import sys
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPECD = os.path.join(ROOT, "tools", "figkit", "spec.d")
FIGDIR = os.path.join(ROOT, "assets", "fig")
MARK = re.compile(r"<!--FIG:([A-Za-z0-9_\-]+)-->")
DONE = re.compile(r'<figure class="fig" data-fig="[^"]+">.*?</figure>\n?', re.S)
H2 = re.compile(r'<h2\b[^>]*>.*?</h2>', re.S)
CJK_STOP = set("的了是在和与对为不用把被这那有也就可以及以从对上下中前后时与或则")


def tokens(text):
    text = re.sub(r"<[^>]+>", " ", text)
    out = set()
    for w in re.findall(r"[A-Za-z_@][A-Za-z0-9_.$/?\-]{2,}", text):
        out.add(w.lower())
    for s in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        for i in range(len(s) - 1):
            big = s[i:i + 2]
            if not (big[0] in CJK_STOP and big[1] in CJK_STOP):
                out.add(big)
    return out


def figure(key, spec, n):
    cap = escape(spec.get("caption") or key)
    alt = escape(spec.get("alt") or spec.get("caption") or key)
    label = spec.get("label", "高保真重绘")
    kindcls = " real" if ("实测" in label or "实机" in label) else ""
    src = escape(spec.get("src", "本站自绘（figkit 高保真画面）"))
    w, h = spec.get("w", 1440), spec.get("h", 900)
    return (f'<figure class="fig" data-fig="{key}">\n'
            f'  <a class="zoom" href="assets/fig/{key}.svg" target="_blank" '
            f'title="点击在新标签打开原图"><img src="assets/fig/{key}.svg" alt="{alt}" '
            f'width="{w}" height="{h}" loading="lazy"></a>\n'
            f'  <figcaption><span class="n">画面 {n}</span><span class="cap">{cap}</span>'
            f'<span class="kind{kindcls}">{escape(label)}</span>'
            f'<span class="src">{src}</span></figcaption>\n'
            f'</figure>')


def main(check=False):
    specs = {os.path.basename(p)[:-5]: json.load(open(p, encoding="utf-8"))
             for p in glob.glob(os.path.join(SPECD, "*.json"))}
    used = set()
    pages = []
    for path in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        src = open(path, encoding="utf-8").read()
        used |= set(MARK.findall(src)) | set(re.findall(r'data-fig="([^"]+)"', src))
        pages.append((path, src))
    orphans = sorted(set(specs) - used)
    if not orphans:
        print("no orphan specs")
        return 0

    PREFIX_PAGE = {"bas": "bas", "btp": "btp", "cds": "cds", "con": "concept",
                   "concept": "concept", "dep": "deploy", "deploy": "deploy",
                   "fiori": "fiori", "hana": "hana", "node": "node", "sec": "security",
                   "test": "testing", "cli": "cli", "java": "java", "prj": "project",
                   "project": "project", "ws": "worksheet", "quiz": "quiz"}

    changed = 0
    for path, src in pages:
        page = os.path.basename(path)
        prefix = page[:-5]
        mine = [k for k in orphans if PREFIX_PAGE.get(k.split("_")[0]) == prefix]
        if not mine:
            continue
        clean = src          # 注意：这里绝不能 strip 已插入的 figure（会误删页面上的画面）
        heads = list(H2.finditer(clean))
        if not heads:
            print(f"SKIP {page}: no <h2> to anchor to")
            continue
        sections = []
        for i, m in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(clean)
            sections.append([i, m.start(), end, tokens(clean[m.start():end]), None])
        existing = clean.count('class="fig"')
        pending = []
        for key in mine:
            spec = specs[key]
            want = tokens((spec.get("caption") or "") + " " + " ".join(
                str(x) for x in (spec.get("blocks") or [])) + " " + key)
            best, best_score = None, 0
            for sec in sections:
                if sec[4] is not None:
                    continue
                score = len(want & sec[3])
                if score > best_score:
                    best, best_score = sec, score
            if best is None:
                best = next((s for s in sections if s[4] is None), None)
            if best is None:
                print(f"SKIP {key}: no free section left in {page}")
                continue
            best[4] = key
            n = existing + 1
            existing += 1
            pending.append((best[2], figure(key, spec, n)))
            print(f"put  {key:12s} -> {page}  画面 {n}  (section score matches={best_score})")
        for offset, html in sorted(pending, key=lambda x: -x[0]):     # 倒序插入，偏移才不会失效
            clean = clean[:offset] + "\n" + html + clean[offset:]
        if clean != src:
            if not check:
                open(path, "w", encoding="utf-8").write(clean)
            changed += 1
    return 0


if __name__ == "__main__":
    sys.exit(main(check="--check" in sys.argv[1:]))
