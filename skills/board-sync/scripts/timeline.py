"""Stage `timeline`: windows.json -> timeline.fcpxml (DaVinci Resolve, FCPXML 1.9) + timeline-premiere.xml (Premiere,
FCP7 XML / xmeml version 5).

The timeline (3840x2160 at the cut's 24000/1001, as long as the WAV):
  V1  board-track.mp4 (1920x1080), one clip from 0, scaled 200 % to fill the 4K frame.
  V2  the 4K final cut, cut at every window: on board windows scaled 32 % and parked in the bottom-right camera zone,
      80 px from the right and bottom edges; on camera windows 100 %, centred. Its own audio is disabled.
  V3  only when the editor passes --mask (the background is kept otherwise): the cutout luma matte, split at the same
      frames as V2 with the same scale and position, so every cam clip has its matte piece lined up directly above
      it. Hidden by default (Premiere: the track's output is off, the clips stay enabled so a Track Matte Key can
      read them; Resolve: the clips are disabled). sync-manifest.md gets the keying lines for both editors.
  A1  the final-cut WAV, one clip from 0, no effects, gain 0 dB.

Why the cut is on V2 and the boards on V1 (DESIGN.md lists them the other way round): video tracks stack upward, so
with the board track above the cut the camera would be hidden under the board on every board window. With the boards
underneath, the camera box sits on top of them, and on camera windows the full-frame cut covers the board track's black.

Position maths (the camera box, both formats)
  Sequence 3840 x 2160. Scale 0.32 -> the 16:9 cut becomes 1228.8 x 691.2 px. Its bottom-right corner goes 80 px in from
  the right and bottom edges: right edge x = 3840 - 80 = 3760, bottom edge y = 2160 - 80 = 2080 (y down from the top).
  Box centre (y down) = (3760 - 1228.8/2, 2080 - 691.2/2) = (3145.6, 1734.4); offset from the frame centre (1920, 1080)
  = (+1225.6 px right, +654.4 px down). The box lies inside the 1230 x 860 camera zone (x >= 2530, y >= 1220); the top
  168.8 px of the zone stay free.
  FCPXML  <adjust-transform position="x y">: origin at the frame centre, y UP, and the unit is 1 % of the FRAME HEIGHT
          (Apple's FCPXML DTD: "position ... expressed as a percentage of frame height", for both x and y).
          x = 1225.6 / 2160 * 100 = 56.7407, y = -654.4 / 2160 * 100 = -30.2963. scale="0.32 0.32" (a factor).
          The board track carries no scale: FCPXML's default spatial conform ("fit") already takes 1920x1080 to the
          4K frame, which is the 200 %; an explicit scale="2 2" on top of the conform would make it 400 %.
  FCP7    Basic Motion <center><horiz/><vert/>: origin at the frame centre, y DOWN, normalised per axis to the frame:
          horiz = 1225.6 / 3840 = 0.319167, vert = 654.4 / 2160 = 0.302963 (0.5 would be the right/bottom edge).
          scale is in percent: 32 for the camera box, 100 full frame, 200 for the 1080p board track (Premiere does not
          auto-scale a clip to the sequence size, so the 200 % is explicit here).
  scripts/timeline_check.py reads both files back and prints each clip's in/out, scale, position and the camera
  box's pixel edges, so the 80 px margins can be checked without an editor.
"""
from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.common import CAM_ZONE_4K, log, parse_fps, probe_duration, read_json, run as run_cmd, which_ffmpeg  # noqa: E402

SEQ_W, SEQ_H = 3840, 2160
MARGIN = 80                     # px from the right and bottom edges at 4K (40 px at 1080p)
CAM_SCALE = 0.32                # 32 % of the frame
BOARD_W, BOARD_H = 1920, 1080   # board-track.mp4

# camera box geometry (see the module docstring)
CAM_W, CAM_H = SEQ_W * CAM_SCALE, SEQ_H * CAM_SCALE                       # 1228.8 x 691.2
CAM_CX, CAM_CY = SEQ_W - MARGIN - CAM_W / 2, SEQ_H - MARGIN - CAM_H / 2   # 3145.6, 1734.4 (y down)
CAM_DX, CAM_DY = CAM_CX - SEQ_W / 2, CAM_CY - SEQ_H / 2                   # +1225.6, +654.4 (y down)
assert CAM_CX - CAM_W / 2 >= CAM_ZONE_4K["x"] and CAM_CY - CAM_H / 2 >= CAM_ZONE_4K["y"], "camera box outside the zone"

FORMAT_NAMES = {Fraction(24000, 1001): "2398", Fraction(24): "24", Fraction(25): "25", Fraction(30000, 1001): "2997",
                Fraction(30): "30", Fraction(50): "50", Fraction(60000, 1001): "5994", Fraction(60): "60"}


def fcpxml_position() -> tuple[float, float]:
    """Camera box offset for FCPXML: % of frame height, y up."""
    return round(CAM_DX / SEQ_H * 100, 4), round(-CAM_DY / SEQ_H * 100, 4)


def fcp7_center() -> tuple[float, float]:
    """Camera box centre for FCP7 Basic Motion: fraction of the frame per axis, y down."""
    return round(CAM_DX / SEQ_W, 6), round(CAM_DY / SEQ_H, 6)


# ── media facts ───────────────────────────────────────────────────────────────────────────────────────────────────
def probe(path: Path) -> dict:
    """Width/height/duration/audio of a media file (ffprobe), {} when it does not exist yet."""
    if not path or not Path(path).exists():
        return {}
    try:
        r = run_cmd([which_ffmpeg("ffprobe"), "-v", "error", "-show_entries",
                     "format=duration:format_tags=timecode:stream=codec_type,width,height,sample_rate,channels:stream_tags=timecode",
                     "-of", "json", path])
        d = json.loads(r.stdout)
    except Exception:
        return {}
    out: dict = {"duration": float(d.get("format", {}).get("duration", 0) or 0)}
    tc = (d.get("format", {}).get("tags", {}) or {}).get("timecode")
    for s in d.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in out:
            out["width"], out["height"] = s.get("width"), s.get("height")
            tc = tc or (s.get("tags", {}) or {}).get("timecode")
        if s.get("codec_type") == "audio" and "channels" not in out:
            out["channels"] = int(s.get("channels") or 2)
            out["rate"] = int(s.get("sample_rate") or 48000)
    if tc:
        out["timecode"] = tc
    return out


def tc_frames(tc: str, fps: Fraction) -> int:
    """'01:00:00:00' -> frames at the nominal rate (NDF)."""
    m = re.match(r"^(\d+):(\d+):(\d+)[:;.](\d+)$", tc or "")
    if not m:
        return 0
    base = int(round(float(fps)))
    h, mi, s, f = map(int, m.groups())
    return ((h * 60 + mi) * 60 + s) * base + f


def project_name(wav: Path) -> str:
    stem = wav.stem
    return re.sub(r"\s*-\s*final cut$", "", stem, flags=re.I).strip() or stem


def cut_path(ctx, name: str) -> Path:
    if getattr(ctx, "cut", None):
        return Path(ctx.cut)
    return Path(ctx.wav).parent / f"{name} - final cut.mp4"   # placeholder: relink in the editor if it is elsewhere


def segments(win: dict, fps: Fraction, total: int) -> list[dict]:
    """Windows as frame ranges [f0, f1) covering 0..total with no gaps."""
    items = win["items"]
    starts = [min(int(round(it["start"] * fps)), total) for it in items]
    segs = []
    for i, it in enumerate(items):
        f0 = starts[i]
        f1 = starts[i + 1] if i + 1 < len(items) else total
        if f1 <= f0:
            continue
        label = f"board {it['n']}" if it["kind"] == "board" else "camera"
        if it["kind"] == "board" and it.get("title"):
            label += f" · {it['title']}"
        segs.append({"kind": it["kind"], "f0": f0, "f1": f1, "label": label, "n": it.get("n")})
    return segs


def _uri(p: Path) -> str:
    """file:// URL of an absolute path, symlinks kept (percent-encoded; file:///C:/... on Windows)."""
    return Path(os.path.abspath(p)).as_uri()


# ── FCPXML 1.9 (DaVinci Resolve) ──────────────────────────────────────────────────────────────────────────────────
def write_fcpxml(path: Path, *, name: str, fps: Fraction, total: int, segs: list[dict], cut: Path, cut_info: dict,
                 track: Path, wav: Path, wav_info: dict, mask: Path | None = None, mask_info: dict | None = None) -> None:
    def t(frames: int) -> str:
        return "0s" if frames == 0 else f"{frames * fps.denominator}/{fps.numerator}s"

    fd = f"{fps.denominator}/{fps.numerator}s"
    tag = FORMAT_NAMES.get(fps)
    root = ET.Element("fcpxml", version="1.9")
    res = ET.SubElement(root, "resources")
    f4k = {"id": "r1", "frameDuration": fd, "width": str(SEQ_W), "height": str(SEQ_H), "colorSpace": "1-1-1 (Rec. 709)"}
    if tag:
        f4k["name"] = f"FFVideoFormat3840x2160p{tag}"
    ET.SubElement(res, "format", f4k)
    fhd = {"id": "r2", "frameDuration": fd, "width": str(BOARD_W), "height": str(BOARD_H), "colorSpace": "1-1-1 (Rec. 709)"}
    if tag:
        fhd["name"] = f"FFVideoFormat1080p{tag}"
    ET.SubElement(res, "format", fhd)
    cut_w, cut_h = cut_info.get("width") or SEQ_W, cut_info.get("height") or SEQ_H
    cut_fmt = "r1"
    if (cut_w, cut_h) != (SEQ_W, SEQ_H):
        ET.SubElement(res, "format", {"id": "r6", "frameDuration": fd, "width": str(cut_w), "height": str(cut_h),
                                      "colorSpace": "1-1-1 (Rec. 709)"})
        cut_fmt = "r6"
    cut_tc = tc_frames(cut_info.get("timecode", ""), fps)
    cut_len = max(total, int(round(cut_info.get("duration", 0) * fps)))
    a_cut = ET.SubElement(res, "asset", {"id": "r3", "name": cut.stem, "start": t(cut_tc), "duration": t(cut_len),
                                         "hasVideo": "1", "format": cut_fmt, "hasAudio": "1", "audioSources": "1",
                                         "audioChannels": str(cut_info.get("channels", 2)),
                                         "audioRate": str(cut_info.get("rate", 48000))})
    ET.SubElement(a_cut, "media-rep", {"kind": "original-media", "src": _uri(cut)})
    a_trk = ET.SubElement(res, "asset", {"id": "r4", "name": track.stem, "start": "0s", "duration": t(total),
                                         "hasVideo": "1", "format": "r2", "hasAudio": "0"})
    ET.SubElement(a_trk, "media-rep", {"kind": "original-media", "src": _uri(track)})
    wav_len = max(total, int(round(wav_info.get("duration", 0) * fps)))
    a_wav = ET.SubElement(res, "asset", {"id": "r5", "name": wav.stem, "start": "0s", "duration": t(wav_len),
                                         "hasVideo": "0", "hasAudio": "1", "audioSources": "1",
                                         "audioChannels": str(wav_info.get("channels", 2)),
                                         "audioRate": str(wav_info.get("rate", 48000))})
    ET.SubElement(a_wav, "media-rep", {"kind": "original-media", "src": _uri(wav)})
    mask_info = mask_info or {}
    if mask is not None:
        m_w, m_h = mask_info.get("width") or cut_w, mask_info.get("height") or cut_h
        m_fmt = "r1" if (m_w, m_h) == (SEQ_W, SEQ_H) else ("r2" if (m_w, m_h) == (BOARD_W, BOARD_H) else "r8")
        if m_fmt == "r8":
            ET.SubElement(res, "format", {"id": "r8", "frameDuration": fd, "width": str(m_w), "height": str(m_h),
                                          "colorSpace": "1-1-1 (Rec. 709)"})
        m_tc = tc_frames(mask_info.get("timecode", ""), fps)
        m_len = max(total, int(round(mask_info.get("duration", 0) * fps)))
        a_mask = ET.SubElement(res, "asset", {"id": "r7", "name": mask.stem, "start": t(m_tc), "duration": t(m_len),
                                              "hasVideo": "1", "format": m_fmt, "hasAudio": "0"})
        ET.SubElement(a_mask, "media-rep", {"kind": "original-media", "src": _uri(mask)})

    lib = ET.SubElement(root, "library")
    ev = ET.SubElement(lib, "event", name=f"{name} - board-sync")
    proj = ET.SubElement(ev, "project", name=f"{name} - board-sync")
    seq = ET.SubElement(proj, "sequence", {"format": "r1", "duration": t(total), "tcStart": "0s", "tcFormat": "NDF",
                                           "audioLayout": "stereo", "audioRate": "48k"})
    spine = ET.SubElement(seq, "spine")
    # V1: the board track (primary storyline). Default conform "fit" scales 1920x1080 to 3840x2160 (= 200 %).
    boards = ET.SubElement(spine, "asset-clip", {"ref": "r4", "offset": "0s", "name": track.stem, "start": "0s",
                                                  "duration": t(total), "format": "r2", "tcFormat": "NDF"})
    ET.SubElement(boards, "adjust-conform", type="fit")
    # V2: the cut, one connected clip per window (lane 1 = above the board track); video only.
    px, py = fcpxml_position()
    for s in segs:
        clip = ET.SubElement(boards, "asset-clip", {"ref": "r3", "lane": "1", "offset": t(s["f0"]),
                                                     "name": f"{cut.stem} · {s['label']}", "start": t(cut_tc + s["f0"]),
                                                     "duration": t(s["f1"] - s["f0"]), "format": cut_fmt,
                                                     "tcFormat": "NDF", "srcEnable": "video"})
        if s["kind"] == "board":
            ET.SubElement(clip, "adjust-transform", {"position": f"{px} {py}", "scale": f"{CAM_SCALE} {CAM_SCALE}"})
        else:
            ET.SubElement(clip, "adjust-transform", {"position": "0 0", "scale": "1 1"})
        ET.SubElement(clip, "adjust-volume", amount="-96dB")   # belt and braces: its audio is off even if enabled
    # V3: the matte, lane 2 (directly above the cam), same cuts and transform as the cam, disabled (hidden).
    if mask is not None:
        for s in segs:
            mc = ET.SubElement(boards, "asset-clip", {"ref": "r7", "lane": "2", "offset": t(s["f0"]),
                                                       "name": f"{mask.stem} · {s['label']}", "start": t(m_tc + s["f0"]),
                                                       "duration": t(s["f1"] - s["f0"]), "format": m_fmt,
                                                       "tcFormat": "NDF", "enabled": "0"})
            if s["kind"] == "board":
                ET.SubElement(mc, "adjust-transform", {"position": f"{px} {py}", "scale": f"{CAM_SCALE} {CAM_SCALE}"})
            else:
                ET.SubElement(mc, "adjust-transform", {"position": "0 0", "scale": "1 1"})
    # A1: the WAV under everything (lane -1), no effects, 0 dB.
    ET.SubElement(boards, "asset-clip", {"ref": "r5", "lane": "-1", "offset": "0s", "name": wav.stem, "start": "0s",
                                         "duration": t(total), "audioRole": "dialogue"})
    for s in segs:
        if s["kind"] == "board":
            ET.SubElement(boards, "marker", {"start": t(s["f0"]), "duration": fd, "value": s["label"]})
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n' + body + "\n", encoding="utf-8")


# ── FCP7 XML / xmeml v5 (Premiere) ────────────────────────────────────────────────────────────────────────────────
def _rate(parent, fps: Fraction) -> None:
    r = ET.SubElement(parent, "rate")
    ET.SubElement(r, "timebase").text = str(int(round(float(fps))))
    ET.SubElement(r, "ntsc").text = "TRUE" if fps.denominator == 1001 else "FALSE"


def _pathurl(p: Path) -> str:
    return _uri(p).replace("file:///", "file://localhost/", 1)


def _motion(parent, scale: float, horiz: float, vert: float) -> None:
    flt = ET.SubElement(parent, "filter")
    eff = ET.SubElement(flt, "effect")
    for k, v in (("name", "Basic Motion"), ("effectid", "basic"), ("effectcategory", "motion"),
                 ("effecttype", "motion"), ("mediatype", "video")):
        ET.SubElement(eff, k).text = v

    def param(pid, name, value=None, vmin=None, vmax=None, point=None):
        p = ET.SubElement(eff, "parameter", authoringApp="PremierePro")
        ET.SubElement(p, "parameterid").text = pid
        ET.SubElement(p, "name").text = name
        if vmin is not None:
            ET.SubElement(p, "valuemin").text = str(vmin)
            ET.SubElement(p, "valuemax").text = str(vmax)
        v = ET.SubElement(p, "value")
        if point is not None:
            ET.SubElement(v, "horiz").text = f"{point[0]:g}"
            ET.SubElement(v, "vert").text = f"{point[1]:g}"
        else:
            v.text = f"{value:g}"

    param("scale", "Scale", scale, 0, 1000)
    param("rotation", "Rotation", 0, -8640, 8640)
    param("center", "Center", point=(horiz, vert))
    param("centerOffset", "Anchor Point", point=(0, 0))


def _file(parent, fid: str, p: Path, fps: Fraction, frames: int, *, video: tuple | None, audio: tuple | None,
          full: bool) -> None:
    f = ET.SubElement(parent, "file", id=fid)
    if not full:
        return
    ET.SubElement(f, "name").text = p.name
    ET.SubElement(f, "pathurl").text = _pathurl(p)
    _rate(f, fps)
    ET.SubElement(f, "duration").text = str(frames)
    media = ET.SubElement(f, "media")
    if video:
        v = ET.SubElement(media, "video")
        sc = ET.SubElement(v, "samplecharacteristics")
        _rate(sc, fps)
        ET.SubElement(sc, "width").text = str(video[0])
        ET.SubElement(sc, "height").text = str(video[1])
        ET.SubElement(sc, "anamorphic").text = "FALSE"
        ET.SubElement(sc, "pixelaspectratio").text = "square"
        ET.SubElement(sc, "fielddominance").text = "none"
    if audio:
        a = ET.SubElement(media, "audio")
        sc = ET.SubElement(a, "samplecharacteristics")
        ET.SubElement(sc, "depth").text = "16"
        ET.SubElement(sc, "samplerate").text = str(audio[0])
        ET.SubElement(a, "channelcount").text = str(audio[1])


def _clipitem(track, cid: str, name: str, fps: Fraction, src_frames: int, f0: int, f1: int, src_in: int) -> ET.Element:
    c = ET.SubElement(track, "clipitem", id=cid)
    ET.SubElement(c, "name").text = name
    ET.SubElement(c, "enabled").text = "TRUE"
    ET.SubElement(c, "duration").text = str(src_frames)
    _rate(c, fps)
    ET.SubElement(c, "start").text = str(f0)
    ET.SubElement(c, "end").text = str(f1)
    ET.SubElement(c, "in").text = str(src_in)
    ET.SubElement(c, "out").text = str(src_in + (f1 - f0))
    return c


def write_fcp7(path: Path, *, name: str, fps: Fraction, total: int, segs: list[dict], cut: Path, cut_info: dict,
               track: Path, wav: Path, wav_info: dict, mask: Path | None = None, mask_info: dict | None = None) -> None:
    root = ET.Element("xmeml", version="5")
    seq = ET.SubElement(root, "sequence", id="sequence-1")
    ET.SubElement(seq, "name").text = f"{name} - board-sync"
    ET.SubElement(seq, "duration").text = str(total)
    _rate(seq, fps)
    tc = ET.SubElement(seq, "timecode")
    _rate(tc, fps)
    ET.SubElement(tc, "string").text = "00:00:00:00"
    ET.SubElement(tc, "frame").text = "0"
    ET.SubElement(tc, "displayformat").text = "NDF"
    media = ET.SubElement(seq, "media")
    video = ET.SubElement(media, "video")
    fmt = ET.SubElement(ET.SubElement(video, "format"), "samplecharacteristics")
    _rate(fmt, fps)
    for k, v in (("width", SEQ_W), ("height", SEQ_H), ("anamorphic", "FALSE"), ("pixelaspectratio", "square"),
                 ("fielddominance", "none"), ("colordepth", 24)):
        ET.SubElement(fmt, k).text = str(v)

    # V1: board track, 200 % (Premiere keeps a 1080p clip at 100 % in a 4K sequence unless told otherwise)
    v1 = ET.SubElement(video, "track")
    c = _clipitem(v1, "clipitem-1", track.name, fps, total, 0, total, 0)
    _file(c, "file-1", track, fps, total, video=(BOARD_W, BOARD_H), audio=None, full=True)
    _motion(c, 100 * SEQ_W / BOARD_W, 0, 0)   # = 200 %
    ET.SubElement(v1, "enabled").text = "TRUE"
    ET.SubElement(v1, "locked").text = "FALSE"

    # V2: the cut per window. No <link> to its audio and no audio clipitem: its own sound is left out.
    cut_w = cut_info.get("width") or SEQ_W
    k = SEQ_W / cut_w                                   # 1 for a 4K cut, 2 for a 1080p one
    cut_tc = tc_frames(cut_info.get("timecode", ""), fps)
    cut_len = max(total, int(round(cut_info.get("duration", 0) * fps)))
    hz, vt = fcp7_center()
    v2 = ET.SubElement(video, "track")
    for i, s in enumerate(segs):
        c = _clipitem(v2, f"clipitem-{i + 2}", f"{cut.stem} · {s['label']}", fps, cut_len, s["f0"], s["f1"],
                      cut_tc + s["f0"])
        _file(c, "file-2", cut, fps, cut_len, video=(cut_w, cut_info.get("height") or SEQ_H), audio=None, full=(i == 0))
        if s["kind"] == "board":
            _motion(c, round(CAM_SCALE * 100 * k, 4), hz, vt)
        else:
            _motion(c, round(100 * k, 4), 0, 0)
    ET.SubElement(v2, "enabled").text = "TRUE"
    ET.SubElement(v2, "locked").text = "FALSE"

    # V3: the matte directly above the cam, same cuts and Basic Motion; track output off (hidden), clips enabled so
    # Premiere's Track Matte Key (matte = the track above) can read them.
    n_mask = 0
    if mask is not None:
        mask_info = mask_info or {}
        m_w = mask_info.get("width") or cut_w
        mk = SEQ_W / m_w
        m_tc = tc_frames(mask_info.get("timecode", ""), fps)
        m_len = max(total, int(round(mask_info.get("duration", 0) * fps)))
        v3 = ET.SubElement(video, "track")
        for i, s in enumerate(segs):
            c = _clipitem(v3, f"clipitem-m{i + 1}", f"{mask.stem} · {s['label']}", fps, m_len, s["f0"], s["f1"],
                          m_tc + s["f0"])
            _file(c, "file-4", mask, fps, m_len, video=(m_w, mask_info.get("height") or round(m_w * SEQ_H / SEQ_W)),
                  audio=None, full=(i == 0))
            if s["kind"] == "board":
                _motion(c, round(CAM_SCALE * 100 * mk, 4), hz, vt)
            else:
                _motion(c, round(100 * mk, 4), 0, 0)
            n_mask += 1
        ET.SubElement(v3, "enabled").text = "FALSE"
        ET.SubElement(v3, "locked").text = "FALSE"

    # A1: the WAV, no effects
    audio = ET.SubElement(media, "audio")
    ET.SubElement(audio, "numOutputChannels").text = "2"
    afmt = ET.SubElement(ET.SubElement(audio, "format"), "samplecharacteristics")
    ET.SubElement(afmt, "depth").text = "16"
    ET.SubElement(afmt, "samplerate").text = str(wav_info.get("rate", 48000))
    ch = int(wav_info.get("channels", 2))
    a1 = ET.SubElement(audio, "track", premiereTrackType="Stereo" if ch == 2 else "Mono")
    wav_len = max(total, int(round(wav_info.get("duration", 0) * fps)))
    c = _clipitem(a1, f"clipitem-{len(segs) + 2}", wav.name, fps, wav_len, 0, total, 0)
    _file(c, "file-3", wav, fps, wav_len, video=None, audio=(wav_info.get("rate", 48000), ch), full=True)
    st = ET.SubElement(c, "sourcetrack")
    ET.SubElement(st, "mediatype").text = "audio"
    ET.SubElement(st, "trackindex").text = "1"
    ET.SubElement(a1, "enabled").text = "TRUE"
    ET.SubElement(a1, "locked").text = "FALSE"

    for s in segs:
        if s["kind"] == "board":
            m = ET.SubElement(seq, "marker")
            ET.SubElement(m, "name").text = s["label"]
            ET.SubElement(m, "in").text = str(s["f0"])
            ET.SubElement(m, "out").text = "-1"
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + body + "\n", encoding="utf-8")


def structure_diff(a: Path, b: Path) -> list[str]:
    """Tag paths present in one file and not the other (for tests/reference/*.xml when it exists)."""
    def paths(p):
        out, stack = set(), []
        for ev, el in ET.iterparse(p, events=("start", "end")):
            if ev == "start":
                stack.append(el.tag)
                out.add("/".join(stack))
            else:
                stack.pop()
        return out
    pa, pb = paths(a), paths(b)
    return [f"only in {a.name}: {x}" for x in sorted(pa - pb)] + [f"only in {b.name}: {x}" for x in sorted(pb - pa)]


def run(ctx) -> dict:
    out = Path(ctx.out)
    fps = ctx.fps if isinstance(ctx.fps, Fraction) else parse_fps(ctx.fps)
    if not (out / "windows.json").exists():
        sys.exit(f"timeline: {out / 'windows.json'} is missing; run the windows stage first.")
    win = read_json(out / "windows.json")
    wav = Path(ctx.wav)
    wav_dur = float(win.get("wav_duration") or probe_duration(wav))
    total = int(round(wav_dur * fps))
    name = project_name(wav)
    cut = cut_path(ctx, name)
    track = out / "board-track.mp4"
    cut_info, wav_info = probe(cut), probe(wav)
    if not cut_info:
        log(f"timeline: the cut is not at {cut}; the timeline names it there. Relink it in the editor if it is elsewhere.")
    if not track.exists():
        log("timeline: board-track.mp4 is not rendered yet; the timeline points at where it will be.")
    segs = segments(win, fps, total)
    mask = Path(ctx.mask) if getattr(ctx, "mask", None) else None
    mask_info = probe(mask) if mask else {}
    if mask is not None and mask_info and cut_info and abs(mask_info.get("duration", 0) - cut_info.get("duration", 0)) > 0.1:
        log(f"timeline: ! the mask ({mask_info['duration']:.2f} s) and the cut ({cut_info['duration']:.2f} s) differ in "
            "length; the matte pieces will not line up. Re-export the mask from the final cut.")
    kw = dict(name=name, fps=fps, total=total, segs=segs, cut=cut, cut_info=cut_info, track=track, wav=wav,
              wav_info=wav_info, mask=mask, mask_info=mask_info)
    f1, f2 = out / "timeline.fcpxml", out / "timeline-premiere.xml"
    write_fcpxml(f1, **kw)
    write_fcp7(f2, **kw)
    for f in (f1, f2):
        ET.parse(f)   # raises on malformed XML
    ref = Path(getattr(ctx, "skill_dir", Path(__file__).resolve().parent.parent)) / "tests" / "reference"
    for f in (f1, f2):
        r = ref / f.name
        if r.exists():
            d = structure_diff(r, f)
            log(f"timeline: {f.name} vs reference: {'same structure' if not d else str(len(d)) + ' differences'}")
            for line in d[:20]:
                log(f"   {line}")
    nb = sum(1 for s in segs if s["kind"] == "board")
    px, py = fcpxml_position()
    hz, vt = fcp7_center()
    log(f"timeline: {len(segs)} cut clips on V2 ({nb} board windows at 32 % bottom-right, {len(segs) - nb} camera at "
        f"100 %), board track on V1, WAV on A1; {total} frames = {total / fps:.3f} s at {fps.numerator}/{fps.denominator}.")
    log(f"          camera box: FCPXML position {px} {py} (% of frame height, y up); FCP7 center {hz} {vt} (y down).")
    if mask is not None:
        log(f"timeline: matte {mask.name} on V3, split like the cam and hidden; keying notes in sync-manifest.md.")
    write_manifest_section(out / "sync-manifest.md", mask=mask, camera_full_background=getattr(
        ctx, "camera_full_background", True), n_cam=sum(1 for s in segs if s["kind"] == "camera"))
    log(f"timeline: wrote {f1} and {f2} (both well-formed XML).")
    return {"frames": total, "segments": segs}


MANIFEST_BEGIN, MANIFEST_END = "<!-- board-sync:timeline -->", "<!-- /board-sync:timeline -->"


def write_manifest_section(path: Path, *, mask: Path | None, camera_full_background: bool, n_cam: int) -> None:
    """Add (or replace) the editor-timeline section of sync-manifest.md; the rest of the file is left as it is."""
    lines = [MANIFEST_BEGIN, "## Editor timeline", "",
             "- timeline.fcpxml (DaVinci Resolve) and timeline-premiere.xml (Premiere), 3840x2160 at the cut's frame rate.",
             "- V1 board-track.mp4 at 200 %. V2 the final cut, cut at every window: 32 % in the bottom-right camera zone "
             "(1228.8 x 691.2 px, 80 px from the right and bottom edges) on boards, 100 % on camera stretches; its own "
             "audio is off. A1 the WAV, no effects, 0 dB."]
    if mask is not None:
        lines += [f"- V3 the cutout matte {mask.name}, directly above the cam, split at the same points with the same "
                  "scale and position, hidden.",
                  "- Premiere: Track Matte Key on the cam clips, matte = the track above, composite using luma",
                  "- Resolve: use the mask track as the cam clip's alpha (luma) matte"]
    if mask is None:
        lines.append("- No mask: the cam keeps its real background (the background is kept unless the editor passes "
                     "--mask).")
    if camera_full_background:
        lines.append(f"- Camera stretches ({n_cam}): full frame with the real background"
                     + ("; leave the key off those cam clips." if mask is not None else "."))
    else:
        lines.append(f"- Camera stretches ({n_cam}): keyed too (--camera-keyed): put the same matte key on the "
                     "full-frame cam clips; the board track is black there, so lay the background you want under them.")
    lines.append(MANIFEST_END)
    block = "\n".join(lines)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if MANIFEST_BEGIN in old and MANIFEST_END in old:
        a, b = old.index(MANIFEST_BEGIN), old.index(MANIFEST_END) + len(MANIFEST_END)
        new = old[:a] + block + old[b:]
    else:
        new = (old.rstrip() + "\n\n" if old.strip() else "") + block + "\n"
    path.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    import argparse
    import types
    ap = argparse.ArgumentParser(description="board-sync timeline stage on its own")
    ap.add_argument("--wav", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cut")
    ap.add_argument("--mask")
    ap.add_argument("--camera-keyed", action="store_true")
    ap.add_argument("--fps", default="24000/1001")
    a = ap.parse_args()
    run(types.SimpleNamespace(wav=Path(a.wav), out=Path(a.out), cut=a.cut and Path(a.cut), mask=a.mask and Path(a.mask),
                              camera_full_background=not a.camera_keyed, fps=parse_fps(a.fps)))
