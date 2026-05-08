$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path "esp")) {
    py -3.11 -m venv esp
}

.\esp\Scripts\python.exe -m pip install --upgrade pip
.\esp\Scripts\pip.exe install -r requirements.txt
.\esp\Scripts\python.exe -m esp_edge_app
