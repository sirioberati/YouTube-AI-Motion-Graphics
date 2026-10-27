---
name: board-sync
description: Animate explainer boards to the presenter's voice. Takes the board HTMLs from Claude Design (04-boards), the final-cut WAV and its words.tsv, the marked script and the board brief; makes every element land on its spoken word; renders one clip per board and a full-length board-track.mp4; checks itself (qa-report.md with contact sheets); and writes the editor timeline for DaVinci Resolve (FCPXML) and Premiere (FCP7 XML) with the camera in the bottom-right zone. Step 5 of the explainer pipeline. Use when the editor says "animate the boards", "sync the boards to his voice", "board video", "render the boards", "build the editor timeline", re-runs one board after a fix, or asks why a board lands early, sits static or covers the camera zone. Runs end to end on Windows and Mac with one setup command (Python via uv, ffmpeg, the installed Edge or Chrome).
---

# board-sync

Step 5 of the explainer pipeline: the boards from Claude Design plus the final-cut audio become a board video where
every element appears on the word that names it, and a timeline the editor opens in DaVinci Resolve or Premiere.

## What it needs (the video's folder)

```
02-cut\<name> - final cut.wav            the final audio (the only sound in the video)
02-cut\<name> - final cut words.tsv      word timings from your editor (if missing, board-sync transcribes the WAV)
02-cut\<name> - final cut.mp4            optional: the 4K cut, only to name it in the timeline
03-board-brief\script-marked.md          the script with [▸ SLIDE n · title] and [CAMERA] markers
03-board-brief\brief.md                  the board brief (builds, anchors, numbers' roles, fillers)
04-boards\NN-Name.html + assets\         one HTML per board from Claude Design, with its assets folder
```

## Setup (once per computer)

Windows, in PowerShell inside this skill's folder:

```
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Mac: `bash setup.sh`. Both are safe to run again. They install uv, a Python 3.12 environment with the packages,
ffmpeg, and check for Edge or Chrome (Playwright's own Chromium is downloaded only if neither is there). The first
transcription, if one is ever needed, downloads the speech model (about 1.6 GB). The setup ends by printing the exact
run command for this computer.

## Run (from the video's folder)

```
& "<skill>\.venv\Scripts\python.exe" "<skill>\board_sync.py" --boards "04-boards" --wav "02-cut\<name> - final cut.wav" --words "02-cut\<name> - final cut words.tsv" --script "03-board-brief\script-marked.md" --brief "03-board-brief\brief.md" --out "05-board-sync\out"
```

On a Mac the same with `<skill>/.venv/bin/python` and forward slashes. Quote every path. Never end a quoted folder
path with a backslash (`"04-boards"`, not `"04-boards\"`).

- `--out` can be left out: it defaults to `05-board-sync\out` next to `04-boards`.
- `--only 4,5` redoes only those boards after a fix; `--stage words|windows|brief|units|choreo|render|qa|timeline|preview`
  runs one stage (each stage reads and writes `--out`, so stages can be re-run alone).
- `--cut "<file>.mp4"` names the 4K cut in the timeline (otherwise it names `02-cut\<name> - final cut.mp4`).
- The background is kept unless the editor passes `--mask <file>` (the cutout luma matte from the cutout step).
  Only then does the timeline get the matte track above the cam; `--camera-keyed` says the full-frame camera
  stretches are keyed too.
- `--check` shows what the computer has (Python, ffmpeg, browser, packages) and which stages are ready.

## What comes out (`05-board-sync\out\`)

| File | What it is |
|---|---|
| `board-track.mp4` | every board at its window, black on camera stretches, exactly as long as the WAV, no audio |
| `boards\NN-Name.mp4` | one clip per board |
| `timeline.fcpxml` | DaVinci Resolve: File, Import, Timeline |
| `timeline-premiere.xml` | Premiere: File, Import |
| `preview.mp4` | the board track with the WAV, for the watch-through only |
| `qa-report.md`, `sheets\NN.jpg` | what to fix, per board, with contact sheets |
| `words.json`, `windows.json`, `sync-manifest.md` | word timings, where each board sits, what lands when |

The timeline: V1 the board track at 200 %, V2 the 4K camera cut at every window (32 % in the bottom-right zone,
80 px from the right and bottom edges, on boards; full frame on camera stretches; its own audio off), A1 the WAV,
no effects. `python scripts/timeline_check.py 05-board-sync\out` prints every clip's in/out, scale and position.

## The QA loop (do this before going on)

Read `qa-report.md`. Fix and re-run until it is clean:

- An element lands before its word, or more than about 2 s after: a timing fix in board-sync (usually the anchor
  words in brief.md), then re-run that board with `--only N`.
- More than about 3 s of speech with nothing new landing: board-sync adds a filler (the presenter's exact words). If it says
  "uncovered > 15 s", a board is missing: back to steps 3 and 4 for that board only.
- A price sticker on a count ("5 out of 13" showing "$13"): fix the number's role in brief.md, re-run.
- Board copy that contradicts what the presenter says: fix the board in Claude Design (never the presenter's words), download that board
  again, re-run.
- Anything in the camera zone: fix the board in Claude Design.

Then watch `preview.mp4` from start to end. Judge by watching. Screenshot anything static, empty or
out of sync and fix it.

Before the first render, look at the boundary table the `windows` stage prints (each board's start and end with the
words around the start). Every board should open on the first words of its block. A board flagged under 40 % matched
means its script lines are not what the presenter said in the final cut: fix script-marked.md, not the timing.

## The rules (all enforced in code; see references/rules.md)

- Land on the spoken word, never before it, never more than 2 s after.
- Named things appear when they are named. A part never appears without its container.
- Structure first: boxes, rails and outlines are there as the board opens; no board opens empty.
- Money and percent stickers only on money words; a count never gets a price sticker.
- Nothing static for more than 3 to 4 s while the presenter talks: fillers are the presenter's exact words.
- Nothing moves after it lands: no zooms, no push-ins, no pulses, no camera moves.
- No music, no sound effects. The WAV is the only sound; no limiter on the voice.
- The camera zone (bottom right, 615 x 430 px at 1080p) stays empty on every board.
- Board copy that contradicts the presenter's words is flagged, never silently changed.
- Ad-libs are never dropped: every spoken word stays in the window it falls in.

## When something goes wrong

See `references/troubleshooting.md`: no browser found, ffmpeg missing, words.tsv missing, a board under 40 % match,
fonts not loading, Windows path quoting, long renders.

## Notes for Claude running this skill

- Exporting the full board video (player with camera, clips and voice): follow the export rules in the html-to-mp4 skill.
  Every clip seeks on every frame, preflight 90 frames first, detached MKV workers, keyframe every 15 frames, TS join,
  then verify frame count, keyframe gap and motion before reporting. The AI Video Editing System project has this as
  `05-board-sync/export.sh`.

- Run the whole thing with one command; re-run single stages only to fix something. Exit code 0 means every stage
  that exists ran; QA findings are in the report, not in the exit code.
- Contracts between stages (file names, JSON shapes) are in `DESIGN.md`. `scripts/common.py` holds the shared helpers.
- The test fixture is built by `tests/make_fixture.py <v2 project> <deck html export>` into `fixtures/` (generated
  data, not shipped).
