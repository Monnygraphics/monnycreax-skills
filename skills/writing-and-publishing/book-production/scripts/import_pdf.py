#!/usr/bin/env python3
"""
import_pdf.py - turn a laid-out PDF manuscript back into a book project.

    python import_pdf.py BOOK.pdf PROJECT_DIR [--title T] [--author A] [--force]

For manuscripts that only exist as a PDF (exported from Word, Canva, another typesetter).
It reads the text layer with PyMuPDF and rebuilds the structure from the typography:

  * running heads, footers and page numbers (small text in the top/bottom margin) are removed
  * the most common text size is the body; bigger sizes are headings, ranked by size
  * a letter-spaced label above a heading ("C H A P T E R  O N E", "P A R T  T W O") becomes its label;
    when CHAPTER headings are bigger than PART headings, chapters are the book's divisions
    (type part) and parts are its chapters, keeping the author's own names
  * headings about 1.3-1.8x body size become ## subheads; an italic line under a title is its subtitle
  * lines are joined into paragraphs by spacing; hyphenated line ends are rejoined;
    indented italic passages become block quotes; bold and italic words are kept
  * the source's contents page and title/copyright pages are left out (the build makes new ones);
    their text goes to import-log.md so nothing is lost silently
  * images are extracted to assets/media/

Scanned PDFs (no text layer) are not supported: OCR them first.
The PDF is never modified. Check the result: read import-log.md and the built proofs.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bookcore as bc  # noqa: E402

SPACED = re.compile(r"^(?:[A-Z0-9&'’] ){2,}[A-Z0-9&'’](?:\s{2,}(?:[A-Z0-9&'’] ?)+)*$")


def unspace(t: str) -> str:
    words = re.split(r"\s{2,}", t.strip())
    return " ".join("".join(w.split()) for w in words)


def span_md(s):
    t = s["text"]
    if not t.strip():
        return t
    b, i = bool(s["flags"] & 16), bool(s["flags"] & 2)
    lead, core, trail = t[: len(t) - len(t.lstrip())], t.strip(), t[len(t.rstrip()):]
    if b and i:
        core = f"***{core}***"
    elif b:
        core = f"**{core}**"
    elif i:
        core = f"*{core}*"
    return lead + core + trail


def read_lines(doc):
    out = []
    for pno, page in enumerate(doc):
        H, W = page.rect.height, page.rect.width
        for blk in page.get_text("dict")["blocks"]:
            if blk.get("type") == 1:
                out.append({"kind": "image", "page": pno, "y0": blk["bbox"][1], "bbox": blk["bbox"], "xref": None,
                            "W": W, "H": H})
                continue
            for ln in blk.get("lines", []):
                spans = [s for s in ln["spans"] if s["text"].strip()]
                if not spans:
                    continue
                text = "".join(s["text"] for s in ln["spans"]).strip()
                size = max(s["size"] for s in spans)
                out.append({"kind": "text", "page": pno, "text": text, "md": "".join(span_md(s) for s in ln["spans"]).strip(),
                            "size": round(size, 1), "bold": all(s["flags"] & 16 for s in spans),
                            "italic": all(s["flags"] & 2 for s in spans),
                            "x0": ln["bbox"][0], "y0": ln["bbox"][1], "x1": ln["bbox"][2], "y1": ln["bbox"][3],
                            "W": W, "H": H})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("project")
    ap.add_argument("--title")
    ap.add_argument("--author")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    import fitz
    root = Path(a.project)
    if root.exists() and any(root.iterdir()) and not a.force:
        sys.exit(f"{root} is not empty. Pass --force to write into it (the old manuscript folder is backed up).")
    doc = fitz.open(a.pdf)
    lines = read_lines(doc)
    texts = [l for l in lines if l["kind"] == "text"]
    if sum(len(l["text"]) for l in texts) < 200:
        sys.exit("This PDF has almost no text layer (a scan?). OCR it first, then import the text.")
    size_chars = Counter()
    for l in texts:
        size_chars[l["size"]] += len(l["text"])
    body = size_chars.most_common(1)[0][0]

    # 1. remove running heads / footers / folios: small text in the outer 10% of the page
    def margin_noise(l):
        top = l["y1"] < l["H"] * 0.10
        bottom = l["y0"] > l["H"] * 0.90
        return (top or bottom) and (l["size"] <= body - 1.5 or re.fullmatch(r"[\divxlc]+", l["text"].lower()))
    removed = Counter(l["text"] for l in texts if margin_noise(l))
    lines = [l for l in lines if l["kind"] != "text" or not margin_noise(l)]

    # 2. heading tiers
    sub_min, head_min = body * 1.3, body * 1.8
    head_sizes = sorted({l["size"] for l in lines if l["kind"] == "text" and l["size"] >= head_min}, reverse=True)

    # 3. walk lines into blocks
    blocks = []   # {"type": "head"/"label"/"sub"/"para"/"image", ...}
    cur = None
    page_left = {}
    for l in lines:
        if l["kind"] == "text" and abs(l["size"] - body) < 0.6:
            page_left[l["page"]] = min(page_left.get(l["page"], 1e9), l["x0"])

    def flush():
        nonlocal cur
        if cur:
            blocks.append(cur)
            cur = None

    prev = None
    for l in lines:
        if l["kind"] == "image":
            flush()
            blocks.append({"type": "image", "page": l["page"], "bbox": l["bbox"]})
            prev = None
            continue
        t = l["text"]
        if SPACED.match(t) and l["size"] < head_min:
            flush()
            blocks.append({"type": "label", "text": unspace(t).title(), "page": l["page"]})
            prev = l
            continue
        if l["size"] >= head_min:
            if cur and cur["type"] == "head" and cur["page"] == l["page"] and abs(cur["size"] - l["size"]) < 0.6:
                cur["text"] += " " + t
            else:
                flush()
                cur = {"type": "head", "text": t, "size": l["size"], "page": l["page"]}
            prev = l
            continue
        if l["size"] >= sub_min:
            if cur and cur["type"] == "sub" and cur["page"] == l["page"] and prev is not None and l["y0"] - prev["y1"] < l["size"]:
                cur["text"] += " " + t
            else:
                flush()
                cur = {"type": "sub", "text": t, "page": l["page"]}
            prev = l
            continue
        # a whole bold short line at body size, not ending a sentence: a minor heading (### )
        if l["bold"] and len(t.split()) <= 12 and not re.search(r"[.,;!]$", t):
            flush()
            blocks.append({"type": "minor", "text": t, "page": l["page"]})
            prev = l
            continue
        # body-ish line
        left = page_left.get(l["page"], l["x0"])
        indented = l["x0"] - left > 8
        quote = l["italic"] and indented
        bullet = re.match(r"^([•●▪\-–*]|\d+[.)])\s+", t)
        new_para = (cur is None or cur["type"] != "para" or bullet or cur.get("quote") != quote
                    or (prev is not None and l["page"] == prev["page"] and l["y0"] - prev["y1"] > max(4.0, l["size"] * 0.55)))
        if cur and cur["type"] == "para" and prev is not None and l["page"] != prev["page"]:
            # page turn: continue the paragraph unless the last line ended a sentence and this starts fresh
            last = cur["lines"][-1]
            ended = re.search(r"[.!?:”\"')]$", last["text"])
            ran_to_bottom = last["y1"] > last["H"] * 0.78
            new_para = bool(bullet) or cur.get("quote") != quote or not ran_to_bottom or bool(ended and l["x0"] - left > 2)
        if new_para:
            flush()
            cur = {"type": "para", "lines": [], "quote": quote, "page": l["page"], "italic_all": True,
                   "centered": indented and (l["W"] - l["x1"]) - (l["x0"] - 0) < 30}
        cur["lines"].append(l)
        cur["italic_all"] = cur["italic_all"] and l["italic"]
        prev = l
    flush()

    def join(ls, field):
        out = ""
        for x in ls:
            s = x[field]
            if out.endswith("-") and s[:1].islower() and not out.endswith(" -"):
                out = out[:-1] + s
            elif out.endswith("-*") and s.startswith("*") and s[1:2].islower():
                out = out[:-2] + s[1:]
            else:
                out = (out + " " + s) if out else s
        out = re.sub(r"\*\*\s+\*\*", " ", out)
        out = re.sub(r"(?<!\*)\*\s+\*(?!\*)", " ", out)
        return out

    # 4. sections
    tiers = {}
    labelled = {}
    for i, blk in enumerate(blocks):
        if blk["type"] == "head":
            lab = blocks[i - 1]["text"] if i and blocks[i - 1]["type"] == "label" else ""
            kind = lab.split()[0].lower() if lab else ""
            labelled.setdefault(kind, []).append(blk["size"])
    chap_div = ("chapter" in labelled and "part" in labelled and
                sum(labelled["chapter"]) / len(labelled["chapter"]) > sum(labelled["part"]) / len(labelled["part"]))

    sections = []
    opening = {"title": "", "type": "opening", "lines": [], "label": "", "subtitle": ""}
    cur_s = opening
    book_title = a.title
    images = []
    covers = []
    first_body_seen = False
    for i, blk in enumerate(blocks):
        if blk["type"] == "label":
            continue
        if blk["type"] == "head":
            lab = blocks[i - 1]["text"] if i and blocks[i - 1]["type"] == "label" else ""
            title = blk["text"].strip()
            norm = lambda s: re.sub(r"\W", "", s.lower())
            if not sections and cur_s is opening and (not lab or norm(lab) == norm(title)) \
                    and bc.classify_heading(title) is None:
                book_title = book_title or title    # the title page
                continue
            if lab and book_title and norm(lab) == norm(book_title) and norm(title) != norm(book_title):
                lab = ""                            # a running head that leaked in, not a label
            if lab and norm(lab) in norm(title):
                lab = ""                            # "Closing" over "Closing Remark": the title says it
            kind = lab.split()[0].lower() if lab else ""
            typ = bc.classify_heading(title) or bc.classify_heading(lab) if not kind or kind not in ("chapter", "part") else None
            if kind == "chapter":
                typ = "part" if chap_div else "chapter"
            elif kind == "part":
                typ = "chapter" if chap_div else "part"
            elif not typ:
                typ = "chapter"
            if cur_s is opening and not sections and typ == "chapter" and not lab and not opening["lines"] and not book_title:
                book_title = title          # a big unlabelled heading on the first pages: the title page
                continue
            if typ in ("part", "chapter"):
                first_body_seen = True
            if typ == "acknowledgements" and not first_body_seen:
                typ = "acknowledgements-front"      # keep the author's placement
            cur_s = {"title": title, "type": typ, "lines": [], "label": lab, "subtitle": "", "page": blk["page"]}
            sections.append(cur_s)
            continue
        if blk["type"] == "sub":
            t = blk["text"].strip()
            if bc.classify_heading(t) == "toc":
                cur_s = {"title": "Contents", "type": "toc", "lines": [], "label": "", "subtitle": ""}
                sections.append(cur_s)
                continue
            cur_s["lines"].append("## " + t)
            continue
        if blk["type"] == "minor":
            cur_s["lines"].append("### " + blk["text"].strip())
            continue
        if blk["type"] == "image":
            x0, y0, x1, y1 = blk["bbox"]
            pw, ph = doc[blk["page"]].rect.width, doc[blk["page"]].rect.height
            if (x1 - x0) * (y1 - y0) > 0.8 * pw * ph and blk["page"] in (0, 1, len(doc) - 1, len(doc) - 2):
                covers.append(blk)   # full-page art at the start or end: the cover, not interior content
                continue
            images.append((cur_s, blk))
            cur_s["lines"].append(f"__IMAGE_{len(images)}__")
            continue
        md = join(blk["lines"], "md")
        plain = join(blk["lines"], "text")
        if cur_s is not opening and not cur_s["lines"] and not cur_s["subtitle"] and blk["italic_all"] and len(plain.split()) <= 16 \
                and cur_s["type"] in ("chapter", "part"):
            cur_s["subtitle"] = plain
            continue
        if blk["quote"] or (blk["italic_all"] and blk["centered"]):
            inner = re.sub(r"^\*(.*)\*$", r"\1", md.strip()) if blk["italic_all"] else md
            cur_s["lines"].append("> " + inner)
        elif re.match(r"^([•●▪–*]|-)\s+", plain):
            cur_s["lines"].append("- " + re.sub(r"^([•●▪–*]|-)\s+", "", md))
        else:
            cur_s["lines"].append(md)

    # 5. write the project
    man = root / "manuscript"
    if man.exists():
        man.rename(root / f"manuscript.bak-{datetime.datetime.now():%Y%m%d-%H%M%S}")
    for d in ("front", "body", "back"):
        (man / d).mkdir(parents=True, exist_ok=True)
    (root / "assets" / "media").mkdir(parents=True, exist_ok=True)
    # images: crop the page region at 300 dpi (works for every image encoding)
    for n, (sec, blk) in enumerate(images, 1):
        page = doc[blk["page"]]
        clip = fitz.Rect(blk["bbox"])
        if clip.width < 20 or clip.height < 20:
            for s in sections + [opening]:
                s["lines"] = [x for x in s["lines"] if x != f"__IMAGE_{n}__"]
            continue
        name = f"image{n:03d}.png"
        page.get_pixmap(dpi=300, clip=clip).save(str(root / "assets" / "media" / name))
        for s in sections + [opening]:
            s["lines"] = [f"![](assets/media/{name})" if x == f"__IMAGE_{n}__" else x for x in s["lines"]]

    for n, blk in enumerate(covers):
        name = "cover-front.png" if blk["page"] <= 1 else "cover-back.png"
        doc[blk["page"]].get_pixmap(dpi=300, clip=fitz.Rect(blk["bbox"])).save(str(root / "assets" / name))
    log = ["# Import log (PDF)\n", f"- Source: `{Path(a.pdf).resolve()}`", f"- Pages: {len(doc)}, body text size {body}pt, "
           f"heading sizes {head_sizes}", f"- Structure: " + ("CHAPTER headings are the book's divisions, PART headings its chapters "
                                                          "(the author's naming is kept)" if chap_div else "standard"),
           f"- Removed running heads / folios: {sum(removed.values())} lines, e.g. {', '.join(list(removed)[:5])}",
           f"- Images: {len(images)} inside the book; cover art found: "
           + (", ".join("cover-front.png" if c["page"] <= 1 else "cover-back.png" for c in covers) or "none")
           + " (saved in assets/, used for the print-shop cover and the ebook)", ""]
    placeholders = []
    if opening["lines"]:
        log.append("Title/copyright text before the first section (not imported; the build makes these pages):")
        log.append("```\n" + "\n".join(opening["lines"])[:2000] + "\n```")
        placeholders = re.findall(r"\[[^\]]{2,80}\]", "\n".join(opening["lines"]))
    counters = {"front": 0, "body": 0, "back": 0}
    contents = ["auto:autograph", "auto:title", "auto:copyright"]
    order = []
    for s in sections:
        if s["type"] == "toc":
            log.append(f"- Dropped the source contents page ({len(s['lines'])} lines); the build makes a new one from the headings.")
            continue
        if not s["title"] and not s["lines"]:
            continue
        matter = "front" if s["type"] in bc.FRONT_TYPES else "back" if s["type"] in bc.BACK_TYPES else "body"
        counters[matter] += 1
        fname = f"{counters[matter]:02d}-{bc.slugify(s['title'])}.md"
        fm = {"type": s["type"]}
        if s["label"]:
            fm["label"] = s["label"]
        if s["subtitle"]:
            fm["subtitle"] = s["subtitle"]
        head = "---\n" + "".join(f'{k}: "{v}"\n' if k != "type" else f"{k}: {v}\n" for k, v in fm.items()) + "---\n"
        text = "\n\n".join(s["lines"])
        (man / matter / fname).write_text(f"{head}# {s['title']}\n\n{text}\n", encoding="utf-8")
        rel = f"{matter}/{fname}"
        order.append((("front", "body", "back").index(matter), rel))
        log.append(f"- {s['type']:<12} {rel}  {('[' + s['label'] + '] ') if s['label'] else ''}"
                   f"({bc.word_count(bc.md_plain(text)):,} words)")
    dedication = [r for _, r in order if "dedication" in r]
    contents += dedication + ["auto:toc"] + [r for _, r in sorted(order, key=lambda x: x[0]) if r not in dedication]
    import yaml
    meta = {"title": book_title or Path(a.pdf).stem.replace("_", " "), "subtitle": "", "author": a.author or "",
            "year": "", "isbn_print": ""}
    cfg = {"meta": meta, "layout": {"trim": "a5", "preset": "auto"}, "contents": contents}
    (root / "book.yml").write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if placeholders:
        log.append("\n## Placeholders found in the source front matter (need answers)\n" + "\n".join(f"- {p}" for p in placeholders))
    (root / "import-log.md").write_text("\n".join(log), encoding="utf-8")
    print(f"project: {root}  sections: {sum(counters.values())} (front {counters['front']}, body {counters['body']}, back {counters['back']})")
    print(f"log: {root / 'import-log.md'}")


if __name__ == "__main__":
    main()
