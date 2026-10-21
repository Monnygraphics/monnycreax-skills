# Short-Form Video → Lesson Workflow

Turn a downloaded short-form video (TikTok/Reels/Shorts style — talking-head, text overlays, b-roll diagrams, usually under a few minutes) into a structured, keepable lesson document.

## When to Use

- User points at a local video file and asks to "learn from it," "make a lesson out of this," "extract the framework," or "what is this teaching"
- Distinct from a plain summary: a lesson states the reusable idea as a teachable framework and is explicit about what's genuinely taught for free versus what's a teaser for a paid offer — it's meant to be referenced later, not just read once

## Workflow

This builds on the base [SKILL.md](../SKILL.md) steps (resolve path → info → transcribe → extract_frames → Read the frames). Once you've done those and actually have the transcript plus a set of viewed frames in hand:

**Identify what's actually being taught**

Read the transcript in full and look at every distinct on-screen graphic (diagrams, text callouts, lists) across the frames you pulled. Short creator videos often put the *actual reusable content* — an exact prompt, a named framework, a labeled diagram — on screen as text rather than saying it aloud verbatim, so don't rely on the audio track alone. If a frame shows something you can't fully make out (small text, a complex diagram) and it seems important, extract a couple of additional frames tightly around that timestamp:

```bash
python scripts/analyze_video.py extract_frames "<path>" --out-dir "<same temp dir>" --interval 0.5
```
then Read just the ones in the relevant time window — cheaper than re-extracting everything at high density.

**Write the lesson**

Produce markdown — a lesson, not a transcript dump. Use this shape, adapting section names to the content and dropping sections that don't apply (e.g. no worksheet if there's no step-by-step method):

```markdown
# Lesson: <short descriptive title — not the raw caption>

**Source:** <duration>-second short-form video, "<one-line description>"
**Format:** <talking-head / carousel / etc, plus notable visual elements>

## 1. The Core Idea (the hook)
<the attention-grabbing opening line/frame, and the underlying principle it sets up>

## 2. Framework: <name>
<the actual teachable content: steps, categories, a table if there's an enumerated model>

## 3. <Second framework/technique, if the video gives one — e.g. an exact prompt>
<quote exact wording in a code block if the video provides something meant to be reused verbatim — pull the exact wording from the frame(s) that show it on screen, not a paraphrase from the audio transcript>

## 4. Worksheet — copy this and use it today
<a fill-in-the-blank version of the framework, only if the content is genuinely instructional/actionable>

## 5. Scope check
<state plainly whether this is the complete teaching or a teaser gated behind a paid course/waitlist/challenge — don't let the lesson overclaim what the free clip actually covers>

## 6. Takeaway
<one paragraph: the single idea most worth remembering>
```

**Save with a clean filename**

Save next to the source video, named for the idea, not the caption: e.g. source `"never let ai write your stories...mp4"` → `Lesson - The Storytelling Wheel (AI as Excavator not Ghostwriter).md`.

**Deliver the file**

Use `SendUserFile` (`display: "attach"`) to hand over the finished `.md` — the deliverable is the file itself. Still give a short chat summary covering the core idea and framework(s), but don't treat the chat message as a substitute for the file.

## Tips

- Don't overclaim: if the clip is visibly a teaser (waitlist CTA, "I'll teach the rest in my [paid thing]"), the Scope check section should say so directly.
- Burned-in captions and on-screen diagram labels are ground truth for exact wording — prefer them over the audio transcript whenever the two differ, since transcription is the more error-prone path for short/unusual words.
- If the source filename doesn't obviously indicate content, a quick look at the first frame (usually the title-card/hook) confirms you extracted the right file before investing more time.
