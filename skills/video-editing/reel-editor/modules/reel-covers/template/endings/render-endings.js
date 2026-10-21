// Render end cards frame by frame (transparent PNGs), then encode:
//   out/<id>_overlay.mov  ProRes 4444 with alpha: drop on the track above the video's last seconds
//   out/<id>.mp4          H.264 on the solid brand colour: append after the video
// Usage: node render-endings.js [id ...]
//        node render-endings.js --intro [id ...]   title overlays from intros.js -> out-intros/
//          (the solid MP4 is cut at INTRO.solidEnd so it ends on the full title, not the fade-out)
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

const HERE = __dirname;
const FPS = 30;
const win = {};
const INTRO = process.argv.includes("--intro");
const K = INTRO
  ? { data: "intros.js", list: "INTROS", cfg: "INTRO", page: "intro.html", out: "out-intros" }
  : { data: "endings.js", list: "ENDINGS", cfg: "ENDCARD", page: "endcard.html", out: "out" };
new Function("window", fs.readFileSync(path.join(HERE, K.data), "utf8"))(win);
new Function("window", fs.readFileSync(path.join(HERE, "brand.js"), "utf8"))(win);
const LIST = win[K.list], CFG = win[K.cfg];
const args = process.argv.slice(2).filter(a => a !== "--intro");
const ids = args.length ? args : LIST.map(e => e.id);
const bg = win.BRAND.colors.dark.bg.replace("#", "0x");
const ff = (...a) => { const r = spawnSync("ffmpeg", ["-loglevel", "error", "-y", ...a], { stdio: "inherit" }); if (r.status) throw new Error("ffmpeg failed"); };

(async () => {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ executablePath: browserPath });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  fs.mkdirSync(path.join(HERE, K.out), { recursive: true });
  for (const id of ids) {
    const e = LIST.find(x => x.id === id);
    if (!e) { console.error("no such id:", id); continue; }
    const frames = Math.round((e.duration || CFG.duration) * FPS);
    const solidFrames = CFG.solidEnd ? Math.round((e.solidEnd || CFG.solidEnd) * FPS) : frames;
    const dir = path.join(HERE, "frames", id);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir, { recursive: true });
    await page.goto(pathToFileURL(path.join(HERE, K.page)).href + "?id=" + encodeURIComponent(id));
    await page.evaluate(() => document.fonts.ready);
    const bad = await page.evaluate(() => [...document.fonts].filter(f => f.status === "error").map(f => f.family));
    if (bad.length) console.error(`${id}: font failed: ${bad.join(", ")}`);
    for (let f = 0; f < frames; f++) {
      await page.evaluate(t => window.seek(t), f / FPS);
      await page.screenshot({ path: path.join(dir, String(f).padStart(4, "0") + ".png"), omitBackground: true });
    }
    const seq = path.join(dir, "%04d.png");
    ff("-framerate", String(FPS), "-i", seq, "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
       path.join(HERE, K.out, `${id}_overlay.mov`));
    ff("-f", "lavfi", "-i", `color=c=${bg}:s=1080x1920:r=${FPS}`, "-framerate", String(FPS), "-i", seq,
       "-filter_complex", "[0][1]overlay=shortest=1,format=yuv420p", "-frames:v", String(solidFrames), "-c:v", "libx264", "-crf", "16", "-preset", "slow",
       "-movflags", "+faststart", path.join(HERE, K.out, `${id}.mp4`));
    fs.rmSync(dir, { recursive: true, force: true });
    console.log("ending", id);
  }
  await browser.close();
})();
