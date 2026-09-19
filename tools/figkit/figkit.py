#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
figkit — high-fidelity SVG re-draws of SAP BTP-family screens.

Why: this training site must show BTP Cockpit / BAS / HANA Cloud / CF CLI / Fiori
screens, but no SAP system is reachable.  figkit renders *re-drawn* screens from a
JSON spec (see SPEC.md) in the SAP Horizon visual language so every procedure step
has a screen beside it.  Everything is a plain <rect>/<text>/<path> — no fonts, no
images, no CDN — so the SVGs stay offline-safe and small, and a real screenshot can
later replace any single file 1:1 (same file name, same canvas).

Usage:
    python3 figkit.py --one  path/to/spec.json [--out out.svg]
    python3 figkit.py --all  <spec.d dir> --outdir <assets/fig dir>

Contract for spec authors: never invent a label that is not on the real screen
without checking the docs; mark uncertain labels with "~".  The renderer fails loudly
on a callout whose `on` string does not exist, so a typo cannot ship silently.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata

# --------------------------------------------------------------------------- theme
T = {
    # SAP Horizon (Fiori 3) palette
    "shell": "#ffffff", "shellLine": "#e5e5e5", "shellInk": "#1d2d3e",
    "brand": "#0070f2", "brandDark": "#0064d9", "brandBg": "#e8f0fb",
    "ink": "#1d2d3e", "ink2": "#354a5f", "muted": "#6a6d70", "muted2": "#8b9094",
    "bg": "#f5f6f7", "surface": "#ffffff", "line": "#e5e5e5", "line2": "#d9d9d9",
    "hover": "#f2f2f2", "sel": "#e8f0fb", "thead": "#f5f6f7",
    "green": "#256f3a", "greenBg": "#e7f4ea",
    "red": "#aa0808", "redBg": "#fdeaea",
    "amber": "#e76500", "amberBg": "#fdf3e8",
    "blue": "#0070f2", "blueBg": "#e8f0fb",
    # BAS (VS Code-like, SAP light theme + dark terminal)
    "ideBar": "#f5f6f7", "ideSide": "#ffffff", "ideTitle": "#ffffff",
    "ideLine": "#e5e5e5", "ideStatus": "#0070f2", "ideStatusInk": "#ffffff",
    "ideTabActive": "#ffffff", "ideTabIdle": "#f5f6f7", "ideGutter": "#8b9094",
    "term": "#1b1b1b", "termLine": "#2a2a2a", "termInk": "#e8e8e8",
    "termGreen": "#6fd36f", "termBlue": "#79c0ff", "termYellow": "#e3d18a",
    # code token colors (light editor)
    "cComment": "#6a9955", "cStr": "#a31515", "cKw": "#0000ff", "cNum": "#098658",
    "cAnno": "#795e26", "cType": "#267f99", "cPlain": "#1d2d3e",
}
SANS = "'72','72full',-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif"
MONO = "'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

# ------------------------------------------------------------------- text metrics
_WIDE = ("W", "F")


def _is_wide(ch: str) -> bool:
    if ch in _WIDE:
        return True
    return unicodedata.east_asian_width(ch) in ("W", "F")


def tw(s: str, size: float, mono: bool = False, bold: bool = False) -> float:
    """Estimated text width.  CJK glyphs are full-width (1.0em), latin ~0.52em."""
    unit = 0.60 if mono else 0.52
    if bold:
        unit += 0.02
    return sum(size * (1.0 if _is_wide(c) else unit) for c in str(s))


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ------------------------------------------------------------------------ canvas
class G:
    """SVG canvas that also records every text box for callout placement checks."""

    def __init__(self, w: int, h: int, bg: str = T["bg"]):
        self.w, self.h = w, h
        self.parts: list[str] = []
        self.texts: list[dict] = []          # recorded text boxes
        self.bottom = 0                      # deepest ink, for overflow checks
        self.parts.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="{bg}"/>')

    # --- primitives -------------------------------------------------------
    def rect(self, x, y, w, h, fill="none", stroke=None, rx=0, sw=1, op=None, dash=None):
        s = f'<rect x="{x:g}" y="{y:g}" width="{max(w,0):g}" height="{max(h,0):g}"'
        if rx:
            s += f' rx="{rx:g}"'
        s += f' fill="{fill}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{sw:g}"'
        if op is not None:
            s += f' opacity="{op:g}"'
        if dash:
            s += f' stroke-dasharray="{dash}"'
        s += "/>"
        self.parts.append(s)
        return self

    def line(self, x1, y1, x2, y2, stroke=T["line"], sw=1, dash=None, op=None):
        s = (f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" '
             f'stroke="{stroke}" stroke-width="{sw:g}"')
        if dash:
            s += f' stroke-dasharray="{dash}"'
        if op is not None:
            s += f' opacity="{op:g}"'
        self.parts.append(s + "/>")
        return self

    def circle(self, cx, cy, r, fill="none", stroke=None, sw=1):
        s = f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{fill}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{sw:g}"'
        self.parts.append(s + "/>")
        return self

    def path(self, d, fill="none", stroke=None, sw=1, rx=None):
        s = f'<path d="{d}" fill="{fill}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{sw:g}" stroke-linecap="round"'
        self.parts.append(s + "/>")
        return self

    def png_ish(self, x, y, w, h, kind="img", fill="#dfe6ec"):
        """Little picture placeholder glyph (used for avatars / tile art)."""
        if kind == "person":
            self.circle(x + w / 2, y + h * 0.36, h * 0.20, fill=fill)
            self.path(f"M{x + w*0.14:.1f} {y + h:.1f} q{w*0.36:.1f} {-h*0.52:.1f} {w*0.72:.1f} 0 Z", fill=fill)
        else:
            self.rect(x, y, w, h, fill=fill, rx=2)
        return self

    def text(self, x, y, s, size=14, fill=None, anchor="start", weight=400,
             mono=False, italic=False, op=None, record=True):
        """y = baseline."""
        if s is None or s == "":
            return self
        fill = fill or T["ink"]
        fam = MONO if mono else SANS
        s = str(s)
        wpx = tw(s, size, mono=mono, bold=(weight or 400) >= 600)
        if anchor == "middle":
            left = x - wpx / 2
        elif anchor == "end":
            left = x - wpx
        else:
            left = x
        if record:
            self.texts.append(dict(x=left, y=y - size * 0.78, w=wpx, h=size * 1.22, s=s, size=size))
        self.bottom = max(self.bottom, y + size * 0.3)
        st = f' font-size="{size:g}" fill="{fill}" font-family="{fam}"'
        if anchor != "start":
            st += f' text-anchor="{anchor}"'
        if weight and weight != 400:
            st += f' font-weight="{weight}"'
        if italic:
            st += ' font-style="italic"'
        if op is not None:
            st += f' opacity="{op:g}"'
        self.parts.append(f'<text x="{x:g}" y="{y:g}"{st}>{esc(s)}</text>')
        return self

    def btext(self, x, y, w, h, s, size=14, fill=None, anchor="start", weight=400,
              mono=False, pad=0):
        """Text vertically centred inside a box of height h; y = box top."""
        base = y + h / 2 + size * 0.35
        if anchor == "start":
            x = x + pad
        elif anchor == "end":
            x = x + w - pad
        else:
            x = x + w / 2
        return self.text(x, base, s, size=size, fill=fill, anchor=anchor, weight=weight, mono=mono)

    def svg(self) -> str:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="{self.w}" height="{self.h}" role="img">')
        return head + "".join(self.parts) + "</svg>"


# ------------------------------------------------------------------- primitives
def wrap(g: G, s, w, size=14, mono=False) -> list[str]:
    """Greedy wrap honouring CJK (breaks anywhere) and latin (breaks on spaces)."""
    out, line = [], ""
    for chunk in re.findall(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]|[^ \u4e00-\u9fff]+| ", str(s)):
        if tw(line + chunk, size, mono) > w and line:
            out.append(line)
            line = chunk.lstrip(" ")
        else:
            line += chunk
    if line.strip() or not out:
        out.append(line.rstrip())
    return out


def code_line_tokens(line: str, lang: str) -> list[tuple[str, str]]:
    """Very small highlighter for CDS / JS / Java / YAML / XML / bash / SQL."""
    kw = {
        "cds": ["entity", "service", "using", "from", "as", "key", "projection", "on", "actions",
                "function", "aspect", "type", "many", "one", "to", "association", "composition",
                "extend", "annotate", "with", "true", "false", "null", "cuid", "managed",
                "localized", "array", "of", "select", "where", "order", "by", "group", "having",
                "namespace", "define", "virtual", "not", "and", "or"],
        "js": ["const", "let", "var", "function", "return", "async", "await", "if", "else", "for",
               "of", "in", "new", "try", "catch", "throw", "this", "class", "extends", "module",
               "exports", "require", "true", "false", "null", "await"],
        "java": ["public", "private", "protected", "class", "interface", "extends", "implements",
                 "void", "static", "final", "new", "return", "if", "else", "for", "while", "try",
                 "catch", "throw", "import", "package", "this", "null", "true", "false",
                 "boolean", "int", "long", "double", "String", "var", "record", "default",
                 "enum", "instanceof", "Optional", "List"],
        "yaml": ["true", "false", "null"],
        "bash": ["cd", "npm", "npx", "mvn", "cf", "btp", "curl", "export", "echo", "git", "sudo"],
        "sql": ["select", "from", "where", "and", "or", "order", "by", "insert", "into", "values",
                "update", "set", "delete", "create", "table", "key", "not", "null", "as", "join",
                "on", "group", "having", "limit", "count", "sum"],
    }.get(lang, [])
    comment_open = {"cds": ["//"], "js": ["//", "/*"], "java": ["//", "/*"], "yaml": ["#"],
                    "bash": ["#"], "sql": ["--", "/*"], "xml": ["<!--"], "json": []}.get(lang, [])
    out, i, n = [], 0, len(line)
    while i < n:
        cm = next((c for c in comment_open if line.startswith(c, i)), None)
        if cm:
            out.append(("c", line[i:]))
            break
        ch = line[i]
        if ch in "\"'`":
            j = i + 1
            while j < n and line[j] != ch:
                j += 2 if line[j] == "\\" else 1
            out.append(("s", line[i:min(j + 1, n)]))
            i = j + 1
            continue
        if ch == "@":
            m = re.match(r"@[\w.:]+", line[i:])
            if m:
                out.append(("an", m.group(0)))
                i += len(m.group(0))
                continue
        m = re.match(r"[A-Za-z_][\w.:]*", line[i:])
        if m:
            w = m.group(0)
            if w in kw:
                out.append(("k", w))
            elif w[:1].isupper() and lang in ("cds", "java"):
                out.append(("ty", w))
            else:
                out.append(("p", w))
            i += len(w)
            continue
        m = re.match(r"\d[\w.]*", line[i:])
        if m:
            out.append(("n", m.group(0)))
            i += len(m.group(0))
            continue
        out.append(("p", ch))
        i += 1
    return out or [("p", "")]


TOKCOL = {"c": T["cComment"], "s": T["cStr"], "k": T["cKw"], "n": T["cNum"],
          "an": T["cAnno"], "ty": T["cType"], "p": T["cPlain"]}


# ---------------------------------------------------------------------- widgets
def draw_blocks(g: G, x: float, y: float, w: float, blocks, ctx: dict) -> float:
    """Render the generic block vocabulary; returns the new bottom y."""
    for b in blocks or []:
        t = b.get("t", "p")
        if t == "space":
            y += b.get("h", 12)
        elif t in ("h1", "h2", "h3", "h4"):
            size = {"h1": 22, "h2": 18, "h3": 15.5, "h4": 14}[t]
            y += b.get("mt", 10 if t != "h1" else 0)
            for i, ln in enumerate(wrap(g, b["text"], w, size)):
                g.text(x, y + size * 0.9 + i * (size * 1.30), ln, size=size, weight=700,
                       fill=b.get("fill", T["ink"]))
            y += size * 1.30 * len(wrap(g, b["text"], w, size)) + 6
        elif t == "p":
            size = b.get("size", 13.5)
            lines = wrap(g, b["text"], w, size)
            for i, ln in enumerate(lines):
                g.text(x, y + size * 0.95 + i * (size * 1.55), ln, size=size, fill=b.get("fill", T["ink2"]))
            y += size * 1.55 * len(lines) + 6
        elif t == "kv":
            lw = b.get("lw", min(240, w * 0.34))
            for lab, val in b["rows"]:
                g.text(x, y + 17, lab, size=13, fill=T["muted"])
                g.text(x + lw, y + 17, val, size=13, fill=T.get("kvInk", T["ink"]))
                y += 26
            y += 6
        elif t == "table":
            y = draw_table(g, x, y, w, b)
        elif t == "tiles":
            y = draw_tiles(g, x, y, w, b)
        elif t == "cards":
            y = draw_cards(g, x, y, w, b)
        elif t == "form":
            y = draw_form(g, x, y, w, b)
        elif t == "code":
            y = draw_code(g, x, y, w, b)
        elif t == "term":
            y = draw_term(g, x, y, w, b)
        elif t in ("note", "banner"):
            y = draw_note(g, x, y, w, b)
        elif t == "list":
            for i, it in enumerate(b["items"]):
                mark = f"{i+1}." if b.get("ordered") else "•"
                g.text(x + 4, y + 16, mark, size=13, fill=T["muted"])
                for j, ln in enumerate(wrap(g, it, w - 24, 13.5)):
                    g.text(x + 24, y + 16 + j * 20, ln, size=13.5, fill=T["ink2"])
                y += 20 * max(1, len(wrap(g, it, w - 24, 13.5))) + 4
            y += 6
        elif t == "tree":
            y = draw_tree(g, x, y, w, b)
        elif t == "toolbar":
            y = draw_toolbar(g, x, y, w, b)
        elif t == "steps":
            y = draw_steps(g, x, y, w, b)
        elif t == "metrics":
            y = draw_metrics(g, x, y, w, b)
        elif t == "progress":
            g.rect(x, y, w, 6, fill=T["line"], rx=3)
            g.rect(x, y, w * b.get("value", 0) / 100.0, 6, fill=T["brand"], rx=3)
            y += 10
            if b.get("text"):
                y += 18
                g.text(x, y, b["text"], size=12.5, fill=T["muted"])
            y += 8
        elif t == "tabs":
            y = draw_tabs(g, x, y, w, b)
        elif t == "hr":
            g.line(x, y + 6, x + w, y + 6, stroke=T["line"])
            y += 14
        elif t == "gap2":            # two-column split helper: ignore, handled by caller
            pass
        else:
            raise ValueError(f"unknown block type: {t!r}")
    return y


def draw_table(g: G, x, y, w, b) -> float:
    cols = b["cols"]
    rows = b["rows"]
    widths = b.get("widths")
    if not widths:
        widths = [w / len(cols)] * len(cols)
    else:
        s = sum(widths)
        widths = [wi / s * w for wi in widths]
    hh = b.get("hh", 34)
    rh = b.get("rh", 34)
    fs = b.get("fs", 12.5)
    # header
    g.rect(x, y, w, hh, fill=T["thead"], stroke=T["line"])
    cx = x
    for i, c in enumerate(cols):
        g.btext(cx + 4, y, widths[i] - 8, hh, c, size=fs, weight=700, fill=T["ink"])
        cx += widths[i]
    y += hh
    for r, row in enumerate(rows):
        if b.get("selected") == r:
            g.rect(x, y, w, rh, fill=T["sel"])
        g.rect(x, y, w, rh, fill="none", stroke=T["line"])
        cx = x
        for i, cell in enumerate(row):
            if i < len(widths):
                col = T["ink2"]
                cweight = 400
                if i == 0 and b.get("firstBold", True):
                    col, cweight = T["ink"], 600
                g.btext(cx + 4, y, widths[i] - 8, rh, cell, size=fs, fill=col, weight=cweight)
            cx += widths[i]
        y += rh
    y += b.get("mb", 10)
    return y


def draw_tiles(g: G, x, y, w, b) -> float:
    n = b.get("cols", 3)
    gap = 12
    tw_ = (w - gap * (n - 1)) / n
    th = b.get("h", 104)
    for i, it in enumerate(b["items"]):
        cx = x + (i % n) * (tw_ + gap)
        cy = y + (i // n) * (th + gap)
        g.rect(cx, cy, tw_, th, fill=T["surface"], stroke=T["line"], rx=8)
        g.rect(cx, cy, tw_, 3, fill=it.get("accent", T["brand"]), rx=2)
        g.rect(cx + 14, cy + 20, 26, 26, fill=it.get("iconBg", T["brandBg"]), rx=6)
        g.btext(cx + 14, cy + 20, 26, 26, it.get("glyph", it["title"][:1]), size=12,
                weight=700, anchor="middle", fill=it.get("accent", T["brand"]))
        g.text(cx + 50, cy + 38, it["title"], size=13.5, weight=700)
        if it.get("sub"):
            for j, ln in enumerate(wrap(g, it["sub"], tw_ - 30, 12)[:2]):
                g.text(cx + 14, cy + 70 + j * 15, ln, size=12, fill=T["muted"])
        if it.get("chip"):
            cw = tw(it["chip"], 11) + 16
            g.rect(cx + 14, cy + th - 26, cw, 18, fill=it.get("chipBg", T["greenBg"]), rx=9)
            g.btext(cx + 14, cy + th - 26, cw, 18, it["chip"], size=11, anchor="middle",
                    fill=it.get("chipInk", T["green"]), weight=600)
    rows = (len(b["items"]) + n - 1) // n
    return y + rows * (th + gap) + b.get("mb", 8)


def draw_cards(g: G, x, y, w, b) -> float:
    n = b.get("cols", 2)
    gap = 14
    cw = (w - gap * (n - 1)) / n
    ch = b.get("h")
    items = b["items"]
    if not ch:
        ch = max(88, 44 + max(len(wrap(g, it.get("text", ""), cw - 34, 12.5)) for it in items) * 17)
    for i, it in enumerate(items):
        cx = x + (i % n) * (cw + gap)
        cy = y + (i // n) * (ch + gap)
        g.rect(cx, cy, cw, ch, fill=T["surface"], stroke=T["line"], rx=8)
        ty = cy + 26
        g.text(cx + 16, ty, it["title"], size=13.5, weight=700)
        if it.get("value") is not None:
            g.text(cx + cw - 16, ty, it["value"], size=17, weight=700, anchor="end",
                   fill=it.get("valueColor", T["ink"]))
        if it.get("text"):
            for j, ln in enumerate(wrap(g, it["text"], cw - 32, 12.5)):
                g.text(cx + 16, ty + 20 + j * 17, ln, size=12.5, fill=T["muted"])
        if it.get("status"):
            g.text(cx + 16, cy + ch - 14, "● " + it["status"], size=12,
                   fill=it.get("statusColor", T["green"]))
    rows = (len(items) + n - 1) // n
    return y + rows * (ch + gap) + b.get("mb", 8)


def draw_form(g: G, x, y, w, b) -> float:
    cols = b.get("cols", 2)
    gap = 20
    fw = (w - gap * (cols - 1)) / cols
    rowh = b.get("rowh", 46)
    for i, f in enumerate(b["fields"]):
        cx = x + (i % cols) * (fw + gap)
        cy = y + (i // cols) * rowh
        g.text(cx, cy + 13, f[0], size=12, fill=T["muted"])
        val = f[1] if len(f) > 1 else ""
        g.rect(cx, cy + 19, fw, 26, fill=T["surface"], stroke=T["line2"], rx=4)
        g.btext(cx + 8, cy + 19, fw - 16, 26, val, size=12.5)
        if len(f) > 2 and f[2]:
            g.text(cx + fw - 4, cy + 13, f[2], size=11.5, fill=T["brand"], anchor="end")
    rows = (len(b["fields"]) + cols - 1) // cols
    return y + rows * rowh + b.get("mb", 8)


def draw_code(g: G, x, y, w, b) -> float:
    lines = b["lines"]
    fs = b.get("fs", 12.5)
    lh = b.get("lh", 19)
    pad = 10
    h = pad * 2 + lh * len(lines)
    g.rect(x, y, w, h, fill=b.get("bg", T["surface"]), stroke=T["line"], rx=6)
    if b.get("title"):
        g.rect(x, y, w, 26, fill=T["thead"], stroke=T["line"], rx=6)
        g.btext(x + 10, y, w - 20, 26, b["title"], size=12, weight=600, fill=T["ink2"])
        yy = y + 26
    else:
        yy = y
    ln_w = 30 if b.get("numbers", True) else 0
    if ln_w:
        g.rect(x + 1, yy, ln_w, h - (26 if b.get("title") else 0) - 1, fill=T["thead"])
    hl = b.get("hl")
    if hl is not None:
        g.rect(x + 1, yy + (hl - 1) * lh, w - 2, lh, fill=b.get("hlBg", "#fffbe6"))
    for i, ln in enumerate(lines):
        by = yy + lh * i + lh * 0.75
        if b.get("numbers", True):
            g.text(x + ln_w - 8, by, i + 1, size=fs - 1.5, mono=True, fill=T["ideGutter"], anchor="end")
        cxp = x + ln_w + 8
        start = cxp
        for kind, tok in code_line_tokens(ln, b.get("lang", "cds")):
            g.text(cxp, by, tok, size=fs, mono=True, fill=TOKCOL[kind], record=False)
            cxp += tw(tok, fs, mono=True)
        # one callout target per source line = union of its tokens (substring-matchable)
        g.texts.append(dict(x=start, y=yy + lh * i, w=max(cxp - start, 1), h=lh, s=ln, size=fs))
    return y + h + b.get("mb", 10)


def draw_term(g: G, x, y, w, b) -> float:
    lines = b["lines"]
    fs = b.get("fs", 12.5)
    lh = b.get("lh", 18.5)
    pad = 10
    h = pad * 2 + lh * len(lines)
    g.rect(x, y, w, h, fill=T["term"], rx=6)
    for i, ln in enumerate(lines):
        by = y + pad + lh * i + lh * 0.75
        col = T["termInk"]
        if ln.startswith("$"):
            col = T["termGreen"]
        elif ln.startswith("#"):
            col = T["termYellow"]
            ln = ln[1:]
        elif ln.startswith("@"):
            col = T["termBlue"]
            ln = ln[1:]
        g.text(x + pad, by, ln, size=fs, mono=True, fill=col)
    return y + h + b.get("mb", 10)


def draw_note(g: G, x, y, w, b) -> float:
    kind = b.get("kind", "info")
    bg = {"info": T["blueBg"], "warn": T["amberBg"], "error": T["redBg"],
          "success": T["greenBg"]}.get(kind, T["blueBg"])
    ink = {"info": T["blue"], "warn": T["amber"], "error": T["red"],
           "success": T["green"]}.get(kind, T["blue"])
    lines = wrap(g, b["text"], w - 40, 12.5)
    h = 20 + 17 * len(lines)
    g.rect(x, y, w, h, fill=bg, rx=6)
    g.circle(x + 16, y + h / 2, 8, fill=ink)
    g.text(x + 16, y + h / 2 + 4, "!", size=11, fill="#ffffff", anchor="middle", weight=700)
    for i, ln in enumerate(lines):
        g.text(x + 32, y + 22 + i * 17, ln, size=12.5, fill=T["ink"])
    return y + h + b.get("mb", 10)


def draw_tree(g: G, x, y, w, b) -> float:
    rowh = b.get("rowh", 24)
    for it in b["items"]:
        d = it.get("d", 0)
        cx = x + d * 14
        kind = it.get("k", "file")
        if it.get("open") or kind == "folder":
            g.path(f"M{cx:.1f} {y+7:.1f} l5 -5 l5 5 Z", fill=T["muted"])
        else:
            g.path(f"M{cx:.1f} {y+4:.1f} l5 5 l-5 5 Z", fill=T["muted"])
        col = T["ink2"] if kind != "folder" else T["ink"]
        weight = 600 if it.get("b") else 400
        g.text(cx + 14, y + 17, it["label"], size=12.5, fill=col, weight=weight)
        if it.get("tag"):
            g.text(x + w - 6, y + 17, it["tag"], size=11, fill=T["brand"], anchor="end")
        y += rowh
    return y + b.get("mb", 8)


def draw_toolbar(g: G, x, y, w, b) -> float:
    h = 36
    cx = x
    for it in b.get("items", []):
        label = it["label"]
        bw = tw(label, 12.5, bold=True) + 30
        primary = it.get("primary")
        g.rect(cx, y, bw, h, fill=T["brand"] if primary else T["surface"],
               stroke=None if primary else T["line2"], rx=6)
        g.btext(cx, y, bw, h, label, size=12.5, anchor="middle",
                fill="#ffffff" if primary else T["brand"], weight=600)
        cx += bw + 8
    box = b.get("search")
    if box is not None:
        bw = min(240, w * 0.3)
        g.rect(x + w - bw, y, bw, h, fill=T["surface"], stroke=T["line2"], rx=6)
        g.circle(x + w - bw + 16, y + h / 2, 6, stroke=T["muted"], sw=1.4)
        g.line(x + w - bw + 20, y + h / 2 + 4, x + w - bw + 24, y + h / 2 + 8, stroke=T["muted"], sw=1.4)
        g.btext(x + w - bw + 30, y, bw - 40, h, box, size=12, fill=T["muted"])
    return y + h + b.get("mb", 10)


def draw_steps(g: G, x, y, w, b) -> float:
    items = b["items"]
    act = b.get("active", 0)
    n = len(items)
    seg = w / n
    for i, it in enumerate(items):
        cxx = x + seg * i + 12
        done = i < act
        cur = i == act
        g.circle(cxx, y + 12, 11, fill=T["brand"] if cur else (T["greenBg"] if done else T["surface"]),
                 stroke=T["brand"] if cur else T["line2"], sw=1.5)
        g.text(cxx, y + 16, "✓" if done else str(i + 1), size=10.5, anchor="middle",
               fill="#ffffff" if cur else (T["green"] if done else T["muted"]), weight=700)
        g.text(cxx + 18, y + 16, it, size=12.5, fill=T["ink"] if cur else T["muted"],
               weight=700 if cur else 400)
        if i < n - 1:
            g.line(cxx + 14 + tw(it, 12.5), y + 12, x + seg * (i + 1) - 4, y + 12, stroke=T["line2"])
    y += 30
    if b.get("sub"):
        g.text(x, y + 10, b["sub"], size=12.5, fill=T["muted"])
        y += 20
    return y + b.get("mb", 6)


def draw_metrics(g: G, x, y, w, b) -> float:
    items = b["items"]
    n = len(items)
    seg = w / n
    for i, it in enumerate(items):
        cx = x + seg * i
        g.rect(cx, y, seg - 10, 62, fill=T["surface"], stroke=T["line"], rx=8)
        g.text(cx + 12, y + 18, it["label"], size=11.5, fill=T["muted"])
        g.text(cx + 12, y + 46, it["value"], size=19, weight=700,
               fill=it.get("color", T["ink"]))
    return y + 62 + b.get("mb", 10)


def draw_tabs(g: G, x, y, w, b) -> float:
    h = 30
    cx = x
    for i, it in enumerate(b.get("items", [])):
        bw = tw(it, 13) + 28
        act = i == b.get("active", 0)
        g.text(cx + 14, y + 20, it, size=13, fill=T["brand"] if act else T["ink2"],
               weight=600 if act else 400)
        if act:
            g.rect(cx + 6, y + h - 3, bw - 12, 3, fill=T["brand"], rx=1.5)
        cx += bw
    g.line(x, y + h - 1, x + w, y + h - 1, stroke=T["line"])
    return y + h + 8


# ---------------------------------------------------------------------- chrome
def shell_bar(g: G, w, product="SAP Business Technology Platform", right_user="JASON",
              search="Search", shell_ink=None, bg=None):
    h = 44
    bg = bg or T["shell"]
    g.rect(0, 0, w, h, fill=bg)
    g.line(0, h, w, h, stroke=T["shellLine"])
    # SAP-ish wordmark (geometric, no logo asset)
    g.rect(14, h / 2 - 9, 60, 18, fill=T["brand"], rx=3)
    g.text(44, h / 2 + 5, "SAP", size=13, weight=700, anchor="middle", fill="#ffffff")
    g.text(84, h / 2 + 5, product, size=13.5, weight=600, fill=shell_ink or T["shellInk"])
    if search is not None:
        sw = min(300, w * 0.26)
        g.rect(430, h / 2 - 14, sw, 28, fill="#f5f6f7", stroke=T["shellLine"], rx=6)
        g.circle(430 + 18, h / 2 - 1, 6, stroke=T["muted"], sw=1.4)
        g.line(430 + 22, h / 2 + 3, 430 + 26, h / 2 + 7, stroke=T["muted"], sw=1.4)
        g.text(430 + 36, h / 2 + 4, search, size=12.5, fill=T["muted"])
    # right icons
    xs = w - 22
    g.circle(xs, h / 2, 13, fill="#e8f0fb")
    g.png_ish(xs - 7, h / 2 - 8, 14, 16, kind="person", fill="#7ba7d1")
    for i, glyph in enumerate(["?", "⚙", "🔔"]):
        gx = xs - 40 - i * 28
        g.text(gx, h / 2 + 5, glyph, size=13, anchor="middle", fill=T["muted"])
    g.text(xs - 40 - 3 * 28 - 14, h / 2 + 5, right_user, size=12.5, fill=T["ink2"],
           anchor="end", weight=600)
    return h


def side_nav(g: G, x, y, w, h, nav: dict, bg=None):
    bg = bg or T["surface"]
    g.rect(x, y, w, h, fill=bg)
    g.line(x + w, y, x + w, y + h, stroke=T["line"])
    cy = y + 14
    if nav.get("title"):
        g.text(x + 16, cy + 12, nav["title"], size=12, fill=T["muted"], weight=700)
        cy += 26
    for it in nav.get("items", []):
        if it.get("sep"):
            cy += 10
            g.line(x + 12, cy - 4, x + w - 12, cy - 4, stroke=T["line"])
            cy += 6
            continue
        act = it.get("active")
        if act:
            g.rect(x + 6, cy, w - 12, 32, fill=T["sel"], rx=6)
            g.rect(x + 6, cy, 3, 32, fill=T["brand"], rx=1.5)
        elif it.get("group"):
            g.text(x + 16, cy + 14, it["label"], size=11.5, fill=T["muted"], weight=700)
            cy += 28
            continue
        g.btext(x + 16, cy, w - 32, 32, it["label"], size=13,
                fill=T["brand"] if act else T["ink2"], weight=600 if act else 400)
        cy += 32
        if it.get("sub") and act:
            for s in it["sub"]:
                g.btext(x + 34, cy, w - 50, 26, s, size=12.5, fill=T["ink2"])
                cy += 26
    return


def callouts(g: G, spec):
    """Red numbered badges + leader lines, auto-placed to avoid covered text."""
    items = spec.get("callouts") or []
    if not items:
        return
    placed = []
    for i, c in enumerate(items):
        tgt = None
        if c.get("on"):
            want = c["on"]
            occ = c.get("on_index", 1) - 1
            hits = [t for t in g.texts if t["s"] == want]
            if not hits:
                hits = [t for t in g.texts if want in t["s"]]
            if not hits:
                raise ValueError(f"callout #{i+1}: text {want!r} not found on screen "
                                 f"(spec {spec.get('key')})")
            hits = sorted(hits, key=lambda t: (t["y"], t["x"]))
            tgt = hits[min(occ, len(hits) - 1)]
        elif c.get("at"):
            x, y = c["at"]
            tgt = dict(x=x, y=y, w=0, h=0, s="")
        else:
            raise ValueError(f"callout #{i+1}: needs 'on' or 'at'")
        label = c["text"]
        bw = tw(label, 12) + 40
        bh = 26
        tx = tgt["x"] + tgt["w"] / 2
        ty = tgt["y"] + tgt["h"] / 2
        best = None
        for dy in (0, -34, 34, -68, 68, -102, 102, -136, 136, -170, 170, -204, 204,
                   -238, 238, -272, 272, -306, 306):
            for dx in (110, -110, 230, -230, 350, -350, 470, -470, 600, -600, 760, -760):
                bx = tx + dx
                by = ty + dy - bh / 2
                if bx - 20 < 4 or bx + bw - 20 > g.w - 4 or by < 50 or by + bh > g.h - 46:
                    continue
                rect = (bx - 22, by - 4, bw + 6, bh + 8)
                if hit_text(g.texts, rect) or any(overlap(rect, p) for p in placed):
                    continue
                best = (bx - 22, by)
                break
            if best:
                break
        if not best:
            best = (min(max(tx + 110, 6), g.w - bw - 6), max(min(ty - 20, g.h - 60), 50))
            g.forced = getattr(g, "forced", 0) + 1
        bx, by = best
        placed.append((bx, by, bw, bh))
        cx, cy = bx + 13, by + bh / 2
        g.path(f"M{cx:.1f} {cy:.1f} L{tx:.1f} {ty:.1f}", stroke=T["red"], sw=1.2)
        g.rect(bx, by, bw, bh, fill="#ffffff", stroke=T["red"], rx=13, sw=1.2)
        g.circle(cx, cy, 10, fill=T["red"])
        g.text(cx, cy + 4, str(i + 1), size=11.5, fill="#ffffff", anchor="middle", weight=700)
        g.text(cx + 16, cy + 4.5, label, size=12, fill=T["red"], weight=600)


def overlap(a, b) -> bool:
    return not (a[0] + a[2] < b[0] or b[0] + b[2] < a[0] or
                a[1] + a[3] < b[1] or b[1] + b[3] < a[1])


def hit_text(texts, rect) -> bool:
    rx, ry, rw, rh = rect
    for t in texts:
        if (t["x"] + t["w"] > rx + 2 and t["x"] < rx + rw - 2 and
                t["y"] + t["h"] > ry + 2 and t["y"] < ry + rh - 2):
            return True
    return False


# ----------------------------------------------------------------------- kinds
def kind_cockpit(g: G, spec):
    h = shell_bar(g, g.w, product=spec.get("product", "SAP Business Technology Platform"))
    nav = spec.get("nav")
    nx = 0
    if nav:
        side_nav(g, 0, h, 250, g.h - h, nav)
        nx = 250
    cx = nx + 28
    cy = h + 22
    cw = g.w - cx - 28
    if spec.get("crumbs"):
        for i, c in enumerate(spec["crumbs"]):
            g.text(cx, cy, c, size=12.5, fill=T["brand"] if i == len(spec["crumbs"]) - 1 else T["muted"])
            cx += tw(c, 12.5) + 14
            if i < len(spec["crumbs"]) - 1:
                g.text(cx - 10, cy, "/", size=12.5, fill=T["muted2"])
        cx = nx + 28
        cy += 18
    if spec.get("title"):
        g.text(cx, cy + 18, spec["title"], size=19, weight=700)
        cy += 30
    if spec.get("subtitle"):
        g.text(cx, cy + 14, spec["subtitle"], size=12.5, fill=T["muted"])
        cy += 22
    if spec.get("tabs"):
        cy = draw_tabs(g, cx, cy, cw, {"items": spec["tabs"], "active": spec.get("activeTab", 0)})
    cy += 12
    cy = draw_blocks(g, cx, cy, cw, spec.get("blocks"), spec)
    if spec.get("status"):
        b0 = g.bottom
        g.rect(0, g.h - 30, g.w, 30, fill=T["surface"])
        g.line(0, g.h - 30, g.w, g.h - 30, stroke=T["line"])
        g.btext(nx + 20, g.h - 30, g.w - 40 - nx, 30, spec["status"], size=12.5, fill=T["ink2"])
        g.bottom = b0


def kind_bas(g: G, spec):
    h = 38
    g.rect(0, 0, g.w, h, fill=T["ideTitle"])
    g.line(0, h, g.w, h, stroke=T["ideLine"])
    menus = spec.get("menus", ["File", "Edit", "Selection", "View", "Go", "Run", "Terminal", "Help"])
    mx = 16
    for m in menus:
        g.text(mx, h / 2 + 4.5, m, size=12.5, fill=T["ink2"])
        mx += tw(m, 12.5) + 18
    g.text(g.w / 2, h / 2 + 4.5, spec.get("window", "schema.cds - project-node - SAP Business Application Studio"),
           size=12.5, anchor="middle", fill=T["muted"])
    for i, glyph in enumerate(["⌘", "▭", "✕"]):
        g.text(g.w - 40 - i * 26, h / 2 + 4.5, glyph, size=12, anchor="middle", fill=T["muted"])
    # activity bar
    ax, aw = 0, 48
    g.rect(ax, h, aw, g.h - h - 22, fill=T["ideBar"])
    ay = h + 16
    for it in (spec.get("activity") or [{"glyph": "⧉", "active": True}, {"glyph": "⌕"}, {"glyph": "⑂"},
                                        {"glyph": "▷"}, {"glyph": "⛭"}]):
        if it.get("active"):
            g.rect(ax, ay - 6, 3, 34, fill=T["brand"])
        g.text(ax + aw / 2, ay + 18, it.get("glyph", "▢"), size=16, anchor="middle",
               fill=T["brand"] if it.get("active") else T["muted"])
        ay += 42
    # side panel
    sx, sw = aw, spec.get("sideW", 268)
    g.rect(sx, h, sw, g.h - h - 22, fill=T["ideSide"])
    g.line(sx + sw, h, sx + sw, g.h - 22, stroke=T["ideLine"])
    sy = h + 12
    if spec.get("sideTitle"):
        g.text(sx + 16, sy + 12, spec["sideTitle"], size=11.5, weight=700, fill=T["ink2"])
        sy += 24
    for sec in spec.get("side", []):
        if sec.get("label"):
            g.text(sx + 16, sy + 12, (("▾ " if sec.get("open", True) else "▸ ") + sec["label"]),
                   size=11.5, weight=700, fill=T["ink2"])
            sy += 22
        sy = draw_tree(g, sx + 16, sy, sw - 26, sec)
    # editor
    ex = sx + sw
    ew = g.w - ex
    panel = spec.get("panel")
    panel_h = 0
    if panel:
        panel_h = int(panel.get("h", 200))
    tabs = spec.get("tabs", [])
    ty = h
    g.rect(ex, ty, ew, 34, fill=T["ideTabIdle"])
    g.line(ex, ty + 34, g.w, ty + 34, stroke=T["ideLine"])
    tx = ex
    for i, t in enumerate(tabs):
        act = i == spec.get("activeTab", 0)
        bw = tw(t, 12.5) + 46
        g.rect(tx, ty, bw, 34, fill=T["ideTabActive"] if act else T["ideTabIdle"])
        if act:
            g.rect(tx, ty, bw, 2, fill=T["brand"])
        g.text(tx + 10, ty + 22, t, size=12.5, fill=T["ink"] if act else T["muted"])
        g.text(tx + bw - 18, ty + 22, "✕", size=11, fill=T["muted"])
        tx += bw
    ey = ty + 34
    eh = g.h - 22 - ey - panel_h
    g.rect(ex, ey, ew, eh, fill=T["surface"])
    if spec.get("breadcrumb"):
        g.btext(ex + 12, ey, ew - 24, 26, spec["breadcrumb"], size=12, fill=T["muted"])
        g.line(ex, ey + 26, g.w, ey + 26, stroke=T["ideLine"])
        cy = ey + 26
    else:
        cy = ey
    ed = spec.get("editor")
    if ed:
        lineh = ed.get("lh", 20)
        ys = cy + (eh - lineh * len(ed["lines"])) / 2 if ed.get("center") else cy + 10
        g.rect(ex, ys - 6, ew, lineh * len(ed["lines"]) + 12, fill=ed.get("bg", "#ffffff"))
        hl = ed.get("hl")
        for i, ln in enumerate(ed["lines"]):
            by = ys + lineh * i + lineh * 0.72
            if hl and (i + 1) in hl:
                g.rect(ex, ys + lineh * i, ew, lineh, fill=ed.get("hlBg", "#fff8e1"))
            g.text(ex + 18, by, i + 1, size=11.5, mono=True, fill=T["ideGutter"], anchor="end")
            cxp = ex + 34
            start = cxp
            for kind, tok in code_line_tokens(ln, ed.get("lang", "cds")):
                g.text(cxp, by, tok, size=ed.get("fs", 12.5), mono=True, fill=TOKCOL[kind], record=False)
                cxp += tw(tok, ed.get("fs", 12.5), mono=True)
            g.texts.append(dict(x=start, y=ys + lineh * i, w=max(cxp - start, 1), h=lineh, s=ln,
                                size=ed.get("fs", 12.5)))
    else:
        draw_blocks(g, ex + 20, cy + 12, ew - 40, spec.get("blocks"), spec)
    if panel:
        py = g.h - 22 - panel_h
        g.rect(ex, py, ew, panel_h, fill=T["term"] if panel.get("dark", True) else T["surface"])
        g.rect(ex, py, ew, 28, fill=panel.get("tabBg", "#252526"))
        g.text(ex + 16, py + 19, panel.get("title", "TERMINAL"), size=11.5, weight=700,
               fill="#d0d0d0" if panel.get("dark", True) else T["ink2"])
        for j, t in enumerate(panel.get("extraTabs", [])):
            g.text(ex + 110 + j * 90, py + 19, t, size=11.5, fill="#9a9a9a")
        for i, ln in enumerate(panel["lines"]):
            col = T["termInk"]
            if ln.startswith("$"):
                col = T["termGreen"]
            elif ln.startswith("@"):
                col = T["termBlue"]
                ln = ln[1:]
            elif ln.startswith("#"):
                col = T["termYellow"]
                ln = ln[1:]
            g.text(ex + 14, py + 46 + i * 17.5, ln, size=11.8, mono=True, fill=col)
    # status bar
    sy2 = g.h - 22
    b0 = g.bottom
    g.rect(0, sy2, g.w, 22, fill=T["ideStatus"])
    st = spec.get("status", ["⑂ main", "", "Node 22.20.0", "0 ▲ 0 ●"])
    g.text(14, sy2 + 15, st[0] if st else "", size=11.5, fill=T["ideStatusInk"])
    for i, s in enumerate(st[1:]):
        g.text(g.w - 20 - i * 150, sy2 + 15, s, size=11.5, fill=T["ideStatusInk"], anchor="end")
    g.bottom = b0


def kind_terminal(g: G, spec):
    h = 34
    g.rect(0, 0, g.w, h, fill="#252526")
    for i, glyph in enumerate(["●", "●", "●"]):
        g.circle(20 + i * 18, h / 2, 6, fill=["#ff5f56", "#ffbd2e", "#27c93f"][i])
    g.text(g.w / 2, h / 2 + 4.5, spec.get("title", "Terminal"), size=12.5,
           anchor="middle", fill="#c8c8c8")
    g.rect(0, h, g.w, g.h - h, fill=T["term"])
    lh = spec.get("lh", 18.5)
    for i, ln in enumerate(spec["lines"]):
        by = h + 22 + lh * i
        col = T["termInk"]
        if ln.startswith("$"):
            col = T["termGreen"]
        elif ln.startswith("@"):
            col = T["termBlue"]
            ln = ln[1:]
        elif ln.startswith("#"):
            col = T["termYellow"]
            ln = ln[1:]
        elif ln.startswith("+"):
            col = T["termGreen"]
            ln = ln[1:]
        g.text(24, by, ln, size=12.5, mono=True, fill=col)
    return


def kind_fiori(g: G, spec):
    mode = spec.get("mode", "app")
    h = shell_bar(g, g.w, product=spec.get("product", "SAP Fiori"),
                  right_user=spec.get("user", "JASON"))
    if mode == "launchpad":
        cy = h + 26
        if spec.get("title"):
            g.text(32, cy + 20, spec["title"], size=20, weight=700)
            cy += 34
        if spec.get("subtitle"):
            g.text(32, cy + 14, spec["subtitle"], size=12.5, fill=T["muted"])
            cy += 24
        cy += 10
        for sec in spec.get("sections", []):
            g.text(32, cy + 16, sec["label"], size=13.5, weight=700)
            cy += 26
            cy = draw_tiles(g, 32, cy, g.w - 64, {"items": sec["items"], "cols": sec.get("cols", 4), "h": 106})
            cy += 14
        return
    # app mode: title bar + optional filter bar + blocks
    cy = h
    g.rect(0, cy, g.w, 50, fill=T["surface"])
    g.line(0, cy + 50, g.w, cy + 50, stroke=T["line"])
    g.text(28, cy + 32, spec.get("title", ""), size=19, weight=700)
    if spec.get("subtitle"):
        g.text(28 + tw(spec["title"], 19, bold=True) + 14, cy + 32, spec["subtitle"], size=13, fill=T["muted"])
    cy += 50
    if spec.get("crumbs"):
        g.rect(0, cy, g.w, 30, fill=T["bg"])
        g.text(28, cy + 20, spec["crumbs"], size=12.5, fill=T["muted"])
        cy += 30
    if spec.get("toolbar"):
        cy = draw_toolbar(g, 28, cy + 12, g.w - 56, spec["toolbar"])
    if spec.get("filter"):
        boxh = 62
        g.rect(24, cy, g.w - 48, boxh, fill=T["surface"], stroke=T["line"], rx=8)
        g.text(40, cy + 24, "フィルタ / Filters", size=12, weight=700, fill=T["ink2"])
        fx = 40
        for i, f in enumerate(spec["filter"]):
            bw = 180
            g.text(fx, cy + 40, f[0], size=10.5, fill=T["muted"])
            g.rect(fx, cy + 44, bw, 14, fill="none", stroke=T["line2"], rx=3)
            fx += bw + 20
        cy += boxh + 12
    cy = draw_blocks(g, 28, cy, g.w - 56, spec.get("blocks"), spec)


def kind_hana(g: G, spec):
    h = shell_bar(g, g.w, product=spec.get("product", "SAP HANA Cloud"),
                  right_user=spec.get("user", "JASON"))
    nx = spec.get("navW", 260)
    if spec.get("nav"):
        side_nav(g, 0, h, nx, g.h - h, spec["nav"])
    else:
        nx = 0
    cx = nx + 24
    cw = g.w - cx - 24
    cy = h + 16
    if spec.get("title"):
        g.text(cx, cy + 16, spec["title"], size=18, weight=700)
        cy += 28
    if spec.get("tabs"):
        cy = draw_tabs(g, cx, cy, cw, {"items": spec["tabs"], "active": spec.get("activeTab", 0)})
    cy += 8
    draw_blocks(g, cx, cy, cw, spec.get("blocks"), spec)
    if spec.get("status"):
        b0 = g.bottom
        g.rect(0, g.h - 28, g.w, 28, fill=T["surface"])
        g.line(0, g.h - 28, g.w, g.h - 28, stroke=T["line"])
        g.btext(nx + 16, g.h - 28, g.w - 32 - nx, 28, spec["status"], size=12, fill=T["ink2"])
        g.bottom = b0


def kind_dialog(g: G, spec):
    base = spec.get("under", {})
    k = base.get("kind", "cockpit")
    base = dict(base)
    base.setdefault("key", spec.get("key"))
    {"cockpit": kind_cockpit, "bas": kind_bas, "hana": kind_hana,
     "fiori": kind_fiori, "terminal": kind_terminal}[k](g, base)
    g.rect(0, 0, g.w, g.h, fill="#1d2d3e", op=0.35)
    dw = spec.get("dw", 720)
    dh = spec.get("dh", 460)
    dx = (g.w - dw) / 2
    dy = max(60, (g.h - dh) / 2)
    g.rect(dx + 2, dy + 6, dw, dh, fill="#000000", op=0.18, rx=10)
    g.rect(dx, dy, dw, dh, fill=T["surface"], rx=10)
    g.text(dx + 22, dy + 32, spec.get("title", ""), size=17, weight=700)
    if spec.get("subtitle"):
        g.text(dx + 22, dy + 54, spec["subtitle"], size=12.5, fill=T["muted"])
    g.line(dx, dy + 66, dx + dw, dy + 66, stroke=T["line"])
    cy = dy + 66 + 14
    if spec.get("steps"):
        cy = draw_steps(g, dx + 22, cy, dw - 44, spec["steps"])
    cy = draw_blocks(g, dx + 22, cy + 6, dw - 44, spec.get("blocks"), spec)
    fh = 56
    g.line(dx, dy + dh - fh, dx + dw, dy + dh - fh, stroke=T["line"])
    bx = dx + dw - 16
    for it in reversed(spec.get("buttons", [{"label": "Cancel"}, {"label": "Create", "primary": True}])):
        bw = tw(it["label"], 12.5, bold=True) + 34
        bx -= bw
        g.rect(bx, dy + dh - fh + 13, bw, 30, fill=T["brand"] if it.get("primary") else T["surface"],
               stroke=None if it.get("primary") else T["line2"], rx=6)
        g.btext(bx, dy + dh - fh + 13, bw, 30, it["label"], size=12.5, anchor="middle",
                fill="#ffffff" if it.get("primary") else T["brand"], weight=600)
        bx -= 10


KINDS = {"cockpit": kind_cockpit, "bas": kind_bas, "terminal": kind_terminal,
         "fiori": kind_fiori, "hana": kind_hana, "dialog": kind_dialog}


# ------------------------------------------------------------------------- API
def render(spec: dict) -> tuple[str, dict]:
    kind = spec.get("kind", "cockpit")
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r} (have {sorted(KINDS)})")
    w = int(spec.get("w", 1440))
    h = int(spec.get("h", 900))
    g = G(w, h)
    KINDS[kind](g, spec)
    callouts(g, spec)
    meta = dict(key=spec.get("key"), kind=kind, w=w, h=h,
                bottom=round(g.bottom, 1), texts=len(g.texts),
                callouts=len(spec.get("callouts") or []), forced=getattr(g, "forced", 0))
    if g.bottom > h - 8:
        raise ValueError(f"content overflows canvas: ink bottom {g.bottom:g} > {h - 8} "
                         f"(spec {spec.get('key')}) — shorten the blocks or raise 'h'")
    return g.svg(), meta


def render_one(path: str, out: str | None = None, verbose=True) -> dict:
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    svg, meta = render(spec)
    out = out or os.path.splitext(path)[0] + ".svg"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    if verbose:
        warn = f"  ! forced={meta['forced']}" if meta.get("forced") else ""
        print(f"OK  {os.path.basename(out):38s} {len(svg):6d} B  {meta['kind']:9s} "
              f"texts={meta['texts']:3d}  bottom={meta['bottom']}{warn}")
    return meta


def main(argv):
    if "--all" in argv:
        i = argv.index("--all")
        src = argv[i + 1]
        outdir = argv[argv.index("--outdir") + 1] if "--outdir" in argv else "."
        os.makedirs(outdir, exist_ok=True)
        files = sorted(f for f in os.listdir(src) if f.endswith(".json"))
        index = {}
        bad = 0
        for f in files:
            try:
                meta = render_one(os.path.join(src, f),
                                  os.path.join(outdir, os.path.splitext(f)[0] + ".svg"))
                index[meta["key"] or os.path.splitext(f)[0]] = meta
            except Exception as e:                      # noqa: BLE001
                bad += 1
                print(f"FAIL {f}: {e}")
        with open(os.path.join(outdir, "figkit.json"), "w", encoding="utf-8") as fh:
            json.dump(index, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"\n{len(files) - bad}/{len(files)} screens rendered -> {outdir}")
        return 1 if bad else 0
    if "--one" in argv:
        src = argv[argv.index("--one") + 1]
        out = argv[argv.index("--out") + 1] if "--out" in argv else None
        render_one(src, out)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
