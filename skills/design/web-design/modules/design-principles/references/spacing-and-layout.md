# Spacing & Layout

## Padding vs. margin

- **Padding** — space *inside* an element's boundary, between its edge and its content. Use it to give content room to breathe inside a container (card, button, section).
- **Margin** (or `gap` in flex/grid) — space *outside* an element's boundary, between it and its neighbors. Use it to separate distinct elements from each other.

Mixing these up inconsistently — padding a container instead of gapping its children, or vice versa — is the single most common cause of "why does this look uneven even though the numbers are right."

## The spacing scale

Never pick spacing values ad hoc ("this looked about right"). Define a constrained numeric scale and use only values from it. This one habit is most of what makes a layout feel *designed* instead of *assembled*.

- **Base unit:** 8px (the 8-point grid — Material Design and most mature design systems use this). 4px exists as a half-step for tight spots.
- **Standard scale:** 4, 8, 12, 16, 24, 32, 48, 64, 96, 128

Assign roles to specific steps so the same *relationship* always uses the same number:

| Tier | Values | Use for |
|---|---|---|
| Micro | 4–8px | Tightly related items: icon + its label, a form label + its input |
| Component | 16–24px | Related items in a group: paragraph spacing, card internal padding |
| Section | 32–48px | Between distinct components on a page: a heading block and the content below it |
| Macro | 64–128px | Between major page sections |

This four-tier pattern is worth naming explicitly because it's usually the actual diagnosis behind "the spacing feels off": either two unrelated things are using a micro-tier gap (so they read as accidentally related), or two related things are using a macro-tier gap (so they read as unrelated).

## Whitespace as an active tool

Whitespace is not empty leftover space — it's doing work, at two scales:

- **Micro whitespace** — the tight spacing inside a component (icon-label gap, line-height, letter-spacing). Governs legibility and precision.
- **Macro whitespace** — the space between and around major layout blocks. Governs *perceived quality*. More macro whitespace reads as premium, editorial, confident. Dense macro whitespace reads as utilitarian and information-dense (dashboards, data tools) — appropriate there, wrong for a luxury brand site. This is the biggest single lever in an editorial/luxury aesthetic: those layouts aren't using an exotic technique, they're using 2–3× the whitespace a typical SaaS site uses.

Whitespace groups and separates exactly like the proximity principle (`principles-and-archetypes.md`): the gap *between* two sections should always be visibly larger than the gap *within* a section, or the sections will visually bleed into each other.

## Grid systems

- **12-column grid** (web/print default) — divides evenly into halves, thirds, and quarters, which is why 12 is the near-universal choice over, say, 10.
- **8pt/4pt grid** (UI/mobile) — every dimension (spacing, component size) is a multiple of the base unit, so everything aligns without hairline mismatches.
- **Gutters** — the fixed gap between columns (typically 16–32px depending on breakpoint), distinct from the **outer margin** (the gap between the grid and the viewport edge, usually larger than the gutter).
- **Container max-width** — constrain content on very wide viewports (commonly 1140–1280px for a centered container; full-bleed only for hero imagery/background). Unconstrained text on a 2560px monitor blows straight past the 45–75 character measure from `typography.md`.
- **Baseline grid** — a vertical rhythm grid where every line of text, regardless of size, lands on a shared baseline multiple. The print-grade version of the spacing scale; mostly relevant for dense editorial/publication layouts.
- **Breakpoints** — a small fixed set (e.g., 375 / 768 / 1024 / 1440) rather than one-off breakpoints per component. Same "constrained scale" logic as spacing.

## Alignment

- Every element should share an edge (left, right, top, bottom, or center) with at least one other element. Nothing floats at an arbitrary position. Alignment creates invisible connective lines the eye uses to parse a layout as organized *before* reading any content.
- **Optical vs. mathematical alignment** — shapes with curves or points (circles, triangles, arrows) need to slightly overshoot a shared edge/baseline compared to rectilinear neighbors, or they'll look smaller or higher than mathematically-identical elements. Classic example: a circular button next to a square one at the "same" size looks off until the circle is nudged 1–2px larger.
- **Text alignment** — left-align (or right-align for RTL) anything longer than 1–2 lines. Centered body text is harder to scan because the eye has to re-find the start of each line at a different x-position each time. Centered alignment works for short, deliberate elements (headlines, short pull-quotes, labels) — notice that even heavily-centered editorial layouts only center 1–3 word headlines and eyebrows, never paragraphs.

## Proportion tools

Compositional aids, not mandatory law:

- **Rule of thirds** — divide a frame into a 3×3 grid and place key subjects/focal points on the intersections rather than dead-center. Used for photo cropping and hero-image composition.
- **Golden ratio (~1.618)** — a proportion many find pleasing for major layout divisions (e.g., a 60/40-ish text/image split) or as a type-scale ratio (`typography.md`). Treat it as one tool among several, not a formula that guarantees good design on its own.
