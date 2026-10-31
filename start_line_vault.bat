@echo off
chcp 65001 >nul
title LINE Vault - Windows 11 本地對話與防過期媒體中心

:: 1. Prefer standalone compiled Windows executable if present
if exist "%~dp0LINE-Vault-win64.exe" (
    start "" "%~dp0LINE-Vault-win64.exe"
    exit /b 0
)
if exist "%~dp0dist\LINE-Vault-win64.exe" (
    start "" "%~dp0dist\LINE-Vault-win64.exe"
    exit /b 0
)

:: 2. Fallback to Python GUI launcher (no console window)
where pythonw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" pythonw -m line_vault
    exit /b 0
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" python -m line_vault
    exit /b 0
)

echo [錯誤 / Error] 找不到 LINE-Vault-win64.exe 或 Python 3.10+！
pause
exit /b 1
