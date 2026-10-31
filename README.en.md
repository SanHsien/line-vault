[**English**](README.en.md) · [繁體中文](README.md)

# LINE Vault

[![CI](https://github.com/SanHsien/line-vault/actions/workflows/ci.yml/badge.svg)](https://github.com/SanHsien/line-vault/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Windows 11 Native Pure GUI LINE Local Chat & Anti-Expiration Media Vault**  
> Features LINE E2EE media decryption, `line-desktop-mcp` encrypted database bridge, permanent anti-expiration cache archiving, FTS5 full-text search, and AI chat insights with suggested replies.

---

## 🗺️ Documentation Map

- [Traditional Chinese Documentation (繁體中文)](README.md)
- [Agent Governance Guidelines (AGENTS.md)](AGENTS.md)
- [Development & Maintenance Guide (docs/DEVELOPMENT.md)](docs/DEVELOPMENT.md)
- [Architecture Decision Records (docs/DECISIONS.md)](docs/DECISIONS.md)
- [Contributing Guide (CONTRIBUTING.md)](CONTRIBUTING.md)
- [Security Policy (SECURITY.md)](SECURITY.md)
- [Repository Review Report (REVIEW.md)](REVIEW.md)

---

## 🎯 Problems & The Pure GUI Solution

LINE Desktop users frequently face critical frustrations:
1. **"File expired and cannot be viewed"**: Photos, videos, and documents sent through LINE expire on the servers after a short period.
2. **Scattered search & history**: Difficult to perform unified, fast keyword and date range searches across multiple chats.
3. **Missed action items**: Project deliverables, quotes, and deadlines get buried in daily group chatter.

**LINE Vault is designed specifically for desktop users who prefer a 100% Pure GUI desktop experience**. Simply double-click to launch a standalone dark-mode native window where all monitoring, media archiving, FTS5 search, E2EE decryption, and AI insights are controlled entirely via mouse clicks.

```
+-------------------------------------------------------------------------+
|                  LINE Vault Pure GUI Desktop Workflow                   |
+-------------------------------------------------------------------------+
|                                                                         |
|  [ Double-click start_line_vault.bat ]                                  |
|        |                                                                |
|        v                                                                |
|  [ Dedicated Native Window (Microsoft Edge / Chrome App Mode) ]         |
|        |                                                                |
|        +-------------------+--------------------+                       |
|        |                   |                    |                       |
|        v                   v                    v                       |
|  [ Chat Monitor Panel ] [ Chat & Media Vault ] [ AI Action Insights ]   |
|  - 1-click anti-expire  - FTS5 ms-level search - Deadlines & quotes     |
|  - Group & 1-on-1 tabs  - Photo/Video/Doc tabs - 1-click reply copy     |
|        |                   |                    |                       |
|        +-------------------+--------------------+                       |
|                            |                                            |
|                            v                                            |
|       [ ⚙️ Settings & Sync Modal (In-App GUI) ]                         |
|       - 🔐 Bridge line-desktop-mcp encrypted database reader            |
|       - 🔄 1-click scan of local LINE cache (%LOCALAPPDATA%\LINE\Data)  |
|       - ⏱️ Background periodic sync & auto-archiving                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## ✨ Key Features

- **🖥️ 100% Pure GUI Desktop App**: Zero command-line knowledge required. Launches as an independent, frameless desktop application window with zero external web framework overhead.
- **🛡️ Permanent Anti-Expiration Backup**: Adheres to LINE Encryption Overview v2.2, verifying 32-byte HMAC-SHA256 tags and decrypting AES-256-CTR ciphertext to ensure media never expires.
- **🌉 `line-desktop-mcp` Reader Bridge**: Seamlessly bridges with local encrypted `.edb` / WAL snapshot readers to synchronize chats and capture decryption keys before files expire.
- **🔍 Local FTS5 Full-Text Search**: Sub-millisecond composite queries across chat rooms, keywords, media types, and date ranges with live highlighting.
- **🤖 Smart AI Conversation Analysis**:
  - **Summary**: Automatically condenses discussion topics and participants.
  - **Action Items**: Extracts deadlines (e.g. "before Friday"), finance quotes, and task requests.
  - **File Health Check**: Live indicators for archived, pending cache, or missing media.
  - **1-Click Smart Replies**: 3 tailored response drafts matching the latest context.
- **🔒 100% Local Privacy**: All database files, keys, and media remain strictly on the local machine with zero cloud telemetry.

---

## 🚀 Quick Start

### 1. Requirements
- **OS**: Windows 11 Native (or Windows 10)
- **Python**: Python 3.10 or newer

### 2. Installation

```powershell
cd C:\GitHub\line-vault
pip install -r requirements.txt
```

### 3. Launching the Pure GUI

Simply **double-click `start_line_vault.bat`** in Windows File Explorer.

LINE Vault opens directly in a dedicated desktop window without keeping a command prompt open.

---

## ⚙️ Settings & Sync in the GUI

Click the **「⚙️ 金庫與同步設定」 (Settings & Sync)** button in the top right header to manage all operations visually:

1. **🔐 Sync LINE Encrypted Database (MCP)**:
   - Provide the path to `line-desktop-mcp`'s `line-reader.py` (auto-detected by default).
   - Configure sync days (e.g. past 14 days) and optional target chat name.
   - Click to synchronize messages, decrypt keys, and save media into the vault.
2. **🔄 Scan Local LINE Cache**:
   - 1-click discovery and archiving of cached attachments in `%LOCALAPPDATA%\LINE\Data`.
3. **⏱️ Background Auto-Poll**:
   - Check the toggle to automatically poll and archive new messages every 5 minutes.
4. **✨ Seed Demo Data**:
   - Load realistic demo conversations with decrypted images, videos, PDF contracts, and ZIP archives.

---

## 🛠️ Development & Windows Verification Gates

Development and verification on Windows 11 follow strict canonical gates (see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)):

```powershell
# 1. Bootstrap maintenance environment
pwsh -NoProfile -File tools\bootstrap_dev.ps1

# 2. Run Windows developer checks (linting, contracts, relative links)
pwsh -NoProfile -File tools\dev_check.ps1

# 3. Run full product automated test suite
pwsh -NoProfile -File tools\test_product.ps1
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
