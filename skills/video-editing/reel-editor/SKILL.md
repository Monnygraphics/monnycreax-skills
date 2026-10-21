---
name: reel-editor
description: "Raw talking-head footage → finished branded 9:16 reels: auto-detects retakes, slates and stumbles, cuts into quiet, repairs bad audio, colour grading (auto-correct, 13 looks, LUTs), 5 Olympian-named styles (Apollo signature, Athena explainer glass, Hermes story, Ares high-energy, Hestia calm captions) with variants, b-roll, music, covers. Modules: clip a long video into shorts, study/analyse a reference video, covers and thumbnails. Only asks brand colours."
---

# Reel Editor

Folder of raw takes → `final.mp4` per video in a branded style, plus thumbnail, intro, outro and carousel.
You are the editor: the scripts only execute an `edit.json` you write after reading the transcript.
The base style is [references/style-spec.md](references/style-spec.md). Read it before planning a first reel.

```
P = python "~/.claude/skills/reel-editor/scripts/reel_edit.py"
```
Set `PYTHONIOENCODING=utf-8` for every call.

## Output rule: the user's folder gets the finished video and nothing else (user request, Oct 2026)
- **All working files go in the hidden work folder.** `$P work <video>` prints it
  (`%LOCALAPPDATA%\claude-work\reel-editor\<footage-folder>\<video>\`). Use that as `<dir>` for every step:
  transcripts, cut, edit.json, previews, check sheets, project.md, phone copies and logs. Scratch frames go
  in the session scratchpad.
- **Never create `reel-edit/` or any other file or folder in the footage folder** (or Downloads, or the Desktop).
- **When the reel passes the self-check:** `$P deliver <dir> --to <footage folder> --name "<Client> - <Topic>"`.
  That copies ONE file, the full-quality `final.mp4`, under a human name. Send that file.
- Thumbnail, cover, carousel and other aspect ratios are **only made when the user asks**, and each is
  delivered the same way: one finished file per asset (a PNG, a PDF) and no source folders.
- Don't mention the work folder, previews or intermediate files in the hand-off unless the user asks.

## Fast path (time and tokens, measured Oct 2026)
A 2-minute reel took ~30 min (render 15 of it). With `prep`, auto-cut and the faster render it is ~10-15 min.
- **Start from `project.md`** (client decisions, brand, rules) instead of re-deriving them. Update it at the end.
- **Read the transcript with `$P transcript <words.json>`** (one line per sentence, pauses marked; half the
  tokens of a word dump). Ask `$P timeline` for exact times only where an edit needs them.
- **One preview round** of 6-12 moments, then render. Check with `$P check` (light 8-across sheets, about 2.5k tokens
  each, versus about 4k before).
- **Render runs itself in the background** (overlay: 8 Chrome processes; glass blur only inside panel ranges at
  quarter size). Work on the cover or carousel meanwhile; don't poll.
- **Many reels: batch mode overnight** ([references/batch-and-covers.md](references/batch-and-covers.md)). It is
  the biggest saver: 30 reels in one run.
- Load a reference file only when its step needs it. Don't read big images you don't act on.

## Series of 3+ reels: use series mode first
Read [references/series-mode.md](references/series-mode.md). One `batch.json` holds the brand, ONE music bed, the SFX
kit (`series.py kit`), intro/outro cards, max 3 b-roll photos per reel (`series.py broll`, unique across the series)
and paper points pages; each reel is ~15 lines of phrases. Hand-editing a single reel cost ~200k tokens (Client B V1);
don't do it for a series.

## Workflow (track as the task list)

### 1. Get the footage
Local folder as is; Drive link via the Google Drive connector into `<scratchpad>/footage/`; IG/TikTok/YouTube
via `yt-dlp` into a new empty folder. Run `$P scan <folder>`. **Read the client's own rules first** (handover
pack, video guide, memory): they override this skill's house style. Keep `project.md` in the work folder
(`$P work`, one level up from the video dir).

### 1b. Map the clips
Transcribe everything, then build a table in `project.md`: clip, length, topic, pillar, take quality, and which
reel it belongs to. Several takes → keep the last complete clean take per line. One message across clips → a
spec `[{"src","start","end"}...]` and `$P assemble spec.json --out <dir>/joined.mp4` (words remapped).

### 2. Prep: one command, in the background (transcribe, voice check, auto-cut, cut)
`$P prep <video> [--mix sw --vocab "names"] [--exclude "a-b"] [--hold 3.8]` does the mechanical half alone:
- **Work folder and transcript:** creates the hidden work dir and transcribes (kept if a transcript already exists).
- **Voice polish:** runs only when the audio measures bad; cuts are still decided on the original.
- **Auto-cut** from the transcript: slates, takes rejected out loud, retakes (keeps the more complete take),
  false starts, self-corrections ("it's simple, no, …"), crew asides and stutters.
- **Cut:** joins in the middle of real quiet, 80 ms J-cuts, numbers as digits.

It prints the cut transcript (about 1 page) plus `check` items. Tested on 17 real clips (Client A, Client B), it
matched every hand-made retake and slate cut with zero false cuts. Kenyan English + Swahili/Sheng: `--mix sw`.
Thresholds: [references/audio-and-cuts.md](references/audio-and-cuts.md).

### 3. Brand colours: the one required question
Follow [references/brand-colours.md](references/brand-colours.md): check memory and `project.md`, then **ask**.
With none, propose 2-3 palettes via `web-design` and wait for the pick.

### 4. Read the cut once, fix by text (don't skip; client feedback, Client A, Oct 2026)
Read the printed cut transcript for meaning: slips, wrong words, mishearings, a weak opening, more than one call to
action. Fix by **editing text, not timestamps**:
- `$P transcript <dir>/words.json --edit <dir>/kept.txt`, then delete words in `kept.txt` (Edit tool) and correct
  misheard spellings (they become caption fixes).
- `$P cut <video> --words <dir>/words.json --out <dir> --text <dir>/kept.txt --jcut 0.08 [--audio-from <polished>]`
  re-cuts with the auto-cuts plus your text edits.
- A client who wants to check the cut themselves gets `$P review <raw> --words ... --serve`. Their
  "Copy for Claude" JSON goes into `cut --review r.json` (cuts and caption fixes in one step).

Accept or reject each `check` item by meaning: a deliberate refrain stays. Hook first; exactly one call to action,
at the end. Note decisions in `project.md`.

### Autonomy (Monny, 2026-10-20): confirm once per client
- **New client or new style:** show one short plan (clips, style, colours, cuts) and wait for a yes.
- **After that:** prep, cut, plan, render, check and deliver without stopping. Report decisions in a few lines after
  delivery.
- **Stop only for** the brand-colour question, or something the client's rules forbid.

### 5. Plan `edit.json`
`$P plan <dir> --template <T> --transition <hex|wave|disc|blinds|arc|dissolve|flash>` drafts punch-ins at every
jump cut and every ~6s. Then fill it by hand: `brand`, `emphasis` (1 word per sentence max), `broll`
(`{start,end,src,layout: full|card|circle|split|ref|collage}`, every 15-40s, on the exact phrase), `cards` (0-2),
`punchins`, `hook`, `tag`, `grade` (run `$P color <dir> --apply --look skin --compare all` first and pick from
`looks.jpg`; see [colour-grading.md](references/colour-grading.md)), `sfx` (off for grief/prayer), `music` (never download without asking),
`captions.box` (soft backing on pale walls).

**Five styles, each with an Olympian name (Monny, 2026-10-21; max 5, he found 11 too many).** Use the god's name with
Monny: `plan --template <god> [--variant <v>]`. Older names (atelier, artemis, zeus, glass, pill...) still resolve.

| Style | Use | Variants (engine) | Reference |
|---|---|---|---|
| **Apollo**: Monny's signature, the default for premium reels | expensive-minimal talks, event recaps, launches: soft-glass headlines + glass captions, dark glass speaker cards, video b-roll, -37 LUFS bed. **Theme colours open per client** | default · `quiet` (captions off: calm, reflective, the old soft glass) | [apollo-style.md](references/apollo-style.md), glass-style.md § Soft glass |
| **Athena** | teaching, explainers, offers: headlines, icon chips, frosted panels over a blurred background | (`glass`, Nyandi) | [glass-style.md](references/glass-style.md) |
| **Hermes** | case studies and third-person testimonies: illustrated scenes, calendar chapters, counters | (`story`, Dane) | [story-style.md](references/story-style.md) |
| **Ares** | bold, high-energy business/motivation | default (`hormozi`) · `bigword` (one huge word) · `boxcaps` (uppercase blocks) | style-spec.md |
| **Hestia** | calm coach/speaker captions; grief and prayer | default (`pill`) · `ghost` (barely there) · `serif` (`serifmix`) | style-spec.md |

**Collage** is a b-roll layout (`layout: "collage"`) usable inside any style, for one or two "idea" lines:
[collage-broll.md](references/collage-broll.md).

Offer Athena or Hermes as an alternative version when they fit. **Only real things on screen:** panel rows,
counters and stats come from the speaker's words or the client, never invented. **B-roll and music sources:** the folder's
`broll/` first, then the shared library `~/ASSETS` (search `~/ASSETS/library-index.csv` by tag; skip files whose
`used_by` already names this client), then Pexels/Pixabay, then a connected image tool. **Every new download goes into
`~/ASSETS/BROLL|MUSIC|IMAGES|~/ASSETS/BROLL|MUSIC|IMAGES|~/ASSETS/BROLL|MUSIC|IMAGES` as `<source>-<id>_<description>.<ext>`, with a row in the index** (Monny, 2026-10-21:
saves tokens and re-downloads). With none of those, write `broll-prompts.md`. No
readable text, watermarks or identifiable non-client people.

### 6. Preview
`$P preview <dir> --at <6-12 moments>`, then Read `preview.jpg`. Fix here, before the render. Try a look
without editing the file: `--override '{"template":"ghost"}'`.

### 7. Thumbnail, intro, outro (reel-covers): only when the user asks
Skip this step unless the user asked for a cover, intro or outro. When they did, follow `modules/reel-covers/MODULE.md` with the same brand. Cover frames: `best_frames.py`, then **choose by eye** (no parted
lips, mid-word mouths, half-closed eyes or hands on the face). Intro, outro and details:
[references/batch-and-covers.md](references/batch-and-covers.md).

### 8. Render (background)
`$P render <dir>`. The overlay is drawn by 8 parallel Chrome processes (50s reel: 201s → 73s). The glass blur
runs only inside panel ranges (2-min glass reel: 924s → 283s total). Use `--reuse-frames` after changing only
punch-ins, music, intro or end card.

### 9. Self-check before showing anything
`$P check <dir>` makes the sheets itself: 2 frames either side of every cut, each overlay's in, middle and out,
and the first and last second. Read every sheet; only claim what was on one. Look for:
- an unhidden jump cut, or a frame of the old clip flashing at a cut
- captions over the face, or below y≈1470
- a failed font (Times appearing), or black in a wipe
- a graphic over the eyes or mouth
- a headline and a caption showing the same words (use `bigwords`)

`ffprobe` the frame count: it must equal duration × fps, with A/V lengths matching. After 3 fix passes, report
what's still wrong.

### 10. Carousel and other platforms: only when the user asks
Carousel: the `linkedin` skill's `li-carousel` module, same brand, 1080x1350, `humanizer` on the copy. Other aspects:
`$P export <final.mp4> --aspect 4:5|1:1|16:9`.

### 11. Hand-off
`$P deliver <dir> --to <footage folder> --name "<Client> - <Topic>"`, then SendUserFile that one delivered file
(render). No phone copy, previews or extra files unless asked. In a few lines, say what was cut and anything
to listen to. Flag graphics outside a video retainer. Update `project.md` (work folder) and memory.
**Never upload to Google Drive on your own** (the user asked, Oct 2026): don't offer it or start it as a next step,
and don't do it in batch mode. Only when the user asks for that specific upload, use the `drive-upload` skill
(rclone, full 1080p, any size). The Drive connector and browser upload cap files at about 10 MB (a 720p preview).

## Files
| File | Role |
|---|---|
| `scripts/reel_edit.py` | prep, scan, transcribe, transcript (--edit), audio, review, cut (--text/--review/auto), assemble, plan, vbroll (video b-roll into the cut), color, preview, render, check, deliver, strip, stills, timeline, export |
| `scripts/autocut.py` | retake/slate/stumble detection and edit-by-text alignment (no dependencies) |
| `scripts/batch.py` | batch mode (see batch-and-covers.md) |
| `scripts/audio_polish.py` | voice diagnosis + conditional repair (`~/.audio-venv`; `$P audio` wraps it) |
| `scripts/collage.py` | halftone collage pieces (`~/.rembg-venv`) |
| `scripts/best_frames.py` | cover frame shortlist (`~/.face-venv`) |
| `scripts/overlay/overlay.html`, `render-overlay.js` | all templates and packs, drawn per frame by `seek(t)`; parallel PNG renderer |
| `scripts/review/review.html`, `serve.js` | transcript review page and its range-capable server |
| `references/*.md` | style-spec, brand-colours, colour-grading, glass-style, story-style, collage-broll, audio-and-cuts, batch-and-covers |

## Gotchas (verified on this machine, Oct 2026)
- No `zoompan`, and never mix the punch-in split/trim/concat graph with the PNG overlay input: both drop frames.
  Render is two passes (`base.mp4`, then overlay). Keep it.
- Every overlay PNG keeps alpha (`#stage` leaves pixel 0,0 transparent); rgb24/rgba flips drop frames.
- Fonts load from Google Fonts at render (needs internet); `fonts failed` means a fallback. Use exact family names.
- iPhone `.mov` has a second, undecodable audio track; everything reads `0:a:0`. 4K is downsized once at `cut`.
- Burned-in captions in a source will clash: blur or crop them, or ask for the clean export.
- The source is never touched. The work folder can be cleared once the user is happy with the reel.

## Modules (merged 2026-10-20)
Read `modules/<name>/MODULE.md` only for the task at hand; paths inside a module are relative to its own folder.

| Module | What it covers |
|---|---|
| `video-clipper` | Turn one long local video (talk, podcast, sermon, webinar, interview — roughly 10 minutes to a few hours) into 3-10 short vertical clips ready for Tik... |
| `video-analyser` | Analyse local video files entirely on-device — no external API, no account, no credits, no per-use cost. Wraps ffmpeg (audio + frame extraction) and l... |
| `reel-covers` | Designs and renders branded Instagram Reel / TikTok / Shorts cover thumbnails from a client's photoshoot, video titles and brand kit. It outputs 1080x... |
| `video-content-strategist` | Use when planning video content strategy, writing video scripts, optimizing YouTube channels, building short-form video pipelines (Reels, TikTok, Shor... |
| `demo-video` | Use when the user asks to create a demo video, product walkthrough, feature showcase, animated presentation, marketing video, or GIF from screenshots ... |
