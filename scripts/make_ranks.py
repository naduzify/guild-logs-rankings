"""PvP rank badges: the official Alliance rank icons, padded with blue so the whole emblem fits the round badge,
plus a red set for the Horde guild pages (ranks/horde/), where the icons' blue is turned red.

The site shows each icon cut to a circle (clip-path: circle(46%)), which used to crop the corners of
emblems that fill the square (chevrons, bars, helmet horns). Each icon is shrunk to EMBLEM of the
badge and laid on a radial blue background in the icons' own tones; its square edges are feathered
so the original frame does not show. For the Horde set, the icon's blue pixels (field and rim) take a red
hue, the silver and gold of the emblem stay. Originals stay in site/assets-src/ranks/. Needs pillow (local venv).

Usage:
    .venv/Scripts/python scripts/make_ranks.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "site" / "assets-src" / "ranks", ROOT / "site" / "public" / "ranks"
SIZE = 112          # output px (badges are shown at 20 to 34 px: 2x and more for sharp screens)
EMBLEM = 0.70       # share of the badge taken by the icon
TRIM = 2            # px cut off each side of the 56px source (dark rim of the original frame)
# Background per set: blue from the icons' own centre and rim; red in the Horde theme's tones.
SETS = {"": ((38, 92, 214), (10, 28, 112)), "horde": ((214, 38, 48), (112, 10, 18))}
BLUE = (120, 200)   # PIL hue range (0-255) of the icons' blue
RED_HUE = 252       # about 355 degrees


def background(centre, edge):
    bg = Image.new("RGB", (SIZE, SIZE), edge)
    px = bg.load()
    c = (SIZE - 1) / 2
    for y in range(SIZE):
        for x in range(SIZE):
            t = min(1.0, ((x - c) ** 2 + (y - c) ** 2) ** 0.5 / (SIZE * 0.5))
            px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(centre, edge))
    return bg


def redden(icon):
    """Blue pixels take a red hue (saturation and value kept); greys, silver and gold do not change."""
    h, s, v = icon.convert("HSV").split()
    blue = Image.eval(h, lambda x: 255 if BLUE[0] <= x <= BLUE[1] else 0)
    blue = Image.composite(blue, Image.new("L", h.size, 0), Image.eval(s, lambda x: 255 if x > 50 else 0))
    h = Image.composite(Image.new("L", h.size, RED_HUE), h, blue)
    return Image.merge("HSV", (h, s, v)).convert("RGB")


def main():
    side = round(SIZE * EMBLEM)
    off = (SIZE - side) // 2
    # Feathered square mask: the icon fades into the background over its outer few pixels.
    feather = max(2, side // 24)
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).rounded_rectangle((feather, feather, side - 1 - feather, side - 1 - feather), radius=feather * 2, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(feather / 1.6))
    files = sorted(SRC.glob("*.jpg"), key=lambda p: int(p.stem))
    for name, (centre, edge) in SETS.items():
        out = OUT / name
        out.mkdir(parents=True, exist_ok=True)
        for path in files:
            icon = Image.open(path).convert("RGB")
            w, h = icon.size
            icon = icon.crop((TRIM, TRIM, w - TRIM, h - TRIM)).resize((side, side), Image.LANCZOS)
            if name == "horde":
                icon = redden(icon)
            badge = background(centre, edge)
            badge.paste(icon, (off, off), mask)
            badge.save(out / path.name, quality=92)
        print(f"{len(files)} badges -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
