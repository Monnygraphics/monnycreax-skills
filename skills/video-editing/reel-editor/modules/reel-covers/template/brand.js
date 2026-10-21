// Brand config. Fill from the client's brand kit (scripts/brand-from-svg.js helps).
// fonts: local files (Windows paths fine) or set googleFonts instead, e.g. "family=Playfair+Display:wght@700&family=Corinthia:wght@700&family=Jost:wght@500"
window.BRAND = {
  name: "Client Brand",
  fonts: [],
  googleFonts: "family=Playfair+Display:wght@400;700&family=Corinthia:wght@700&family=Jost:wght@500",
  type: { head: "Playfair Display", headWeight: 700, script: "Corinthia", sans: "Jost", headScale: 1, scriptScale: 0.65 },
  colors: {
    // light tile: pale bg, dark brand colour arch.  dark tile: deep brand bg, light/warm arch.
    light: { bg: "#F4EDE3", fg: "#2A211C", script: "#8A6A2F", shape: "#2E231D", line: "#8A6A2F" },
    dark:  { bg: "#2E231D", fg: "#F4EDE3", script: "#CFAE6E", shape: "#D9C4A8", line: "#CFAE6E" },
    full:  { shade: "28,20,15", l1: "#F4EDE3", l2: "#CFAE6E", kickerBg: "#CFAE6E", kickerFg: "#2E231D" },
  },
  wordmark: "CLIENT BRAND",
  mark: "", // inline <svg fill="currentColor">…</svg> from scripts/extract-mark.js, or "" for wordmark only
  tag: ["Episode {ep} of", "The Series", "Name"], // used on arch covers that have ep:
};
