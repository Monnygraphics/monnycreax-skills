#!/usr/bin/env python3
"""
import_docx.py - turn a canonical .docx (or .txt / .md) manuscript into a book project.

    python import_docx.py BOOK.docx PROJECT_DIR [--title T] [--author A] [--keep-toc]

Creates:
    PROJECT_DIR/book.yml                 meta + layout + explicit contents order
    PROJECT_DIR/manuscript/front/*.md    dedication, preface, ...
    PROJECT_DIR/manuscript/body/*.md     chapters (and parts)
    PROJECT_DIR/manuscript/back/*.md     acknowledgements, about the author, ...
    PROJECT_DIR/import-log.md            what was detected, every automatic change

Rules carried in (Scribe lessons):
  * text is read line-break aware, so words never fuse
  * tracked insertions are kept and deletions dropped (= accept all); the log says so
  * the source's own contents list is dropped and rebuilt from body titles
  * emoji are stripped from headings; invisible characters normalised
  * nothing is rewritten: wording, quotes and em dashes stay as the author wrote them
The .docx is never modified.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bookcore as bc  # noqa: E402


def yaml_str(v):
    v = str(v)
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("project")
    ap.add_argument("--title")
    ap.add_argument("--author")
    ap.add_argument("--keep-toc", action="store_true", help="keep the source contents section as text")
    ap.add_argument("--force", action="store_true", help="write into a non-empty project folder")
    a = ap.parse_args()

    root = Path(a.project)
    if root.exists() and any(root.iterdir()) and not a.force:
        sys.exit(f"{root} is not empty. Pass --force to write into it (existing files with the same names are replaced).")
    paras, facts = bc.read_manuscript(a.docx)
    log = [f"# Import log\n", f"- Source: `{Path(a.docx).resolve()}`",
           f"- Paragraphs read: {len(paras)}",
           f"- Tracked changes: {facts['insertions']} insertions kept, {facts['deletions']} deletions dropped (accept-all)"
           + ("  **Confirm with the author that accept-all is right.**" if facts['insertions'] + facts['deletions'] else ""),
           f"- Comments in source: {len(facts['comments'])} (not imported into the text; see manuscript_map.py comments.md)",
           f"- Images in source: {len(facts.get('media', {}))} imported to assets/media/ (check placement and resolution)",
           f"- Tables in source: {facts['tables']} imported as simple tables (merged cells and colours are not kept)", ""]
    changes = []

    # Title guess: first Title-styled or first centred, large paragraph before any heading
    title = a.title
    author = a.author or ""
    for p in paras[:15]:
        if p.text.strip() and (p.style.lower() == "title" or (p.level == 1 and not bc.classify_heading(p.text))):
            title = title or p.text.strip()
            break

    sections = []
    for sec in bc.split_docx_sections(paras):
        changes += sec.get("changes", [])
        if sec.get("book_title"):
            title = title or sec["book_title"]
        out_lines = []
        for p in sec["paras"]:
            t = p.text.strip()
            md = p.md.strip()
            if p.level == 2:
                md = "## " + bc.EMOJI_RE.sub("", t).strip()
            elif p.level >= 3:
                md = "### " + bc.EMOJI_RE.sub("", t).strip()
            elif p.is_list:
                md = "- " + md
            elif p.style.lower() in ("quote", "intensequote", "blocktext"):
                md = "> " + md.replace("\n", "\n> ")
            fused = bc.combined_word_suspects(p.text)
            if fused:
                changes.append(f"possible fused words left for review (not changed) in '{sec['title'][:40]}': {', '.join(fused[:6])}")
            if p.page_break_before and out_lines:
                out_lines += ["\newpage", ""]
            out_lines += [md, ""]
        sections.append({"title": sec["title"], "type": sec["type"], "lines": out_lines})

    # The opening block (before the first heading) is usually title/copyright text: keep it as notes.
    opening = sections.pop(0) if sections and sections[0]["type"] == "opening" else None
    if opening and any(l.strip() for l in opening["lines"]):
        text = "\n".join(opening["lines"])
        m = re.search(r"(?:copyright|©)\s*(?:©)?\s*(\d{4})\s+(?:by\s+)?([A-Z][^\n.]{2,60})", text, re.I)
        if m:
            author = author or m.group(2).strip()
        isbn = re.search(r"ISBN[^\d]*([\d\-X ]{10,17})", text)
        by = re.search(r"(?im)^\s*by\s+([A-Z][\w.'\- ]{2,60})\s*$", text)
        if by:
            author = author or by.group(1).strip()
        log.append("Opening text before the first heading (title/copyright material) was not imported as a section:")
        log.append("```\n" + text.strip()[:1500] + "\n```")
        log.append("")
    else:
        isbn = None

    man = root / "manuscript"
    if man.exists():
        import datetime
        bak = root / f"manuscript.bak-{datetime.datetime.now():%Y%m%d-%H%M%S}"
        man.rename(bak)
        log.append(f"- Previous manuscript folder moved to {bak.name} (nothing deleted).")
    for d in ("front", "body", "back"):
        (man / d).mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir(exist_ok=True)
    if facts.get("media"):
        (root / "assets" / "media").mkdir(exist_ok=True)
        for name, blob in facts["media"].items():
            (root / "assets" / "media" / name).write_bytes(blob)
    counters = {"front": 0, "body": 0, "back": 0}
    contents = ["auto:autograph", "auto:title", "auto:copyright"]
    after_toc = []
    dedication = []
    for s in sections:
        if not s["title"] and not any(x.strip() for x in s["lines"]):
            continue
        typ = s["type"]
        prose = sum(1 for l in s["lines"] if len(l.split()) > 25)
        if typ == "toc" and prose:
            log.append(f"- **Kept** a contents-like section with {prose} prose paragraph(s): check it by hand ({s['title']}).")
            typ = s["type"] = "preface"
        if typ == "toc" and not a.keep_toc:
            log.append(f"- Dropped source contents section ({sum(1 for l in s['lines'] if l.strip())} lines); it is rebuilt from body titles.")
            continue
        matter = "front" if typ in bc.FRONT_TYPES else "back" if typ in bc.BACK_TYPES else "body"
        counters[matter] += 1
        fname = f"{counters[matter]:02d}-{bc.slugify(s['title'])}.md"
        body = "\n".join(s["lines"]).strip()
        body = re.sub(r"\n{3,}", "\n\n", body)
        fm = f"---\ntype: {typ}\n---\n" if typ != (bc.classify_heading(s["title"]) or "chapter") else ""
        (man / matter / fname).write_text(f"{fm}# {s['title']}\n\n{body}\n", encoding="utf-8")
        rel = f"{matter}/{fname}"
        if typ == "dedication":
            dedication.append(rel)
        else:
            after_toc.append((("front", "body", "back").index(matter), rel))
        log.append(f"- {typ:<16} {rel}  ({bc.word_count(bc.md_plain(body)):,} words)")
    contents += dedication + ["auto:toc"] + [r for _, r in sorted(after_toc, key=lambda x: x[0])]

    yml = ["# Book project. Edit meta and layout; reorder 'contents' to reorder the book.",
           "meta:",
           f"  title: {yaml_str(title or Path(a.docx).stem)}",
           '  subtitle: ""',
           f"  author: {yaml_str(author)}",
           '  publisher: ""',
           '  year: ""',
           '  edition: "First edition"',
           f"  isbn_print: {yaml_str(isbn.group(1).strip() if isbn else '')}",
           '  isbn_ebook: ""',
           '  location: ""',
           '  contact: ""',
           '  language: en',
           '  description: ""',
           "layout:",
           "  trim: 6x9            # 5x8 5.25x8 5.5x8.5 6x9 6.14x9.21 7x10 8.5x11 ...",
           "  preset: auto         # auto | classic | devotional | business | warm | workbook (auto reads the text)",
           "  # body_font / heading_font / label_font / body_size / leading / accent override the preset",
           "  autograph_page: true # a signing page at the front (Signed for / By / Date / Note)",
           "  margins: auto        # auto = KDP gutter for the page count, or {top, bottom, inside, outside} in inches",
           "  chapter_start: right # right = chapters open on odd pages; any = next page",
           "  running_heads: true",
           "  verso_head: author   # author | title",
           "  toc_page_numbers: true",
           "  paper: cream         # white | cream (spine maths)",
           "  docx_size: 12",
           "  docx_line_spacing: 1.5",
           "contents:"]
    yml += [f"  - {c}" for c in contents]
    (root / "book.yml").write_text("\n".join(yml) + "\n", encoding="utf-8")
    if changes:
        log.append("\n## Automatic changes and review notes")
        log += [f"- {c}" for c in changes]
    log.append("\n## Check before building\n- meta in book.yml (title, author, ISBN, publisher, year)\n- section types: front matter written by the author is a Preface, not a Foreword\n- any list or quote formatting the importer guessed")
    (root / "import-log.md").write_text("\n".join(log), encoding="utf-8")
    print(f"project: {root}  sections: {sum(counters.values())} (front {counters['front']}, body {counters['body']}, back {counters['back']})")
    print(f"log: {root / 'import-log.md'}")


if __name__ == "__main__":
    main()
