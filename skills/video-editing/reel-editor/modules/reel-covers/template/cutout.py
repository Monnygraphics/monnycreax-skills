"""Remove the studio background from the arch-style photos -> cutouts/<name>.png.

Run with the rembg venv:  ~/.rembg-venv/Scripts/python cutout.py
"""
import re
import sys
from pathlib import Path

from PIL import Image
from rembg import new_session, remove

HERE = Path(__file__).resolve().parent
src = (HERE / "thumbs.js").read_text(encoding="utf-8")
# photos used by arch-style entries
names = re.findall(r'style: "arch".*?photo: "([^"]+)"', src)
if len(sys.argv) > 1:
    names = sys.argv[1:]

out = HERE / "cutouts"
out.mkdir(exist_ok=True)
session = new_session("isnet-general-use")
for name in names:
    dst = out / f"{name}.png"
    if dst.exists():
        continue
    img = Image.open(HERE / "photos" / f"{name}.jpg").convert("RGB")
    cut = remove(img, session=session, alpha_matting=True,
                 alpha_matting_foreground_threshold=240,
                 alpha_matting_background_threshold=10)
    cut = cut.crop(cut.getbbox())  # trim to the subject
    cut.save(dst)
    print("cut", name, cut.size, flush=True)
