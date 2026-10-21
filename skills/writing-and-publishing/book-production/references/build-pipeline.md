# Build Pipeline Reference (routes B and C)

One source, every format: the bookpub idea, rebuilt on what is installed here (Python + Chrome).

## The fast path: manuscript to print-shop pack

```bash
python $BP/make_book.py "MANUSCRIPT.docx" --trim a5 --title "Title" --author "Name" [--subtitle ..] [--year 2026] [--isbn ..] [--publisher ..]
```

Accepts .docx (styled or plain), .txt or .md. Creates `<title>-book/` beside the manuscript, builds, checks, and writes `build/print-shop/`:

| File | What it is |
|---|---|
| `<title>-interior-a5.pdf` | the file the printer prints |
| `PRINT-SHOP-ORDER.md` | the spec sheet to hand over (size, pages, paper, binding, cover, spine) |
| `cover-spec.md` | spine width and full wrap size for the cover designer |
| `print-check.md` | the automatic checks |
| `proofs/*.png` | title, contents, first chapter opener, a mid-book spread, last page |

Run it again after any change: it rebuilds from the project and keeps edits made there. `--force` re-imports from the manuscript (the old `manuscript/` folder is moved to a backup, never deleted). It formats only; it never rewrites the author's words.

What a plain manuscript needs to import well: chapter titles on their own lines, either as "Chapter 1 ..." / "CHAPTER ONE", or as short bold or ALL-CAPS lines. Named sections (Dedication, Preface, Introduction, Acknowledgements, About the Author) are recognised by name. Always read `import-log.md` and the proof pages; if a chapter split looks wrong, fix the Markdown files and `contents:` in book.yml, then rebuild.

## Presets (layout.preset)

| preset | body / headings | size (6x9; a5 is 0.5pt smaller) | for |
|---|---|---|---|
| classic | EB Garamond / EB Garamond | 11.5 | memoir, manifesto, idea-led nonfiction |
| devotional | EB Garamond / Cormorant Garamond | 11.5 | faith, sermons, devotionals |
| business | Source Serif 4 / Inter | 10.5 | business, leadership, money, branding |
| warm | Lora / Lora | 10.5 | self-help, family, relationships, wellness |
| workbook | Inter / Inter, block paragraphs | 10 | guides, workbooks, journals |

`auto` scores the text against each preset's vocabulary (per 1,000 words) and falls back to classic on a weak signal. The scores are in `build/build-report.json`; overrule with one line when the content says otherwise.

## Messy input: structure_plan.py

For transcripts, notes and drafts without chapters: `dump` numbers every paragraph (giant transcript paragraphs are split at sentence ends, .srt/.vtt timestamps removed), Claude writes `plan.json` (sections by paragraph range, drafted sections, light edits, drops), `build` assembles the project, refuses to lose paragraphs, and writes `changes.md` for the author's approval. Full format in `structure_plan.py --help`.

## Project layout

```
my-book/
  book.yml                 meta, layout, contents order
  manuscript/
    front/01-dedication.md
    front/02-preface.md
    body/01-chapter-one-the-mango-stand.md
    back/01-about-the-author.md
  assets/                  images (cover.jpg = ebook cover)
  build/                   generated: never edit, always rebuild
  import-log.md
```

## book.yml

```yaml
meta:
  title: "The Honest Brand"
  subtitle: ""
  author: "Bethwel Monny"
  publisher: "MonnyCreaX"
  year: 2026
  edition: "First edition"
  isbn_print: ""          # blank = no ISBN line on the copyright page
  isbn_ebook: ""
  location: "Nairobi, Kenya"
  contact: "hello@example.com"
  language: en
  description: ""         # ebook metadata
  copyright_extra: ""     # disclaimer, scripture permission line, cover credit
layout:
  trim: a5                # a5 5x8 5.25x8 5.5x8.5 6x9 6.14x9.21 7x10 8.5x11 b5 royal ...
  preset: auto            # auto | classic | devotional | business | warm | workbook (sets the keys below)
  autograph_page: true    # signing page first; false removes it
  autograph_lines: [Signed for, By, Date, Note]
  chapter_words: true     # "Chapter 1" in the source prints as "Chapter One"
  heading_weight: 500
  body_font: EB Garamond  # bundled: EB Garamond, Cormorant Garamond, Lora, Source Serif 4, Inter; installed fonts work by name
  heading_font: EB Garamond
  label_font: ""          # e.g. Lufga for chapter labels and running heads (brand look)
  accent: "#1a1a1a"       # chapter labels; keep it quiet
  body_size: 11.5         # pt; 10.5-11 for a5, 11-12 for 6x9
  leading: 1.42
  margins: auto           # or {top: 0.8, bottom: 0.85, inside: 0.85, outside: 0.6} in inches
  chapter_start: right    # right = recto openers with blank versos; any = next page (fewer blanks)
  running_heads: true
  verso_head: author      # author | title
  toc_page_numbers: true
  drop_folio_on_openers: false
  first_line_indent: true # false = block paragraphs with space between
  hyphenate: true
  smart_quotes: true
  even_page_count: true
  number_chapters: true   # adds "Chapter One" labels when titles have none
  docx_font: Garamond
  docx_size: 12
  docx_line_spacing: 1.5
  docx_page_numbers: true
contents:                 # order of the book; auto: entries are generated from meta
  - auto:autograph
  - auto:title
  - auto:copyright
  - front/01-dedication.md
  - auto:toc
  - front/02-preface.md
  - body/01-chapter-one.md
  - back/01-about-the-author.md
```

A contents entry can also be a mapping: `- {file: body/05-part-two.md, type: part}`. Add `auto:halftitle` before `auto:title` for a half-title page.

## Section files

The first `# Heading` is the section title. "Chapter One: The Mango Stand" becomes label "Chapter One" + title "The Mango Stand". Optional front matter overrides detection:

```markdown
---
type: preface        # any type from book-anatomy.md
label: ""            # custom label, e.g. "Law 12"
subtitle: ""
toc: true            # list in contents
recto: true          # open on a right-hand page
---
# Preface
```

## Markdown dialect

| Write | Get |
|---|---|
| `## Heading`, `### Heading` | subheads (`#` is reserved for the section title) |
| `*italic*`, `**bold**` | emphasis |
| `> quote` then `> -- Name` | block quote with right-aligned attribution |
| `- item`, `1. item` | lists |
| `***` or `* * *` or `---` | scene break (spaced asterisks) |
| `\newpage` | forced page break |
| `![alt](assets/fig.jpg){Caption}` | figure, kept on one page |
| `text[^1]` and `[^1]: note` | numbered notes, listed at the end of the chapter |
| `::: callout Label` ... `:::` | callout box (designed interiors only, with approval) |
| `::: pullquote` ... `:::` | pull quote (designed interiors only, with approval) |
| a line starting with `<` | raw HTML passes through |

## How the PDF gets its pagination right

Chrome prints the HTML with mirrored `@page :left/:right` margins and writes PDF bookmarks for every section `<h1>` (title and copyright carry hidden ones). The build then loops, at most six passes:

1. Read where each section starts from the bookmarks.
2. Margins: if the real page count crosses a KDP gutter step, recompute margins and re-render.
3. Recto starts: every section that should open on the right but lands on an even page gets a blank page before it (computed in one go, since each blank shifts the rest). Re-render.
4. Contents: fill real page numbers (roman before Chapter One, arabic after). Re-render and confirm nothing moved.

Then PyMuPDF stamps running heads and folios (Chrome cannot vary them per chapter or suppress them on openers), skips blanks, sets bookmarks and metadata, and pads to an even page count.

Fonts: Chrome writes non-default instances of variable fonts as Type 3 fonts, which IngramSpark rejects and some print RIPs render badly. The bundled EB Garamond is a set of static cuts made with fontTools for that reason. To add another family, see `assets/fonts/README.md`.

## Troubleshooting

| Symptom | Cause, fix |
|---|---|
| "Outline has N entries but the book has M sections" | A raw `<h1>` in Markdown, or a section with no title. Use `##` inside sections. |
| "Browser did not write a PDF" | Chrome/Edge not found or blocked. Set `CHROME_PATH`. |
| font substituted warning | The font name is not installed. Install it, or use EB Garamond. |
| Type 3 fonts in check | A variable font. Use static font files. |
| Too many blank pages | `chapter_start: any`, or merge very short front-matter sections. |
| Chapter split wrong after import | Edit the Markdown files and `contents:`; do not re-import over edits. |
| Wrong quotes in a code sample | `smart_quotes: false`, or wrap it in backticks. |
