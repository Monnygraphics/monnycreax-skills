"""Align each reel's spoken words to its teleprompter script, then fix the cut automatically.

Usage: python align.py <batch.json> <script.md> [--only 12] [--dry]

script.md: one "## <reel id>" heading per reel followed by its script text.
For every reel (source words minus its current `exclude` ranges):
  - repeats and restarts ("because because", "take ... take dress") -> the earlier attempt joins `exclude`
  - short stray words not in the script ("No,", "Okay.", "Oh yeah") -> `exclude`
  - the same word heard or spelled differently (organization/organisation, impotent/important) -> `fix_at`
    [[source time, script word]], applied to that one word only
  - real deviations (she said a different word) are left as spoken and only reported
Writes the merged exclude/fix back into batch.json (kept under "align") and prints one line per reel.
"""
import difflib
import json
import os
import re
import sys
from pathlib import Path

FN = {"a", "an", "the", "that", "and", "so", "no", "okay", "oh", "yeah", "because", "um", "uh", "like", "just", "i", "it"}
NUM = {"30": "thirty", "10": "ten", "2": "two", "5": "five"}


def tok(w):
    w = w.lower().replace("’", "'").replace("-", "")
    w = re.sub(r"[^a-z0-9']", "", w)
    return NUM.get(w, w)


def ranges(s):
    out = []
    for p in (s or "").split(","):
        if "-" in p:
            a, b = p.split("-", 1)
            out.append((float(a), float(b)))
    return out


def fmt(rs):
    return ",".join(f"{a:.2f}-{b:.2f}" for a, b in sorted(rs))


def merge(rs):
    out = []
    for a, b in sorted(rs):
        if out and a <= out[-1][1] + 0.05:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(x) for x in out]


def scripts(md):
    d, cur = {}, None
    for line in Path(md).read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            cur = line[3:].strip(); d[cur] = []
        elif cur:
            d[cur].append(line)
    return {k: " ".join(v).split() for k, v in d.items()}


def align(r, words, script):
    excl0 = ranges(r.get("exclude", ""))
    kept = [w for w in words if not any(a <= w["s"] < b for a, b in excl0)]
    sc = [tok(w) for w in script]
    cut, fixes, dev = [], [], []
    scs = " " + " ".join(sc) + " "
    k = 0   # immediate repeats ("because because", "you are, you are"): drop the first copy unless the script repeats too
    while k < len(kept):
        hit = 0
        for n in (4, 3, 2, 1):
            x = [tok(w["w"]) for w in kept[k:k + n]]
            y = [tok(w["w"]) for w in kept[k + n:k + 2 * n]]
            if len(y) == n and x == y and " " + " ".join(x + y) + " " not in scs:
                a0 = kept[k]["s"] - 0.04 if k == 0 else max(kept[k]["s"] - 0.04, kept[k - 1]["e"] + 0.02)
                cut.append((round(a0, 2), round(kept[k + n]["s"] - 0.06, 2)))
                dev.append(("cut", " ".join(w["w"] for w in kept[k:k + n])))
                kept = kept[:k] + kept[k + n:]
                hit = 1
                break
        if not hit:
            k += 1
    sp = [tok(w["w"]) for w in kept]
    sm = difflib.SequenceMatcher(None, sc, sp, autojunk=False)

    def span(i, j):   # source range of kept[i..j-1], clamped clear of the neighbours
        a = kept[i]["s"] - 0.04
        b = kept[j - 1]["e"] + 0.04
        if i > 0:
            a = max(a, kept[i - 1]["e"] + 0.02)
        if j < len(kept):
            b = min(b, kept[j]["s"] - 0.06)
        return (round(a, 2), round(b, 2))

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "insert":
            n = j2 - j1
            ins = sp[j1:j2]
            after = sp[j2:j2 + n + 2]
            # a restart: the inserted words reappear right after (the clean attempt follows)
            restart = any(x in after for x in ins)
            stray = n == 1 and ins[0] in FN or 2 <= n <= 4   # one content word ("most") is just her phrasing
            if restart or stray:
                cut.append(span(j1, j2))
                dev.append(("cut", " ".join(w["w"] for w in kept[j1:j2])))
            else:
                dev.append(("extra?", " ".join(w["w"] for w in kept[j1:j2])))
        elif op == "replace":
            said = " ".join(w["w"] for w in kept[j1:j2])
            want = " ".join(script[i1:i2])
            x, y = sp[j1:j2], sc[i1:i2]
            same = len(x) == len(y) and all(p[:4] == q[:4] and abs(len(p) - len(q)) <= 2 for p, q in zip(x, y))
            if same:   # spelling / mishearing of the same word: caption shows the script word, pinned to its time
                for k in range(j2 - j1):
                    w = kept[j1 + k]
                    tail = re.sub(r"^.*?([.,!?;:]*)$", r"", w["w"])
                    new = script[i1 + k].strip('.,!?;:"')
                    new = new[0].upper() + new[1:] if w["w"][:1].isupper() else new
                    fixes.append([round(w["s"], 2), new + tail])
            elif (j2 - j1) > (i2 - i1) + 2:   # spoke much more than the script here: likely a restart
                dev.append(("extra?", said))
            else:
                dev.append(("said", f"{said} | script: {want}"))
    return cut, fixes, dev


def main():
    a = sys.argv[1:]
    bj, md = a[0], a[1]
    only = a[a.index("--only") + 1].split(",") if "--only" in a else None
    cfg = json.loads(Path(bj).read_text(encoding="utf-8"))
    out = Path(os.path.expandvars(cfg["out"]))
    sc = scripts(md)
    for r in cfg["reels"]:
        if only and r["id"][:2] not in only:
            continue
        if r["id"] not in sc:
            print(r["id"], "no script"); continue
        base = r.setdefault("align", {"exclude": r.get("exclude", ""), "fix": r.get("fix", [])})
        r["exclude"], r["fix"] = base["exclude"], list(base["fix"])   # re-runs start from the hand-set values
        wj = out / "_map" / f"{Path(r['src']).stem}.json"
        words = json.loads(wj.read_text(encoding="utf-8"))["words"]
        cut, fixes, dev = align(r, words, sc[r["id"]])
        r["exclude"] = fmt(merge(ranges(r["exclude"]) + cut))
        r["fix_at"] = fixes   # [source start time, caption word]
        r["force"] = True
        print(f"{r['id']}: cut {len(cut)}, caption fixes {len(fixes)}: " + "; ".join(f"{y}" for x, y in fixes)
              + "".join(f"\n   {k}: {v}" for k, v in dev if k != "cut")
              + ("\n   cuts: " + " | ".join(v for k, v in dev if k == "cut") if cut else ""))
    if "--dry" not in a:
        Path(bj).write_text(json.dumps(cfg, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
