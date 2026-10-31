"""LINE Vault - Windows 11 本地對話與防過期媒體管理中心."""

from line_vault.analyzer import ChatAnalyzer
from line_vault.archiver import MediaArchiver
from line_vault.crypto import (
    decrypt_e2ee_media,
    derive_media_keys,
    encrypt_e2ee_media,
    sniff_media_format,
)
from line_vault.db import VaultDB

__version__ = "1.0.0"
APP_NAME = "LINE Vault — 本地對話與防過期媒體中心"
APP_VERSION = __version__
APP_AUTHOR = "SanHsien"
GITHUB_REPO = "SanHsien/line-vault"
GITHUB_REPO_URL = "https://github.com/SanHsien/line-vault"
GITHUB_RELEASES_URL = "https://github.com/SanHsien/line-vault/releases"

__all__ = [
    "__version__",
    "APP_NAME",
    "APP_VERSION",
    "APP_AUTHOR",
    "GITHUB_REPO",
    "GITHUB_REPO_URL",
    "GITHUB_RELEASES_URL",
    "VaultDB",
    "MediaArchiver",
    "ChatAnalyzer",
    "derive_media_keys",
    "decrypt_e2ee_media",
    "encrypt_e2ee_media",
    "sniff_media_format",
]
