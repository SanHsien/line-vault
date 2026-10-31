# 本機開發與維護指南 (Development Guide)

本指南說明如何在 Windows 11 原生環境下建置、開發、測試與驗收 `line-vault`。

## 環境需求

- **作業系統**：Windows 11 x64 原生環境（PowerShell 7 或 Windows PowerShell 5.1）
- **Python**：Python >= 3.10（支援至 3.14）
- **瀏覽器**：Microsoft Edge（Windows 內建）或 Google Chrome（供 `--app` 獨立視窗模式使用）
- **LINE 桌面端**（選用，實機測試時使用）：Windows LINE Desktop 26.x

## 目錄結構說明

```text
line-vault/
├── .github/                  # GitHub Actions 工作流程、PR 範本、Dependabot
├── docs/                     # 開發指南與架構決策紀錄 (ADR)
├── line_vault/               # 核心產品套件
│   ├── static/               # 純 GUI 前端資產 (HTML, CSS, JS)
│   ├── analyzer.py           # AI 對話分析與回覆建議
│   ├── archiver.py           # 防過期永久金庫與 MCP 橋接
│   ├── cli.py                # 桌面純 GUI 獨立視窗啟動器
│   ├── crypto.py             # E2EE 媒體解密與 Magic Bytes 探測
│   ├── db.py                 # SQLite WAL 模式與 FTS5 全文索引
│   └── server.py             # 零外部依賴 ThreadingHTTPServer 與 REST API
├── tests/                    # 產品全量自動化測試套件
├── tools/                    # Windows 維護工具與開發門禁腳本
│   └── tests/                # 專用維護合約測試 (契約測試)
├── start_line_vault.bat      # 雙擊無控制台視窗啟動腳本
├── requirements.txt          # 執行依賴
└── requirements-dev.txt      # 開發與維護依賴
```

## 1. 快速初始化開發環境

在 PowerShell 中執行初始化腳本：

```powershell
pwsh -NoProfile -File tools\bootstrap_dev.ps1
```

腳本將會自動：
1. 檢查 Python 版本並建立 `.venv` 虛擬環境。
2. 安裝 `requirements.txt` 與 `requirements-dev.txt`。
3. 執行 `tools\dev_check.ps1` 進行完整驗收。

## 2. Windows 本機開發門禁 (Dev Check)

每次提交或完成修改前必須執行：

```powershell
pwsh -NoProfile -File tools\dev_check.ps1
```

檢查項目包含：
- `compileall`：編譯 `line_vault`、`tools` 與 `tests` 之 Python 語法。
- `ruff check`：執行靜態代碼分析。
- `pytest -c tools\pytest.ini tools\tests`：執行維護契約測試。
- `check_links.py`：掃描所有 Markdown 文件的相對連結有效性。

## 3. 全量產品測試 (Product Tests)

執行產品自動化測試套件：

```powershell
pwsh -NoProfile -File tools\test_product.ps1
```

測試涵蓋：
- E2EE HKDF-SHA256、AES-256-CTR 與 HMAC 認證。
- Magic Bytes 二進位格式探測。
- SQLite 交易、FTS5 全文檢索與資料庫操作。
- 快取掃描、縮圖降級與 E2EE 密文永久歸檔。
- `line-desktop-mcp` 讀取引擎橋接同步與快取還原。
- REST API 端點（含路徑周遊安全防護）。

## 4. 依賴新鮮度檢查

執行依賴新鮮度比對工具：

```powershell
python tools\check_dependency_freshness.py
```

比對 `requirements.txt` 與 `requirements-dev.txt` 的宣告版本與 PyPI 最新現行版。

## 5. 發布與版本管理策略 (Release Policy)

- **直接提交至 main**：本專案所有功能與修復直接提交至 `main` 主分支，不建立長期 feature 分支。
- **單一最新標籤**：語意化版本 `1.0.0`，全倉庫維持單一最新 Release / Tag（`v1.0.0`），發布時清理或覆蓋舊標籤。

## 6. 相關指引連結

- [Agent 協作指引 (AGENTS.md)](../AGENTS.md)
- [產品發展藍圖 (docs/ROADMAP.md)](ROADMAP.md)
- [英文發展藍圖 (docs/ROADMAP.en.md)](ROADMAP.en.md)
- [架構決策紀錄 (docs/DECISIONS.md)](DECISIONS.md)
- [貢獻指南 (CONTRIBUTING.md)](../CONTRIBUTING.md)
- [安全政策 (SECURITY.md)](../SECURITY.md)
- [審查報告 (REVIEW.md)](../REVIEW.md)
- [繁體中文說明 (README.md)](../README.md)
- [英文說明 (README.en.md)](../README.en.md)
