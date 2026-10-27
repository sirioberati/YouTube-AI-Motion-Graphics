"""Export boards to an MP4, frame by frame, the way the video describes it.

Chrome opens each board, every animation is paused and moved to the exact time of each frame (a virtual clock, so no
frame is ever dropped the way a screen recording drops them), every frame is saved as a PNG, and FFmpeg joins the
frames into a video with your voice.

  One board:   python tools/export.py boards/D44Line.html --seconds 8 -o out/line.mp4
  A timeline:  python tools/export.py timeline.json --audio my-voice.wav -o out/video.mp4 --workers 6
  Check first: python tools/export.py timeline.json --audio my-voice.wav -o out/test.mp4 --first 60

timeline.json (times in seconds on your audio; a board's own clock starts at 0 when it comes on screen):
  [{"board": "boards/D44Line.html", "start": 0.0, "end": 7.4},
   {"board": "boards/C111Slope.html", "start": 7.4, "end": 15.0}]

The render is split into parts, each saved as MKV (a stopped MKV can still be opened; an MP4 can't), run by several
workers at once, then joined without re-encoding. At the end the frame count is checked against the length.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

W, H = 1920, 1080
SEEK = """t => { for (const a of document.getAnimations()) { a.pause(); a.currentTime = t * 1000; }
  if (window.seek) window.seek(t);                                   // boards with their own clock
  if (window.gsap) { gsap.globalTimeline.pause(); gsap.globalTimeline.seek(t, false); }
  document.querySelectorAll('video').forEach(v => { v.pause(); if (v.duration) v.currentTime = t % v.duration; }); }"""


def plan(src, seconds, fps):
    """Return a list of (board_path, board_time) for every frame of the output."""
    if src.endswith(".json"):
        tl = json.load(open(src)); base = os.path.dirname(os.path.abspath(src))
        frames = []
        for k in tl:
            s, e = round(k["start"] * fps), round(k["end"] * fps)   # rounded on the whole timeline: no drift
            p = k["board"] if os.path.isabs(k["board"]) else os.path.join(base, k["board"])
            frames += [(p, (f / fps) - k["start"]) for f in range(s, e)]
        return frames
    return [(os.path.abspath(src), f / fps) for f in range(round(seconds * fps))]


def render_part(job):
    from playwright.sync_api import sync_playwright
    idx, frames, fps, tmp, chrome = job
    out = os.path.join(tmp, f"part{idx:03d}.mkv")
    if os.path.exists(out): return out                       # resume: finished parts are kept
    fdir = os.path.join(tmp, f"f{idx:03d}"); os.makedirs(fdir, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(**({"channel": "chrome"} if chrome else {}))
        pg = b.new_page(viewport={"width": W, "height": H}); cur = None
        for i, (board, t) in enumerate(frames):
            if board != cur:
                pg.goto("file://" + board); pg.wait_for_load_state("networkidle")
                pg.evaluate("document.fonts.ready"); cur = board
            pg.evaluate(SEEK, max(0.0, t)); pg.wait_for_timeout(5)
            pg.screenshot(path=os.path.join(fdir, f"{i:06d}.png"))
        b.close()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(fdir, "%06d.png"),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-g", "15",
                    "-r", str(fps), out], check=True)
    shutil.rmtree(fdir)
    print(f"  part {idx} done ({len(frames)} frames)", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="a board .html or a timeline .json")
    ap.add_argument("-o", "--out", required=True, help="output .mp4")
    ap.add_argument("--audio", help="your voice (wav/mp3); muxed on, and the video is cut to its length")
    ap.add_argument("--seconds", type=float, default=8, help="length when exporting one board (default 8)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--part", type=float, default=20, help="seconds per part (default 20)")
    ap.add_argument("--first", type=float, help="render only the first N seconds (check before the full render)")
    ap.add_argument("--chrome", action="store_true", help="use your installed Chrome instead of Playwright's Chromium")
    a = ap.parse_args()

    frames = plan(a.src, a.seconds, a.fps)
    if a.first: frames = frames[:round(a.first * a.fps)]
    n = round(a.part * a.fps)
    tmp = os.path.splitext(a.out)[0] + "-parts"; os.makedirs(tmp, exist_ok=True)
    jobs = [(i, frames[s:s + n], a.fps, tmp, a.chrome) for i, s in enumerate(range(0, len(frames), n))]
    print(f"{len(frames)} frames = {len(frames) / a.fps:.2f} s in {len(jobs)} parts, {a.workers} workers", flush=True)
    with ThreadPoolExecutor(a.workers) as ex: parts = list(ex.map(render_part, jobs))

    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in parts))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst]
    if a.audio: cmd += ["-i", a.audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k", "-shortest"]
    subprocess.run(cmd + ["-c:v", "copy", "-movflags", "+faststart", a.out], check=True)

    got = int(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                              "stream=nb_read_packets", "-of", "csv=p=0", a.out], capture_output=True, text=True).stdout.strip())
    ok = got == len(frames) or (a.audio and got <= len(frames))
    print(f"{'OK' if ok else 'FRAME COUNT MISMATCH'}: {got} frames written, {len(frames)} planned -> {a.out}")
    if ok: shutil.rmtree(tmp)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
