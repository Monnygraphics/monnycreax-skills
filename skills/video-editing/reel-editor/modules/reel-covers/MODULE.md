---
name: reel-covers
description: Designs and renders branded Instagram Reel / TikTok / Shorts cover thumbnails from a client's photoshoot, video titles and brand kit. It outputs 1080x1920 covers, 3:4 profile-grid crops and a whole-feed preview, in the style of polished coach/speaker feeds: a cutout portrait on a brand arch, or a full-bleed photo, with a bold + script headline, a series tag and a checkerboard grid. Also renders 3 to 5 second animated branded end cards / outros per video (transparent ProRes MOV overlay + solid MP4) without touching the full videos. Uses local AI background removal (rembg), HTML templates, Chrome and ffmpeg. Use when the user wants video endings, outros or end-card overlays for a brand's videos, or when the user wants thumbnails, reel covers, video covers or an Instagram grid look for a client or themselves, shares a photoshoot folder plus video titles or scripts, or points at a reference feed they want to match ("like her thumbnails", "covers for these videos", "design the thumbnails for this series").
---

# Reel Covers

Photos + titles + brand kit → a consistent, on-brand set of reel covers. Start a new project with `scripts/new-project.js`.

## Quick start

```bash
node ~/.claude/skills/reel-editor/modules/reel-covers/scripts/new-project.js "<project>/thumbnails" --photos "<shoot folder>"
node ~/.claude/skills/reel-editor/modules/reel-covers/scripts/brand-from-svg.js "<brand kit SVG folder>"
# fill brand.js + thumbs.js, then:
~/.rembg-venv/Scripts/python -I "<project>/thumbnails/cutout.py"
node "<project>/thumbnails/render.js"
```

## Workflow

Track these as the task list:

1. **Gather inputs.** You need: the shoot folder, the titles (from scripts, a WhatsApp paste or a list), the brand kit (SVG/AI folder, colours, fonts, logo), and an optional reference feed or screenshot. Check memory and project `CLAUDE.md` for client context and voice rules. If no kit exists, ask before inventing one (a parent brand's kit or a neutral warm style is the fallback).
2. **Scaffold + contact sheet.** Run `scripts/new-project.js <dir> --photos <shoot>`. It copies the template, downscales photos to 2400px, and writes `photos/_contact-sheet.jpg` (numbered) + `photos/_index.txt`. Read the sheet once and pick shots by number.
3. **Brand.** Run `scripts/brand-from-svg.js <kit>` for swatches, fonts and installed font files. Render or Read the kit to confirm what the fonts look like. Extract the logo mark with `--mark <logo.svg> --viewbox "x y w h" --out mark.svg`. Fill `brand.js`: local font files or `googleFonts`, light/dark/full colours, wordmark, mark, series tag.
4. **Plan covers in `thumbs.js`.** One entry per video: split each title into `line1` (bold) and `line2` (script), keeping the client's wording. Choose `style` (arch for calm/explainer, full for myths, hot takes and environment shots), alternate `theme`, and check outfit-vs-arch contrast. Use `ep:` for the auto series tag and `kicker:` + `accent: "?"` for Myth-or-Fact covers.
5. **Cutouts.** Run `cutout.py` (arch photos only, skips existing). First-time setup: `python -m venv ~/.rembg-venv && ~/.rembg-venv/Scripts/python -m pip install "rembg[cpu]" pillow`. The first run downloads a ~180MB model, so run it in the background.
6. **Render.** Run `node render.js` (Chrome or Edge, auto-detected). It prints PROBLEMS for missing fonts, bad ids or failed images.
7. **Review.** Read `out/grid-preview.jpg`, fix with `tweaks.js` or theme flips, then re-render single ids and Read the full cover. Rules and common fixes: [references/design-rules.md](references/design-rules.md).
8. **Deliver.** Send `grid-preview.jpg` + one full cover with SendUserFile. Name the output folders: `out/cover` is for upload and `out/grid` is the profile preview. Flag scope if graphics fall outside the client's package. Save client and brand facts to memory.

## End cards (video endings)

When the user wants 3 to 5 second branded endings or outros for the same videos, reuse the cover project's `brand.js`:

1. Copy `template/endings/*` and `brand.js` into `<project>/endings`. Never open the full videos. `ffprobe` one for size and fps only, since the template is 1080x1920 @ 30fps.
2. Fill `endings.js`: one entry per video with an `Up next` title (in series order; the last one shows the follow line), the tagline in the client's own big-idea wording, and a duration of 3 to 5s.
3. Run `node render-endings.js` in the background (~35s per ending). For each ending it writes:
   - `out/<id>_overlay.mov`: ProRes 4444 with alpha. Put it on the track above the video's last seconds; a brand-colour veil dissolves the footage into the card. CapCut and Premiere accept it.
   - `out/<id>.mp4`: H.264 on the solid brand colour, to append after the clip.
4. Check with one ffmpeg strip, not by watching: frames 12/45/120 of the mp4, plus the overlay composited on one frame taken from the last second of a video (`-sseof -1.2`). Read that single image.

Variant `variant: "welcome"` (+ `duration: 5`) suits a series opener or brand intro: it is slower and cinematic. The mark comes into focus, then "WELCOME TO" and the brand name written in script, then a small-caps tagline. Default animation (CSS keyframes, frozen per frame through `window.seek(t)`): veil fades in, a ring draws around the mark, the mark pops, the wordmark tracks in, a rule grows, the script tagline rises, then "Up next".

## Intros (title cards)

Use `template/endings/intro.html` + `intros.js` (1.5 to 4s, default 2.8s) and render with `node render-endings.js --intro` → `out-intros/<id>.mp4` (solid) + `<id>_overlay.mov` (type only, alpha). Sequence: the ring draws, the monogram pops, the episode kicker tracks in, the bold title rises from a mask, the script line writes in, then the rule grows, all with a slow drift.

**First, check how the videos open.** Grab one frame at 0.5s and one at 2.5s from each video into a single strip and Read it once. If the editor already put a title card there (a client sub-brand did: about 2s of plain serif on teal), the intro replaces that card. Do not stack a second title on top of it.

## Files (template/)

| File | Role |
|---|---|
| `brand.js` | fonts, colours (light / dark / full), wordmark, mark SVG, tag pattern |
| `thumbs.js` | one entry per cover |
| `tweaks.js` | per-cover fixes: `l1`/`l2`/`tag` CSS, cutout `h/x/y`, photo `pos/zoom` |
| `index.html` | the layouts (arch + full), driven entirely by the three files above |
| `render.js` | Playwright → `out/cover`, `out/grid`, `out/grid-preview.jpg` |
| `cutout.py` | rembg (isnet-general-use + alpha matting) → `cutouts/<photo>.png` |

## Gotchas
- Windows Git Bash ffmpeg: `drawtext` without `fontfile=` segfaults (fontconfig). The `image2` + `tile` filter breaks on mixed photo sizes, so use hstack/vstack (new-project.js does).
- Playwright ships without a browser here. render.js uses installed Chrome (`CHROME_PATH` overrides it).
- `file://` page + local font files work. If fonts silently fall back, render.js reports it.
- Run Python on downloaded or client files with `-I`.
