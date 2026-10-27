"""Stage `preview`: board-track.mp4 + the final-cut WAV -> preview.mp4, for the watch-through only.

    ffmpeg -i board-track.mp4 -i <wav> -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest preview.mp4

The video is copied as it is (no re-encode); the WAV is already the track's length.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.common import log, probe_duration, which_ffmpeg  # noqa: E402


def run(ctx) -> Path:
    out = Path(ctx.out)
    track = out / "board-track.mp4"
    wav = Path(ctx.wav) if getattr(ctx, "wav", None) else None
    if not track.exists():
        sys.exit(f"preview: {track} is missing; run the render stage first.")
    if wav is None or not wav.exists():
        sys.exit(f"preview: the WAV was not found: {wav}")
    dst = out / "preview.mp4"
    tmp = out / "preview.part.mp4"
    cmd = [which_ffmpeg("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-i", str(track), "-i", str(wav),
           "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", str(tmp)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        tmp.unlink(missing_ok=True)
        sys.exit(f"preview: ffmpeg failed:\n{r.stderr.strip()[-2000:]}")
    tmp.replace(dst)
    v, a = probe_duration(track), probe_duration(dst)
    log(f"preview: wrote {dst} ({a:.2f} s; board track {v:.2f} s, WAV {probe_duration(wav):.2f} s). "
        "Watch it from start to end.")
    return dst


if __name__ == "__main__":
    import argparse
    import types
    ap = argparse.ArgumentParser(description="board-sync preview stage on its own")
    ap.add_argument("--wav", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    run(types.SimpleNamespace(wav=Path(a.wav), out=Path(a.out)))
