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
            data=json.dumps({"days": 7}).encode("utf-8"),
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
    for pattern in ("vault_data/", "*.edb", "*.key", ".env"):
        assert pattern in content


def test_find_system_app_browser():
    """Verify system app browser search behaves safely on Windows and non-Windows."""
    result = find_system_app_browser()
    assert result is None or (isinstance(result, str) and len(result) > 0)


