"""Board HTML -> units/NN.json.

A board is a Design-Component export: one `.m-root` (1920x1080) with absolutely positioned children, usually wrapped
in a `.m-fit`. Its Motion <script> loops on its own timers; board-sync drops it and drives every element itself.

Units (in DOM order): the root's direct children (headline, header label), every direct child of `.m-fit`, and the
deck's own build elements inside them (`.m-draw .m-hand .m-type .m-pop .m-grow .m-growx`: receipt rows, strokes,
stickers, bars). Each unit carries:
  id (uNN), path (element-child indices from the root, so the scene can find it again), kind, text, own_text,
  bbox {x,y,w,h} MEASURED in the browser after fonts are ready, children (ids), parent, price/prices,
  default_move, rotation/transform (inline transforms recorded), plus measurement details (font, shapes, ends).

  run(ctx)                    all boards in ctx.boards (honours ctx.only) -> <ctx.out>/units/NN.json
  parse_board(path, page)     one board, with an open Playwright page -> dict
  read_board(path)            the board split into head (links/styles) and root markup, URLs made absolute
  launch_browser(pw)          Chrome / Edge / bundled Chromium, whichever exists
"""
from __future__ import annotations

import html as H
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

W, HGT = 1920, 1080
TAG = re.compile(r"<(/?)([a-zA-Z][\w:-]*)((?:\"[^\"]*\"|'[^']*'|[^'\">])*?)(/?)>", re.S)
VOID = {"img", "br", "hr", "input", "meta", "link", "source", "wbr", "area", "col", "embed", "track", "param"}
BUILD_CLASSES = ("m-draw", "m-hand", "m-type", "m-pop", "m-grow", "m-growx")
PRICE_RE = re.compile(r"[−\-+~≈]?\$\s?\d[\d,]*(?:\.\d+)?(?:\s?[KkMmBb](?![A-Za-z]))?|[−\-+~≈]?\d[\d,]*(?:\.\d+)?\s?%")
DEFAULT_MOVE = {"headline": "label", "container": "rise", "zone": "rise", "row": "wipe", "bar": "grow",
                "sticker": "pop", "note": "write", "arrow": "draw", "icon": "rise", "image": "rise",
                "legend": "rise", "label": "rise"}


# ───────────────────────── markup walking (no DOM library needed) ─────────────────────────
def element_span(s: str, open_start: int) -> tuple[int, int, int]:
    """(open_end, close_start, close_end) of the element whose open tag starts at open_start."""
    depth = 0
    first = TAG.match(s, open_start)
    if not first:
        raise ValueError("no tag at offset")
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
                return first.end(), m.start(), m.end()
    raise ValueError("unbalanced markup in the board")


def _abs_url(url: str, base: Path) -> str:
    u = url.strip()
    if not u or u.startswith(("#", "data:", "http:", "https:", "file:", "blob:", "about:", "javascript:", "mailto:")):
        return url
    if re.match(r"^[a-zA-Z]:[\\/]", u) or u.startswith("/"):
        return Path(u).as_uri() if Path(u).exists() else url
    p = (base / u.split("#")[0].split("?")[0]).resolve()
    return p.as_uri()


def rewrite_urls(markup: str, base: Path) -> str:
    """src/href/poster attributes and url(...) in styles → absolute file:// URIs of the board folder."""
    def attr(m):
        return f'{m.group(1)}={m.group(2)}{_abs_url(H.unescape(m.group(3)), base)}{m.group(2)}'
    markup = re.sub(r'\b(src|href|poster)=(["\'])(.*?)\2', attr, markup)

    def css(m):
        q = m.group(1) or ""
        return f"url({q}{_abs_url(H.unescape(m.group(2)), base)}{q})"
    markup = re.sub(r"url\(\s*(\"|'|&quot;)?([^)\"'&]+?)(?:\1)?\s*\)", css, markup)
    return markup


def read_board(path) -> dict:
    """Split a board export into what a scene needs. Scripts, comments and the camera guide are dropped."""
    path = Path(path).resolve()
    s = path.read_text(encoding="utf-8", errors="replace")
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s_noscript = re.sub(r"<script\b.*?</script\s*>", "", s, flags=re.S | re.I)
    head_m = re.search(r"<head\b.*?</head\s*>", s_noscript, flags=re.S | re.I)
    head = head_m.group(0) if head_m else ""
    links = [rewrite_urls(m.group(0), path.parent) for m in re.finditer(r"<link\b[^>]*>", head, flags=re.I)
             if re.search(r"rel=[\"']?stylesheet", m.group(0), re.I)]
    styles = [rewrite_urls(m.group(0), path.parent) for m in re.finditer(r"<style\b.*?</style\s*>", head, flags=re.S | re.I)]
    title_m = re.search(r"<title>(.*?)</title>", head, flags=re.S | re.I)
    title = H.unescape(title_m.group(1)).strip() if title_m else path.stem
    rm = re.search(r"<(\w+)\b[^>]*\bclass=\"[^\"]*\bm-root\b[^\"]*\"", s_noscript)
    if not rm:
        raise SystemExit(f"{path.name}: no .m-root element; is this a Design-Component board export?")
    oe, cs, ce = element_span(s_noscript, rm.start())
    root = s_noscript[rm.start():ce]
    root = re.sub(r"<sc-if\b.*?</sc-if\s*>", "", root, flags=re.S | re.I)
    root = re.sub(r"<(video\b[^>]*?)\s+autoplay(?:=\"[^\"]*\")?", r"<\1", root, flags=re.I)
    root = rewrite_urls(root, path.parent)
    root_open = TAG.match(root, 0).group(0)
    style_m = re.search(r'style="([^"]*)"', root_open)
    root_style = H.unescape(style_m.group(1)) if style_m else ""
    bg = re.search(r"background(?:-color)?:\s*(#[0-9A-Fa-f]{3,8}|rgba?\([^)]*\)|[a-z]+)\s*(?:;|$)", root_style)
    return {"path": str(path), "file": path.name, "dir": str(path.parent), "title": title, "links": links,
            "styles": styles, "root": root, "root_style": root_style, "bg": bg.group(1) if bg else "#FFFFFF"}


def static_page(board: dict, extra_head: str = "", extra_body: str = "") -> str:
    """The board's root alone on a 1920x1080 page, with its fonts/styles and no scripts (what the scene inlines)."""
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
            f"<title>{H.escape(board['title'])}</title>\n" + "\n".join(board["links"]) + "\n" + "\n".join(board["styles"]) +
            "\n<style>html,body{margin:0;padding:0;width:1920px;height:1080px;overflow:hidden;background:"
            + board["bg"] + "} .m-root{position:absolute!important;left:0;top:0} "
            "*{animation:none!important;transition:none!important}</style>\n" + extra_head +
            "</head><body>\n" + board["root"] + "\n" + extra_body + "</body></html>\n")


# ───────────────────────── browser ─────────────────────────
def launch_browser(pw):
    """Chrome or Edge if installed (no download needed), else Playwright's bundled Chromium."""
    order = ["msedge", "chrome"] if sys.platform.startswith("win") else ["chrome", "msedge"]
    errs = []
    for ch in order + [None]:
        try:
            return pw.chromium.launch(channel=ch) if ch else pw.chromium.launch()
        except Exception as e:  # noqa: BLE001
            errs.append(f"{ch or 'bundled chromium'}: {str(e).splitlines()[0]}")
    raise SystemExit("No browser found for board-sync (tried " + "; ".join(errs) +
                     "). Install Microsoft Edge or Google Chrome, or run: python -m playwright install chromium")


EXTRACT_JS = r"""
() => {
  const root = document.querySelector('.m-root');
  if (!root) return {error: 'no .m-root'};
  const R = root.getBoundingClientRect();
  const SKIP = new Set(['script','style','template','sc-if','link','meta','noscript','title']);
  const BUILD = '.m-draw,.m-hand,.m-type,.m-pop,.m-grow,.m-growx';
  const SHAPES = 'path,line,polyline,polygon,circle,ellipse,rect';
  const found = [];
  const seen = new Set();
  const add = (el, level) => { if (!el || seen.has(el) || SKIP.has(el.tagName.toLowerCase())) return; seen.add(el); found.push({el, level}); };
  const kids = Array.from(root.children).filter(k => !SKIP.has(k.tagName.toLowerCase()));
  const fit = kids.find(k => k.classList.contains('m-fit'));
  for (const k of kids) {
    if (k === fit) continue;
    add(k, 'top');
    k.querySelectorAll(BUILD).forEach(d => add(d, 'sub'));
  }
  if (fit) for (const k of Array.from(fit.children)) {
    if (SKIP.has(k.tagName.toLowerCase())) continue;
    add(k, 'fit');
    k.querySelectorAll(BUILD).forEach(d => add(d, 'sub'));
  }
  found.sort((a, b) => (a.el.compareDocumentPosition(b.el) & Node.DOCUMENT_POSITION_FOLLOWING) ? -1 : 1);
  found.forEach((f, i) => f.el.setAttribute('data-bsu', String(i)));
  const pathOf = (el) => { const p = []; let e = el; while (e && e !== root) { const par = e.parentElement; if (!par) return null; p.unshift(Array.prototype.indexOf.call(par.children, e)); e = par; } return p; };
  const rel = (r) => ({x: r.left - R.left, y: r.top - R.top, w: r.width, h: r.height});
  const norm = (t) => (t || '').replace(/ /g, ' ').replace(/\s+/g, ' ').trim();
  const ownText = (el) => {
    const parts = [];
    const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = tw.nextNode())) {
      const p = n.parentElement;
      if (!p || ['style','script'].includes(p.tagName.toLowerCase())) continue;
      const owner = p.closest('[data-bsu]');
      if (owner === el) parts.push(n.textContent);
    }
    return norm(parts.join(' '));
  };
  const maxFont = (el) => {
    let m = 0;
    const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = tw.nextNode())) {
      if (!n.textContent.trim()) continue;
      const p = n.parentElement; if (!p) continue;
      m = Math.max(m, parseFloat(getComputedStyle(p).fontSize) || 0);
    }
    return m;
  };
  const out = found.map(({el, level}, i) => {
    const cs = getComputedStyle(el);
    const tag = el.tagName.toLowerCase();
    let r = el.getBoundingClientRect();
    let box = rel(r);
    const shapes = [];
    const isDraw = el.classList.contains('m-draw') || tag === 'svg';
    if (!isDraw && (r.width < 2 || r.height < 2)) {
      // a group with no size of its own (absolutely positioned children): measure what it draws
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      const take = (q) => { if (q.width + q.height <= 0) return; x0 = Math.min(x0, q.left); y0 = Math.min(y0, q.top); x1 = Math.max(x1, q.right); y1 = Math.max(y1, q.bottom); };
      el.querySelectorAll('*').forEach(d => {
        const t = d.tagName.toLowerCase();
        if (d.closest('svg')) { if (SHAPES.split(',').includes(t)) take(d.getBoundingClientRect()); return; }
        if (d.querySelector('svg')) return;
        const dcs = getComputedStyle(d);
        const hasText = Array.from(d.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
        const boxy = parseFloat(dcs.borderTopWidth) > 0 || (dcs.backgroundColor !== 'rgba(0, 0, 0, 0)') || dcs.backgroundImage !== 'none';
        if (hasText || boxy || t === 'img' || t === 'video') take(d.getBoundingClientRect());
      });
      if (x1 > x0) box = {x: x0 - R.left, y: y0 - R.top, w: x1 - x0, h: y1 - y0};
    }
    if (isDraw) {
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      el.querySelectorAll(SHAPES).forEach(sh => {
        const sr = sh.getBoundingClientRect();
        const scs = getComputedStyle(sh);
        const sw = parseFloat(scs.strokeWidth) || 0;
        const pad = scs.stroke && scs.stroke !== 'none' ? sw / 2 + 1 : 0;
        if (sr.width + sr.height <= 0) return;
        x0 = Math.min(x0, sr.left - pad); y0 = Math.min(y0, sr.top - pad);
        x1 = Math.max(x1, sr.right + pad); y1 = Math.max(y1, sr.bottom + pad);
        let L = 0, p0 = null, p1 = null;
        try {
          L = sh.getTotalLength();
          const m = sh.getScreenCTM();
          const a = sh.getPointAtLength(0), b = sh.getPointAtLength(L);
          const tr = (p) => ({x: m.a * p.x + m.c * p.y + m.e - R.left, y: m.b * p.x + m.d * p.y + m.f - R.top});
          p0 = tr(a); p1 = tr(b);
        } catch (e) {}
        shapes.push({tag: sh.tagName.toLowerCase(), L: Math.round(L * 10) / 10, p0, p1, stroke: scs.stroke, sw,
                     dash: scs.strokeDasharray, fill: scs.fill});
      });
      if (x1 > x0) box = {x: x0 - R.left, y: y0 - R.top, w: x1 - x0, h: y1 - y0};
    }
    let ink = null;
    if (!isDraw && (el.textContent || '').trim()) {
      // where the letters actually are (a 1700 px wide headline box may hold 600 px of text)
      // only the painted letters: one range per text node (a range over the whole element would also return the
      // boxes of child elements, e.g. a 1920x1080 stroke layer)
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      const tw2 = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let tn;
      while ((tn = tw2.nextNode())) {
        if (!tn.textContent.trim()) continue;
        const pe = tn.parentElement;
        if (!pe || ['style', 'script'].includes(pe.tagName.toLowerCase())) continue;
        const rg = document.createRange(); rg.selectNodeContents(tn);
        Array.from(rg.getClientRects()).forEach(q => { if (q.width > 0 && q.height > 0) { x0 = Math.min(x0, q.left); y0 = Math.min(y0, q.top); x1 = Math.max(x1, q.right); y1 = Math.max(y1, q.bottom); } });
      }
      if (x1 > x0) ink = {x: x0 - R.left, y: y0 - R.top, w: x1 - x0, h: y1 - y0};
    }
    const hl = [];
    if (level === 'top') {
      el.querySelectorAll('span,mark,em,b,strong').forEach(sp => {
        const bg = getComputedStyle(sp).backgroundImage + ' ' + (sp.getAttribute('style') || '');
        if (/gradient/.test(bg) || sp.tagName.toLowerCase() === 'mark') hl.push({text: norm(sp.textContent), lines: sp.getClientRects().length, path: pathOf(sp)});
      });
    }
    const border = ['Top','Right','Bottom','Left'].some(s => parseFloat(cs['border' + s + 'Width']) > 0 && cs['border' + s + 'Style'] !== 'none');
    const bgc = cs.backgroundColor;
    const hasBg = (bgc && bgc !== 'rgba(0, 0, 0, 0)' && bgc !== 'transparent') || (cs.backgroundImage && cs.backgroundImage !== 'none');
    return {
      i, path: pathOf(el), level, tag, cls: Array.from(el.classList), style: el.getAttribute('style') || '',
      text: norm(el.innerText !== undefined ? el.innerText : el.textContent), own_text: ownText(el),
      bbox: box, el_box: rel(r), ink, font: parseFloat(cs.fontSize) || 0, max_font: maxFont(el), color: cs.color,
      border, has_bg: !!hasBg, fill: bgc, opacity: parseFloat(cs.opacity), position: cs.position,
      transform: el.style.transform || '', computed_transform: cs.transform, display: cs.display,
      media: el.querySelectorAll('img,video').length + ((tag === 'img' || tag === 'video') ? 1 : 0),
      shapes, hl, data_hd: el.hasAttribute('data-hd')
    };
  });
  found.forEach(f => f.el.removeAttribute('data-bsu'));
  return {units: out, root: rel(R)};
}
"""


# ───────────────────────── classification ─────────────────────────
def _rotation(transform: str) -> float | None:
    m = re.fullmatch(r"\s*rotate\(\s*(-?[\d.]+)deg\s*\)\s*", transform or "")
    return float(m.group(1)) if m else None


def _clamp_ink(ink: dict | None, box: dict) -> dict | None:
    """The letters' box, never larger than the element's painted box or the frame (rotated text may poke out a little)."""
    if not ink:
        return None
    x0 = max(ink["x"], box["x"] - 8, 0.0)
    y0 = max(ink["y"], box["y"] - 8, 0.0)
    x1 = min(ink["x"] + ink["w"], box["x"] + box["w"] + 8, float(W))
    y1 = min(ink["y"] + ink["h"], box["y"] + box["h"] + 8, float(HGT))
    if x1 <= x0 or y1 <= y0:
        return None
    return {"x": round(x0, 1), "y": round(y0, 1), "w": round(x1 - x0, 1), "h": round(y1 - y0, 1)}


def _inside(a: dict, b: dict, tol: float = 6) -> bool:
    """bbox a lies inside bbox b."""
    return (a["x"] >= b["x"] - tol and a["y"] >= b["y"] - tol and a["x"] + a["w"] <= b["x"] + b["w"] + tol
            and a["y"] + a["h"] <= b["y"] + b["h"] + tol)


def _area(b: dict) -> float:
    return max(0.0, b["w"]) * max(0.0, b["h"])


def _prices(text: str) -> list[str]:
    return [p.strip() for p in PRICE_RE.findall(text or "") if re.search(r"\d", p)]


def classify(raw: list[dict]) -> list[dict]:
    """Raw browser records -> units with kinds, children, parents, default moves."""
    units = []
    headline_done = False
    for r in raw:
        cls = set(r["cls"])
        text = r["text"]
        b = r["bbox"]
        u = {"id": f"u{r['i'] + 1}", "path": r["path"], "tag": r["tag"], "cls": r["cls"], "level": r["level"],
             "text": text, "own_text": r["own_text"], "bbox": {k: round(v, 1) for k, v in b.items()},
             "ink": _clamp_ink(r.get("ink"), b),
             "font": r["font"], "max_font": r["max_font"], "rotation": _rotation(r["transform"]),
             "transform": r["transform"], "delay_ms": next((int(c[5:]) for c in r["cls"] if re.fullmatch(r"m-at-\d+", c)), 0)}
        if r["level"] == "top" and text and not headline_done and (r["data_hd"] or r["max_font"] >= 48):
            kind = "headline"
            headline_done = True
            u["hl"] = r["hl"]
        elif r["level"] == "top" and text and r["max_font"] < 48 and b["y"] < 230:
            kind = "label"
            u["header"] = True
        elif "m-draw" in cls or r["tag"] == "svg":
            kind = "arrow"
        elif "m-hand" in cls:
            kind = "note"
        elif "m-type" in cls:
            kind = "row"
        elif "m-grow" in cls or "m-growx" in cls:
            kind = "bar"
        elif "m-pop" in cls:
            own_pos = bool(re.search(r"\b(left|top|right|bottom|inset)\s*:", r["style"]))
            kind = "sticker" if own_pos else "container"
        elif r["tag"] in ("img", "video") or (r["media"] and not text):
            kind = "image"
        elif text and b["y"] >= 960 and b["h"] <= 80 and len(text) <= 48:
            kind = "legend"
        elif text:
            kind = "label"
        elif b["w"] <= 220 and b["h"] <= 220 and b["w"] >= 8 and b["h"] >= 8:
            kind = "icon"                # small textless shape; becomes a container below if text sits inside it
        else:
            kind = "zone"            # textless: rails, baselines, panels, hatching (may become container below)
        if kind == "zone" and b["w"] * b["h"] >= 0.85 * W * HGT and not r["media"]:
            u["backdrop"] = True     # a full-frame panel: part of the board's paper, not content
            u["fill"] = r.get("fill")
        u["kind"] = kind
        u["box_like"] = bool(r["border"] or r["has_bg"]) and kind not in ("headline", "arrow", "note", "row")
        if kind == "arrow":
            sh = [s for s in r["shapes"] if s.get("L")]
            u["shapes"] = len(r["shapes"])
            u["stroke_len"] = round(sum(s["L"] for s in sh), 1)
            longest = max(sh, key=lambda s: s["L"], default=None)
            if longest and longest.get("p0") and longest.get("p1"):
                p0, p1 = longest["p0"], longest["p1"]
                d = ((p0["x"] - p1["x"]) ** 2 + (p0["y"] - p1["y"]) ** 2) ** 0.5
                u["ends"] = [[round(p0["x"], 1), round(p0["y"], 1)], [round(p1["x"], 1), round(p1["y"], 1)]]
                # a mostly straight open stroke with few parts is an arrow/connector; a closed loop is a ring; else a drawing
                share = longest["L"] / max(1e-6, sum(s["L"] for s in sh))
                if len(sh) <= 2 and d < 0.35 * longest["L"]:
                    u["stroke"] = "ring"          # a circle / loop around something
                elif share >= 0.5 and d >= 0.45 * longest["L"]:
                    u["stroke"] = "arrow"         # a connector, an underline, an arrow with its short head strokes
                else:
                    u["stroke"] = "drawing"       # a figure, an outline, a sketch
            u["dashed"] = any((s.get("dash") or "none") not in ("none", "") for s in r["shapes"])
        pr = _prices(r["own_text"] or text) or _prices(text)
        if pr:
            u["price"] = pr[0]
            u["prices"] = pr
        units.append(u)

    by_id = {u["id"]: u for u in units}
    # DOM nesting first: the nearest unit ancestor is the parent
    for u in units:
        best = None
        for v in units:
            if v is u or len(v["path"] or []) >= len(u["path"] or []):
                continue
            if u["path"][:len(v["path"])] == v["path"] and (best is None or len(v["path"]) > len(best["path"])):
                best = v
        u["parent"] = best["id"] if best else None
        u["dom_parent"] = bool(best)
    # geometry: a box-like or textless unit that encloses another unit is its container
    canvas = W * HGT
    for u in units:
        if u["parent"] or u["kind"] in ("headline", "legend") or (u["kind"] == "label" and u.get("header")):
            continue
        best = None
        for v in units:
            if v is u or v["kind"] in ("headline", "arrow", "legend", "note", "row") or _area(v["bbox"]) > 0.6 * canvas:
                continue
            if v["kind"] == "label" and not v["box_like"]:
                continue
            if _area(v["bbox"]) <= _area(u["bbox"]) or not _inside(u["bbox"], v["bbox"]):
                continue
            if u["path"][:len(v["path"])] == v["path"]:
                continue
            if best is None or _area(v["bbox"]) < _area(best["bbox"]):
                best = v
        if best:
            u["parent"] = best["id"]
    for u in units:
        u["children"] = [v["id"] for v in units if v.get("parent") == u["id"]]
    for u in units:
        kids = [by_id[c] for c in u["children"]]
        if u["kind"] == "zone" and kids:
            u["kind"] = "container"
        elif u["kind"] == "icon" and any(k["text"] for k in kids):
            u["kind"] = "container"
        elif u["kind"] == "label" and kids:
            u["kind"] = "container"
    for u in units:
        mv = DEFAULT_MOVE[u["kind"]]
        if u["kind"] == "label" and u.get("header"):
            mv = "label"
        if u["kind"] == "bar" and "m-growx" in u["cls"]:
            mv = "growx"
        if u.get("backdrop"):
            mv = "label"
        u["default_move"] = mv
        u["in_camera_zone"] = _overlaps_zone(u["bbox"]) and u["kind"] not in ("headline",)
    return units


def _overlaps_zone(b: dict) -> bool:
    z = common.CAM_ZONE_1080
    return b["x"] < z["x"] + z["w"] and z["x"] < b["x"] + b["w"] and b["y"] < z["y"] + z["h"] and z["y"] < b["y"] + b["h"]


# ───────────────────────── entry points ─────────────────────────
def board_number(path) -> int | None:
    m = re.match(r"^(\d+)", Path(path).name)
    return int(m.group(1)) if m else None


def board_files(boards_dir) -> dict[int, Path]:
    out: dict[int, Path] = {}
    for p in sorted(Path(boards_dir).glob("*.htm*")):
        n = board_number(p)
        if n is None:
            continue
        if n in out:
            common.log(f"units: two boards numbered {n:02d} ({out[n].name}, {p.name}); using {out[n].name}")
            continue
        out[n] = p
    return out


def parse_board(path, page, work_dir=None) -> dict:
    """Measure one board in an open Playwright page. work_dir holds the temporary measuring page (default: next to
    the board's units output or the board itself)."""
    path = Path(path).resolve()
    board = read_board(path)
    if work_dir is None:
        import tempfile
        work_dir = tempfile.mkdtemp(prefix="board-sync-")
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    tmp = work / f"_measure-{path.stem}.html"
    tmp.write_text(static_page(board), encoding="utf-8")
    try:
        page.set_viewport_size({"width": W, "height": HGT})
        page.goto(tmp.resolve().as_uri(), wait_until="load")
        page.evaluate("async () => { await document.fonts.ready; await Promise.all(Array.from(document.fonts).map(f => f.status === 'unloaded' ? f.load().catch(() => {}) : 0)); await document.fonts.ready; }")
        data = page.evaluate(EXTRACT_JS)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    if data.get("error"):
        raise SystemExit(f"{path.name}: {data['error']}")
    units = classify(data["units"])
    head = next((u for u in units if u["kind"] == "headline"), None)
    return {"n": board_number(path), "file": path.name, "path": str(path), "title": board["title"],
            "headline": head["text"] if head else "", "bg": board["bg"], "size": [W, HGT], "units": units,
            "camera_zone_hits": [u["id"] for u in units if u["in_camera_zone"]]}


def _get(ctx, name, default=None):
    if isinstance(ctx, dict):
        return ctx.get(name, default)
    return getattr(ctx, name, default)


def _only(ctx) -> set[int] | None:
    only = _get(ctx, "only")
    if not only:
        return None
    if isinstance(only, str):
        return {int(x) for x in re.findall(r"\d+", only)}
    return {int(x) for x in only}


def run(ctx, numbers=None) -> dict:
    """Parse every board (or ctx.only, or the given numbers) into <out>/units/NN.json."""
    from playwright.sync_api import sync_playwright
    out = Path(_get(ctx, "out"))
    files = board_files(_get(ctx, "boards"))
    if not files:
        raise SystemExit(f"units: no board HTML files (NN-Name.html) in {_get(ctx, 'boards')}")
    want = set(numbers) if numbers else _only(ctx)
    todo = {n: p for n, p in files.items() if want is None or n in want}
    (out / "units").mkdir(parents=True, exist_ok=True)
    done = {}
    with sync_playwright() as pw:
        browser = launch_browser(pw)
        page = browser.new_page(viewport={"width": W, "height": HGT}, device_scale_factor=1)
        for n, p in sorted(todo.items()):
            data = parse_board(p, page, work_dir=out / "units")
            common.write_json(out / "units" / f"{n:02d}.json", data)
            kinds = {}
            for u in data["units"]:
                kinds[u["kind"]] = kinds.get(u["kind"], 0) + 1
            zone = f"; in the camera zone: {', '.join(data['camera_zone_hits'])}" if data["camera_zone_hits"] else ""
            common.log(f"units: board {n:02d} {p.name}: {len(data['units'])} units "
                       f"({', '.join(f'{v} {k}' for k, v in sorted(kinds.items()))}){zone}")
            done[n] = data
        browser.close()
    return done


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Parse board HTMLs into units JSON (prints one board when given a file).")
    ap.add_argument("board")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = launch_browser(pw)
        pg = b.new_page(viewport={"width": W, "height": HGT})
        print(json.dumps(parse_board(a.board, pg), ensure_ascii=False, indent=1))
        b.close()
