## 變更摘要 (Summary)
<!-- 簡要說明本次修改的目標與主要變更 -->

## 修改動機 (Motivation)
<!-- 說明為什麼需要此變更或修復之問題 -->

## 本機驗證輸出 (Verification Output)
<!-- 貼上 Windows 11 原生 PowerShell 門禁執行結果 -->
```text
pwsh -NoProfile -File tools\dev_check.ps1
pwsh -NoProfile -File tools\test_product.ps1
```

## 隱私與安全自我檢查 (Privacy & Security Checklist)
- [ ] 未提交任何真實 LINE 聊天紀錄、快取檔案或個人機密資料
- [ ] 未提交任何 API key、Token 或私鑰
- [ ] 無 `os.system`、`shell=True`、`eval(` 或 `except Exception: pass` 等靜默吞例外構造
- [ ] 相對文件連結均通過 `tools\check_links.py` 驗證
