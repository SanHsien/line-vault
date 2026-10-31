# LINE Vault Product Roadmap

This document outlines the architectural milestones and product evolution history of `line-vault`. Goals and delivery statuses across each phase are detailed below:

---

## Milestone Overview

| Milestone | Core Theme | Status | Key Deliverables |
| :--- | :--- | :---: | :--- |
| **Phase 1** | Core Encryption Vault & Full-Text Search | [x] Completed | E2EE media decryption, magic bytes sniffing, SQLite WAL + FTS5 millisecond search |
| **Phase 2** | Pure GUI Workspace & Windows Desktop Experience | [x] Completed | 3-pane modern dark theme GUI, Edge/Chrome App standalone window launcher, media galleries |
| **Phase 3** | Local AI Smart Analysis & Contextual Smart Replies | [x] Completed | Rule/AI action item extraction, vault file health inspection, one-click contextual reply copying |
| **Phase 4** | Message Bookmarks & Action Item Check-Off | [x] Completed | Star bookmarking (⭐), dedicated bookmarks tab, action item check-off loop (✅) |
| **Phase 5** | One-Click Chat Report Export & .txt Chat Import | [x] Completed | One-click Markdown/JSON report export, GUI import of official LINE .txt chat history |
| **Phase 6+** | Future Visions | [ ] Planned | Local offline Whisper voice-to-text, custom LLM endpoint integration (Ollama/OpenAI) |

---

## Detailed Milestone Descriptions

### Phase 1: Core Encryption Vault & FTS5 Indexing — `[x] Completed`
- [x] LINE E2EE (Letter Sealing) AES-256-CBC media decryption engine and SHA-256 integrity verification.
- [x] Media file format sniffing via magic bytes (JPEG, PNG, GIF, MP4, PDF, ZIP, etc.).
- [x] SQLite WAL high-concurrency architecture with FTS5 inverted full-text index.
- [x] Local cache fingerprint matching and automatic vault archiving mechanism.

### Phase 2: Pure GUI Workspace & Windows Desktop Integration — `[x] Completed`
- [x] Zero-build-dependency 3-pane dark theme workspace (Chat list, message/media viewer, AI insight pane).
- [x] Windows 11 native standalone window launch (`start_line_vault.bat` double-click console-less launcher, Edge/Chrome `--app` mode).
- [x] Media photo wall, video gallery, and document vault with direct local file download.
- [x] Date range filtering and full-text real-time search term highlighting.

### Phase 3: AI Smart Analysis & Contextual Replies — `[x] Completed`
- [x] Rule-based and smart AI analysis extracting milestones, quotes/invoices, questions, and assigned tasks.
- [x] Attachment health status tracking (vault-archived, thumbnail-cached, pending download).
- [x] Contextual suggested replies across 3 tones (business professional, proactive, rigorous) with one-click clipboard copying.
- [x] Bilingual AI analysis generation (Traditional Chinese `zh-TW` and English `en`).

### Phase 4: Message Bookmarking & Action Item Check-Off — `[x] Completed`
- [x] Message-level star bookmarking (⭐ click to toggle, persisted to database).
- [x] Dedicated Bookmarks navigation tab for quick access to key messages across chats.
- [x] Action item check-off loop (✅ checkbox), automatically striking through completed items and deducting from dashboard pending stats.

### Phase 5: One-Click Report Export & .txt Chat History Import — `[x] Completed`
- [x] One-click chat and AI analysis report export (structured Markdown and full JSON format).
- [x] GUI upload and parsing of official LINE desktop/mobile exported `.txt` chat histories.
- [x] Automatic chat creation and immediate AI insight generation upon import.
- [x] Seamless bilingual GUI switcher (Traditional Chinese / English with one click).

---

## Future Visions

- [ ] **Offline Voice-to-Text**: Integrate local lightweight Whisper models for transcribing voice messages offline.
- [ ] **Custom External LLM Integration**: Connect to custom Ollama or OpenAI-compatible endpoints for multi-turn deep dialogue insights.
- [ ] **Scheduled Automated Archiving**: Windows Task Scheduler integration for background incremental vault synchronization.
