# Brand colour gate

Brand colours are the **one question this skill must ask**. Ask them before planning any graphics, and do not
render before the user answers.

## 1. Look for colours first
Check these, in order, before asking:
1. The footage folder: `brand/`, `logo*`, `*kit*`, `*.svg`, `*.ase`, `brand.json`, or a PDF brand guide.
   Run `node ~/.claude/skills/reel-editor/modules/reel-covers/scripts/brand-from-svg.js <kit folder>` on an SVG kit to get swatches.
2. Memory and the project's `CLAUDE.md`. Save each client's palette to memory once, so later reels reuse it.
3. An existing `brand.js` from a `reel-covers` project for the same client. Reuse it so thumbnails, intros,
   outros, carousels and the reel all match.

## 2. Ask
Always ask, even when you found colours, so the user can confirm. Use AskUserQuestion with:
- "Use these brand colours: <swatches found>" (when found)
- "I'll send my own hex codes"
- "Pick colours for me from the video" (runs step 3 and comes back for approval)

## 3. When the user has no colours: derive them, then ask again
Only after reading the transcript:
1. **Understand the video.** Note the topic, emotional tone (reflective, bold, warm, urgent), audience and
   region, and the speaker's wardrobe and set colours. Grab 2-3 frames from `cut.mp4` and Read them, because
   the accent must not clash with the outfit or the background.
2. **Research.** Look at how the speaker's niche presents itself (2-3 accounts or sites in the same space via
   `agent-reach` or web search), plus the client's own Instagram or site if one exists.
3. **Use the `web-design` skill** for the colour reasoning: its design read and its palette data
   (`ui-ux-pro-max` palettes, the DESIGN.md brand library) to pick a palette that matches the tone and
   industry. Follow the user's feedback memory: no cream + Garamond "Claude site" look. Prefer rich, cinematic
   accents.
4. **Propose 2-3 palettes** in the edit.json brand shape, each with a one-line reason tied to the transcript,
   and show one preview strip per palette (`reel_edit.py preview ... --override '{"brand":{...}}'`).
5. **Ask the user to pick one.** Only then go on to render.

## 4. What `edit.json` needs
```json
"brand": {
  "accent":    "#7A1414",   // wipes, pills, title band, rings: the colour of the video
  "accent2":   "#2A0606",   // deeper shade, used for depth
  "highlight": "#E3262E",   // boxcaps active-word box (defaults to accent)
  "pop":       "#2FA89E",   // small loud accent: hook underline, tag dot, hormozi active word
  "label": "Archivo",       // tracked-caps labels (hook bar, pillar tag); defaults to sans
  "ink":       "#FFFFFF",   // text on accent
  "paper":     "#EFEDE8",   // light text cards
  "dark":      "#120505",   // dark text cards
  "sans": "Inter", "serif": "Fraunces", "display": "Montserrat"   // Google Fonts names
}
```
Contrast checks: white captions need the bottom gradient. An accent used as a pill behind white text needs a
contrast ratio of at least 4.5:1 with white. Gold and yellow accents (`bigword`, `ghost`) are used as text
colour on dark backgrounds instead.

For a series, keep one palette and rotate which brand colour is the `accent` per video (see style-spec §9).
