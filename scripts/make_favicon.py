"""Site favicon: a Fable "F" in Cinzel Black, parchment gradient on Alliance navy.

Cinzel (SIL Open Font License) is close to the Fable logo lettering. Needs fonttools
and pillow in the local venv (not pipeline requirements). Writes favicon.svg,
favicon-32.png, apple-touch-icon.png and icon-512.png into OUT_DIR.

Usage:
    curl -L -o Cinzel.ttf "https://github.com/google/fonts/raw/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf"
    .venv/Scripts/python scripts/make_favicon.py Cinzel.ttf site/public
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
WEIGHT = 900
font = instantiateVariableFont(TTFont(src), {"wght": WEIGHT})
gs = font.getGlyphSet()
glyph = gs[font.getBestCmap()[ord("F")]]
bp = BoundsPen(gs); glyph.draw(bp); x0, y0, x1, y1 = bp.bounds

# Fit the glyph in a 64-unit box with padding, y flipped for SVG.
S, PAD = 64, 13
scale = (S - 2 * PAD) / max(x1 - x0, y1 - y0)
dx = (S - (x1 - x0) * scale) / 2 - x0 * scale
dy = (S + (y1 - y0) * scale) / 2 + y0 * scale
pen = SVGPathPen(gs)
glyph.draw(TransformPen(pen, (scale, 0, 0, -scale, dx, dy)))
d = pen.getCommands()

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <radialGradient id="bg" cx="50%" cy="20%" r="85%">
      <stop offset="0" stop-color="#1c4f9e"/><stop offset=".55" stop-color="#0b2a4e"/><stop offset="1" stop-color="#061529"/>
    </radialGradient>
    <linearGradient id="gold" x1="0" y1="0" x2=".25" y2="1">
      <stop offset=".1" stop-color="#ffffff"/><stop offset="1" stop-color="#eccaa1"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="14" fill="url(#bg)"/>
  <path d="{d}" fill="url(#gold)"/>
</svg>
'''
open(f"{out}/favicon.svg", "w", encoding="utf-8").write(svg)

# PNG fallbacks (apple-touch-icon, browsers without SVG favicons): same drawing with Pillow.
def png(size, name, radius):
    k = size / S
    bg = Image.new("RGB", (size, size), "#061529")
    top = Image.new("RGB", (size, size), "#1c4f9e")
    fade = Image.radial_gradient("L").resize((size * 2, size * 2)).crop((size // 2, int(size * 0.8), size // 2 + size, int(size * 0.8) + size))
    bg = Image.composite(bg, top, fade.point(lambda v: min(255, int(v * 1.3))))
    mask_big = Image.new("L", (S * 16, S * 16), 0)
    # Render the glyph path itself to match the SVG exactly.
    from fontTools.pens.basePen import BasePen
    class Poly(BasePen):
        def __init__(self, gs): super().__init__(gs); self.polys, self.cur = [], []
        def _moveTo(self, p): self.cur = [p]
        def _lineTo(self, p): self.cur.append(p)
        def _curveToOne(self, a, b, c):
            p0 = self.cur[-1]
            for i in range(1, 9):
                t = i / 8; u = 1 - t
                self.cur.append((u**3*p0[0]+3*u*u*t*a[0]+3*u*t*t*b[0]+t**3*c[0], u**3*p0[1]+3*u*u*t*a[1]+3*u*t*t*b[1]+t**3*c[1]))
        def _qCurveToOne(self, a, b):
            p0 = self.cur[-1]
            for i in range(1, 9):
                t = i / 8; u = 1 - t
                self.cur.append((u*u*p0[0]+2*u*t*a[0]+t*t*b[0], u*u*p0[1]+2*u*t*a[1]+t*t*b[1]))
        def _closePath(self): self.polys.append(self.cur); self.cur = []
    pp = Poly(gs); glyph.draw(TransformPen(pp, (scale * 16, 0, 0, -scale * 16, dx * 16, dy * 16)))
    # Union of contours: the variable font keeps overlapping contours, and F has no counters.
    for poly in pp.polys:
        m = Image.new("L", mask_big.size, 0); ImageDraw.Draw(m).polygon(poly, fill=255)
        mask_big = Image.frombytes("L", mask_big.size, bytes(a | b for a, b in zip(mask_big.tobytes(), m.tobytes())))
    mask = mask_big.resize((size, size), Image.LANCZOS)
    grad = Image.new("RGB", (1, 256))
    for y in range(256):
        t = max(0, min(1, (y / 255 - .1) / .9))
        grad.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip((255, 255, 255), (0xec, 0xca, 0xa1))))
    gold = grad.resize((size, size))
    bg.paste(gold, (0, 0), mask)
    if radius:
        r = Image.new("L", (size * 4, size * 4), 0)
        ImageDraw.Draw(r).rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1), radius=int(radius * k * 4), fill=255)
        out_img = Image.new("RGBA", (size, size)); out_img.paste(bg, (0, 0), r.resize((size, size), Image.LANCZOS))
    else:
        out_img = bg
    out_img.save(f"{out}/{name}")

png(32, "favicon-32.png", 14)
png(180, "apple-touch-icon.png", 0)  # iOS rounds the corners itself
png(512, "icon-512.png", 14)
print("ok", WEIGHT, round(scale, 4))
