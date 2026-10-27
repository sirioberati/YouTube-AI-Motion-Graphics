"""render.py: scenes/NN.html -> boards/NN-Name.mp4 (Playwright frame-step + ffmpeg), then board-track.mp4.

Public:
    run(ctx)             render every board in windows.json (or ctx.only), then assemble_track(ctx)
    assemble_track(ctx)  board clips + black clips, in window order, concat demuxer, -c copy, exact frame count

ctx needs `out` (the --out folder). Optional: `only` ("4,5" or [4, 5]), `fps` (else windows.json's), `wav`
(else windows.json's wav_duration), `workers` (else min(3, cpu//2)), `no_reuse` (turn static-frame reuse off).

Sample-exact maths (fps is a Fraction, 24000/1001 by default; every count below is an integer number of frames):
    track frames T            = round(wav_duration * fps)
    window k on the track     = frames [S_k, E_k) with S_k = round(start_k * fps), E_k = round(end_k * fps)
    board clip length L_k     = E_k - S_k
    board clip frame i        = scene time  t_i = (S_k + i) / fps - start_k   (clamped to >= 0)
Frame i of a board sits at track frame S_k + i, which plays at (S_k + i) / fps on the WAV's clock, so seeking the
scene to (S_k + i) / fps - start_k shows exactly what belongs under the audio at that frame. Because consecutive
windows share their boundary seconds (end_k == start_k+1), the slots [S_k, E_k) tile the track with no gap, no
overlap and no drift, and black clips fill [0, S_first), camera stretches, and [E_last, T).
DESIGN.md says L = round((end - start) * fps); the two agree except when start is off the frame grid, where they
can differ by one frame. E_k - S_k is the one that tiles the track exactly (a clip one frame long would have to be
trimmed, and cutting the last frame of a B-frame stream under -c copy breaks the B-frames that reference it).
"""
from __future__ import annotations

import base64
import json
import os
import queue
import subprocess
import threading
import time
from fractions import Fraction
from pathlib import Path

try:  # imported as part of a package (scripts.render) or with scripts/ on sys.path
    from . import common as C
except ImportError:  # pragma: no cover
    import common as C

W, H = 1920, 1080
CHANNELS = ("chrome", "msedge", None)          # installed Chrome, then Edge, then Playwright's bundled chromium
LAUNCH_ARGS = ["--force-color-profile=srgb", "--hide-scrollbars", "--mute-audio"]
NO_MOTION_CSS = ("*, *::before, *::after { animation: none !important; transition: none !important;"
                 " caret-color: transparent !important; }")
PROGRESS_EVERY = 5.0                           # seconds between progress lines per board
REUSE_CHECK_EVERY = 48                         # every Nth reused frame is captured anyway and compared


# ───────────────────────────── shared helpers (qa.py uses these too) ─────────────────────────────

def out_dir(ctx) -> Path:
    return Path(getattr(ctx, "out")).expanduser().resolve()


def load_windows(ctx) -> dict:
    p = out_dir(ctx) / "windows.json"
    if not p.exists():
        raise SystemExit(f"windows.json not found in {p.parent}. Run the windows stage first.")
    return C.read_json(p)


def get_fps(ctx, windows: dict) -> Fraction:
    v = getattr(ctx, "fps", None) or windows.get("fps") or "24000/1001"
    return v if isinstance(v, Fraction) else C.parse_fps(v)


def fps_str(fps: Fraction) -> str:
    return f"{fps.numerator}/{fps.denominator}"


def parse_only(only) -> set[int] | None:
    if only in (None, "", [], ()):
        return None
    if isinstance(only, (int, float)):
        return {int(only)}
    if isinstance(only, str):
        return {int(x) for x in only.replace(";", ",").split(",") if x.strip()}
    return {int(x) for x in only}


def board_items(windows: dict, only=None) -> list[dict]:
    keep = parse_only(only)
    items = [it for it in windows.get("items", []) if it.get("kind") == "board"]
    if keep is not None:
        items = [it for it in items if int(it.get("n", -1)) in keep]
    return items


def nn(item: dict) -> str:
    return f"{int(item['n']):02d}"


def board_name(item: dict) -> str:
    """'04-OwnTeam.html' -> '04-OwnTeam'. Without a file name: '04-Your-own-team-cheaper'."""
    f = item.get("file")
    if f:
        return Path(str(f).replace("\\", "/")).stem
    words = "".join(ch if ch.isalnum() else " " for ch in str(item.get("title", "Board"))).split()
    return f"{nn(item)}-" + ("-".join(words)[:40] or "Board")


def clip_path(out: Path, item: dict) -> Path:
    return out / "boards" / f"{board_name(item)}.mp4"


def scene_path(out: Path, item: dict) -> Path:
    return out / "scenes" / f"{nn(item)}.html"


def slot(start: float, end: float, fps: Fraction) -> tuple[int, int]:
    """(first track frame S, frame count L) of a window: S = round(start*fps), L = round(end*fps) - S."""
    s = C.frames_for(start, fps)
    return s, max(0, C.frames_for(end, fps) - s)


def frame_time(i: int, s_frame: int, start: float, fps: Fraction) -> float:
    """Board-local scene time shown by frame i of a board clip (see the module docstring)."""
    return max(0.0, float(Fraction(s_frame + i) / fps) - start)


def frame_index(t_local: float, s_frame: int, start: float, n_frames: int, fps: Fraction) -> int:
    """The clip frame that shows board-local time t_local (the first frame at or after it), clamped to the clip."""
    i = int(round((start + t_local) * fps)) - s_frame
    if float(Fraction(s_frame + i) / fps) - start < t_local - 1e-6:
        i += 1
    return min(max(i, 0), max(n_frames - 1, 0))


def encoder_args(fps: Fraction) -> list[str]:
    """One encoder setting for board clips AND black clips, so the concat demuxer can join them with -c copy."""
    f = fps_str(fps)
    # scale: a real RGB -> Y'CbCr conversion with the BT.709 matrix into limited range (the -color* tags only label
    # the stream); setparams: newer ffmpeg lets frame properties override the -color* output options, so the frames
    # themselves are labelled BT.709 too, otherwise primaries/transfer come out "unknown".
    return ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,"
                   "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-r", f, "-movflags", "+faststart", "-an"]


def count_frames(path: Path) -> int:
    """Frames in the first video stream, counted from the packets (no decode), falling back to the header."""
    r = C.run([C.which_ffmpeg("ffprobe"), "-v", "error", "-select_streams", "v:0", "-count_packets",
               "-show_entries", "stream=nb_read_packets,nb_frames", "-of", "json", path])
    st = (json.loads(r.stdout).get("streams") or [{}])[0]
    for k in ("nb_read_packets", "nb_frames"):
        v = st.get(k)
        if v not in (None, "N/A"):
            return int(v)
    return -1


def replace_file(src: Path, dst: Path) -> None:
    """os.replace, with a plain message when Windows refuses because the file is open in an editor or player."""
    try:
        os.replace(src, dst)
    except PermissionError as e:
        raise RuntimeError(f"cannot overwrite {dst.name}: it is open in another program (close it in Resolve, "
                           f"Premiere or the video player and re-run)") from e


def _fmt_s(x: float) -> str:
    m, s = divmod(max(0.0, x), 60)
    return f"{int(m)}:{s:04.1f}" if m else f"{s:.1f} s"


# ───────────────────────────── browser ─────────────────────────────

_channel_lock = threading.Lock()
_channel_ok: list = []          # the channel that launched once, reused by every worker


def launch_browser(pw):
    """Chrome, then Edge, then the bundled chromium. Raises SystemExit with a plain message if none launches."""
    with _channel_lock:
        order = _channel_ok[:1] or list(CHANNELS)
    errors = []
    for ch in order:
        try:
            kw = {"args": LAUNCH_ARGS, "headless": True}
            if ch:
                kw["channel"] = ch
            b = pw.chromium.launch(**kw)
            with _channel_lock:
                if not _channel_ok:
                    _channel_ok.append(ch)
                    C.log(f"browser: {ch or 'bundled chromium'} {b.version}")
            return b
        except Exception as e:  # noqa: BLE001
            errors.append(f"{ch or 'bundled'}: {str(e).splitlines()[0][:160]}")
    raise SystemExit("No browser could start. Install Google Chrome or Microsoft Edge, or run setup "
                     "(it runs `playwright install chromium`).\n  " + "\n  ".join(errors))


class _Page:
    """One reusable page per worker, with a CDP session for fast captures."""

    def __init__(self, browser):
        self.browser = browser
        self.context = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1)
        self.page = self.context.new_page()
        self.errors: list[str] = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        try:
            self.cdp = self.context.new_cdp_session(self.page)
        except Exception:  # noqa: BLE001  (not Chromium: fall back to page.screenshot)
            self.cdp = None

    def close(self):
        try:
            self.context.close()
        except Exception:  # noqa: BLE001
            pass

    def shot(self) -> bytes:
        """PNG of the viewport. CDP captureScreenshot with optimizeForSpeed (fast zlib) is ~3x faster than
        page.screenshot(animations='disabled', caret='hide'), which re-scans animations and re-injects its caret
        style on every call; the scene already has no animations and NO_MOTION_CSS hides carets once."""
        if self.cdp is not None:
            r = self.cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True,
                                                         "fromSurface": True, "captureBeyondViewport": False})
            return base64.b64decode(r["data"])
        return self.page.screenshot(type="png", animations="disabled", caret="hide")

    def seek(self, t: float):
        if self.cdp is not None:
            r = self.cdp.send("Runtime.evaluate", {"expression": f"window.__seek({t!r})", "awaitPromise": True})
            d = r.get("exceptionDetails")
            if d:
                why = (d.get("exception") or {}).get("description") or d.get("text", "")
                raise RuntimeError(f"__seek({t:.3f}) threw: {str(why).splitlines()[0] if why else 'an error'}")
        else:
            self.page.evaluate("t => window.__seek(t)", t)


# JS: intervals (board-local seconds) during which the scene's paused GSAP timelines change anything. Frames whose
# time step crosses none of them are pixel-identical to the previous frame, so the previous PNG is reused.
# Returns null (reuse off) when anything else could move: running timelines, video, canvas, iframes, gifs.
_INTERVALS_JS = r"""() => {
  const g = window.gsap;
  if (!g || !g.globalTimeline) return null;
  if (document.querySelector('video, canvas, iframe, object, embed, img[src$=".gif" i]')) return null;
  const top = g.globalTimeline.getChildren(false, true, true);
  if (!top.length) return null;
  const out = [];
  const walk = (tl, off, scale) => {
    for (const c of tl.getChildren(false, true, true)) {
      const ts = c.timeScale() || 1;
      const a = off + c.startTime() / scale, b = a + c.totalDuration() / ts / scale;
      if (c.getChildren) walk(c, a, scale * ts);
      out.push([a, b]);
    }
  };
  for (const c of top) {
    if (!c.paused() && c.totalDuration() > 0 && c.isActive && c.isActive()) return null;   // something runs on its own
  }
  const main = window.__tl && window.__tl.getChildren ? [window.__tl] : top.filter((c) => c.paused());
  for (const c of main) {
    if (c.getChildren) walk(c, 0, 1); else out.push([0, c.totalDuration()]);
  }
  return out;
}"""


# ───────────────────────────── one board ─────────────────────────────

def _render_board(pg: _Page, item: dict, out: Path, fps: Fraction, reuse: bool, label: str) -> dict:
    scene = scene_path(out, item)
    if not scene.exists():
        raise FileNotFoundError(f"{scene} is missing (run the choreo stage)")
    start, end = float(item["start"]), float(item["end"])
    s_frame, n_frames = slot(start, end, fps)
    if n_frames <= 0:
        raise ValueError(f"window {start:.3f}-{end:.3f} is shorter than one frame")
    design_n = C.frames_for(end - start, fps)
    if design_n != n_frames:
        C.log(f"{label}: {n_frames} frames on the track grid (round((end-start)*fps) = {design_n}; start is off the frame grid)")

    pg.errors.clear()
    pg.page.goto(scene.as_uri(), wait_until="load", timeout=120_000)
    pg.page.wait_for_function("() => typeof window.__seek === 'function' && window.__ready !== undefined",
                              timeout=60_000)
    dur = pg.page.evaluate("async () => { await window.__ready; return Number(window.__dur) || 0; }")
    pg.page.add_style_tag(content=NO_MOTION_CSS)
    if dur and abs(dur - (end - start)) > 1.5 / float(fps):
        C.log(f"{label}: note: scene __dur {dur:.3f} s vs window {end - start:.3f} s; rendering the window")
    intervals = pg.page.evaluate(_INTERVALS_JS) if reuse else None
    if intervals is not None:
        intervals = sorted((float(a), float(b)) for a, b in intervals)

    out_mp4 = clip_path(out, item)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_mp4.with_name(f".{out_mp4.stem}.partial.mp4")
    errlog = out_mp4.with_name(f".{out_mp4.stem}.ffmpeg.log")
    cmd = [C.which_ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostats", "-y",
           "-f", "image2pipe", "-framerate", fps_str(fps), "-c:v", "png", "-i", "-",
           *encoder_args(fps), "-f", "mp4", str(tmp)]
    with open(errlog, "wb") as ef:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=ef)
        q: queue.Queue = queue.Queue(maxsize=24)
        werr: list = []

        def pump():
            try:
                while True:
                    b = q.get()
                    if b is None:
                        break
                    proc.stdin.write(b)
            except Exception as e:  # noqa: BLE001
                werr.append(e)
                while q.get() is not None:   # drain so the producer never blocks forever
                    pass

        wt = threading.Thread(target=pump, daemon=True)
        wt.start()
        t0 = last_log = time.perf_counter()
        prev_png, prev_t, captured, reused, since_check = None, None, 0, 0, 0
        try:
            for i in range(n_frames):
                if werr:
                    raise RuntimeError(f"ffmpeg stopped accepting frames: {werr[0]}")
                t = frame_time(i, s_frame, start, fps)
                static = (prev_png is not None and intervals is not None and
                          not any(a <= t + 1e-6 and b >= prev_t - 1e-6 for a, b in intervals))
                if static and since_check < REUSE_CHECK_EVERY:
                    png = prev_png
                    reused += 1
                    since_check += 1
                else:
                    pg.seek(t)
                    png = pg.shot()
                    captured += 1
                    if static:           # spot check: a frame we would have reused must be byte-identical
                        since_check = 0
                        if png != prev_png:
                            intervals = None
                            C.log(f"{label}: the page changes outside its GSAP timeline; static-frame reuse off")
                prev_png, prev_t = png, t
                q.put(png)
                now = time.perf_counter()
                if now - last_log >= PROGRESS_EVERY:
                    last_log = now
                    rate = (i + 1) / (now - t0)
                    C.log(f"{label}: {i + 1}/{n_frames} frames, {rate:.1f} fps, ETA {_fmt_s((n_frames - i - 1) / rate)}")
        except BaseException:
            q.put(None)
            wt.join()
            try:
                proc.stdin.close()
            except Exception:  # noqa: BLE001
                pass
            proc.wait()
            ef.close()
            msg = errlog.read_text(encoding="utf-8", errors="replace").strip()[-600:]
            tmp.unlink(missing_ok=True)
            errlog.unlink(missing_ok=True)
            if werr:
                raise RuntimeError(f"ffmpeg stopped accepting frames: {msg or werr[0]}") from None
            raise
        q.put(None)
        wt.join()
        try:
            proc.stdin.close()
        except Exception:  # noqa: BLE001
            pass
        rc = proc.wait()
    elapsed = time.perf_counter() - t0
    msg = errlog.read_text(encoding="utf-8", errors="replace").strip()[-600:] if errlog.exists() else ""
    got = count_frames(tmp) if not werr and rc == 0 else -1
    if werr or rc != 0 or got != n_frames:
        tmp.unlink(missing_ok=True)
        errlog.unlink(missing_ok=True)
        if werr or rc != 0:
            raise RuntimeError(f"ffmpeg failed (exit {rc}): {msg or werr}")
        raise RuntimeError(f"clip has {got} frames, expected {n_frames}")
    replace_file(tmp, out_mp4)
    errlog.unlink(missing_ok=True)
    if pg.errors:
        C.log(f"{label}: page script error(s) during render: {pg.errors[0][:200]}")
    rate = n_frames / elapsed if elapsed else 0.0
    C.log(f"{label}: done, {n_frames} frames in {_fmt_s(elapsed)} ({rate:.1f} fps; "
          f"{captured} captured, {reused} reused) -> boards/{out_mp4.name}")
    return {"n": int(item["n"]), "file": str(out_mp4), "frames": n_frames, "seconds": elapsed,
            "captured": captured, "reused": reused}


# ───────────────────────────── worker pool ─────────────────────────────

def _worker(jobs: queue.Queue, done: list, failed: list, lock: threading.Lock, out: Path, fps: Fraction, reuse: bool):
    from playwright.sync_api import sync_playwright   # one Playwright instance per thread (its API is not thread-safe)
    with sync_playwright() as pw:
        browser = None
        pg = None
        while True:
            try:
                item, attempt = jobs.get_nowait()
            except queue.Empty:
                break
            label = f"board {nn(item)} {board_name(item)[len(nn(item)) + 1:]}".rstrip()
            try:
                if browser is None or not browser.is_connected():
                    browser = launch_browser(pw)
                    pg = None
                if pg is None:
                    pg = _Page(browser)
                res = _render_board(pg, item, out, fps, reuse, label)
                with lock:
                    done.append(res)
            except SystemExit as e:
                with lock:
                    failed.append({"n": int(item["n"]), "error": str(e)})
                # no browser at all: fail everything still queued, the same way
                while True:
                    try:
                        it, _ = jobs.get_nowait()
                    except queue.Empty:
                        break
                    with lock:
                        failed.append({"n": int(it["n"]), "error": str(e)})
                break
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}"[:400]
                if pg is not None:
                    pg.close()
                pg = None
                if attempt == 0:
                    C.log(f"{label}: failed ({err}); retrying once")
                    jobs.put((item, 1))
                else:
                    C.log(f"{label}: FAILED again ({err})")
                    with lock:
                        failed.append({"n": int(item["n"]), "error": err})
        if pg is not None:
            pg.close()
        if browser is not None:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass


def run(ctx) -> dict:
    """Render every board clip (honouring ctx.only), then assemble board-track.mp4."""
    out = out_dir(ctx)
    windows = load_windows(ctx)
    fps = get_fps(ctx, windows)
    items = board_items(windows, getattr(ctx, "only", None))
    if not items:
        C.log("render: no boards to render")
        return {"rendered": [], "failed": [], "fps": 0.0}
    C.which_ffmpeg()
    workers = getattr(ctx, "workers", None) or min(3, max(1, (os.cpu_count() or 2) // 2))
    workers = max(1, min(int(workers), len(items)))
    reuse = not (getattr(ctx, "no_reuse", False) or os.environ.get("BOARD_SYNC_NO_REUSE"))
    total_frames = sum(slot(float(it["start"]), float(it["end"]), fps)[1] for it in items)
    C.log(f"render: {len(items)} board(s), {total_frames} frames at {fps_str(fps)} fps, {workers} worker(s)")

    jobs: queue.Queue = queue.Queue()
    # longest first, so a long board does not start last and leave the other workers idle
    for it in sorted(items, key=lambda x: float(x["end"]) - float(x["start"]), reverse=True):
        jobs.put((it, 0))
    done, failed, lock = [], [], threading.Lock()
    t0 = time.perf_counter()
    threads = [threading.Thread(target=_worker, args=(jobs, done, failed, lock, out, fps, reuse), daemon=True)
               for _ in range(workers)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    elapsed = time.perf_counter() - t0
    frames = sum(d["frames"] for d in done)
    rate = frames / elapsed if elapsed else 0.0
    C.log(f"render: {len(done)} board(s), {frames} frames in {_fmt_s(elapsed)} = {rate:.1f} fps overall")
    if failed:
        C.log("render: NOT rendered (their windows stay black on the track; qa-report lists them): " +
              ", ".join(f"{f['n']:02d} ({f['error'][:120]})" for f in sorted(failed, key=lambda f: f["n"])))
    if any(f["error"].startswith("No browser") for f in failed) and not done:
        raise SystemExit(failed[0]["error"])
    C.write_json(out / "render-log.json", {"fps_overall": round(rate, 2), "seconds": round(elapsed, 2),
                                           "rendered": sorted(done, key=lambda d: d["n"]),
                                           "failed": sorted(failed, key=lambda f: f["n"])})
    assemble_track(ctx)
    return {"rendered": done, "failed": failed, "fps": rate}


# ───────────────────────────── board track ─────────────────────────────

BLACK_CHUNK = 240     # frames per reusable black chunk (10 s, inside x264's default 250-frame GOP)


def _black_clip(folder: Path, n_frames: int, fps: Fraction, cache: dict) -> Path:
    """A black clip of exactly n_frames, same encoder settings as the boards (cached by length)."""
    if n_frames in cache:
        return cache[n_frames]
    p = folder / f"black-{n_frames:06d}.mp4"
    C.run([C.which_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={fps_str(fps)}",
           "-frames:v", str(n_frames), *encoder_args(fps), "-f", "mp4", p])
    cache[n_frames] = p
    return p


def _black_parts(folder: Path, n_frames: int, fps: Fraction, cache: dict) -> list[tuple[Path, int]]:
    """n_frames of black as whole files: k copies of one BLACK_CHUNK-frame clip plus one remainder clip. Every part
    starts on its own keyframe and is used whole, so -c copy never cuts inside a GOP, and a 20-minute camera stretch
    costs one 240-frame encode instead of 28,000 frames."""
    k, rest = divmod(n_frames, BLACK_CHUNK)
    parts = [(_black_clip(folder, BLACK_CHUNK, fps, cache), BLACK_CHUNK)] * k
    if rest:
        parts.append((_black_clip(folder, rest, fps, cache), rest))
    return parts


def _concat_line(p: Path) -> str:
    return "file '" + p.resolve().as_posix().replace("'", "'\\''") + "'"


def _plan(windows: dict, out: Path, fps: Fraction, total: int) -> list[tuple[str, int, Path | None, str]]:
    """[(kind, frames, clip or None for black, label)] tiling [0, total) exactly."""
    plan, cursor = [], 0
    items = sorted(windows.get("items", []), key=lambda it: float(it.get("start", 0)))
    for it in items:
        s, n = slot(float(it["start"]), float(it["end"]), fps)
        if s < cursor:                       # overlapping windows: never go back in time
            C.log(f"track: window at {float(it['start']):.3f} s overlaps the previous one by {cursor - s} frame(s); trimmed")
            n -= cursor - s
            s = cursor
        if s > cursor:
            plan.append(("gap", s - cursor, None, f"gap {cursor}-{s}"))
        if n <= 0:
            continue
        if s + n > total:                    # never past the WAV
            n = total - s
            if n <= 0:
                break
        if it.get("kind") == "board":
            clip = clip_path(out, it)
            if clip.exists() and count_frames(clip) == slot(float(it["start"]), float(it["end"]), fps)[1] == n:
                plan.append(("board", n, clip, f"board {nn(it)}"))
            else:
                why = "not rendered" if not clip.exists() else "clip length does not match its window (re-render it)"
                C.log(f"track: board {nn(it)} {why}; its window stays black")
                plan.append(("missing", n, None, f"board {nn(it)} (black)"))
        else:
            plan.append(("camera", n, None, "camera"))
        cursor = s + n
    if cursor < total:
        plan.append(("tail", total - cursor, None, "tail"))
    return plan


def assemble_track(ctx) -> Path:
    """board-track.mp4: every board at its window, black elsewhere, exactly round(wav_duration*fps) frames."""
    out = out_dir(ctx)
    windows = load_windows(ctx)
    fps = get_fps(ctx, windows)
    wav = getattr(ctx, "wav", None)
    wav_dur = C.probe_duration(Path(wav)) if wav and Path(wav).exists() else float(windows["wav_duration"])
    if windows.get("wav_duration") and abs(wav_dur - float(windows["wav_duration"])) > 0.5 / float(fps):
        C.log(f"track: WAV is {wav_dur:.3f} s but windows.json says {float(windows['wav_duration']):.3f} s; using the WAV")
    total = C.frames_for(wav_dur, fps)              # T = round(wav_duration * fps)
    plan = _plan(windows, out, fps, total)

    parts = out / "_track"
    parts.mkdir(parents=True, exist_ok=True)
    final = out / "board-track.mp4"
    tmp = out / ".board-track.partial.mp4"
    cache: dict = {}
    for attempt in range(2):
        lines = ["ffconcat version 1.0"]
        for kind, n, clip, _ in plan:
            for src, m in ([(clip, n)] if clip is not None else _black_parts(parts, n, fps, cache)):
                secs = Fraction(m) / fps                # exact length of this entry; outpoint = its own end
                lines += [_concat_line(src), f"duration {float(secs):.6f}", f"outpoint {float(secs):.6f}"]
        listing = parts / "concat.txt"
        listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
        C.run([C.which_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
               "-i", listing, "-c", "copy", "-an", "-movflags", "+faststart", "-f", "mp4", tmp])
        got = count_frames(tmp)
        if got == total:
            break
        delta = total - got
        C.log(f"track: {got} frames, expected {total} ({delta:+d}); re-doing with the trailing black adjusted")
        if plan and plan[-1][2] is None and plan[-1][1] + delta > 0:
            k, n, _, lab = plan[-1]
            plan[-1] = (k, n + delta, None, lab)
        elif delta > 0:
            plan.append(("pad", delta, None, "pad"))
        else:
            break
    try:
        replace_file(tmp, final)
    except RuntimeError as e:
        raise SystemExit(str(e))
    got = count_frames(final)
    dur = C.probe_duration(final)
    ok = got == total
    C.log(f"track: board-track.mp4 {got} frames ({dur:.3f} s), expected round({wav_dur:.3f} x {fps_str(fps)}) = {total}"
          f" {'OK' if ok else 'MISMATCH'}; {sum(1 for p in plan if p[0] == 'board')} board clip(s), "
          f"{sum(1 for p in plan if p[2] is None)} black clip(s)")
    for p in parts.glob("*"):
        p.unlink(missing_ok=True)
    try:
        parts.rmdir()
    except OSError:
        pass
    return final


if __name__ == "__main__":   # python scripts/render.py <out> [--only 4,5] [--track-only]
    import argparse
    import types
    ap = argparse.ArgumentParser(description="board-sync render stage")
    ap.add_argument("out")
    ap.add_argument("--only")
    ap.add_argument("--workers", type=int)
    ap.add_argument("--wav")
    ap.add_argument("--track-only", action="store_true")
    a = ap.parse_args()
    c = types.SimpleNamespace(out=a.out, only=a.only, workers=a.workers, wav=a.wav, fps=None)
    assemble_track(c) if a.track_only else run(c)
