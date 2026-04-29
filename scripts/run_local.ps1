$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$pythonPath = Join-Path $repoRoot "venv\Scripts\python.exe"
$envPath = Join-Path $repoRoot ".env"
$wsgiPath = Join-Path $repoRoot "wsgi.py"

Set-Location $repoRoot

Write-Host "Google Form Automation Tool"
Write-Host "Working directory: $repoRoot"

if (-not (Test-Path $pythonPath)) {
    Write-Host ""
    Write-Host "Could not find .\venv\Scripts\python.exe."
    Write-Host "Set up the local environment first:"
    Write-Host "  py -3 -m venv venv"
    Write-Host "  .\venv\Scripts\python.exe -m pip install -r requirements.txt"
    Write-Host "  Copy-Item .env.example .env"
    Write-Host "  Edit .env with SECRET_KEY, DB_PATH, CHROME_BINARY_PATH, and CHROME_DRIVER_PATH."
    exit 1
}

if (-not (Test-Path $envPath)) {
    Write-Host ""
    Write-Host "Warning: .env was not found."
    Write-Host "Copy .env.example to .env and configure it before using Selenium features."
}

Write-Host ""
Write-Host "Starting local server..."
Write-Host "Open: http://localhost:5000"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

& $pythonPath $wsgiPath
