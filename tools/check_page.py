#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static checks for one page (or all pages): run after writing a page.

    python3 tools/check_page.py btp.html
    python3 tools/check_page.py --all

Checks: tag balance, exactly one <article>/<main>, code-head has a copy-btn,
lang-* class known to main.js, quiz data-answer matches an option data-key,
internal links resolve, FIG markers have a spec, no markdown leftovers,
no stray pipe inside <td>.
"""
import os
import re
import sys
import json
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
LANGS = {"abap", "cds", "sql", "js", "java", "xml", "yaml", "bash", "text", "json", "groovy"}


class Bal(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids, self.hrefs, self.imgs = [], [], [], [], []
        self.counts = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.counts[tag] = self.counts.get(tag, 0) + 1
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        if tag == "img" and a.get("src"):
            self.imgs.append((a["src"], a.get("alt", "")))
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"line {self.getpos()[0]}: extra </{tag}>")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                unclosed = [t for t, _ in self.stack[i + 1:]]
                self.errors.append(
                    f"line {self.getpos()[0]}: </{tag}> closes over unclosed {unclosed} "
                    f"(opened line {self.stack[i][1]})")
                del self.stack[i:]
                return
        self.errors.append(f"line {self.getpos()[0]}: stray </{tag}>")


def check(path: str) -> list[str]:
    p = os.path.join(ROOT, path) if not os.path.isabs(path) else path
    src = open(p, encoding="utf-8").read()
    errs = []
    b = Bal()
    b.feed(src)
    errs += b.errors
    if b.stack:
        errs.append(f"unclosed tags at EOF: {[t for t, _ in b.stack]}")
    for tag, want in (("article", 1), ("main", 1), ("header", 1), ("footer", 1)):
        if b.counts.get(tag, 0) != want:
            errs.append(f"expected exactly {want} <{tag}>, found {b.counts.get(tag, 0)}")
    dup = {i for i in b.ids if b.ids.count(i) > 1}
    if dup:
        errs.append(f"duplicate id(s): {sorted(dup)}")
    # code blocks
    for m in re.finditer(r'<pre class="hl">(.*?)</pre>', src, re.S):
        blk = m.group(1)
        if 'class="copy-btn"' not in blk:
            errs.append(f"code block without copy-btn: {blk[:70]!r}")
        lang = re.search(r'<code class="lang-([a-z0-9]+)"', blk)
        if not lang:
            errs.append(f"code block without lang-* class: {blk[:70]!r}")
        elif lang.group(1) not in LANGS:
            errs.append(f"unknown lang-{lang.group(1)} (main.js will skip highlighting)")
    # quiz
    for m in re.finditer(r'<div class="quiz-q" data-answer="([A-D])">(.*?)</div>\s*</div>', src, re.S):
        ans, body = m.group(1), m.group(2)
        keys = re.findall(r'class="opt" data-key="([A-D])"', body)
        if ans not in keys:
            errs.append(f"quiz-q data-answer={ans} has no matching option (keys={keys})")
        if not re.search(r'<div class="explain">', src[m.start():m.start() + 4000]):
            errs.append("quiz-q without .explain")
    # figure markers
    specs = {f[:-5] for f in os.listdir(os.path.join(ROOT, "tools", "figkit", "spec.d"))
             if f.endswith(".json")}
    for m in re.finditer(r"<!--FIG:([A-Za-z0-9_\-]+)-->", src):
        if m.group(1) not in specs:
            errs.append(f"FIG marker {m.group(1)} has no spec file yet")
    # links & assets
    for href in b.hrefs:
        if href.startswith(("http", "#", "mailto:")):
            continue
        tgt = href.split("#")[0]
        if tgt and not os.path.exists(os.path.join(ROOT, tgt)):
            errs.append(f"dead internal link: {href}")
    for src_, alt in b.imgs:
        if src_.startswith("http"):
            continue
        if not os.path.exists(os.path.join(ROOT, src_)):
            if not src_.startswith("assets/fig/"):
                errs.append(f"missing image: {src_}")
        if not alt:
            errs.append(f"img without alt: {src_}")
    for bad in ("**", "⟦"):
        if bad in src:
            errs.append(f"markdown marker {bad!r} left in HTML")
    for m in re.finditer(r"<td>[^<]*\|", src):
        errs.append(f"pipe inside <td>: {m.group(0)[:50]!r}")
    return errs


def main(argv):
    if not argv or "--all" in argv:
        files = sorted(f for f in os.listdir(ROOT) if f.endswith(".html"))
    else:
        files = [a for a in argv if a.endswith(".html")]
    bad = 0
    for f in files:
        errs = check(f)
        if errs:
            bad += 1
            print(f"FAIL {f}")
            for e in errs:
                print("     " + e)
        else:
            print(f"PASS {f}")
    print(f"\n{len(files) - bad}/{len(files)} pages clean")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
