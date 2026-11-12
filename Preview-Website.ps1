$ErrorActionPreference = 'Stop'
$siteRoot = $PSScriptRoot
$pythonPath = (Get-Command python -ErrorAction Stop).Source
Push-Location -LiteralPath $siteRoot
try {
    & $pythonPath 'build.py'
    if ($LASTEXITCODE -ne 0) { throw 'Website build failed. The previous review output was retained.' }
    Write-Host 'Local review: http://127.0.0.1:8765'
    Write-Host 'Open that address after the server starts. Keep this window open; Ctrl+C stops the preview.'
    & $pythonPath 'tools/preview.py' '--port' '8765'
} finally {
    Pop-Location
}
