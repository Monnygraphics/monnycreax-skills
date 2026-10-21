# web-design: one self-contained web design skill

Entry point: `SKILL.md`. Everything else is bundled, so this folder works on its own.

## Install
- **Claude Code**: unzip so the folder sits at `~/.claude/skills/web-design/` (the folder must contain `SKILL.md` directly).
- **claude.ai chat** (web, desktop, mobile): Settings → Capabilities → turn on Code execution → Skills → Upload skill → choose `web-design.zip`. It then triggers automatically on web design requests.
- **Claude Code on the web (cloud)**: cloud sessions don't see `~/.claude/skills`. Commit this folder to the repo as `.claude/skills/web-design/`.
- **Canva**: connect the Canva connector (claude.ai Settings → Connectors, or `/mcp` in Claude Code). **Pinterest** has no connector. The skill uses public board RSS feeds, pin URLs, uploaded screenshots, or Claude in Chrome.
- Optional for browser checks: `npm install -g @playwright/cli@latest`. The ui-ux-pro-max search needs Python 3.

## Contents
- `modules/pinterest-moodboard`, `modules/canva-design`: Pinterest → design direction, and Canva brand kits / imagery / export / launch graphics (added 2026-10-14)
- `SKILL.md`: pipeline, merged rules, and the module router
- `references/preflight.md`, `references/verify.md`: pre-ship checklist, browser verification recipe
- `design-md/`: 84 real-site DESIGN.md systems + `INDEX.md`
- `modules/` (31): design-taste-frontend, redesign-existing-projects, image-to-code, imagegen-frontend-web, imagegen-frontend-mobile, minimalist-ui, industrial-brutalist-ui, high-end-visual-design, gpt-taste, stitch-design-taste, brandkit, full-output-enforcement, web-design-guidelines, writing-guidelines, vercel-react-best-practices, vercel-composition-patterns, vercel-react-view-transitions, vercel-react-native-skills, deploy-to-vercel, vercel-cli-with-tokens, vercel-optimize, playwright-cli, ui-ux-pro-max, design-principles, apple-design, animate, improve-animations, review-animations, pick-ui-library

## Credits
- taste-skill modules: Leonxlnx/taste-skill (MIT)
- web-design-guidelines, writing-guidelines, vercel-* and deploy modules: vercel-labs/agent-skills (MIT)
- design-md library: VoltAgent/awesome-design-md (MIT)
- playwright-cli: microsoft/playwright-cli (Apache-2.0)
- ui-ux-pro-max: nextlevelbuilder/ui-ux-pro-max-skill (MIT)
- apple-design, animate, improve-animations, review-animations, pick-ui-library: emilkowalski/skills (MIT)
- design-principles, merged rules and pipeline: MonnyCreaX
Snapshot built 2026-10-13, updated 2026-10-14.
