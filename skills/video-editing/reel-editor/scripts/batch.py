"""Batch-edit many reels unattended (overnight runs).

Usage: python batch.py <batch.json> [--only 03,07] [--worker 0 --workers 2]

batch.json:
{
  "footage": "D:/footage/client-a",                       # folder with the source clips
  "out": "%LOCALAPPDATA%/claude-work/reel-editor/client-a",   # hidden working folder, one sub-folder per reel
  "deliver": "D:/footage/client-a/Edited reels",          # optional: only the finished <title or id>.mp4 files land here
  "defaults": { ...edit.json fields applied to every reel (brand, grade, base_zoom, captions...) },
  "pillars": { "Marriage & Family": {"template": "pill", "transition": "wave", ...}, ... },
  "reels": [
    {"id": "02-empowerment", "src": "IMG_0088.mov", "pillar": "Marriage & Family",
     "hook": "Somebody's going to be upset with this one, but I said it.",
     "cards": [{"phrase": "aggressiveness ... marketplace", "text": "Empowered at work.\\nSubmitted at home."}],
     "emphasis": ["submission"], "fix": [["bedroom", "boardroom"]], "exclude": "", "hold": 0}
  ]
}
Card and hook times are found by matching the phrase against the cut transcript, so they survive re-cuts.
Each reel writes <out>/<id>/final.mp4, preview.jpg, check.jpg and a line in <out>/batch-log.jsonl.
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = [sys.executable, str(HERE / "reel_edit.py")]
ENV = {"PYTHONIOENCODING": "utf-8"}


def sh(args, cwd=None):
    import os
    env = {**os.environ, **ENV}
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if r.returncode:
        raise RuntimeError(f"{' '.join(map(str, args[:3]))} failed:\n{r.stderr[-2500:]}")
    return r.stdout


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def find_phrase(words, phrase, after=0.0):
    """Best fuzzy window match of phrase in words -> (start_idx, end_idx, ratio)."""
    target = [norm(x) for x in phrase.split() if norm(x)]
    toks = [norm(w["w"]) for w in words]
    n, best = len(target), (None, None, 0.0)
    for i in range(len(toks)):
        if words[i]["s"] < after:
            continue
        for L in (n - 1, n, n + 1):
            if L <= 0 or i + L > len(toks):
                continue
            r = difflib.SequenceMatcher(None, target, toks[i:i + L]).ratio()
            if r > best[2]:
                best = (i, i + L - 1, r)
    return best


def apply_fixes(words, fixes):
    """fix: [["a red", "Aret"], ["bedroom", "boardroom"]] - phrase-level, keeps punctuation and timings."""
    for src, dst in fixes or []:
        sw = [norm(x) for x in src.split()]
        i = 0
        while i <= len(words) - len(sw):
            if [norm(w["w"]) for w in words[i:i + len(sw)]] == sw:
                tail = re.sub(r"^.*?([.,!?;:]*)$", r"\1", words[i + len(sw) - 1]["w"])
                lead_cap = words[i]["w"][:1].isupper()
                d = dst[0].upper() + dst[1:] if lead_cap and dst[:1].isalpha() else dst
                words[i:i + len(sw)] = [{"w": d + tail, "s": words[i]["s"], "e": words[i + len(sw) - 1]["e"]}]
            i += 1
    return words


def opening_line(words, max_words=16):
    """Her own first sentence (the hook in her words) -> (text, index of its last word)."""
    end = None
    for k, w in enumerate(words[:max_words]):
        if re.search(r"[.!?][\"'\u201d]?$", w["w"]):
            end = k
            break
    if end is None:  # long first sentence: stop at a comma after 5+ words, else at max_words
        commas = [k for k, w in enumerate(words[:max_words]) if k >= 5 and w["w"].endswith(",")]
        end = commas[0] if commas else min(len(words), max_words) - 1
    text = " ".join(w["w"] for w in words[:end + 1]).rstrip(",;:")
    if not re.search(r"[.!?]$", text):
        text += "\u2026"
    return text, end


def place(words, phrase, busy, after, dur, min_len, max_len, pad_before=0.15):
    """Find phrase on the cut timeline, return (start, end, ratio) clear of busy ranges, or None."""
    i, j, ratio = find_phrase(words, phrase, after=after)
    if i is None or ratio < 0.65:
        return None, ratio
    s = max(0.0, words[i]["s"] - pad_before)
    e = min(max(words[j]["e"] + 0.3, s + min_len), s + max_len, dur - 0.5)
    if any(not (e <= a or s >= b) for a, b in busy):
        return None, -1
    return (round(s, 2), round(e, 2)), ratio


def stray_lead(words):
    """A slate word or false start before a long pause ('First.', 'Sir.', 'Actually.') -> source end time."""
    if len(words) > 3:
        for k in (1, 2):
            if words[k]["s"] - words[k - 1]["e"] > 0.7:
                return words[k]["s"] - 0.15
    return None


def run_reel(cfg, r, log):
    t0 = time.time()
    footage, out = Path(cfg["footage"]), Path(os.path.expandvars(cfg["out"]))
    d = out / r["id"]
    d.mkdir(parents=True, exist_ok=True)
    if (d / "final.mp4").exists() and not r.get("force"):
        return {"id": r["id"], "status": "skip (final exists)"}
    src = footage / r["src"]
    status = {"id": r["id"], "src": r["src"], "notes": []}

    # 1. accurate transcript
    wj = d / "words.json"
    mapped = out / "_map" / f"{Path(r['src']).stem}.json"   # series mode transcribes every clip up front
    if not wj.exists() and mapped.exists():
        shutil.copy2(mapped, wj)
    if not wj.exists():
        sh(P + ["transcribe", str(src), "--out", str(wj), "--model", cfg.get("model", "small"), "--language", "en"])
    data = json.loads(wj.read_text(encoding="utf-8"))
    data["words"] = apply_fixes(data["words"], r.get("fix"))
    for t, txt in r.get("fix_at", []):   # positional caption fixes from align.py
        for w in data["words"]:
            if abs(w["s"] - t) < 0.02:
                w["w"] = txt
                break
    wj.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    # 2. cut (drop a stray slate word at the start)
    excl = r.get("exclude", "")
    lead = stray_lead(data["words"]) if r.get("trim_lead", True) else None
    if lead:
        excl = ",".join(x for x in [f"0-{lead:.2f}", excl] if x)
        status["notes"].append(f"dropped stray opening '{data['words'][0]['w']}'")
    # voice polish only for bad audio (noise, background, echo, heavy/thin, clipping); "audio": "force"|"off" per reel
    polished = None
    if r.get("audio", cfg.get("audio", "auto")) != "off":
        ar = json.loads(sh(P + ["audio", str(src), "--out", str(d), "--words", str(wj)]
                           + (["--force"] if r.get("audio") == "force" else [])))
        polished = Path(ar["use_for_cut"]) if ar.get("action") == "polished" else None
        if polished:
            status["notes"].append("voice polish: " + ", ".join(ar.get("problems") or ["forced"]))
    cut_args = P + ["cut", str(src), "--words", str(wj), "--out", str(d)]
    if r.get("audio", cfg.get("audio", "auto")) != "off" and polished:
        cut_args += ["--audio-from", str(polished)]   # decide cuts on the original, take the cleaned sound
    if excl:
        cut_args += ["--exclude", excl]
    if cfg.get("silence_db") is not None:   # tighter pause detection for noisy rooms (e.g. -12)
        cut_args += ["--silence-db", str(cfg["silence_db"])]
    hold = r.get("hold", cfg.get("outro", {}).get("hold", 0) if cfg.get("outro") and r.get("outro", True) else 0)
    if hold:
        cut_args += ["--hold", str(hold)]
    status["cut"] = json.loads(sh(cut_args))

    # 3. plan + fill
    pil = cfg.get("pillars", {}).get(r.get("pillar"), {})
    rot = cfg.get("transitions", ["hex", "wave", "disc", "blinds", "arc"])   # OG wipes rotate across a series
    tpl = r.get("template", pil.get("template", cfg.get("template", "pill")))
    trn = r.get("transition", pil.get("transition", rot[r.get("_k", 0) % len(rot)]))
    sh(P + ["plan", str(d), "--template", tpl, "--transition", trn, "--zoom", str(cfg.get("zoom", 1.28)), "--force"])
    edit = json.loads((d / "edit.json").read_text(encoding="utf-8"))
    cw = json.loads((d / "cut_words.json").read_text(encoding="utf-8"))
    words, dur = cw["words"], cw["duration"]
    for k, v in cfg.get("defaults", {}).items():
        edit[k] = v
    for k, v in pil.items():
        if k not in ("template", "transition"):
            edit[k] = v
    edit["emphasis"] = r.get("emphasis", [])

    busy = []  # occupied ranges (hook, cards, b-roll) so overlays never collide
    hook = r.get("hook", cfg.get("hook", "auto"))
    if hook == "auto" and words:
        text, k = opening_line(words)
        edit["hook"] = {"text": text, "start": 0, "end": round(min(words[k]["e"] + 0.35, dur), 2), "hideCaps": True}
        busy.append((0, edit["hook"]["end"]))
        status["hook"] = text
    elif hook:
        i, j, ratio = find_phrase(words[:40], hook)
        if ratio >= 0.6 and i is not None and i <= 3:
            end = min(words[j]["e"] + 0.35, dur)
            edit["hook"] = {"text": hook, "start": 0, "end": round(end, 2), "hideCaps": True}
        else:
            # a curated hook (her strongest claim, not her lead-in): own the first seconds, captions resume after
            edit["hook"] = {"text": hook, "start": 0, "end": r.get("hook_end", 3.6), "hideCaps": True}
        busy.append((0, edit["hook"]["end"]))
    if cfg.get("intro_overlay"):   # keep cards and b-roll clear of the title overlay
        il = cfg.get("intro_len", 3.6)
        busy.append((0, il))
        # title legibility (Monny, Oct 2026): blur + dim the footage and switch captions off under the title
        edit["blur"] = [{"start": 0, "end": il, "dim": cfg.get("intro_dim", 0.38)}]
        edit["nocaps"] = [{"start": 0, "end": il}]
    g = r.get("glass")   # glass hook box: what the video is about, right after the title, captions hidden under it
    if g:
        gs = cfg.get("intro_len", 3.6) + 0.1 if cfg.get("intro_overlay") else 0.3
        ge = min(gs + g.get("hold", 5.0), dur - 1)
        edit["hook"] = {"text": g["text"], "kicker": g.get("kicker"), "style": "glass", "start": round(gs, 2),
                        "end": round(ge, 2), "hideCaps": True}
        busy.append((gs, ge))
    intro = cfg.get("intro")
    if intro and r.get("intro", True):
        edit["intro"] = {"logo": intro["logo"], "kicker": r.get("pillar") or intro.get("kicker", ""),
                         "end": intro.get("end", 3.0)}
    elif r.get("pillar") and r.get("tag", True):
        ts = busy[-1][1] + 0.3 if busy else 0.5
        edit["tag"] = {"text": r["pillar"], "start": round(ts, 2), "end": round(ts + 4.5, 2),
                       "color": cfg.get("tag_color")}
    speech_end = cw.get("speech_end", dur)
    first_free = (busy[-1][1] if busy else 0) + 1.0
    cards = []
    for c in r.get("cards", []):
        if c.get("points"):   # points page: opens on `phrase`, each point pops on its own phrase
            i, j, ratio = find_phrase(words, c["phrase"], after=first_free)
            if i is None or ratio < 0.65:
                status["notes"].append(f"points page not placed ({ratio:.2f}): {c['phrase'][:40]}")
                continue
            s, pts, after = max(0.0, words[i]["s"] - 0.15), [], words[i]["s"]
            for p in c["points"]:
                pi, pj, pr = find_phrase(words, p.get("phrase", p["text"]), after=after)
                if pi is None or pr < 0.6:
                    status["notes"].append(f"point not found ({pr:.2f}): {p['text'][:30]}")
                    continue
                pts.append({"text": p["text"], "at": round(words[pi]["s"], 2)})
                after = words[pi]["s"]
            e = min((pts[-1]["at"] if pts else s + 2) + c.get("hold", 1.8), speech_end - 0.3)
            if any(not (e <= a or s >= b) for a, b in busy):
                status["notes"].append(f"points page overlaps: {c['phrase'][:40]}")
                continue
            busy.append((s, e))
            cards.append({"start": round(s, 2), "end": round(e, 2), "text": c["text"], "sub": c.get("sub"),
                          "points": pts, "style": c.get("style", "paper")})
            continue
        got, ratio = place(words, c["phrase"], busy, first_free, speech_end, c.get("min", 2.4), 4.5)
        if not got:
            status["notes"].append(f"card not placed ({ratio:.2f}): {c['phrase'][:40]}")
            continue
        busy.append(got)
        cards.append({"start": got[0], "end": got[1], "text": c["text"], "sub": c.get("sub"),
                      "style": c.get("style", "paper")})
    edit["cards"] = cards
    broll = []
    lays = cfg.get("broll_layouts", ["card", "circle", "split"])
    for bi, b in enumerate(r.get("broll", [])[:r.get("broll_max", cfg.get("broll_max", 3))]):
        b = {"layout": lays[(bi + r.get("_k", 0)) % len(lays)], **b}
        got, ratio = place(words, b["phrase"], busy, first_free, speech_end, 3.0, 4.6, pad_before=0.25)
        if not got:
            status["notes"].append(f"b-roll not placed ({ratio:.2f}): {b['phrase'][:40]}")
            continue
        busy.append(got)
        broll.append({"start": got[0], "end": got[1], "src": str(Path(cfg.get("broll_dir", "")) / b["src"]),
                      "layout": b.get("layout", pil.get("broll_layout", "full"))})
    edit["broll"] = broll
    mus = r.get("music", pil.get("music", cfg.get("music")))   # series: one bed for every reel
    if isinstance(mus, list) and mus:
        mus = mus[r.get("_pi", 0) % len(mus)]
    if mus:
        edit["music"] = {"src": str(Path(cfg.get("music_dir", "")) / mus),
                         "lufs": pil.get("music_lufs", cfg.get("music_lufs", -33))}
    if pil.get("sfx", cfg.get("sfx")) is not None:
        edit["sfx"] = pil.get("sfx", cfg.get("sfx"))
    for k in ("intro_overlay", "endcard"):   # per-episode cards: "D:/x/{id}_overlay.mov"
        if cfg.get(k) and r.get(k, True):
            edit[k] = cfg[k].format(id=r["id"])
    edit.update(r.get("edit", {}))
    if cfg.get("outro") and r.get("outro", True) and cw.get("speech_end"):
        nxt = r.get("_next_hook")
        edit["outro"] = {"start": round(speech_end + 0.1, 2), "logo": cfg["outro"]["logo"],
                         "next": nxt, "follow": cfg["outro"].get("follow", "Follow for more")}
    (d / "edit.json").write_text(json.dumps(edit, indent=2, ensure_ascii=False), encoding="utf-8")

    # 4. preview strip (kept for review), render, self-check strip
    at = [0.3, max(0.5, edit.get("hook", {}).get("end", 2) - 0.6)] + [c["start"] + 1.0 for c in cards] + \
         [b["start"] + 1.0 for b in broll] + ([edit["outro"]["start"] + 1.2] if edit.get("outro") else []) + \
         [p["start"] + 0.5 for p in edit["punchins"][:3]] + [dur * 0.6, dur - 1.0]
    at = sorted(set(round(min(max(x, 0.1), dur - 0.1), 2) for x in at))[:14]
    if cfg.get("preview", True):   # series mode skips it: the check strip covers the same frames
        sh(P + ["preview", str(d), "--at", ",".join(map(str, at))])
    sh(P + ["render", str(d)])
    fin = d / "final.mp4"
    meta = json.loads(sh(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                          "stream=nb_frames,duration", "-of", "json", str(fin)]))["streams"][0]
    fps = cw.get("fps", 30)
    expect = round(dur * fps)
    if edit.get("endcard"):   # the outro card is appended after the cut
        ec = json.loads(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json",
                            str(d / edit["endcard"])]))["format"]["duration"]
        expect += round(float(ec) * fps)
    status["frames"], status["expected_frames"] = int(meta.get("nb_frames", 0)), expect
    if abs(status["frames"] - expect) > 2:
        status["notes"].append(f"FRAME COUNT MISMATCH {status['frames']} vs {expect}")
    cps = cw.get("cut_points", [])
    chk = sorted(set([0.4] + [round(c + 0.15, 2) for c in cps[:6]] + [dur - 0.6]))[:12]
    sh(P + ["strip", str(fin), "--at", ",".join(map(str, chk)), "--out", str(d / "check.jpg")])
    if cfg.get("deliver"):
        dl = Path(os.path.expandvars(cfg["deliver"])); dl.mkdir(parents=True, exist_ok=True)
        nm = re.sub(r'[<>:"/\|?*]+', "", r.get("title") or r["id"]).strip()
        shutil.copy2(fin, dl / f"{nm}.mp4")
    status.update({"status": "ok", "duration": round(dur, 1), "template": tpl, "transition": trn,
                   "cards": len(cards), "minutes": round((time.time() - t0) / 60, 1)})
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--only", default="")
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()
    cfg = json.loads(Path(a.batch).read_text(encoding="utf-8"))
    reels = cfg["reels"]
    counts = {}
    for k, r in enumerate(reels):  # music rotates inside a pillar; outro names the next reel by her opening line
        r["_k"] = k
        r["_pi"] = counts.get(r.get("pillar"), 0)
        counts[r.get("pillar")] = r["_pi"] + 1
        nxt = reels[k + 1] if k + 1 < len(reels) else None
        if nxt and nxt.get("hook") and nxt["hook"] != "auto":
            r["_next_hook"] = nxt["hook"]
        elif nxt:
            wj = Path(os.path.expandvars(cfg["out"])) / nxt["id"] / "words.json"
            if wj.exists():
                ws = apply_fixes(json.loads(wj.read_text(encoding="utf-8"))["words"], nxt.get("fix"))
                lead = stray_lead(ws)
                if lead:
                    ws = [w for w in ws if w["s"] >= lead]
                r["_next_hook"] = opening_line(ws, 12)[0]
    if a.only:
        keep = set(a.only.split(","))
        reels = [r for r in reels if r["id"].split("-")[0] in keep or r["id"] in keep]
    reels = reels[a.worker::a.workers]
    log = Path(os.path.expandvars(cfg["out"])) / "batch-log.jsonl"
    for r in reels:
        try:
            st = run_reel(cfg, r, log)
        except Exception as e:  # keep going: one bad clip must not stop the night
            st = {"id": r["id"], "status": "error", "error": str(e)[-1500:], "trace": traceback.format_exc()[-800:]}
        st["worker"] = a.worker
        st["at"] = time.strftime("%H:%M:%S")
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(st, ensure_ascii=False) + "\n")
        print(json.dumps({k: st.get(k) for k in ("id", "status", "minutes", "notes")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
