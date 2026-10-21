# Colour grading

Applied to the base video in render pass 1 and in `preview`, so the preview shows the grade. B-roll stills and
overlay graphics are not graded.

## Workflow (one extra command, ~40s)
1. `$P color <dir> --apply --look <look> --compare all` reads 8 frames of `cut.mp4`, writes the correction plus the
   look into `edit.json` `grade`, and makes `looks.jpg`: original, corrected and every look on one frame.
   Read the sheet once and pick the look by eye. `--at <s>` picks the frame; `--strength 0.7` previews looks at 70%.
2. Change the look in `edit.json` and confirm in the normal `preview` round. Don't send looks.jpg unless the
   client is choosing a look (then it is the one image you send them).
3. Same camera and room across a series: grade once and put `grade` in the series/batch `defaults`.

## edit.json `grade`
A look name (`"warm"`), a raw ffmpeg chain, or a dict:

```json
"grade": {"wb": [0.99, 1, 0.98], "gamma": 1.05, "levels": [0.03, 0.97],
          "temp": 0.2, "tint": 0, "contrast": 1.04, "saturation": 1.0, "vibrance": 0.08,
          "look": "skin", "strength": 0.8, "lut": "D:/luts/client.cube", "vignette": false}
```

| Key | What it does | Range |
|---|---|---|
| `wb` | white balance gains R,G,B (from `color`) | 0.92-1.08 |
| `gamma` | exposure of mid-tones: >1 brighter | 0.85-1.25 |
| `levels` | black and white point | `[0-0.07, 0.88-1]` |
| `temp` / `tint` | + warmer / cooler; + magenta / green | -1 to 1, use ±0.1-0.4 |
| `contrast`, `saturation`, `brightness` | ffmpeg `eq` | 0.9-1.15 |
| `vibrance` | boosts muted colours more than strong ones (safer on skin than saturation) | 0-0.2 |
| `look` | a preset below | |
| `lut` | a `.cube` file (client or camera LUT); replaces `look` | |
| `strength` | how much of the look/LUT to mix in | 0-1 |
| `vignette` | soft dark corners | bool |

Corrections run first, then the look at `strength`.

## Looks
| Look | Use |
|---|---|
| `neutral` | a light lift, safe anywhere |
| `skin` | **default for Black/African clients**: warm mids, open shadows, highlight roll-off against shine |
| `warm`, `golden` | coaching, faith, lifestyle; golden is sunset-warm |
| `bright` | airy, clean teaching reels in pale rooms |
| `soft` | gentle, low contrast; grief, prayer, reflective |
| `film` | soft-glass pack (teal shadows, warm highlights, lifted blacks, vignette) |
| `cinematic`, `teal-orange` | stylised, premium; teal-orange pushes dark navy suits blue, so check |
| `moody`, `punchy` | dramatic or high-energy; punchy suits hormozi |
| `mono` | black and white, for a quote or a single section only |

## Rules
- Skin first: judge the grade on the face. Never let dark skin go grey, green or ashy, or crush to black.
  Lower `strength` before you swap looks.
- Correct before styling: a lamp-orange or window-blue cast is `wb`/`temp`, not a look.
- `color` stays gentle on purpose (all values clamped). If the footage is badly off, set the values by hand
  and check them on a `preview`.
- Mixed cameras or rooms in one reel: grade each source before `assemble` (`ffmpeg -vf "<chain>"`, the chain
  printed by `python -c "import reel_edit as R; print(R.grade_chain({'grade': {...}}))"`), then use a single look.
