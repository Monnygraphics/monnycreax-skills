#!/usr/bin/env python3
"""
cover_calc.py - spine width and full-wrap cover size for a paperback, plus the cover-designer brief numbers.

    python cover_calc.py --pages 212 --trim 6x9 [--paper cream|white|color|premium-color] [--platform kdp|ingram]
    python cover_calc.py --pdf build/interior.pdf --trim 6x9 --paper cream

KDP spine = page count x paper factor (KDP's published per-page thickness):
    white 0.002252 in, cream 0.0025 in, standard colour 0.002252 in, premium colour 0.002347 in.
Full cover width = bleed + back + spine + front + bleed, bleed 0.125 in each outside edge.
KDP allows spine text only from 80 pages; keep spine text 0.0625 in clear of each spine edge.
IngramSpark paper calipers vary by stock; the numbers here are close but ALWAYS download
Ingram's own cover template (ingramspark.com/cover-template-generator) for the final file.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_book import TRIMS, kdp_min_gutter  # noqa: E402

KDP_PAPER = {"white": 0.002252, "cream": 0.0025, "color": 0.002252, "premium-color": 0.002347}
# Approximate IngramSpark calipers (inches per page) for common stocks; verify with their template.
INGRAM_PAPER = {"white": 0.0022, "cream": 0.0025, "color": 0.0021, "premium-color": 0.0021}
# Print-shop stocks: approximate thickness per printed page (half a sheet), inches.
PRINTSHOP_PAPER = {"70gsm": 0.045 / 25.4, "80gsm": 0.05 / 25.4, "90gsm": 0.055 / 25.4, "100gsm": 0.06 / 25.4,
                   "cream": 0.05 / 25.4, "white": 0.05 / 25.4}
BLEED = 0.125


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", type=int)
    ap.add_argument("--pdf", help="read the page count from the interior PDF")
    ap.add_argument("--trim", default="6x9")
    ap.add_argument("--paper", default="cream", help="kdp/ingram: white|cream|color|premium-color; printshop: 70gsm|80gsm|90gsm|100gsm")
    ap.add_argument("--platform", default="kdp", choices=["kdp", "ingram", "printshop"])
    a = ap.parse_args()
    pages = a.pages
    if a.pdf:
        import fitz
        pages = len(fitz.open(a.pdf))
    if not pages:
        sys.exit("give --pages or --pdf")
    key = a.trim.lower().replace(" ", "")
    if key not in TRIMS:
        sys.exit(f"unknown trim {a.trim}; use one of {', '.join(TRIMS)}")
    w, h = TRIMS[key]
    table = {"kdp": KDP_PAPER, "ingram": INGRAM_PAPER, "printshop": PRINTSHOP_PAPER}[a.platform]
    if a.paper not in table:
        sys.exit(f"paper '{a.paper}' not known for {a.platform}; use one of {', '.join(table)}")
    factor = table[a.paper]
    global BLEED
    if a.platform == "printshop":
        BLEED = 3 / 25.4
    spine = pages * factor
    full_w = BLEED + w + spine + w + BLEED
    full_h = BLEED + h + BLEED
    print(f"# Cover numbers: {pages} pages, {w:.2f} x {h:.2f} in ({w * 25.4:.0f} x {h * 25.4:.0f} mm), "
          f"{a.paper} paper, {a.platform.upper()}\n")
    print(f"- Spine width: {spine:.4f} in ({spine * 25.4:.2f} mm)")
    print(f"- Full wrap (with bleed): {full_w:.4f} x {full_h:.4f} in  ({full_w * 25.4:.1f} x {full_h * 25.4:.1f} mm)")
    print(f"- At 300 ppi: {round(full_w * 300)} x {round(full_h * 300)} px")
    print(f"- Layout left to right (mm): bleed {BLEED * 25.4:.1f} | back {w * 25.4:.1f} | spine {spine * 25.4:.2f} | front {w * 25.4:.1f} | bleed {BLEED * 25.4:.1f}")
    print(f"- Front cover alone: {w:.2f} x {h:.2f} in; ebook KDP ebook cover 1600 x 2560 px (1:1.6) minimum ideal")
    if a.platform == "kdp":
        if pages < 80:
            print("- Spine text: NOT allowed (KDP needs 80+ pages). Leave the spine plain or a single colour.")
        else:
            print(f"- Spine text: allowed. Keep it within {max(spine - 0.125, 0):.4f} in (0.0625 in clear each side).")
        print("- Barcode: KDP places it on the back, lower right, 2 x 1.2 in. Keep that area clear.")
    elif a.platform == "ingram":
        print("- Spine text: Ingram recommends 48+ pages; check the template's safe zone.")
        print("- Barcode: Ingram's template includes the ISBN barcode box; do not move it.")
    else:
        print("- Bleed: 3 mm on every edge (print-shop standard). Spine is an ESTIMATE: ask the shop to confirm")
        print("  the spine for their paper and binding before the cover is finalised.")
        print("- Spine text: fine from about 80 pages at 80gsm (spine over 4 mm); below that keep it plain.")
        print("- Barcode: if the book has an ISBN, leave a 50 x 30 mm clear box on the back cover.")
    print(f"- Interior gutter needed at this page count (KDP minimum): {kdp_min_gutter(pages)} in")
    print("- Safe zone: keep text and faces 0.125 in inside the trim on all edges (0.25 in is safer).")
    if pages < 24:
        print("! Under 24 pages: KDP will not print a paperback this short.")


if __name__ == "__main__":
    main()
