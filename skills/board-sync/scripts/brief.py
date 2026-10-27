"""brief.md -> brief.json.

Reads the board brief written by the explainer-board-brief skill (template: brief-template.md, both the full and the
compact board format) and keeps, per board, what the animation needs:

  n, title, lines, type, builds [{element, anchor, anchors}], numbers {text: role}, fillers [{text, anchor, style, near}],
  tag, flags, plus quoted (the script lines quoted under **Lines:**) and silent (the black silent board).

Tolerant on purpose: headings may vary in punctuation, boards may come in any order, a missing section is empty.
Nothing in the brief is ever rewritten; it is only read.

  run(ctx)      reads ctx.brief (path or None), writes <ctx.out>/brief.json
  parse(text)   -> dict, for tests
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

QUOTE_OPEN = "\"“”«"
ARROWS = ("→", "->", "=>", "⟶", "➜")
NOTE_STYLES = ("hand", "sticker", "tag", "mono", "stamp")
ROLE_WORDS = {"money": "money", "price": "money", "cost": "money", "dollars": "money", "usd": "money",
              "percent": "percent", "percentage": "percent", "%": "percent", "pct": "percent",
              "count": "count", "number": "count", "quantity": "count", "amount": "count",
              "time": "time", "duration": "time", "date": "date", "year": "date", "label": "label", "other": "other",
              "recalled": "recalled", "recall": "recalled", "context": "recalled",
              "ratio": "ratio", "fraction": "ratio", "multiple": "ratio", "multiplier": "ratio"}
KNOWN_ROLES = ("money", "percent", "count", "time", "date", "ratio", "recalled")
# a role note written next to a label or number: (money), (money, recalled), (count), (money, said 'three')
ROLE_PAREN = re.compile(r"\s*\((?=[^()]*\b(?:money|percent|count|time|date|ratio|fraction|recalled|duration)\b)[^()]*\)", re.I)
HONESTY = ("SEEN", "EXAMPLE", "MY READ", "SIMPLIFIED")

BOARD_HEAD = re.compile(r"^\s{0,3}#{1,6}\s*(?:board|slide|card)\s*#?\s*(\d+)\b\s*[·:.\-–—|]*\s*(.*?)\s*$", re.I)
ANY_HEAD = re.compile(r"^\s{0,3}#{1,6}\s+\S")
FIELD = re.compile(r"^\s*(?:[-*+]\s+)?(?:\*\*|__)?\s*([A-Za-z][A-Za-z ,/&'’()→\-]{0,60}?)\s*(?:\*\*|__)?\s*:\s*(?:\*\*|__)?\s*(.*)$")
NUMBERED = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+(.*)$")

FIELD_KEYS = [  # (normalised field name prefix, key)
    ("lines", "lines"), ("line", "lines"), ("window", "window"), ("title", "titleline"),
    ("the viewer must understand", "understand"), ("viewer must understand", "understand"), ("understand", "understand"),
    ("type", "type"),
    ("focal visual", "visual"), ("visual", "visual"),
    ("on screen exactly", "onscreen"), ("on screen", "onscreen"), ("onscreen", "onscreen"),
    ("builds", "builds"), ("build", "builds"),
    ("fillers", "fillers"), ("filler", "fillers"),
    ("tag flags", "tagflags"), ("tags flags", "tagflags"), ("tag and flags", "tagflags"),
    ("tags", "tag"), ("tag", "tag"),
    ("returns to the anchor", "returns"), ("returns", "returns"),
    ("flags", "flags"), ("flag", "flags"),
]


# ───────────────────────── small text helpers ─────────────────────────
def _clean(s: str) -> str:
    """Drop markdown emphasis (**x**, __x__, `x`) but keep literal underscores such as "$_.__"."""
    s = re.sub(r"\*\*|`", "", s or "")
    s = re.sub(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def _field_key(name: str) -> str | None:
    n = re.sub(r"\(.*?\)", " ", name.lower())
    n = re.sub(r"[^a-z ]+", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    for pre, key in FIELD_KEYS:
        if n == pre or n.startswith(pre + " ") or n.startswith(pre):
            return key
    return None


def split_outside_quotes(s: str, seps=("·", ";", "•", "|")) -> list[str]:
    """Split on any separator that is not inside a quoted string. Commas are never separators here."""
    out, buf, q = [], [], None
    i = 0
    while i < len(s):
        ch = s[i]
        if q:
            buf.append(ch)
            if (q == '"' and ch == '"') or (q == "“" and ch in "”\"") or (q == "«" and ch == "»"):
                q = None
        elif ch in ('"', "“", "«"):
            q = ch
            buf.append(ch)
        elif ch in seps:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [p.strip() for p in out if p.strip()]


def quoted(s: str) -> list[str]:
    """Every quoted string in s, in order (straight or curly quotes, guillemets)."""
    return [m.group(1) or m.group(2) or m.group(3) for m in
            re.finditer(r'"([^"]+)"|“([^”"]+)[”"]|«([^»]+)»', s)]


def _split_arrow(item: str) -> tuple[str, str | None]:
    """'element → anchor' split on the LAST arrow outside quotes."""
    best = -1
    blen = 0
    q = None
    for i, ch in enumerate(item):
        if q:
            if (q == '"' and ch == '"') or (q == "“" and ch in "”\"") or (q == "«" and ch == "»"):
                q = None
            continue
        if ch in ('"', "“", "«"):
            q = ch
            continue
        for a in ARROWS:
            if item.startswith(a, i):
                best, blen = i, len(a)
    if best < 0:
        return item.strip(), None
    return item[:best].strip(), item[best + blen:].strip()


# ───────────────────────── field parsers ─────────────────────────
def parse_anchor(spec: str | None) -> dict:
    """The right-hand side of a build: verbatim words, structure, with:, +N, @seconds, hide."""
    if spec is None:
        return {"anchor": None, "anchors": []}
    s = _clean(spec)
    low = s.lower().strip(" .")
    if not s:
        return {"anchor": None, "anchors": []}
    if low.startswith("structure") or low in ("open", "opens", "as the board opens", "on open"):
        return {"anchor": "structure", "anchors": ["structure"]}
    if low in ("hide", "hidden", "never", "never shown", "skip"):
        return {"anchor": "hide", "anchors": ["hide"]}
    m = re.match(r"^with\s*:?\s*(.+)$", s, re.I)
    if m:
        tgt = quoted(m.group(1))
        t = tgt[0] if tgt else m.group(1).strip(" .\"“”")
        return {"anchor": "with:" + t, "anchors": ["with:" + t]}
    m = re.match(r"^\+\s*(\d+(?:\.\d+)?)\s*s?$", s)
    if m:
        return {"anchor": "+" + m.group(1), "anchors": ["+" + m.group(1)]}
    m = re.match(r"^(?:@|at\s+)(\d+(?:\.\d+)?)\s*s?$", s, re.I)
    if m:
        return {"anchor": "@" + m.group(1), "anchors": ["@" + m.group(1)]}
    qs = quoted(s)
    if qs:
        return {"anchor": qs[0].strip(), "anchors": [q.strip() for q in qs]}
    return {"anchor": s.strip(" ."), "anchors": [s.strip(" .")]}


def parse_builds(raw_items: list[str]) -> list[dict]:
    builds = []
    for it in raw_items:
        it = _clean(it)
        if not it or it.lower() in ("none", "-", "n/a"):
            continue
        elem, spec = _split_arrow(it)
        m = re.match(r"^structure\b[^:]*:\s*(.*)$", elem, re.I)
        if spec is None and m:
            builds.append({"element": m.group(1).strip(), "anchor": "structure", "anchors": ["structure"], "raw": it})
            continue
        if spec is None and re.match(r"^structure\b", elem, re.I):
            rest = re.sub(r"^structure\b\s*[:\-–—]?\s*", "", elem, flags=re.I)
            rest = re.sub(r"^(?:as|when)\s+the\s+(?:board|slide)\s+opens\s*[:\-–—]?\s*|^on\s+open\s*[:\-–—]?\s*", "", rest, flags=re.I)
            builds.append({"element": rest.strip(" ."), "anchor": "structure", "anchors": ["structure"], "raw": it})
            continue
        a = parse_anchor(spec)
        if m and spec is not None:            # "structure: the receipt → 'words'" keeps the element text after the colon
            elem = m.group(1).strip()
        builds.append({"element": elem, "anchor": a["anchor"], "anchors": a["anchors"], "raw": it})
    for x in builds:
        # roles written on the element ("$20" (money, recalled), $500,000 (money)) are kept as numbers, then removed
        # from the element so it can be matched against the board's text
        inf: dict[str, str] = {}
        x["numbers"] = parse_numbers(x["element"], infer=False, inferred=inf)
        x["numbers_inferred"] = inf
        x["element"] = re.sub(r"\s+", " ", ROLE_PAREN.sub("", x["element"])).strip()
    return builds


def _infer_role(t: str) -> str:
    if "$" in t or re.search(r"\bdollars?\b|\bbucks\b|[€£]", t, re.I):
        return "money" + ("+percent" if "%" in t or re.search(r"\bpercent\b", t, re.I) else "")
    if "%" in t or re.search(r"\bpercent\b", t, re.I):
        return "percent"
    return "number"


def parse_numbers(text: str, infer: bool = True, inferred: dict | None = None) -> dict:
    """'"$5,000" (money)', '"$5,000 (money)"', '<$500,000 (money)>' → {"$5,000": "money"}.
    Roles: money, percent, count, time, date, recalled (context that returns, not spoken on this board), or several
    joined with '+' ("money+percent", "money+recalled"). A parenthesis that is not a
    role ("(orange)") is ignored and the role is inferred from the text ($ → money, % → percent, else number)."""
    nums: dict[str, str] = {}

    def known(r: str) -> list[str]:
        roles = []
        for part in re.split(r"[,/&+;]|\band\b", r.strip().lower()):
            part = part.strip()
            role = next((v for k, v in ROLE_WORDS.items() if part == k or part.startswith(k + " ") or part == k + "s"), None)
            if role and role not in roles:
                roles.append(role)
        return roles

    def role_of(r: str, key: str) -> str | None:
        roles = known(r)
        if roles:
            return "+".join(roles)
        if re.search(r"\d", key):
            if inferred is not None:
                inferred[key] = _infer_role(key)
            return _infer_role(key)
        return None

    pats = [r'["“]([^"”]+?)["”]\s*\(([^()]*)\)',
            r'["“<]([^"”<>]*?[\d⅓⅔¼½¾][^"”<>]*?)\s*\(([^()]*)\)\s*[>"”]']
    for pat in pats:
        for m in re.finditer(pat, text):
            key = re.sub(r"\s*\([^()]*\)\s*$", "", m.group(1)).strip()
            role = role_of(m.group(2), key)
            if role and key and key not in nums:
                nums[key] = role
    # an unquoted number with a role: $500,000 (money) → "half a million dollars"
    for m in re.finditer(r'(?<![\w"“$.,])([−\-+~≈]?\$?\d[\d,.]*(?:\s?(?:%|×|x|K|k|M|m|B|bn)\b|%|×)?)\s*\(([^()]*)\)', text):
        roles = known(m.group(2))
        key = m.group(1).strip()
        if roles and key not in nums and not any(key in k for k in nums):
            nums[key] = "+".join(roles)
    for q in (quoted(text) if infer else []):
        q2 = re.sub(r"\s*\([^)]*\)\s*$", "", q).strip()
        if q2 in nums or not re.search(r"\d", q2):
            continue
        nums[q2] = _infer_role(q2)
        if inferred is not None:
            inferred[q2] = nums[q2]
    return nums


def _num_values(key: str) -> tuple:
    return tuple(sorted(re.sub(r"[,]", "", n).rstrip(".") for n in re.findall(r"\d[\d,.]*", key)))


def _dedupe_numbers(nums: dict) -> dict:
    """One entry per number: "$10" (money, recalled) on screen and "List price · $10" (money, recalled) in Builds are
    the same number. A recalled role wins over a plain one; the shortest text is kept."""
    best: dict[tuple, tuple[str, str]] = {}
    order = []
    for k, v in nums.items():
        base = "+".join(r for r in v.split("+") if r != "recalled") or "number"
        vals = _num_values(k)
        vals = vals + (base,) if vals else vals          # "$10" (money) and "10 seconds" (time) stay apart
        if not vals:
            best[(k,)] = (k, v)
            order.append((k,))
            continue
        cur = best.get(vals)
        if cur is None:
            best[vals] = (k, v)
            order.append(vals)
            continue
        ck, cv = cur
        if "recalled" in v and "recalled" not in cv:
            best[vals] = (k if len(k) <= len(ck) else ck, v)
        elif ("recalled" in v) == ("recalled" in cv) and len(k) < len(ck):
            best[vals] = (k, cv if cv == v else (v if len(v) > len(cv) else cv))
    return {best[o][0]: best[o][1] for o in order}


def parse_fillers(items: list[str]) -> list[dict]:
    out = []
    for it in items:
        it = _clean(it)
        low = it.lower().strip(" .")
        if not it or low in ("none", "-", "n/a") or low.startswith("none") or low.startswith("no filler"):
            continue
        left, spec = _split_arrow(it)
        style = None
        qpos = min([i for i in (left.find('"'), left.find("“")) if i >= 0], default=-1)
        sm = re.search(r"\((hand|sticker|tag|mono|stamp)[^)]*\)", left, re.I) or (
            re.search(r"\b(hand|sticker|tag|mono|stamp)\b", left[:qpos], re.I) if qpos >= 0 else None)
        if sm:
            style = sm.group(1).lower()
        near = None
        lq = left
        for q in quoted(left)[:1]:          # the note text itself is never the 'near' target
            lq = lq.replace(q, "", 1)
        nm = re.search(r"\b(?:near|next to|beside|under|below|above|by)\s+(\"[^\"]+\"|“[^”]+”|[^\"“(]+)", lq, re.I)
        if nm:
            near = nm.group(1).strip(" .,\"“”")
        qs = quoted(left)
        anchor = parse_anchor(spec)["anchor"] if spec is not None else None
        drawn = None
        if qs:
            text = qs[0]
        elif anchor and spec is not None:
            # a filler described as a mark ("underline under the slot") with no words of its own:
            # board-sync writes the spoken anchor words instead (it never invents a drawing)
            text, drawn = anchor.strip(" ."), left.strip(" .")
        else:
            text = re.sub(r"\((?:hand|sticker|tag|mono|stamp)[^)]*\)", "", left, flags=re.I)
            text = re.sub(r"^(?:a |an |the )?(?:hand(?:written)? note|note|sticker|tag|stamp|mono line)\s*:?\s*", "", text, flags=re.I)
            text = text.strip(" .:")
        if anchor is None:
            anchor = text.replace("\\n", " ").replace("\n", " ")
        if not text:
            continue
        out.append({"text": text, "anchor": anchor, "style": style or "hand", "near": near, "described": drawn, "raw": it})
    return out


def _split_items(val: str, sub: list[str]) -> list[str]:
    """A field's items: inline ' · ' separated parts plus any numbered/bulleted sub-lines."""
    items = []
    if val.strip():
        items += split_outside_quotes(val)
    for s in sub:
        m = NUMBERED.match(s)
        line = m.group(1) if m else s
        if line.strip().startswith(">"):
            continue
        items += split_outside_quotes(line) if (" · " in line or ";" in line) and not m else [line]
    return [i for i in (x.strip() for x in items) if i]


# ───────────────────────── board assembly ─────────────────────────
def _board_from(n: int, head_rest: str, body: list[str]) -> dict:
    title = head_rest
    rng, btype = "", ""
    status = None
    m = re.search(r"\[(NEW|CHANGED|UNCHANGED|CUT)\]\s*$", title, re.I)
    if m:
        status = m.group(1).upper()
        title = title[:m.start()].strip()
    m = re.search(r"\(\s*(L\s*\d+\s*(?:[–\-—]\s*L?\s*\d+)?)\s*(?:,\s*([^)]*))?\)\s*$", title)
    if m:
        rng = re.sub(r"\s+", "", m.group(1))
        btype = (m.group(2) or "").strip()
        title = title[:m.start()].strip()
    title = _clean(title).strip(" ·:-–—").strip("\"“”")
    fields: dict[str, list] = {}
    order: list[str] = []
    cur = None
    for line in body:
        if not line.strip():
            continue
        fm = FIELD.match(line)
        key = _field_key(fm.group(1)) if fm else None
        indented = len(line) - len(line.lstrip()) >= 2
        sub_item = indented and cur is not None and (NUMBERED.match(line) or line.strip().startswith(">"))
        if fm and key and not sub_item:
            cur = key
            fields.setdefault(cur, [fm.group(2).strip(), []])
            if cur not in order:
                order.append(cur)
            continue
        if cur:
            fields[cur][1].append(line.rstrip())
    b = {"n": n, "title": title, "lines": rng, "window": "", "highlight": "", "quoted": [], "type": btype,
         "numbers_inferred": {}, "understand": "", "visual": "",
         "onscreen": "", "builds": [], "numbers": {}, "fillers": [], "tag": "", "flags": [], "returns": "",
         "silent": False, "status": status}
    if "lines" in fields:
        v, sub = fields["lines"]
        rm = re.search(r"L\s*\d+\s*(?:[–\-—]\s*L?\s*\d+)?", v)
        if rm and not b["lines"]:
            b["lines"] = re.sub(r"\s+", "", rm.group(0))
        for s in sub:
            s2 = s.strip()
            if s2.startswith(">"):
                b["quoted"].append(re.sub(r"^L\d+\s+", "", s2.lstrip("> ").strip()))
        if not rm and v and not b["lines"]:
            b["lines"] = _clean(v)
    if "window" in fields:
        b["window"] = _clean(fields["window"][0])
    for k in ("understand", "visual", "type", "returns"):
        if k in fields:
            v, sub = fields[k]
            txt = _clean(" ".join([v] + [s.strip() for s in sub]))
            if k == "type" and b["type"]:
                continue
            b[k] = txt
    if "onscreen" in fields:
        v, sub = fields["onscreen"]
        b["onscreen"] = _clean(" ".join([v] + [s.strip() for s in sub]))
    if "builds" in fields:
        v, sub = fields["builds"]
        b["builds"] = parse_builds(_split_items(v, sub))
    if "fillers" in fields:
        v, sub = fields["fillers"]
        if not re.match(r"^\s*(none|no fillers?|n/a)\b", _clean(v), re.I):
            b["fillers"] = parse_fillers(_split_items(v, sub))
    if "tag" in fields:
        v, sub = fields["tag"]
        b["tag"] = _clean(" ".join([v] + [s.strip() for s in sub])).strip(" .")
    if "flags" in fields:
        v, sub = fields["flags"]
        items = ([_clean(v)] if v.strip() else []) + [_clean((NUMBERED.match(x) or re.match(r"(.*)", x.strip())).group(1))
                                                       for x in sub if x.strip() and not x.strip().startswith(">")]
        b["flags"] += [f for f in items if f and f.lower().strip(" .") not in ("none", "-", "n/a", "no")]
    if "tagflags" in fields:
        v, sub = fields["tagflags"]
        parts = _split_items(v, sub)
        tags, flags = [], []
        for p in parts:
            pu = p.upper()
            if p.lower().strip(" .") in ("none", "-", "n/a"):
                continue
            if any(pu.startswith(h) for h in HONESTY) and len(p) < 60:
                tags.append(p)
            else:
                flags.append(p)
        if tags and not b["tag"]:
            b["tag"] = " · ".join(tags)
        b["flags"] += flags
    tl = ""
    if "titleline" in fields:
        tl = _clean(" ".join([fields["titleline"][0]] + [x.strip() for x in fields["titleline"][1]]))
        b["title_line"] = tl
        tq = quoted(re.sub(r"\(\s*highlight[^)]*\)", "", tl, flags=re.I))
        if tq and not b["title"]:
            b["title"] = tq[0]
    hay_hl = tl + " " + b["onscreen"]
    hm = (re.search(r"(?:keyword|word)s?\s+to\s+highlight\s*:?\s*[\"“]([^\"”]+)[\"”]", hay_hl, re.I)
          or re.search(r"\(\s*highlight(?:ed)?\s*:?\s*[\"“]([^\"”]+)[\"”]\s*\)", hay_hl, re.I))
    b["highlight"] = hm.group(1).strip() if hm else ""
    inferred: dict[str, str] = {}
    b["numbers"] = parse_numbers(re.sub(r"\(\s*highlight[^)]*\)", "", b["onscreen"], flags=re.I), inferred=inferred)
    for x in b["builds"]:                      # roles written inside Builds (the newer compact format) count too
        for k, v in (x.get("numbers") or {}).items():
            if k not in b["numbers"] or "recalled" in v:
                b["numbers"][k] = v
                if k in (x.get("numbers_inferred") or {}):
                    inferred[k] = v
                else:
                    inferred.pop(k, None)
    norm_t = re.sub(r"\W+", " ", b["title"]).strip().lower()
    for k in [k for k in b["numbers"] if re.sub(r"\W+", " ", k).strip().lower() == norm_t and norm_t]:
        b["numbers"].pop(k)                    # the board's own title is not a number on the board
    b["numbers"] = _dedupe_numbers(b["numbers"])
    # numbers whose role nobody wrote: kept, and listed so the QA report asks the editor to check them
    b["numbers_inferred"] = {k: v for k, v in b["numbers"].items() if k in inferred and inferred[k] == v}
    hay = " ".join([b["title"], b["type"], b["visual"]]).lower()
    b["silent"] = bool(re.search(r"\bblack\b.*\bsilent\b|\bsilent\b.*\bblack\b|\bsilent board\b", hay))
    b["unparsed_fields"] = [k for k in fields if k not in ("lines", "window", "titleline", "understand", "visual", "type", "returns", "onscreen",
                                                           "builds", "fillers", "tag", "flags", "tagflags")]
    return b


def parse(text: str) -> dict:
    """Parse brief.md text. Returns {"boards": [board, ...] sorted by n, "warnings": [...]}."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    boards: dict[int, dict] = {}
    warnings: list[str] = []
    cur_n, cur_head, body = None, "", []

    def flush():
        if cur_n is None:
            return
        b = _board_from(cur_n, cur_head, body)
        if cur_n in boards:
            warnings.append(f"board {cur_n} appears twice in the brief; the later one is used")
        boards[cur_n] = b

    for line in lines:
        m = BOARD_HEAD.match(line)
        if m:
            flush()
            cur_n, cur_head, body = int(m.group(1)), m.group(2), []
            continue
        if ANY_HEAD.match(line) and cur_n is not None:
            # a heading of another kind (## Camera-only lines …) closes the board
            if re.match(r"^\s{0,3}#{1,3}\s", line):
                flush()
                cur_n, cur_head, body = None, "", []
                continue
        if cur_n is not None:
            body.append(line)
    flush()
    for n, b in boards.items():
        if not b["builds"]:
            warnings.append(f"board {n}: no Builds list; every element will be anchored by its own text")
    return {"boards": [boards[n] for n in sorted(boards)], "warnings": warnings}


# ───────────────────────── stage entry ─────────────────────────
def _get(ctx, name, default=None):
    if isinstance(ctx, dict):
        return ctx.get(name, default)
    return getattr(ctx, name, default)


def run(ctx) -> dict:
    out = Path(_get(ctx, "out"))
    out.mkdir(parents=True, exist_ok=True)
    src = _get(ctx, "brief")
    if not src or not Path(src).is_file():
        data = {"source": str(src) if src else None, "missing": True, "boards": [],
                "warnings": ["no brief.md: every element is anchored by its own text"]}
        common.write_json(out / "brief.json", data)
        common.log("brief: no brief.md given; every element will be anchored by its own text (the QA report says so).")
        return data
    text = Path(src).read_text(encoding="utf-8", errors="replace")
    data = parse(text)
    data = {"source": str(Path(src).resolve()), "missing": False, **data}
    common.write_json(out / "brief.json", data)
    nb = len(data["boards"])
    nbuilds = sum(len(b["builds"]) for b in data["boards"])
    common.log(f"brief: {nb} boards, {nbuilds} builds read from {Path(src).name}")
    for w in data["warnings"]:
        common.log("brief: " + w)
    return data


if __name__ == "__main__":
    import json
    p = Path(sys.argv[1])
    print(json.dumps(parse(p.read_text(encoding="utf-8")), ensure_ascii=False, indent=1))
