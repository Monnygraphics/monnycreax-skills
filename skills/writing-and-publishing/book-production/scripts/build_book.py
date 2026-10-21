#!/usr/bin/env python3
"""
build_book.py - one book project in, every format out (the bookpub idea).

    python build_book.py PROJECT_DIR [--formats pdf,epub,docx,html] [--trim 6x9] [--out DIR] [--keep-html]

Formats
  pdf   print interior. Chrome/Edge headless renders HTML+CSS, then a PyMuPDF pass
        stamps running heads and folios, so the layout rules a printer expects hold:
        chapters open on recto (blank versos inserted), no heads on openers or blanks,
        roman folios in front matter, arabic from the first chapter or introduction,
        mirrored margins with a KDP-safe gutter for the final page count, TOC page
        numbers filled in from the real pagination, PDF bookmarks.
  epub  EPUB 3 (with an NCX for older readers), reflowable, cover if assets/cover.jpg.
  docx  editable Word manuscript: trim page size, mirrored margins, Garamond spec,
        chapters on odd pages, PAGE fields in the footer, a TOC field Word refreshes on open.
  html  the print HTML with fonts beside it, so the author can open and re-export it.

Needs: Python 3.10+, python-docx, PyYAML, PyMuPDF (fitz), lxml, and Chrome or Edge.
Set CHROME_PATH if the browser is not found.
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bookcore as bc  # noqa: E402

SKILL = Path(__file__).resolve().parent.parent
FONT_DIR = SKILL / "assets" / "fonts"

# Amazon KDP paperback trims (inches). IngramSpark accepts all of these and more.
TRIMS = {"5x8": (5, 8), "5.06x7.81": (5.06, 7.81), "5.25x8": (5.25, 8), "5.5x8.5": (5.5, 8.5),
         "6x9": (6, 9), "6.14x9.21": (6.14, 9.21), "6.69x9.61": (6.69, 9.61), "7x10": (7, 10),
         "7.44x9.69": (7.44, 9.69), "7.5x9.25": (7.5, 9.25), "8x10": (8, 10), "8.25x6": (8.25, 6),
         "8.25x8.25": (8.25, 8.25), "8.5x8.5": (8.5, 8.5), "8.5x11": (8.5, 11),
         "a5": (148 / 25.4, 210 / 25.4), "b5": (176 / 25.4, 250 / 25.4), "royal": (156 / 25.4, 234 / 25.4)}

# KDP minimum inside margin (gutter) by page count.
KDP_GUTTER = [(150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875)]

WPP = {"a5": 250, "5x8": 230, "5.25x8": 245, "5.5x8.5": 270, "6x9": 320, "6.14x9.21": 330, "7x10": 410, "8.5x11": 520}


def kdp_min_gutter(pages: int) -> float:
    for limit, g in KDP_GUTTER:
        if pages <= limit:
            return g
    return 0.875


def auto_margins(trim, pages, layout):
    m = layout.get("margins")
    if isinstance(m, dict):
        return {k: float(m[k]) for k in ("top", "bottom", "inside", "outside")}
    w, h = trim
    base = 0.75 if w >= 6 else 0.65
    inside = max(kdp_min_gutter(pages) + 0.3, base + 0.1)
    return {"top": round(base + 0.05, 3), "bottom": round(base + 0.1, 3),
            "inside": round(inside, 3), "outside": round(base - 0.1, 3)}


# --------------------------------------------------------------------------
# fonts
# --------------------------------------------------------------------------
FONT_SEARCH = [FONT_DIR, Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
               Path(os.environ.get("LOCALAPPDATA", "~")) / "Microsoft/Windows/Fonts",
               Path.home() / "Library/Fonts", Path("/Library/Fonts"), Path("/System/Library/Fonts"),
               Path("/usr/share/fonts"), Path.home() / ".fonts", Path.home() / ".local/share/fonts"]
# Static instances only: Chrome writes non-default instances of variable fonts as
# Type 3 fonts, which IngramSpark rejects. assets/fonts/README.md says how to add more.
BUNDLED_FAMILIES = {"EB Garamond": "EBGaramond", "Lora": "Lora", "Source Serif 4": "SourceSerif4",
                    "Inter": "Inter", "Cormorant Garamond": "CormorantGaramond"}
WEIGHTS = {"Regular": 400, "Medium": 500, "SemiBold": 600, "Bold": 700}


def _scan_bundled():
    out = {}
    for fam, stem in BUNDLED_FAMILIES.items():
        faces = []
        for f in sorted(FONT_DIR.glob(f"{stem}-*.ttf")):
            style = f.stem[len(stem) + 1:]
            italic = style.endswith("Italic")
            wname = style[:-6] if italic else style
            faces.append((f.name, "italic" if italic else "normal", WEIGHTS.get(wname or "Regular", 400)))
        if faces:
            out[fam] = faces
    return out


BUNDLED = _scan_bundled()


def find_font_file(family: str, italic=False, bold=False) -> Path | None:
    key = family.replace(" ", "").lower()
    want = "bolditalic" if bold and italic else "bold" if bold else "italic" if italic else "regular"
    cands = []
    for d in FONT_SEARCH:
        d = d.expanduser()
        if not d.exists():
            continue
        try:
            files = list(d.rglob("*.[ot]tf")) if d.name != "Fonts" else list(d.glob("*.[ot]tf"))
        except OSError:
            continue
        for f in files:
            n = f.stem.replace(" ", "").replace("-", "").replace("_", "").lower()
            n = re.sub(r"\[.*\]", "", n)
            if n.startswith(key):
                rest = n[len(key):]
                score = 0 if rest in (want, "") and not (rest == "" and want != "regular") else \
                    1 if rest.startswith(want) else 5 if not any(x in rest for x in ("bold", "italic", "light", "thin", "black", "medium", "semi", "extra")) else 9
                if want == "regular" and rest in ("", "regular", "vf", "variablefontwght"):
                    score = 0
                cands.append((score, len(rest), f))
    if not cands:
        return None
    cands.sort()
    return cands[0][2]


def font_css(families, dest: Path | None) -> str:
    css = []
    for fam in families:
        if fam in BUNDLED:
            for fname, style, weight in BUNDLED[fam]:
                src = FONT_DIR / fname
                if dest:
                    (dest / "fonts").mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest / "fonts" / fname)
                css.append(f"@font-face {{ font-family: '{fam}'; src: url('fonts/{fname}') format('truetype'); "
                           f"font-style: {style}; font-weight: {weight}; }}")
    return "\n".join(css)


# --------------------------------------------------------------------------
# HTML assembly
# --------------------------------------------------------------------------
def esc(s):
    return html.escape(str(s or ""), quote=True)


def section_html(s: bc.Section, meta, layout, toc_entries=None, page_numbers=None) -> str:
    t = s.type
    attrs = f'id="{s.slug}" class="sec sec-{t} {s.matter}{" compact" if s.meta.get("compact") else ""}"'
    if s.meta.get("auto"):
        if t == "title":
            sub = f'<p class="tp-subtitle">{esc(meta["subtitle"])}</p>' if meta.get("subtitle") else ""
            pub = f'<p class="tp-publisher">{esc(meta["publisher"])}</p>' if meta.get("publisher") else ""
            return (f'<section {attrs}><h1 class="ghost">{esc(meta["title"])}</h1><div class="tp">'
                    f'<p class="tp-title">{esc(meta["title"])}</p>{sub}'
                    f'<p class="tp-author">{esc(meta["author"])}</p>{pub}</div></section>')
        if t == "autograph":
            lines = layout.get("autograph_lines") or ["Signed for", "By", "Date", "Note"]
            rows = "".join(f'<div class="ag-row"><span>{esc(l)}</span><span class="ag-line"></span></div>' for l in lines)
            return (f'<section {attrs}><h1 class="ghost">Signed Copy</h1><div class="ag">'
                    f'<p class="ag-title">{esc(meta["title"])}</p><p class="ag-head">{esc(s.meta.get("heading", "A signed copy"))}</p>'
                    f'{rows}<div class="ag-row ag-note"><span class="ag-line"></span></div></div></section>')
        if t == "halftitle":
            return f'<section {attrs}><h1 class="ghost">{esc(meta["title"])}</h1><p class="ht-title">{esc(meta["title"])}</p></section>'
        if t == "copyright":
            year = meta.get("year") or datetime.date.today().year
            lines = [f"Copyright &copy; {esc(year)} {esc(meta['author'])}", esc(meta.get("rights") or "All rights reserved."),
                     "No part of this book may be reproduced, stored in a retrieval system, or transmitted in any form "
                     "or by any means without the prior written permission of the publisher, except for brief "
                     "quotations in reviews and articles."]
            if meta.get("copyright_extra"):
                lines.append(esc(meta["copyright_extra"]))
            if meta.get("publisher"):
                lines.append("Published by " + esc(meta["publisher"]) + (", " + esc(meta["location"]) if meta.get("location") else ""))
            if meta.get("edition"):
                lines.append(esc(meta["edition"]) + (" " + esc(year) if str(year) not in str(meta["edition"]) else ""))
            if meta.get("isbn_print"):
                lines.append("ISBN " + esc(meta["isbn_print"]) + " (paperback)")
            if meta.get("isbn_ebook"):
                lines.append("ISBN " + esc(meta["isbn_ebook"]) + " (ebook)")
            if meta.get("contact"):
                lines.append(esc(meta["contact"]))
            body = "".join(f"<p>{l}</p>" for l in lines)
            return f'<section {attrs}><h1 class="ghost">Copyright</h1><div class="cp">{body}</div></section>'
        if t == "toc":
            rows = []
            for e in toc_entries or []:
                pg = (page_numbers or {}).get(e.slug, "")
                lab = f'<span class="toc-label">{esc(e.label)}</span>' if e.label else ""
                show_pg = layout.get("toc_page_numbers", True)
                pgspan = f'<span class="toc-pg">{esc(pg) if page_numbers else "000"}</span>' if show_pg else ""
                cls = "toc-part" if e.type == "part" else ("toc-front" if e.matter == "front" else "toc-entry")
                rows.append(f'<li class="{cls}"><a href="#{e.slug}">{lab}<span class="toc-title">{esc(e.title)}</span>{pgspan}</a></li>')
            return f'<section {attrs}><h1 class="sec-title">{esc(s.title)}</h1><ol class="toc">{"".join(rows)}</ol></section>'
    body = bc.md_to_html(s.body_md)
    if layout.get("_soft_hyphens"):
        body = soft_hyphenate(body, layout.get("_lang", "en"))
    lab_text = s.label
    if s.label and layout.get("label_numeric") and s.type != "part":
        n = bc.number_value(s.label.split()[-1])
        lab_text = f"{n:02d}" if n else s.label
    label = f'<p class="chapter-label">{esc(lab_text)}</p>' if s.label else ""
    sub = f'<p class="chapter-subtitle">{esc(s.subtitle)}</p>' if s.subtitle else ""
    if t == "part":
        return f'<section {attrs}>{label}<h1 class="sec-title">{esc(s.title)}</h1>{sub}<div class="part-body">{body}</div></section>'
    if t in ("dedication", "epigraph"):
        return f'<section {attrs}><h1 class="ghost">{esc(s.title)}</h1><div class="ded">{body}</div></section>'
    return f'<section {attrs}><header class="opener">{label}<h1 class="sec-title">{bc.inline_md(s.title)}</h1>{sub}</header>{body}</section>'


_HYPH = {}


def soft_hyphenate(html_text: str, lang: str = "en") -> str:
    """Insert soft hyphens into long lowercase words in text nodes. Headless Chrome often has no
    hyphenation dictionary, so justified lines stretch their word spaces instead: the 'cheap' look.
    pyphen (the WeasyPrint hyphenator) gives the break points; Chrome breaks only where needed."""
    try:
        import pyphen
    except ImportError:
        return html_text
    code = {"en": "en_GB"}.get(lang, lang)
    if code not in _HYPH:
        try:
            _HYPH[code] = pyphen.Pyphen(lang=code, left=3, right=3)
        except KeyError:
            _HYPH[code] = pyphen.Pyphen(lang="en_GB", left=3, right=3)
    dic = _HYPH[code]

    def words(m):
        return re.sub(r"(?<![\w­])([a-zà-ÿ]{7,})(?![\w­])", lambda w: dic.inserted(w.group(1), hyphen="­"), m.group(0))
    # text nodes only, never inside tags or attribute values
    return re.sub(r">[^<]+<", words, html_text)


def house_style_css(layout, live_h):
    """Whole-book looks learned from reference books (layout.style). Appended after the base CSS."""
    st = layout.get("style")
    bf, hf = layout["body_font"], layout["heading_font"]
    if st == "unbrand":   # UNBRAND-END: airy, plain, confident
        return f"""
.opener {{ padding-top: {round(live_h * 0.05, 2)}in; min-height: {round(live_h * 0.36, 2)}in; margin-bottom: 0; }}
.chapter-label {{ font-family: '{bf}', serif; text-transform: none; letter-spacing: 0; font-weight: 700; font-size: 0.95em; color: #111; margin-bottom: 0.5em; }}
.opener h1, .sec-part h1 {{ text-transform: uppercase; font-weight: 700; font-size: 2.05em; letter-spacing: 0.01em; margin: 0.15em 0 0.45em; }}
.chapter-subtitle {{ font-size: 0.9em; margin-top: 0; }}
.opener + p.first::first-line {{ font-variant: normal; letter-spacing: 0; }}
p {{ text-indent: 1.5em; margin-bottom: {layout.get("para_space", "0.45em")}; }}
p.first, h2 + p, h3 + p, h4 + p, blockquote + p, ul + p, ol + p, .opener + p {{ text-indent: 0; }}
h3 {{ font-family: '{bf}', serif; font-weight: 700; font-size: 1em; text-align: left; margin: 2.4em 0 0.55em; }}
h4 {{ font-family: '{bf}', serif; font-weight: 700; font-style: italic; font-variant: normal; letter-spacing: 0; font-size: 0.97em; margin: 1.5em 0 0.4em; }}
.sec-toc h1, .sec-preface h1, .sec-introduction h1, .sec-acknowledgements-front h1 {{ text-transform: uppercase; font-weight: 700; }}
.toc-label {{ text-transform: none; letter-spacing: 0; font-family: '{bf}', serif; font-weight: 700; color: #111; font-size: 0.85em; }}
.toc-part {{ font-variant: normal; font-weight: 700; }}
"""
    if st == "isi":   # Blueprints of Dominion: modern, bold sans titles, block paragraphs
        return f"""
.opener {{ padding-top: {round(live_h * 0.07, 2)}in; margin-bottom: 1.8em; }}
.chapter-label {{ font-family: '{bf}', serif; font-size: 3.1em; letter-spacing: 0; text-transform: none; color: #222; font-weight: 400; margin-bottom: 0.35em; line-height: 1; }}
.chapter-label::after {{ content: ""; display: block; width: 1.1em; margin: 0.18em auto 0; border-bottom: 0.08em solid #444; }}
.opener h1, .sec-part h1 {{ font-family: '{hf}', sans-serif; text-transform: uppercase; font-weight: 700; font-size: 1.35em; letter-spacing: 0.01em; margin: 0.6em 0 0.7em; }}
.chapter-subtitle {{ display: inline-block; background: #ececec; color: #555; font-style: normal; font-family: '{hf}', sans-serif; font-size: 0.78em; padding: 0.55em 1.2em; margin-top: 0; line-height: 1.4; }}
.opener + p.first::first-line {{ font-variant: normal; letter-spacing: 0; }}
p {{ text-indent: 0; margin-bottom: {layout.get("para_space", "0.75em")}; }}
h3 {{ font-family: '{hf}', sans-serif; font-weight: 700; font-size: 1.02em; text-align: left; margin: 1.7em 0 0.55em; }}
h4 {{ font-family: '{hf}', sans-serif; font-weight: 700; font-variant: normal; letter-spacing: 0; font-size: 0.9em; margin: 1.3em 0 0.4em; }}
blockquote {{ margin: 1em 1.2em; }}
.sec-toc h1, .sec-preface h1, .sec-introduction h1, .sec-acknowledgements-front h1 {{ font-family: '{hf}', sans-serif; font-weight: 700; text-transform: uppercase; font-size: 1.35em; }}
.toc-label {{ font-family: '{hf}', sans-serif; color: #333; }}
"""
    return ""


def build_css(layout, trim, margins, fonts_css):
    w, h = trim
    bf = layout["body_font"]
    hf = layout["heading_font"]
    lf = layout.get("label_font") or hf
    size = float(layout["body_size"])
    lead = float(layout["leading"])
    acc = layout.get("accent") or "#1a1a1a"
    live_h = h - margins["top"] - margins["bottom"]
    indent = "1.2em" if layout.get("first_line_indent", True) else "0"
    para_gap = "0" if layout.get("first_line_indent", True) else "0.6em"
    hyph = "auto" if layout.get("hyphenate", True) else "manual"
    return f"""{fonts_css}
@page {{ size: {w}in {h}in; margin: {margins['top']}in {margins['outside']}in {margins['bottom']}in {margins['inside']}in; }}
@page :left {{ margin-left: {margins['outside']}in; margin-right: {margins['inside']}in; }}
@page :right {{ margin-left: {margins['inside']}in; margin-right: {margins['outside']}in; }}
html {{ font-family: '{bf}', 'EB Garamond', Garamond, Georgia, serif; font-size: {size}pt; line-height: {lead}; color: #111; font-weight: {int(layout.get("body_weight", 400))}; }}
body {{ margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.sec {{ break-before: page; }}
.sec:first-child {{ break-before: auto; }}
.blank-page {{ break-before: page; height: 1px; }}
.page-break {{ break-after: page; }}
h1, h2, h3, h4 {{ font-family: '{hf}', serif; font-weight: {int(layout.get("heading_weight", 500))}; break-after: avoid; line-height: 1.2; }}
.ag {{ padding-top: {round(live_h * 0.12, 2)}in; }}
.ag p {{ text-align: center; text-indent: 0; }}
.ag-title {{ font-family: '{hf}', serif; font-size: 1.3em; margin-bottom: 0.4em; }}
.ag-head {{ font-family: '{lf}', serif; text-transform: uppercase; letter-spacing: 0.18em; font-size: 0.72em; color: {acc}; margin-bottom: 3em; }}
.ag-row {{ display: flex; align-items: flex-end; gap: 0.8em; margin: 0 0 2.4em; font-style: italic; }}
.ag-line {{ flex: 1; border-bottom: 0.6pt solid #555; height: 1.2em; }}
.ag-note {{ margin-top: -1em; }}
table {{ width: 100%; border-collapse: collapse; margin: 1em 0; font-size: 0.88em; break-inside: avoid; }}
th, td {{ border-bottom: 0.5pt solid #999; padding: 0.3em 0.4em; text-align: left; vertical-align: top; }}
th {{ font-family: '{lf}', serif; border-bottom: 1pt solid #333; }}
td p, th p {{ text-indent: 0; text-align: left; margin: 0; }}
h1.ghost {{ position: absolute; font-size: 1px; line-height: 1px; color: transparent; margin: 0; height: 1px; overflow: hidden; }}
p {{ margin: 0; text-align: justify; hyphens: {hyph}; -webkit-hyphens: {hyph}; orphans: 2; widows: 2; text-indent: {indent}; margin-bottom: {para_gap}; text-wrap: pretty; }}
p.first, h2 + p, h3 + p, h4 + p, blockquote + p, ul + p, ol + p, figure + p, .scene-break + p, .opener + p, aside + p {{ text-indent: 0; }}
.opener {{ padding-top: {round(live_h * 0.18, 2)}in; margin-bottom: 2.2em; text-align: center; }}
.chapter-label {{ font-family: '{lf}', serif; text-indent: 0; text-align: center; text-transform: uppercase; letter-spacing: 0.18em; font-size: 0.78em; color: {acc}; margin-bottom: 0.9em; }}
.opener h1, .sec-part h1, .sec-toc h1 {{ font-size: 1.9em; margin: 0; text-align: center; }}
.chapter-subtitle {{ text-indent: 0; text-align: center; font-style: italic; margin-top: 0.6em; }}
.opener + p.first::first-line {{ font-variant: small-caps; letter-spacing: 0.04em; }}
h2 {{ font-size: 1.18em; margin: 1.5em 0 0.6em; }}
h3 {{ font-size: 1.2em; margin: 1.5em 0 0.55em; }}
h4 {{ font-family: '{bf}', serif; font-size: 0.9em; font-variant: small-caps; letter-spacing: 0.06em; font-weight: 600; margin: 1.15em 0 0.35em; }}
h3 + h4 {{ margin-top: 0.4em; }}
h4 {{ font-size: 1em; margin: 1em 0 0.3em; }}
blockquote {{ margin: 1em 1.6em; font-size: 0.95em; font-style: {"italic" if layout.get("quote_italic") else "normal"}; }}
blockquote em {{ font-style: {"normal" if layout.get("quote_italic") else "italic"}; }}
blockquote p {{ text-indent: 0; margin-bottom: 0.4em; text-align: left; text-wrap: pretty; }}
blockquote .attribution {{ text-align: right; font-style: italic; font-size: 0.92em; }}
ul, ol {{ margin: 0.6em 0 0.8em; padding-left: 1.6em; }}
li {{ margin-bottom: 0.25em; text-align: left; }}
.scene-break {{ text-align: center; text-indent: 0; margin: 0.9em 0; letter-spacing: 0.3em; }}
figure {{ margin: 1em 0; text-align: center; break-inside: avoid; }}
figure img {{ max-width: 100%; max-height: {round(live_h * 0.7, 2)}in; }}
figcaption {{ font-size: 0.85em; font-style: italic; margin-top: 0.4em; }}
sup.fn-ref {{ font-size: 0.65em; line-height: 0; }}
.chapter-notes {{ margin-top: 2em; font-size: 0.85em; border-top: 0.5pt solid #999; padding-top: 0.6em; }}
.chapter-notes li {{ text-align: left; }}
a {{ color: inherit; text-decoration: none; }}
code {{ font-family: Consolas, 'Courier New', monospace; font-size: 0.88em; }}
.tp {{ height: {round(live_h - 0.12, 2)}in; display: flex; flex-direction: column; text-align: center; }}
.tp p {{ text-indent: 0; text-align: center; }}
.tp-title {{ font-family: '{hf}', serif; font-size: 2.6em; line-height: 1.1; margin-top: {round(live_h * 0.22, 2)}in; }}
.tp-subtitle {{ font-style: italic; font-size: 1.2em; margin-top: 0.8em; }}
.tp-author {{ font-family: '{lf}', serif; text-transform: uppercase; letter-spacing: 0.16em; font-size: 0.95em; margin-top: auto; margin-bottom: 1.2in; }}
.tp-publisher {{ font-size: 0.8em; letter-spacing: 0.1em; text-transform: uppercase; }}
.ht-title {{ text-align: center; text-indent: 0; margin-top: {round(live_h * 0.3, 2)}in; font-family: '{hf}', serif; font-size: 1.5em; }}
.cp {{ height: {round(live_h - 0.12, 2)}in; display: flex; flex-direction: column; justify-content: flex-end; font-size: 0.78em; line-height: 1.45; }}
.cp p {{ text-indent: 0; text-align: left; margin-bottom: 0.7em; hyphens: manual; }}
.todo {{ color: #b00; }}
.ded {{ padding-top: {round(live_h * 0.28, 2)}in; text-align: center; font-style: italic; }}
.ded p {{ text-align: center; text-indent: 0; margin-bottom: 0.5em; }}
.sec-part {{ text-align: center; padding-top: {round(live_h * 0.3, 2)}in; }}
.part-body p {{ text-align: center; text-indent: 0; font-style: italic; margin-top: 1em; }}
{house_style_css(layout, live_h)}
.compact .opener {{ padding-top: 0; min-height: 0; margin-bottom: 1em; }}
.compact p {{ margin-bottom: 0.25em; }}
.sec-toc h1 {{ margin-bottom: 1.6em; padding-top: {round(live_h * 0.08, 2)}in; }}
ol.toc {{ list-style: none; padding: 0; margin: 0; }}
ol.toc li {{ margin: 0 0 0.55em; }}
ol.toc a {{ display: flex; align-items: baseline; gap: 0.5em; }}
.toc-label {{ font-family: '{lf}', serif; font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.12em; color: {acc}; flex: 0 0 11.5em; }}
.toc-title {{ flex: 1; }}
.toc-pg {{ font-variant-numeric: tabular-nums lining-nums; min-width: 2.2em; text-align: right; }}
li.toc-part {{ margin-top: 1em; font-variant: small-caps; letter-spacing: 0.05em; }}
.callout {{ border-left: 2pt solid {acc}; padding: 0.4em 0 0.4em 0.9em; margin: 1em 0; break-inside: avoid; }}
.callout-label {{ display: block; font-family: '{lf}', serif; font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.12em; color: {acc}; margin-bottom: 0.3em; }}
.callout p {{ text-indent: 0; }}
.pull-quote {{ font-size: 1.3em; line-height: 1.3; font-style: italic; text-align: center; margin: 1.2em 1em; break-inside: avoid; }}
.pull-quote p {{ text-align: center; text-indent: 0; }}
"""


def assemble_html(meta, layout, sections, trim, margins, fonts_css, page_numbers=None, blanks_before=()):
    css = build_css(layout, trim, margins, fonts_css)
    toc_entries = [s for s in sections if s.toc and s.type != "toc"]
    parts = []
    for s in sections:
        if s.slug in blanks_before:
            parts.append('<div class="blank-page" aria-hidden="true"></div>')
        parts.append(section_html(s, meta, layout, toc_entries, page_numbers))
    if "__end__" in blanks_before:
        parts.append('<div class="blank-page" aria-hidden="true"></div>')
    lang = esc(meta.get("language") or "en")
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{esc(meta["title"])}</title>'
            f'<style>{css}</style></head><body>' + "\n".join(parts) + "</body></html>")


# --------------------------------------------------------------------------
# Chrome rendering
# --------------------------------------------------------------------------
def find_browser():
    env = os.environ.get("CHROME_PATH")
    cands = [env] if env else []
    cands += [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    for c in cands:
        if c and Path(c).exists():
            return c
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        p = shutil.which(n)
        if p:
            return p
    return None


def render_pdf(html_path: Path, pdf_path: Path, browser: str):
    prof = Path(tempfile.mkdtemp(prefix="bookprof-"))
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--no-first-run",
           "--disable-extensions", "--generate-pdf-document-outline", f"--user-data-dir={prof}",
           "--virtual-time-budget=15000", f"--print-to-pdf={pdf_path.resolve()}", html_path.resolve().as_uri()]
    if pdf_path.exists():
        pdf_path.unlink()
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    shutil.rmtree(prof, ignore_errors=True)
    if not pdf_path.exists():
        raise RuntimeError("Browser did not write a PDF. Try setting CHROME_PATH, or open the HTML and print it.")


def section_starts(pdf_path: Path, sections):
    import fitz
    doc = fitz.open(str(pdf_path))
    toc = [e for e in doc.get_toc(simple=True) if e[0] == 1]
    n = len(doc)
    doc.close()
    if len(toc) != len(sections):
        raise RuntimeError(f"Outline has {len(toc)} top-level entries but the book has {len(sections)} sections. "
                           "Each section needs exactly one <h1>; check the Markdown for raw <h1> tags.")
    return [e[2] for e in toc], n


def roman(n: int) -> str:
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
            (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


NO_FOLIO = {"halftitle", "title", "copyright", "dedication", "epigraph", "part", "also-by", "autograph"}
ARABIC_START = {"introduction", "prologue", "part", "chapter"}


def page_plan(sections, starts, total):
    """Map every physical page to (section index, is_opener) and a folio string."""
    owner = []
    for p in range(1, total + 1):
        idx = max(i for i, st in enumerate(starts) if st <= p) if p >= starts[0] else 0
        owner.append(idx)
    arabic_from = next((starts[i] for i, s in enumerate(sections) if s.type in ARABIC_START), starts[0])
    folios = []
    for p in range(1, total + 1):
        folios.append(str(p - arabic_from + 1) if p >= arabic_from else roman(p))
    return owner, folios


def stamp_pdf(pdf_in: Path, pdf_out: Path, meta, layout, sections, starts, blank_pages, margins, trim):
    import fitz
    doc = fitz.open(str(pdf_in))
    total = len(doc)
    owner, folios = page_plan(sections, starts, total)
    head_font_name = layout.get("head_font") or layout.get("label_font") or layout["heading_font"]
    ff = find_font_file(head_font_name, italic=bool(layout.get("head_italic"))) or find_font_file(layout["body_font"])
    head_upper = layout.get("head_upper", bool(layout.get("label_font")))
    folio_ff = find_font_file(layout["body_font"]) or ff
    verso = meta["author"] if layout.get("verso_head", "author") == "author" and meta.get("author") else meta["title"]
    w_pt, h_pt = trim[0] * 72, trim[1] * 72
    head_size = float(layout.get("head_size") or (7.5 if head_upper else 8.5))
    folio_size = max(8.5, float(layout["body_size"]) - 1.5)
    for p in range(1, total + 1):
        page = doc[p - 1]
        sidx = owner[p - 1]
        s = sections[sidx]
        if p in blank_pages:
            continue
        opener = p == starts[sidx]
        recto = p % 2 == 1
        inside = margins["inside"] * 72
        outside = margins["outside"] * 72
        left = inside if recto else outside
        right = w_pt - (outside if recto else inside)
        center = (left + right) / 2
        kw = {}
        if ff:
            kw = {"fontname": "headf", "fontfile": str(ff)}
        fkw = {"fontname": "foliof", "fontfile": str(folio_ff)} if folio_ff else {}
        if layout.get("running_heads", True) and not opener and s.type not in NO_FOLIO and s.type != "toc":
            text = (meta["title"] if layout.get("recto_head") == "title" else s.title) if recto else verso
            text = re.sub(r"[*_`]", "", text)
            if head_upper:
                text = text.upper()
            spacing = 1.2 if head_upper else 0.3
            font = fitz.Font(fontfile=str(ff)) if ff else fitz.Font("tiro")
            tw = font.text_length(text, fontsize=head_size) + spacing * max(len(text) - 1, 0)
            while tw > (right - left) * 0.8 and len(text) > 10:
                text = text[: int(len(text) * 0.85)].rstrip() + "\u2026"
                tw = font.text_length(text, fontsize=head_size) + spacing * max(len(text) - 1, 0)
            y = margins["top"] * 72 * 0.55
            # letter-spaced: place char by char
            x = center - tw / 2
            for ch in text:
                page.insert_text((x, y), ch, fontsize=head_size, color=(0.25, 0.25, 0.25), **kw)
                x += font.text_length(ch, fontsize=head_size) + spacing
        show_folio = s.type not in NO_FOLIO and not (opener and layout.get("drop_folio_on_openers", False))
        if show_folio:
            f = folios[p - 1]
            font = fitz.Font(fontfile=str(folio_ff)) if folio_ff else fitz.Font("tiro")
            tw = font.text_length(f, fontsize=folio_size)
            y = h_pt - margins["bottom"] * 72 * 0.45
            page.insert_text((center - tw / 2, y), f, fontsize=folio_size, color=(0.15, 0.15, 0.15), **fkw)
    # bookmarks: drop ghost entries for title/copyright, keep the rest
    toc = []
    for i, s in enumerate(sections):
        if s.type in ("title", "copyright", "halftitle"):
            continue
        label = (s.label + ": " if s.label else "") + re.sub(r"[*_`]", "", s.title)
        toc.append([1, label, starts[i]])
    doc.set_toc(toc)
    doc.set_metadata({"title": meta["title"], "author": meta["author"], "subject": meta.get("description", ""),
                      "creator": "book-production skill", "producer": "Chrome + PyMuPDF"})
    doc.save(str(pdf_out), garbage=3, deflate=True)
    doc.close()
    return folios


def build_pdf(meta, layout, sections, trim, out_dir: Path, browser, keep_html=False, log=print):
    words = sum(bc.word_count(bc.md_plain(s.body_md)) for s in sections)
    est_pages = max(24, int(words / WPP.get(layout["trim"], 320)) + 12)
    margins = auto_margins(trim, est_pages, layout)
    work = out_dir / "_work"
    work.mkdir(parents=True, exist_ok=True)
    fonts_css = font_css({layout["body_font"], layout["heading_font"], layout.get("label_font") or layout["heading_font"]}, work)
    for fam in {layout["body_font"], layout["heading_font"], layout.get("label_font")} - {None, ""}:
        if fam not in BUNDLED and not find_font_file(fam):
            log(f"  ! font '{fam}' not found on this machine; the browser will substitute. Install it or pick another.")
    assets = Path(sections[0].path).parents[2] / "assets" if sections and sections[0].path else None
    if assets is None:
        for s in sections:
            if s.path:
                assets = Path(s.path).parents[2] / "assets"
                break
    if assets and assets.exists():
        shutil.copytree(assets, work / "assets", dirs_exist_ok=True)

    layout = {**layout, "_soft_hyphens": layout.get("hyphenate", True), "_lang": (meta.get("language") or "en")[:2]}
    recto_needed = {s.slug for s in sections if s.recto and (layout.get("chapter_start", "right") == "right"
                                                              or s.matter == "front" or s.type == "part")}
    if layout.get("blank_pages") is False:      # the client wants no empty pages anywhere
        recto_needed = set()
    extra_blanks = set()
    if layout.get("blank_after_title"):          # an empty page right after the title page
        ti = next((i for i, s in enumerate(sections) if s.type == "title"), None)
        if ti is not None and ti + 1 < len(sections):
            extra_blanks.add(sections[ti + 1].slug)
    if layout.get("blank_at_end"):
        extra_blanks.add("__end__")
    blanks = set(extra_blanks)
    page_numbers = None
    for attempt in range(6):
        html_doc = assemble_html(meta, layout, sections, trim, margins, fonts_css, page_numbers, blanks)
        hp = work / "book.html"
        hp.write_text(html_doc, encoding="utf-8")
        raw = work / "raw.pdf"
        render_pdf(hp, raw, browser)
        starts, total = section_starts(raw, sections)
        # 1) gutter for the real page count
        need = auto_margins(trim, total, layout)
        if need != margins and not isinstance(layout.get("margins"), dict):
            log(f"  margins adjusted for {total} pages: {need}")
            margins = need
            continue
        # 2) recto starts: find sections that open on an even page
        fix, offset = [], 0
        for s, st in zip(sections, starts):
            if s.slug in recto_needed and (st + offset) % 2 == 0:
                fix.append(s.slug)
                offset += 1
        if fix:
            blanks |= set(fix)
            log(f"  inserting blank verso before: {', '.join(fix)}")
            continue
        # 3) TOC numbers from the real pagination
        _, folios = page_plan(sections, starts, total)
        want = {s.slug: folios[st - 1] for s, st in zip(sections, starts)}
        if page_numbers != want and any(s.type == "toc" for s in sections) and layout.get("toc_page_numbers", True):
            page_numbers = want
            continue
        break
    else:
        log("  ! pagination did not settle in 6 passes; check the PDF by eye")
    if layout.get("even_page_count", layout.get("blank_pages") is not False) and total % 2 == 1:
        blanks.add("__end__")
        html_doc = assemble_html(meta, layout, sections, trim, margins, fonts_css, page_numbers, blanks)
        hp.write_text(html_doc, encoding="utf-8")
        render_pdf(hp, raw, browser)
        starts, total = section_starts(raw, sections)
    import fitz
    d = fitz.open(str(raw))
    blank_pages = {i + 1 for i in range(len(d)) if not d[i].get_text().strip() and not d[i].get_images()}
    d.close()
    final = out_dir / f"{bc.slugify(meta['title'])}-interior-{layout['trim']}.pdf"
    stamp_pdf(raw, final, meta, layout, sections, starts, blank_pages, margins, trim)
    if keep_html:
        html_out = out_dir / "html"
        if html_out.exists():
            shutil.rmtree(html_out)
        shutil.copytree(work, html_out, ignore=shutil.ignore_patterns("*.pdf"))
    report = {"pdf": str(final), "pages": total, "trim": layout["trim"], "margins_in": margins,
              "kdp_min_gutter_in": kdp_min_gutter(total), "blank_versos": sorted(b for b in blanks if b != "__end__"),
              "section_starts": {s.slug: st for s, st in zip(sections, starts)}, "words": words}
    shutil.rmtree(work, ignore_errors=True)
    return report


# --------------------------------------------------------------------------
# EPUB 3
# --------------------------------------------------------------------------
EPUB_CSS = """body { font-family: serif; line-height: 1.45; margin: 0 4%; }
h1 { font-size: 1.6em; text-align: center; margin: 2.5em 0 1.2em; font-weight: normal; }
.chapter-label { text-align: center; text-transform: uppercase; letter-spacing: 0.15em; font-size: 0.8em; margin-top: 3em; text-indent: 0; }
.chapter-label + h1 { margin-top: 0.6em; }
.chapter-subtitle { text-align: center; font-style: italic; text-indent: 0; }
p { margin: 0; text-indent: 1.2em; text-align: justify; }
p.first, h2 + p, h3 + p, blockquote + p, ul + p, ol + p, .scene-break + p, aside + p { text-indent: 0; }
h2 { font-size: 1.2em; margin: 1.5em 0 0.5em; } h3 { font-size: 1.05em; font-style: italic; }
blockquote { margin: 1em 1.5em; } blockquote p { text-indent: 0; }
.attribution { text-align: right; font-style: italic; }
.scene-break { text-align: center; text-indent: 0; margin: 1em 0; }
.tp { text-align: center; margin-top: 25%; } .tp p { text-align: center; text-indent: 0; }
.tp-title { font-size: 2em; } .tp-subtitle { font-style: italic; } .tp-author { margin-top: 3em; text-transform: uppercase; letter-spacing: 0.1em; }
.cp p { text-indent: 0; font-size: 0.85em; margin-bottom: 0.6em; text-align: left; }
.ded { margin-top: 30%; text-align: center; font-style: italic; } .ded p { text-align: center; text-indent: 0; }
.callout { border-left: 2px solid #444; padding-left: 0.8em; margin: 1em 0; }
.pull-quote { font-style: italic; text-align: center; font-size: 1.15em; margin: 1em; }
.chapter-notes { font-size: 0.85em; margin-top: 2em; }
figure { text-align: center; margin: 1em 0; } img { max-width: 100%; }
h1.ghost { display: none; } .toc-pg { display: none; } .todo { color: #b00; }
"""


def to_xhtml_fragment(h: str) -> str:
    from lxml import etree, html as lh
    frags = lh.fragments_fromstring(h)
    out = []
    for f in frags:
        if isinstance(f, str):
            out.append(html.escape(f))
        else:
            for el in f.iter():
                if el.tag == "img" and el.get("src", "").startswith("assets/"):
                    el.set("src", "../" + el.get("src"))
            out.append(etree.tostring(f, method="xml", encoding="unicode"))
    return "\n".join(out)


def build_epub(meta, layout, sections, out_dir: Path, project: Path, log=print):
    lang = meta.get("language") or "en"
    ident = meta.get("isbn_ebook") or f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, meta['title'] + meta['author'])}"
    files, manifest, spine, nav = [], [], [], []
    cover = next((p for p in [project / "assets" / n for n in ("cover.jpg", "cover.jpeg", "cover.png", "cover-front.jpg", "cover-front.png")] if p.exists()), None)
    toc_entries = [s for s in sections if s.toc and s.type != "toc"]
    for i, s in enumerate(sections):
        if s.type == "toc":
            continue  # nav.xhtml is the contents in an ebook
        name = f"{i:03d}-{s.slug}.xhtml"
        h = section_html(s, meta, {**layout, "toc_page_numbers": False}, toc_entries)
        h = re.sub(r"^<section[^>]*>|</section>$", "", h)
        if s.label and not s.meta.get("auto"):
            h = h.replace('<header class="opener">', "").replace("</header>", "", 1)
        body = to_xhtml_fragment(h)
        epub_type = {"chapter": "chapter", "part": "part", "copyright": "copyright-page", "title": "titlepage",
                     "dedication": "dedication", "preface": "preface", "foreword": "foreword", "introduction": "introduction",
                     "acknowledgements": "acknowledgments", "about-author": "appendix", "appendix": "appendix",
                     "epilogue": "epilogue", "glossary": "glossary", "bibliography": "bibliography", "notes": "endnotes"}.get(s.type, "")
        et = f' epub:type="{epub_type}"' if epub_type else ""
        doc = (f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" '
               f'xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}"><head><meta charset="utf-8"/>'
               f'<title>{esc(s.title)}</title><link rel="stylesheet" type="text/css" href="../css/book.css"/></head>'
               f'<body><section{et} class="sec-{s.type}">{body}</section></body></html>')
        files.append((f"OEBPS/text/{name}", doc))
        manifest.append(f'<item id="s{i}" href="text/{name}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="s{i}"/>')
        if s.toc or s.type in ("title",):
            label = (s.label + ": " if s.label else "") + re.sub(r"[*_`]", "", s.title)
            nav.append((label, f"text/{name}", s))
    imgs = []
    if (project / "assets").exists():
        for p in (project / "assets").rglob("*"):
            if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"):
                rel = p.relative_to(project).as_posix()
                mt = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif",
                      ".svg": "image/svg+xml", ".webp": "image/webp"}[p.suffix.lower()]
                props = ' properties="cover-image"' if cover and p == cover else ""
                iid = "cover-img" if props else "img" + str(len(imgs))
                imgs.append((p, f"OEBPS/{rel}"))
                manifest.append(f'<item id="{iid}" href="{rel}" media-type="{mt}"{props}/>')
    if cover:
        crel = cover.relative_to(project).as_posix()
        files.insert(0, ("OEBPS/text/cover.xhtml",
                         f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" '
                         f'xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}"><head><meta charset="utf-8"/><title>Cover</title>'
                         f'<style>body{{margin:0;text-align:center}} img{{max-width:100%;max-height:100%}}</style></head>'
                         f'<body epub:type="cover"><img src="../{crel}" alt="Cover"/></body></html>'))
        manifest.insert(0, '<item id="cover" href="text/cover.xhtml" media-type="application/xhtml+xml"/>')
        spine.insert(0, '<itemref idref="cover" linear="yes"/>')
    navli = "".join(f'<li><a href="{href}">{esc(t)}</a></li>' for t, href, _ in nav)
    first_body = next((href for t, href, s in nav if s.matter == "body"), nav[0][1] if nav else "")
    landmarks = f'<li><a epub:type="toc" href="nav.xhtml">Contents</a></li>' + (
        f'<li><a epub:type="bodymatter" href="{first_body}">Start</a></li>' if first_body else "")
    files.append(("OEBPS/nav.xhtml",
                  f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" '
                  f'xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}"><head><meta charset="utf-8"/>'
                  f'<title>Contents</title><link rel="stylesheet" type="text/css" href="css/book.css"/></head><body>'
                  f'<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>{navli}</ol></nav>'
                  f'<nav epub:type="landmarks" hidden=""><ol>{landmarks}</ol></nav></body></html>'))
    manifest.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
    ncx_points = "".join(f'<navPoint id="n{i}" playOrder="{i + 1}"><navLabel><text>{esc(t)}</text></navLabel>'
                         f'<content src="{href}"/></navPoint>' for i, (t, href, _) in enumerate(nav))
    files.append(("OEBPS/toc.ncx",
                  f'<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
                  f'<head><meta name="dtb:uid" content="{esc(ident)}"/></head><docTitle><text>{esc(meta["title"])}</text></docTitle>'
                  f'<navMap>{ncx_points}</navMap></ncx>'))
    manifest.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
    files.append(("OEBPS/css/book.css", EPUB_CSS))
    manifest.append('<item id="css" href="css/book.css" media-type="text/css"/>')
    modified = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opf_meta = [f'<dc:identifier id="bookid">{esc(ident)}</dc:identifier>', f'<dc:title>{esc(meta["title"])}</dc:title>',
                f'<dc:language>{esc(lang)}</dc:language>', f'<meta property="dcterms:modified">{modified}</meta>']
    if meta.get("author"):
        opf_meta.append(f'<dc:creator>{esc(meta["author"])}</dc:creator>')
    if meta.get("publisher"):
        opf_meta.append(f'<dc:publisher>{esc(meta["publisher"])}</dc:publisher>')
    if meta.get("description"):
        opf_meta.append(f'<dc:description>{esc(meta["description"])}</dc:description>')
    if meta.get("year"):
        opf_meta.append(f'<dc:date>{esc(meta["year"])}</dc:date>')
    opf_meta.append(f'<dc:rights>{esc(meta.get("rights", ""))}</dc:rights>')
    if cover:
        opf_meta.append('<meta name="cover" content="cover-img"/>')
    opf = (f'<?xml version="1.0" encoding="utf-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
           f'unique-identifier="bookid" xml:lang="{lang}"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           + "".join(opf_meta) + f'</metadata><manifest>{"".join(manifest)}</manifest>'
           f'<spine toc="ncx">{"".join(spine)}</spine></package>')
    files.append(("OEBPS/content.opf", opf))
    container = ('<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    # well-formedness check on every XML file before writing
    from lxml import etree
    problems = []
    for name, content in files:
        if name.endswith((".xhtml", ".opf", ".ncx")):
            try:
                etree.fromstring(content.encode("utf-8"))
            except etree.XMLSyntaxError as e:
                problems.append(f"{name}: {e}")
    out = out_dir / f"{bc.slugify(meta['title'])}.epub"
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        for name, content in files:
            z.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)
        for src, arc in imgs:
            z.write(src, arc, compress_type=zipfile.ZIP_DEFLATED)
    if problems:
        log("  ! EPUB XML problems:\n    " + "\n    ".join(problems[:10]))
    return {"epub": str(out), "chapters": len(nav), "xml_problems": problems, "cover": bool(cover)}


# --------------------------------------------------------------------------
# DOCX
# --------------------------------------------------------------------------
INLINE_TOKEN = re.compile(r"(\*\*\*.+?\*\*\*|\*\*.+?\*\*|(?<![\w*])\*(?!\s).+?(?<!\s)\*(?![\w*])|\[\^[^\]]+\])")


def add_inline(par, text, footnotes=None, base_italic=False):
    text = bc.smart_quotes(text)
    for part in INLINE_TOKEN.split(text):
        if not part:
            continue
        b = i = False
        if part.startswith("***") and part.endswith("***") and len(part) > 6:
            part, b, i = part[3:-3], True, True
        elif part.startswith("**") and part.endswith("**") and len(part) > 4:
            part, b = part[2:-2], True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            part, i = part[1:-1], True
        elif part.startswith("[^"):
            key = part[2:-1]
            if footnotes is not None and key in footnotes:
                n = list(footnotes).index(key) + 1
                r = par.add_run(str(n))
                r.font.superscript = True
                continue
        part = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", part).replace("`", "")
        r = par.add_run(part)
        r.bold = b or None
        r.italic = (i != base_italic) or None


def add_html_table(doc, html_src, size):
    """Simple <table> (rows of th/td text) -> a Word table."""
    from lxml import html as lh
    from docx.shared import Pt
    try:
        t = lh.fromstring(html_src)
    except Exception:
        return
    rows = [[c.text_content().strip() for c in tr.xpath("./th|./td")] for tr in t.iter("tr")]
    rows = [r for r in rows if r]
    if not rows:
        return
    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=cols)
    try:
        table.style = "Table Grid"
    except Exception:
        pass
    header = bool(t.xpath(".//th"))
    for i, r in enumerate(rows):
        for j in range(cols):
            cell = table.cell(i, j)
            cell.text = ""
            run = cell.paragraphs[0].add_run(r[j] if j < len(r) else "")
            run.font.size = Pt(size - 2)
            run.bold = (i == 0 and header) or None
            cell.paragraphs[0].paragraph_format.first_line_indent = None
    doc.add_paragraph()


def build_docx(meta, layout, sections, trim, out_dir: Path, log=print):
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt

    words = sum(bc.word_count(bc.md_plain(s.body_md)) for s in sections)
    est = max(24, int(words / 300) + 12)
    m = auto_margins(trim, est, layout)
    doc = Document()
    font = layout.get("docx_font") or "Garamond"
    size = float(layout.get("docx_size") or 12)
    spacing = float(layout.get("docx_line_spacing") or 1.5)
    st = doc.styles["Normal"]
    st.font.name = font
    st.element.rPr.rFonts.set(qn("w:eastAsia"), font)
    st.font.size = Pt(size)
    pf = st.paragraph_format
    pf.line_spacing = spacing
    pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.widow_control = True
    for name, sz, align in (("Heading 1", size * 1.8, WD_ALIGN_PARAGRAPH.CENTER), ("Heading 2", size * 1.25, WD_ALIGN_PARAGRAPH.LEFT),
                            ("Heading 3", size * 1.08, WD_ALIGN_PARAGRAPH.LEFT), ("Title", size * 2.6, WD_ALIGN_PARAGRAPH.CENTER)):
        hs = doc.styles[name]
        hs.font.name = layout.get("docx_heading_font") or font
        rpr = hs.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.insert(0, rf)
        for k in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rf.set(qn(k), layout.get("docx_heading_font") or font)
        for k in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rf.get(qn(k)) is not None:
                del rf.attrib[qn(k)]
        hs.font.size = Pt(sz)
        hs.font.bold = name != "Heading 3"
        hs.font.italic = name == "Heading 3"
        hs.font.color.rgb = None
        hs.paragraph_format.alignment = align
        hs.paragraph_format.space_before = Pt(size * (4 if name == "Heading 1" else 1.2))
        hs.paragraph_format.space_after = Pt(size * (1.6 if name == "Heading 1" else 0.5))
        hs.paragraph_format.keep_with_next = True
        hs.paragraph_format.line_spacing = 1.15
    # mirrored margins
    settings = doc.settings.element
    mm = OxmlElement("w:mirrorMargins")
    settings.insert(0, mm)
    upd = OxmlElement("w:updateFields")
    upd.set(qn("w:val"), "true")
    settings.append(upd)

    def setup(sec):
        sec.page_width, sec.page_height = Inches(trim[0]), Inches(trim[1])
        sec.top_margin, sec.bottom_margin = Inches(m["top"]), Inches(m["bottom"])
        sec.left_margin, sec.right_margin = Inches(m["inside"]), Inches(m["outside"])
        sec.footer_distance = Inches(max(0.3, m["bottom"] - 0.35))

    setup(doc.sections[0])
    footer = doc.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if layout.get("docx_page_numbers", True):
        r = footer.add_run()
        for tag, txt in (("begin", None), (None, " PAGE \\* MERGEFORMAT "), ("separate", None), (None, "1"), ("end", None)):
            if tag:
                el = OxmlElement("w:fldChar")
                el.set(qn("w:fldCharType"), tag)
                r._r.append(el)
            else:
                el = OxmlElement("w:instrText" if txt.startswith(" ") else "w:t")
                el.set(qn("xml:space"), "preserve")
                el.text = txt
                r._r.append(el)
        r.font.size = Pt(size - 2)
    toc_entries = [s for s in sections if s.toc and s.type != "toc"]
    first = True
    for s in sections:
        if not first:
            odd = s.recto and (layout.get("chapter_start", "right") == "right" or s.type == "part") and s.type != "copyright"
            if odd:
                ns = doc.add_section(WD_SECTION.ODD_PAGE)
                setup(ns)
            else:
                doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        first = False
        if s.meta.get("auto"):
            if s.type in ("title", "halftitle"):
                p = doc.add_paragraph(meta["title"], style="Title")
                p.paragraph_format.space_before = Pt(size * 12)
                if s.type == "title":
                    if meta.get("subtitle"):
                        sp = doc.add_paragraph()
                        sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        rr = sp.add_run(meta["subtitle"])
                        rr.italic = True
                        rr.font.size = Pt(size * 1.2)
                    ap_ = doc.add_paragraph()
                    ap_.paragraph_format.space_before = Pt(size * 16)
                    ap_.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    ra = ap_.add_run(meta["author"].upper())
                    ra.font.size = Pt(size)
                    if meta.get("publisher"):
                        pp = doc.add_paragraph()
                        pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        pp.add_run(meta["publisher"]).font.size = Pt(size - 2)
            elif s.type == "copyright":
                h = section_html(s, meta, layout)
                for k, line in enumerate(re.findall(r"<p>(.*?)</p>", h)):
                    txt = html.unescape(re.sub(r"<[^>]+>", "", line))
                    cp = doc.add_paragraph()
                    cp.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    cp.paragraph_format.space_after = Pt(6)
                    if k == 0:
                        cp.paragraph_format.space_before = Pt(size * 22)
                    cp.paragraph_format.line_spacing = 1.15
                    cp.add_run(txt).font.size = Pt(size - 3)
            elif s.type == "autograph":
                tp = doc.add_paragraph()
                tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                tp.paragraph_format.space_before = Pt(size * 6)
                tp.add_run(meta["title"]).font.size = Pt(size * 1.3)
                hp_ = doc.add_paragraph()
                hp_.alignment = WD_ALIGN_PARAGRAPH.CENTER
                hp_.paragraph_format.space_after = Pt(size * 3)
                hp_.add_run(str(s.meta.get("heading", "A signed copy")).upper()).font.size = Pt(size - 2)
                for lab in (layout.get("autograph_lines") or ["Signed for", "By", "Date", "Note"]) + [""]:
                    lp_ = doc.add_paragraph()
                    lp_.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    lp_.paragraph_format.space_after = Pt(size * 1.6)
                    if lab:
                        lp_.add_run(lab + "  ").italic = True
                    lp_.add_run("_" * (40 if lab else 52))
            elif s.type == "toc":
                doc.add_paragraph(s.title, style="Heading 1")
                p = doc.add_paragraph()
                r = p.add_run()
                switches = 'TOC \\o "1-1" \\h \\z \\u' + ("" if layout.get("toc_page_numbers", True) else " \\n")
                for tag, txt in (("begin", None), (None, f" {switches} "), ("separate", None),
                                 (None, "Right-click and choose Update Field to build the contents."), ("end", None)):
                    if tag:
                        el = OxmlElement("w:fldChar")
                        el.set(qn("w:fldCharType"), tag)
                        r._r.append(el)
                    else:
                        el = OxmlElement("w:instrText" if txt.startswith(" ") else "w:t")
                        el.set(qn("xml:space"), "preserve")
                        el.text = txt
                        r._r.append(el)
            continue
        # body sections
        ded_top = s.type in ("dedication", "epigraph")
        if s.label:
            lp = doc.add_paragraph()
            lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            lp.paragraph_format.space_before = Pt(size * 5)
            lr = lp.add_run(s.label.upper())
            lr.font.size = Pt(size - 1)
        if s.type not in ("dedication", "epigraph"):
            hp = doc.add_paragraph(style="Heading 1")
            add_inline(hp, s.title)
            if s.label:
                hp.paragraph_format.space_before = Pt(4)
        if s.subtitle:
            sp = doc.add_paragraph()
            sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            sp.add_run(s.subtitle).italic = True
        md = s.body_md
        footnotes = dict(re.findall(r"^\[\^([^\]]+)\]:\s*(.+)$", md, flags=re.M))
        md = re.sub(r"^\[\^[^\]]+\]:.*$", "", md, flags=re.M)
        first_para = True
        for block in re.split(r"\n\s*\n", md):
            b = block.strip()
            if not b:
                continue
            if b == "\\newpage":
                doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
                continue
            if re.match(r"^(\*\s*\*\s*\*|-{3,}|_{3,})$", b):
                sp = doc.add_paragraph("*\u2003*\u2003*")
                sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                first_para = True
                continue
            mh = re.match(r"^(#{1,6})\s+(.+)$", b)
            if mh and "\n" not in b:
                lvl = min(len(mh.group(1)) + 1, 3)
                add_inline(doc.add_paragraph(style=f"Heading {lvl}"), mh.group(2))
                first_para = True
                continue
            if b.startswith(":::"):
                inner = [l for l in b.splitlines()[1:] if l.strip() != ":::"]
                label = b.splitlines()[0][3:].strip().split(None, 1)
                if len(label) > 1:
                    lp = doc.add_paragraph()
                    lp.add_run(label[1].upper()).bold = True
                cp = doc.add_paragraph()
                cp.paragraph_format.left_indent = Inches(0.3)
                add_inline(cp, " ".join(inner))
                continue
            if b.startswith(">"):
                lines = [re.sub(r"^\s*>\s?", "", l) for l in b.splitlines()]
                attribution = lines.pop() if lines and re.match(r"^\s*(--|\u2014)\s*\S", lines[-1]) else ""
                qp = doc.add_paragraph()
                qp.paragraph_format.left_indent = qp.paragraph_format.right_indent = Inches(0.5)
                qp.paragraph_format.space_before = qp.paragraph_format.space_after = Pt(6)
                qp.alignment = WD_ALIGN_PARAGRAPH.LEFT
                add_inline(qp, " ".join(l.strip() for l in lines), footnotes, base_italic=True)
                if attribution:
                    ap2 = doc.add_paragraph()
                    ap2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    ap2.paragraph_format.right_indent = Inches(0.5)
                    add_inline(ap2, re.sub(r"^\s*(--|\u2014)\s*", "\u2014 ", attribution), footnotes, base_italic=True)
                first_para = True
                continue
            if re.match(r"^([-*+]|\d+[.)])\s+", b):
                for item in re.split(r"\n(?=\s*(?:[-*+]|\d+[.)])\s+)", b):
                    ordered = bool(re.match(r"^\s*\d", item))
                    txt = re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", item).replace("\n", " ")
                    add_inline(doc.add_paragraph(style="List Number" if ordered else "List Bullet"), txt, footnotes)
                first_para = True
                continue
            if b.startswith("!["):
                im = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)", b)
                src = Path(s.path).parents[2] / im.group(2) if im and s.path else None
                if src and src.exists():
                    doc.add_picture(str(src), width=Inches(trim[0] - m["inside"] - m["outside"]))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                continue
            if b.startswith("<table"):
                add_html_table(doc, b, size)
                first_para = True
                continue
            if b.startswith("<"):
                continue
            p = doc.add_paragraph()
            if not first_para:
                p.paragraph_format.first_line_indent = Inches(0.3)
            add_inline(p, " ".join(l.strip() for l in b.splitlines()), footnotes)
            if s.type in ("dedication", "epigraph"):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.first_line_indent = None
                p.runs and setattr(p.runs[0], "italic", True)
                if ded_top:
                    p.paragraph_format.space_before = Pt(size * 14)
                    ded_top = False
            first_para = False
        if footnotes:
            np_ = doc.add_paragraph()
            np_.paragraph_format.space_before = Pt(size)
            np_.add_run("Notes").bold = True
            for n, (k, v) in enumerate(footnotes.items(), 1):
                fp = doc.add_paragraph()
                fp.paragraph_format.first_line_indent = None
                add_inline(fp, f"{n}. {v}")
                for r in fp.runs:
                    r.font.size = Pt(size - 2)
    out = out_dir / f"{meta['title']} Manuscript {datetime.date.today().year} ({layout['trim']}).docx"
    out = out_dir / re.sub(r'[<>:"/\\|?*]', "", out.name)
    doc.save(str(out))
    return {"docx": str(out), "margins_in": m, "font": f"{font} {size}pt, {spacing} spacing"}


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--formats", default="pdf,epub,docx")
    ap.add_argument("--trim", help="override layout.trim, e.g. 5.5x8.5")
    ap.add_argument("--out", help="output folder (default PROJECT/build)")
    ap.add_argument("--keep-html", action="store_true", help="also deliver the print HTML + fonts (formats html does the same)")
    a = ap.parse_args()
    project = Path(a.project)
    meta, layout, sections = bc.load_project(project)
    bc.SMART_QUOTES = bool(layout.get("smart_quotes", True))
    if a.trim:
        layout["trim"] = a.trim
    key = str(layout["trim"]).lower().replace(" ", "").replace("in", "").replace("\u00d7", "x")
    if key not in TRIMS:
        sys.exit(f"Unknown trim '{layout['trim']}'. Use one of: {', '.join(TRIMS)}")
    layout["trim"] = key
    trim = TRIMS[key]
    out = Path(a.out) if a.out else project / "build"
    out.mkdir(parents=True, exist_ok=True)
    formats = {f.strip() for f in a.formats.split(",") if f.strip()}
    if "html" in formats:
        a.keep_html = True
        formats.add("pdf")
    report = {"title": meta["title"], "built": datetime.datetime.now().isoformat(timespec="seconds"),
              "design": {k: layout.get(k) for k in ("preset", "preset_why", "preset_scores", "body_font", "heading_font",
                                                    "label_font", "body_size", "leading")},
              "drafted_unapproved": [s.title for s in sections if s.meta.get("drafted") and not s.meta.get("approved")],
              "sections": [{"type": s.type, "title": s.title, "words": bc.word_count(bc.md_plain(s.body_md))} for s in sections]}
    print(f"{meta['title']} | {len(sections)} sections | trim {key}")
    print(f"design: {layout['preset']} preset - {layout['body_font']} body, {layout['heading_font']} headings, "
          f"{layout['body_size']}pt ({layout['preset_why']})")
    drafted = [s.title for s in sections if s.meta.get("drafted") and not s.meta.get("approved")]
    if drafted:
        print(f"! drafted text awaiting author approval: {', '.join(drafted)}")
    if "pdf" in formats:
        browser = find_browser()
        if not browser:
            sys.exit("No Chrome/Edge found for PDF. Set CHROME_PATH, or build --formats epub,docx.")
        print("pdf: rendering...")
        report["pdf"] = build_pdf(meta, layout, sections, trim, out, browser, a.keep_html)
        print(f"  -> {report['pdf']['pdf']} ({report['pdf']['pages']} pages)")
    if "epub" in formats:
        report["epub"] = build_epub(meta, layout, sections, out, project)
        print(f"epub -> {report['epub']['epub']}")
    if "docx" in formats:
        report["docx"] = build_docx(meta, layout, sections, trim, out)
        print(f"docx -> {report['docx']['docx']}")
    (out / "build-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"report -> {out / 'build-report.json'}")


if __name__ == "__main__":
    main()
