# Apollo style (`plan --template apollo`)

Monny's signature "expensive minimal" look, locked in on 2026-10-21 after the Claude Community Kenya recap
(Client D, Meetup Part 2). Monny: "love these edits and I love this style". It is built on the soft-glass
engine ([glass-style.md](glass-style.md) § Soft glass) **with the glass caption pills switched back on**.
Named after Apollo, god of the arts, music and light. Use it for talks, event recaps, community/brand stories, launches and premium personal-brand reels. Swap to a calmer
template only for grief or prayer.

`$P plan <dir> --template apollo` writes every setting below. Only the theme colours are left open.

## Fixed: the same on every Apollo reel
| Layer | Setting |
|---|---|
| Engine | `"template": "glass"`, `"glassStyle": "soft"`, `"glassTone": "dark"` (dark frosted glass reads on any footage) |
| Grade + field | `"grade": "film"`, `"topblur": {"to": 0.3, "sigma": 22}`, `"scrim": 0.22`, no gradient |
| Headlines | spaced sans kicker between hairlines, then an **italic serif** line (Playfair Display + Montserrat). About one per beat; kicker = setup, main = payoff, in the speaker's words. Use `"color": "accent"` on 3-4 key lines. They summarise; they don't repeat the caption word for word |
| Captions | ON: 3-word dark frosted pills at y 0.775, active word in `pop` |
| Cards | `promo` speaker/guest cards (photo + kicker + title + 2 icon rows timed to the words) at **y 0.52, below the face**, `"blur": false`; `list` compact cards for any spoken list or steps (y 0.52, left) |
| Bubbles | thank-yous and short lists stacking beside the speaker (right, y 0.47) |
| Chips | 1-2 small quiet icons on the hook and one key noun |
| Ending | last ~6s: `"blur": [{"start","end","dim": 0.35}]` + centred head (`"y": 0.36`) + logo/poster `tile` + `pills` (one `solid`: the event/offer, then date, then a sign-off) |
| Motion | hard cuts, punch-ins from `plan`, the default whoosh only (`"sfx": {"db": -20}`) |
| Music | ONE calm bed, **`"lufs": -37`** (Monny found -31 too loud). It sits about 13 dB under the voice and fades out on the end card |

## Open: the theme (decided per client or per video)
`plan` writes `"THEME"` in every brand colour, and `render` refuses to run until they are filled. Source, in order:
1. The client's brand kit or memory (`project.md`, `memory/<client>.md`).
2. The client's own posts or screenshots (Peter's came from the community's IG speaker posters).
3. Otherwise ask the single brand-colour question ([brand-colours.md](brand-colours.md)).

| Key | Role | Peter (terracotta) | Gold example |
|---|---|---|---|
| `accent` / `highlight` | accent headlines, solid pill | `#CC785C` | `#C9A227` |
| `accent2` | darker accent | `#A9583F` | `#8C6D12` |
| `pop` | active caption word, icons. **Lift the accent's lightness so it glows on dark glass** | `#EE9A78` | `#F2CC5B` |
| `cream` / `ink` / `paper` | headline and body text | `#F4EDE4` | `#F6EEDC` |
| `dark` | deep base | `#1F1A17` | `#14110A` |
Fonts may be swapped for the client's brand fonts. Keep one serif italic for headlines and one clean sans.

## Media sourcing
- **B-roll video** (preferred): the client's own clips first. Lay them in with
  `$P vbroll <dir> vbroll.json` (`[{"start","end","src","in"}]`, cut timeline). It crops to 9:16, mutes the clip,
  keeps the speaker's voice, and always rebuilds from `cut_aroll.mp4`, so you can edit and re-run.
  Every 6-10s of talk, 3-4s each, on the exact phrase (numbers → crowds, "community" → people interacting).
  Sample frames at the chosen `in` point first: skip motion-blurred passers-by and camera pans.
- **When the folder has no b-roll or images:** search `~/ASSETS/library-index.csv` first, then get them from the internet (Pexels video/photo first, then other
  free-licence sources, via `agent-reach` or the web). No watermarks, no readable third-party text. For African
  clients, Black/African people only, in premium or corporate wear. Note each source in `project.md`.
- **Never** put footage of one person under another person's name (no host b-roll under a guest's headline or card).
- **Guest photos** for promo cards: crop them from the client's posters or screenshots (photo only, no app UI).
- **Music:** pick from the local library first (`~/ASSETS/~/ASSETS/BROLL|MUSIC|IMAGES` via the index, `~/Music`, previous reel work
  folders), choosing calm chill or ambient business beds for Apollo. Download from Pixabay Music or other royalty-free
  sources only when Monny asks for music or approves. Use one bed per reel at -37 LUFS.

## Workflow
`prep` → fix text (names!) → `plan --template apollo` → fill the theme from the client → heads, cards, bubbles, ending
→ `vbroll` → `preview` (check cards sit below the face and the b-roll frames are clean) → `render` → `check` → `deliver`.
