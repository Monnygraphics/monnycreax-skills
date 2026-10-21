"""Paper-collage pieces for the `collage` b-roll layout (gbro-collage-broll look, made locally, no video API).

Each input photo becomes a transparent PNG: subject cut out (rembg), black-and-white halftone dots, and a
warm-cream paper keyline around the edge. The overlay assembles the pieces on a flat colour field.

Run with the rembg venv:
  ~/.rembg-venv/Scripts/python collage.py <img> [<img> ...] --out <dir>/collage [--no-cut name.jpg] [--dot 9]
Flat objects (a chessboard, a calendar, a document) can skip the cutout with --no-cut and get a straight-edged
paper card instead.
"""
import argparse
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

CREAM = (246, 238, 220, 255)


def halftone(gray, dot, angle=45):
    """Classic amplitude-modulated halftone: one dot per cell, radius from local darkness, screen at `angle`."""
    w, h = gray.size
    big = gray.rotate(angle, expand=True, fillcolor=255)
    bw, bh = big.size
    small = big.resize((max(1, bw // dot), max(1, bh // dot)), Image.BOX)
    out = Image.new("L", (bw * 2, bh * 2), 255)          # draw at 2x for smooth dots
    d = ImageDraw.Draw(out)
    px = small.load()
    for y in range(small.size[1]):
        for x in range(small.size[0]):
            dark = 1 - px[x, y] / 255
            if dark < 0.04:
                continue
            r = dot * 1.13 * math.sqrt(dark)                # area-true: ink coverage = darkness (cell is 2*dot at 2x)
            cx, cy = (x + 0.5) * dot * 2, (y + 0.5) * dot * 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    out = out.resize((bw, bh), Image.LANCZOS).rotate(-angle, expand=False, fillcolor=255)
    l, t = (bw - w) // 2, (bh - h) // 2
    return out.crop((l, t, l + w, t + h))


def piece(src, out, cut=True, dot=5, keyline=10, session=None, max_side=1100):
    img = Image.open(src).convert("RGB")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    if cut:
        from rembg import remove
        rgba = remove(img, session=session, alpha_matting=True,
                      alpha_matting_foreground_threshold=240, alpha_matting_background_threshold=10)
        alpha = rgba.split()[3].point(lambda a: 255 if a > 128 else 0)   # crisp machine-cut edge
    else:
        alpha = Image.new("L", img.size, 255)
    # tone-map from the subject's own pixels (mask), not the whole photo, and lift shadows: a global curve
    # turns dark skin under a dark hat into a solid black blob once it goes through the dot screen
    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray, cutoff=1, mask=alpha)
    gray = gray.point(lambda v: int(255 * (v / 255) ** 0.7))
    # local contrast: lift each pixel against its neighbourhood (large-radius unsharp mask), so a face in shadow
    # keeps its features next to a bright, busy shirt, then normalise the shadows of the subject itself
    import numpy as np
    g = np.asarray(gray, dtype=np.float32)
    local = np.asarray(gray.filter(ImageFilter.GaussianBlur(max(8, min(gray.size) // 18))), dtype=np.float32)
    g = np.clip(local * 0.35 + 128 * 0.65 + (g - local) * 1.9, 0, 255)
    gray = ImageOps.autocontrast(Image.fromarray(g.astype(np.uint8)), cutoff=1, mask=alpha)
    ink = halftone(gray, dot)
    pad = keyline + 4
    W, H = img.size[0] + 2 * pad, img.size[1] + 2 * pad
    a = Image.new("L", (W, H), 0); a.paste(alpha, (pad, pad))
    if cut:  # smooth the silhouette a little so the keyline reads as a scissor cut, not a mask
        a = a.filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: 255 if v > 128 else 0)
    ring = a.filter(ImageFilter.MaxFilter(keyline * 2 + 1)) if cut else a
    base = Image.new("RGBA", (W, H), CREAM)
    paper = Image.new("RGBA", (W, H), (0, 0, 0, 0)); paper.paste(base, (0, 0), ring if cut else a)
    # the printed halftone sits inside the silhouette, on warm off-white stock
    stock = Image.new("RGB", (W, H), (236, 232, 222))
    inked = Image.new("RGB", (W, H), (236, 232, 222)); inked.paste(ink.convert("RGB"), (pad, pad))
    inked = ImageChops.multiply(stock, inked)
    if not cut:  # straight card: inset the print to leave a cream border
        kb = keyline * 2   # straight cards get a wider cream border so the paper edge reads at reel size
        inner = Image.new("L", (W, H), 0); ImageDraw.Draw(inner).rectangle([kb, kb, W - kb - 1, H - kb - 1], fill=255)
        a = inner
    paper.paste(inked, (0, 0), a)
    paper = paper.crop(paper.getbbox())
    paper.save(out)
    return paper.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-cut", nargs="*", default=[], help="file names to keep as straight paper cards")
    ap.add_argument("--dot", type=int, default=5, help="halftone cell size in px (bigger = coarser print)")
    ap.add_argument("--keyline", type=int, default=10)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    session = None
    if any(Path(p).name not in a.no_cut for p in a.images):
        from rembg import new_session
        session = new_session("isnet-general-use")
    for p in a.images:
        p = Path(p)
        dst = out / (p.stem + ".png")
        size = piece(p, dst, cut=p.name not in a.no_cut, dot=a.dot, keyline=a.keyline, session=session)
        print(f"{dst}  {size[0]}x{size[1]}")


if __name__ == "__main__":
    main()
