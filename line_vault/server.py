"""Zero-dependency HTTP server and REST API for LINE Vault built with ThreadingHTTPServer."""

import json
import os
import platform
import re
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from line_vault.analyzer import ChatAnalyzer
from line_vault.archiver import MediaArchiver
from line_vault.db import VaultDB


class VaultRequestHandler(BaseHTTPRequestHandler):
    """Request handler implementing static asset serving and REST API endpoints."""

    server_vault_dir: Path
    allowed_scan_root: Path
    db: VaultDB
    archiver: MediaArchiver
    analyzer: ChatAnalyzer
    static_dir: Path

    def log_message(self, format_str: str, *args) -> None:
        """Suppress standard logging in tests/quiet mode."""
        pass

    def _resolve_safe_scan_dir(self, user_dir: str | None) -> str | None:
        """Resolve and validate custom LINE scan directory against path injection."""
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        default_line_dir = None
        if local_appdata:
            candidate = Path(local_appdata) / "LINE" / "Data"
            default_line_dir = str(candidate if candidate.exists() else Path(local_appdata) / "LINE")

        if not user_dir or not str(user_dir).strip():
            return default_line_dir if (default_line_dir and os.path.isdir(default_line_dir)) else None

        user_dir_str = str(user_dir).strip()
        if default_line_dir and user_dir_str in (
            default_line_dir,
            "%LOCALAPPDATA%\\LINE\\Data",
            "%LOCALAPPDATA%\\LINE",
        ):
            return default_line_dir if os.path.isdir(default_line_dir) else None

        base_root = os.path.normpath(os.path.realpath(str(self.allowed_scan_root)))
        fullpath = os.path.normpath(os.path.realpath(user_dir_str))
        if not fullpath.startswith(base_root):
            return None
        if not os.path.isdir(fullpath):
            return None
        return fullpath

    def _resolve_safe_reader_script(self, user_script: str | None) -> str | None:
        """Resolve and validate line-desktop-mcp reader script path against path injection."""
        default_script = r"C:\GitHub\line-desktop-mcp\src\extensions\python\line-reader.py"
        if not user_script or not str(user_script).strip():
            return None

        user_script_str = str(user_script).strip()
        if user_script_str == default_script:
            return default_script if os.path.isfile(default_script) else None

        base_root = os.path.normpath(os.path.realpath(str(self.allowed_scan_root)))
        fullpath = os.path.normpath(os.path.realpath(user_script_str))
        if not fullpath.startswith(base_root):
            return None
        if not os.path.isfile(fullpath):
            return None
        return fullpath

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, data: object, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message, "status": status}, status=status)

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Static Web UI files
        if path in ("/", "/index.html"):
            return self._serve_static_file("index.html", "text/html; charset=utf-8")
        if path in ("/styles.css", "/static/styles.css"):
            return self._serve_static_file("styles.css", "text/css; charset=utf-8")
        if path in ("/app.js", "/static/app.js"):
            return self._serve_static_file("app.js", "application/javascript; charset=utf-8")

        # 2. API Endpoints
        if path == "/api/status":
            stats = self.db.get_dashboard_stats()
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            line_path = Path(local_appdata) / "LINE" if local_appdata else None
            line_detected = bool(line_path and line_path.exists())

            return self._send_json({
                "status": "online",
                "version": "1.0.0",
                "stats": stats,
                "vault_dir": str(self.server_vault_dir),
                "line_detected": line_detected,
                "line_path": str(line_path) if line_detected else "",
                "fts5_enabled": self.db.has_fts5,
                "platform": platform.platform(),
            })

        if path == "/api/chats":
            only_mon = query.get("monitored", [""])[0] in ("1", "true")
            c_type = query.get("chat_type", [None])[0]
            q_text = query.get("q", [None])[0]
            chats = self.db.list_chats(only_monitored=only_mon, chat_type=c_type, query=q_text)
            return self._send_json(chats)

        if path == "/api/messages":
            chat_id = query.get("chat_id", [None])[0]
            q_text = query.get("q", [""])[0]
            c_type = query.get("content_type", [None])[0]
            d_from = query.get("date_from", [None])[0]
            d_to = query.get("date_to", [None])[0]
            only_bm = query.get("bookmarked", ["0"])[0] in ("1", "true")
            limit_str = query.get("limit", ["200"])[0]
            try:
                limit = int(limit_str)
            except ValueError:
                limit = 200

            msgs = self.db.search_messages(
                query=q_text,
                chat_id=chat_id,
                content_type=c_type,
                date_from=d_from,
                date_to=d_to,
                only_bookmarked=only_bm,
                limit=limit,
            )
            return self._send_json(msgs)

        if path == "/api/media":
            chat_id = query.get("chat_id", [None])[0]
            m_type = query.get("media_type", [None])[0]
            q_text = query.get("q", [None])[0]
            limit_str = query.get("limit", ["200"])[0]
            try:
                limit = int(limit_str)
            except ValueError:
                limit = 200

            media_list = self.db.list_media(
                chat_id=chat_id,
                media_type=m_type,
                query=q_text,
                limit=limit,
            )
            return self._send_json(media_list)

        # GET /api/media/file/<media_id>
        if path.startswith("/api/media/file/"):
            media_id = path[len("/api/media/file/"):]
            return self._serve_media_file(media_id)

        # GET /api/insights/<chat_id>
        if path.startswith("/api/insights/"):
            chat_id = path[len("/api/insights/"):]
            insight = self.db.get_latest_insight(chat_id)
            if not insight:
                return self._send_error("No insight found for chat", status=404)
            return self._send_json(insight)

        # GET /api/export/<chat_id>
        if path.startswith("/api/export/"):
            chat_id = path[len("/api/export/"):]
            fmt = query.get("fmt", ["markdown"])[0]
            try:
                filename, mime_type, content = self.archiver.export_chat_report(chat_id, fmt=fmt)
                body = content.encode("utf-8")
                safe_ascii_name = re.sub(r"[^A-Za-z0-9_.\-]", "_", filename)
                safe_utf8_name = urllib.parse.quote(filename)
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{safe_ascii_name}"; filename*=UTF-8\'\'{safe_utf8_name}',
                )
                self.end_headers()
                self.wfile.write(body)
                return
            except ValueError as ve:
                return self._send_error(str(ve), status=404)
            except (KeyError, OSError) as exc:
                return self._send_error(str(exc), status=500)

        return self._send_error("Not Found", status=404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # POST /api/chats/<chat_id>/monitor
        monitor_match = re.match(r"^/api/chats/([^/]+)/monitor$", path)
        if monitor_match:
            chat_id = monitor_match.group(1)
            body = self._read_json_body()
            monitored = bool(body.get("monitored", True))
            auto_backup = bool(body.get("auto_backup_media", True))
            auto_analyze = bool(body.get("auto_analyze", True))

            updated = self.db.set_chat_monitoring(
                chat_id=chat_id,
                monitored=monitored,
                auto_backup_media=auto_backup,
                auto_analyze=auto_analyze,
            )
            if not updated:
                return self._send_error("Chat not found", status=404)

            # Auto analyze if monitoring enabled
            if monitored and auto_analyze:
                try:
                    self.analyzer.analyze_chat(chat_id)
                except Exception as exc:
                    updated["analysis_error"] = str(exc)

            return self._send_json(updated)

        # POST /api/messages/<message_id>/bookmark
        bm_match = re.match(r"^/api/messages/([^/]+)/bookmark$", path)
        if bm_match:
            message_id = bm_match.group(1)
            body = self._read_json_body()
            target_val = body.get("bookmarked")
            updated = self.db.toggle_message_bookmark(message_id, bookmarked=target_val)
            if not updated:
                return self._send_error("Message not found", status=404)
            return self._send_json(updated)

        # POST /api/insights/<chat_id>/action-status
        action_match = re.match(r"^/api/insights/([^/]+)/action-status$", path)
        if action_match:
            chat_id = action_match.group(1)
            body = self._read_json_body()
            if "action_index" not in body:
                return self._send_error("Missing action_index", status=400)
            try:
                action_idx = int(body["action_index"])
            except ValueError:
                return self._send_error("Invalid action_index", status=400)
            done = bool(body.get("done", True))
            updated = self.db.update_action_item_status(chat_id, action_idx, done=done)
            if not updated:
                return self._send_error("Insight or action item not found", status=404)
            return self._send_json(updated)

        # POST /api/import-text
        if path == "/api/import-text":
            body = self._read_json_body()
            chat_name = body.get("chat_name", "")
            text_content = body.get("text_content", "")
            chat_id = body.get("chat_id")
            auto_analyze = bool(body.get("auto_analyze", True))
            if not text_content.strip():
                return self._send_error("Empty text_content", status=400)
            try:
                res = self.archiver.import_line_text_export(
                    chat_name=chat_name,
                    text_content=text_content,
                    chat_id=chat_id,
                    analyzer=self.analyzer if auto_analyze else None,
                )
                stats = self.db.get_dashboard_stats()
                return self._send_json({"success": True, "import_result": res, "stats": stats})
            except Exception as exc:
                return self._send_error(str(exc), status=500)

        # POST /api/analyze/<chat_id>
        analyze_match = re.match(r"^/api/analyze/([^/]+)$", path)
        if analyze_match:
            chat_id = analyze_match.group(1)
            body = self._read_json_body()
            lang = body.get("lang", "zh-TW")
            try:
                insight = self.analyzer.analyze_chat(chat_id, lang=lang)
                return self._send_json(insight)
            except ValueError as ve:
                return self._send_error(str(ve), status=404)
            except Exception as exc:
                return self._send_error(str(exc), status=500)

        # POST /api/analyze-all
        if path == "/api/analyze-all":
            body = self._read_json_body()
            lang = body.get("lang", "zh-TW")
            chats = self.db.list_chats(only_monitored=True)
            results = []
            errors = []
            for c in chats:
                try:
                    res = self.analyzer.analyze_chat(c["chat_id"], lang=lang)
                    results.append(res)
                except Exception as exc:
                    errors.append({"chat_id": c["chat_id"], "error": str(exc)})
            return self._send_json({"analyzed_count": len(results), "insights": results, "errors": errors})

        # POST /api/demo/seed
        if path == "/api/demo/seed":
            seed_res = self.archiver.seed_demo_data(analyzer=self.analyzer)
            stats = self.db.get_dashboard_stats()
            return self._send_json({"success": True, "seed_result": seed_res, "stats": stats})

        # POST /api/scan-line
        if path == "/api/scan-line":
            body = self._read_json_body()
            if body.get("use_mcp_reader"):
                safe_script = self._resolve_safe_reader_script(body.get("reader_script"))
                safe_cache = self._resolve_safe_scan_dir(body.get("cache_dir"))
                sync_res = self.archiver.sync_from_mcp_reader(
                    chat_name=body.get("chat_name"),
                    days=int(body.get("days", 14)),
                    analyzer=self.analyzer,
                    reader_script=safe_script,
                    cache_root=safe_cache,
                )
                stats = self.db.get_dashboard_stats()
                return self._send_json({"success": True, "sync_result": sync_res, "stats": stats})

            raw_cache_dir = body.get("cache_dir")
            safe_dir = self._resolve_safe_scan_dir(raw_cache_dir)
            if not safe_dir:
                return self._send_error("Invalid or inaccessible LINE cache directory", status=403 if raw_cache_dir else 404)
            scan_res = self.archiver.scan_local_line_directory(safe_dir, analyzer=self.analyzer)
            stats = self.db.get_dashboard_stats()
            return self._send_json({"success": True, "scan_result": scan_res, "stats": stats})

        # POST /api/sync-mcp
        if path == "/api/sync-mcp":
            body = self._read_json_body()
            chat_name = body.get("chat_name")
            days = int(body.get("days", 14))
            safe_script = self._resolve_safe_reader_script(body.get("reader_script"))
            safe_cache = self._resolve_safe_scan_dir(body.get("cache_dir"))
            sync_res = self.archiver.sync_from_mcp_reader(
                chat_name=chat_name,
                days=days,
                analyzer=self.analyzer,
                reader_script=safe_script,
                cache_root=safe_cache,
            )
            stats = self.db.get_dashboard_stats()
            return self._send_json({"success": True, "sync_result": sync_res, "stats": stats})

        return self._send_error("Not Found", status=404)

    def _serve_static_file(self, filename: str, mime_type: str) -> None:
        filepath = self.static_dir / filename
        if not filepath.is_file():
            return self._send_error(f"Static file {filename} not found", status=404)

        with open(filepath, "rb") as f:
            content = f.read()

        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_media_file(self, media_id: str) -> None:
        media = self.db.get_media(media_id)
        if not media:
            return self._send_error("Media not found", status=404)

        rel_path = media.get("vault_rel_path") or ""
        base_vault = os.path.normpath(os.path.realpath(str(self.server_vault_dir)))
        fullpath = os.path.normpath(os.path.realpath(os.path.join(base_vault, rel_path)))

        if not fullpath.startswith(base_vault):
            return self._send_error("Access denied", status=403)

        if not os.path.isfile(fullpath):
            return self._send_error("File on disk not found", status=404)

        file_path = Path(fullpath)
        mime_type = media.get("mime_type") or "application/octet-stream"
        file_size = os.path.getsize(fullpath)
        filename = media.get("file_name") or file_path.name
        safe_ascii_name = re.sub(r"[^A-Za-z0-9_.\-]", "_", filename)
        safe_utf8_name = urllib.parse.quote(filename)

        m_type = media.get("media_type")
        disposition_type = "inline" if m_type in ("image", "video", "audio") else "attachment"

        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header(
            "Content-Disposition",
            f'{disposition_type}; filename="{safe_ascii_name}"; filename*=UTF-8\'\'{safe_utf8_name}',
        )
        self.end_headers()

        with open(fullpath, "rb") as f:
            while chunk := f.read(65536):
                self.wfile.write(chunk)


def create_server(
    vault_dir: Path | str = "vault_data",
    host: str = "127.0.0.1",
    port: int = 8765,
    allowed_scan_root: Path | str | None = None,
) -> ThreadingHTTPServer:
    """Create configured ThreadingHTTPServer instance."""
    v_dir = Path(vault_dir).resolve()
    v_dir.mkdir(parents=True, exist_ok=True)

    scan_root = Path(allowed_scan_root).resolve() if allowed_scan_root else v_dir.parent.resolve()

    db = VaultDB(v_dir / "vault.db")
    archiver = MediaArchiver(v_dir, db)
    analyzer = ChatAnalyzer(db)

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        static_dir = (Path(meipass) / "line_vault" / "static").resolve()
    else:
        static_dir = (Path(__file__).parent / "static").resolve()

    class BoundHandler(VaultRequestHandler):
        pass

    BoundHandler.server_vault_dir = v_dir
    BoundHandler.allowed_scan_root = scan_root
    BoundHandler.db = db
    BoundHandler.archiver = archiver
    BoundHandler.analyzer = analyzer
    BoundHandler.static_dir = static_dir

    server = ThreadingHTTPServer((host, port), BoundHandler)
    return server


def run_server(
    vault_dir: Path | str = "vault_data",
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
    allowed_scan_root: Path | str | None = None,
) -> None:
    """Run the LINE Vault HTTP server until interrupted."""
    server = create_server(vault_dir=vault_dir, host=host, port=port, allowed_scan_root=allowed_scan_root)
    url = f"http://{host}:{port}"
    print(f"[*] LINE Vault server started at {url}")
    print(f"[*] Vault directory: {Path(vault_dir).resolve()}")

    if open_browser:
        try:
            webbrowser.open(url)
        except webbrowser.Error:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down LINE Vault server...")
    finally:
        server.server_close()
