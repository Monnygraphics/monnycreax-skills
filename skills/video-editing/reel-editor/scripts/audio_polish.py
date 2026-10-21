"""Voice polish for BAD audio only: diagnose a recording, and fix only the problems it measures.

  ~/.audio-venv/Scripts/python audio_polish.py diagnose <video> [--words words.json]
  ~/.audio-venv/Scripts/python audio_polish.py polish   <video> --out <dir> [--words words.json] [--force]

`diagnose` prints a JSON report with a verdict per problem. `polish` runs the diagnosis and, only when
something fails, writes <dir>/polished.mov (the picture stream-copied, the voice repaired, the same length
and timing so words.json still lines up). Clean audio is left alone: nothing is written, and the report says so.

Fixes, each used only when its check fails:
  noise / background sound -> DeepFilterNet (deep-filter.exe, MIT/Apache), attenuation limited to keep it natural
  echo / room              -> WPE dereverberation (nara_wpe, MIT), before the denoiser
  heavy / muddy voice      -> EQ: rumble high-pass, cut ~250 Hz mud, gentle presence lift
  thin voice               -> EQ: low-shelf warmth
  uneven or harsh          -> gentle compression + de-esser (whenever any fix runs)
Loudness is still set at render (-14 LUFS), so this step does not touch the final level.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

DF_EXE = Path(os.environ.get("DEEP_FILTER", Path.home() / ".audio-tools" / "deep-filter.exe"))
SR = 48000

# thresholds (tuned so clean studio and lav recordings pass; see SKILL.md "Voice polish")
SNR_BAD = 20.0          # dB speech-over-noise (above 100 Hz); below this room tone/hiss is plainly audible.
                        # decent phone takes sit at 25-35; Client A's AC-room takes measured 8
GAP_VAR_BAD = 9.0       # dB std of the pause energy: intermittent sounds (voices, traffic, a door, a phone)...
BG_SNR = 25.0           # ...that are also loud (speech less than this above the pause floor). A steady music bed
                        # or hum reads as "noise" instead, and the denoiser removes most of it.
DECAY_BAD = 0.24        # s for the sound to fall 20 dB after a word ends; above this the room is ringing
                        # (clean take 0.12 s; the same take through a 0.7 s room 0.30 s)
# low-mid (150-400 Hz) over clarity (1.5-4 kHz) energy in speech frames. Normal speech (long-term average
# speech spectrum) sits near +12 dB, so only a clear departure counts.
MUD_HEAVY = 17.0
MUD_THIN = 6.0
CLIP_BAD = 0.001        # share of samples at full scale


def load(video):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a:0", "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def frames_db(x, win=0.05, hop=0.025):
    n, h = int(SR * win), int(SR * hop)
    if len(x) < n:
        return np.array([-120.0]), hop
    idx = np.arange(0, len(x) - n, h)
    sq = np.concatenate([[0.0], np.cumsum(x.astype(np.float64) ** 2)])
    rms = np.sqrt((sq[idx + n] - sq[idx]) / n)
    return 20 * np.log10(rms + 1e-9), hop


def speech_mask(db, hop, words):
    m = np.zeros(len(db), bool)
    if words:
        for w in words:
            m[int(w["s"] / hop):int(w["e"] / hop) + 1] = True
    else:   # no transcript: loudest 45% of frames are speech
        m = db > np.percentile(db, 55)
    return m


def band_db(x, idx, lo, hi, n=2048):
    win = np.hanning(n)
    f = np.fft.rfftfreq(n, 1 / SR)
    sel = (f >= lo) & (f < hi)
    e = []
    for i in idx[:: max(1, len(idx) // 400)]:
        seg = x[i:i + n]
        if len(seg) < n:
            continue
        e.append(np.sum(np.abs(np.fft.rfft(seg * win))[sel] ** 2))
    return 10 * np.log10(np.mean(e) + 1e-12) if e else -120.0


def diagnose(video, words=None):
    x = load(video)
    if not len(x):
        return {"error": "no audio"}
    # levels for the noise checks come from a 100 Hz high-passed copy: rumble below that is barely audible and
    # the EQ removes it anyway, so it must not trigger the denoiser on its own
    from scipy.signal import butter, sosfilt
    xh = sosfilt(butter(4, 100, "highpass", fs=SR, output="sos"), x).astype(np.float32)
    db, hop = frames_db(xh)
    sp = speech_mask(db, hop, words)
    # real pauses only: gaps of >= 0.45 s between words, trimmed 0.15 s after the word and 0.08 s before the next
    # (Whisper's word times are tight, so plain non-word frames still carry the tails of speech)
    pause = np.zeros(len(db), bool)
    for w0, w1 in zip(words or [], (words or [])[1:]):
        if w1["s"] - w0["e"] >= 0.45:
            pause[int((w0["e"] + 0.15) / hop):int((w1["s"] - 0.08) / hop)] = True
    if pause.sum() < 10:   # no transcript or no pauses: the quietest 15% of frames
        pause = db <= np.percentile(db, 15)
    # active-speech level: 85th percentile, so the quiet frames between syllables don't drag it down
    speech_lvl = float(np.percentile(db[sp], 85)) if sp.any() else float(np.percentile(db, 90))
    g = db[pause]
    noise_floor = float(np.percentile(g, 30))
    gap_var = float(np.std(g))
    gap_loud = float(np.percentile(g, 90))
    snr = speech_lvl - noise_floor
    # echo: after each word that is followed by >= 0.35 s of pause, time for the level to fall 20 dB from the word end
    decays = []
    for k, w in enumerate(words or []):
        nxt = words[k + 1]["s"] if k + 1 < len(words) else w["e"] + 1.0
        if nxt - w["e"] < 0.35:
            continue
        i0 = int(w["e"] / hop)
        seg = db[i0:int(nxt / hop)]
        if len(seg) < 6:
            continue
        top = max(db[max(0, i0 - 4):i0 + 1].max(), seg[0])
        target = max(top - 20, noise_floor + 3)
        below = np.where(seg <= target)[0]
        decays.append((below[0] if len(below) else len(seg)) * hop)
    decay = float(np.median(decays)) if len(decays) >= 3 else None
    sp_idx = (np.where(sp)[0] * int(SR * hop)).astype(int)
    mud = band_db(x, sp_idx, 150, 400) - band_db(x, sp_idx, 1500, 4000) if len(sp_idx) else 0.0
    clip = float(np.mean(np.abs(x) >= 0.995))
    peak = float(20 * np.log10(np.max(np.abs(x)) + 1e-9))
    checks = {
        "noise": {"bad": snr < SNR_BAD, "snr_db": round(snr, 1), "limit": SNR_BAD},
        "background": {"bad": gap_var > GAP_VAR_BAD and snr < BG_SNR, "pause_variation_db": round(gap_var, 1),
                       "loud_pause_below_speech_db": round(speech_lvl - gap_loud, 1), "limit": GAP_VAR_BAD},
        "echo": {"bad": decay is not None and decay > DECAY_BAD, "decay_s": None if decay is None else round(decay, 2),
                 "limit": DECAY_BAD, "samples": len(decays)},
        "heavy": {"bad": mud > MUD_HEAVY, "lowmid_vs_clarity_db": round(mud, 1), "limit": MUD_HEAVY},
        "thin": {"bad": mud < MUD_THIN, "lowmid_vs_clarity_db": round(mud, 1), "limit": MUD_THIN},
        "clipping": {"bad": clip > CLIP_BAD, "share": round(clip, 5), "peak_dbfs": round(peak, 1)},
    }
    for v in checks.values():
        v["bad"] = bool(v["bad"])
    bad = [k for k, v in checks.items() if v["bad"]]
    return {"video": str(video), "verdict": "polish" if bad else "clean", "problems": bad,
            "speech_db": round(speech_lvl, 1), "noise_floor_db": round(noise_floor, 1), "checks": checks}


def dereverb(x):
    from nara_wpe.utils import istft, stft
    from nara_wpe.wpe import wpe
    Y = stft(x[None, :], size=1024, shift=256)              # (1, T, F)
    Z = wpe(Y.transpose(2, 0, 1), taps=10, delay=3, iterations=3).transpose(1, 2, 0)
    z = istft(Z, size=1024, shift=256)[0][: len(x)]
    if len(z) < len(x):
        z = np.pad(z, (0, len(x) - len(z)))
    return z.astype(np.float32)


def denoise(x, atten, tmp):
    if not DF_EXE.exists():
        raise SystemExit(f"deep-filter not found at {DF_EXE}")
    src = Path(tmp) / "in.wav"
    sf.write(src, x, SR, subtype="FLOAT")
    out = Path(tmp) / "df"
    subprocess.run([str(DF_EXE), "-D", "-a", str(atten), "-o", str(out), str(src)], check=True,
                   capture_output=True)
    y, _ = sf.read(out / "in.wav", dtype="float32")
    if y.ndim > 1:
        y = y.mean(axis=1)
    return np.pad(y, (0, max(0, len(x) - len(y))))[: len(x)].astype(np.float32)


def eq_chain(problems):
    f = ["highpass=f=75"]
    if "heavy" in problems:
        f += ["equalizer=f=250:t=q:w=1.1:g=-4", "equalizer=f=3600:t=q:w=1.4:g=2"]
    if "thin" in problems:
        f += ["lowshelf=f=180:g=3"]
    f += ["deesser=i=0.35:m=0.5:f=0.5", "acompressor=threshold=-22dB:ratio=2.5:attack=8:release=120:makeup=2"]
    return ",".join(f)


def polish(video, outdir, words=None, force=False):
    rep = diagnose(video, words)
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "audio_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    probs = rep.get("problems", [])
    if not probs and not force:
        return {**rep, "action": "none: audio is clean, original kept"}
    x = load(video)
    steps = []
    with tempfile.TemporaryDirectory() as tmp:
        if "echo" in probs:
            x = dereverb(x); steps.append("dereverb (WPE)")
        if {"noise", "background", "echo"} & set(probs) or force:
            atten = 40 if "background" in probs else 24      # limited, so the voice keeps its air
            x = denoise(x, atten, tmp); steps.append(f"denoise (DeepFilterNet, limit {atten} dB)")
        wav = Path(tmp) / "voice.wav"
        sf.write(wav, x, SR, subtype="FLOAT")
        chain = eq_chain(probs); steps.append("eq/compress: " + chain)
        out = outdir / "polished.mov"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "copy", "-af", chain, "-c:a", "pcm_s24le", "-ar", str(SR), "-shortest", str(out)], check=True)
    return {**rep, "action": "polished", "steps": steps, "output": str(out)}


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("diagnose", "polish"):
        s = sp.add_parser(name); s.add_argument("video"); s.add_argument("--words")
        if name == "polish":
            s.add_argument("--out", required=True); s.add_argument("--force", action="store_true")
    a = ap.parse_args()
    words = json.loads(Path(a.words).read_text(encoding="utf-8"))["words"] if a.words else None
    res = diagnose(a.video, words) if a.cmd == "diagnose" else polish(a.video, a.out, words, a.force)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
