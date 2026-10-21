# Series mode (token-lean, Oct 2026)

For any series of 3+ reels from one shoot. Measured cost of hand-editing one reel (Client B V1): ~200k tokens
(transcript dumps, hand-written edit.json, b-roll compositing, two 4k-token check sheets per render).
Series mode does the same through `batch.py`: Claude writes ~15 lines of JSON per reel and reads one log line
plus one small check strip per reel.

## Rules that save the most
- **Set up once, reuse:** brand, template, music bed, SFX kit, intro/outro cards and b-roll layouts live in
  `batch.json` top level. Reels only carry what differs.
- **Read each transcript once**, compact (`$P transcript`), and write the reel spec right away. Never print
  word-level JSON; batch finds every time by phrase.
- **Never hand-place times.** Points, cards, b-roll and hooks are phrases.
- **No preview round per reel.** Render the first reel, show it, then batch the rest. Read `check.jpg` (12 small
  frames) and `batch-log.jsonl`, not full check sheets, unless a note flags a problem.
- **Run in the background**, two workers. Don't poll; wait for the notification.

## Steps
1. `scan` + transcribe all clips in one background loop into `<out>/_map/` (one call).
2. Read the transcripts (one `transcript` call for all) and write `batch.json`: clip map → one reel each, with
   `exclude` ranges for slates/retakes, `fix` for mishearings, 1 points page, max 3 b-roll phrases with a
   Pexels query `q`.
3. `python series.py kit batch.json --music <url|file>`: picks a whoosh/pop/paper/click from the user's SFX
   folders (`sfx_library`) and the single music bed, and writes them into batch.json.
4. B-roll photos: run the browser snippet below on pexels.com with every `q` (one call), save the result as
   `candidates.json`, then `python series.py broll batch.json candidates.json`. Read `_kit/broll-sheet.jpg`
   once; swap any bad pick by adding its id to `_kit/used.json` and re-running.
5. Intro/outro cards: render all episodes once (`render-endings.js --intro <ids>`, then without `--intro`).
6. `python batch.py batch.json --only <first id>`, deliver, user reviews. Then the rest:
   `--worker 0 --workers 2` and `--worker 1 --workers 2` in the background.

## Browser snippet (Pexels photo search, ids only)
```js
const Q=[/* queries */]; const o={}; for(const q of Q){const h=await (await fetch('/search/'+encodeURIComponent(q)+'/?orientation=portrait')).text();
const d=JSON.parse(h.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/)[1]).props.pageProps.initialData.data||[];
o[q]=d.slice(0,5).map(x=>x.attributes.id)} o
```
Pexels blocks curl on search pages (403) but `images.pexels.com` downloads fine.

## batch.json shape (series fields)
```json
{"footage": "D:/footage/shoot-1", "out": "%LOCALAPPDATA%/claude-work/reel-editor/shoot-1", "deliver": "D:/footage/shoot-1",
 "template": "serifmix", "hook": null, "zoom": 1.28,
 "transitions": ["hex", "wave", "disc", "blinds", "arc"], "broll_max": 3, "broll_layouts": ["card", "circle", "split"],
 "sfx_library": ["~/ASSETS/SOUND EFFECTS"], "music_lufs": -36,
 "intro_overlay": "D:/x/out-intros/{id}_overlay.mov", "intro_len": 3.6, "endcard": "D:/x/out/{id}.mp4",
 "defaults": {"brand": {...}, "captions": {...}},
 "reels": [{"id": "09-executive-presence", "src": "C0637.MP4", "title": "Client B - 09 ...",
   "exclude": "0-4.9", "fix": [["laure", "loudest."]], "emphasis": ["listens"],
   "cards": [{"phrase": "it's often the person who listens", "sub": "the most influential person", "text": "Not the loudest.",
              "points": [{"text": "Listens carefully", "phrase": "listens carefully"}, ...]}],
   "broll": [{"phrase": "barely says a word", "q": "black woman boardroom meeting"}]}]}
```
A points page (`cards[].points`) is the OG paper page: off-white, kicker + serif title, each point pops in
(with the kit's pop sound) on the word that names it. Captions hide while it is up.

## Glass hook box (Monny, Oct 2026)
Every series reel gets one: `"glass": {"kicker": "Executive presence", "text": "Why the quietest person often has the most influence"}`.
A frosted box (white edge, tinted brand dark) at y≈0.6 right after the intro title, ~5s, captions hidden under it.
Write the text as the hook: what the video is about, in her terms, one sentence. Keep b-roll and cards after it.

## Intro title legibility (Monny, Oct 2026)
With `intro_overlay`, batch blurs + dims the footage under the title (`intro_dim`, default 0.38) and switches
captions off for `intro_len` (`nocaps`). Long title lines shrink in the card (>15 chars 86px, >19 chars 74px).

## Script alignment + pauses (Monny, Oct 2026)
Before rendering a series, save the teleprompter script as `script.md` (`## <reel id>` per reel) and run
`python align.py batch.json script.md` (add `--dry` to preview). It removes immediate repeats ("because because",
"you are, you are"), restarts and stray filler words, and pins caption spelling to the script (`fix_at`, one word
at a time). Content words she added ("most important") stay. Set `"silence_db": -12` in batch.json for rooms with
hum: the default -20 left 6-12 pauses over 0.45s per reel.
B-roll: queries say "black"/"african"; check the sheet for non-African faces, bare skin, casual clothes and text.
Per-reel `broll_max` overrides the series cap.
