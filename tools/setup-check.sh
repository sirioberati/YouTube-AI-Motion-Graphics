#!/usr/bin/env bash
# Checks that everything the workflow needs is installed. Run: bash tools/setup-check.sh
ok=0; miss=0
check() { if command -v "$1" >/dev/null 2>&1; then echo "  ✓ $1"; ok=$((ok+1)); else echo "  ✕ $1  ->  $2"; miss=$((miss+1)); fi; }
echo "Tools"
check python3 "install Python 3.10+ from python.org"
check ffmpeg  "macOS: brew install ffmpeg · Windows: winget install ffmpeg"
check ffprobe "comes with ffmpeg"
check node    "optional, only for editing kit.js: nodejs.org"
check claude  "install Claude Code: https://claude.com/claude-code"
echo "Python packages"
for p in faster_whisper playwright numpy PIL; do
  if python3 -c "import $p" 2>/dev/null; then echo "  ✓ $p"; ok=$((ok+1)); else echo "  ✕ $p  ->  pip install -r skills/board-sync/requirements.txt"; miss=$((miss+1)); fi
done
if python3 -c "from playwright.sync_api import sync_playwright as s; p=s().start(); b=p.chromium.launch(); b.close(); p.stop()" 2>/dev/null; then
  echo "  ✓ Chromium for Playwright"; ok=$((ok+1))
elif python3 -c "from playwright.sync_api import sync_playwright as s; p=s().start(); b=p.chromium.launch(channel='chrome'); b.close(); p.stop()" 2>/dev/null; then
  echo "  ✓ Chrome (use --chrome with tools/export.py)"; ok=$((ok+1))
else echo "  ✕ Chromium for Playwright  ->  python3 -m playwright install chromium"; miss=$((miss+1)); fi
echo "Repo"
[ -f boards/index.html ] && echo "  ✓ boards/ ($(ls boards/*.html | wc -l | tr -d ' ') files)" || { echo "  ✕ run this from the repo folder"; miss=$((miss+1)); }
[ -f tools/export.py ] && echo "  ✓ tools/export.py" || { echo "  ✕ tools/export.py missing"; miss=$((miss+1)); }
[ -f checks.md ] && echo "  ✓ checks.md" || { echo "  ✕ checks.md missing"; miss=$((miss+1)); }
echo
if [ $miss -eq 0 ]; then echo "All set. Open boards/index.html to see every board."; else echo "$miss missing. Install them, then run this again."; exit 1; fi
