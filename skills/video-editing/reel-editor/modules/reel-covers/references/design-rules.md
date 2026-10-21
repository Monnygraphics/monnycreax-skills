# Reel cover design rules

Learned building a client sub-brand (Oct 2026), modelled on Prisca Ndifor's Instagram grid (instagram.com/priscandifors).

## What makes the reference work
- Two tile types mixed in one grid: **cutout portrait on a brand shape** (calm, branded) and **full-bleed photo with type** (punchy, for myths/hot takes/events).
- Headline = **bold line + script line** ("When Other People / *Stop Defining You*"). The script carries the emotion.
- A small **series tag** ("Day 33 of the identity project") makes the feed feel like a body of work.
- **Checkerboard rhythm**: light tile, dark tile, alternating. Same layout every time, so the grid reads as one brand.

## Canvas
- Design at **1080x1920** (Reel cover). Instagram's profile grid crops to the centre **1080x1440** (3:4), so keep the wordmark, headline and tag inside y 240 to 1680. render.js exports both.
- Headline top at ~336px, wordmark lockup at ~262px. On full covers the type sits at the bottom (bottom ~320px) over a gradient.

## Choosing photos
- Make a contact sheet first (scripts/new-project.js) and pick by number. Use one Read on the sheet, not 35 image reads.
- **Arch covers need a clean studio backdrop** (grey, brown, plain). The subject cuts out cleanly, and props like a chair or laptop are fine.
- **Full covers want strong colour backdrops** (red, patterned light) or an environment (office). Pick shots where the bottom third is legs, a chair or floor, because the type covers it.
- Vary looks across the set (outfit or backdrop changes every 1 to 2 covers).
- **Outfit vs arch contrast**: never put a dark outfit on a dark arch, or a colour on the same hue (royal blue on teal is borderline but works). Flip the theme of that cover instead.

## Type
- Bold line: the brand's headline font at weight 700. Bold reads at thumbnail size, and thin weights vanish.
- Script line: script fonts have small x-heights, so size them big (Pantherdam needed 236px, Corinthia ~150px). Use `scriptScale` in brand.js.
- Lines over 14 characters auto-shrink (`.long`). `text-wrap: balance` avoids orphans.
- **Script capitals swing** (B, M, I, H). Check any line2 that starts with capitals or contains a brand name, and give it extra margin-top in tweaks.js (a client sub-brand cover 01: `margin-top:34px`).
- Keep the client's exact title wording. Only choose where to split it between bold and script.
- Follow the client's voice rules (for example, no em dashes).

## Brand
- Use the client's real kit. Look for an SVG/AI folder, render it to an image and look at it, because kit labels lie (her "Canela" is a geometric sans).
- If a sub-brand has no identity yet, borrow the parent brand's kit (a client sub-brand uses its parent brand's kit) or stay neutral and warm. Never put the studio's own house look on a client.
- Logo mark: inline SVG with `fill="currentColor"` so it recolours on light and dark tiles.

## Review loop
1. Render all covers, then Read `out/grid-preview.jpg` (the whole feed in one image).
2. Look for: text collisions, tag sitting on the face or hair, low-contrast outfit vs arch, fonts falling back (render.js reports failed fonts), orphan words.
3. Fix with tweaks.js or a theme flip, re-render only those ids (`node render.js <id>`), and Read the full-size cover.
4. Show the user grid-preview.jpg plus one full cover.

## Scope
Graphics are often outside a video retainer. Mention it once so the studio can decide: bonus or add-on.
