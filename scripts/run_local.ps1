$ErrorActionPreference = "Stop"

# Xác định đường dẫn gốc của repo (giữ nguyên để định vị các file cấu hình)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$envPath = Join-Path $repoRoot ".env"
$wsgiPath = Join-Path $repoRoot "wsgi.py"

Set-Location $repoRoot

Write-Host "Google Form Automation Tool"
Write-Host "Working directory: $repoRoot"

# Kiểm tra .env (vẫn giữ vì đây là cấu hình người dùng)
if (-not (Test-Path $envPath)) {
    Write-Host "`nWarning: .env was not found."
    Write-Host "Copy .env.example to .env and configure it before using Selenium features."
}

Write-Host "`nStarting local server..."
Write-Host "Open: http://localhost:5000"
Write-Host "Press Ctrl+C to stop.`n"

# Sử dụng uv run - nó sẽ tự tìm env và cài các lib nếu thiếu
uv run python $wsgiPath