#!/usr/bin/env node
// Read a client's brand kit folder (SVG/AI exports) and report what brand.js needs.
//   node brand-from-svg.js <kit-folder> [--mark <logo.svg> --out <project>/mark.txt]
// Prints: named palette entries ("Teal Blue Hex: #035D6C"), most-used colours,
// font families used, and matching font files installed on this machine.
// --mark: pulls the <path> shapes from a logo SVG into one inline SVG with fill=currentColor
//         (so it recolours per theme). Paste the result into brand.js `mark`.
//         Crop with --viewbox "x y w h" when the logo file also contains a wordmark.
const fs = require("fs");
const path = require("path");
const os = require("os");

const args = process.argv.slice(2);
const opt = k => { const i = args.indexOf(k); return i > -1 ? args[i + 1] : null; };
const kit = args[0];
if (!kit) { console.error("usage: node brand-from-svg.js <kit-folder> [--mark logo.svg] [--viewbox 'x y w h'] [--out file]"); process.exit(1); }

const svgs = fs.readdirSync(kit).filter(f => /\.svg$/i.test(f));
const all = svgs.map(f => fs.readFileSync(path.join(kit, f), "utf8")).join("\n");

// named swatches (text in palette sheets, often split across tspans)
const flat = all.replace(/<[^>]*>/g, "").replace(/\s+/g, " ");
const named = [...new Set(flat.match(/[A-Z][A-Za-z /]{2,30}\s*Hex:\s*#\s*[0-9A-Fa-f ]{6,8}/g) || [])]
  .map(s => s.replace(/#\s*([0-9A-Fa-f ]+)/, (_, h) => "#" + h.replace(/ /g, "").slice(0, 6).toUpperCase()));
console.log("Named swatches:\n  " + (named.join("\n  ") || "(none found)"));

const counts = {};
for (const h of all.match(/#[0-9a-fA-F]{6}\b/g) || []) counts[h.toUpperCase()] = (counts[h.toUpperCase()] || 0) + 1;
console.log("\nMost-used colours:\n  " + Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([h, n]) => `${h} x${n}`).join("\n  "));

const fams = {};
for (const m of all.matchAll(/font-family:\s*([^;"}]+)/g)) { const f = m[1].trim(); fams[f] = (fams[f] || 0) + 1; }
console.log("\nFont families:\n  " + (Object.entries(fams).map(([f, n]) => `${f} x${n}`).join("\n  ") || "(text is outlined, none)"));

// installed font files whose name matches a family word
const fontDirs = [
  "C:/Windows/Fonts",
  path.join(os.homedir(), "AppData/Local/Microsoft/Windows/Fonts"),
  "/Library/Fonts", path.join(os.homedir(), "Library/Fonts"),
].filter(d => fs.existsSync(d));
const words = new Set(Object.keys(fams).flatMap(f => f.split(/[,\s'-]+/)).map(w => w.toLowerCase()).filter(w => w.length > 3 && !/^(bold|regular|medium|black|light|italic|semibold|signature|script|display|personal|only)$/.test(w)));
const hits = fontDirs.flatMap(d => fs.readdirSync(d).filter(f => [...words].some(w => f.toLowerCase().includes(w))).map(f => path.join(d, f).replace(/\\/g, "/")));
console.log("\nInstalled font files matching:\n  " + (hits.join("\n  ") || "(none: use Google Fonts lookalikes)"));
console.log("\nCheck: render the kit (it may label fonts wrongly, e.g. a sans called 'Canela'). Trust the picture, not the name.");

const markFile = opt("--mark");
if (markFile) {
  const src = fs.readFileSync(path.isAbsolute(markFile) ? markFile : path.join(kit, markFile), "utf8");
  const vb = opt("--viewbox") || (src.match(/viewBox="([^"]+)"/) || [])[1] || "0 0 100 100";
  const paths = [...src.matchAll(/<(path|polygon|circle|ellipse|rect)\b([^>]*?)\/?>/g)]
    .map(([, tag, attrs]) => `<${tag}${attrs.replace(/\s(class|style|fill|stroke)="[^"]*"/g, "")}/>`);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}" fill="currentColor">${paths.join("")}</svg>`;
  const out = opt("--out");
  if (out) fs.writeFileSync(out, svg);
  console.log(`\nMark: ${paths.length} shapes, viewBox ${vb}${out ? ` -> ${out}` : ""}`);
  if (!out) console.log(svg.slice(0, 300) + "...");
}
