# board-sync setup for Windows. One command, safe to run again. In PowerShell, in this folder:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
# 1. uv (winget, else the official installer)    2. .venv with Python 3.12 and requirements.txt
# 3. ffmpeg (winget Gyan.FFmpeg, else the static-ffmpeg pip fallback)    4. a browser: Edge/Chrome, else Playwright's chromium
# 5. a self-check, then the exact run command.
# No admin rights needed beyond winget's usual prompt.
$ErrorActionPreference = 'Stop'
$Skill = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Skill

function Say($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user;$env:USERPROFILE\.local\bin;$env:LOCALAPPDATA\Microsoft\WinGet\Links"
}
function Uv-Ok { if (-not (Have 'uv')) { return $false }; try { & uv --version *> $null; return ($LASTEXITCODE -eq 0) } catch { return $false } }

# 1. uv -------------------------------------------------------------------------------------------------------------
if (-not (Uv-Ok)) {
    Say 'Installing uv (Python package manager)'
    if (Have 'winget') {
        & winget install --id astral-sh.uv -e --source winget --accept-source-agreements --accept-package-agreements
        Refresh-Path
    }
    if (-not (Uv-Ok)) {
        & powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
        Refresh-Path
    }
}
$UseUv = Uv-Ok

# 2. venv + packages ------------------------------------------------------------------------------------------------
$Py = Join-Path $Skill '.venv\Scripts\python.exe'
if ($UseUv) {
    if (-not (Test-Path -LiteralPath $Py)) { Say 'Creating .venv (Python 3.12) with uv'; & uv venv .venv --python 3.12 }
    Say 'Installing Python packages (first time: a few minutes)'
    & uv pip install --python $Py -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'uv pip install failed (see above).' }
} else {
    if (-not (Test-Path -LiteralPath $Py)) {
        Say 'uv is not available: creating .venv with the Python launcher'
        if (Have 'py') { & py -3.12 -m venv .venv; if ($LASTEXITCODE -ne 0) { & py -3 -m venv .venv } }
        elseif (Have 'python') { & python -m venv .venv }
        else { throw 'No uv and no Python found. Install uv (winget install astral-sh.uv) and run this again.' }
    }
    Say 'Installing Python packages with pip (first time: a few minutes)'
    & $Py -m pip install --upgrade pip | Out-Null
    & $Py -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'pip install failed (see above).' }
}

# 3. ffmpeg ---------------------------------------------------------------------------------------------------------
if ((Have 'ffmpeg') -and (Have 'ffprobe')) {
    Write-Host "ffmpeg: $((Get-Command ffmpeg).Source)"
} else {
    Say 'Installing ffmpeg'
    if (Have 'winget') {
        & winget install --id Gyan.FFmpeg -e --source winget --accept-source-agreements --accept-package-agreements
        Refresh-Path
    }
    if (-not ((Have 'ffmpeg') -and (Have 'ffprobe'))) {
        Write-Host 'Using the static-ffmpeg fallback (downloads ffmpeg into the venv on first use)'
        & $Py -c "import static_ffmpeg; static_ffmpeg.add_paths(); import shutil; print('ffmpeg:', shutil.which('ffmpeg'))"
    }
}

# 4. browser --------------------------------------------------------------------------------------------------------
$candidates = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$Browser = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if ($Browser) {
    Write-Host "browser: $Browser"
} else {
    Say 'No Edge or Chrome found: installing Playwright chromium (about 150 MB)'
    & $Py -m playwright install chromium
}

# 5. check + run command --------------------------------------------------------------------------------------------
Say 'Self-check'
& $Py (Join-Path $Skill 'board_sync.py') --check

$Run = "& `"$Py`" `"$(Join-Path $Skill 'board_sync.py')`" --boards `"04-boards`" --wav `"02-cut\<name> - final cut.wav`" --words `"02-cut\<name> - final cut words.tsv`" --script `"03-board-brief\script-marked.md`" --brief `"03-board-brief\brief.md`" --out `"05-board-sync\out`""
Write-Host ''
Write-Host 'Setup done. To run board-sync, open PowerShell in the video''s folder (the one with 02-cut, 03-board-brief,'
Write-Host '04-boards) and paste this, with <name> replaced by the video''s name:'
Write-Host ''
Write-Host $Run -ForegroundColor Green
Write-Host ''
