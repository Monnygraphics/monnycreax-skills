// Render the reel's overlay layer (captions, title, b-roll inserts, wipes) as transparent PNGs.
// Usage: node render-overlay.js <project dir>   (needs edit.json, cut_words.json, cut.mp4)
// Writes <dir>/frames/00000.png ... one per frame at 30fps. Frames whose state key repeats are
// hard-linked to the previous PNG instead of re-screenshotted, so static caption holds cost nothing.
const path = require("path");
const fs = require("fs");
const { spawnSync } = require("child_process");
const { pathToFileURL } = require("url");

function loadPlaywright() {
  try { return require("playwright"); } catch {}
  return require(path.join(process.env.APPDATA || "", "npm/node_modules/@playwright/cli/node_modules/playwright"));
}
const browserPath = [process.env.CHROME_PATH, "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"].filter(Boolean).find(p => fs.existsSync(p));

const dir = path.resolve(process.argv[2] || ".");
// --at 1.5,4.2 renders only those moments to <dir>/preview/ (fast look before a full render)
const atArg = process.argv.indexOf("--at");
const AT = atArg > 0 ? process.argv[atArg + 1].split(",").map(Number) : null;
const ovArg = process.argv.indexOf("--override");
const edit = JSON.parse(fs.readFileSync(path.join(dir, "edit.json"), "utf8"));
if (ovArg > 0) Object.assign(edit, JSON.parse(process.argv[ovArg + 1]));
const cw = JSON.parse(fs.readFileSync(path.join(dir, "cut_words.json"), "utf8"));
const FPS = cw.fps || 30;
const dur = parseFloat(spawnSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
  path.join(dir, "cut.mp4")], { encoding: "utf8" }).stdout);
const frames = Math.round(dur * FPS);

for (const o of [edit.intro, edit.outro]) {
  if (o && o.logo && !/^(file|https?):/.test(o.logo)) o.logo = pathToFileURL(path.resolve(dir, o.logo)).href;
}
for (const b of edit.broll || []) {
  for (const pc of b.pieces || []) pc.url = pathToFileURL(path.resolve(dir, pc.src)).href;   // collage pieces
  if (b.layout === "collage") continue;
  const p = path.resolve(dir, b.src);
  if (!fs.existsSync(p)) { console.error("missing b-roll:", p); process.exit(1); }
  b.url = pathToFileURL(p).href;
}
// glass pack images: tile src and promo panel img
const fileUrl = s => /^(file|https?|data):/.test(s) ? s : pathToFileURL(path.resolve(dir, s)).href;
for (const t of edit.tiles || []) if (t.src) t.src = fileUrl(t.src);
for (const p of edit.panels || []) if (p.img) p.img = fileUrl(p.img);

const wArg = process.argv.indexOf("--workers");
// independent Chrome pages each draw a contiguous frame range; seek(t) is stateless, so ranges can run in parallel
const WORKERS = Math.max(1, wArg > 0 ? +process.argv[wArg + 1] : Math.min(8, Math.floor(require("os").cpus().length / 2)));

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on("pageerror", e => console.error("page error:", e.message));
  await page.goto(pathToFileURL(path.join(__dirname, "overlay.html")).href);
  const res = await page.evaluate(d => window.init(d), { edit, words: cw.words, fps: FPS });
  return { page, res };
}

(async () => {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ executablePath: browserPath });
  const { page, res } = await openPage(browser);
  console.log("overlay init", JSON.stringify(res));
  if (res.badImgs.length) { console.error("images failed to load:", res.badImgs); process.exit(1); }
  if (res.badFonts.length) console.error("fonts failed (fallback used):", res.badFonts);

  if (AT) {
    const pv = path.join(dir, "preview");
    fs.mkdirSync(pv, { recursive: true });
    for (const [i, t] of AT.entries()) {
      await page.evaluate(t => window.seek(t), t);
      await page.screenshot({ path: path.join(pv, `ov_${String(i).padStart(3, "0")}.png`), omitBackground: true });
    }
    await browser.close();
    return;
  }
  const out = path.join(dir, "frames");
  fs.rmSync(out, { recursive: true, force: true });
  fs.mkdirSync(out, { recursive: true });
  const t0 = Date.now();
  const n = Math.min(WORKERS, Math.max(1, Math.floor(frames / 120)));
  // one Chrome process per worker: pages inside one browser share its screenshot/encode pipeline and barely scale
  const pages = [page], extra = [];
  for (let i = 1; i < n; i++) { const br = await chromium.launch({ executablePath: browserPath }); extra.push(br); pages.push((await openPage(br)).page); }
  let done = 0, shots = 0;
  const run = async (pg, a, b) => {
    let lastKey = null, lastFile = null;
    for (let f = a; f < b; f++) {
      const file = path.join(out, String(f).padStart(5, "0") + ".png");
      const key = await pg.evaluate(t => window.seek(t), f / FPS);
      if (key === lastKey && lastFile) {
        try { fs.linkSync(lastFile, file); } catch { fs.copyFileSync(lastFile, file); }
      } else {
        await pg.screenshot({ path: file, omitBackground: true });
        shots++; lastKey = key; lastFile = file;
      }
      if (++done % 600 === 0) console.log(`frame ${done}/${frames} (${shots} unique, ${n} workers, ${((Date.now() - t0) / 1000).toFixed(0)}s)`);
    }
  };
  const step = Math.ceil(frames / n);
  await Promise.all(pages.map((pg, i) => run(pg, i * step, Math.min(frames, (i + 1) * step))));
  await Promise.all(extra.map(br => br.close()));
  await browser.close();
  console.log(`overlay done: ${frames} frames, ${shots} unique, ${n} workers, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
})();
