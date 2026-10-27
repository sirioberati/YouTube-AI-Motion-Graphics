#!/usr/bin/env python3
"""Auto-choreograph a Design-Component deck card on the spoken words.

  deck_auto.py <card.html> --id c07 --vo vo.json --n 7 --out-scene compositions/c07.html --out-root roots/c07.html
               [--assets assets/deck] [--fonts-css assets/deck/fonts.css] [--override choreo/c07.js] [--sfx]

What it does
  - keeps the card's layout and look (white paper, dot grid, fonts); drops its Motion script and the
    <sc-if camGuide> talking-head guide; strips inline transforms (GSAP owns them)
  - reveal units = the header label, the headline, every direct child of .m-fit, plus the deck's own
    build elements inside them (.m-draw .m-hand .m-type .m-pop .m-grow .m-growx)
  - each unit is anchored to the first distinctive word of its own text in the card's VO words (monotonic
    search, numbers matched both ways); units without text or without a match cascade 0.12 s after the
    previous one; the deck's m-at-N delays are honoured relative to their group; min gap 0.1 s
  - moves: label → rise · headline → rise + highlight stamp on its word · box/text → rise ·
    .m-draw → stroke draw · .m-hand → write-on · .m-type → wipe · .m-pop → pop · .m-grow(x) → grow
  - slow push-in on the card, one soft SFX per typed line / pop / write (with --sfx, in the root)
  - --override appends your JS after the generated choreography (same globals: tl, SID, DUR, $, $$, DK, BK)

Outputs: a <template> sub-composition (for the master index) and a standalone root page (for per-card renders).
"""
import argparse
import html as H
import json
import re
import sys
from difflib import SequenceMatcher

TAG = re.compile(r"<(/?)([a-zA-Z][\w:-]*)([^>]*?)(/?)>", re.S)
VOID = {"img", "br", "hr", "input", "meta", "link", "source", "wbr", "area", "col", "embed", "track"}
NUM = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
       "10": "ten", "11": "eleven", "12": "twelve", "13": "thirteen", "14": "fourteen", "15": "fifteen", "20": "twenty",
       "30": "thirty", "32": "thirty-two", "35": "thirty-five", "40": "forty", "50": "fifty", "60": "sixty",
       "100": "hundred", "150": "150", "240": "240", "500": "five", "720": "720", "1080": "1080", "2000": "two"}
STOP = set("the a an of to in on and or for with at by is are was it its this that these those as from your you we i my our me he she they them his her their be been".split())


# ───────────────────────── markup walking ─────────────────────────
def element_span(s, open_start):
    """(open_end, close_start, close_end) of the element whose open tag starts at open_start."""
    depth = 0
    for m in TAG.finditer(s, open_start):
        closing, name, selfc = m.group(1), m.group(2).lower(), m.group(4)
        if not closing:
            if name in VOID or selfc:
                if depth == 0:
                    return m.end(), m.end(), m.end()
                continue
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return None, m.start(), m.end()
    raise SystemExit("unbalanced markup")


def children(s, open_start):
    """direct children open-tag starts of the element at open_start"""
    oe, cs, ce = element_span(s, open_start)
    depth = 0
    kids = []
    for m in TAG.finditer(s, open_start):
        if m.start() >= cs:
            break
        closing, name, selfc = m.group(1), m.group(2).lower(), m.group(4)
        if not closing:
            if depth == 1:
                kids.append(m.start())
            if not (name in VOID or selfc):
                depth += 1
        else:
            depth -= 1
    return kids


def attrs_of(s, open_start):
    m = TAG.match(s, open_start)
    return m.group(2).lower(), m.group(3)


def cls_of(attrs):
    m = re.search(r'class="([^"]*)"', attrs)
    return m.group(1).split() if m else []


def style_of(attrs):
    m = re.search(r'style="([^"]*)"', attrs)
    return m.group(1) if m else ""


def px(style, key):
    m = re.search(key + r":\s*(-?[\d.]+)px", style)
    return float(m.group(1)) if m else None


def inner_text(s, open_start):
    oe, cs, ce = element_span(s, open_start)
    m = TAG.match(s, open_start)
    raw = s[m.end():cs]
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S)
    tx = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", H.unescape(tx)).strip()


def descendants_with_m(s, open_start):
    """build elements (.m-*) strictly inside the element, in DOM order (open-tag starts)"""
    oe, cs, ce = element_span(s, open_start)
    m0 = TAG.match(s, open_start)
    out = []
    for m in TAG.finditer(s, m0.end()):
        if m.start() >= cs:
            break
        if m.group(1):
            continue
        cl = cls_of(m.group(3))
        if any(c in ("m-draw", "m-hand", "m-type", "m-pop", "m-grow", "m-growx") for c in cl):
            out.append(m.start())
    return out


# ───────────────────────── word anchoring ─────────────────────────
def norm(t):
    t = t.lower()
    t = re.sub(r"[“”\"'’‘(),.!?:;…·]+", "", t)
    t = t.replace("$", "").replace("%", " percent").replace("≈", "").replace("~", "")
    t = t.strip("-—– ")
    return NUM.get(t, t)


def key_tokens(text):
    toks = []
    for raw in text.split():
        n = norm(raw)
        if not n:
            continue
        for p in n.split():
            if p in STOP or len(p) < 3 and not p.isdigit():
                continue
            toks.append(p)
    return toks


def same(w, k):
    return w == k or (len(k) >= 5 and len(w) >= 5 and SequenceMatcher(None, w, k).ratio() >= 0.86)


def find_anchor(vo, cursor, toks, window=400, soft=False):
    """VO word index for the unit: the first occurrence at/after the cursor of a *strong* key token
    (a number, or ≥5 letters said at most twice in the card). Weak matches ('price', 'list') cascade instead."""
    if not toks:
        return None
    normed = [norm(w["w"]) for w in vo]
    strong = []
    for k in toks[:6]:
        f = sum(1 for w in normed if same(w, k))
        if f == 0:
            continue
        if re.search(r"\d", k) or (len(k) >= 5 and f <= 2):
            strong.append((f, toks.index(k), k))
    for f, _, k in sorted(strong):
        for i in range(cursor, len(vo)):
            if same(normed[i], k):
                return i
    return None


def find_phrase(vo, phrase):
    """index of the first word of a phrase ('double', 'half a million', 'twenty percent') in the VO words"""
    toks = [norm(t) for t in phrase.split()]
    toks = [t for t in toks if t]
    normed = [norm(w["w"]) for w in vo]
    for i in range(len(vo)):
        if all(i + j < len(vo) and same(normed[i + j], toks[j]) for j in range(len(toks))):
            return i
    return None


# ───────────────────────── main ─────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card")
    ap.add_argument("--id", required=True)
    ap.add_argument("--vo", required=True)
    ap.add_argument("--n", type=int, required=True, help="card number in vo.json")
    ap.add_argument("--out-scene", required=True)
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--fonts-css", default="assets/deck/fonts.css")
    ap.add_argument("--override", default=None)
    ap.add_argument("--sfx", action="store_true")
    ap.add_argument("--min-gap", type=float, default=0.1)
    ap.add_argument("--anchors", default=None, help="JSON {unit text prefix | id: word phrase | seconds | '+0.4' | 'with:<text prefix>' | 'hide'}")
    ap.add_argument("--manifest", action="store_true")
    ap.add_argument("--no-fillers", action="store_true", help="skip the dead-air notes and second-mention pulses")
    ap.add_argument("--camera", action="store_true", help="allow camera moves (slow push-in, 1.08 leans toward stickers). Off by default: zooms were rejected in review")
    ap.add_argument("--gap", type=float, default=2.2, help="a silence between reveals longer than this gets a note")
    a = ap.parse_args()

    vo = json.load(open(a.vo, encoding="utf-8"))
    card = next(c for c in vo["cards"] if c["n"] == a.n)
    T0 = card["start"]
    DUR = round(card["end"] - card["start"], 3)
    words = [{"w": w["w"], "t": round(w["t"] - T0, 3)} for w in card["words"]]

    s = open(a.card, encoding="utf-8").read()
    r = s.find('<div class="m-root')
    if r < 0:
        sys.exit("no .m-root")
    rm = TAG.match(s, r)
    root_style = style_of(rm.group(3))
    oe, cs, ce = element_span(s, r)

    # ── collect units ──
    units = []  # dict(start, kind, cls, text, delay_ms, id)
    uid = [0]

    def new_id():
        uid[0] += 1
        return f"{a.id}-u{uid[0]}"

    kids = children(s, r)
    fit_start = None
    for k in kids:
        name, attrs = attrs_of(s, k)
        cl = cls_of(attrs)
        if name == "sc-if":
            continue
        if "m-fit" in cl:
            fit_start = k
            continue
        txt = inner_text(s, k)
        kind = "headline" if "font-size: 7" in style_of(attrs) or len(txt) > 24 else "label"
        units.append({"start": k, "kind": kind, "cls": cl, "text": txt, "style": style_of(attrs)})
    if fit_start is not None:
        for k in children(s, fit_start):
            name, attrs = attrs_of(s, k)
            cl = cls_of(attrs)
            st = style_of(attrs)
            txt = inner_text(s, k)
            units.append({"start": k, "kind": "unit", "cls": cl, "text": txt, "style": st, "tag": name})
            for d in descendants_with_m(s, k):
                dn, dattrs = attrs_of(s, d)
                units.append({"start": d, "kind": "sub", "cls": cls_of(dattrs), "text": inner_text(s, d), "style": style_of(dattrs), "tag": dn, "parent": k})
    units.sort(key=lambda u: u["start"])
    for u in units:
        u["id"] = new_id()

    # price / number elements at any depth inside .m-fit: the camera punches into these when they are said
    PRICE_RE = re.compile(r"^[~≈−\-+]?\$?\d[\d,.]*\s?\d*\s?(%|K|M|k|p)?$")
    prices = []
    if fit_start is not None:
        f_oe, f_cs, f_ce = element_span(s, fit_start)
        fm = TAG.match(s, fit_start)
        unit_starts = {u["start"] for u in units}
        for m in TAG.finditer(s, fm.end()):
            if m.start() >= f_cs:
                break
            if m.group(1) or m.group(2).lower() in VOID or m.group(4):
                continue
            txt = inner_text(s, m.start())
            toks = txt.split()
            last = toks[-1] if toks else ""
            is_line = "m-type" in cls_of(m.group(3))
            pure = 1 <= len(txt) <= 9 and PRICE_RE.match(txt) and re.search(r"\d", txt)
            tail = (len(toks) <= 3 or is_line) and PRICE_RE.match(last or "x") and re.search(r"\d", last) and "?" not in last
            if pure or tail:
                wrap_at = None
                if not pure:
                    txt = last
                    oe2, cs2, ce2 = element_span(s, m.start())
                    inner_start = TAG.match(s, m.start()).end()
                    # last occurrence of the price token as text inside the element (not inside a tag)
                    pos = s.rfind(txt, inner_start, cs2)
                    while pos > 0 and s.rfind("<", inner_start, pos) > s.rfind(">", inner_start, pos):
                        pos = s.rfind(txt, inner_start, pos)
                    if pos < 0:
                        continue
                    wrap_at = pos
                # skip wrappers whose only content is a single child with the same text (keep the innermost)
                kids = children(s, m.start())
                if len(kids) == 1 and inner_text(s, kids[0]) == txt:
                    continue
                prices.append({"start": m.start(), "text": txt, "wrap_at": wrap_at, "unit_start": max([u["start"] for u in units if u["start"] <= m.start()] or [None])})
        for pr in prices:
            if pr["wrap_at"] is None:
                pr["id"] = next((u["id"] for u in units if u["start"] == pr["start"]), None) or f"{a.id}-p{len([x for x in prices if x is not pr and x.get('id')]) + 1}"
            else:
                pr["id"] = f"{a.id}-p{len([x for x in prices if x is not pr and x.get('id')]) + 1}"

    # ── inject ids (walk backwards so offsets hold) ──
    body = s[rm.end():cs]
    base = rm.end()
    todo = [{"start": u["start"], "id": u["id"], "cls": u["cls"], "tag": u.get("tag")} for u in units]
    todo += [{"start": pr["start"], "id": pr["id"], "cls": [], "tag": None} for pr in prices if pr["wrap_at"] is None and pr["start"] not in {u["start"] for u in units}]
    todo += [{"start": pr["wrap_at"], "id": pr["id"], "wrap": pr["text"]} for pr in prices if pr["wrap_at"] is not None]
    for u in sorted(todo, key=lambda u: -u["start"]):
        if u.get("wrap"):
            pos = u["start"] - base
            body = body[:pos] + f'<span id="{u["id"]}" style="display:inline-block">' + u["wrap"] + "</span>" + body[pos + len(u["wrap"]):]
            continue
        m = TAG.match(s, u["start"])
        tag = m.group(0)
        extra = f' id="{u["id"]}"'
        if any(c in ("m-draw", "m-skip") for c in u["cls"]) or u.get("tag") == "svg":
            extra += " data-layout-ignore aria-hidden=\"true\""
        pos = u["start"] - base
        tag_new = tag[:-2] + extra + "/>" if tag.endswith("/>") else tag[:-1] + extra + ">"
        body = body[:pos] + tag_new + body[pos + len(tag):]
    # drop the camera guide
    body = re.sub(r"<sc-if\b.*?</sc-if>", "", body, flags=re.S)
    # transforms → GSAP
    body = re.sub(r"(?<![\w-])transform\s*:\s*[^;\"]*;?", "", body)

    # ── classify + move per unit ──
    def move_of(u):
        cl = u["cls"]
        if "m-draw" in cl:
            return "draw"
        if "m-hand" in cl:
            return "write"
        if "m-type" in cl:
            return "wipe"
        if "m-pop" in cl:
            # a row inside a list (no position of its own) must not scale out of line: it appears instead of popping
            return "rise" if px(u["style"], "left") is None else "pop"
        if "m-growx" in cl:
            return "growx"
        if "m-grow" in cl:
            return "grow"
        if u["kind"] == "headline":
            return "headline"
        if u["kind"] == "label":
            return "label"
        if u.get("tag") == "svg":
            return "draw"
        return "rise"

    for u in units:
        u["move"] = move_of(u)
        u["delay"] = next((int(c[5:]) for c in u["cls"] if c.startswith("m-at-")), 0)
        top = px(u["style"], "top")
        u["meta"] = u["kind"] == "unit" and top is not None and top >= 985 and len(u["text"]) < 40

    # ── anchor to words ──
    overrides = json.load(open(a.anchors, encoding="utf-8")) if a.anchors else {}
    if "_gap" in overrides:
        a.min_gap = float(overrides.pop("_gap"))
    cascade_only = overrides.pop("_default", None) == "cascade"   # ladder revisits: no word matching, just build fast
    notes_off = overrides.pop("_notes", None) == "off"
    hand_notes = overrides.pop("_add", []) or []
    mute_notes = [m.lower() for m in (overrides.pop("_mute", []) or [])]   # auto notes containing one of these phrases are skipped            # [{"text","at": phrase|seconds,"x","y","size"(96),"hold"(s)}]
    stamps_off = overrides.pop("_stamps", None) == "off"      # per-card: no price stamps (numbers said in another sense)
    pulses_off = overrides.pop("_pulses", None) == "off"
    open_off = overrides.pop("_open", None) is False

    def override_for(u):
        for key, val in overrides.items():
            if key == u["id"] or (u["text"] and u["text"].lower().startswith(key.lower())):
                return val
        return None

    cursor = 0
    prev_t = 0.0
    last_group_t = 0.0
    for u in units:
        ov = override_for(u)
        if ov == "hide":
            u["move"] = "hidden"
            u["t"] = 0.0
            continue
        if u["move"] == "label":
            u["t"] = 0.0
            continue
        if u["move"] == "headline":
            u["t"] = 0.08
            toks = key_tokens(u["text"])
            # the highlighted words (span with the marker gradient) stamp on their word
            u["hl"] = None
            m = re.search(r"<span[^>]*background:\s*linear-gradient[^>]*>(.*?)</span>", s[u["start"]:element_span(s, u["start"])[1]], flags=re.S)
            if m:
                hl = re.sub(r"<[^>]+>", " ", H.unescape(m.group(1))).strip()
                idx = find_anchor(words, 0, key_tokens(hl), window=60)
                u["hl"] = words[idx]["t"] if idx is not None else None
            prev_t = 0.3
            continue
        if u["meta"]:
            u["t"] = 0.25
            continue
        t = None
        if isinstance(ov, (int, float)):
            t = float(ov)
            u["anchor"] = f"@{ov}"
        elif isinstance(ov, str) and ov.startswith("+"):
            t = prev_t + float(ov)
            u["anchor"] = ov
            u["delta"] = float(ov)
        elif isinstance(ov, str) and ov.startswith("with:"):
            u["with"] = ov[5:]
            u["anchor"] = ov
            t = prev_t + 0.02
        elif isinstance(ov, str):
            idx = find_phrase(words, ov)
            if idx is None:
                print(f"warning: override phrase {ov!r} not in card {a.n} VO", file=sys.stderr)
            else:
                t = words[idx]["t"] + 0.05
                cursor = max(cursor, idx + 1)
                u["anchor"] = "=" + ov
                last_group_t = t
        if t is None:
            toks = key_tokens(u["text"])
            idx = find_anchor(words, cursor, toks) if (toks and not cascade_only) else None
            if idx is not None:
                t = words[idx]["t"] + 0.05
                cursor = max(cursor, idx + 1) if idx >= cursor else cursor
                u["anchor"] = words[idx]["w"]
                last_group_t = t
            else:
                # m-at delays sequence decoratives after the thing they decorate
                t = (last_group_t + u["delay"] / 1000.0 * 0.7) if u["delay"] else prev_t + 0.12
                u["anchor"] = "~"
        t = max(t, 0.3)
        t = min(t, max(0.3, DUR - 0.7))
        u["t"] = round(t, 3)
        prev_t = u["t"]

    # 'with:' groups and containment: a textless box appears just before the first text it contains
    by_text = {u["text"].lower(): u for u in units if u.get("text")}
    for u in units:
        if u.get("with"):
            tgt = next((v for k, v in by_text.items() if k.startswith(u["with"].lower())), None)
            if tgt:
                u["t"] = tgt["t"]
    # re-apply "+x" chains in DOM order now that every with: target is resolved
    prev = None
    for u in units:
        if u["move"] in ("label", "headline", "hidden") or u["meta"]:
            continue
        if u.get("delta") is not None and prev is not None:
            u["t"] = round(min(max(0.3, prev["t"] + u["delta"]), max(0.3, DUR - 0.7)), 3)
        prev = u
    for u in units:
        if u["kind"] == "unit" and not u["text"] and u["move"] == "rise" and override_for(u) is None:
            l, tp, w, h = px(u["style"], "left"), px(u["style"], "top"), px(u["style"], "width"), px(u["style"], "height")
            if None in (l, tp, w, h):
                continue
            inside = [v for v in units if v is not u and v.get("text") and v["kind"] == "unit" and px(v["style"], "left") is not None
                      and l <= px(v["style"], "left") <= l + w and tp <= (px(v["style"], "top") or -1) <= tp + h]
            if inside:
                u["t"] = round(max(0.3, min(v["t"] for v in inside) - 0.15), 3)
                u["anchor"] = "⊃"
    # a textless box/outline/icon that only cascaded leads its label: the next text unit within 3 DOM steps that has a real anchor
    body_units = [u for u in units if u["move"] not in ("label", "headline", "hidden") and not u["meta"]]
    for i, u in enumerate(body_units):
        if u.get("text") or u.get("anchor") not in ("~", "⊃", None):
            continue
        for k in range(1, 4):
            if i + k >= len(body_units):
                break
            v = body_units[i + k]
            if v.get("text") and v.get("anchor") not in ("~", None) and not str(v.get("anchor", "")).startswith("+"):
                if v["t"] > u["t"] + 0.5:
                    u["t"] = round(max(0.3, v["t"] - 0.1 * k - 0.15), 3)
                    u["anchor"] = "→" + v["text"][:12]
                break
            if v.get("text"):
                break
    # opening fill: a card never starts empty — if nothing lands in the first 1.2 s, the textless structure
    # (boxes, outlines, icons, rails, panels) cascades in from 0.45 s; labels and numbers still wait for their words
    body_units = [u for u in units if u["move"] not in ("label", "headline", "hidden") and not u["meta"]]
    first_t = min([u["t"] for u in body_units], default=DUR)
    if first_t > 1.2 and not cascade_only and not open_off:
        t = 0.45
        for u in body_units:
            if u.get("text") or u["move"] in ("pop", "write", "wipe"):
                break            # the first labelled unit ends the opening structure
            if u["t"] <= 1.2:
                continue
            u["t"] = round(t, 3)
            u["anchor"] = "open"
            t += 0.28
            if t > 3.2:
                break
    first_now = min([u["t"] for u in body_units], default=DUR)
    if first_now > 2.0 and not cascade_only and not open_off and body_units:
        u0 = body_units[0]
        if u0["move"] in ("rise", "pop", "draw", "grow", "growx"):
            u0["t"] = 0.9
            u0["anchor"] = "open"
    # order by time (ties: DOM order), then enforce the minimum gap
    order = sorted([u for u in units if u["move"] not in ("label", "headline", "hidden") and not u["meta"]], key=lambda u: (u["t"], u["start"]))
    last = 0.0
    for u in order:
        if u["t"] < last + a.min_gap:
            u["t"] = round(last + a.min_gap, 3)
        last = u["t"]

    # ── fillers: a handwritten note for every stretch of dead air, a pulse when something on the card is said again ──
    notes, pulses = [], []
    if not a.no_fillers:
        card_tokens = set()
        for u in units:
            card_tokens.update(key_tokens(u.get("text", "")))
        normed = [norm(w["w"]) for w in words]
        freq = {}
        for w in normed:
            freq[w] = freq.get(w, 0) + 1
        NUMWORDS = {"double", "half", "million", "thousand", "third", "twice", "zero"}
        JUNK = {"because", "whether", "before", "after", "changes", "covers", "customer", "number", "people", "mostly", "thinking", "moment",
                "everything", "starting", "keeping", "copying", "always", "switch", "buying", "without", "whichever", "something", "somebody",
                "anything", "nothing", "together", "already", "another", "through", "between", "against", "instead", "especially", "obviously"}

        def is_num(i):
            w = words[i]["w"]
            return bool(re.search(r"\d", w)) or normed[i] in NUMWORDS

        LEAD = {"about", "half", "exactly", "nearly", "almost", "double", "over", "under", "roughly", "around", "every", "one", "no"}
        UNIT = {"%", "percent", "million", "thousand", "dollars", "hour", "-hour", "seconds", "sellers", "models", "clip", "clips", "prices", "versions",
                "a", "an", "to", "off", "under", "more", "less", "of", "in", "per", "on", "at"}

        def ends_sentence(k):
            return k >= 0 and k < len(words) and bool(re.search(r"[.?!]$", words[k]["w"]))

        def phrase_at(i):
            start = i
            if i > 0 and (normed[i - 1] in LEAD or words[i - 1]["w"].endswith("$")) and not ends_sentence(i - 1):
                start = i - 1
            end = i
            # extend forward through units/connectors up to 3 more words, never across a sentence end
            while end + 1 < len(words) and end - i < 3 and not ends_sentence(end):
                nx = normed[end + 1]
                if nx in UNIT or (end == i and nx and nx not in STOP) or (end > i and normed[end] in {"a", "an", "to", "of", "in", "per", "on"}):
                    end += 1
                else:
                    break
            toks = [words[k]["w"] for k in range(start, end + 1)]
            # cut at the first comma inside the phrase
            for k, tk in enumerate(toks[:-1]):
                if tk.endswith(","):
                    toks = toks[:k + 1]
                    break
            TRAIL = STOP | {"a", "an", "to", "of", "in", "per", "on", "more", "less", "like", "which", "because", "either", "so", "when", "if", "but", "and", "or"}
            while len(toks) > 1 and norm(toks[-1]) in TRAIL:
                toks.pop()
            txt = " ".join(toks)
            txt = re.sub(r"\s+%", "%", txt).replace(" ,", ",").replace(" -", "-").replace("$ ", "$")
            txt = re.sub(r"[.,;:?!]+$", "", txt).strip()
            if re.fullmatch(r"[\d.,]+", txt):  # a bare number says nothing
                return None
            if " " not in txt and not re.search(r"[$%\d]", txt):  # a lone plain word says nothing either
                return None
            return txt[:30] if len(txt) >= 3 else None

        # geometry: every unit's box with the time it appears; the talking-head slot and the headline band are always there
        FIXED = [(0, 40, 1920, 160)]
        tboxes = []
        for u in units:
            l, tp = px(u["style"], "left"), px(u["style"], "top")
            if l is None or tp is None or u["move"] == "hidden":
                continue
            w = px(u["style"], "width") or min(1000, 22 * len(u.get("text", "")) + 40)
            h = px(u["style"], "height") or 64
            tboxes.append((u.get("t", 0.0), (l, tp, w, h), u["kind"] == "unit" and not u["meta"]))
        BIG = [(96, 300, 1100, 170), (96, 540, 1100, 170), (700, 300, 1100, 170), (96, 760, 1100, 170), (1300, 300, 580, 170), (700, 540, 1100, 170), (96, 420, 1100, 170), (1300, 540, 580, 170)]
        MID = [(1300, 250, 560, 100), (1300, 400, 560, 100), (1300, 500, 560, 100), (96, 900, 900, 90), (720, 900, 900, 90), (1300, 900, 560, 90), (96, 230, 900, 90),
               (96, 420, 900, 90), (96, 600, 900, 90), (720, 600, 900, 90), (720, 420, 900, 90), (96, 780, 900, 90), (1300, 650, 560, 90), (1300, 780, 560, 90)]

        def free_at(rect, t0, t1):
            x, y, w, h = rect
            for (bl, bt, bw, bh) in FIXED + [b for (tb, b, _) in tboxes if tb <= t1 + 0.3]:
                if x < bl + bw and bl < x + w and y < bt + bh and bt < y + h:
                    return False
            return True

        def place(t0, t1, text):
            """(x, y, font) for a note shown from t0 to t1: big and central when the card is still empty"""
            coverage = sum(b[2] * b[3] for (tb, b, content) in tboxes if content and tb <= t0 + 0.3) / (1920 * 1080)
            if coverage < 0.15:
                for r in BIG:
                    if free_at(r, t0, t1):
                        return r[0], r[1], 130 if len(text) <= 16 else 96
            if coverage < 0.40:
                for r in BIG:
                    if free_at(r, t0, t1):
                        return r[0], r[1], 84 if len(text) <= 22 else 64
            for r in MID:
                if free_at(r, t0, t1):
                    return r[0], r[1], 54
            return None
        slot = True   # notes are placed one by one below

        # hand notes first: they take their slot, auto notes avoid them
        for hn in hand_notes:
            at = hn.get("at", 0)
            if isinstance(at, str):
                k = find_phrase(words, at)
                if k is None:
                    sys.stderr.write(f"warning: _add note {hn.get('text')!r}: phrase {at!r} not in card {a.n} VO\n")
                    continue
                t0 = round(words[k]["t"] + 0.05, 3)
            else:
                t0 = float(at)
            size = int(hn.get("size", 96))
            notes.append({"t": t0, "text": hn["text"], "id": f"{a.id}-n{len(notes) + 1}", "x": int(hn["x"]), "y": int(hn["y"]), "font": size,
                          "hold": hn.get("hold"), "hand": True, "style": hn.get("style", "hand"), "color": hn.get("color"), "rot": hn.get("rot")})
            tboxes.append((t0, (int(hn["x"]), int(hn["y"]), int(hn.get("w", min(1100, int(size * 0.55 * len(hn["text"]) + 40)))), int(size * 1.3)), False))
        events = sorted(set([0.3] + [u["t"] for u in units if u["move"] not in ("label", "hidden", "headline") and not u["meta"] and u.get("anchor") != "open"]
                            + [n["t"] for n in notes] + [DUR]))
        used = set()
        for g0, g1 in zip(events, events[1:]):
            if g1 - g0 < a.gap or slot is None or notes_off:
                continue
            w0 = g0 + (2.6 if any(abs(g0 - hn["t"]) < 0.01 for hn in notes if hn.get("hand")) else 0.0)
            while g1 - w0 >= a.gap and len(notes) < 16:
                cands = []
                lead = 0.6 if w0 <= 0.35 else 0.8
                for i, w in enumerate(words):
                    if not (w0 + lead <= w["t"] <= g1 - 0.5) or i in used:
                        continue
                    n = normed[i]
                    if not n or n in STOP or n == "fill" or n == "phil":
                        continue
                    raw = w["w"].lower()
                    junk = n in JUNK or any(raw.endswith(e) for e in ("n't", "'re", "'ve", "'ll", "'d", "'s"))
                    score = 3 if is_num(i) else (1 if (len(n) >= 5 and freq.get(n, 0) <= 2 and n not in card_tokens and not junk) else 0)
                    if score:
                        cands.append((-score, i))
                placed = False
                for _, i in sorted(cands):
                    txt = phrase_at(i)
                    if txt:
                        t0 = round(words[i]["t"] + 0.05, 3)
                        if any(m in txt.lower() for m in mute_notes) or any(hn["t"] - 2.6 < t0 < hn["t"] + 2.6 for hn in notes if hn.get("hand")):
                            continue
                        pos = place(t0, min(g1, t0 + 5.0), txt)
                        if pos is None:
                            continue
                        used.update(range(max(0, i - 1), i + 3))
                        notes.append({"t": t0, "text": txt, "id": f"{a.id}-n{len(notes) + 1}", "x": pos[0], "y": pos[1], "font": pos[2]})
                        w0 = t0 + 3.2
                        placed = True
                        break
                if not placed:
                    break
        notes.sort(key=lambda n: n["t"])
        for k, n in enumerate(notes):
            n["id"] = f"{a.id}-n{k + 1}"
        # pulses: a unit's strong token said again ≥ 2.5 s after its reveal (max 2 per unit, 6 per card)
        def money_ok(i):
            w = words[i]["w"]; nxt = normed[i + 1] if i + 1 < len(words) else ""; prev = normed[i - 1] if i > 0 else ""
            if not re.search(r"\d", w):
                return True
            ok = ("$" in w) or ("%" in w) or nxt in ("dollars", "dollar", "bucks", "percent", "%") or prev in (
                "at", "pay", "pays", "paying", "paid", "costs", "cost", "charges", "charge", "charged", "price", "sell", "sells", "selling",
                "buy", "buys", "keeps", "keep", "is", "about", "around", "than", "me", "you", "for", "list")
            if prev in ("of", "out") or nxt in ("different", "sellers", "prices", "versions", "companies", "models", "seconds", "minutes", "lines",
                                               "apps", "clips", "times", "out", "users", "videos", "ways", "things", "kinds", "of", "providers", "resellers", "receipts"):
                ok = False
            return ok
        for u in units:
            if pulses_off or u["move"] not in ("rise", "pop", "wipe", "write") or not u.get("text") or len(pulses) >= 6:
                continue
            toks = [k for k in key_tokens(u["text"])[:4] if re.search(r"\d", k) or (len(k) >= 6 and freq.get(k, 0) <= 3)]
            hits = [w["t"] for i, w in enumerate(words) if normed[i] in toks and w["t"] > u["t"] + 2.5 and money_ok(i)]
            for t in hits[:2]:
                pulses.append((u["id"], round(t + 0.03, 3)))

    # ── choreography JS ──
    js = []
    js.append(f'// {a.card.split("/")[-1]} · card {a.n:>2} · VO {T0:.2f} → {T0 + DUR:.2f} · auto-choreographed on the spoken words')
    js.append('const cam = "#" + SID + "-cam"; const zoomEl = "#" + SID + "-zoom";')
    ids_hidden = [u["id"] for u in units if u["move"] not in ("label",)]
    units_sorted = sorted(units, key=lambda u: (u.get("t", 0), u["start"]))
    js.append("DK.hide(" + json.dumps(["#" + i for i in ids_hidden]) + ");")
    for u in units:
        rot = re.search(r"rotate\((-?[\d.]+)deg\)", u["style"])
        if rot and u["move"] != "hidden":
            js.append(f'gsap.set("#{u["id"]}", {{ rotation: {rot.group(1)} }});')
    # baselines for transform moves (gsap.set, never tl.set at 0)
    for u in units:
        i = "#" + u["id"]
        if u["move"] == "grow":
            js.append(f'gsap.set("{i}", {{ transformOrigin: "50% 100%", scaleY: 0 }});')
        elif u["move"] == "growx":
            js.append(f'gsap.set("{i}", {{ transformOrigin: "0% 50%", scaleX: 0 }});')
    if a.camera:
        js.append(f'DK.push(tl, cam, 0, DUR, {{ to: {1.02 if DUR > 20 else 1.035} }});')
    for u in units_sorted:
        i = "#" + u["id"]
        t = u["t"]
        mv = u["move"]
        note = f'  // {u["anchor"] if u.get("anchor") else ""} {u["text"][:40]!r}' if u.get("text") else ""
        if mv == "hidden":
            continue
        if mv == "label":
            js.append(f'gsap.set("{i}", {{ opacity: 1 }});')
        elif mv == "headline":
            js.append(f'DK.rise(tl, "{i}", {t}, {{ y: 22, dur: 0.5 }});')
            if u.get("hl") is not None:
                js.append(f'$$("{i} span").forEach((sp) => {{ gsap.set(sp, {{ display: "inline-block", transformOrigin: "50% 60%" }}); tl.fromTo(sp, {{ scale: 1 }}, {{ scale: 1.07, rotation: -1.2, duration: 0.12, ease: "power2.out", immediateRender: false }}, {max(0.3, round(u["hl"], 3))}); tl.to(sp, {{ scale: 1, rotation: 0, duration: 0.3, ease: "back.out(2)" }}, {max(0.3, round(u["hl"], 3)) + 0.12}); }});')
        elif mv == "rise":
            js.append(f'DK.rise(tl, "{i}", {t}, {{ y: 14, dur: 0.4 }});{note}')
        elif mv == "draw":
            js.append(f'tl.set("{i}", {{ opacity: 1 }}, {t}); DK.draw(tl, "{i} path, {i} circle, {i} line, {i} polyline", {t}, {{ dur: 0.5 }});{note}')
        elif mv == "write":
            js.append(f'DK.write(tl, "{i}", {t}, {{ dur: 0.5 }});{note}')
        elif mv == "wipe":
            js.append(f'DK.wipe(tl, "{i}", {t}, {{ dur: 0.35 }});{note}')
        elif mv == "pop":
            js.append(f'DK.pop(tl, "{i}", {t}, {{ from: 0.82, dur: 0.38 }});{note}')
        elif mv == "grow":
            js.append(f'tl.set("{i}", {{ opacity: 1 }}, {t}); tl.to("{i}", {{ scaleY: 1, duration: 0.55, ease: "power3.out" }}, {t});{note}')
        elif mv == "growx":
            js.append(f'tl.set("{i}", {{ opacity: 1 }}, {t}); tl.to("{i}", {{ scaleX: 1, duration: 0.55, ease: "power3.out" }}, {t});{note}')
    note_html = ""
    if notes:
        STYLES = {
            "hand":    "font-family:'Instrument Serif',serif;font-style:italic;font-weight:700;line-height:1;color:{c};white-space:nowrap;transform-origin:0 100%",
            "sticker": "font-family:'Inter',sans-serif;font-weight:700;line-height:1;letter-spacing:-0.02em;color:#1F2937;background:{c};padding:0.32em 0.5em 0.28em;border-radius:0.22em;box-shadow:0 10px 24px rgba(0,0,0,0.14);white-space:nowrap;transform-origin:50% 50%",
            "tag":     "font-family:'JetBrains Mono',monospace;font-weight:600;line-height:1;letter-spacing:0.08em;text-transform:uppercase;color:#1F2937;background:{c};padding:0.45em 0.8em 0.4em;border-radius:999px;white-space:nowrap;transform-origin:50% 50%",
            "mono":    "font-family:'JetBrains Mono',monospace;font-weight:500;line-height:1.3;color:{c};white-space:nowrap;transform-origin:0 50%",
            "stamp":   "font-family:'Inter',sans-serif;font-weight:700;line-height:1;letter-spacing:0.04em;text-transform:uppercase;color:{c};border:0.09em solid {c};padding:0.18em 0.3em 0.12em;border-radius:0.12em;white-space:nowrap;transform-origin:50% 50%",
        }
        DEFAULT_COLOR = {"hand": "#2563EB", "sticker": "#DBEAFE", "tag": "#CDEFC4", "mono": "#1F2937", "stamp": "#E8552B"}
        for k, n in enumerate(notes):
            st = n.get("style") or "hand"
            if st not in STYLES:
                st = "hand"
            css = STYLES[st].format(c=n.get("color") or DEFAULT_COLOR[st])
            note_html += ('<div id="' + n["id"] + '" class="hf-note" data-layout-allow-overlap style="position:absolute;left:' + str(n["x"]) + 'px;top:' + str(n["y"]) + 'px;'
                          "font-size:" + str(n["font"]) + "px;" + css + '">' + H.escape(n["text"]).replace("\\n", "<br>").replace("\n", "<br>") + "</div>")
        js.append("// fillers · dead-air notes (one slot, each fades when the next lands) and second-mention pulses")
        js.append("DK.hide(" + json.dumps(["#" + n["id"] for n in notes]) + ");")
        def rect_of(n):
            return (n["x"], n["y"], len(n["text"]) * 0.5 * n["font"], n["font"] * 1.1)
        def overlap(r1, r2):
            return r1[0] < r2[0] + r2[2] and r2[0] < r1[0] + r1[2] and r1[1] < r2[1] + r2[3] and r2[1] < r1[1] + r1[3]
        for k, n in enumerate(notes):
            st = n.get("style") or "hand"
            rot = n.get("rot") if n.get("rot") is not None else (-2.5 if st == "hand" else (-4 if st in ("sticker", "stamp") else 0))
            js.append('gsap.set("#' + n["id"] + '", { rotation: ' + str(rot) + ' });')
            if st == "hand":
                js.append('DK.write(tl, "#' + n["id"] + '", ' + str(n["t"]) + ', { dur: ' + ("0.6" if n["font"] > 60 else "0.45") + ' });  // ' + repr(n["text"]))
                if n["font"] > 60:
                    js.append('tl.fromTo("#' + n["id"] + '", { scale: 0.92 }, { scale: 1, duration: 0.7, ease: "back.out(1.6)", immediateRender: false }, ' + str(n["t"]) + ');')
            elif st == "mono":
                js.append('DK.wipe(tl, "#' + n["id"] + '", ' + str(n["t"]) + ', { dur: 0.35 });  // ' + repr(n["text"]))
            else:
                js.append('DK.pop(tl, "#' + n["id"] + '", ' + str(n["t"]) + ', { from: 0.6, dur: 0.42 });  // ' + repr(n["text"]))
            hold = n.get("hold")
            if n.get("hand"):
                ends = [] if (hold is not None and float(hold) < 0) else [n["t"] + (float(hold) if hold else 9.0)]
                for m in notes[k + 1:]:
                    if overlap(rect_of(n), rect_of(m)):
                        ends.append(m["t"] - 0.25)
                        break
            else:
                ends = [n["t"] + 7.0]
                if k + 1 < len(notes):
                    ends.append(notes[k + 1]["t"] - 0.25)
            nw, nh = len(n["text"]) * 0.5 * n["font"], n["font"] * 1.1
            for (tb, (bl, bt, bw, bh), _) in tboxes:
                if tb > n["t"] + 0.3 and n["x"] < bl + bw and bl < n["x"] + nw and n["y"] < bt + bh and bt < n["y"] + nh:
                    ends.append(tb - 0.2)
            if not ends:
                continue
            t_end = min(ends)
            if t_end < DUR - 0.3:
                js.append('tl.to("#' + n["id"] + '", { opacity: 0, duration: 0.2, ease: "power1.in" }, ' + str(round(max(n["t"] + 0.8, t_end), 3)) + ');')
    # price zooms: the number on the card is said → punch into it (1.4×), stamp it, come back or chain to the next
    pzooms = []
    if not a.no_fillers and prices and not stamps_off:
        digits_vo = []
        for i, w in enumerate(words):
            d = re.sub(r"\D", "", w["w"])
            if d and i + 1 < len(words) and re.match(r"^,?\d{3}$", words[i + 1]["w"].strip()):
                d += re.sub(r"\D", "", words[i + 1]["w"])
            if norm(w["w"]) == "half" and i + 2 < len(words) and norm(words[i + 2]["w"]) == "million":
                d = "500"
            digits_vo.append(d)
        unit_t = {u["start"]: u.get("t", 0.0) for u in units}
        card_pct = {re.sub(r"\D", "", pr["text"]) for pr in prices if "%" in pr["text"]}
        card_usd = {re.sub(r"\D", "", pr["text"]) for pr in prices if "$" in pr["text"]}
        for pr in prices:
            d = re.sub(r"\D", "", re.sub(r"\.00\b", "", pr["text"]))
            if d in ("500000", "500"):
                d = "500"
            if not d:
                continue
            vis = unit_t.get(pr["unit_start"], 0.0) - 0.3
            hits = []
            for i, w in enumerate(words):
                if digits_vo[i] != d or w["t"] < vis:
                    continue
                nxt = norm(words[i + 1]["w"]) if i + 1 < len(words) else ""
                pct_next = nxt in ("percent", "%")
                if "%" in pr["text"] and not pct_next:
                    continue
                if "%" not in pr["text"] and d in card_pct and pct_next:
                    continue
                if "$" in pr["text"]:
                    # a dollar price stamps only when the number is said as money: "$13", "13 dollars", "pay 13", never "5 out of 13" or "13 different prices"
                    prev = norm(words[i - 1]["w"]) if i > 0 else ""
                    money = ("$" in w["w"]) or nxt in ("dollars", "dollar", "bucks") or prev in (
                        "at", "pay", "pays", "paying", "paid", "costs", "cost", "charges", "charge", "charged", "price", "sell", "sells",
                        "selling", "buy", "buys", "keeps", "keep", "is", "about", "around", "than", "me", "you", "for", "costing", "list")
                    if prev in ("of", "out") or nxt in ("different", "sellers", "prices", "versions", "companies", "models", "seconds", "minutes",
                                                        "lines", "apps", "clips", "times", "out", "percent", "%", "users", "videos", "ways",
                                                        "things", "kinds", "of", "providers", "resellers", "receipts"):
                        money = False
                    if not money:
                        continue
                if not hits or w["t"] - hits[-1] >= 2.5:
                    hits.append(w["t"])
                if len(hits) >= 2:
                    break
            for t in hits:
                pzooms.append({"t": round(max(0.3, t), 3), "sel": "#" + pr["id"], "text": pr["text"], "Z": 1.5, "kind": "said"})
        pzooms.sort(key=lambda z: z["t"])
        kept = []
        for z in pzooms:
            if kept and z["t"] - kept[-1]["t"] < 0.9:
                continue
            if len(kept) >= 6:
                break
            kept.append(z)
        # reveal zooms: a price-bearing row lands → the camera leans into its number while the group fills in
        ev_all = sorted(set([u["t"] for u in units if u["move"] not in ("label", "hidden", "headline") and not u["meta"]] + [DUR]))
        seen_units = set()
        for pr in prices:
            us = pr["unit_start"]
            if us in seen_units or us not in unit_t:
                continue
            t0 = unit_t[us]
            nxt = next((t for t in ev_all if t > t0 + 0.5), DUR)
            if nxt - t0 < 0.8 or t0 < 0.4:
                continue
            if any(abs(z["t"] - t0) < 1.3 for z in kept):
                continue
            seen_units.add(us)
            kept.append({"t": round(t0 + 0.45, 3), "sel": "#" + pr["id"], "text": pr["text"], "Z": 1.3, "kind": "reveal", "cap": round(min(1.5, nxt - t0 - 0.8), 3)})
        kept.sort(key=lambda z: z["t"])
        pzooms = kept[:8]
        for k, z in enumerate(pzooms):
            nxt = pzooms[k + 1]["t"] if k + 1 < len(pzooms) else DUR
            z["hold"] = round(min(z.get("cap", 1.2), max(0.4, nxt - z["t"] - 0.8)), 3)
            z["ret"] = True
            if z["t"] + z["hold"] + 0.8 > DUR:
                z["hold"] = round(max(0.3, DUR - 0.9 - z["t"]), 3)
        if pzooms:
            js.append("// price stamps · the sticker itself slaps up when its number is said (or its row lands), holds, settles back")
            js.append('const stamp = (sel, t, hold, Z) => { const el = $(sel); if (!el) return; gsap.set(el, { transformOrigin: "50% 50%" });'
                      ' const rr = $("#root").getBoundingClientRect(); const big = el.getBoundingClientRect().height / (rr.width / 1920 || 1) > 70; if (big) Z = Math.min(Z, 1.22);'
                      ' tl.fromTo(el, { scale: 1, rotation: 0 }, { scale: Z, rotation: big ? -1.5 : -4, duration: 0.3, ease: "back.out(2.4)", immediateRender: false }, t);'
                      ' tl.to(el, { rotation: big ? 0.8 : 2, duration: 0.5, ease: "sine.inOut" }, t + 0.3);'
                      ' tl.to(el, { scale: 1, rotation: 0, duration: 0.4, ease: "power2.inOut" }, t + 0.3 + hold); };')
            for z in pzooms:
                js.append(f'stamp("{z["sel"]}", {z["t"]}, {z["hold"]}, {z["Z"]});  // {z["kind"]} {z["text"]!r}')

    # zooms: the camera pushes toward stickers, handwritten notes and the big numbers, holds a beat, eases back
    zooms = []
    if not a.no_fillers and a.camera:
        ev = sorted(set([u["t"] for u in units if u["move"] not in ("label", "hidden", "headline") and not u["meta"]] + [n["t"] for n in notes] + [DUR]))
        cands = [u for u in units_sorted if u["move"] in ("pop", "write") or (u["move"] == "rise" and u.get("text") and len(u["text"]) <= 12 and re.match(r"[$?~≈+\-−]", u["text"]))]
        last_end = -1.0
        busy = [(z["t"] - 0.6, z["t"] + z["hold"] + 0.7) for z in pzooms]
        for u in cands:
            if u["t"] < last_end + 1.5 or len(zooms) >= 4:
                continue
            if any(b0 <= u["t"] <= b1 or b0 <= u["t"] + 1.8 <= b1 for (b0, b1) in busy):
                continue
            l, tp = px(u["style"], "left"), px(u["style"], "top")
            if l is None or tp is None:
                continue
            w = px(u["style"], "width") or min(1000, 22 * len(u["text"]) + 40)
            h = px(u["style"], "height") or 64
            cx, cy = l + w / 2, tp + h / 2
            nxt = next((t for t in ev if t > u["t"] + 0.1), DUR)
            hold = min(max(nxt - u["t"], 1.2), 3.0)
            if u["t"] + hold + 0.6 > DUR - 0.2:
                hold = max(0.8, DUR - 0.8 - u["t"])
            if hold < 0.8:
                continue
            zooms.append((round(u["t"], 3), round(hold, 3), round(cx), round(cy), u["id"]))
            last_end = u["t"] + hold + 0.6
        for (t, hold, cx, cy, uid) in zooms:
            Z = 1.08
            # push toward the element, but never lose the headline: the card's top-left (96,104) stays in frame
            tx = max((1 - Z) * (cx - 960), 10 - (960 + Z * (96 - 960)))
            ty = max((1 - Z) * (cy - 540), 24 - (540 + Z * (104 - 540)))
            js.append(f'tl.to(zoomEl, {{ scale: {Z}, x: {round(tx, 1)}, y: {round(ty, 1)}, duration: 0.7, ease: "power2.inOut" }}, {t});  // zoom → {uid}')
            js.append(f'tl.to(zoomEl, {{ scale: 1, x: 0, y: 0, duration: 0.6, ease: "power2.inOut" }}, {round(t + hold, 3)});')
    for (uid, t) in pulses:
        js.append(f'tl.to("#{uid}", {{ scale: 1.05, duration: 0.14, ease: "power2.out", yoyo: true, repeat: 1 }}, {t});')
    body += note_html
    if a.override:
        js.append("// ── override ──")
        js.append(open(a.override, encoding="utf-8").read())
    choreo = "\n        ".join(js)

    # ── root style: keep the card's paper, dots, fonts ──
    bg = re.search(r"background:\s*(#[0-9A-Fa-f]{6})", root_style)
    bgc = bg.group(1) if bg else "#FFFFFF"
    col = re.search(r"color:\s*(#[0-9A-Fa-f]{6})", root_style)
    colc = col.group(1) if col else "#1F2937"
    ff = re.search(r"font-family:\s*([^;]+)", root_style)
    ffs = ff.group(1).strip() if ff else "'Hanken Grotesk', sans-serif"
    bgi = re.search(r"background-image:[^;]+;\s*background-size:[^;]+;?", root_style)
    bgi = bgi.group(0) if bgi else ""
    paper = f"background:{bgc};color:{colc};font-family:{ffs};{bgi}"

    cam_open = (f'<div id="{a.id}-cam" style="position:absolute;inset:0;transform-origin:50% 50%;{paper}">'
                f'<div id="{a.id}-zoom" style="position:absolute;inset:0;transform-origin:50% 50%">')
    scene_root = (f'<div id="root" data-composition-id="{a.id}" data-width="1920" data-height="1080" '
                  f'style="position:absolute;inset:0;overflow:hidden;{paper}">{cam_open}{body}</div></div></div>')
    head_js = f"""const tl = gsap.timeline({{ paused: true }});
        const SID = "{a.id}";
        const DUR = {DUR};
        const $ = (sel) => document.querySelector(sel);
        const $$ = (sel) => Array.from(document.querySelectorAll(sel));
        {choreo}
        window.__timelines["{a.id}"] = tl;"""

    scene = f"""<!doctype html>
<html>
  <head><meta charset="UTF-8" /></head>
  <body>
    <!-- generated by explainer-deck/deck_auto.py from {a.card.split('/')[-1]} · edit the override, not the markup -->
    <template>
      <link rel="stylesheet" href="{a.fonts_css}" />
      <style>
        #root {{ position: absolute; inset: 0; }}
        #root a {{ color: #3B8BFF; }}
      </style>
      {scene_root}
      <script>
        {head_js}
      </script>
    </template>
  </body>
</html>
"""
    open(a.out_scene, "w", encoding="utf-8").write(scene)

    # ── standalone root (per-card render) ──
    sfx = []
    if a.sfx:
        k = 11
        for u in units:
            if u["move"] in ("wipe",):
                sfx.append(f'<audio id="sfx-{u["id"]}" data-start="{u["t"]:.3f}" data-duration="0.03" data-track-index="{k}" data-volume="0.22" src="assets/synth/tick.wav"></audio>')
            elif u["move"] in ("pop",):
                sfx.append(f'<audio id="sfx-{u["id"]}" data-start="{max(0, u["t"] - 0.02):.3f}" data-duration="0.5" data-track-index="{k}" data-volume="0.28" src="assets/sfx/pop.mp3"></audio>')
            elif u["move"] in ("write",):
                sfx.append(f'<audio id="sfx-{u["id"]}" data-start="{u["t"]:.3f}" data-duration="0.45" data-track-index="{k}" data-volume="0.18" src="assets/sfx/click-soft.mp3"></audio>')
            else:
                continue
            k += 1
        for n in notes:
            sfx.append(f'<audio id="sfx-{n["id"]}" data-start="{n["t"]:.3f}" data-duration="0.45" data-track-index="{k}" data-volume="0.16" src="assets/sfx/click-soft.mp3"></audio>')
            k += 1
        for (t, hold, cx, cy, uid) in zooms:
            sfx.append(f'<audio id="sfx-zoom-{uid}" data-start="{max(0, t - 0.05):.3f}" data-duration="0.57" data-track-index="{k}" data-volume="0.14" src="assets/sfx/whoosh-short.mp3"></audio>')
            k += 1
        for j, z in enumerate(pzooms):
            sfx.append(f'<audio id="sfx-stamp-{j}" data-start="{max(0, z["t"] - 0.02):.3f}" data-duration="0.5" data-track-index="{k}" data-volume="{0.26 if z["kind"] == "said" else 0.18}" src="assets/sfx/pop.mp3"></audio>')
            k += 1
    root = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <script src="../assets/banger-kit.js"></script>
    <script src="../assets/deck-kit.js"></script>
    <link rel="stylesheet" href="../{a.fonts_css}" />
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1920px; height: 1080px; overflow: hidden; background: {bgc}; }}
      #root {{ position: absolute; inset: 0; overflow: hidden; {paper} }}
      #root a {{ color: #3B8BFF; }}
    </style>
  </head>
  <body>
    <!-- generated by explainer-deck/deck_auto.py from {a.card.split('/')[-1]} · card {a.n} · VO {T0:.3f} → {T0 + DUR:.3f} -->
    <div id="root" data-composition-id="{a.id}" data-start="0" data-duration="{DUR}" data-width="1920" data-height="1080">
      {cam_open}{body.replace('src="assets/', 'src="../assets/')}</div></div>
      {chr(10).join(sfx)}
    </div>
    <script>
      {head_js}
      tl.seek(0);
    </script>
  </body>
</html>
"""
    root = root.replace("src=\"assets/", "src=\"../assets/")
    open(a.out_root, "w", encoding="utf-8").write(root)

    print(f"{a.card.split('/')[-1]}: card {a.n} · {DUR:.2f}s · {len(units)} units → {a.out_scene}, {a.out_root}")
    if a.manifest:
        for n in notes:
            print(f"  {n['t']:>7} note     {n['id']:<10} {n['text']!r} @{n['x']},{n['y']} {n['font']}px")
        if pulses:
            print(f"  pulses: {pulses}")
        if zooms:
            print(f"  zooms: {[(z[0], z[1], z[4]) for z in zooms]}")
        if pzooms:
            print(f"  stamps: {[(z['t'], z['text'], z['kind']) for z in pzooms]}")
        for u in units_sorted:
            print(f"  {u['t'] if 't' in u else '-':>7} {u['move']:<8} {u['id']:<10} {('«' + u.get('anchor', '') + '»') if u.get('anchor') else '':<16} {u['text'][:56]}")


if __name__ == "__main__":
    main()
