# AGENTS.md

給 Codex、Claude Code、Cursor、Antigravity 與其他自動化代理人在本專案工作時的指引。產品與圖形介面使用方式先讀 [`README.md`](README.md)（英文版見 [`README.en.md`](README.en.md)）；開發與驗收細節見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)；產品藍圖見 [`docs/ROADMAP.md`](docs/ROADMAP.md)（英文版見 [`docs/ROADMAP.en.md`](docs/ROADMAP.en.md)）。

## 專案定位

本專案為 **Windows 11 / 10 原生純圖形化（Pure GUI）LINE 本地對話與防過期媒體管理中心**。
核心價值為 E2EE 端對端加密媒體解析、本機快取防過期永久留存、與 `line-desktop-mcp` 加密資料庫讀取引擎整合、本地 FTS5 全文搜尋以及 AI 行動摘要與建議回覆。

- `origin` 是 `SanHsien/line-vault`（預設分支 `main`）。
- 開發與完整驗收環境為 **Windows 11 + PowerShell**。
- **純 GUI 產品架構原則**：使用者明確要求「改純 GUI 介面，不使用 CLI」。因此本專案不提供指令列子命令，雙擊 `start_line_vault.bat` 或執行 `pythonw -m line_vault` 直接啟動獨立視窗桌面應用程式，所有功能均需能在圖形介面內完整操作。
- **提交與發布策略**：維護與新功能直接提交至 `main` 主分支，不建立分支；發布採用單一最新 Release / Tag（`v1.0.0`），自動清理或覆蓋舊標籤，保持倉庫極簡潔淨。

## 硬性邊界

- **不提交任何真實資料**：嚴禁提交真實聊天資料、快取圖片/影片、`.edb`、`.edb-wal`、金庫資料庫（`vault_data/`）、金鑰（`.key`）或 `.env`。
- **無假資料與無空殼**：禁止使用假資料或 `// TODO` 空殼函式當作實作完成。
- **嚴禁靜默吞例外**：禁止使用 `except Exception: pass`。所有例外處理必須捕獲明確型別並記錄或回傳結構化狀態。
- **目標平台實跑驗證**：回報完成前必須在 Windows 11 原生環境執行通過 `tools\dev_check.ps1` 與 `tools\test_product.ps1`。
- **PR 與 Push 目標**：PR、push 與 release 一律打向 `SanHsien/line-vault`。

## 技術架構與資料流

- **本機引擎與 REST API**：`line_vault/server.py`，基於標準庫 `http.server.ThreadingHTTPServer`，零外部 Web 框架依賴。
- **E2EE 加密與格式探測**：`line_vault/crypto.py`，符合 LINE Encryption Overview v2.2 規範（HKDF-SHA256、AES-256-CTR、HMAC-SHA256、Magic Bytes 嗅探）。
- **資料庫與全文檢索**：`line_vault/db.py`，SQLite3 WAL 模式與 FTS5 虛擬資料表。
- **防過期金庫與 MCP 橋接**：`line_vault/archiver.py`，依據雜湊去重保存原檔，並可介接 `line-desktop-mcp` 的 `line-reader.py`。
- **AI 智慧分析引擎**：`line_vault/analyzer.py`，規則式與語意提取截止日、款項、待辦與 3 款回覆草稿。
- **前端純 GUI 介面**：`line_vault/static/`（`index.html`、`styles.css`、`app.js`），現代深色模式、響應式 3 欄版型與設定視窗。
- **桌面應用啟動器**：`line_vault/cli.py`，自動探測 Microsoft Edge 或 Chrome 並以 `--app` 獨立無邊框應用程式視窗啟動。
- **驗證與契約工具**：`tools/` 與 `tools/tests/`，包含門禁腳本、依賴新鮮度與文件連結檢查。

## 開發原則

1. 變更前先調研計畫，修改後必須執行 `tools\dev_check.ps1` 與 `tools\test_product.ps1`。
2. 保持文件與相對連結完整性，每次更新文件需通過 `tools/check_links.py`。
3. 遵循繁體中文回覆規範，技術術語維持英文原文。
4. 任何重大決策記錄於 [`docs/DECISIONS.md`](docs/DECISIONS.md)。安全通報見 [`SECURITY.md`](SECURITY.md)，貢獻流程見 [`CONTRIBUTING.md`](CONTRIBUTING.md)，歷史審查見 [`REVIEW.md`](REVIEW.md)。

## 媒體歸檔與快取處理原則（2026-11-02 規範）

- **嚴禁要求使用者手動逐一開啟聊天室媒體作為補齊手段**：對於擁有數十個聊天室、成千上萬檔案的使用者，手動點開每張照片/影片在現實中完全不可行。任何推導為「請至聊天室逐一尋找並點開放大」的指引均屬敷衍與不合格回答。
- **正確認知本機快取與批次機制**：
  1. **批次下載**：若需快速補齊聊天室完整原檔，應說明 LINE 桌面版內建之「聊天室選單 -> 照片．影片清單 -> 一鍵全選下載」批次功能，於幾秒內將整群媒體載入本機，再由 LINE Vault 自動接手永久歸檔。
  2. **自動打撈**：系統底層透過 `%LOCALAPPDATA%\LINE\Cache` 自動關聯比對聊天室 SHA1 目錄進行打撈，零人工點擊。
  3. **防禦性介面**：原檔尚未落地的媒體，前端一律以優雅「待快取卡片」呈現，嚴禁產生原生破圖，嚴禁觸發看圖軟體報錯。
