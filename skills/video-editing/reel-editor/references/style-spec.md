# Reel editing style spec

The house style for this skill. It comes from studying five Prisca Ndifor reels (Oct 2026): seated talking head,
2-3 minutes, reflective topics. All five follow one system, and each video gets its own caption template and
accent colour. Hand this file to a human editor as the brief. `edit.json` is the same spec in machine-readable form.

## 1. Format
- One locked-off medium shot (head to lap, hands visible) for the whole video. No second angle.
- 1080x1920, 30fps. Source in 4K if possible so punch-ins stay sharp.
- Speaking pace is about 125-150 wpm. The edit keeps a slow, calm talk moving. It must never feel frantic.
- A dark gradient fades up from the bottom (0% to 30% of the height) and sits behind every caption.

## 2. Cuts
- Remove every pause longer than **~0.32s**. Silences of 400ms or more are always safe to cut. Cuts between
  150 and 400ms land on phrase boundaries. Never cut a gap shorter than 150ms (you would cut mid-word).
- Pad cut boundaries: 60ms before a word, 120ms after it, with a 12-15ms audio fade at every cut so nothing pops.
- Cut filler words (um, uh, erm) and false starts. When a line was said twice, keep the **last clean take**.
- **Every jump cut changes the framing** (see 3). A visible jump cut on the same framing is the one thing
  this style never shows.

## 3. Zoom in / zoom out (punch-ins)
- There are two framings: **wide (1.0)** and **tight (1.12-1.20, default 1.16)**. The crop is biased upward
  (y bias 0.32) so the face stays in the upper third.
- A framing change is a **hard cut on a sentence or jump-cut boundary**, never a slow animated zoom.
- Use the tight frame for the emotional or important line. Hold it for 2-6s, then go back to wide.
- No framing should hold longer than ~6-7s. On long unbroken takes, change framing at breath points.
- B-roll stills always get a slow push-in (Ken Burns): scale 1.03 to 1.10 over their time on screen.

## 4. Transitions: accent-colour shape wipes
- **Duration 0.45s** (about 13 frames), easeInOutCubic.
- The accent shape leads and the incoming content follows inside it about 0.1s behind. The accent shows as a
  moving rim, never a flat flash. Going out is the same move in reverse.
- Captions stay on screen through the wipe, which makes the change feel continuous.
- Use one transition type per video, matched to its template:

| Transition | Move | Pairs with |
|---|---|---|
| `hex` | hexagon grows in from the right edge and sweeps across | `pill` |
| `wave` | sine-edged band rises from the bottom | `ghost` |
| `disc` | disc grows from the bottom-right corner, with thin accent rings left on screen | `bigword` |
| `blinds` | 5 staggered horizontal bars slide in from the right | `boxcaps` |
| `arc` | ellipse drops from the top (pair with `split` b-roll so the speaker stays in the lower half) | `serifmix` |

- Transitions happen only at b-roll and text-card entries and exits, about every 15-40s. Do not add transitions
  between talking-head cuts.

## 5. Captions: the 5 templates
Shared rules:
- Words appear in sync with speech. Show **1-5 words** per chunk (max ~24 characters) on 1-2 lines, and break
  chunks at punctuation and at pauses longer than 0.6s.
- The **active word is highlighted**. Each word pops in from 86% to 100% scale over 0.12s.
- Position: lower-middle. The top of the caption block sits at ~64% of the height (y ≈ 1230px), over the chest,
  never over the face.
- Keep everything inside the **Instagram safe zone**: top 220px clear, nothing below y = 1470, 35px side
  margins, and the right 100px clear from y ≈ 1155 down (like/comment icons).
- One emphasis word per sentence at most. Pick the emotional noun or verb ("identity", "heartbreak", "gift").

| Template | Font | Look | Active word | Emphasis |
|---|---|---|---|---|
| `pill` | Inter 600, 56px | white, soft shadow | white text on an accent **rounded pill** | (pill only) |
| `ghost` | Inter 500, 54px | unspoken words at 28% white, spoken words white | accent-coloured text on a dark rounded box | (colour only) |
| `bigword` | Montserrat 700, 52px | unspoken words at 55%, spoken words white | brighter | the emphasis word gets its **own chunk at 118px in the accent colour** |
| `boxcaps` | Montserrat 700, 50px, Title Case | words appear only as spoken, so the line grows from the centre | white on a **square highlight box** (`highlight` colour, usually red) | (box only) |
| `serifmix` | Inter 600, 52px, tight tracking (-0.035em) | each word fades and un-blurs in (8px to 0 over 0.18s) | none | emphasis word in **italic serif, 84px** (Instrument Serif / DM Serif / Fraunces) |

Use the client's own fonts when they have them. Otherwise use the defaults above. The template sets the
rhythm, and the font family can change.

## 6. Title card and text cards
- **Title card (0-3s):** a top band in the accent colour with a chevron bottom edge and the topic in a serif
  (96px). It slides down on entry and up on exit. Use the video's topic in 2-3 words ("African Achievements").
- **Text cards:** a full-screen paper (light) or dark background with 1-3 words in a serif at 92px that blur in.
  Use them as a beat on the big line, at most 1-2 per video. Captions hide while a card is up.

## 7. B-roll
- Use **photographic stills** (AI-generated or stock): cinematic, warm or moody, no text in the image.
  Show one every 15-40s for 2.5-6s. Stills feel like PNG overlays because they sit inside shapes.
- Each still **literally illustrates the phrase being spoken** at that moment ("family, education" over a
  family dinner; "possibility" over a passport on a table; "they buy a house" over a couple holding keys).
- Layouts: `full` (full frame, push-in), `card` (rounded image on the accent colour), `circle` (full frame plus
  accent rings), `split` (image in a top-half arc while the speaker keeps talking below).
- The speaker's audio continues under all b-roll. Captions stay on.
- Opening on b-roll with the hook line captioned over it is a strong start (2 of the 5 references do it).

## 8. Audio
- Voice is loudness-normalised to **-14 LUFS**, true peak -1.5 dB.
- Music is an optional ambient pad (no beat drops), **~20-24 dB under the voice** (`music.db = -24`), with a
  1.5s fade in and a 2.5s fade out. It should be barely noticed, mostly in pauses and transitions.
- Do not sync cuts to music.

## 9. Per-video variety, same system
Each video in a series gets a different template, transition and accent colour (all from the brand palette),
so the feed looks varied while the structure stays the same. Rotate through the five pairings in section 4.
