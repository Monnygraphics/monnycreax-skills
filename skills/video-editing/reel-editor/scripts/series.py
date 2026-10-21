"""Series kit: set up shared assets ONCE per series so each reel costs only a few lines of batch.json.

  python series.py kit <batch.json> [--music <file|url>]
      Picks a whoosh, pop, paper and click from cfg["sfx_library"] (folders), copies them plus the music bed into
      <out>/_kit/, and writes cfg "sfx" / "music" / "music_dir" back into batch.json. Prints one short line.
  python series.py broll <batch.json> <candidates.json>
      candidates.json = {query: [pexels photo ids]} from the browser snippet in references/series-mode.md.
      Every reel b-roll entry {"phrase", "q"} gets the first photo id not used anywhere in the series
      (ids kept in <out>/_kit/used.json, so no photo repeats across reels or batches). Downloads the 1440px jpg
      to <out>/_kit/broll/, sets "src", and writes ONE contact sheet <out>/_kit/broll-sheet.jpg (read it once).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130"}
SFX = {  # role: (filename keywords, min s, max s)
    "whoosh": (("whoosh", "swoosh", "swish", "woosh"), 0.35, 1.4),
    "pop": (("pop", "bubble"), 0.05, 0.6),
    "paper": (("paper", "page", "newspaper"), 0.3, 1.6),
    "click": (("click", "mouse"), 0.03, 0.5),
    "chime": (("chime", "marimba", "ding", "positive", "bell"), 0.4, 4.0),
}


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def get(url, dst):
    req = urllib.request.Request(url, headers={**UA, "Referer": "https://www.pexels.com/"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def save(p, d):
    Path(p).write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")


def kit(bj, music=None):
    cfg = load(bj)
    k = Path(os.path.expandvars(cfg["out"])) / "_kit"
    (k / "sfx").mkdir(parents=True, exist_ok=True)
    files = [p for root in cfg.get("sfx_library", []) for p in Path(root).rglob("*")
             if p.suffix.lower() in (".wav", ".mp3")]
    picked = {}
    for role, (keys, lo, hi) in SFX.items():
        want = cfg.get("sfx_pick", {}).get(role)   # explicit override: a path
        cands = [Path(want)] if want else sorted(p for p in files if any(x in p.name.lower() for x in keys))
        for p in cands:
            if lo <= dur(p) <= hi:
                dst = k / "sfx" / f"{role}{p.suffix.lower()}"
                shutil.copy2(p, dst)
                picked[role] = str(dst)
                break
    sx = {"file": picked.get("whoosh"), "card_file": picked.get("paper") or picked.get("whoosh"),
          "pop": picked.get("pop") or picked.get("click"), "chime": picked.get("chime"), "db": -20, "card_db": -16, "pop_db": -18}
    cfg["sfx"] = {a: b for a, b in sx.items() if b is not None}
    if music:
        dst = k / ("music" + (Path(music).suffix if not music.startswith("http") else ".mp3"))
        if music.startswith("http"):
            get(music, dst)
        elif Path(music).resolve() != dst.resolve():   # re-running the kit with its own bed: nothing to copy
            shutil.copy2(music, dst)
        cfg["music_dir"], cfg["music"] = str(k), dst.name
    save(bj, cfg)
    print("kit:", ", ".join(f"{r}={Path(p).name}" for r, p in picked.items()), "| music:", cfg.get("music"))


def broll(bj, cj):
    cfg, cand = load(bj), load(cj)
    k = Path(os.path.expandvars(cfg["out"])) / "_kit"
    bd = k / "broll"
    bd.mkdir(parents=True, exist_ok=True)
    up = k / "used.json"
    used = set(load(up)) if up.exists() else set()
    cfg["broll_dir"] = str(bd)
    tiles, miss = [], []
    for r in cfg["reels"]:
        for b in r.get("broll", []):
            if b.get("src") and (bd / b["src"]).exists():
                used.add(re.sub(r"\D", "", b["src"]))
                tiles.append((r["id"], bd / b["src"]))
                continue
            pid = dst = None
            for i in (str(x) for x in cand.get(b.get("q", ""), []) if str(x) not in used):
                dst = bd / f"px{i}.jpg"
                try:   # some newer photos use another file name: skip to the next candidate
                    if not dst.exists():
                        get(f"https://images.pexels.com/photos/{i}/pexels-photo-{i}.jpeg?auto=compress&cs=tinysrgb&w=1440", dst)
                    pid = i
                    break
                except Exception:
                    dst.unlink(missing_ok=True)
            if not pid:
                miss.append(f"{r['id']}:{b.get('q')}")
                continue
            b["src"] = dst.name
            used.add(pid)
            tiles.append((r["id"], dst))
    save(bj, cfg)
    save(up, sorted(used))
    if tiles:  # one small sheet for the whole series: 6 across, 160px tiles, labelled with the reel number
        args, fl = [], []
        for n, (rid, p) in enumerate(tiles):
            args += ["-i", str(p)]
            fl.append(f"[{n}:v]scale=160:284:force_original_aspect_ratio=increase,crop=160:284,"
                      rf"drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='{rid[:2]}':x=6:y=6:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6[t{n}]")
        cols = 6
        lay = "|".join(f"{(i % cols) * 160}_{(i // cols) * 284}" for i in range(len(tiles)))
        fl.append("".join(f"[t{i}]" for i in range(len(tiles))) +
                  (f"xstack=inputs={len(tiles)}:layout={lay}:fill=black[o]" if len(tiles) > 1 else "null[o]"))
        subprocess.run(["ffmpeg", "-y", "-v", "error", *args, "-filter_complex", ";".join(fl), "-map", "[o]",
                        "-frames:v", "1", str(k / "broll-sheet.jpg")], check=True)
    print(f"broll: {len(tiles)} photos, sheet {k / 'broll-sheet.jpg'}" + (f" | MISSING {miss}" if miss else ""))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["kit"]:
        kit(a[1], a[a.index("--music") + 1] if "--music" in a else None)
    elif a[:1] == ["broll"]:
        broll(a[1], a[2])
    else:
        print(__doc__)
