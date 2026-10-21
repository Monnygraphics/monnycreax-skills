"""Find what to cut from a talking-head transcript, and turn text edits into cuts. No dependencies.

detect(words)            -> [{start, end, reason, text, sure}]   slates, rejected takes, retakes, false starts, stutters
from_text(words, text)   -> (exclude ranges, caption fixes)      the kept text, with words deleted (and spellings fixed)
to_text(words)           -> the transcript as editable text, one sentence per line

Times are source seconds. A range runs from the first dropped word to just before the next kept word, so the
cut step drops exactly those words and snaps the join into the quiet between them.
"""
import difflib
import re

SLATE = {"action", "cut", "rolling", "speed", "marker", "take", "ready", "again", "go", "okay", "ok", "alright", "and",
         "so", "um", "uh", "three", "two", "one", "3", "2", "1", "start", "can", "i", "we", "are", "good", "let's", "lets",
         "camera", "sound", "set", "yes", "yeah"}
SLATE_CORE = {"action", "cut", "rolling", "three", "3", "marker", "speed", "take"}
REJECT = [r"\blet me (start|try|do|say) (that |this |it )?(again|over)\b", r"\bstart (again|over)\b", r"\bscratch that\b",
          r"\bfrom the top\b", r"\bone more time\b", r"\blet me redo\b", r"\bno,? no\b", r"\bsorry,? (let me|i)\b",
          r"\bcan i start( again)?\b", r"\bwait,? wait\b", r"\bi messed up\b", r"\bcan i (finish|go|redo)\b",
          r"\b(that|last|this) sentence\b", r"\bthere'?s a gap\b", r"^(can )?i start( again)?\??$"]
ASIDE = {"okay", "ok", "no", "sorry", "wait", "gap", "hold", "on", "second", "sec", "again", "cut", "yeah", "hmm", "alright"}
UNFINISHED = {"the", "a", "an", "to", "and", "so", "i", "we", "you", "of", "in", "on", "about", "because", "my", "our",
              "your", "is", "are", "was", "that", "this", "but", "or", "for", "with", "if", "when", "it's", "its", "they"}
KEEP_DOUBLE = {"very", "really", "so", "no", "yes", "yeah", "bye", "ha", "go", "more", "much", "many", "far", "long"}


def norm(w):
    return re.sub(r"[^\w']", "", w.lower())


def sentences(words, gap=0.7):
    """Split into sentence-ish segments at end punctuation or pauses longer than `gap`."""
    segs, cur = [], []
    for i, w in enumerate(words):
        if cur and w["s"] - words[i - 1]["e"] > gap:
            segs.append(cur); cur = []
        cur.append(i)
        if re.search(r"[.?!]$", w["w"]):
            segs.append(cur); cur = []
    if cur:
        segs.append(cur)
    return segs


def _range(words, i0, i1):
    """Source range dropping words i0..i1 inclusive."""
    s = words[i0]["s"] - 0.02
    e = words[i1 + 1]["s"] - 0.02 if i1 + 1 < len(words) else words[i1]["e"] + 0.3
    return round(max(0.0, s), 3), round(max(e, s + 0.05), 3)


def detect(words):
    out = []
    if not words:
        return out
    toks = [norm(w["w"]) for w in words]
    segs = sentences(words)
    dur = words[-1]["e"]

    def add(i0, i1, reason, sure=True):
        s, e = _range(words, i0, i1)
        out.append({"start": s, "end": e, "reason": reason, "sure": sure,
                    "text": " ".join(words[k]["w"] for k in range(i0, i1 + 1))})

    # 1. slates at the very start or end ("action", "three two one", "can I start?")
    for seg in segs:
        t0, t1 = words[seg[0]]["s"], words[seg[-1]]["e"]
        st = {toks[k] for k in seg if toks[k]}
        if (t0 < 8 or t1 > dur - 6) and len(seg) <= 5 and st and st <= SLATE and st & (SLATE_CORE | {"start", "ready", "go"}):
            add(seg[0], seg[-1], "slate")
    # 1b. a countdown or "action" running straight into the first line ("3, 2, 1, let me tell you..."): word by word
    slate_after = set()
    k = 0
    while k < len(words) and words[k]["s"] < 8 and toks[k] in SLATE and toks[k] not in ("i", "we", "can", "so", "and"):
        k += 1
    if k and any(toks[j] in SLATE_CORE for j in range(k)):
        add(0, k - 1, "slate")
        slate_after.add(k)
    k = len(words) - 1
    while k >= 0 and words[k]["e"] > dur - 6 and toks[k] in SLATE_CORE | {"cut", "okay", "ok", "and"}:
        k -= 1
    # a closing slate is said after a pause ("...meaningful action." is speech, "... <pause> Cut." is a slate)
    if (k < len(words) - 1 and any(toks[j] in SLATE_CORE for j in range(k + 1, len(words)))
            and (k < 0 or words[k + 1]["s"] - words[k]["e"] > 0.5)):
        add(k + 1, len(words) - 1, "slate")
    # 2. takes rejected out loud: drop the failed attempt and the remark
    for n, seg in enumerate(segs):
        txt = " ".join(words[k]["w"] for k in seg).lower()
        if any(re.search(p, txt) for p in REJECT):
            # "let me start again" also drops the failed line before it; crew talk ("there's a gap") drops only itself,
            # unless the line before it is unfinished (no end punctuation)
            crew = re.search(r"gap|sentence|can i (finish|go)", txt)
            prev_open = n and not re.search(r"[.?!]$", words[segs[n - 1][-1]]["w"])
            first = segs[n - 1][0] if n and len(seg) <= 6 and (not crew or prev_open) else seg[0]
            add(first, seg[-1], "rejected take")
    # 3. retakes: the same run of 3+ words said again within 60 s means the line was re-recorded. Drop the earlier
    #    attempt up to where the redo starts, unless the earlier take is the complete one and the later a broken
    #    fragment: then drop the fragment instead. Repeats spaced further apart, or 3-word ones, are flagged "check".
    content = [k for k in range(len(words)) if toks[k]]
    pos = {k: n for n, k in enumerate(content)}
    def run_len(i, j):          # matching tokens from content positions i and j
        n = 0
        while j + n < len(content) and i + n < j and toks[content[i + n]] == toks[content[j + n]]:
            n += 1
        return n
    def sentence_end(ci):       # where this take's sentence ends: end punctuation only (a mid-line pause isn't an end)
        k = ci
        while k + 1 < len(content) and k - ci < 40 and not re.search(r"[.?!]$", words[content[k]]["w"]):
            k += 1
        return k
    def is_start(ci):           # retakes restart at the start of a sentence
        if ci == 0 or content[ci] in slate_after:     # the first word after a cut slate starts a line
            return True
        prev, cur = words[content[ci - 1]], words[content[ci]]
        return bool(re.search(r"[.?!]$", prev["w"])) or cur["s"] - prev["e"] > 0.4
    ci, taken = 0, set()
    while ci < len(content):
        best = None
        if not is_start(ci):
            ci += 1; continue
        for cj in range(ci + 3, len(content)):
            if words[content[cj]]["s"] - words[content[ci]]["s"] > 60:
                break
            # the redo may start a word or two into the original line ("If someone came..." / "...if <pause> someone came")
            n = max(run_len(ci + off, cj) for off in range(3) if ci + off < cj)
            stop = words[content[cj]]["s"] - words[content[cj] - 1]["e"] if content[cj] else 0
            # 4+ matching words, or 3 when the speaker stopped first ("It's about being X. It's about being Y" is rhetoric)
            # a line ending on , . ? ! is finished ("the fact that X, the fact that Y," is an anaphora list, not a retake)
            a_done = bool(re.search(r"[.,?!]$", words[content[cj] - 1]["w"])) if content[cj] else False
            # a redo follows a pause or an unfinished line; "What do I need to work on? What do I need to change?" is rhetoric
            # a redo that stalls in its first words ("Allow <13 s> someone...") is a failed attempt whatever came before
            stall = any(words[content[k + 1]]["s"] - words[content[k]]["e"] > 3
                        for k in range(cj, min(cj + 4, len(content) - 1)))
            if is_start(cj) and (n >= 4 or (n >= 3 and stop >= 1.5)) and (stop >= 0.9 or not a_done or stall):
                best = (cj, n); break
        if not best or content[ci] in taken:
            ci += 1; continue
        cj, n = best
        a_end, b_end = sentence_end(ci), sentence_end(cj)
        a_len, b_len = a_end - ci + 1, b_end - cj + 1
        gap = words[content[cj]]["s"] - words[content[ci]]["s"]
        pause = words[content[cj]]["s"] - words[content[cj] - 1]["e"] if content[cj] else 0
        sure = gap <= 45 and (n >= 4 or pause >= 1.5)   # 3-word match counts when the speaker stopped before the redo
        # the redo counts as broken only if it stalls (a 3 s+ gap inside it), like "Allow <13 s> someone to finish..."
        stalls = any(words[content[k + 1]]["s"] - words[content[k]]["e"] > 3 for k in range(cj, b_end))
        if b_len + 2 < a_len and b_end + 1 < len(content) and stalls:
            # the redo is a broken fragment ("Allow <13 s> someone to finish their thought.") and the first take was complete
            add(content[cj], content[b_end], "broken retake (kept the complete earlier take)", sure)
            taken.update(content[cj:b_end + 1]); ci += 1
        else:
            add(content[ci], content[cj] - 1, "retake (kept the later take)" if sure else "repeat: cut only if not deliberate",
                sure)
            taken.update(content[ci:cj]); ci = cj
    # 4. false starts: 1-3 words, a pause, then the same opening again ("So the... <pause> So the reason is")
    for n, a in enumerate(segs[:-1]):
        b = segs[n + 1]
        ta = [toks[k] for k in a if toks[k]]
        tb = [toks[k] for k in b if toks[k]]
        if (ta and len(ta) <= 3 and tb[:len(ta)] == ta and words[b[0]]["s"] - words[a[-1]]["e"] > 0.3
                and not re.search(r"[.?!]$", words[a[-1]]["w"])):
            add(a[0], a[-1], "false start")
    # 4b. trailed off ("I usually teach people about...") then restarted with the same words within a few seconds
    for n, a in enumerate(segs[:-1]):
        if not words[a[-1]]["w"].endswith(("...", "…", "-")):
            continue
        b = segs[n + 1]
        if words[b[0]]["s"] - words[a[-1]]["e"] > 8:
            continue
        ca = {toks[k] for k in a if len(toks[k]) > 3}
        cb = {toks[k] for k in b if len(toks[k]) > 3}
        if len(ca & cb) >= 2 or (ca and ca <= cb):
            add(a[0], a[-1], "trailed off, restarted")
    # 4c. self-correction "it's simple, no, finances sound simple": a word before "no,"/"sorry," comes back right after
    for i, w in enumerate(words):
        if toks[i] in ("no", "sorry") and w["w"].rstrip().endswith(","):
            before = [k for k in range(max(0, i - 5), i) if len(toks[k]) > 3]
            after = {toks[k] for k in range(i + 1, min(len(words), i + 7))}
            hit = [k for k in before if toks[k] in after]
            if hit:
                j = i - 1   # back to the start of the corrected clause (after the last , . ? !)
                while j > 0 and not re.search(r"[.,?!]$", words[j - 1]["w"]) and i - j < 6:
                    j -= 1
                add(j, i, "self-correction")
    # 4d. asides between pauses ("Okay." / "No," / "There's a gap."): cut when made only of aside words, else flag
    for a in segs:
        ta = [toks[k] for k in a if toks[k]]
        before = words[a[0]]["s"] - words[a[0] - 1]["e"] if a[0] else 9
        after = words[a[-1] + 1]["s"] - words[a[-1]]["e"] if a[-1] + 1 < len(words) else 9
        if ta and len(ta) <= 3 and before > 0.8 and after > 0.8 and set(ta) & ASIDE and len(set(ta) - ASIDE) <= 1:
            add(a[0], a[-1], "aside", sure=set(ta) <= ASIDE)
    # 5. stutters: the same word twice in a row ("the the", "I I")
    for i in range(len(words) - 1):
        if toks[i] and toks[i] == toks[i + 1] and toks[i] not in KEEP_DOUBLE and words[i + 1]["s"] - words[i]["e"] < 0.8:
            add(i, i, "stutter")
    # merge overlaps, keep the strongest reason
    out.sort(key=lambda r: r["start"])
    merged = []
    for r in out:
        if merged and r["start"] <= merged[-1]["end"]:
            m = merged[-1]
            m["end"] = max(m["end"], r["end"]); m["sure"] = m["sure"] and r["sure"]
            if r["reason"] not in m["reason"]:
                m["reason"] += " + " + r["reason"]
            continue
        merged.append(dict(r))
    return merged


def to_text(words):
    # lines break at sentence ends and long pauses only, so a line reads as a thought ("stop, go, and have it.")
    return "\n".join(" ".join(words[k]["w"] for k in seg) for seg in sentences(words, gap=2.0)) + "\n"


def from_text(words, text):
    """Align the edited text to the transcript. Deleted words become exclude ranges; a word replaced one-for-one
    (a spelling fix) becomes a caption fix {i, to}. Inserted words are ignored (captions show what was said)."""
    orig = [norm(w["w"]) for w in words]
    new_raw = text.split()
    new = [norm(w) for w in new_raw]
    sm = difflib.SequenceMatcher(None, orig, new, autojunk=False)
    drop, fixes = set(), []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":                    # same word, new spelling ("daytoday" -> "day-to-day", case, hyphens)
            for k in range(i2 - i1):
                o, n2 = words[i1 + k]["w"], new_raw[j1 + k]
                if o.rstrip(".,?!;:") != n2.rstrip(".,?!;:"):
                    fixes.append({"i": i1 + k, "to": n2})
        elif op == "delete":
            drop.update(range(i1, i2))
        elif op == "replace":
            if i2 - i1 == j2 - j1:          # same count: spelling fixes
                for k in range(i2 - i1):
                    fixes.append({"i": i1 + k, "to": new_raw[j1 + k]})
            else:                            # more words removed than typed back: drop the extra
                for k in range(i2 - i1):
                    if k < j2 - j1:
                        fixes.append({"i": i1 + k, "to": new_raw[j1 + k]})
                    else:
                        drop.add(i1 + k)
    ranges, run = [], []
    for i in sorted(drop):
        if run and i != run[-1] + 1:
            ranges.append(_range(words, run[0], run[-1])); run = []
        run.append(i)
    if run:
        ranges.append(_range(words, run[0], run[-1]))
    return ranges, fixes
