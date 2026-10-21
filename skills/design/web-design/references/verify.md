# Browser Verification Recipe (playwright-cli)

`@playwright/cli` is installed globally (`playwright-cli --version`). Full command reference: `modules/playwright-cli/MODULE.md` (+ its `references/`). It is token-cheap: it returns compact snapshots with element refs (`e15`) instead of dumping the DOM.

`file://` URLs are blocked by playwright-cli; always serve over http. Serve the page first (`npx serve .`, `npm run dev`, or the project's `.claude/launch.json` via the Browser pane's `preview_start`). Save screenshots inside the project (e.g. `./.screens/`), not the home directory.

```bash
playwright-cli open http://localhost:3000
playwright-cli console error          # must be empty

# Breakpoints
playwright-cli resize 375 812  && playwright-cli screenshot --filename=.screens/mobile.png
playwright-cli resize 768 1024 && playwright-cli screenshot --filename=.screens/tablet.png
playwright-cli resize 1280 720 && playwright-cli screenshot --filename=.screens/laptop.png   # hero must fit here
playwright-cli resize 1920 1080 && playwright-cli screenshot --filename=.screens/desktop.png

# Dark mode
playwright-cli set-color-scheme dark && playwright-cli screenshot --filename=.screens/laptop-dark.png
playwright-cli clear-color-scheme

# Horizontal overflow at mobile (must be false)
playwright-cli resize 375 812
playwright-cli eval "document.documentElement.scrollWidth > innerWidth"

# Keyboard: tab through and confirm visible focus on each stop
playwright-cli press Tab && playwright-cli screenshot --filename=.screens/focus-1.png

# Full-page capture for review
playwright-cli screenshot --filename=.screens/full.png --full-page
playwright-cli close
```

Reduced motion: check the CSS has a `@media (prefers-reduced-motion: reduce)` block covering every animation (grep), since emulation support varies by CLI version.

**Design feedback from the user on the live page**: `playwright-cli open <url>` then `playwright-cli show --annotate`. The user draws boxes and comments; you receive the annotated screenshot and notes.

**Image-to-code fidelity**: screenshot the build at the reference image's width, then Read both images and list differences in text → type → spacing → components → color order.

Read each saved screenshot with the Read tool before claiming it looks right, and share them as proof.
