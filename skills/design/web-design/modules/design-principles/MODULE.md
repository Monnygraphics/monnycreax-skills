---
name: design-principles
description: >
  Core visual design fundamentals for branding and brand identity work:
  typography (font classification, pairing rules, type scale, hierarchy,
  line-height/letter-spacing), color theory and WCAG contrast/accessibility,
  spacing and grid systems (padding vs margin, 8pt scale, whitespace,
  alignment, proportion), and the foundational principles of design
  (contrast, repetition, alignment, proximity, hierarchy, balance, Gestalt
  basics). Includes worked style archetypes — including an Editorial Luxury
  archetype matching the MonnyCreaX house system — that show the principles
  combined into a real system. Use whenever building, specifying, or
  critiquing a brand's visual system: choosing/pairing fonts, building a
  color palette, setting spacing/layout rules, writing a brand style guide,
  or reviewing a design (client site, deck, social template, logo) for
  whether the type, color, contrast, or spacing choices actually hold up.
  Triggers: "font pairing", "what colors should I use", "check contrast",
  "spacing feels off", "design principles", "build a brand style guide",
  "critique this design", "is this accessible", "why does this look off".
  Complements brand-strategist (strategy/positioning — run that first for
  the identity truths this skill translates into visuals) and ui-ux-pro-max
  (searchable database of 161 palettes/57 font pairings/UX patterns for
  live app/product UI). Do NOT use for pure app-interaction/UX mechanics
  (touch target sizing, navigation patterns, animation timing) — that's
  ui-ux-pro-max's job, not this skill's.
---

# Design Principles (Branding & Visual Identity)

The theory layer under every brand visual decision: why a font pairing
works, why a palette holds together, why spacing feels "designed" instead
of assembled, and why some layouts have an obvious focal point while others
compete with themselves. Use this to build new brand visuals from scratch
or to diagnose why an existing one isn't landing.

## When to use

- Choosing or pairing typefaces for a brand, deck, or site
- Building a color palette (not just picking pretty colors — architecting roles)
- Checking contrast/accessibility on real text-background or text-photo pairs
- Setting spacing/grid rules for a layout system
- Reviewing a design and needing to name *specifically* what's wrong, not just "it feels off"
- Translating brand-strategist's Phase 3.2 (Visual/Expression) direction into an actual palette, type system, and spacing system

## Do NOT use for

- Live app/product UI mechanics (touch targets, navigation patterns, animation
  timing, form validation UX) — use `ui-ux-pro-max` for that.
- Brand strategy/positioning itself (the "who are you, what do you claim")
  — use `brand-strategist`; this skill starts once identity is already clear.

## The four pillars (quick reference)

| Pillar | Governs | Non-negotiable rule | Deep dive |
|---|---|---|---|
| **Typography** | Voice, hierarchy, readability | Max 2 type families with distinct roles; never pair two fonts of near-identical style | `references/typography.md` |
| **Color & Contrast** | Mood, brand recognition, accessibility | AA minimum: 4.5:1 body text, 3:1 large text/UI components | `references/color-and-contrast.md` |
| **Spacing & Layout** | Rhythm, organization, perceived quality | Pull every spacing value from a fixed scale (4/8pt); align everything to something | `references/spacing-and-layout.md` |
| **Core Principles** | Whether it reads as *one system* | Contrast, Repetition, Alignment, Proximity (CRAP) — plus hierarchy, balance, unity | `references/principles-and-archetypes.md` |

## Pre-ship checklist

Run this before calling any brand visual done:

- [ ] Two type families max, each with one clear role (display vs body vs label)
- [ ] A defined type scale used consistently (not ad hoc font sizes)
- [ ] Text contrast checked and passing — including decorative/accent text and text over photography, not just body copy
- [ ] Palette has exactly one accent color, a defined neutral ramp, and clear roles (primary/secondary/accent/neutral)
- [ ] Every spacing value traces back to the scale, not eyeballed
- [ ] Every element aligns to something; related items are grouped by proximity, unrelated items are separated
- [ ] One clear focal point — the eye has an obvious place to land first

## How to apply

### Building a new brand visual system
1. Start from `brand-strategist`'s Phase 3.2 (Visual/Expression) output if it exists — identity truths should drive every choice below, not taste alone.
2. Assign type roles and pick the pairing → `references/typography.md`
3. Architect the palette (primary/secondary/accent/neutrals, not just swatches) → `references/color-and-contrast.md`
4. Define the spacing scale and grid → `references/spacing-and-layout.md`
5. Choose or adapt a style archetype so all the above cohere into one system → `references/principles-and-archetypes.md`
6. Run the pre-ship checklist above.

### Critiquing an existing design
1. Check contrast first — it's the one non-negotiable, binary pass/fail item.
2. Count type families and check for a consistent scale.
3. Check whether spacing follows a rhythm (a small set of repeated values) or looks random.
4. Check for a single clear hierarchy/focal point and correct proximity grouping.
5. Name the 2–3 highest-impact fixes. Don't list everything — prioritize what's actually breaking the read.

## Relationship to other skills

- **brand-strategist** — produces the identity/positioning truths (who, what they own, how it should feel). This skill translates those truths into an actual type system, palette, and spacing system. Strategy first, then this.
- **ui-ux-pro-max** — a searchable database of pre-built palettes, font pairings, and UX/interaction patterns for live app and product UI. Reach for it when the deliverable is a functioning app screen and you want a fast, validated combination. Reach for this skill when the deliverable is brand identity, print, decks, or marketing/social assets, or when you need to *reason about why* a combination works well enough to adapt or invent one rather than pick a pre-built option.

## References (load only what you need)

- `references/typography.md` — font classification, pairing rules, type scale, hierarchy mechanics, line-height/measure, web delivery
- `references/color-and-contrast.md` — color theory/harmonies, brand palette architecture, WCAG contrast math + tables, dark mode, text-over-image
- `references/spacing-and-layout.md` — padding vs margin, spacing scale, whitespace as a tool, grids, alignment, proportion
- `references/principles-and-archetypes.md` — CRAP + Gestalt principles, hierarchy/balance/emphasis/unity, worked style archetypes (incl. Editorial Luxury)
