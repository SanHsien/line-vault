[CmdletBinding()]
param(
    [string]$Version = "1.0.0"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if ((Test-Path -LiteralPath $venvPython) -and (& $venvPython -m PyInstaller --version 2>$null)) {
    $pythonExe = $venvPython
} elseif (Test-Path -LiteralPath "C:\Python314\python.exe") {
    $pythonExe = "C:\Python314\python.exe"
} else {
    $pythonExe = (Get-Command python -ErrorAction Stop).Source
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "==> Building Windows 11 Standalone GUI Executable (LINE-Vault-win64.exe)"
Get-Process -Name "LINE-Vault-win64" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300
& $pythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --noconsole `
    --name "LINE-Vault-win64" `
    --add-data "line_vault\static;line_vault/static" `
    "line_vault\__main__.py"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

$exePath = Join-Path $repoRoot "dist\LINE-Vault-win64.exe"
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Compiled executable not found at $exePath"
}

$zipPath = Join-Path $repoRoot "dist\LINE-Vault-v$Version-win64.zip"
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Write-Host "==> Packaging Release Bundle ($zipPath)"
Compress-Archive -Path @(
    $exePath,
    (Join-Path $repoRoot "start_line_vault.bat"),
    (Join-Path $repoRoot "docs\sample_line_chat_export.txt"),
    (Join-Path $repoRoot "README.md"),
    (Join-Path $repoRoot "README.en.md"),
    (Join-Path $repoRoot "LICENSE")
) -DestinationPath $zipPath -Force

if (Test-Path -LiteralPath (Join-Path $repoRoot "LINE-Vault-win64.spec")) {
    Remove-Item -LiteralPath (Join-Path $repoRoot "LINE-Vault-win64.spec") -Force
}

# Always start/restart the background engine on port 8765 outside any transient job object so open GUI windows stay connected
$distWorkingDir = Split-Path -Parent $exePath
try {
    $null = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine      = "`"$exePath`" --no-window"
        CurrentDirectory = $distWorkingDir
    } -ErrorAction Stop
} catch {
    Start-Process -FilePath $exePath -WorkingDirectory $distWorkingDir -ArgumentList "--no-window"
}
Start-Sleep -Milliseconds 1200

Write-Host "BUILD RELEASE GREEN: $exePath & $zipPath"
