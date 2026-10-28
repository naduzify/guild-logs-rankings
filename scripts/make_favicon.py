"""PNG favicons from the official World of Warcraft: Forever favicon (SVG).

The SVG is only filled paths styled by CSS classes, so it is rasterised here with
fontTools (path parsing) and Pillow, supersampled. Needs fonttools and pillow in
the local venv (not pipeline requirements). Writes favicon-32.png,
apple-touch-icon.png and icon-512.png next to the SVG, centred on a square.

Usage:
    .venv/Scripts/python scripts/make_favicon.py site/public/favicon.svg
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from fontTools.pens.basePen import BasePen
from fontTools.svgLib.path import parse_path
from PIL import Image, ImageChops, ImageDraw

SS = 8  # supersampling factor
MARGIN = 0.03  # share of the square left empty on each side
# Stray layers left in the source file (bright green slivers), not part of the logo.
SKIP_FILLS = {"#0dff0d"}


class Poly(BasePen):
    """Flattens path contours into polygons."""
    def __init__(self): super().__init__(None); self.polys, self.cur = [], []
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, a, b, c):
        p0 = self.cur[-1]
        for i in range(1, 13):
            t = i / 12; u = 1 - t
            self.cur.append((u**3*p0[0]+3*u*u*t*a[0]+3*u*t*t*b[0]+t**3*c[0], u**3*p0[1]+3*u*u*t*a[1]+3*u*t*t*b[1]+t**3*c[1]))
    def _qCurveToOne(self, a, b):
        p0 = self.cur[-1]
        for i in range(1, 13):
            t = i / 12; u = 1 - t
            self.cur.append((u*u*p0[0]+2*u*t*a[0]+t*t*b[0], u*u*p0[1]+2*u*t*a[1]+t*t*b[1]))
    def _closePath(self):
        if self.cur: self.polys.append(self.cur)
        self.cur = []
    _endPath = _closePath


def load(svg_path):
    """[(fill, polygons)] in drawing order, plus the bounding box of what is drawn."""
    root = ET.parse(svg_path).getroot()
    ns = {"s": "http://www.w3.org/2000/svg"}
    css = "".join(s.text or "" for s in root.iter("{http://www.w3.org/2000/svg}style"))
    fills = {m[0]: m[1].lower() for m in re.findall(r"\.([\w-]+)\s*\{\s*fill:\s*(#[0-9a-fA-F]{3,6})", css)}
    shapes = []
    for el in root.iterfind(".//s:path", ns):
        fill = el.get("fill") or fills.get(el.get("class", ""), "#000000")
        if fill in SKIP_FILLS:
            continue
        pen = Poly(); parse_path(el.get("d"), pen)
        shapes.append((fill, pen.polys))
    # Framed on the drawing, not the viewBox: the source viewBox has empty space around the logo.
    pts = [pt for _, polys in shapes for poly in polys for pt in poly]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return shapes, (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def render(shapes, box, size, background=None):
    big = size * SS
    x0, y0, w, h = box
    k = big * (1 - 2 * MARGIN) / max(w, h)
    ox, oy = (big - w * k) / 2 - x0 * k, (big - h * k) / 2 - y0 * k
    img = Image.new("RGBA", (big, big), background or (0, 0, 0, 0))
    for fill, polys in shapes:
        # Even-odd within a path, so inner contours cut holes as in the browser for these simple shapes.
        mask = Image.new("L", (big, big), 0)
        for poly in polys:
            m = Image.new("L", (big, big), 0)
            ImageDraw.Draw(m).polygon([(ox + x * k, oy + y * k) for x, y in poly], fill=255)
            mask = ImageChops.difference(mask, m)
        img.paste(Image.new("RGB", (big, big), fill), (0, 0), mask)
    return img.resize((size, size), Image.LANCZOS)


svg = Path(sys.argv[1])
shapes, box = load(svg)
render(shapes, box, 32).save(svg.parent / "favicon-32.png")
render(shapes, box, 180, background="#061529").save(svg.parent / "apple-touch-icon.png")  # iOS wants an opaque square
render(shapes, box, 512).save(svg.parent / "icon-512.png")
print("ok", len(shapes), "paths")
