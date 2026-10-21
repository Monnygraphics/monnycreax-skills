# Glass style (template `glass`, the "Nyandi" look)

Studied from Nyandia Gachago's reel (instagram.com/reel/DelthhztvuB, Oct 2026, captioned "Video fully edited
by AI"): a Kenyan educator speaking English with Swahili/Sheng mixed in. The user rated it top editing. Use it
for **educational, explainer and offer reels** (a framework, "3 checks", a masterclass promo) where the
speaker's points can become on-screen objects. For grief, testimony or prayer, use the calm templates.

## What it does
| Layer | Look | Rhythm |
|---|---|---|
| Captions | 3 words in a dark frosted pill, Montserrat 700, white, **active word in the neon accent**, near chest height (y 0.775) | every group fades up as it lands |
| Headlines (`heads`) | top of frame: small *italic serif kicker* ("stop paying for", "instead, run", "No. 1") + huge heavy caps line (FOLLOWER COUNT, 3 CHECKS) in white or the accent | one per idea, held for the whole sentence (3-10s), zoom-blur in, blur out |
| Icon chips (`chips`) | 112px frosted circle beside the head, line icon glowing in the accent | pops in with the headline, mirrors the noun ("followers" → users, "trust" → shield) |
| Glass panels (`panels`) | big frosted card mid-frame; **the video behind is blurred and dimmed**. Mock UI built from what she says: comment rows ("Where can I buy this?"), stat bars, a promo card | rows appear one by one on the words that name them; a highlight row glows; a solid badge pops ("BUYING INTENT") |
| Promo card | glass card: image left, italic kicker, caps title, icon rows (date, time, venue, price) | for the offer near the end |
| End pills (`pills`) | info chips: solid accent for the key one (SAT 31 OCT), frosted for the rest | staggered pops, with an image `tile` beside |
| Sparks (`sparks`) | accent glyphs ($, ★) drifting up | 1-2s, only on a money/win line |

Colour: one neon accent (her green `#2BE36B`) against white type. Use the client's brightest brand colour as
`pop`; if the brand is muted, lift its lightness so it glows (Client A's teal `#2FA89E` became `#45D6C6`).
Fonts: Montserrat (display/captions) + Playfair Display italic (kickers). Brand fonts can replace them.
No shape wipes, title card or hook bar: the headline does that job. Cuts are hard, with punch-ins as usual.

## edit.json fields (times on the cut timeline)
```json
"template": "glass", "gradient": false, "captions": {"y": 0.775}, "scrim": 0.34, "glass_blur": 28,
"heads":  [{"start": 0.1, "end": 4.3, "kicker": "stop paying for", "text": "FOLLOWER\nCOUNT", "color": "accent|ink", "size": 132, "y": 0.06}],
"chips":  [{"start": 0.4, "end": 4.3, "icon": "users", "side": "left|right", "y": 0.2}],
"panels": [{"start": 16.6, "end": 22.9, "type": "list|bars|promo", "icon": "chat", "title": "Sponsored post", "sub": "1.2M followers",
            "items": [{"user": "@weekend.shopper", "text": "Where can I buy this?", "at": 17.5, "hl": true, "tick": "?"},
                      {"text": "Based in Nairobi", "value": 64, "at": 20.1}],
            "badge": {"text": "Buying intent", "at": 21.0}, "blur": true, "y": 0.33}],
"panels (promo)": [{"type": "promo", "img": "broll/poster.jpg", "kicker": "join me live", "title": "AI Growth Masterclass",
            "sub": "Part 2", "items": [{"icon": "calendar", "text": "Saturday, 31 October", "at": 30.2}]}],
"tiles":  [{"start": 44, "end": 52, "src": "broll/me.png", "side": "left", "y": 0.5}],
"pills":  [{"start": 44, "end": 52, "y": 0.74, "rows": [[{"text": "Sat 31 Oct", "solid": true}, {"text": "9 AM"}], [{"text": "Virtual"}]]}],
"sparks": [{"start": 12, "end": 14, "glyph": "$", "count": 6}]
```
- `bars` items take `value` (0-100). **Only use numbers the speaker says or the client supplies.** Never
  invent stats; use `list` rows of her own phrases instead.
- `scrim` (0-0.5) is the dark halo behind headlines: about 0.34 on bright white walls, 0 on mid-tone rooms.
- The blur under a panel is done in the ffmpeg base pass (`panels[].blur`, default true, or bare
  `"blur": [{"start","end"}]` ranges), ramping in over 0.35s. CSS backdrop-filter cannot see the video because
  the overlay is drawn as separate PNGs.
- Icons: users, user, heart, eye, shield, list, chat, comment, pulse, calendar, clock, video, spark, bulb,
  money, trend, check, fire, target, cart, mic, bot, hand, star, book, cross, pray.

## Planning a glass reel (Claude's job)
1. From the transcript, find the reel's **spine**: claim, then a numbered method, then the offer or CTA. Each beat
   gets one headline. Use her words; keep kickers lowercase and conversational and the main lines 1-3 words.
2. Turn every list or example she speaks into a panel whose rows appear on the exact word (`at`).
3. Put a chip next to each headline that names a concrete noun. Use sparks at most once.
4. Keep the captions running under everything, including panels. Hide nothing.
5. Swahili/Sheng lines stay in the captions as spoken (transcribe with `--mix sw`, then proofread).

## Soft glass variant (`"glassStyle": "soft"`), from Nyandia's 2nd reel (instagram.com/reel/Deq0kaqtqF4, Oct 2026)
The same family, but calmer and more editorial. Use it for warm, reflective or premium talks, and when the client's
brand is elegant rather than loud. Client A's reel 07 in this style is the worked example
(`%LOCALAPPDATA%/claude-work/reel-editor/client-a/reel-07/edit.json`).

| Element | Soft glass |
|---|---|
| Captions | **off** (`"captions": {"off": true}`). The headlines carry every line, so write one per sentence |
| Headlines | small spaced-out sans kicker between hairline dashes (— How do you —), then an **italic serif** main line in `cream`, normal case, ~90px; words drift in one by one, blur out at the end |
| Background | `"grade": "film"` (warm highlights, teal shadows, lifted blacks, vignette) + `"topblur": {"to": 0.3}` (a permanent soft lens blur over the top 30%, so headlines sit on a calm field) |
| Accent | one warm accent (her gold; use the client's own: Client A = cream `#F6EEDC` + teal `#45D6C6`) |
| Chips | small (86px) and quiet, no glow |
| `bubbles` | short quotes stacking one by one beside the speaker: `{"start","end","side": "right","x": 0.06,"y": 0.5,"items": [{"text","at"}]}` |
| Compact cards | `panels[].size: "compact"` (+ `"side": "left"`, `"blur": false`): small side cards (pack sizes, a payment schedule with a highlighted row) |
| Ending | `"blur": [{"start","end","dim": 0.35}]` over the last seconds, plus a centred head (`"y": 0.36`), stacked `pills` (one `solid`) and a logo/photo `tile` |
| Tone | `"glassTone": "dark"` on pale walls or white clothes: light glass has no contrast there (found on Client A's white top) |

Writing rule: with no captions, each headline must stand on its own. Use her words, compressed: kicker = the setup,
main = the payoff ("One of the leading causes of" / *divorce.*). Swahili lines stay in Swahili ("Biashara iko" /
*chini?*). Keep the numbers she says, and don't invent any.
