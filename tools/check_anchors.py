#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anchor-level link check: every `page.html#id` must hit a real id in that page.

    python3 tools/check_anchors.py

`check_page.py` only verifies that the *file* exists; a link to a renamed or
deleted `#anchor` would still ship.  This walks every internal link with a
fragment, collects the ids of the target page, and prints the broken ones
grouped by source page.  Exit code 1 when anything is broken.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK = re.compile(r'href="([^"#]+\.html)?#([A-Za-z0-9_\-.:]+)"')
ID = re.compile(r'\bid="([^"]+)"')


def ids_of(path):
    return set(ID.findall(open(path, encoding="utf-8").read()))


def main():
    cache = {}
    broken = {}
    total = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        src = open(path, encoding="utf-8").read()
        page = os.path.basename(path)
        for m in LINK.finditer(src):
            target = m.group(1) or page
            anchor = m.group(2)
            total += 1
            tpath = os.path.join(ROOT, target)
            if not os.path.exists(tpath):
                broken.setdefault(page, []).append(f"{target}#{anchor} (目标页面不存在)")
                continue
            if target not in cache:
                cache[target] = ids_of(tpath)
            if anchor not in cache[target]:
                broken.setdefault(page, []).append(f"{target}#{anchor}")
    for page, items in broken.items():
        print(f"FAIL {page}")
        for it in sorted(set(items)):
            print(f"     -> {it}")
    print(f"\n{total} 个带锚点的内部链接，{sum(len(set(v)) for v in broken.values())} 个无效"
          f"（{len(broken)} 个页面受影响）")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
