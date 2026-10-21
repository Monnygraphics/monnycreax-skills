---
name: book-production
description: "Take a nonfiction manuscript (draft, Word file, or talk/sermon transcript) to print-ready files: editing, front/back matter, a typeset A5 or KDP print PDF, Word and EPUB, spine size and print checks. Use for formatting, typesetting, KDP/IngramSpark or print-shop prep of a book."
---

# Book Production: Manuscript to Print-Ready Book

This skill captures the production process built while taking *UNBRAND-END: Authenticity Beyond Performance* from a 27,000-word draft to a 99-page print-ready manuscript, plus a tested local toolchain that turns one manuscript into every file a printer or store asks for. Use it for Monny's own books and for client books (founders, coaches, thought leaders, speakers) where MonnyCreaX supports the book as part of a personal brand build.

The process has eight stages. Not every session runs all eight. Start every session by locating where the book currently sits (Stage 0), then pick up from there.

| Stage | What happens | Tool in this skill |
|---|---|---|
| 0 Locate | find the canonical file | Drive search, `manuscript_map.py` header |
| 1 Map | one deep read, one map | `scripts/manuscript_map.py` |
| 2 Align | developmental diagnosis | `references/editorial-playbook.md` |
| 3 Edit | waves, one problem type at a time | map flags + playbook |
| 4 Verify | every quote and fact | `citations.csv` from the map |
| 5 Matter | front and back matter | `references/book-anatomy.md` |
| 6 Format | Word, print PDF, EPUB | `scripts/make_book.py`, `scripts/structure_plan.py`, `scripts/import_docx.py`, `scripts/build_book.py` |
| 7 Toolchain | docx surgery, rendering | `references/docx-surgery.md`, `references/build-pipeline.md` |
| 8 Audit | print-readiness and handoff | `scripts/check_print.py`, `scripts/cover_calc.py`, `references/handoff-assets.md` |

## Quick path: any manuscript in, print-ready book out

This replaces the formatter / typesetter / book designer. Whatever the client has (a clean Word file, an A4 draft with messy formatting, a PDF exported from Word/Canva/another layout (`import_pdf.py` rebuilds headings, labels, subtitles, quotes, lists and extracts cover art; scanned PDFs need OCR first), a .txt, an unfinished draft, or a transcript of talks), the end state is the same: a typeset, structured book and a print-shop pack. The page size of the input does not matter; the output is set to the chosen trim.

**Ask only what is missing:** title, author name as printed, trim (default **A5**, the Kenyan print-shop size), and subtitle / year / ISBN / publisher if they have them. No ISBN is fine: the line is left off (see "ISBN" below).

**1. Look at the material** (30 seconds): `python $BP/structure_plan.py dump SOURCE -o WORK` prints stats: words, heading-like lines, fillers, whether it reads like a transcript, and the suggested design.

**2a. It already has chapters** (headings, "Chapter 1" lines, bold or ALL-CAPS titles):
```bash
python $BP/make_book.py "MANUSCRIPT.docx" --trim a5 --title "..." --author "..."
```
Then read `import-log.md` and the proof PNGs. If a split is wrong, fix the Markdown in the project and rerun `make_book.py PROJECT_DIR`.

**2b. It has no usable structure** (a transcript, notes, one long draft; `make_book.py` warns "No chapter structure found"):
1. Read `WORK/paragraphs.md` fully (in parts if long). Plan the book: chapter breaks by topic, chapter titles in the author's own phrases, subheads, what to drop (sign-offs, "can you hear me", repeats), which paragraphs need light cleanup (false starts, fillers; meaning unchanged, author's vocabulary kept).
2. If the book has no introduction, or a section the structure needs, draft it from the author's own material and mark it `"drafted": true`. Never invent biography, stories or quotes.
3. Show the author the outline (section titles + what each covers) before building. Then fill `WORK/plan.json` and run:
```bash
python $BP/structure_plan.py build WORK/plan.json "%LOCALAPPDATA%/claude-work/book-production/<slug>" --trim a5
python $BP/make_book.py "%LOCALAPPDATA%/claude-work/book-production/<slug>" --trim a5 --out "<user's folder>/<Title>"
```
`build` refuses to run if any paragraph would be lost (in no section and not dropped). `PROJECT_DIR/changes.md` lists every drafted section, edited paragraph, dropped paragraph and filler cleanup for the author to approve. A drafted section blocks printing until its file says `approved: true`.

**3. Deliver one file.** The user's folder gets only `<Title>/<Title>.pdf` (next to the manuscript, or `--out`). Word or EPUB only with `--extras word,epub` when asked. Never put the project, builds, proofs, maps, order sheets or cover specs in the user's folders: they live in the hidden work folder `%LOCALAPPDATA%\claude-work\book-production\<slug>\` (`bookcore.work_root`; `make_book.py`, `structure_plan.py`, `manuscript_map.py` and `check_print.py` all default there). Look at the proofs yourself, then tell the user in a few lines: pages, size, spine width, and anything only they can answer. Recommend one proof copy before a full run.

**What the build decides on its own** (all overridable in `book.yml`):
- **Design preset from the content** (`preset: auto`): `classic` (memoir, idea-led: EB Garamond), `devotional` (faith: Cormorant Garamond headings, EB Garamond text), `business` (leadership, money, brand: Inter headings, Source Serif 4 text), `warm` (self-help, family, wellness: Lora), `workbook` (guides, exercises: Inter, block paragraphs). Say which preset was chosen and why; the author can switch with one line. A client brand font always wins (`body_font`, `heading_font`, `label_font`).
- **Book structure:** signing page ("A signed copy": Signed for / By / Date / Note), title page, copyright page, dedication, contents with real page numbers, then front matter, chapters ("Chapter One" labels), back matter. Chapters open on right-hand pages; blank left pages are inserted where needed.
- **Typography and alignment:** justified text with hyphenation, first-line indents, small-caps chapter openings, curly quotes, running heads (author on the left, chapter on the right), page numbers (roman before Chapter One), mirrored margins with a proper gutter, tables and images kept whole.
- **Checks:** fonts embedded, page size, safe margins, image resolution, leftover placeholders, unapproved drafted text.

**ISBN.** Optional for a private print run; needed to sell through bookshops, Amazon or IngramSpark. If they have one, pass `--isbn` (it goes on the copyright page; the cover designer adds the barcode). If not, the book prints fine without it. To get one in Kenya: apply to the ISBN agency at KNLS (Kenya National Library Service) with the title, author, publisher and format; one ISBN per format (paperback, ebook). Check KNLS's current form and requirements before advising on cost or timing. KDP can also assign a free ISBN, valid only on Amazon.

**What still needs a human:** the author approving drafted text and structural edits, a cover design (the numbers are in `cover-spec.md`), and reading one printed proof copy. For deeper editing (argument, voice, quote verification), run Stages 1-4 below.

## Full process

Scripts live in `~/.claude/skills/book-production/scripts/` (call it `$BP`). Run each with `--help`. They need Python with python-docx, PyYAML, lxml, PyMuPDF and fontTools, plus Chrome or Edge for PDFs. All present on Monny's machine.

---

## The Non-Negotiables

These rules were earned the hard way. Read them before touching any manuscript.

1. **Find the true source file before anything else.** Books accumulate versions. UNBRAND-END had at least two Drive files and several delivered .docx copies, and one session was lost because the "original" Drive file turned out to be the pre-edit version. Confirm with the author which file is canonical before reading or editing.
2. **Never compound on modified output files.** Return to the canonical spine and apply surgical changes. Each regenerated file drifts further from the author's voice. (In the build pipeline the canonical spine is the book project's Markdown; outputs are always regenerated from it, never edited.)
3. **Concept first, then execute.** The author directs, Claude proposes with reasoning, the author approves, Claude executes. Switch to autonomous execution only when the author explicitly grants it in that session.
4. **Work section by section, chapter by chapter.** No repeated full-document passes. Build one complete map at the start of the session, hold it, then work issue by issue without re-reading the whole book between edits.
5. **Offer clean text blocks when the author prefers to paste.** Some authors want to place edits themselves. Ask once per session.
6. **Do not add structure the author did not ask for.** Reflection boxes, "How to Read This Book" sections, closing "The Work Continues" pages, ornamental dividers and chapter teasers were all added to UNBRAND-END and all rejected. Structure that instructs the reader can betray the book's own argument. Propose it; never insert it unasked. This includes callouts and pull-quotes in a designed interior. House defaults Monny asked for are the exception: the signing page and the contents page (switch the signing page off with `autograph_page: false`). New prose, such as a missing introduction, is only ever a `drafted: true` proposal until the author approves it.
7. **Every attributed quote must be verified verbatim before print.** No exceptions (see Stage 4).
8. **The book's thesis governs the edit.** If the structure of the manuscript contradicts what the book argues, that is the most important edit in the book.
9. **No em dashes in any new text Claude writes.** Use commas, colons, or separate sentences. Flag em dashes in the author's existing text and let the author decide.
10. **Automatic fixes are logged and tested both ways.** Any scripted change (fused words, numbering, merged sections) goes in a change log the author can see, and a fix function is tried on already-correct text before it is trusted on a whole book. Fixes that look right on paper have corrupted clean text before (Scribe's known bug #14).
11. **Never say "print-ready" until `check_print.py` passes and the proof pages have been looked at.** Every rendering bug in the tools this skill learned from was silent.

---

## Stage 0: Locate and Confirm

**Goal:** know exactly which file is the book, and what state it is in.

- Search the author's Drive with a partial title (`title contains 'unbrand'`) rather than the full title. Partial matches catch every variant.
- If the author shares a Google Docs link, the file ID is the string between `/d/` and `/edit`. Download it as .docx to work locally.
- List every candidate with modified date. Ask the author to confirm the canonical file if more than one exists.
- Search past conversations with targeted, split queries ("back cover copy [title]", "editor feedback [title]") rather than one broad query. Reconcile what was done against what is actually in the file. If transcripts and file disagree, the file wins.
- If no file is loaded in the session, do not perform edits from memory or transcripts. Ask for the upload or the Drive link.
- If a book project folder already exists (`book.yml` + `manuscript/`), that folder is the canonical spine; check `build/build-report.json` for the last build.

**Output:** one line naming the canonical file and its current state (word count, page estimate, last stage completed).

---

## Stage 1: The Deep Read and the Map

**Goal:** one full read that produces a map you can work from for the rest of the session.

Run the map first, then read the book with the map beside you:

```bash
python $BP/manuscript_map.py "BOOK.docx" -o "BOOK-map" --cap 3 --trim 6x9
```

It writes `map.md` (counts, page estimates per trim, chapter table with opening and closing lines, front/back matter checklist, outside voices against the cap, typography counts, flags per section), `citations.csv` (every attributed quote, status unverified) and `comments.md` (reviewer comments with the text they are anchored on). It reads .docx (tracked changes and line breaks handled), .md, or a book project folder. It never edits.

The map must record, and the script covers most of it:

- Word count and estimated page count at the target trim size
- Every chapter: title, subtitle, opening move, closing move, word count
- Front matter present and missing
- Back matter present and missing
- Every external voice: who, where, how often, and whether a quote opens or closes a section
- Recurring stylistic patterns (rhetorical tics, repeated constructions)
- Places where a claim stands without a concrete scene or example (human read only)
- Any author notes, reviewer remarks or placeholders left in the text ("NEW SECTION", pasted comments)

Pattern flags are leads, not verdicts. The human read still decides; patterns miss voice problems and paraphrased borrowing.

**Length targets:** a typical nonfiction trade book runs 100 pages or more. If the book is short, grow it genuinely: personal anchor stories, grounded examples, answers to real reader questions. Never pad. UNBRAND-END grew from 72 to 99 pages through grounding scenes and reader-question sections, not filler.

---

## Stage 2: Developmental Alignment

**Goal:** make sure the manuscript does what the book claims to do. Run these checks and present findings as a short diagnosis before proposing any fixes. Detail and diagnosis format: `references/editorial-playbook.md`.

- **Thesis Integrity Check:** does the structure obey its own argument? UNBRAND-END argued against borrowed authority while leaning on Chris Do 20 times and Steven Bartlett 11 times. That irony was the single most important edit in the book. The map's outside-voices table is the starting evidence.
- **Opening Check:** does Chapter One pull the reader in, or warm up? UNBRAND-END cut its Introduction and opened straight into the mango stand story. A strong scene beats a framing essay.
- **Voice Check:** manifesto or memoir? The concept leads, the personal story serves the concept, the reader is always in the room.
- **Foreword Check:** a foreword is written by someone else. If the author wrote it, it becomes a Preface in the author's voice.
- **Audience Check:** for senior readers, make sure examples address them. Local texture (Kenyan place names) stays, with a light gloss for international readers.

---

## Stage 3: Editorial Waves

**Goal:** fix line-level and structural problems in focused waves, one problem type at a time. Run each wave across all chapters, surfacing one item at a time for approval unless the author has granted autonomy.

| Problem | Map flag | Fix |
|---|---|---|
| Landing quotes | "section ends on a quote", "opens on a quote" | Move the quote inside the section where it earns its place. End on the author's reasoning. Open chapters in the author's voice. |
| Borrowed authority overload | voices "over cap" | Agree a cap (UNBRAND-END: 3 per voice). Replace excess with the author's amplified reasoning. |
| Deny-deny-land clusters | "deny-deny-land" | Vary: a question, a scene, or a plain statement. Spread the rest thinly. |
| Ungrounded abstraction | (human read) | Add a scene or anchor story from the author's real life. Never invent biography. |
| Fragment and AI-prose texture | "fragment stack" | Thin fragments, restore full sentences, cut lines that sound produced. |
| Parallel structure breaks | (human read) | Match italics, subheading and spacing to the pattern. |
| Inconsistent naming | (human read) | Standardise once the author picks the version. |
| Fused words | "fused words" | A lost line break; fix only after looking. The guard list in `bookcore.py` protects names like McDonald, iPhone, LinkedIn. |
| Promises the book does not keep | "promise to verify" | Either deliver it or cut the promise. |

Reviewer feedback: read full comments from `comments.md` (Google Docs emails truncate). Log each as a numbered item: location, the reviewer's point, proposed fix, status. Remove all comment markers and pasted remarks before print. A developmental question from a reviewer can become a new section where it naturally belongs; propose placement before drafting.

Voice standard for new text: direct, concept-first, grounded, no hedging, matched to the author's rhythm. For faith-informed authors, spiritual grounding stays present but not preachy. Run new passages through the `humanizer` skill before showing them.

---

## Stage 4: Attribution and Fact Verification

**Goal:** nothing in the book that could damage the author's credibility. Work through `citations.csv` row by row.

- **Verbatim standard.** Check every quote against a primary source (book text, official transcript, recorded talk). UNBRAND-END's Femi Lazarus passage was an elaborated paraphrase; the verified shorter quote replaced it.
- **Citation record.** Fill the csv columns: verified wording, source title, date, location or page, URL, decision.
- **Three options when a quote fails:** use the real quote, paraphrase with clear attribution, or drop the name and let the idea stand in the author's voice.
- **Titles and honorifics.** Verify "Dr", "Apostle", "Prof" before printing; then confirm the author's preference.
- **Case studies.** Verify dates, figures and quotes against reputable sources (Isaacson for Jobs, Schultz's 2008 Starbucks return).
- **Scripture.** Match the reference to the exact verse in the author's chosen translation; flag rather than guess.
- **Diversity of voices.** If outside voices skew toward one demographic, flag it and offer verified alternatives.

---

## Stage 5: Front and Back Matter

**Goal:** a complete book, in the right order. Full anatomy, page-side rules and copyright-page template: `references/book-anatomy.md`.

Front: title page, copyright page (verso), dedication, contents, preface (author) or foreword (someone else). Body: chapters (parts optional). Back: closing section, appendix, acknowledgements (a deliberate choice either way), about the author.

- Contents: chapter titles, optional quiet one-line descriptions, no dividers. Built from body titles, never copied from the source's own contents list. Page numbers come from the final pagination (the build does this) or stay off.
- Copyright page: for senior positioning, recommend a domain email over Gmail. The author decides. ISBN for Kenya from KNLS (Kenya National Library Service) or a platform ISBN.
- About the Author: review after all edits so it matches the book's scope.
- Dedication: the author's own words. Draft only if asked, and keep it brief.

---

## Stage 6: Formatting and Typesetting

**Goal:** the files the author actually needs. Ask which route before building; it decides the toolchain.

| Route | When | How |
|---|---|---|
| **A. Word manuscript** (default) | the author or a publisher will keep editing; a publisher does its own layout | surgical edits to the canonical .docx (Stage 7), or `build_book.py --formats docx` from a project |
| **B. Typeset book** | self-publishing on KDP / IngramSpark, or a print shop wants a PDF | `import_docx.py` once, then `build_book.py --formats pdf,epub,docx` |
| **C. Designed interior** | guides, workbooks, playbooks where tables and callouts help; only when asked | route B plus `references/designed-interiors.md` |

**Route A default spec (UNBRAND-END):** Garamond 12pt, justified, 1.5 spacing; headings in Garamond or Lufga with a clear hierarchy; page break before every chapter and every front or back matter section; pull quotes indented and italic, sparingly; a light accent colour only (about 30% maximum), no heavy themed backgrounds. Confirm trim size first: 6 x 9 in is standard trade nonfiction; UNBRAND-END was built on 8.5 x 11 in with 1.25 in side margins and 1 in top and bottom. If the manuscript is already hand-styled well, preserve it and make surgical changes; do not rebuild it from scratch.

**Route B, the typeset book:**

```bash
python $BP/import_docx.py "BOOK.docx" "D:/Books/my-book"      # once; read import-log.md
# edit book.yml (meta, layout) and the Markdown in manuscript/ from here on
python $BP/build_book.py "D:/Books/my-book" --formats pdf,epub,docx,html
python $BP/check_print.py "D:/Books/my-book/build/<title>-interior-6x9.pdf" --trim 6x9
```

The PDF build gives real book typography: EB Garamond (bundled, static cuts so no Type 3 fonts), chapters opening on recto with blank versos inserted, no running heads on openers or blanks, author on verso heads and chapter title on recto heads, roman folios in front matter and arabic from Chapter One or the Introduction, mirrored margins with the KDP gutter for the final page count, contents page numbers from the real pagination, curly quotes, hyphenation, PDF bookmarks. Layout options, the Markdown dialect and how pagination works: `references/build-pipeline.md`.

Page numbers in Word: footers use a `PAGE` field (written to every footer). Some authors prefer to add page numbers themselves after the final read. Ask.

---

## Stage 7: Technical Toolchain

**Editing an existing .docx in place (route A):** unpack, edit `word/document.xml` with Python string replacement, validate with lxml after every batch, pack with the original's relationships. Anchors, entity encoding, orphaned paragraph tags, TOC versus real headings, and the Scribe bug catalog are in `references/docx-surgery.md`. Read the `anthropic-skills:docx` skill before the first edit in a session.

**Reading any .docx:** never join runs naively. `bookcore.read_docx()` keeps `<w:br/>` breaks (the root cause of fused words), keeps tracked insertions and drops deletions (accept-all, reported), and returns comments with their anchor text.

**Rendering:** `build_book.py` drives Chrome/Edge headless and post-processes with PyMuPDF. On claude.ai or a cloud box without Chrome, build `--formats epub,docx`, and render the PDF on Monny's machine. LibreOffice (`soffice --headless --convert-to pdf`) is the fallback to preview a .docx as PDF; it is not installed locally.

**Render and look:** after any build, open the proof PNGs `check_print.py` writes (title, contents, first opener, a mid-book spread, last page). Measurements do not catch a bad-looking page.

**Delivery:** a clear versioned name, for example `TITLE Final Manuscript 2026 (Clean).docx` or `title-interior-6x9.pdf`. Leave the canonical Drive original untouched unless the author asks.

---

## Stage 8: Print-Readiness Audit and Handoff

**Goal:** a clear, honest list of what stands between the file and the printer.

```bash
python $BP/check_print.py interior.pdf --trim 6x9           # or a .docx
python $BP/cover_calc.py --pdf interior.pdf --trim 6x9 --paper cream --platform kdp
```

**Must fix (cannot print without)**
- ISBN on the copyright page (KNLS in Kenya, or a platform ISBN for self-publishing)
- Any unverified quote (open rows in citations.csv)
- Any promise the book does not keep
- Reviewer comment markers, tracked changes or placeholders still in the body
- `check_print.py` must-fix items: wrong page size, fonts not embedded, text outside the safe area, under 24 pages

**Should fix (strongly recommended)**
- Contents page numbers set after final pagination, or removed
- About the Author reviewed against the finished book
- Back cover copy written
- One clean top-to-bottom proofread after all surgical edits. Multiple rounds of surgery always leave seams.
- Images under 300 ppi, chapter openers on a verso

**Flagged but acceptable (author's call)**
- No acknowledgements page
- Personal email on the copyright page
- Em dashes in the author's own text

Handoff assets (templates in `references/handoff-assets.md`): back cover copy (200 to 250 words from the book's own language, its own .docx), cover designer brief (with `cover_calc.py` numbers), spine and cover files (designer's job, on the checklist), publisher concept note if pitching, and the KDP / IngramSpark upload checklist.

**End every production session with:**
1. What was completed this session
2. What remains, in the three tiers above
3. The single next action

---

## Anti-Patterns to Avoid

- Editing from transcripts or memory when the file is not loaded
- Regenerating the whole book instead of making surgical edits
- Adding reflection apparatus, reading guides, dividers, callouts or pull-quotes without approval
- Letting outside voices close sections or open chapters
- Padding to hit a page count
- Trusting a quote because it "sounds like" the speaker
- Re-reading the whole manuscript between every small edit
- Declaring the book print-ready before the clean proofread pass and a passing `check_print.py`
- Editing a built PDF, EPUB or generated .docx instead of the project source
- Using variable fonts in a print PDF (Type 3 fonts; IngramSpark rejects them)

---

## Reference Case: UNBRAND-END

- **Author:** Bethwel Monny, MonnyCreaX
- **Structure:** seven chapters with portmanteau titles (EDEN-TITY, CRY-TIVITY, EX-PRESS-SURE, AUTHEN-TICK, UNBRAND-END, B-LANDS VS BRANDS, AUTHENTIC)
- **Journey:** 72 pages and 27,000 words, grown to 99 pages through grounding stories and reader-question sections
- **Feedback rounds:** two beta readers (16 comments plus 7 developmental questions), then an editor's five-problem review
- **Defining edit:** resolving the irony of a book against borrowed authority leaning on borrowed voices; capped at 3 appearances per outside voice
- **Rejected additions:** reflection boxes, "How to Read This Book", "The Work Continues", ornamental dividers
- **Remaining at handoff:** ISBN, cover, final proofread

Sources this skill learned from (all MIT; EB Garamond under OFL): `references/sources.md`.
