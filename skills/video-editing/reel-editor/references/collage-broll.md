# Collage b-roll (layout `collage`, the gbro look made locally)

Adapted from github.com/pyang5166/gbro-collage-broll (MIT, "狗哥笔记"). That skill turns one ~5s spoken line
into an editorial **halftone paper-collage** clip: black-and-white halftone photo cut-outs and coloured cardstock
with cream keylines and soft shadows, assembling piece by piece from an empty flat colour field. It needs
Codex's built-in `image_gen` plus a paid Gemini video key (`gemini-omni-flash-preview`, billed per clip).
**We do not use its pipeline.** We keep its look and its metaphor discipline, and build the clip locally for free:
`collage.py` makes the pieces and the overlay animates the assembly.

## When
A line that is an idea rather than a scene: a principle, a contrast or a mechanism ("money and marriage go hand
in hand", "attention before demand"). Use 1-2 per reel at most, 3-6s each. Story scenes stay with `story`;
glass panels stay with lists and data.

## Workflow (keep gbro's two gates)
1. **Metaphor gate.** For each chosen line, write the core meaning, emotion, a one-sentence visual idea,
   3-6 objects, the background colour and the assembly order. Show it to the user and wait.
   - Colour by meaning (gbro): burnt orange/red = time, labour, urgency; mustard = tools, warning; deep green =
     cognition, reset; deep purple = rules, long memory; teal = judgement, collaboration. A brand colour can
     replace these.
2. **Pieces.** Find photos for the objects (folder `broll/`, Pexels, or an image tool when connected), then:
   `~/.rembg-venv/Scripts/python -I scripts/collage.py <imgs> --out <dir>/collage [--no-cut flat.jpg]`
   This cuts out the subject (rembg), tone-maps from the subject's own pixels with local contrast (so dark skin
   keeps its features), prints it as a 45° halftone, and adds a cream keyline. Use `--no-cut` for flat objects
   (a document, a calendar, a board) to get a straight paper card. Check the pieces on a red field before
   placing them.
3. **Still gate.** Run `preview` at the fully assembled moment and show it. Rearrange until the metaphor reads at
   a glance. Then render.

## edit.json
```json
{"start": 23.2, "end": 29.4, "layout": "collage", "bg": "#C8382E", "transition": "disc",
 "cards":  [{"color": "#F2C230", "x": 0.5, "y": 0.36, "w": 0.62, "h": 0.2, "rot": -3, "from": "left", "at": 23.55}],
 "pieces": [{"src": "collage/chart.png", "x": 0.33, "y": 0.30, "w": 0.42, "rot": -6, "from": "top",    "at": 23.9},
            {"src": "collage/man.png",   "x": 0.52, "y": 0.60, "w": 0.74, "rot": 2,  "from": "bottom", "at": 24.4},
            {"src": "collage/rings.png", "x": 0.72, "y": 0.27, "w": 0.34, "rot": 8,  "from": "drop",   "at": 25.3}]}
```
- `x`/`y` are the piece centre as fractions of the frame, `w` the width fraction. `from`: top | bottom | left |
  right | drop (lands from above with a slight scale-down). `at` is the absolute time it starts (default:
  staggered 0.45s apart). Each takes 0.42s with a small overshoot.
- Motion is quantised to 12 fps (stop-motion), so it reads as hand-placed paper, not a smooth slide.
- Order (gbro): structure first, then the subject or cards, then the action or result last. Leave clean
  colour-field space. Keep 3-6 large groups, never confetti.
- No text inside the collage. The captions carry the words.
