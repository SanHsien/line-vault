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

## ADR-006: CodeQL `py/path-injection` 路徑正規化白名單與 PyInstaller 單一執行檔封裝

- **狀態**：已採用 (Accepted)
- **背景**：GitHub CodeQL 針對 `POST /api/scan-line` 與 `POST /api/sync-mcp` 提出 `py/path-injection` 警告；同時 Windows 使用者需要免安裝 Python 環境即可執行的 `.exe` 單一執行檔。
- **決策**：
  - 所有由 HTTP JSON Body 傳入之自訂路徑皆須經過 `os.path.normpath(os.path.realpath(...))` 正規化，並以 `if not fullpath.startswith(base_root):` 強制驗證位於授權根目錄內，預設路徑則直接由伺服器端環境變數組裝，徹底消除外部不可信路徑注入。
  - `create_server()` 支援 `getattr(sys, "_MEIPASS", None)` 資源定位，並透過 `tools/build_release.ps1` 呼叫 PyInstaller 產出無黑窗獨立執行檔 `LINE-Vault-win64.exe` 與 `LINE-Vault-v1.0.0-win64.zip`。
  - 版本採語意化版本（SemVer `v1.0.0`），直接推送 `main` 並開啟 GitHub 分支保護（禁止刪除分支、要求 `analyze` 與 `test (3.12)` 狀態檢查），Release 與 Tag 僅保留最新一版。

---

## ADR-007: 瀏覽器設定檔隔離（阻絕第三方擴充套件廣告注入）與前端 JS 語法機械驗證防線

- **狀態**：已採用 (Accepted)
- **背景（實機教訓）**：
  1. 初版 `cli.py` 呼叫 `msedge.exe --app=http://127.0.0.1:8765` 時未指定獨立 `--user-data-dir` 與 `--disable-extensions`，導致 Chromium 直接沿用使用者預設瀏覽器設定檔並載入第三方閱讀外掛（「AI 速讀」），在視窗左下角注入外掛推廣白框。
  2. 初版 `app.js` 在 `renderInsight()` 結尾多出一個 `}`，導致 `DOMContentLoaded` 區塊提前閉合並觸發瀏覽器 `SyntaxError`，造成左側清單卡在「載入中...」且所有 UI 按鈕點擊無效；而當時 `pytest` 僅以字串比對檢查 `/app.js`，未驗證 JS 括號結構與執行期 DOM 渲染。
  3. 頂部 `.app-header` 未設定 `flex-wrap: wrap`，在非最大化視窗（1280px）下最右側按鈕遭裁切。
- **決策**：
  1. `cli.py` 啟動桌面視窗時強制指定隔離設定檔 `--user-data-dir=<vault_dir>/.gui_profile` 並加上 `--disable-extensions`、`--disable-component-extensions-with-background-pages`、`--disable-features=Translate,EdgeSidebar,msEdgeSidebarV2`，搭配 CSS 與 `MutationObserver` 雙重屏蔽非原生容器節點，徹底杜絕任何第三方擴充套件注入。
  2. `.app-header` 改為 `flex-wrap: wrap` 自適應排版與橫向膠囊 KPI 卡片，並內建「❓ 使用說明」視窗與中央「🚀 3 步快速開始與測試指南」互動面板。
  3. 在 `tests/test_line_vault.py` 新增 `test_frontend_js_syntax_and_dom_ids_integrity` 機械防線，逐行檢查 `app.js` 括號／字串／模板語法平衡、防止根區塊提前閉合，並強制驗證所有 `document.getElementById` 與 `index.html` 100% 對齊。
  4. **重要教訓（2026-10-31）**：
     - `tools/build_release.ps1` 在重新編譯 `dist/LINE-Vault-win64.exe` 時若執行 `Stop-Process` 釋放檔案鎖定，卻未在編譯完成後自動重啟背景服務（`--no-window`），會導致使用者已開啟在桌面上的 `http://127.0.0.1:8765` 視窗失去後端連線，點擊任何按鈕（載入範例、重新分析全部、匯入文字、同步資料庫、掃描快取）皆因 `ERR_CONNECTION_REFUSED` 顯示失敗。已在 `build_release.ps1` 結尾強制自動重啟背景服務。
     - PyInstaller 封裝後的 `sys.executable` 指向 `LINE-Vault-win64.exe` 本身而非 `python.exe`，因此本機 LINE 讀取引擎必須直接以原生 Python 模組（`line_vault/line_reader.py` 的 `BuiltinLineReader`）在行程內（In-process）執行，絕不可在預設路徑下透過 `subprocess.run([sys.executable, ...])` 呼叫外部 `.py` 腳本。

---

## 相關文件

- [全域協作與代理規則 (AGENTS.md)](../AGENTS.md)
- [產品發展藍圖 (docs/ROADMAP.md)](ROADMAP.md)
- [英文發展藍圖 (docs/ROADMAP.en.md)](ROADMAP.en.md)
- [本機開發與驗證指南 (docs/DEVELOPMENT.md)](DEVELOPMENT.md)
- [安全政策 (SECURITY.md)](../SECURITY.md)
- [架構審查報告 (REVIEW.md)](../REVIEW.md)
