param()

$scriptPath = Join-Path $PSScriptRoot "gui_launcher.py"
$python = "C:\Users\Akane\AppData\Local\Programs\Python\Python313\python.exe"

Start-Process -FilePath $python -ArgumentList $scriptPath -WorkingDirectory $PSScriptRoot -Verb RunAs
