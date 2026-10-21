#!/usr/bin/env python3
"""
Local video analyser — no external API, no account, no credits.

Wraps ffmpeg (audio + frame extraction) and faster-whisper (local speech-to-
text) so Claude can build its own understanding of a video file directly:
read the spoken-word transcript this script produces, then look at the
extracted frame images itself with the Read tool for on-screen text,
diagrams, and visuals. There is no third-party "describe this video" call
in the loop — Claude's own vision does that part.

Usage:
    python analyze_video.py <command> [args...]

Commands:
    info <video_path>
        Duration, resolution, fps via ffprobe.

    transcribe <video_path> [--model tiny|base|small|medium] [--language en] [--out PATH]
        Extracts audio and runs local faster-whisper. Prints JSON with
        timestamped segments. --model default "small" (already cached
        locally; bump to "medium" for tricky audio, drop to "base"/"tiny"
        for speed on long files).

    extract_frames <video_path> [--out-dir DIR] [--interval SECONDS] [--max-frames N]
        Samples frames at a fixed interval via ffmpeg and prints JSON
        listing each frame's file path + timestamp, so you can Read() them.
        Default: evenly spaced to land around --max-frames (default 24),
        never closer together than 1s.

    extract_audio <video_path> [--out PATH]
        Just the 16kHz mono wav extraction step, exposed standalone in case
        you want to feed the audio to something else.

Requires: ffmpeg + ffprobe on PATH, and the faster-whisper Python package
(both already present on this machine).
"""

import sys
import os
import json
import argparse
import subprocess
import tempfile
import hashlib


def _ffprobe_duration(video_path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    video_stream = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    return duration, data, video_stream


def _parse_fps(rate_str):
    try:
        num, den = rate_str.split("/")
        den = float(den)
        return round(float(num) / den, 2) if den else None
    except Exception:
        return None


def cmd_info(args):
    duration, _data, video_stream = _ffprobe_duration(args.video)
    print(json.dumps({
        "duration_seconds": round(duration, 2),
        "width": video_stream.get("width") if video_stream else None,
        "height": video_stream.get("height") if video_stream else None,
        "fps": _parse_fps(video_stream.get("r_frame_rate", "")) if video_stream else None,
    }, indent=2))


def _extract_audio(video_path, out_path=None):
    if out_path is None:
        stem = hashlib.sha1(os.path.abspath(video_path).encode("utf-8", "surrogateescape")).hexdigest()[:12]
        out_path = os.path.join(tempfile.gettempdir(), f"va_{stem}.wav")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-ar", "16000", "-ac", "1", "-vn", out_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr.strip()[-800:]}")
    return out_path


def cmd_extract_audio(args):
    out_path = _extract_audio(args.video, args.out)
    print(json.dumps({"audio_path": out_path}, indent=2))


def cmd_transcribe(args):
    audio_path = _extract_audio(args.video)
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(args.model, device="cpu", compute_type="int8")
        segments, info = model.transcribe(
            audio_path, language=args.language, beam_size=5, vad_filter=True,
        )
        result = {
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration_seconds": round(info.duration, 2),
            "segments": [
                {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
                for s in segments
            ],
        }
        output = json.dumps(result, indent=2, ensure_ascii=False)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(output)
            print(json.dumps({"saved_to": args.out, "segment_count": len(result["segments"])}, indent=2))
        else:
            print(output)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


def cmd_extract_frames(args):
    duration, _data, _vs = _ffprobe_duration(args.video)

    interval = args.interval if args.interval else max(1.0, duration / args.max_frames)

    if args.out_dir:
        out_dir = args.out_dir
    else:
        stem = hashlib.sha1(os.path.abspath(args.video).encode("utf-8", "surrogateescape")).hexdigest()[:12]
        out_dir = os.path.join(tempfile.gettempdir(), f"va_frames_{stem}")
    os.makedirs(out_dir, exist_ok=True)

    pattern = os.path.join(out_dir, "frame_%04d.jpg")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", args.video, "-vf", f"fps=1/{interval}", "-q:v", "2", pattern],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed: {result.stderr.strip()[-800:]}")

    frames = sorted(f for f in os.listdir(out_dir) if f.startswith("frame_") and f.endswith(".jpg"))
    listing = [
        {"path": os.path.join(out_dir, f), "timestamp_seconds": round(i * interval, 2)}
        for i, f in enumerate(frames)
    ]
    print(json.dumps({"out_dir": out_dir, "interval_seconds": round(interval, 2), "frames": listing}, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Local video analyser (ffmpeg + faster-whisper)", prog="analyze_video")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("info", help="Duration/resolution/fps via ffprobe")
    p.add_argument("video", help="Path to video file")

    p = sub.add_parser("transcribe", help="Local speech-to-text via faster-whisper")
    p.add_argument("video", help="Path to video file")
    p.add_argument("--model", default="small", help="tiny|base|small|medium (default: small)")
    p.add_argument("--language", default=None, help="Lock language e.g. 'en' (default: auto-detect)")
    p.add_argument("--out", default=None, help="Write JSON transcript to this path instead of stdout")

    p = sub.add_parser("extract_frames", help="Sample frames for visual inspection")
    p.add_argument("video", help="Path to video file")
    p.add_argument("--out-dir", default=None, help="Directory for extracted frames (default: temp dir)")
    p.add_argument("--interval", type=float, default=None, help="Seconds between frames (overrides --max-frames)")
    p.add_argument("--max-frames", type=int, default=24, help="Target frame count when --interval isn't set (default: 24)")

    p = sub.add_parser("extract_audio", help="Extract 16kHz mono wav only")
    p.add_argument("video", help="Path to video file")
    p.add_argument("--out", default=None, help="Output wav path (default: temp dir)")

    return parser


COMMANDS = {
    "info": cmd_info,
    "transcribe": cmd_transcribe,
    "extract_frames": cmd_extract_frames,
    "extract_audio": cmd_extract_audio,
}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = build_parser().parse_args()
    try:
        COMMANDS[args.command](args)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
