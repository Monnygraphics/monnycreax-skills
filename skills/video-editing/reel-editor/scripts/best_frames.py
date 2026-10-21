"""Pick thumbnail-worthy frames of the speaker: eyes open, mouth closed (or a soft smile), sharp.

Run with the face venv (mediapipe Tasks + opencv):
  ~/.face-venv/Scripts/python best_frames.py <video> --out <dir> [--top 3] [--every 1.0]
Writes <dir>/<stem>_cand1.jpg ... (full resolution) and prints JSON scores.
Setup once: python -m venv ~/.face-venv && ~/.face-venv/Scripts/python -m pip install mediapipe opencv-python-headless
            curl -o ~/.face-venv/models/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

MODEL = Path(os.path.expanduser("~/.face-venv/models/face_landmarker.task"))


def dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def openness(lm):
    """Eye aspect ratio (lid gap / eye width, both eyes) and inner-lip gap / mouth width, from face-mesh points."""
    ear_l = (dist(lm[159], lm[145]) + dist(lm[158], lm[153])) / (2 * dist(lm[33], lm[133]))
    ear_r = (dist(lm[386], lm[374]) + dist(lm[385], lm[380])) / (2 * dist(lm[362], lm[263]))
    mar = dist(lm[13], lm[14]) / dist(lm[78], lm[308])
    return min(ear_l, ear_r), mar


def frames(video, every, width=720):
    """Decode one frame per `every` seconds in a single ffmpeg pass (rotation applied), as BGR arrays."""
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height:stream_side_data=rotation", "-of", "json", str(video)],
                           capture_output=True, text=True)
    st = json.loads(probe.stdout)["streams"][0]
    w, h = st["width"], st["height"]
    rot = 0
    for sd in st.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"] or 0)
    if abs(rot) % 180 == 90:
        w, h = h, w
    ow, oh = width, int(round(h * width / w / 2) * 2)
    cmd = ["ffmpeg", "-loglevel", "error", "-i", str(video), "-vf", f"fps=1/{every},scale={ow}:{oh}",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size, k = ow * oh * 3, 0
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield k * every, np.frombuffer(buf, np.uint8).reshape(oh, ow, 3)
        k += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--every", type=float, default=0.5)
    ap.add_argument("--skip", type=float, default=1.5, help="ignore the first/last seconds (slates, reaching for the phone)")
    a = ap.parse_args()
    opts = vision.FaceLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=str(MODEL)),
                                        output_face_blendshapes=True, num_faces=1)
    det = vision.FaceLandmarker.create_from_options(opts)
    rows = []
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                a.video], capture_output=True, text=True).stdout or 0)
    for t, img in frames(a.video, a.every):
        if t < a.skip or (dur and t > dur - a.skip):
            continue
        res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
        if not res.face_blendshapes:
            continue
        b = {c.category_name: c.score for c in res.face_blendshapes[0]}
        blink = max(b.get("eyeBlinkLeft", 0), b.get("eyeBlinkRight", 0))
        squint = max(b.get("eyeSquintLeft", 0), b.get("eyeSquintRight", 0))
        jaw = b.get("jawOpen", 0)
        funnel = max(b.get("mouthFunnel", 0), b.get("mouthPucker", 0))
        smile = (b.get("mouthSmileLeft", 0) + b.get("mouthSmileRight", 0)) / 2
        look = max(b.get("eyeLookDownLeft", 0), b.get("eyeLookDownRight", 0),
                   b.get("eyeLookOutLeft", 0), b.get("eyeLookOutRight", 0))
        lm = res.face_landmarks[0]
        ear, mar = openness(lm)
        xs, ys = [q.x for q in lm], [q.y for q in lm]
        box = [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sharp = cv2.Laplacian(gray, cv2.CV_64F).var()
        # lower is better for blink/jaw/funnel/look; a small smile helps; sharpness breaks ties
        # open eyes (EAR ~0.25-0.35) and closed lips (MAR < ~0.05) dominate; blendshapes refine
        # lips apart shows teeth (and any tooth gap): penalise lip movement hard; a closed-lip smile is good
        teeth = max(b.get("mouthLowerDownLeft", 0), b.get("mouthLowerDownRight", 0),
                    b.get("mouthUpperUpLeft", 0), b.get("mouthUpperUpRight", 0), b.get("mouthStretchLeft", 0),
                    b.get("mouthStretchRight", 0))
        score = (-6.0 * min(ear, 0.34) + 8.0 * max(mar - 0.02, 0) + 3.0 * teeth + 1.0 * blink + 1.2 * look
                 + 2.0 * jaw + 0.8 * funnel - 0.6 * min(smile, 0.3) + 1.5 * max(smile - 0.45, 0)
                 - 0.0003 * min(sharp, 600))
        rows.append({"t": round(t, 2), "score": round(score, 4), "ear": round(ear, 3), "mar": round(mar, 3),
                     "box": box, "teeth": round(teeth, 3), "blink": round(blink, 3), "jaw": round(jaw, 3),
                     "funnel": round(funnel, 3), "smile": round(smile, 3), "look": round(look, 3),
                     "sharp": round(sharp, 1)})
    rows.sort(key=lambda r: r["score"])
    picks, chosen = [], []
    for r in rows:  # spread picks at least 4s apart so candidates differ
        if all(abs(r["t"] - c) > 4 for c in chosen):
            chosen.append(r["t"])
            picks.append(r)
        if len(picks) >= a.top:
            break
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(a.video).stem
    for i, r in enumerate(picks, 1):
        f = out / f"{stem}_cand{i}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(r["t"]), "-i", a.video, "-frames:v", "1",
                        "-q:v", "2", str(f)])
        r["file"] = str(f)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"video": a.video, "scored": len(rows), "picks": picks}, indent=1))


if __name__ == "__main__":
    main()
