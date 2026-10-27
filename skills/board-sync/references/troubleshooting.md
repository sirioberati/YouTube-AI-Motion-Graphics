# board-sync: troubleshooting

Start with the self-check. It says what is missing in plain words:

```
"<skill>\.venv\Scripts\python.exe" "<skill>\board_sync.py" --check        (Windows)
"<skill>/.venv/bin/python" "<skill>/board_sync.py" --check                (Mac)
```

If `.venv` does not exist, setup has not run on this computer: run `setup.ps1` (Windows) or `setup.sh` (Mac).

## No browser found

board-sync renders the boards in the Edge or Chrome that is already installed (through Playwright). If `--check` says
"browser: none found", either install Chrome, or let setup fetch Playwright's own Chromium:

```
"<skill>\.venv\Scripts\python.exe" -m playwright install chromium
```

Edge is on every Windows 10/11 computer, so on Windows this usually means Edge was removed or lives in an unusual
folder. A company laptop may block the Chromium download; then install Chrome from google.com/chrome.

## ffmpeg missing ("ffmpeg not found")

Run setup again: it installs ffmpeg with winget (Windows, package `Gyan.FFmpeg`) or brew (Mac). If winget is not
allowed on the computer, setup falls back to the `static-ffmpeg` package inside the venv, which downloads ffmpeg the
first time it is used. After a winget install, close and reopen PowerShell so the new PATH is seen.

## words.tsv missing

Without `02-cut\<name> - final cut words.tsv`, board-sync transcribes the WAV itself (faster-whisper large-v3-turbo).
That works, but:

- the first time it downloads the model (about 1.6 GB);
- on a CPU it takes about three times the audio's length (a 27-minute video: over an hour); with an NVIDIA GPU a
  few minutes;
- the QA report says "timing from board-sync's own transcription".

The better fix is to export the words.tsv from your editor (step 2) and pass it with `--words`. board-sync keeps its
own transcription in `05-board-sync\out\words.tsv` and reuses it on the next run; delete that file to transcribe again
(for example after the cut changed).

## A board under 40 % match

The `windows` stage prints a table with each board's start, end and the words around its start, and warns
"board N: only X % of its script words were found in the audio". It means the lines under that board's marker in
`script-marked.md` are not what the presenter says in the final cut: the script was written before the edit, a section was cut,
or the marker sits on the wrong lines. board-sync does not guess where such a board goes: it gives it the gap between
its neighbours and reports it.

Fix: open `script-marked.md`, compare that board's lines with the final cut (`02-cut\<name> - final cut script.txt`
or the subtitles), put the actual spoken words under the marker, then re-run from the windows stage:

```
... board_sync.py <same arguments> --stage windows
```

Related messages:
- "no lines under the marker, it is a hold board": intended for a silent or breath board; it takes the gap between
  its neighbours. If it was not meant to be a hold board, the lines went under the wrong marker.
- "board N has two markers in the script": two boards share a number. Renumber one; both point at the same file.
- "N s of speech with no script line under it": an ad-lib longer than 15 s. It stays on the board it falls in; the
  QA report proposes a new board for it.
- "speech before the first marker": add a `[CAMERA]` or `[▸ SLIDE 1 · …]` marker above the first spoken line.

## Fonts not loading (boards render in a fallback font)

The board HTMLs load their fonts from the `assets` folder next to them (`assets\fonts.css`, `assets\fonts\*.woff2`).
Check:

- `04-boards\assets\` exists and was downloaded together with the boards from Claude Design (not only the HTMLs);
- the HTML files were not renamed into a different folder from `assets`;
- the font files are not blocked: on Windows, right-click a downloaded zip, Properties, Unblock, before unzipping.

Then re-run the boards that looked wrong with `--only N`. The contact sheets in `sheets\` show the real rendered
frames, so a wrong font is visible there.

## Windows path quoting

- Quote every path that has a space: `--wav "02-cut\my-video - final cut.wav"`.
- Never end a quoted folder path with a backslash. `"04-boards\"` makes Windows read the closing quote as part of
  the path and swallow the next arguments; board-sync stops with "This path swallowed the next arguments". Write
  `"04-boards"`.
- In PowerShell, start the command with `&` when the first item is a quoted path (the command setup prints already
  does).
- Run the command from the video's folder, or give full paths. `--out` defaults to `05-board-sync\out` next to the
  boards folder.
- OneDrive folders work, but files "online only" are downloaded on first read; keep the video folder "always on
  this device" while rendering.

## Long renders

Rendering takes every frame of every board through the browser, so a 27-minute video is about 40,000 frames.

- Re-render only what changed: `--only 4,5` after fixing boards 4 and 5; the board track is rebuilt from the clips.
- Re-run single stages when nothing upstream changed: `--stage qa`, `--stage timeline`, `--stage preview`.
- Close other heavy apps (the editor, a second browser) while it renders; boards render in parallel, one browser
  tab each.
- Keep the laptop plugged in and awake (Windows: Settings, System, Power, never sleep while plugged in).
- If it was interrupted, look in `05-board-sync\out\boards\` for the clips already made and render the rest with
  `--only` (for example `--only 18,19,20`); the board track is assembled from all the clips at the end of every
  render.

## The timeline opens with offline media

The timeline files point at the absolute paths of the cut, the board track and the WAV on the computer that ran
board-sync. On another computer, or after moving the folder, relink: Resolve asks when importing; in Premiere
right-click the offline clips, Link Media. The cut is named `02-cut\<name> - final cut.mp4` unless `--cut` gave its
real path. Check the result with `python scripts\timeline_check.py 05-board-sync\out`.
