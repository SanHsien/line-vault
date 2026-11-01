"""LINE Vault - Windows 11 本地對話與防過期媒體管理中心."""

import sys
from pathlib import Path

from line_vault.analyzer import ChatAnalyzer
from line_vault.archiver import MediaArchiver
from line_vault.crypto import (
    decrypt_e2ee_media,
    derive_media_keys,
    encrypt_e2ee_media,
    sniff_media_format,
)
from line_vault.db import VaultDB

__version__ = "1.3.0"
APP_NAME = "LINE Vault — 本地對話與防過期媒體中心"
APP_VERSION = __version__
APP_AUTHOR = "SanHsien"
GITHUB_REPO = "SanHsien/line-vault"
GITHUB_REPO_URL = "https://github.com/SanHsien/line-vault"
GITHUB_RELEASES_URL = "https://github.com/SanHsien/line-vault/releases"


def get_default_vault_dir() -> Path:
    """Resolve default vault directory `<app_dir>/line-vault`.

    When compiled as a standalone binary (PyInstaller/sys.frozen), app_dir is sys.executable.parent.
    Otherwise, app_dir is current working directory.
    """
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
    else:
        app_dir = Path.cwd().resolve()
    return (app_dir / "line-vault").resolve()


__all__ = [
    "__version__",
    "APP_NAME",
    "APP_VERSION",
    "APP_AUTHOR",
    "GITHUB_REPO",
    "GITHUB_REPO_URL",
    "GITHUB_RELEASES_URL",
    "get_default_vault_dir",
    "VaultDB",
    "MediaArchiver",
    "ChatAnalyzer",
    "derive_media_keys",
    "decrypt_e2ee_media",
    "encrypt_e2ee_media",
    "sniff_media_format",
]
