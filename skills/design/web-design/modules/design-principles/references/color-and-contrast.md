# Color & Contrast

## Color models

- **Hex/RGB** — how screens store color. Not intuitive to reason about or adjust by hand.
- **HSL** (Hue 0–360°, Saturation 0–100%, Lightness 0–100%) — the practical model for building a *ramp*. Hold hue and saturation constant, vary lightness, and you get a coherent tint/shade ramp for one brand color (e.g., hover/active/disabled states, or a 9-step neutral ramp). Reach for HSL, not hex, whenever you need "this color, but lighter/darker."

## Color harmonies (positions on the color wheel)

| Harmony | Structure | Feel | Risk |
|---|---|---|---|
| Monochromatic | One hue, varying lightness/saturation | Calm, cohesive, minimal, low-risk | Can feel flat without a neutral or accent break |
| Analogous | 2–3 adjacent hues (e.g. blue/blue-green/green) | Harmonious, natural, low tension | Can lack a focal point if nothing else contrasts |
| Complementary | 2 opposite hues (e.g. blue/orange) | Maximum contrast and energy | Two large complementary fields fight each other — use one as a small accent, not two equal fields |
| Split-complementary | Base hue + the two hues adjacent to its complement | Same energy as complementary, softer | Still needs one dominant hue |
| Triadic | 3 evenly-spaced hues | Vibrant, playful | Chaotic unless one hue clearly dominates |
| Tetradic | 4 hues | Rich, complex | Hardest to balance — one dominant, the rest small accents only |

## Brand palette architecture

A palette is not a list of pretty swatches — it's a set of *roles*. Define these explicitly:

- **Primary / signature** — 1 color. The one people associate with the brand.
- **Secondary** — 1–2 supporting colors, usually related to primary (an analogous hue, or a deeper/lighter version of it).
- **Accent** — exactly 1 color, reserved *only* for calls-to-action and the single most important highlight. It should be the most saturated/highest-contrast color in the system — specifically so it stands out *because* it's rare. Using the accent color everywhere is the most common beginner mistake; it cancels the accent's entire job.
- **Neutrals** — a ramp of 5–9 steps (near-white → near-black), usually warmed or cooled slightly to match the brand's temperature rather than pure gray. Used for text, backgrounds, borders, dividers. Most of any real layout is neutral, not brand color — this is true even of the boldest brand systems.
- **Semantic colors** (success/warning/error/info) — kept separate from the brand palette and conventional enough to still read correctly (green = success, red = error) even inside a brand system that itself uses red or green as its signature color. Don't let brand color override semantic meaning in functional UI.

**The 60-30-10 rule** — apply the palette in roughly that proportion per screen/page/spread: 60% dominant/neutral, 30% secondary, 10% accent. This turns a swatch list into an actual application rule.

## Color psychology (use with caution)

Directional, culturally-bound associations — never let this override contrast/accessibility or the positioning work from `brand-strategist`:

| Color | Common association |
|---|---|
| Blue | Trust, calm, stability |
| Red | Urgency, passion, appetite |
| Green | Growth, health, wealth |
| Gold / amber | Premium, warmth, celebration |
| Black | Authority, luxury, formality |
| Cream / off-white | Warmth, approachability (vs. pure white, which reads clinical/minimal) |
| Deep jewel tones (burgundy, emerald, navy) | Quiet luxury, sophistication, restraint |

## WCAG contrast — the actual thresholds

WCAG defines a **contrast ratio** from the *relative luminance* of two colors, ranging 1:1 (no contrast) to 21:1 (pure black on pure white).

**Relative luminance** (per channel, R/G/B normalized to 0–1): if channel ≤ 0.03928, linear = channel / 12.92; otherwise linear = ((channel + 0.055) / 1.055) ^ 2.4. Then `L = 0.2126·R + 0.7152·G + 0.0722·B`.

**Contrast ratio** = (L1 + 0.05) / (L2 + 0.05), where L1 is the lighter of the two colors.

Don't hand-calculate in practice — use a checker (WebAIM Contrast Checker, browser devtools). Know the numbers below so you can eyeball whether a pairing is close or way off:

| Standard | Normal text | Large text (≥24px, or ≥18.66px bold) | UI components / graphical objects |
|---|---|---|---|
| **AA** (minimum) | 4.5:1 | 3:1 | 3:1 |
| **AAA** (enhanced) | 7:1 | 4.5:1 | — |

Rules that follow from this:

- **Color is never the only signal.** Roughly 8% of men (and a smaller share of women) have some color-vision deficiency, most commonly red-green. Pair any color-coded meaning with an icon, text label, or pattern.
- **Dark mode is not "invert the light palette."** Desaturate and lighten brand colors for dark backgrounds — pure saturated colors vibrate/glow uncomfortably on black. Re-check contrast independently per theme; a pairing that passes AA in light mode can fail in dark mode and vice versa.
- **Text over photography** must be checked against the busiest/lightest part of the image the text actually crosses, not the image's average brightness. Use a scrim — a solid or gradient overlay (commonly 30–60% black, or a color from the palette) — between photo and text rather than trusting the raw photo to always be dark or light enough. This is the single most common contrast failure in the photo-hero-plus-headline pattern used across editorial/luxury brand sites.
- **Check decorative and accent text too, not just body copy.** Thin gold script on cream, or a light caption color on a mid-tone background, is exactly where contrast quietly fails AA even when the primary body-text pairing is fine — because it's the pairing nobody thinks to check.

## Quick sanity checks

- Cream (#ECE6E1) on near-black (#181617): ~16:1 — comfortably clears AAA.
- If an accent or caption color "feels a little light," it's worth running the actual checker before shipping — the eye is bad at judging contrast ratios near the AA cutoff.
