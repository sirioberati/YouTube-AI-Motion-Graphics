#!/usr/bin/env bash
# board-sync setup for Mac (and Linux). One command, safe to run again:
#   bash setup.sh
# 1. uv (brew, else the official installer)    2. .venv with Python 3.12 and requirements.txt
# 3. ffmpeg (brew, else the static-ffmpeg pip fallback)    4. a browser: Chrome/Edge, else Playwright's chromium
# 5. a self-check, then the exact run command.
# Without uv (or with BOARD_SYNC_NO_UV=1) it falls back to python3 -m venv + pip.
set -euo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SKILL"
say() { printf '\n== %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
uv_ok() { have uv && uv --version >/dev/null 2>&1; }   # a pyenv shim without uv behind it does not count

# 1. uv ------------------------------------------------------------------------------------------------------------
if [ "${BOARD_SYNC_NO_UV:-0}" != "1" ] && ! uv_ok; then
  say "Installing uv (Python package manager)"
  if have brew; then brew install uv || true
  else curl -LsSf https://astral.sh/uv/install.sh | sh || true; fi
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
USE_UV=0
if [ "${BOARD_SYNC_NO_UV:-0}" != "1" ] && uv_ok; then USE_UV=1; fi

# 2. venv + packages ------------------------------------------------------------------------------------------------
PY="$SKILL/.venv/bin/python"
if [ "$USE_UV" = "1" ]; then
  if [ ! -x "$PY" ]; then say "Creating .venv (Python 3.12) with uv"; uv venv .venv --python 3.12; fi
  say "Installing Python packages (first time: a few minutes)"
  uv pip install --python "$PY" -r requirements.txt
else
  if [ ! -x "$PY" ]; then
    BASE=""
    for c in python3.12 python3.13 python3.11 python3.10 python3; do
      if have "$c" && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then BASE="$c"; break; fi
    done
    if [ -z "$BASE" ]; then
      echo "No Python 3.10+ found and uv is not available. Install uv (https://docs.astral.sh/uv/) or Python 3.12, then run this again."
      exit 1
    fi
    say "Creating .venv with $BASE (uv not available)"
    "$BASE" -m venv .venv
  fi
  say "Installing Python packages with pip (first time: a few minutes)"
  "$PY" -m pip install --upgrade pip >/dev/null
  "$PY" -m pip install -r requirements.txt
fi

# 3. ffmpeg ---------------------------------------------------------------------------------------------------------
if have ffmpeg && have ffprobe; then
  echo "ffmpeg: $(command -v ffmpeg)"
else
  say "Installing ffmpeg"
  if have brew; then brew install ffmpeg || true; fi
  if ! (have ffmpeg && have ffprobe); then
    echo "Using the static-ffmpeg fallback (downloads ffmpeg into the venv on first use)"
    "$PY" -c "import static_ffmpeg; static_ffmpeg.add_paths(); import shutil; print('ffmpeg:', shutil.which('ffmpeg'))"
  fi
fi

# 4. browser --------------------------------------------------------------------------------------------------------
BROWSER=""
for app in "/Applications/Microsoft Edge.app" "/Applications/Google Chrome.app" \
           "$HOME/Applications/Microsoft Edge.app" "$HOME/Applications/Google Chrome.app"; do
  if [ -d "$app" ]; then BROWSER="$app"; break; fi
done
if [ -z "$BROWSER" ]; then
  for exe in microsoft-edge google-chrome google-chrome-stable chromium chromium-browser; do
    if have "$exe"; then BROWSER="$(command -v "$exe")"; break; fi
  done
fi
if [ -n "$BROWSER" ]; then
  echo "browser: $BROWSER"
else
  say "No Edge or Chrome found: installing Playwright's chromium (about 150 MB)"
  "$PY" -m playwright install chromium
fi

# 5. check + run command --------------------------------------------------------------------------------------------
say "Self-check"
"$PY" "$SKILL/board_sync.py" --check || true

cat <<EOF

Setup done. To run board-sync, open a terminal in the video's folder (the one with 02-cut, 03-board-brief, 04-boards)
and paste this, with <name> replaced by the video's name:

"$PY" "$SKILL/board_sync.py" --boards "04-boards" --wav "02-cut/<name> - final cut.wav" --words "02-cut/<name> - final cut words.tsv" --script "03-board-brief/script-marked.md" --brief "03-board-brief/brief.md" --out "05-board-sync/out"

EOF
