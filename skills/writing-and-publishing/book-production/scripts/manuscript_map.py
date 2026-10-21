#!/usr/bin/env python3
"""
manuscript_map.py - Stage 1 "deep read" map + editorial lint for a manuscript.

    python manuscript_map.py BOOK.docx|BOOK.md|PROJECT_DIR [-o OUT_DIR] [--cap 3] [--trim 6x9]

Writes to OUT_DIR (default: <input>-map/):
    map.md          the map: counts, page estimates, chapters, matter, voices, flags
    citations.csv   every attributed quote, status=unverified (Stage 4 worksheet)
    comments.md     reviewer comments with their anchor text (docx only)

It only reads. It never edits the manuscript.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bookcore as bc  # noqa: E402

# Words per printed page, typical trade nonfiction setting (body 11-12pt, ~1.4 leading).
WPP = {"5x8": 230, "5.25x8": 245, "5.5x8.5": 270, "6x9": 320, "6.14x9.21": 330,
       "7x10": 410, "8.5x11 (12pt, 1.5 sp)": 420}
TRADE_MIN_PAGES = 100

SPEECH_VERBS = r"(?:says|said|writes|wrote|notes|noted|puts it|put it|argues|argued|observes|observed|reminds us|teaches|taught|once said|explains|explained|declares|declared|insists|tells us|told me|told us)"
NAME = r"((?:(?:Dr|Prof|Rev|Apostle|Pastor|Bishop|Sir|Mr|Mrs|Ms)\.?\s)?[A-Z][a-zA-Z'\-]+(?:\s(?:de|van|von|da|la)?\s?[A-Z][a-zA-Z'\-]+){0,2})"
VOICE_PATTERNS = [
    re.compile(r"[\"“]([^\"”]{12,400})[\"”]\s*[,.]?\s*(?:—|--|-)?\s*" + NAME + r"\s+" + SPEECH_VERBS),
    re.compile(NAME + r"\s+" + SPEECH_VERBS + r"[,:]?\s*[\"“]([^\"”]{12,400})[\"”]"),
    re.compile(r"[\"“]([^\"”]{12,400})[\"”]\s*(?:—|--|―)\s*" + NAME),
    re.compile(r"(?:As|According to)\s+" + NAME + r"\s*(?:" + SPEECH_VERBS + r")?,\s*[\"“]?([^\"”.]{12,300})"),
]
NOT_NAMES = {"The", "This", "That", "It", "He", "She", "They", "We", "You", "I", "But", "And", "So",
             "God", "Jesus", "Lord", "Chapter", "Yes", "No", "Then", "When", "If", "One", "Someone",
             "People", "Everyone", "Nobody", "My", "Our", "Your", "His", "Her", "Their"}
DENY = re.compile(r"^(?:it|this|that|he|she|they|you|we|life|success|branding|a brand|the brand|authenticity)?\s*(?:is|was|are|were)\s+not\b|^(?:it's|that's|this isn't|it isn't|isn't|not)\b|^not\s", re.I)
LAND = re.compile(r"^(?:it|this|that|they|you|we)\s*(?:is|was|are|'s|’s)\b|^it’s\b|^it's\b", re.I)
PLACEHOLDER = re.compile(r"\b(TODO|TBD|TK|XX+|FIXME|lorem ipsum|insert (?:here|story|quote|example)|NEW SECTION|"
                         r"add (?:story|example|quote) here|\[\s*\]|\?\?\?+|reviewer:|editor:|comment:)", re.I)
PROMISE = re.compile(r"(at the end of (each|every) chapter|in (each|every) chapter you|in this book,? (you will|I will|we will)|"
                     r"(reflection|discussion) questions|workbook|exercises? (at|in) the end|later in this book|in chapter \w+,? (we|I|you) will)", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?”\"])\s+(?=[A-Z“\"])")


def sections_from_docx(path):
    paras, facts = bc.read_manuscript(path)
    out = []
    for sec in bc.split_docx_sections(paras):
        rows = [("h" if p.level in (2, 3) else "p", p.text.strip()) for p in sec["paras"] if p.text.strip()]
        title = sec["title"] or "(opening: title / copyright text)"
        out.append({"title": title, "type": "front-unknown" if sec["type"] == "opening" else sec["type"], "paras": rows})
        if sec.get("book_title"):
            facts["book_title"] = sec["book_title"]
    return out, facts


def sections_from_md_text(text):
    sections, cur = [], {"title": "(opening)", "type": "front-unknown", "paras": []}
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if not b:
            continue
        m = re.match(r"^#\s+(.+)$", b)
        if m and "\n" not in b:
            if cur["paras"] or cur["type"] != "front-unknown":
                sections.append(cur)
            t = m.group(1).strip()
            cur = {"title": t, "type": bc.classify_heading(t) or "chapter", "paras": []}
            continue
        kind = "h" if b.startswith("#") else ("q" if b.startswith(">") else "p")
        cur["paras"].append((kind, bc.md_plain(b).strip()))
    sections.append(cur)
    return sections


def sections_from_project(root):
    meta, layout, secs = bc.load_project(root)
    out = []
    for s in secs:
        if s.meta.get("auto"):
            continue
        paras = []
        for b in re.split(r"\n\s*\n", s.body_md):
            b = b.strip()
            if b:
                kind = "h" if b.startswith("#") else ("q" if b.startswith(">") else "p")
                paras.append((kind, bc.md_plain(b).strip()))
        out.append({"title": (s.label + ": " if s.label else "") + s.title, "type": s.type, "paras": paras})
    return out, meta


def sentences(text):
    return [s.strip() for s in SENT_SPLIT.split(text.replace("\n", " ")) if s.strip()]


def find_voices(sections):
    hits = []
    for si, s in enumerate(sections):
        body = [t for k, t in s["paras"] if k != "h"]
        for pi, t in enumerate(body):
            for pat in VOICE_PATTERNS:
                for m in pat.finditer(t):
                    g = m.groups()
                    name = next((x for x in g if x and re.match(r"^[A-Z]", x) and len(x) < 50 and len(x.split()) <= 4), "")
                    quote = max((x for x in g if x), key=len)
                    name = re.sub(r"^(?:As|According to|And|But|So)\s+", "", name.strip())
                    if not name or name.split()[0] in NOT_NAMES:
                        continue
                    pos = "opens section" if pi == 0 else ("closes section" if pi >= len(body) - 1 else "inside")
                    hits.append({"speaker": name.strip(), "quote": quote.strip(), "section": s["title"], "position": pos})
    # de-duplicate overlapping matches
    seen, uniq = set(), []
    for h in hits:
        key = (h["speaker"], re.sub(r"\W+", "", h["quote"].lower())[:30])
        if key not in seen:
            seen.add(key)
            uniq.append(h)
    # standalone blockquote paragraphs that end with an attribution line
    return uniq


def surname_mentions(sections, speakers):
    """Count every mention of each speaker's surname (catches unquoted borrowing)."""
    full = "\n".join(t for s in sections for _, t in s["paras"])
    out = {}
    for sp in speakers:
        last = sp.split()[-1]
        n_full = len(re.findall(r"\b%s\b" % re.escape(sp), full))
        n_last = len(re.findall(r"\b%s\b" % re.escape(last), full)) if len(last) >= 4 and len(sp.split()) > 1 else 0
        out[sp] = max(n_full, n_last)
    return out


def lint_section(s):
    flags = defaultdict(list)
    body = [t for k, t in s["paras"] if k != "h"]
    sents = [x for t in body for x in sentences(t)]
    # deny-deny-land: >=2 denials within a 4-sentence window followed by a landing line
    i = 0
    while i < len(sents):
        window = sents[i:i + 4]
        denials = [w for w in window if DENY.search(w)]
        if len(denials) >= 2 and any(LAND.search(w) and not DENY.search(w) for w in window[1:]):
            flags["deny-deny-land"].append(" / ".join(window)[:220])
            i += 4
        else:
            i += 1
    # fragment stacks: 3+ consecutive short paragraphs
    run = []
    for t in body + [""]:
        if t and len(t.split()) <= 7:
            run.append(t)
        else:
            if len(run) >= 3:
                flags["fragment stack"].append(" | ".join(run)[:200])
            run = []
    for t in body:
        for m in list(PLACEHOLDER.finditer(t))[:1]:
            flags["placeholder / note left in text"].append(t[max(0, m.start() - 40): m.end() + 60])
        for m in list(PROMISE.finditer(t))[:1]:
            flags["promise to verify"].append(t[max(0, m.start() - 60): m.end() + 80])
        for w in bc.combined_word_suspects(t):
            flags["fused words (lost line break?)"].append(w)
    if body:
        last = body[-1]
        if re.match(r"^[\"“]", last) or re.search(r"(—|--)\s*[A-Z][a-z]+(\s[A-Z][a-z]+)?\s*$", last):
            flags["section ends on a quote (landing quote)"].append(last[:160])
        first = body[0]
        if re.match(r"^[\"“]", first):
            flags["section opens on a quote"].append(first[:160])
    return flags


def estimate_pages(words):
    return {k: round(words / v) for k, v in WPP.items()}


def numbering_check(sections):
    nums = []
    for s in sections:
        m = bc.CHAPTER_RE.match(s["title"]) or bc.NUMBERED_RE.match(s["title"])
        if m:
            v = bc.number_value(m.group(2))
            if v:
                nums.append(v)
    if not nums:
        return None, []
    c = Counter(nums)
    dups = sorted(n for n, k in c.items() if k > 1)
    gaps = sorted(set(range(1, max(nums) + 1)) - set(nums))
    return nums, [f"duplicate number(s): {dups}"] * bool(dups) + [f"missing number(s): {gaps}"] * bool(gaps)


def structure_type(sections):
    titles = [s["title"] for s in sections]
    if sum(bool(bc.NUMBERED_RE.match(t)) for t in titles) >= 3:
        return "numbered (Law/Principle/Step N)"
    if sum(bool(bc.CHAPTER_RE.match(t)) for t in titles) >= 2:
        return "chapter-named (Chapter N / Chapter One)"
    if sum(s["type"] == "chapter" for s in sections) >= 3:
        return "section-named (headings, no numbering)"
    return "unclear - confirm with the author"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("-o", "--out")
    ap.add_argument("--cap", type=int, default=3, help="max appearances per outside voice before flagging")
    ap.add_argument("--trim", default="6x9")
    a = ap.parse_args()
    src = Path(a.source)
    out = Path(a.out) if a.out else bc.work_root(bc.slugify(src.stem), "map")
    out.mkdir(parents=True, exist_ok=True)

    facts, comments = {}, []
    if src.is_dir():
        sections, _meta = sections_from_project(src)
        kind = "book project"
    elif src.suffix.lower() in (".docx", ".txt"):
        sections, facts = sections_from_docx(src)
        comments = facts.get("comments", [])
        kind = "Word document"
    else:
        sections = sections_from_md_text(src.read_text(encoding="utf-8"))
        kind = "Markdown/text"

    all_text = "\n".join(t for s in sections for _, t in s["paras"])
    total_words = bc.word_count(all_text)
    uni = bc.unicode_report(all_text)
    voices = find_voices(sections)
    by_speaker = Counter(v["speaker"] for v in voices)
    mentions = surname_mentions(sections, list(by_speaker))
    nums, num_issues = numbering_check(sections)
    present_types = {s["type"] for s in sections}

    L = []
    L.append(f"# Manuscript map: {src.name}\n")
    L.append(f"- Source: `{src}` ({kind})")
    if src.is_file():
        import datetime
        L.append(f"- Modified: {datetime.datetime.fromtimestamp(src.stat().st_mtime):%Y-%m-%d %H:%M}")
    L.append(f"- Words: **{total_words:,}** across {len(sections)} sections")
    est = estimate_pages(total_words)
    L.append("- Estimated interior pages (body only, before front/back matter): " +
             ", ".join(f"{k}: ~{v}" for k, v in est.items()))
    t_est = est.get(a.trim, round(total_words / 320))
    if t_est < TRADE_MIN_PAGES:
        L.append(f"- **Length:** about {t_est} pages at {a.trim}. Under the ~{TRADE_MIN_PAGES}-page trade norm. "
                 "Grow with grounded scenes and real reader questions, never padding.")
    L.append(f"- Structure: {structure_type(sections)}")
    if num_issues:
        L.append(f"- **Numbering:** {'; '.join(num_issues)} (sequence found: {nums})")
    if facts:
        tc = facts["insertions"] + facts["deletions"]
        L.append(f"- Tracked changes: {facts['insertions']} insertions, {facts['deletions']} deletions"
                 + ("  **-> ask the author: accept all, or review first?**" if tc else ""))
        L.append(f"- Comments: {len(comments)}  |  Images: {facts['images']}  |  Tables: {facts['tables']}")
    L.append("")

    L.append("## Chapters and sections\n")
    L.append("| # | Type | Title | Words | Opens with | Closes with |")
    L.append("|---|---|---|---:|---|---|")
    for i, s in enumerate(sections, 1):
        body = [t for k, t in s["paras"] if k != "h"]
        w = bc.word_count(" ".join(body))
        first = (sentences(body[0])[0] if body else "")[:70].replace("|", "/")
        last = (sentences(body[-1])[-1] if body else "")[:70].replace("|", "/")
        L.append(f"| {i} | {s['type']} | {s['title'][:60]} | {w:,} | {first} | {last} |")
    chap_words = [bc.word_count(" ".join(t for k, t in s["paras"])) for s in sections if s["type"] == "chapter"]
    if chap_words:
        avg = sum(chap_words) / len(chap_words)
        uneven = [s["title"] for s in sections if s["type"] == "chapter"
                  and bc.word_count(" ".join(t for k, t in s["paras"])) < avg * 0.45]
        L.append(f"\nChapter length: avg {avg:,.0f} words, min {min(chap_words):,}, max {max(chap_words):,}."
                 + (f" Noticeably short: {', '.join(uneven)}." if uneven else ""))
    L.append("")

    L.append("## Front and back matter\n")
    want_front = ["title", "copyright", "dedication", "toc", "foreword/preface"]
    opening_txt = " ".join(t for s in sections if s["type"] == "front-unknown" for _, t in s["paras"]).lower()
    have = {"foreword/preface": bool(present_types & {"foreword", "preface"}),
            "title": bool(facts.get("book_title")) or "title" in present_types,
            "copyright": "copyright" in present_types or "copyright" in opening_txt or "©" in opening_txt}
    rows = []
    for t in want_front:
        ok = have.get(t, t in present_types)
        rows.append(f"- {'[x]' if ok else '[ ]'} {t}")
    for t in ["introduction", "conclusion", "appendix", "acknowledgements", "about-author", "bibliography", "notes"]:
        rows.append(f"- {'[x]' if t in present_types else '[ ]'} {t}")
    L += rows
    if "foreword" in present_types:
        L.append("- Check: is the Foreword written by someone else? If the author wrote it, it is a Preface.")
    if "toc" in present_types:
        L.append("- Source has its own contents list. Rebuild it from the body titles; source TOCs drift.")
    L.append("")

    L.append(f"## Outside voices (cap {a.cap} per voice)\n")
    if by_speaker:
        L.append("| Speaker | Attributed quotes | All surname mentions | Opens a section | Closes a section |")
        L.append("|---|---:|---:|---:|---:|")
        for sp, n in by_speaker.most_common():
            opens = sum(1 for v in voices if v["speaker"] == sp and v["position"] == "opens section")
            closes = sum(1 for v in voices if v["speaker"] == sp and v["position"] == "closes section")
            over = " **over cap**" if max(n, mentions.get(sp, 0)) > a.cap else ""
            L.append(f"| {sp}{over} | {n} | {mentions.get(sp, 0)} | {opens} | {closes} |")
        L.append("\nRun the thesis-integrity check: does the book argue something its borrowed voices undercut?")
    else:
        L.append("No attributed quotes detected by pattern. Still read for paraphrased borrowing.")
    L.append("")

    L.append("## Typography and hygiene\n")
    mixed_dq = uni["straight_double"] and uni["curly_double"]
    mixed_sq = uni["straight_single"] and uni["curly_single"]
    L.append(f"- Em dashes in the author's text: {uni['em_dash']} (flag only; the author decides). En dashes: {uni['en_dash']}. Double hyphens: {uni['double_hyphen']}")
    L.append(f"- Quotes: straight double {uni['straight_double']}, curly double {uni['curly_double']}"
             + (" **(mixed)**" if mixed_dq else "") + f"; straight single {uni['straight_single']}, curly single {uni['curly_single']}"
             + (" **(mixed)**" if mixed_sq else ""))
    L.append(f"- Non-breaking spaces: {uni['nbsp']}, zero-width chars: {uni['zero_width']}, double spaces: {uni['double_space']}, emoji: {uni['emoji']}, '...' {uni['ellipsis_dots']}")
    L.append("")

    L.append("## Flags by section\n")
    any_flag = False
    totals = Counter()
    for s in sections:
        f = lint_section(s)
        if not f:
            continue
        any_flag = True
        L.append(f"### {s['title']}")
        for k, items in f.items():
            totals[k] += len(items)
            L.append(f"- **{k}** ({len(items)})")
            for it in items[:4]:
                L.append(f"  - {it}")
            if len(items) > 4:
                L.append(f"  - ...and {len(items) - 4} more")
        L.append("")
    if not any_flag:
        L.append("No pattern flags. Still do the human read; patterns miss voice problems.\n")
    else:
        L.insert(L.index("## Flags by section\n") + 1, "Totals: " + ", ".join(f"{k} {v}" for k, v in totals.most_common()) + "\n")

    if comments:
        L.append(f"## Reviewer comments ({len(comments)}) - full text in comments.md\n")
        for c in comments[:10]:
            L.append(f"- [{c['id']}] {c['author']}: {c['text'][:120]}  (on: \"{c['anchor'][:60]}\")")
        L.append("")

    L.append("## Next\n")
    L.append("1. Confirm this is the canonical file (Stage 0).\n2. Run the Stage 2 checks (thesis integrity, opening, voice, foreword, audience) and present a short diagnosis before any fix.\n3. Work flags wave by wave (Stage 3), one problem type at a time.\n4. Verify every row in citations.csv before print (Stage 4).")
    (out / "map.md").write_text("\n".join(L), encoding="utf-8")

    with open(out / "citations.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["#", "speaker", "quote_as_in_manuscript", "section", "position", "status",
                    "verified_wording", "source_title", "date", "location_or_page", "url", "decision"])
        for i, v in enumerate(voices, 1):
            w.writerow([i, v["speaker"], v["quote"], v["section"], v["position"], "unverified", "", "", "", "", "", ""])

    if comments:
        C = [f"# Reviewer comments: {src.name}\n", "| # | Author | Anchored on | Comment | Proposed fix | Status |", "|---|---|---|---|---|---|"]
        for c in comments:
            C.append(f"| {c['id']} | {c['author']} | {c['anchor'][:80].replace('|', '/')} | {c['text'].replace(chr(10), ' ').replace('|', '/')} |  | open |")
        (out / "comments.md").write_text("\n".join(C), encoding="utf-8")

    print(f"map: {out / 'map.md'}")
    print(f"words {total_words:,} | sections {len(sections)} | voices {len(by_speaker)} | quotes {len(voices)} | comments {len(comments)}")


if __name__ == "__main__":
    main()
