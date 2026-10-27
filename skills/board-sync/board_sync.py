"""board-sync: explainer boards + the final-cut audio -> a word-synced board video and an editor timeline.

Run (paths may contain spaces; quote them; on Windows never end a quoted folder path with a backslash):

  python board_sync.py --boards 04-boards --wav "02-cut/<name> - final cut.wav"
                       --words "02-cut/<name> - final cut words.tsv"
                       --script 03-board-brief/script-marked.md --brief 03-board-brief/brief.md
                       [--out 05-board-sync/out] [--cut "02-cut/<name> - final cut.mp4"]
                       [--mask "02-cut/cutout/final-mask.mp4"] [--camera-keyed]
                       [--fps 24000/1001] [--only 4,5] [--stage all|words|windows|brief|units|choreo|render|qa|timeline|preview]

--out defaults to 05-board-sync/out next to the boards folder (<boards>/../05-board-sync/out).
--mask is used only when it is passed: the background is kept unless the editor passes --mask (a luma matte from the
cutout step). Without it the timeline has the cam with its real background, in the zone on board stretches and full
frame on [CAMERA] stretches.

Every stage reads its inputs from --out and writes there, so one stage can be re-run on its own. The exit code is 0
even when the QA report has findings; it is non-zero only when a stage cannot run (missing file, no browser, no ffmpeg).
"""
from __future__ import annotations

import argparse
import importlib
import os
import platform
import shutil
import sys
import time
import traceback
import types
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent

for _stream in (sys.stdout, sys.stderr):   # Windows pipes default to cp1252: never crash printing "▸", "→" or "’"
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from scripts.common import log, parse_fps  # noqa: E402

STAGES = ["words", "windows", "brief", "units", "choreo", "render", "qa", "timeline", "preview"]
NEEDS = {   # inputs a stage cannot run without (checked before the stage starts)
    "words": ["out"],
    "windows": ["script", "wav", "out"],
    "brief": ["out"],
    "units": ["boards", "out"],
    "choreo": ["boards", "out"],
    "render": ["boards", "out"],
    "qa": ["out"],
    "timeline": ["wav", "out"],
    "preview": ["wav", "out"],
}
FLAG = {"boards": "--boards", "wav": "--wav", "script": "--script", "out": "--out", "brief": "--brief",
        "words": "--words", "cut": "--cut"}


def clean_path(value: str | None) -> Path | None:
    """A path argument as typed in PowerShell/cmd/zsh. Strips stray quotes (a quoted path ending in a backslash leaves
    a trailing quote on Windows) and catches the case where that swallowed the next arguments."""
    if value is None:
        return None
    v = value.strip().strip('"').strip("'").strip()
    if ' --' in v:
        sys.exit(f"This path swallowed the next arguments: {value!r}\n"
                 "On Windows, do not end a quoted folder path with a backslash: write \"04-boards\", not \"04-boards\\\".")
    return Path(v).expanduser()


def build_ctx(a: argparse.Namespace) -> types.SimpleNamespace:
    only = None
    if a.only:
        try:
            only = {int(x) for x in a.only.replace(" ", "").split(",") if x}
        except ValueError:
            sys.exit(f"--only takes board numbers separated by commas, like 4,5 (got {a.only!r}).")
    ctx = types.SimpleNamespace(
        boards=clean_path(a.boards), wav=clean_path(a.wav), words=clean_path(a.words), script=clean_path(a.script),
        brief=clean_path(a.brief), cut=clean_path(a.cut), out=clean_path(a.out), mask=clean_path(a.mask),
        camera_full_background=not a.camera_keyed, fps=parse_fps(a.fps), only=only, skill_dir=SKILL_DIR,
        stage=a.stage)
    for k in ("boards", "wav", "words", "script", "brief", "cut", "out", "mask"):
        p = getattr(ctx, k)
        if p is not None:
            setattr(ctx, k, Path(os.path.abspath(p)))   # absolute, symlinks kept (a linked WAV keeps its own name)
    if ctx.out is None and ctx.boards is not None:
        # 04-boards -> 05-board-sync/out beside it; any other boards folder -> <boards>/../05-board-sync/out (same rule)
        ctx.out = ctx.boards.parent / "05-board-sync" / "out"
        log(f"--out not given: writing to {ctx.out}")
    # the background is never removed unless the editor asks: a mask is used only when --mask is passed
    if ctx.mask is not None and not ctx.mask.exists():
        log(f"! --mask {ctx.mask} does not exist yet; the timeline will name it there (relink it in the editor).")
    if ctx.out is not None:
        ctx.out.mkdir(parents=True, exist_ok=True)
    return ctx


def check_inputs(stage: str, ctx) -> None:
    for k in NEEDS.get(stage, []):
        p = getattr(ctx, k)
        if p is None:
            sys.exit(f"stage {stage} needs {FLAG[k]}.")
        if k != "out" and not p.exists():
            sys.exit(f"stage {stage}: {FLAG[k]} was not found: {p}")
    if ctx.boards is not None and stage in ("units", "choreo", "render") and not ctx.boards.is_dir():
        sys.exit(f"stage {stage}: --boards must be the folder with the NN-Name.html files: {ctx.boards}")


def load_stage(stage: str):
    """The stage's module, or None when it is not in this copy of board-sync yet."""
    name = f"scripts.{stage}"
    try:
        mod = importlib.import_module(name)
    except ModuleNotFoundError as e:
        if e.name in (name, "scripts"):
            return None
        raise
    return mod if hasattr(mod, "run") else None


def run_stage(stage: str, ctx) -> bool:
    try:
        mod = load_stage(stage)
    except ModuleNotFoundError as e:
        sys.exit(f"stage {stage} cannot run: the Python package '{e.name}' is missing. Run setup.ps1 / setup.sh again.")
    if mod is None:
        log(f"stage {stage} not available (scripts/{stage}.py is missing or has no run()); skipped.")
        return False
    check_inputs(stage, ctx)
    log(f"\n== {stage} ==")
    t0 = time.time()
    try:
        mod.run(ctx)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(f"stage {stage} stopped by you.")
    except Exception:
        traceback.print_exc()
        sys.exit(f"stage {stage} failed (the error is above). Fix it and re-run with --stage {stage}.")
    log(f"   {stage} done in {time.time() - t0:.1f} s")
    return True


def check_env() -> int:
    """--check: what this machine has (python, ffmpeg, browser, packages). Exit 0 when everything needed is there."""
    ok = True
    log(f"python      {platform.python_version()} ({sys.executable})")
    for exe in ("ffmpeg", "ffprobe"):
        p = shutil.which(exe)
        if not p:
            try:
                import static_ffmpeg  # type: ignore
                static_ffmpeg.add_paths()
                p = shutil.which(exe)
            except Exception:
                p = None
        log(f"{exe:<11} {p or 'MISSING (run setup)'}")
        ok &= bool(p)
    for pkg in ("faster_whisper", "playwright", "numpy", "PIL"):
        try:
            importlib.import_module(pkg)
            log(f"{pkg:<11} ok")
        except Exception:
            log(f"{pkg:<11} MISSING (run setup)")
            ok = False
    found = browsers()
    log(f"browser     {found[0] if found else 'none found: setup installs Playwright chromium'}")
    for st in STAGES:
        try:
            have = load_stage(st) is not None
        except Exception as e:   # a module that fails to import is reported, not hidden
            have = False
            log(f"stage {st:<9} import error: {e}")
            continue
        log(f"stage {st:<9} {'ready' if have else 'not available'}")
    return 0 if ok else 1


def browsers() -> list[str]:
    """Installed Edge/Chrome executables (what render.py launches through Playwright channels)."""
    cands: list[Path] = []
    if sys.platform.startswith("win"):
        import os
        for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
            if base:
                cands += [Path(base) / "Microsoft/Edge/Application/msedge.exe", Path(base) / "Google/Chrome/Application/chrome.exe"]
    elif sys.platform == "darwin":
        for base in (Path("/Applications"), Path.home() / "Applications"):
            cands += [base / "Microsoft Edge.app", base / "Google Chrome.app"]
    else:
        cands += [Path(p) for p in (shutil.which("microsoft-edge") or "", shutil.which("google-chrome") or "",
                                    shutil.which("chromium") or "") if p]
    return [str(p) for p in cands if str(p) and p.exists()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="board_sync.py", description="Word-sync explainer boards to the final-cut audio.")
    ap.add_argument("--boards", help="folder with the board HTMLs (NN-Name.html) and their assets folder")
    ap.add_argument("--wav", help="the final-cut WAV")
    ap.add_argument("--words", help="the final-cut words.tsv from your editor (optional: without it the WAV is transcribed)")
    ap.add_argument("--script", help="script-marked.md with [▸ SLIDE n · title] and [CAMERA] markers")
    ap.add_argument("--brief", help="brief.md (optional: without it every element lands on its own text)")
    ap.add_argument("--cut", help="the 4K final cut MP4 (optional: only to name it in the timeline files)")
    ap.add_argument("--out", help="output folder (default: 05-board-sync/out next to the boards folder)")
    ap.add_argument("--mask", help="only if the editor wants the background removed: the cutout luma matte (mask.mp4, "
                                   "same length and fps as the cut), put on the track above the cam in both timelines. "
                                   "Without it the cam keeps its real background")
    ap.add_argument("--camera-keyed", action="store_true",
                    help="the full-frame [CAMERA] stretches are keyed too (default: they keep the real background)")
    ap.add_argument("--fps", default="24000/1001", help="frame rate of the cut (default 24000/1001 = 23.976)")
    ap.add_argument("--only", help="re-do only these boards, e.g. 4,5")
    ap.add_argument("--stage", default="all", choices=["all"] + STAGES, help="run one stage (default: all, in order)")
    ap.add_argument("--check", action="store_true", help="show what this machine has and which stages are ready, then stop")
    a = ap.parse_args(argv)
    if a.check:
        return check_env()
    if not a.out and not a.boards:
        ap.error("--out is required when --boards is not given (the output folder, e.g. 05-board-sync/out)")
    ctx = build_ctx(a)
    stages = STAGES if a.stage == "all" else [a.stage]
    log(f"board-sync: {', '.join(stages)} -> {ctx.out}")
    ran, skipped = [], []
    for st in stages:
        (ran if run_stage(st, ctx) else skipped).append(st)
    log(f"\nboard-sync finished. Ran: {', '.join(ran) or 'nothing'}."
        + (f" Not available: {', '.join(skipped)}." if skipped else ""))
    if "qa" in ran and (ctx.out / "qa-report.md").exists():
        log(f"Read the QA report next: {ctx.out / 'qa-report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
