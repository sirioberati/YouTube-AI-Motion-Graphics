# board-sync · design and module contracts

board-sync turns explainer boards (Design-Component HTML exports from Claude Design, one 1920×1080 board per file)
plus the final-cut audio into a word-synced board video and an editor timeline. Step 5 of the explainer pipeline
(`~/.claude/skills/explainer-video-pipeline/references/step-5-animate.md`). Self-contained: Python via uv, ffmpeg,
Playwright driving the installed Edge/Chrome, GSAP bundled. Windows first, Mac second. No HyperFrames, no Mac-only tools.

## Folder
```
board-sync/   (shipped inside the Editor Handoff Kit: no absolute paths to any machine in any file; setup.ps1 / setup.sh at this root)
  SKILL.md                      what it is, how a trainee runs it, the rules, the QA loop
  DESIGN.md                     this file
  setup.ps1  setup.sh           one-click: uv, venv, requirements, ffmpeg, browser check
  requirements.txt              faster-whisper, playwright, numpy, pillow, (static-ffmpeg as fallback)
  board_sync.py                 CLI: all stages, or --stage X
  scripts/
    words.py      read words.tsv (primary) or run faster-whisper (fallback) → words.json
    windows.py    script-marked.md + words.json → windows.json (slide windows, camera stretches, uncovered)
    brief.py      brief.md → brief.json (per board: builds, number roles, fillers, tags, flags)
    units.py      board HTML → units.json (every element: id, kind, text, bbox, move)
    choreo.py     units + brief + words → cues (NN.cues.json) + scene HTML (NN.html) with the player
    render.py     scene HTML → boards/NN-Name.mp4 (Playwright frame-step + ffmpeg); track assembly
    qa.py         real frames vs the word list → qa-report.md + sheets/
    timeline.py   windows.json → timeline.fcpxml (Resolve) + timeline-premiere.xml (FCP7 XML)
    preview.py    board-track.mp4 + WAV → preview.mp4
    common.py     paths, fps maths, logging, ffmpeg/ffprobe lookup
  assets/
    gsap.min.js   GSAP 3.14.x (bundled, offline)
    kit.js        the move library (rise, wipe, grow, growx, pop, write, draw, stamp, hide, note) on one paused timeline
    player.html   template: <board DOM> + kit + cues → window.__seek(t), window.__dur, window.__ready
  references/
    rules.md          your rules, verbatim, and how each is enforced in code
    brief-format.md   what board-sync reads from script-marked.md and brief.md
    troubleshooting.md
  tests/
    make_fixture.py   builds fixtures/ from your v2 project (boards, wav, words.tsv, script-marked.md, brief.md); paths are arguments
    stub-*.{html,json} tiny stub scene for render/QA self-tests
  fixtures/           generated test data only (excluded from the handoff kit); never shipped
```

## CLI
```
uv run board_sync.py --boards <dir> --wav <file> [--words <file.tsv>] --script <script-marked.md> --brief <brief.md>
                     [--cut <final cut.mp4>] --out <dir> [--fps 24000/1001] [--only 4,5] [--stage all|words|windows|choreo|render|qa|timeline|preview]
```
Every stage reads its inputs from `--out` and writes there, so a stage can be re-run alone. Exit code 0 even with QA
findings; non-zero only when a stage cannot run (missing file, no browser, no ffmpeg). Log lines are plain English.

Inputs are separate paths. The trainee's layout is `04-boards\`, `02-cut\<name> - final cut.wav`,
`02-cut\<name> - final cut words.tsv`, `03-board-brief\script-marked.md|brief.md`, `05-board-sync\out\`.
Windows paths with spaces and backslashes must work (pathlib everywhere, never shell string concatenation).

## Outputs in --out
```
words.json          [{"w": "If", "t": 0.00, "e": 0.28, "c": 0.77}, …]   t/e seconds on the final timeline
windows.json        see below
brief.json          parsed brief
units/NN.json       parsed board
cues/NN.cues.json   the timeline of board NN (see below)
scenes/NN.html      the renderable scene (self-contained: inlined board DOM, kit, gsap, cues; assets by relative path)
boards/NN-Name.mp4  one clip per board, exactly round((end-start)*fps) frames, 1920×1080, H.264 yuv420p, no audio
board-track.mp4     every board at its window, black elsewhere, exactly round(wav_duration*fps) frames, no audio
preview.mp4         board-track.mp4 + the WAV (aac 192k), for the watch-through only
timeline.fcpxml     DaVinci Resolve
timeline-premiere.xml  Premiere (FCP7 XML)
sync-manifest.md    per board: every element, its anchor, its landing time; notes; stamps
qa-report.md        findings, per board, with the sheets linked
sheets/NN.jpg       contact sheet of the real render at the landing times
```

## words.json / words.tsv
words.tsv (your editor export, primary): tab-separated, header `start  end  word  frame_in  frame_out  confidence`,
seconds on the final timeline at 24000/1001, one row per word, punctuation attached to the word ("$9", ".40", "it?").
Fallback: faster-whisper `large-v3-turbo` (word_timestamps=True, language en, vad_filter off) on the WAV, written in
the same tsv format to `--out/words.tsv` and flagged in the QA report ("timing from board-sync's own transcription").
Normalisation for matching (shared, in common.py): lowercase, strip everything except letters, digits, `$`, `%`, `'`;
number words to digits (one…twelve, twenty, thirty, hundred, thousand, million as tokens), `$9 .40` style splits joined
when a token is only digits/punctuation; "half a million" is also matched as 500000/500K.

## windows.json
```
{"fps": "24000/1001", "wav_duration": 1655.65, "timing_source": "words.tsv" | "faster-whisper",
 "items": [
   {"kind": "board", "n": 4, "title": "Your own team, cheaper", "file": "04-OwnTeam.html",
    "start": 33.76, "end": 53.12,                       # seconds on the final timeline (start = 0.15 s before the first matched word, never inside the previous item)
    "script_lines": ["Think about it like this.", …],   # the lines under the marker, verbatim
    "words": [{"w","t","e"}…],                           # every spoken word inside the window, INCLUDING ad-libs
    "matched": 0.86,                                     # share of script tokens found
    "uncovered": [{"start": 44.1, "end": 61.3, "text": "…"}]   # spoken stretches > 15 s with no script line (ad-libs) → stays in the window, flagged
   },
   {"kind": "camera", "start": 53.12, "end": 57.18, "words": [...]}
 ]}
```
Matching: tokens of each `[▸ SLIDE N]` block (and each `[CAMERA]` block) are aligned to the word list with difflib
SequenceMatcher on normalised tokens, in order, monotonic (a block never starts before the previous block's end).
A block's first matched word gives its start (minus 0.15 s, clamped), the next block's start gives its end; the last
block ends at the WAV end. Words the script does not contain (ad-libs) are never dropped: they stay in whichever
window they fall in. A board whose block matches under 40 % of its tokens is reported, not guessed. A board with no
lines (a hold board) takes the gap between its neighbours.

## brief.json
From brief.md (template in `~/.claude/skills/explainer-board-brief/references/brief-template.md`, both the full and the
compact board format). Per board: `n`, `title`, `lines`, `type`, `builds` = ordered list of `{"element": "<text or
description>", "anchor": "<verbatim words>" | "structure"}`, `numbers` = `{"$500,000": "money", "5 of 13": "count"}`,
`fillers` = free text split into items, `tag`, `flags`. Board n is matched to the HTML file by its leading number
`NN-`. Missing brief → every element is anchored by its own text (fallback) and the report says so.

## units/NN.json
From the board HTML (Design-Component export: a 1920×1080 root with absolutely positioned children; classes seen on
Typical decks: `m-type` (typed text), `m-hand` (handwriting), `m-draw` (SVG stroke), `m-pop` (sticker/card),
`m-at-NNNN` (the export's own delay, ignored), inline `rotate()`; a Motion `<script>` that loops on its own timers:
DROP it). Units are the direct children of the root in DOM order, plus nested rows of a receipt/list (`m-type` lines)
and SVG strokes, each with: `id` (uNN), `kind` (headline | label | row | bar | sticker | note | arrow | container |
icon | image | legend | zone), `text`, `bbox` {x,y,w,h} measured in the browser (getBoundingClientRect after fonts
are ready, so a hidden-at-start element is measured before hiding), `children` (ids), `price` (if the text carries
$ or %), `default_move` by kind: headline → label (visible at 0, highlight pop on its word), container/zone → rise,
row → wipe, bar → grow (origin bottom), sticker/card → pop (from 0.82), note → write, arrow/stroke → draw,
icon/image → rise, legend → rise at 0.25 s. Camera zone = x ≥ 1920-40-615, y ≥ 1080-40-430 (1080p); a unit whose bbox
overlaps it is a QA finding (except on a board whose brief says it is the black silent board).

## cues/NN.cues.json
```
{"n": 4, "dur": 19.36, "start": 33.76, "fps": "24000/1001",
 "cues": [{"id": "u2", "move": "rise", "t": 0.45, "why": "structure"},
          {"id": "u3", "move": "write", "t": 2.19, "why": "anchor 'Kevin' @2.19"},
          {"id": "n1", "move": "note", "t": 14.47, "text": "Kevin's own services, for less", "x": 1240, "y": 300, "size": 84, "style": "hand", "until": 19.0},
          {"id": "u5", "move": "stamp", "t": 4.92, "why": "money '$5,000' said '$5 ,000'"}],
 "flags": ["copy '$150–240K/yr' vs spoken '$100,000 to $200,000'"]}
```
Times are board-local seconds. Rules applied, in this order (all from real reviews, see references/rules.md):
1. Structure first: containers, zones, outlines, rails, chart baselines cascade from 0.45 s (+0.12 each); the first
   content item by 0.9 s; a board under 5 s gets its whole structure plus labels inside the first second.
2. Every build in the brief lands on its anchor: first occurrence of the verbatim phrase inside the board's words
   (normalised match, tolerant of punctuation and "$9 .40"); t = word.t - board.start, +0.05. If the phrase is not
   found: try the element's own text; then the brief line's key number; then report "anchor not found" and cascade
   the element 0.2 s after the previous one (never hide silently).
3. Never before the word, never more than 2 s after; a chain (`with:`) lands 0.1 s after its target.
4. Named things on their name; a part never without its container (a child's t ≥ its container's t + 0.1; the
   container is pulled to the child's t - 0.1 if the brief anchored only the child); an arrow never before both ends.
5. Money vs count: a stamp (1.5× pop then settle, caps 1.22× over 70 px) only on a number whose brief role is money
   or percent and whose spoken token carries $, dollars, bucks, %, percent, or follows pay/costs/at/is/about/list.
   Never after "of"/"out", never before different/sellers/prices/versions/seconds/minutes/lines/apps/clips.
6. Nothing static over 3 s while the presenter talks: the brief's fillers first (each with its anchor), then auto notes: a phrase
   of 2–4 of the presenter's exact words (numbers or 5+-letter words not already on the board), hand style, placed in the largest
   free rectangle at that moment (measured from the bboxes of what is visible), big (130/96 px) under 15 % coverage,
   84/64 under 40 %, else 54 px; one every ~3.2 s, 16 per board max, never in the camera zone, fading when something
   lands on it or after 9 s.
7. Nothing moves after it lands: no pulses, no nudges, no camera moves, no loops. The headline highlight pops once on
   its word. No sound effects, no music.
8. Reading order: rows top to bottom in spoken order; if the voice names a lower row first, keep the order and land it on its word anyway.
9. Copy that contradicts speech (a number on the board whose role is money and no spoken number matches it within the
   window, or a brief flag) → `flags`, never changed.
10. Uncovered speech > 15 s (from windows.json) → the report proposes a new board with the spoken words.

## scenes/NN.html and the player
One self-contained HTML per board: the board's root DOM inlined (its own `<link>`s rewritten to absolute file paths of
the board folder's assets so fonts and images load), `assets/gsap.min.js` and `assets/kit.js` inlined, the cues
inlined as JSON. `kit.js` builds ONE paused GSAP timeline from the cues (every tween at an absolute time,
immediateRender false, gsap.set baselines at build; hidden-at-start elements set with opacity 0 before the first
frame), exposes `window.__seek(t)` (timeline.seek(t, false) then `document.fonts.ready`), `window.__dur`, and
`window.__ready` (a promise resolved after fonts and images). Deterministic: no Date.now, no Math.random, no CSS
animations or transitions (kit injects `* { animation: none !important; transition: none !important }`), no DrawSVG
(stroke draw = manual strokeDasharray/strokeDashoffset tween), stroke `pathLength` computed once at build.

## render.py
Playwright (python) → `chromium.launch(channel="msedge")`, else `channel="chrome"`, else bundled chromium
(`playwright install chromium`, offered by setup). Viewport 1920×1080, deviceScaleFactor 1, `page.goto(file://…)`,
await `__ready`. For frame i in range(frames): `__seek(i/fps)`, `page.screenshot(type="png")` → ffmpeg stdin
(`-f image2pipe -c:v png -r 24000/1001 -i -` → `-c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p
-color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 -r 24000/1001 -movflags +faststart`).
Boards render in parallel (one browser context each, default min(3, cpu//2)). `frames = round((end-start)*fps)`
exactly. Track: the board clips plus black clips (`color=black:s=1920x1080:r=24000/1001`, same encoder settings) in
window order through the concat demuxer with `outpoint` per entry, `-c copy`; total frames = round(wav_duration*fps);
verified with ffprobe after writing (±1 frame → re-done with a trailing black pad).

## qa.py
From the REAL clips. For each cue with a bbox: grab the frame at t-0.1 and t+0.5 (ffmpeg select by frame index),
mean abs diff inside the bbox: the element must be absent/unchanged before and present after; failure = "lands early"
or "did not land". Dead stretches: consecutive cue times > 3 s apart while words are spoken (from windows.json) →
listed with the spoken words. Stamps: listed with the three spoken words around them. Uncovered > 15 s: listed as
"propose a new board: <words>". Camera zone: sampled frames (every 2 s) with non-background pixels inside the zone →
finding. Copy flags from cues. Timing source and match ratios per board. Contact sheet per board: 16 frames at the
cue times, 4×4, 480 px wide each, with the time stamped in a corner. Report is plain markdown with a one-line verdict
per board (clean / N findings) and the fix for each finding in the trainee's terms (see step-5-animate.md's loop).

## timeline.py
Sequence 3840×2160 @ 24000/1001 (matches the cut), duration = WAV duration.
V1: the cut (`--cut` path, or a placeholder named "<name> - final cut.mp4"), one clip per window: on board windows
scale 32 % and position so the clip sits in the bottom-right zone 80 px from the right and bottom edges (1230×860 at
4K); on camera windows scale 100 %, centred; the clip's own audio DISABLED/muted.
V2: board-track.mp4 (1920×1080) scaled 200 % to fill the frame, one clip, from 0.
A1: the WAV, one clip from 0, no effects, no limiter, gain 0 dB.
FCPXML 1.9: resources (format r1 3840x2160 24000/1001; assets with absolute file URLs and the WAV as audio-only),
library/event/project/sequence/spine; the cam clips carry `<adjust-transform scale="0.32 0.32" position="x y">`
(position in FCPXML is in sequence pixels from centre: x = 1920-80-615 = 1225 → centre offset (1225, -650)? compute
from the zone: zone centre at (3840-80-615, 2160-80-430) = (3145, 1650); offset from frame centre = (1225, -570) in
FCPXML's y-up convention), audio role disabled by omitting the audio lane and setting the asset's `hasAudio="0"` on
the connected use or `<clip ... audioRole>` muted via `enabled="0"` on its audio component.
FCP7 XML (xmeml version 5): sequence 3840×2160 timebase 24 ntsc TRUE, video tracks V1/V2 with `<filter>` Basic Motion
(scale 32, center x/y in Premiere's normalised units: center = ((zone centre x - 1920)/3840*…) — document the formula
in the code and verify on a known case), audio track with the WAV, the cam clip's audio track omitted. Both files are
validated as well-formed XML and, where a reference file exists (tests/reference/*.xml), diffed structurally.

## preview.py
`ffmpeg -i board-track.mp4 -i <wav> -c:v copy -c:a aac -b:a 192k -shortest preview.mp4` (the WAV is already the track length).

## setup.ps1 / setup.sh
Windows: `winget install astral-sh.uv` if uv is missing (or the irm installer), `uv venv .venv --python 3.12`,
`uv pip install -r requirements.txt`, ffmpeg via `winget install Gyan.FFmpeg` if missing (fallback: pip
`static-ffmpeg` and `static_ffmpeg.add_paths()` in common.py), check Edge/Chrome (`playwright install chromium` only if
neither exists), print the one-line run command. Mac: brew for uv/ffmpeg, else the same fallbacks. Idempotent; no admin
rights beyond winget's usual prompt.

## Fixture and test
`tests/make_fixture.py <v2-project-dir> <deck-html-dir>` builds `fixtures/` from an earlier project (both paths are arguments, never defaults; `fixtures/` is excluded from the shipped kit):
boards = `cards/HNNName.html` copied as `NN-Name.html` with `assets/` (fonts, img, video), wav = `assets/vo.wav`,
words.tsv = `edited-cut/transcript-words.tsv`, script-marked.md = per card `[▸ SLIDE N · title]` + the card's spoken
words from `vo.json` (every word, as spoken), brief.md = per card the builds from `choreo/cNN.json` (unit text →
phrase) and the unit list from `build-manifest.txt`, numbers' roles from the stamps rule. The full run on the fixture
is the acceptance test: 34 boards, zero "anchor not found" on boards with a brief, no dead stretch over 4 s, track
frames = round(1655.65 * 24000/1001), both XML files well-formed.
