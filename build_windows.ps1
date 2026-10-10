# Build a self-contained Windows installer with Python 3.12 and Inno Setup 6.
# Run from anywhere: powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
param([switch]$SkipInstaller)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function ExecOrFail([string]$label, [scriptblock]$command) {
    & $command
    if ($LASTEXITCODE -ne 0) { throw "$label failed with exit code $LASTEXITCODE" }
}

ExecOrFail 'Install build dependencies' { py -m pip install -r requirements-openrgb.txt 'pyinstaller>=6.11,<7' }
ExecOrFail 'Generate application icon' { py tools/create_icon.py }
ExecOrFail 'Unit tests' { py -m unittest discover -s tests -v }
ExecOrFail 'PyInstaller' { py -m PyInstaller --noconfirm --clean --onedir --windowed --name SeirenEmoteController --icon build_assets/app.ico --add-data 'emote_manifest.json;.' seiren_emote_gui.py }

$application = Join-Path $PSScriptRoot 'dist\SeirenEmoteController\SeirenEmoteController.exe'
if (!(Test-Path $application)) { throw "Packaged application missing: $application" }
Write-Host "Packaged application: $application"

if ($SkipInstaller) { exit 0 }
$inno = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $inno) { throw 'Inno Setup 6 was not found. Install from https://jrsoftware.org/isinfo.php or run -SkipInstaller.' }
New-Item -Path release -ItemType Directory -Force | Out-Null
ExecOrFail 'Inno Setup' { & $inno 'installer\SeirenEmoteController.iss' }
$setup = Get-Item 'release\SeirenEmoteController_Setup_*.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $setup) { throw 'Installer .exe was not generated' }
Write-Host "Installer ready: $($setup.FullName)"
