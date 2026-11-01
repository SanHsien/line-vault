"""Windows 11 Native Pure GUI Desktop Launcher for LINE Vault.

Running this module directly starts the local LINE Vault service and opens a dedicated,
borderless desktop application window via Microsoft Edge / Chrome application mode.
Zero command line interaction is required.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from line_vault import get_default_vault_dir
from line_vault.server import create_server


def find_system_app_browser() -> str | None:
    """Locate Microsoft Edge or Google Chrome to run in standalone window mode (--app)."""
    # 1. Check PATH for msedge / chrome
    for exe in ("msedge.exe", "msedge", "chrome.exe", "chrome"):
        found = shutil.which(exe)
        if found and Path(found).is_file():
            return found

    # 2. Check standard Windows installation paths
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_appdata = os.environ.get("LOCALAPPDATA", "")

    candidate_locations = [
        # Edge (standard on all Windows 10 & 11)
        rf"{program_files_x86}\Microsoft\Edge\Application\msedge.exe",
        rf"{program_files}\Microsoft\Edge\Application\msedge.exe",
        rf"{local_appdata}\Microsoft\Edge\Application\msedge.exe",
        # Chrome
        rf"{program_files}\Google\Chrome\Application\chrome.exe",
        rf"{program_files_x86}\Google\Chrome\Application\chrome.exe",
        rf"{local_appdata}\Google\Chrome\Application\chrome.exe",
    ]

    for cand in candidate_locations:
        if cand and Path(cand).is_file():
            return cand

    return None


def _cleanup_stale_instance_on_port(host: str, port: int) -> None:
    """If an older background LINE-Vault-win64.exe is holding the port, terminate it cleanly."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        if sock.connect_ex((host, port)) != 0:
            return

    # Port is currently occupied; if running on Windows, terminate stale LINE-Vault-win64.exe processes
    if os.name == "nt":
        current_pid = os.getpid()
        try:
            subprocess.run(
                [
                    "taskkill",
                    "/F",
                    "/FI",
                    f"PID ne {current_pid}",
                    "/IM",
                    "LINE-Vault-win64.exe",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
            time.sleep(0.3)
        except (OSError, subprocess.SubprocessError):
            return


def launch_gui(
    vault_dir: Path | str | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    no_window: bool = False,
) -> int:
    """Launch LINE Vault local engine and open the standalone native app window."""
    v_dir = Path(vault_dir).resolve() if vault_dir is not None else get_default_vault_dir()
    v_dir.mkdir(parents=True, exist_ok=True)

    if not no_window:
        _cleanup_stale_instance_on_port(host, port)

    try:
        server = create_server(vault_dir=v_dir, host=host, port=port)
    except OSError:
        # Port still in use by another application; bind to any available ephemeral port
        server = create_server(vault_dir=v_dir, host=host, port=0)

    actual_port = server.server_port
    app_url = f"http://{host}:{actual_port}"

    srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
    srv_thread.start()

    # Allow server to bind and start listening
    time.sleep(0.15)

    app_proc: subprocess.Popen | None = None
    if not no_window:
        browser_exe = find_system_app_browser()
        if browser_exe:
            # Dedicated clean profile directory ensures:
            # 1. Zero third-party browser extensions / ad injections ("AI 速讀" etc.)
            # 2. Standalone window mode (--app) is always honored even when Edge/Chrome is already open
            profile_dir = v_dir / ".gui_profile"
            profile_dir.mkdir(parents=True, exist_ok=True)
            app_args = [
                browser_exe,
                f"--app={app_url}",
                f"--user-data-dir={profile_dir}",
                "--disable-extensions",
                "--disable-component-extensions-with-background-pages",
                "--disable-background-mode",
                "--disable-sync",
                "--disable-features=Translate,EdgeSidebar,msEdgeSidebarV2,msHubApps,msEdgeCollections,msEdgeStartupBoost",
                "--no-first-run",
                "--no-default-browser-check",
                "--window-size=1440,900",
            ]
            try:
                app_proc = subprocess.Popen(app_args)
            except (OSError, subprocess.SubprocessError):
                webbrowser.open(app_url)
        else:
            webbrowser.open(app_url)

    try:
        start_ts = time.time()
        while srv_thread.is_alive():
            now = time.time()
            # 1. Window close beacon received and grace period elapsed (prevents accidental exit on F5)
            pending = getattr(server, "shutdown_pending_time", None)
            if pending is not None and (now - pending) >= 1.2:
                break

            # 2. Heartbeat loss after client was active (> 7.0 seconds of no heartbeats)
            if not no_window and getattr(server, "has_active_client", False):
                last_hb = getattr(server, "last_heartbeat_time", now)
                if (now - last_hb) > 7.0:
                    break

            # 3. Dedicated browser process exited
            if app_proc is not None:
                ret = app_proc.poll()
                if ret is not None and (now - start_ts) > 1.0:
                    break

            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        if app_proc is not None and app_proc.poll() is None:
            try:
                app_proc.terminate()
            except OSError:
                pass

    return 0


def main(argv: list[str] | None = None) -> int:
    """Pure GUI launcher entrypoint."""
    parser = argparse.ArgumentParser(
        prog="line-vault",
        description="LINE Vault - Windows 11 本地對話與防過期媒體中心（純 GUI 桌面應用程式）",
    )
    parser.add_argument(
        "--vault-dir",
        default=None,
        help="金庫資料儲存目錄 (預設: <程式所在資料夾>\\line-vault)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="本地服務通訊埠 (預設: 8765)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="本機監聽位址 (預設: 127.0.0.1)",
    )
    parser.add_argument(
        "--no-window",
        action="store_true",
        help="僅啟動背景引擎，不彈出桌面應用視窗",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return launch_gui(
        vault_dir=args.vault_dir,
        host=args.host,
        port=args.port,
        no_window=args.no_window,
    )


if __name__ == "__main__":
    sys.exit(main())
