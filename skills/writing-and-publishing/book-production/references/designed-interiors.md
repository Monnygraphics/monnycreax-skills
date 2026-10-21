# Designed Interiors (route C)

For guides, workbooks, playbooks and how-to books where a table, a process diagram or a callout genuinely helps the reader. Learned from the Booksmith skill. Not for memoir, manifesto or argument-led books like UNBRAND-END.

**Non-negotiable #6 still rules:** every callout, pull-quote, table or chart is a proposal. List them with reasons, get approval, then build. Default is plain prose.

## Classification: one decision per block, stop at the first match

1. A single sentence or statistic worth pausing on, which the author agrees to echo -> **pull-quote** (`::: pullquote`). The sentence also stays in the text.
2. A tip, warning or aside the reader can skip without losing the thread -> **callout** (`::: callout Tip`).
3. Several items with the same attributes (tools x cost/features/best for) -> **table** (raw HTML `<table>` block).
4. Numbers: shares, rankings, trends -> **chart** image (matplotlib, 300 dpi, PNG in `assets/`), via `![...](assets/chart.png){Caption}`.
5. A process, timeline, hierarchy or decision path -> **diagram** (the `archify` or `diagram-design` skill, exported as an image).
6. Everything else -> **plain paragraph**.

Chart choice: parts of a whole with up to 6 slices -> donut; a few categories -> horizontal bar; change over 3+ points -> line; "4 out of 5" -> pictogram. Fewer than 3 data points -> a sentence, not a chart.

Density: no more than one or two converted blocks per three or four pages; never the same treatment twice in a row; after classifying, count conversions against total sections and cut back if it reads like a brochure.

## Typography by genre

| Genre | Headings | Body | Why |
|---|---|---|---|
| Business, strategy, self-help guide | Lufga, Space Grotesk or Poppins | Inter or Source Serif 4 | current, credible, not decorative |
| Tech / tool step-by-step | Space Grotesk or IBM Plex Sans | Inter + IBM Plex Mono for exact commands | mono signals "type exactly this" |
| Devotional, faith, companion | Cormorant Garamond or Playfair Display | EB Garamond, Lora or Source Serif 4 | warmth and permanence |
| Cookbook | Fraunces or Lora bold | Karla or Nunito Sans | approachable |
| Workbook, journal | Poppins or Quicksand | Open Sans or Nunito Sans | legible, does not compete with handwriting |

A font the author or client brand names always wins. For MonnyCreaX's own books, the brand is EB Garamond with Lufga labels (`label_font: Lufga`). Any font used in a print PDF must be a static (non-variable) file to avoid Type 3 fonts; check with `check_print.py`.

## Building it

Use the normal pipeline with these layout settings, then add blocks with the Markdown dialect (`references/build-pipeline.md`):

```yaml
layout:
  trim: 7x10                # or 8.5x11 for workbooks; 6x9 / a5 for text-led guides
  label_font: Lufga
  accent: "#8a6d1f"         # one accent, used sparingly
  first_line_indent: false  # block paragraphs read better around boxes
```

Callout and pull-quote styles live in `build_book.py` (`.callout`, `.pull-quote`); adjust there for a client's look. Tables: keep them under a page (`break-inside: avoid` is applied to figures; long tables need splitting by hand).

## Rendering notes that differ from Booksmith

Booksmith rendered with wkhtmltopdf and had to avoid CSS variables, flexbox and @page margin boxes. This skill renders with current Chrome, where those work; the rules that still apply: self-host fonts beside the HTML (the build copies them), never clip body text with a fixed height plus `overflow: hidden` (content silently disappears), and always look at a rendered page of every block type before delivering.

## Handing over editable source

Build with `--formats html` to deliver the print HTML and its `fonts/` folder. Instructions for the author: open `book.html` in Chrome, Ctrl+P, destination "Save as PDF", paper size already set, margins "Default", headers and footers off, background graphics on. Note: the running heads and contents page numbers are added by the build, not by the browser, so a browser re-export will not have them. For anything beyond small text fixes, edit the project and rebuild.
