"""Built-in Native Windows 11 LINE Database & Cache Reader Engine.

Bundled directly inside LINE Vault (and compiled into LINE-Vault-win64.exe) so users
never need to install or configure an external line-reader.py script.
Operates in 100% read-only mode without locking active LINE.exe files.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from pathlib import Path

from line_vault.crypto import sniff_media_format

# Printable CJK + ASCII text pattern for extracting message snippets from WAL / EDB pages
_TEXT_SNIPPET_RE = re.compile(
    r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffefA-Za-z0-9_.\-:/，。！？、（）「」『』【】\s]{6,200}"
)


def try_deobfuscate_xor_media(raw: bytes) -> bytes:
    """Detect and reverse single-byte XOR obfuscation used by Windows LINE cache files."""
    if len(raw) < 16:
        return raw

    # Already a recognized plaintext format?
    direct_info = sniff_media_format(raw)
    if direct_info["format"] != "bin":
        return raw

    # Candidate XOR keys derived from known magic headers:
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    # JPG: FF D8 FF
    # GIF: 47 49 46 38
    # PDF: 25 50 44 46
    candidate_keys = [
        raw[0] ^ 0x89,
        raw[0] ^ 0xFF,
        raw[0] ^ 0x47,
        raw[0] ^ 0x25,
    ]
    # MP4 'ftyp' at offset 4..8
    if len(raw) >= 12:
        candidate_keys.append(raw[4] ^ ord("f"))

    seen: set[int] = set()
    for key in candidate_keys:
        if key == 0 or key in seen:
            continue
        seen.add(key)
        # Test first 32 bytes before decoding full payload
        header_probe = bytes(b ^ key for b in raw[:32])
        probe_info = sniff_media_format(header_probe)
        if probe_info["format"] != "bin":
            return bytes(b ^ key for b in raw)

    return raw


class BuiltinLineReader:
    """Built-in native reader for Windows LINE desktop data, .edb/WAL files, and cache buckets."""

    def __init__(self, line_root: Path | str | None = None):
        if line_root is not None and str(line_root).strip():
            self.root = Path(line_root).resolve()
        else:
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            self.root = (Path(local_appdata) / "LINE").resolve() if local_appdata else Path("vault_data/cache").resolve()

    def discover_databases_and_Wal(self) -> list[Path]:
        """Locate all .edb, .edb-wal, .db, and .sqlite files under the LINE root."""
        if not self.root.exists():
            return []
        found: list[Path] = []
        try:
            for ext in ("*.edb", "*.edb-wal", "*.db", "*.sqlite"):
                for p in self.root.rglob(ext):
                    if p.is_file():
                        found.append(p)
        except OSError:
            pass
        return found

    def extract_wal_text_snippets(self, db_files: list[Path], max_snippets: int = 40) -> list[dict]:
        """Extract readable UTF-8 conversation snippets from non-locked .edb-wal / .db pages."""
        snippets: list[dict] = []
        seen_texts: set[str] = set()

        for path in db_files:
            try:
                size = path.stat().st_size
                if size == 0 or size > 64 * 1024 * 1024:
                    continue
                # Read up to 2 MB tail where recent WAL frames live
                with open(path, "rb") as f:
                    if size > 2 * 1024 * 1024:
                        f.seek(size - 2 * 1024 * 1024)
                    chunk = f.read()

                decoded = chunk.decode("utf-8", errors="ignore")
                for match in _TEXT_SNIPPET_RE.finditer(decoded):
                    txt = match.group(0).strip()
                    # Must contain at least 2 CJK characters to avoid binary/SQL noise
                    cjk_count = sum(1 for c in txt if "\u4e00" <= c <= "\u9fff")
                    if cjk_count < 2 or len(txt) < 4:
                        continue
                    if txt in seen_texts:
                        continue
                    seen_texts.add(txt)
                    mtime_ms = int(path.stat().st_mtime * 1000)
                    msg_id = f"edb_{hashlib.sha1(txt.encode('utf-8')).hexdigest()[:12]}"
                    snippets.append({
                        "id": msg_id,
                        "sender": "LINE 本機紀錄",
                        "text": txt,
                        "type": "text",
                        "timestampMs": mtime_ms,
                        "sourceFile": path.name,
                    })
                    if len(snippets) >= max_snippets:
                        return snippets
            except OSError:
                continue

        return snippets

    def run_native_sync(
        self,
        archiver,
        chat_name: str | None = None,
        days: int = 14,
        analyzer=None,
    ) -> dict:
        """Perform an all-in-one built-in sync of Windows LINE databases and media cache."""
        if not self.root.exists():
            return {
                "status": "ok",
                "engine": "builtin-native-reader",
                "chats_synced": 0,
                "messages_synced": 0,
                "media_archived": 0,
                "edb_databases_found": [],
            }

        db_files = self.discover_databases_and_Wal()
        edb_names = [p.name for p in db_files]

        chats_synced = 0
        messages_synced = 0
        media_archived = 0
        synced_chat_ids: list[str] = []

        # 1. Extract readable conversation snippets from .edb / .edb-wal / .db if available
        snippets = self.extract_wal_text_snippets(db_files)
        if snippets:
            edb_chat_id = "c_line_edb_sync"
            edb_chat_title = chat_name or "本機 LINE 資料庫同步紀錄"
            archiver.db.upsert_chat(
                chat_id=edb_chat_id,
                chat_name=edb_chat_title,
                chat_type="group",
                monitored=True,
                notes=f"由內建引擎同步自 {self.root} ({len(edb_names)} 個資料庫檔)",
            )
            chats_synced += 1
            synced_chat_ids.append(edb_chat_id)
            for idx, item in enumerate(snippets):
                archiver.db.upsert_message(
                    message_id=item["id"],
                    chat_id=edb_chat_id,
                    sender_id="line_edb",
                    sender_name=item["sender"],
                    timestamp_ms=item["timestampMs"] + idx,
                    content_type="text",
                    text_content=item["text"],
                )
                messages_synced += 1

        # 2. Scan and deobfuscate media cache files (including XOR-encoded cache items)
        cache_chat_id = "c_local_line_scan"
        cache_chat_title = chat_name or "本機 LINE 快取防過期媒體庫"
        files_inspected = 0

        try:
            for candidate in self.root.rglob("*"):
                if not candidate.is_file():
                    continue
                suffix = candidate.suffix.lower()
                if suffix in (".edb", ".edb-wal", ".edb-shm", ".db", ".sqlite", ".ini", ".log", ".dll", ".exe"):
                    continue
                files_inspected += 1
                if files_inspected > 800:
                    break

                try:
                    size = candidate.stat().st_size
                    if size < 32 or size > 50 * 1024 * 1024:
                        continue
                    raw = candidate.read_bytes()
                    restored = try_deobfuscate_xor_media(raw)
                    info = sniff_media_format(restored, fallback_filename=candidate.name)
                    if info["format"] == "bin":
                        continue

                    if cache_chat_id not in synced_chat_ids:
                        archiver.db.upsert_chat(
                            chat_id=cache_chat_id,
                            chat_name=cache_chat_title,
                            chat_type="group",
                            monitored=True,
                            notes=f"自動掃描與解密還原自 {self.root}",
                        )
                        chats_synced += 1
                        synced_chat_ids.append(cache_chat_id)

                    sha10 = info["sha256"][:10]
                    msg_id = f"scan_{sha10}"
                    mtime_ms = int(candidate.stat().st_mtime * 1000)
                    ext = info["ext"]
                    safe_name = candidate.name if candidate.name.endswith(ext) else f"{candidate.stem}{ext}"

                    chat_folder = archiver.media_dir / cache_chat_id
                    chat_folder.mkdir(parents=True, exist_ok=True)
                    dest_file = chat_folder / f"{msg_id}{ext}"
                    dest_file.write_bytes(restored)

                    archiver.db.upsert_message(
                        message_id=msg_id,
                        chat_id=cache_chat_id,
                        sender_id="local_line",
                        sender_name="LINE 本機快取",
                        timestamp_ms=mtime_ms,
                        content_type=info["media_type"],
                        text_content=f"自本機 LINE 快取永久歸檔：{safe_name}",
                        media_status="archived",
                        file_name=safe_name,
                    )
                    archiver.db.register_media(
                        media_id=f"m_{msg_id}",
                        message_id=msg_id,
                        chat_id=cache_chat_id,
                        media_type=info["media_type"],
                        file_name=safe_name,
                        mime_type=info["mime_type"],
                        format_name=info["format"],
                        size_bytes=info["size_bytes"],
                        sha256=info["sha256"],
                        vault_rel_path=f"media/{cache_chat_id}/{dest_file.name}",
                        source_role="original",
                    )
                    messages_synced += 1
                    media_archived += 1
                except OSError:
                    continue
        except OSError:
            pass

        # If neither WAL snippets nor cache media were found yet, still register the local LINE status chat
        if chats_synced == 0 and edb_names:
            edb_chat_id = "c_line_edb_sync"
            archiver.db.upsert_chat(
                chat_id=edb_chat_id,
                chat_name=chat_name or "本機 LINE 資料庫巡檢紀錄",
                chat_type="group",
                monitored=True,
                notes=f"已偵測到 {len(edb_names)} 個 LINE 資料庫檔案",
            )
            archiver.db.upsert_message(
                message_id="edb_status_01",
                chat_id=edb_chat_id,
                sender_id="system",
                sender_name="內建讀取引擎",
                timestamp_ms=1730000000000,
                content_type="text",
                text_content=(
                    f"已成功連線檢測本機 LINE 目錄 ({self.root})，"
                    f"發現資料庫檔案：{', '.join(edb_names[:5])}，"
                    f"共巡檢 {files_inspected} 個快取檔案。"
                ),
            )
            chats_synced = 1
            messages_synced = 1
            synced_chat_ids.append(edb_chat_id)

        if analyzer:
            for cid in synced_chat_ids:
                try:
                    analyzer.analyze_chat(cid)
                except (ValueError, sqlite3.Error):
                    continue

        return {
            "status": "ok",
            "engine": "builtin-native-reader",
            "scanned_dir": str(self.root),
            "edb_databases_found": edb_names,
            "files_inspected": files_inspected,
            "chats_synced": chats_synced,
            "messages_synced": messages_synced,
            "media_archived": media_archived,
        }
