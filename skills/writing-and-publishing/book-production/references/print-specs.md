# Print Specs: KDP, IngramSpark, local print shops, ebooks

Cross-check against the platform's own help pages before a real upload if this file is more than a year old.

## Trim sizes the build knows (`layout.trim`)

| key | inches | mm | Typical use |
|---|---|---|---|
| `a5` | 5.83 x 8.27 | 148 x 210 | Kenyan / UK / EU print shops, the local default |
| `5x8` | 5 x 8 | 127 x 203 | compact nonfiction, poetry |
| `5.25x8` | 5.25 x 8 | 133 x 203 | compact nonfiction |
| `5.5x8.5` | 5.5 x 8.5 | 140 x 216 | trade paperback, devotionals |
| `6x9` | 6 x 9 | 152 x 229 | US trade nonfiction standard (KDP default) |
| `6.14x9.21` | 6.14 x 9.21 | 156 x 234 | slightly larger trade |
| `7x10`, `7.5x9.25`, `8x10` | | | illustrated guides |
| `8.5x11` | 8.5 x 11 | 216 x 279 | workbooks, journals (UNBRAND-END draft size) |
| `8.25x8.25`, `8.5x8.5` | | | square |

KDP "large trim" (wider than 6.12 in or taller than 9 in) costs more per page.

## Interior margins

KDP minimum inside margin (gutter) by page count:

| Pages | Inside | Outside, top, bottom (no bleed) |
|---|---|---|
| 24-150 | 0.375 in | 0.25 in |
| 151-300 | 0.5 in | 0.25 in |
| 301-500 | 0.625 in | 0.25 in |
| 501-700 | 0.75 in | 0.25 in |
| 701-828 | 0.875 in | 0.25 in |

The build's `margins: auto` uses the KDP gutter for the final page count plus 0.3 in for comfort, and generous outside/top/bottom margins (about 0.55-0.8 in). These suit a print shop too; perfect-bound books need the gutter because the spine glue eats paper.

## Bleed

Only needed when an image or colour touches the page edge. Text-only interiors: no bleed. If any page bleeds, the whole file must: KDP adds 0.125 in to top, bottom and outside (page = trim + 0.125 wide, + 0.25 tall); print shops usually ask for 3 mm on all sides. Covers always have bleed.

## Page counts

- KDP paperback: 24 to 828 pages (black ink, white or cream). Spine text from 80 pages.
- IngramSpark: 18+ pages for paperback; spine text from 48 pages; even page count required.
- Print shops: perfect binding (glued spine) usually from about 40-48 pages. Saddle stitch (stapled) works up to about 48-64 pages and needs a page count divisible by 4. Ask.

The build pads to an even page count by default.

## The PDF itself

- All fonts embedded, no Type 3 fonts (variable fonts in Chrome cause these; the bundled EB Garamond is static for this reason). `check_print.py` checks.
- Images 300 ppi at printed size; greyscale for black-and-white interiors.
- One PDF, single pages in reading order (not spreads), page 1 = a right-hand page. The print shop does imposition (arranging pages on big sheets) unless they ask otherwise.
- IngramSpark prefers PDF/X-1a or PDF/X-4. A Chrome PDF is standard PDF; it usually passes Ingram's checks when fonts are embedded and there is no transparency. If Ingram rejects it, run it through Acrobat Preflight "Convert to PDF/X-4".
- Local print shops take a normal PDF. Tell them: trim size, page count, paper (70/80 gsm bond, or cream book wove), binding, cover paper (250-300 gsm art card), lamination (matte or gloss), quantity.

## Spine width (`cover_calc.py`)

- KDP per-page thickness: white 0.002252 in, cream 0.0025 in, colour 0.002252 in, premium colour 0.002347 in.
- IngramSpark: depends on stock; always use their cover template generator for the final file.
- Print shops: depends on the paper they stock. Rough: 70 gsm about 0.045 mm per page, 80 gsm about 0.05 mm, 90 gsm about 0.055 mm. Ask the shop to confirm the spine before the cover is designed. `cover_calc.py --platform printshop --paper 80gsm` uses these.

## Ebooks

- KDP takes EPUB (MOBI is retired). Cover 2560 x 1600 px (1.6:1), JPG, RGB.
- Validate before upload: KDP's online previewer, or EPUBCheck (the W3C tool, Java) if installed. The build checks XML well-formedness only.
- Ebooks carry their own ISBN (or none on KDP).
