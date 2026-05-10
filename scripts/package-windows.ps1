$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$packageJsonPath = Join-Path $repoRoot 'package.json'
$buildScript = Join-Path $repoRoot 'build_exe.bat'
$backendArtifact = Join-Path $repoRoot 'dist\GoogleFormTool\GoogleFormTool.exe'

if (-not (Test-Path $packageJsonPath)) {
    throw "package.json not found at $packageJsonPath"
}

$packageJson = Get-Content -Path $packageJsonPath -Raw | ConvertFrom-Json
$version = $packageJson.version
if (-not $version) {
    throw 'package.json version is required for installer artifact naming.'
}

if (-not (Test-Path $buildScript)) {
    throw "Backend build script not found at $buildScript"
}

Write-Host "Packaging Google Form Automation Tool version $version"
Write-Host 'Building backend sidecar in release mode...'
& $buildScript release
if ($LASTEXITCODE -ne 0) {
    throw "Backend build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $backendArtifact)) {
    throw "Backend artifact missing after build: $backendArtifact"
}

Write-Host "Backend artifact ready: $backendArtifact"

if (-not (Test-Path (Join-Path $repoRoot 'node_modules'))) {
    Write-Host 'Installing npm dependencies...'
    npm install
    if ($LASTEXITCODE -ne 0) {
        throw "npm install failed with exit code $LASTEXITCODE"
    }
}

Write-Host 'Building Windows NSIS and MSI installers...'
npm run package:win
if ($LASTEXITCODE -ne 0) {
    throw "electron-builder failed with exit code $LASTEXITCODE"
}

Write-Host "Windows installers built for version $version in $(Join-Path $repoRoot 'release')"
