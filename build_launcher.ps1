param(
    [string]$PythonExe = "python",
    [string]$VersionTag = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

& $PythonExe -m pip install -r requirements-gui.txt

& $PythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    FerrumBotLauncher.spec

if ([string]::IsNullOrWhiteSpace($VersionTag)) {
    & $PythonExe tools/release_packaging.py `
        --project-root $root `
        --dist-dir dist/LAA `
        --output-root release
} else {
    & $PythonExe tools/release_packaging.py `
        --project-root $root `
        --dist-dir dist/LAA `
        --output-root release `
        --version-tag $VersionTag
}
