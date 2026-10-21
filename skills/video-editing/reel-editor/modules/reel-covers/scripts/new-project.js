#!/usr/bin/env node
// Scaffold a reel-cover project and prep the shoot photos.
//   node new-project.js <project-dir> [--photos <shoot-folder>]
// - copies template/ into <project-dir> (never overwrites existing files)
// - downscales every photo to 2400px long edge into <project-dir>/photos (ffmpeg)
// - builds photos/_contact-sheet.jpg (7 across) + photos/_index.txt (number -> name)
//   so you can Read one image and pick shots by number.
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const args = process.argv.slice(2);
const dir = args[0];
const opt = k => { const i = args.indexOf(k); return i > -1 ? args[i + 1] : null; };
if (!dir) { console.error("usage: node new-project.js <project-dir> [--photos <folder>] [--example <name>]"); process.exit(1); }

const SKILL = path.resolve(__dirname, "..");
const out = path.resolve(dir);
fs.mkdirSync(out, { recursive: true });

function copyIn(srcDir) {
  for (const f of fs.readdirSync(srcDir).filter(f => !/\.(jpe?g|png)$/i.test(f))) {
    const dst = path.join(out, f);
    if (fs.existsSync(dst)) { console.log("kept existing", f); continue; }
    const src = path.join(srcDir, f);
    if (fs.statSync(src).isDirectory()) fs.cpSync(src, dst, { recursive: true });
    else fs.copyFileSync(src, dst);
    console.log("added", f);
  }
}
const example = opt("--example");
if (example) copyIn(path.join(SKILL, "examples", example));
copyIn(path.join(SKILL, "template"));

const shoot = opt("--photos");
if (shoot) {
  const ff = (...a) => spawnSync("ffmpeg", ["-loglevel", "error", "-y", ...a], { stdio: "inherit" });
  const photos = path.join(out, "photos");
  const thumbs = path.join(photos, "_tiles");
  fs.mkdirSync(thumbs, { recursive: true });
  const files = fs.readdirSync(shoot).filter(f => /\.(jpe?g|png|webp|tiff?)$/i.test(f)).sort();
  const index = [];
  files.forEach((f, i) => {
    const name = path.parse(f).name.replace(/-Edit$/i, "");
    const dst = path.join(photos, name + ".jpg");
    if (!fs.existsSync(dst))
      ff("-i", path.join(shoot, f), "-vf", "scale='if(gt(iw,ih),2400,-2)':'if(gt(iw,ih),-2,2400)'", "-q:v", "2", dst);
    const n = String(i + 1).padStart(3, "0");
    // numbered tile; fontfile avoids the fontconfig crash in Git Bash ffmpeg builds
    const font = process.platform === "win32" ? "C\\:/Windows/Fonts/arial.ttf" : "/System/Library/Fonts/Helvetica.ttc";
    const pad = "scale=200:300:force_original_aspect_ratio=decrease,pad=200:300:(ow-iw)/2:(oh-ih)/2";
    const r = ff("-i", dst, "-vf", `${pad},drawtext=fontfile='${font}':text='${i + 1}':x=8:y=8:fontsize=26:fontcolor=yellow:box=1:boxcolor=black@0.7`, path.join(thumbs, n + ".jpg"));
    if (r.status !== 0) ff("-i", dst, "-vf", pad, path.join(thumbs, n + ".jpg")); // unlabeled fallback
    index.push(`${i + 1}\t${name}`);
  });
  fs.writeFileSync(path.join(photos, "_index.txt"), index.join("\n") + "\n");
  // rows of 7 with hstack, then vstack (the image2 + tile filter breaks on mixed sizes)
  const tiles = fs.readdirSync(thumbs).filter(f => f.endsWith(".jpg")).sort().map(f => path.join(thumbs, f));
  const blank = path.join(thumbs, "_blank.png");
  ff("-f", "lavfi", "-i", "color=c=black:s=200x300", "-frames:v", "1", blank);
  const rows = [];
  for (let i = 0; i < tiles.length; i += 7) {
    const row = tiles.slice(i, i + 7);
    while (row.length < 7) row.push(blank);
    const rowFile = path.join(thumbs, `_row${rows.length}.jpg`);
    ff(...row.flatMap(t => ["-i", t]), "-filter_complex", "hstack=inputs=7", rowFile);
    rows.push(rowFile);
  }
  const sheet = path.join(photos, "_contact-sheet.jpg");
  if (rows.length === 1) fs.copyFileSync(rows[0], sheet);
  else ff(...rows.flatMap(r => ["-i", r]), "-filter_complex", `vstack=inputs=${rows.length}`, sheet);
  console.log(`prepped ${files.length} photos -> ${photos}\ncontact sheet: ${sheet}\nindex: ${path.join(photos, "_index.txt")}`);
}
