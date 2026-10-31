# 貢獻指南 (Contributing)

感謝您對 LINE Vault 的關注與貢獻！我們歡迎能提升 Windows 11 桌面體驗、檔案解密安全性與穩定度的小型改動。

## 開始之前

1. 詳讀 [`AGENTS.md`](AGENTS.md)、[`README.md`](README.md)（英文版見 [`README.en.md`](README.en.md)）與 [`SECURITY.md`](SECURITY.md)。
2. 確認問題在最新 `main` 分支上仍可重現，並確認無重複的 Issue 或 PR。
3. **純 GUI 原則**：本專案採用 100% 純 GUI 桌面介面設計，新增功能必須能在圖形介面內完整操作。
4. 嚴禁提交任何真實使用者的對話紀錄、快取檔案、個人身分資訊或 API 金鑰。

## 本機開發與門禁驗收

在 Windows 11 原生環境中進行開發：

```powershell
# 1. 初始化維護環境
pwsh -NoProfile -File tools\bootstrap_dev.ps1

# 2. 執行開發門禁（靜態檢查、合約測試、相對連結檢查）
pwsh -NoProfile -File tools\dev_check.ps1

# 3. 執行全量產品測試
pwsh -NoProfile -File tools\test_product.ps1
```

更多除錯與開發指引請參見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。

## 提交規範

- 一次提交聚焦單一問題或改動。
- 修改功能或介面時，同步更新繁體中文與英文說明。
- 提交訊息建議採用 Conventional Commits 格式（如 `feat:`, `fix:`, `docs:`, `test:`, `chore:`）。
- 開立 PR 時請填寫完整資訊並附上 `dev_check.ps1` 與 `test_product.ps1` 的綠燈執行輸出。
