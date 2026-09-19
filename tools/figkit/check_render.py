#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rasterise figkit SVGs with headless Chrome and report ink statistics.

Used as the "I cannot see the image" gate: proves each screen actually draws
(non-blank), that the light/dark chrome is present, and that the red callout
colour appears.  Chrome is spawned one process per image, so never run this
concurrently with another Chrome-spawning tool on this machine.
"""
import os
import re
import struct
import subprocess
import sys
import tempfile
import zlib

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def rasterize(svg: str, out_png: str, w: int, h: int) -> None:
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--screenshot={out_png}", f"--window-size={w},{h}",
                        "--default-background-color=00000000", f"file://{os.path.abspath(svg)}"],
                       check=True, capture_output=True, timeout=90, cwd=td)


def read_png(path: str):
    """Minimal PNG decoder: returns (w, h, pixels as list of (r,g,b)) — 8-bit RGB/RGBA."""
    data = open(path, "rb").read()
    pos, w, h, idat, bitd, ctype = 8, 0, 0, b"", 8, 6
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bitd, ctype = struct.unpack(">IIBB", chunk[:10])
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    raw = zlib.decompress(idat)
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    stride = w * ch
    out, prev = [], bytearray(stride)
    i = 0
    for _ in range(h):
        f = raw[i]
        i += 1
        line = bytearray(raw[i:i + stride])
        i += stride
        for x in range(stride):
            a = line[x - ch] if x >= ch else 0
            b = prev[x]
            c = prev[x - ch] if x >= ch else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        out.append(bytes(line))
        prev = line
    return w, h, ch, out


def stats(png: str) -> dict:
    w, h, ch, rows = read_png(png)
    ink = 0
    red = 0
    dark = 0
    nonwhite = 0
    total = w * h
    step = 3
    for y in range(0, h, step):
        r = rows[y]
        for x in range(0, w, step):
            o = x * ch
            px = r[o:o + 3]
            if px[0] > 246 and px[1] > 246 and px[2] > 246:
                continue
            nonwhite += 1
            if px[0] < 90 and px[1] < 90 and px[2] < 90:
                dark += 1
            if px[0] > 130 and px[1] < 80 and px[2] < 80:
                red += 1
            ink += 1
    n = max(1, (w // step) * (h // step))
    return dict(w=w, h=h, ink_pct=round(ink * 100.0 / n, 1),
                dark_pct=round(dark * 100.0 / n, 1), red_px=red)


def main(argv):
    figdir = argv[0] if argv else "assets/fig"
    tmp = tempfile.mkdtemp(prefix="figcheck_")
    svgs = sorted(f for f in os.listdir(figdir) if f.endswith(".svg"))
    bad = 0
    for f in svgs:
        m = re.search(r'viewBox="0 0 (\d+) (\d+)"', open(os.path.join(figdir, f), encoding="utf-8").read())
        w, h = (int(m.group(1)), int(m.group(2))) if m else (1440, 900)
        png = os.path.join(tmp, f[:-4] + ".png")
        try:
            rasterize(os.path.join(figdir, f), png, w, h)
            s = stats(png)
        except Exception as e:                                    # noqa: BLE001
            print(f"NG   {f:34s} render failed: {e}")
            bad += 1
            continue
        ok = s["ink_pct"] > 2 and s["red_px"] > 20
        bad += 0 if ok else 1
        print(f"{'OK  ' if ok else 'NG  '} {f:34s} {s['w']}x{s['h']}  ink {s['ink_pct']:5.1f}%  "
              f"dark {s['dark_pct']:4.1f}%  callout-red {s['red_px']:4d}px")
    print(f"\n{len(svgs) - bad}/{len(svgs)} screens draw.  PNGs: {tmp}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
