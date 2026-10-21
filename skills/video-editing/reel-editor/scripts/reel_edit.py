"""reel-editor pipeline: raw talking-head footage -> edited 9:16 reel.

Commands
  scan <folder>                          list videos, b-roll, music and brand files in a footage folder
  transcribe <video> --out words.json    word-level transcript (local faster-whisper)
  cut <video> --words words.json --out <dir>
                                         remove pauses, normalise to 1080x1920@30, write <dir>/cut.mp4
                                         + <dir>/cut_words.json (word times remapped, cut points listed)
  plan <dir> [--template apollo|athena|hermes|ares|hestia] [--variant v] [--transition hex] [--title "..."]
                                         draft <dir>/edit.json: punch-ins that hide every jump cut,
                                         title card, empty b-roll list for Claude to fill
  color <dir> [--apply] [--look skin] [--compare all]
                                         analyse cut.mp4 colour (white balance, exposure, levels), write the
                                         correction into edit.json grade, looks.jpg side-by-side sheet
  render <dir> [--frames-only] [--keep-frames]
                                         overlay frames (Chrome) + punch-ins + audio mix -> <dir>/final.mp4
  preview <dir> --at 2,9.5 [--override '{"template":"ghost"}']
                                         overlay composited at a few moments -> <dir>/preview.jpg (seconds)
  stills <video> --out <folder> [--n 12]  sharp speaker frames for reel-covers thumbnails
  assemble <spec.json> --out joined.mp4  join chosen ranges from several clips/takes (+ remapped words)
  timeline <video> <start> <end> --out t.png
                                         filmstrip + waveform for a cut decision
  export <final.mp4> --aspect 4:5|1:1|16:9
                                         other platforms (LinkedIn/feed crop, YouTube blurred fill)
  strip <video> --at 1,5,9.5 --out strip.jpg
                                         one contact strip of frames for review
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
W, H = 1080, 1920
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
# All working files (transcripts, cuts, previews, check sheets, frames) live here, out of the user's sight.
# The user's folder only ever receives the finished video, via `deliver`.
WORK_ROOT = Path(os.environ.get("REEL_WORK") or
                 Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache") / "claude-work" / "reel-editor")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "reel"


def work_dir(video):
    """Hidden working folder for one source video: WORK_ROOT/<footage-folder>/<video>/."""
    v = Path(video).resolve()
    d = WORK_ROOT / slug(v.parent.name) / slug(v.stem)
    d.mkdir(parents=True, exist_ok=True)
    return d


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(f"command failed: {cmd[0]}")
    return r.stdout


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
               "-of", "json", str(path)])
    d = json.loads(out)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), {})
    return {"duration": float(d["format"]["duration"]), "width": v.get("width"), "height": v.get("height"),
            "fps": v.get("r_frame_rate"), "audio": any(s["codec_type"] == "audio" for s in d["streams"])}


def pick_fps(info, want):
    """Keep the source rate when it is a clean 24/25/30 (no judder from duplicated frames), else 30."""
    if want and want != "auto":
        return int(want)
    try:
        n, d = (info.get("fps") or "30/1").split("/")
        f = round(float(n) / float(d))
    except (ValueError, ZeroDivisionError):
        f = 30
    return f if f in (24, 25, 30) else 30


def dir_fps(d):
    try:
        return int(json.loads((Path(d) / "cut_words.json").read_text(encoding="utf-8")).get("fps", 30))
    except FileNotFoundError:
        return 30


def out_json(obj):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------- work / deliver
def cmd_work(a):
    """Print (and create) the hidden working folder for a source video. Use it as <dir> for every step."""
    out_json({"dir": str(work_dir(a.video))})


def cmd_deliver(a):
    """Copy the one finished file into the user's folder, named for people, and nothing else."""
    d = Path(a.dir)
    src = d / ("final.mp4" if not a.file else a.file)
    if not src.exists():
        raise SystemExit(f"nothing to deliver: {src} missing")
    to = Path(a.to); to.mkdir(parents=True, exist_ok=True)
    name = re.sub(r'[<>:"/\|?*]+', "", a.name).strip() or "reel"
    dest = to / f"{name}{src.suffix}"
    shutil.copy2(src, dest)
    out_json({"delivered": str(dest), "mb": round(dest.stat().st_size / 1e6, 1)})


# ---------------------------------------------------------------- scan
def cmd_scan(a):
    root = Path(a.folder)
    found = {"videos": [], "broll": [], "music": [], "brand": [], "other": []}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or "reel-edit" in p.parts:
            continue
        ext, rel = p.suffix.lower(), str(p.relative_to(root))
        low = rel.lower()
        if ext in VIDEO_EXT and "broll" not in low and "b-roll" not in low:
            try:
                found["videos"].append({"path": str(p), **probe(p)})
            except SystemExit:
                found["other"].append(rel)
        elif ext in IMAGE_EXT and ("broll" in low or "b-roll" in low):
            found["broll"].append(str(p))
        elif ext in VIDEO_EXT:
            found["broll"].append(str(p))
        elif ext in AUDIO_EXT:
            found["music"].append(str(p))
        elif any(k in low for k in ("brand", "logo", "kit", "colour", "color", "font")):
            found["brand"].append(str(p))
        else:
            found["other"].append(rel)
    out_json(found)


# ---------------------------------------------------------------- transcribe
MIX_PROMPTS = {
    "sw": "Kenyan English with Swahili and Sheng: pekee, juu ya hii, kwa hizo, ama ni, sasa, wewe, hii ni, "
          "si ndio, manze, poa, sawa, kabisa, Mungu, maisha, pesa, biashara, watu, hapana, ndio, hiyo.",
}


def cmd_transcribe(a):
    from faster_whisper import WhisperModel
    # default 4 CPU threads is fastest here: 12 threads measured slower (39s vs 33s for 60s of audio, Oct 2026)
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    # a disfluent prompt makes Whisper write "um"/"uh" instead of silently dropping them, so cut can remove them
    prompt = None if a.clean else "Umm, so, uh, I mean, like, you know, I was, uh, thinking."
    lang = a.language
    if a.mix:
        # mixed-language speech: auto-detect labels the whole clip as the minority language and the model then
        # "translates" English words into nonsense; transcribing as English with the other language's common
        # words in the prompt keeps both languages as spoken. Claude still proofreads the result (SKILL step 4).
        lang = lang or "en"
        prompt = ((prompt + " ") if prompt else "") + MIX_PROMPTS.get(a.mix, "")
    if a.vocab:
        prompt = ((prompt + " ") if prompt else "") + a.vocab.replace(",", ", ") + "."
    segs, info = model.transcribe(a.video, language=lang, word_timestamps=True, vad_filter=True,
                                  initial_prompt=prompt)
    words, segments = [], []
    for s in segs:
        segments.append({"s": round(s.start, 3), "e": round(s.end, 3), "text": s.text.strip()})
        for w in s.words or []:
            t = w.word.strip()
            if not t:
                continue
            # Whisper splits some words into fragments ("single" + "-hood"); a fragment has no leading space
            if words and (not w.word.startswith(" ") or t.startswith("-")) and t[0] not in "\"'(":
                words[-1]["w"] += t.lstrip("-") if words[-1]["w"].isalpha() and t.startswith("-") else t
                words[-1]["e"] = round(w.end, 3)
                continue
            words.append({"w": t, "s": round(w.start, 3), "e": round(w.end, 3)})
    Path(a.out).write_text(json.dumps({"language": info.language, "words": words, "segments": segments},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
    out_json({"out": a.out, "words": len(words), "segments": len(segments), "language": info.language})


# ---------------------------------------------------------------- cut
def keep_ranges(words, dur, max_pause, pad_in, pad_out):
    rng = []
    for w in words:
        s, e = max(0.0, w["s"] - pad_in), min(dur, w["e"] + pad_out)
        if rng and s - rng[-1][1] <= max_pause:
            rng[-1][1] = max(rng[-1][1], e)
        else:
            rng.append([s, e])
    return [r for r in rng if r[1] - r[0] > 0.12]


def silences(src, rel_db, min_len):
    """Measured silent stretches (Whisper word timings stretch across pauses, so words alone miss gaps)."""
    vol = run_err(["ffmpeg", "-hide_banner", "-i", str(src), "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"])
    m = re.search(r"mean_volume: (-?[\d.]+) dB", vol)
    thr = (float(m.group(1)) if m else -30.0) + rel_db
    log = run_err(["ffmpeg", "-hide_banner", "-i", str(src), "-map", "0:a:0",
                   "-af", f"silencedetect=n={thr:.1f}dB:d={min_len}", "-f", "null", "-"])
    st = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    en = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", log)]
    return list(zip(st, en)), thr


def subtract(rng, gaps, pad_in, pad_out, keep):
    """Remove each silent gap from the keep ranges, leaving pad_out after speech and pad_in before it."""
    out = [list(r) for r in rng]
    for gs, ge in gaps:
        cs, ce = gs + pad_out, ge - pad_in   # the part of the silence we actually remove
        if ce - cs < keep:
            continue
        nxt = []
        for a, b in out:
            if ce <= a or cs >= b:
                nxt.append([a, b])
            else:
                if cs > a:
                    nxt.append([a, cs])
                if ce < b:
                    nxt.append([ce, b])
        out = nxt
    return [r for r in out if r[1] - r[0] > 0.12]


def envelope(src, rate=16000, hop=0.005, win=0.02):
    """Short-window loudness (dBFS) every `hop` seconds, from the source audio."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-map", "0:a:0", "-ac", "1", "-ar", str(rate),
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    h, n = int(rate * hop), int(rate * win)
    if len(x) < n:
        return np.zeros(1), hop
    sq = np.concatenate([[0.0], np.cumsum(x * x)])
    starts = np.arange(0, len(x) - n, h)
    rms = np.sqrt((sq[starts + n] - sq[starts]) / n)
    return 20 * np.log10(rms + 1e-6), hop


def snap_ranges(rng, env, hop, kept_words, look_in=0.25, look_out=0.35):
    """Move every cut into the quietest 20 ms nearby: Whisper word starts are reliable but ends often come
    early, so an out-point waits for the sound to die. Never crosses into a neighbouring kept word.
    Returns the snapped ranges and warnings for cuts that still land on sound."""
    import numpy as np
    starts = sorted(w["s"] for w in kept_words)
    ends = sorted(w["e"] for w in kept_words)
    db = lambda t: float(env[min(len(env) - 1, max(0, int(t / hop)))])
    floor = float(np.percentile(env, 10))
    speech = float(np.percentile(env, 80))
    # "on sound" = within 25 dB of speech; a deep denoised floor must not make room tone count as sound
    loud = max(floor + 0.45 * (speech - floor), speech - 25)
    def quietest(a, b):
        """Middle of the longest quiet run in [a, b] (within 6 dB of the window's floor). The single quietest frame
        can sit in a dip inside a word (a plosive), which clips it; a run is real silence between words."""
        i, j = max(0, int(a / hop)), min(len(env) - 1, int(b / hop))
        if j <= i:
            return a
        seg = env[i:j + 1]
        quiet = seg <= seg.min() + 6
        best, cur, bs, cs = 0, 0, 0, 0
        for n, qv in enumerate(quiet):
            if qv:
                if cur == 0:
                    cs = n
                cur += 1
                if cur > best:
                    best, bs = cur, cs
            else:
                cur = 0
        return (i + bs + best // 2) * hop
    out, warn = [], []
    for k, (a, b) in enumerate(rng):
        prev_end = max([e for e in ends if e <= a + 0.05] or [0.0])
        next_start = min([x for x in starts if x >= b - 0.05] or [b + look_out])
        lo = max(a - look_in, prev_end + 0.02, out[-1][1] if out else 0.0)
        na = quietest(lo, a + 0.02) if a - lo > 0.01 else a
        hi = min(b + look_out, next_start - 0.02)
        nb = quietest(b - 0.02, hi) if hi - b > 0.01 else b
        if nb - na < 0.12:
            na, nb = a, b
        out.append([round(na, 3), round(nb, 3)])
        for t, side in ((na, "in"), (nb, "out")):
            if db(t) > loud:
                warn.append({"source_t": round(t, 2), "side": side, "db": round(db(t), 1)})
    return out, warn


NUM = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                  "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
NUM.update({w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())})
SCALE = {"hundred": 100, "thousand": 1000, "million": 10 ** 6, "billion": 10 ** 9}
UNITS = {"percent", "per", "shillings", "shilling", "dollars", "years", "minutes", "hours", "days", "months",
         "weeks", "people", "times", "kes", "ksh"}


def digits_in_captions(words):
    """Spoken numbers as digits on screen ("twenty five" -> 25, "a hundred percent" -> 100%). Keeps small
    standalone numbers as words ("one time", "two of them") unless a unit follows. Timing spans the run."""
    out, i = [], 0
    bare = lambda w: re.sub(r"[^a-z-]", "", w.lower())
    while i < len(words):
        j, total, cur, seen = i, 0, 0, False
        if bare(words[i]["w"]) == "a" and i + 1 < len(words) and bare(words[i + 1]["w"]) in SCALE:
            j, cur, seen = i + 1, 1, True   # "a hundred" / "a million"
        while j < len(words):
            t = bare(words[j]["w"])
            parts = t.split("-")
            if all(p in NUM for p in parts) and parts[0]:
                v = sum(NUM[p] for p in parts)
                if 10 <= cur < 100 and v >= 10 and total == 0:   # "twenty twenty six" is a year: 2026
                    cur = cur * 100 + v
                else:
                    cur += v
                seen = True; j += 1
            elif t in SCALE and seen:
                if SCALE[t] == 100:
                    cur = max(cur, 1) * 100
                else:
                    total += max(cur, 1) * SCALE[t]; cur = 0
                j += 1
            elif t == "and" and seen and j + 1 < len(words) and bare(words[j + 1]["w"]).split("-")[0] in NUM:
                j += 1
            else:
                break
        if not seen:
            out.append(words[i]); i += 1; continue
        val = total + cur
        nxt = bare(words[j]["w"]) if j < len(words) else ""
        unit = nxt in UNITS
        if val < 10 and not unit and j - i == 1:
            out.append(words[i]); i += 1; continue
        punct = re.sub(r"^.*?([.,!?;:]*)$", r"", words[j - 1]["w"])
        txt = (f"{val / 10 ** 9:g} billion" if val >= 10 ** 9 and val % 10 ** 7 == 0 else
               f"{val / 10 ** 6:g} million" if val >= 10 ** 6 and val % 10 ** 4 == 0 else
               str(val) if 1900 <= val <= 2100 else f"{val:,}")
        e = words[j - 1]["e"]
        if nxt == "percent" or (nxt == "per" and j + 1 < len(words) and bare(words[j + 1]["w"]) == "cent"):
            k = j + (2 if nxt == "per" else 1)
            punct = re.sub(r"^.*?([.,!?;:]*)$", r"", words[k - 1]["w"]); e = words[k - 1]["e"]; j = k; txt += "%"
        out.append({**words[i], "w": txt + punct, "e": e})
        i = j
    return out


def run_err(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stderr


FILLERS = {"um", "umm", "uh", "uhh", "uhm", "er", "erm", "ah", "ahh", "hmm", "mm", "mhm"}


def parse_ranges(txt):
    out = []
    for part in (txt or "").split(","):
        if part.strip():
            s, e = part.split("-")
            out.append((float(s), float(e)))
    return out


def cmd_cut(a):
    src = Path(a.video)
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    info = probe(src)
    data = json.loads(Path(a.words).read_text(encoding="utf-8"))
    excl = parse_ranges(a.exclude)
    import autocut
    allw = data["words"]
    fixes = {}                              # word index -> caption spelling fix
    auto_cut, to_check = [], []
    if not a.no_auto:                       # retakes, slates, stumbles: apply the sure ones, report the rest
        # detect on what the manual excludes keep: an excluded bad take must not make the kept take look like a retake
        for r in autocut.detect([w for w in allw if not any(s <= w["s"] < e for s, e in excl)]):
            (auto_cut if r["sure"] else to_check).append(r)
        excl += [(r["start"], r["end"]) for r in auto_cut]
    if a.text:                              # edit-by-text: deleted words are cut, respelled words become caption fixes
        rr, fx = autocut.from_text(allw, Path(a.text).read_text(encoding="utf-8"))
        excl += rr
        fixes.update({f["i"]: f["to"] for f in fx})
    if a.review:                            # the review page's "Copy for Claude" JSON
        rv = json.loads(Path(a.review).read_text(encoding="utf-8"))
        excl += parse_ranges(rv.get("exclude", ""))
        for f in rv.get("fixes", []):
            i = min(range(len(allw)), key=lambda k: abs(allw[k]["s"] - f["t"]))
            fixes[i] = f["to"]
    for i, t in fixes.items():
        allw[i] = {**allw[i], "w": t}
    words = [w for w in allw
             if not (a.keep_fillers is False and re.sub(r"[^a-z]", "", w["w"].lower()) in FILLERS)
             and not any(s <= w["s"] < e for s, e in excl)]
    dropped = len(data["words"]) - len(words)
    rng = keep_ranges(words, info["duration"], a.max_pause, a.pad_in, a.pad_out) if not a.no_cut \
        else [[0.0, info["duration"]]]
    gaps, thr = ([], None)
    if not a.no_cut and a.silence_db is not None:
        gaps, thr = silences(src, a.silence_db, a.max_pause)
        # a "silence" that covers the start of a spoken word is soft speech, not a pause: never cut it
        # (at -12 dB a quiet opening read as silent and 45 words vanished from a reel, Oct 2026)
        on = [(w["s"], w["s"] + min(0.35, max(0.08, w["e"] - w["s"]))) for w in words]
        gaps = [(gs, ge) for gs, ge in gaps if not any(gs < oe and ge > os_ for os_, oe in on)]
        rng = subtract(rng, gaps, a.pad_in, a.pad_out + 0.04, 0.12)
    warns = []
    if not a.no_cut and not a.no_snap:
        env, hop = envelope(src)
        rng, warns = snap_ranges(rng, env, hop, words)

    # put every cut on the source's frame grid: a trimmed picture holds whole frames while its sound doesn't, so
    # off-grid cuts lose up to a frame of picture per segment and the lips drift ahead of the voice
    # (measured: 0.145 s by the end of a 17-segment reel before this)
    num, _, den = (info.get("fps") or "30/1").partition("/")
    sfps = float(num) / float(den or 1) if float(num or 0) > 0 else 30.0
    q = lambda t: round(round(t * sfps) / sfps, 6)
    rng = [[q(s0), q(e0)] for s0, e0 in rng if q(e0) - q(s0) >= 3 / sfps]
    a.jcut = round(a.jcut * sfps) / sfps

    fps = pick_fps(info, a.fps)
    sp = a.speed
    short = min(info.get("width") or W, info.get("height") or H)
    cw_, ch_ = (1440, 2560) if (short >= 2000 and not a.lowres) else (W, H)
    # drop to the output frame rate BEFORE scaling: a 50 fps 4K 10-bit HEVC camera file otherwise scales every frame
    # it then throws away (10 s of Client B's C0638: 131 s -> 42 s with this order + ultrafast below)
    vf_norm = f"fps={fps},scale={cw_}:{ch_}:force_original_aspect_ratio=increase:flags=bilinear,crop={cw_}:{ch_},setsar=1"
    if sp != 1.0:
        vf_norm = f"setpts=PTS/{sp}," + vf_norm
    lines, labels, alabels = [], "", ""
    # --audio-from: the edit is decided on the original recording (silences, snapping), the sound comes from the
    # voice-polished copy (same timing). Deciding on the cleaned audio moved cut points by up to 0.9 s.
    audio_in, ain = ([], "0:a:0")
    if a.audio_from:
        audio_in, ain = ["-i", str(a.audio_from)], "1:a:0"
    jc = a.jcut   # J-cut: the next line is heard before its picture shows (picture switches jc later)
    vsel = []   # one select pass over the source: N trim chains on one 4K input buffered every frame N times (37 min cuts)
    for i, (s, e) in enumerate(rng):
        d = e - s
        vs = s + (jc if i > 0 else 0.0)
        ve = min(info["duration"], e + (jc if i < len(rng) - 1 else 0.0))
        vsel.append(f"between(t,{vs:.4f},{ve - 0.0005:.4f})")
        lines.append(f"[{ain}]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.012,afade=t=out:st={max(0, d - 0.015):.3f}:d=0.015[a{i}];")
        labels += f"[v{i}]"; alabels += f"[a{i}]"
    hold = a.hold
    if hold > 0:  # freeze the last frame (and pad silence) so a closing card can wipe in over her
        vf_norm += f",tpad=stop_mode=clone:stop_duration={hold}"
    apad = f",apad=pad_dur={hold}" if hold > 0 else ""
    atempo = f";[ac0]atempo={sp}{apad}[ac]" if sp != 1.0 else f";[ac0]anull{apad}[ac]"
    # picture and sound concatenate separately: with a J-cut their segment lengths differ, and a joint concat
    # would pad the shorter stream and drift the sync
    lines.append(f"[0:v]select='{'+'.join(vsel)}',setpts=N/FRAME_RATE/TB,{vf_norm}[v];"
                 f"{alabels}concat=n={len(rng)}:v=0:a=1[ac0]{atempo}")
    script = outdir / "cut_filter.txt"
    script.write_text("\n".join(lines), encoding="utf-8")
    cut = outdir / "cut.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), *audio_in, "-filter_complex_script", str(script),
         "-map", "[v]", "-map", "[ac]", "-c:v", "libx264", "-crf", "12", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(cut)])

    # remap words onto the cut timeline
    offsets, acc = [], 0.0
    for s, e in rng:
        offsets.append(acc)
        acc += e - s
    remapped = []
    for w in words:
        for (s, e), off in zip(rng, offsets):
            if s - 0.001 <= w["s"] <= e:
                remapped.append({"w": w["w"], "s": round((w["s"] - s + off) / sp, 3),
                                 "e": round((min(w["e"], e) - s + off) / sp, 3)})
                break
        else:
            # Whisper often stamps a sentence's first word a little early, inside the silence we removed.
            # The audio of the word is kept (the next range starts at the real onset), so keep the caption too:
            # pin it to the start of the range it runs into instead of dropping it.
            for (s, e), off in zip(rng, offsets):
                if w["s"] < s < w["e"] + 0.6:
                    remapped.append({"w": w["w"], "s": round(off / sp, 3),
                                     "e": round((max(min(w["e"], e), s + 0.12) - s + off) / sp, 3)})
                    break
    if not a.no_digits:
        remapped = digits_in_captions(remapped)
    cut_points = [round(o / sp, 3) for o in offsets[1:]]
    removed = info["duration"] - acc / sp
    acc = acc / sp
    speech_end = round(acc, 3)
    acc += hold
    (outdir / "cut_words.json").write_text(json.dumps(
        {"source": str(src), "duration": round(acc, 3), "speech_end": speech_end, "fps": fps, "speed": sp,
         "cut_points": cut_points,
         "words": remapped},
        ensure_ascii=False, indent=1), encoding="utf-8")
    out_json({"cut": str(cut), "source_duration": round(info["duration"], 2), "cut_duration": round(acc, 2),
              "removed_seconds": round(removed, 2), "words_dropped": dropped, "silences_found": len(gaps),
              "silence_threshold_db": None if thr is None else round(thr, 1), "segments": len(rng), "cut_points": len(cut_points),
              "cuts_on_sound": warns[:12],
              "auto_cut": [f"{r['start']:.2f}-{r['end']:.2f} {r['reason']}: {r['text'][:60]}" for r in auto_cut],
              "check": [f"{r['start']:.2f}-{r['end']:.2f} {r['reason']}: {r['text'][:60]}" for r in to_check],
              "caption_fixes": len(fixes)})


# ---------------------------------------------------------------- assemble
def cmd_review(a):
    """OneTake-style transcript review page: strike words to cut, fix captions, copy the result back to Claude."""
    src = Path(a.video).resolve()
    words = json.loads(Path(a.words).read_text(encoding="utf-8"))["words"]
    out = Path(a.out).resolve() if a.out else work_dir(src) / "review.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    proxy = out.parent / "review_proxy.mp4"   # small H.264 copy: browsers can't play iPhone HEVC .mov
    if not proxy.exists():
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", "scale=-2:854", "-c:v", "libx264", "-preset",
             "ultrafast", "-crf", "30", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(proxy)])
    data = {"video": proxy.name, "source": str(src), "title": a.title or src.stem, "slug": src.stem,
            "duration": probe(src)["duration"], "fillers": sorted(FILLERS),
            "strike": [r for r in (a.strike or "").split(",") if r], "words": words}
    html = (HERE / "review" / "review.html").read_text(encoding="utf-8")
    out.write_text(html.replace("/*__DATA__*/{}", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    out_json({"review": str(out), "words": len(words), "prestruck": len(data["strike"]),
              "open": f"http://localhost:{a.port}/review.html" if a.serve else out.as_uri()})
    if a.serve:  # file:// works too; the server is for seeking in browsers that block local video ranges
        subprocess.run([node_bin(), str(HERE / "review" / "serve.js"), str(out.parent), str(a.port)])


def cmd_assemble(a):
    """Join chosen ranges from several takes/clips into one source (best take per line, multi-clip videos).

    spec JSON: [{"src": "IMG_0085.mov", "start": 3.2, "end": 41.0}, ...] in story order. Word timings come from
    each clip's transcript (<transcripts>/<stem>.json), so the joined file needs no re-transcription."""
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    base_dir = Path(a.spec).resolve().parent
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tdir = Path(a.transcripts) if a.transcripts else None

    def resolve(x):
        x = Path(x)
        return x if x.is_absolute() else base_dir / x

    fps = pick_fps(probe(resolve(spec[0]["src"])), a.fps)
    inputs, lines, labels, words, acc = [], [], "", [], 0.0
    for i, seg in enumerate(spec):
        src = resolve(seg["src"])
        info = probe(src)
        s, e = float(seg.get("start", 0)), float(seg.get("end", info["duration"]))
        inputs += ["-i", str(src)]
        lines.append(f"[{i}:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS,"
                     f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},setsar=1[v{i}];")
        lines.append(f"[{i}:a:0]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS,aresample=48000,"
                     f"afade=t=in:d=0.015,afade=t=out:st={max(0, e - s - 0.02):.3f}:d=0.02[a{i}];")
        labels += f"[v{i}]"; alabels += f"[a{i}]"
        tj = (tdir or WORK_ROOT / slug(src.parent.name) / "_transcripts") / f"{src.stem}.json"
        if tj.exists():
            for w in json.loads(tj.read_text(encoding="utf-8"))["words"]:
                if s <= w["s"] < e:
                    words.append({"w": w["w"], "s": round(w["s"] - s + acc, 3),
                                  "e": round(min(w["e"], e) - s + acc, 3)})
        else:
            print(f"no transcript for {src.name}: transcribe the joined file instead", file=sys.stderr)
        acc += e - s
    lines.append(f"{labels}concat=n={len(spec)}:v=1:a=1[v][a]")
    script = out.with_suffix(".filter.txt")
    script.write_text("\n".join(lines), encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex_script", str(script), "-map", "[v]",
         "-map", "[a]", "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", str(out)])
    script.unlink()
    wj = out.with_suffix(".words.json")
    wj.write_text(json.dumps({"language": "en", "words": words, "assembled_from": spec}, ensure_ascii=False,
                             indent=1), encoding="utf-8")
    out_json({"joined": str(out), "words": str(wj), "duration": round(acc, 2), "segments": len(spec), "fps": fps})


# ---------------------------------------------------------------- plan
SENT_END = re.compile(r"[.!?]['\"”]?$")


# Monny's five editing styles carry Olympian names (2026-10-21); each holds variants of the older templates.
# style -> {variant: engine template}; the first variant is the default
GODS = {"apollo": {"default": "apollo", "quiet": "softglass"},   # signature (apollo-style.md); quiet = no captions
        "athena": {"default": "glass"},                          # explainers, frameworks, offers (glass-style.md)
        "hermes": {"default": "story"},                          # case studies, testimonies (story-style.md)
        "ares":   {"default": "hormozi", "bigword": "bigword", "boxcaps": "boxcaps"},   # bold, high energy
        "hestia": {"default": "pill", "ghost": "ghost", "serif": "serifmix"}}           # calm, simple captions
# older names still accepted: engine templates, the first Olympian set, and Apollo's first name
ALIASES = {"atelier": ("apollo", "default"), "artemis": ("apollo", "quiet"), "zeus": ("ares", "bigword"),
           "hephaestus": ("ares", "boxcaps"), "aphrodite": ("hestia", "serif"), "hades": ("hestia", "ghost")}
for _g, _vs in GODS.items():
    for _v, _t in _vs.items():
        if _t not in ("apollo", "softglass"):
            ALIASES.setdefault(_t, (_g, _v))


def resolve_style(name, variant=None):
    """'apollo' / 'ares --variant bigword' / an old name -> (god, variant, engine template)."""
    god, var = (name, variant or "default") if name in GODS else ALIASES.get(name, (None, None))
    if not god:
        raise SystemExit(f"unknown style {name!r}: use one of {', '.join(GODS)}")
    if variant:
        var = variant
    if var not in GODS[god]:
        raise SystemExit(f"{god} has variants: {', '.join(GODS[god])}")
    return god, var, GODS[god][var]


def cmd_plan(a):
    d = Path(a.dir)
    cw = json.loads((d / "cut_words.json").read_text(encoding="utf-8"))
    words, dur = cw["words"], cw["duration"]
    # sentence starts
    starts = [words[0]["s"]] if words else []
    for prev, w in zip(words, words[1:]):
        if SENT_END.search(prev["w"]):
            starts.append(w["s"])
    # every jump cut and roughly every second sentence becomes a framing change
    # a jump cut must always change framing (that is what hides it); sentence marks only when not crowded
    marks = []
    for c in sorted(round(c, 2) for c in cw["cut_points"]):
        if not marks or c - marks[-1] >= 0.7:
            marks.append(c)
    for s in (round(s, 2) for s in starts[1::2]):
        if all(abs(s - m) >= 1.6 for m in marks):
            marks.append(s)
    marks.sort()
    # no framing change should last longer than ~6s: fill long stretches at natural breath points
    bounds = [0.0] + marks + [dur]
    for lo, hi in zip(bounds, bounds[1:]):
        t = lo
        while hi - t > 7.0:
            cand = [w2["s"] for w1, w2 in zip(words, words[1:]) if t + 3.5 <= w2["s"] <= t + 6 and w2["s"] - w1["e"] > 0.08]
            nxt = cand[0] if cand else next((w["s"] for w in words if w["s"] >= t + 5), hi)
            if hi - nxt < 2.0:
                break
            marks.append(round(nxt, 2))
            t = nxt
    marks.sort()
    punch, tight = [], False
    for i, m in enumerate(marks):
        tight = not tight
        nxt = marks[i + 1] if i + 1 < len(marks) else dur
        if tight:
            punch.append({"start": m, "end": round(min(nxt, m + a.max_hold), 2), "zoom": a.zoom})
    god, var, t = resolve_style(a.template, a.variant)
    edit = {
        "template": t,
        "transition": a.transition,
        "brand": {"accent": "#7A1414", "accent2": "#2A0606", "ink": "#FFFFFF", "paper": "#EFEDE8",
                  "dark": "#120505", "sans": "Inter", "serif": "Fraunces", "display": "Montserrat",
                  "_note": "PLACEHOLDER - replace with the colours the user confirmed"},
        "title": {"text": a.title, "start": 0.0, "end": 3.0} if a.title else None,
        "emphasis": [],
        "punchins": punch,
        "broll": [],
        "cards": [],
        "music": None,
        "intro_overlay": None,
        "endcard": None,
        "captions": {"maxWords": 4, "maxChars": 24, "y": 0.66},
    }
    if t in ("glass", "softglass"):  # references/glass-style.md: headlines replace the title card; fill these by hand
        edit.update({"title": None, "gradient": False, "scrim": 0.34,
                     "captions": {"maxWords": 3, "maxChars": 22, "y": 0.775},
                     "brand": {**edit["brand"], "display": "Montserrat", "sans": "Montserrat", "serif": "Playfair Display",
                               "pop": "#2BE36B"},
                     "heads": [], "chips": [], "panels": [], "tiles": [], "pills": [], "sparks": []})
    if t in ("apollo", "softglass"):  # references/apollo-style.md: soft glass + glass captions; the theme is left open
        edit.update({"template": "glass", "glassStyle": "soft", "glassTone": "dark",
                     "title": None, "gradient": False, "scrim": 0.22, "grade": "film", "topblur": {"to": 0.3, "sigma": 22},
                     "captions": {"maxWords": 3, "maxChars": 22, "y": 0.775}, "zoom_y_bias": 0.3,
                     "brand": {"accent": "THEME", "accent2": "THEME", "highlight": "THEME", "pop": "THEME",
                               "ink": "THEME", "paper": "THEME", "cream": "THEME", "dark": "THEME",
                               "sans": "Montserrat", "label": "Montserrat", "display": "Montserrat", "serif": "Playfair Display",
                               "_note": "THEME is open: fill from the client's brand (apollo-style.md § Theme)"},
                     "music": {"src": "music/bed.mp3", "lufs": -37}, "sfx": {"db": -20},
                     "heads": [], "chips": [], "panels": [], "bubbles": [], "tiles": [], "pills": [], "sparks": [], "blur": []})
    if t == "softglass":  # Apollo quiet: the same look with captions off, so the headlines carry every line
        edit.update({"captions": {"off": True}, "scrim": 0.2})
    edit["style"] = god if var == "default" else f"{god}/{var}"
    p = d / "edit.json"
    if p.exists() and not a.force:
        raise SystemExit(f"{p} exists; pass --force to overwrite")
    p.write_text(json.dumps(edit, indent=2, ensure_ascii=False), encoding="utf-8")
    out_json({"edit": str(p), "punchins": len(punch), "sentences": len(starts), "duration": dur})


# ---------------------------------------------------------------- render
GRADES = {  # starting points; "grade" in edit.json can also be a raw ffmpeg filter chain
    "none": "",
    "neutral": "eq=contrast=1.06:saturation=1.06",
    "warm": "eq=contrast=1.05:saturation=1.08:gamma=0.98,colorbalance=rs=.035:gs=.01:bs=-.035:rm=.025:bm=-.025",
    "cinematic": "eq=contrast=1.08:saturation=0.94,colorbalance=rs=-.03:bs=.04:rh=.05:bh=-.05,"
                 "curves=all='0/0.03 0.5/0.5 1/0.97'",
    "soft": "eq=contrast=0.97:saturation=1.03:gamma=1.03,curves=all='0/0.04 1/0.98'",
    # soft-glass look (Nyandi reel 2): warm highlights, slightly green-teal shadows, lifted blacks, vignette
    "film": "eq=contrast=1.06:saturation=1.06:gamma=0.98,colorbalance=rs=-.02:gs=.02:bs=.01:rh=.05:gh=.015:bh=-.05,"
            "curves=all='0/0.05 0.5/0.49 1/0.95',vignette=angle=PI/4.6",
    # rich dark skin: warm mids, open shadows so skin keeps detail, highlights rolled off so shine doesn't clip
    "skin": "eq=contrast=1.04:saturation=1.05,colorbalance=rm=.025:gm=.005:bm=-.02:rh=.01:bh=-.01,"
            "curves=all='0/0.02 0.25/0.27 0.75/0.76 1/0.96',vibrance=intensity=0.08",
    "bright": "eq=contrast=1.02:saturation=1.04:gamma=1.06,curves=all='0/0.02 0.5/0.54 1/0.99',vibrance=intensity=0.1",
    "golden": "eq=contrast=1.05:saturation=1.08,colorbalance=rs=.02:bs=-.04:rm=.04:gm=.015:bm=-.04:rh=.04:bh=-.05",
    "teal-orange": "eq=contrast=1.08:saturation=1.02,colorbalance=rs=-.05:gs=.01:bs=.06:rm=.03:bm=-.03:rh=.06:gh=.01:bh=-.06,"
                   "vibrance=intensity=0.12",
    "moody": "eq=contrast=1.12:saturation=0.86:gamma=0.94,colorbalance=rs=-.02:bs=.03:rh=.03:bh=-.02,"
             "curves=all='0/0.04 0.5/0.46 1/0.93',vignette=angle=PI/4",
    "punchy": "eq=contrast=1.12:saturation=1.1,vibrance=intensity=0.15,curves=all='0/0 0.25/0.22 0.75/0.79 1/1'",
    "mono": "hue=s=0,eq=contrast=1.12,curves=all='0/0.03 0.5/0.5 1/0.97'",
}


def _ffpath(p):
    """A file path as an ffmpeg filter argument (Windows drive colon escaped)."""
    return "'" + str(Path(p).resolve()).replace("\\", "/").replace(":", "\\:") + "'"


def grade_chain(edit):
    """edit["grade"] is a look name, a raw ffmpeg chain, or a dict:
    {"look": "warm", "strength": 0.7, "lut": "x.cube", "wb": [r,g,b], "gamma": 1.05, "levels": [black, white],
     "temp": -1..1, "tint": -1..1, "contrast": 1.05, "saturation": 1.0, "vibrance": 0.1, "vignette": true}
    Corrections (wb, gamma, levels, temp, tint, sliders) run first, then the look or LUT at `strength`."""
    g = edit.get("grade") or "none"
    if isinstance(g, str):
        return GRADES.get(g, g)
    fix = []
    if g.get("wb"):
        r, gg, b = (float(x) for x in g["wb"])
        fix.append(f"colorchannelmixer=rr={r:.4f}:gg={gg:.4f}:bb={b:.4f}")
    if g.get("levels"):
        bp, wp = (float(x) for x in g["levels"])
        fix.append(f"curves=all='{bp:.3f}/0 {wp:.3f}/1'")
    eq = {k: float(g[k]) for k in ("gamma", "contrast", "saturation", "brightness") if k in g}
    if eq:
        fix.append("eq=" + ":".join(f"{k}={v:.3f}" for k, v in eq.items()))
    t, tn = float(g.get("temp", 0)), float(g.get("tint", 0))
    if t or tn:  # temp: + warmer / - cooler; tint: + magenta / - green (mid-tones, gentle highlights)
        fix.append(f"colorbalance=rm={.06 * t:.3f}:bm={-.06 * t:.3f}:gm={-.05 * tn:.3f}"
                   f":rh={.03 * t:.3f}:bh={-.03 * t:.3f}:gh={-.025 * tn:.3f}")
    if g.get("vibrance"):
        fix.append(f"vibrance=intensity={float(g['vibrance']):.3f}")
    look = f"lut3d=file={_ffpath(g['lut'])}" if g.get("lut") else GRADES.get(g.get("look") or "none", g.get("look") or "")
    s = float(g.get("strength", 1.0))
    if look and s < 0.999:  # mix the look over the corrected picture
        look = (f"split[grA][grB];[grB]{look}[grL];"
                f"[grA][grL]blend=all_expr='A*{1 - s:.3f}+B*{s:.3f}'")
    chain = ",".join(fix + ([look] if look and s > 0.001 else []))
    if g.get("vignette"):
        chain += ("," if chain else "") + "vignette=angle=PI/4.6"
    return chain


def analyse_colour(video, n=8):
    """Sample frames and suggest a neutral correction: white balance from near-grey pixels,
    exposure (gamma) from median luma, black/white points from the 1st/99th percentiles. All clamped gentle."""
    dur = probe(video)["duration"]
    w, h, px = 72, 128, []
    for i in range(n):
        t = dur * (i + 0.5) / n
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                              "-vf", f"scale={w}:{h}:flags=area,format=rgb24", "-f", "rawvideo", "-"],
                             capture_output=True).stdout
        px += [(raw[k] / 255, raw[k + 1] / 255, raw[k + 2] / 255) for k in range(0, len(raw) - 2, 3)]
    if not px:
        raise SystemExit("could not read frames")
    lum = sorted(.2126 * r + .7152 * g + .0722 * b for r, g, b in px)
    p1, p50, p99 = (lum[int(len(lum) * q)] for q in (.01, .5, .99))
    grey = [(r, g, b) for r, g, b in px if .3 < .2126 * r + .7152 * g + .0722 * b < .92 and max(r, g, b) - min(r, g, b) < .1]
    out = {"median": round(p50, 3), "black": round(p1, 3), "white": round(p99, 3),
           "grey_share": round(len(grey) / len(px), 3), "suggest": {}}
    sug = out["suggest"]
    if len(grey) > len(px) * .02:  # enough neutral surfaces (walls, shirts) to trust a white balance
        R, G, B = (sum(c[i] for c in grey) / len(grey) for i in range(3))
        out["cast"] = {"r": round(R / G, 3), "b": round(B / G, 3)}
        clamp = lambda x: max(.92, min(1.08, x))
        gr, gb = clamp(G / R), clamp(G / B)
        if abs(gr - 1) > .015 or abs(gb - 1) > .015:
            sug["wb"] = [round(gr, 4), 1.0, round(gb, 4)]
    target = .42
    if abs(p50 - target) > .05 and .03 < p50 < .97:
        import math
        sug["gamma"] = round(max(.85, min(1.25, math.log(p50) / math.log(target))), 3)
    bp = round(min(.07, p1 - .02), 3) if p1 > .06 else 0.0
    wp = round(max(.88, p99 + .02), 3) if p99 < .86 else 1.0
    if bp or wp < 1:
        sug["levels"] = [bp, wp]
    return out


def cmd_color(a):
    d = Path(a.dir).resolve()
    video = Path(a.video) if a.video else d / "cut.mp4"
    edit_p = d / "edit.json"
    edit = json.loads(edit_p.read_text(encoding="utf-8")) if edit_p.exists() else {}
    res = {}
    if not a.compare_only:
        res = analyse_colour(video)
        if a.apply:
            g = edit.get("grade") or {}
            g = {"look": g} if isinstance(g, str) and g != "none" else ({} if isinstance(g, str) else dict(g))
            for k in ("wb", "gamma", "levels"):
                g.pop(k, None)
            g.update(res["suggest"])
            if a.look:
                g["look"] = a.look
            edit["grade"] = g
            edit_p.write_text(json.dumps(edit, indent=2, ensure_ascii=False), encoding="utf-8")
            res["grade"] = g
    if a.compare:
        looks = [x.strip() for x in a.compare.split(",") if x.strip()] if a.compare != "all" else \
            ["original", "corrected"] + [k for k in GRADES if k != "none"]
        t = float(a.at) if a.at else probe(video)["duration"] * .4
        base = edit.get("grade") if isinstance(edit.get("grade"), dict) else {}
        corr = {k: v for k, v in {**base, **res.get("suggest", {})}.items() if k in ("wb", "gamma", "levels")}
        tiles = Path(a.scratch or d) / "color_tiles"
        tiles.mkdir(parents=True, exist_ok=True)
        for f in tiles.glob("*.png"):
            f.unlink()
        for i, name in enumerate(looks):
            if name == "original":
                ch = ""
            elif name == "corrected":
                ch = grade_chain({"grade": corr}) if corr else ""
            else:
                ch = grade_chain({"grade": {**corr, "look": name, "strength": a.strength}})
            lab = name.replace("'", "")
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-filter_complex",
                 f"[0:v]{ch + ',' if ch else ''}scale=270:-2,drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':"
                 f"text='{lab}':x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=5",
                 "-frames:v", "1", str(tiles / f"t_{i:03d}.png")])
        cols = min(len(looks), 6)
        out = Path(a.out) if a.out else d / "looks.jpg"
        run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-i", str(tiles / "t_%03d.png"),
             "-vf", f"tile={cols}x{(len(looks) + cols - 1) // cols}:padding=4", "-frames:v", "1", str(out)])
        res["sheet"] = str(out)
        res["looks"] = looks
    out_json(res)


def blur_ranges(edit):
    """Glass pack: time ranges where the base video is blurred and dimmed behind a frosted panel."""
    r = [(float(p["start"]), float(p["end"]), float(p.get("dim", 0.07))) for p in edit.get("panels") or [] if p.get("blur", True)]
    r += [(float(b["start"]), float(b["end"]), float(b.get("dim", 0.07))) for b in edit.get("blur") or []]
    return sorted(r)


def topblur_filter(edit, src, dst, nframes, fps):
    """Soft-glass depth: a permanent soft blur over the top of the frame, fading to sharp by `to` (fraction of the
    height), so headlines sit on a calm field. The gradient mask is drawn once and looped (no per-frame maths)."""
    tb = edit.get("topblur")
    if not tb:
        return [f"[{src}]null[{dst}]"]
    to = float(tb.get("to", 0.3)) if isinstance(tb, dict) else 0.3
    sig = (float(tb.get("sigma", 22)) if isinstance(tb, dict) else 22) / 4
    y0, y1 = int(H * to * 0.4), int(H * to)
    return [f"[{src}]split[ta][tb]",
            f"[tb]scale={W // 4}:{H // 4},gblur=sigma={sig:.2f}:steps=2,scale={W}:{H}:flags=bilinear,format=yuva420p[tbl]",
            f"gradients=s={W}x{H}:c0=0xFFFFFF:c1=0x000000:x0={W // 2}:y0={y0}:x1={W // 2}:y1={y1}:nb_colors=2:speed=0:r={fps},"
            f"trim=end_frame=1,loop=loop={max(0, nframes - 1)}:size=1,format=gray,settb=1/{fps},setpts=N[tmk]",
            f"[tbl][tmk]alphamerge[tbm]",
            f"[ta][tbm]overlay=format=auto:shortest=1,format=yuv420p[{dst}]"]


def blur_filter(edit, src, dst, nframes, fps):
    """Glass background: blurred + dimmed copy faded in over 0.35s and out over 0.3s inside each panel range only.
    Frame-exact segments: sharp stretches pass through untouched; each panel stretch overlays a quarter-size blur
    (looks the same for a heavy background blur, ~16x cheaper) with an alpha fade. Was a per-pixel blend
    expression over the whole video: 13 of 15 render minutes on a 2-min glass reel."""
    rng = []
    for s0, e0, dm in blur_ranges(edit):    # frame ranges, overlaps merged (keeping the stronger dim)
        a, b = max(0, int(round(s0 * fps))), min(nframes, int(round(e0 * fps)))
        if b - a < 3:
            continue
        if rng and a <= rng[-1][1]:
            rng[-1][1] = max(rng[-1][1], b); rng[-1][2] = max(rng[-1][2], dm)
        else:
            rng.append([a, b, max(dm, 1e-4)])   # >0 marks the segment as blurred, even at dim 0
    if not rng:
        return [f"[{src}]null[{dst}]"]
    segs, pos = [], 0
    for a, b, dm in rng:
        if a > pos:
            segs.append((pos, a, 0))
        segs.append((a, b, dm)); pos = b
    if pos < nframes:
        segs.append((pos, nframes, 0))
    sig = edit.get("glass_blur", 28) / 4
    out = [f"[{src}]split={len(segs)}" + "".join(f"[g{i}]" for i in range(len(segs)))]
    labels = ""
    for i, (a, b, bl) in enumerate(segs):
        f = f"[g{i}]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS"
        if bl:
            L = (b - a) / fps
            out.append(f + f",split[s{i}][r{i}]")
            out.append(f"[r{i}]scale={W // 4}:{H // 4},gblur=sigma={sig:.2f}:steps=2,scale={W}:{H}:flags=bilinear,"
                       f"eq=brightness={-bl:.3f}:saturation=0.9,format=yuva420p,"
                       f"fade=t=in:st=0:d={min(0.35, L / 2):.3f}:alpha=1"
                       + (f",fade=t=out:st={max(0, L - 0.3):.3f}:d={min(0.3, L / 2):.3f}:alpha=1" if b < nframes - 1 else "")
                       + f"[k{i}]")   # a blur that runs to the end holds (soft-glass ending), no fade-out
            out.append(f"[s{i}][k{i}]overlay=format=auto,format=yuv420p[h{i}]")
        else:
            out.append(f + f"[h{i}]")
        labels += f"[h{i}]"
    out.append(f"{labels}concat=n={len(segs)}:v=1:a=0,settb=1/{fps},setpts=N[{dst}]")
    return out


def punch_filter(punch, nframes, yb, fps=FPS, grade="", base_zoom=1.0):
    """Base-video framing as frame-exact segments (zoompan drops frames inside multi-input graphs)."""
    segs, pos = [], 0
    for p in sorted(punch, key=lambda p: p["start"]):
        a, b = max(pos, int(round(p["start"] * fps))), min(nframes, int(round(p["end"] * fps)))
        if b <= a:
            continue
        if a > pos:
            segs.append((pos, a, base_zoom))
        segs.append((a, b, float(p.get("zoom", 1.16))))
        pos = b
    if pos < nframes:
        segs.append((pos, nframes, base_zoom))
    pre = f"{grade}," if grade else ""
    parts, labels = [f"[0:v]{pre}split={len(segs)}" + "".join(f"[s{i}]" for i in range(len(segs)))], ""
    for i, (a, b, z) in enumerate(segs):
        f = f"[s{i}]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS"
        if z != 1.0:
            f += f",crop=iw/{z}:ih/{z}:(iw-iw/{z})/2:(ih-ih/{z})*{yb}"
        f += f",scale={W}:{H}:flags=lanczos,setsar=1"
        parts.append(f + f"[z{i}]")
        labels += f"[z{i}]"
    parts.append(f"{labels}concat=n={len(segs)}:v=1:a=0,settb=1/{fps},setpts=N[b]")
    return parts


def node_bin():
    return shutil.which("node") or "node"


def theme_open(edit):
    """Brand keys still set to the Apollo THEME placeholder (the colours must come from the client)."""
    return [k for k, v in (edit.get("brand") or {}).items() if v == "THEME"]


def cmd_vbroll(a):
    """Lay video b-roll into the cut: spec = [{"start","end","src","in"}] on the cut timeline. Landscape or 4K
    clips are centre-cropped to 9:16 and muted; the speaker's audio stays. The clean A-roll is kept once as
    cut_aroll.mp4 and every run rebuilds from it, so the spec can be edited and re-run freely."""
    d = Path(a.dir).resolve()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    cut, aroll = d / "cut.mp4", d / "cut_aroll.mp4"
    if not aroll.exists():
        shutil.copy2(cut, aroll)
    info = probe(aroll)
    W, H = info["width"], info["height"]
    fps = pick_fps(info, None)
    inputs, fc, last = ["-i", str(aroll)], [], "0:v"
    for n, ev in enumerate(spec, 1):
        dur = float(ev["end"]) - float(ev["start"]) + 0.1
        inputs += ["-ss", f"{float(ev.get('in', 0)):.3f}", "-t", f"{dur:.3f}", "-i", str(Path(ev["src"]))]
        fc.append(f"[{n}:v]fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
                  f"setpts=PTS-STARTPTS+{float(ev['start']):.3f}/TB[b{n}]")
        fc.append(f"[{last}][b{n}]overlay=eof_action=pass:enable='between(t,{float(ev['start']):.3f},{float(ev['end']):.3f})'[v{n}]")
        last = f"v{n}"
    if not spec:
        shutil.copy2(aroll, cut)
    else:
        run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{last}]",
             "-map", "0:a", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-c:a", "copy", str(cut)])
    out_json({"cut": str(cut), "aroll": str(aroll), "clips": len(spec), "duration": probe(cut)["duration"]})


def cmd_render(a):
    d = Path(a.dir).resolve()
    edit = json.loads((d / "edit.json").read_text(encoding="utf-8"))
    if theme_open(edit):
        raise SystemExit(f"Apollo theme still open ({', '.join(theme_open(edit))}): set the client's colours first")
    cut = d / "cut.mp4"
    info = probe(cut)
    frames = d / "frames"
    # frames can only be reused when nothing the overlay draws has changed
    import hashlib
    ov_keys = ("template", "transition", "brand", "title", "emphasis", "broll", "cards", "captions", "hook", "tag", "gradient", "intro", "outro",
               "heads", "chips", "panels", "tiles", "pills", "sparks", "bubbles", "glassStyle", "glassTone",
               "bigwords", "counters", "calendars", "headStyle", "scrim", "nocaps")
    ov_hash = hashlib.sha1(json.dumps({k: edit.get(k) for k in ov_keys}, sort_keys=True).encode()).hexdigest()
    stamp = frames / "_overlay.sha1"
    reuse = a.reuse_frames and stamp.exists() and stamp.read_text() == ov_hash
    if a.reuse_frames and not reuse:
        print("overlay fields changed since the frames were drawn: re-rendering the overlay", file=sys.stderr)
    if not reuse:
        r = subprocess.run([node_bin(), str(HERE / "overlay" / "render-overlay.js"), str(d)], text=True)
        if r.returncode:
            raise SystemExit("overlay render failed")
        stamp.write_text(ov_hash)
    if a.frames_only:
        return

    yb = edit.get("zoom_y_bias", 0.32)  # keep the face in frame when punching in
    fps = dir_fps(d)
    nframes = len(list(frames.glob("[0-9]*.png")))
    # pass 1: framing (punch-ins) on its own; split/trim/concat stalls when mixed with the PNG overlay input
    base = d / "base.mp4"
    pf = punch_filter(edit.get("punchins") or [], nframes, yb, fps, grade_chain(edit), float(edit.get("base_zoom", 1.0)))
    pf[-1] = pf[-1][:-3] + "[b0]"
    pf += topblur_filter(edit, "b0", "b1", nframes, fps)
    pf += blur_filter(edit, "b1", "b", nframes, fps)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(cut), "-filter_complex",
         ";".join(pf), "-map", "[b]", "-an",
         "-c:v", "libx264", "-crf", "11", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(base)])
    inputs = ["-i", str(base), "-framerate", str(fps), "-i", str(frames / "%05d.png"), "-i", str(cut)]
    fc = ["[1:v]format=rgba[o]", "[0:v][o]overlay=0:0:format=auto:shortest=1[ov]"]
    vlast = "ov"
    if edit.get("intro_overlay"):
        inputs += ["-i", str((d / edit["intro_overlay"]).resolve())]
        fc.append(f"[{vlast}][3:v]overlay=0:0:eof_action=pass[iv]")
        vlast = "iv"
    fc.append(f"[{vlast}]format=yuv420p[v]")
    fc.append("[2:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[voice]")
    alast = "voice"
    m = edit.get("music")
    if m and m.get("src"):
        idx = inputs.count("-i")
        inputs += ["-stream_loop", "-1", "-i", str((d / m["src"]).resolve())]
        dur = info["duration"]
        level = f"loudnorm=I={m["lufs"]}:TP=-9:LRA=7" if m.get("lufs") is not None else f"volume={m.get('db', -24)}dB"
        swell = ""
        if edit.get("outro"):  # nobody speaks over the outro card: lift the bed there (+9 dB over 0.6s)
            o = float(edit["outro"]["start"])
            swell = f",volume='1+1.8*min(max((t-{o:.2f})/0.6,0),1)':eval=frame"
        fc.append(f"[{idx}:a]aresample=48000,{level},aresample=48000{swell},"
                  f"afade=t=in:d=1.5" + ("" if edit.get("endcard") else f",afade=t=out:st={max(0, dur - 2.5):.2f}:d=2.5") + "[bed]")
        fc.append(f"[voice][bed]amix=inputs=2:duration=first:normalize=0[mix]")
        alast = "mix"
    sx = edit.get("sfx")
    hits = []  # (time, sound file)
    if sx and (sx.get("whoosh") or sx.get("file")):
        wh = sx.get("file")
        if not wh:  # soft filtered-noise swish, generated so no third-party sfx files are needed
            wh = str(d / "_whoosh.wav")
            run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anoisesrc=d=0.5:c=pink:a=0.5",
                 "-af", "highpass=f=500,lowpass=f=2800,afade=t=in:d=0.22:curve=qsin,afade=t=out:st=0.22:d=0.28:curve=qsin",
                 "-ar", "48000", "-ac", "2", wh])
        card_snd = sx.get("card_file") or wh
        for ev in edit.get("broll") or []:
            hits += [(max(0.0, ev["start"] - 0.08), wh), (max(0.0, ev["end"] - 0.42), wh)]
        for ev in edit.get("cards") or []:
            hits += [(max(0.0, ev["start"] - 0.05), card_snd)]
            if sx.get("pop"):   # one soft pop per point on a points page
                hits += [(max(0.0, p["at"] - 0.02), sx["pop"]) for p in ev.get("points") or [] if "at" in p]
        if edit.get("outro"):
            hits += [(max(0.0, edit["outro"]["start"] - 0.08), wh)]
    if hits:
        files = sorted(set(f for _, f in hits))
        base_idx = inputs.count("-i")
        for f in files:
            inputs += ["-i", str(f)]
        for fi, f in enumerate(files):
            mine = [i for i, (_, ff) in enumerate(hits) if ff == f]
            vol = sx.get("card_db", sx.get("db", -20)) if (f == card_snd and f != wh) else \
                sx.get("pop_db", sx.get("db", -20)) if f == sx.get("pop") else sx.get("db", -20)
            fc.append(f"[{base_idx + fi}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol}dB,"
                      f"asplit={len(mine)}" + "".join(f"[w{i}]" for i in mine))
        for i, (t, _) in enumerate(hits):
            ms = int(t * 1000)
            fc.append(f"[w{i}]adelay={ms}|{ms}[wd{i}]")
        fc.append(f"[{alast}]" + "".join(f"[wd{i}]" for i in range(len(hits))) +
                  f"amix=inputs={len(hits) + 1}:duration=first:normalize=0[sfxmix]")
        alast = "sfxmix"
    body = d / "body.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
         "-map", "[v]", "-map", f"[{alast}]", "-t", f"{info['duration']:.3f}",
         "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(body)])

    final = d / "final.mp4"
    if edit.get("endcard"):
        ec = (d / edit["endcard"]).resolve()
        ed, bd = probe(ec)["duration"], info["duration"]
        # ending (Monny, Oct 2026): the music carries on under the outro card, a soft chime lands with the logo,
        # and the card fades out with the music instead of cutting off
        ein = ["-i", str(body), "-i", str(ec), "-f", "lavfi", "-t", "10", "-i", "anullsrc=r=48000:cl=stereo"]
        afc = [f"[2:a]atrim=0:{ed:.3f}[sil]"]
        mix = ["[sil]"]
        m = edit.get("music")
        if m and m.get("src"):
            ein += ["-stream_loop", "-1", "-i", str((d / m["src"]).resolve())]
            lvl = f"loudnorm=I={m['lufs']}:TP=-9:LRA=7" if m.get("lufs") is not None else f"volume={m.get('db', -24)}dB"
            afc.append(f"[3:a]aresample=48000,atrim={bd:.3f}:{bd + ed + 1:.3f},asetpts=PTS-STARTPTS,{lvl},"
                       f"volume={edit.get('outro_music_lift_db', 5)}dB,atrim=0:{ed:.3f},"
                       f"afade=t=out:st={max(0, ed - 2.2):.2f}:d=2.2[em]")
            mix.append("[em]")
        ch = (edit.get("sfx") or {}).get("chime")
        if ch:
            k = ein.count("-i")
            ein += ["-i", str(ch)]
            afc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,"
                       f"volume={(edit.get('sfx') or {}).get('chime_db', -14)}dB,adelay=150|150[ech]")
            mix.append("[ech]")
        afc.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:normalize=0,aformat=channel_layouts=stereo[ea]")
        run(["ffmpeg", "-y", "-loglevel", "error", *ein, "-filter_complex",
             f"[1:v]scale={W}:{H},fps={fps},setsar=1,format=yuv420p,"
             f"fade=t=out:st={max(0, ed - 1.0):.2f}:d=1.0[ev];" + ";".join(afc) + ";"
             "[0:v][0:a][ev][ea]concat=n=2:v=1:a=1[v][a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "17", "-preset", "veryfast",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)])
        body.unlink()
    else:
        body.replace(final)
    base.unlink(missing_ok=True)
    if not a.keep_frames:
        shutil.rmtree(frames, ignore_errors=True)
    out_json({"final": str(final), **probe(final)})


# ---------------------------------------------------------------- preview
def cmd_preview(a):
    """Overlay at a few moments composited on the matching cut.mp4 frames -> one strip (seconds, not minutes)."""
    d = Path(a.dir).resolve()
    ts = [float(x) for x in a.at.split(",")]
    pv = d / "preview"
    shutil.rmtree(pv, ignore_errors=True)
    cmd = [node_bin(), str(HERE / "overlay" / "render-overlay.js"), str(d), "--at", a.at]
    if a.override:
        cmd += ["--override", a.override]
    if subprocess.run(cmd).returncode:
        raise SystemExit("overlay preview failed")
    edit = json.loads((d / "edit.json").read_text(encoding="utf-8"))
    if a.override:
        edit.update(json.loads(a.override))
    yb = edit.get("zoom_y_bias", 0.32)
    for i, t in enumerate(ts):
        z = next((p.get("zoom", 1.16) for p in edit.get("punchins") or [] if p["start"] <= t < p["end"]),
                 float(edit.get("base_zoom", 1.0)))
        g = grade_chain(edit)
        crop = (f"{g}," if g else "") + (f"crop=iw/{z}:ih/{z}:(iw-iw/{z})/2:(ih-ih/{z})*{yb}," if z != 1.0 else "") \
            + f"scale={W}:{H},"
        dm = next((x for s0, e0, x in blur_ranges(edit) if s0 + 0.2 <= t < e0), None)
        if dm is not None:
            crop += f"gblur=sigma={edit.get('glass_blur', 28)}:steps=2,eq=brightness={-dm:.3f}:saturation=0.9,"
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", str(d / "cut.mp4"),
             "-i", str(pv / f"ov_{i:03d}.png"), "-filter_complex",
             f"[0:v]{crop}setsar=1[b0];" + ";".join(topblur_filter(edit, "b0", "b", 1, 30)) + ";[b][1:v]overlay=0:0,scale=360:-1,drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':"
             f"text='{t:.2f}s':x=6:y=6:fontsize=22:fontcolor=yellow:box=1:boxcolor=black",
             "-frames:v", "1", str(pv / f"c_{i:03d}.png")])
    cols = min(len(ts), 6)
    rows = (len(ts) + cols - 1) // cols
    out = Path(a.out) if a.out else d / "preview.jpg"
    run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-i", str(pv / "c_%03d.png"),
         "-vf", f"tile={cols}x{rows}", "-frames:v", "1", str(out)])
    shutil.rmtree(pv, ignore_errors=True)
    out_json({"preview": str(out)})


# ---------------------------------------------------------------- stills
def cmd_stills(a):
    """Sharp speaker frames from the source (no overlay) for reel-covers thumbnails when there is no photoshoot."""
    src = Path(a.video)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dur = probe(src)["duration"]
    tmp = out / "_cand"
    tmp.mkdir(exist_ok=True)
    picks = []
    for i in range(a.n):
        lo, hi = dur * (i + 0.1) / a.n, dur * (i + 0.9) / a.n
        best = None
        for k in range(4):  # largest JPEG in the window ~ sharpest, eyes-open frame
            t = lo + (hi - lo) * k / 3
            f = tmp / f"{i:02d}_{k}.jpg"
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
                 "-q:v", "2", str(f)])
            if f.exists() and (best is None or f.stat().st_size > best[1].stat().st_size):
                best = (t, f)
        if best:
            dst = out / f"still_{i + 1:02d}_{best[0]:.1f}s.jpg"
            shutil.copy(best[1], dst)
            picks.append(str(dst))
    shutil.rmtree(tmp, ignore_errors=True)
    out_json({"stills": picks})


# ---------------------------------------------------------------- timeline
def cmd_timeline(a):
    """Filmstrip + waveform for a time range: use at ambiguous cut decisions (retake starts, breaths)."""
    dur = a.end - a.start
    n = max(4, min(12, int(dur / 0.5)))
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(a.start), "-t", f"{dur:.3f}", "-i", a.video,
         "-filter_complex",
         f"[0:v]fps={n / dur:.4f},scale=-2:200,tile={n}x1,scale=1600:-2[s2];"
         f"[0:a:0]showwavespic=s=1600x160:colors=0x2FA89E[wave];"
         f"[s2][wave]vstack=2,drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':"
         f"text='{a.start:.2f}s - {a.end:.2f}s':x=8:y=8:fontsize=24:fontcolor=yellow:box=1:boxcolor=black",
         "-frames:v", "1", a.out])
    out_json({"timeline": a.out})


# ---------------------------------------------------------------- export
def cmd_export(a):
    """Other platforms from final.mp4: 4:5 / 1:1 (LinkedIn, feed) crop, 16:9 (YouTube) on a blurred fill."""
    src = Path(a.video)
    tag = a.aspect.replace(":", "x")
    out = Path(a.out) if a.out else src.with_name(f"{src.stem}_{tag}.mp4")
    if a.aspect in ("4:5", "1:1"):
        h = 1350 if a.aspect == "4:5" else 1080
        vf = f"crop=1080:{h}:0:(ih-{h})*{a.y}"
    elif a.aspect == "16:9":
        vf = ("split[a][b];[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=30:3,"
              "eq=brightness=-0.08[bg];[b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:0")
    else:
        raise SystemExit("aspect must be 4:5, 1:1 or 16:9")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", f"[0:v]{vf},format=yuv420p[v]",
         "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "copy",
         "-movflags", "+faststart", str(out)])
    out_json({"export": str(out), **probe(out)})


# ---------------------------------------------------------------- strip
def cmd_strip(a):
    ts = [float(x) for x in a.at.split(",")]
    tmp = Path(a.out).with_suffix("")
    tmp.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(ts):
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", a.video, "-frames:v", "1",
             "-vf", f"scale={getattr(a, 'width', 270)}:-1,drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':"
                    f"text='{t:.2f}s':x=4:y=4:fontsize={16 if getattr(a, 'width', 270) < 220 else 20}:"
                    "fontcolor=yellow:box=1:boxcolor=black", str(tmp / f"{i:03d}.png")])
    cols = min(len(ts), getattr(a, "cols", 6))
    rows = (len(ts) + cols - 1) // cols
    run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-i", str(tmp / "%03d.png"),
         "-vf", f"tile={cols}x{rows}", "-frames:v", "1", a.out])
    shutil.rmtree(tmp, ignore_errors=True)
    out_json({"strip": a.out})


AUDIO_PY = Path.home() / ".audio-venv" / "Scripts" / "python.exe"


def audio_polish(video, outdir, words=None, force=False):
    """Run the voice-polish check; returns (source to cut from, report). The original is used unless the
    audio fails a check (noise, background, echo, heavy, thin, clipping), see scripts/audio_polish.py."""
    if not AUDIO_PY.exists():
        return Path(video), {"action": "skipped: ~/.audio-venv missing"}
    cmd = [str(AUDIO_PY), "-I", str(HERE / "audio_polish.py"), "polish", str(video), "--out", str(outdir)]
    if words:
        cmd += ["--words", str(words)]
    if force:
        cmd += ["--force"]
    rep = json.loads(run(cmd))
    out = Path(rep.get("output", "")) if rep.get("action") == "polished" else Path(video)
    return out, rep


def cmd_audio(a):
    src, rep = audio_polish(a.video, a.out, a.words, a.force)
    out_json({"use_for_cut": str(src), "verdict": rep.get("verdict"), "problems": rep.get("problems"),
              "action": rep.get("action"), "steps": rep.get("steps"),
              "measures": {k: {kk: vv for kk, vv in v.items() if kk not in ("bad", "limit")}
                           for k, v in (rep.get("checks") or {}).items()}})


def cmd_transcript(a):
    """Token-light reading view: one line per sentence with its start time, pauses > 0.8s marked inline.
    Read this to plan; ask `timeline` for exact word times only where an edit needs them."""
    words = json.loads(Path(a.words).read_text(encoding="utf-8"))["words"]
    if getattr(a, "edit", None):            # editable copy: delete words to cut them, fix spellings for captions
        import autocut
        Path(a.edit).write_text(autocut.to_text(words), encoding="utf-8")
        out_json({"edit_me": a.edit, "then": "cut ... --text <this file>"})
        return
    line, out, t0 = [], [], None
    for i, w in enumerate(words):
        if t0 is None:
            t0 = w["s"]
        if i and w["s"] - words[i - 1]["e"] > 0.8:
            line.append(f"<{w['s'] - words[i - 1]['e']:.1f}s>")
        line.append(w["w"])
        if re.search(r"[.?!]$", w["w"]) or i == len(words) - 1:
            out.append(f"[{t0:.1f}] " + " ".join(line)); line, t0 = [], None
    print("\n".join(out))


def cmd_prep(a):
    """One command for the mechanical half of an edit, run in the background: work folder, transcript (kept if it
    exists), voice check (polish only bad audio), auto-cut of retakes/slates/stumbles, cut with J-cuts, then the
    compact cut transcript and anything flagged "check". Claude then reads ~1 page and writes edit.json."""
    src = Path(a.video).resolve()
    d = work_dir(src)
    wj = d / "words.json"
    if not wj.exists():
        cmd_transcribe(argparse.Namespace(video=str(src), out=str(wj), model=a.model, language=None, clean=False,
                                          mix=a.mix, vocab=a.vocab))
    src_audio, rep = audio_polish(src, d, wj)
    cut_ns = argparse.Namespace(video=str(src), words=str(wj), out=str(d), exclude=a.exclude, max_pause=0.32,
                                pad_in=0.06, pad_out=0.12, no_cut=False, no_snap=False, no_auto=False, text=None,
                                review=None, keep_fillers=False, silence_db=-20.0, speed=1.0, hold=a.hold, fps="auto",
                                lowres=False, jcut=a.jcut, no_digits=False,
                                audio_from=str(src_audio) if rep.get("action") == "polished" else None)
    cmd_cut(cut_ns)
    print(f"\n# work dir: {d}\n# audio: {rep.get('verdict')} {rep.get('problems') or ''}\n# cut transcript:")
    cmd_transcript(argparse.Namespace(words=str(d / "cut_words.json"), edit=None))


def cmd_check(a):
    """Self-check sheets for a rendered reel, no hand-picked times: 2 frames either side of every cut, each
    overlay's first, middle and last frame, and the first and last second. 24 frames per sheet."""
    d = Path(a.dir).resolve()
    cw = json.loads((d / "cut_words.json").read_text(encoding="utf-8"))
    edit = json.loads((d / "edit.json").read_text(encoding="utf-8"))
    video = Path(a.video).resolve() if a.video else d / "final.mp4"
    fps, dur = cw.get("fps", FPS), probe(video)["duration"]
    f2 = 2 / fps
    ts = {0.2: "start", round(dur - 0.6, 2): "end"}
    for c in cw.get("cut_points", []):
        ts.setdefault(round(c - f2, 3), "cut-"); ts.setdefault(round(c + f2, 3), "cut+")
    for key in ("broll", "cards", "panels", "heads", "calendars", "bigwords", "chips", "counters", "pills", "tiles"):
        for ev in edit.get(key) or []:
            s0, e0 = float(ev["start"]), float(ev["end"])
            for t, tag in ((s0 + 0.15, "in"), ((s0 + e0) / 2, "mid"), (e0 - 0.12, "out")):
                ts.setdefault(round(t, 3), f"{key}-{tag}")
    times = sorted(t for t in ts if 0 <= t < dur)
    sheets = []
    per = 32   # 180px tiles, 8 across: ~2.5k image tokens a sheet instead of ~4k for 24 big tiles
    for k in range(0, len(times), per):
        out = d / f"check_{k // per + 1:02d}.jpg"
        cmd_strip(argparse.Namespace(video=str(video), at=",".join(f"{t:.3f}" for t in times[k:k + per]), out=str(out),
                                     width=180, cols=8))
        sheets.append(str(out))
    out_json({"sheets": sheets, "frames": len(times), "cuts": len(cw.get("cut_points", []))})


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("scan"); s.add_argument("folder")
    s = sp.add_parser("work"); s.add_argument("video")
    s = sp.add_parser("deliver"); s.add_argument("dir"); s.add_argument("--to", required=True)
    s.add_argument("--name", required=True); s.add_argument("--file", default=None, help="default final.mp4")
    s = sp.add_parser("transcribe"); s.add_argument("video"); s.add_argument("--out", required=True)
    s.add_argument("--model", default="small"); s.add_argument("--language", default=None)
    s.add_argument("--clean", action="store_true", help="let Whisper drop fillers (no um/uh in the transcript)")
    s.add_argument("--mix", default=None, help="code-switching speech, e.g. 'sw' for Kenyan English + Swahili/Sheng: "
                   "transcribes as English with a vocabulary prompt so the Swahili words are spelled, not anglicised")
    s.add_argument("--vocab", default="", help="extra words/names to bias spelling (comma separated)")
    s = sp.add_parser("cut"); s.add_argument("video"); s.add_argument("--words", required=True)
    s.add_argument("--out", required=True); s.add_argument("--max-pause", type=float, default=0.32)
    s.add_argument("--pad-in", type=float, default=0.06); s.add_argument("--pad-out", type=float, default=0.12)
    s.add_argument("--no-cut", action="store_true", help="only normalise to 1080x1920, keep every pause")
    s.add_argument("--no-snap", action="store_true", help="keep word-timing cuts (default: snap into measured quiet)")
    s.add_argument("--no-auto", action="store_true", help="don't auto-cut detected retakes, slates and stumbles")
    s.add_argument("--text", default=None, help="edited transcript (from `transcript --edit`): deleted words are cut")
    s.add_argument("--review", default=None, help="review page JSON (exclude + caption fixes)")
    s.add_argument("--audio-from", default=None, help="take the sound from this file (the voice-polished copy); cuts are still decided on <video>")
    s.add_argument("--jcut", type=float, default=0.0, help="J-cut: picture switches this many s after the sound (0.06-0.12)")
    s.add_argument("--no-digits", action="store_true", help="keep spoken numbers as words in captions")
    s.add_argument("--keep-fillers", action="store_true", help="keep um/uh words (default: cut them)")
    s.add_argument("--exclude", default="", help="source ranges to drop, e.g. retakes: '12.4-19.8,40-44.5'")
    s.add_argument("--fps", default="auto", help="output frame rate (auto = keep a clean 24/25/30 source rate)")
    s.add_argument("--speed", type=float, default=1.0, help="tighten pacing, e.g. 1.05 (pitch preserved)")
    s.add_argument("--hold", type=float, default=0.0,
                   help="seconds to freeze the last frame at the end (room for a closing card)")
    s.add_argument("--lowres", action="store_true", help="work at 1080x1920 even from 4K (default keeps 1440x2560)")
    s.add_argument("--silence-db", type=float, default=-20.0,
                   help="silence = quieter than speech mean + this (dB); also cut measured gaps. None-able via --no-silence")
    s.add_argument("--no-silence", dest="silence_db", action="store_const", const=None,
                   help="cut on word timings only")
    s = sp.add_parser("review"); s.add_argument("video"); s.add_argument("--words", required=True)
    s.add_argument("--out", default=None); s.add_argument("--title", default=None)
    s.add_argument("--strike", default="", help="ranges Claude suggests cutting, pre-struck: '0-1.2,40.1-44.5'")
    s.add_argument("--serve", action="store_true", help="serve the page with seeking support (blocks; run in background)")
    s.add_argument("--port", type=int, default=4590)
    s = sp.add_parser("assemble"); s.add_argument("spec"); s.add_argument("--out", required=True)
    s.add_argument("--transcripts", default=None); s.add_argument("--fps", default="auto")
    s = sp.add_parser("timeline"); s.add_argument("video"); s.add_argument("start", type=float)
    s.add_argument("end", type=float); s.add_argument("--out", required=True)
    s = sp.add_parser("export"); s.add_argument("video"); s.add_argument("--aspect", required=True)
    s.add_argument("--y", type=float, default=0.42, help="crop position for 4:5/1:1 (0 top .. 1 bottom)")
    s.add_argument("--out", default=None)
    s = sp.add_parser("plan"); s.add_argument("dir"); s.add_argument("--template", default="pill",
                                                                   help="apollo | athena | hermes | ares | hestia (older names still work)")
    s.add_argument("--variant", default=None, help="apollo: quiet | ares: bigword, boxcaps | hestia: ghost, serif")
    s.add_argument("--transition", default="hex", choices=["hex", "wave", "disc", "blinds", "arc", "dissolve", "flash"])
    s.add_argument("--title", default=None); s.add_argument("--zoom", type=float, default=1.16)
    s.add_argument("--max-hold", type=float, default=6.0); s.add_argument("--force", action="store_true")
    s = sp.add_parser("render"); s.add_argument("dir"); s.add_argument("--frames-only", action="store_true")
    s.add_argument("--keep-frames", action="store_true")
    s.add_argument("--reuse-frames", action="store_true", help="skip the overlay pass, re-composite existing frames")
    s = sp.add_parser("preview"); s.add_argument("dir"); s.add_argument("--at", required=True)
    s.add_argument("--override", default=None, help="JSON merged over edit.json, e.g. '{\"template\":\"ghost\"}'")
    s.add_argument("--out", default=None)
    s = sp.add_parser("stills"); s.add_argument("video"); s.add_argument("--out", required=True)
    s.add_argument("--n", type=int, default=12)
    s = sp.add_parser("transcript"); s.add_argument("words")
    s.add_argument("--edit", default=None, help="write the transcript as editable text (one sentence per line) here")
    s = sp.add_parser("prep"); s.add_argument("video")
    s.add_argument("--exclude", default=""); s.add_argument("--jcut", type=float, default=0.08)
    s.add_argument("--hold", type=float, default=0.0); s.add_argument("--mix", default=None)
    s.add_argument("--vocab", default=""); s.add_argument("--model", default="small")
    s = sp.add_parser("audio"); s.add_argument("video"); s.add_argument("--out", required=True)
    s.add_argument("--words", default=None); s.add_argument("--force", action="store_true",
                   help="polish even if every check passes")
    s = sp.add_parser("color"); s.add_argument("dir"); s.add_argument("--video", default=None)
    s.add_argument("--apply", action="store_true", help="write the suggested correction into edit.json grade")
    s.add_argument("--look", default=None, help="with --apply, also set the look")
    s.add_argument("--compare", default=None, help="'all' or comma list of looks -> looks.jpg side by side")
    s.add_argument("--compare-only", action="store_true", help="skip the analysis, just draw the sheet")
    s.add_argument("--strength", type=float, default=1.0); s.add_argument("--at", default=None)
    s.add_argument("--out", default=None); s.add_argument("--scratch", default=None)
    s = sp.add_parser("check"); s.add_argument("dir"); s.add_argument("--video", default=None)
    s = sp.add_parser("vbroll"); s.add_argument("dir"); s.add_argument("spec")
    s = sp.add_parser("strip"); s.add_argument("video"); s.add_argument("--at", required=True)
    s.add_argument("--out", required=True)
    a = p.parse_args()
    {"scan": cmd_scan, "prep": cmd_prep, "work": cmd_work, "deliver": cmd_deliver, "review": cmd_review, "check": cmd_check, "vbroll": cmd_vbroll, "color": cmd_color, "audio": cmd_audio, "transcript": cmd_transcript, "transcribe": cmd_transcribe, "cut": cmd_cut, "plan": cmd_plan,
     "render": cmd_render, "preview": cmd_preview, "stills": cmd_stills, "strip": cmd_strip,
     "assemble": cmd_assemble, "timeline": cmd_timeline, "export": cmd_export}[a.cmd](a)


if __name__ == "__main__":
    main()
