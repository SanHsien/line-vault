@echo off
chcp 65001 >nul
title LINE Vault - 本地對話與防過期媒體管理中心

echo ======================================================================
echo    LINE Vault (LINE 金庫) - Windows 11 本地對話與防過期媒體中心
echo ======================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [錯誤] 找不到 Python！請確認已安裝 Python 3.10+ 並加入 PATH。
    pause
    exit /b 1
)

echo [1/3] 檢查 Python 依賴套件...
python -c "import cryptography" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [提示] 正在安裝必要套件 (cryptography)...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [錯誤] 套件安裝失敗。
        pause
        exit /b 1
    )
)

echo [2/3] 準備啟動本機伺服器...
set VAULT_PORT=8765
set VAULT_URL=http://127.0.0.1:%VAULT_PORT%

echo [3/3] 開啟預設瀏覽器: %VAULT_URL%
start "" "%VAULT_URL%"

echo.
echo 伺服器正在運行於 %VAULT_URL%
echo 按下 Ctrl+C 可停止伺服器。
echo ======================================================================
echo.

python -m line_vault web --port %VAULT_PORT%
if %ERRORLEVEL% neq 0 (
    pause
)
