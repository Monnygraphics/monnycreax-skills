---
name: video-clipper
description: Turn one long local video (talk, podcast, sermon, webinar, interview — roughly 10 minutes to a few hours) into 3-10 short vertical clips ready for TikTok/Reels/Shorts. Local-first and free: faster-whisper transcribes, then Claude itself reads the transcript and judges which moments are hook-driven and self-contained enough to trend — no OpenAI/Gemini/MuAPI call, no per-clip cost, no watermark. Optionally accelerates the full-video transcript pass with Groq's hosted Whisper (~$0.04-0.11/hour of audio, needs the user's own GROQ_API_KEY) since this machine has no GPU and local CPU transcription of a full hour is slow. ffmpeg then cuts each pick, reframes it to 9:16 (blurred-background pad, nothing cropped out), and burns in captions transcribed fresh from just that clip for accuracy. Use whenever the user wants to turn a long recording into short clips, asks for "viral clips," "shorts from this," "clip this video," an Opus Clip-style workflow, or the best moments pulled out of a long video for social media — without watching the whole thing themselves. Do NOT use for a single manual trim/export where the user already gives an exact timestamp, or for a video that exists only as a remote URL with no local file (pair with a downloader first).
---

# Video Clipper

Turn a long local video into short, trend-ready social clips — Claude does the "which moments are worth clipping" judgment call directly by reading the transcript, the same way a human editor would skim a script. There is no external highlight-detection API anywhere in this pipeline.

## Why this shape

- **Claude is the AI, not a paid API.** Every "opus-clip-alternative" project calls out to OpenAI/Gemini for moment-detection, or ships a much weaker heuristic (audio energy, scene changes). You're already running this session — read the transcript and pick moments directly, at no incremental cost and no key to manage.
- **Two transcription passes, different jobs.** Full-hour accuracy is too slow on CPU (this machine has no CUDA device — confirmed via `ctranslate2.get_cuda_device_count()` — so everything runs on CPU int8). The `small` model runs ~4x realtime, meaning a 60-minute video would take ~4 hours. So: pass 1 transcribes the *whole* video fast and rough (`tiny` model) purely so Claude can find good moments and rough in/out points; pass 2 (inside `render`, automatic) re-transcribes *only* the selected clip's own short audio range at higher accuracy for the captions that actually get burned in. The slow, accurate model only ever touches a few minutes of audio total, never the full hour.
- **Vertical reframe never crops content out.** Default is a blurred, scaled copy of the frame filling the 9:16 canvas behind a full, uncropped copy of the original — not a center-crop that could cut off a speaker who moves around. Pass `--no-vertical` to skip reframing (e.g. source is already vertical).
- **Caption styling is empirically verified, not guessed.** `FontSize=16` with no `original_size` override on the `subtitles` filter renders correctly at 1080x1920 on this ffmpeg build — an earlier attempt at explicit `original_size=1080x1920` badly over-scaled and mispositioned the text (tested via a hand-crafted SRT + frame extraction). Don't reintroduce `original_size` without re-verifying the same way.

## Setup

`ffmpeg`/`ffprobe`, `faster-whisper`, and `requests` are already present (same local dependencies as the `video-analyser` skill). This machine has no GPU (confirmed: `nvidia-smi` absent, 0 CUDA devices via ctranslate2), so local Whisper runs CPU int8 — fine for short clips, too slow for a full long video (see Step 1).

**Optional but recommended: Groq API key**, for the full-video rough pass. Groq hosts Whisper on inference hardware built for speed — a full hour transcribes in well under a minute instead of hours on local CPU — at ~$0.04/hour of audio (`whisper-large-v3-turbo`). This is the one part of the pipeline where cloud is worth it; clip *selection* stays Claude (free, no API), and rendering stays local ffmpeg (free) either way. If `GROQ_API_KEY` isn't set, everything still works via the local `tiny`-model fallback, just slower.

To set up: the user creates their own key at https://console.groq.com/keys (account creation isn't something to do on their behalf), then sets it for this machine, e.g. in PowerShell: `[Environment]::SetEnvironmentVariable("GROQ_API_KEY", "gsk_...", "User")` (persists across sessions) or `$env:GROQ_API_KEY = "gsk_..."` (current session only). Worth a one-line heads-up that clip audio leaves the machine for this step — a non-issue for content headed to public social media, worth a beat of thought for anything sensitive.

## Step 0: Resolve the file path and get your bearings

Same caution as `video-analyser`: resolve messy downloaded filenames in Python rather than hand-typing them (long captions-as-filenames, smart quotes, emoji). Then check duration:
```bash
python "~/.claude/skills/reel-editor/modules/video-analyser/scripts/analyze_video.py" info "<path>"
```
Use the duration to set expectations with the user up front — roughly how long the rough transcription pass will take (see Step 1).

## Step 1: Rough full-video transcript (fast pass)

If `GROQ_API_KEY` is set (check with `echo $env:GROQ_API_KEY` or just try it and see if it errors), prefer the cloud pass — dramatically faster, trivial cost:
```bash
python "~/.claude/skills/reel-editor/modules/video-clipper/scripts/clip_video.py" transcribe_groq "<path>" --out "<temp>.json"
```
Otherwise fall back to local:
```bash
python "~/.claude/skills/reel-editor/modules/video-analyser/scripts/analyze_video.py" transcribe "<path>" --model tiny --out "<temp>.json"
```
Run the local fallback with `run_in_background` for anything over ~10 minutes of source — it's still slower than instant even at `tiny`, and there's nothing else in this pipeline to parallelize it against (unlike `video-analyser`, there's no frame-extraction step here). Tell the user roughly what to expect time-wise before kicking it off rather than going quiet for a long stretch.

This transcript only needs to be good enough to *find* moments and rough in/out points — it is not what gets burned into the final captions (that's Step 3's fresh per-clip pass, local by default regardless — short clips are already fast on CPU, so cloud mainly buys accuracy there via `--caption-engine groq`, not speed).

## Step 2: Pick the clips

Read the transcript JSON. Select **3-10 segments** — let the actual material set the count; don't pad to hit 10 if only four moments are genuinely strong, and don't cap at 3 if eight are great. For each candidate, apply real editorial judgment:

- **Hook in the first 1-2 sentences** — a question, a bold claim, a surprising number, something that stops a scroll.
- **Self-contained** — makes sense with zero context from earlier in the video; no dangling "like I said" or pronouns pointing outside the clip.
- **A real payoff** — lands somewhere (an insight, a punchline, a turn), doesn't just trail off.
- **Clean boundaries** — start at the beginning of a sentence/thought, end after a complete one, not mid-word. Add ~0.5-1s buffer on each side (the rough transcript's timestamps are approximate).
- **Reasonable length** — most social clips land best under ~90s; allow longer only if the payoff genuinely needs it.
- **Spread across the source** and non-overlapping — don't pick five moments from the same five minutes if the rest of the hour has material too.

For each pick, note: start/end seconds, a one-line suggested hook/title, and a one-line reason it could land. Share this list with the user as you go — not a blocking approval gate, render straight through unless something looks genuinely off or the user has said they want to review picks first.

## Step 3: Render each pick

```bash
python "~/.claude/skills/reel-editor/modules/video-clipper/scripts/clip_video.py" render "<source_video>" --start <sec> --end <sec> --out "<video_dir>\clips\clip_01_<slug>.mp4"
```
One call per clip. Each call re-transcribes just that clip's own audio (default `base` model — bump to `--caption-model small` if the source audio is noisy/accented, or add `--caption-engine groq` to use Groq's `whisper-large-v3` instead) for accurate burned-in captions, reframes to 9:16, and encodes the final mp4. Defaults are vertical + captions on; pass `--no-vertical` or `--no-captions` to drop either. If a clip's audio range is silence/music, `captions_burned` comes back `false` automatically — that's an expected fallback, not an error.

Number outputs in the order you'd recommend posting them, and slug the filename from the hook (e.g. `clip_01_why-most-founders-quit.mp4`) so filenames are self-describing in a folder of 10.

## Step 4: Hand back the results

List what got made: filename, duration, hook, and why it was picked — plus where the files landed. If the user wants adjustments (different in/out point, drop a pick, different caption model), that's a fast re-render of just that one clip via `render`, not a full re-run of Steps 1-2.

## Tips

- `render`'s JSON output includes `caption_error` if the precision transcription pass hit a problem — the clip still gets cut (falls back to no captions) rather than failing outright, but worth surfacing to the user if it happens.
- Very quiet/distant-mic source audio benefits from `--caption-model small` on the render step even though it's slower — worth it since captions are burned in permanently and can't be fixed after the fact without a re-render.
- Delete files in `clips/` only if the user says so — unlike temp frames in `video-analyser`, these are the deliverable, not scratch output.
