# Editorial Playbook (Stages 2 and 3)

How to turn the map into a diagnosis, then into edits the author approves.

## 1. The diagnosis (present before any fix)

Keep it to one screen. Format:

```
DIAGNOSIS: <title>, <words> words, ~<pages> pages at <trim>

The one thing: <the thesis-integrity problem, or "none found">
Opening: <does Chapter One start with a scene or a warm-up?>
Voice: <manifesto / memoir / mixed; where biography stops serving the idea>
Matter: <foreword vs preface; missing front/back matter>
Audience: <who the examples serve; who they leave out>

Waves I propose, in order:
1. <highest-impact problem type> (<n> instances)
2. ...
Your call: <the one decision the author must make first, e.g. the voice cap>
```

Rank waves by damage to the book's argument, not by count. A book against borrowed authority with 20 Chris Do quotes fixes that first even if it has 80 fragment stacks.

## 2. The five checks, with questions to ask

**Thesis integrity.** State the thesis in one sentence from the book's own words. Then ask: does the structure obey it? Look at what the map shows: who speaks most, where outside voices sit (opening or closing sections), what the chapter order implies. Typical contradictions: a book on authenticity built from borrowed frameworks; a book on rest written as a productivity checklist; a book on listening that never lets another voice speak.

**Opening.** Read the first 500 words of Chapter One. If the first concrete person, place or moment appears after word 300, the chapter is warming up. Options: cut the Introduction and open on the strongest scene; move framing material to a short Preface.

**Voice.** Mark each personal story: does it serve the concept on that page? Stories that only say "this happened to me" get cut or reframed so the idea leads.

**Foreword.** Who wrote it? The author's own words are a Preface. A real foreword names its writer under the title.

**Audience.** Count examples by who they are about (students, employees, founders, CEOs). If the stated reader is senior and the examples are all early-career, add universal turns that address them.

## 3. Running a wave

1. Pick one problem type. Take the instances from the map, plus any found while reading.
2. For each instance, show: location (chapter, the paragraph's first words), the current text, the proposed text, and one line of reasoning.
3. Wait for approval (or batch approval if the author granted autonomy this session).
4. Apply the edit to the canonical source only: the .docx by surgery, or the project Markdown.
5. Log it: `| # | chapter | type | before | after | approved |` in a session log file beside the manuscript.
6. Next instance. Do not re-read the whole book between edits.

When the author prefers to paste: give the replacement as a clean block, with the exact sentence it replaces quoted above it.

## 4. Problem types in depth

**Landing quotes.** An outside quote closes a section or chapter, so someone else gets the last word. Fix: move the quote earlier, where it supports a step in the argument, and end on the author's own conclusion. A chapter never opens on an outside quote either; an epigraph is a deliberate exception the author must choose.

**Borrowed authority overload.** Agree the cap first (UNBRAND-END: 3 per voice across the book). Keep the three strongest, verified uses. Replace the rest by asking: what did the author learn that this quote was standing in for? Write that, in their voice.

**Deny-deny-land.** "It is not X. It is not Y. It is Z." Once per chapter can be a deliberate move. Clustered, it reads as AI cadence. Rewrite as a question ("So what is it?"), a scene that shows Z, or a plain statement of Z.

**Ungrounded abstraction.** A claim with no person, place or moment within a page. Ask the author for the real story behind it. Never invent biography, dialogue or numbers.

**Fragment stacks.** Three or more one-line paragraphs in a row. Merge into full sentences; keep at most one fragment for emphasis.

**AI-prose texture.** Rhythmic triads, "Here's the thing", "Let that sink in", stacked rhetorical questions, inflated verbs. Run the `humanizer` skill over any passage Claude writes, and flag (not rewrite) these patterns in the author's text.

**Parallel structure breaks.** A scripture block, case study or sidebar formatted differently from its siblings. Match the established pattern.

**Inconsistent naming.** Same person or term written several ways (Femi / Pastor Femi / Lazarus). The author picks; apply everywhere in one pass.

**Promises not kept.** "At the end of each chapter you will find..." with nothing there. Deliver or cut.

## 5. Reviewer comments

1. Extract with `manuscript_map.py` (writes `comments.md` with anchor text).
2. Number them. Columns: #, reviewer, anchored on, their point, proposed fix, status (open / proposed / approved / done / declined with reason).
3. Developmental questions ("any advice for people rebuilding a failed brand?") may become a new section. Propose where it belongs and roughly how long, then draft only on approval.
4. Before print: no comment markers, no pasted reviewer remarks in the body (`check_print.py` on the .docx confirms).

## 6. Automatic fixes and the change log (from Scribe)

Some problems are mechanical: fused words from lost line breaks, duplicate or missing chapter numbers, emoji in headings, stray non-breaking spaces. Rules:

- Every automatic change goes in a change log (before / after / where).
- Ask the author once: review the log before the file is finalised, or receive it with the file. Default for a new book: before.
- Test any fix function on already-correct text before running it on the whole book. It must leave clean text unchanged.
- Numbering: one duplicate plus one matching gap can be renumbered automatically (first occurrence fills the gap). Anything more complex goes to the author.
- Quote style (straight vs curly) is a choice. The typeset build converts to curly; in a Word manuscript, flag mixed styles and let the author choose.
