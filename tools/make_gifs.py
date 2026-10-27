"""Record every board in boards/ as a looping GIF in docs/gifs/ (frame-exact: animations are paused and moved to
each frame's time, no screen recording).  python tools/make_gifs.py . [--workers 4] [--only D44Line]"""
import os, sys, glob, subprocess, tempfile, shutil
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright

REPO = os.path.abspath(sys.argv[1]); W = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
FPS, MAXLEN, OUTW = 12, 12.0, 640
out = os.path.join(REPO, "docs", "gifs"); os.makedirs(out, exist_ok=True)
names = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(REPO, "boards", "*.html")) if not f.endswith("index.html"))
if "--only" in sys.argv: names = [sys.argv[sys.argv.index("--only") + 1]]

LEN_JS = """() => { let m = 0; for (const a of document.getAnimations()) { const t = a.effect.getTiming();
  const d = (typeof t.duration === 'number' ? t.duration : 0) + (t.delay || 0); if (isFinite(d)) m = Math.max(m, d); } return m / 1000; }"""
SEEK_JS = "t => { for (const a of document.getAnimations()) { a.pause(); a.currentTime = t * 1000; } document.querySelectorAll('video').forEach(v => { v.pause(); try { v.currentTime = t % (v.duration || 4); } catch (e) {} }); }"

def run(chunk):
    with sync_playwright() as p:
        try: b = p.chromium.launch(channel="chrome")
        except Exception: b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=OUTW / 1920)
        for n in chunk:
            gif = os.path.join(out, n + ".gif")
            if os.path.exists(gif): continue
            pg.goto("file://" + os.path.join(REPO, "boards", n + ".html")); pg.wait_for_load_state("networkidle")
            pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
            L = pg.evaluate(LEN_JS); L = min(MAXLEN, L) if L > 1 else 6.0
            tmp = tempfile.mkdtemp()
            for i in range(int(L * FPS)):
                pg.evaluate(SEEK_JS, i / FPS); pg.screenshot(path=f"{tmp}/{i:04d}.png")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/%04d.png", "-vf",
                            f"scale={OUTW}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
                            "-loop", "0", gif], check=True)
            shutil.rmtree(tmp); print(n, round(L, 1), "s", os.path.getsize(gif) // 1024, "KB", flush=True)
        b.close()

chunks = [names[i::W] for i in range(W)]
with ThreadPoolExecutor(W) as ex: list(ex.map(run, chunks))
print("done", len(names))
