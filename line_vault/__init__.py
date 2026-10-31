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

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "VaultDB",
    "MediaArchiver",
    "ChatAnalyzer",
    "derive_media_keys",
    "decrypt_e2ee_media",
    "encrypt_e2ee_media",
    "sniff_media_format",
]
