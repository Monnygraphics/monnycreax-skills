---
name: web-design
description: Design, build, redesign or review websites, landing pages, portfolios and web-app UI, from a brief, screenshot, Pinterest board or brand kit, with browser verification and deploy. Includes UI/UX, accessibility, frontend engineering and design-review modules.
---

# Web Design (Unified, self-contained)

One skill, one pipeline. This file holds the **merged rules**. The depth lives in **31 bundled modules** under `modules/<name>/MODULE.md` (each is a complete original skill, kept with its own references, rules, scripts and data). Read a module only when its phase is reached; never load them all.

```
0 CLASSIFY → 1 DESIGN READ → 2 DIRECTION → 3 CONCEPT (optional image-first) → 4 BUILD → 5 REVIEW → 6 VERIFY IN BROWSER → 7 SHIP
```

Paths below are relative to this skill's folder. When a module mentions its own `references/`, `rules/`, `scripts/` or `data/`, those sit inside that module's folder.

---

## 0. Classify the job (pick one row, read the listed module)

| Job | Read | Then |
|---|---|---|
| New landing page / marketing site / portfolio | this file + `modules/design-taste-frontend` | 4 → 5 → 6 |
| Redesign / "make it premium / less generic" | `modules/redesign-existing-projects` (audit first, never break function) | 5 → 6 |
| Screenshot / mockup / Figma → code | `modules/image-to-code` (analysis + extraction rules §20-28) | 6 (compare side by side) |
| Generate concept images before coding | `modules/imagegen-frontend-web` / `modules/imagegen-frontend-mobile` | then `image-to-code` |
| Pinterest board / pins / "here's my moodboard" | `modules/pinterest-moodboard` (pull pins → palette, type, layout, dials) | 2 → 4 |
| Canva brand kit / Canva design / need images, OG or social graphics | `modules/canva-design` (requires Canva connector) | 1, 3, 4, 7 |
| "Make it look like <brand>" / need a DESIGN.md | `design-md/INDEX.md` + `modules/stitch-design-taste` | 4 |
| Pick style / palette / fonts / chart type / UX rules | `modules/ui-ux-pro-max` (run `python modules/ui-ux-pro-max/scripts/search.py "<query>" --design-system`), `modules/design-principles` (theory, contrast math) | 4 |
| Motion: one animation | `modules/animate` (+ `RECIPES.md`), `modules/apple-design` for gestures/springs | 5 `modules/review-animations` |
| Motion audit of a codebase | `modules/improve-animations` | |
| Choosing UI libraries (dialogs, toasts, cmdk, motion, charts, dnd) | `modules/pick-ui-library` | |
| React / Next.js code | `modules/vercel-react-best-practices`, `modules/vercel-composition-patterns`, `modules/vercel-react-view-transitions` | |
| React Native / Expo | `modules/vercel-react-native-skills` (+ `imagegen-frontend-mobile` for concepts) | |
| UI code review / a11y audit | `modules/web-design-guidelines` (offline rules: `guidelines-snapshot.md`) | |
| Copy / microcopy review | `modules/writing-guidelines` | |
| Brand identity board / logo system imagery | `modules/brandkit` | |
| Browser automation / testing | `modules/playwright-cli` + `references/verify.md` | |
| Deploy / perf & cost | `modules/deploy-to-vercel`, `modules/vercel-cli-with-tokens`, `modules/vercel-optimize` | |

Style presets (read only when the design read lands there): `modules/minimalist-ui` (editorial, warm mono, flat bento), `modules/industrial-brutalist-ui` (Swiss + terminal, data-heavy), `modules/high-end-visual-design` (agency polish), `modules/gpt-taste` (GSAP-heavy Awwwards motion). `modules/full-output-enforcement` when a long file must be emitted with no placeholders.

Optional, only if installed separately on the machine (gstack, not bundled because they need the gstack binary): `design-consultation`, `design-shotgun`, `design-html`, `design-review`, `/browse`, `/qa`.

---

## Environments (Claude Code / claude.ai chat / cloud)

Detect where you are and adapt. The pipeline and rules don't change; only the tooling does.

| | Claude Code (desktop / CLI) | claude.ai chat (skill uploaded) | Claude Code on the web (cloud) |
|---|---|---|---|
| Build output | project files | a single-file **HTML artifact** (or React artifact). For multi-page sites, ask for a zip deliverable | project files in the repo |
| Verify (phase 6) | `references/verify.md` (playwright-cli) or the Browser pane | render the artifact. Self-check at 375px and 1280px mentally against preflight. The code tool can run `modules/ui-ux-pro-max/scripts/search.py` and preflight greps | playwright-cli if it installs. Otherwise headless checks + preflight greps |
| Deploy (phase 7) | Vercel modules | hand the user the files. Vercel CLI is not available in chat | Vercel modules if a token is set |
| Pinterest | RSS / web fetch / Claude in Chrome / screenshots | web fetch of RSS or pin URLs, or uploaded screenshots | web fetch / screenshots |
| Canva | Canva MCP (`/mcp` to authorise) | Canva connector (Settings → Connectors) | connector if enabled for the session |

Module paths are relative to this skill's folder in every environment. In claude.ai chat the skill files are read from the skill directory, so read modules the same way.

---

## 1. Design Read (always, before any code)

State one line: **"Reading this as: <page kind> for <audience>, with a <vibe> language, leaning toward <system / aesthetic family>."**

Signals: page kind, the user's vibe words, references (URLs, screenshots, named brands), audience, existing brand assets, quiet constraints (accessibility-first, regulated, public sector, kids). Quiet constraints override taste. If genuinely ambiguous ask **one** question; otherwise declare and proceed.

Then set three dials (taste-skill):

| Preset | VARIANCE (symmetry→chaos) | MOTION (static→cinematic) | DENSITY (airy→cockpit) |
|---|---|---|---|
| SaaS landing | 7 | 6 | 4 |
| Agency / creative | 9 | 8 | 3 |
| Premium consumer | 7 | 6 | 3 |
| Personal brand / authority (coach, speaker, founder) | 6 | 4 | 3 |
| Editorial / blog | 6 | 4 | 3 |
| Dashboard / app UI | 4 | 3 | 7 |
| Trust-first / public sector | 3 | 2 | 5 |
| Redesign (preserve) | match | +1 | match |

### Authority order (resolves every conflict between skills)
1. The user's explicit brief in this conversation.
2. The **client's own brand** (their logo, colors, fonts, existing site).
3. **MonnyCreaX house system** (cream/ink/gold, EB Garamond + Lufga, no em dashes) - **only** for MonnyCreaX / bethwelmonny.com materials. Never reuse it for a client (rejected on sight by Client A).
4. A chosen `design-md/<brand>` reference (structure and discipline, not identity).
5. taste-skill defaults and bans below.

So: taste-skill's "no serif default" and "no cream+brass palette default" are **defaults**, overridden by 1-3. A ban only stops you from *reaching for* a cliché unprompted.

---

## 2. Direction sources

- **DESIGN.md library**: `design-md/INDEX.md` lists 84 real-site systems by category (AI, dev tools, fintech, retail, automotive, editorial, retro). Read 1-2 matching files, extract the *rules* (type scale, spacing rhythm, radius, accent discipline, component anatomy), then write the project's own `DESIGN.md` at repo root (`modules/stitch-design-taste` format) so later sessions stay consistent. Never copy another brand's logo, wordmark, proprietary typeface, or signature color for a client.
- **ui-ux-pro-max** (`modules/ui-ux-pro-max`): run its search script for style / palette / font pairing / UX rules per product type.
- **design-principles** (`modules/design-principles`): type classification and scale, WCAG contrast math, 8pt spacing, CRAP / Gestalt, "why does this feel off".

---

## 3. Image-first concepts (optional, for visually important pages)

The `image-to-code` / `imagegen-*` modules were written for Codex's built-in image tool. In Claude Code and claude.ai:
- **Best input**: a screenshot, mockup, or Figma frame the user supplies. Read it with the Read tool (or Figma MCP `get_screenshot` / `get_design_context`).
- **Moodboard first**: if the user has a Pinterest board, run `modules/pinterest-moodboard` before writing image prompts.
- **Generating**: Canva `generate-image` (see `modules/canva-design`) or Figma MCP `generate_image` if connected; otherwise write the per-section art-direction prompts from `modules/imagegen-frontend-web` and skip to code.
- Rules that still apply without generation: one image per section (never a compressed board), deep analysis before code, extraction order **text → typography → spacing → components → color** (`modules/image-to-code` §21-25), anti-drift (build what the image shows, not what you assume).

---

## 4. Build: merged non-negotiables

### Typography
- Display and body from a deliberate pairing (ui-ux-pro-max / design-principles). Inter is not a default (fine for neutral/Linear-style/public-sector). Fraunces and Instrument Serif are banned as defaults. Serif only when the brand or a genuinely editorial/luxury/heritage family justifies it.
- Emphasis inside a headline = italic or bold of the **same** family, never a random second family.
- Hero headline max 2 lines desktop; plan font size and image size together. Body `max-width: 65ch`, line-height 1.5-1.7.
- `text-wrap: balance` on headings, `pretty` on body. `…` not `...`, curly quotes, `tabular-nums` for number columns, non-breaking spaces in `10 MB`, `⌘ K`.
- Italic display words with descenders (g j p q y): line-height ≥ 1.1 plus bottom reserve.

### Color
- One accent, locked across the whole page. Saturation under 80%. One neutral temperature (do not mix warm and cool greys).
- No AI purple/blue glow, no neon outer glows, no gradient text on big headers, no pure `#000`.
- Tokens on `:root`; dark mode via tokens, tested in both modes; `color-scheme` set; `<meta name="theme-color">` matches background.
- Contrast: WCAG AA (4.5:1 body, 3:1 large text and UI) for buttons, placeholders, helper and error text, ghost buttons over images (add scrim or stroke).

### Layout
- Hero fits the first viewport: max 4 text elements (optional eyebrow, headline, ≤20-word subtext, 1 primary + ≤1 secondary CTA). Top padding ≤ 6rem. Logo walls, pricing teasers, and avatar rows go **below** the hero.
- Nav on one line at 1024px, height 64-80px.
- No three-equal-cards feature row. No more than 2 zigzag image/text sections in a row. Each layout family at most once per page; 8 sections need ≥ 4 families.
- Bento: exactly as many cells as content, varied backgrounds in 2-3 cells, no empty tiles.
- Eyebrows: at most 1 per 3 sections. No section numbers (`01 /`, `002 ·`), no scroll cues, no decorative status dots, no locale/weather strips, no pills overlaid on photos.
- Cards only when elevation means hierarchy; otherwise spacing or dividers. One radius scale for the page. Shadows tinted to the background.
- Every multi-column block declares its `< 768px` collapse. Flex children `min-w-0`. No horizontal scroll at 375px. Safe-area insets on full-bleed.

### Components and states
- Every interactive element: hover, `:focus-visible` ring (never bare `outline: none`), active (scale 0.98 or 1px press), disabled, loading (skeleton matching final shape), empty, error.
- Forms: label above input, never placeholder-as-label, correct `type`/`inputmode`/`autocomplete`, errors inline under the field, focus first error, never block paste.
- `<button>` for actions, `<a>` for navigation, icon-only buttons get `aria-label`, decorative icons `aria-hidden`.
- One CTA label per intent across the page (not "Get in touch" + "Contact us" + "Let's talk"). CTA text never wraps on desktop.
- Icons from a real set (Phosphor, Tabler, Radix, HugeIcons); no hand-rolled SVG icons, no emoji as icons, no div-built fake product screenshots.

### Content
- Real, specific copy: no "Elevate / Seamless / Unleash / Next-Gen", no Acme/Nexus names, no John Doe, no 99.99%. Use plausible, locale-appropriate names and organic numbers.
- **No em dashes (—) or en-dash separators anywhere visible.** (taste-skill and MonnyCreaX agree.) Use commas, colons, periods, or a hyphen.
- Active voice, specific button labels ("Book a Discovery Call", not "Submit"), errors that say how to fix.

### Motion
- Purpose first (feedback, orientation, continuity); frequent actions get little or no motion. Animate `transform`/`opacity` only; never `transition: all`. Interruptible.
- `prefers-reduced-motion` honoured on everything, decorative loops stop. Hover effects gated by `(hover: hover)`.
- Details: `modules/animate` (curves, durations, recipes) and `modules/apple-design` (springs, gestures, materials).

### Performance
- `<img>` with width/height, `loading="lazy"` below the fold, `fetchpriority="high"` on the hero image. Fonts preloaded with `font-display: swap`. Video over GIF. Virtualise lists > 50. No layout reads in render.
- Targets: LCP < 2.5s, CLS < 0.1, INP < 200ms. React specifics in `modules/vercel-react-best-practices`.

### Stack defaults (when the user has none)
Single page or brochure site: semantic HTML + modern CSS (custom properties, grid, container queries). App: Next.js + Tailwind + a real component primitive (Radix / base-ui / shadcn **customised**, never default-state). Verify every dependency exists before importing.

---

## 5. Review

1. `modules/web-design-guidelines` on changed files (fetches live rules; offline fallback `modules/web-design-guidelines/guidelines-snapshot.md`). Output `file:line - issue`.
2. Run the mechanical checks in `references/preflight.md` (em-dash grep, eyebrow count, CTA intents, contrast, layout families).
3. Visual / taste pass: `modules/redesign-existing-projects` audit list (or gstack `design-review` if installed). Motion diffs: `modules/review-animations`. Copy: `modules/writing-guidelines`.

## 6. Verify in a real browser (never claim "done" from code alone)

Use `references/verify.md` (playwright-cli recipe: 375 / 768 / 1280 / 1920 widths, light and dark, console errors, keyboard tab-through, reduced motion). Inside the Claude desktop app the built-in Browser pane (`preview_start`) works too. For user feedback on a live page: `playwright-cli show --annotate`. Show screenshots as proof.

## 7. Ship

`modules/deploy-to-vercel` (or `modules/vercel-cli-with-tokens` for token auth) → `modules/vercel-optimize` once real traffic exists. Otherwise the project's own deploy (`/ship`, `/land-and-deploy`).

---

## Output contract
1. Design Read line + dials + chosen reference(s).
2. The build (complete files, no `// ...rest` placeholders).
3. Pre-flight results (pass/fail per item, fixed before reporting).
4. Browser proof (screenshots at mobile and desktop).

## Modules (merged 2026-10-20)
Read `modules/<name>/MODULE.md` only for the task at hand; paths inside a module are relative to its own folder.

| Module | What it covers |
|---|---|
| `design-consultation` | Design consultation: understands your product, researches the landscape, proposes a complete design system (aesthetic, typography, color, layout, spac... |
| `design-html` | Design finalization: generates production-quality Pretext-native HTML/CSS. (gstack) |
| `design-review` | Designer's eye QA: finds visual inconsistency, spacing issues, hierarchy problems, AI slop patterns, and slow interactions — then fixes them. (gstack) |
| `design-shotgun` | Design shotgun: generate multiple AI design variants, open a comparison board, collect structured feedback, and iterate. (gstack) |
| `senior-frontend` | Frontend development skill for React, Next.js, TypeScript, and Tailwind CSS applications. Use when building React components, optimizing Next.js perfo... |
| `frontend-ui-engineering` | Builds production-quality, accessible, responsive user-facing UIs. Use when building or modifying interfaces and pages, creating components, implement... |
| `a11y-audit` | Accessibility audit skill for scanning, fixing, and verifying WCAG 2.2 Level A and AA compliance across React, Next.js, Vue, Angular, Svelte, and plai... |
| `full-page-screenshot` | Use when the user asks to capture a full-page screenshot, long screenshot, or complete page capture of a web page. Handles SPA scroll containers, lazy... |
| `ux-researcher-designer` | UX research and design toolkit for Senior UX Designer/Researcher including data-driven persona generation, journey mapping, usability testing framewor... |
