---
name: video-analyser
description: Analyse local video files entirely on-device — no external API, no account, no credits, no per-use cost. Wraps ffmpeg (audio + frame extraction) and local faster-whisper (speech-to-text) so Claude builds its own understanding directly, viewing extracted frames with its own vision instead of trusting a third-party captioning model. Use this whenever the user points at a local video file (a download, a screen recording, a meeting clip, a short-form TikTok/Reels/Shorts export) and asks to analyse, summarise, transcribe, describe, extract a lesson or framework from, or otherwise understand its content — even if they don't say "video" explicitly (e.g. "what's this clip about," "learn from this," "make a lesson out of this file," "what is he saying here"). Also use for local audio-only files needing transcription. Do NOT use for videos that only exist as a remote URL with no local file — that needs a different approach since this skill has no upload/fetch step.
---

# Video Analyser

Understand a local video file by extracting what a language model can't get from the file alone — the spoken words and a sampling of visual frames — then reasoning over both directly. No third-party video-understanding API is involved; every step here is your own analysis of local ffmpeg/faster-whisper output.

## Why this shape

Video files aren't directly readable as text or images. The fix is mundane: pull the audio out and transcribe it locally (`faster-whisper`, already installed, fully offline), and pull a handful of representative frames out as JPGs (`ffmpeg`), then use the Read tool on those frames the same way you'd read any screenshot. You are the "video understanding model" here — there's no need to ask another service to describe the video and then trust its description second-hand. That also means there's no ambiguity to resolve between "what the captioning model said" and "what's actually on screen" (a real problem with hosted video-AI APIs) — you're looking at the actual pixels yourself.

## Setup

Nothing to configure. Requires `ffmpeg`/`ffprobe` on PATH and the `faster-whisper` Python package — both already present on this machine. Run everything via:
```bash
python scripts/analyze_video.py <command> [args...]
```

## Step 0: Resolve the file path

Downloaded video filenames (especially from social platforms) are often the entire caption — long, with emoji and smart-quote characters (`"` `"`, U+201C/U+201D) that get mangled if you retype them into a shell command. Resolve the path in Python and pass it programmatically instead of hand-typing it:

```bash
python -c "
import os, subprocess, sys
d = r'<folder, e.g. C:\Users\<user>\Downloads>'
match = next((os.path.join(d, f) for f in os.listdir(d) if '<distinctive lowercase substring>' in f.lower()), None)
result = subprocess.run([sys.executable, 'analyze_video.py', 'info', match], capture_output=True, text=True, encoding='utf-8')
print(result.stdout, result.stderr)
"
```
Set `PYTHONIOENCODING=utf-8` in the environment for these calls — Windows consoles default to cp1252 and crash trying to print emoji that can legitimately appear in filenames or transcripts.

## Step 1: Get your bearings

```bash
python scripts/analyze_video.py info "<path>"
```
Returns duration, resolution, fps. Use the duration to judge how many frames you'll want and roughly how long transcription will take (very roughly real-time-ish on CPU with the default model — a 2-3 min clip takes a couple minutes; for anything long, consider `--model base` for speed).

## Step 2: Transcribe the audio

```bash
python scripts/analyze_video.py transcribe "<path>" --out "<somewhere in temp>.json"
```
Runs local `faster-whisper` (default model `small`, already cached — no download wait). Writing to `--out` rather than stdout keeps a large transcript out of your context until you actually need to read pieces of it; for short clips, printing to stdout directly is fine too. This is the slow part of the pipeline — measured at roughly 3-4x realtime on this machine's CPU with `small` (a 139s clip took ~9 minutes), versus frame extraction which is closer to 1s per output frame. Kick transcription off first and let it run in the background while you do frame extraction/viewing, rather than waiting on it serially. For anything over a few minutes of runtime, drop to `--model base` for roughly 2x the speed at a modest accuracy cost, or just accept the wait via a backgrounded call.

If the video has no meaningful speech (silent b-roll, music-only), segments will come back empty/sparse — that's expected, not an error; lean on frames instead.

## Step 3: Sample frames and actually look at them

```bash
python scripts/analyze_video.py extract_frames "<path>" --max-frames 20
```
Prints a JSON list of `{path, timestamp_seconds}`. **Then call the Read tool on each frame path** — that's the step that actually gives you visual understanding; extraction alone just produces files on disk. Short-form creator videos routinely carry their most important content as burned-in on-screen text (captions, diagram labels, callouts) that audio transcription alone will never surface, and that's often *more* reliable than the spoken track. Read enough frames to catch each distinct on-screen graphic/caption change, not just the first one — 15-25 frames is a reasonable default for a sub-3-minute clip; raise `--max-frames` for longer or visually denser content, lower it if the video is static talking-head with no on-screen text.

Frames land in a temp directory by default (not the source folder) since they're disposable working files, not a deliverable.

## Step 4: Synthesize

You now have a timestamped spoken-word transcript and a set of frames you've actually seen. Cross-reference them yourself — e.g. if the transcript has a word that seems out of place, check whether a nearby frame shows on-screen text that resolves it. Then produce whatever the user actually asked for:

- **General "what is this video about"** → a direct answer/summary in chat.
- **"Extract a lesson" / "what's this teaching" / "make a framework out of this"** → see [references/lesson_extraction.md](references/lesson_extraction.md) for the structured lesson-document workflow.
- **"Transcribe this"** → hand back the transcript, cleaned up (fix obvious mis-hears you caught via the frames, keep timestamps if useful).

## Tips

- Kick off `transcribe` (slow) and `extract_frames` (fast) as parallel tool calls when you know you'll need both — don't serialize them.
- Delete temp frame/audio files when you're done with them if there were a lot of them; they're throwaway.
- If `transcribe` errors on `faster_whisper` import, the package genuinely isn't installed in whatever Python `analyze_video.py` is running under — check with `python -c "import faster_whisper"` before assuming it's a code bug.
