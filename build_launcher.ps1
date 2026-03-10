param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

& $PythonExe -m pip install -r requirements-gui.txt

& $PythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    FerrumBotLauncher.spec
