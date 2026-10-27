"""Stage `windows`: where each board sits on the final timeline.

Reads script-marked.md (`[▸ SLIDE <n> · <title>]` and `[CAMERA]` markers, the lines under each) and words.json, aligns
every block's words to the spoken words, and writes windows.json:

  {"fps": "24000/1001", "wav_duration": 1655.654, "timing_source": "words.tsv" | "faster-whisper",
   "items": [{"kind": "board", "n": 4, "title": ..., "file": "04-OwnTeam.html", "start": .., "end": ..,
              "script_lines": [...], "words": [{"w","t","e"}...], "matched": 0.86, "uncovered": [...]},
             {"kind": "camera", "start": .., "end": .., "words": [...]}, ...]}

How the times are decided (DESIGN.md, windows.json):
- One global alignment of all script tokens against all spoken tokens (difflib, monotonic by construction), so a block
  can never start before the previous block's matched words.
- start = the block's first credibly matched word - 0.15 s, never inside the previous block (clamped to the end of
  the previous block's last matched word). end = the next item's start; the last item ends at the WAV's end.
- Every spoken word stays in the window it falls in. Ad-libs are never dropped.
- A block with no lines (a hold board), or one whose words were not found well enough to trust (under 40 % matched
  and no run of 3 matched words), takes the gap between its neighbours and is reported, never guessed.
- Spoken stretches over 15 s with no script match are listed in the window as "uncovered".
- Every boundary is snapped down to a frame at --fps, so round((end - start) * fps) adds up exactly to the track.
"""
from __future__ import annotations

import difflib
import math
import re
import sys
from fractions import Fraction
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.common import log, parse_fps, probe_duration, read_json, tokens, write_json  # noqa: E402

LEAD = 0.15            # a board opens this long before its first word
LOW_MATCH = 0.40       # under this share of matched script tokens a block is reported
UNCOVERED_S = 15.0     # spoken stretch with no script match that gets flagged

# [▸ SLIDE 4 · Title], also tolerated: [> SLIDE 4 - Title], [► SLIDE 4: Title], [▸SLIDE 4], markdown-wrapped markers.
MARKER = re.compile(r"^\[\s*(?:▸|►|▶|‣|>|&gt;|»)?\s*SLIDE\s*#?\s*(\d+)\s*(?:[·•∙\-–—:|.,]+\s*([^\]]*?))?\s*\](.*)$",
                    re.I)
CAMERA = re.compile(r"^\[\s*(?:▸|►|▶|>|&gt;)?\s*CAMERA\b[^\]]*\](.*)$", re.I)
SKIP_LINE = re.compile(r"^(#{1,6}\s|-{3,}$|\*{3,}$|_{3,}$|<!--)")
DIRECTION = re.compile(r"^[\[(].*[\])]$")          # a line that is only a bracketed direction: [B-ROLL], (pause)
LINE_NO = re.compile(r"^L\d+[\s:.)\]\-–]+", re.I)   # "L12: ..." line numbers from the brief
FOLD = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "“": '"', "”": '"', "—": " ", "–": " ", " ": " "})


def fold(text: str) -> str:
    """Typographic quotes/dashes to plain ones so 'nobody’s' matches whisper's "nobody's"."""
    return text.translate(FOLD)


def speech_text(line: str) -> str:
    """The spoken part of a script line: line numbers, inline [directions] and markdown quote marks removed."""
    s = LINE_NO.sub("", line.strip())
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = s.lstrip(">").strip()
    return fold(s)


# ── script-marked.md ──────────────────────────────────────────────────────────────────────────────────────────────
def parse_script(path) -> list[dict]:
    """Blocks in file order: {"kind": "board"|"camera", "n", "title", "lines": [verbatim script lines]}."""
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    blocks: list[dict] = []
    pre: list[str] = []
    cur = None
    for raw in text.split("\n"):
        line = raw.strip().lstrip("﻿")
        core = line.strip("*_`").strip()
        m = MARKER.match(core)
        if m:
            cur = {"kind": "board", "n": int(m.group(1)), "title": (m.group(2) or "").strip(), "lines": []}
            blocks.append(cur)
            rest = (m.group(3) or "").strip().strip("*_`").strip()
            if rest:
                cur["lines"].append(rest)
            continue
        m = CAMERA.match(core)
        if m:
            cur = {"kind": "camera", "lines": []}
            blocks.append(cur)
            rest = (m.group(1) or "").strip().strip("*_`").strip()
            if rest:
                cur["lines"].append(rest)
            continue
        if not line or SKIP_LINE.match(line) or DIRECTION.match(line):
            continue
        (pre if cur is None else cur["lines"]).append(line)
    if pre and blocks:
        # spoken lines before the first marker: an on-camera opening (reported; harmless when it is just notes)
        blocks.insert(0, {"kind": "camera", "lines": pre, "implicit": True})
    return blocks


# ── tokens with their word index ─────────────────────────────────────────────────────────────────────────────────
def word_tokens(words: list[dict]) -> tuple[list[str], list[int]]:
    """Normalised tokens of the spoken words and, per token, the index of its word.

    Number splits the transcriber makes are joined back: "$5" ",000" -> "$5000", "$9" ".40" -> "$940",
    "38" "%" -> "38%", so they match the script's "$5,000", "$9.40", "38%".
    """
    toks: list[str] = []
    owner: list[int] = []
    for i, w in enumerate(words):
        raw = fold(w["w"]).strip()
        tt = tokens(raw)
        if not tt:
            continue
        if toks and owner[-1] == i - 1 and re.search(r"\d", toks[-1]):
            if (raw[:1] in ".," and tt[0].isdigit()) or tt[0] == "%":
                toks[-1] = toks[-1] + tt[0]
                tt = tt[1:]
        for t in tt:
            toks.append(t)
            owner.append(i)
    return toks, owner


def align(script_toks: list[str], spoken_toks: list[str]) -> tuple[list, list]:
    """Map each script token to a spoken token index (or None), with the length of the matching run it is in."""
    sm = difflib.SequenceMatcher(None, script_toks, spoken_toks, autojunk=False)
    m: list = [None] * len(script_toks)
    run: list = [0] * len(script_toks)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            m[a + k] = b + k
            run[a + k] = size
    return m, run


def credible(j: int, m: list, run: list) -> bool:
    """A match is trusted when it is part of a run of 2+, or a neighbouring script token matched within 3 words."""
    if m[j] is None:
        return False
    if run[j] >= 2:
        return True
    for k in (j - 2, j - 1, j + 1, j + 2):
        if 0 <= k < len(m) and m[k] is not None and abs(m[k] - m[j]) <= 3 + abs(k - j):
            return True
    return False


def _trim(cl: list[tuple[int, int]], reverse: bool = False) -> tuple[int, int] | None:
    """First (or last) match of a block, skipping up to a quarter of strays that sit far from the block's next match."""
    if not cl:
        return None
    seq = cl[::-1] if reverse else cl
    k, limit = 0, max(1, len(seq) // 4)
    while k + 1 < len(seq) and k < limit:
        (j0, w0), (j1, w1) = seq[k], seq[k + 1]
        if abs(w1 - w0) > abs(j1 - j0) + 3:
            k += 1
            continue
        break
    return seq[k]


def find_boards(boards_dir) -> dict[int, str]:
    """Board number -> file name, from `NN-Name.html` in the boards folder."""
    out: dict[int, str] = {}
    if not boards_dir or not Path(boards_dir).is_dir():
        return out
    for p in sorted(Path(boards_dir).iterdir()):
        m = re.match(r"^(\d{1,3})[-_ .]", p.name)
        if p.suffix.lower() in (".html", ".htm") and m:
            n = int(m.group(1))
            if n in out:
                log(f"  two board files for board {n}: {out[n]} and {p.name}; using {out[n]}")
                continue
            out[n] = p.name
    return out


# ── the stage ─────────────────────────────────────────────────────────────────────────────────────────────────────
def compute(blocks: list[dict], words: list[dict], wav_duration: float, fps: Fraction) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    # script tokens, block by block
    s_toks: list[str] = []
    s_block: list[int] = []
    for bi, b in enumerate(blocks):
        b["tok0"] = len(s_toks)
        for line in b["lines"]:
            for t in tokens(speech_text(line)):
                s_toks.append(t)
                s_block.append(bi)
        b["tok1"] = len(s_toks)
    w_toks, owner = word_tokens(words)
    m, run = align(s_toks, w_toks)

    # which spoken words are covered by a trusted match (for "uncovered")
    covered = [False] * len(words)
    for j in range(len(s_toks)):
        if credible(j, m, run):
            covered[owner[m[j]]] = True

    # per block: matched share and anchors
    for b in blocks:
        n_tok = b["tok1"] - b["tok0"]
        js = range(b["tok0"], b["tok1"])
        b["matched"] = round(sum(1 for j in js if m[j] is not None) / n_tok, 3) if n_tok else 0.0
        cl = [(j, owner[m[j]]) for j in js if credible(j, m, run)]
        longest = max((run[j] for j in js if m[j] is not None), default=0)
        b["anchored"] = bool(cl) and (b["matched"] >= LOW_MATCH or longest >= 3)
        b["first_w"] = _trim(cl)[1] if b["anchored"] else None
        b["last_w"] = _trim(cl, reverse=True)[1] if b["anchored"] else None
        label = f"board {b['n']}" if b["kind"] == "board" else "camera block"
        if n_tok == 0:
            b["timing"] = "gap"
            if b["kind"] == "board":
                log(f"  {label}: no lines under the marker, it is a hold board and takes the gap between its neighbours")
        elif not b["anchored"]:
            b["timing"] = "gap"
            if b.get("implicit"):
                continue
            warnings.append(f"{label}: only {b['matched']:.0%} of its script words were found in the audio, so it is "
                            "not placed by its words; it takes the gap between its neighbours. Check the script "
                            "against the final cut.")
        else:
            b["timing"] = "words"
            if b["matched"] < LOW_MATCH:
                warnings.append(f"{label}: only {b['matched']:.0%} of its script words were found in the audio "
                                "(placed by the words that were found; check it).")

    # text before the first marker that was not spoken (a title, notes for the reader) is not a camera stretch
    for b in [b for b in blocks if b.get("implicit") and not b["anchored"]]:
        log("  the text before the first marker is not in the audio (notes, not speech); ignored")
        blocks.remove(b)

    # starts of anchored blocks
    prev_end = 0.0
    for b in blocks:
        if b["timing"] != "words":
            continue
        t0 = words[b["first_w"]]["t"]
        b["start"] = max(t0 - LEAD, prev_end, 0.0)
        prev_end = max(prev_end, words[b["last_w"]]["e"])
        b["prev_end"] = prev_end

    # gap items take the gap between their anchored neighbours, split evenly when several sit together
    i = 0
    while i < len(blocks):
        if blocks[i]["timing"] == "words":
            i += 1
            continue
        k = i
        while k < len(blocks) and blocks[k]["timing"] != "words":
            k += 1
        before = next((blocks[x] for x in range(i - 1, -1, -1) if blocks[x]["timing"] == "words"), None)
        after = blocks[k] if k < len(blocks) else None
        g0 = words[before["last_w"]]["e"] if before else 0.0
        g1 = after["start"] if after else wav_duration
        if after is not None and before is not None:
            g0 = min(g0, g1)
        span = max(0.0, g1 - g0)
        for x in range(i, k):
            blocks[x]["start"] = g0 + span * (x - i) / (k - i)
        if span < 1.0:
            names = ", ".join(f"board {blocks[x]['n']}" if blocks[x]["kind"] == "board" else "a camera block"
                              for x in range(i, k))
            warnings.append(f"{names}: the gap between its neighbours is only {span:.2f} s.")
        i = k

    # frame-snap, keep the order, close every item at the next one's start
    items = []
    last_f = -1
    for b in blocks:
        f = math.floor(b["start"] * fps + 1e-6)   # floor: a board never opens after its first word
        if f < last_f:
            f = last_f
        last_f = f
        b["f0"] = f
    end_f_total = wav_duration * fps   # the last item ends at the WAV's end exactly (not snapped)
    if blocks and blocks[0]["f0"] > 0:
        first_t = blocks[0]["f0"] / fps
        if any(w["t"] < first_t for w in words):
            blocks.insert(0, {"kind": "camera", "lines": [], "implicit": True, "f0": 0, "matched": 0.0,
                              "timing": "gap", "tok0": 0, "tok1": 0})
            warnings.append(f"there is speech before the first marker's words (0-{float(first_t):.2f} s); it is "
                            "kept as a camera stretch. Add a [CAMERA] or [▸ SLIDE] marker for it.")
        else:
            blocks[0]["f0"] = 0
    for idx, b in enumerate(blocks):
        start = round(float(Fraction(b["f0"]) / fps), 4)
        end = round(float(Fraction(blocks[idx + 1]["f0"]) / fps), 4) if idx + 1 < len(blocks) else round(wav_duration, 4)
        if idx + 1 == len(blocks) and b["f0"] >= end_f_total:
            warnings.append("the last block starts at or after the end of the WAV; is this the right WAV?")
        it = {"kind": b["kind"]}
        if b["kind"] == "board":
            it.update({"n": b["n"], "title": b.get("title", ""), "file": None})
        it.update({"start": start, "end": end})
        if b.get("implicit"):
            it["implicit"] = True
        it["script_lines"] = list(b["lines"])
        it["timing"] = b["timing"]
        it["matched"] = round(b["matched"], 2)
        it["words"] = []
        it["uncovered"] = []
        items.append(it)

    # every spoken word goes to the window it starts in (ad-libs included)
    k = 0
    for wi, w in enumerate(words):
        while k + 1 < len(items) and w["t"] >= items[k + 1]["start"]:
            k += 1
        items[k]["words"].append({"w": w["w"], "t": w["t"], "e": w["e"]})
        w["_item"] = k
    if words and words[-1]["e"] > wav_duration + 0.5:
        warnings.append(f"the words run to {words[-1]['e']:.2f} s but the WAV is {wav_duration:.2f} s long: are the "
                        "words.tsv and the WAV from the same final cut?")

    # uncovered: runs of spoken words with no trusted script match, longer than 15 s
    run_start = None
    for wi in range(len(words) + 1):
        unc = wi < len(words) and not covered[wi]
        if unc and run_start is None:
            run_start = wi
        elif not unc and run_start is not None:
            a, z = run_start, wi - 1
            dur = words[z]["e"] - words[a]["t"]
            if dur > UNCOVERED_S:
                # the window holding most of the stretch
                share: dict[int, float] = {}
                for x in range(a, z + 1):
                    share[words[x]["_item"]] = share.get(words[x]["_item"], 0.0) + (words[x]["e"] - words[x]["t"])
                host = max(share, key=share.get)
                items[host]["uncovered"].append({"start": round(words[a]["t"], 3), "end": round(words[z]["e"], 3),
                                                 "text": " ".join(words[x]["w"] for x in range(a, z + 1))})
            run_start = None
    for w in words:
        w.pop("_item", None)
    for it in items:
        for u in it["uncovered"]:
            where = f"board {it['n']}" if it["kind"] == "board" else "a camera stretch"
            warnings.append(f"{where}: {u['end'] - u['start']:.1f} s of speech ({u['start']:.2f}-{u['end']:.2f} s) "
                            "with no script line under it (kept in the window; consider a new board).")
    return items, warnings


def boundary_table(items: list[dict]) -> str:
    """Plain table: n, start, end, duration, matched, the two words before and the two words after each start."""
    rows = [f"{'n':>4}  {'title':<30} {'start':>9} {'end':>9} {'dur':>7} {'match':>6}  around the start",
            f"{'-' * 4}  {'-' * 30} {'-' * 9} {'-' * 9} {'-' * 7} {'-' * 6}  {'-' * 40}"]
    allw = [w for it in items for w in it["words"]]
    for it in items:
        before = [w["w"] for w in allw if w["t"] < it["start"]][-2:]
        after = [w["w"] for w in allw if w["t"] >= it["start"]][:2]
        n = str(it.get("n", "cam"))
        tag = "" if it.get("timing") == "words" else "  (gap)"
        title = (it.get("title") or ("(camera)" if it["kind"] == "camera" else ""))
        title = title if len(title) <= 30 else title[:29] + "…"
        rows.append(f"{n:>4}  {title:<30} {it['start']:>9.2f} {it['end']:>9.2f} {it['end'] - it['start']:>7.2f} "
                    f"{it['matched']:>6.0%}  {' '.join(before):>24} | {' '.join(after)}{tag}")
    return "\n".join(rows)


def run(ctx) -> dict:
    out = Path(ctx.out)
    fps = ctx.fps if isinstance(ctx.fps, Fraction) else parse_fps(ctx.fps)
    if not getattr(ctx, "script", None) or not Path(ctx.script).exists():
        sys.exit(f"windows: script-marked.md was not found: {getattr(ctx, 'script', None)}")
    if not (out / "words.json").exists():
        sys.exit(f"windows: {out / 'words.json'} is missing; run the words stage first.")
    if not getattr(ctx, "wav", None) or not Path(ctx.wav).exists():
        sys.exit(f"windows: the WAV was not found: {getattr(ctx, 'wav', None)}")
    words = read_json(out / "words.json")
    wav_duration = probe_duration(Path(ctx.wav))
    blocks = parse_script(ctx.script)
    if not any(b["kind"] == "board" for b in blocks):
        sys.exit(f"windows: no [▸ SLIDE <n> · <title>] markers were found in {ctx.script}.")
    seen: set[int] = set()
    dupes: list[str] = []
    for b in blocks:
        if b["kind"] == "board":
            if b["n"] in seen:
                dupes.append(f"board {b['n']} has two markers in the script; both windows are kept in script order and "
                             "share the same board file. Renumber one of them if they are different boards.")
            seen.add(b["n"])
    items, warnings = compute(blocks, words, wav_duration, fps)
    warnings = dupes + warnings

    files = find_boards(getattr(ctx, "boards", None))
    for it in items:
        if it["kind"] == "board":
            it["file"] = files.get(it["n"])
            if it["file"] is None and files:
                warnings.append(f"board {it['n']}: no file NN-Name.html for it in the boards folder.")
    unused = sorted(set(files) - {it["n"] for it in items if it["kind"] == "board"})
    if unused:
        warnings.append("board files with no marker in the script (not used): " + ", ".join(files[n] for n in unused))

    src = getattr(ctx, "timing_source", None)
    if src not in ("words.tsv", "faster-whisper"):
        src = "words.tsv" if getattr(ctx, "words", None) and Path(ctx.words).exists() else "faster-whisper"
    data = {"fps": f"{fps.numerator}/{fps.denominator}", "wav_duration": round(wav_duration, 4), "timing_source": src,
            "items": items, "warnings": warnings}
    write_json(out / "windows.json", data)

    boards = [it for it in items if it["kind"] == "board"]
    cams = [it for it in items if it["kind"] == "camera"]
    log(f"windows: {len(boards)} boards, {len(cams)} camera stretches, WAV {wav_duration:.2f} s, timing from {src}.")
    log(boundary_table(items))
    for w in warnings:
        log(f"  ! {w}")
    log(f"windows: wrote {out / 'windows.json'}")
    return data


if __name__ == "__main__":
    import argparse
    import types
    ap = argparse.ArgumentParser(description="board-sync windows stage on its own")
    ap.add_argument("--script", required=True)
    ap.add_argument("--wav", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--boards")
    ap.add_argument("--words")
    ap.add_argument("--fps", default="24000/1001")
    a = ap.parse_args()
    run(types.SimpleNamespace(script=Path(a.script), wav=Path(a.wav), out=Path(a.out), boards=a.boards and Path(a.boards),
                              words=a.words and Path(a.words), fps=parse_fps(a.fps)))
