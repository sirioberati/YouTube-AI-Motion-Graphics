"""Read timeline.fcpxml and timeline-premiere.xml back and print every clip: track, in/out on the timeline (frames and
timecode), source in, scale, position, and the camera box's pixel edges in the 3840x2160 frame, so a human can check
the 80 px margins and the cuts without opening an editor.

    python scripts/timeline_check.py <out folder | timeline.fcpxml | timeline-premiere.xml> [--all]

By default it prints the first 6 clips of each track and a summary; --all prints every clip.
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

SEQ_W, SEQ_H = 3840, 2160

for _stream in (sys.stdout, sys.stderr):   # Windows pipes default to cp1252: never crash printing "▸", "→" or "’"
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def tc(frames: int, fps: Fraction) -> str:
    base = int(round(float(fps)))
    f = frames % base
    s = frames // base
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{f:02d}"


def rt(s: str | None) -> Fraction:
    """FCPXML rational time '1001/24000s' -> seconds as a Fraction."""
    if not s:
        return Fraction(0)
    s = s.rstrip("s")
    if "/" in s:
        n, d = s.split("/")
        return Fraction(int(n), int(d))
    return Fraction(s)


def box(cx_off: float, cy_off_down: float, scale: float, src_w: float = SEQ_W, src_h: float = SEQ_H) -> str:
    """Pixel edges of a scaled clip whose centre sits at the given offset from the frame centre (y down)."""
    w, h = src_w * scale, src_h * scale
    cx, cy = SEQ_W / 2 + cx_off, SEQ_H / 2 + cy_off_down
    left, top, right, bottom = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    return (f"box x {left:.1f}-{right:.1f}, y {top:.1f}-{bottom:.1f} ({w:.1f}x{h:.1f}); "
            f"right margin {SEQ_W - right:.1f} px, bottom margin {SEQ_H - bottom:.1f} px")


def check_fcpxml(p: Path, show_all: bool) -> None:
    root = ET.parse(p).getroot()
    fmts = {f.get("id"): f for f in root.iter("format")}
    assets = {a.get("id"): a for a in root.iter("asset")}
    seq = next(root.iter("sequence"))
    f = fmts[seq.get("format")]
    fps = 1 / rt(f.get("frameDuration"))
    total = int(round(rt(seq.get("duration")) * fps))
    print(f"\n{p.name}: FCPXML {root.get('version')}, sequence {f.get('width')}x{f.get('height')} @ "
          f"{fps.numerator}/{fps.denominator}, {total} frames ({tc(total, fps)})")
    spine = seq.find("spine")
    rows: dict[str, list[str]] = {}
    for parent in spine:
        clips = [(parent, "V1 (spine)")] + [(c, f"lane {c.get('lane')}") for c in parent if c.tag in ("asset-clip", "clip")]
        base = rt(parent.get("offset")) - rt(parent.get("start"))
        for c, where in clips:
            a = assets.get(c.get("ref"))
            a_fmt = fmts.get(a.get("format")) if a is not None else None
            off = rt(c.get("offset")) + (base if c is not parent else 0)
            f0 = int(round(off * fps))
            n = int(round(rt(c.get("duration")) * fps))
            src = int(round(rt(c.get("start")) * fps))
            tr = c.find("adjust-transform")
            conform = c.find("adjust-conform")
            line = f"  {tc(f0, fps)} -> {tc(f0 + n, fps)}  frames {f0}-{f0 + n} (src in {src})  {c.get('name', '')[:60]}"
            if a is not None and a.get("hasVideo") == "1":
                sw = float(a_fmt.get("width")) if a_fmt is not None else SEQ_W
                sh = float(a_fmt.get("height")) if a_fmt is not None else SEQ_H
                fit = min(SEQ_W / sw, SEQ_H / sh) if (conform is None or conform.get("type", "fit") == "fit") else 1.0
                if tr is not None:
                    sc = float(tr.get("scale", "1 1").split()[0])
                    px, py = (float(x) for x in tr.get("position", "0 0").split())
                    # FCPXML: position in % of frame height, y up
                    dx, dy_down = px / 100 * SEQ_H, -py / 100 * SEQ_H
                    line += f"\n      scale {sc:g} (x conform {fit:g}), position {px:g} {py:g} -> {box(dx, dy_down, sc * fit, sw, sh)}"
                else:
                    line += f"\n      no transform; conform fit x{fit:g} -> {sw * fit:.0f}x{sh * fit:.0f}"
                if c.get("srcEnable"):
                    line += f"; srcEnable={c.get('srcEnable')}"
                if c.get("enabled") == "0":
                    line += "; disabled (hidden)"
            else:
                line += f"  [audio{', role ' + c.get('audioRole') if c.get('audioRole') else ''}]"
            rows.setdefault(where, []).append(line)
    for where, lines in rows.items():
        print(f" {where}: {len(lines)} clip(s)")
        for line in (lines if show_all else lines[:6]):
            print(line)
        if not show_all and len(lines) > 6:
            print(f"  ... {len(lines) - 6} more (--all to list)")
    _contiguity(rows.get("lane 1", []), total, "lane 1 (cam)")
    if "lane 2" in rows:
        _contiguity(rows["lane 2"], total, "lane 2 (matte)")
        same = [re.search(r"frames \S+", x).group(0) for x in rows["lane 1"]] == \
               [re.search(r"frames \S+", x).group(0) for x in rows["lane 2"]]
        print(f" matte pieces line up with the cam clips: {'yes' if same else 'NO'}")


def _contiguity(lines: list[str], total: int, label: str) -> None:
    spans = [tuple(map(int, m.groups())) for m in (re.search(r"frames (\d+)-(\d+)", x) for x in lines) if m]
    if not spans:
        return
    gaps = [(a1, b0) for (a0, a1), (b0, b1) in zip(spans, spans[1:]) if b0 != a1]
    ok = spans[0][0] == 0 and spans[-1][1] == total and not gaps
    print(f" {label}: {'covers 0-' + str(total) + ' with no gaps or overlaps' if ok else 'GAPS/OVERLAPS: ' + str(gaps[:5]) + f' first {spans[0]}, last {spans[-1]}'}")


def check_fcp7(p: Path, show_all: bool) -> None:
    root = ET.parse(p).getroot()
    seq = root.find("sequence")
    rate = seq.find("rate")
    tb = int(rate.findtext("timebase"))
    fps = Fraction(tb * 1000, 1001) if rate.findtext("ntsc") == "TRUE" else Fraction(tb)
    total = int(seq.findtext("duration"))
    sc = seq.find("media/video/format/samplecharacteristics")
    print(f"\n{p.name}: xmeml {root.get('version')}, sequence {sc.findtext('width')}x{sc.findtext('height')} @ "
          f"{fps.numerator}/{fps.denominator}, {total} frames ({tc(total, fps)})")
    files: dict[str, ET.Element] = {}
    for f in root.iter("file"):
        if f.find("name") is not None:
            files[f.get("id")] = f
    for kind in ("video", "audio"):
        for i, track in enumerate(seq.findall(f"media/{kind}/track"), start=1):
            items = track.findall("clipitem")
            label = f"{'V' if kind == 'video' else 'A'}{i}"
            hidden = " (track output off: hidden)" if track.findtext("enabled") == "FALSE" else ""
            print(f" {label}: {len(items)} clip(s){hidden}")
            lines = []
            for c in items:
                f0, f1 = int(c.findtext("start")), int(c.findtext("end"))
                line = f"  {tc(f0, fps)} -> {tc(f1, fps)}  frames {f0}-{f1} (src in {c.findtext('in')})  {c.findtext('name')[:60]}"
                eff = c.find("filter/effect")
                if kind == "video" and eff is not None:
                    params = {p_.findtext("parameterid"): p_ for p_ in eff.findall("parameter")}
                    s = float(params["scale"].findtext("value")) / 100 if "scale" in params else 1.0
                    h = float(params["center"].findtext("value/horiz")) if "center" in params else 0.0
                    v = float(params["center"].findtext("value/vert")) if "center" in params else 0.0
                    fid = c.find("file").get("id")
                    fe = files.get(fid)
                    sw = float(fe.findtext("media/video/samplecharacteristics/width") or SEQ_W) if fe is not None else SEQ_W
                    sh = float(fe.findtext("media/video/samplecharacteristics/height") or SEQ_H) if fe is not None else SEQ_H
                    # FCP7: center normalised per axis to the sequence frame, y down
                    line += f"\n      scale {s * 100:g} %, center {h:g} {v:g} -> {box(h * SEQ_W, v * SEQ_H, s, sw, sh)}"
                lines.append(line)
            for line in (lines if show_all else lines[:6]):
                print(line)
            if not show_all and len(lines) > 6:
                print(f"  ... {len(lines) - 6} more (--all to list)")
            if kind == "video" and i >= 2:
                _contiguity(lines, total, label)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    p = Path(a.path)
    targets = [p / "timeline.fcpxml", p / "timeline-premiere.xml"] if p.is_dir() else [p]
    for t in targets:
        if not t.exists():
            print(f"missing: {t}")
            continue
        root_tag = ET.parse(t).getroot().tag
        (check_fcpxml if root_tag == "fcpxml" else check_fcp7)(t, a.all)
    return 0


if __name__ == "__main__":
    sys.exit(main())
