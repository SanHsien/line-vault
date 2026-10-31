[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = (Get-Command python -ErrorAction Stop).Source
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "==> Run line-vault product test suite (Windows 11)"
& $pythonExe -m pytest -v -p no:cacheprovider tests
if ($LASTEXITCODE -ne 0) {
    throw "Product tests failed with exit code $LASTEXITCODE"
}

Write-Host "PRODUCT TESTS GREEN" -ForegroundColor Green
