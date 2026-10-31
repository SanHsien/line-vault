# 安全政策 (Security Policy)

## 支援範圍

安全修正與更新以本 repository 的最新 `main` 分支為主。

## 私下通報安全漏洞

若發現針對 `line-vault` 的安全性問題、加密金鑰外洩風險或路徑周遊（Path Traversal）漏洞，請透過 GitHub Security Advisories 的 **Report a vulnerability** 入口進行私下通報：
<https://github.com/SanHsien/line-vault/security/advisories/new>。

若該入口暫不可用，請透過 GitHub 個人檔案聯絡維護者，切勿直接建立公開 Issue。

通報時請包含：
- 受影響版本與作業系統環境
- 漏洞成因與詳細可重現步驟（PoC）
- 潛在安全影響與建議修正方式

**注意**：通報內容中**切勿附帶任何真實 LINE 聊天內容、使用者個資、實際快取媒體檔案或真實金鑰**。

## 本機隱私與防護原則

1. **完全離線本地執行**：LINE Vault 所有解密作業、資料庫儲存與 AI 分析均在本機完成，絕無外部伺服器遙測或資料回傳。
2. **嚴格路徑周遊防禦**：伺服器提供靜態與媒體二進位下載時，嚴格使用 `relative_to` 與真實路徑解析校驗，阻擋任何周遊攻擊。
3. **無明文金鑰落地**：金鑰衍生與快取還原僅在記憶體中進行，永久歸檔僅保存還原後之乾淨檔案。
