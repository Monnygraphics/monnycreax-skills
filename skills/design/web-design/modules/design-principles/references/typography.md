# Typography

## Anatomy, briefly

Only enough to make the pairing rules below make sense:

- **x-height** — height of lowercase letters like `x`, `n`, `o` (excludes ascenders/descenders). The single biggest driver of a typeface's perceived size and legibility at small sizes.
- **Cap-height** — height of capital letters.
- **Ascender / descender** — the parts of letters like `h`/`b` that rise above x-height, and `g`/`p` that drop below the baseline.
- **Counter** — the enclosed or partially-enclosed space inside letters like `o`, `e`, `a`.
- **Baseline** — the invisible line all letters (except descenders) sit on.

## Classification

### Serif

| Class | Examples | Character | Reads as |
|---|---|---|---|
| Old-style / Garalde | Garamond, Bembo, Caslon | Low stroke contrast, angled stress, calligraphic roots | Literary, timeless, trustworthy, warm |
| Transitional | Times New Roman, Baskerville, Georgia | More vertical stress, moderate contrast | Neutral, editorial, safe, highly legible |
| Didone / Modern | Didot, Bodoni, Playfair Display | Extreme thick/thin contrast, vertical stress, hairline serifs | Luxury, fashion, high-end editorial, dramatic |
| Slab | Rockwell, Roboto Slab, Zilla Slab | Heavy block serifs, low contrast | Bold, sturdy, confident, industrial |

### Sans-serif

| Class | Examples | Character | Reads as |
|---|---|---|---|
| Grotesque | Helvetica, Akzidenz-Grotesk | Early sans, slightly quirky proportions | Utilitarian, a little vintage-modern |
| Neo-grotesque | Helvetica Neue, Inter, Arial | Cleaner, more uniform strokes | Neutral, modern, Swiss |
| Geometric | Futura, Poppins, Century Gothic | Built from circles/squares/triangles | Modern, clean, can feel cold at scale |
| Humanist | Gill Sans, Lato, Open Sans, Lufga | Calligraphic roots, varied stroke widths | Friendly, warm, highly legible at small sizes |

### Other

- **Script/handwriting** (Great Vibes, Parisienne) — accents and signatures only. Never body text, never all-caps (scripts are designed with connecting strokes that all-caps setting breaks).
- **Display/decorative** — headlines only, at large sizes. Illegible or exhausting at body-text sizes almost by design.
- **Monospace** (JetBrains Mono, IBM Plex Mono) — technical/code contexts, or as a deliberate "editorial meets data" accent for labels, timestamps, numerals.

## Pairing rules

1. **Contrast, don't conflict.** Pair fonts that are clearly different in structure (serif + sans) or clearly different in role (display weight vs. text weight). Two fonts that are almost-but-not-quite alike create visual tension with no payoff — the reader half-registers a mismatch without knowing why.
2. **Limit to two families.** A third is allowed only as a rare, deliberate accent (e.g., a monospace for numerals/labels).
3. **Assign explicit roles and never let two fonts compete for the same one:** Display/Headline, Body, Accent/Label. Every piece of type in the system should map to exactly one role.
4. **Match or clash on purpose.** For harmony, pick fonts with similar x-height and mood. For editorial tension (an advanced move, use rarely), deliberately clash proportions — but only once you understand what "harmony" looks like well enough to know you're breaking it.
5. **Reliable default pairs:**
   - Playfair Display (or Canela/Freight Display) + Inter/Source Sans/Lufga — the high-contrast-serif-display + humanist-sans-body pattern behind most editorial/luxury personal-brand sites.
   - Georgia + Verdana — the boring-but-bulletproof web-native pair.
   - Garamond + Lufga — MonnyCreaX's own house pairing (soft old-style serif + warm humanist sans).
6. **Superfamily shortcut.** When unsure, pick a type family that ships matched serif and sans cuts (PT Serif/PT Sans, Source Serif/Source Sans, Noto Serif/Noto Sans). They share metrics by design, so harmony is guaranteed.

## Type scale (hierarchy by size)

Don't pick font sizes ad hoc — derive them from a ratio (a "modular scale") so every step feels intentional and related to the others.

| Ratio name | Value | Feel |
|---|---|---|
| Minor Second | 1.067 | Very subtle — dense/editorial |
| Major Second | 1.125 | Subtle |
| Minor Third | 1.2 | Safe default for UI/product |
| Major Third | 1.25 | Good default for marketing/brand sites |
| Perfect Fourth | 1.333 | Noticeable, confident |
| Golden Ratio | 1.618 | Dramatic — huge headline vs. small label, the editorial-luxury look |

**Practical common scale (px, base 16):** 12, 14, 16, 18, 20, 24, 32, 40, 48, 64, 80

Rules:
- Never go below 16px for body text on web. 12–14px is for labels/captions/eyebrows only.
- Cap a brand system at 5–6 scale steps. More than that becomes unmanageable and stops reading as a "scale" at all.

## Hierarchy mechanics beyond size

- **Weight** — 400 for body, 500–600 for subheads/emphasis, 700 for headlines. Don't use more than 3 weights of one family in a single system.
- **Color** — a muted/secondary text color for de-emphasis (captions, metadata, timestamps) vs. full-contrast primary text for anything that must be read first. (Check both against the contrast minimums in `color-and-contrast.md` — muted text is where accessibility fails quietly.)
- **Case + tracking** — small caps or all-caps with positive letter-spacing (+5% to +12%) is the standard "eyebrow/label" treatment. Always pair wide tracking with short, all-caps/small-caps text; never apply wide tracking to a full paragraph — it kills readability by breaking word-shape recognition.
- **Italics** — for a single emphasized word/phrase or an attribution line, not entire paragraphs.

## Line-height, measure, and tracking

- **Body line-height:** 1.5–1.6× the font size (16px text → ~24–26px line-height).
- **Headline line-height:** tighter, 1.1–1.3× — large type needs proportionally less line-height because the eye travels less relative to letter size.
- **Measure (line length):** 45–75 characters per line; ~66 is the sweet spot. Too long and the eye loses its place on the wrap; too short and reading feels choppy.
- **Letter-spacing (tracking):** 0 by default for body text. Tighten large display headlines slightly (-1% to -3%) — big type has proportionally too much space at default tracking. Open up small caps/labels (+5% to +12%).

## Web/technical delivery

- **Variable fonts** cover a full weight range in one file — better performance than loading four static weights separately.
- **`font-display: swap`** avoids invisible text while a webfont loads.
- **Licensing** — Google Fonts are free for any use. A purchased/foundry font (e.g., an Adobe Fonts library face) typically needs a *web-embedding* license separate from its desktop license. Check before shipping a client site with a paid typeface.
