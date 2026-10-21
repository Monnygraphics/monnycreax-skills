# Audio, transcription and cutting: details

Loaded on demand from SKILL.md steps 2, 2b, 4 and 4b.

## Mixed-language transcription (Kenyan English + Swahili/Sheng)
Add `--mix sw` (plus `--vocab "names,brand words"`). Auto-detect labels such clips `sw` and garbles both
languages ("pekee" came out as "per care", "ama ni fire" as "A money fire"). Tested on Nyandi's reel (Oct 2026):
`small` + `--mix sw` recovers most Swahili in 24s. `--model medium` also gets "kwa hizo", but takes ~10 min per
minute of audio, so use it only for heavy Swahili. Neither caught "juu ya hii". Keep Swahili in the captions as
spoken (don't translate it), and fix what is left in the step 4 proofread.
Speed: `small` runs ~2x faster than realtime here (60s of audio in 33s). The default 4 threads is the fastest;
12 measured slower.

## Voice polish: bad audio only (`$P audio`)
It measures the recording and repairs it only if a check fails. Otherwise it keeps the original and writes
nothing new. Pass the `use_for_cut` it returns to `cut --audio-from`: the edit is still decided on the original
recording. Cutting the cleaned copy directly moved cut points by up to 0.9 s, because its pauses are far quieter.

| Check | Fails when (speech vs real pauses, above 100 Hz) | Fix |
|---|---|---|
| noise | speech < 20 dB above the room floor (hiss, hum, AC, a music bed) | DeepFilterNet, capped at 24 dB so the voice keeps its air |
| background | the pauses swing > 9 dB and are loud (voices, traffic, doors) | DeepFilterNet at 40 dB |
| echo | sound takes > 0.24 s to fall 20 dB after a word (clean ~0.12) | WPE dereverb, then the denoiser |
| heavy / thin | low-mid vs clarity band > 17 dB / < 6 dB (normal speech ~12) | EQ: cut 250 Hz mud and lift 3.6 kHz presence / warm low shelf |
| clipping | > 0.1% of samples at full scale | reported (it can't be undone; ask for another take) |

Any fix also adds a rumble high-pass, a de-esser and gentle compression. Loudness is still set at render. The
output keeps exact timing (cross-correlation lag 0). Measured Oct 2026:
- Client A's AC-room takes failed **noise** at 8 dB and improved to 27.5 dB.
- A 0.7 s echo test went from 0.30 to 0.23 s.
- 2 min of audio takes ~25 s.

Limits: intermittent bursts can read as "echo" rather than "background", but they still go through the
denoiser. Open-source dereverb fixes mild rooms, not a bathroom. Finished reels with a music bed are not raw
footage, so don't diagnose those. Tools: `~/.audio-tools/deep-filter.exe` (DeepFilterNet 0.5.6, MIT/Apache) and
`~/.audio-venv` (nara_wpe MIT, scipy, soundfile). The DeepFilterNet Python package does not work there: there is
no torchaudio for torch 2.12.

## Review page (OneTake idea, optional)
When the user or client wants to check the cut themselves, run `$P review <raw video> --words <dir>/words.json
--strike "<your suggested ranges>" --serve` (background). It opens a page with the video beside the transcript,
fillers and Claude's suggestions pre-struck.
- Click a word to play from it; Shift+click selects; X strikes or restores; double-click fixes a caption word.
- Playback skips struck words.
- "Copy for Claude" gives `{"exclude": "...", "fixes": [...]}`.

Plain `review` without `--serve` writes the file to open directly (file:// seeks fine).

## Cut quality (ideas from Attention Machine, our own code)
- **Snapped to quiet:** every cut moves to the quietest 20 ms nearby, never into a neighbouring kept word.
  `cuts_on_sound` lists the cuts that still land on sound: listen to those, or widen the exclude. `--no-snap` turns
  it off.
- **Frame grid:** cuts sit on the source's frames, so the picture and sound stay the same length. Before this,
  the lips drifted up to 0.15s by the end of a heavily cut reel.
- **J-cuts:** `--jcut 0.08` lets the next line be heard ~2 frames before its picture. Use 0.06-0.12 on talking
  heads; 0 for slates or music-synced edits.
- **Numbers as digits** in captions by default (25, 100%, 2026, "193 million"). Small standalone numbers stay
  words ("one time"). `--no-digits` keeps words.
- Other options: `--speed 1.03-1.06` for a slow speaker (pitch preserved), `--silence-db` (default speech mean
  -20 dB), `--fps 30` to force. Roughly 8-25% removed is normal for a raw phone take.


## Auto-cut and edit-by-text (2026-10-20)
`scripts/autocut.py` reads the transcript and finds:
- **slates:** countdowns or "action", even when run into the first line
- **takes rejected out loud:** "let me start again", "can I start?", "scratch that"
- **retakes:** the same 3-4+ words restarting a line after a pause or an unfinished line; it keeps the more complete
  take, so a redo that stalls is dropped instead
- **false starts, self-corrections** ("it's simple, no, …"), **crew asides** ("there's a gap", "can I finish that
  last sentence") and **stutters**

Deliberate rhetoric is left alone: anaphora ("the fact that X, the fact that Y"), parallel questions, and the same
opening with different endings and no pause ("It's about being X. It's about being Y").

**Tested** on 17 real clips (Client A 00-07, Client B 09-18): every hand-made retake, slate and crew-talk cut was
found, with zero false cuts. Not found: meaning slips such as "singleness, marriage, … singleness". Those are fixed
by text.

**Edit by text:** `transcript --edit kept.txt`, delete words, fix spellings, then `cut --text kept.txt`. Deleted words
become cuts; respelled, hyphenated or recapitalised words become caption fixes.

## Speed: camera format matters most
Decoding is the floor. Client B's Sony files (4K HEVC, 10-bit 4:2:2, 50 fps) decode at about 4 s of CPU per second of
footage, and parallel processes barely help (the decoder already uses the cores). A 100 s clip takes ~7 min to cut.
iPhone or 4:2:0 8-bit files are several times faster. Ask clients to shoot 4K or 1080p, 4:2:0 8-bit, 25/30 fps for
reels. `cut` drops to the output frame rate before scaling and writes `cut.mp4` with x264 ultrafast at CRF 12, a
visually lossless stepping stone.
