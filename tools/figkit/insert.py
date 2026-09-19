#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Insert figkit screens into the pages at `<!--FIG:key-->` markers.

    python3 tools/figkit/insert.py            # rewrite pages
    python3 tools/figkit/insert.py --check    # verify only (no writes)

- Every `<!--FIG:key-->` (its own line) becomes a <figure class="fig"> with the
  page-local 画面 N numbering, the caption/alt/label coming from the spec file.
- Idempotent: previously inserted figures (tagged data-fig) are stripped first.
- A marker whose key has no spec, or a spec whose SVG is missing, is a hard error.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPECD = os.path.join(ROOT, "tools", "figkit", "spec.d")
FIGDIR = os.path.join(ROOT, "assets", "fig")

MARK = re.compile(r"^[ \t]*<!--FIG:([A-Za-z0-9_\-]+)-->[ \t]*$", re.M)
DONE = re.compile(r'<figure class="fig" data-fig="[^"]+">.*?</figure>\n?', re.S)


def load_specs() -> dict:
    out = {}
    for f in sorted(os.listdir(SPECD)):
        if not f.endswith(".json"):
            continue
        key = f[:-5]
        spec = json.load(open(os.path.join(SPECD, f), encoding="utf-8"))
        out[key] = spec
    return out


def figure(key: str, spec: dict, n: int) -> str:
    cap = spec.get("caption") or key
    alt = spec.get("alt") or cap
    label = spec.get("label", "高保真重绘")
    kindcls = " real" if "实测" in label or "实机" in label else ""
    src = spec.get("src", "本站自绘（figkit 高保真画面）")
    w = spec.get("w", 1440)
    h = spec.get("h", 900)
    return (f'<figure class="fig" data-fig="{key}">\n'
            f'  <a class="zoom" href="assets/fig/{key}.svg" target="_blank" '
            f'title="点击在新标签打开原图"><img src="assets/fig/{key}.svg" alt="{alt}" '
            f'width="{w}" height="{h}" loading="lazy"></a>\n'
            f'  <figcaption><span class="n">画面 {n}</span><span class="cap">{cap}</span>'
            f'<span class="kind{kindcls}">{label}</span>'
            f'<span class="src">{src}</span></figcaption>\n'
            f'</figure>')


def run(check=False) -> int:
    specs = load_specs()
    errors, used = [], set()
    for f in sorted(os.listdir(ROOT)):
        if not f.endswith(".html"):
            continue
        path = os.path.join(ROOT, f)
        src = open(path, encoding="utf-8").read()
        clean = DONE.sub("", src)
        counter = [0]

        def repl(m):
            key = m.group(1)
            if key not in specs:
                errors.append(f"{f}: marker FIG:{key} has no spec file")
                return m.group(0)
            if not os.path.exists(os.path.join(FIGDIR, key + ".svg")):
                errors.append(f"{f}: spec {key} has no rendered SVG (run figkit --all)")
                return m.group(0)
            used.add(key)
            counter[0] += 1
            return figure(key, specs[key], counter[0])

        new = MARK.sub(repl, clean)
        # keys referenced indirectly (e.g. via html comments in prose) are reported below
        if new != src and not check:
            open(path, "w", encoding="utf-8").write(new)
            print(f"figs {f:24s} {counter[0]} 张")
        elif new != src and check:
            errors.append(f"{f}: figure markup out of date")
    unused = sorted(set(specs) - used)
    for u in unused:
        print(f"INFO spec {u} is not referenced by any page")
    for e in errors:
        print("ERR  " + e)
    print(f"\n{len(used)} screens placed in pages, {len(unused)} specs unused, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(run(check="--check" in sys.argv[1:]))
