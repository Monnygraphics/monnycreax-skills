# Batch mode, covers and credits: details

Loaded on demand from SKILL.md steps 7 and Batch.

## Thumbnail / cover frames
Use the photoshoot if there is one. Otherwise pick frames from the video with
`~/.face-venv/Scripts/python scripts/best_frames.py <video> --out <dir> --top 6`. It uses MediaPipe face
landmarks and ranks frames for open eyes, fully closed lips, a soft closed-lip smile and sharpness (setup is in
the docstring). Then **look at every candidate** on a face-crop sheet (crop each frame to its `box`) and choose by
eye: the scores are a shortlist, not the decision.

Reject:
- parted lips (they show teeth and any tooth gap, which clients notice)
- mid-word mouths
- lowered or half-closed eyes
- hands across the face

With no clean candidate, re-run with `--every 0.33 --top 12`. Don't use `$P stills`: it picks by sharpness only,
and the covers it chose for Client A had mid-word mouths and blinks (client feedback, Oct 2026).
Motion intro: `render-endings.js --intro` → `<id>_overlay.mov`, set `"intro_overlay"` and `"title": null` (one
title only, or they stack). Outro: `render-endings.js` → `<id>.mp4`, set `"endcard"`.

## Batch mode (many reels, unattended / overnight)
After the clip map and one reference reel the user has seen, write `batch.json` in the work folder (`%LOCALAPPDATA%/claude-work/reel-editor/<footage-folder>/`, set `"deliver"` to the footage folder) (format in
the `scripts/batch.py` docstring; worked example: the Client A batch, Oct 2026). Give each reel:
- its source clip, pillar and written hook
- 1-2 pull-quote cards **as phrases** (times are found on the cut transcript, so they survive re-cuts)
- emphasis words, word `fix`es for known mishearings, and `exclude` ranges for slips

Run it in the background with two workers on a 16-thread machine:
`python scripts/batch.py batch.json --worker 0 --workers 2` (and `--worker 1`). Each reel writes `final.mp4`,
`preview.jpg`, `check.jpg` and a line in `batch-log.jsonl`. One failure never stops the batch. Every clip gets
the voice-polish check (`"audio": "force" | "off"` per reel).

Batch features (all optional):
- **Hook in her own words** (default `hook: "auto"`): the speaker's opening sentence, with the captions hidden
  underneath.
- **`intro`** `{logo, end}`: the logo pops in at the top with the pillar as a kicker for ~3s.
- **`outro`** `{logo, hold, follow}`: `cut --hold` freezes the last frame. An accent wipe reveals the logo lockup,
  then "Up next" with the next reel's opening line, then a follow pill. Music swells +9 dB.
- **`broll`** `{phrase, src}`, placed on the spoken phrase. Sources:
  - **Pexels** (free licence; search pages carry `__NEXT_DATA__`)
  - the client's own images
  - connected image tools

  Never Pinterest (no licence). Check a contact sheet for tone before rendering.
- **Music per pillar** (`music` list rotates, `music_lufs` -33, -40 for grief). Pixabay Music is the free source.
- **`sfx`** `{file, card_file, db, card_db}` from the user's own library. Measure peaks; sit under the voice.

In the morning:
1. Read `batch-log.jsonl` and every `check.jpg`.
2. Grep the cut transcripts for words a client would not say.
3. Fix with `--only <id>` after deleting that reel's `final.mp4`.

Keep the machine awake (`request_keep_awake`) and send a phone notification when done.

## Other platforms
`$P export <final.mp4> --aspect 4:5` (`--y` sets the crop), `1:1`, or `16:9` (vertical on a blurred fill). For
real long-form YouTube, re-run `cut` with `--max-pause 0.6`.

## Credits and what was not taken
- **Ideas from:**
  - browser-use/video-use (MIT; needs a paid ElevenLabs key)
  - tenfoldmarc/video-edit-skill (no licence: ideas only)
  - 6missedcalls/video-editing-skill (MIT)
  - Attention Machine (PolyForm Internal Use: ideas only, our own code)
  - gbro-collage-broll (MIT look; its paid Gemini pipeline not used)
  - OneTake (MIT; its review idea)
- **Not included:** the person cutout that puts words behind the head (per-frame matting: hours on this CPU).
