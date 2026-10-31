[English](README.en.md) · **繁體中文**

# LINE Vault (LINE 金庫)

[![CI](https://github.com/SanHsien/line-vault/actions/workflows/ci.yml/badge.svg)](https://github.com/SanHsien/line-vault/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Windows 11 原生純圖形化（Pure GUI）LINE 本地對話與防過期媒體管理中心**  
> 支援 E2EE 端對端加密媒體解析、`line-desktop-mcp` 加密資料庫橋接、快取防過期永久留存、FTS5 全文檢索與 AI 智慧對話摘要與行動建議。

---

## 🗺️ 文件導航 (Documentation Map)

- [English Documentation](README.en.md)
- [Agent 協作指引 (AGENTS.md)](AGENTS.md)
- [開發與維護指南 (docs/DEVELOPMENT.md)](docs/DEVELOPMENT.md)
- [架構決策紀錄 (docs/DECISIONS.md)](docs/DECISIONS.md)
- [貢獻指南 (CONTRIBUTING.md)](CONTRIBUTING.md)
- [安全政策 (SECURITY.md)](SECURITY.md)
- [架構審查報告 (REVIEW.md)](REVIEW.md)

---

## 🎯 痛點與純 GUI 解決方案

LINE 電腦版使用者最常面臨的致命痛點：
1. **「檔案過期無法讀取」**：伺服器上的照片、影片與文件有嚴格保存期限，超期即永久失效。
2. **搜尋與回顧雜亂**：跨群組、跨聊天室難以進行精準關鍵字與日期篩選。
3. **重要工作待辦遺漏**：專案群組中客戶交代的需求、截止日或報價散落各處。

**LINE Vault 專為不願接觸終端機的桌面使用者打造，採 100% 純 GUI（圖形化介面）設計**。雙擊啟動即可開啟深色模式原生視窗，所有對話監控、檔案保存、FTS5 全文搜尋、E2EE 媒體解密與 AI 建議均透過點擊完成。

```
+-------------------------------------------------------------------------+
|                    LINE Vault 純 GUI 桌面運作流程                       |
+-------------------------------------------------------------------------+
|                                                                         |
|  [ 雙擊 start_line_vault.bat ]                                          |
|        |                                                                |
|        v                                                                |
|  [ 獨立原生桌面視窗 (Microsoft Edge / Chrome App Mode) ]                |
|        |                                                                |
|        +-------------------+--------------------+                       |
|        |                   |                    |                       |
|        v                   v                    v                       |
|  [ 聊天室監控面板 ]   [ 對話與媒體金庫 ]   [ AI 智慧行動建議 ]          |
|  - 一鍵切換防過期備份 - FTS5 毫秒全文檢索  - 自動提取截止日與報價       |
|  - 多群組與個人分類   - 相片牆/影片/檔案櫃 - 3 款情境回覆草稿一鍵複製   |
|        |                   |                    |                       |
|        +-------------------+--------------------+                       |
|                            |                                            |
|                            v                                            |
|       [ ⚙️ 金庫與同步設定 (Settings & Sync Modal) ]                     |
|       - 🔐 整合 line-desktop-mcp 加密資料庫讀取引擎                     |
|       - 🔄 一鍵掃描本機 LINE 快取資料夾 (%LOCALAPPDATA%\LINE\Data)      |
|       - ⏱️ 背景自動巡檢與防過期永久留存                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## ✨ 核心特性

- **🖥️ 100% 純 GUI 桌面體驗**：無需任何指令列操作！雙擊即開獨立無邊框應用程式視窗，無外部 Web 框架負擔。
- **🛡️ 防過期永久備份**：依據 LINE Encryption Overview v2.2 規範，驗證 32 位元組 HMAC-SHA256 標籤並還原 AES-256-CTR 密文，確保相片、影片與重要合約永不過期。
- **🌉 整合 `line-desktop-mcp` 讀取引擎**：直接介接本機加密 `.edb` / WAL 讀取器，免操作 LINE 介面即可將對話與待下載媒體金鑰全自動同步進金庫。
- **🔍 本地 FTS5 毫秒檢索**：複合條件查詢（聊天室、關鍵字、媒體類型、起訖日期），支援即時高亮標記。
- **🤖 智慧對話分析**：
  - **對話重點摘要**：自動歸納參與者發言主題與脈絡。
  - **行動清單提取**：自動辨識期限（如「週五前」、「明天」）、金流（「報價」、「發票」）與待辦。
  - **檔案巡檢狀態**：即時標示已永久存檔、縮圖暫存中或亟需快取之檔案。
  - **一鍵建議回覆**：針對最後對話情境提供 3 組不同語氣的繁體中文回覆草稿，點擊即可複製。
- **🔒 100% 本地隱私保障**：所有資料庫與解密檔案完整保存在使用者本機磁碟，完全無外部雲端上傳或遙測。

---

## 🚀 快速開始

### 1. 系統需求
- **作業系統**：Windows 11 原生環境（或 Windows 10）
- **Python 版本**：Python 3.10 或更新版本

### 2. 安裝方式

```powershell
# 切換至專案根目錄
cd C:\GitHub\line-vault

# 初始化並安裝依賴
pip install -r requirements.txt
```

### 3. 一鍵啟動純 GUI 桌面應用

直接在檔案總管中**雙擊執行 `start_line_vault.bat`**。

系統將自動在獨立視窗中開啟 LINE Vault 桌面應用程式，無需開啟黑底終端機視窗。

---

## ⚙️ 圖形化設定與同步操作

在 LINE Vault 視窗右上角點選 **「⚙️ 金庫與同步設定」**，即可在單一視窗內完成所有維護與資料導入作業：

1. **🔐 同步 LINE 加密資料庫 (MCP)**：
   - 填入 `line-desktop-mcp` 的 `line-reader.py` 路徑（預設自動偵測）。
   - 設定同步天數（例如近 14 天）與目標聊天室。
   - 點擊按鈕，系統將自動提取訊息與媒體金鑰，並自快取還原原檔歸檔至金庫。
2. **🔄 掃描本機 LINE 快取資料夾**：
   - 一鍵掃描 `%LOCALAPPDATA%\LINE\Data` 快取檔案並進行防過期永久留存。
3. **⏱️ 背景自動巡檢**：
   - 勾選開啟後，系統每 5 分鐘自動巡檢同步最新訊息與檔案附件。
4. **✨ 載入範例資料**：
   - 一鍵建立多個真實工作與家庭聊天室範例（包含已解密的相片、示範影片、合約 PDF 與部署包 ZIP），供即時體驗完整功能。

---

## 🛠️ 開發與自動化驗收

本專案遵循嚴謹的 Windows 原生開發門禁（詳細請見 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)）：

```powershell
# 1. 快速建立維護環境
pwsh -NoProfile -File tools\bootstrap_dev.ps1

# 2. 執行 Windows 本地開發門禁（靜態檢查、合約測試、相對連結）
pwsh -NoProfile -File tools\dev_check.ps1

# 3. 執行全量產品自動化測試
pwsh -NoProfile -File tools\test_product.ps1
```

---

## 📄 授權條款

本專案採用 [MIT License](LICENSE) 開源授權。
