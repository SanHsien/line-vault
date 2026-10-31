"""Media archiver for LINE E2EE media payloads, cache scanning, and demo seeding."""

import hashlib
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path

from line_vault.crypto import (
    decrypt_e2ee_media,
    encrypt_e2ee_media,
    generate_key_material,
    sniff_media_format,
)
from line_vault.db import VaultDB


def _sanitize_path_part(text: str) -> str:
    """Sanitize string for safe directory and file names."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", text)


class MediaArchiver:
    """Handles permanent archiving of LINE media attachments, cache extraction, and mock seeding."""

    def __init__(self, vault_dir: Path | str, db: VaultDB):
        self.vault_dir = Path(vault_dir).resolve()
        self.media_dir = self.vault_dir / "media"
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.db = db

    def archive_encrypted_bytes(
        self,
        message_id: str,
        chat_id: str,
        encrypted_data: bytes,
        material_b64: str,
        fallback_filename: str | None = None,
        source_role: str = "original",
    ) -> dict:
        """Authenticate, decrypt, inspect, and permanently archive an encrypted media payload."""
        decrypted_bytes = decrypt_e2ee_media(encrypted_data, material_b64)
        info = sniff_media_format(decrypted_bytes, fallback_filename)

        safe_chat = _sanitize_path_part(chat_id)
        safe_msg = _sanitize_path_part(message_id)
        chat_folder = self.media_dir / safe_chat
        chat_folder.mkdir(parents=True, exist_ok=True)

        sha10 = info["sha256"][:10]
        ext = info["ext"]
        filename = fallback_filename or f"{safe_msg}_{sha10}{ext}"
        if not filename.endswith(ext):
            filename += ext

        dest_file = chat_folder / f"{safe_msg}_{sha10}{ext}"
        with open(dest_file, "wb") as f:
            f.write(decrypted_bytes)

        rel_path = f"media/{safe_chat}/{dest_file.name}"
        media_id = f"m_{safe_msg}_{sha10[:8]}"

        record = self.db.register_media(
            media_id=media_id,
            message_id=message_id,
            chat_id=chat_id,
            media_type=info["media_type"],
            file_name=filename,
            mime_type=info["mime_type"],
            format_name=info["format"],
            size_bytes=info["size_bytes"],
            sha256=info["sha256"],
            vault_rel_path=rel_path,
            source_role=source_role,
        )
        return record

    def scan_and_archive_line_cache(
        self,
        chat_id: str,
        message_id: str,
        cache_root: Path | str,
        material_b64: str,
        declared_bytes: int,
        fallback_filename: str | None = None,
        thumb_path: Path | str | None = None,
    ) -> dict:
        """Scan LINE cache directory for a candidate matching declared_bytes + 32, decrypt, and archive."""
        root = Path(cache_root).resolve()
        if not root.exists():
            return {"status": "cache_root_not_found", "message_id": message_id}

        chat_hash = hashlib.sha1(chat_id.encode("utf-8")).hexdigest()
        expected_size = declared_bytes + 32

        # Candidate paths to inspect
        candidate_paths: list[Path] = []

        # 1. Standard LINE 26.x cache pattern: <account_bucket>/<chat_hash>/m/
        for match in root.glob(f"*/{chat_hash}/m/*"):
            if match.is_file() and match.stat().st_size == expected_size:
                candidate_paths.append(match)

        # 2. General fallback search in cache_root if specific hash folder not matched
        if not candidate_paths:
            for f in root.rglob("*"):
                if f.is_file() and f.stat().st_size == expected_size:
                    candidate_paths.append(f)

        for cand in candidate_paths:
            try:
                with open(cand, "rb") as cf:
                    cand_data = cf.read()
                record = self.archive_encrypted_bytes(
                    message_id=message_id,
                    chat_id=chat_id,
                    encrypted_data=cand_data,
                    material_b64=material_b64,
                    fallback_filename=fallback_filename,
                    source_role="original",
                )
                return {"status": "archived", "media": record, "source_cache": str(cand)}
            except (ValueError, OSError, sqlite3.Error):
                continue

        # If original not yet in cache, check if thumbnail exists
        if thumb_path:
            t_path = Path(thumb_path).resolve()
            if t_path.is_file():
                try:
                    with open(t_path, "rb") as tf:
                        t_data = tf.read()
                    # Check if thumb is encrypted or plaintext
                    try:
                        thumb_decrypted = decrypt_e2ee_media(t_data, material_b64)
                    except ValueError:
                        thumb_decrypted = t_data

                    info = sniff_media_format(thumb_decrypted, fallback_filename or "thumb.jpg")
                    safe_chat = _sanitize_path_part(chat_id)
                    safe_msg = _sanitize_path_part(message_id)
                    chat_folder = self.media_dir / safe_chat
                    chat_folder.mkdir(parents=True, exist_ok=True)

                    dest_file = chat_folder / f"{safe_msg}_thumb_{info['sha256'][:8]}{info['ext']}"
                    with open(dest_file, "wb") as f:
                        f.write(thumb_decrypted)

                    rel_path = f"media/{safe_chat}/{dest_file.name}"
                    media_id = f"m_{safe_msg}_thumb"

                    if not self.db.get_chat(chat_id):
                        self.db.upsert_chat(chat_id=chat_id, chat_name=chat_id)
                    # Ensure message row exists and mark as cached_pending before registering media FK
                    self.db.upsert_message(
                        message_id=message_id,
                        chat_id=chat_id,
                        media_status="cached_pending",
                        file_name=fallback_filename or "",
                    )
                    record = self.db.register_media(
                        media_id=media_id,
                        message_id=message_id,
                        chat_id=chat_id,
                        media_type="image",
                        file_name=f"thumb_{fallback_filename or 'preview.jpg'}",
                        mime_type=info["mime_type"],
                        format_name=info["format"],
                        size_bytes=info["size_bytes"],
                        sha256=info["sha256"],
                        vault_rel_path=rel_path,
                        source_role="thumbnail",
                    )
                    self.db.upsert_message(
                        message_id=message_id,
                        chat_id=chat_id,
                        media_status="cached_pending",
                        file_name=fallback_filename or "",
                    )
                    return {
                        "status": "cached_pending",
                        "media": record,
                        "pending_original": True,
                    }
                except (ValueError, OSError, sqlite3.Error) as exc:
                    return {
                        "status": "thumbnail_error",
                        "message_id": message_id,
                        "error": str(exc),
                    }

        return {"status": "not_found", "message_id": message_id}

    def scan_local_line_directory(self, line_data_dir: Path | str, analyzer=None) -> dict:
        """Scan a local LINE Data/Cache directory and import/archive discovered media assets."""
        root = Path(line_data_dir).resolve()
        if not root.exists():
            raise FileNotFoundError(f"LINE directory not found: {root}")

        edb_files = [p.name for p in root.rglob("*.edb") if p.is_file()]
        files_inspected = 0
        media_imported = 0
        chat_id = "c_local_line_scan"

        for candidate in root.rglob("*"):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() in (".edb", ".edb-wal", ".edb-shm", ".db", ".sqlite", ".ini", ".log"):
                continue
            files_inspected += 1
            if files_inspected > 500:
                break
            try:
                size = candidate.stat().st_size
                if size == 0 or size > 50 * 1024 * 1024:
                    continue
                raw = candidate.read_bytes()
                info = sniff_media_format(raw, fallback_filename=candidate.name)
                if info["format"] == "bin":
                    continue

                if not self.db.get_chat(chat_id):
                    self.db.upsert_chat(
                        chat_id=chat_id,
                        chat_name="本機 LINE 快取掃描歸檔",
                        chat_type="group",
                        monitored=True,
                        notes=f"自動掃描自 {root}",
                    )

                sha10 = info["sha256"][:10]
                msg_id = f"scan_{sha10}"
                mtime_ms = int(candidate.stat().st_mtime * 1000)
                ext = info["ext"]
                safe_name = candidate.name if candidate.name.endswith(ext) else f"{candidate.stem}{ext}"

                chat_folder = self.media_dir / chat_id
                chat_folder.mkdir(parents=True, exist_ok=True)
                dest_file = chat_folder / f"{msg_id}{ext}"
                dest_file.write_bytes(raw)

                self.db.upsert_message(
                    message_id=msg_id,
                    chat_id=chat_id,
                    sender_id="local_line",
                    sender_name="LINE 本機快取",
                    timestamp_ms=mtime_ms,
                    content_type=info["media_type"],
                    text_content=f"自本機快取永久歸檔：{safe_name}",
                    media_status="archived",
                    file_name=safe_name,
                )
                self.db.register_media(
                    media_id=f"m_{msg_id}",
                    message_id=msg_id,
                    chat_id=chat_id,
                    media_type=info["media_type"],
                    file_name=safe_name,
                    mime_type=info["mime_type"],
                    format_name=info["format"],
                    size_bytes=info["size_bytes"],
                    sha256=info["sha256"],
                    vault_rel_path=f"media/{chat_id}/{dest_file.name}",
                    source_role="original",
                )
                media_imported += 1
            except OSError:
                continue

        if media_imported > 0 and analyzer is not None:
            analyzer.analyze_chat(chat_id)

        return {
            "scanned_dir": str(root),
            "edb_databases_found": edb_files,
            "files_inspected": files_inspected,
            "media_imported": media_imported,
        }

    def sync_from_mcp_reader(
        self,
        chat_name: str | None = None,
        days: int = 14,
        analyzer=None,
        reader_script: Path | str | None = None,
        cache_root: Path | str | None = None,
        runner=None,
    ) -> dict:
        """Bridge with line-desktop-mcp encrypted .edb / WAL reader.

        Extracts chats, messages, and key materials, then uses scan_and_archive_line_cache
        to permanently save media from local LINE cache before expiration.
        """
        if reader_script is not None:
            resolved_reader = Path(reader_script).resolve()
        else:
            env_reader = os.environ.get("LINE_VAULT_READER_SCRIPT")
            if env_reader:
                resolved_reader = Path(env_reader).resolve()
            else:
                resolved_reader = Path("C:/GitHub/line-desktop-mcp/src/extensions/python/line-reader.py").resolve()

        python_exe = os.environ.get("LINE_MCP_PYTHON", sys.executable)

        if cache_root is not None:
            resolved_cache_root = Path(cache_root).resolve()
        else:
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            resolved_cache_root = (
                Path(local_appdata) / "LINE" / "Data"
                if local_appdata
                else Path("vault_data/cache")
            )

        if runner is None:
            if not resolved_reader.is_file():
                return {
                    "status": "reader_not_configured",
                    "chats_synced": 0,
                    "messages_synced": 0,
                    "media_archived": 0,
                }

            def default_runner(action: str, extra_args: list[str]) -> dict:
                cmd = [python_exe, str(resolved_reader), action, *extra_args]
                payload = {}
                if action == "recent":
                    days_val = int(extra_args[0]) if extra_args and extra_args[0].isdigit() else days
                    payload = {"action": "recent", "days": days_val}
                elif action == "messages":
                    c_name = extra_args[0] if extra_args else (chat_name or "")
                    days_val = int(extra_args[1]) if len(extra_args) > 1 and extra_args[1].isdigit() else days
                    payload = {"action": "messages", "chatName": c_name, "days": days_val}
                input_str = json.dumps(payload)
                try:
                    proc = subprocess.run(
                        cmd,
                        input=input_str,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=30,
                        check=False,
                    )
                    out = proc.stdout.strip()
                    if out:
                        return json.loads(out)
                except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
                    pass
                return {}

            exec_runner = default_runner
        else:
            exec_runner = runner

        recent_res = exec_runner("recent", [str(days)])
        all_recent: list[dict] = []
        if isinstance(recent_res, dict):
            all_recent = recent_res.get("recentChats") or recent_res.get("chats") or []
        elif isinstance(recent_res, list):
            all_recent = recent_res

        chats_to_sync: list[dict] = []
        if chat_name:
            matched = [
                c for c in all_recent
                if (c.get("chatName") or c.get("name")) == chat_name
            ]
            chats_to_sync = matched if matched else [{"chatName": chat_name, "chatType": "group"}]
        else:
            chats_to_sync = all_recent

        chats_synced_count = 0
        messages_synced_count = 0
        media_archived_count = 0
        synced_chat_ids: list[str] = []

        for ch in chats_to_sync:
            c_name = ch.get("chatName") or ch.get("name") or (chat_name if chat_name else "未命名聊天室")
            c_id = ch.get("chatId") or ch.get("id") or f"c_{hashlib.md5(c_name.encode('utf-8')).hexdigest()[:12]}"
            c_type = ch.get("chatType") or ch.get("type") or "group"
            unread = int(ch.get("unreadCount") or 0)

            self.db.upsert_chat(
                chat_id=c_id,
                chat_name=c_name,
                chat_type=c_type,
                monitored=True,
                unread_count=unread,
            )
            chats_synced_count += 1
            synced_chat_ids.append(c_id)

            msg_res = exec_runner("messages", [c_name, str(days), "--include-media-meta"])
            raw_msgs = []
            if isinstance(msg_res, dict):
                raw_msgs = msg_res.get("messages") or []
            elif isinstance(msg_res, list):
                raw_msgs = msg_res

            for msg in raw_msgs:
                msg_id = (
                    msg.get("id")
                    or msg.get("messageId")
                    or f"m_{hashlib.md5(str(msg).encode('utf-8')).hexdigest()[:12]}"
                )
                sender_name = msg.get("sender") or msg.get("senderName") or "成員"
                sender_id = msg.get("senderId") or ""
                text = msg.get("text") or msg.get("content") or ""
                c_type_msg = msg.get("type") or ("image" if msg.get("isImage") else "text")
                ts_ms = int(msg.get("timestampMs") or msg.get("timestamp") or 0)
                if ts_ms < 10000000000:
                    ts_ms *= 1000

                file_name = msg.get("fileName") or ""
                thumb_path = msg.get("thumbPath")

                key_material = msg.get("keyMaterial")
                declared_bytes = msg.get("declaredBytes")
                if not key_material and isinstance(msg.get("media"), dict):
                    media_dict = msg["media"]
                    key_material = media_dict.get("keyMaterial")
                    declared_bytes = media_dict.get("declaredBytes")
                    file_name = file_name or media_dict.get("fileName") or ""
                    thumb_path = thumb_path or media_dict.get("thumbPath")

                initial_status = "none"
                if key_material and declared_bytes:
                    initial_status = "pending"

                self.db.upsert_message(
                    message_id=msg_id,
                    chat_id=c_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    timestamp_ms=ts_ms,
                    content_type=c_type_msg,
                    text_content=text,
                    media_status=initial_status,
                    file_name=file_name,
                )
                messages_synced_count += 1

                if key_material and declared_bytes:
                    scan_res = self.scan_and_archive_line_cache(
                        chat_id=c_id,
                        message_id=msg_id,
                        cache_root=resolved_cache_root,
                        material_b64=key_material,
                        declared_bytes=int(declared_bytes),
                        fallback_filename=file_name,
                        thumb_path=thumb_path,
                    )
                    if scan_res.get("status") == "archived":
                        media_archived_count += 1

        if analyzer:
            for cid in synced_chat_ids:
                try:
                    analyzer.analyze_chat(cid)
                except (ValueError, sqlite3.Error):
                    continue

        return {
            "status": "ok",
            "chats_synced": chats_synced_count,
            "messages_synced": messages_synced_count,
            "media_archived": media_archived_count,
        }

    def seed_demo_data(self, analyzer=None) -> dict:
        """Seed realistic Traditional Chinese chat history, media files, and AI insights."""
        # 1. Create Chats
        chats = [
            {
                "chat_id": "c_proj_delivery",
                "chat_name": "專案A-客戶交付群",
                "chat_type": "group",
                "monitored": True,
                "auto_backup_media": True,
                "auto_analyze": True,
                "unread_count": 0,
                "notes": "Q4 客戶重要交付專案，本週五驗收初版",
            },
            {
                "chat_id": "c_rd_core",
                "chat_name": "產品研發核心群",
                "chat_type": "group",
                "monitored": True,
                "auto_backup_media": True,
                "auto_analyze": True,
                "unread_count": 0,
                "notes": "微服務核心演算法與發布追蹤",
            },
            {
                "chat_id": "c_vendor_wang",
                "chat_name": "王小明（供應商）",
                "chat_type": "direct",
                "monitored": True,
                "auto_backup_media": True,
                "auto_analyze": True,
                "unread_count": 1,
                "notes": "伺服器硬體報價與發票請款窗口",
            },
            {
                "chat_id": "c_family_life",
                "chat_name": "家庭生活與帳單群",
                "chat_type": "group",
                "monitored": False,
                "auto_backup_media": False,
                "auto_analyze": False,
                "unread_count": 0,
                "notes": "家庭生活日常與水電開銷",
            },
        ]

        for c in chats:
            self.db.upsert_chat(**c)

        # Base timestamp: recent days
        base_ts = 1730000000000

        # 2. Seed Messages & Media for c_proj_delivery
        key_delivery = generate_key_material()
        self.db.upsert_message(
            message_id="msg_d_01",
            chat_id="c_proj_delivery",
            sender_id="u_pm",
            sender_name="專案經理 陳雅婷",
            timestamp_ms=base_ts + 10000,
            content_type="text",
            text_content="各位同仁好，客戶要求本週五 (11/06) 17:00 前務必交付系統初版，請前端與後端同仁盡快確認進度！",
        )
        self.db.upsert_message(
            message_id="msg_d_02",
            chat_id="c_proj_delivery",
            sender_id="u_be",
            sender_name="後端工程師 林書豪",
            timestamp_ms=base_ts + 20000,
            content_type="text",
            text_content="後端 API 均已部署至測試機，相關文件已上傳至共用資料夾，目前正與前端進行串接驗證。",
        )

        # Valid 1x1 PNG bytes
        valid_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00"
            b"IEND\xaeB`\x82"
        )
        enc_png = encrypt_e2ee_media(valid_png, key_delivery)
        self.db.upsert_message(
            message_id="msg_d_03",
            chat_id="c_proj_delivery",
            sender_id="u_ui",
            sender_name="設計師 張詠欣",
            timestamp_ms=base_ts + 30000,
            content_type="image",
            text_content="交付版本的 UI 成果截圖如下，請大家確認視覺與元件佈局。",
            media_status="archived",
            file_name="delivery_ui_preview.png",
        )
        self.archive_encrypted_bytes(
            message_id="msg_d_03",
            chat_id="c_proj_delivery",
            encrypted_data=enc_png,
            material_b64=key_delivery,
            fallback_filename="delivery_ui_preview.png",
        )

        # Valid PDF bytes
        valid_pdf = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n"
            b"0000000117 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n"
        )
        enc_pdf = encrypt_e2ee_media(valid_pdf, key_delivery)
        self.db.upsert_message(
            message_id="msg_d_04",
            chat_id="c_proj_delivery",
            sender_id="u_client",
            sender_name="客戶代表 許總監",
            timestamp_ms=base_ts + 40000,
            content_type="file",
            text_content="收到截圖！請記得將正式報價單（含稅 NT$ 180,000）與簽署合約一併附在交付檔案中，謝謝。",
            media_status="archived",
            file_name="正式報價合約_Q4.pdf",
        )
        self.archive_encrypted_bytes(
            message_id="msg_d_04",
            chat_id="c_proj_delivery",
            encrypted_data=enc_pdf,
            material_b64=key_delivery,
            fallback_filename="正式報價合約_Q4.pdf",
        )

        self.db.upsert_message(
            message_id="msg_d_05",
            chat_id="c_proj_delivery",
            sender_id="u_pm",
            sender_name="專案經理 陳雅婷",
            timestamp_ms=base_ts + 50000,
            content_type="text",
            text_content="好的許總監，合約與報價單已經備齊，請技術團隊同仁於今天下班前完成最後驗收測試並回報！",
        )

        # 3. Seed Messages & Media for c_rd_core
        key_rd = generate_key_material()
        # Valid MP4 header container bytes
        valid_mp4 = (
            b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
            b"\x00\x00\x00\x08free\x00\x00\x00\x10mdat\x00\x01\x02\x03\x04\x05\x06\x07"
        )
        enc_mp4 = encrypt_e2ee_media(valid_mp4, key_rd)
        self.db.upsert_message(
            message_id="msg_rd_01",
            chat_id="c_rd_core",
            sender_id="u_arch",
            sender_name="架構師 王大為",
            timestamp_ms=base_ts + 60000,
            content_type="video",
            text_content="我們的新版本微服務已經通過高併發壓力測試，完整效能示範錄影在此。",
            media_status="archived",
            file_name="stress_test_demo.mp4",
        )
        self.archive_encrypted_bytes(
            message_id="msg_rd_01",
            chat_id="c_rd_core",
            encrypted_data=enc_mp4,
            material_b64=key_rd,
            fallback_filename="stress_test_demo.mp4",
        )

        # Valid ZIP bytes
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("deploy.sh", "#!/bin/bash\necho 'Deploying microservices...'\n")
            zf.writestr("release_notes.txt", "Version 2.4.0 Release Build\n")
        valid_zip = zip_buf.getvalue()
        enc_zip = encrypt_e2ee_media(valid_zip, key_rd)

        self.db.upsert_message(
            message_id="msg_rd_02",
            chat_id="c_rd_core",
            sender_id="u_qa",
            sender_name="測試經理 鄭惠芬",
            timestamp_ms=base_ts + 70000,
            content_type="text",
            text_content="請問預計何時可以出正式測試報告？另外完整部署壓縮包是否已打包完成？",
        )
        self.db.upsert_message(
            message_id="msg_rd_03",
            chat_id="c_rd_core",
            sender_id="u_arch",
            sender_name="架構師 王大為",
            timestamp_ms=base_ts + 80000,
            content_type="file",
            text_content="打包好的發布包在此，請測試團隊下載驗收。",
            media_status="archived",
            file_name="release_v2.4.0_bundle.zip",
        )
        self.archive_encrypted_bytes(
            message_id="msg_rd_03",
            chat_id="c_rd_core",
            encrypted_data=enc_zip,
            material_b64=key_rd,
            fallback_filename="release_v2.4.0_bundle.zip",
        )
        self.db.upsert_message(
            message_id="msg_rd_04",
            chat_id="c_rd_core",
            sender_id="u_qa",
            sender_name="測試經理 鄭惠芬",
            timestamp_ms=base_ts + 90000,
            content_type="text",
            text_content="收到發布包，馬上進行安裝測試，預計明天中午前反饋測試結果！",
        )

        # 4. Seed Messages for c_vendor_wang
        self.db.upsert_message(
            message_id="msg_w_01",
            chat_id="c_vendor_wang",
            sender_id="u_wang",
            sender_name="王小明",
            timestamp_ms=base_ts + 100000,
            content_type="text",
            text_content="您好！本季度的伺服器零件採購報價已更新，總額為 NT$ 65,000 元，發票將於下週一開立，請問這批零件數量能否在今天下班前確認？",
        )
        self.db.upsert_message(
            message_id="msg_w_02",
            chat_id="c_vendor_wang",
            sender_id="u_me",
            sender_name="我",
            timestamp_ms=base_ts + 110000,
            content_type="text",
            text_content="好的小明，我先與採購部核對數量後馬上回覆您。",
        )
        self.db.upsert_message(
            message_id="msg_w_03",
            chat_id="c_vendor_wang",
            sender_id="u_wang",
            sender_name="王小明",
            timestamp_ms=base_ts + 120000,
            content_type="text",
            text_content="麻煩您了，如果需要調整規格清單請隨時告知，感謝配合！",
        )

        # 5. Seed Messages for c_family_life
        self.db.upsert_message(
            message_id="msg_fam_01",
            chat_id="c_family_life",
            sender_id="u_mom",
            sender_name="媽媽",
            timestamp_ms=base_ts + 130000,
            content_type="text",
            text_content="本月的水電瓦斯費帳單已經寄到囉，總共 3,450 元，請記得這週末前去繳納～",
        )
        self.db.upsert_message(
            message_id="msg_fam_02",
            chat_id="c_family_life",
            sender_id="u_dad",
            sender_name="爸爸",
            timestamp_ms=base_ts + 140000,
            content_type="text",
            text_content="收到，我星期六去超商繳！",
        )
        self.db.upsert_message(
            message_id="msg_fam_03",
            chat_id="c_family_life",
            sender_id="u_sis",
            sender_name="妹妹",
            timestamp_ms=base_ts + 150000,
            content_type="text",
            text_content="週末大家要不要一起吃火鍋慶祝？",
        )

        # 6. Run AI Analysis if analyzer provided
        analyzed_count = 0
        if analyzer:
            for cid in ["c_proj_delivery", "c_rd_core", "c_vendor_wang"]:
                analyzer.analyze_chat(cid)
                analyzed_count += 1

        return {
            "chats_seeded": len(chats),
            "media_seeded": 4,
            "monitored_analyzed": analyzed_count,
        }
