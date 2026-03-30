"""
Dennis Forge — Optional bundle encryption layer

Philosophy:
- Optional, never mandatory
- Offline-first
- Simple, auditable crypto
- No lock-in

Implements:
- AES-256 ZIP encryption
- Password-based protection
"""

from __future__ import annotations

import io
import getpass
import pyzipper


# ============================================================
# PASSWORD HELPERS
# ============================================================

def prompt_password(confirm: bool = False) -> bytes:
    """
    Secure password prompt.

    Returns bytes (never str) for crypto safety.
    """
    pwd = getpass.getpass("Bundle password: ")

    if confirm:
        pwd2 = getpass.getpass("Confirm password: ")
        if pwd != pwd2:
            raise ValueError("Passwords do not match")

    if not pwd:
        raise ValueError("Empty password not allowed")

    return pwd.encode("utf-8")


# ============================================================
# ENCRYPTION
# ============================================================

def encrypt_bytes(data: bytes, password: bytes) -> bytes:
    """
    Encrypt arbitrary bytes into an AES ZIP container.

    Returns encrypted ZIP bytes.
    """
    buf = io.BytesIO()

    with pyzipper.AESZipFile(
        buf,
        mode="w",
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as zf:
        zf.setpassword(password)
        zf.writestr("payload.bin", data)

    return buf.getvalue()


def decrypt_bytes(data: bytes, password: bytes) -> bytes:
    """
    Decrypt AES ZIP bytes back into original payload.
    """
    buf = io.BytesIO(data)

    with pyzipper.AESZipFile(buf, mode="r") as zf:
        zf.setpassword(password)
        return zf.read("payload.bin")