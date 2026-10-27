"""units + brief + words -> cues/NN.cues.json + scenes/NN.html.

Every element of a board lands on the words that name it. The rules (see references/rules.md) are applied in
this order:
  1  structure first (containers, zones, rails, baselines cascade from 0.45 s; first content by 0.9 s; a board under
     5 s gets its structure and labels inside the first second)
  2  every build in the brief lands on its anchor words (fallbacks: the element's own text, its key number, then a
     reported cascade 0.2 s after the previous element; never hidden silently)
  3  never before the word, never more than 2 s after; a with: chain lands 0.1 s after its target
  4  named things on their name; a part never without its container; an arrow never before both of its ends
  5  money vs count: a stamp only on a money/percent number said as money/percent
  6  nothing static over 3 s while the presenter talks: the brief's fillers first, then auto notes in the presenter's exact words
  7  nothing moves after it lands (no pulses, nudges, camera moves, loops; the headline highlight pops once)
  8  reading order kept; a lower row named first still lands on its word
  9  copy that contradicts speech is flagged, never changed
  10 uncovered speech over 15 s is proposed as a new board

  build_board(n, units, brief_board, words, start, end, fps) -> cues dict
  write_scene(units_doc, cues, path)                        -> scenes/NN.html
  run(ctx)                                                  -> all boards (honours ctx.only)
"""
from __future__ import annotations

import html as H
import json
import math
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

SKILL = Path(__file__).resolve().parent.parent
W, HGT = 1920, 1080
STOP = set(common.STOP) | {"it's", "that's", "there's", "i'm", "i've", "we're", "they're", "you're", "let's", "going",
                           "gonna", "into", "onto", "from", "about", "also", "even", "still", "some", "any", "all"}
MULT = {"hundred": 100, "thousand": 1000, "k": 1000, "grand": 1000, "million": 1_000_000, "m": 1_000_000,
        "billion": 1_000_000_000, "b": 1_000_000_000}
ONES = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
        "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
        "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
MONEY_WORDS = {"dollars", "dollar", "bucks", "usd"}
PCT_WORDS = {"percent", "per-cent", "%", "pct"}
PAY_BEFORE = {"at", "pay", "pays", "paying", "paid", "costs", "cost", "costing", "charges", "charge", "charged", "price",
              "sell", "sells", "selling", "buy", "buys", "keeps", "keep", "is", "about", "around", "than", "me", "you",
              "for", "list", "lists", "spends", "spend", "spending", "makes", "earn", "earns", "worth"}
COUNT_AFTER = {"different", "sellers", "prices", "versions", "seconds", "minutes", "lines", "apps", "clips", "times",
               "out", "users", "videos", "ways", "things", "kinds", "of", "providers", "resellers", "receipts",
               "companies", "models", "people", "boards", "days", "hours", "years", "months", "weeks", "steps"}
JUNK = {"because", "whether", "before", "after", "changes", "covers", "customer", "number", "people", "mostly",
        "thinking", "moment", "everything", "starting", "keeping", "copying", "always", "switch", "buying", "without",
        "whichever", "something", "somebody", "anything", "nothing", "together", "already", "another", "through",
        "between", "against", "instead", "especially", "obviously", "actually", "basically", "essentially", "really",
        "literally", "right", "there", "these", "those", "their", "where", "which", "while", "would", "could", "should",
        "being", "doing", "having", "getting", "saying", "think", "thing", "things", "kind", "point", "pretty", "probably",
        "maybe", "today", "about", "other", "every", "never", "again", "first", "second", "third", "people's"}
KIND_WORDS = {
    "figure": ("arrow", "icon", "image"), "stick": ("arrow",), "person": ("arrow", "icon", "image"),
    "character": ("arrow", "icon", "image"), "drawing": ("arrow",), "sketch": ("arrow",), "doodle": ("arrow",),
    "outline": ("arrow", "zone", "container"), "circle": ("arrow",), "ring": ("arrow",), "underline": ("arrow",),
    "arrow": ("arrow",), "arrows": ("arrow",), "stroke": ("arrow",), "scribble": ("arrow",), "connector": ("arrow",),
    "spokes": ("arrow",), "spoke": ("arrow",), "bracket": ("arrow", "zone"), "line": ("zone", "arrow"),
    "lines": ("zone", "arrow"), "bar": ("bar",), "bars": ("bar",), "column": ("bar",), "columns": ("bar",),
    "box": ("container", "sticker", "zone", "icon"), "boxes": ("container", "sticker", "zone", "icon"),
    "card": ("sticker", "container", "label"), "cards": ("sticker", "container", "label"),
    "panel": ("container", "zone"), "frame": ("container", "zone"), "receipt": ("container",),
    "receipts": ("container",), "container": ("container",), "slot": ("container", "zone", "sticker"),
    "sticker": ("sticker",), "stickers": ("sticker",), "chip": ("sticker", "label"), "chips": ("sticker", "label"),
    "pill": ("sticker", "label"), "badge": ("sticker", "legend"), "stamp": ("sticker",), "icon": ("icon", "image"),
    "logo": ("icon", "image"), "image": ("image",), "video": ("image",), "tile": ("image", "icon", "container"),
    "tiles": ("image", "icon", "container"), "screenshot": ("image",), "tag": ("legend",), "legend": ("legend",),
    "baseline": ("zone",), "rail": ("zone",), "axis": ("zone",), "grid": ("zone", "container"),
    "hatching": ("zone", "container"), "zone": ("zone",), "note": ("note",), "handwriting": ("note",),
    "caption": ("note", "label"), "row": ("row",), "rows": ("row",), "item": ("row", "label"), "items": ("row", "label"),
    "bubble": ("container", "sticker", "label"), "stage": ("zone", "container"), "hub": ("container", "icon", "arrow"),
}
STRUCT_KINDS = ("zone", "container", "bar", "icon", "image")
REVEALS = ("rise", "wipe", "grow", "growx", "pop", "write", "draw")
CAM = common.CAM_ZONE_1080
NOTE_COLORS = {"hand": "#2563EB", "sticker": "#DBEAFE", "tag": "#CDEFC4", "mono": "#1F2937", "stamp": "#E8552B"}
NOTE_COLORS_DARK = {"hand": "#DBEAFE", "sticker": "#DBEAFE", "tag": "#CDEFC4", "mono": "#F6F7F9", "stamp": "#FF8A65"}


def _is_dark(color) -> bool:
    """True for a dark fill ("#1F2937", "rgb(17, 17, 17)"): notes then use light ink."""
    if not color or not isinstance(color, str):
        return False
    c = color.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", c)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(x * 2 for x in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    else:
        m = re.match(r"rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)(?:[ ,/]+([\d.]+))?", c)
        if not m or (m.group(4) is not None and float(m.group(4)) < 0.5):
            return False
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 < 0.4
# per style: (char width in em, extra width in em, line height in em, extra height in em), measured in Chrome on the
# deck fonts (Instrument Serif 700, Inter 700, JetBrains Mono) with a little margin; rotation is added in _note_box
NOTE_METRICS = {"hand": (0.40, 0.12, 1.05, 0.08), "sticker": (0.54, 1.0, 1.0, 0.62), "tag": (0.70, 1.6, 1.0, 0.88),
                "mono": (0.61, 0.1, 1.3, 0.03), "stamp": (0.61, 0.75, 1.0, 0.5)}
NOTE_ROT = {"hand": -2.5, "sticker": -4.0, "stamp": -4.0, "tag": 0.0, "mono": 0.0}
NOTE_SIZES = {"sticker": [44, 34, 28], "tag": [30, 26, 22], "mono": [34, 30, 26], "stamp": [56, 44, 34]}


# ───────────────────────── words → token stream ─────────────────────────
NUM_RE = re.compile(r"^([+\-−~≈]?)(\$)?(\d[\d,]*(?:\.\d+)?)([kmb])?(%)?$")


def _core(raw: str) -> str:
    t = (raw or "").lower().replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    t = re.sub(r"^[^\w$%.,+\-−~≈']+", "", t)
    t = re.sub(r"[^\w$%]+$", "", t)
    return t.strip("'")


def _num(v: float) -> str:
    return (f"{v:.2f}".rstrip("0").rstrip(".")) if v != int(v) else str(int(v))


def tokenize(words: list[dict]) -> list[dict]:
    """Normalised tokens over a word list [{w, t}], each {k, v, money, pct, i0, i1, digits}.
    Joins "$5" ",000" → $5000, "$9" ".40" → $9.4, "30" "%" → 30%; folds "five thousand dollars" → $5000,
    "half a million" → 500000, "twenty five" → 25."""
    toks: list[dict] = []
    i = 0
    n = len(words)

    def last_num():
        return toks[-1] if toks and toks[-1]["v"] is not None else None

    while i < n:
        raw = words[i]["w"]
        c = _core(raw)
        prev = last_num()
        prev_adjacent = prev is not None and prev["i1"] == i - 1
        if not c:
            i += 1
            continue
        # continuation pieces of a number split by the transcriber
        if prev_adjacent and re.fullmatch(r",\d{3}", c):
            prev["v"] = prev["v"] * 1000 + int(c[1:])
            prev["digits"] += c[1:]
            prev["i1"] = i
            i += 1
            continue
        if prev_adjacent and re.fullmatch(r"\.\d+", c) and float(prev["v"]).is_integer():
            prev["v"] = prev["v"] + float("0" + c)
            prev["digits"] += c[1:]
            prev["i1"] = i
            i += 1
            continue
        if prev_adjacent and c in PCT_WORDS:
            prev["pct"] = True
            prev["i1"] = i
            i += 1
            continue
        if prev_adjacent and c in MONEY_WORDS:
            prev["money"] = True
            prev["i1"] = i
            i += 1
            continue
        if prev_adjacent and c in MULT and c not in ("m", "b", "k"):
            prev["v"] = prev["v"] * MULT[c]
            prev["i1"] = i
            prev["digits"] = re.sub(r"\D", "", _num(prev["v"]))
            i += 1
            continue
        if c == "half" and i + 2 < n and _core(words[i + 1]["w"]) in ("a", "an") and _core(words[i + 2]["w"]) in MULT:
            v = 0.5 * MULT[_core(words[i + 2]["w"])]
            toks.append({"k": _num(v), "v": v, "money": False, "pct": False, "i0": i, "i1": i + 2, "digits": _num(v)})
            i += 3
            continue
        if c in ONES or c in TENS:
            v = ONES.get(c, TENS.get(c))
            if prev_adjacent and prev.get("word") and prev["v"] in TENS.values() and c in ONES and 0 < v < 10:
                prev["v"] += v
                prev["i1"] = i
                prev["digits"] = str(int(prev["v"]))
                i += 1
                continue
            toks.append({"k": str(v), "v": float(v), "money": False, "pct": False, "i0": i, "i1": i, "digits": str(v), "word": True})
            i += 1
            continue
        m = NUM_RE.match(c.replace("−", "-"))
        if m:
            sign, dollar, digits, mult, pct = m.groups()
            v = float(digits.replace(",", ""))
            if mult:
                v *= MULT[mult]
            toks.append({"k": "", "v": v, "money": bool(dollar), "pct": bool(pct), "i0": i, "i1": i,
                         "digits": digits.replace(",", "").replace(".", ""), "neg": sign in ("-", "−")})
            i += 1
            continue
        k = common.norm(c)
        if k:
            toks.append({"k": k, "v": None, "money": False, "pct": False, "i0": i, "i1": i})
        i += 1
    for t in toks:
        if t["v"] is not None:
            t["k"] = ("$" if t["money"] else "") + _num(t["v"]) + ("%" if t["pct"] else "")
    return toks


def text_tokens(text: str) -> list[dict]:
    text = (text or "").replace("\\n", " ").replace("·", " ").replace("…", " ")
    return tokenize([{"w": w, "t": 0.0} for w in re.split(r"\s+", text.strip()) if w])


def tok_eq(a: dict, b: dict) -> bool:
    if a["v"] is not None or b["v"] is not None:
        if a["v"] is None or b["v"] is None:
            return False
        if (a["pct"] and b["money"]) or (a["money"] and b["pct"]):
            return False
        if abs(abs(a["v"]) - abs(b["v"])) < 1e-6:
            return True
        da, db = a["digits"].strip("0"), b["digits"].strip("0")
        return len(a["digits"]) >= 3 and len(b["digits"]) >= 3 and da == db
    x, y = a["k"], b["k"]
    if x == y or common.same(x, y):
        return True
    if x.endswith("'s") and x[:-2] == y or y.endswith("'s") and y[:-2] == x:
        return True
    return len(x) >= 5 and len(y) >= 5 and SequenceMatcher(None, x, y).ratio() >= 0.86


def is_content(t: dict) -> bool:
    return t["v"] is not None or (t["k"] not in STOP and len(t["k"]) >= 2)


def find_phrase(stream: list[dict], phrase, start: int = 0) -> list[int] | None:
    """Positions (stream indices) of the phrase's tokens, exact and consecutive, first occurrence at/after start."""
    p = text_tokens(phrase) if isinstance(phrase, str) else phrase
    if not p:
        return None
    for s in range(max(0, start), len(stream) - len(p) + 1):
        if all(tok_eq(stream[s + j], p[j]) for j in range(len(p))):
            return list(range(s, s + len(p)))
    return None


def find_gappy(stream: list[dict], phrase, start: int = 0) -> list[int] | None:
    """Tolerant match: at least 60 % of the phrase's content tokens, in order, inside a short span (ad-libs and
    transcription slips between them). Returns the matched positions, earliest start first."""
    p = text_tokens(phrase) if isinstance(phrase, str) else phrase
    content = [t for t in p if is_content(t)]
    if not content:
        return None
    need = max(1, math.ceil(0.6 * len(content)))
    span = len(p) + 4
    best = None
    for s in range(max(0, start), len(stream)):
        j0 = next((j for j, c in enumerate(content) if tok_eq(stream[s], c)), None)
        if j0 is None:
            continue
        pos = [s]
        j, k = j0 + 1, s + 1
        while j < len(content) and k < min(len(stream), s + span):
            # a content word may be missing ("Kevin sets the price" said as "Kevin says the price")
            hit = next((jj for jj in range(j, len(content)) if tok_eq(stream[k], content[jj])), None)
            if hit is not None:
                pos.append(k)
                j = hit + 1
            k += 1
        if len(pos) >= need:
            best = pos
            break
    return best


def money_ok(stream: list[dict], words: list[dict], j: int, want: str = "money") -> bool:
    """Is spoken token j said as money (or percent)? Never after 'of'/'out', never before a count noun."""
    t = stream[j]
    if t["v"] is None:
        return False
    nxt = _core(words[t["i1"] + 1]["w"]) if t["i1"] + 1 < len(words) else ""
    prv = _core(words[t["i0"] - 1]["w"]) if t["i0"] > 0 else ""
    if want == "percent":
        # "10 % of that" is a percent said as a percent; "5 out of 13" never is
        return t["pct"] and prv not in ("of", "out")
    if prv in ("of", "out") or nxt in COUNT_AFTER:
        return False
    if t["pct"]:
        return False
    return t["money"] or prv in PAY_BEFORE


# ───────────────────────── geometry helpers ─────────────────────────
def _ov(a, b) -> bool:
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def _pad(b, p):
    return {"x": b["x"] - p, "y": b["y"] - p, "w": b["w"] + 2 * p, "h": b["h"] + 2 * p}


def _center(b):
    return b["x"] + b["w"] / 2, b["y"] + b["h"] / 2


def _dist(a, b) -> float:
    ax, ay = _center(a)
    bx, by = _center(b)
    return math.hypot(ax - bx, ay - by)


def _gap(a, b) -> float:
    dx = max(0.0, max(a["x"], b["x"]) - min(a["x"] + a["w"], b["x"] + b["w"]))
    dy = max(0.0, max(a["y"], b["y"]) - min(a["y"] + a["h"], b["y"] + b["h"]))
    return math.hypot(dx, dy)


def _in_zone(b) -> bool:
    return _ov(b, CAM)


# ───────────────────────── the choreographer ─────────────────────────
class Board:
    def __init__(self, n, units_doc, brief_board, words, start, end, fps):
        self.n = n
        self.U = units_doc["units"] if isinstance(units_doc, dict) else list(units_doc)
        self.by = {u["id"]: u for u in self.U}
        self.order = {u["id"]: k for k, u in enumerate(self.U)}
        self.brief = brief_board or None
        self.start, self.end = float(start), float(end)
        self.dur = round(self.end - self.start, 3)
        self.fps = str(fps)
        self.words = [{"w": w["w"], "t": round(float(w["t"]) - self.start, 3),
                       "e": round(float(w.get("e", w["t"])) - self.start, 3)} for w in words]
        self.S = tokenize(self.words)
        self.freq: dict[str, int] = {}
        for t in self.S:
            self.freq[t["k"]] = self.freq.get(t["k"], 0) + 1
        self.plan: dict[str, dict] = {}
        self.claimed: dict[str, int] = {}     # uid -> build index
        self.report: list[str] = []
        self.flags: list[str] = []
        self.cues: list[dict] = []
        self.notes: list[dict] = []
        self.context_ids: set[str] = set()
        self.arrow_waits: dict[str, tuple] = {}
        self.max_notes = max(16, math.ceil(self.dur / 4.0))        # brief fillers
        self.hard_cap = max(self.max_notes, math.ceil(self.dur / 2.0))  # fillers + auto notes for dead air
        self.dark = _is_dark(units_doc.get("bg") if isinstance(units_doc, dict) else None) or any(
            _is_dark(u.get("fill")) for u in self.U if u.get("backdrop"))
        self.utok = {u["id"]: text_tokens(u.get("own_text") or u.get("text") or "") for u in self.U}
        self.ttok = {u["id"]: text_tokens(u.get("text") or "") for u in self.U}

    # ── small helpers ──
    def wt(self, j: int) -> float:
        """board-local time of stream token j (its first word)."""
        return self.words[self.S[j]["i0"]]["t"]

    def wtxt(self, pos: list[int]) -> str:
        i0, i1 = self.S[pos[0]]["i0"], self.S[pos[-1]]["i1"]
        return " ".join(w["w"] for w in self.words[i0:i1 + 1])

    def set(self, uid, t, how, why, word=None, move=None, dep=None, phrase=None):
        u = self.by[uid]
        self.plan[uid] = {"t": None if t is None else round(float(t), 3), "how": how, "why": why, "word": word,
                          "move": move or u["default_move"], "dep": dep, "phrase": phrase}

    def visible_units(self):
        return [u for u in self.U if self.plan.get(u["id"], {}).get("move") not in ("hide",)]

    # ── element description → units ──
    def best_text_unit(self, q: str, allow_claimed=False, near=None, skip=()) -> dict | None:
        qt = text_tokens(q)
        if not qt:
            # no words or numbers in it ("$_.__"): compare the raw text
            raw = re.sub(r"\s+", "", q).lower()
            hits = [u for u in self.U if raw and re.sub(r"\s+", "", (u.get("own_text") or u.get("text") or "")).lower() == raw
                    and (allow_claimed or u["id"] not in self.claimed) and u["id"] not in skip]
            return hits[0] if hits else None
        qn = " ".join(t["k"] for t in qt)
        cands = []
        for u in self.U:
            if u["id"] in skip:
                continue
            if u["kind"] == "headline" and qn not in " ".join(t["k"] for t in self.ttok[u["id"]]):
                continue
            own = self.utok[u["id"]]
            full = self.ttok[u["id"]]
            if not own and not full:
                continue
            score = 0
            if len(own) == len(qt) and all(tok_eq(a, b) for a, b in zip(own, qt)):
                score = 5
            elif len(full) == len(qt) and all(tok_eq(a, b) for a, b in zip(full, qt)):
                score = 4.5
            elif len(own) >= len(qt) and all(tok_eq(a, b) for a, b in zip(own, qt)):
                score = 4
            elif find_phrase(own, qt) is not None:
                score = 3
            elif find_phrase(full, qt) is not None:
                score = 2
            elif len(qt) >= 2:
                hits = sum(1 for t in qt if is_content(t) and any(tok_eq(t, o) for o in full))
                content = sum(1 for t in qt if is_content(t))
                if content and hits / content >= 0.75:
                    score = 1
            if score:
                claimed = u["id"] in self.claimed
                cands.append((score, 0 if not claimed else -1, -(len(full)), u))
        if not cands:
            return None
        free = [c for c in cands if c[1] == 0]
        pool = free if (free or not allow_claimed) else cands
        if not pool:
            return None
        top = max(c[0] for c in pool)
        pool = [c for c in pool if c[0] == top]
        if near is not None and len(pool) > 1:
            pool.sort(key=lambda c: _dist(c[3]["bbox"], near))
            return pool[0][3]
        # same score: the deepest (fewest extra words), then DOM order
        pool.sort(key=lambda c: (c[2] * -1, self.order[c[3]["id"]]))
        return pool[0][3]

    def match_element(self, elem: str, prev_units: list[dict]) -> tuple[list[dict], list[str]]:
        found: list[dict] = []
        notes: list[str] = []
        for uid in re.findall(r"(?<![\w-])#?(u\d+)\b", elem):
            if uid in self.by and self.by[uid] not in found:
                found.append(self.by[uid])
        if found:          # explicit unit ids are authoritative: the description around them is for people
            return found, notes
        parts = [p for p in _split_parts(elem) if p.strip()]
        for part in parts:
            qs = _quoted(part)
            low = re.sub(r'"[^"]*"|“[^”]*”', " ", part).lower()
            kinds = [k for w, k in KIND_WORDS.items() if re.search(r"\b" + re.escape(w) + r"\b", low)]
            allowed_k = set(k for ks in kinds for k in ks)
            refs = []
            for q in qs:
                taken = {x["id"] for x in found}
                u = self.best_text_unit(q, skip=taken) or self.best_text_unit(q, allow_claimed=True)
                if not u:
                    notes.append(f"no element with the text \"{q}\"")
                    continue
                # '"$5,000" card' names the card itself; 'arrow from "6M" to the row' only points at "6M"
                texty = re.search(r"\b(label|labels|text|number|numbers|price|name|title|word|words|value|amount|line)\b", low)
                if u["id"] not in self.claimed and u not in found and (not kinds or u["kind"] in allowed_k or texty):
                    found.append(u)
                else:
                    refs.append(u)
            if qs and (not kinds or not refs):
                continue
            plain = [w for w in re.findall(r"[\w$%.,'’]+", low) if w not in KIND_WORDS and w not in STOP and
                     w not in ("from", "to", "on", "of", "with", "its", "his", "her", "their", "empty", "first",
                               "second", "lit", "lights", "returns", "red", "blue", "green", "orange", "teal", "yellow",
                               "small", "big", "large", "new", "one", "both", "each", "every", "all", "s")]
            # an unquoted name that is a unit's whole text ("Kevin + label")
            if plain and not kinds:
                u = self.best_text_unit(" ".join(plain), skip={x["id"] for x in found})
                if u and u not in found:
                    found.append(u)
                    continue
            if kinds:
                allowed = allowed_k
                ref_units = refs or found or [u for u in (self.best_text_unit(w, allow_claimed=True) for w in plain) if u] or prev_units
                plural = any(re.search(r"\b" + w + r"\b", low) for w in KIND_WORDS if w.endswith("s") and w[:-1] in KIND_WORDS)
                pool = [u for u in self.U if u["kind"] in allowed and u["id"] not in self.claimed and u not in found
                        and not (u["kind"] == "arrow" and u.get("bbox", {}).get("w", 0) * u.get("bbox", {}).get("h", 0) <= 0)]
                if "circle" in low or "ring" in low:
                    pool.sort(key=lambda u: 0 if u.get("stroke") == "ring" else 1)
                textless_first = [u for u in pool if not u.get("text")] + [u for u in pool if u.get("text")]
                pool = textless_first
                if not pool:
                    loose = [r for r in refs if r["id"] not in self.claimed and r not in found]
                    if loose:          # the kind word described the quoted element itself
                        found += loose
                    elif not (plain and self.best_text_unit(" ".join(plain), allow_claimed=True)):
                        notes.append(f"nothing on the board matches \"{part.strip()}\"")
                    continue
                if ref_units:
                    rb = ref_units[0]["bbox"]
                    pool.sort(key=lambda u: (_gap(u["bbox"], rb), _dist(u["bbox"], rb)))
                else:
                    pool.sort(key=lambda u: self.order[u["id"]])
                if plural:
                    near = [u for u in pool if not ref_units or _gap(u["bbox"], ref_units[0]["bbox"]) < 350]
                    found += (near or pool[:1])[:4]
                else:
                    found.append(pool[0])
            elif plain:
                u = self.best_text_unit(" ".join(plain), skip={x["id"] for x in found})
                if u and u not in found:
                    found.append(u)
                else:
                    notes.append(f"nothing on the board matches \"{part.strip()}\"")
            elif part.strip() and not qs:
                # symbols only ("±", "→"): the next unused element with exactly that text
                u = self.best_text_unit(part.strip(), skip={x["id"] for x in found})
                if u and u not in found:
                    found.append(u)
                else:
                    notes.append(f"nothing on the board matches \"{part.strip()}\"")
        return found, notes

    # ── anchoring ──
    def locate(self, phrase: str, cursor: int, elem_units: list[dict]) -> tuple[int, list[int], str] | None:
        """(landing token index, matched positions, how) for a phrase: exact after the cursor, exact anywhere,
        tolerant after the cursor, tolerant anywhere."""
        for finder, frm, how in ((find_phrase, cursor, "exact"), (find_phrase, 0, "exact"),
                                 (find_gappy, cursor, "tolerant"), (find_gappy, 0, "tolerant")):
            pos = finder(self.S, phrase, frm)
            if pos:
                # land on the first matched word that names the element itself (named things on their name)
                land = pos[0]
                etoks = [t for u in elem_units for t in self.ttok[u["id"]] if is_content(t)]
                for j in pos:
                    if is_content(self.S[j]) and any(tok_eq(self.S[j], e) for e in etoks):
                        land = j
                        break
                return land, pos, how
        return None

    def own_text_anchor(self, u: dict, cursor: int) -> tuple[int, str] | None:
        toks = [t for t in self.utok[u["id"]] if is_content(t)] or [t for t in self.ttok[u["id"]] if is_content(t)]
        strong = []
        for k, t in enumerate(toks[:8]):
            f = sum(1 for s in self.S if tok_eq(s, t))
            if not f:
                continue
            if t["v"] is not None or (len(t["k"]) >= 5 and f <= 2 and t["k"] not in JUNK):
                strong.append((0 if t["v"] is not None else 1, f, k, t))
            elif len(t["k"]) >= 4 and t["k"] not in STOP:
                strong.append((2, f, k, t))       # last resort: a frequent or plain word of its own text
        money_unit = "$" in (u.get("text") or "")
        for _, _, _, t in sorted(strong, key=lambda x: x[:3]):
            for frm in (cursor, 0):
                for j in range(frm, len(self.S)):
                    if tok_eq(self.S[j], t):
                        if t["v"] is not None and money_unit and not t["pct"] and not money_ok(self.S, self.words, j):
                            continue
                        return j, self.wtxt([j])
        return None

    def run(self) -> dict:
        U = self.U
        builds = (self.brief or {}).get("builds", []) if self.brief else []
        if not self.brief:
            self.report.append("no brief for this board: every element is anchored by its own text")
        # fixed furniture
        for u in U:
            if u["kind"] == "headline":
                self.set(u["id"], 0.0, "fixed", "headline: on screen from the first frame", move="label")
            elif u["kind"] == "label" and u.get("header"):
                self.set(u["id"], 0.0, "fixed", "header label: on screen from the first frame", move="label")
            elif u.get("backdrop"):
                self.set(u["id"], 0.0, "fixed", "backdrop: part of the board's paper, on screen from the first frame",
                         move="label")
        structure: list[str] = []
        pending: dict[str, tuple] = {}
        bt: list[float | None] = []
        b_units: list[list[str]] = []
        cursor = 0
        prev_units: list[dict] = []
        # ── rule 2: the brief's builds, in order ──
        for bi, b in enumerate(builds):
            anchors = b.get("anchors") or ([b["anchor"]] if b.get("anchor") else [])
            elem_units, notes = self.match_element(b.get("element", ""), prev_units)
            elem_units = [u for u in elem_units if u["kind"] != "headline" or b.get("anchor") == "hide"]
            fresh = [u for u in elem_units if u["id"] not in self.claimed and u["id"] not in self.plan]
            if not fresh:
                why = "; ".join(notes) if notes else "every match was already placed by an earlier build"
                if b.get("anchor") != "structure" or notes:
                    self.report.append(f"build {bi + 1} \"{b.get('element', '')[:60]}\": element not found on the board ({why})")
                bt.append(None)
                b_units.append([])
                continue
            for u in fresh:
                self.claimed[u["id"]] = bi
            ids = [u["id"] for u in fresh]
            b_units.append(ids)
            prev_units = fresh
            a0 = (anchors[0] if anchors else None) or ""
            if a0 == "hide":
                for uid in ids:
                    self.set(uid, 0.0, "hide", f"brief: build {bi + 1} hides it", move="hide")
                bt.append(None)
                continue
            if a0 == "structure":
                structure += ids
                bt.append(0.45)
                continue
            if a0.startswith("with:"):
                for k, uid in enumerate(ids):
                    pending[uid] = ("with", a0[5:], 0.1 + 0.1 * k, bi)
                bt.append(None)
                continue
            m = re.fullmatch(r"\+(\d+(?:\.\d+)?)", a0)
            if m:
                for k, uid in enumerate(ids):
                    pending[uid] = ("plus", bi, float(m.group(1)) + 0.1 * k)
                bt.append(None)
                continue
            m = re.fullmatch(r"@(\d+(?:\.\d+)?)", a0)
            if m:
                for k, uid in enumerate(ids):
                    self.set(uid, float(m.group(1)) + 0.1 * k, "at", f"brief: fixed time {m.group(1)} s (not tied to a word)")
                bt.append(float(m.group(1)))
                continue
            # phrase anchors: one per unit in order when several are given ("rows → 'a', 'b', 'c'")
            land_t = None
            groups = [ids] if len(anchors) <= 1 else [[uid] for uid in ids[:len(anchors) - 1]] + [ids[len(anchors) - 1:]]
            for gi, gids in enumerate(groups):
                if not gids:
                    continue
                phrase = (anchors[min(gi, len(anchors) - 1)] if anchors else "") or ""
                hit = self.locate(phrase, cursor, [self.by[x] for x in gids]) if phrase.strip() else None
                how, why = "phrase", None
                if hit:
                    j, pos, mode = hit
                    # the next build searches from this landing word on: monotonic, and overlapping anchors
                    # ("train the next model", then "next model") still find their first occurrence
                    cursor = max(cursor, j)
                    tw = self.wt(j)
                    said = self.wtxt(pos)
                    why = f"anchor '{phrase}' @{tw + 0.05:.2f}" + ("" if mode == "exact" else f" (heard '{said}')")
                    word = {"w": self.words[self.S[j]["i0"]]["w"], "t": tw}
                else:
                    # fallbacks: the element's own text, then the key number in the build
                    own = None
                    for uid in gids:
                        own = self.own_text_anchor(self.by[uid], cursor)
                        if own:
                            break
                    if not own:
                        nums = [t for t in text_tokens((b.get("raw") or b.get("element") or "") + " " + phrase) if t["v"] is not None]
                        for nt in nums:
                            j2 = next((j for j in range(len(self.S)) if tok_eq(self.S[j], nt)), None)
                            if j2 is not None:
                                own = (j2, self.wtxt([j2]))
                                break
                    if own:
                        j, said = own
                        tw = self.wt(j)
                        how = "own"
                        heard = f"anchor '{phrase}' not heard" if phrase.strip() else "no anchor words in the brief"
                        why = f"{heard}; own text/number '{said}' @{tw + 0.05:.2f}"
                        word = {"w": self.words[self.S[j]["i0"]]["w"], "t": tw}
                        msg = (f"anchor not found: build {bi + 1} \"{b.get('element', '')[:50]}\" ({heard}); "
                               f"landed on its own text '{said}' @{tw + 0.05:.2f}")
                        self.report.append(msg)
                        self.flags.append(msg)
                    else:
                        prev_t = next((x for x in reversed(bt) if x is not None), 0.45)
                        for k, uid in enumerate(gids):
                            pending[uid] = ("cascade_after", prev_t, 0.2 + 0.1 * k)
                        msg = (f"anchor not found: build {bi + 1} \"{b.get('element', '')[:50]}\" "
                               + (f"(\"{phrase}\" not heard" if phrase.strip() else "(no anchor words in the brief")
                               + "); cascaded 0.2 s after the previous element")
                        self.report.append(msg)
                        self.flags.append(msg)
                        continue
                t0 = tw + 0.05
                for k, uid in enumerate(gids):
                    self.set(uid, t0 + 0.1 * k, how, why if k == 0 else why + f" (+{0.1 * k:.1f} in its group)", word=word,
                             phrase=phrase or None)
                if land_t is None:
                    land_t = t0
            bt.append(land_t)
        # recalled numbers ("$20 (money, recalled)") are context: they come with the structure, never on a word
        for nt in self._recalled_tokens():
            for u in U:
                if u["id"] in self.claimed or u["id"] in self.plan or u["kind"] in ("headline", "legend"):
                    continue
                if any(tok_eq(nt, x) for x in (self.utok[u["id"]] or self.ttok[u["id"]])):
                    self.claimed[u["id"]] = -1
                    structure.append(u["id"])
        # ── furniture and everything the brief did not name ──
        for u in U:
            uid = u["id"]
            if uid in self.plan or uid in pending or uid in structure:
                continue
            if u["kind"] == "legend":
                self.set(uid, 0.25, "fixed", "honesty tag: on screen at 0.25 s")
        own_cursor = 0
        for u in U:
            uid = u["id"]
            if uid in self.plan or uid in pending or uid in structure:
                continue
            par = u.get("parent")
            if par and par in self.claimed and par not in structure and self.plan.get(par, {}).get("move") != "hide":
                # a part of something the brief named lands with it ("$10" printed on B's bar)
                pending[uid] = ("attach", par, 0.1)
                continue
            has_text = bool((u.get("own_text") or u.get("text") or "").strip()) and u["kind"] not in ("container",) or (
                u["kind"] == "container" and (u.get("own_text") or "").strip())
            if has_text:
                hit = self.own_text_anchor(u, own_cursor)
                if hit:
                    j, said = hit
                    own_cursor = max(own_cursor, j + 1)
                    tw = self.wt(j)
                    why = f"own text '{said}' @{tw + 0.05:.2f}" + ("" if not self.brief else " (not in the brief)")
                    self.set(uid, tw + 0.05, "own", why, word={"w": self.words[self.S[j]["i0"]]["w"], "t": tw})
                    continue
                if u["kind"] == "container":
                    pending[uid] = ("contain",)
                    continue
                pending[uid] = ("cascade_dom",)
                continue
            # textless
            if u["children"]:
                pending[uid] = ("contain",)
            elif u.get("parent"):
                pending[uid] = ("attach", u["parent"], 0.1)
            elif u["kind"] == "arrow":
                pending[uid] = ("arrow",)
            elif u["kind"] in ("zone",):
                structure.append(uid)
            else:
                pending[uid] = ("near",)
        # ── rule 1: structure cascade (with the unnamed parts and holders of what the brief put there) ──
        sset = list(dict.fromkeys(structure))
        for uid in list(sset):
            u = self.by[uid]
            p = u.get("parent")
            while p and p not in self.claimed and p not in sset and p not in self.plan:
                sset.append(p)
                pending.pop(p, None)
                p = self.by[p].get("parent")
            for c in u["children"]:
                cu = self.by[c]
                if c not in self.claimed and c not in self.plan and not (cu.get("text") or "").strip():
                    sset.append(c)
                    pending.pop(c, None)
        sset = sorted(set(sset), key=lambda x: self.order[x])
        self.context_ids = set(sset)          # structure-step elements are context: no stamp, no copy flag
        short = self.dur < 5.0
        step = 0.12 if not short else min(0.12, 0.55 / max(1, len(sset)))
        for k, uid in enumerate(sset):
            self.set(uid, 0.45 + step * k, "structure", "structure: on screen as the board opens")
        # ── resolve chains and attachments ──
        self._resolve(pending, bt, b_units)
        # ── rule 4: parts after containers, arrows after both ends ──
        self._containment()
        # ── rule 1: the opening, and short boards ──
        self._opening(short)
        self._follow()
        # ── rule 3 + clamps ──
        for uid, p in self.plan.items():
            if p["t"] is None:
                continue
            if p.get("word") and p["how"] in ("phrase", "own"):
                lo, hi = p["word"]["t"], p["word"]["t"] + 2.0
                if p["t"] < lo:
                    p["t"] = round(lo + 0.05, 3)
                if p["t"] > hi:
                    p["t"] = round(hi, 3)
                    p["why"] += " (capped at 2 s after its word)"
            p["t"] = round(min(max(p["t"], 0.0), max(0.0, self.dur - 0.25)), 3)
        self._containment(final=True)
        self._highlight()
        self._stamps()
        self._notes()
        self._flags()
        return self._emit()

    def _resolve(self, pending, bt, b_units):
        for _ in range(12):
            progress = False
            for uid, spec in list(pending.items()):
                t = None
                why = ""
                kind = spec[0]
                if kind == "with":
                    tgt = self._target(spec[1], uid)
                    if tgt is None:
                        self.report.append(f"{uid}: with: target \"{spec[1]}\" not found; cascaded")
                        pending[uid] = ("cascade_dom",)
                        progress = True
                        continue
                    if tgt in self.plan and self.plan[tgt]["t"] is not None:
                        t = self.plan[tgt]["t"] + spec[2]
                        why = f"with: '{spec[1]}' ({tgt}) +{spec[2]:.1f}"
                        word = self.plan[tgt].get("word")
                        self.set(uid, t, "with", why, word=word, dep=(tgt, spec[2]))
                        if bt[spec[3]] is None:
                            bt[spec[3]] = t
                elif kind == "plus":
                    bi = spec[1]
                    prev = next((bt[k] for k in range(bi - 1, -1, -1) if bt[k] is not None), None)
                    prev_pending = any(x in pending for k in range(bi) for x in b_units[k])
                    if prev is not None and not prev_pending:
                        t = prev + spec[2]
                        self.set(uid, t, "plus", f"+{spec[2]:.2f} s after the previous build")
                        if bt[bi] is None:
                            bt[bi] = t
                elif kind == "cascade_after":
                    t = spec[1] + spec[2]
                    self.set(uid, t, "cascade", f"anchor not found: cascaded {spec[2]:.1f} s after the previous element")
                elif kind == "attach":
                    p = spec[1]
                    if p in self.plan and self.plan[p]["t"] is not None:
                        t = self.plan[p]["t"] + spec[2]
                        self.set(uid, t, "attach", f"part of {p}: lands with it", word=self.plan[p].get("word"), dep=(p, spec[2]))
                    elif p not in pending:
                        pending[uid] = ("near",)
                        progress = True
                        continue
                elif kind == "contain":
                    kids = [c for c in self.by[uid]["children"]]
                    timed = [self.plan[c]["t"] for c in kids if c in self.plan and self.plan[c]["t"] is not None
                             and self.plan[c]["move"] != "hide"]
                    # parts that are only waiting for this container do not hold it back
                    waiting = [c for c in kids if c in pending and not (pending[c][0] == "attach" and pending[c][1] == uid)]
                    if not timed and not waiting:
                        pending[uid] = ("near",)
                        progress = True
                        continue
                    if timed and not waiting:
                        t = min(timed) - 0.1
                        self.set(uid, max(0.0, t), "contain", "holds parts that land later: lands just before its first part")
                    elif not kids or (not timed and not any(c in pending for c in kids)):
                        pending[uid] = ("near",)
                        progress = True
                        continue
                elif kind == "arrow":
                    ends = self._ends(uid)
                    if ends is None:
                        pending[uid] = ("near",)
                        progress = True
                        continue
                    if all(e in self.plan and self.plan[e]["t"] is not None for e in ends):
                        t = max(self.plan[e]["t"] for e in ends) + 0.1
                        self.set(uid, t, "arrow", f"arrow: after both ends ({', '.join(ends)})")
                elif kind == "near":
                    tgt = self._nearest_timed(uid, pending)
                    if tgt is not None:
                        t = self.plan[tgt]["t"] + 0.1
                        self.set(uid, t, "attach", f"lands with the element it touches ({tgt})", word=self.plan[tgt].get("word"),
                                 dep=(tgt, 0.1))
                    elif not any(x for x in pending if x != uid and pending[x][0] != "near"):
                        self.set(uid, 0.45, "structure", "unattached structure: on screen as the board opens")
                elif kind == "cascade_dom":
                    prev = [v["id"] for v in self.U if self.order[v["id"]] < self.order[uid] and v["id"] in self.plan
                            and self.plan[v["id"]]["t"] is not None and self.plan[v["id"]]["move"] != "label"]
                    if prev or not any(self.order[x] < self.order[uid] for x in pending if x != uid):
                        base = self.plan[prev[-1]]["t"] if prev else 0.45
                        self.set(uid, base + 0.2, "cascade", "no anchor in the words: cascaded after the element before it")
                        if self.brief:
                            self.report.append(f"{uid} \"{(self.by[uid].get('text') or '')[:40]}\": not in the brief and its "
                                               f"text is not spoken; cascaded after {prev[-1] if prev else 'the opening'}")
                if uid in self.plan:
                    pending.pop(uid, None)
                    progress = True
            if not pending:
                break
            if not progress:
                for uid in list(pending):
                    self.set(uid, 0.45, "structure", "unresolved: on screen as the board opens")
                    self.report.append(f"{uid}: could not be tied to anything; shown as structure")
                    pending.pop(uid)
                break

    def _target(self, text: str, uid: str) -> str | None:
        if re.fullmatch(r"u\d+", text.strip()) and text.strip() in self.by:
            return text.strip()
        u = self.best_text_unit(text, allow_claimed=True, near=self.by[uid]["bbox"])
        return u["id"] if u and u["id"] != uid else None

    def _ends(self, uid) -> list[str] | None:
        u = self.by[uid]
        if u.get("stroke") != "arrow" or not u.get("ends"):
            return None
        out = []
        for (x, y) in u["ends"]:
            pt = {"x": x - 1, "y": y - 1, "w": 2, "h": 2}
            best = None
            for v in self.U:
                # an arrow's ends are the things it connects (boxes, labels, figures), never another stroke
                if v["id"] == uid or v["kind"] in ("headline", "legend", "arrow") or v.get("backdrop") \
                        or v["bbox"]["w"] * v["bbox"]["h"] > 0.5 * W * HGT:
                    continue
                g = _gap(pt, v["bbox"])
                if g <= 60 and (best is None or g < best[0]):
                    best = (g, v["id"])
            if best and best[1] not in out:
                out.append(best[1])
        return out or None

    def _nearest_timed(self, uid, pending) -> str | None:
        u = self.by[uid]
        best = None
        for v in self.U:
            if v["id"] == uid or v["kind"] in ("headline", "legend") or v["id"] not in self.plan:
                continue
            p = self.plan[v["id"]]
            if p["t"] is None or p["move"] in ("hide", "label"):
                continue
            g = _gap(u["bbox"], v["bbox"])
            a, b = u["bbox"], v["bbox"]
            ov = max(0.0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])) * \
                max(0.0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
            key = (g, -ov)
            if g <= 160 and (best is None or key < best[0]):
                best = (key, v["id"])
        if best:
            return best[1]
        if any(x for x in pending if x != uid and pending[x][0] != "near"):
            return None
        return None

    def _containment(self, final=False):
        for _ in range(8):
            changed = False
            for u in self.U:
                p = u.get("parent")
                if not p or u["id"] not in self.plan or p not in self.plan:
                    continue
                cu, pu = self.plan[u["id"]], self.plan[p]
                if cu["t"] is None or pu["t"] is None or "hide" in (cu["move"], pu["move"]) or pu["move"] == "label":
                    continue
                if cu["t"] >= pu["t"] + 0.1 - 1e-6:
                    continue
                named_parent = pu["how"] in ("phrase", "at", "with", "plus")
                named_child = cu["how"] in ("phrase", "at", "with", "plus")
                if named_parent and (not named_child or (pu["t"] + 0.1 - (cu.get("word") or {"t": cu["t"]})["t"] <= 2.0)):
                    cu["t"] = round(pu["t"] + 0.1, 3)
                    cu["why"] += f" (after its container {p})"
                else:
                    pu["t"] = round(max(0.0, cu["t"] - 0.1), 3)
                    if "pulled" not in pu["why"]:
                        pu["why"] += f" (pulled to its part {u['id']})"
                changed = True
            for u in self.U:
                if u["kind"] != "arrow" or u["id"] not in self.plan or self.plan[u["id"]]["move"] == "hide":
                    continue
                ends = self._ends(u["id"])
                if not ends:
                    continue
                ts = [self.plan[e]["t"] for e in ends if e in self.plan and self.plan[e]["t"] is not None
                      and self.plan[e]["move"] != "label"]
                if ts and self.plan[u["id"]]["t"] < max(ts) + 0.1 - 1e-6:
                    pa = self.plan[u["id"]]
                    last = max((e for e in ends if e in self.plan and self.plan[e]["t"] is not None
                                and self.plan[e]["move"] != "label"), key=lambda e: self.plan[e]["t"])
                    pa["t"] = round(max(ts) + 0.1, 3)
                    if "(after both ends)" not in pa["why"]:
                        pa["why"] += " (after both ends)"
                    if pa.get("word") and pa["how"] in ("phrase", "own"):
                        self.arrow_waits[u["id"]] = (last, pa.get("phrase") or pa["word"]["w"], pa["word"]["t"])
                    changed = True
            if not changed:
                break

    def _follow(self):
        """Attachments follow what they hang on: an outline or stroke drawn on a container comes 0.1 s after the
        container wherever it ended up (structure in the opening cascade, never with the content)."""
        for _ in range(6):
            changed = False
            for uid, p in self.plan.items():
                d = p.get("dep")
                if not d or d[0] not in self.plan or self.plan[d[0]]["t"] is None or p["t"] is None:
                    continue
                want = round(self.plan[d[0]]["t"] + d[1], 3)
                if abs(p["t"] - want) > 1e-6 and p["how"] in ("attach", "with"):
                    p["t"] = want
                    changed = True
            if not changed:
                break

    def _opening(self, short: bool):
        content = [(p["t"], uid) for uid, p in self.plan.items() if p["t"] is not None and p["move"] not in ("label", "hide")
                   and self.by[uid]["kind"] not in ("headline", "legend")]
        if short:
            # a board under 5 s: structure and labels inside the first second
            loose = sorted([uid for uid, p in self.plan.items() if p["how"] not in ("phrase", "own", "at", "fixed")
                            and p["move"] not in ("label", "hide")], key=lambda x: self.order[x])
            for k, uid in enumerate(loose):
                self.plan[uid]["t"] = round(min(self.plan[uid]["t"] or 1.0, 0.3 + 0.7 * k / max(1, len(loose))), 3)
            return
        first = min([t for t, _ in content], default=self.dur)
        if first <= 0.9:
            return
        cands = sorted([uid for uid, p in self.plan.items() if p["how"] in ("contain", "attach", "structure", "cascade", "arrow")
                        and self.by[uid]["kind"] in STRUCT_KINDS and not (self.by[uid].get("text") or "").strip()
                        and (p["t"] or 0) > 0.9], key=lambda x: self.order[x])[:4]
        if cands:
            for k, uid in enumerate(cands):
                self.plan[uid]["t"] = round(0.45 + 0.12 * k, 3)
                self.plan[uid]["why"] += " (opening: structure on screen by 0.9 s)"
                self.plan[uid]["how"] = "structure"
        else:
            self.report.append(f"opens with the headline only until {first:.2f} s: the first element is named then "
                               "(named things land on their name)")

    def _highlight(self):
        head = next((u for u in self.U if u["kind"] == "headline"), None)
        if not head or not head.get("hl"):
            return
        hl = head["hl"][0]
        word = (self.brief or {}).get("highlight") or hl["text"]
        if not hl.get("path") or hl.get("lines", 1) != 1:
            return
        pos = find_phrase(self.S, word) or find_gappy(self.S, word)
        if not pos:
            return
        t = self.wt(pos[0]) + 0.05
        if t > self.dur - 0.5:
            return
        self.cues.append({"id": head["id"], "move": "highlight", "t": round(t, 3), "path": hl["path"],
                          "why": f"headline highlight '{hl['text']}' pops once on '{self.wtxt(pos)}'",
                          "bbox": head["bbox"]})

    def _number_keys(self) -> list[tuple[str, dict, str]]:
        """(key text, numeric token, role) for every money/percent number on the board."""
        out = []
        nums = (self.brief or {}).get("numbers") or {}
        if nums:
            for key, role in nums.items():
                if "recalled" in role.split("+"):
                    continue                  # context that returns: never stamped, never checked against speech
                for t in text_tokens(key):
                    if t["v"] is None:
                        continue
                    r = role.split("+")
                    if t["pct"] and "percent" in r:
                        out.append((key, t, "percent"))
                    elif t["money"] and "money" in r:
                        out.append((key, t, "money"))
                    elif not t["pct"] and not t["money"] and r == ["money"] and not re.search(r"\b(of|out)\b", key):
                        out.append((key, t, "money"))
                    elif not t["pct"] and not t["money"] and r == ["percent"]:
                        out.append((key, t, "percent"))
        else:
            seen = set()
            for u in self.U:
                for p in u.get("prices", []):
                    for t in text_tokens(p):
                        if t["v"] is not None and (t["money"] or t["pct"]) and (p, t["k"]) not in seen:
                            seen.add((p, t["k"]))
                            out.append((p, t, "percent" if t["pct"] else "money"))
        return out

    def _recalled_tokens(self) -> list[dict]:
        out = []
        for key, role in ((self.brief or {}).get("numbers") or {}).items():
            if "recalled" in role.split("+"):
                out += [t for t in text_tokens(key) if t["v"] is not None]
        return out

    def _holders(self, nt) -> list[dict]:
        return [u for u in self.U if u["kind"] not in ("headline", "legend")
                and any(tok_eq(nt, x) for x in (self.utok[u["id"]] or self.ttok[u["id"]]))]

    def _stamps(self):
        stamped = set()
        for key, nt, role in self._number_keys():
            holders = [u for u in self.U if u["id"] in self.plan and self.plan[u["id"]]["move"] not in ("hide",)
                       and u["id"] not in self.context_ids
                       and u["kind"] not in ("headline", "legend") and any(tok_eq(nt, x) for x in self.utok[u["id"]] or self.ttok[u["id"]])]
            if not holders:
                continue
            for j, st in enumerate(self.S):
                if not tok_eq(st, nt) or not money_ok(self.S, self.words, j, role):
                    continue
                tw = self.wt(j)
                same_word = [u for u in holders if u["id"] not in stamped and self.plan[u["id"]].get("word")
                             and abs(self.plan[u["id"]]["word"]["t"] - tw) < 0.6]
                landed = [u for u in holders if u["id"] not in stamped and self.plan[u["id"]]["t"] <= tw + 0.3]
                pick = (same_word or sorted(landed, key=lambda u: -self.plan[u["id"]]["t"]))[:1]
                if not pick:
                    continue
                u = pick[0]
                t = max(tw + 0.05, self.plan[u["id"]]["t"] + 0.3)
                if t > self.dur - 0.6:
                    continue
                target = next((p for p in u.get("prices", []) if any(tok_eq(nt, x) for x in text_tokens(p))), None)
                if not target:
                    raw_txt = u.get("own_text") or u.get("text") or ""
                    target = next((w for w in re.split(r"\s+", raw_txt) if any(tok_eq(nt, x) for x in text_tokens(w))), key)
                said = " ".join(w["w"] for w in self.words[max(0, st["i0"] - 1): st["i1"] + 2])
                self.cues.append({"id": u["id"], "move": "stamp", "t": round(t, 3), "target": target,
                                  "why": f"{role} '{key}' said '{self.wtxt([j])}' (… {said} …)", "bbox": u["bbox"]})
                stamped.add(u["id"])
                break

    # ── rule 6: fillers and notes ──
    def _note_box(self, text, x, y, size, style):
        cw, ew, lh, eh = NOTE_METRICS[style]
        lines = text.split("\n")

        def em(line):   # block and box glyphs, arrows and wide characters come from a fallback font: count them wide
            return sum(max(cw, 0.95) if (0x2190 <= ord(ch) <= 0x2BFF or ord(ch) >= 0x2E80) else cw for ch in line)
        w = (max(em(s) for s in lines) + ew) * size
        h = (len(lines) * lh + eh) * size
        a = math.radians(abs(NOTE_ROT.get(style, 0.0)))
        w2, h2 = w * math.cos(a) + h * math.sin(a), w * math.sin(a) + h * math.cos(a)
        return {"x": round(x - (w2 - w) / 2), "y": round(y - (h2 - h) / 2), "w": round(w2), "h": round(h2)}

    def _blocked(self, t0, t1, ignore=None):
        rects = [_pad(CAM, 24)]
        head = next((u for u in self.U if u["kind"] == "headline"), None)
        if head:   # nothing above or beside the title: the band from the top edge to the headline's bottom
            rects.append({"x": 0, "y": 0, "w": W, "h": head["bbox"]["y"] + head["bbox"]["h"] + 14})
        for u in self.U:
            p = self.plan.get(u["id"])
            if not p or p["move"] == "hide" or p["t"] is None:
                continue
            if p["t"] <= t1 and not u.get("backdrop"):
                b = u["bbox"]
                if u.get("ink") and not u.get("box_like") and u["kind"] in ("headline", "label", "row", "note", "legend"):
                    b = u["ink"]           # free space next to short text in a wide box is usable
                if b["w"] * b["h"] <= 0:
                    continue
                rects.append(_pad(b, 16 if u["kind"] != "headline" else 10))
        for n in self.notes:
            if n is ignore or (ignore == "old" and n["t"] <= t0 - 2.5):
                continue
            if n["t"] <= t1 and n["until"] >= t0:
                rects.append(_pad(n["bbox"], 22))
        return rects

    def _coverage(self, t0):
        a = 0.0
        for u in self.U:
            p = self.plan.get(u["id"])
            if not p or p["t"] is None or p["move"] == "hide" or p["t"] > t0 + 0.3 or u["kind"] in ("headline",) \
                    or u.get("backdrop"):
                continue
            if u["parent"] and u["parent"] in self.plan:
                continue
            b = u["bbox"]
            a += max(0.0, b["w"]) * max(0.0, b["h"])
        return min(1.0, a / (W * HGT))

    def _free_spot(self, t0, t1, wbox, hbox, pref=None, ignore=None):
        """Top-left of a free wbox x hbox spot visible from t0 to t1, inside the largest free area, closest to pref."""
        cell = 20
        gw, gh = W // cell, HGT // cell
        free = [[True] * gw for _ in range(gh)]
        for r in self._blocked(t0, t1, ignore):
            x0, y0 = max(0, int(r["x"] // cell)), max(0, int(r["y"] // cell))
            x1, y1 = min(gw, int(math.ceil((r["x"] + r["w"]) / cell))), min(gh, int(math.ceil((r["y"] + r["h"]) / cell)))
            for yy in range(y0, y1):
                row = free[yy]
                for xx in range(x0, x1):
                    row[xx] = False
        # margins
        for yy in range(gh):
            for xx in range(gw):
                if xx * cell < 64 or (xx + 1) * cell > W - 48 or yy * cell < 40 or (yy + 1) * cell > HGT - 36:
                    free[yy][xx] = False
        # prefix sums of blocked cells
        ps = [[0] * (gw + 1) for _ in range(gh + 1)]
        for yy in range(gh):
            acc = 0
            for xx in range(gw):
                acc += 0 if free[yy][xx] else 1
                ps[yy + 1][xx + 1] = ps[yy][xx + 1] + acc
        cw, ch = int(math.ceil(wbox / cell)), int(math.ceil(hbox / cell))
        if cw > gw or ch > gh:
            return None
        fits = []
        for yy in range(0, gh - ch + 1):
            for xx in range(0, gw - cw + 1):
                if ps[yy + ch][xx + cw] - ps[yy][xx + cw] - ps[yy + ch][xx] + ps[yy][xx] == 0:
                    fits.append((xx, yy))
        if not fits:
            return None
        if pref is None:
            # centre of the largest free rectangle (histogram method)
            best = (0, 0, 0, 0, 0)
            hist = [0] * gw
            for yy in range(gh):
                for xx in range(gw):
                    hist[xx] = hist[xx] + 1 if free[yy][xx] else 0
                stack = []
                for xx in range(gw + 1):
                    hcur = hist[xx] if xx < gw else 0
                    start = xx
                    while stack and stack[-1][1] >= hcur:
                        s, hh = stack.pop()
                        area = hh * (xx - s)
                        if area > best[0]:
                            best = (area, s, yy - hh + 1, xx - s, hh)
                        start = s
                    stack.append((start, hcur))
            _, bx, by, bw, bh = best
            # the top-left of the largest free area (leaves room for the next note below or beside it)
            pref = (bx * cell + wbox / 2, by * cell + hbox / 2)
        px, py = pref
        xx, yy = min(fits, key=lambda f: (math.hypot(f[0] * cell + wbox / 2 - px, f[1] * cell + hbox / 2 - py), f[1], f[0]))
        return xx * cell + 4, yy * cell + 4

    def _place(self, text, t0, style, near=None, sizes=None, hold=9.0):
        cov = self._coverage(t0)
        if sizes is None:
            if style == "hand":
                n = max(len(s) for s in text.split("\n"))
                if cov < 0.15:
                    sizes = [130 if n <= 16 else 96, 84, 64, 54, 44, 38, 32]
                elif cov < 0.40:
                    sizes = [84 if n <= 22 else 64, 54, 44, 38, 32]
                else:
                    sizes = [54, 44, 38, 32]
            else:
                sizes = NOTE_SIZES[style]
        pref = None
        if near is not None:
            nb = near["bbox"]
            pref = (nb["x"] + nb["w"] / 2, nb["y"] + nb["h"] + 40)
        for ignore in (None, "old"):
            # second pass: a note that has been up for 2.5 s gives its place to the new one (it fades as this lands)
            for size in sizes:
                box = self._note_box(text, 0, 0, size, style)
                spot = self._free_spot(t0, t0 + 3.2, box["w"], box["h"], pref, ignore)
                if spot:
                    x, y = spot
                    bbox = self._note_box(text, x, y, size, style)
                    if _in_zone(bbox):
                        continue
                    if ignore == "old":
                        for n in self.notes:
                            if n["t"] <= t0 - 2.5 and n["until"] > t0 - 0.25 and _ov(_pad(n["bbox"], 22), bbox):
                                n["until"] = round(max(n["t"] + 0.8, t0 - 0.25), 3)
                    return x, y, size, bbox
        return None

    def _until(self, note, t0, hold):
        ends = [t0 + hold, self.dur]
        for u in self.U:
            p = self.plan.get(u["id"])
            if p and p["t"] is not None and p["move"] != "hide" and p["t"] > t0 + 0.3 and _ov(_pad(u["bbox"], 6), note):
                ends.append(p["t"] - 0.15)
        return round(max(t0 + 0.8, min(ends)), 3)

    def _notes(self):
        fill = (self.brief or {}).get("fillers") or []
        board_text = " ".join((u.get("text") or "") for u in self.U).lower()
        filler_times = []
        skipped: list[str] = []
        # brief fillers first, each on its own anchor
        for f in fill:
            if len(self.notes) >= self.max_notes:
                self.report.append(f"{self.max_notes} notes on this board: further fillers skipped")
                break
            text = (f.get("text") or "").replace("\\n", "\n").strip()
            anchor = f.get("anchor") or text.replace("\n", " ")
            hit = self.locate(anchor, 0, []) if anchor else None
            if not hit:
                self.report.append(f"filler \"{text[:40]}\": anchor \"{anchor}\" not heard; skipped")
                continue
            j, pos, mode = hit
            t0 = round(self.wt(pos[0]) + 0.05, 3)
            style = f.get("style") if f.get("style") in NOTE_COLORS else "hand"
            near = None
            if f.get("near"):
                near = self.best_text_unit(f["near"], allow_claimed=True)
            spot = self._place(text, t0, style, near=near)
            if spot and near is not None and _ov(_pad(near["bbox"], 40), CAM):
                self.report.append(f"filler \"{text[:40]}\": asked to sit near {near['id']}, which touches the camera "
                                   f"zone; placed at {spot[0]},{spot[1]} outside it")
            if not spot:
                skipped.append(f"\"{text[:40]}\" @{t0:.2f}")
                continue
            x, y, size, bbox = spot
            note = {"t": t0, "text": text, "x": x, "y": y, "size": size, "style": style, "bbox": bbox,
                    "why": f"brief filler on '{self.wtxt(pos)}' @{t0:.2f}", "word": {"w": self.words[self.S[pos[0]]["i0"]]["w"], "t": self.wt(pos[0])}}
            note["until"] = self._until(bbox, t0, 9.0)
            self.notes.append(note)
            filler_times.append(t0)
        if skipped:
            self.report.append(f"{len(skipped)} brief filler(s) skipped, no free space outside the camera zone and the "
                               f"board's elements at that moment: " + "; ".join(skipped))
        # auto notes: every stretch over 3 s with nothing landing while the presenter talks (the presenter's exact words)
        used = set()
        for _ in range(4 * self.hard_cap + 40):
            if len(self.notes) >= self.hard_cap:
                break
            events = sorted(set([0.0, self.dur] + [p["t"] for p in self.plan.values() if p["t"] is not None and
                                                    p["move"] not in ("label", "hide")] +
                                [c["t"] for c in self.cues] + [n["t"] for n in self.notes]))
            gap = None
            for g0, g1 in zip(events, events[1:]):
                if g1 - g0 > 3.0 and any(g0 + 0.3 < w["t"] < g1 - 0.3 for w in self.words) and (g0, g1) not in used:
                    gap = (g0, g1)
                    break
            if not gap:
                break
            used.add(gap)
            g0, g1 = gap
            lead = 2.2 if any(abs(n["t"] - g0) < 0.01 for n in self.notes) else 1.0
            # within 3 s of the last landing: the strongest spoken words first, then any of the presenter's words;
            # failing that, the earliest of the presenter's words anywhere in the stretch (the rest is handled on the next pass)
            placed = (self._auto_note(g0 + lead, min(g1 - 0.6, g0 + 3.0), g1, board_text, filler_times, g0=g0)
                      or self._auto_note(g0 + 0.6, min(g1 - 0.6, g0 + 3.0), g1, board_text, filler_times, loose=True, g0=g0)
                      or self._auto_note(g0 + 0.6, g1 - 0.6, g1, board_text, filler_times, loose=True, early=True, g0=g0)
                      # last resort, so nothing sits static for over 4 s: closer to a brief filler (1.3 s)
                      or (g1 - g0 > 4.0 and self._auto_note(g0 + 0.6, g1 - 0.6, g1, board_text, filler_times, loose=True,
                                                            early=True, g0=g0, clear_cap=1.3)))
            if placed:
                used.discard(gap)
        self.notes.sort(key=lambda n: n["t"])
        # what is still static for more than 4 s while the presenter talks, and why (the QA report repeats it)
        events = sorted(set([0.0, self.dur] + [p["t"] for p in self.plan.values() if p["t"] is not None and
                                                p["move"] not in ("label", "hide")] + [c["t"] for c in self.cues] +
                            [n["t"] for n in self.notes]))
        for g0, g1 in zip(events, events[1:]):
            inside = [w for w in self.words if g0 < w["t"] < g1]
            if g1 - g0 > 4.0 and inside and (min(g1, inside[-1]["e"]) - max(g0, inside[0]["t"])) > 3.0:
                why = ("the notes cap for this board is reached" if len(self.notes) >= self.hard_cap else
                       "no free space outside the camera zone and the board's elements for a note")
                self.report.append(f"static {g0:.2f}-{g1:.2f} s ({g1 - g0:.1f} s) while the presenter talks: {why}")

    def _auto_note(self, a, b, g1, board_text, filler_times, loose=False, early=False, g0=None, clear_cap=2.6) -> bool:
        if b <= a:
            return False
        # an auto note keeps 2.6 s clear of the brief's fillers; between two fillers that are closer than that allows,
        # it takes the middle (never closer than 1.2 s)
        span = (g1 - g0) if g0 is not None else 99.0
        clear = min(clear_cap, max(1.2, span / 2 - 0.2))
        cands = []
        board_toks = [t for u in self.U for t in self.ttok[u["id"]]]
        for j, st in enumerate(self.S):
            tw = self.wt(j)
            if not (a <= tw <= b):
                continue
            if any(abs(tw - ft) < clear for ft in filler_times):
                continue
            if any(n.get("j") is not None and abs(n["j"] - j) <= 2 for n in self.notes):
                continue
            k = st["k"]
            if st["v"] is not None:
                score = 3
            elif len(k) >= 5 and k not in STOP and k not in JUNK and not k.endswith(("n't", "'re", "'ve", "'ll", "'d")):
                on_board = any(tok_eq(st, bt) for bt in board_toks)
                score = 0 if on_board else (2 if self.freq.get(k, 0) <= 2 else 1)
                if not score and loose:
                    score = 0.5
            elif loose and len(k) >= 3 and k not in STOP:
                score = 0.5                      # any of the presenter's words, when nothing stronger is said
            elif loose and k:
                score = 0.25                     # a small word that starts a spoken phrase ("it exists")
            else:
                score = 0
            if score:
                cands.append((-score, tw, j))
        order = sorted(cands, key=lambda c: (c[1], c[0])) if early else sorted(cands)
        for _, tw, j in order:
            text = self._phrase_at(j) or (self._phrase_at(j, loose=True) if loose else None)
            if not text or text.lower() in board_text:
                continue
            if any(text.lower() == n["text"].lower() for n in self.notes):
                continue
            t0 = round(tw + 0.05, 3)
            spot = self._place(text, t0, "hand")
            while not spot and loose and len(text.split()) > 2:
                text = " ".join(text.split()[:-1])          # a shorter piece of the same words fits where the long one does not
                while len(text.split()) > 1 and _core(text.split()[-1]) in STOP:
                    text = " ".join(text.split()[:-1])
                spot = self._place(text, t0, "hand") if " " in text else None
            if not spot:
                continue
            x, y, size, bbox = spot
            note = {"t": t0, "text": text, "x": x, "y": y, "size": size, "style": "hand", "bbox": bbox, "j": j,
                    "why": f"auto note: the presenter's words '{text}' @{t0:.2f} (nothing else lands here for over 3 s)",
                    "word": {"w": self.words[self.S[j]["i0"]]["w"], "t": tw}}
            note["until"] = self._until(bbox, t0, 9.0)
            self.notes.append(note)
            return True
        return False

    def _phrase_at(self, j, loose=False) -> str | None:
        """2-4 of the presenter's exact words around token j, never across a sentence end."""
        words = self.words
        st = self.S[j]
        i0, i1 = st["i0"], st["i1"]

        def ends(k):
            return 0 <= k < len(words) and bool(re.search(r"[.?!]$", words[k]["w"]))
        LEAD = {"about", "half", "exactly", "nearly", "almost", "double", "over", "under", "roughly", "around", "every",
                "no", "not", "only", "just", "the", "a", "an", "your", "my", "our", "their", "own"}
        UNIT = {"%", "percent", "million", "thousand", "dollars", "hour", "seconds", "sellers", "models", "clip", "clips",
                "prices", "versions", "a", "an", "to", "off", "under", "more", "less", "of", "in", "per", "on", "at"}
        start = i0
        if i0 > 0 and _core(words[i0 - 1]["w"]) in LEAD and not ends(i0 - 1):
            start = i0 - 1
        end = i1
        while end + 1 < len(words) and end - start < 3 and not ends(end) and not words[end]["w"].endswith(","):
            nx = _core(words[end + 1]["w"])
            if nx in UNIT or (end == i1 and nx and nx not in STOP) or (end > i1 and _core(words[end]["w"]) in
                                                                         {"a", "an", "to", "of", "in", "per", "on"}):
                end += 1
            else:
                break
        toks = [words[k]["w"] for k in range(start, end + 1)]
        TRAIL = STOP | {"a", "an", "to", "of", "in", "per", "on", "more", "less", "like", "which", "because", "either",
                        "so", "when", "if", "but", "and", "or"}
        while len(toks) > 1 and _core(toks[-1]) in TRAIL:
            toks.pop()
        while len(toks) > 1 and _core(toks[0]) in {"and", "so", "but", "or", "because", "then"}:
            toks.pop(0)
        txt = " ".join(toks)
        txt = re.sub(r"\s+%", "%", txt).replace(" ,", ",").replace(" .", ".").replace("$ ", "$")
        txt = re.sub(r"[.,;:?!]+$", "", txt).strip(" \"'“”")
        if re.fullmatch(r"[\d.,$%]+", txt) and not re.search(r"[$%]", txt):
            return None
        if " " not in txt and not re.search(r"[$%\d]", txt):
            if not loose:
                return None
            # loose: three of the presenter's words from here, trailing small words dropped, never across a sentence end
            k, out_w = i0, []
            while k < len(words) and len(out_w) < 4:
                out_w.append(words[k]["w"])
                if ends(k):
                    break
                k += 1
            while len(out_w) > 1 and _core(out_w[-1]) in TRAIL:
                out_w.pop()
            txt = re.sub(r"[.,;:?!]+$", "", " ".join(out_w)).strip(" \"'“”")
            if " " not in txt:
                return None
        return txt[:30] if len(txt) >= 3 else None

    def _flags(self):
        for uid, (end, words, wt) in sorted(self.arrow_waits.items(), key=lambda x: self.order[x[0]]):
            t = self.plan[uid]["t"]
            if t - wt <= 0.35:
                continue
            et = (self.by[end].get("text") or "").strip()
            label = f"{end} \"{et[:40]}\"" if et else end
            self.flags.append(f"arrow waits for {label} (anchor '{words}' at {wt:.2f} s, lands at {t:.2f} s)")
            if t - wt > 2.0:
                self.report.append(f"{uid}: arrow lands {t - wt:.1f} s after its anchor '{words}' ({wt:.2f} s) because "
                                   f"{label} only lands at {self.plan[end]['t']:.2f} s (never before both ends)")
        for f in (self.brief or {}).get("flags") or []:
            self.flags.append(f"brief: {f}")
        for k, role in ((self.brief or {}).get("numbers_inferred") or {}).items():
            self.flags.append(f"role inferred: {k} (treated as {role})")
        spoken = [t for t in self.S if t["v"] is not None]
        seen = set()
        for key, nt, role in self._number_keys():
            if role != "money" or (key, nt["k"]) in seen:
                continue
            seen.add((key, nt["k"]))
            hold = self._holders(nt)
            if hold and all(u["id"] in self.context_ids for u in hold):
                continue                      # listed in the structure step: context, not a claim made here
            def said_as(s):
                if abs(abs(s["v"]) - abs(nt["v"])) < 1e-6 or tok_eq(s, nt):
                    return True
                # spoken shorthand: "three" for $3,000, "fifty" for $50,000
                return s["v"] and any(abs(abs(s["v"]) * m - abs(nt["v"])) < 1e-6 for m in (1000, 1_000_000))
            if not any(said_as(s) for s in spoken):
                said = ", ".join(dict.fromkeys(self.wtxt([k]) for k, s in enumerate(self.S) if s["v"] is not None
                                               and not (s.get("word") and abs(s["v"]) <= 2))) or "no numbers"
                self.flags.append(f"copy '{key}' is on the board but no spoken number in this board's window matches it "
                                  f"(numbers the presenter says here: {said[:120]})")

    def _emit(self) -> dict:
        cues = []
        for u in self.U:
            p = self.plan.get(u["id"])
            if not p:
                continue
            c = {"id": u["id"], "move": p["move"], "t": p["t"] if p["move"] not in ("label", "hide") else 0.0,
                 "why": p["why"], "bbox": u["bbox"], "kind": u["kind"]}
            if p.get("word"):
                c["word"] = p["word"]
            if u.get("text"):
                c["text"] = u["text"][:80]
            cues.append(c)
        cues += self.cues
        for k, n in enumerate(self.notes):
            c = {"id": f"n{k + 1}", "move": "note", "t": n["t"], "text": n["text"], "x": n["x"], "y": n["y"],
                 "size": n["size"], "style": n["style"], "until": n["until"], "why": n["why"], "bbox": n["bbox"],
                 "color": (NOTE_COLORS_DARK if self.dark else NOTE_COLORS)[n["style"]]}
            if n.get("word"):
                c["word"] = n["word"]
            cues.append(c)
        order = {"label": 0, "hide": 0}
        cues.sort(key=lambda c: (order.get(c["move"], 1), c["t"], self.order.get(c["id"], 999)))
        return {"n": self.n, "dur": self.dur, "start": round(self.start, 3), "fps": self.fps, "cues": cues,
                "flags": self.flags, "report": self.report}


def _split_parts(elem: str) -> list[str]:
    """'Kevin stick figure + "Kevin"' → parts on + , ; and 'with' outside quotes."""
    out, buf, q = [], [], None
    s = elem
    i = 0
    while i < len(s):
        ch = s[i]
        if q:
            buf.append(ch)
            if (q == '"' and ch == '"') or (q == "“" and ch in "”\""):
                q = None
            i += 1
            continue
        if ch in ('"', "“"):
            q = ch
            buf.append(ch)
            i += 1
            continue
        m = re.match(r"\s*(?:\+|,|;|&|\band\b|\bplus\b)\s*", s[i:])
        if m and m.group(0).strip() and (ch in "+,;&" or s[i:].lstrip().startswith(("and ", "plus "))):
            out.append("".join(buf))
            buf = []
            i += len(m.group(0))
            continue
        buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [p.strip() for p in out if p.strip()]


def _quoted(s: str) -> list[str]:
    return [m.group(1) or m.group(2) for m in re.finditer(r'"([^"]+)"|“([^”"]+)[”"]', s)]


def build_board(n, units, brief_board, words, start, end, fps) -> dict:
    """Cues for one board. words: [{w, t, e}] on the final timeline (seconds); start/end: the board's window."""
    return Board(n, units, brief_board, words, start, end, fps).run()


# ───────────────────────── scene writing ─────────────────────────
def scene_data(units_doc: dict, cues: dict) -> dict:
    """What the kit needs: the cues plus where each unit lives in the board DOM."""
    umap = {}
    for u in units_doc["units"]:
        umap[u["id"]] = {"path": u["path"], "rotation": u.get("rotation"), "kind": u["kind"]}
    return {"n": cues["n"], "dur": cues["dur"], "fps": cues["fps"], "cues": cues["cues"], "units": umap}


def write_scene(units_doc: dict, cues: dict, path) -> Path:
    import units as units_mod
    board = units_mod.read_board(units_doc["path"])
    tpl = (SKILL / "assets" / "player.html").read_text(encoding="utf-8")
    gsap = (SKILL / "assets" / "gsap.min.js").read_text(encoding="utf-8")
    kit = (SKILL / "assets" / "kit.js").read_text(encoding="utf-8")
    data = json.dumps(scene_data(units_doc, cues), ensure_ascii=False, separators=(",", ":"))

    def js_safe(s: str) -> str:
        return s.replace("</script", "<\\/script").replace("<!--", "<\\!--")
    vals = {"TITLE": H.escape(f"{cues['n']:02d} · {board['title']} · board-sync"),
            "HEAD": "\n".join(board["links"] + board["styles"]),
            "BG": board["bg"], "ROOT": board["root"], "GSAP": js_safe(gsap), "KIT": js_safe(kit),
            "CUES": js_safe(data)}
    out = re.sub(r"@@(TITLE|HEAD|BG|ROOT|GSAP|KIT|CUES)@@", lambda m: vals[m.group(1)], tpl)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(out, encoding="utf-8")
    return path


# ───────────────────────── stage entry ─────────────────────────
def _get(ctx, name, default=None):
    if isinstance(ctx, dict):
        return ctx.get(name, default)
    return getattr(ctx, name, default)


def _manifest_lines(item: dict, cues: dict) -> list[str]:
    L = [f"### Board {cues['n']:02d} · {item.get('title', '')}  ({item.get('file', '')})",
         f"window {cues['start']:.2f} → {cues['start'] + cues['dur']:.2f} s ({cues['dur']:.2f} s)", "",
         "| t (board) | t (timeline) | move | element | why |", "|---:|---:|---|---|---|"]
    for c in cues["cues"]:
        el = c.get("text") or c.get("target") or ""
        el = (c["id"] + (" " + json.dumps(el[:50], ensure_ascii=False) if el else "")).replace("|", "/")
        L.append(f"| {c['t']:.2f} | {cues['start'] + c['t']:.2f} | {c['move']} | {el} | {c['why'].replace('|', '/')} |")
    for f in cues["flags"]:
        L.append(f"- FLAG: {f}")
    for r in cues["report"]:
        L.append(f"- note: {r}")
    for p in cues.get("proposals", []):
        L.append(f"- PROPOSE: {p}")
    L.append("")
    return L


def run(ctx) -> dict:
    out = Path(_get(ctx, "out"))
    wpath = out / "windows.json"
    if not wpath.is_file():
        raise SystemExit("choreo: windows.json is missing in the output folder; run the windows stage first.")
    windows = common.read_json(wpath)
    fps = windows.get("fps") or _get(ctx, "fps") or "24000/1001"
    bpath = out / "brief.json"
    if not bpath.is_file():
        import brief as brief_mod
        brief_mod.run(ctx)
    brief = common.read_json(bpath)
    by_n = {b["n"]: b for b in brief.get("boards", [])}
    only = _get(ctx, "only")
    if isinstance(only, str):
        only = [int(x) for x in re.findall(r"\d+", only)]
    want = set(int(x) for x in only) if only else None
    items = [it for it in windows.get("items", []) if it.get("kind") == "board" and (want is None or it["n"] in want)]
    missing = [it["n"] for it in items if not (out / "units" / f"{it['n']:02d}.json").is_file()]
    if missing:
        import units as units_mod
        units_mod.run(ctx, numbers=missing)
    (out / "cues").mkdir(parents=True, exist_ok=True)
    (out / "scenes").mkdir(parents=True, exist_ok=True)
    result = {}
    for it in items:
        n = it["n"]
        udoc = common.read_json(out / "units" / f"{n:02d}.json")
        bb = by_n.get(n)
        cues = build_board(n, udoc, bb, it.get("words", []), it["start"], it["end"], fps)
        if not bb and not brief.get("missing"):
            cues["report"].insert(0, "this board has no entry in brief.md")
        cues["proposals"] = [f"{u['start']:.2f}–{u['end']:.2f} s ({u['end'] - u['start']:.1f} s of speech with no script line): "
                             f"propose a new board for: \"{u.get('text', '')[:300]}\"" for u in it.get("uncovered", [])
                             if u.get("end", 0) - u.get("start", 0) > 15]
        common.write_json(out / "cues" / f"{n:02d}.cues.json", cues)
        write_scene(udoc, cues, out / "scenes" / f"{n:02d}.html")
        nn = sum(1 for c in cues["cues"] if c["move"] == "note")
        ns = sum(1 for c in cues["cues"] if c["move"] == "stamp")
        common.log(f"choreo: board {n:02d}: {len(cues['cues'])} cues ({nn} notes, {ns} stamps), "
                   f"{len(cues['flags'])} flags, {len(cues['report'])} report lines")
        result[n] = cues
    write_manifest(out, windows, fps)
    return result


def write_manifest(out: Path, windows: dict, fps) -> Path:
    """sync-manifest.md: the choreo section (every board with cues in out/cues) between its markers; whatever other
    stages wrote outside the markers is kept as it is."""
    START, END = "<!-- choreo:start -->", "<!-- choreo:end -->"
    items = {it["n"]: it for it in windows.get("items", []) if it.get("kind") == "board"}
    lines = [START, "## Choreography (board-sync choreo)", "",
             f"timing: {windows.get('timing_source', 'words.tsv')} · fps {fps} · times in seconds", ""]
    for cp in sorted((out / "cues").glob("*.cues.json")):
        try:
            cues = common.read_json(cp)
        except Exception:  # noqa: BLE001
            continue
        lines += _manifest_lines(items.get(cues.get("n"), {}), cues)
    lines.append(END)
    block = "\n".join(lines)
    path = out / "sync-manifest.md"
    old = path.read_text(encoding="utf-8") if path.is_file() else "# Sync manifest\n\n"
    if START in old and END in old:
        a, b = old.index(START), old.index(END) + len(END)
        new = old[:a] + block + old[b:]
    else:
        new = old.rstrip("\n") + "\n\n" + block + "\n"
    path.write_text(new, encoding="utf-8")
    return path
