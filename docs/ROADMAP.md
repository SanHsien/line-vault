# 路線圖

> 本 repo 後續工作的單一真相源。做完一項，就在同一個 commit 刪掉那一列；新工作只加在這裡。
> 現況段的數字是 2026-11-02 依 `main` `99ae95fb1e8b` 查的快照，開工前先重查 GitHub。英文鏡像見 [`ROADMAP.en.md`](ROADMAP.en.md)，兩份同一個 commit 改。

## 現況

Windows 11 / 10 原生純 GUI 的 LINE 本地對話與防過期媒體金庫（E2EE 媒體還原、本機快取歸檔、FTS5 全文檢索、規則式 AI 待辦與回覆建議），公開 repo，維護者自己創作，不是 fork；功能範圍見 `README.md` 核心特性，架構決策見 [`DECISIONS.md`](DECISIONS.md)。原路線圖的 Phase 1–6 已全部完成並從本檔移除（歷史在 `git log`）。2026-11-02 查：open issue 0、open PR 0、Dependabot 告警 0；code scanning open 1（#12 `py/full-ssrf`，`line_vault/server.py:642`，掃描對象 `99ae95f`）；`main` 上 CI 與 CodeQL 最近一次（`99ae95f`，2026-11-01）皆 success；最新 Release 是 v1.4.3（遠端只保留這一個 tag）；`main` 分支保護必要檢查是 `analyze` 與 `test (3.12)`；依賴新鮮度報告全數 fresh；`python -m pytest tests` 在 `99ae95f` 為 33 項通過，加上本次新增的 61 項更新下載安全測試共 94 項通過（本機 Python 3.14.10）。告警 #12 的修補（更新下載只收本專案 release 資產、redirect 只留在 GitHub 下載主機、大小上限）隨本次納管一起提交，決策見 `docs/DECISIONS.md` ADR-008。repo 內沒有任何一份對真實登入中 LINE 的實機驗收紀錄（見下表）。（`gh issue list`／`gh pr list`／`gh api repos/SanHsien/line-vault/dependabot/alerts?state=open`／`gh api repos/SanHsien/line-vault/code-scanning/alerts?state=open`／`gh run list -R SanHsien/line-vault -b main`／`gh release list -R SanHsien/line-vault`）

## 近期：可以直接動手
| 項目 | 為什麼 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 確認告警 #12 在修補推上 `main` 後被 CodeQL 關閉 | 修補是否真的清掉告警只有 CodeQL 能證明；本機沒有 CodeQL CLI，這一步沒驗過。若仍 open，代表 CodeQL 不認這個寫法，要改成使用者值完全不進 URL（只收 `asset_type`，URL 由常數與 GitHub API 回應組出）；不要由派工方自行 dismiss | 推上 `main` 且 CodeQL workflow success 後，`gh api repos/SanHsien/line-vault/code-scanning/alerts/12 --jq .state` 回 `fixed`，`gh api "repos/SanHsien/line-vault/code-scanning/alerts?state=open" --jq length` 回 `0`；仍 open 就把 `gh api .../alerts/12` 的資料流貼進本列，交維護者決定 | Claude Sonnet | `line_vault/server.py` 的 `resolve_update_download_url`／`UpdateRedirectHandler`／`fetch_update_asset`；`tests/test_update_download_security.py`；`gh api repos/SanHsien/line-vault/code-scanning/alerts/12` |
| 本機 REST API 加 Origin／Host 檢查，拿掉 `Access-Control-Allow-Origin: *` | 目前每個回應都送 `Access-Control-Allow-Origin: *`，`do_POST` 不看 Content-Type（`_read_json_body` 直接 `json.loads`），全程式沒有 Origin 或 Host 驗證；依程式碼判斷，使用者瀏覽任何網頁時，該網頁都能對 `127.0.0.1:8765` 讀取聊天資料並呼叫 `POST /api/shutdown`、`DELETE /api/chats/<id>`，DNS rebinding 同理（未實測利用）。同一個缺口也是告警 #12 那條下載端點能被網頁遠端觸發的原因 | 新測試：帶 `Origin: https://evil.example` 的請求得不到 `Access-Control-Allow-Origin`，寫入與刪除型端點回 403；`Host` 不是 `127.0.0.1:<port>` 或 `localhost:<port>` 回 403；GUI 自己的同源請求不受影響（`tests/test_line_vault.py` 全綠，`app.js` 不改 fetch 寫法）；`SECURITY.md` 的本機防護原則補一條 | Claude Sonnet | `line_vault/server.py:309-312`（`_send_cors_headers`）；`line_vault/server.py:558`（`do_POST`）；`line_vault/server.py:737`（`/api/shutdown`）；`line_vault/server.py:542`（`do_DELETE`）；`rg -n "Origin|\"Host\"" line_vault` 無驗證碼 |
| 版本號只留一個來源，文件不寫死「v1.0.0」 | `pyproject.toml` 是 `1.0.0`，`line_vault/__init__.py` 與實際 Release 是 `1.4.3`；README 徽章、`tools/build_release.ps1` 預設值、`app.js` 備用字串都還是 1.0.0；多份文件寫「單一最新 Release／Tag（`v1.0.0`）」，實際最新是 v1.4.3，讀的人會以為下載到舊版 | `pyproject.toml` 的版本取自 `line_vault.__version__`（`dynamic`）或由新契約測試比對兩者相等；`build_release.ps1` 預設值不再寫死或由同一來源取得；文件改寫成「單一最新 Release／Tag」不帶版號；`tests/test_line_vault.py` 的版本斷言改為與 `__version__` 比對；`tools\dev_check.ps1` 與 `tools\test_product.ps1` 綠；動手前確認 `C:\GitHub\line-vault` 沒有別的寫入者 | Claude Sonnet | `pyproject.toml:7`；`line_vault/__init__.py:16`；`tools/build_release.ps1:3`；`README.md:7,91`；`AGENTS.md:13`；`CONTRIBUTING.md:10`；`docs/DEVELOPMENT.md:90`；`tests/test_line_vault.py:1393`；`line_vault/static/app.js:1277` |
| 收斂 `server.py` 的 5 處 `except Exception` | `AGENTS.md` 要求例外處理「必須捕獲明確型別並記錄或回傳結構化狀態」；契約測試只攔 `except Exception: pass`，這 5 處雖有回傳錯誤，但把所有未預期錯誤（含程式缺陷）都吞成同一種回應，AGENTS 的規則沒有被機器擋住 | `rg -n "except Exception" line_vault` 無命中，或每一處改成明確型別並有測試釘住該端點對該型別的回應；契約測試補一條擋 `except Exception`（同檔其他合法位置先列清單）；`pytest tests` 綠 | Claude Sonnet | `line_vault/server.py:439,634,685,699,713`；`AGENTS.md:19`；`tools/tests/test_repo_contracts.py:30`（`FORBIDDEN_PATTERNS`） |
| 補一份 Windows 實機驗收紀錄 | 專案至今的測試都用合成快取與模擬資料；收尾報告明寫「尚未對本機真實登入中的 LINE.exe 跑全量實機匯入」，之後的版本修正了多個實機問題，但 repo 內沒有任何一份實機驗收紀錄可查 | 新增 `docs/` 下一份標日期的驗收紀錄：Windows build、LINE 桌面版版本、Edge／Chrome 版本、解析度與 DPI、逐項 checklist（掃描快取、MCP 同步、媒體還原、待快取卡片、更新檢查與下載）結果與問題截圖；不得含真實聊天內容；發現的缺陷各開 issue | 維護者 | `mission-reports/2026-10-31-line-vault.md:61`；`docs/` 目前只有 DECISIONS、DEVELOPMENT、ROADMAP 與範例匯出檔，無驗收紀錄 |

## 中期：等條件成立再做
| 項目 | 觸發條件 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| Google Drive／Sheets 雲端外送鏡像（選用） | 維護者決定放寬「100% 本機、無外部上傳」的承諾 | 預設關閉、需使用者在 GUI 明確開啟；外送前有機敏欄位脫敏且有測試；`README.md`、`SECURITY.md` 的本機隱私原則同步改寫；`DECISIONS.md` 新增 ADR 寫明資料離開本機的範圍 | Claude Opus | `README.md:84`（目前承諾無雲端上傳）；`SECURITY.md` 本機隱私原則 1；`docs/ANALYSIS_EXTERNAL_WORKFLOWS.md`（借鏡來源）；原路線圖 Phase 7（`git show 99ae95f:docs/ROADMAP.md`） |
| Gemini 視覺模型與 Function Calling 萃取收據、合約欄位（選用） | 上一列的雲端外送決定通過，且維護者決定接受把已落盤檔案送往外部模型 | 只對使用者指定的檔案隨選呼叫、金鑰只存本機設定不進 repo；送出前有脫敏與確認步驟；未設金鑰時功能不出現而不是報錯；測試涵蓋拒送與脫敏 | Claude Opus | `docs/ANALYSIS_EXTERNAL_WORKFLOWS.md`（兩階段原則：先收集分類儲存，再決定是否送 AI）；原路線圖 Phase 7 |
| 本機 Whisper 離線語音轉文字 | 維護者要求，且打包後的 `LINE-Vault-win64.exe` 體積與啟動時間增加可接受 | 點擊語音訊息可離線產生繁中字幕；模型不進 repo、首次使用時下載並驗 SHA-256；`tools/build_release.ps1` 的產物大小在本列記下前後對照 | Claude Opus | 原路線圖「未來願景」（`git show 99ae95f:docs/ROADMAP.md`）；`tools/build_release.ps1` |
| 自訂 LLM 端點（Ollama、OpenAI 相容） | 維護者要求更深的多輪洞察，且接受 OpenAI 相容端點可能是雲端 | 端點與金鑰在 GUI 設定；預設仍是現有的規則式分析；選到非 `127.0.0.1` 端點時顯示明確的資料外送提示；測試涵蓋未設定、連線失敗與回應格式錯誤 | Claude Sonnet | 原路線圖「未來願景」；`line_vault/analyzer.py`（現有規則式分析） |
| 以 Windows 工作排程器在 LINE Vault 沒開著時也巡檢歸檔 | 實際出現「應用程式沒開、媒體過期而未歸檔」；先過 Windows 三問（偵測器與被監控物是否同生共死、既有機制是否已提供） | 工作排程器項目由 GUI 一鍵建立與移除；沒開 GUI 時增量歸檔成功；移除後無殘留；現有 `VaultAutoUpdater` 只在程序執行時巡檢，新機制不得與它重複同步同一批檔案 | Claude Opus | `line_vault/server.py:183`（`VaultAutoUpdater`）；原路線圖「未來願景」自動排程備份 |
| 媒體子資料夾依「年-月」或檔案類型再分層 | 單一聊天室的媒體資料夾大到難以瀏覽，或維護者要求 | 設定可選分層方式，預設維持現狀；既有已歸檔檔案不搬動或有可重跑的遷移；歸檔去重（雜湊）不受影響 | Claude Sonnet | `docs/ANALYSIS_EXTERNAL_WORKFLOWS.md:52`；`line_vault/archiver.py`（依聊天室名稱建子資料夾的實作） |

## 刻意不做
| 不做什麼 | 理由 | 什麼情況下重新考慮 |
| --- | --- | --- |
| 提供命令列子命令（`stats`、`search`、`scan` 等） | 使用者明確要求純 GUI，所有功能須能在圖形介面完成（`docs/DECISIONS.md` ADR-005、`AGENTS.md:12`） | 維護者改變產品定位 |
| 非官方 LINE 帳號密碼或 QR 假客戶端登入，以及從 LINE 雲端強拉已過期媒體 | 極易觸發帳號封鎖與踢掉手機端；改採掃描本機快取加 E2EE 還原（`mission-reports/2026-10-31-line-vault.md:58`） | LINE 提供官方、允許個人帳號的匯出或讀取介面 |
| 自動、未經使用者確認就發送 LINE 訊息 | 專案範圍只讀與建議；回覆草稿一律由使用者複製（`mission-reports/2026-10-31-line-vault.md:15`） | 維護者明確要求並設計逐次確認流程 |
| 要求使用者手動逐一開啟聊天室媒體來補齊快取，或讓前端露出破圖 | 對數十個聊天室、成千上萬個檔案不可行；改用 LINE 內建批次下載加自動打撈，未落地的一律顯示待快取卡片（`AGENTS.md:41-47`） | LINE 取消批次下載或快取目錄結構改變到無法關聯 |
| 引入 FastAPI、Flask、Electron 等外部 Web／桌面框架 | 零依賴、雙擊即啟動是產品賣點，也縮小攻擊面（`docs/DECISIONS.md` ADR-001） | 標準庫 `http.server` 無法滿足需求且有具體量測 |
| 保留多個舊 Release／Tag | 維護者的單一最新 Release／Tag 政策（`AGENTS.md:13`）；遠端現在只有 v1.4.3 | 維護者改變發布政策 |

## 維護方式
自有 repo，直接在 `main` 上工作，不開分支與 PR。依賴由 Dependabot（pip、github-actions 每週）與每週一的 `Dependency freshness` 追蹤；合併前 `pwsh -NoProfile -File tools\dev_check.ps1`（compileall、ruff、契約測試、文件連結）與 `pwsh -NoProfile -File tools\test_product.ps1`（產品測試）全綠，CI 在 Windows 上跑 Python 3.10–3.14。中英文件（`README`、本檔）同一個 commit 改。修 `REVIEW.md` 列的問題時回註修復 commit 與日期。查現況：`gh issue list -R SanHsien/line-vault`、`gh api "repos/SanHsien/line-vault/code-scanning/alerts?state=open"`、`gh run list -R SanHsien/line-vault -b main -L 8`。
