#!/usr/bin/env python3
"""
structure_plan.py - give structure to raw material: transcripts, unfinished drafts, text with no chapters.

Step 1, dump: number every paragraph so Claude can read the material and plan the book.

    python structure_plan.py dump SOURCE [-o WORKDIR]
        SOURCE: .docx .txt .md, or a transcript (.srt .vtt or plain text)
        writes WORKDIR/paragraphs.md   (P0001 | text ...  read this)
               WORKDIR/paragraphs.json (the same, for the build step)
               WORKDIR/plan.json       (a template to fill in)
               WORKDIR/stats.md        (words, filler counts, headings found)

Step 2, plan: Claude fills plan.json and shows the author the outline before building.

    {
      "meta":   {"title": "...", "subtitle": "", "author": "...", "year": "", "isbn_print": ""},
      "preset": "auto",                  # or classic | devotional | business | warm | workbook
      "clean_fillers": true,             # drop um/uh/erm and doubled words ("the the"); every change logged
      "sections": [
        {"type": "introduction", "title": "Introduction", "text": "...", "drafted": true},
        {"type": "chapter", "title": "The First Step", "from": "P0001", "to": "P0042",
         "subheads": {"P0020": "What the Rain Taught Me"}},
        {"type": "about-author", "title": "About the Author", "from": "P0300", "to": "P0302"}
      ],
      "replace": {"P0012": "the paragraph, lightly cleaned (fillers, false starts), meaning unchanged"},
      "drop":    ["P0003", "P0004"]      # off-topic chatter, duplicates, 'can you hear me' lines
    }

    A section takes either a paragraph range (from/to: the author's words) or "text" (new
    writing, which MUST carry "drafted": true until the author approves it).

Step 3, build: assemble the book project, refusing to lose a paragraph silently.

    python structure_plan.py build WORKDIR/plan.json PROJECT_DIR [--allow-gaps]
        every paragraph must be in exactly one section or listed in "drop"
        writes the project (book.yml + manuscript/) and PROJECT_DIR/changes.md, the list the
        author approves: drafted sections, replaced paragraphs (before/after), dropped
        paragraphs, filler cleanups.
    Then: python make_book.py PROJECT_DIR --trim a5
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bookcore as bc  # noqa: E402

FILLERS = re.compile(r"(?i)(?<![\w'])(um+|uh+|erm+|uhm+|hmm+|ah+)(?![\w'])[,.]?\s*")
DOUBLED = re.compile(r"(?i)\b(\w+)(\s+\1\b)+")
TIMESTAMP = re.compile(r"^\s*(\d+\s*$|\d{1,2}:\d{2}(:\d{2})?([.,]\d+)?\s*(-->.*)?$|WEBVTT.*$|NOTE\b.*$)")
SPEAKER = re.compile(r"^\s*(\[?[A-Z][\w .'-]{0,30}\]?|Speaker \d+)\s*:\s+")


def load_source(src: Path) -> list[dict]:
    ext = src.suffix.lower()
    if ext in (".srt", ".vtt"):
        lines = [l for l in src.read_text(encoding="utf-8-sig").splitlines() if l.strip() and not TIMESTAMP.match(l)]
        text = " ".join(re.sub(r"<[^>]+>", "", l).strip() for l in lines)
        return regroup([text])
    paras, facts = bc.read_manuscript(src)
    out = []
    for p in paras:
        if not p.text.strip():
            continue
        out.append({"text": p.text.strip(), "md": p.md.strip() or p.text.strip(), "heading": p.level or 0,
                    "kind": p.kind})
    # transcripts often arrive as a few giant paragraphs: split them into readable ones
    if out and max(bc.word_count(o["text"]) for o in out) > 400:
        big = []
        for o in out:
            if bc.word_count(o["text"]) > 400 and o["kind"] == "text":
                big += regroup([o["text"]])
            else:
                big.append(o)
        out = big
    if facts.get("media"):
        print(f"note: {len(facts['media'])} images found; import with import_docx.py for image-heavy books")
    return out


def regroup(texts, target=150):
    """Split long text into ~target-word paragraphs at sentence ends."""
    out = []
    for t in texts:
        sents = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", t)
        buf = []
        for s in sents:
            buf.append(s)
            if bc.word_count(" ".join(buf)) >= target:
                out.append(" ".join(buf))
                buf = []
        if buf:
            out.append(" ".join(buf))
    return [{"text": x, "md": x, "heading": 0, "kind": "text"} for x in out if x.strip()]


def pid(i):
    return f"P{i + 1:04d}"


def cmd_dump(a):
    src = Path(a.source)
    work = Path(a.out) if a.out else bc.work_root(bc.slugify(src.stem), "structure")
    work.mkdir(parents=True, exist_ok=True)
    paras = load_source(src)
    for i, p in enumerate(paras):
        p["id"] = pid(i)
    (work / "paragraphs.json").write_text(json.dumps(paras, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# {src.name}: {len(paras)} paragraphs\n",
             "Format: ID | [H] marks a line that looks like a heading | text\n"]
    for p in paras:
        t = p["text"].replace("\n", " / ")
        mark = "[H] " if p["heading"] or (len(t.split()) <= 10 and not re.search(r"[.,;:!?]$", t)) else ""
        lines.append(f"{p['id']} | {mark}{t}")
    (work / "paragraphs.md").write_text("\n".join(lines), encoding="utf-8")
    full = "\n".join(p["text"] for p in paras)
    fillers = len(FILLERS.findall(full))
    doubled = len(DOUBLED.findall(full))
    speakers = sum(1 for p in paras if SPEAKER.match(p["text"]))
    preset, scores = bc.detect_preset(full)
    stats = [f"# Stats: {src.name}", f"- paragraphs: {len(paras)}", f"- words: {bc.word_count(full):,}",
             f"- heading-like lines: {sum(1 for l in lines if '| [H]' in l)}",
             f"- fillers (um/uh/erm...): {fillers}", f"- doubled words: {doubled}",
             f"- speaker labels: {speakers}" + ("  (interview/transcript: decide whose voice the book is in)" if speakers else ""),
             f"- suggested design preset: {preset} {scores}",
             f"- looks like a transcript: {'yes' if fillers > 10 or speakers > 5 or src.suffix.lower() in ('.srt', '.vtt') else 'no'}"]
    (work / "stats.md").write_text("\n".join(stats), encoding="utf-8")
    template = {"meta": {"title": "", "subtitle": "", "author": "", "year": "", "isbn_print": ""},
                "preset": "auto", "clean_fillers": fillers > 0,
                "sections": [{"type": "chapter", "title": "", "from": paras[0]["id"] if paras else "P0001",
                              "to": paras[-1]["id"] if paras else "P0001", "subheads": {}}],
                "replace": {}, "drop": []}
    plan = work / "plan.json"
    if not plan.exists():
        plan.write_text(json.dumps(template, indent=2), encoding="utf-8")
    print("\n".join(stats))
    print(f"\nread: {work / 'paragraphs.md'}\nfill: {plan}")


def clean_text(t, log, where):
    new = FILLERS.sub("", t)
    new = DOUBLED.sub(lambda m: m.group(1), new)
    new = re.sub(r"\s{2,}", " ", new).strip()
    new = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), new)
    if new != t:
        log.append((where, t, new))
    return new


def cmd_build(a):
    plan_path = Path(a.plan)
    work = plan_path.parent
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    paras = json.loads((work / "paragraphs.json").read_text(encoding="utf-8"))
    ids = [p["id"] for p in paras]
    index = {p["id"]: i for i, p in enumerate(paras)}
    drop = set(plan.get("drop", []))
    replace = plan.get("replace", {})
    unknown = [x for x in list(drop) + list(replace) if x not in index]
    owner = {}
    problems = []
    for si, s in enumerate(plan["sections"]):
        if "text" in s:
            if not s.get("drafted") and not s.get("approved"):
                problems.append(f"section '{s.get('title')}' has new text but no \"drafted\": true")
            continue
        if s.get("from") not in index or s.get("to") not in index:
            problems.append(f"section '{s.get('title')}' has a bad range {s.get('from')}..{s.get('to')}")
            continue
        for i in range(index[s["from"]], index[s["to"]] + 1):
            if ids[i] in owner:
                problems.append(f"{ids[i]} is in two sections ('{plan['sections'][owner[ids[i]]].get('title')}' and '{s.get('title')}')")
            owner[ids[i]] = si
    gaps = [x for x in ids if x not in owner and x not in drop]
    if unknown:
        problems.append(f"unknown paragraph ids: {unknown[:10]}")
    if gaps and not a.allow_gaps:
        runs, start = [], None
        for x in ids:
            if x in gaps and start is None:
                start = x
            if x not in gaps and start is not None:
                runs.append(start)
                start = None
        problems.append(f"{len(gaps)} paragraph(s) are in no section and not dropped (would be lost): "
                        + ", ".join(gaps[:15]) + (" ..." if len(gaps) > 15 else ""))
    if problems:
        print("PLAN PROBLEMS - nothing written:")
        for p in problems:
            print(" -", p)
        sys.exit(1)

    root = Path(a.project)
    man = root / "manuscript"
    if man.exists():
        import datetime
        man.rename(root / f"manuscript.bak-{datetime.datetime.now():%Y%m%d-%H%M%S}")
    for d in ("front", "body", "back"):
        (man / d).mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir(exist_ok=True)
    clean_log, contents_mid = [], []
    counters = {"front": 0, "body": 0, "back": 0}
    dedication = []
    for s in plan["sections"]:
        typ = s.get("type", "chapter")
        title = s.get("title") or typ.replace("-", " ").title()
        matter = "front" if typ in bc.FRONT_TYPES else "back" if typ in bc.BACK_TYPES else "body"
        counters[matter] += 1
        fname = f"{counters[matter]:02d}-{bc.slugify(title)}.md"
        fm = {"type": typ}
        if s.get("drafted"):
            fm["drafted"] = True
        if s.get("approved"):
            fm["approved"] = True
        for k in ("label", "subtitle"):
            if s.get(k):
                fm[k] = s[k]
        body = []
        if "text" in s:
            body.append(s["text"].strip())
        else:
            subheads = s.get("subheads", {})
            for i in range(index[s["from"]], index[s["to"]] + 1):
                p = paras[i]
                if p["id"] in drop:
                    continue
                if p["id"] in subheads:
                    body.append(f"## {subheads[p['id']]}")
                md = replace.get(p["id"], p["md"])
                if plan.get("clean_fillers") and p.get("kind", "text") == "text":
                    md = clean_text(md, clean_log, p["id"])
                if p["heading"] and p["id"] not in replace and i == index[s["from"]] and \
                        re.sub(r"\W", "", p["text"].lower()) in re.sub(r"\W", "", title.lower()):
                    continue  # the source heading line that this section's title replaces
                body.append(md)
        head = "---\n" + "".join(f"{k}: {json.dumps(v) if isinstance(v, str) else str(v).lower()}\n" for k, v in fm.items()) + "---\n"
        (man / matter / fname).write_text(f"{head}# {title}\n\n" + "\n\n".join(body) + "\n", encoding="utf-8")
        rel = f"{matter}/{fname}"
        (dedication if typ == "dedication" else contents_mid).append((("front", "body", "back").index(matter), rel))

    import yaml
    meta = {k: v for k, v in (plan.get("meta") or {}).items() if v}
    cfg = {"meta": {"title": "Untitled", **meta},
           "layout": {"trim": a.trim, "preset": plan.get("preset", "auto")},
           "contents": ["auto:autograph", "auto:title", "auto:copyright"] + [r for _, r in dedication] + ["auto:toc"]
           + [r for _, r in sorted(contents_mid, key=lambda x: x[0])]}
    (root / "book.yml").write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")

    L = [f"# Changes for author approval: {cfg['meta'].get('title')}\n",
         "Nothing below is final until the author approves it. Approve a drafted section by changing",
         "`drafted: true` to `approved: true` at the top of its file.\n",
         f"## Structure ({len(plan['sections'])} sections)"]
    for s in plan["sections"]:
        span = f"{s['from']}-{s['to']}" if "from" in s else "NEW TEXT (drafted)"
        L.append(f"- {s.get('type')}: **{s.get('title')}**  [{span}]")
    drafted = [s for s in plan["sections"] if s.get("drafted")]
    if drafted:
        L.append(f"\n## Drafted text ({len(drafted)}): written for the author, needs approval")
        for s in drafted:
            L.append(f"\n### {s.get('title')}\n\n{s['text'].strip()}")
    if replace:
        L.append(f"\n## Edited paragraphs ({len(replace)})")
        for k, v in replace.items():
            L.append(f"\n**{k}** before:\n> {paras[index[k]]['text']}\n\nafter:\n> {v}")
    if drop:
        L.append(f"\n## Removed paragraphs ({len(drop)})")
        for k in sorted(drop):
            L.append(f"- {k}: {paras[index[k]]['text'][:160]}")
    if clean_log:
        L.append(f"\n## Filler and doubled-word cleanups ({len(clean_log)})")
        for where, before, after in clean_log[:200]:
            L.append(f"- {where}: \"{before[:120]}\" -> \"{after[:120]}\"")
    (root / "changes.md").write_text("\n".join(L), encoding="utf-8")
    print(f"project: {root}  sections: {len(plan['sections'])}  drafted: {len(drafted)}  edited: {len(replace)}  "
          f"dropped: {len(drop)}  filler cleanups: {len(clean_log)}")
    print(f"for approval: {root / 'changes.md'}")
    print(f"next: python make_book.py \"{root}\" --trim {a.trim}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("source")
    d.add_argument("-o", "--out")
    b = sub.add_parser("build")
    b.add_argument("plan")
    b.add_argument("project")
    b.add_argument("--trim", default="a5")
    b.add_argument("--allow-gaps", action="store_true")
    a = ap.parse_args()
    cmd_dump(a) if a.cmd == "dump" else cmd_build(a)


if __name__ == "__main__":
    main()
