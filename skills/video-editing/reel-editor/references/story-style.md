# Story style (template `story`, the "Dane" look)

Studied from instagram.com/p/DdoSNMCgyk_ (uploader "dane", Oct 2026), a 2-minute property-marketing reel from
Nairobi. The speaker sells a framework ("attention, traffic, demand") by narrating one **persona's year**
(Esther, 46, managing director at a Westlands law firm) as illustrated scenes. Use it when the talk is a
**story, case study or customer journey**: a client before and after, "a day in the life", a parable, a
testimony told in the third person. It suits Client A's marriage and career stories.

## Structure it follows
1. **Hook with proof:** a big number counts up at the top while he says it (0 → 193.1M SHILLINGS).
2. **Framework in N words:** each keyword stacks at the top on the word ("ATTENTION" / "TRAFFIC" / "DEMAND").
3. **Persona:** "The easiest way to show you is to tell you about Esther." Then a full-screen illustrated
   portrait with a name label ("Esther, 46 yrs old").
4. **Chapters:** a calendar page flips to the month ("February, this is where the attention begins").
   Each chapter is 3-6 illustrated scenes with dissolves, each 2-5s, matching the narration line by line.
   He returns to camera between scenes to deliver the "she doesn't know it yet" beats.
5. **Turn:** inline big words at caption height ("But THIS will CHANGE her LIFE"), one word at a time.
6. **Analogy:** a reference photo on a clean white card (Steve Jobs) with a small serif label.
7. **Payoff + CTA:** back to the number; "click learn more".

## Look
| Layer | Spec |
|---|---|
| Captions | 2-3 words, **small serif** (Libre Baskerville ~40px), white, soft shadow, no box, no active-word highlight, chest height |
| Script lines | a quoted line ("We need to be in the room") switches the caption to a script face (Kaushan Script) |
| Big words | script kicker + condensed caps (Anton ~130px) at caption height; replaces the caption for 0.6-1s |
| Headlines | top, condensed caps (Anton), script kicker, keywords stack line by line (`lines`) |
| Counter | condensed white number top-left, eases from `from` to `to` over ~1.2s, small suffix |
| Scenes | full-screen illustrations, slow Ken Burns (in / out / left / right / up), **dissolve** between scenes, **flash** (soft white) into the first scene of a chapter |
| Calendar | cream card, desk calendar, the old month's page flips up and away to the new month (~2s) |
| Ref card | white background, photo centred, serif label |
| Camera | two framings (wide desk / tight face) alternating at section changes, punch-ins as usual |

## edit.json fields
```json
"template": "story", "headStyle": "cond", "captions": {"y": 0.62, "script": [{"start": 72.9, "end": 75.5}]},
"brand": {..., "cond": "Anton", "script": "Kaushan Script", "story": "Libre Baskerville"},
"counters":  [{"start": 2.6, "end": 7.0, "from": 0, "to": 193.1, "decimals": 1, "suffix": "M SHILLINGS", "dur": 1.4, "x": 0.08, "y": 0.05}],
"heads":     [{"start": 7.2, "end": 11.4, "kicker": "is in", "lines": [{"text": "ATTENTION", "at": 8.6}, {"text": "TRAFFIC", "at": 9.4}, {"text": "DEMAND", "at": 10.2}]}],
"calendars": [{"start": 14.1, "end": 16.2, "month": "FEBRUARY", "from": "JANUARY"}],
"bigwords":  [{"start": 25.6, "end": 26.2, "kicker": "But", "text": "this"}, {"start": 26.2, "end": 26.9, "kicker": "will", "text": "change"}],
"broll":     [{"start": 16.6, "end": 18.0, "src": "broll/esther-portrait.png", "transition": "flash", "kb": "in"},
              {"start": 17.7, "end": 20.3, "src": "broll/esther-office.png", "transition": "dissolve", "kb": "left"},
              {"start": 77.8, "end": 80.2, "src": "broll/ref.jpg", "layout": "ref", "label": "Steve Jobs", "transition": "dissolve"}]
```
- On pale walls the small serif captions lose contrast: add `"box": true` to `captions` for a soft dark backing
  (or a number 0.2-0.45 for its opacity). This works with every template.
- Overlapping scenes (the next starts before this one ends) dissolve over each other; the outgoing scene holds,
  so the talking head never leaks through mid-dissolve.
- `counters` only for numbers the speaker says. Never invent a figure.
- Inline big words should hit the beat that turns the story. Use 3-6 words at most per reel.

## The scenes are the work
The edit lives or dies on the illustrations. Plan them as a **storyboard** from the transcript (one line → one
scene), then generate them:
1. Write a **character sheet** once and paste it into every prompt so the persona stays the same person. Example:
   "Esther, 46-year-old Kenyan woman, short natural afro, rust-orange turtleneck, warm brown skin, calm
   confident face".
2. Use one **style line** for every scene: "warm cinematic 2D illustration, soft painterly shading, clean
   lines, Nairobi setting, 9:16 vertical, no text". Avoid readable text in images. Add name labels in the edit.
3. Vary the shots like a film: wide establishing, medium action, close-up detail (the phone screen, the
   cheque), POV (through the car window).
4. Generate with a connected image tool (Canva `generate-image`, Figma `generate_image`). If none is
   connected, write `broll-prompts.md` (scene, timestamp, line, full prompt) and ask the user to generate the
   images and drop them into `broll/`. The persona is fictional. Never use a real person's likeness unless it is
   the client (a ref card of a public figure is an editorial reference, as Dane did with Steve Jobs).
5. Calendar cards and counters are drawn by the overlay, so they need no images.
