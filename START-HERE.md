# Start here

> Want more open-source AI workflows? [Join the TEIN AI waitlist](https://tein.ai) · [Join our free community](https://www.skool.com/publicai)

## 1. Install

You need:

- **Claude Code**: https://claude.com/claude-code
- **Python 3.10+**: https://python.org
- **FFmpeg**: macOS `brew install ffmpeg` · Windows `winget install ffmpeg`
- **Chrome**, to open and record the boards

Then install the Python packages and the browser the renderer uses:

```bash
bash skills/board-sync/setup.sh
```

On Windows: `powershell -ExecutionPolicy Bypass -File skills\board-sync\setup.ps1`

## 2. Install the skills

Copy the three skill folders into your Claude skills folder:

```bash
cp -R skills/* ~/.claude/skills/
```

Or keep them per project: copy them into `.claude/skills/` inside your video's folder.

## 3. Run the setup check

```bash
bash tools/setup-check.sh
```

Everything should show ✓. Anything with ✕ prints the command that fixes it.

## 4. Look at the boards

Open `boards/index.html` in Chrome. Every board plays live. The catalog in `skills/explainer-board-system/references/board-catalog.md` says what each one is for and the words that should trigger it.

## 5. Make a video

Put your video (or just its audio) and your boards in one folder, open Claude Code there, and follow `prompts/` from step 7:

1. `07-transcribe.md`: Whisper, a timestamp for every word.
2. `07b-board-brief.md`: which lines need a board and what goes on it.
3. `08-sync.md`: every element lands on the word that names it.
4. `09-export.md`: Chrome renders every frame, FFmpeg joins them with your voice. Render the first 60 seconds first.

Every time you fix a board, say "add it to checks.md". That file is how it learns your taste.

## 6. Export without the skill

To render boards straight to an MP4 (Chrome renders every frame, FFmpeg adds your voice):

```bash
python tools/export.py boards/D44Line.html --seconds 8 -o out/line.mp4
```

How the boards, the sync and the export work: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
