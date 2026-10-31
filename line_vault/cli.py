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


def launch_gui(
    vault_dir: Path | str = "vault_data",
    host: str = "127.0.0.1",
    port: int = 8765,
    no_window: bool = False,
) -> int:
    """Launch LINE Vault local engine and open the standalone native app window."""
    v_dir = Path(vault_dir).resolve()
    v_dir.mkdir(parents=True, exist_ok=True)

    try:
        server = create_server(vault_dir=v_dir, host=host, port=port)
    except OSError:
        # Port already in use; bind to any available ephemeral port
        server = create_server(vault_dir=v_dir, host=host, port=0)

    actual_port = server.server_port
    app_url = f"http://{host}:{actual_port}"

    srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
    srv_thread.start()

    # Allow server to bind and start listening
    time.sleep(0.15)

    if not no_window:
        browser_exe = find_system_app_browser()
        if browser_exe:
            # Launch in standalone application window mode (removes address bar and tabs).
            # Note: Do not shut down server on proc.wait() because Edge/Chrome hands off
            # to an existing browser process and exits the launcher stub immediately.
            app_args = [
                browser_exe,
                f"--app={app_url}",
                "--window-size=1280,820",
            ]
            try:
                subprocess.Popen(app_args)
            except (OSError, subprocess.SubprocessError):
                webbrowser.open(app_url)
        else:
            webbrowser.open(app_url)

    try:
        while srv_thread.is_alive():
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()

    return 0


def main(argv: list[str] | None = None) -> int:
    """Pure GUI launcher entrypoint."""
    parser = argparse.ArgumentParser(
        prog="line-vault",
        description="LINE Vault - Windows 11 本地對話與防過期媒體中心（純 GUI 桌面應用程式）",
    )
    parser.add_argument(
        "--vault-dir",
        default="vault_data",
        help="金庫資料儲存目錄 (預設: vault_data)",
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
