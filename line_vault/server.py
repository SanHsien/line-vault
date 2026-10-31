"""Zero-dependency HTTP server and REST API for LINE Vault built with ThreadingHTTPServer."""

import json
import os
import platform
import re
import sqlite3
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from line_vault import (
    APP_AUTHOR,
    APP_NAME,
    APP_VERSION,
    GITHUB_RELEASES_URL,
    GITHUB_REPO,
    GITHUB_REPO_URL,
)
from line_vault.analyzer import ChatAnalyzer
from line_vault.archiver import MediaArchiver
from line_vault.db import VaultDB


def _parse_semver(ver_str: str) -> tuple[int, int, int]:
    """Parse semantic version string like 'v1.0.0' into a comparable (major, minor, patch) tuple."""
    cleaned = str(ver_str or "").strip().lstrip("vV")
    parts = re.findall(r"\d+", cleaned)
    nums = [int(p) for p in parts[:3]]
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


class VaultAutoUpdater:
    """Background daemon thread for periodically syncing LINE databases and updating AI insights."""

    def __init__(self, db: VaultDB, archiver: MediaArchiver, analyzer: ChatAnalyzer):
        self.db = db
        self.archiver = archiver
        self.analyzer = analyzer
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background daemon updater thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="VaultAutoUpdater")
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the updater thread to stop and wait for termination."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        """Periodic loop running auto-sync and analysis."""
        from line_vault.line_reader import BuiltinLineReader

        while not self._stop_event.is_set():
            settings = self.db.get_settings()
            if not settings.get("auto_update_enabled", True):
                if self._stop_event.wait(timeout=2.0):
                    break
                continue

            interval_min = max(1, int(settings.get("auto_update_interval_minutes", 5)))
            interval_sec = interval_min * 60

            # Wait for the interval before running the first cycle
            if self._stop_event.wait(timeout=interval_sec):
                break

            try:
                reader = BuiltinLineReader()
                reader.run_native_sync(self.archiver, days=0, analyzer=self.analyzer)
                monitored_chats = self.db.list_chats(only_monitored=True)
                for c in monitored_chats:
                    if self._stop_event.is_set():
                        break
                    try:
                        self.analyzer.analyze_chat(c["chat_id"])
                    except (ValueError, OSError, sqlite3.Error):
                        continue
            except (OSError, RuntimeError, sqlite3.Error):
                continue


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
        default_line_root = None
        default_line_dir = None
        if local_appdata:
            line_base = Path(local_appdata) / "LINE"
            default_line_root = os.path.normpath(os.path.realpath(str(line_base)))
            candidate = line_base / "Data"
            default_line_dir = str(candidate if candidate.exists() else line_base)

        if not user_dir or not str(user_dir).strip():
            return default_line_dir if (default_line_dir and os.path.isdir(default_line_dir)) else None

        user_dir_str = str(user_dir).strip()
        if default_line_dir and user_dir_str in (
            default_line_dir,
            default_line_root,
            "%LOCALAPPDATA%\\LINE\\Data",
            "%LOCALAPPDATA%\\LINE",
        ):
            return default_line_dir if os.path.isdir(default_line_dir) else None

        base_root = os.path.normpath(os.path.realpath(str(self.allowed_scan_root)))
        fullpath = os.path.normpath(os.path.realpath(user_dir_str))
        allowed_by_root = fullpath.startswith(base_root) or bool(
            default_line_root and fullpath.startswith(default_line_root)
        )
        if not allowed_by_root:
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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
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
                "version": APP_VERSION,
                "app_name": APP_NAME,
                "author": APP_AUTHOR,
                "github_repo": GITHUB_REPO,
                "github_url": GITHUB_REPO_URL,
                "releases_url": GITHUB_RELEASES_URL,
                "stats": stats,
                "vault_dir": str(self.server_vault_dir),
                "line_detected": line_detected,
                "line_path": str(line_path) if line_detected else "",
                "fts5_enabled": self.db.has_fts5,
                "platform": platform.platform(),
            })

        if path == "/api/settings":
            return self._send_json(self.db.get_settings())

        if path == "/api/about":
            return self._send_json({
                "app_name": APP_NAME,
                "version": APP_VERSION,
                "author": APP_AUTHOR,
                "license": "MIT License",
                "github_repo": GITHUB_REPO,
                "github_url": GITHUB_REPO_URL,
                "github_repo_url": GITHUB_REPO_URL,
                "releases_url": GITHUB_RELEASES_URL,
                "github_releases_url": GITHUB_RELEASES_URL,
                "download_exe_url": f"{GITHUB_RELEASES_URL}/latest/download/LINE-Vault-win64.exe",
                "platform": platform.platform(),
                "vault_dir": str(self.server_vault_dir),
            })

        if path == "/api/check-update":
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            default_exe_url = f"{GITHUB_RELEASES_URL}/latest/download/LINE-Vault-win64.exe"
            default_zip_url = f"{GITHUB_RELEASES_URL}/latest/download/LINE-Vault-v{APP_VERSION}-win64.zip"
            try:
                req = urllib.request.Request(
                    api_url,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": f"LINE-Vault/{APP_VERSION}",
                    },
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    rel_data = json.loads(resp.read().decode("utf-8"))
                tag_name = str(rel_data.get("tag_name") or f"v{APP_VERSION}")
                latest_ver = tag_name.lstrip("vV") or APP_VERSION
                has_update = _parse_semver(latest_ver) > _parse_semver(APP_VERSION)
                html_url = str(rel_data.get("html_url") or GITHUB_RELEASES_URL)
                published_at = str(rel_data.get("published_at") or "")
                body_notes = str(rel_data.get("body") or "")
                exe_url = default_exe_url
                zip_url = default_zip_url
                for asset in rel_data.get("assets") or []:
                    if not isinstance(asset, dict):
                        continue
                    aname = str(asset.get("name") or "")
                    burl = str(asset.get("browser_download_url") or "")
                    if burl and aname.lower().endswith(".exe"):
                        exe_url = burl
                    elif burl and aname.lower().endswith(".zip"):
                        zip_url = burl
                return self._send_json({
                    "status": "ok",
                    "current_version": APP_VERSION,
                    "latest_version": latest_ver,
                    "tag_name": tag_name,
                    "has_update": has_update,
                    "release_url": html_url,
                    "download_exe_url": exe_url,
                    "download_zip_url": zip_url,
                    "published_at": published_at,
                    "release_notes": body_notes[:1000],
                })
            except Exception as exc:
                return self._send_json({
                    "status": "offline",
                    "current_version": APP_VERSION,
                    "latest_version": APP_VERSION,
                    "tag_name": f"v{APP_VERSION}",
                    "has_update": False,
                    "release_url": GITHUB_RELEASES_URL,
                    "download_exe_url": default_exe_url,
                    "download_zip_url": default_zip_url,
                    "published_at": "",
                    "message": f"無法連線至 GitHub API ({exc})，可直接開啟 Releases 網頁檢視。",
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
            limit_str = query.get("limit", ["0"])[0]
            try:
                limit = int(limit_str)
            except ValueError:
                limit = 0

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
            limit_str = query.get("limit", ["0"])[0]
            try:
                limit = int(limit_str)
            except ValueError:
                limit = 0

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

    def do_DELETE(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # DELETE /api/chats/<chat_id>
        delete_match = re.match(r"^/api/chats/([^/]+)$", path)
        if delete_match:
            chat_id = urllib.parse.unquote(delete_match.group(1))
            removed = self.archiver.delete_chat(chat_id)
            if not removed:
                return self._send_error("Chat not found", status=404)
            stats = self.db.get_dashboard_stats()
            return self._send_json({"success": True, "deleted_chat_id": chat_id, "stats": stats})

        return self._send_error("Not Found", status=404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # POST /api/settings
        if path == "/api/settings":
            body = self._read_json_body()
            updated = self.db.update_settings(body)
            return self._send_json(updated)

        # POST /api/pick-folder
        if path == "/api/pick-folder":
            body = self._read_json_body()
            init_dir = str(body.get("initial_dir") or "").strip()
            mock_path = str(body.get("mock_path") or "").strip()
            selected_path = mock_path
            if not selected_path and os.environ.get("PYTEST_CURRENT_TEST"):
                selected_path = init_dir or str(self.server_vault_dir)
            elif not selected_path and sys.platform == "win32":
                try:
                    ps_script = (
                        "Add-Type -AssemblyName System.Windows.Forms; "
                        "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                        "$f.Description = '請選擇 LINE Vault 媒體保存目錄'; "
                        "$f.ShowNewFolderButton = $true; "
                    )
                    if init_dir and os.path.isdir(init_dir):
                        ps_script += f"$f.SelectedPath = '{init_dir}'; "
                    ps_script += (
                        "if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { "
                        "Write-Output $f.SelectedPath "
                        "}"
                    )
                    proc = subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=15,
                        check=False,
                    )
                    out = proc.stdout.strip()
                    if out and os.path.isdir(out):
                        selected_path = out
                except (subprocess.SubprocessError, OSError):
                    selected_path = ""
            return self._send_json({"status": "ok", "selected_path": selected_path})

        # POST /api/chats/<chat_id>/delete
        del_match = re.match(r"^/api/chats/([^/]+)/delete$", path)
        if del_match:
            chat_id = urllib.parse.unquote(del_match.group(1))
            removed = self.archiver.delete_chat(chat_id)
            if not removed:
                return self._send_error("Chat not found", status=404)
            stats = self.db.get_dashboard_stats()
            return self._send_json({"success": True, "deleted_chat_id": chat_id, "stats": stats})

        # POST /api/chats/<chat_id>/monitor
        monitor_match = re.match(r"^/api/chats/([^/]+)/monitor$", path)
        if monitor_match:
            chat_id = urllib.parse.unquote(monitor_match.group(1))
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

        # POST /api/demo/clear
        if path == "/api/demo/clear":
            clear_res = self.archiver.clear_demo_data()
            stats = self.db.get_dashboard_stats()
            return self._send_json({"success": True, "clear_result": clear_res, "stats": stats})

        # POST /api/open-url
        if path == "/api/open-url":
            body = self._read_json_body()
            target_url = str(body.get("url") or GITHUB_REPO_URL).strip()
            if not target_url.startswith(GITHUB_REPO_URL):
                return self._send_error("Only official repository URLs are permitted", status=400)
            try:
                if hasattr(os, "startfile"):
                    os.startfile(target_url)  # type: ignore[attr-defined]
                else:
                    webbrowser.open(target_url)
                return self._send_json({"success": True, "opened_url": target_url})
            except Exception as exc:
                return self._send_error(str(exc), status=500)

        # POST /api/download-update
        if path == "/api/download-update":
            body = self._read_json_body()
            dl_url = str(body.get("download_url") or f"{GITHUB_REPO_URL}/releases/latest/download/LINE-Vault-win64.exe").strip()
            if not dl_url.startswith(GITHUB_REPO_URL) and not dl_url.startswith("https://objects.githubusercontent.com/"):
                return self._send_error("Untrusted download URL", status=400)
            downloads_dir = Path.home() / "Downloads"
            if not downloads_dir.exists():
                downloads_dir = self.server_vault_dir
            filename = Path(urllib.parse.urlparse(dl_url).path).name or "LINE-Vault-win64.exe"
            if not filename.endswith((".exe", ".zip")):
                filename = "LINE-Vault-win64.exe"
            dest_path = downloads_dir / f"LINE-Vault-latest-{filename}"
            try:
                req = urllib.request.Request(
                    dl_url,
                    headers={"User-Agent": f"LINE-Vault/{APP_VERSION}"},
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data_bytes = resp.read()
                dest_path.write_bytes(data_bytes)
                return self._send_json({
                    "success": True,
                    "saved_path": str(dest_path),
                    "size_bytes": len(data_bytes),
                })
            except Exception as exc:
                return self._send_error(f"下載更新檔案失敗 ({exc})", status=500)

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
        settings = self.db.get_settings()
        custom_storage = os.path.normpath(os.path.realpath(str(settings.get("media_storage_dir", ""))))

        allowed_roots = [base_vault]
        if custom_storage and os.path.isdir(custom_storage):
            allowed_roots.append(custom_storage)

        if os.path.isabs(rel_path):
            fullpath = os.path.normpath(os.path.realpath(rel_path))
        else:
            fullpath = os.path.normpath(os.path.realpath(os.path.join(base_vault, rel_path)))
            if not os.path.isfile(fullpath) and custom_storage:
                cand = os.path.normpath(os.path.realpath(os.path.join(custom_storage, rel_path)))
                if os.path.isfile(cand):
                    fullpath = cand

        is_allowed = any(
            fullpath == root or fullpath.startswith(root + os.sep)
            for root in allowed_roots
        )
        if not is_allowed:
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
    enable_auto_updater: bool = False,
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
    if enable_auto_updater:
        updater = VaultAutoUpdater(db, archiver, analyzer)
        updater.start()
        server.auto_updater = updater
    else:
        server.auto_updater = None
    return server


def run_server(
    vault_dir: Path | str = "vault_data",
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
    allowed_scan_root: Path | str | None = None,
) -> None:
    """Run the LINE Vault HTTP server until interrupted."""
    server = create_server(
        vault_dir=vault_dir,
        host=host,
        port=port,
        allowed_scan_root=allowed_scan_root,
        enable_auto_updater=True,
    )
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
        if getattr(server, "auto_updater", None):
            server.auto_updater.stop()
        server.server_close()
