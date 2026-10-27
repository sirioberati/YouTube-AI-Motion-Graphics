"""Stage `words`: the word timings every later stage works from.

Primary source: the your editor export `<name> - final cut words.tsv` (--words), tab-separated with the header
`start end word frame_in frame_out confidence`, seconds on the final timeline.
Fallback (no tsv): faster-whisper large-v3-turbo on the WAV (word_timestamps, language en, no VAD), written to
`--out/words.tsv` in the same format so a re-run reuses it instead of transcribing again.

Writes `--out/words.json`: [{"w": "If", "t": 0.0, "e": 0.28, "c": 0.77}, ...] (t/e seconds, c confidence 0..1).
Sets ctx.timing_source to "words.tsv" or "faster-whisper" (windows.py records it in windows.json).
"""
from __future__ import annotations

import os
import sys
from fractions import Fraction
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.common import frames_for, log, parse_fps, which_ffmpeg, write_json  # noqa: E402

TSV_HEADER = ["start", "end", "word", "frame_in", "frame_out", "confidence"]
MODEL = "large-v3-turbo"


def load_tsv(path) -> list[dict]:
    """Read a words.tsv (your editor export or board-sync's own) into [{"w","t","e","c"}], sorted by start.

    Tolerates a BOM, Windows line endings, a missing header (columns then taken in the standard order), extra or
    missing trailing columns (no confidence column -> c = 1.0) and blank lines. Rows that cannot be read are skipped
    with a log line, never guessed.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    if not lines:
        return []
    head = [c.strip().lower() for c in lines[0].split("\t")]
    if "start" in head and "word" in head:
        cols = {name: i for i, name in enumerate(head)}
        body = list(enumerate(lines[1:], start=2))
    else:
        cols = {name: i for i, name in enumerate(TSV_HEADER)}
        body = list(enumerate(lines, start=1))
    ci = cols.get("confidence")
    rows, skipped = [], 0
    for ln, line in body:
        if not line.strip():
            continue
        parts = line.split("\t")
        try:
            t = float(parts[cols["start"]].strip().replace(",", "."))
            e = float(parts[cols["end"]].strip().replace(",", "."))
            w = parts[cols["word"]].strip()
        except (ValueError, IndexError, KeyError):
            skipped += 1
            if skipped <= 5:
                log(f"  words.tsv line {ln} skipped (not start/end/word): {line[:60]!r}")
            continue
        if not w:
            continue
        c = 1.0
        if ci is not None and ci < len(parts) and parts[ci].strip():
            try:
                c = float(parts[ci].strip().replace(",", "."))
            except ValueError:
                c = 1.0
        if e < t:
            e = t
        rows.append({"w": w, "t": round(t, 3), "e": round(e, 3), "c": round(c, 3)})
    if skipped > 5:
        log(f"  ... {skipped} unreadable lines skipped in {p.name}")
    rows.sort(key=lambda r: r["t"])   # stable: equal starts keep file order
    return rows


def write_tsv(path, rows: list[dict], fps) -> None:
    """Write rows in the your editor words.tsv format (frames at `fps`, rounded to the nearest frame)."""
    fps = parse_fps(fps) if not isinstance(fps, Fraction) else fps
    out = ["\t".join(TSV_HEADER)]
    for r in rows:
        out.append(f"{r['t']:.2f}\t{r['e']:.2f}\t{r['w']}\t{frames_for(r['t'], fps)}\t{frames_for(r['e'], fps)}\t{r['c']:.2f}")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")


def _device():
    """cuda/float16 when an NVIDIA GPU is visible to CTranslate2, else cpu/int8 (fast and accurate enough on CPU)."""
    try:
        import ctranslate2  # type: ignore
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def decode_16k(wav):
    """The WAV as 16 kHz mono float32 samples, decoded by ffmpeg (not PyAV: faster-whisper's own decoder breaks with
    PyAV 17+, and ffmpeg is already required)."""
    import subprocess
    import numpy as np  # type: ignore
    cmd = [which_ffmpeg("ffmpeg"), "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(wav),
           "-f", "f32le", "-acodec", "pcm_f32le", "-ac", "1", "-ar", "16000", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"words: ffmpeg could not read {wav}:\n{r.stderr.decode('utf-8', 'replace')[-1500:]}")
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def transcribe(wav, model_name: str = MODEL) -> list[dict]:
    """faster-whisper word timings for the whole WAV: [{"w","t","e","c"}]."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        sys.exit("words: there is no words.tsv and faster-whisper is not installed. Run setup.ps1 / setup.sh, "
                 "or export the words.tsv from your editor and pass it with --words.")
    wav = Path(wav)
    device, ctype = _device()
    log(f"words: no words.tsv, transcribing {wav.name} with faster-whisper {model_name} on {device} ({ctype}).")
    log("       The first run downloads the model (about 1.6 GB). On a CPU this takes about three times the audio's "
        "length (a 27-minute cut: over an hour); with an NVIDIA GPU a few minutes. The words.tsv from your editor "
        "skips all of this.")
    audio = decode_16k(wav)
    model = WhisperModel(model_name, device=device, compute_type=ctype, cpu_threads=os.cpu_count() or 4)
    # condition_on_previous_text=False: on 20-30 minute talks it stops whisper from looping a phrase.
    segments, info = model.transcribe(audio, language="en", word_timestamps=True, vad_filter=False,
                                      beam_size=5, condition_on_previous_text=False)
    total = float(getattr(info, "duration", 0.0) or 0.0)
    rows, next_report = [], 60.0
    for seg in segments:
        for w in (seg.words or []):
            word = (w.word or "").strip()
            if not word:
                continue
            t = float(w.start)
            e = max(float(w.end), t)
            if rows and t < rows[-1]["t"]:
                t = rows[-1]["t"]
            rows.append({"w": word, "t": round(t, 3), "e": round(e, 3), "c": round(float(w.probability or 0.0), 3)})
        if seg.end >= next_report:
            pct = f" ({seg.end / total:.0%})" if total else ""
            log(f"  transcribed {seg.end / 60:.1f} min{pct}")
            next_report = seg.end + 60.0
    return rows


def run(ctx) -> list[dict]:
    out = Path(ctx.out)
    out.mkdir(parents=True, exist_ok=True)
    src = Path(ctx.words) if getattr(ctx, "words", None) else None
    if src is not None and src.exists():
        rows = load_tsv(src)
        source = "words.tsv"
        log(f"words: {len(rows)} words from {src.name} (timings from your editor).")
    else:
        if src is not None:
            log(f"words: {src} was not found, so board-sync transcribes the WAV itself.")
        if not getattr(ctx, "wav", None) or not Path(ctx.wav).exists():
            sys.exit(f"words: the WAV was not found: {getattr(ctx, 'wav', None)}")
        own = out / "words.tsv"
        if own.exists() and own.stat().st_mtime >= Path(ctx.wav).stat().st_mtime:
            rows = load_tsv(own)
            log(f"words: reusing board-sync's own transcription {own} ({len(rows)} words). "
                "Delete it to transcribe again.")
        else:
            rows = transcribe(ctx.wav)
            write_tsv(own, rows, ctx.fps)
            log(f"words: wrote {own} ({len(rows)} words).")
        source = "faster-whisper"
    if not rows:
        sys.exit("words: no words were read. Check that the words.tsv has start, end and word columns.")
    write_json(out / "words.json", rows)
    ctx.timing_source = source
    log(f"words: wrote {out / 'words.json'} ({len(rows)} words, {rows[0]['t']:.2f}-{rows[-1]['e']:.2f} s, "
        f"timing from {source}).")
    return rows


if __name__ == "__main__":
    import argparse
    import types
    ap = argparse.ArgumentParser(description="board-sync words stage on its own")
    ap.add_argument("--wav")
    ap.add_argument("--words")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", default="24000/1001")
    a = ap.parse_args()
    run(types.SimpleNamespace(wav=a.wav and Path(a.wav), words=a.words and Path(a.words), out=Path(a.out),
                              fps=parse_fps(a.fps)))
