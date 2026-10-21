#!/usr/bin/env python3
"""
Cuts short, social-ready clips out of a long local video: precise trim,
optional 9:16 vertical reframe (blur-pad, never crops content out), and
optional burned-in captions transcribed fresh from just that clip's own
audio (more accurate than reusing timestamps from a fast full-video pass).

No external highlight-detection API is called here — Claude picks the
start/end timestamps (see SKILL.md) and hands them to this script, which
only does the mechanical ffmpeg/faster-whisper work.

Usage:
    python clip_video.py render <video_path> --start SEC --end SEC --out PATH
        [--no-vertical] [--no-captions] [--caption-model tiny|base|small|medium]

Requires: ffmpeg/ffprobe on PATH, faster-whisper package (both already
present on this machine, same as the video-analyser skill).
"""

import sys
import os
import json
import argparse
import subprocess
import tempfile
import hashlib


def _run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {result.stderr.strip()[-1500:]}")
    return result


def _extract_audio_range(video_path, start, duration, out_path):
    _run([
        "ffmpeg", "-y", "-ss", str(start), "-i", video_path, "-t", str(duration),
        "-ar", "16000", "-ac", "1", "-vn", out_path,
    ])


def _transcribe_wav(wav_path, model_size):
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(wav_path, beam_size=5, vad_filter=True)
    return [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]


def _extract_audio_compressed(video_path, out_path):
    """Small compressed mono file for upload — well under any API size cap even for hours of audio."""
    _run([
        "ffmpeg", "-y", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1",
        "-c:a", "libmp3lame", "-b:a", "64k", out_path,
    ])


def _transcribe_groq(audio_path, model):
    import requests

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable not set. Get a free key at "
            "https://console.groq.com/keys, then in PowerShell: "
            '$env:GROQ_API_KEY = "gsk_..."  (or set it as a permanent user env var).'
        )
    with open(audio_path, "rb") as f:
        resp = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (os.path.basename(audio_path), f, "audio/mpeg")},
            data={"model": model, "response_format": "verbose_json"},
            timeout=600,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    return [
        {"start": round(float(s["start"]), 2), "end": round(float(s["end"]), 2), "text": s["text"].strip()}
        for s in data.get("segments", [])
    ]


def _srt_timestamp(seconds):
    seconds = max(0.0, seconds)
    total_ms = round(seconds * 1000)
    hh, rem = divmod(total_ms, 3600000)
    mm, rem = divmod(rem, 60000)
    ss, ms = divmod(rem, 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def _write_srt(segments, out_path):
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_srt_timestamp(seg['start'])} --> {_srt_timestamp(seg['end'])}")
        lines.append(seg["text"])
        lines.append("")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _escape_for_subtitles_filter(path):
    p = os.path.abspath(path).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def cmd_render(args):
    if args.end <= args.start:
        raise ValueError("--end must be greater than --start")
    duration = args.end - args.start

    tmp_dir = tempfile.gettempdir()
    stem = hashlib.sha1(
        f"{args.video}{args.start}{args.end}{os.getpid()}".encode("utf-8", "surrogateescape")
    ).hexdigest()[:12]
    wav_path = os.path.join(tmp_dir, f"vc_{stem}.wav")
    srt_path = os.path.join(tmp_dir, f"vc_{stem}.srt")

    caption_segments = []
    caption_error = None
    try:
        if not args.no_captions:
            try:
                _extract_audio_range(args.video, args.start, duration, wav_path)
                if args.caption_engine == "groq":
                    caption_segments = _transcribe_groq(wav_path, args.caption_model_groq)
                else:
                    caption_segments = _transcribe_wav(wav_path, args.caption_model)
                if caption_segments:
                    _write_srt(caption_segments, srt_path)
            except Exception as e:
                caption_error = str(e)
                caption_segments = []

        filter_parts = []
        if not args.no_vertical:
            filter_parts.append(
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,gblur=sigma=20[bg]"
            )
            filter_parts.append("[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg]")
            filter_parts.append("[bg][fg]overlay=(W-w)/2:(H-h)/2[vbase]")
            current = "[vbase]"
        else:
            current = "[0:v]"

        have_captions = (not args.no_captions) and bool(caption_segments)
        final_map = None
        if have_captions:
            style = (
                "FontName=Arial,FontSize=16,Bold=1,PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H00000000,BorderStyle=1,Outline=1.2,Shadow=0,"
                "Alignment=2,MarginV=60"
            )
            escaped = _escape_for_subtitles_filter(srt_path)
            filter_parts.append(
                f"{current}subtitles=filename='{escaped}':force_style='{style}'[vout]"
            )
            final_map = "[vout]"
        elif current != "[0:v]":
            final_map = current

        out_dir = os.path.dirname(os.path.abspath(args.out))
        os.makedirs(out_dir, exist_ok=True)

        cmd = ["ffmpeg", "-y", "-ss", str(args.start), "-i", args.video, "-t", str(duration)]
        if filter_parts:
            cmd += ["-filter_complex", ";".join(filter_parts), "-map", final_map]
        else:
            cmd += ["-map", "0:v"]
        # first audio stream only: newer iPhone recordings ship a second "apac" spatial-audio
        # track this ffmpeg build can't decode, which crashes -map 0:a? outright
        cmd += ["-map", "0:a:0?"]
        cmd += [
            "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            args.out,
        ]
        _run(cmd)

        result = {
            "out": os.path.abspath(args.out),
            "start": args.start,
            "end": args.end,
            "duration_seconds": round(duration, 2),
            "vertical": not args.no_vertical,
            "captions_burned": have_captions,
            "caption_segment_count": len(caption_segments),
        }
        if caption_error:
            result["caption_error"] = caption_error
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        for p in (wav_path, srt_path):
            if os.path.exists(p):
                os.remove(p)


def cmd_transcribe_groq(args):
    stem = hashlib.sha1(
        os.path.abspath(args.video).encode("utf-8", "surrogateescape")
    ).hexdigest()[:12]
    audio_path = os.path.join(tempfile.gettempdir(), f"vc_rough_{stem}.mp3")
    try:
        _extract_audio_compressed(args.video, audio_path)
        segments = _transcribe_groq(audio_path, args.model)
        result = {"engine": "groq", "model": args.model, "segments": segments}
        output = json.dumps(result, indent=2, ensure_ascii=False)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(output)
            print(json.dumps(
                {"saved_to": args.out, "segment_count": len(segments), "engine": "groq"}, indent=2,
            ))
        else:
            print(output)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


def build_parser():
    parser = argparse.ArgumentParser(description="Cut social clips from a long local video", prog="clip_video")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("render", help="Cut, vertical-reframe, and caption one clip")
    p.add_argument("video", help="Path to source video file")
    p.add_argument("--start", type=float, required=True, help="Clip start, seconds")
    p.add_argument("--end", type=float, required=True, help="Clip end, seconds")
    p.add_argument("--out", required=True, help="Output mp4 path")
    p.add_argument("--no-vertical", action="store_true", help="Keep source aspect ratio instead of a 9:16 reframe")
    p.add_argument("--no-captions", action="store_true", help="Skip burned-in captions")
    p.add_argument(
        "--caption-model", default="base",
        help="faster-whisper model when --caption-engine local (default: base; try small if audio is noisy)",
    )
    p.add_argument(
        "--caption-engine", default="local", choices=["local", "groq"],
        help="Engine for this clip's precise captions (default: local; groq needs GROQ_API_KEY)",
    )
    p.add_argument(
        "--caption-model-groq", default="whisper-large-v3",
        help="Groq model when --caption-engine groq (default: whisper-large-v3, the more accurate tier)",
    )

    p = sub.add_parser(
        "transcribe_groq",
        help="Full-video rough transcript via Groq's hosted Whisper (fast, ~$0.04-0.11 per hour of audio)",
    )
    p.add_argument("video", help="Path to source video file")
    p.add_argument(
        "--model", default="whisper-large-v3-turbo",
        help="whisper-large-v3-turbo (cheap/fast, default) or whisper-large-v3 (more accurate)",
    )
    p.add_argument("--out", default=None, help="Write JSON transcript to this path instead of stdout")

    return parser


COMMANDS = {"render": cmd_render, "transcribe_groq": cmd_transcribe_groq}


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
