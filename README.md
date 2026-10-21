# MonnyCreaX Skills for Claude

These are the Claude skills I use every day at MonnyCreaX for video editing, branding, copy, design, books, research and dev work. I've packaged them here so friends can install them and use them on their own work.

A skill is a folder of instructions (and sometimes scripts) that Claude loads when the task needs it. Once a skill is installed you just describe the job, for example "edit the takes in D:\shoot-1 into reels", and Claude picks the right skill on its own.

> Made by **Bethwel Monny** ([MonnyCreaX](https://monnycreax.vercel.app)). Several skills build on open-source work by other people. See [CREDITS.md](CREDITS.md).

---

## What's inside

### 🎬 Video editing
| Skill | What it does |
|---|---|
| [reel-editor](skills/video-editing/reel-editor) | Turns a folder of raw talking-head takes into finished 9:16 reels. It finds retakes, slates and stumbles, cuts on pauses, cleans the audio, colour grades (13 looks plus LUTs) and adds captions, b-roll and music in five styles: Apollo, Athena, Hermes, Ares and Hestia. Its modules also clip long videos into shorts, break down a reference reel and make covers and thumbnails. |

### 📣 Brand and marketing
| Skill | What it does |
|---|---|
| [brand-strategist](skills/brand-and-marketing/brand-strategist) | Brand Council: positioning, UVP, personality, content strategy, weekly plans, offers, pricing and launches |
| [copywriting](skills/brand-and-marketing/copywriting) | Page copy, cold email, email sequences, ad copy, social posts, X |
| [humanizer](skills/brand-and-marketing/humanizer) | Rewrites AI-sounding text so it reads like a person wrote it |
| [linkedin](skills/brand-and-marketing/linkedin) | Drafts LinkedIn posts, comments, DMs, profile rewrites, plans and carousels in your voice (it never posts anything) |
| [growth](skills/brand-and-marketing/growth) | SEO, AI-search visibility, schema, CRO, analytics, paid-ads strategy |
| [contract-and-proposal-writer](skills/brand-and-marketing/contract-and-proposal-writer) | Proposals, contracts, SOWs and NDAs |

### 🎨 Design
| Skill | What it does |
|---|---|
| [web-design](skills/design/web-design) | Designs, builds, redesigns and reviews websites and web-app UI, working from a brief, screenshot, Pinterest board or brand kit |
| [ui-ux-pro-max-skill](skills/design/ui-ux-pro-max-skill) | UI/UX library: 50+ styles, 160+ palettes, font pairings, UX rules |
| [diagrams](skills/design/diagrams) | Technical diagrams and client-ready visuals: journeys, funnels, org charts |

### 📚 Writing and publishing
| Skill | What it does |
|---|---|
| [book-production](skills/writing-and-publishing/book-production) | Manuscript → print-ready A5/KDP PDF, Word and EPUB, with spine size and print checks |

### 🔎 Research and career
| Skill | What it does |
|---|---|
| [research](skills/research-and-career/research) | Dossiers on people and companies, market sizing, competitor teardowns, meeting-transcript analysis |
| [agent-reach](skills/research-and-career/agent-reach) | Lets Claude read the web, X, Reddit, YouTube and more (needs the Agent Reach CLI) |
| [career-ops](skills/research-and-career/career-ops) | Job-search command centre (needs the career-ops project, see below) |

### 🛠️ Dev tools
| Skill | What it does |
|---|---|
| [gstack](skills/dev-tools/gstack) | Garry Tan's engineering toolkit: plan, review, QA, ship, browser testing |
| [browse](skills/dev-tools/browse), [qa](skills/dev-tools/qa), [review](skills/dev-tools/review), [ship](skills/dev-tools/ship), [investigate](skills/dev-tools/investigate) | The gstack commands I use most (they need gstack installed) |
| [graphify](skills/dev-tools/graphify) | Turns a codebase or folder into a knowledge graph you can query |
| [reverse-engineer-anything](skills/dev-tools/reverse-engineer-anything) | Reverse engineers apps and binaries with the REA CLI |
| [skill-inspector](skills/dev-tools/skill-inspector) | Checks a third-party skill for safety before you install it |

---

## Install

You need [Claude Code](https://claude.com/claude-code), either the desktop app or the CLI. Skills live in `~/.claude/skills/`, which is `C:\Users\<you>\.claude\skills\` on Windows.

**1. Download this repo.** Either use **Code → Download ZIP** on GitHub and unzip it, or run:

```bash
git clone https://github.com/Monnygraphics/monnycreax-skills.git
cd monnycreax-skills
```

**2. Install the skills you want.**

Windows (PowerShell):
```powershell
.\install.ps1 reel-editor humanizer      # just these
.\install.ps1 -Category video-editing    # a whole category
.\install.ps1 -All                       # everything
```

Mac / Linux:
```bash
./install.sh reel-editor humanizer
./install.sh --category video-editing
./install.sh --all
```

If Windows blocks the script, run it as `powershell -ExecutionPolicy Bypass -File .\install.ps1 -All`. Run `.\install.ps1` with no options to list every skill.

The installer skips any skill you already have. Add `-Force` (or `--force`) to replace it.

**3. Restart Claude Code.** Then ask for the job in plain words.

**Using claude.ai instead?** Every skill except gstack is attached as a zip on the [Releases page](https://github.com/Monnygraphics/monnycreax-skills/releases). Upload the zip under **Settings → Capabilities → Skills**. Scripts that need ffmpeg or Python will only run in Claude Code on your own machine. claude.ai may reject the biggest zips (web-design, diagrams, ui-ux-pro-max).

---

## Setup for the video skills

reel-editor runs Python and ffmpeg on your computer. Install these once:

1. **ffmpeg**: `winget install Gyan.FFmpeg` (Windows) or `brew install ffmpeg` (Mac)
2. **Python 3.10+**, then:
   ```bash
   pip install -r requirements-video.txt
   ```
3. **Node.js 18+** and **Google Chrome or Edge**. The captions, glass panels and covers are rendered as HTML in a headless browser:
   ```bash
   npm i -g playwright
   ```
4. **Optional: a free [Groq](https://console.groq.com) API key** for faster transcription. Set it as `GROQ_API_KEY`. Without a key, transcription runs locally with faster-whisper, which is slower but free.

Then try it:

> "Edit the raw takes in `D:\Videos\shoot-1` into reels in the Apollo style. My brand colours are #0B0B0F and #F5B700."

The skill only asks for your brand colours. Your folder gets the finished `final.mp4` files and nothing else, because working files go to a hidden folder (`%LOCALAPPDATA%\claude-work\reel-editor` on Windows).

**B-roll and music library (optional).** If you keep a library at `~/ASSETS` with `BROLL`, `MUSIC` and `IMAGES` folders and a `library-index.csv`, the skill checks it before it downloads anything.

## Setup for other skills

- **linkedin**: copy [`skills/brand-and-marketing/linkedin/templates/voice.md`](skills/brand-and-marketing/linkedin/templates/voice.md) to `~/.claude/linkedin/voice.md` and fill it in. Every draft is written in that voice.
- **book-production**: Python plus `pip install python-docx lxml pymupdf pyphen pyyaml`, and Chrome or Edge to print the PDF. The fonts are bundled (all SIL Open Font Licence).
- **gstack** and its commands (browse, qa, review, ship, investigate): install [Bun](https://bun.sh), then run `./setup` inside `~/.claude/skills/gstack`. Full guide: [garrytan/gstack](https://github.com/garrytan/gstack).
- **agent-reach**: install the CLI from [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach).
- **career-ops**: this folder holds only the router. It needs the full project from [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops).
- **graphify**: `uv tool install graphifyy` (or `pipx install graphifyy`). See [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify).
- **reverse-engineer-anything**: needs the REA CLI from [morluto/rea](https://github.com/morluto/rea).

---

## A few notes

- Some instructions mention MonnyCreaX: house fonts, pricing, my own way of working. Change them to suit you. Every skill is plain Markdown, so you can open it and edit it.
- **The skills never post, send or publish anything without asking you first.**
- Found a bug or made something better? Open an issue or send me a message.

## Licence

See [LICENSE.md](LICENSE.md). The short version: third-party parts keep their own open-source licences, listed in [CREDITS.md](CREDITS.md). My own skills are free for you to use and adapt for your own and client work, but please don't resell or republish them as a product.
