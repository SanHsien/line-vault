"""Comprehensive test suite for LINE Vault: crypto, db, archiver, analyzer, and server."""

import base64
import hashlib
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from line_vault.analyzer import ChatAnalyzer
from line_vault.archiver import MediaArchiver
from line_vault.cli import find_system_app_browser
from line_vault.crypto import (
    decrypt_e2ee_media,
    derive_media_keys,
    encrypt_e2ee_media,
    generate_key_material,
    sniff_media_format,
)
from line_vault.db import VaultDB
from line_vault.server import create_server


# ============================================================================
# 1. Crypto Tests
# ============================================================================
def test_derive_media_keys_success():
    """Verify derivation of 32-byte enc_key, 32-byte mac_key, and 16-byte CTR IV."""
    raw_key = b"\x42" * 32
    key_b64 = base64.b64encode(raw_key).decode("ascii")

    enc_key, mac_key, iv = derive_media_keys(key_b64)

    assert len(enc_key) == 32
    assert len(mac_key) == 32
    assert len(iv) == 16
    # Last 4 bytes of IV must be null bytes
    assert iv.endswith(b"\x00\x00\x00\x00")
    # Repeated derivation must be deterministic
    enc2, mac2, iv2 = derive_media_keys(key_b64)
    assert enc_key == enc2
    assert mac_key == mac2
    assert iv == iv2


def test_derive_media_keys_invalid_inputs():
    """Verify invalid base64 or invalid length raises ValueError('MEDIA_KEY_UNAVAILABLE')."""
    with pytest.raises(ValueError, match="MEDIA_KEY_UNAVAILABLE"):
        derive_media_keys("")

    with pytest.raises(ValueError, match="MEDIA_KEY_UNAVAILABLE"):
        derive_media_keys("not-valid-base64!@#$")

    # 16 bytes instead of 32
    short_b64 = base64.b64encode(b"short16byteshere").decode("ascii")
    with pytest.raises(ValueError, match="MEDIA_KEY_UNAVAILABLE"):
        derive_media_keys(short_b64)


def test_encrypt_decrypt_roundtrip():
    """Verify AES-256-CTR + HMAC-SHA256 encryption and decryption roundtrip."""
    key = generate_key_material()
    payload = b"Hello, Windows 11 LINE Vault E2EE Media Decryption Test!"

    encrypted = encrypt_e2ee_media(payload, key)
    # Ciphertext + 32-byte HMAC tag
    assert len(encrypted) == len(payload) + 32

    decrypted = decrypt_e2ee_media(encrypted, key)
    assert decrypted == payload


def test_decrypt_tampered_ciphertext():
    """Corrupted ciphertext must fail HMAC validation."""
    key = generate_key_material()
    payload = b"Secret Financial Report 2026"
    encrypted = bytearray(encrypt_e2ee_media(payload, key))

    # Tamper with first byte of ciphertext
    encrypted[0] ^= 0xFF

    with pytest.raises(ValueError, match="MEDIA_AUTHENTICATION_FAILED"):
        decrypt_e2ee_media(bytes(encrypted), key)


def test_decrypt_tampered_tag():
    """Corrupted HMAC tag must fail validation."""
    key = generate_key_material()
    payload = b"Secret Photo File"
    encrypted = bytearray(encrypt_e2ee_media(payload, key))

    # Tamper with the last byte (part of tag)
    encrypted[-1] ^= 0xFF

    with pytest.raises(ValueError, match="MEDIA_AUTHENTICATION_FAILED"):
        decrypt_e2ee_media(bytes(encrypted), key)


def test_decrypt_too_short():
    """Payloads shorter than 33 bytes cannot contain ciphertext + tag."""
    key = generate_key_material()
    with pytest.raises(ValueError, match="MEDIA_KEY_UNAVAILABLE"):
        decrypt_e2ee_media(b"short", key)


def test_sniff_media_format():
    """Verify detection of various binary formats via magic bytes."""
    # PNG
    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    info_png = sniff_media_format(png_data)
    assert info_png["media_type"] == "image"
    assert info_png["format"] == "png"
    assert info_png["ext"] == ".png"

    # JPEG
    jpeg_data = b"\xff\xd8\xff\xe0" + b"\x00" * 20
    info_jpeg = sniff_media_format(jpeg_data)
    assert info_jpeg["media_type"] == "image"
    assert info_jpeg["format"] == "jpeg"
    assert info_jpeg["ext"] == ".jpg"

    # GIF
    gif_data = b"GIF89a" + b"\x00" * 20
    info_gif = sniff_media_format(gif_data)
    assert info_gif["media_type"] == "image"
    assert info_gif["format"] == "gif"

    # WEBP
    webp_data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 10
    info_webp = sniff_media_format(webp_data)
    assert info_webp["media_type"] == "image"
    assert info_webp["format"] == "webp"

    # MP4
    mp4_data = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 20
    info_mp4 = sniff_media_format(mp4_data)
    assert info_mp4["media_type"] == "video"
    assert info_mp4["format"] == "mp4"

    # MP3
    mp3_data = b"ID3\x03\x00\x00" + b"\x00" * 20
    info_mp3 = sniff_media_format(mp3_data)
    assert info_mp3["media_type"] == "audio"
    assert info_mp3["format"] == "mp3"

    # WAV
    wav_data = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 20
    info_wav = sniff_media_format(wav_data)
    assert info_wav["media_type"] == "audio"
    assert info_wav["format"] == "wav"

    # OGG
    ogg_data = b"OggS\x00" + b"\x00" * 20
    info_ogg = sniff_media_format(ogg_data)
    assert info_ogg["media_type"] == "audio"
    assert info_ogg["format"] == "ogg"

    # PDF
    pdf_data = b"%PDF-1.4\n..."
    info_pdf = sniff_media_format(pdf_data)
    assert info_pdf["media_type"] == "file"
    assert info_pdf["format"] == "pdf"

    # ZIP
    zip_data = b"PK\x03\x04\x00"
    info_zip = sniff_media_format(zip_data)
    assert info_zip["media_type"] == "file"
    assert info_zip["format"] == "zip"

    # Fallback with filename
    generic_data = b"hello plain text"
    info_fallback = sniff_media_format(generic_data, fallback_filename="notes.txt")
    assert info_fallback["format"] == "txt"
    assert info_fallback["ext"] == ".txt"


# ============================================================================
# 2. Database Tests
# ============================================================================
def test_vault_db_operations(tmp_path: Path):
    """Test full CRUD operations on VaultDB."""
    db_file = tmp_path / "test_vault.db"
    db = VaultDB(db_file)

    # 1. Upsert and list chats
    db.upsert_chat(
        chat_id="chat_1",
        chat_name="客戶交付專案群",
        chat_type="group",
        monitored=True,
        notes="重要客戶",
    )
    db.upsert_chat(
        chat_id="chat_2",
        chat_name="家庭生活群",
        chat_type="group",
        monitored=False,
    )

    c1 = db.get_chat("chat_1")
    assert c1 is not None
    assert c1["chat_name"] == "客戶交付專案群"
    assert c1["monitored"] is True

    monitored_list = db.list_chats(only_monitored=True)
    assert len(monitored_list) == 1
    assert monitored_list[0]["chat_id"] == "chat_1"

    # Toggle monitoring
    db.set_chat_monitoring("chat_2", monitored=True)
    c2 = db.get_chat("chat_2")
    assert c2["monitored"] is True

    # 2. Messages and FTS5 search
    db.upsert_message(
        message_id="m1",
        chat_id="chat_1",
        sender_id="u1",
        sender_name="專案經理",
        timestamp_ms=1730001000000,
        content_type="text",
        text_content="請於本週五前確認報價單明細，總金額為 NT$ 120,000 元。",
    )
    db.upsert_message(
        message_id="m2",
        chat_id="chat_1",
        sender_id="u2",
        sender_name="工程師",
        timestamp_ms=1730002000000,
        content_type="image",
        text_content="測試截圖如下",
        media_status="pending",
        file_name="screenshot.png",
    )

    # Search by keyword
    results = db.search_messages(query="報價單")
    assert len(results) == 1
    assert results[0]["message_id"] == "m1"

    # Search by sender
    results_sender = db.search_messages(query="工程師")
    assert len(results_sender) == 1
    assert results_sender[0]["message_id"] == "m2"

    # 3. Media registration and joining
    db.register_media(
        media_id="media_001",
        message_id="m2",
        chat_id="chat_1",
        media_type="image",
        file_name="screenshot.png",
        mime_type="image/png",
        format_name="png",
        size_bytes=4096,
        sha256="abc1234567890",
        vault_rel_path="media/chat_1/m2_abc1234567.png",
    )

    # Message search must join media record
    m2_joined = db.search_messages(chat_id="chat_1", content_type="image")
    assert len(m2_joined) == 1
    assert m2_joined[0]["media_id"] == "media_001"
    assert m2_joined[0]["media_status"] == "archived"
    assert m2_joined[0]["media_size_bytes"] == 4096

    # 4. Insights
    db.save_insight(
        chat_id="chat_1",
        summary="討論報價與截圖驗收",
        action_items=[{"title": "確認報價", "priority": "high"}],
        suggested_replies=[{"label": "收到", "tone": "專業", "text": "好的，已確認！"}],
        important_files=[],
        urgency="high",
    )
    insight = db.get_latest_insight("chat_1")
    assert insight is not None
    assert insight["urgency"] == "high"
    assert len(insight["action_items"]) == 1

    # 5. Dashboard stats
    stats = db.get_dashboard_stats()
    assert stats["total_chats"] == 2
    assert stats["monitored_chats"] == 2
    assert stats["total_messages"] == 2
    assert stats["archived_media_count"] == 1
    assert stats["total_media_bytes"] == 4096

    db.close()


# ============================================================================
# 3. Archiver & Cache Scanning Tests
# ============================================================================
def test_archiver_archive_encrypted_bytes(tmp_path: Path):
    """Test decrypting and archiving an encrypted payload into the vault directory."""
    vault_dir = tmp_path / "vault"
    db = VaultDB(vault_dir / "vault.db")
    archiver = MediaArchiver(vault_dir, db)

    db.upsert_chat(chat_id="chat_test", chat_name="測試聊天室")
    db.upsert_message(
        message_id="msg_test_01",
        chat_id="chat_test",
        content_type="file",
        file_name="test_doc.pdf",
    )

    pdf_bytes = b"%PDF-1.4 sample pdf content for line vault test"
    key = generate_key_material()
    enc_bytes = encrypt_e2ee_media(pdf_bytes, key)

    record = archiver.archive_encrypted_bytes(
        message_id="msg_test_01",
        chat_id="chat_test",
        encrypted_data=enc_bytes,
        material_b64=key,
        fallback_filename="test_doc.pdf",
    )

    assert record["media_id"].startswith("m_msg_test_01")
    assert record["media_type"] == "file"
    assert record["format_name"] == "pdf"
    assert record["size_bytes"] == len(pdf_bytes)

    # Check physical file on disk
    saved_file = vault_dir / record["vault_rel_path"]
    assert saved_file.exists()
    assert saved_file.read_bytes() == pdf_bytes

    # Check database status updated
    msg = db.search_messages(chat_id="chat_test")[0]
    assert msg["media_status"] == "archived"

    db.close()


def test_archiver_scan_line_cache(tmp_path: Path):
    """Simulate LINE cache directory structure and verify candidate file matching."""
    vault_dir = tmp_path / "vault"
    cache_root = tmp_path / "line_cache"
    db = VaultDB(vault_dir / "vault.db")
    archiver = MediaArchiver(vault_dir, db)

    chat_id = "c_alpha"
    msg_id = "m_100"
    db.upsert_chat(chat_id=chat_id, chat_name="Alpha")
    db.upsert_message(message_id=msg_id, chat_id=chat_id, content_type="image")

    # Plaintext photo
    photo_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    key = generate_key_material()
    enc_photo = encrypt_e2ee_media(photo_bytes, key)

    # Build simulated LINE 26.x cache directory
    chat_hash = hashlib.sha1(chat_id.encode("utf-8")).hexdigest()
    m_dir = cache_root / "u_account_1" / chat_hash / "m"
    m_dir.mkdir(parents=True, exist_ok=True)

    cache_file = m_dir / "cached_payload.dat"
    with open(cache_file, "wb") as f:
        f.write(enc_photo)

    # 1. Scan and find original
    res = archiver.scan_and_archive_line_cache(
        chat_id=chat_id,
        message_id=msg_id,
        cache_root=cache_root,
        material_b64=key,
        declared_bytes=len(photo_bytes),
        fallback_filename="photo.png",
    )
    assert res["status"] == "archived"
    assert res["media"]["size_bytes"] == len(photo_bytes)

    # 2. Thumbnail fallback test when original does not match
    thumb_path = tmp_path / "thumb.jpg"
    with open(thumb_path, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 30)

    res_thumb = archiver.scan_and_archive_line_cache(
        chat_id="c_other",
        message_id="m_200",
        cache_root=cache_root,
        material_b64=key,
        declared_bytes=99999,  # Non-matching size
        fallback_filename="preview.jpg",
        thumb_path=thumb_path,
    )
    assert res_thumb["status"] == "cached_pending"
    assert res_thumb["pending_original"] is True

    db.close()


def test_archiver_sync_from_mcp_reader(tmp_path: Path):
    """Verify bridge synchronization from line-desktop-mcp reader with cache archiving."""
    vault_dir = tmp_path / "vault_mcp"
    cache_root = tmp_path / "line_cache"
    db = VaultDB(vault_dir / "vault.db")
    archiver = MediaArchiver(vault_dir, db)
    analyzer = ChatAnalyzer(db)

    chat_id = "c_mcp_test"
    chat_name = "MCP專案協作群"
    photo_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
    key = generate_key_material()
    enc_photo = encrypt_e2ee_media(photo_bytes, key)

    # Place encrypted payload in cache
    chat_hash = hashlib.sha1(chat_id.encode("utf-8")).hexdigest()
    m_dir = cache_root / "bucket_1" / chat_hash / "m"
    m_dir.mkdir(parents=True, exist_ok=True)
    with open(m_dir / "photo.dat", "wb") as f:
        f.write(enc_photo)

    def mock_runner(action: str, extra_args: list[str]) -> dict:
        if action == "recent":
            return {
                "recentChats": [
                    {
                        "chatId": chat_id,
                        "chatName": chat_name,
                        "chatType": "group",
                        "unreadCount": 1,
                    }
                ]
            }
        if action == "messages":
            return {
                "messages": [
                    {
                        "id": "msg_mcp_01",
                        "sender": "客戶代表",
                        "text": "請於本週五前確認報價單，金額為 NT$ 88,000 元。",
                        "type": "image",
                        "timestampMs": 1730008000000,
                        "fileName": "quote_spec.png",
                        "keyMaterial": key,
                        "declaredBytes": len(photo_bytes),
                    }
                ]
            }
        return {}

    sync_result = archiver.sync_from_mcp_reader(
        chat_name=chat_name,
        days=14,
        analyzer=analyzer,
        cache_root=cache_root,
        runner=mock_runner,
    )

    assert sync_result["status"] == "ok"
    assert sync_result["chats_synced"] == 1
    assert sync_result["messages_synced"] == 1
    assert sync_result["media_archived"] == 1

    # Verify chat was created & monitored
    chat = db.get_chat(chat_id)
    assert chat is not None
    assert chat["monitored"] is True

    # Verify media was decrypted and saved to vault
    saved_media = db.list_media(chat_id=chat_id)
    assert len(saved_media) == 1
    assert saved_media[0]["size_bytes"] == len(photo_bytes)
    assert (vault_dir / saved_media[0]["vault_rel_path"]).read_bytes() == photo_bytes

    # Verify AI insight was generated
    insight = db.get_latest_insight(chat_id)
    assert insight is not None
    assert len(insight["action_items"]) >= 1

    db.close()


def test_archiver_seed_demo_data(tmp_path: Path):
    """Verify demo data seeding creates chats, messages, and encrypted attachments."""
    vault_dir = tmp_path / "vault_demo"
    db = VaultDB(vault_dir / "vault.db")
    archiver = MediaArchiver(vault_dir, db)
    analyzer = ChatAnalyzer(db)

    result = archiver.seed_demo_data(analyzer=analyzer)
    assert result["chats_seeded"] == 4
    assert result["media_seeded"] == 4
    assert result["monitored_analyzed"] == 3

    stats = db.get_dashboard_stats()
    assert stats["total_chats"] == 4
    assert stats["monitored_chats"] == 3
    assert stats["total_messages"] >= 10
    assert stats["archived_media_count"] == 4

    # Verify seeded media files physically exist in vault
    media_list = db.list_media()
    assert len(media_list) == 4
    for m in media_list:
        file_path = vault_dir / m["vault_rel_path"]
        assert file_path.exists()
        assert file_path.stat().st_size > 0

    db.close()


# ============================================================================
# 4. Analyzer Tests
# ============================================================================
def test_analyzer_action_items_and_replies(tmp_path: Path):
    """Verify AI extraction of action items, deadlines, quotes, and suggested replies."""
    vault_dir = tmp_path / "vault_ai"
    db = VaultDB(vault_dir / "vault.db")
    analyzer = ChatAnalyzer(db)

    chat_id = "c_project"
    db.upsert_chat(chat_id=chat_id, chat_name="軟體交付專案群", monitored=True)

    # 1. Message with deadline and urgency
    db.upsert_message(
        message_id="msg_01",
        chat_id=chat_id,
        sender_name="專案經理 陳雅婷",
        timestamp_ms=1000,
        content_type="text",
        text_content="各位同仁好，客戶要求本週五前務必交付初版，請大家盡快確認！",
    )
    # 2. Message with finance quote
    db.upsert_message(
        message_id="msg_02",
        chat_id=chat_id,
        sender_name="客戶代表 許總監",
        timestamp_ms=2000,
        content_type="text",
        text_content="請記得將正式報價單（含稅 NT$ 180,000）與發票開立明細附上，謝謝。",
    )
    # 3. Message with question
    db.upsert_message(
        message_id="msg_03",
        chat_id=chat_id,
        sender_name="測試經理",
        timestamp_ms=3000,
        content_type="text",
        text_content="請問這批微服務部署包何時可以進行正式驗收？",
    )

    insight = analyzer.analyze_chat(chat_id)
    assert insight is not None
    assert insight["urgency"] in ("high", "medium")
    assert "陳雅婷" in insight["summary"]

    actions = insight["action_items"]
    assert len(actions) >= 3

    # Check categories
    categories = [a["category"] for a in actions]
    assert "deadline" in categories
    assert "finance" in categories
    assert "question" in categories

    # Check suggested replies
    replies = insight["suggested_replies"]
    assert len(replies) == 3
    for r in replies:
        assert "label" in r
        assert "tone" in r
        assert len(r["text"]) > 5

    db.close()


# ============================================================================
# 5. REST API & Web Server Tests
# ============================================================================
def test_server_rest_api_endpoints(tmp_path: Path):
    """Test full HTTP REST API endpoints using standard urllib against a test server."""
    vault_dir = tmp_path / "vault_srv"
    server = create_server(vault_dir=vault_dir, host="127.0.0.1", port=0)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"

    srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
    srv_thread.start()

    try:
        # 1. GET / (Static index.html)
        with urllib.request.urlopen(f"{base_url}/") as res:
            assert res.status == 200
            html = res.read().decode("utf-8")
            assert "LINE Vault" in html
            assert "styles.css" in html

        # 2. GET /styles.css
        with urllib.request.urlopen(f"{base_url}/styles.css") as res:
            assert res.status == 200
            css = res.read().decode("utf-8")
            assert "--bg-main" in css

        # 3. GET /app.js
        with urllib.request.urlopen(f"{base_url}/app.js") as res:
            assert res.status == 200
            js = res.read().decode("utf-8")
            assert "DOMContentLoaded" in js

        # 4. GET /api/status
        with urllib.request.urlopen(f"{base_url}/api/status") as res:
            assert res.status == 200
            status_data = json.loads(res.read().decode("utf-8"))
            assert status_data["status"] == "online"
            assert "stats" in status_data

        # 5. POST /api/demo/seed
        req_seed = urllib.request.Request(f"{base_url}/api/demo/seed", data=b"{}", method="POST")
        with urllib.request.urlopen(req_seed) as res:
            assert res.status == 200
            seed_data = json.loads(res.read().decode("utf-8"))
            assert seed_data["success"] is True
            assert seed_data["stats"]["total_chats"] == 4

        # 6. GET /api/chats
        with urllib.request.urlopen(f"{base_url}/api/chats") as res:
            assert res.status == 200
            chats = json.loads(res.read().decode("utf-8"))
            assert len(chats) == 4

        # 7. POST /api/chats/<chat_id>/monitor
        req_monitor = urllib.request.Request(
            f"{base_url}/api/chats/c_family_life/monitor",
            data=json.dumps({"monitored": True, "auto_backup_media": True, "auto_analyze": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_monitor) as res:
            assert res.status == 200
            updated = json.loads(res.read().decode("utf-8"))
            assert updated["monitored"] is True

        # 8. GET /api/messages
        with urllib.request.urlopen(f"{base_url}/api/messages?chat_id=c_proj_delivery") as res:
            assert res.status == 200
            msgs = json.loads(res.read().decode("utf-8"))
            assert len(msgs) >= 4

        # 9. GET /api/media
        with urllib.request.urlopen(f"{base_url}/api/media") as res:
            assert res.status == 200
            media_items = json.loads(res.read().decode("utf-8"))
            assert len(media_items) == 4
            first_media_id = media_items[0]["media_id"]

        # 10. GET /api/media/file/<media_id>
        with urllib.request.urlopen(f"{base_url}/api/media/file/{first_media_id}") as res:
            assert res.status == 200
            content = res.read()
            assert len(content) > 0

        # 11. GET /api/insights/<chat_id>
        with urllib.request.urlopen(f"{base_url}/api/insights/c_proj_delivery") as res:
            assert res.status == 200
            ins = json.loads(res.read().decode("utf-8"))
            assert len(ins["action_items"]) > 0

        # 12. POST /api/analyze-all
        req_analyze_all = urllib.request.Request(
            f"{base_url}/api/analyze-all",
            data=b"{}",
            method="POST",
        )
        with urllib.request.urlopen(req_analyze_all) as res:
            assert res.status == 200
            all_res = json.loads(res.read().decode("utf-8"))
            assert all_res["analyzed_count"] >= 3

        # 13. POST /api/scan-line with custom simulated directory
        sim_line_dir = tmp_path / "sim_line_data"
        sim_line_dir.mkdir(parents=True, exist_ok=True)
        (sim_line_dir / "chat.edb").write_bytes(b"encrypted_db_header")
        (sim_line_dir / "cached_img.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        req_scan = urllib.request.Request(
            f"{base_url}/api/scan-line",
            data=json.dumps({"cache_dir": str(sim_line_dir)}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_scan) as res:
            assert res.status == 200
            scan_payload = json.loads(res.read().decode("utf-8"))
            assert scan_payload["success"] is True
            assert scan_payload["scan_result"]["media_imported"] == 1
            assert "chat.edb" in scan_payload["scan_result"]["edb_databases_found"]

        # 14. POST /api/sync-mcp endpoint check
        req_sync = urllib.request.Request(
            f"{base_url}/api/sync-mcp",
            data=json.dumps({"days": 7, "cache_dir": str(sim_line_dir)}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_sync) as res:
            assert res.status == 200
            sync_data = json.loads(res.read().decode("utf-8"))
            assert sync_data["success"] is True
            assert "sync_result" in sync_data

        # 15. Path traversal protection test
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{base_url}/api/media/file/../../../../etc/passwd")
        assert exc_info.value.code in (403, 404)

    finally:
        server.shutdown()
        server.server_close()


def test_gitignore_safety_contract():
    """Verify .gitignore explicitly blocks local vault data, .edb, .key, and .env files."""
    repo_root = Path(__file__).resolve().parent.parent
    gitignore_path = repo_root / ".gitignore"
    assert gitignore_path.is_file()
    content = gitignore_path.read_text(encoding="utf-8")
    for pattern in ("vault_data/", "line-vault/", "*.edb", "*.key", ".env"):
        assert pattern in content


def test_find_system_app_browser():
    """Verify system app browser search behaves safely on Windows and non-Windows."""
    result = find_system_app_browser()
    assert result is None or (isinstance(result, str) and len(result) > 0)


# ============================================================================
# 6. LV-03 Milestones 3-5 & CodeQL Security Tests
# ============================================================================

def test_bilingual_ai_analyzer(tmp_path: Path):
    """Verify bilingual AI analyzer produces valid Traditional Chinese and English outputs."""
    db = VaultDB(tmp_path / "test.db")
    archiver = MediaArchiver(tmp_path, db)
    analyzer = ChatAnalyzer(db)

    # Seed demo chats
    archiver.seed_demo_data()

    # 1. Analyze in Traditional Chinese (default)
    ins_zh = analyzer.analyze_chat("c_proj_delivery", lang="zh-TW")
    assert "累計" in ins_zh["summary"]
    assert "對話" in ins_zh["summary"]
    assert len(ins_zh["action_items"]) > 0
    assert any(item["priority"] in ("high", "medium", "low") for item in ins_zh["action_items"])
    assert len(ins_zh["suggested_replies"]) > 0

    # 2. Analyze in English
    ins_en = analyzer.analyze_chat("c_proj_delivery", lang="en")
    assert "Chat" in ins_en["summary"]
    assert "accumulated" in ins_en["summary"]
    assert len(ins_en["action_items"]) > 0
    assert any("Securely preserved" in f["action_advice"] or "Thumbnail" in f["action_advice"] for f in ins_en["important_files"])
    assert any("tone" in r for r in ins_en["suggested_replies"])

    # 3. Empty chat analysis
    db.upsert_chat("c_empty", "Empty Channel")
    empty_zh = analyzer.analyze_chat("c_empty", lang="zh-TW")
    assert "尚無對話紀錄" in empty_zh["summary"]

    empty_en = analyzer.analyze_chat("c_empty", lang="en")
    assert "currently has no message history" in empty_en["summary"]


def test_message_bookmarks_unit_and_api(tmp_path: Path):
    """Verify message bookmarks toggle, database filter, and REST API endpoint."""
    db = VaultDB(tmp_path / "test.db")
    db.upsert_chat("c_test_bm", "Bookmark Test Chat")
    db.upsert_message(
        message_id="msg_bm_01",
        chat_id="c_test_bm",
        sender_id="u_alice",
        sender_name="Alice",
        timestamp_ms=1700000000000,
        content_type="text",
        text_content="Important account credentials and passwords",
        bookmarked=False,
    )
    db.upsert_message(
        message_id="msg_bm_02",
        chat_id="c_test_bm",
        sender_id="u_bob",
        sender_name="Bob",
        timestamp_ms=1700000001000,
        content_type="text",
        text_content="Casual lunch chatter",
        bookmarked=False,
    )

    # Initial state: no bookmarks
    bookmarked_msgs = db.search_messages(chat_id="c_test_bm", only_bookmarked=True)
    assert len(bookmarked_msgs) == 0

    # Toggle bookmark on
    toggled = db.toggle_message_bookmark("msg_bm_01")
    assert toggled is not None
    assert toggled["bookmarked"] is True

    # Check search with only_bookmarked=True
    bookmarked_msgs = db.search_messages(chat_id="c_test_bm", only_bookmarked=True)
    assert len(bookmarked_msgs) == 1
    assert bookmarked_msgs[0]["message_id"] == "msg_bm_01"
    assert bookmarked_msgs[0]["bookmarked"] is True

    # Toggle off
    toggled_off = db.toggle_message_bookmark("msg_bm_01", bookmarked=False)
    assert toggled_off["bookmarked"] is False
    assert len(db.search_messages(chat_id="c_test_bm", only_bookmarked=True)) == 0

    # Start test server for API endpoint test
    server = create_server(vault_dir=tmp_path / "vault", host="127.0.0.1", port=0)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()

    try:
        req_seed = urllib.request.Request(f"{base_url}/api/demo/seed", data=b"{}", method="POST")
        with urllib.request.urlopen(req_seed) as res:
            assert res.status == 200

        req_bm = urllib.request.Request(
            f"{base_url}/api/messages/msg_d_01/bookmark",
            data=json.dumps({"bookmarked": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_bm) as res:
            assert res.status == 200
            bm_data = json.loads(res.read().decode("utf-8"))
            assert bm_data["bookmarked"] is True

        with urllib.request.urlopen(f"{base_url}/api/messages?bookmarked=1") as res:
            assert res.status == 200
            bm_list = json.loads(res.read().decode("utf-8"))
            assert any(m["message_id"] == "msg_d_01" for m in bm_list)

    finally:
        server.shutdown()
        server.server_close()


def test_action_item_check_off_and_kpi_impact(tmp_path: Path):
    """Verify action item status check-off and dynamic dashboard KPI pending calculation."""
    db = VaultDB(tmp_path / "test.db")
    archiver = MediaArchiver(tmp_path, db)
    analyzer = ChatAnalyzer(db)
    archiver.seed_demo_data(analyzer=analyzer)

    stats_before = db.get_dashboard_stats()
    action_items_before = stats_before["action_items_count"]
    assert action_items_before > 0

    ins = db.get_latest_insight("c_proj_delivery")
    assert ins is not None
    assert len(ins["action_items"]) > 0

    updated_ins = db.update_action_item_status("c_proj_delivery", action_index=0, done=True)
    assert updated_ins is not None
    assert updated_ins["action_items"][0]["done"] is True

    stats_after = db.get_dashboard_stats()
    assert stats_after["action_items_count"] == action_items_before - 1

    unmarked_ins = db.update_action_item_status("c_proj_delivery", action_index=0, done=False)
    assert unmarked_ins["action_items"][0]["done"] is False
    stats_restored = db.get_dashboard_stats()
    assert stats_restored["action_items_count"] == action_items_before


def test_chat_report_export_markdown_and_json(tmp_path: Path):
    """Verify chat and AI report export in Markdown and JSON formats."""
    db = VaultDB(tmp_path / "test.db")
    archiver = MediaArchiver(tmp_path, db)
    analyzer = ChatAnalyzer(db)
    archiver.seed_demo_data(analyzer=analyzer)

    fname_md, mime_md, content_md = archiver.export_chat_report("c_proj_delivery", fmt="markdown")
    assert fname_md.endswith(".md")
    assert "text/markdown" in mime_md
    assert "# LINE Vault 對話與智能分析報告" in content_md
    assert "## 1. AI 執行摘要" in content_md
    assert "## 2. 待辦事項清單" in content_md
    assert "## 3. 關鍵流通檔案健康度" in content_md
    assert "## 5. 最近對話紀錄" in content_md

    fname_json, mime_json, content_json = archiver.export_chat_report("c_proj_delivery", fmt="json")
    assert fname_json.endswith(".json")
    assert mime_json == "application/json"
    parsed = json.loads(content_json)
    assert parsed["chat"]["chat_id"] == "c_proj_delivery"
    assert "insight" in parsed
    assert "messages" in parsed
    assert len(parsed["messages"]) > 0

    server = create_server(vault_dir=tmp_path / "vault", host="127.0.0.1", port=0)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()

    try:
        req_seed = urllib.request.Request(f"{base_url}/api/demo/seed", data=b"{}", method="POST")
        with urllib.request.urlopen(req_seed) as res:
            assert res.status == 200

        with urllib.request.urlopen(f"{base_url}/api/export/c_proj_delivery?fmt=markdown") as res:
            assert res.status == 200
            assert "text/markdown" in res.headers.get("Content-Type", "")
            md_text = res.read().decode("utf-8")
            assert "LINE Vault" in md_text

        with urllib.request.urlopen(f"{base_url}/api/export/c_proj_delivery?fmt=json") as res:
            assert res.status == 200
            assert "application/json" in res.headers.get("Content-Type", "")
            json_text = res.read().decode("utf-8")
            data = json.loads(json_text)
            assert data["chat"]["chat_id"] == "c_proj_delivery"

    finally:
        server.shutdown()
        server.server_close()


def test_import_line_text_export_unit_and_api(tmp_path: Path):
    """Verify parsing LINE exported .txt chat logs, message categorization, and REST import."""
    db = VaultDB(tmp_path / "test.db")
    archiver = MediaArchiver(tmp_path, db)
    analyzer = ChatAnalyzer(db)

    sample_text = """[LINE] 專案交付團隊的聊天記錄
儲存日期：2026/10/31 15:00

2026/10/31(六)
10:15\t王小明\t早安各位！今天預計提交第一階段成果。
10:20\tAlice\t收到，請記得在今天下午5點前將報價單與發票傳上來。
10:22\t王小明\t[檔案] 2026_Q4_報價單.pdf
10:25\tBob\t[照片]
10:30\t我\t沒問題，收到報價後我們會盡速審核！
"""

    res = archiver.import_line_text_export(
        chat_name="專案交付團隊",
        text_content=sample_text,
        analyzer=analyzer,
    )

    assert res["status"] == "ok"
    assert res["imported_messages"] == 5
    assert res["analyzed"] is True

    msgs = db.search_messages(chat_id=res["chat_id"])
    assert len(msgs) == 5
    file_msg = next((m for m in msgs if m["content_type"] == "file"), None)
    assert file_msg is not None
    assert "報價單.pdf" in file_msg["file_name"]

    img_msg = next((m for m in msgs if m["content_type"] == "image"), None)
    assert img_msg is not None

    ins = db.get_latest_insight(res["chat_id"])
    assert ins is not None
    assert len(ins["action_items"]) > 0

    server = create_server(vault_dir=tmp_path / "vault", host="127.0.0.1", port=0)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()

    try:
        import_body = {
            "chat_name": "API 匯入測試群",
            "text_content": sample_text,
            "auto_analyze": True,
        }
        req_imp = urllib.request.Request(
            f"{base_url}/api/import-text",
            data=json.dumps(import_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_imp) as api_res:
            assert api_res.status == 200
            data = json.loads(api_res.read().decode("utf-8"))
            assert data["success"] is True
            assert data["import_result"]["imported_messages"] == 5

    finally:
        server.shutdown()
        server.server_close()


def test_codeql_path_injection_security(tmp_path: Path):
    """Verify CodeQL path injection barriers block untrusted directory and script traversals."""
    vault_dir = tmp_path / "safe_vault"
    server = create_server(
        vault_dir=vault_dir,
        host="127.0.0.1",
        port=0,
        allowed_scan_root=tmp_path / "safe_vault",
    )
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()

    try:
        # Attempt scan with an outside path
        req_bad_scan = urllib.request.Request(
            f"{base_url}/api/scan-line",
            data=json.dumps({"cache_dir": r"C:\Windows\System32"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req_bad_scan)
        assert exc_info.value.code in (403, 404)

        # Attempt traversal via relative paths
        req_traversal = urllib.request.Request(
            f"{base_url}/api/scan-line",
            data=json.dumps({"cache_dir": r"..\..\Windows"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_traversal:
            urllib.request.urlopen(req_traversal)
        assert exc_traversal.value.code in (403, 404)

    finally:
        server.shutdown()
        server.server_close()


def test_frontend_js_syntax_and_dom_ids_integrity():
    """Verify app.js has balanced braces/parens/strings and all getElementById targets exist in index.html."""
    import re

    repo_root = Path(__file__).resolve().parent.parent
    app_js = (repo_root / "line_vault" / "static" / "app.js").read_text(encoding="utf-8")
    index_html = (repo_root / "line_vault" / "static" / "index.html").read_text(encoding="utf-8")
    styles_css = (repo_root / "line_vault" / "static" / "styles.css").read_text(encoding="utf-8")

    # 1. Verify every static document.getElementById("...") in app.js exists in index.html
    html_ids = set(re.findall(r'id="([^"]+)"', index_html))
    js_ids = set(re.findall(r'document\.getElementById\("([^"]+)"\)', app_js))
    missing_ids = js_ids - html_ids
    assert not missing_ids, f"DOM IDs referenced in app.js but missing in index.html: {missing_ids}"

    # 2. Verify brace/paren/bracket balance and ensure DOMContentLoaded scope never closes early
    lines = app_js.splitlines()
    brace_depth = 0
    paren_depth = 0
    bracket_depth = 0
    in_block_comment = False
    in_single = False
    in_double = False
    template_stack: list[int] = []  # tracks brace_depth when entering ${...} inside backticks
    in_template_text = False
    opened_root = False

    for line_no, line in enumerate(lines, start=1):
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            nxt = line[i + 1] if i + 1 < n else ""

            if in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if in_single:
                if ch == "\\":
                    i += 2
                    continue
                if ch == "'":
                    in_single = False
                i += 1
                continue

            if in_double:
                if ch == "\\":
                    i += 2
                    continue
                if ch == '"':
                    in_double = False
                i += 1
                continue

            if in_template_text:
                if ch == "\\":
                    i += 2
                    continue
                if ch == "$" and nxt == "{":
                    template_stack.append(brace_depth)
                    brace_depth += 1
                    in_template_text = False
                    i += 2
                    continue
                if ch == "`":
                    in_template_text = False
                i += 1
                continue

            # Normal code state
            if ch == "/" and nxt == "/":
                break
            if ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            # Skip regex literal (/.../) on replace(/ or match(/ lines
            if ch == "/" and "new RegExp" not in line and ("replace(/" in line or "match(/" in line):
                # advance to closing /
                i += 1
                while i < n:
                    if line[i] == "\\":
                        i += 2
                        continue
                    if line[i] == "/":
                        break
                    i += 1
                i += 1
                continue

            if ch == "'":
                in_single = True
            elif ch == '"':
                in_double = True
            elif ch == "`":
                in_template_text = True
            elif ch == "{":
                brace_depth += 1
                if brace_depth == 1:
                    opened_root = True
            elif ch == "}":
                brace_depth -= 1
                assert brace_depth >= 0, f"Unexpected extra '}}' at app.js:{line_no}"
                if template_stack and brace_depth == template_stack[-1]:
                    template_stack.pop()
                    in_template_text = True
                if opened_root and line_no < len(lines):
                    assert brace_depth >= 1, (
                        f"Root DOMContentLoaded block closed prematurely at app.js:{line_no}"
                    )
            elif ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth -= 1
                assert paren_depth >= 0, f"Unexpected extra ')' at app.js:{line_no}"
            elif ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth -= 1
                assert bracket_depth >= 0, f"Unexpected extra ']' at app.js:{line_no}"

            i += 1

    assert brace_depth == 0, f"Unclosed '{{' in app.js (remaining depth={brace_depth})"
    assert paren_depth == 0, f"Unclosed '(' in app.js (remaining depth={paren_depth})"
    assert bracket_depth == 0, f"Unclosed '[' in app.js (remaining depth={bracket_depth})"
    assert not in_template_text and not template_stack, "Unclosed template literal in app.js"

    # 3. Verify anti-extension CSS & responsive header rules exist in styles.css
    assert "--disable-extensions" in (repo_root / "line_vault" / "cli.py").read_text(encoding="utf-8")
    assert "--user-data-dir=" in (repo_root / "line_vault" / "cli.py").read_text(encoding="utf-8")
    assert "flex-wrap: wrap" in styles_css
    assert "not(.app-header)" in styles_css


def test_non_ascii_media_and_report_download(tmp_path: Path):
    """Verify downloading Chinese-named media ('正式報價合約_Q4.pdf') and Chinese chat reports succeeds without latin-1 header errors."""
    server = create_server(vault_dir=tmp_path / "vault_dl", host="127.0.0.1", port=0)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()

    try:
        # 1. Seed demo data
        req_seed = urllib.request.Request(f"{base_url}/api/demo/seed", data=b"{}", method="POST")
        with urllib.request.urlopen(req_seed) as res_seed:
            assert res_seed.status == 200

        # 2. Find '正式報價合約_Q4.pdf' in /api/media
        with urllib.request.urlopen(f"{base_url}/api/media") as res_media:
            media_items = json.loads(res_media.read().decode("utf-8"))
        pdf_item = next((m for m in media_items if m["file_name"] == "正式報價合約_Q4.pdf"), None)
        assert pdf_item is not None, "正式報價合約_Q4.pdf should exist in demo media"

        # 3. Download /api/media/file/<media_id> for '正式報價合約_Q4.pdf'
        with urllib.request.urlopen(f"{base_url}/api/media/file/{pdf_item['media_id']}") as res_pdf:
            assert res_pdf.status == 200
            pdf_bytes = res_pdf.read()
            assert pdf_bytes.startswith(b"%PDF-1.4")
            disp = res_pdf.headers.get("Content-Disposition", "")
            assert "filename*=UTF-8''" in disp
            assert urllib.parse.quote("正式報價合約_Q4.pdf") in disp

        # 4. Download /api/export/c_proj_delivery (chat_name='專案A-客戶交付群')
        with urllib.request.urlopen(f"{base_url}/api/export/c_proj_delivery?fmt=markdown") as res_exp:
            assert res_exp.status == 200
            exp_disp = res_exp.headers.get("Content-Disposition", "")
            assert urllib.parse.quote("line_vault_report_專案A-客戶交付群.md") in exp_disp
            exp_text = res_exp.read().decode("utf-8")
            assert "專案A-客戶交付群" in exp_text
    finally:
        server.shutdown()
        server.server_close()


def test_builtin_native_line_reader_and_xor_media(tmp_path: Path):
    """Verify BuiltinLineReader works out-of-the-box with SQLite/EDB databases and deobfuscates XOR media."""
    import sqlite3
    import struct
    import time

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    from line_vault.line_reader import (
        _md5,
        _page_iv,
        decrypt_edb_page,
        derive_edb_key,
        try_deobfuscate_xor_media,
    )

    mock_line_root = tmp_path / "LINE"
    mock_data_dir = mock_line_root / "Data"
    mock_db_dir = mock_data_dir / "db"
    mock_db_dir.mkdir(parents=True)

    # 1. Create a real LINE schema SQLite database at mock_db_dir / "qwb_test.edb"
    edb_path = mock_db_dir / "qwb_test.edb"
    conn = sqlite3.connect(str(edb_path))
    conn.execute("CREATE TABLE _groupChat (_chatMid TEXT PRIMARY KEY, _chatName TEXT)")
    conn.execute(
        "CREATE TABLE _contact (_mid TEXT PRIMARY KEY, _displayNameOverridden TEXT, _displayName TEXT)"
    )
    conn.execute(
        "CREATE TABLE _message ("
        "_id INTEGER PRIMARY KEY, _chatId TEXT, _from TEXT, "
        "_createdTime INTEGER, _text TEXT, _contentType INTEGER, "
        "_contentMetadata TEXT, _contentInfo TEXT)"
    )
    now_ms = int(time.time() * 1000)
    conn.execute("INSERT INTO _groupChat VALUES ('c_real_grp_1', '真實LINE研發群組')")
    conn.execute("INSERT INTO _contact VALUES ('u_alice_1', '', 'Alice 設計師')")
    conn.execute(
        "INSERT INTO _message VALUES (1001, 'c_real_grp_1', 'u_alice_1', ?, '請於週五前確認新版架構規格書與 NT$ 120,000 預算', 0, '{}', '{}')",
        (now_ms,),
    )
    conn.commit()
    conn.close()

    # Verify wxSQLite3 AES-128-CBC page encryption/decryption roundtrip
    raw_sqlite_bytes = edb_path.read_bytes()
    page1 = raw_sqlite_bytes[:4096]
    base_key = derive_edb_key(b"0123456789abcdef0123456789abcdef")
    p1_aes_key = _md5(base_key + struct.pack("<I", 1) + b"sAlT")
    enc_payload = Cipher(algorithms.AES(p1_aes_key), modes.CBC(_page_iv(1))).encryptor().update(page1[16:])
    fake_enc_page1 = b"\x00" * 8 + enc_payload[:8] + page1[16:24] + enc_payload[8:]
    dec_page1 = decrypt_edb_page(fake_enc_page1, base_key, 1)
    assert dec_page1 == page1

    # 2. Create a single-byte XOR obfuscated PNG file (key = 0x5A)
    valid_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00"
        b"IEND\xaeB`\x82"
    )
    xor_png = bytes(b ^ 0x5A for b in valid_png)
    xor_file = mock_data_dir / "cache_img_xor01"
    xor_file.write_bytes(xor_png)

    # Verify deobfuscation helper directly
    assert try_deobfuscate_xor_media(xor_png) == valid_png

    # 3. Verify sync_from_mcp_reader uses BuiltinLineReader when no external script exists
    db = VaultDB(tmp_path / "vault.db")
    archiver = MediaArchiver(tmp_path / "vault", db)
    analyzer = ChatAnalyzer(db)

    sync_res = archiver.sync_from_mcp_reader(
        days=14,
        analyzer=analyzer,
        reader_script=tmp_path / "non_existent_reader.py",
        cache_root=mock_line_root,
    )
    assert sync_res["status"] == "ok"
    assert sync_res["engine"] == "builtin-native-reader"
    assert sync_res["chats_synced"] >= 2
    assert sync_res["messages_synced"] >= 1
    assert sync_res["media_archived"] == 1
    chats = {c["chat_id"]: c for c in db.list_chats()}
    assert "c_real_grp_1" in chats
    assert chats["c_real_grp_1"]["chat_name"] == "真實LINE研發群組"


def test_unlimited_txt_messages_and_delete_clear_about_apis(tmp_path: Path):
    """Verify >300 .txt messages are returned without truncation, demo/chat deletion works, and /api/about works."""
    import json
    import threading
    import urllib.request

    from line_vault.server import create_server

    vault_dir = tmp_path / "vault_unlim"
    server = create_server(vault_dir=vault_dir, host="127.0.0.1", port=0)
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    try:
        # 1. Seed demo data and then clear demo data via POST /api/demo/clear
        req_seed = urllib.request.Request(f"{base_url}/api/demo/seed", data=b"{}", method="POST")
        with urllib.request.urlopen(req_seed) as resp:
            assert resp.status == 200
        with urllib.request.urlopen(f"{base_url}/api/chats") as resp:
            chats_before = json.loads(resp.read().decode("utf-8"))
            assert len(chats_before) == 4

        req_clear = urllib.request.Request(f"{base_url}/api/demo/clear", data=b"{}", method="POST")
        with urllib.request.urlopen(req_clear) as resp:
            clear_data = json.loads(resp.read().decode("utf-8"))
            assert clear_data["success"] is True
            assert clear_data["clear_result"]["deleted_count"] == 4
        with urllib.request.urlopen(f"{base_url}/api/chats") as resp:
            chats_after = json.loads(resp.read().decode("utf-8"))
            assert len(chats_after) == 0

        # 2. Import a .txt chat history with 450 messages (> 300 former limit)
        lines = ["[LINE] 大型專案超過三百則對話紀錄.txt", "儲存日期：2026/10/31 18:00", ""]
        lines.append("2026/10/31（週六）")
        for i in range(1, 451):
            hh = (8 + (i // 60)) % 24
            mm = i % 60
            lines.append(f"{hh:02d}:{mm:02d}\t成員{i % 5}\t這是第 {i} 則重要訊息，確認無 300 則上限截斷")
        txt_payload = "\n".join(lines)

        req_imp = urllib.request.Request(
            f"{base_url}/api/import-text",
            data=json.dumps({
                "chat_name": "大型專案450則測試群",
                "text_content": txt_payload,
                "auto_analyze": True,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_imp) as resp:
            imp_data = json.loads(resp.read().decode("utf-8"))
            assert imp_data["success"] is True
            assert imp_data["import_result"]["imported_messages"] == 450
            chat_id = imp_data["import_result"]["chat_id"]

        # Verify GET /api/messages?limit=0&chat_id=... returns ALL 450 messages
        with urllib.request.urlopen(f"{base_url}/api/messages?limit=0&chat_id={chat_id}") as resp:
            msgs = json.loads(resp.read().decode("utf-8"))
            assert len(msgs) == 450
            assert "第 1 則" in msgs[0]["text_content"]
            assert "第 450 則" in msgs[-1]["text_content"]

        # Verify GET /api/about returns app metadata
        with urllib.request.urlopen(f"{base_url}/api/about") as resp:
            about = json.loads(resp.read().decode("utf-8"))
            assert about["version"] == "1.4.1"
            assert about["author"] == "SanHsien"
            assert "github.com/SanHsien/line-vault" in about["github_repo_url"]

        # Verify POST /api/chats/<chat_id>/delete deletes the chat room
        req_del = urllib.request.Request(
            f"{base_url}/api/chats/{chat_id}/delete",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_del) as resp:
            del_data = json.loads(resp.read().decode("utf-8"))
            assert del_data["success"] is True

        with urllib.request.urlopen(f"{base_url}/api/chats") as resp:
            assert len(json.loads(resp.read().decode("utf-8"))) == 0
    finally:
        server.shutdown()
        server.server_close()


def test_theme_modes_and_plain_txt_import(tmp_path: Path):
    """Verify light/dark/system theme support in static assets and fallback plain .txt import."""
    repo_root = Path(__file__).resolve().parent.parent
    index_html = (repo_root / "line_vault" / "static" / "index.html").read_text(encoding="utf-8")
    styles_css = (repo_root / "line_vault" / "static" / "styles.css").read_text(encoding="utf-8")
    app_js = (repo_root / "line_vault" / "static" / "app.js").read_text(encoding="utf-8")

    # Verify no external script input box remains in index.html
    assert "inputReaderScript" not in index_html
    # Verify theme toggle and 3 theme modes exist
    assert 'id="btnThemeToggle"' in index_html
    assert ':root[data-theme="light"]' in styles_css
    assert "applyTheme" in app_js

    # Verify plain .txt import (without HH:MM tabs) and sample_line_chat_export.txt
    db = VaultDB(tmp_path / "txt.db")
    archiver = MediaArchiver(tmp_path / "txt_vault", db)
    analyzer = ChatAnalyzer(db)

    plain_res = archiver.import_line_text_export(
        chat_name="一般文字備忘錄",
        text_content="王經理：請於明天下午三點前確認合約條款\n陳工程師：收到，馬上處理！",
        analyzer=analyzer,
    )
    assert plain_res["status"] == "ok"
    assert plain_res["imported_messages"] == 2

    sample_path = repo_root / "docs" / "sample_line_chat_export.txt"
    assert sample_path.is_file()
    sample_res = archiver.import_line_text_export(
        chat_name="",
        text_content=sample_path.read_text(encoding="utf-8"),
        analyzer=analyzer,
    )
    assert sample_res["status"] == "ok"
    assert sample_res["imported_messages"] == 6


def test_settings_api_and_folder_sanitization(tmp_path: Path):
    """Verify settings defaults, GET/POST persistence, folder sanitization, and About modal integrity."""
    import json
    import threading
    import urllib.request

    from line_vault.archiver import _sanitize_chat_folder_name
    from line_vault.db import VaultDB
    from line_vault.server import create_server

    # 1. Folder sanitization tests
    assert _sanitize_chat_folder_name("專案A-客戶交付群") == "專案A-客戶交付群"
    assert _sanitize_chat_folder_name('<重要>測試/路徑?*"') == "重要_測試_路徑"
    assert _sanitize_chat_folder_name("  .測試群.  ") == "測試群"
    assert _sanitize_chat_folder_name("", fallback_id="fallback_chat") == "fallback_chat"

    # 2. Settings default values
    v_dir = tmp_path / "v_settings"
    db = VaultDB(v_dir / "vault.db")
    settings = db.get_settings()
    assert settings["auto_update_interval_minutes"] == 5
    assert settings["auto_update_enabled"] is True
    assert settings["auto_download_stickers"] is True
    assert settings["auto_download_images"] is True
    assert settings["auto_download_videos"] is True
    assert settings["auto_download_files"] is True
    assert settings["organize_by_chat_name"] is True
    assert str(v_dir.resolve()) in settings["media_storage_dir"]

    # 3. Settings REST API GET / POST
    server = create_server(vault_dir=v_dir, host="127.0.0.1", port=0)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{port}"

    try:
        # GET /api/settings
        with urllib.request.urlopen(f"{base_url}/api/settings") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["auto_update_interval_minutes"] == 5

        # POST /api/settings update
        post_data = {
            "auto_update_interval_minutes": 10,
            "auto_download_stickers": False,
            "media_storage_dir": str((v_dir / "custom_media").resolve()),
        }
        req = urllib.request.Request(
            f"{base_url}/api/settings",
            data=json.dumps(post_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            updated = json.loads(resp.read().decode("utf-8"))
            assert updated["auto_update_interval_minutes"] == 10
            assert updated["auto_download_stickers"] is False

        # Verify GET reflects updated settings
        with urllib.request.urlopen(f"{base_url}/api/settings") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data["auto_update_interval_minutes"] == 10
            assert data["auto_download_stickers"] is False

        # POST /api/pick-folder
        req_pick = urllib.request.Request(
            f"{base_url}/api/pick-folder",
            data=json.dumps({"initial_dir": ""}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_pick) as resp:
            assert resp.status == 200
            pick_res = json.loads(resp.read().decode("utf-8"))
            assert pick_res["status"] == "ok"
    finally:
        server.shutdown()
        server.server_close()
        db.close()

    # 4. Verify About modal in index.html has no btnOpenReleases or btnOpenRepo
    repo_root = Path(__file__).resolve().parent.parent
    index_html = (repo_root / "line_vault" / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (repo_root / "line_vault" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'id="btnOpenReleases"' not in index_html
    assert 'id="btnOpenRepo"' not in index_html
    assert "btnOpenReleases" not in app_js
    assert "btnOpenRepo" not in app_js
    assert "openExternalRepoUrl" not in app_js


def test_sticker_download_and_cache_management(tmp_path: Path):
    """Verify sticker archiving, local cache priority, de-duplication, and mock CDN fetching."""
    from line_vault.archiver import MediaArchiver
    from line_vault.db import VaultDB

    vault_dir = tmp_path / "v_sticker"
    db = VaultDB(vault_dir / "vault.db")
    archiver = MediaArchiver(vault_dir, db)

    chat_id = "c_test_chat"
    db.upsert_chat(chat_id=chat_id, chat_name="貼圖測試群")
    msg_id = "m_stk_test_01"
    db.upsert_message(message_id=msg_id, chat_id=chat_id, content_type="sticker")

    # 1. Local sticker cache hit
    mock_stk_root = tmp_path / "line_stickers"
    pkg_dir = mock_stk_root / "pkg_42"
    pkg_dir.mkdir(parents=True)
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    (pkg_dir / "1001.png").write_bytes(fake_png)

    res_local = archiver.download_and_archive_sticker(
        chat_id=chat_id,
        message_id=msg_id,
        stk_id="1001",
        stk_pkg_id="pkg_42",
        sticker_root=mock_stk_root,
    )
    assert res_local["status"] == "archived"
    assert res_local["media"]["media_type"] == "image"
    assert res_local["media"]["source_role"] == "sticker"
    assert "sticker_1001.png" in res_local["file_path"]

    # 2. De-duplication (local vault cache priority, does not re-download)
    res_repeat = archiver.download_and_archive_sticker(
        chat_id=chat_id,
        message_id=msg_id,
        stk_id="1001",
        stk_pkg_id="pkg_42",
        sticker_root=mock_stk_root,
    )
    assert res_repeat["status"] == "archived"
    assert res_repeat.get("cached") is True

    # 3. CDN download via mock fetcher
    def mock_fetcher(url: str) -> bytes | None:
        if "sticker/2002/" in url:
            return b"\x89PNG\r\n\x1a\n" + b"\x42" * 40
        return None

    msg_id_2 = "m_stk_test_02"
    db.upsert_message(message_id=msg_id_2, chat_id=chat_id, content_type="sticker")
    res_cdn = archiver.download_and_archive_sticker(
        chat_id=chat_id,
        message_id=msg_id_2,
        stk_id="2002",
        fetcher=mock_fetcher,
    )
    assert res_cdn["status"] == "archived"
    assert res_cdn["media"]["size_bytes"] == 48

    # 4. Failure handling (when sticker is missing everywhere)
    res_fail = archiver.download_and_archive_sticker(
        chat_id=chat_id,
        message_id="m_stk_none",
        stk_id="9999",
        fetcher=lambda url: None,
    )
    assert res_fail["status"] == "download_failed"
    assert "sticker_id" in res_fail

    db.close()


def test_native_sync_days_zero_unlimited_and_community_and_type_filters(tmp_path: Path):
    """Verify days=0 unlimited sync (>300 msgs), community classification, and checkbox filtering."""
    import json
    import sqlite3
    import time

    from line_vault.analyzer import ChatAnalyzer
    from line_vault.archiver import MediaArchiver
    from line_vault.db import VaultDB
    from line_vault.line_reader import BuiltinLineReader

    # 1. Create mock LINE Data directory with a test .edb containing >300 messages
    mock_line_root = tmp_path / "mock_line"
    mock_db_dir = mock_line_root / "Data" / "db"
    mock_db_dir.mkdir(parents=True)
    edb_path = mock_db_dir / "unlimited_test.edb"

    conn = sqlite3.connect(str(edb_path))
    conn.execute("CREATE TABLE _groupChat (_chatMid TEXT PRIMARY KEY, _chatName TEXT)")
    conn.execute("CREATE TABLE _contact (_mid TEXT PRIMARY KEY, _displayNameOverridden TEXT, _displayName TEXT)")
    conn.execute(
        "CREATE TABLE _message ("
        "_id INTEGER PRIMARY KEY, _chatId TEXT, _from TEXT, "
        "_createdTime INTEGER, _text TEXT, _contentType INTEGER, "
        "_contentMetadata TEXT, _contentInfo TEXT)"
    )

    base_time = int(time.time() * 1000) - 10000000
    # Group chat (c_ prefix)
    conn.execute("INSERT INTO _groupChat VALUES ('c_dev_team', '研發專案核心群')")
    conn.execute("INSERT INTO _contact VALUES ('u_boss', '', '研發總監')")
    conn.execute("INSERT INTO _contact VALUES ('u_member', '', '工程師')")
    # Community chat (m_ prefix)
    conn.execute("INSERT INTO _groupChat VALUES ('m_openchat_tech', '開源技術社群')")
    # Direct chat (u_ prefix)
    conn.execute("INSERT INTO _contact VALUES ('u_vendor_lee', '', '李經理')")

    # Insert 350 messages into c_dev_team (>300 former limit)
    msgs_data = []
    for i in range(1, 351):
        ts = base_time + i * 1000
        mid = 1000 + i
        if i == 50:
            # Sticker message
            meta = json.dumps({"STKID": "stk_888", "STKPKGID": "pkg_99", "STKTXT": "讚"})
            msgs_data.append((mid, "c_dev_team", "u_boss", ts, "", 7, meta, "{}"))
        elif i == 100:
            # Image message
            meta = json.dumps({"FILE_SIZE": "128"})
            msgs_data.append((mid, "c_dev_team", "u_boss", ts, "[相片]", 1, meta, "{}"))
        else:
            msgs_data.append((mid, "c_dev_team", "u_member", ts, f"測試對話訊息第 {i} 則", 0, "{}", "{}"))

    # Also add 1 message to community and 1 to direct chat
    msgs_data.append((2001, "m_openchat_tech", "u_boss", base_time + 500000, "歡迎加入開源技術社群！", 0, "{}", "{}"))
    msgs_data.append((3001, "u_vendor_lee", "u_vendor_lee", base_time + 600000, "你好，請問合約進度？", 0, "{}", "{}"))

    conn.executemany("INSERT INTO _message VALUES (?, ?, ?, ?, ?, ?, ?, ?)", msgs_data)
    conn.commit()
    conn.close()

    # 2. Test Scenario A: sync with auto_download_stickers=False and auto_download_images=False
    vault_dir = tmp_path / "v_unlimited"
    db = VaultDB(vault_dir / "vault.db")
    db.update_settings({
        "auto_download_stickers": False,
        "auto_download_images": False,
    })
    archiver = MediaArchiver(vault_dir, db)
    analyzer = ChatAnalyzer(db)
    reader = BuiltinLineReader(line_root=mock_line_root / "Data")

    sync_res = reader.run_native_sync(archiver, days=0, analyzer=analyzer)
    assert sync_res["status"] == "ok"
    assert sync_res["chats_synced"] >= 3

    # Verify chat types: community, group, direct
    chat_comm = db.get_chat("m_openchat_tech")
    assert chat_comm is not None
    assert chat_comm["chat_type"] == "community"

    chat_grp = db.get_chat("c_dev_team")
    assert chat_grp is not None
    assert chat_grp["chat_type"] == "group"

    chat_dir = db.get_chat("u_vendor_lee")
    assert chat_dir is not None
    assert chat_dir["chat_type"] == "direct"

    # Verify >300 messages are ALL synced without truncation
    all_grp_msgs = db.search_messages(chat_id="c_dev_team", limit=0)
    assert len(all_grp_msgs) == 350

    # Since auto_download_stickers=False, sticker was not archived
    stk_msg = next((m for m in all_grp_msgs if m["content_type"] == "sticker"), None)
    assert stk_msg is not None
    assert stk_msg["media_status"] == "none"

    # 3. Test Scenario B: Enable stickers download and re-sync
    fake_stk_png = b"\x89PNG\r\n\x1a\n" + b"\x55" * 32

    def mock_fetcher(url: str) -> bytes:
        return fake_stk_png

    db.update_settings({"auto_download_stickers": True})
    stk_res = archiver.download_and_archive_sticker(
        chat_id="c_dev_team",
        message_id=stk_msg["message_id"],
        stk_id="stk_888",
        fetcher=mock_fetcher,
    )
    assert stk_res["status"] == "archived"

    # Verify analyzer covers unlimited date range and 350 messages
    insight = analyzer.analyze_chat("c_dev_team")
    assert "350 則對話" in insight["summary"]
    assert "無上限分析" in insight["summary"] or "對話時間範圍" in insight["summary"]

    db.close()


def test_community_square_name_resolution_and_folder_migration(tmp_path: Path):
    """Verify _square and _squareChat resolve real community names and migrate legacy folders."""
    import sqlite3

    from line_vault.line_reader import BuiltinLineReader

    vault_dir = tmp_path / "vault_comm"
    db = VaultDB(vault_dir / "vault.db")
    archiver = MediaArchiver(vault_dir, db)

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE _contact (_mid TEXT, _displayNameOverridden TEXT, _displayName TEXT);")
    conn.execute("CREATE TABLE _groupChat (_chatMid TEXT, _chatName TEXT);")
    conn.execute("CREATE TABLE _square (_mid TEXT, _name TEXT);")
    conn.execute("CREATE TABLE _squareChat (_squareChatMid TEXT, _squareMid TEXT, _name TEXT);")
    conn.execute("CREATE TABLE _squareMember (_squareMemberMid TEXT, _displayName TEXT);")
    conn.execute(
        """
        CREATE TABLE _message (
            _id INTEGER PRIMARY KEY,
            _chatId TEXT,
            _from TEXT,
            _createdTime INTEGER,
            _text TEXT,
            _contentType INTEGER,
            _contentMetadata TEXT,
            _contentInfo TEXT
        );
        """
    )

    conn.execute("INSERT INTO _square VALUES ('s_open_01', '台灣開源技術社群');")
    conn.execute("INSERT INTO _squareChat VALUES ('m_chat_01', 's_open_01', 'AI 技術交流分區');")
    conn.execute("INSERT INTO _squareMember VALUES ('u_mem_01', '小明工程師');")
    conn.execute("INSERT INTO _message VALUES (1, 'm_chat_01', 'u_mem_01', 1700000000000, '大家早安', 0, '{}', '{}');")

    reader = BuiltinLineReader()
    c_cnt, m_cnt, med_cnt = reader._sync_decrypted_sqlite_db(
        conn=conn,
        archiver=archiver,
        chat_name_filter=None,
        days=0,
    )

    assert c_cnt == 1
    assert m_cnt == 1

    chat_row = db.get_chat("m_chat_01")
    assert chat_row is not None
    assert chat_row["chat_type"] == "community"
    assert "台灣開源技術社群" in chat_row["chat_name"]
    assert "AI 技術交流分區" in chat_row["chat_name"]

    msgs = db.search_messages(chat_id="m_chat_01", limit=0)
    assert len(msgs) == 1
    assert msgs[0]["sender_name"] == "小明工程師"

    db.close()
    conn.close()


def test_archive_local_file_and_autolink_cached_media(tmp_path: Path):
    """Verify archive_local_file archives original files directly and auto_link_cached_media_to_chats recovers cache."""
    import hashlib

    from line_vault.archiver import MediaArchiver
    from line_vault.db import VaultDB

    vault_dir = tmp_path / "v_autolink"
    db = VaultDB(vault_dir / "vault.db")
    archiver = MediaArchiver(vault_dir, db)

    chat_id = "c_autolink_chat"
    db.upsert_chat(chat_id=chat_id, chat_name="自動歸檔群")

    # 1. Test archive_local_file
    sample_file = tmp_path / "original_photo.jpg"
    # Write a simple valid JPEG header
    sample_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"A" * 100)
    res = archiver.archive_local_file(
        chat_id=chat_id,
        message_id="msg_orig_01",
        source_file=sample_file,
        fallback_filename="original_photo.jpg",
    )
    assert res["status"] == "archived"
    assert res["source_role"] == "original"
    msgs = db.search_messages(chat_id=chat_id)
    assert msgs[0]["media_status"] == "archived"

    # 2. Test auto_link_cached_media_to_chats
    cache_root = tmp_path / "FakeCache"
    chat_hash = hashlib.sha1(chat_id.encode("utf-8")).hexdigest()
    m_cache_dir = cache_root / "acc_1" / chat_hash / "m" / "sub"
    m_cache_dir.mkdir(parents=True, exist_ok=True)
    orphan_cache_file = m_cache_dir / "cached_img.eimg"
    orphan_cache_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"B" * 200)

    recovered = archiver.auto_link_cached_media_to_chats(cache_root)
    assert recovered == 1
    media_list = db.list_media(chat_id=chat_id)
    assert len(media_list) >= 2


def test_help_buttons_and_concept_modal():
    """Verify presence of .btn-help elements and conceptHelpModal in frontend assets."""
    repo_root = Path(__file__).resolve().parent.parent
    index_html = (repo_root / "line_vault" / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (repo_root / "line_vault" / "static" / "app.js").read_text(encoding="utf-8")
    styles_css = (repo_root / "line_vault" / "static" / "styles.css").read_text(encoding="utf-8")

    assert 'id="conceptHelpModal"' in index_html
    assert 'class="btn-help"' in index_html
    assert '.btn-help' in styles_css
    assert 'HELP_TOPICS' in app_js
    assert 'openConceptHelp' in app_js
    assert 'cached_pending' in app_js
