# CLAUDE.md

Claude Code 在本專案工作時的指引入口：

- **全域協作與代理規則**：請先完整閱讀 [`AGENTS.md`](AGENTS.md)。
- **產品發展藍圖**：參閱 [`docs/ROADMAP.md`](docs/ROADMAP.md)（英文版見 [`docs/ROADMAP.en.md`](docs/ROADMAP.en.md)）。
- **開發環境與驗證門禁**：詳細 Windows 11 PowerShell 執行方式見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。
- **架構決策與審查狀態**：參閱 [`docs/DECISIONS.md`](docs/DECISIONS.md) 與 [`REVIEW.md`](REVIEW.md)。
- **安全與貢獻規範**：參閱 [`SECURITY.md`](SECURITY.md) 與 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

> ⚠️ **核心規範提醒**：本專案為 **Windows 11 / 10 專用 100% 純 GUI 桌面應用**，不提供 CLI 子命令。直接 push 至 `main` 主分支，維持單一最新 Release / Tag。嚴禁指引使用者逐一手動點開聊天室媒體，媒體未快取時嚴禁露出破圖或引發看圖軟體報錯，一律以優雅待快取卡片與批次機制處理。完成前務必在 Windows 11 執行 `tools\dev_check.ps1` 與 `tools\test_product.ps1`。
