#!/usr/bin/env python3
"""
bookcore.py - shared helpers for the book-production scripts.

Pieces and where the ideas came from:
  * docx reading that respects <w:br/>, tracked changes and comments
    (Scribe's get_full_text lesson: naive run-joining fuses words)
  * guarded combined-words fix + unicode scan (Scribe, MIT)
  * a small Markdown dialect for the book project (bookpub's one-source idea)
  * the book project loader: book.yml + manuscript/ folder (bookpub, MIT)

Standard library + python-docx + PyYAML only.
"""
from __future__ import annotations

import html
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def work_root(*parts) -> Path:
    """Hidden place for everything that is not the deliverable (projects, builds, proofs, maps).
    Windows: %LOCALAPPDATA%/claude-work/book-production (AppData is hidden). Override with CLAUDE_WORK."""
    import os
    base = os.environ.get("CLAUDE_WORK") or os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.cache"),
                                                         "claude-work")
    p = Path(base, "book-production", *parts)
    p.mkdir(parents=True, exist_ok=True)
    return p
WQ = "{%s}" % W

# --------------------------------------------------------------------------
# Section vocabulary (book anatomy). Order = default position in a book.
# --------------------------------------------------------------------------
FRONT_TYPES = ["halftitle", "also-by", "title", "copyright", "dedication", "epigraph",
               "toc", "foreword", "preface", "acknowledgements-front", "introduction", "prologue"]
BODY_TYPES = ["part", "chapter"]
BACK_TYPES = ["epilogue", "afterword", "conclusion", "appendix", "acknowledgements", "glossary",
              "notes", "bibliography", "resources", "index", "about-author", "also-by-back", "colophon"]
ALL_TYPES = FRONT_TYPES + BODY_TYPES + BACK_TYPES

# Headings that identify a section type when importing a manuscript.
TYPE_BY_HEADING = [
    (r"^(table of )?contents$", "toc"),
    (r"^dedication$", "dedication"),
    (r"^epigraph$", "epigraph"),
    (r"^foreword$", "foreword"),
    (r"^preface$", "preface"),
    (r"^introduction$", "introduction"),
    (r"^prologue$", "prologue"),
    (r"^epilogue$", "epilogue"),
    (r"^afterword$", "afterword"),
    (r"^conclusion$", "conclusion"),
    (r"^appendix\b.*", "appendix"),
    (r"^acknowledge?ments?$", "acknowledgements"),
    (r"^glossary$", "glossary"),
    (r"^(end ?)?notes$", "notes"),
    (r"^(bibliography|references|works cited)$", "bibliography"),
    (r"^(resources|further reading)$", "resources"),
    (r"^about the authors?$", "about-author"),
    (r"^(also by|other books by).*", "also-by-back"),
    (r"^colophon$", "colophon"),
    (r"^copyright( page)?$", "copyright"),
    (r"^part\s+([ivxlc]+|\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b.*", "part"),
]

NUM_WORDS = ("one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
             "fifteen sixteen seventeen eighteen nineteen twenty").split()
CHAPTER_RE = re.compile(
    r"^(chapter|ch\.)\s+(\d+|[ivxlc]+|" + "|".join(NUM_WORDS) + r")\b[\s:.\-–—]*(.*)$", re.I)
NUMBERED_RE = re.compile(r"^(law|principle|rule|lesson|step|day|key|secret|habit)\s+(\d+)\b[\s:.\-–—]*(.*)$", re.I)


SMALL_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to", "vs", "with", "from"}


def title_case(s: str) -> str:
    """ALL CAPS heading -> Title Case, keeping small words lower ("About the Author")."""
    words = s.lower().split()
    return " ".join(w if (i and w in SMALL_WORDS) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def classify_heading(text: str) -> str | None:
    t = text.strip().lower().rstrip(".:")
    for pat, typ in TYPE_BY_HEADING:
        if re.match(pat, t):
            return typ
    if CHAPTER_RE.match(text.strip()) or NUMBERED_RE.match(text.strip()):
        return "chapter"
    return None


def number_value(token: str) -> int | None:
    t = token.lower()
    if t.isdigit():
        return int(t)
    if t in NUM_WORDS:
        return NUM_WORDS.index(t) + 1
    roman = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}
    if all(ch in roman for ch in t):
        total, prev = 0, 0
        for ch in reversed(t):
            v = roman[ch]
            total = total - v if v < prev else total + v
            prev = max(prev, v)
        return total
    return None


# --------------------------------------------------------------------------
# Text hygiene (Scribe lessons)
# --------------------------------------------------------------------------
NAME_PREFIXES = ["Mac", "Mc", "La", "De", "Di", "Le", "Van", "Von", "O'"]
STYLIZATION_PREFIXES = ["i", "e"]  # iPhone, eBook
KNOWN_CAMEL = {"YouTube", "LinkedIn", "PowerPoint", "WhatsApp", "TikTok", "PayPal", "JavaScript",
               "YouVersion", "GitHub", "McKinsey", "MasterCard", "FedEx", "OpenAI", "ChatGPT",
               "MonnyCreaX", "iPhone", "eBay", "SoundCloud", "WordPress", "HubSpot", "DreamWorks"}
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")
_WORD = re.compile(r"[A-Za-z][A-Za-z']*[A-Za-z]")


def combined_word_suspects(text: str) -> list[str]:
    """Words like 'GodIsTalking' that look fused (a lost line break). Guarded."""
    out = []
    for w in _WORD.findall(text):
        if w in KNOWN_CAMEL or not _CAMEL.search(w) or w.isupper():
            continue
        if any(w.startswith(p) and len(w) > len(p) and w[len(p)].isupper() and _CAMEL.search(w[len(p):]) is None
               for p in NAME_PREFIXES + STYLIZATION_PREFIXES):
            continue
        out.append(w)
    return out


def fix_combined_words(text: str, change_log: list | None = None, context: str = "") -> str:
    """Insert a space at lower->Upper boundaries inside suspect words only."""
    fixed = text
    for w in set(combined_word_suspects(text)):
        fixed = re.sub(r"\b%s\b" % re.escape(w), _CAMEL.sub(" ", w), fixed)
    if fixed != text and change_log is not None:
        change_log.append({"type": "combined_words", "context": context, "before": text, "after": fixed})
    return fixed


EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF️]")
INVISIBLES = {" ": " ", "​": "", "‌": "", "‍": "", "﻿": "", " ": " "}


def normalize_invisibles(text: str) -> str:
    for k, v in INVISIBLES.items():
        text = text.replace(k, v)
    return text


def unicode_report(text: str) -> dict:
    return {
        "straight_double": text.count('"'),
        "curly_double": text.count("“") + text.count("”"),
        "straight_single": len(re.findall(r"(?<=\w)'(?=\w)|(?<!\w)'", text)),
        "curly_single": text.count("‘") + text.count("’"),
        "nbsp": text.count(" "),
        "zero_width": sum(text.count(c) for c in "​‌‍﻿"),
        "em_dash": text.count("—"),
        "en_dash": text.count("–"),
        "double_hyphen": text.count("--"),
        "double_space": len(re.findall(r"(?<=\S)  +(?=\S)", text)),
        "emoji": len(EMOJI_RE.findall(text)),
        "ellipsis_dots": text.count("..."),
    }


def word_count(text: str) -> int:
    return len(re.findall(r"[\w’']+", text))


# --------------------------------------------------------------------------
# DOCX reading
# --------------------------------------------------------------------------
@dataclass
class Para:
    text: str                 # plain text, \n at <w:br/>
    md: str                   # inline markdown (*italic*, **bold**)
    style: str = ""
    level: int = 0            # heading level from style/outline, 0 = body
    align: str = ""
    is_list: bool = False
    page_break_before: bool = False
    comment_ids: list = field(default_factory=list)
    kind: str = "text"        # text | image | table


def _run_md(text: str, b: bool, i: bool) -> str:
    if not text.strip():
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    core = text.strip()
    if b and i:
        core = f"***{core}***"
    elif b:
        core = f"**{core}**"
    elif i:
        core = f"*{core}*"
    return lead + core + trail


def _flag(rpr, tag) -> bool:
    if rpr is None:
        return False
    el = rpr.find(WQ + tag)
    if el is None:
        return False
    val = el.get(WQ + "val")
    return val not in ("0", "false", "none")


def read_docx(path: str | Path) -> tuple[list[Para], dict]:
    """Return paragraphs (tracked insertions kept, deletions dropped = 'accept all')
    plus a dict of document facts: tracked changes, comments, images, styles."""
    from docx import Document
    doc = Document(str(path))
    style_bold, style_italic, style_level = {}, {}, {}
    for s in doc.styles:
        try:
            el = s.element
        except Exception:
            continue
        sid = el.get(WQ + "styleId")
        name = (s.name or "").lower()
        rpr = el.find(WQ + "rPr")
        style_bold[sid] = _flag(rpr, "b")
        style_italic[sid] = _flag(rpr, "i")
        m = re.match(r"heading (\d)", name)
        if m:
            style_level[sid] = int(m.group(1))
        elif name == "title":
            style_level[sid] = 1
        else:
            ppr = el.find(WQ + "pPr")
            ol = ppr.find(WQ + "outlineLvl") if ppr is not None else None
            if ol is not None and ol.get(WQ + "val", "9").isdigit() and int(ol.get(WQ + "val")) < 3:
                style_level[sid] = int(ol.get(WQ + "val")) + 1

    body = doc.element.body
    facts = {"insertions": len(body.findall(".//" + WQ + "ins")),
             "deletions": len(body.findall(".//" + WQ + "del")),
             "images": len(body.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")),
             "tables": len(body.findall(".//" + WQ + "tbl")),
             "comments": read_docx_comments(path), "media": {}}
    paras: list[Para] = []
    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    V = "{urn:schemas-microsoft-com:vml}"

    def grab_image(el):
        rid = None
        blip = next(el.iter(A + "blip"), None)
        if blip is not None:
            rid = blip.get(R + "embed")
        if rid is None:
            im = next(el.iter(V + "imagedata"), None)
            rid = im.get(R + "id") if im is not None else None
        part = doc.part.related_parts.get(rid) if rid else None
        if part is None:
            return None
        ext = Path(str(part.partname)).suffix.lower() or ".png"
        name = f"image{len(facts['media']) + 1:03d}{ext}"
        facts["media"][name] = part.blob
        return name

    def cell_text(tc):
        return " ".join("".join(t.text or "" for t in cp.iter(WQ + "t")) for cp in tc.iter(WQ + "p")).strip()

    for p in body.iter(WQ + "p", WQ + "tbl"):
        if any(a.tag == WQ + "tbl" for a in p.iterancestors()):
            continue
        if p.tag == WQ + "tbl":
            rows = []
            for tr in p.iter(WQ + "tr"):
                cells = [cell_text(tc) for tc in tr.findall(WQ + "tc")]
                if any(cells):
                    rows.append(cells)
            if not rows:
                continue
            first = "".join(f"<th>{html.escape(c)}</th>" for c in rows[0])
            rest = "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
            md_tbl = f"<table><thead><tr>{first}</tr></thead><tbody>{rest}</tbody></table>"
            paras.append(Para(text=" | ".join(" ".join(r) for r in rows), md=md_tbl, kind="table"))
            continue
        ppr = p.find(WQ + "pPr")
        sid = ""
        level = 0
        align = ""
        is_list = False
        pb_before = False
        if ppr is not None:
            ps = ppr.find(WQ + "pStyle")
            sid = ps.get(WQ + "val") if ps is not None else ""
            jc = ppr.find(WQ + "jc")
            align = jc.get(WQ + "val") if jc is not None else ""
            is_list = ppr.find(WQ + "numPr") is not None
            pb_before = ppr.find(WQ + "pageBreakBefore") is not None
            ol = ppr.find(WQ + "outlineLvl")
            if ol is not None and ol.get(WQ + "val", "9").isdigit() and int(ol.get(WQ + "val")) < 3:
                level = int(ol.get(WQ + "val")) + 1
        level = level or style_level.get(sid, 0)
        if "list" in (sid or "").lower():
            is_list = True
        plain, md = [""], [""]
        images = []
        comment_ids = [c.get(WQ + "id") for c in p.iter(WQ + "commentRangeStart")]
        for r in p.iter(WQ + "r"):
            # skip deleted runs, and runs that belong to a nested paragraph
            anc = r.getparent()
            skip = False
            while anc is not None and anc is not p:
                if anc.tag in (WQ + "del", WQ + "moveFrom"):
                    skip = True
                    break
                if anc.tag == WQ + "p":
                    skip = True
                    break
                anc = anc.getparent()
            if skip:
                continue
            rpr = r.find(WQ + "rPr")
            rs = rpr.find(WQ + "rStyle") if rpr is not None else None
            b = _flag(rpr, "b") or style_bold.get(sid, False)
            i = _flag(rpr, "i") or style_italic.get(sid, False)
            for ch in r:
                tag = ch.tag.split("}")[-1]
                if tag == "t":
                    t = ch.text or ""
                    plain[-1] += t
                    md[-1] += _run_md(t, b and level == 0, i and level == 0)
                elif tag == "tab":
                    plain[-1] += "\t"
                    md[-1] += " "
                elif tag == "br":
                    if ch.get(WQ + "type") == "page":
                        pb_before = pb_before or not "".join(plain).strip()
                    else:
                        plain.append("")
                        md.append("")
                elif tag in ("drawing", "pict", "object"):
                    name = grab_image(ch)
                    if name:
                        images.append(name)
        text = normalize_invisibles("\n".join(plain))
        mdt = normalize_invisibles("\n".join(md))
        mdt = re.sub(r"\*\*\s*\*\*|(?<!\*)\*\s*\*(?!\*)", "", mdt)  # merge split emphasis
        if text.strip() or not images:
            paras.append(Para(text=text, md=mdt, style=sid, level=level, align=align,
                              is_list=is_list, page_break_before=pb_before, comment_ids=comment_ids))
        for name in images:
            paras.append(Para(text=f"[image {name}]", md=f"![](assets/media/{name})", kind="image"))
    return paras, facts


def read_text_manuscript(path: str | Path) -> tuple[list[Para], dict]:
    """A .txt or .md manuscript as Para objects. '# ' / '## ' lines become headings.
    Paragraphs are blank-line separated; a file with almost no blank lines is read one paragraph per line."""
    raw = Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    raw = normalize_invisibles(raw)
    lines = raw.split("\n")
    blank = sum(1 for l in lines if not l.strip())
    blocks = re.split(r"\n\s*\n", raw) if blank > len(lines) * 0.15 else lines
    paras = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        m = re.match(r"^(#{1,3})\s+(.+)$", b)
        if m and "\n" not in b:
            paras.append(Para(text=m.group(2).strip(), md=m.group(2).strip(), level=len(m.group(1))))
            continue
        text = re.sub(r"\s*\n\s*", " ", b) if not b.startswith((">", "-", "*", "1.")) else b
        paras.append(Para(text=md_plain(text).strip(), md=text, is_list=bool(re.match(r"^[-*]\s", b))))
    facts = {"insertions": 0, "deletions": 0, "images": 0, "tables": 0, "comments": []}
    return paras, facts


def read_manuscript(path: str | Path) -> tuple[list[Para], dict]:
    return read_docx(path) if str(path).lower().endswith(".docx") else read_text_manuscript(path)


def split_docx_sections(paras: list[Para]) -> list[dict]:
    """Group paragraphs into sections: {"title", "type", "paras": [Para], "changes": [...]}.

    * Heading 1 / Title styles, or short lines that read as a heading
      ("Chapter One", "Preface", "About the Author"), start a section.
    * "Chapter One" alone followed by a short title line merges into one title.
    * Inside the source's own contents list only real Heading-1 paragraphs end it,
      so its entries are not mistaken for chapters.
    """
    sections = []
    cur = {"title": "", "type": "opening", "paras": []}
    await_title = False
    # Plain manuscripts (no Heading styles at all): a short line that is wholly bold,
    # ALL CAPS or centred, with no closing punctuation, counts as a heading.
    plain = not any(p.level == 1 for p in paras)

    def looks_like_heading(p, t):
        if p.kind != "text":
            return False
        if not plain or len(t.split()) > 10 or len(t) < 3 or re.search(r"[.,;:!]$", t):
            return False
        md = p.md.strip()
        bold = md.startswith("**") and md.endswith("**")
        caps = t.isupper() and sum(c.isalpha() for c in t) >= 3
        return bold or caps or p.align == "center"

    def keys(t):
        full = re.sub(r"[^a-z0-9]", "", t.lower())
        m = CHAPTER_RE.match(t.strip())
        out = {full}
        if m:
            out.add(re.sub(r"[^a-z0-9]", "", f"chapter {m.group(2)}".lower()))
            if m.group(3).strip():
                out.add(re.sub(r"[^a-z0-9]", "", m.group(3).lower()))
        return {k for k in out if k}

    # how often each short line occurs: a contents entry is repeated later as a real heading
    occurs = {}
    for p in paras:
        t = p.text.strip()
        if t and len(t) < 90:
            for k in keys(t):
                occurs[k] = occurs.get(k, 0) + 1
    toc_seen = set()
    chapter_marked = sum(1 for p in paras if CHAPTER_RE.match(p.text.strip() or "x")) >= 2 * (
        1 + any(classify_heading(p.text.strip()) == "toc" for p in paras if len(p.text) < 40))

    for p in paras:
        t = p.text.strip()
        if not t:
            continue
        if p.style.lower() == "title" and not sections and cur["type"] == "opening":
            cur["book_title"] = t
            continue
        if plain and not sections and cur["type"] == "opening" and not cur.get("book_title") and not cur["paras"] \
                and len(t.split()) <= 12 and not classify_heading(t) and p.kind == "text":
            cur["book_title"] = t  # first short line of a plain manuscript is usually its title
            continue
        short = len(t) < 90 and "\n" not in t and p.kind == "text"
        typ = classify_heading(t) if short else None
        heading = p.level == 1 or (typ is not None and (p.level or len(t.split()) <= 10)) or looks_like_heading(p, t)
        if cur["type"] == "toc":
            if not plain:
                ends = p.level == 1
            else:
                k = keys(t) if short else set()
                repeated = bool(k & toc_seen)                       # body heading repeating an entry
                unlisted = heading and k and all(occurs.get(x, 0) <= 1 for x in k)  # heading not in the list
                ends = repeated or unlisted or len(t.split()) > 25
                if not ends:
                    toc_seen |= k
            if not ends:
                cur["paras"].append(p)
                continue
        if await_title and not cur["paras"] and short and len(t.split()) <= 12 and \
                (heading or p.align == "center" or p.level or plain) and not (typ and typ != "chapter") \
                and not CHAPTER_RE.match(t) and not re.search(r"[.,;:!]$", t):
            cur["title"] = f"{cur['title']}: {EMOJI_RE.sub('', t).strip()}"
            await_title = False
            continue
        await_title = False
        if heading and plain and typ is None and p.level != 1 and chapter_marked and cur["type"] == "chapter":
            # the book marks chapters explicitly, so a bold / caps line inside one is a subheading
            sub = re.sub(r"^\*+|\*+$", "", t).strip()
            cur["paras"].append(Para(text=title_case(sub) if sub.isupper() else sub, md=sub, level=2))
            continue
        if heading:
            clean = re.sub(r"^\*+|\*+$", "", EMOJI_RE.sub("", t).strip()).strip()
            if plain and clean.isupper() and not CHAPTER_RE.match(clean):
                clean = title_case(clean)
            sections.append(cur)
            cur = {"title": clean, "type": typ or "chapter", "paras": [],
                   "changes": [f"heading emoji stripped: {t!r} -> {clean!r}"] if EMOJI_RE.search(t) else []}
            cm = CHAPTER_RE.match(clean)
            await_title = bool(cm and not cm.group(3).strip())
            continue
        cur["paras"].append(p)
    sections.append(cur)
    return [s for s in sections if s["type"] != "opening" or s["paras"] or s.get("book_title")]


def read_docx_comments(path: str | Path) -> list[dict]:
    """Full comment text from word/comments.xml (email notifications truncate)."""
    from lxml import etree
    out = []
    with zipfile.ZipFile(str(path)) as z:
        if "word/comments.xml" not in z.namelist():
            return out
        root = etree.fromstring(z.read("word/comments.xml"))
        doc_root = etree.fromstring(z.read("word/document.xml"))
    # anchor text: walk the document in order between start and end markers
    anchors, active = {}, {}
    for el in doc_root.iter():
        if el.tag == WQ + "commentRangeStart":
            active[el.get(WQ + "id")] = []
        elif el.tag == WQ + "commentRangeEnd":
            cid = el.get(WQ + "id")
            if cid in active:
                anchors[cid] = "".join(active.pop(cid))
        elif el.tag == WQ + "t":
            for buf in active.values():
                buf.append(el.text or "")
    for c in root.iter(WQ + "comment"):
        cid = c.get(WQ + "id")
        body = "\n".join("".join(t.text or "" for t in p.iter(WQ + "t")) for p in c.iter(WQ + "p"))
        out.append({"id": cid, "author": c.get(WQ + "author", ""), "date": c.get(WQ + "date", ""),
                    "text": body.strip(), "anchor": anchors.get(cid, "").strip()})
    return out


# --------------------------------------------------------------------------
# Book project: book.yml + manuscript/*.md
# --------------------------------------------------------------------------
@dataclass
class Section:
    type: str
    title: str
    body_md: str
    path: str = ""
    label: str = ""          # e.g. "Chapter One"
    subtitle: str = ""
    toc: bool = True
    recto: bool = True
    slug: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def matter(self) -> str:
        if self.type in FRONT_TYPES:
            return "front"
        if self.type in BACK_TYPES:
            return "back"
        return "body"


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"[\s_]+", "-", s)[:60] or "section"


DEFAULT_META = {"title": "Untitled", "subtitle": "", "author": "", "publisher": "", "year": "",
                "edition": "First edition", "isbn_print": "", "isbn_ebook": "", "language": "en",
                "rights": "All rights reserved.", "contact": "", "location": "", "description": "",
                "copyright_extra": ""}

DEFAULT_LAYOUT = {"trim": "6x9", "body_font": "EB Garamond", "heading_font": "EB Garamond",
                  "label_font": "", "body_size": 11.5, "leading": 1.42, "accent": "#1a1a1a",
                  "margins": "auto", "bleed": False, "chapter_start": "right", "running_heads": True,
                  "verso_head": "author", "toc_page_numbers": True, "first_line_indent": True,
                  "drop_folio_on_openers": False, "hyphenate": True, "paper": "cream",
                  "docx_font": "Garamond", "docx_size": 12, "docx_line_spacing": 1.5}


# Design presets: one coherent look per kind of book. book.yml `layout:` keys override them.
# Fonts are bundled static cuts (no Type 3 fonts in the PDF).
PRESETS = {
    "classic": {   # memoir, manifesto, narrative and idea-led nonfiction
        "why": "literary serif for long reading; quiet small-caps chapter labels",
        "body_font": "EB Garamond", "heading_font": "EB Garamond", "label_font": "", "heading_weight": 500,
        "body_size": 11.5, "leading": 1.42, "accent": "#1a1a1a", "first_line_indent": True,
        "docx_font": "Garamond"},
    "devotional": {  # faith, spiritual growth, prayer, sermons
        "why": "elegant Cormorant Garamond titles over Lora text, large enough to read easily; scripture set apart in italics",
        "body_font": "Lora", "heading_font": "Cormorant Garamond", "label_font": "", "heading_weight": 600,
        "body_size": 12, "leading": 1.5, "accent": "#5a3e1b", "first_line_indent": True, "quote_italic": True,
        "docx_font": "Garamond"},
    "business": {  # business, leadership, branding, money, self-help with frameworks
        "why": "modern sans headings for a current, credible tone over a highly readable text serif",
        "body_font": "Source Serif 4", "heading_font": "Inter", "label_font": "Inter", "heading_weight": 600,
        "body_size": 10.5, "leading": 1.45, "accent": "#1f3a5f", "first_line_indent": True,
        "docx_font": "Georgia"},
    "warm": {  # self-help, relationships, parenting, wellness, personal stories with lessons
        "why": "friendly, rounded serif that reads as approachable and personal",
        "body_font": "Lora", "heading_font": "Lora", "label_font": "", "heading_weight": 600,
        "body_size": 10.5, "leading": 1.48, "accent": "#6b3a2a", "first_line_indent": True,
        "docx_font": "Georgia"},
    "workbook": {  # guides, workbooks, journals, step-by-step how-to
        "why": "clean sans for short-burst reading, block paragraphs and space to write",
        "body_font": "Inter", "heading_font": "Inter", "label_font": "Inter", "heading_weight": 700,
        "body_size": 10, "leading": 1.5, "accent": "#1f3a5f", "first_line_indent": False,
        "docx_font": "Calibri"},
}
# House styles measured from reference books (2026-10-18). Use with `preset:` in book.yml.
PRESETS["unbrand"] = {
    "why": "Monny's UNBRAND-END look: airy 1.6 leading, wide margins, plain bold caps openers, no running heads",
    "style": "unbrand", "body_font": "EB Garamond", "body_weight": 500, "heading_font": "EB Garamond",
    "label_font": "", "heading_weight": 700, "body_size": 12, "leading": 1.62, "accent": "#111111",
    "first_line_indent": True, "quote_italic": True, "running_heads": False,
    "margins": {"top": 0.75, "bottom": 0.95, "inside": 1.0, "outside": 0.95}, "docx_font": "Garamond"}
PRESETS["isi"] = {
    "why": "Blueprints of Dominion look: numbered chapters, bold sans titles, grey subtitle band, block paragraphs",
    "style": "isi", "body_font": "Source Serif 4", "heading_font": "Inter", "label_font": "", "heading_weight": 700,
    "body_size": 11.5, "leading": 1.5, "accent": "#222222", "first_line_indent": False, "quote_italic": True,
    "label_numeric": True, "running_heads": True, "head_font": "Source Serif 4", "head_italic": True,
    "head_upper": False, "head_size": 8, "recto_head": "title",
    "margins": {"top": 0.85, "bottom": 0.95, "inside": 0.9, "outside": 0.8}, "docx_font": "Times New Roman"}
PRESET_SIGNALS = {
    "devotional": r"\b(god|lord|jesus|christ|holy spirit|scripture|prayer|pray|faith|bible|psalm|church|grace|worship|kingdom|amen|verse|gospel|blessing)\b",
    "business": r"\b(business|brand|branding|clients?|customers?|revenue|profit|market(ing)?|strategy|leadership|leaders?|team|startup|entrepreneur|sales|pricing|investors?|company|career|negotiat\w*)\b",
    "warm": r"\b(heal(ing)?|feelings?|relationships?|marriage|parent(ing)?|children|self-care|anxiety|love|forgive(ness)?|emotions?|wellness|mother|father|family)\b",
    "workbook": r"(\b(exercise|worksheet|journal prompt|write down|fill in|reflect on|your answer|step \d+|checklist|activity)\b|_{5,})",
    "classic": r"\b(i remember|years later|my childhood|that night|when i was|we lived|growing up)\b",
}


def detect_preset(text: str) -> tuple[str, dict]:
    """Score the manuscript against each preset's vocabulary. Returns (preset, per-1000-word scores)."""
    words = max(word_count(text), 1)
    low = text.lower()
    scores = {k: round(len(re.findall(p, low)) * 1000 / words, 2) for k, p in PRESET_SIGNALS.items()}
    best = max(scores, key=scores.get)
    # thresholds: a faint signal is not a genre; fall back to the classic book look
    if scores[best] < {"devotional": 4, "business": 5, "warm": 5, "workbook": 1.5, "classic": 1}.get(best, 3):
        best = "classic"
    if best == "warm" and scores["devotional"] >= 4:
        best = "devotional"
    return best, scores


def parse_front_matter(text: str) -> tuple[dict, str]:
    import yaml
    if text.startswith("---\n") or text.startswith("---\r\n"):
        end = text.find("\n---", 4)
        if end != -1:
            meta = yaml.safe_load(text[4:end]) or {}
            return meta, text[end + 4:].lstrip("\r\n")
    return {}, text


def load_project(root: str | Path) -> tuple[dict, dict, list[Section]]:
    import yaml
    root = Path(root)
    cfg = yaml.safe_load((root / "book.yml").read_text(encoding="utf-8")) or {}
    meta = {**DEFAULT_META, **(cfg.get("meta") or {})}
    user_layout = dict(cfg.get("layout") or {})
    layout = {**DEFAULT_LAYOUT, **user_layout}
    entries = cfg.get("contents")
    man = root / "manuscript"
    if not entries:
        entries = ["auto:title", "auto:copyright"]
        files = sorted(p for p in man.rglob("*.md"))
        front = [f for f in files if f.parent.name.startswith(("0", "front"))]
        rest = [f for f in files if f not in front]
        entries += [str(f.relative_to(man)).replace("\\", "/") for f in front[:1] if "dedic" in f.name]
        entries += ["auto:toc"]
        entries += [str(f.relative_to(man)).replace("\\", "/") for f in front if "dedic" not in f.name]
        entries += [str(f.relative_to(man)).replace("\\", "/") for f in rest]
    sections: list[Section] = []
    chap_no = 0
    for e in entries:
        opts = {}
        if isinstance(e, dict):
            opts = dict(e)
            e = opts.pop("file", None) or ("auto:" + opts.pop("auto"))
        if e.startswith("auto:"):
            typ = e[5:]
            if typ == "autograph" and user_layout.get("autograph_page") is False:
                continue
            titles = {"title": "Title Page", "copyright": "Copyright", "toc": "Contents",
                      "halftitle": meta["title"], "autograph": "Signed Copy"}
            sections.append(Section(type=typ, title=opts.get("title", titles.get(typ, typ.title())),
                                    body_md="", toc=False, recto=typ != "copyright",
                                    slug=typ, meta={"auto": True, **opts}))
            continue
        p = man / e
        fm, body = parse_front_matter(p.read_text(encoding="utf-8"))
        fm.update(opts)
        m = re.match(r"^#\s+(.+?)\s*$", body, re.M)
        title = fm.get("title") or (m.group(1) if m else p.stem.replace("-", " ").title())
        if m and not fm.get("title"):
            body = body[: m.start()] + body[m.end():]
        typ = fm.get("type") or classify_heading(title) or ("chapter" if "front" not in e and "back" not in e else
                                                           ("preface" if "front" in e else "appendix"))
        label = fm.get("label", "")
        if typ == "chapter" and not label and fm.get("numbered", layout.get("number_chapters", True)):
            cm = CHAPTER_RE.match(title)
            chap_no += 1
            if cm:
                n = number_value(cm.group(2))
                label = f"Chapter {NUM_WORDS[n - 1].title()}" if n and 0 < n <= 20 and layout.get("chapter_words", True) \
                    else f"Chapter {cm.group(2).title()}"
                title = cm.group(3).strip() or title
            else:
                label = f"Chapter {NUM_WORDS[chap_no - 1].title() if chap_no <= 20 else chap_no}"
                fm["_autolabel"] = True
        no_toc = typ in ("dedication", "epigraph", "copyright", "title", "halftitle")
        sections.append(Section(type=typ, title=title.strip(), body_md=body.strip(), path=str(p),
                                label=label, subtitle=fm.get("subtitle", ""), toc=fm.get("toc", not no_toc),
                                recto=fm.get("recto", True), slug="", meta=fm))
    # a book with its own labels (Part One, Interlude...) gets no invented "Chapter N" labels
    if any(s.meta.get("label") and not s.meta.get("_autolabel") for s in sections):
        for s in sections:
            if s.meta.get("_autolabel"):
                s.label = ""
    # design preset: DEFAULT_LAYOUT < preset < the book's own layout keys
    preset = str(user_layout.get("preset", "auto")).lower()
    scores = {}
    if preset == "auto":
        preset, scores = detect_preset("\n".join(md_plain(s.body_md) for s in sections))
    p = PRESETS.get(preset, PRESETS["classic"])
    layout = {**DEFAULT_LAYOUT, **{k: v for k, v in p.items() if k != "why"}, **user_layout}
    layout["preset"] = preset
    layout["preset_why"] = p["why"]
    layout["preset_scores"] = scores
    small = str(layout.get("trim", "")).lower() in ("a5", "5x8", "5.06x7.81", "5.25x8")
    # (no automatic shrink on small trims: readers found 11pt Garamond at A5 too small, 2026-10-18)
    seen = set()
    for i, s in enumerate(sections):
        base = s.slug or slugify(s.title)
        slug = base
        n = 2
        while slug in seen:
            slug = f"{base}-{n}"
            n += 1
        s.slug = slug
        seen.add(slug)
    return meta, layout, sections


# --------------------------------------------------------------------------
# Markdown -> HTML (the book dialect)
# --------------------------------------------------------------------------
# Supported: # ## ### headings, paragraphs, *italic* **bold** `code`, [text](url),
# > blockquote (a last line starting with "--" or an em dash becomes the attribution),
# - / * / 1. lists, *** or * * * scene break, \newpage, ![alt](img){caption},
# ::: callout Label ... ::: and ::: pullquote ... ::: (designed interiors only),
# lines starting with "<" pass through as raw HTML, [^1] footnotes with [^1]: text.

SMART_QUOTES = True  # build_book sets this from layout.smart_quotes


def smart_quotes(s: str) -> str:
    """Typesetter's quotes: straight " and ' become curly. Leaves code spans and URLs alone."""
    if not SMART_QUOTES or ('"' not in s and "'" not in s):
        return s
    parts = re.split(r"(`[^`]*`|\]\([^)]*\))", s)
    for i in range(0, len(parts), 2):
        t = parts[i]
        t = re.sub(r"(?<=\w)'(?=\w)", "\u2019", t)                      # don't, Kenya's
        t = re.sub(r"'(?=\d0s\b)", "\u2019", t)                          # '90s
        t = re.sub(r"(^|[\s(\[{\u2014\u2013\-/])'", "\\1\u2018", t)      # opening single
        t = t.replace("'", "\u2019")
        t = re.sub(r'(^|[\s(\[{\u2014\u2013\-/\u2018])"', "\\1\u201c", t)  # opening double
        t = t.replace('"', "\u201d")
        parts[i] = t
    return "".join(parts)


def inline_md(s: str, footnotes: dict | None = None) -> str:
    s = smart_quotes(s)
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    if footnotes is not None:
        def fn(m):
            key = m.group(1)
            if key not in footnotes:
                return m.group(0)
            order = footnotes.setdefault("__order__", [])
            if key not in order:
                order.append(key)
            n = order.index(key) + 1
            return f'<sup class="fn-ref" id="fnref-{n}">{n}</sup>'
        s = re.sub(r"\[\^([^\]]+)\]", fn, s)
    s = s.replace("\n", "<br>")
    return s


def md_to_html(md: str, designed: bool = False) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    footnotes = {}
    keep = []
    for ln in lines:
        m = re.match(r"^\[\^([^\]]+)\]:\s*(.+)$", ln)
        if m:
            footnotes[m.group(1)] = m.group(2)
        else:
            keep.append(ln)
    lines = keep
    out: list[str] = []
    i = 0
    first_para = True

    def para_block(start):
        j = start
        buf = []
        while j < len(lines) and lines[j].strip() and not re.match(r"^(#{1,6}\s|>|[-*+]\s|\d+[.)]\s|:::|\\newpage|<|!\[)", lines[j]) \
                and not re.match(r"^\s*(\*\s*\*\s*\*|-{3,}|_{3,})\s*$", lines[j]):
            buf.append(lines[j].rstrip())
            j += 1
        return j, " ".join(b.strip() for b in buf)

    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        if not st:
            i += 1
            continue
        if st == "\\newpage":
            out.append('<div class="page-break"></div>')
            i += 1
            continue
        if re.match(r"^(\*\s*\*\s*\*|-{3,}|_{3,})$", st):
            out.append('<p class="scene-break" aria-hidden="true">*&#8195;*&#8195;*</p>')
            first_para = True
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", st)
        if m:
            lvl = min(len(m.group(1)) + 1, 4)  # '#' is the section title, so body '#' maps to h2
            out.append(f"<h{lvl}>{inline_md(m.group(2), footnotes)}</h{lvl}>")
            first_para = True
            i += 1
            continue
        if st.startswith(":::"):
            kind = st[3:].strip().split(None, 1)
            name = kind[0].lower() if kind else "callout"
            label = kind[1] if len(kind) > 1 else ""
            j = i + 1
            inner = []
            while j < len(lines) and lines[j].strip() != ":::":
                inner.append(lines[j])
                j += 1
            inner_html = md_to_html("\n".join(inner), designed)
            if name == "pullquote":
                out.append(f'<aside class="pull-quote">{inner_html}</aside>')
            else:
                lab = f'<span class="callout-label">{inline_md(label)}</span>' if label else ""
                out.append(f'<aside class="callout callout-{slugify(name)}">{lab}{inner_html}</aside>')
            i = j + 1
            continue
        if st.startswith("<"):
            j = i
            buf = []
            while j < len(lines) and lines[j].strip():
                buf.append(lines[j])
                j += 1
            out.append("\n".join(buf))
            i = j
            continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)(\{(.+)\})?$", st)
        if m:
            cap = f"<figcaption>{inline_md(m.group(4))}</figcaption>" if m.group(4) else ""
            out.append(f'<figure><img src="{html.escape(m.group(2))}" alt="{html.escape(m.group(1))}">{cap}</figure>')
            i += 1
            continue
        if st.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            attribution = ""
            if buf and re.match(r"^\s*(--|—|―)\s*\S", buf[-1]):
                attribution = re.sub(r"^\s*(--|—|―)\s*", "", buf.pop())
            inner = md_to_html("\n".join(buf), designed)
            cite = f'<p class="attribution">{inline_md(attribution, footnotes)}</p>' if attribution else ""
            out.append(f"<blockquote>{inner}{cite}</blockquote>")
            first_para = True
            continue
        if re.match(r"^([-*+]|\d+[.)])\s+", st):
            ordered = bool(re.match(r"^\d", st))
            tag = "ol" if ordered else "ul"
            items = []
            while i < len(lines) and re.match(r"^\s*([-*+]|\d+[.)])\s+", lines[i]):
                item = re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", lines[i])
                i += 1
                while i < len(lines) and lines[i].startswith(("  ", "\t")) and lines[i].strip():
                    item += " " + lines[i].strip()
                    i += 1
                items.append(f"<li>{inline_md(item, footnotes)}</li>")
            out.append(f"<{tag}>{''.join(items)}</{tag}>")
            first_para = True
            continue
        i, text = para_block(i)
        if not text:
            i += 1
            continue
        cls = ' class="first"' if first_para else ""
        out.append(f"<p{cls}>{inline_md(text, footnotes)}</p>")
        first_para = False
    order = footnotes.get("__order__", [])
    if order:
        notes = "".join(f"<li>{inline_md(footnotes[k])}</li>" for k in order)
        out.append(f'<div class="chapter-notes"><p class="first"><em>Notes</em></p><ol>{notes}</ol></div>')
    return "\n".join(out)


def md_plain(md: str) -> str:
    """Strip the book Markdown down to reading text (for counts and lint)."""
    t = re.sub(r"^\[\^[^\]]+\]:.*$", "", md, flags=re.M)
    t = re.sub(r"^:::.*$", "", t, flags=re.M)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"^\s*(#{1,6}|>|[-*+]|\d+[.)])\s?", "", t, flags=re.M)
    t = re.sub(r"[*_`]", "", t)
    return t
