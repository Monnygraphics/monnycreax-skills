// Render every cover.
//   out/cover/<id>.jpg  1080x1920  Reel / TikTok / Shorts cover (what gets uploaded)
//   out/grid/<id>.jpg   1080x1440  3:4 profile-grid crop (how Instagram shows it on the profile)
//   out/grid-preview.jpg           whole feed mock, 3 across, newest first
// Usage: node render.js [id ...]      (no ids = all)
const path = require("path");
const fs = require("fs");
const { pathToFileURL } = require("url");

function loadPlaywright() {
  try { return require("playwright"); } catch {}
  const globalCli = path.join(process.env.APPDATA || "", "npm/node_modules/@playwright/cli/node_modules/playwright");
  try { return require(globalCli); } catch {}
  throw new Error("playwright not found: npm i -g @playwright/cli (or npm i playwright in this folder)");
}
function findBrowser() {
  const candidates = [
    process.env.CHROME_PATH,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
  ].filter(Boolean);
  return candidates.find(p => fs.existsSync(p)); // undefined -> playwright's own chromium
}

const { chromium } = loadPlaywright();
const HERE = __dirname;
const win = {};
new Function("window", fs.readFileSync(path.join(HERE, "thumbs.js"), "utf8"))(win);
const ids = process.argv.slice(2).length ? process.argv.slice(2) : win.THUMBS.map(t => t.id);

(async () => {
  for (const d of ["out/cover", "out/grid"]) fs.mkdirSync(path.join(HERE, d), { recursive: true });
  const browser = await chromium.launch({ executablePath: findBrowser() });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  page.on("requestfailed", r => { if (!r.url().endsWith("tweaks.js")) errors.push("failed: " + r.url()); });
  const url = pathToFileURL(path.join(HERE, "index.html")).href;
  for (const id of ids) {
    await page.goto(`${url}?id=${encodeURIComponent(id)}`);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(() => [...document.images].every(i => i.complete));
    const bad = await page.evaluate(() => [...document.fonts].filter(f => f.status === "error").map(f => f.family));
    if (bad.length) errors.push(`${id}: font failed to load: ${bad.join(", ")}`);
    if (!(await page.locator(".card").count())) { errors.push(`${id}: no such id in thumbs.js`); continue; }
    await page.locator(".card").screenshot({ path: path.join(HERE, "out/cover", `${id}.jpg`), type: "jpeg", quality: 92 });
    await page.screenshot({ path: path.join(HERE, "out/grid", `${id}.jpg`), type: "jpeg", quality: 92,
      clip: { x: 0, y: 240, width: 1080, height: 1440 } });
    console.log("rendered", id);
  }
  // feed mock: newest first like Instagram (last entry top-left)
  const all = win.THUMBS.map(t => t.id).reverse()
    .filter(id => fs.existsSync(path.join(HERE, "out/grid", `${id}.jpg`)));
  const tiles = all.map(id => `<img src="${pathToFileURL(path.join(HERE, "out/grid", id + ".jpg")).href}">`).join("");
  await page.setViewportSize({ width: 1080, height: 400 });
  await page.goto(url); // file:// origin so the tiles can load
  await page.setContent(`<style>body{margin:0;background:#fff}div{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;width:1080px}img{width:100%;display:block}</style><div>${tiles}</div>`);
  await page.waitForFunction(() => [...document.images].every(i => i.complete));
  await page.locator("div").screenshot({ path: path.join(HERE, "out/grid-preview.jpg"), type: "jpeg", quality: 88 });
  await browser.close();
  if (errors.length) { console.error("PROBLEMS:\n  " + [...new Set(errors)].join("\n  ")); process.exitCode = 1; }
})();
