@echo off
chcp 65001 >nul
title LINE Vault - Windows 11 本地對話與防過期媒體中心

:: Check python availability
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

echo [錯誤] 找不到 Python！請確認已安裝 Python 3.10+ 並加入 PATH。
pause
exit /b 1
