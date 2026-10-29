"""Side art of the guild chooser: Varian (Alliance, Fable's side) and Garrosh (Horde, NightShift's side).

Varian is mirrored so he faces Garrosh across the cut. Both are resized for the web; fades and placement
are done in CSS. Originals stay in site/assets-src/chooser/. Needs pillow (local venv).

Usage:
    .venv/Scripts/python scripts/make_chooser_art.py
"""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "site" / "assets-src" / "chooser", ROOT / "site" / "public" / "chooser"
WIDTH = 1600  # shown on half a wide screen (cropped to cover) or full phone width


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, mirror in (("varian.webp", True), ("garrosh.webp", False)):
        img = Image.open(SRC / name).convert("RGB")
        if mirror:
            img = ImageOps.mirror(img)
        img = img.resize((WIDTH, round(img.height * WIDTH / img.width)), Image.LANCZOS)
        out = OUT / (Path(name).stem + ".webp")
        img.save(out, quality=74, method=6)
        print(out.relative_to(ROOT), img.size, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
