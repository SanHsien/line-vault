"""Cryptographic utilities for LINE E2EE media decryption, authentication, and sniffing."""

import base64
import binascii
import hashlib
import hmac
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def derive_media_keys(material_b64: str) -> tuple[bytes, bytes, bytes]:
    """Derive encryption, MAC, and IV keys from a 32-byte base64 key material.

    According to LINE Encryption Overview v2.2:
    - 76 bytes derived via HKDF-SHA256 (salt=None, info=b'FileEncryption')
    - enc_key: derived[0:32]
    - mac_key: derived[32:64]
    - iv: derived[64:76] + b'\\x00\\x00\\x00\\x00' (16 bytes)
    """
    if not material_b64 or not isinstance(material_b64, str):
        raise ValueError("MEDIA_KEY_UNAVAILABLE")

    try:
        raw_material = base64.b64decode(material_b64.strip(), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("MEDIA_KEY_UNAVAILABLE") from exc

    if len(raw_material) != 32:
        raise ValueError("MEDIA_KEY_UNAVAILABLE")

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=76,
        salt=None,
        info=b"FileEncryption",
    )
    derived = hkdf.derive(raw_material)

    enc_key = derived[0:32]
    mac_key = derived[32:64]
    iv = derived[64:76] + b"\x00\x00\x00\x00"

    return enc_key, mac_key, iv


def decrypt_e2ee_media(data: bytes, material_b64: str) -> bytes:
    """Authenticate and decrypt LINE E2EE encrypted media payload.

    Payload format:
    - ciphertext: data[:-32]
    - tag: data[-32:] (HMAC-SHA256 of ciphertext using mac_key)
    Raises ValueError('MEDIA_KEY_UNAVAILABLE') or ValueError('MEDIA_AUTHENTICATION_FAILED').
    """
    if not isinstance(data, (bytes, bytearray)) or len(data) < 33:
        raise ValueError("MEDIA_KEY_UNAVAILABLE")

    raw_data = bytes(data)
    ciphertext = raw_data[:-32]
    tag = raw_data[-32:]

    enc_key, mac_key, iv = derive_media_keys(material_b64)

    expected_tag = hmac.digest(mac_key, ciphertext, "sha256")
    if not hmac.compare_digest(expected_tag, tag):
        raise ValueError("MEDIA_AUTHENTICATION_FAILED")

    cipher = Cipher(algorithms.AES(enc_key), modes.CTR(iv))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return plaintext


def encrypt_e2ee_media(plaintext: bytes, material_b64: str) -> bytes:
    """Encrypt and authenticate media payload using AES-256-CTR and HMAC-SHA256.

    Appends the 32-byte HMAC-SHA256 authentication tag to ciphertext.
    Used for creating test fixtures and mock LINE caches.
    """
    if not isinstance(plaintext, (bytes, bytearray)):
        raise TypeError("Plaintext must be bytes")

    enc_key, mac_key, iv = derive_media_keys(material_b64)

    cipher = Cipher(algorithms.AES(enc_key), modes.CTR(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(bytes(plaintext)) + encryptor.finalize()
    tag = hmac.digest(mac_key, ciphertext, "sha256")

    return ciphertext + tag


def generate_key_material() -> str:
    """Generate a random 32-byte key material encoded in base64."""
    return base64.b64encode(os.urandom(32)).decode("ascii")


def sniff_media_format(data: bytes, fallback_filename: str | None = None) -> dict:
    """Identify media type, mime type, extension, and calculate SHA256 checksum.

    Recognizes PNG, JPEG, GIF, WEBP, MP4, MP3, WAV, OGG, PDF, ZIP, or falls back.
    """
    data_bytes = bytes(data) if isinstance(data, (bytes, bytearray)) else b""
    size = len(data_bytes)
    sha256_hash = hashlib.sha256(data_bytes).hexdigest()

    # Default fallback
    media_type = "file"
    format_name = "bin"
    mime_type = "application/octet-stream"
    ext = ".bin"

    # Magic byte inspection
    if data_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        media_type = "image"
        format_name = "png"
        mime_type = "image/png"
        ext = ".png"
    elif data_bytes.startswith(b"\xff\xd8\xff"):
        media_type = "image"
        format_name = "jpeg"
        mime_type = "image/jpeg"
        ext = ".jpg"
    elif data_bytes.startswith(b"GIF87a") or data_bytes.startswith(b"GIF89a"):
        media_type = "image"
        format_name = "gif"
        mime_type = "image/gif"
        ext = ".gif"
    elif size >= 12 and data_bytes[:4] == b"RIFF" and data_bytes[8:12] == b"WEBP":
        media_type = "image"
        format_name = "webp"
        mime_type = "image/webp"
        ext = ".webp"
    elif size >= 8 and data_bytes[4:8] == b"ftyp":
        media_type = "video"
        format_name = "mp4"
        mime_type = "video/mp4"
        ext = ".mp4"
    elif data_bytes.startswith(b"ID3") or (
        size >= 4 and data_bytes[0] == 0xFF and (data_bytes[1] & 0xFE) in (0xFA, 0xF2, 0xE2) and (data_bytes[2] & 0xF0) not in (0x00, 0xF0)
    ):
        media_type = "audio"
        format_name = "mp3"
        mime_type = "audio/mpeg"
        ext = ".mp3"
    elif size >= 12 and data_bytes[:4] == b"RIFF" and data_bytes[8:12] == b"WAVE":
        media_type = "audio"
        format_name = "wav"
        mime_type = "audio/wav"
        ext = ".wav"
    elif data_bytes.startswith(b"OggS"):
        media_type = "audio"
        format_name = "ogg"
        mime_type = "audio/ogg"
        ext = ".ogg"
    elif data_bytes.startswith(b"%PDF-"):
        media_type = "file"
        format_name = "pdf"
        mime_type = "application/pdf"
        ext = ".pdf"
    elif data_bytes.startswith(b"PK\x03\x04"):
        media_type = "file"
        format_name = "zip"
        mime_type = "application/zip"
        ext = ".zip"
    elif fallback_filename:
        # Fallback to file extension
        suffix = Path(fallback_filename).suffix.lower()
        if suffix in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"]:
            media_type = "image"
            format_name = suffix.lstrip(".")
            mime_type = f"image/{'jpeg' if format_name in ['jpg', 'jpeg'] else format_name}"
            ext = suffix
        elif suffix in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            media_type = "video"
            format_name = suffix.lstrip(".")
            mime_type = f"video/{format_name}"
            ext = suffix
        elif suffix in [".mp3", ".wav", ".ogg", ".m4a", ".aac"]:
            media_type = "audio"
            format_name = suffix.lstrip(".")
            mime_type = f"audio/{format_name}"
            ext = suffix
        elif suffix in [".txt", ".csv", ".json", ".xml", ".md"]:
            media_type = "file"
            format_name = suffix.lstrip(".")
            mime_type = "text/plain"
            ext = suffix
        elif suffix in [".pdf", ".zip", ".docx", ".xlsx", ".pptx"]:
            media_type = "file"
            format_name = suffix.lstrip(".")
            mime_type = "application/octet-stream"
            ext = suffix

    return {
        "media_type": media_type,
        "format": format_name,
        "mime_type": mime_type,
        "ext": ext,
        "sha256": sha256_hash,
        "size_bytes": size,
    }
