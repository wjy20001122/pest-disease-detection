$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path "esp")) {
    py -3.11 -m venv esp
}

.\esp\Scripts\python.exe -m pip install --upgrade pip
.\esp\Scripts\pip.exe install -r requirements.txt

if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}
if (Test-Path "dist\ESP-Edge") {
    Remove-Item -Recurse -Force "dist\ESP-Edge"
}

.\esp\Scripts\pyinstaller.exe .\ESP-Edge.spec --noconfirm

Write-Host ""
Write-Host "[OK] Build completed: dist\ESP-Edge\ESP-Edge.exe"
Write-Host "Run it from PowerShell or double click the exe."
