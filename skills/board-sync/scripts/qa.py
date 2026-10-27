"""qa.py: check the REAL rendered clips against the word list -> qa-report.md, sync-manifest.md, sheets/NN.jpg.

Public:
    run(ctx)   check every board in windows.json (ctx.only re-checks just those; the others come from qa/NN.json)

Per board (all times board-local seconds unless marked "abs"):
- Landing, from frames of boards/NN-Name.mp4: for each cue with a bbox (the cue's own, else units/NN.json's), the
  frame just before its word (min(t, anchor) - 0.1 s), the frame at t + 0.5 s and a reference frame (the first frame,
  or just after the last earlier cue whose box overlaps this one has settled, so a row inside its container is
  compared with the container already there). Score = mean over the box of the per-pixel max channel difference,
  with differences under NOISE zeroed (H.264 noise). Nothing new in the box by t + 0.5 -> "did not land"; more than
  half of the final change already there before the word -> "lands early" (a second pass finds when it appeared).
- Late: the cue's anchor time (from "anchor_t"/"word_t" or "@x.xx" in "why") more than 2 s before t -> "lands late".
- Dead stretches: consecutive landings more than 3 s apart while the presenter talks for more than 3 s (windows.json words);
  cues that did not land in the real clip do not count as landings.
- Stamps with the three spoken words around them; a stamp after "of"/"out" or before a count word -> finding.
- Uncovered speech > 15 s -> "propose a new board: <words>". Copy flags from the cues. "anchor not found" cues.
- Camera zone: frames every 2 s, pixels in the bottom-right zone that differ from the board background (the median
  of the frame's top-left 20x20 px) -> finding, with the units whose bbox overlaps the zone as the likely culprits.
- Contact sheet: 4x4 tiles (480x270) at the landing frames (t + 0.5), filled with evenly spaced frames if the board
  has fewer than 16 cues, time stamped in the top-left corner.
"""
from __future__ import annotations

import re
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np

try:
    from . import common as C
    from . import render as R
except ImportError:  # pragma: no cover
    import common as C
    import render as R

HALF = 2                      # frames are decoded at 960x540; boxes are halved to match
FW, FH = R.W // HALF, R.H // HALF
NOISE = 12                    # per-pixel max channel difference below this is codec noise (0-255); measured on
                              # static frames across keyframes at crf 18, half size: 99.99th percentile 8
THR = 1.0                     # mean gated difference over a box that counts as "something is there / changed"
SOFT_THR = 1.0                # mean UNgated difference over a box that counts as landed (faint, ghosted elements)
EARLY_SHARE = 0.5             # share of the final change already present before the word -> lands early
SETTLE = 0.6                  # seconds after a cue before its element counts as settled (reference frames)
LATE_AFTER = 2.0
EARLY_SCAN = 6.0              # seconds before the word searched for when an early element appeared
DEAD_AFTER = 3.0
UNCOVERED_AFTER = 15.0
CAM_SAMPLE_EVERY = 2.0
CAM_PX_DIFF = 40              # a zone pixel this far from the background colour is content
CAM_SHARE = 0.005             # share of zone pixels that must be content for a finding
EMPHASIS_PX = 40              # pixels (at 960x540) that must change at the peak of a stamp/highlight pop
EMPHASIS = {"stamp": 0.18, "highlight": 0.12}   # kit.js: pops on an element already on screen; seconds to the peak
STATIC_MOVES = {"label", "hide"}  # on screen from the first frame / never shown: no landing to check
COUNT_PREV = {"of", "out"}
COUNT_NEXT = {"different", "sellers", "prices", "versions", "seconds", "minutes", "lines", "apps", "clips"}

FIX = {
    "early": "Timing fix in board-sync: it must land on its word, never before. Check this element's anchor in "
             "brief.md is the words the presenter says at that moment, then re-run board-sync for this board (--only {n}). "
             "If it is still early, check it by hand.",
    "late": "Timing fix in board-sync: it lands more than ~2 s after its word. Check its anchor in brief.md, then "
            "re-run board-sync for this board (--only {n}).",
    "noland": "Timing fix in board-sync: the element never shows up in the render. Re-run board-sync for this board "
              "(--only {n}); if it is still missing, check it by hand.",
    "anchor": "The anchor for this element in brief.md is not something the presenter says. Copy the presenter's exact words for it from "
              "the transcript into brief.md, then re-run board-sync for this board (--only {n}).",
    "dead": "Board-sync adds a filler (the presenter's exact words): add a filler to this board in brief.md, anchored on the "
            "words above, then re-run board-sync for this board (--only {n}).",
    "uncovered": "Add a board: back to step 3/4 for that board only (the words above are its lines), then re-run.",
    "count": "A price sticker on a count: fix the number's role in brief.md (count, not money), then re-run.",
    "copy": "Board copy that contradicts what the presenter says: fix the board in Claude Design (never the presenter's words), "
            "re-download that board, re-run.",
    "camera": "Something is in the camera zone (bottom-right 615x430 px): fix the board in Claude Design, "
              "re-download that board, re-run.",
    "missing": "Re-run board-sync's render for this board (--only {n}); if it fails again, render-log.json says why.",
    "match": "Only {pct}% of this board's script words were found in the audio, so its window may be wrong. Check "
             "that its [▸ SLIDE {n}] block in script-marked.md is what the presenter says in the final cut, then re-run.",
}


# ───────────────────────────── inputs ─────────────────────────────

def _units_map(out: Path, item: dict) -> dict:
    p = out / "units" / f"{R.nn(item)}.json"
    if not p.exists():
        return {}
    data = C.read_json(p)
    units = data.get("units", []) if isinstance(data, dict) else data
    return {str(u.get("id")): u for u in units if isinstance(u, dict) and u.get("id") is not None}


def _brief_board(out: Path, n: int) -> dict:
    p = out / "brief.json"
    if not p.exists():
        return {}
    data = C.read_json(p)
    boards = data.get("boards", data) if isinstance(data, dict) else data
    if isinstance(boards, dict):
        return boards.get(str(n)) or boards.get(n) or {}
    for b in boards if isinstance(boards, list) else []:
        if isinstance(b, dict) and int(b.get("n", -1)) == n:
            return b
    return {}


def _is_silent_board(brief: dict) -> bool:
    blob = " ".join(str(brief.get(k, "")) for k in ("type", "tag", "flags", "title")).lower()
    return "silent" in blob and "black" in blob


def _bbox(cue: dict, units: dict) -> dict | None:
    """The box to watch: the unit's ink box (its glyphs) when units.json has one, else the cue's or unit's bbox. A
    one-glyph row inside a 1000 px wide box would otherwise average away to nothing."""
    u = units.get(str(cue.get("id"))) or {}
    b = cue.get("bbox") or u.get("bbox")
    ink = u.get("ink") if cue.get("move") != "note" else None
    try:
        if isinstance(ink, dict) and b:
            ix, iy, iw, ih = (float(ink[k]) for k in ("x", "y", "w", "h"))
            bx, by, bw, bh = (float(b[k]) for k in ("x", "y", "w", "h"))
            inter = max(0.0, min(ix + iw, bx + bw) - max(ix, bx)) * max(0.0, min(iy + ih, by + bh) - max(iy, by))
            if iw * ih >= 64 and inter >= 0.8 * iw * ih and iw * ih <= 1.2 * bw * bh:   # a real ink box, inside
                b = ink
    except (KeyError, TypeError, ValueError):
        pass
    if not b:
        return None
    try:
        return {k: float(b[k]) for k in ("x", "y", "w", "h")}
    except (KeyError, TypeError, ValueError):
        return None


def _note_box(cue: dict) -> dict | None:
    """Generous box of a note without a bbox (x/y may be its corner or its centre): used only to pick references."""
    if cue.get("x") is None or cue.get("y") is None:
        return None
    size = float(cue.get("size") or 64)
    w = 0.6 * size * max(1, len(str(cue.get("text", ""))))
    h = 1.4 * size
    x, y = float(cue["x"]), float(cue["y"])
    return {"x": x - w / 2, "y": y - h, "w": w * 1.5, "h": h * 2}


def _overlap(a: dict, b: dict) -> bool:
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def _anchor_t(cue: dict, dur: float, start: float) -> float | None:
    w = cue.get("word")
    if isinstance(w, dict) and isinstance(w.get("t"), (int, float)):      # choreo's {"w", "t"}, board-local
        v = float(w["t"])
        return v - start if v > dur + 0.5 else v
    for k in ("anchor_t", "word_t"):
        if isinstance(cue.get(k), (int, float)):
            v = float(cue[k])
            return v - start if v > dur + 0.5 else v
    m = re.search(r"@\s*(-?\d+(?:\.\d+)?)", str(cue.get("why", "")))
    if not m:
        return None
    v = float(m.group(1))
    return v - start if v > dur + 0.5 else v          # an absolute time slipped in: make it board-local


def _anchor_words(cue: dict) -> str:
    if cue.get("anchor"):
        return str(cue["anchor"])
    why = str(cue.get("why", ""))
    m = re.search(r"'([^']+)'", why) or re.search(r'"([^"]+)"', why)
    if m:
        return m.group(1)
    if isinstance(cue.get("word"), dict) and cue["word"].get("w"):
        return str(cue["word"]["w"])
    return "(structure)" if why.startswith("structure") else (why or "-")


def _element(cue: dict, units: dict) -> str:
    u = units.get(str(cue.get("id"))) or {}
    txt = cue.get("text") or u.get("text") or ""
    txt = " ".join(str(txt).split())
    if not txt:
        txt = f"({u.get('kind') or cue.get('move') or 'element'})"
    return txt if len(txt) <= 60 else txt[:57] + "..."


def _words(item: dict) -> list[dict]:
    ws = [w for w in item.get("words", []) if isinstance(w, dict) and "t" in w]
    return sorted(ws, key=lambda w: float(w["t"]))


def _word_at(words: list[dict], t_abs: float) -> int | None:
    """Index of the word being spoken at t_abs (else the last one that started before it)."""
    best = None
    for i, w in enumerate(words):
        if float(w["t"]) <= t_abs + 0.02:
            best = i
        else:
            break
    return best


def _say(words: list[dict]) -> str:
    return " ".join(str(w.get("w", "")) for w in words).strip()


# ───────────────────────────── frames ─────────────────────────────

def iter_frames(clip: Path, indices):
    """Yield (index, 960x540 RGB frame) for the given frame indices of a clip, decoded in one pass (select by frame
    number). Streams: nothing is kept, so long ranges cost no memory."""
    idx = sorted({int(i) for i in indices if i is not None and i >= 0})
    if not idx:
        return
    terms, a = [], idx[0]                                  # runs of consecutive indices become between(n,a,b)
    for prev, cur in zip(idx, idx[1:] + [None]):
        if cur != prev + 1:
            terms.append(f"eq(n,{a})" if a == prev else f"between(n,{a},{prev})")
            a = cur
    while len(terms) > 1:      # a balanced sum: ffmpeg's expression parser refuses more than 100 nested terms
        terms = [f"({terms[k]}+{terms[k + 1]})" if k + 1 < len(terms) else terms[k] for k in range(0, len(terms), 2)]
    cmd = [C.which_ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", str(clip),
           "-vf", f"select='{terms[0]}',scale={FW}:{FH}:flags=area,format=rgb24",
           "-fps_mode", "passthrough", "-f", "rawvideo", "-"]
    size = FW * FH * 3
    got = 0
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in idx:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            got += 1
            yield i, np.frombuffer(buf, np.uint8).reshape(FH, FW, 3)
    finally:
        proc.stdout.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        proc.wait()
        if got < len(idx):
            C.log(f"qa: {clip.name}: decoded {got} of {len(idx)} frames {err.strip()[:200]}")


def grab_frames(clip: Path, indices) -> dict[int, np.ndarray]:
    """The given frame indices of a clip, at 960x540 RGB, as {index: frame}."""
    return dict(iter_frames(clip, indices))


def appeared_at(curve: list[tuple[int, float]], cmax: float) -> int | None:
    """curve = [(frame, share of the element's ink not yet in place)] in frame order, ending at a frame where it has
    landed. Walking back from the end: skip the settled part (near 0), then follow the distance up while it keeps
    rising; where it stops rising is the state just before the element appeared, so the frame after it is the first
    frame it shows. None when it is still rising at the start of the curve (it was there before the scan began)."""
    if cmax <= 0.02 or len(curve) < 2:
        return None
    tol = max(0.02 * cmax, 0.004)
    k = len(curve) - 1
    while k > 0 and curve[k][1] < 0.1 * cmax:                  # settled (already landed)
        k -= 1
    while k > 0 and curve[k - 1][1] > curve[k][1] + tol:       # still rising, going back in time
        k -= 1
    if k == 0:
        return None
    plateau = max(curve[k - 1][1], curve[k][1])
    j = k                                                      # first frame clearly below the plateau
    while j < len(curve) - 1 and curve[j][1] >= plateau - tol:
        j += 1
    return curve[j][0]


def _box_px(b: dict) -> tuple[int, int, int, int] | None:
    x0 = max(0, int(b["x"] // HALF))
    y0 = max(0, int(b["y"] // HALF))
    x1 = min(FW, int(-(-(b["x"] + b["w"]) // HALF)))
    y1 = min(FH, int(-(-(b["y"] + b["h"]) // HALF)))
    return (x0, y0, x1, y1) if x1 - x0 >= 2 and y1 - y0 >= 2 else None


def _diff(a: np.ndarray, b, box) -> np.ndarray:
    """Per-pixel max channel difference inside a box (b may be a frame or a background colour)."""
    x0, y0, x1, y1 = box
    bb = b[y0:y1, x0:x1] if isinstance(b, np.ndarray) and b.ndim == 3 else b
    return np.abs(a[y0:y1, x0:x1].astype(np.int16) - np.asarray(bb, dtype=np.int16)).max(axis=2)


def _bg(frame: np.ndarray) -> np.ndarray:
    """The board's background colour: the median of the frame's top-left 20x20 px."""
    return np.median(frame[:20 // HALF, :20 // HALF].reshape(-1, 3), axis=0).astype(np.int16)


def score(a: np.ndarray, b: np.ndarray, box) -> float:
    x0, y0, x1, y1 = box
    d = np.abs(a[y0:y1, x0:x1].astype(np.int16) - b[y0:y1, x0:x1].astype(np.int16)).max(axis=2)
    d[d < NOISE] = 0
    return float(d.mean())


# ───────────────────────────── one board ─────────────────────────────

def check_board(out: Path, item: dict, fps: Fraction, windows: dict) -> dict:
    n = int(item["n"])
    tag = R.nn(item)
    start, end = float(item["start"]), float(item["end"])
    dur = end - start
    s_frame, n_frames = R.slot(start, end, fps)
    words = _words(item)
    units = _units_map(out, item)
    brief = _brief_board(out, n)
    cue_file = out / "cues" / f"{tag}.cues.json"
    cdata = C.read_json(cue_file) if cue_file.exists() else {}
    cues = sorted([c for c in cdata.get("cues", []) if isinstance(c, dict) and isinstance(c.get("t"), (int, float))],
                  key=lambda c: float(c["t"]))
    clip = R.clip_path(out, item)
    res = {"n": n, "name": R.board_name(item), "title": item.get("title", ""), "start": start, "end": end,
           "matched": item.get("matched"), "findings": [], "stamps": [], "rows": [], "sheet": None,
           "clip": clip.name, "clip_mtime": clip.stat().st_mtime if clip.exists() else None}
    F = res["findings"]

    def add(kind, text, fix_key, t=None, **fmt):
        F.append({"kind": kind, "t": t, "text": text, "fix": FIX[fix_key].format(n=n, **fmt)})

    if cue_file.exists() and clip.exists() and cue_file.stat().st_mtime > clip.stat().st_mtime + 1:
        add("stale render", f"cues/{tag}.cues.json is newer than boards/{clip.name}: the clip does not show the "
            "latest timing.", "missing")
    if not cue_file.exists():
        add("no cues", f"cues/{tag}.cues.json is missing (the choreo stage did not run for this board).", "missing")
    m = item.get("matched")
    if isinstance(m, (int, float)) and m < 0.4 and item.get("script_lines"):     # a hold board has no lines
        add("low match", f"Only {round(m * 100)}% of the script words for this board were found in the audio.",
            "match", pct=round(m * 100))

    # ── frame plan ──
    rows = []
    for c in cues:
        t = float(c["t"])
        a_t = _anchor_t(c, dur, start)
        box = _bbox(c, units)
        status = ("visible from the start" if c.get("move") == "label" else "hidden" if c.get("move") == "hide"
                  else "not checked (no box)" if not box else "")
        rows.append({"cue": c, "t": t, "anchor_t": a_t, "box": box, "status": status, "abs": start + t})
    have_clip = clip.exists()
    n_clip = R.count_frames(clip) if have_clip else 0
    fi = (lambda t: R.frame_index(t, s_frame, start, n_clip, fps))
    want: set[int] = {0}
    for r in rows:
        if not r["box"] or r["cue"].get("move") in STATIC_MOVES:
            continue
        tb = max(0.0, min(r["t"], r["anchor_t"] if r["anchor_t"] is not None else r["t"]) - 0.1)
        ref_t = 0.0
        for p in rows:                                     # last earlier cue overlapping this box, settled
            pb = p["box"] or _note_box(p["cue"])
            if p is r or not pb or p["t"] >= tb or not _overlap(pb, r["box"]):
                continue
            ref_t = max(ref_t, min(p["t"] + SETTLE, tb))
        r.update(tb=tb, ta=min(r["t"] + 0.5, dur), ref_t=ref_t)
        if r["cue"].get("move") in EMPHASIS:                 # a pop on something already there: check its peak
            r["ta"] = min(r["t"] + EMPHASIS[r["cue"]["move"]], dur)
        want |= {fi(tb), fi(r["ta"]), fi(ref_t)}
    cam_ts = [k * CAM_SAMPLE_EVERY for k in range(int(dur // CAM_SAMPLE_EVERY) + 1)] + [max(0.0, dur - 0.05)]
    sheet_ts = _sheet_times(rows, dur)
    if have_clip:
        want |= {fi(t) for t in cam_ts} | {fi(t) for t, _ in sheet_ts}
        frames = grab_frames(clip, want)
    else:
        frames = {}
        why = ""
        log_p = out / "render-log.json"
        if log_p.exists():
            fail = [f for f in C.read_json(log_p).get("failed", []) if int(f.get("n", -1)) == n]
            why = f" The render said: {fail[0]['error']}" if fail else ""
        add("not rendered", f"boards/{clip.name} does not exist.{why}", "missing")

    # ── landings ──
    # New ink = pixels inside the box that are not background in the landed frame A and differ from the reference R
    # (taken after anything overlapping that landed earlier has settled). Early = most of that ink already in place in
    # B, the frame just before the word. Ink that disappears (a note fading out) is never counted as a landing.
    first = frames.get(0)
    bg = _bg(first) if first is not None else None
    early_rows = []
    for r in rows:
        c = r["cue"]
        label = f"{c.get('id')} \"{_element(c, units)}\""
        if r["anchor_t"] is not None and r["t"] - r["anchor_t"] > LATE_AFTER:
            add("lands late", f"{label} lands at {r['t']:.2f} s, {r['t'] - r['anchor_t']:.1f} s after its word "
                f"'{_anchor_words(c)}' ({r['anchor_t']:.2f} s).", "late", t=r["t"])
        if "not found" in str(c.get("why", "")).lower():
            add("anchor not found", f"{label}: its anchor was not found in what the presenter says ({c.get('why')}); it was "
                f"placed after the previous element at {r['t']:.2f} s.", "anchor", t=r["t"])
        if "tb" not in r or not frames or bg is None:
            continue
        box = _box_px(r["box"])
        fr = [frames.get(fi(x)) for x in (r["ref_t"], r["tb"], r["ta"])]
        if box is None or any(f is None for f in fr):
            r["status"] = "not checked"
            continue
        ref, before, after = fr
        if r["t"] >= dur - 0.05:
            r["status"] = "did not land"
            add("did not land", f"{label} is timed at {r['t']:.2f} s, after the board ends ({dur:.2f} s).", "noland",
                t=r["t"])
            continue
        if c.get("move") in EMPHASIS:            # the pop scales a part of the box (a "$500K" inside its card)
            moved = int((_diff(after, before, box) >= NOISE).sum())
            r["scores"] = (moved,)
            r["status"] = "ok" if moved >= EMPHASIS_PX else "did not land"
            if moved < EMPHASIS_PX:
                add("did not land", f"{label}: its {c.get('move')} at {r['t']:.2f} s does not show in the render.",
                    "noland", t=r["t"])
            continue
        d_ar = _diff(after, ref, box)
        new_ink = (d_ar >= NOISE) & (_diff(after, bg, box) >= NOISE)
        landed = float((d_ar * new_ink).mean())
        soft = float(d_ar.mean())        # ungated: a faint card whose every pixel moves less than NOISE still counts
        share = float((_diff(after, before, box)[new_ink] < NOISE).mean()) if new_ink.any() else 0.0
        r["scores"] = (round(landed, 2), round(share, 2), round(soft, 2))
        if landed < THR and soft < SOFT_THR:
            r["status"] = "did not land"
            text = f"{label}: nothing new appears in its box by {r['ta']:.2f} s (cue {r['t']:.2f} s)."
            if soft >= 0.1:
                text += (" Only a faint change shows (a fill close to the background colour); its outline or "
                         "content arrives later, so this part of the board opens empty.")
            pre_new = float(((_diff(before, first, box) >= NOISE) & (_diff(before, bg, box) >= NOISE)).mean())
            if float((_diff(first, bg, box) >= NOISE).mean()) > 0.02 and pre_new <= 0.02:
                text += " Its box has content from the first frame: it may be on screen from the start."
            add("did not land", text, "noland", t=r["t"])
            if pre_new > 0.02:          # something new arrived in its box before the word: find when (second pass)
                r["finding"] = F[-1]
                early_rows.append((r, label, box, before))
        elif share >= EARLY_SHARE:
            r["status"] = "lands early"
            early_rows.append((r, label, box, before))
        else:
            r["status"] = "ok"
    if early_rows and have_clip:                             # second pass: when did it really appear?
        win = {id(r): (fi(max(0.0, r["tb"] - EARLY_SCAN)), fi(r["tb"])) for r, *_ in early_rows}
        starts = grab_frames(clip, {a for a, _ in win.values()})
        inks = {}
        for r, _, box, before in early_rows:                # its ink: present before the word, absent at scan start
            f0 = starts.get(win[id(r)][0])
            inks[id(r)] = ((_diff(before, f0, box) >= NOISE) & (_diff(before, bg, box) >= NOISE)) if f0 is not None else None
        curves: dict[int, list] = {id(r): [] for r, *_ in early_rows}
        for i, f in iter_frames(clip, {i for a, b in win.values() for i in range(a, b + 1)}):
            for r, _, box, before in early_rows:
                a, b = win[id(r)]
                q = inks[id(r)]
                if a <= i <= b and q is not None and q.any():
                    curves[id(r)].append((i, 1.0 - float((_diff(f, before, box)[q] < NOISE).mean())))
        for r, label, box, before in early_rows:
            cv = curves[id(r)]
            seen = appeared_at(cv, max((v for _, v in cv), default=0.0))
            word_t = r["anchor_t"] if r["anchor_t"] is not None else r["t"]
            words_q = f"its word '{_anchor_words(r['cue'])}' at {word_t:.2f} s (cue {r['t']:.2f} s)"
            if "finding" in r:          # did not land, but its box changed before the word: say when, claim nothing
                if seen is not None and R.frame_time(seen, s_frame, start, fps) < word_t - 0.05:
                    t_seen = R.frame_time(seen, s_frame, start, fps)
                    r["finding"]["text"] += (f" Its box changes at {t_seen:.2f} s (abs {start + t_seen:.2f}), before "
                                             f"{words_q}: it may have landed early.")
                continue
            if seen is not None:
                t_seen = R.frame_time(seen, s_frame, start, fps)
                if t_seen >= word_t - 0.05:                  # it did start on its word after all
                    r["status"] = "ok"
                    continue
                r["seen"] = t_seen
                txt = (f"{label} starts appearing at {t_seen:.2f} s (abs {start + t_seen:.2f}), "
                       f"{word_t - t_seen:.2f} s before {words_q}.")
            else:
                t0 = R.frame_time(win[id(r)][0], s_frame, start, fps)
                r["seen"] = t0
                txt = f"{label} is already on screen at {t0:.2f} s (abs {start + t0:.2f}), before {words_q}."
            add("lands early", txt, "early", t=r["t"])

    # ── dead stretches (landings that really happened) ──
    lands = sorted({0.0, dur} | {r["t"] for r in rows if r["cue"].get("move") not in STATIC_MOVES
                                 and r["status"] != "did not land" and 0 <= r["t"] <= dur})
    for a, b in zip(lands, lands[1:]):
        if b - a <= DEAD_AFTER:
            continue
        inside = [w for w in words if start + a <= float(w["t"]) < start + b]
        if not inside:
            continue
        talk = min(start + b, float(inside[-1].get("e", inside[-1]["t"]))) - max(start + a, float(inside[0]["t"]))
        if talk > DEAD_AFTER:
            add("dead stretch", f"{a:.2f}-{b:.2f} s (abs {start + a:.2f}-{start + b:.2f}): {b - a:.1f} s with nothing "
                f"new while the presenter says \"{_say(inside)}\".", "dead", t=a)

    # ── stamps ──
    for r in rows:
        c = r["cue"]
        if c.get("move") != "stamp":
            continue
        i = _word_at(words, start + r["anchor_t"] if r["anchor_t"] is not None else r["abs"])
        around = words[max(0, (i or 0) - 1):(i or 0) + 2] if i is not None else []
        res["stamps"].append({"id": c.get("id"), "element": _element(c, units), "t": r["t"], "abs": r["abs"],
                              "words": _say(around)})
        if i is not None:
            prev_w = C.norm(str(words[i - 1]["w"])) if i > 0 else ""
            next_w = C.norm(str(words[i + 1]["w"])) if i + 1 < len(words) else ""
            if prev_w in COUNT_PREV or next_w in COUNT_NEXT:
                add("stamp on a count", f"{c.get('id')} \"{_element(c, units)}\" stamps at {r['t']:.2f} s on "
                    f"\"{_say(around)}\", which reads as a count, not money.", "count", t=r["t"])

    # ── uncovered speech, copy flags ──
    for u in item.get("uncovered", []) or []:
        if float(u.get("end", 0)) - float(u.get("start", 0)) > UNCOVERED_AFTER:
            text = u.get("text") or _say([w for w in words if float(u["start"]) <= float(w["t"]) < float(u["end"])])
            add("uncovered", f"{float(u['start']):.2f}-{float(u['end']):.2f} s (abs): {float(u['end']) - float(u['start']):.0f} s "
                f"of speech with no script line. Propose a new board: \"{text}\".", "uncovered")
    for fl in cdata.get("flags", []) or []:
        add("copy", f"{fl}", "copy")

    # ── camera zone ──
    if frames and not _is_silent_board(brief):
        z = C.CAM_ZONE_1080
        zx0, zy0 = z["x"] // HALF, z["y"] // HALF
        zx1, zy1 = (z["x"] + z["w"]) // HALF, (z["y"] + z["h"]) // HALF
        hits = []
        for t in cam_ts:
            f = frames.get(fi(t))
            if f is None:
                continue
            bg = np.median(f[:20 // HALF, :20 // HALF].reshape(-1, 3), axis=0)
            zone = f[zy0:zy1, zx0:zx1].astype(np.int16)
            share = float((np.abs(zone - bg.astype(np.int16)).max(axis=2) > CAM_PX_DIFF).mean())
            if share > CAM_SHARE:
                hits.append((t, share))
        if hits:
            culprits = [f"{uid} \"{_element({'id': uid}, units)}\"" for uid, u in units.items()
                        if u.get("bbox") and _overlap({k: float(u["bbox"][k]) for k in "xywh"}, z)]
            add("camera zone", f"content in the camera zone from {hits[0][0]:.1f} s (up to {max(h[1] for h in hits) * 100:.1f}% "
                f"of the zone)" + (f"; overlapping: {', '.join(culprits)}" if culprits else "") + ".", "camera",
                t=hits[0][0])

    # ── contact sheet ──
    if frames:
        res["sheet"] = _contact_sheet(out, tag, [(t, lab, frames.get(fi(t))) for t, lab in sheet_ts], start)

    res["rows"] = [{"id": r["cue"].get("id"), "element": _element(r["cue"], units), "move": r["cue"].get("move", ""),
                    "anchor": _anchor_words(r["cue"]), "t": round(r["t"], 3), "abs": round(r["abs"], 3),
                    "heard": _say(words[i:i + 1]) if (i := _word_at(words, r["abs"])) is not None else "",
                    "status": r["status"] or "ok", "scores": r.get("scores"), "seen": r.get("seen")} for r in rows]
    res["timing_source"] = windows.get("timing_source", "words.tsv")
    F.sort(key=lambda f: (f["t"] is None, f["t"] or 0))
    return res


def _sheet_times(rows: list[dict], dur: float) -> list[tuple[float, str]]:
    """16 (time, label) pairs: the landing frames (t + 0.5), thinned to 16, or filled with the frames farthest from
    the ones already picked (evenly spread) when the board has fewer than 16 cues."""
    last = max(0.0, dur - 0.05)
    picks = [(min(r["t"] + 0.5, last), f"{r['cue'].get('id', '')} cue {r['t']:.2f}") for r in rows if 0 <= r["t"] <= dur]
    if len(picks) > 16:
        picks = [picks[round(k * (len(picks) - 1) / 15)] for k in range(16)]
    cands = [last * j / 63 for j in range(64)]
    while len(picks) < 16 and cands:
        best = max(cands, key=lambda t: min((abs(t - p[0]) for p in picks), default=t))
        picks.append((best, ""))
        cands.remove(best)
    return sorted(picks)[:16]


def _contact_sheet(out: Path, tag: str, tiles, start: float) -> str | None:
    from PIL import Image, ImageDraw, ImageFont
    tw, th = 480, 270
    sheet = Image.new("RGB", (tw * 4, th * 4), (20, 20, 20))
    try:
        font = ImageFont.load_default(size=18)
    except TypeError:                                    # Pillow < 10.1
        font = ImageFont.load_default()
    for k, (t, lab, f) in enumerate(tiles[:16]):
        if f is None:
            continue
        im = Image.fromarray(f).resize((tw, th), Image.BILINEAR)
        d = ImageDraw.Draw(im)
        text = f"{t:5.2f}s  abs {start + t:.2f}" + (f"  {lab}" if lab else "")
        x0, y0, x1, y1 = d.textbbox((8, 6), text, font=font)
        d.rectangle((x0 - 5, y0 - 4, x1 + 5, y1 + 4), fill=(0, 0, 0))
        d.text((8, 6), text, fill=(255, 255, 255), font=font)
        sheet.paste(im, ((k % 4) * tw, (k // 4) * th))
    p = out / "sheets" / f"{tag}.jpg"
    p.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(p, "JPEG", quality=85)
    return f"sheets/{tag}.jpg"


# ───────────────────────────── report ─────────────────────────────

def _timing_line(windows: dict) -> str:
    src = str(windows.get("timing_source", "words.tsv"))
    if "whisper" in src.lower():
        return ("Timing: **timing from board-sync's own transcription** (faster-whisper), because no words.tsv was "
                "given. Word times can be off by a little; watch preview.mp4 closely.")
    return "Timing: words.tsv (your editor word timings)."


def _track_line(out: Path, windows: dict, fps: Fraction, ctx) -> str:
    p = out / "board-track.mp4"
    wav = getattr(ctx, "wav", None)
    wav_dur = C.probe_duration(Path(wav)) if wav and Path(wav).exists() else float(windows.get("wav_duration", 0))
    want = C.frames_for(wav_dur, fps)
    if not p.exists():
        return f"Track: board-track.mp4 not built yet (expected {want} frames)."
    got = R.count_frames(p)
    ok = "matches" if got == want else "DOES NOT MATCH"
    return f"Track: board-track.mp4 has {got} frames; round({wav_dur:.3f} s x {R.fps_str(fps)}) = {want}: {ok}."


def _verdict(r: dict) -> str:
    if not r["findings"]:
        return "clean"
    kinds: dict[str, int] = {}
    for f in r["findings"]:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    n = len(r["findings"])
    return f"{n} finding{'s' if n != 1 else ''} (" + ", ".join(f"{k} x{v}" for k, v in kinds.items()) + ")"


def _write_report(out: Path, results: list[dict], windows: dict, fps: Fraction, ctx) -> Path:
    clean = sum(1 for r in results if not r["findings"])
    L = ["# board-sync QA report", "",
         _timing_line(windows), _track_line(out, windows, fps, ctx),
         f"Boards: {len(results)}, clean {clean}, with findings {len(results) - clean}.", "",
         "Fix every finding and re-run until this report is clean, then watch preview.mp4 from start to end.", "",
         "## Verdicts", ""]
    for r in results:
        L.append(f"- {r['n']:02d} {r['title'] or r['name']}: {_verdict(r)}")
    for r in results:
        m = r.get("matched")
        mt = f", matched {round(m * 100)}% of its script words" if isinstance(m, (int, float)) else ""
        L += ["", f"## {r['n']:02d} · {r['title'] or r['name']}", "",
              f"Window {r['start']:.2f}-{r['end']:.2f} s ({r['end'] - r['start']:.2f} s){mt}. Clip: boards/{r['clip']}. "
              f"Timing source: {r.get('timing_source', 'words.tsv')}.", ""]
        if r.get("sheet"):
            L += [f"![contact sheet {r['n']:02d}]({r['sheet']})", ""]
        if r["findings"]:
            for k, f in enumerate(r["findings"], 1):
                L.append(f"{k}. **{f['kind']}**: {f['text']}  ")
                L.append(f"   Fix: {f['fix']}")
        else:
            L.append("Clean.")
        if r["stamps"]:
            L += ["", "Stamps (check each is money, not a count):"]
            for s in r["stamps"]:
                L.append(f"- {s['id']} \"{s['element']}\" at {s['t']:.2f} s (abs {s['abs']:.2f}): \"{s['words']}\"")
    p = out / "qa-report.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


QA_START, QA_END = "<!-- qa:start -->", "<!-- qa:end -->"


def _write_manifest(out: Path, results: list[dict], windows: dict) -> Path:
    """sync-manifest.md: the QA section between its markers (every cue of every board: element, anchor words, landing
    time board-local and on the final timeline, and what the real render shows). The choreo and timeline sections,
    and anything else outside the markers, are kept as they are."""
    L = [QA_START, "## Landings checked on the real render (board-sync qa)", "",
         f"timing: {windows.get('timing_source', 'words.tsv')} · times in seconds · \"heard then\" = the word being "
         "saying when it lands", ""]
    for r in results:
        L += [f"### {r['n']:02d} · {r['title'] or r['name']}", "",
              f"Window {r['start']:.2f}-{r['end']:.2f} s on the final timeline; clip boards/{r['clip']}.", "",
              "| cue | element | move | anchor (the presenter's words) | lands (board) | lands (timeline) | heard then | QA |",
              "|---|---|---|---|---|---|---|---|"]
        for row in r["rows"]:
            el = row["element"].replace("|", "\\|")
            an = row["anchor"].replace("|", "\\|")
            qa = row["status"] + (f" (seen {row['seen']:.2f})" if row.get("seen") is not None else "")
            L.append(f"| {row['id']} | {el} | {row['move']} | {an} | {row['t']:.2f} | {row['abs']:.2f} | "
                     f"{row['heard']} | {qa} |")
        if not r["rows"]:
            L.append("| - | (no cues) | | | | | | |")
        if r["stamps"]:
            L += ["", "Stamps: " + "; ".join(f"{s['id']} at {s['t']:.2f} on \"{s['words']}\"" for s in r["stamps"])]
        notes = [f for f in r["findings"] if f["kind"] in ("copy", "anchor not found", "uncovered")]
        if notes:
            L += ["", "Notes: " + " ".join(f["text"] for f in notes)]
        L.append("")
    L.append(QA_END)
    block = "\n".join(L)
    path = out / "sync-manifest.md"
    old = path.read_text(encoding="utf-8") if path.is_file() else "# Sync manifest\n\n"
    if QA_START in old and QA_END in old:
        a, b = old.index(QA_START), old.index(QA_END) + len(QA_END)
        new = old[:a] + block + old[b:]
    else:
        new = old.rstrip("\n") + "\n\n" + block + "\n"
    path.write_text(new, encoding="utf-8")
    return path


# ───────────────────────────── entry ─────────────────────────────

def run(ctx) -> dict:
    out = R.out_dir(ctx)
    windows = R.load_windows(ctx)
    fps = R.get_fps(ctx, windows)
    all_items = R.board_items(windows, None)
    only = R.parse_only(getattr(ctx, "only", None))
    store = out / "qa"
    results = []
    for item in all_items:
        n = int(item["n"])
        cached = store / f"{R.nn(item)}.json"
        clip = R.clip_path(out, item)
        if only is not None and n not in only and cached.exists():
            prev = C.read_json(cached)
            mt = clip.stat().st_mtime if clip.exists() else None
            if prev.get("clip_mtime") == mt and prev.get("start") == float(item["start"]):
                results.append(prev)
                continue
        C.log(f"qa: board {R.nn(item)} {R.board_name(item)}")
        try:
            r = check_board(out, item, fps, windows)
        except Exception as e:  # noqa: BLE001  one broken board never stops the report
            r = {"n": n, "name": R.board_name(item), "title": item.get("title", ""), "start": float(item["start"]),
                 "end": float(item["end"]), "matched": item.get("matched"), "stamps": [], "rows": [], "sheet": None,
                 "clip": clip.name, "clip_mtime": None,
                 "findings": [{"kind": "qa error", "t": None, "text": f"QA could not check this board: {e}",
                               "fix": "Check it by hand."}]}
        C.write_json(cached, r)
        results.append(r)
    results.sort(key=lambda r: r["n"])
    rep = _write_report(out, results, windows, fps, ctx)
    man = _write_manifest(out, results, windows)
    clean = sum(1 for r in results if not r["findings"])
    C.log(f"qa: {len(results)} board(s), {clean} clean, {len(results) - clean} with findings -> {rep.name}, {man.name}, sheets/")
    for r in results:
        C.log(f"qa:   {r['n']:02d} {r['title'] or r['name']}: {_verdict(r)}")
    return {"boards": len(results), "clean": clean, "report": str(rep), "manifest": str(man)}


if __name__ == "__main__":   # python scripts/qa.py <out> [--only 4,5]
    import argparse
    import types
    ap = argparse.ArgumentParser(description="board-sync qa stage")
    ap.add_argument("out")
    ap.add_argument("--only")
    ap.add_argument("--wav")
    a = ap.parse_args()
    run(types.SimpleNamespace(out=a.out, only=a.only, wav=a.wav, fps=None))
