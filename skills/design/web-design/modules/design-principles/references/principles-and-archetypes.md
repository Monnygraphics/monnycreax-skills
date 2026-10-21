# Core Principles & Style Archetypes

## CRAP — the four load-bearing principles

From Robin Williams' *The Non-Designer's Design Book* — still the fastest diagnostic for "why does this not look right":

1. **Contrast** — if two things are not the same, make them clearly, deliberately different (size, weight, color, spacing). Weak, almost-contrast reads as a mistake. Strong contrast reads as an intentional decision — it's the actual mechanism behind hierarchy and a focal point.
2. **Repetition** — repeat a visual choice (a color, a shape, a spacing value, a treatment) across a piece so it reads as one system. This is the mechanism behind brand consistency across touchpoints, and also behind rhythm within a single layout (a repeated card treatment across a grid, a consistent icon style).
3. **Alignment** — nothing placed arbitrarily; every element shares a visual connection with another. Full detail in `spacing-and-layout.md`.
4. **Proximity** — group related items close together, separate unrelated items with more space. This alone organizes information hierarchy before a viewer reads a single word, and it's what lets a layout drop borders/boxes/dividers and still read as organized — borders are a crutch when proximity is done right.

## Extended principles

- **Hierarchy** — an explicit priority order (what gets read/seen 1st, 2nd, 3rd), encoded with the tools above: size, weight, color, position, whitespace. A layout with no hierarchy makes everything compete, and the viewer ends up reading nothing.
- **Balance** — the distribution of visual weight (size, color intensity, density) across a composition.
  - *Symmetrical* balance: formal, stable, calm — centered layouts.
  - *Asymmetrical* balance: a large light element on one side can balance a small dark/dense element on the other. More dynamic and modern, but the weights have to actually balance or the layout tips.
- **Emphasis / focal point** — exactly one clear entry point per composition, created via contrast + isolation (surrounding whitespace) + position — not by making many things loud simultaneously.
- **Unity / harmony** — every choice (color, type, spacing, imagery treatment, icon style) should feel like it belongs to the same system. The fastest way to break unity: one more typeface, one more accent color, or one more icon style than the system defines.
- **Scale / proportion** — size relationships communicate importance. A headline 4× the body size reads as dominant; a headline 1.1× the body size barely registers as a headline. See the modular type scale in `typography.md` for the numeric version of this.
- **Movement / flow** — how the eye travels through a composition. Western reading defaults to a **Z-pattern** on sparse layouts (top-left → top-right → diagonal → bottom-left → bottom-right) or an **F-pattern** on text-dense layouts (repeated left-to-right sweeps, decreasing in width down the page). Design the entry point and let size/contrast/alignment guide the eye along an intended path instead of fighting the natural pattern.

## Gestalt principles (the perceptual "why")

- **Similarity** — elements that look alike (same color/shape/size) read as related or grouped, even without proximity.
- **Proximity** — items placed close together read as a group (the perceptual basis for the CRAP principle above).
- **Closure** — the eye completes incomplete shapes. Constantly used in minimal logomarks that imply a full form from partial lines.
- **Continuation** — the eye follows a line, curve, or alignment across a composition rather than jumping direction. The basis for why aligned edges feel connected even across large gaps.
- **Figure-ground** — the eye separates a composition into a foreground "figure" and a background "ground." Ambiguous figure-ground (unclear what's foreground vs. background — e.g. low-contrast text on a busy photo) is uncomfortable and illegible. Clear figure-ground, via a decisive scrim or contrast jump, is what makes photo-hero text sections actually readable.

---

## Worked style archetypes

A style archetype is nothing more than a specific, consistent set of answers to four questions — type roles, palette architecture, spacing/whitespace density, and which principles get emphasized — applied through CRAP/Gestalt. These three are reference points, not the only options.

### 1. Editorial Luxury / Quiet-Luxury Personal Brand

The archetype behind most coach/consultant/founder personal-brand sites — and MonnyCreaX's own house system.

- **Typography** — a high-contrast Didone or transitional serif for display headlines (Playfair Display, Canela, Freight Display — or a softer old-style serif like Garamond, MonnyCreaX's own choice) paired with a humanist or geometric sans for body text and tracked-out small-caps labels/eyebrows (Lufga, Inter, Neue Montreal).
- **Color** — warm neutral base (cream/ivory, roughly `#ECE6E1`–`#F5F5F0`) + a deep grounding neutral (espresso brown or near-black, roughly `#181617`–`#2A1F1A`) + exactly one signature accent (a metallic gold, or a single jewel tone — burgundy, emerald, deep rust). 60/30/10 split, never more than one accent.
- **Spacing** — generous macro whitespace (2–3× a typical SaaS site), full-bleed sections alternating light/dark for rhythm, wide section padding (roughly 96–160px vertical on desktop).
- **Signature motifs** — circular or arched photo crops, thin-line (1–1.5px) geometric icons, outlined pill/rect buttons with tracked all-caps labels, subtle organic texture (marble, soft shadow, gradient) instead of flat color fields, dot-pagination carousels, numbered process lists (01 / 02 / 03).
- **Contrast discipline** — because the palette leans on subtle neutrals and metallics, contrast has to be checked deliberately (`color-and-contrast.md`). This archetype fails quietly (thin gold-on-cream captions, light script over busy photography) far more often than loud, high-saturation archetypes do, precisely because nothing in it looks aggressive enough to trigger a second look.
- **House note** — this is MonnyCreaX's own signature system (cream/ink/gold, EB Garamond/Lufga). Default to it on coach/consultant/founder personal-brand builds unless the client's positioning from `brand-strategist` calls for something else.

### 2. Minimal Modern Tech/SaaS (contrast case)

- **Typography** — one geometric or neo-grotesque sans for everything (Inter, Söhne, Neue Montreal). Weight carries the hierarchy instead of a second family.
- **Color** — a near-grayscale neutral ramp + one saturated, high-contrast accent (electric blue, violet, or a single brand color) used only for CTAs and interactive states.
- **Spacing** — tight, consistent 8pt grid, denser than editorial-luxury — optimized for information density and repeated UI patterns, not macro whitespace.
- **Signature motifs** — flat color fields (no texture/gradient), sharp or minimally-rounded corners, restrained or absent photography.

### 3. Bold Maximalist/Brutalist (contrast case)

- **Typography** — oversized, sometimes deliberately raw system or mono fonts, extreme scale jumps.
- **Color** — high-saturation, sometimes intentionally clashing combinations, minimal restraint.
- **Spacing** — asymmetric, sometimes deliberately breaking the grid it establishes — a break only reads as intentional if the grid was legible in the first place (see Alignment above).
- **Signature motifs** — thick borders, raw/unstyled form controls, rule-breaking as the brand statement itself.
