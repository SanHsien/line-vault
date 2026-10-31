# 架構決策紀錄 (Architecture Decision Records)

本文檔記錄 `line-vault` 核心技術架構與關鍵演進決策。

---

## ADR-001: 零外部框架依賴與原生桌面應用視窗

- **狀態**：已採用 (Accepted)
- **背景**：一般桌面 Web 應用常依賴 FastAPI、Flask 或 Electron，造成體積龐大、冷啟動緩慢與環境依賴繁雜。
- **決策**：
  - 後端採用 Python 標準庫 `http.server.ThreadingHTTPServer`，提供多執行緒並行 REST API 服務。
  - 前端採用純 Vanilla JavaScript 與原生 CSS Dark Mode，零建置步驟（Zero Build Step）。
  - 桌面視窗透過微軟 Edge 或 Google Chrome 內建之 `--app=http://127.0.0.1:<port>` 獨立視窗模式啟動，兼具原生桌面無邊框體驗與極速載入特性。
- **後果**：系統無需安裝 Node.js 或複雜 Web 框架，雙擊即可瞬間啟動，執行緒安全由資料庫鎖保護。

---

## ADR-002: 符合 LINE Encryption Overview v2.2 規格之 E2EE 媒體還原

- **狀態**：已採用 (Accepted)
- **背景**：LINE 電腦版接收的照片、影片與檔案具有端對端加密（E2EE）保護，直接提取快取檔案無法閱讀。
- **決策**：
  - 嚴格依照 LINE 官方加密規格實作：
    1. 使用 HKDF-SHA256（`salt=None`，`info=b"FileEncryption"`）從 32 位元組 Key Material 衍生 76 位元組密鑰。
    2. 分割為 `enc_key`（32B）、`mac_key`（32B）與 `iv`（12B + 4B 零填充）。
    3. 驗證密文後方 32 位元組 HMAC-SHA256 標籤之完整性。
    4. 使用 AES-256-CTR 解密還原二進位資料。
    5. 透過 Magic Bytes 自動探測還原原始副檔名（`.png`, `.jpg`, `.mp4`, `.pdf`, `.zip` 等）。
- **後果**：能夠在本地將已快取之加密檔案百分之百還原為未過期原檔，永久存檔。

---

## ADR-003: SQLite3 WAL 模式、FTS5 全文檢索與 CJK LIKE 容錯

- **狀態**：已採用 (Accepted)
- **背景**：歷史訊息量龐大，標準關聯式查詢在模糊搜尋時效能不彰。
- **決策**：
  - 資料庫開啟 `PRAGMA journal_mode = WAL;`，允許讀寫並行且防範崩潰損毀。
  - 建立 `messages_fts` 虛擬資料表，支援即時全文檢索。
  - 若特定環境之 SQLite 未啟用 FTS5，系統自動無縫降級至複合 `LIKE` 模式，確保功能不中斷。
- **後果**：毫秒級搜尋數十萬則歷史對話，並具備優異容錯彈性。

---

## ADR-004: 與 `line-desktop-mcp` (`line-reader.py`) 的安全子行程橋接

- **狀態**：已採用 (Accepted)
- **背景**：Windows LINE 桌面版將對話與金鑰保存在加密的 `.edb` / WAL 資料庫中。`line-desktop-mcp` 已具備受限唯讀記憶體探針與解碼能力。
- **決策**：
  - 在 `MediaArchiver` 實作 `sync_from_mcp_reader` 方法，透過標準 `subprocess.run`（無 `shell=True`）呼叫 `line-reader.py`。
  - 取得最近對話清單、訊息紀錄與媒體 `keyMaterial`、`declaredBytes`。
  - 在檔案過期前，自動自快取資料庫尋找匹配檔案，解密並歸檔至金庫。
- **後果**：免除重複開發底層記憶體探針的維護成本，直接複用成熟安全的本機唯讀架構。

---

## ADR-005: 100% 純 GUI 桌面導向（捨棄 CLI 介面）

- **狀態**：已採用 (Accepted)
- **背景**：使用者明確反饋「不想用 CLI 介面，改純 GUI 介面」。
- **決策**：
  - 移除終端機命令列子命令（如 `line-vault stats`、`line-vault search`、`line-vault scan` 等）。
  - 將所有設定、掃描、MCP 同步、範例載入與 AI 分析操作整合至前端 GUI（頂部設定彈窗與對話面板）。
  - 雙擊 `start_line_vault.bat` 使用 `pythonw` 啟動，完全隱藏命令提示字元黑視窗。
- **後果**：大幅降低使用者操作門檻，符合一般桌面使用者的直覺習慣。

---

## 相關文件

- [全域協作與代理規則 (AGENTS.md)](../AGENTS.md)
- [本機開發與驗證指南 (docs/DEVELOPMENT.md)](DEVELOPMENT.md)
- [安全政策 (SECURITY.md)](../SECURITY.md)
- [架構審查報告 (REVIEW.md)](../REVIEW.md)
