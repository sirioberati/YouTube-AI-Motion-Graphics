"""Shared helpers for board-sync: paths, fps maths, token normalisation, ffmpeg lookup, logging."""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys
from fractions import Fraction
from pathlib import Path

NUMWORDS = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
            "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15",
            "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30", "forty": "40",
            "fifty": "50", "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90", "hundred": "100", "thousand": "1000",
            "million": "1000000", "billion": "1000000000"}
STOP = {"the", "a", "an", "and", "or", "but", "so", "to", "of", "in", "on", "at", "is", "it", "its", "it's", "that", "this",
        "for", "with", "as", "by", "be", "are", "was", "were", "you", "your", "i", "my", "we", "our", "they", "their", "them",
        "he", "she", "his", "her", "do", "does", "did", "not", "no", "yes", "if", "then", "than", "there", "here", "what",
        "which", "who", "how", "when", "where", "just", "like", "now", "very", "really", "basically", "actually", "guys"}


def norm(tok: str) -> str:
    """Lowercase, keep letters/digits/$/%/', number words → digits. '' for pure punctuation."""
    t = tok.lower().strip().replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", "").replace("\u201d", "")
    t = re.sub(r"[^\w$%']", "", t)
    t = t.replace("_", "")
    if t in NUMWORDS:
        return NUMWORDS[t]
    return t


def tokens(text: str) -> list[str]:
    """Normalised tokens of a text, empty tokens dropped. Keeps '$9', '.40'→'40', '5,000'→'5000'."""
    out = []
    for raw in re.findall(r"[\w$%'.,]+", text):
        raw = raw.replace(",", "") if re.fullmatch(r"[\d,]+", raw) else raw
        t = norm(raw)
        if t:
            out.append(t)
    return out


def same(a: str, b: str) -> bool:
    """Loose equality for anchoring: exact, or digits-only forms equal, or one is the other's stem (plural/possessive)."""
    if a == b:
        return True
    da, db = re.sub(r"\D", "", a), re.sub(r"\D", "", b)
    if da and db and da == db and (a.startswith("$") or b.startswith("$") or a.isdigit() or b.isdigit()):
        return True
    for x, y in ((a, b), (b, a)):
        if len(x) >= 4 and (y == x + "s" or y == x + "'s" or y == x + "es" or y == x + "ed" or y == x + "ing"):
            return True
    return False


def parse_fps(s: str | float) -> Fraction:
    if isinstance(s, (int, float)):
        return Fraction(s).limit_denominator(1001)
    s = str(s).strip()
    if "/" in s:
        n, d = s.split("/")
        return Fraction(int(n), int(d))
    return Fraction(s).limit_denominator(1001)


def frames_for(seconds: float, fps: Fraction) -> int:
    return int(round(seconds * fps))


def seconds_for(frames: int, fps: Fraction) -> float:
    return float(frames / fps)


def which_ffmpeg(name: str = "ffmpeg") -> str:
    p = shutil.which(name)
    if p:
        return p
    try:
        import static_ffmpeg  # type: ignore
        static_ffmpeg.add_paths()
        p = shutil.which(name)
        if p:
            return p
    except Exception:
        pass
    sys.exit(f"{name} not found. Run setup.ps1 / setup.sh (it installs ffmpeg) or put ffmpeg on PATH.")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], check=True, capture_output=True, text=True, **kw)


def probe_duration(path: Path) -> float:
    r = run([which_ffmpeg("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(r.stdout.strip())


def read_json(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path, data) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def log(msg: str) -> None:
    print(msg, flush=True)


CAM_ZONE_1080 = {"x": 1920 - 40 - 615, "y": 1080 - 40 - 430, "w": 615, "h": 430}   # bottom-right camera zone at 1080p
CAM_ZONE_4K = {"x": 3840 - 80 - 1230, "y": 2160 - 80 - 860, "w": 1230, "h": 860}
